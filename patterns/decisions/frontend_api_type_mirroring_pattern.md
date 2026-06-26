---
name: frontend-api-type-mirroring-pattern
description: >-
  Use when a Vue/TypeScript frontend and a backend API are co-developed and the
  team must choose, from day 1, how to keep frontend types aligned with backend
  response shapes — symptoms include a drifted interface discovered at runtime as
  an `undefined` value or missing field, a reviewer flagging a large hand-written
  DTO with no compile-time guard, or a new endpoint that will expand the manually
  mirrored surface beyond what a single review can reliably catch.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.1"
---

# Frontend API Type Mirroring Pattern

## Purpose

When a Vue/TypeScript frontend calls a typed backend API, every response shape
must be expressed as a TypeScript type somewhere in the frontend codebase. The
question is: **who owns that type, and how does it stay aligned with the
backend?**

Answering this question explicitly — and recording the answer as an ADR — on
day 1 prevents a recurring class of integration bugs. A field added or renamed
in the backend silently compiles in the frontend; the symptom appears at runtime
as an `undefined` value, a missing render, or a broken UI path. Without a
deliberate strategy, teams drift into whichever approach is most convenient at
the moment, which produces an inconsistent codebase that is later expensive to
unify.

**The single idea worth repeating:** the API contract is the single source of
truth; the frontend mirrors it. Whether that mirror is maintained by hand or
generated automatically is a strategy choice, but the directionality is
not — the backend contract drives, the frontend follows.

## Options and Trade-offs

| Strategy | How it works | Strengths | Weaknesses |
|---|---|---|---|
| **Hand-written mirror** | A developer writes TypeScript `interface`s under `src/features/*/types/` that copy the backend response shape field-for-field. | Zero build infrastructure. Consistent with existing feature-type conventions. Easy to read and navigate. | No compile-time link to the backend. Drift is caught only by tests or human review. Does not scale with a growing API surface or team. |
| **Codegen from OpenAPI spec** | A tool (`openapi-typescript`, `orval`) reads the backend's OpenAPI definition and emits TypeScript types, checked into the frontend or generated at build time. | Drift is structurally impossible: a Rust DTO change fails the generator or produces a type error in the consuming code. Scales to large API surfaces and independent teams. | Requires build infrastructure (a maintained OpenAPI spec, a generator wired into CI). Introduces a generated-vs-hand-written split if adopted incrementally. |
| **Serialize-and-snapshot drift guard** | A test serializes the backend response and compares it to a committed snapshot; a mismatch fails CI. | Lower infrastructure cost than full codegen; provides a CI break on drift. | Still no compile-time check; the snapshot must be updated manually on every intentional change. A lighter step toward codegen, not a permanent alternative. |

### When each option is appropriate

**Hand-written mirror** is acceptable when:
- the frontend and backend ship in the same release (no independent deployment
  window where stale types can survive in production);
- a single developer or a very small team reviews every API change alongside
  its frontend mirror in the same pull request;
- each feature owns a small, focused type file with limited fan-out; and
- the codebase is already uniformly hand-written and inconsistency would
  outweigh the guard.

**Codegen** becomes necessary when any of these conditions changes:
- the API surface grows beyond what one reviewer can keep in sync by
  inspection;
- a second consumer depends on the same contract;
- the team grows or the packages deploy independently;
- a type-drift bug actually reaches a running environment.

**The serialize-and-snapshot guard** is a practical intermediate step: lower
cost than full codegen, higher safety than pure hand-writing. It is a valid
choice if the revisit triggers above are approaching but full codegen is not
yet warranted.

## Why Day 1 Matters

Choosing late has compounding costs:

1. **Inconsistency is a decision.** A codebase that is half hand-written and
   half generated is harder to work in than either approach uniformly applied.
   Adopting codegen for one endpoint creates a generated island in a hand-written
   codebase; the inconsistency is a cost that must be weighed explicitly.

2. **The migration is repo-wide.** When the team eventually moves to codegen, it
   is not a per-feature change — it requires selecting a generator, driving it
   from the OpenAPI spec, wiring it into the build and CI, and migrating every
   existing hand-written type directory. Starting that work piecemeal inside a
   single feature plan defeats the consistency that justified staying manual.

3. **The OpenAPI spec must stay accurate for codegen to be possible.** If
   the spec drifts from the implementation during the hand-written phase, the
   future migration has no accurate source. Keeping the spec updated alongside
   every backend API change — even when no generator consumes it — is the
   investment that makes the future migration viable.

## Worked Example — ironbox

ironbox follows the **hand-written mirror** strategy.

### The mechanism

The Rust backend uses `utoipa` with `#[derive(Serialize, ToSchema)]` on every
response type. This produces an OpenAPI spec (`core/src/infrastructure/api/openapi.rs`)
that is the human-readable contract of record. The backend model file for each
endpoint carries a comment naming the frontend file it mirrors:

```rust
// core/src/infrastructure/api/workspace_overview/model.rs
//
// Wire DTOs for the workspace-overview API surface.
// The overview response and the browser-facing SSE event bodies, snake_case
// (the frontend mirrors these field-for-field).

#[derive(Serialize, ToSchema)]
pub struct WorkspaceOverviewResponse {
    pub connections_count: u64,
    pub sources_count: u64,
    pub storage_vaults_count: u64,
    pub schedules_count: u64,
    pub backups_count: u64,
    pub restores_count: u64,
    pub jobs_count: u64,
    pub latest_backup: Option<LatestBackup>,
    pub latest_restore: Option<LatestRestore>,
    pub recent_jobs: Vec<JobResponse>,
    pub connectivity_health_available: bool,
    pub connectivity_subjects: Vec<ConnectivitySubject>,
}
```

The TypeScript mirror lives under `web/src/features/workspaces/types/workspaceOverview.ts`
and explicitly names the Rust file it tracks:

```typescript
// web/src/features/workspaces/types/workspaceOverview.ts
// Wire types — snake_case, mirrors core/src/infrastructure/api/workspace_overview/model.rs

export interface WorkspaceOverviewResponse {
  connections_count: number;
  sources_count: number;
  storage_vaults_count: number;
  schedules_count: number;
  backups_count: number;
  restores_count: number;
  jobs_count: number;
  latest_backup: LatestBackupResponse | null;
  latest_restore: LatestRestoreResponse | null;
  recent_jobs: WorkspaceOverviewRecentJob[];
  connectivity_health_available: boolean;
  connectivity_subjects: ConnectivitySubjectResponse[];
}
```

Fields are snake_case on the wire, matching the Rust serialization convention
and the field names in the TypeScript interface exactly. There is no
transformation layer between what the backend serializes and what the frontend
types declare.

### How drift is mitigated without codegen

Three constraints hold the risk to an acceptable level:

- **Co-release.** `.github/workflows/release.yml` builds and publishes `core`
  and `web` in the same workflow. A backend field change and its frontend mirror
  live in the same pull request and the same release; there is no window in
  which a new backend field is live against an old frontend in production.
- **Single-PR review.** One developer owns both packages. The reviewer who
  approves a contract change sees the TypeScript mirror in the same diff.
- **Feature tests cover rendering.** A drifted field that the UI actually
  renders will break the feature's component, composable, or end-to-end tests.
  The unguarded case is a drifted field that nothing renders — which is harmless
  rather than silently broken.

### The SSE carve-out

Server-sent-event streams (the jobs stream, the M7 connectivity overview stream)
are not modeled by standard OpenAPI generators. These remain hand-written client
handlers with matching server-side event constants regardless of whether the
REST contracts migrate to codegen. The `CONNECTIVITY_DEGRADED_EVENT`,
`CONNECTIVITY_RECOVERED_EVENT`, and `CONNECTIVITY_RESYNC_EVENT` string constants
defined in `model.rs` are documented and mirrored by hand in
`web/src/constants/connectivity.ts`. This is a permanent carve-out, not a
temporary one.

### Revisit triggers

Move to codegen when any of these conditions hold:
- the shared/API type surface grows beyond what a single reviewer can keep in
  sync by inspection;
- a contract gains a second independent consumer;
- the team grows beyond a single developer, or `core` and `web` begin to deploy
  independently;
- a type-drift bug actually reaches a running environment.

When these triggers fire, the migration is a **repo-wide initiative**: pick a
generator, drive it from the OpenAPI spec, wire it into CI, and migrate all
existing `src/features/*/types/` directories in one pass.

## Quick Reference — Invariants

- **The API contract is the single source of truth.** The frontend mirrors it;
  it does not define it.
- **Field names on the wire match field names in the TypeScript interface.**
  No silent camelCase/snake_case transformation that can mask a missed update.
- **Every mirrored type file names the backend file it tracks** (comment or
  explicit reference), so a reviewer knows where to look when the backend
  changes.
- **The OpenAPI spec stays accurate** alongside every backend API change, even
  when no generator consumes it — it is the source a future migration will use.
- **The migration to codegen is repo-wide**, not per-feature. Starting it
  piecemeal inside a feature plan creates inconsistency that defeats the
  rationale for staying manual.
- **SSE stream event types stay hand-written** regardless of the REST strategy:
  OpenAPI generators do not model `text/event-stream` bodies.

## Anti-Patterns to Avoid

- **Editing generated files by hand.** Once codegen is in place, hand-editing
  the output is the same class of error as not using codegen at all. Generated
  files are read-only; corrections go in the source spec or the generator
  configuration.
- **Adopting codegen for one endpoint only.** A single generated island in a
  hand-written codebase is harder to reason about than either approach uniformly.
  If codegen is adopted, migrate the full surface.
- **Leaving the OpenAPI spec stale.** A spec that lags the implementation is
  useless as a future codegen source and misleading as a human-readable contract.
  The spec is a first-class artifact — keep it updated with every backend API
  change.
- **Assuming co-release always holds.** The hand-written mirror strategy is
  explicitly conditional on co-release and a small team. Document the
  assumptions in the ADR so they are visible when they change.
- **Adding field-name transformations in the HTTP client.** A camelCase
  conversion layer between the wire format and the TypeScript type hides mismatches
  that a field-for-field comparison would catch.

## Relationship to Other Skills and Patterns

- **[docs_artifact_layout_pattern](../documentation/docs_artifact_layout_pattern.md)** —
  describes where this ADR lives (`docs/decisions/`) and the layout conventions
  for recording this decision at the time it is made.
- **`rest-api-design` / `syneto-rest-api-design`** — defines the REST API
  contract that the frontend is mirroring. The contract is the source; this
  pattern governs how the frontend tracks it.
- **`frontend-vue-development`** — the feature-based architecture
  (`src/features/*/types/`) is where hand-written wire types live; this pattern
  integrates with that layout.
- **`frontend-vue-code-style`** — wire types follow the same interface and
  naming conventions as the rest of the frontend type system; this pattern does
  not introduce exceptions.
