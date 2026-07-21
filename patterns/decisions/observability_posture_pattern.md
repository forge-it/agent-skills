---
name: observability-posture-pattern
description: >-
  Use when starting a new backend project (or reviewing a plan that promises
  "metrics and alerts") and any of these symptoms are present: implementation
  plans pledge dashboards or alerting while no binary has a metric recorder,
  exporter, or scrape endpoint; a feature milestone is about to introduce the
  project's first telemetry stack as a side effect; log statements are
  free-form strings nobody can query; operational state lives only in logs
  instead of durable rows; or someone proposes building a homegrown
  collection/aggregation pipeline. Produces a day-1 ADR that locks the
  boundary — the application emits, the platform collects — and stages
  adoption so instrumentation (the only expensive-to-change part) is right
  from commit 1 while the telemetry stack arrives with the deployment
  milestone that can actually consume it.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.1"
---

# Observability Posture Pattern

## Purpose

**In one line:** decide on day 1 that the application only *emits* stable,
structured signals — named `tracing`/logging events and durable state rows —
and that collecting, storing, dashboarding, and alerting are always the
deployment platform's job, adopted in named stages.

Every backend project eventually needs alerting and dashboards. The trap is
timing: a feature milestone promises "emit a metric, add an alert," and
suddenly a data-plane change is also selecting a telemetry product, deploying
a collector, and inventing a pipeline. The opposite trap is vagueness —
"metrics later, somewhere" — which ships a SaaS with no alerting at all.

The resolution rests on two facts:

1. **Signals differ by question shape.** Structured events answer *"what
   happened in this case?"* (forensics, audit). Metrics answer *"how is the
   system behaving now — should a human be woken up?"* (alerting, SLOs).
   Traces answer cross-service latency questions — least urgent when the
   workflows are already durable database rows.
2. **Only instrumentation is expensive to change later.** Backends,
   collectors, and dashboards are swappable deployment infrastructure. A
   logging facade already in the binary can be configured for JSON stdout
   today and OTLP later without touching a single call site.

So the day-1 decision is about the *boundary and the instrumentation*, never
about the stack.

> **Core principle (separation of concerns):** the application owns *emitting*
> — stable event names, typed fields, durable state rows. The platform owns
> *collecting* — shipping, storage, indexing, dashboards, alert evaluation.
> Nothing the application ships may aggregate, forward, or store telemetry for
> its own sake. One boundary, two owners, never blurred.

## The Golden Rule and the Three Surfaces

The application's only observability surfaces are, in adoption order:

1. **Stable, named structured events** (typed fields, JSON to stdout) via the
   language's standard facade (`tracing` in Rust, `structlog`/stdlib logging in
   Python — see the `general-logging` skill for event shape).
2. **Durable state rows** in the primary database — readiness, dispatch
   intents, attempt outcomes, audit trails. These exist for *correctness*
   first; observability reads them for free.
3. *(Only on demonstrated need)* one Prometheus-format `/metrics` endpoint.

The application never ships logs, never aggregates for dashboards, never hosts
an observability-only event store.

## Staged Adoption

### Stage 1 — commit 1 (always)

- Declare operational events as a **stable contract**: event names and typed
  fields are documented; renaming one is a breaking change to runbooks and is
  treated as such.
- Structured JSON to stdout; `docker logs` / `kubectl logs` are the readers.
- Operational questions get **runbook queries** over the durable rows (SQL)
  and broker state (management UI / CLI) — "poor man's metrics," deliberately:
  the same rows become real metrics in Stage 2 with zero application change.
- Every plan-level "emit a metric" / "add an alert" promise is replaced by a
  named event plus its runbook check.
- **No new dependencies, no exporter, no collector, no metrics stack.**

### Stage 2 — bound to a named deployment milestone (committed, not vague)

When the production (e.g. Kubernetes) deployment is built, *that* plan
installs the standard platform stack — e.g. kube-prometheus-stack (Prometheus
+ Alertmanager + Grafana) plus Loki — and lights up what Stage 1 already
emits:

- **Logs:** Loki tails container stdout; the Stage-1 structured events become
  searchable and dashboardable with zero application changes.
- **Free metrics:** broker and database exporters (RabbitMQ's built-in
  Prometheus plugin, `postgres_exporter`), node/kube-state-metrics,
  crash-loop alerting — none of it touches the application.
- **App-level metrics without touching the app:** a scheduled SQL exporter
  (e.g. Prometheus `sql_exporter`) runs the Stage-1 runbook queries and
  exposes them as gauges. Workers ready, dispatch backlog, attempts
  reconciling become alertable time series *precisely because* Stage 1 put
  that state in durable rows.

Small deployments (homelab, on-prem Compose) keep `docker logs` + runbooks
from the same images; no obligation.

**The stage must be bound to a named milestone.** "Metrics later" with no
owner is how a SaaS launches without alerting.

### Stage 3 — only on demonstrated need

- A real `/metrics` endpoint (via the language's metrics facade) for
  high-frequency counters SQL polling cannot serve.
- OpenTelemetry/OTLP if a vendor backend or multi-backend routing becomes real.
- Distributed tracing if cross-service latency debugging becomes a recurring
  pain.

Each is additive on top of the Stage-1 contract; nothing from earlier stages
is discarded.

## Worked Example (ironbox)

The reference codebase locked this posture in an ADR ("ADR-R10: Observability
posture") while planning its worker execution bridge. The bridge plan had
promised dispatch-recovery metrics and DLQ alerts while neither binary had any
recorder or exporter — only `tracing` formatting. The ADR:

- swept the plan of every "emit a metric" promise, replacing each with a named
  structured event plus a runbook query over the durable task/attempt rows
  that already existed for correctness (leases, dispatch intents, enrollment
  and cancellation audit trails);
- committed Stage 2 to the SaaS Kubernetes deployment milestone, where the
  RabbitMQ Prometheus plugin, `postgres_exporter`, and `sql_exporter` over the
  Stage-1 runbook queries provide alerting with zero app changes;
- explicitly rejected OTLP-now, a scrape endpoint with no scraper deployed to
  read it, Kafka as an event log at a volume Postgres rows already covered,
  and any homegrown collection pipeline.

## Quick Reference — Invariants

- **The application emits; the platform collects.** Shipping, storage,
  indexing, dashboards, and alert evaluation are never application code.
- **Event names and fields are a stable contract** from commit 1. Renames are
  breaking changes.
- **Structured JSON to stdout** — never free-form strings, never app-side log
  shipping.
- **Correctness state lives in durable rows**, and observability reads those
  rows — first via runbook SQL, later via a scheduled SQL exporter.
- **Stage 2 is bound to a named milestone.** The production deployment plan
  owns installing the platform stack.
- **Stage 3 surfaces (metrics endpoint, OTLP, tracing) arrive only on
  demonstrated need**, additively.

## Anti-Patterns to Avoid

- **Homegrown collection/aggregation pipeline.** The named failure mode this
  pattern exists to prevent. Stdout and SQL are the only boundaries the
  application owns.
- **Introducing the first telemetry stack inside a feature milestone.** A
  data-plane change is the wrong place to select a telemetry product.
- **A scrape endpoint with no scraper.** An app-side `/metrics` surface before
  any collector is deployed to read it is dead code with a dependency cost.
- **Vague deferral** ("metrics later, somewhere"). Unowned Stage 2 means the
  launch arrives without alerting.
- **An event-log broker (Kafka) for observability** at a scale the database
  rows and existing broker already cover.
- **Free-form log strings.** They can't become a contract, a dashboard, or an
  alert. Named events with typed fields can.

## Relationship to Other Patterns and Skills

- **`general-logging` (skill)** — defines the wide-event shape the Stage-1
  structured events use.
- **[worker pattern](../scalability/worker_pattern.md)** — the durable task
  rows (leases, attempts, outcomes) that pattern mandates for correctness are
  exactly the rows Stage 1 queries and Stage 2 exports as metrics.
- **[docs artifact layout](../documentation/docs_artifact_layout_pattern.md)**
  — the posture is recorded as a day-1 ADR in `docs/decisions/`; the Stage-1
  runbook queries live with the component runbooks.
- **`greenfield-project-setup` (skill)** — sequences this decision as a day-1
  ADR so no later plan has to re-derive the boundary.
