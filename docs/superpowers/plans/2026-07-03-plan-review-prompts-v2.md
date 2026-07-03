# Plan-Review Prompt Collection v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decouple the combined stack-based plan-review prompts into single-language prompts plus a dedicated API-seam prompt and three concern lenses, and rebuild the subagent orchestrators as staged pipelines (panel → synthesis → adversarial verification).

**Architecture:** Every reviewer prompt is a standalone markdown file with one concern and a shared output contract, so pipeline panels can compose them interchangeably. Orchestration lives in five `pipeline-<stack>.md` files, each a three-stage script with deletable stages. Spec: `docs/superpowers/specs/2026-07-03-plan-review-prompts-v2-design.md`.

**Tech Stack:** Markdown prompt files only. Verification is `ls`/`grep`. No code, no tests to run.

## Global Constraints

- Placeholders: `<X>` = plan path, `<Y>` = output path prefix, `<BACKEND>` = `Rust` or `Python` (seam prompt only), `<agent-skills>` = this repo's root (pipelines only). Placeholder fill-in lines sit at the bottom of every file, one per line, as `<X> = ` etc.
- Filename spelling is `aggressive` — never `aggresive`.
- Shared output contract in every reviewer prompt: findings grouped Blocking / Important / Nit; each finding = (1) issue in one sentence, (2) exact location in the plan, (3) codebase citation, (4) concrete fix; one-line verdict (`ship as-is` / `ship after Blocking fixed` / `rework before implementation`); no preamble.
- Shared quality bar in every reviewer prompt: no vague feedback, no hedging, quote the plan when challenging it, cite `file:line` when justifying a finding.
- Single-language and lens prompts carry a scope guard: out-of-scope observations go into a one-line "Out of scope" list, never investigated.
- Structure-doc rule is repo-agnostic: "if the project has a structure document (`project_structure.md`, `CLAUDE.md`, or `docs/guidelines/`), read it first" — never a hardcoded path.
- Every file deletion or rename is synced into every file that references the old path, in the same commit.
- Commit message style: `chore: <description>` (matches repo history), ending with the Claude co-author line.

---

### Task 1: Rust single-language prompts

**Files:**
- Create: `prompts/plan-review/single-language/plan-review-rust.md`
- Create: `prompts/plan-review/single-language/plan-review-rust-aggressive.md`

**Interfaces:**
- Produces: the two Rust panel members referenced by path in Task 6's pipelines.

- [ ] **Step 1: Write `plan-review-rust.md` (mild = systematic)** with exactly this content:

```markdown
Your task is to review the Rust side of plan <X> against the current codebase and write your findings to <Y>.

Scope: you are the Rust reviewer. Judge only the Rust backend concerns of the plan. If you notice issues outside that scope (frontend, API contract, tooling), record each as a one-line note in an "Out of scope" list at the end — do not investigate them.

Rules:
- Read the plan in full before you start. Then check every claim against the actual state of the codebase. No skimming, no trusting the plan's own description of the code.
- Verify every Rust file path, module reference, and import the plan mentions. If it no longer exists, was renamed, or moved, flag it.
- If the project has a structure document (project_structure.md, CLAUDE.md, or docs/guidelines/), read it first and flag anything the plan places in the wrong layer or folder.

Work through the full checklist:

Hexagonal architecture:
- Domain leaking into adapters, or adapters leaking into domain. Cite the file.
- Ports that take infrastructure types (sqlx rows, reqwest responses, HTTP bodies) instead of domain types.
- Use cases that reach for IO directly instead of going through a port.
- Module placement: business logic in `api/`, framework code in `domain/`, anything in `infrastructure/` that should not know about HTTP.
- Dependencies pointing the wrong way: anything in `domain/` importing from `application/` or `infrastructure/`.

Errors, async, and idioms:
- Error types that mix transport, persistence, and domain concerns in one enum.
- `.unwrap()` / `.expect()` on operations that can fail at runtime; panics in request paths.
- Blocking calls inside async contexts; spawned work without cancellation or error propagation.
- Invariants enforced by comments or convention that the type system could enforce instead.

Silence — what the plan does not say:
- Tests: which behaviors get unit tests, which get integration tests. A plan silent on proof is a finding.
- Migrations: ordering, downgrade path, deploy-order coupling between schema and code.
- Unstated assumptions about concurrency, ordering, idempotency, cache invalidation, feature flags.
- Rollback and observability for every new code path. Silence is a finding when it should not be silent.

Cross-cutting:
- Separation-of-concerns violations: any file, struct, or function that mixes responsibilities. This is the most important check.
- Single-responsibility violations: anything doing more than one thing. Tied for most important.
- Architectural weak decisions: leaky abstractions, tight coupling, missing seams between layers, shortcuts that mortgage future work.
- Ambiguities: every place an implementer would have to guess what the author meant. Guesses become bugs.
- Missing pieces, internal contradictions, and scope that should be cut.

Quality bar:
- No vague feedback. "Consider refactoring" is not a finding. "Extract X from path/to/file.rs:42 into its own module because it mixes concern A with concern B" is a finding.
- No hedging. Drop "might," "could," "perhaps," "you may want to." If you cannot verify something, say so directly — that is honest.
- Quote the plan when you challenge it. Cite file:line when you justify a finding. A finding without a citation is an opinion.
- If an area of the plan is genuinely sound, say so in one line and move on. Do not manufacture findings.

Output format in <Y>:
- Group findings by severity: Blocking, Important, Nit.
- Each finding states: (1) the issue in one sentence, (2) the exact location in the plan, (3) the codebase citation that proves the issue, (4) the concrete fix.
- After the findings, list any "Out of scope" one-liners.
- End with a one-line verdict: ship as-is, ship after Blocking fixed, or rework before implementation.
- No preamble. Get to the findings.

<X> = 
<Y> = 
```

- [ ] **Step 2: Write `plan-review-rust-aggressive.md`** with exactly this content:

```markdown
Your task is to tear the Rust side of plan <X> apart against the current codebase and write your findings to <Y>.

You are the Rust reviewer. Most reviewers skim, trust the plan's description of the code, and hedge. You will not.

I bet you cannot find every meaningful issue on the Rust side of this plan. Prove me wrong. Hunt from angles the plan did not anticipate.

Scope: judge only the Rust backend concerns of the plan. If you notice issues outside that scope (frontend, API contract, tooling), record each as a one-line note in an "Out of scope" list at the end — do not investigate them.

Rules:
- Read the plan in full before you start. Then check every claim against the actual state of the codebase. No skimming, no trusting the plan's own description of the code.
- Verify every Rust file path, module reference, and import the plan mentions. If it no longer exists, was renamed, or moved, flag it.
- If the project has a structure document (project_structure.md, CLAUDE.md, or docs/guidelines/), read it first and flag anything the plan places in the wrong layer or folder.

Do at least three review passes, each from a different angle. Do not stop after one.

Pass 1 — hexagonal architecture:
- Domain leaking into adapters, or adapters leaking into domain. Cite the file.
- Ports that take infrastructure types (sqlx rows, reqwest responses, HTTP bodies) instead of domain types.
- Use cases that reach for IO directly instead of going through a port.
- Module placement: business logic in `api/`, framework code in `domain/`, anything in `infrastructure/` that should not know about HTTP.
- Dependencies pointing the wrong way: anything in `domain/` importing from `application/` or `infrastructure/`.

Pass 2 — errors, async, and idioms:
- Error types that mix transport, persistence, and domain concerns in one enum.
- `.unwrap()` / `.expect()` on operations that can fail at runtime; panics in request paths.
- Blocking calls inside async contexts; spawned work without cancellation or error propagation.
- Invariants enforced by comments or convention that the type system could enforce instead.

Pass 3 — silence hunt, what the plan does not say:
- Tests: which behaviors get unit tests, which get integration tests. A plan silent on proof is a finding.
- Migrations: ordering, downgrade path, deploy-order coupling between schema and code.
- Unstated assumptions about concurrency, ordering, idempotency, cache invalidation, feature flags.
- Rollback and observability for every new code path. Silence is a finding when it should not be silent.

Across all passes:
- Flag separation-of-concerns violations: any file, struct, or function that mixes responsibilities. This is the most important check.
- Flag single-responsibility violations: anything doing more than one thing. Tied for most important.
- Flag architectural weak decisions: leaky abstractions, tight coupling, missing seams between layers, shortcuts that mortgage future work.
- Identify ambiguities: every place an implementer would have to guess what the author meant. Guesses become bugs.
- Note missing pieces, internal contradictions, and scope that should be cut.

No vague feedback. "Consider refactoring" is not a finding. "Extract X from path/to/file.rs:42 into its own module because it mixes concern A with concern B" is a finding.

No hedging. Drop "might," "could," "perhaps," "you may want to." If you cannot verify something, say so directly — that is honest. Hedging while pretending to know is dishonest.

Quote the plan when you challenge it. Cite file:line when you justify a finding. A finding without a citation is an opinion.

If you find nothing wrong, you missed things. Plans are never perfect. Run another pass from a new angle.

Output format in <Y>:
- Group findings by severity: Blocking, Important, Nit.
- Within each group, tag each finding with the pass that produced it: architecture / errors-async-idioms / silence.
- Each finding states: (1) the issue in one sentence, (2) the exact location in the plan, (3) the codebase citation that proves the issue, (4) the concrete fix.
- After the findings, list any "Out of scope" one-liners.
- End with a one-line verdict: ship as-is, ship after Blocking fixed, or rework before implementation.
- No preamble. No "I reviewed the plan and…" Get to the findings.

<X> = 
<Y> = 
```

- [ ] **Step 3: Verify**

Run: `ls prompts/plan-review/single-language/ && grep -L "<X> = " prompts/plan-review/single-language/*.md`
Expected: both files listed; grep prints nothing (every file has the placeholder block).

- [ ] **Step 4: Commit**

```bash
git add prompts/plan-review/single-language/
git commit -m "chore: add single-language rust plan-review prompts"
```

---

### Task 2: Python single-language prompts

**Files:**
- Create: `prompts/plan-review/single-language/plan-review-python.md`
- Create: `prompts/plan-review/single-language/plan-review-python-aggressive.md`

**Interfaces:**
- Produces: the two Python panel members referenced by path in Task 6's pipelines.

- [ ] **Step 1: Write `plan-review-python.md` (mild = systematic)** with exactly this content:

```markdown
Your task is to review the Python side of plan <X> against the current codebase and write your findings to <Y>.

Scope: you are the Python reviewer. Judge only the Python backend concerns of the plan. If you notice issues outside that scope (frontend, API contract, tooling), record each as a one-line note in an "Out of scope" list at the end — do not investigate them.

Rules:
- Read the plan in full before you start. Then check every claim against the actual state of the codebase. No skimming, no trusting the plan's own description of the code.
- Verify every Python file path, module reference, and import the plan mentions. If it no longer exists, was renamed, or moved, flag it.
- If the project has a structure document (project_structure.md, CLAUDE.md, or docs/guidelines/), read it first and flag anything the plan places in the wrong layer or folder.

Work through the full checklist:

DDD + hexagonal architecture:
- Domain leaking into adapters, or adapters leaking into domain. Cite the file.
- Domain models that are not pure dataclasses: ORM-mapped classes used as the domain model, Pydantic models leaking past the API boundary, framework decorators on domain entities.
- Repositories not defined as ports in the domain, or returning ORM rows / SQLAlchemy `Result` objects / dict payloads instead of domain aggregates.
- Use cases / application services importing SQLAlchemy, httpx, FastAPI, or any other infrastructure directly instead of going through a port.
- Unit of Work missing, implicit, or not committed explicitly. Multiple repositories mutated without a single transaction boundary. Repositories created outside the UoW.
- SQLAlchemy mapping style: declarative `Base` subclasses used as the domain instead of classical (imperative) mapping onto pure dataclasses. Flag the file.
- Module placement: business logic in `api/` or routers, framework code in `domain/`, anything in `domain/` importing from `infrastructure/` or `api/`.

Errors, async, and idioms:
- Exception hierarchies that mix transport, persistence, and domain concerns. HTTP status codes baked into domain exceptions.
- Async boundaries: blocking IO inside `async def`, sync ORM calls in async handlers, missing `await`, `asyncio.run` inside request paths, thread-pool offloads not used where required.
- Python idioms: mutable default arguments, broad `except Exception`, `print` instead of structured logging, dict-as-record instead of dataclass, missing type hints on public functions, single-letter or abbreviated names.

Silence — what the plan does not say:
- Tests: unit, integration, contract — which behaviors get which proof. A plan silent on proof is a finding.
- Migrations: Alembic ordering, downgrade path, deploy-order coupling between schema and code.
- Unstated assumptions about concurrency, ordering, idempotency, transaction isolation, cache invalidation, feature flags.
- Rollback and observability for every new code path. Silence is a finding when it should not be silent.

Cross-cutting:
- Separation-of-concerns violations: any file, class, or function that mixes responsibilities. This is the most important check.
- Single-responsibility violations: anything doing more than one thing. Tied for most important.
- Architectural weak decisions: leaky abstractions, tight coupling, missing seams between layers, shortcuts that mortgage future work.
- Ambiguities: every place an implementer would have to guess what the author meant. Guesses become bugs.
- Missing pieces, internal contradictions, and scope that should be cut.

Quality bar:
- No vague feedback. "Consider refactoring" is not a finding. "Extract X from path/to/file.py:42 into its own module because it mixes concern A with concern B" is a finding.
- No hedging. Drop "might," "could," "perhaps," "you may want to." If you cannot verify something, say so directly — that is honest.
- Quote the plan when you challenge it. Cite file:line when you justify a finding. A finding without a citation is an opinion.
- If an area of the plan is genuinely sound, say so in one line and move on. Do not manufacture findings.

Output format in <Y>:
- Group findings by severity: Blocking, Important, Nit.
- Each finding states: (1) the issue in one sentence, (2) the exact location in the plan, (3) the codebase citation that proves the issue, (4) the concrete fix.
- After the findings, list any "Out of scope" one-liners.
- End with a one-line verdict: ship as-is, ship after Blocking fixed, or rework before implementation.
- No preamble. Get to the findings.

<X> = 
<Y> = 
```

- [ ] **Step 2: Write `plan-review-python-aggressive.md`** with exactly this content:

```markdown
Your task is to tear the Python side of plan <X> apart against the current codebase and write your findings to <Y>.

You are the Python reviewer. Most reviewers skim, trust the plan's description of the code, and hedge. You will not.

I bet you cannot find every meaningful issue on the Python side of this plan. Prove me wrong. Hunt from angles the plan did not anticipate.

Scope: judge only the Python backend concerns of the plan. If you notice issues outside that scope (frontend, API contract, tooling), record each as a one-line note in an "Out of scope" list at the end — do not investigate them.

Rules:
- Read the plan in full before you start. Then check every claim against the actual state of the codebase. No skimming, no trusting the plan's own description of the code.
- Verify every Python file path, module reference, and import the plan mentions. If it no longer exists, was renamed, or moved, flag it.
- If the project has a structure document (project_structure.md, CLAUDE.md, or docs/guidelines/), read it first and flag anything the plan places in the wrong layer or folder.

Do at least three review passes, each from a different angle. Do not stop after one.

Pass 1 — DDD + hexagonal architecture:
- Domain leaking into adapters, or adapters leaking into domain. Cite the file.
- Domain models that are not pure dataclasses: ORM-mapped classes used as the domain model, Pydantic models leaking past the API boundary, framework decorators on domain entities.
- Repositories not defined as ports in the domain, or returning ORM rows / SQLAlchemy `Result` objects / dict payloads instead of domain aggregates.
- Use cases / application services importing SQLAlchemy, httpx, FastAPI, or any other infrastructure directly instead of going through a port.
- Unit of Work missing, implicit, or not committed explicitly. Multiple repositories mutated without a single transaction boundary. Repositories created outside the UoW.
- SQLAlchemy mapping style: declarative `Base` subclasses used as the domain instead of classical (imperative) mapping onto pure dataclasses. Flag the file.
- Module placement: business logic in `api/` or routers, framework code in `domain/`, anything in `domain/` importing from `infrastructure/` or `api/`.

Pass 2 — errors, async, and idioms:
- Exception hierarchies that mix transport, persistence, and domain concerns. HTTP status codes baked into domain exceptions.
- Async boundaries: blocking IO inside `async def`, sync ORM calls in async handlers, missing `await`, `asyncio.run` inside request paths, thread-pool offloads not used where required.
- Python idioms: mutable default arguments, broad `except Exception`, `print` instead of structured logging, dict-as-record instead of dataclass, missing type hints on public functions, single-letter or abbreviated names.

Pass 3 — silence hunt, what the plan does not say:
- Tests: unit, integration, contract — which behaviors get which proof. A plan silent on proof is a finding.
- Migrations: Alembic ordering, downgrade path, deploy-order coupling between schema and code.
- Unstated assumptions about concurrency, ordering, idempotency, transaction isolation, cache invalidation, feature flags.
- Rollback and observability for every new code path. Silence is a finding when it should not be silent.

Across all passes:
- Flag separation-of-concerns violations: any file, class, or function that mixes responsibilities. This is the most important check.
- Flag single-responsibility violations: anything doing more than one thing. Tied for most important.
- Flag architectural weak decisions: leaky abstractions, tight coupling, missing seams between layers, shortcuts that mortgage future work.
- Identify ambiguities: every place an implementer would have to guess what the author meant. Guesses become bugs.
- Note missing pieces, internal contradictions, and scope that should be cut.

No vague feedback. "Consider refactoring" is not a finding. "Extract X from path/to/file.py:42 into its own module because it mixes concern A with concern B" is a finding.

No hedging. Drop "might," "could," "perhaps," "you may want to." If you cannot verify something, say so directly — that is honest. Hedging while pretending to know is dishonest.

Quote the plan when you challenge it. Cite file:line when you justify a finding. A finding without a citation is an opinion.

If you find nothing wrong, you missed things. Plans are never perfect. Run another pass from a new angle.

Output format in <Y>:
- Group findings by severity: Blocking, Important, Nit.
- Within each group, tag each finding with the pass that produced it: architecture / errors-async-idioms / silence.
- Each finding states: (1) the issue in one sentence, (2) the exact location in the plan, (3) the codebase citation that proves the issue, (4) the concrete fix.
- After the findings, list any "Out of scope" one-liners.
- End with a one-line verdict: ship as-is, ship after Blocking fixed, or rework before implementation.
- No preamble. No "I reviewed the plan and…" Get to the findings.

<X> = 
<Y> = 
```

- [ ] **Step 3: Verify**

Run: `grep -c "Unit of Work" prompts/plan-review/single-language/plan-review-python*.md`
Expected: `1` per file.

- [ ] **Step 4: Commit**

```bash
git add prompts/plan-review/single-language/
git commit -m "chore: add single-language python plan-review prompts"
```

---

### Task 3: Vue single-language prompts

**Files:**
- Create: `prompts/plan-review/single-language/plan-review-vue.md`
- Create: `prompts/plan-review/single-language/plan-review-vue-aggressive.md`

**Interfaces:**
- Produces: the two Vue panel members referenced by path in Task 6's pipelines.

- [ ] **Step 1: Write `plan-review-vue.md` (mild = systematic)** with exactly this content:

```markdown
Your task is to review the Vue side of plan <X> against the current codebase and write your findings to <Y>.

Scope: you are the Vue reviewer. Judge only the Vue 3 frontend concerns of the plan. If you notice issues outside that scope (backend, API contract, tooling), record each as a one-line note in an "Out of scope" list at the end — do not investigate them.

Rules:
- Read the plan in full before you start. Then check every claim against the actual state of the codebase. No skimming, no trusting the plan's own description of the code.
- Verify every component, composable, store, and file path the plan mentions. If it no longer exists, was renamed, or moved, flag it.
- If the project has a structure document (project_structure.md, CLAUDE.md, or docs/guidelines/), read it first and flag anything the plan places in the wrong layer or folder.

Work through the full checklist:

Separation of concerns:
- Components doing data fetching, state mutation, business logic, and rendering in the same file. Name the file.
- Composables that hold more than one responsibility, or that should have been a store.
- Stores holding component-local state, or components holding cross-cutting state.
- Prop drilling, event re-emission chains, parent components reaching into child internals.

Reactivity and types:
- Losing reactivity through destructuring, `ref` vs `reactive` confusion, computed used where a watcher belongs and the reverse.
- Types defined twice — once for the API, once for the UI — when one source of truth exists or should.

UX states and silence — what the plan does not say:
- Loading, empty, and failure states for every data source the plan touches. A missing state is a finding.
- Accessibility: keyboard reachability, focus handling, and labels for anything interactive the plan adds.
- i18n: user-facing strings the plan hardcodes.
- Component tests: which behaviors get tested. A plan silent on proof is a finding.

Cross-cutting:
- Separation-of-concerns violations: any component, composable, or store that mixes responsibilities. This is the most important check.
- Single-responsibility violations: anything doing more than one thing. Tied for most important.
- Architectural weak decisions: leaky abstractions, tight coupling, missing seams between layers, shortcuts that mortgage future work.
- Ambiguities: every place an implementer would have to guess what the author meant. Guesses become bugs.
- Missing pieces, internal contradictions, and scope that should be cut.

Quality bar:
- No vague feedback. "Consider refactoring" is not a finding. "Extract the fetch logic from path/to/Component.vue:42 into a composable because it mixes data access with rendering" is a finding.
- No hedging. Drop "might," "could," "perhaps," "you may want to." If you cannot verify something, say so directly — that is honest.
- Quote the plan when you challenge it. Cite file:line when you justify a finding. A finding without a citation is an opinion.
- If an area of the plan is genuinely sound, say so in one line and move on. Do not manufacture findings.

Output format in <Y>:
- Group findings by severity: Blocking, Important, Nit.
- Each finding states: (1) the issue in one sentence, (2) the exact location in the plan, (3) the codebase citation that proves the issue, (4) the concrete fix.
- After the findings, list any "Out of scope" one-liners.
- End with a one-line verdict: ship as-is, ship after Blocking fixed, or rework before implementation.
- No preamble. Get to the findings.

<X> = 
<Y> = 
```

- [ ] **Step 2: Write `plan-review-vue-aggressive.md`** with exactly this content:

```markdown
Your task is to tear the Vue side of plan <X> apart against the current codebase and write your findings to <Y>.

You are the Vue reviewer. Most reviewers skim, trust the plan's description of the code, and hedge. You will not.

I bet you cannot find every meaningful issue on the Vue side of this plan. Prove me wrong. Hunt from angles the plan did not anticipate.

Scope: judge only the Vue 3 frontend concerns of the plan. If you notice issues outside that scope (backend, API contract, tooling), record each as a one-line note in an "Out of scope" list at the end — do not investigate them.

Rules:
- Read the plan in full before you start. Then check every claim against the actual state of the codebase. No skimming, no trusting the plan's own description of the code.
- Verify every component, composable, store, and file path the plan mentions. If it no longer exists, was renamed, or moved, flag it.
- If the project has a structure document (project_structure.md, CLAUDE.md, or docs/guidelines/), read it first and flag anything the plan places in the wrong layer or folder.

Do at least three review passes, each from a different angle. Do not stop after one.

Pass 1 — separation of concerns:
- Components doing data fetching, state mutation, business logic, and rendering in the same file. Name the file.
- Composables that hold more than one responsibility, or that should have been a store.
- Stores holding component-local state, or components holding cross-cutting state.
- Prop drilling, event re-emission chains, parent components reaching into child internals.

Pass 2 — reactivity and types:
- Losing reactivity through destructuring, `ref` vs `reactive` confusion, computed used where a watcher belongs and the reverse.
- Types defined twice — once for the API, once for the UI — when one source of truth exists or should.

Pass 3 — UX states and silence, what the plan does not say:
- Loading, empty, and failure states for every data source the plan touches. A missing state is a finding.
- Accessibility: keyboard reachability, focus handling, and labels for anything interactive the plan adds.
- i18n: user-facing strings the plan hardcodes.
- Component tests: which behaviors get tested. A plan silent on proof is a finding.

Across all passes:
- Flag separation-of-concerns violations: any component, composable, or store that mixes responsibilities. This is the most important check.
- Flag single-responsibility violations: anything doing more than one thing. Tied for most important.
- Flag architectural weak decisions: leaky abstractions, tight coupling, missing seams between layers, shortcuts that mortgage future work.
- Identify ambiguities: every place an implementer would have to guess what the author meant. Guesses become bugs.
- Note missing pieces, internal contradictions, and scope that should be cut.

No vague feedback. "Consider refactoring" is not a finding. "Extract the fetch logic from path/to/Component.vue:42 into a composable because it mixes data access with rendering" is a finding.

No hedging. Drop "might," "could," "perhaps," "you may want to." If you cannot verify something, say so directly — that is honest. Hedging while pretending to know is dishonest.

Quote the plan when you challenge it. Cite file:line when you justify a finding. A finding without a citation is an opinion.

If you find nothing wrong, you missed things. Plans are never perfect. Run another pass from a new angle.

Output format in <Y>:
- Group findings by severity: Blocking, Important, Nit.
- Within each group, tag each finding with the pass that produced it: separation-of-concerns / reactivity-types / ux-states-silence.
- Each finding states: (1) the issue in one sentence, (2) the exact location in the plan, (3) the codebase citation that proves the issue, (4) the concrete fix.
- After the findings, list any "Out of scope" one-liners.
- End with a one-line verdict: ship as-is, ship after Blocking fixed, or rework before implementation.
- No preamble. No "I reviewed the plan and…" Get to the findings.

<X> = 
<Y> = 
```

- [ ] **Step 3: Verify**

Run: `grep -c "loading, empty, and failure states" -i prompts/plan-review/single-language/plan-review-vue*.md`
Expected: `1` per file.

- [ ] **Step 4: Commit**

```bash
git add prompts/plan-review/single-language/
git commit -m "chore: add single-language vue plan-review prompts"
```

---

### Task 4: API-seam prompt

**Files:**
- Create: `prompts/plan-review/single-language/plan-review-api-seam.md`

**Interfaces:**
- Produces: the seam panel member; Task 6's full-stack pipelines fill its `<BACKEND>` placeholder (`Rust` or `Python`).

- [ ] **Step 1: Write `plan-review-api-seam.md`** with exactly this content:

```markdown
Your task is to tear apart the API seam of plan <X> against the current codebase and write your findings to <Y>.

The backend is <BACKEND>; the frontend is Vue 3. You review ONLY the wire between them: the contract, not the code on either side. Most reviewers stay on one side of the wire and miss the seams. You will not.

I bet you cannot find every contract issue in this plan. Prove me wrong.

Scope: judge only what crosses the wire — shapes, statuses, parameters, auth, serialization. In-language design issues on either side go in an "Out of scope" list at the end, one line each — do not investigate them.

Rules:
- Read the plan in full before you start. Then check every claim against the actual state of the codebase on BOTH sides of the wire. No skimming, no trusting the plan's own description of the code.
- Verify every endpoint, route, handler, and frontend call site the plan mentions. If it no longer exists, was renamed, or moved, flag it.

Checks:
- Contract drift: response shapes the plan assumes versus what the backend handler actually returns. Cite both sides. For a Rust backend that means the serde response structs and handler return types; for a Python backend the Pydantic response models and FastAPI response_model declarations.
- Type generation: if TypeScript types are generated from the backend schema (OpenAPI or otherwise), is the generation step in the plan? If not, drift is guaranteed. If types are hand-maintained on both sides, flag that as the root cause.
- Error contract: how does a backend error become an HTTP status and a Vue-visible message? Check error handlers, problem-details shape, validation error shape. If the plan does not answer, that is a finding.
- Auth and permission edges: which endpoints does the plan touch, which roles can hit them, what does the Vue side do when forbidden? Verify the backend actually enforces what the plan claims.
- Pagination, sorting, filtering: if the backend adds it, is the frontend wired? If the frontend assumes it, does the backend deliver? Query parameter names must match exactly.
- Serialization edges: datetime timezone handling, decimal precision, enum string vs int representation, null vs missing field. Each is a finding when the plan is silent.
- For every new or changed endpoint: does the frontend consume it, and does the contract cover the failure responses the frontend must render?

No vague feedback. "Consider aligning the types" is not a finding. "The plan assumes `created_at` is an ISO string but handler path/to/handler returns epoch millis — regenerate the client type and fix the formatter in path/to/Component.vue" is a finding.

No hedging. Drop "might," "could," "perhaps," "you may want to." If you cannot verify something, say so directly — that is honest. Hedging while pretending to know is dishonest.

Quote the plan when you challenge it. Cite file:line on each side of the wire when you justify a finding. A finding without a citation is an opinion.

If you find nothing wrong, you missed things. Plans are never perfect. Walk the contract again endpoint by endpoint.

Output format in <Y>:
- Group findings by severity: Blocking, Important, Nit.
- Each finding states: (1) the issue in one sentence, (2) the exact location in the plan, (3) the citation on each side of the wire that proves it, (4) the concrete fix.
- After the findings, list any "Out of scope" one-liners.
- End with a one-line verdict: ship as-is, ship after Blocking fixed, or rework before implementation.
- No preamble. No "I reviewed the plan and…" Get to the findings.

<X> = 
<Y> = 
<BACKEND> = 
```

- [ ] **Step 2: Verify**

Run: `grep -c "<BACKEND>" prompts/plan-review/single-language/plan-review-api-seam.md`
Expected: `2` or more (header use + fill-in line).

- [ ] **Step 3: Commit**

```bash
git add prompts/plan-review/single-language/plan-review-api-seam.md
git commit -m "chore: add api-seam plan-review prompt"
```

---

### Task 5: Lens prompts

**Files:**
- Create: `prompts/plan-review/lenses/plan-review-security.md`
- Create: `prompts/plan-review/lenses/plan-review-tests-and-migrations.md`
- Create: `prompts/plan-review/lenses/plan-review-operational-readiness.md`

**Interfaces:**
- Produces: the three lens panel members referenced by path in Task 6's pipelines.

- [ ] **Step 1: Write `plan-review-security.md`** with exactly this content:

```markdown
Your task is to review plan <X> against the current codebase for security concerns only, and write your findings to <Y>.

Scope: you are the security reviewer. Judge only security, in any language the plan touches. Architecture, style, and product concerns go in an "Out of scope" list at the end, one line each — do not investigate them.

Rules:
- Read the plan in full before you start. Then check every claim against the actual state of the codebase. No skimming, no trusting the plan's own description of the code.
- Verify every file path, endpoint, and module the plan mentions. If it no longer exists, was renamed, or moved, flag it.

Work through the full checklist:

- Authentication and authorization: for every endpoint, route, command, or job the plan adds or changes — who can call it, and where is that enforced in code? Enforcement claimed in the plan but absent from the code is a finding.
- Input validation: every input crossing a trust boundary — HTTP bodies, query parameters, headers, file uploads, message payloads. Type, length, range, encoding.
- Injection surfaces: SQL built by string concatenation or formatting, shell commands from user input, path traversal on file operations, HTML injection through templates or `v-html`.
- Secrets: keys, tokens, or passwords appearing in code, config, logs, or error messages the plan introduces. How are new secrets provisioned and rotated?
- Data exposure: response payloads leaking fields the caller should not see. Multi-tenant edges: can tenant A reach tenant B's rows through any path the plan touches?
- Sensitive data in logs: credentials, tokens, or personal data flowing into logs on new code paths.
- Silence: the plan touches authentication, authorization, or input handling and says nothing about the security consequences. That silence is a finding.

Quality bar:
- No vague feedback. "Validate the input" is not a finding. "The new upload endpoint in the plan takes a filename used at path/to/handler without normalization — reject path separators before use" is a finding.
- No hedging. Drop "might," "could," "perhaps," "you may want to." If you cannot verify something, say so directly — that is honest.
- Quote the plan when you challenge it. Cite file:line when you justify a finding. A finding without a citation is an opinion.
- If an area of the plan is genuinely sound, say so in one line and move on. Do not manufacture findings.

Output format in <Y>:
- Group findings by severity: Blocking, Important, Nit.
- Each finding states: (1) the issue in one sentence, (2) the exact location in the plan, (3) the codebase citation that proves the issue, (4) the concrete fix.
- After the findings, list any "Out of scope" one-liners.
- End with a one-line verdict: ship as-is, ship after Blocking fixed, or rework before implementation.
- No preamble. Get to the findings.

<X> = 
<Y> = 
```

- [ ] **Step 2: Write `plan-review-tests-and-migrations.md`** with exactly this content:

```markdown
Your task is to review plan <X> against the current codebase for proof and migration safety only, and write your findings to <Y>.

Scope: you are the proof-and-migration reviewer. Judge only whether the plan proves its changes and migrates data safely, in any language the plan touches. Architecture, style, and product concerns go in an "Out of scope" list at the end, one line each — do not investigate them.

Rules:
- Read the plan in full before you start. Then check every claim against the actual state of the codebase. No skimming, no trusting the plan's own description of the code.
- Verify every test file, migration, and module the plan mentions. If it no longer exists, was renamed, or moved, flag it.
- Find where the project's existing tests live and how they are shaped before judging the planned ones.

Work through the full checklist:

- Proof per change: for every behavior the plan adds or alters, which test proves it — unit, integration, or contract? Name the missing test. "Add tests" without naming behaviors is itself a finding.
- Test placement and shape: do the planned tests live where the project's existing tests live, and do they assert behavior rather than implementation detail?
- Regression surface: which existing tests should change or break because of this plan? A plan that changes behavior without touching any existing test is suspicious — say which test file should have been mentioned.
- Migration ordering: do schema migrations land before, with, or after the code that needs them? Is the order stated? Can the previous version of the code run against the new schema during a rolling deploy?
- Downgrade path: does every migration have a working down path? Is data loss on downgrade acknowledged?
- Backfill safety: any data backfill — is it idempotent, batched, and restartable? What happens if it dies halfway through?
- Deploy-order coupling: does the plan require a deploy sequence (migration before code, backend before frontend, worker after queue change)? If yes and unstated, that is a finding.

Quality bar:
- No vague feedback. "Improve test coverage" is not a finding. "The plan's new discount rule has no test proving the rounding behavior — add a unit test beside the existing pricing tests" is a finding.
- No hedging. Drop "might," "could," "perhaps," "you may want to." If you cannot verify something, say so directly — that is honest.
- Quote the plan when you challenge it. Cite file:line when you justify a finding. A finding without a citation is an opinion.
- If an area of the plan is genuinely sound, say so in one line and move on. Do not manufacture findings.

Output format in <Y>:
- Group findings by severity: Blocking, Important, Nit.
- Each finding states: (1) the issue in one sentence, (2) the exact location in the plan, (3) the codebase citation that proves the issue, (4) the concrete fix.
- After the findings, list any "Out of scope" one-liners.
- End with a one-line verdict: ship as-is, ship after Blocking fixed, or rework before implementation.
- No preamble. Get to the findings.

<X> = 
<Y> = 
```

- [ ] **Step 3: Write `plan-review-operational-readiness.md`** with exactly this content:

```markdown
Your task is to review plan <X> against the current codebase for operational readiness only, and write your findings to <Y>.

Scope: you are the operations reviewer. Judge only how this plan behaves in production — deploy, failure, recovery — in any language the plan touches. Architecture, style, and product concerns go in an "Out of scope" list at the end, one line each — do not investigate them.

Rules:
- Read the plan in full before you start. Then check every claim against the actual state of the codebase. No skimming, no trusting the plan's own description of the code.
- Verify every file path, service, and module the plan mentions. If it no longer exists, was renamed, or moved, flag it.

Work through the full checklist:

- Rollback story: if this change misbehaves in production, what is the undo — revert commit, feature flag off, migration down? The plan must name one. No named undo is a finding.
- Feature flags: should risky behavior ship dark? A plan that flips behavior for all users at deploy time with no flag and no staged rollout is a finding when the change is user-facing or data-touching.
- Observability: structured logs on new paths, metrics on new operations, and enough context in each to debug a failure at 2 AM. "We'll see it in the logs" without naming the log line is a finding.
- External calls: every new call to a database, queue, or third-party API — timeout, retry policy, and failure mode. What does the user see when the dependency is down?
- Idempotency and retries: can every new operation be retried safely? For jobs and consumers: what happens on redelivery or double-processing?
- Capacity: anything the plan adds that is O(n) over a growing table, an unbounded queue, a per-request fan-out, or an unpaginated listing.
- Silence: the plan adds production behavior and says nothing about failure. That silence is a finding.

Quality bar:
- No vague feedback. "Add monitoring" is not a finding. "The new webhook dispatcher has no retry policy and no dead-letter path — a single 5xx from the receiver drops the event silently" is a finding.
- No hedging. Drop "might," "could," "perhaps," "you may want to." If you cannot verify something, say so directly — that is honest.
- Quote the plan when you challenge it. Cite file:line when you justify a finding. A finding without a citation is an opinion.
- If an area of the plan is genuinely sound, say so in one line and move on. Do not manufacture findings.

Output format in <Y>:
- Group findings by severity: Blocking, Important, Nit.
- Each finding states: (1) the issue in one sentence, (2) the exact location in the plan, (3) the codebase citation that proves the issue, (4) the concrete fix.
- After the findings, list any "Out of scope" one-liners.
- End with a one-line verdict: ship as-is, ship after Blocking fixed, or rework before implementation.
- No preamble. Get to the findings.

<X> = 
<Y> = 
```

- [ ] **Step 4: Verify**

Run: `ls prompts/plan-review/lenses/ && grep -L "Out of scope" prompts/plan-review/lenses/*.md`
Expected: three files listed; grep prints nothing.

- [ ] **Step 5: Commit**

```bash
git add prompts/plan-review/lenses/
git commit -m "chore: add plan-review lens prompts"
```

---

### Task 6: Pipeline orchestrators

**Files:**
- Create: `prompts/plan-review/subagents/pipeline-rust-vue.md`
- Create: `prompts/plan-review/subagents/pipeline-python-vue.md`
- Create: `prompts/plan-review/subagents/pipeline-rust.md`
- Create: `prompts/plan-review/subagents/pipeline-python.md`
- Create: `prompts/plan-review/subagents/pipeline-vue.md`

**Interfaces:**
- Consumes: every prompt file created in Tasks 1–5, plus `generic/plan-review-day-off-bet.md` and `generic/plan-review-loss-framing.md`, referenced by exact path.

All five files share one template; only the panel table, the panel size N, and the `found-by k/N` denominator differ. The full template is given once for `pipeline-rust-vue.md`; the other four repeat it with their own panel table and N substituted. The embedded Stage 2 and Stage 3 briefs use indented blocks (no nested code fences).

- [ ] **Step 1: Write `pipeline-rust-vue.md`** with exactly this content (N = 8):

```markdown
Your task is to run a staged review pipeline on plan <X> against the current codebase.

The pipeline has three stages: Stage 1 dispatches a parallel review panel, Stage 2 synthesizes the panel's findings into one report, Stage 3 adversarially verifies the serious findings. Run the stages in order, completing each before starting the next.

(Note for the human dispatching this prompt — delete stages from the bottom for a cheaper run: Stage 1 only = raw parallel reviews; Stages 1–2 = consolidated report; all three = verified report.)

Stage 1 — Panel

Launch 8 subagents in parallel to review plan <X>. Eight independent perspectives, no cross-talk, no shared context beyond the plan itself.

Rules:
- Dispatch all 8 subagents in a single message. Parallel, not sequential.
- Each subagent receives: (1) the plan path <X>, (2) its output path <Y>-plan-review-NN.md where NN comes from the table below, (3) the contents of its prompt file with the placeholder lines at the bottom filled in — nothing else. No summary of prior conversation, no hints, no framing.
- Pass each prompt verbatim. Do not paraphrase, condense, or "improve" it — the framing in each prompt is load-bearing.
- Do not read, merge, or edit the review files. The panel's raw output belongs to the user.
- If a prompt below does not fit the project's stack, swap it before dispatching and tell the user which one you swapped and why.

| NN | Prompt file | Extra placeholder fill |
|----|-------------|------------------------|
| 01 | <agent-skills>/prompts/plan-review/single-language/plan-review-rust-aggressive.md | — |
| 02 | <agent-skills>/prompts/plan-review/single-language/plan-review-vue-aggressive.md | — |
| 03 | <agent-skills>/prompts/plan-review/single-language/plan-review-api-seam.md | <BACKEND> = Rust |
| 04 | <agent-skills>/prompts/plan-review/generic/plan-review-day-off-bet.md | — |
| 05 | <agent-skills>/prompts/plan-review/generic/plan-review-loss-framing.md | — |
| 06 | <agent-skills>/prompts/plan-review/lenses/plan-review-security.md | — |
| 07 | <agent-skills>/prompts/plan-review/lenses/plan-review-tests-and-migrations.md | — |
| 08 | <agent-skills>/prompts/plan-review/lenses/plan-review-operational-readiness.md | — |

Wait for all 8 to finish before starting Stage 2.

Stage 2 — Synthesis

Dispatch ONE fresh subagent — do not do this work yourself — with exactly this brief:

    Read the review files <Y>-plan-review-01.md through <Y>-plan-review-08.md. They are 8 independent reviews of plan <X>. Write a synthesis to <Y>-plan-review-synthesis.md:
    - Merge findings that describe the same underlying issue into one entry that names every review that found it (by file number) and keeps the strongest citation.
    - Tag every entry with its corroboration: found-by k/8.
    - Where reviews disagree — one calls something sound, another calls it a flaw — record the disagreement as a disagreement. Never silently resolve it.
    - Order entries by severity (Blocking, Important, Nit), then by corroboration within each severity.
    - Do not add findings of your own. Do not drop any panel finding: every finding from every review appears, either merged into an entry or as its own entry.
    - End with a verdict tally: each review's one-line verdict and the count per verdict.

Do not edit the synthesis when it returns. Wait for it to finish before starting Stage 3.

Stage 3 — Adversarial verification

Read <Y>-plan-review-synthesis.md — only this file, and only to enumerate its Blocking and Important findings. Nits skip verification.

For each Blocking or Important finding, dispatch one skeptic subagent — all skeptics in a single message, in parallel — each with exactly this brief, with the finding pasted in:

    You are a skeptic. Here is a claimed problem with plan <X>: [paste the full finding, including its plan location and codebase citation]. Try to REFUTE it against the actual plan text and the actual codebase. Check the citation: does the cited code say what the finding claims? Check the reasoning: does the problem actually follow? If the finding survives your best attempt to kill it, your verdict is CONFIRMED, with the evidence that survived. If it does not, or you cannot verify it, your verdict is REFUTED, with the evidence or the missing verification that killed it. Report exactly: the verdict, then at most three sentences of evidence with file:line citations. Nothing else.

Assemble the skeptic verdicts verbatim into <Y>-plan-review-verified.md: each finding followed by its verdict and evidence, ordered Blocking then Important, corroboration tags preserved. Close the file with one line stating the CONFIRMED and REFUTED counts and a final recommendation: ship as-is, ship after CONFIRMED Blocking fixed, or rework before implementation.

<X> = 
<Y> = 
<agent-skills> = 
```

- [ ] **Step 2: Write `pipeline-python-vue.md`** — identical template with N = 8 throughout, and this panel table:

| NN | Prompt file | Extra placeholder fill |
|----|-------------|------------------------|
| 01 | `<agent-skills>/prompts/plan-review/single-language/plan-review-python-aggressive.md` | — |
| 02 | `<agent-skills>/prompts/plan-review/single-language/plan-review-vue-aggressive.md` | — |
| 03 | `<agent-skills>/prompts/plan-review/single-language/plan-review-api-seam.md` | `<BACKEND> = Python` |
| 04 | `<agent-skills>/prompts/plan-review/generic/plan-review-day-off-bet.md` | — |
| 05 | `<agent-skills>/prompts/plan-review/generic/plan-review-loss-framing.md` | — |
| 06 | `<agent-skills>/prompts/plan-review/lenses/plan-review-security.md` | — |
| 07 | `<agent-skills>/prompts/plan-review/lenses/plan-review-tests-and-migrations.md` | — |
| 08 | `<agent-skills>/prompts/plan-review/lenses/plan-review-operational-readiness.md` | — |

- [ ] **Step 3: Write `pipeline-rust.md`** — identical template with N = 6 throughout ("Launch 6 subagents", "01.md through -06.md", "found-by k/6", "Wait for all 6"), and this panel table:

| NN | Prompt file | Extra placeholder fill |
|----|-------------|------------------------|
| 01 | `<agent-skills>/prompts/plan-review/single-language/plan-review-rust-aggressive.md` | — |
| 02 | `<agent-skills>/prompts/plan-review/single-language/plan-review-rust.md` | — |
| 03 | `<agent-skills>/prompts/plan-review/generic/plan-review-day-off-bet.md` | — |
| 04 | `<agent-skills>/prompts/plan-review/lenses/plan-review-security.md` | — |
| 05 | `<agent-skills>/prompts/plan-review/lenses/plan-review-tests-and-migrations.md` | — |
| 06 | `<agent-skills>/prompts/plan-review/lenses/plan-review-operational-readiness.md` | — |

- [ ] **Step 4: Write `pipeline-python.md`** — identical template with N = 6 throughout, and this panel table:

| NN | Prompt file | Extra placeholder fill |
|----|-------------|------------------------|
| 01 | `<agent-skills>/prompts/plan-review/single-language/plan-review-python-aggressive.md` | — |
| 02 | `<agent-skills>/prompts/plan-review/single-language/plan-review-python.md` | — |
| 03 | `<agent-skills>/prompts/plan-review/generic/plan-review-day-off-bet.md` | — |
| 04 | `<agent-skills>/prompts/plan-review/lenses/plan-review-security.md` | — |
| 05 | `<agent-skills>/prompts/plan-review/lenses/plan-review-tests-and-migrations.md` | — |
| 06 | `<agent-skills>/prompts/plan-review/lenses/plan-review-operational-readiness.md` | — |

- [ ] **Step 5: Write `pipeline-vue.md`** — identical template with N = 5 throughout, and this panel table (no seam, no operational-readiness per spec):

| NN | Prompt file | Extra placeholder fill |
|----|-------------|------------------------|
| 01 | `<agent-skills>/prompts/plan-review/single-language/plan-review-vue-aggressive.md` | — |
| 02 | `<agent-skills>/prompts/plan-review/single-language/plan-review-vue.md` | — |
| 03 | `<agent-skills>/prompts/plan-review/generic/plan-review-day-off-bet.md` | — |
| 04 | `<agent-skills>/prompts/plan-review/lenses/plan-review-security.md` | — |
| 05 | `<agent-skills>/prompts/plan-review/lenses/plan-review-tests-and-migrations.md` | — |

- [ ] **Step 6: Verify every referenced path exists**

Run:
```bash
grep -ho '<agent-skills>/prompts/plan-review/[a-z-]*/[a-z-]*\.md' prompts/plan-review/subagents/pipeline-*.md | sort -u | sed 's|<agent-skills>|.|' | xargs ls -la
```
Expected: every listed file exists (no `ls` errors). Also run `grep -c "Stage 3" prompts/plan-review/subagents/pipeline-*.md` — expected ≥ 1 per file.

- [ ] **Step 7: Commit**

```bash
git add prompts/plan-review/subagents/pipeline-*.md
git commit -m "chore: add staged plan-review pipeline orchestrators"
```

---

### Task 7: Housekeeping — typo fix, deletions, reference sync

**Files:**
- Modify: `prompts/plan-review/generic/plan-review-money-bet.md` (line 18: `aseverity` → `severity`)
- Delete: `prompts/plan-review/stack-based/` (all 4 files)
- Delete: `prompts/plan-review/subagents/parallel-5-agents-rust-vue.md`
- Delete: `prompts/plan-review/subagents/parallel-5-agents-python-vue.md`
- Delete: `prompts/plan-review/subagents/parallel-3-agents-generic.md`
- Delete: `prompts/plan-review/subagents/parallel-2-agents-rust-vue.md`

- [ ] **Step 1: Fix the typo** in `generic/plan-review-money-bet.md`: change `- Group findings by aseverity: Blocking, Important, Nit.` to `- Group findings by severity: Blocking, Important, Nit.`

- [ ] **Step 2: Delete superseded files**

```bash
git rm -r prompts/plan-review/stack-based/
git rm prompts/plan-review/subagents/parallel-5-agents-rust-vue.md prompts/plan-review/subagents/parallel-5-agents-python-vue.md prompts/plan-review/subagents/parallel-3-agents-generic.md prompts/plan-review/subagents/parallel-2-agents-rust-vue.md
```

- [ ] **Step 3: Verify no dangling references** (rule-number-sync applied to paths)

Run: `grep -rn "plan-review/stack-based\|parallel-5-agents\|parallel-3-agents-generic\|parallel-2-agents\|aggresive" prompts/`
Expected: no matches anywhere under `prompts/`. (The spec document under `docs/` may still mention `stack-based/` — it describes the change; that is fine.)

- [ ] **Step 4: Verify final tree matches the spec**

Run: `find prompts/plan-review -type f | sort`
Expected: exactly 18 files — 7 in `single-language/`, 3 in `generic/`, 3 in `lenses/`, 5 in `subagents/`.

- [ ] **Step 5: Commit**

```bash
git add prompts/plan-review/
git commit -m "chore: remove superseded stack-based prompts and orchestrators, fix typo"
```
