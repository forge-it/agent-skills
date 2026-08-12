---
name: greenfield-project-setup
description: >-
  Use when starting a NEW green-field backend or full-stack project — python+vue,
  rust+vue, or a combination in a monorepo — and the repository must be
  structured correctly from commit 1 so it never needs a costly structural
  refactor later. Use when bootstrapping a monorepo, standing up a new service,
  or laying the foundation an agent fleet (including parallel git-worktree
  agents) will build on. Symptoms it prevents: wiring blobs in main, the
  application layer importing infrastructure, ad-hoc scripts, advisory-only
  lints, port collisions across worktrees, conventions enforced only by prose
  that review cannot hold, a workspace member whose gate nobody runs, a worker
  bolted on months too late.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.4"
---

# Greenfield Project Setup (Orchestrator)

## Purpose

This skill is a **sequencer, not a content dump**. Its single responsibility is
to bring up a new project's foundation **in the right order**, delegating each
concern to the skill or pattern that owns it and **running a verification gate**
after each phase. It never re-encodes architecture or style rules — those live
in the delegated skills, which stay the single source of truth.

**The goal:** a structure so correct and self-guarding that agents — including
several working in parallel git worktrees — stay productive and *cannot drift*,
and that never needs a multi-week structural refactor. Every phase ends in a
gate precisely so a missing invariant fails loudly *now*, at setup, instead of
silently months later.

> **Core principle (separation of concerns / single responsibility):** this
> orchestrator owns *ordering and verification* and nothing else. Each delegated
> skill owns its own concern. If you find yourself explaining *how* to lay out a
> hexagonal module here, stop — that belongs to the architecture skill; link it.

## When to Use / When Not

**Use** for a new backend or full-stack project with real business logic and
external integrations (a database, a broker, third-party APIs), especially a
monorepo mixing rust / python / vue components.

**Do not use** for a throwaway script, a single-purpose CLI, or a library with
no persistence or integrations — the gates would be ceremony without payoff.

## How To Use This Skill

1. **Establish the stack.** Detect from any existing files, otherwise ask: which
   components (rust backend, python backend, vue frontend), and is a scalable
   broker-backed **worker** in scope? (Default it **on** for anything intended
   as a SaaS — retrofitting it later is the costly refactor.)
2. **Walk the phases in order.** They are dependency-ordered; later phases assume
   earlier gates passed. Use the **Stack Matrix** to skip phases that don't apply
   to your components.
3. **For each phase:** invoke the named skill (`REQUIRED SUB-SKILL`) or read the
   named pattern doc, produce the artifacts, then **run the gate before moving
   on.** A gate is not optional — a failing gate means the invariant is not live.
4. **Never skip a gate** to "come back later." Violating the letter of the gate
   is violating the spirit of the setup.

## The Phases

Each row: what the phase establishes, what it delegates to (SKILL = invoke by
name; *pattern* = read the doc), and the gate that proves it is live.

| # | Phase | Delegates to | Gate (proof it is live) |
|---|-------|--------------|--------------------------|
| 0 | Stack + repo init | — | monorepo dirs (`core/` rust, `web/` vue, `worker/`, `crates/`, or a python package / uv workspace root) + `git` initialized |
| 1 | Workspace + toolchain | rust: SKILL `rust-workspace-setup` + `rust-project-setup`; python: SKILL `python-project-setup` (a multi-package repo also *reads* conventions/`python` — its greenfield recipe, not this skill, owns creating the uv workspace root) | `cargo build` succeeds / `uv sync` succeeds **and the package actually imports** — `uv sync` exits 0 on a `src/` layout with no `[build-system]`, so it alone proves nothing |
| 2 | Component skeletons | SKILL `rust-hexagonal-architecture` + `rust-project-structure` / `python-ddd` / `frontend-vue-development` | each component compiles |
| 3 | Architecture invariant gates | rust workspace: *read* `rust-architecture-test-setup` (catalogue only) → SKILL `rust-conventions-crate-setup`; rust single crate: SKILL `rust-architecture-test-setup`; python: SKILL `python-import-linter-setup` + *read* conventions/`python` for the conventions package; vue: SKILL `frontend-vue-eslint-setup` | the gate **passes clean AND fails on a planted violation** — the member-local gate fails in the owning component and no other; every member has a gate. Python's `lint-imports` half is one root-level contract set, so its findings are *not* member-local |
| 4 | Backend wiring + lifecycle | *composition_pattern* → *bootstrap_pattern* → *runtime_pattern* | app boots; workers drain on SIGTERM |
| 5 | Task runner | SKILL `justfile-setup` | `just` recipes (dev / local-prod / prod / lint / test-all) run, **plus one recipe per gate family** — on a Rust workspace `cargo test --workspace --test structure`; on a Python repo `uv run lint-imports` plus a per-member `cd <member> && uv run pytest` (never `uv run --package X pytest` from the root — it aborts collection) |
| 6 | Local infra + parallel test isolation | *local_port_allocation_pattern* + *parallel_test_isolation_pattern* | integration tests pass **in parallel**, no collisions |
| 7 | Scalability (opt-in, default-on for SaaS) | *worker_pattern* + *worker_fleet_pattern* + the shared task-contracts package — rust: a workspace crate (`rust-workspace-setup`); python: a uv workspace member (see *worker_pattern*'s Python mapping) | worker boots and consumes a test task |
| 8 | Day-1 cross-cutting decisions (ADRs) | *observability_posture_pattern*; *frontend_api_type_mirroring_pattern* (if vue+backend); *worker_fleet_pattern* topology + identity ADRs (if worker); port allocation (phase 6); the convention-enforcement policy and its permission protocol (phase 3); the task-runner growth mechanism (`import`, never `mod`) | each decision recorded as an ADR in `docs/decisions/` |
| 9 | Navigation + docs | *claude_md_pattern* + *docs_artifact_layout_pattern* + *repo_root_files_pattern* | root + per-component `CLAUDE.md` and `docs/` trees exist; root files present |
| 10 | Automation gates | SKILL `agent-hooks-setup` + `ci-setup`; *dependency_audit_pattern* | hooks fire locally; CI is green on a trial PR **and invokes the task runner, never a hand-listed crate/member set**; audit command runs |
| 11 | Continuous practices (wire in, not one-shot) | SKILL `rust-testing` / `python-testing` + `python-commands`, `*-code-style`, `rust-design-principles` / `rust-design-idioms`, `rest-api-design`, `reconcile-docs` | referenced by `CLAUDE.md`, enforced by phase-10 hooks + CI |
| 12 | Final verification sweep | — | **every** gate green together (see Quick Reference) |

Pattern docs live under `../../patterns/`; e.g. `composition_pattern` is
`../../patterns/project_structure/composition_pattern.md`, the lifecycle ones are
in `../../patterns/lifecycle/`, and the rest under `../../patterns/{documentation,
decisions,testing,automation,scalability,conventions}/`.

### Phase 3 on a Rust workspace is two sub-steps, in one order

**Read** `rust-architecture-test-setup` for the rule catalogue — which invariants
this project enforces — but do not install its single-crate `tests/structure/`
tree. Then **invoke** `rust-conventions-crate-setup` for the packaging. A
single-crate project does the reverse: invoke the first skill and stop, since the
conventions crate buys a locality it does not yet need.

Skipping the second step on a workspace is what leaves one crate's gate scanning
its siblings, or the scanner copied per crate — both refactors later.

### Phase 3 on a Python monorepo has the same two sub-steps

**Invoke** `python-import-linter-setup` for the layer and boundary contracts —
what Python cannot enforce by construction. Then **read** conventions/`python` and
install the conventions package it specifies. Same ordering as Rust, different
mechanics.

One asymmetry to know going in: `lint-imports` runs one root-level contract set,
so unlike the conventions gate its findings are not member-local — do not expect
the "fails in the owning component and no other" half of the phase gate from it.
Gate *coverage*, by contrast, is mechanized on both stacks: each conventions
library carries a **coverage rule** that fails when a member owns no gate. The
Python one reads `[manifest] members` from `uv.lock` — uv's own list, never
inferred from source kinds, since an out-of-glob path dependency with
`[tool.uv] package = false` also locks as `virtual`.

Note the phase boundary: phase 3 **installs** the gates; phases 5 and 10 are what
make them **reachable**. The task-runner recipe and the CI step belong there, not
here.

### Why this order

Toolchain/workspace (1) gives crates a home before you scaffold them (2). The
skeleton must exist before its invariant gate (3) can guard it. Wiring (4) needs
the components. The task runner (5) is what every later phase and CI invokes.
Test isolation (6) depends on port allocation. The worker (7) reuses the wiring
patterns from (4) and the shared contracts package from (1). Docs and navigation (9) describe
what now exists. Automation (10) makes all prior gates *blocking*. Continuous
practices (11) are wired into those gates. The final sweep (12) runs everything
at once.

## Stack Matrix

Which phases apply to which components (✓ = applies, — = skip):

| Phase | Rust backend | Python backend | Vue frontend | Worker |
|-------|:---:|:---:|:---:|:---:|
| 1 workspace/toolchain | ✓ | ✓ (uv, pinned interpreter) | ✓ (node) | ✓ (same stack as its API) |
| 2 skeleton | ✓ hexagonal | ✓ DDD | ✓ feature-arch | ✓ hexagonal |
| 3 invariant gate | ✓ structure-test (+ conventions crate on a workspace) | ✓ import-linter (+ conventions package on a uv workspace) | ✓ eslint | ✓ own gate + the shared conventions crate/package |
| 4 wiring/lifecycle | ✓ | ✓ | — | ✓ |
| 6 test isolation | ✓ | ✓ pytest fixtures + xdist worker identity | partial | ✓ |
| 7 worker | — | — | — | ✓ |
| 8 day-1 ADRs | ✓ | ✓ | ✓ (type-mirroring consumer) | ✓ (fleet topology + identity) |
| 9 docs + CLAUDE.md | ✓ | ✓ | ✓ | ✓ |
| 10 hooks/CI/audit | ✓ | ✓ | ✓ | ✓ |

A **combination** monorepo runs the per-component phases once per component
directory; the root-level phases (5 task runner, 9 root docs, 10 CI/hooks) run
once at the root and fan in.

## Quick Reference — Final Verification Sweep (phase 12)

The foundation is live only when **all** of these pass together:

- [ ] every component builds (`cargo build`, `uv sync` **plus a real import of each Python package**, web build)
- [ ] architecture gates pass **and** fail on a planted violation (structure test / `lint-imports` / eslint) — the member-local gate failing in the component the violation lives in **and no other member's gate**
- [ ] every workspace member owns a gate, proven by the conventions library's coverage rule on both stacks — note `cargo test --workspace --test structure` passes when a gate is missing, so it proves nothing here, and both rules assert the gate *file* exists, not that it calls every rule
- [ ] every gate is reachable from the task runner, and CI invokes the runner instead of a hand-listed crate/member set
- [ ] every convention rule has a `should_flag`/`should_pass` fixture pair, and they actually run
- [ ] no gate test is disabled or landed red — `grep -rn '#\[ignore' --include='*.rs' .` returns nothing, and `grep -rn '\(@pytest\.mark\|pytestmark = pytest\.mark\)\.\(skip\|xfail\)' --include='*.py' */tests/architecture` returns nothing (scoped to gate directories: a `skipif` in an ordinary suite is legitimate, so a repo-wide grep here only teaches you to wave the check through)
- [ ] every `GRANTED_*` permission ledger is still empty — `grep -rn 'GRANTED_' --include='*.rs' .` shows only empty collections
- [ ] `rustfmt --check`, `clippy -D warnings`, `ruff check`, `ruff format --check`, type checks clean
- [ ] unit + integration tests pass **in parallel** (isolation works)
- [ ] `just test-all` (the single CI entry recipe) runs locally
- [ ] agent hooks are installed and fire on a trial commit
- [ ] CI is green on a trial PR (gates are blocking)
- [ ] dependency-audit command runs across every ecosystem in the repo
- [ ] root + per-component `CLAUDE.md` and `docs/` exist; ADRs recorded
- [ ] the worker (if in scope) boots and consumes a test task

## Anti-Patterns to Avoid

- **Skipping gates** ("I'll wire CI later"). The invariant is not live until its
  gate is. Deferred gates become never-gates.
- **Deferring the worker** when the product is a SaaS. Bolting on a broker-backed
  worker after the API is entangled with synchronous heavy work is the multi-week
  refactor this whole skill exists to prevent.
- **Re-encoding rules here.** Copying hexagonal-layout or style rules into this
  skill instead of delegating. It bloats the orchestrator and the copy drifts.
- **Scaffolding before the workspace exists** (phase 2 before phase 1), so crates
  have no shared home and dependencies are duplicated per crate.
- **Advisory-only enforcement.** Stopping at phase 3 (local gates) without phase
  10 (CI makes them blocking). Local gates an agent can bypass are not invariants.
  The same failure in a second disguise: per-component gates plus a hand-maintained
  crate/member list in CI, so every member added later is silently unenforced until
  someone remembers the list. Let CI invoke the task runner, and let a coverage
  rule prove every member owns a gate — the Rust conventions crate and the Python
  conventions package each carry one (phase 3).
- **Hardcoded ports / shared test DB.** Skipping phase 6 kills parallel-worktree
  productivity — the exact thing the setup is meant to enable.
- **Duplicating the rule scanner per component.** Two copies of a non-trivial
  walker drift apart quietly, and one component's gate policing its siblings
  reports a violation against the wrong owner. Rules belong in one shared library
  — a Rust conventions crate, a Python conventions package — that each component
  instantiates against its own tree (phase 3).

## What This Skill Orchestrates (index)

**Setup skills (executable):** `rust-workspace-setup`, `rust-project-setup`,
`rust-architecture-test-setup`, `rust-conventions-crate-setup`,
`python-project-setup`, `python-import-linter-setup`,
`frontend-vue-eslint-setup`, `justfile-setup`, `ci-setup`, `agent-hooks-setup`.

**Architecture/knowledge skills:** `rust-hexagonal-architecture`,
`rust-project-structure`, `python-ddd`, `frontend-vue-development`,
`rust-design-principles`, `rust-design-idioms`, `rest-api-design`,
`rust-testing`, `python-testing`, `python-commands`, `rust-code-style`,
`python-code-style-v1`, `frontend-vue-code-style`, `reconcile-docs`.

**Patterns (read the doc):** project_structure/`composition_pattern`;
lifecycle/`bootstrap_pattern`, `runtime_pattern`; scalability/`worker_pattern`,
`worker_fleet_pattern`; testing/`parallel_test_isolation_pattern`;
conventions/`rust`, `python`; decisions/`local_port_allocation_pattern`,
`frontend_api_type_mirroring_pattern`, `observability_posture_pattern`;
documentation/`claude_md_pattern`, `docs_artifact_layout_pattern`,
`repo_root_files_pattern`; automation/`dependency_audit_pattern`.

**Continuous guards (installed in phase 10):** `rust-structure-and-style-guard`,
`vue-structure-and-style-guard`, `python-structure-and-style-guard` — dispatched
by the agent hooks so drift is caught on every commit, including in parallel
worktrees.
