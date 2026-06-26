---
name: claude-md-pattern
description: >-
  Use when bootstrapping or maintaining CLAUDE.md files in a monorepo — when an
  agent keeps editing the wrong component, when a parallel worktree agent asks
  the wrong questions, when the root CLAUDE.md has grown into an architecture
  manual, when a component CLAUDE.md is missing and agents fall back to guessing
  project layout, or when a new monorepo component is added and needs its own
  navigation context.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.1"
---

# CLAUDE.md Hierarchy Pattern

## Purpose

A CLAUDE.md file is the first thing an agent reads when it enters a directory.
In a monorepo, a single file at the root cannot serve all agents equally — a
Rust backend agent and a Vue frontend agent have almost nothing in common. At
the same time, a component-level file that duplicates the root or tries to
document everything grows too large and drifts out of sync.

**In one line:** the root CLAUDE.md is the monorepo map and global rules; each
component CLAUDE.md is that component's own structure, commands, and guard
rails — nothing else.

This is the same separation-of-concerns principle applied to documentation:
each file has exactly one audience and one job.

**Why it matters for parallel agents:** When multiple worktree agents run
simultaneously on different components, each agent reads only the CLAUDE.md for
its own subtree. If that file is correct and lean, the agent stays oriented,
uses the right commands, applies the right skills, and never mistakes a backend
rule for a frontend one. A missing or bloated CLAUDE.md is the most common
cause of an agent editing the wrong layer, using the wrong build command, or
inventing architectural conventions that conflict with the project's actual
patterns.

> **Core principle (separation of concerns / single responsibility):** the root
> file owns the monorepo map and cross-cutting rules; each component file owns
> that component only. Never duplicate content across levels, and never let
> either file grow into a manual — link to docs/ instead.

## When to Apply

Apply whenever:

- A new monorepo component directory is created and needs agent orientation.
- An existing CLAUDE.md has grown beyond one screenful of dense prose.
- Agents are misapplying rules from one component to another.
- Parallel worktree agents keep asking duplicate questions about project layout.
- A component is added or renamed and the root file's directory map is stale.
- Architecture skills (rust-hexagonal-architecture, python-ddd,
  frontend-vue-development) have been adopted and the component CLAUDE.md does
  not reference them yet.

**When NOT to apply:** a single-package repository with no components. One root
CLAUDE.md is correct there; creating sub-level files for a flat repo adds
indirection without benefit.

## The Two Levels

### Root CLAUDE.md — the monorepo map

**Audience:** any agent that starts at the repo root without knowing where to
go.

**Single responsibility:** tell agents where everything lives and where to run
every category of command. No architecture prose — that belongs in docs/ and
the component CLAUDE.md files.

Contents:

1. **Component directory table** — one row per component with a one-sentence
   role description. An agent should be able to read this table and immediately
   know which directory to enter.
2. **STOP / where to run commands** — the most important section. Monorepos
   have subtle command scoping (workspace-root vs. per-crate `cargo run`,
   per-package `npm`, cwd-relative env loading). Agents guess wrong here
   constantly; make it explicit with a table.
3. **Global developer entrypoints** — the short list of cross-cutting commands
   (a task runner like `just`, top-level CI recipes). Keep it to the commands
   that span more than one component.
4. **Fast navigation** — four to eight bullet points pointing to the key docs
   that do not live under any single component (ADRs, architecture vision,
   browser-testing guides). These are the links an agent follows when it needs
   context beyond the map.
5. **Where plans, specs, and scratch go** — a single table covering the
   `docs/` layout. Agents need to know where to write; if this is missing they
   invent their own locations and create waste.
6. **Repo map** — a minimal listing of every component directory and its key
   subdirectories. Enough to navigate; not enough to be a full directory dump.
7. **Global working rules** — a short numbered list of cross-cutting rules that
   apply to every agent in every component (no speculative code, verify before
   claiming, SRP, preserve scope). Keep this to ten rules or fewer.

Token discipline: the root file loads into every agent context on every
invocation. Each sentence costs tokens. If a rule applies only to one
component, it belongs in that component's CLAUDE.md.

### Component CLAUDE.md — the component contract

**Audience:** an agent that has entered this directory and needs to work on
this component.

**Single responsibility:** describe this component's structure, working rules,
applicable skills, and key commands. Nothing about sibling components.

Contents:

1. **One-line role** — what this component owns in plain English.
2. **Repo map** — a code-fence directory tree showing every significant
   directory and file with a brief label. An agent should be able to pick the
   right file from this tree without reading source. Aim for one screenful.
3. **Runtime modes** — three rows: local dev/testing, local deployed stack,
   production image. Agents need this to start the right thing without guessing.
4. **Working rules** — grouped by concern (architecture, conventions, testing,
   commands). Keep each rule actionable: "never import infrastructure from
   application" beats "keep layers clean."
5. **Architecture pointer** — the `IMPORTANT:` line naming the applicable skill
   (`rust-hexagonal-architecture`, `python-ddd`, `frontend-vue-development`)
   and the docs-level guidelines file it should read before touching code.
6. **Commands** — the exact command strings for build, test, lint, format, and
   run — both from inside the component directory and from the repo root. Agents
   copy-paste these; ambiguity here causes broken runs.
7. **Quality gate** — what must pass before handing work back (lint, format,
   type check). Name the command explicitly so an agent can run it without
   reasoning about what "clean" means.

## Worked Templates

The three templates below are distilled from real production CLAUDE.md files.
Copy the skeleton, replace the angle-bracket placeholders with your values, and
delete sections that do not apply. Keep each file lean — if a section would
require more than five lines of prose, it belongs in docs/.

---

### Template A — Root CLAUDE.md

```markdown
# <Product Name> Monorepo

This repository is split by runtime responsibility:

- `<component-a>/` is the <role, e.g. "Rust backend and current production service">.
- `<component-b>/` is the <role, e.g. "Vue 3 + Vite frontend">.
- `<component-c>/` is the <role, e.g. "Rust worker runtime for async task execution">.
- `crates/<shared-crate>/` is the <role, e.g. "shared wire-contract crate consumed by core and worker">.

## STOP — Where to run commands

**The repository root is a Cargo workspace** (members: `<component-a>`, `<component-c>`, `crates/<shared-crate>`).

- Rust build/test/lint: run from the repo root with `-p` — `cargo build -p <crate-name>`, `cargo test -p <crate-name>`, `cargo fmt --all`.
- Rust *run* targets stay per-crate: `cd <component-a> && cargo run` (env loading is cwd-relative).
- Node / Vue: run from `<component-b>/`.
- Docker Compose for the test stack: run from `<component-a>/docker/`.
- Cross-cutting flows: use `just` recipes from the repo root.

## Fast Navigation

- Architecture and future direction: `<component-a>/docs/`.
- Frontend direction: `<component-a>/docs/decisions/<adr-frontend>.md`.
- Root-level developer entrypoints: `justfile`.
- Manual testing guide: `docs/guidelines/browser-testing.md`.

## Where plans, specs, and scratch go

All design/plan/scratch artifacts live under the repo-root `docs/` tree.

| Path | Tracked? | Put here |
| ---- | -------- | -------- |
| `docs/plans/` | committed | durable implementation plans |
| `docs/decisions/` | committed | repo-level ADRs (the "why") |
| `docs/scratches/` | gitignored | throwaway notes |

## Repo Map

### `<component-a>/`
- `src/domain/` business entities, value objects, repository traits
- `src/application/` use cases and orchestration services
- `src/infrastructure/` API, database, gateways, runtime wiring
- `docs/` ADRs, runbooks, architecture, future plans

### `<component-b>/`
- `src/app/` app bootstrap and router wiring
- `src/features/` feature modules (page, components, composables, stores, API, types)
- `src/shared/` design system, API client, cross-cutting composables

### `<component-c>/`
- `src/application/` task-type handlers and generic execution machinery
- `src/infrastructure/` broker, gRPC, and config adapters

### `crates/`
- `<shared-crate>/` <one-line role>

## General Working Rules

1. Don't assume. Don't hide confusion. Surface trade-offs.
2. Minimum surgical code that solves the actual problem. Nothing speculative.
3. Always discuss important design decisions with the operator.
4. The foundation of good code is SRP (Single Responsibility Principle).
5. Verify before claiming. Never say something is done, fixed, or passing without fresh evidence.
6. Preserve exact scope. Touch only what you must.
7. Never invent new patterns when existing project patterns already cover the problem.
8. Leave touched code cleaner than you found it; do not broaden this into unrelated refactors.
```

---

### Template B — Rust Backend Component CLAUDE.md

```markdown
# <Product Name> <Component Name>

<One sentence: what this component owns — e.g. "Rust backend for the <Product> platform.">

This package owns: <HTTP API, auth, scheduling, persistence, …>.

## Repo Map

```text
src/
├── domain/                  # Business entities, value objects, repository traits
│   └── <concept>/           # One folder per domain concept
│       ├── mod.rs or <concept>.rs
│       └── repository.rs    # Repository trait (port)
│
├── application/             # Use cases and orchestration services
│   └── <concept>/           # One folder per use-case grouping
│
├── composition.rs           # Composition root — the ONE place that names concrete adapters
├── composition/
│   └── builders.rs          # Concern-grouped build_* service-graph helpers
│
└── infrastructure/          # Adapters and runtime wiring
    ├── api/                 # HTTP handlers, routes, DTOs
    ├── database/            # Repository implementations, migrations
    ├── config/              # Env config loading
    └── runtime/             # Background schedulers and sweepers

tests/
├── common/                  # Shared builders, fixtures, helpers
├── unit/                    # Pure domain/application tests
├── integration/             # Adapter tests against real infrastructure
└── e2e/                     # Full API flows

docker/
├── Dockerfile               # Production image
├── docker-compose.yaml      # Local test dependencies
└── docker-compose.local.yaml # Local deployed stack

migrations/                  # Database migrations
docs/                        # ADRs, runbooks, architecture, future plans
```

## Runtime Modes

- Local testing: `docker/docker-compose.yaml`
- Local deployment: `docker/docker-compose.local.yaml`
- Production image: `docker/Dockerfile`

## Tech Stack

Rust (pinned in `../rust-toolchain.toml`) · Tokio · <HTTP framework> · <DB> · <ORM>

## Working Rules

### Architecture

IMPORTANT: Never break hexagonal architecture. Before writing or modifying any
code, apply the `rust-hexagonal-architecture` skill to verify that dependency
flow and layer responsibilities are respected.

IMPORTANT: When adding a new concept or restructuring an existing one, follow
`docs/guidelines/project_structure.md` — it is the authoritative guideline for
module and folder layout.

- Keep dependencies pointing inward: `domain → application → infrastructure → composition`.
- Domain code must not depend on the HTTP framework, ORM, or transport DTOs.
- `application/` must never import from `crate::infrastructure`. Services depend
  only on ports (`Arc<dyn Trait>`), never concrete adapters.
- The composition root is the one place permitted to name concrete adapters and
  wire them into ports. Neither `application` nor `infrastructure` may reference
  `composition`.
- Ports are traits in `domain/` or `application/`; infrastructure implements them.
- Handlers translate HTTP requests to use cases; they must not own business rules.

### Code Conventions

- Never break SRP. Ask the operator before breaking it.
- Do not introduce `anyhow` or `thiserror`. Use explicit error enums scoped to
  the operation.
- Prefer newtypes and parse-don't-validate for domain values.
- Use `module_name.rs`, not `mod.rs`.

### Testing

- Keep tests in `tests/`, not inline with source.
- Consult `docs/knowledge-base/` for testing patterns before writing a new test.
- Use unit tests for pure logic, integration tests for adapters, e2e for flows.

### Commands

- Build/test/lint from repo root: `cargo build|test|clippy -p <crate-name>`
- Run from component dir: `cd <component>/ && cargo run` (env loading is cwd-relative)
- From repo root: `just dev-<component>-test`, `just dev-test-stack-up`, `just local-<component>-deploy-up`
```

---

### Template C — Vue Frontend Component CLAUDE.md

```markdown
# <Product Name> Web

Vue 3 frontend for the <Product> dashboard.

This package owns the browser UI: authenticated dashboard, workspace-scoped
resource pages, and <other feature surfaces>.

## Repo Map

```text
src/
├── app/                     # App bootstrap and router wiring
│   ├── App.vue
│   └── router.ts
│
├── features/                # Feature modules — one folder per domain feature
│   └── <feature>/
│       ├── <Feature>Page.vue    # Route-level page component
│       ├── components/          # Feature-scoped presentational components
│       ├── composables/         # Feature-scoped composition functions
│       ├── api/                 # Feature-scoped API calls
│       ├── stores/              # Feature-scoped Pinia stores
│       ├── types/               # Feature-scoped TypeScript types
│       └── index.ts             # Public barrel export
│
├── shared/
│   ├── api/                 # HTTP client setup, interceptors, error handling
│   ├── components/          # Design system primitives (BaseButton, BaseModal)
│   ├── composables/         # App-wide composition functions
│   ├── domains/             # Cross-feature business concepts, no routes
│   ├── layouts/             # Layout shells
│   ├── stores/              # Cross-cutting Pinia stores (auth, theme)
│   ├── styles/              # Global CSS, design tokens, theme variables
│   ├── types/               # Shared TypeScript types
│   └── utils/               # Pure helper functions
│
└── main.ts                  # Vue app entrypoint

docker/
├── Dockerfile               # Production image: build with Vite, serve via Nginx
└── docker-compose.local.yaml # Local deployed stack
```

## Runtime Modes

- Local testing: `npm run dev` via Vite with hot reload
- Local deployment: `docker/docker-compose.local.yaml`
- Production image: `docker/Dockerfile`

## Working Rules

### Structure

IMPORTANT: When writing or reviewing any Vue, composable, store, or module
code, apply the `frontend-vue-development` skill and follow
`frontend-vue-code-style`.

- Keep `app/` limited to bootstrap, routing, and global plugin wiring.
- Each feature owns its page, components, composables, stores, API calls, and
  types. Features never import from other features.
- Shared code is lifted to the correct shared layer: cross-feature business
  concepts go to `shared/domains/<domain>/`; design-system primitives go to
  `shared/components/`; foundation utilities go to flat `shared/` folders.
- These boundaries are lint-enforced by the custom rules in `eslint.config.js`
  (one-way: `features/` → `shared/domains/` → `shared/` foundation). Do not
  add new violations.

### Vue Conventions

- Use Composition API with TypeScript.
- Keep data flow one-way: props down, events up.
- Prefer container/presenter separation when a page grows beyond simple rendering.
- Keep API helpers outside components; components must not hardcode fetch logic.

### Commands

- Inside `<component-b>/`: `npm run dev`, `npm run build`, `npm run check`,
  `npm run lint`, `npm run lint:fix`, `npm run format`, `npm run format:check`
- From repo root: `just dev-web-up`, `just dev-web-test`, `just web-check`,
  `just local-web-deploy-up`

### Code Conventions

- Never break SRP. Ask the operator before breaking it.

### Quality Gate

After any code change, run lint and type check before handing work back:
- `npm run lint` and `npm run format:check` inside `<component-b>/`
- From repo root: `just web-check`

If either check fails, fix the issues and rerun before marking work complete.

## API Boundary

- Vite dev server proxies `/api/*` to the backend's local address.
- Production Nginx proxies `/api/*` to the backend container over the shared
  Docker network.
- Treat the backend as the source of truth for domain state and contracts.
```

## Quick Reference — Invariants

- **Root file = navigation and global rules only.** Architecture prose belongs
  in docs/; component rules belong in the component's CLAUDE.md.
- **Component file = that component only.** Never describe sibling components;
  never duplicate global rules.
- **Both files must stay lean.** Every line costs tokens on every agent
  invocation. If a section requires more than five lines of prose, link to a
  docs/ file instead.
- **Commands must be exact.** Copy-paste ready: the right flags, the right
  working directory, both the component-local form and the repo-root form.
- **Architecture skills must be named explicitly.** An agent will not apply a
  skill it is not told to apply. Each component CLAUDE.md must name its skill
  (rust-hexagonal-architecture, python-ddd, frontend-vue-development) with an
  IMPORTANT: prefix so no agent skips it.
- **The root repo map must stay in sync with the directory tree.** A stale map
  is worse than no map — agents will navigate to the wrong place confidently.
  Use the reconcile-docs skill after adding or renaming components.

## Anti-Patterns to Avoid

- **Dumping architecture into CLAUDE.md instead of linking docs/.** A
  CLAUDE.md that reproduces hexagonal layer rules in full prose, lists every
  ADR inline, or explains domain-model shape is too large to be useful. Link to
  the relevant docs/ file and keep the rule actionable.
- **One monolithic root CLAUDE.md that tries to cover all components.** The
  file grows with every component addition, loads into every agent regardless
  of which component it is working on, and drifts because the team only edits
  it when something breaks.
- **Forgetting the commands section.** The most common agent mistake after
  "wrong layer" is "wrong command directory." Cwd-relative env loading,
  workspace-vs-per-crate Cargo targets, and different npm script names are all
  sharp edges. Document them explicitly.
- **Component file that duplicates global rules.** If a rule appears in both
  the root and a component file, it will drift. Keep each rule in exactly one
  place. Global rules live in the root; component-specific rules live in the
  component.
- **Missing architecture skill pointer.** A component CLAUDE.md that says
  "follow hexagonal architecture" without naming the skill and the docs file
  relies on the agent already knowing the pattern. Name it — `IMPORTANT: apply
  the rust-hexagonal-architecture skill before writing any code`.
- **Stale repo map.** A root CLAUDE.md that still lists a deleted component or
  does not list a new one trains agents to look in the wrong place. Add a
  reconcile-docs run to the definition of done for any component addition or
  rename.

## Relationship to Other Patterns and Skills

- **[docs_artifact_layout_pattern.md](docs_artifact_layout_pattern.md)** —
  governs the `docs/` tree that CLAUDE.md files link into. The root CLAUDE.md
  should have a "Where plans, specs, and scratch go" section that maps to the
  layout this pattern defines.
- **[repo_root_files_pattern.md](repo_root_files_pattern.md)** — covers the
  other files that live alongside CLAUDE.md at the repo root (justfile,
  rust-toolchain.toml, .github/, etc.). The root CLAUDE.md references these
  without needing to define their shape.
- **reconcile-docs skill** — run after any code change that adds, renames, or
  removes a component, moves a docs/ file, or changes a command. Keeps both
  levels of CLAUDE.md current so the map does not drift from the code.
- **rust-hexagonal-architecture skill** — the architecture skill a Rust backend
  component CLAUDE.md must reference. Name it explicitly with an IMPORTANT:
  marker so agents always load it before touching code.
- **python-ddd skill** — the equivalent for Python backend components. Same
  placement rule: named explicitly in the component CLAUDE.md.
- **frontend-vue-development skill** — the equivalent for Vue frontend
  components. Named explicitly in the component CLAUDE.md alongside
  frontend-vue-code-style.
