---
name: local-port-allocation-pattern
description: >-
  Use when starting a new project that will run multiple local services
  (API, worker, database, broker, object store, mail emulator, frontend
  dev server) and any of these symptoms are present or anticipated: port
  collisions block parallel worktree checkouts, parallel integration-test
  runs stomp on each other's fixture ports, developers fight over
  conventionally-numbered ports (5432, 8000, 3306) that other local
  projects also claim, or ad-hoc conflict-avoidance ports have accumulated
  with no central registry. Produces an ADR that locks down a
  non-overlapping host-port range for the project before the first port
  number is hardcoded anywhere.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.1"
---

# Local Port Allocation Pattern

## Purpose

Every project that runs more than one local service will eventually collide
on ports with other projects on the same machine — or with parallel
worktrees of itself. The collision usually surfaces as a cryptic
`address already in use` error at the worst possible time: mid-CI run,
mid-pairing session, or the moment a parallel worktree checkout is needed
for a hotfix.

**In one line:** allocate one non-overlapping host-port range per project
from day one, subdivide it into per-service bands, record the allocation
as an ADR in `docs/decisions/`, and then never hardcode a port number
outside that ADR and the environment template it seeds.

This is a **day-1 decision**. Every port number that is hardcoded before
the allocation exists has to be hunted down and migrated later. The
migration is mechanical but tedious; the decision costs nothing upfront.

## The Problem

### Why conventional ports break parallel work

Services started with conventional ports (`5432` for PostgreSQL, `8000`
for an API, `5173` for Vite) assume they are the only occupant of that
port on the machine. That assumption holds on a single developer machine
running exactly one project at a time. It breaks in every other scenario:

- **Parallel worktrees.** When an agent or developer runs a second
  worktree — a common pattern for hotfixes or parallel feature work — both
  worktrees try to start their fixture containers on the same host port.
  The second one fails, immediately or silently.
- **Parallel integration tests.** Test suites that spin up fixture
  containers (databases, brokers, mail emulators) in parallel runs will
  stomp on each other unless each run gets its own ports.
- **Multiple local projects.** A PostgreSQL on `5432` started for project
  A blocks project B from starting its own PostgreSQL on the same port.
  The developer must remember to stop one before starting the other.

The conventional response is ad-hoc: raise one conflicting port, note the
change nowhere, repeat when the next collision appears. The result is a
slow drift of unrelated port decisions with no central registry and no
rationale.

### The decision that fixes it

Allocate a dedicated, project-unique host-port range from a registry
(informal or org-wide), subdivide it into per-service-category bands,
and record the full table in an ADR. From that point forward:

- Every local host-port mapping comes from the ADR table.
- Container-internal ports stay conventional (they are invisible to the
  host and are part of service-to-service contracts inside an isolated
  network).
- Environment templates read from the ADR table; application code reads
  from environment templates — no hardcoded numbers in source.

## Separation of Concerns

> **Core principle:** the ADR owns the numbers; the environment template
> owns the surface exposed to application code; application code owns
> none of them.

Three responsibilities, three places. The ADR is the authoritative
registry. The environment template (`.env.template`, `.env.example`, or
equivalent) is the machine-readable projection of the ADR. Application
and test code read configured endpoints; they never embed port literals.

## Worked Example: IronBox

IronBox allocates all local host-published ports from the inclusive range
`8700–8800`, recorded as an ADR under `docs/decisions/`.

### What is in scope for the range

- Host ports in local Docker Compose files
- Host ports in test-fixture Docker Compose files
- Local development server ports
- Local `.env.template` endpoint ports used by tests and development
- Documentation that tells developers which local host ports to use

### What is explicitly out of scope

- Production Kubernetes Service or container ports
- Docker container-internal ports
- Third-party protocol defaults when connecting to real external systems

Container-internal ports stay conventional: the core API container still
listens on `8000` internally; PostgreSQL containers still listen on `5432`
internally. Only the host side of local port mappings moves into the
allocated range.

### The band subdivision

The range is divided into per-category bands so that adding a new service
requires only consulting the relevant band, not scanning the whole table:

| Range | Category |
|---|---|
| `8700–8709` | Application runtimes (API, worker, frontend dev server) |
| `8710–8739` | Database fixtures |
| `8740–8759` | Object store, mail emulator, and external API emulators |
| `8760–8779` | SSH and remote-machine fixtures |
| `8780–8800` | Message-broker fixtures and future local services |

### The per-port allocation table

| Port | Local service |
|---|---|
| `8700` | Core API — direct development |
| `8701` | Core API — local deployment host mapping |
| `8702` | Web Vite dev server |
| `8703` | Web Nginx — local deployment host mapping |
| `8704` | Core gRPC worker control plane |
| `8710` | PostgreSQL — IronBox development database |
| `8711` | PostgreSQL — backup-target fixture |
| `8712` | PostgreSQL 17 — backup-target fixture (when enabled) |
| `8713` | PostgreSQL — local-deployment database |
| `8720` | MySQL 8 — backup-target fixture |
| `8721` | MySQL 5.7 legacy — backup-target fixture |
| `8730` | MongoDB — backup-target fixture |
| `8740` | MinIO API fixture |
| `8741` | Mailpit SMTP fixture |
| `8742` | Mailpit UI/API fixture |
| `8743` | fake-gcs-server fixture |
| `8744` | Azurite blob emulator fixture |
| `8760` | SSH source-machine fixture |
| `8761` | SSH storage-vault-machine fixture |
| `8762` | SSH Windows storage-vault-machine fixture |
| `8780` | RabbitMQ AMQP fixture |
| `8781` | RabbitMQ management UI/API fixture |

### Why this enables parallel worktree agents

With all host ports confined to `8700–8800`, a second worktree of the
same project can start its own fixture stack on a different sub-range (or
with a configurable offset applied uniformly via the environment template)
without touching the first worktree's ports. Parallel integration-test
runs gain the same isolation: each run's fixture containers bind to a
pre-allocated slice of the range that no other run touches.

## How to Record the Decision (ADR)

Place the ADR under `docs/decisions/` per the
docs-artifact-layout-pattern. Use a sequentially numbered file name such
as `02-local-port-allocation.md`. The ADR must contain at minimum:

1. **Status** — Accepted.
2. **Context** — what services the project runs locally and why
   conventional ports cause collisions.
3. **Decision** — the chosen inclusive range and what it applies to (host
   ports only; not container-internal ports; not production).
4. **Allocation policy** — the band subdivision table and the per-port
   allocation table. State explicitly that new ports require updating this
   ADR before being introduced anywhere else.
5. **Consequences** — local setup is less likely to collide with other
   projects; developers must not infer production ports from local host
   ports; code that needs local fixture endpoints must read from
   `.env`/`.env.template`, not from hardcoded port literals.

A lightweight follow-up enforcement step is a CI check that verifies Docker Compose host mappings,
`.env.template` endpoints, development-server defaults, and documentation
all stay aligned with the ADR's table. This check is optional at day one
but prevents the table from drifting.

## Quick Reference — Invariants

- **Allocate before the first port is used.** Every port number committed
  outside the ADR and environment template is a migration debt.
- **One range per project, non-overlapping with other local projects.**
  The range must not conflict with ranges allocated to other projects that
  run on the same developer machines.
- **Subdivide into bands.** Bands limit the scan needed when adding a new
  service to one category row, not the whole table.
- **Container-internal ports stay conventional.** The range applies only
  to host-side port mappings in local and test-fixture Compose files. Do
  not change container-internal ports; they are part of service-to-service
  contracts.
- **Environment template is the authoritative machine-readable surface.**
  Application code, test code, and development tooling read configured
  endpoints; they never embed port literals from the ADR table directly.
- **New ports require updating the ADR first.** Reserve the port in the
  ADR, then update Compose files, environment templates, and code. Never
  in the other order.
- **Production ports are independent.** The local allocation is
  intentionally different from production. Local host ports must not be
  used to infer production ports.

## Anti-Patterns to Avoid

- **Using conventional ports without an allocation ADR.** `5432`, `8000`,
  `3306`, `5173` and similar defaults are almost certainly already
  occupied on any active developer machine. Using them without a
  reservation guarantees eventual collision.
- **Ad-hoc conflict resolution.** Changing one port when a conflict
  appears, without recording the change in a central table, produces an
  unmaintainable scatter of arbitrary numbers with no rationale and no
  way to check for future conflicts.
- **Hardcoding port numbers in application or test code.** Source code
  that contains literal port numbers must be updated every time a port
  moves. Read configured endpoints from the environment template instead.
- **Applying the range to container-internal ports.** The range is for
  host-side mappings only. Renaming a PostgreSQL container's internal
  listener from `5432` to `8710` breaks every standard tooling expectation
  inside that container's network.
- **Silently reusing a band for an unrelated service.** If the database
  band (`8710–8739`) is used for a new message broker because it has free
  numbers, the band semantic is lost and future readers cannot rely on band
  membership to understand what a port does.
- **Skipping the ADR and going straight to env templates.** The env
  template is the machine-readable surface; the ADR is the rationale,
  scope, and update policy. Without the ADR, the env template has no
  owner, no change policy, and no record of what is excluded (production
  ports, container-internal ports).

## Relationship to Other Patterns

- **[parallel test isolation pattern](../testing/parallel_test_isolation_pattern.md)**
  — port allocation is the foundation
  for parallel test isolation: each parallel test run gets its own slice
  of the allocated range, or a configured offset, so fixture containers
  never overlap. The two patterns are complementary; implement port
  allocation first.
- **docs-artifact-layout-pattern** — ADRs live under `docs/decisions/`
  per that pattern. The allocation ADR is exactly the kind of architectural
  decision that pattern governs: a day-1 structural choice with
  long-lasting consequences recorded where future contributors will look
  for it.
