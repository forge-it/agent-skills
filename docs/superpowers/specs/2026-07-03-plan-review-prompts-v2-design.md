# Plan-Review Prompt Collection v2 — Design

Date: 2026-07-03
Status: approved

## Goals

1. Decouple the combined stack-based plan-review prompts (`rust-vue`, `python-vue`) into single-language prompts so each prompt reviews exactly one concern: one backend language, the frontend, or the API seam between them.
2. Make the subagent orchestrator prompts more powerful: stack-composed panels, a synthesis + dedup stage, an adversarial verification stage, and new single-concern reviewer lenses.

## Decisions (user-approved)

- The seam (API contract) becomes a dedicated prompt, not folded into the language prompts.
- Each language gets exactly two variants: one mild (systematic) and one aggressive.
- All four orchestrator upgrades are in scope: composition from single-language prompts, synthesis + dedup, adversarial verification, and new lenses.
- New lenses live in a new `lenses/` folder, keeping `generic/` single-purpose (motivational framings).
- Orchestrators are one pipeline file per stack with deletable stages, not separate tier files.
- Full-stack deep panel size is 8 reviewers; rust and python panels are 6; vue is 5 (no seam, no operational-readiness — its migration/rollback emphasis is backend work).
- `stack-based/` and the four current orchestrators are deleted after the split (git history preserves them).
- The seam prompt is aggressive-only: one concern, one strong variant.

## Target file tree

```
prompts/plan-review/
├── single-language/                        # replaces stack-based/ (deleted)
│   ├── plan-review-rust.md                 # mild = systematic
│   ├── plan-review-rust-aggressive.md
│   ├── plan-review-python.md
│   ├── plan-review-python-aggressive.md
│   ├── plan-review-vue.md
│   ├── plan-review-vue-aggressive.md
│   └── plan-review-api-seam.md             # <BACKEND> placeholder: Rust or Python
├── generic/                                # unchanged content, typo fixes only
│   ├── plan-review-day-off-bet.md
│   ├── plan-review-loss-framing.md
│   └── plan-review-money-bet.md
├── lenses/                                 # new: concern-scoped, language-agnostic
│   ├── plan-review-security.md
│   ├── plan-review-tests-and-migrations.md
│   └── plan-review-operational-readiness.md
└── subagents/                              # replaces the current 4 orchestrators
    ├── pipeline-rust-vue.md
    ├── pipeline-python-vue.md
    ├── pipeline-rust.md
    ├── pipeline-python.md
    └── pipeline-vue.md
```

## Single-language prompts — shared contract

Every prompt in `single-language/` follows the same skeleton so panels are interchangeable:

- **Header:** review plan `<X>` against the current codebase, write findings to `<Y>`. The `<X>`/`<Y>` placeholder convention is unchanged (established across all prompt folders in this repo).
- **Grounding rules:** read the plan in full before starting; verify every file path, module reference, and import the plan cites; read the project's own structure doc if present (`project_structure.md`, `CLAUDE.md`). This replaces the hardcoded `core/docs/guidelines/project_structure.md` path so prompts work in any repository.
- **Quality mechanisms present in BOTH variants** (they are what make reviews good; not reserved for aggressive): no hedging; no vague findings ("consider refactoring" is not a finding); quote the plan when challenging it; cite `file:line` when justifying a finding; group findings Blocking / Important / Nit; end with a one-line verdict (ship as-is / ship after Blocking fixed / rework); no preamble.
- **Mild vs. aggressive differ only in framing and pass structure:**
  - Mild = neutral systematic reviewer, single thorough pass over the full checklist.
  - Aggressive = the bet framing ("I bet you cannot find every meaningful issue. Prove me wrong."), minimum three passes from different angles, and "if you find nothing wrong, you missed things — run another pass."

### Per-language coverage

- **Rust** (`plan-review-rust.md`, `-aggressive.md`): hexagonal layering (domain/application/infrastructure, dependencies pointing inward); ports taking infrastructure types (sqlx rows, reqwest responses) instead of domain types; use cases reaching for IO directly; error enums mixing transport/persistence/domain concerns; module placement; async/blocking boundaries; `.unwrap()` and panics in request paths; Rust idioms. Aggressive passes: (1) architecture, (2) errors/async/idioms, (3) silence-hunting (tests, migrations, rollback, observability).
- **Python** (`plan-review-python.md`, `-aggressive.md`): DDD + hexagonal layering; pure-dataclass domain models (no ORM/Pydantic/framework leakage); classical (imperative) SQLAlchemy mapping, never declarative `Base` subclasses as the domain; repositories defined as ports in the domain, returning aggregates (not ORM rows/`Result`/dicts); explicit Unit of Work with explicit commit; async boundaries (blocking IO in `async def`, sync ORM in async handlers, missing `await`); Python idioms (mutable defaults, broad `except Exception`, `print` vs structured logging, missing type hints, single-letter names). Same three-pass shape for aggressive.
- **Vue** (`plan-review-vue.md`, `-aggressive.md`): separation of concerns across components/composables/stores (fetching + mutation + business logic + rendering in one file); composables with more than one responsibility or that should be stores; stores holding component-local state and the inverse; prop drilling, event re-emission chains, parents reaching into child internals; reactivity pitfalls (destructuring, `ref` vs `reactive`, computed vs watcher); types defined twice; loading/empty/failure states for every endpoint the plan touches; a11y/i18n silence. UX states move here from the seam (they are Vue-side work); the seam still checks the contract that feeds them.

## The seam prompt

`plan-review-api-seam.md` owns the wire and nothing else:

- Contract drift: response shapes the plan assumes vs. what the backend handler actually returns — cited on both sides.
- Type generation: if TypeScript types are generated from the backend schema, is the generation step in the plan? If types are hand-maintained on both sides, flag that as the root cause.
- Error contract: backend error → HTTP status → Vue-visible message. Silence is a finding.
- Auth and permission edges: which endpoints the plan touches, which roles can hit them, what the Vue side does when forbidden.
- Pagination, sorting, filtering wired end-to-end; query parameter names match exactly.
- Serialization edges: datetime timezone, decimal precision, enum string-vs-int, null vs missing field.

One `<BACKEND>` placeholder (`Rust` or `Python`) tunes the backend-specific instructions (e.g., check Pydantic response models vs. serde structs).

## Lenses

Three language-agnostic single-concern reviewers in `lenses/`, same skeleton and output contract as the single-language prompts:

- **security:** authn/authz gaps on touched endpoints, input validation, injection surfaces, secrets handling, tenancy/data-exposure edges the plan is silent on.
- **tests-and-migrations:** does the plan say what proves each change (unit/integration/contract); migration ordering and downgrade path; deploy-order coupling; backfill safety.
- **operational-readiness:** rollback story, feature flags, observability (structured logs, metrics on new paths), failure modes of new external calls, idempotency/retry.

## Orchestrator pipelines

Each `pipeline-<stack>.md` is one file with three stages. The header states: run Stage 1 only for a quick pass, Stages 1–2 for a consolidated report, all three for a verified report — delete what you don't want before pasting.

### Stage 1 — Panel (parallel, verbatim dispatch)

Keeps every load-bearing rule from the current orchestrators:

- All agents dispatched in a single message — parallel, not sequential.
- Each agent receives only: the plan path `<X>`, its output path `<Y>-plan-review-NN.md`, and its prompt file contents — verbatim, no paraphrasing, no conversation summary, no hints.
- The orchestrator never reads, merges, or edits the reviews.
- If a listed prompt does not fit the project's stack, swap it and tell the user which one and why.

Panels:

| Pipeline | Panel |
|---|---|
| rust-vue (8) | rust-aggressive, vue-aggressive, api-seam (BACKEND=Rust), day-off-bet, loss-framing, security, tests-and-migrations, operational-readiness |
| python-vue (8) | python-aggressive, vue-aggressive, api-seam (BACKEND=Python), day-off-bet, loss-framing, security, tests-and-migrations, operational-readiness |
| rust (6) | rust-aggressive, rust-mild, day-off-bet, security, tests-and-migrations, operational-readiness |
| python (6) | python-aggressive, python-mild, day-off-bet, security, tests-and-migrations, operational-readiness |
| vue (5) | vue-aggressive, vue-mild, day-off-bet, security, tests-and-migrations |

Review files are numbered `<Y>-plan-review-NN.md` with NN = 01..N matching panel order.

Mild variants earn their keep in the single-language pipelines, where the panel is smaller and framing diversity matters more.

### Stage 2 — Synthesis (one fresh subagent)

A fresh subagent (not the orchestrator) reads the N review files and writes `<Y>-plan-review-synthesis.md`:

- Findings deduped across reviewers.
- Each finding tagged `found-by: k/N reviewers`.
- Disagreements kept visible as disagreements, never silently resolved.
- Ranked by severity, then corroboration count.
- Raw review files remain on disk.

### Stage 3 — Adversarial verification (parallel skeptics)

- The orchestrator reads the synthesis file — and only the synthesis file, only to enumerate Blocking/Important findings for dispatch; the "never reads reviews" rule applies to the Stage 1 raw reviews.
- For each Blocking/Important finding in the synthesis, one skeptic subagent is dispatched whose prompt is to refute the finding against the codebase, defaulting to refuted when uncertain.
- Verdicts fold into `<Y>-plan-review-verified.md`: findings marked CONFIRMED (with the skeptic's evidence) or REFUTED (with why).
- Nits skip verification — not worth the tokens.

## Housekeeping (synced in the same change)

- `aggresive` → `aggressive` in every filename and every reference to those filenames.
- `aseverity` → `severity` in `generic/plan-review-money-bet.md`.
- Old `stack-based/` files and the four current orchestrators deleted; every path reference inside `subagents/` updated in the same commit (rule-number-sync lesson applied to file paths).

## Out of scope (future passes)

- `plan-write/`, `code-implementation-review/`, and `implement-code/` still contain stack-coupled prompts; the same decoupling pattern can be applied there later.
- Additional lenses beyond the three above.
