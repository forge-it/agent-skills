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
  lints, port collisions across worktrees, a worker bolted on months too late.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.1"
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
| 0 | Stack + repo init | — | monorepo dirs (`core/` rust, `web/` vue, `worker/`, `crates/`, or a python pkg) + `git` initialized |
| 1 | Workspace + toolchain | SKILL `rust-workspace-setup` + `rust-project-setup`; python: `uv` init | `cargo build` / `uv sync` succeeds |
| 2 | Component skeletons | SKILL `rust-hexagonal-architecture` + `rust-project-structure` / `python-ddd` / `frontend-vue-development` | each component compiles |
| 3 | Architecture invariant gates | SKILL `rust-architecture-test-setup` / `python-import-linter-setup` / `frontend-vue-eslint-setup` | the gate **passes clean AND fails on a planted violation** |
| 4 | Backend wiring + lifecycle | *composition_pattern* → *bootstrap_pattern* → *runtime_pattern* | app boots; workers drain on SIGTERM |
| 5 | Task runner | SKILL `justfile-setup` | `just` recipes (dev / local-prod / prod / lint / test-all) run |
| 6 | Local infra + parallel test isolation | *local_port_allocation_pattern* + *parallel_test_isolation_pattern* | integration tests pass **in parallel**, no collisions |
| 7 | Scalability (opt-in, default-on for SaaS) | *worker_pattern* + the shared task-contracts crate (`rust-workspace-setup`) | worker boots and consumes a test task |
| 8 | Day-1 cross-cutting decisions (ADRs) | *frontend_api_type_mirroring_pattern* (if vue+backend); port allocation (phase 6) | each decision recorded as an ADR in `docs/decisions/` |
| 9 | Navigation + docs | *claude_md_pattern* + *docs_artifact_layout_pattern* + *repo_root_files_pattern* | root + per-component `CLAUDE.md` and `docs/` trees exist; root files present |
| 10 | Automation gates | SKILL `agent-hooks-setup` + `ci-setup`; *dependency_audit_pattern* | hooks fire locally; CI is green on a trial PR; audit command runs |
| 11 | Continuous practices (wire in, not one-shot) | SKILL `rust-testing` / `python-testing`, `*-code-style`, `rust-design-principles` / `rust-design-idioms`, `rest-api-design`, `reconcile-docs` | referenced by `CLAUDE.md`, enforced by phase-10 hooks + CI |
| 12 | Final verification sweep | — | **every** gate green together (see Quick Reference) |

Pattern docs live under `../../patterns/`; e.g. `composition_pattern` is
`../../patterns/project_structure/composition_pattern.md`, the lifecycle ones are
in `../../patterns/lifecycle/`, and the rest under `../../patterns/{documentation,
decisions,testing,automation,scalability}/`.

### Why this order

Toolchain/workspace (1) gives crates a home before you scaffold them (2). The
skeleton must exist before its invariant gate (3) can guard it. Wiring (4) needs
the components. The task runner (5) is what every later phase and CI invokes.
Test isolation (6) depends on port allocation. The worker (7) reuses the wiring
patterns from (4) and the shared crate from (1). Docs and navigation (9) describe
what now exists. Automation (10) makes all prior gates *blocking*. Continuous
practices (11) are wired into those gates. The final sweep (12) runs everything
at once.

## Stack Matrix

Which phases apply to which components (✓ = applies, — = skip):

| Phase | Rust backend | Python backend | Vue frontend | Worker |
|-------|:---:|:---:|:---:|:---:|
| 1 workspace/toolchain | ✓ | ✓ (uv) | ✓ (node) | ✓ (rust) |
| 2 skeleton | ✓ hexagonal | ✓ DDD | ✓ feature-arch | ✓ hexagonal |
| 3 invariant gate | ✓ structure-test | ✓ import-linter | ✓ eslint | ✓ structure-test |
| 4 wiring/lifecycle | ✓ | ✓ | — | ✓ |
| 6 test isolation | ✓ | ✓ | partial | ✓ |
| 7 worker | — | — | — | ✓ |
| 8 type-mirroring ADR | (provider) | (provider) | ✓ (consumer) | — |
| 9 docs + CLAUDE.md | ✓ | ✓ | ✓ | ✓ |
| 10 hooks/CI/audit | ✓ | ✓ | ✓ | ✓ |

A **combination** monorepo runs the per-component phases once per component
directory; the root-level phases (5 task runner, 9 root docs, 10 CI/hooks) run
once at the root and fan in.

## Quick Reference — Final Verification Sweep (phase 12)

The foundation is live only when **all** of these pass together:

- [ ] every component builds (`cargo build`, `uv sync`/build, web build)
- [ ] architecture gates pass **and** fail on a planted violation (structure test / `lint-imports` / eslint)
- [ ] `rustfmt --check`, `clippy -D warnings`, type checks clean
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
- **Hardcoded ports / shared test DB.** Skipping phase 6 kills parallel-worktree
  productivity — the exact thing the setup is meant to enable.

## What This Skill Orchestrates (index)

**Setup skills (executable):** `rust-workspace-setup`, `rust-project-setup`,
`rust-architecture-test-setup`, `python-import-linter-setup`,
`frontend-vue-eslint-setup`, `justfile-setup`, `ci-setup`, `agent-hooks-setup`.

**Architecture/knowledge skills:** `rust-hexagonal-architecture`,
`rust-project-structure`, `python-ddd`, `frontend-vue-development`,
`rust-design-principles`, `rust-design-idioms`, `rest-api-design`,
`rust-testing`, `python-testing`, `rust-code-style`, `python-code-style`,
`frontend-vue-code-style`, `reconcile-docs`.

**Patterns (read the doc):** project_structure/`composition_pattern`;
lifecycle/`bootstrap_pattern`, `runtime_pattern`; scalability/`worker_pattern`;
testing/`parallel_test_isolation_pattern`;
decisions/`local_port_allocation_pattern`, `frontend_api_type_mirroring_pattern`;
documentation/`claude_md_pattern`, `docs_artifact_layout_pattern`,
`repo_root_files_pattern`; automation/`dependency_audit_pattern`.

**Continuous guards (installed in phase 10):** `rust-structure-and-style-guard`,
`vue-structure-and-style-guard`, `python-structure-and-style-guard` — dispatched
by the agent hooks so drift is caught on every commit, including in parallel
worktrees.
