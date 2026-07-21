---
name: worker-fleet-pattern
description: >-
  Use when a project has (or will have) a broker-backed worker and no document
  records where the system deploys or what shape the worker fleet has — or when
  any of these symptoms appear: plan reviews argue from a "small fixed set of
  hand-provisioned workers" assumption nobody ever decided; a design makes
  adding worker N+1 more expensive than worker N (hand-issued certificate,
  operator-inserted registration row, fixed container name); worker identity
  and channel security are being designed per deployment target instead of
  once; or secure Worker↔Core communication is deferred because "we only have
  two workers." Produces two day-1 ADRs: the deployment-topology decision
  (homogeneous fleet, replica-count-only scaling) and the fleet-identity
  decision (self-enrollment with the control plane as certificate authority).
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.1"
---

# Worker Fleet Pattern

## Purpose

**In one line:** decide on day 1 that the workers are a homogeneous,
horizontally scaled fleet whose size changes by replica count alone — and
derive worker identity and channel security from that rule, so no per-worker
ceremony can ever creep in.

The [worker pattern](worker_pattern.md) splits the API from a broker-backed
worker. This pattern answers the two questions that follow immediately and are
brutally expensive to answer late:

1. **Topology** — where does the system deploy, and how many workers does a
   deployment have? Left unrecorded, every later plan and review silently
   defaults to "a small fixed set of individually provisioned workers," and
   whole design rounds get argued from that wrong assumption.
2. **Identity** — how does a worker prove it is a legitimate fleet member
   before it receives work (and possibly resolved credentials)? Designed after
   the fleet exists, the answer degenerates into hand-issued certificates and
   operator-inserted database rows — exactly the ceremony that breaks scaling.

> **Core principle (single responsibility, applied to fleet shape):** every
> worker is identical and can execute every task type. There are no worker
> roles, no specialization tiers, no per-worker capability differences. Load
> spreads through the broker's competing-consumer delivery on shared queues:
> more workers means more consumers, nothing else.

## Decision 1 — Topology: homogeneous fleet, replica-count-only scaling

Record in an ADR:

- **The deployment targets**, all served from the **same container images** —
  typically a primary production platform (e.g. a Kubernetes cluster running
  N worker pods) and a small-scale form (e.g. Docker Compose on a homelab or
  client on-premise server running 1–N containers). Deployments differ only in
  platform and replica count, never in worker behavior.
- **The zero-ceremony rule:** adding a worker must require **no** manual step
  proportional to worker count — no hand-issued certificate, no manually
  pre-provisioned per-instance database row, no operator registration
  ceremony. `kubectl scale` (or adding a Compose replica) is the entire
  procedure. **Any design that makes worker N+1 more expensive to add than
  worker N violates the ADR.** Rows created automatically at runtime (the
  enrollment upserts below) satisfy this rule; rows an operator must insert
  violate it.

This one paragraph is the fulcrum: every later identity, security, and
scheduling design is checked against "does this scale with worker count?"

## Decision 2 — Identity: self-enrollment, control plane as CA

One mechanism, identical on every deployment target, no external dependency
(cluster-only tools like cert-manager don't unify a Compose target and split
the feature per platform):

- **Two control-plane listeners.** An **mTLS listener** carries every worker
  RPC (task control, lifecycle, execution), requiring client certificates
  issued by the control plane's own CA. An **enrollment listener**
  (server-TLS, no client certs) hosts enrollment plus health/reflection;
  workers verify it against a mounted trust anchor, so enrollment cannot be
  intercepted or impersonated.
- **A worker mounts exactly two artifacts:** the server trust anchor (a
  long-lived public certificate) and the shared enrollment secret. Nothing
  else — nothing per-worker.
- **Enrollment protocol (HMAC challenge–response + CSR):** at boot the worker
  generates a keypair **in memory** (the private key never persists and never
  transits), requests a single-use nonce, and sends
  `{name, CSR, HMAC(secret, nonce ‖ name ‖ CSR)}`. The control plane verifies
  the tag (constant-time), verifies the CSR self-signature (proof of key
  possession), stamps the identity SAN itself (the requested identity is
  ignored), and signs a short-lived leaf certificate. The secret never crosses
  the wire; the nonce kills replay; binding name+CSR into the tag kills
  tampering.
- **Make-before-break renewal:** the new fingerprint is stored *pending*
  while the previous stays valid; the first authenticated mTLS use promotes
  pending → active and retires the predecessor. A lost enrollment response
  strands nothing.
- **Worker names come from the platform** — pod name via the downward API on
  Kubernetes, container hostname on Compose — with an env override only for
  exceptional deployments. A fixed `container_name` is forbidden: it blocks
  replica scaling.
- **The registration table is machine-populated** by enrollment upserts
  (name, active + pending fingerprints, timestamps, enabled flag). Two
  lifecycle words, never conflated: **supersession** (automatic,
  certificate-level replacement at renewal) and **disablement** (operator,
  sticky, per-worker kill switch — the one state that never self-heals).
- **Everything else self-heals:** every boot re-enrolls (in-memory key),
  long-lived processes proactively re-enroll at ~2/3 of leaf lifetime, and any
  recoverable certificate rejection triggers automatic re-enrollment with
  backoff. Issuer-CA rotation is "replace the material, restart the control
  plane" — the fleet re-enrolls itself. No plaintext fallback exists at any
  stage.

## Worked Example (ironbox)

The reference codebase locked both decisions in two ADRs ("ADR-R07: Deployment
targets and worker fleet topology", "ADR-R08: Worker–Core security") after a
plan-review round argued findings from an unstated "small fixed set of
hand-provisioned workers" assumption:

- **Topology:** SaaS on Kubernetes (~10 worker pods serving the first ~100
  clients, 20–50 expected within ~2 years, no design ceiling) and
  homelab/on-premise Docker Compose (typically 2–3 containers) — same images,
  differing only in platform and replica count. The zero-ceremony rule was
  written as binding: any design making worker N+1 costlier than worker N
  violates the ADR.
- **Identity:** Core is the CA (candidate implementation `rcgen` — pure Rust,
  no openssl), issuing 60-day worker leaf certificates. Two Core listeners
  (mTLS for all worker RPCs; server-TLS enrollment hosting enrollment +
  health/reflection). Workers derive their name from the pod name (downward
  API) or container hostname, enroll via the HMAC + CSR exchange at every
  boot, and proactively re-enroll at ~day 40 of the 60-day leaf. A
  cert-manager-based identity was explicitly rejected because it could not
  unify the Compose targets. One deployment-file consequence: the Compose
  worker service had to drop its fixed `container_name` so replicas could
  scale.

## Why day 1 and not later

The worker pattern's contract crate and lease fencing already exist from the
first task type. The moment tasks carry anything sensitive (resolved
credentials, tenant data), the Worker↔Core channel needs mutual identity — and
if the topology ADR wasn't written, the identity design will quietly assume
hand-provisioning, which then contaminates schema (operator-inserted rows),
deployment files (fixed container names), and runbooks (certificate
ceremonies). Unwinding that is a redesign; writing the two ADRs before the
first worker ships is an afternoon.

## Quick Reference — Invariants

- **Homogeneous fleet:** every worker executes every task type; capacity
  scaling is only a replica-count change.
- **Zero per-worker ceremony:** no step of adding a worker scales with worker
  count. Runtime-created rows yes; operator-created rows no.
- **Same images at every deployment size**, from production cluster to
  homelab.
- **One identity mechanism for all targets** — self-enrollment against the
  control plane as CA; no external identity infrastructure.
- **Private keys never leave the worker process**; the shared secret never
  transits the network; certificates are short-lived and renewal is
  make-before-break.
- **Platform-derived worker names**; never a fixed container name.
- **Disablement is the only non-self-healing state**, and it is an explicit
  operator decision.

## Anti-Patterns to Avoid

- **Manual per-worker provisioning** — hand-issued certificates,
  operator-inserted registration rows, rotate-by-runbook. Violates the
  zero-ceremony rule the moment the fleet grows.
- **Per-target identity mechanisms** (cert-manager/SPIFFE on the cluster,
  something else on Compose) — splits one feature into N implementations and
  adds external dependencies.
- **Control-plane-generated keypairs shipped to workers** — private keys must
  never transit or exist outside the worker process.
- **A plaintext enrollment channel or plaintext fallback after a failed TLS
  rollout** — recovery is forward-only and self-healing; a fallback removes
  the boundary protecting resolved credentials.
- **Worker roles / capability tiers** — reintroduces per-worker
  differentiation; scheduling, capacity math, and admission all fork on it.
- **Unrecorded topology** — every reviewer re-derives their own fleet
  assumption and findings get argued from the wrong one.

## Relationship to Other Patterns and Skills

- **[worker pattern](worker_pattern.md)** — the prerequisite: API/worker/broker
  split, contract crate, lease fencing, drain semantics. This pattern fixes
  the fleet's *shape* and *identity* on top of it.
- **[observability posture](../decisions/observability_posture_pattern.md)** —
  enrollment attempts and issuances are audit-logged as Stage-1 structured
  events; the machine-populated registration table is a durable-row surface
  runbook queries (and later metrics) read.
- **[local port allocation](../decisions/local_port_allocation_pattern.md)** —
  the two control-plane listeners claim their ports from the project's
  allocated range.
- **`rust-architecture-test-setup` (skill)** — the manifest dependency gate
  keeps the worker core-free and free of direct database drivers, which is
  what keeps the fleet stateless and horizontally scalable.
- **`greenfield-project-setup` (skill)** — sequences both ADRs into the day-1
  decision phase when a worker is in scope.
