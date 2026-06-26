---
name: docs-artifact-layout-pattern
description: >-
  Use when a monorepo accumulates docs, ADRs, plans, and agent artifacts in
  inconsistent locations — scattered across .plans/, superpowers/, ephemeral_plans/,
  or similar ad-hoc directories — and you need a single, navigable, two-level
  layout that separates whole-product artifacts from component-specific ones and
  enforces a clean git-lifecycle boundary between durable design records and
  ephemeral working state.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.1"
---

# Docs Artifact Layout Pattern

## Purpose

A monorepo has two distinct scopes of documentation: artifacts that concern the
**whole product** (cross-cutting ADRs, product-wide plans, shared guidelines)
and artifacts that concern **one component** (the backend's API reference, the
frontend's feature ADRs, a worker's runbook). When both scopes land in a single
flat directory — or scatter across ad-hoc paths like `.plans/`, `superpowers/`,
`ephemeral_plans/` — contributors and agents cannot answer the basic question
*"where does this kind of file go?"* without reading history.

**In one line:** this pattern gives every artifact a predictable address by
applying the same principle twice — separation of concerns — once across the
repo (root docs vs. component docs) and once within each docs tree (each
subdirectory holds exactly one kind of artifact).

> **Core principle (separation of concerns / single responsibility):** the root
> `docs/` owns *cross-cutting, whole-product* artifacts. Each component's own
> `docs/` owns *that component's* artifacts. Nothing crosses the line: a
> component's ADR never lives at the root, and a whole-product gap never lives
> under `core/`. One scope, one owner, one location.

---

## The Two-Level Split

### Level 1 — Root `docs/` (cross-cutting, whole-product)

Holds every artifact whose scope is the product as a whole or that crosses
component boundaries:

| Subdirectory | What it holds |
|---|---|
| `decisions/` | Product-level ADRs — durable "why" records that span more than one component (e.g. the artifact-layout ADR itself, connectivity health model, port allocation strategy). Tracked in git. |
| `plans/` | Durable implementation plans worth keeping in history — promoted from scratch after a feature ships. Tracked in git. |
| `gaps/` | Known shortfalls or deferred work that spans the whole product or has no single component owner. Tracked in git. |
| `guidelines/` | Cross-cutting engineering guidelines not owned by one component. Tracked in git. |
| `knowledge-base/` | Shared reference material — how-tos, verified solutions — relevant across components. Tracked in git. |
| `prompts/` | Reusable prompt templates for agent tasks at the product level. Tracked in git. |
| `superpowers/` | **Gitignored.** Ephemeral working area for the superpowers plugin (brainstorming specs, `sdd/` state). Hardcoded default path for the `brainstorming` skill — no redirect needed. |
| `scratches/` | **Gitignored.** Freeform throwaway notes; never committed. |

The committed/ignored boundary is enforced by two `.gitignore` lines
(`docs/superpowers/`, `docs/scratches/`) rather than by a `.`-prefix
convention, making the split explicit and visible to `git status`.

### Level 2 — Per-component `docs/` (component-specific)

Each component directory (`core/`, `web/`, `worker/`, …) carries its own
`docs/` subtree. That subtree holds only what is **specific to that component**;
it mirrors a consistent set of subdirectories across components so agents and
contributors can navigate by convention:

| Subdirectory | What it holds |
|---|---|
| `decisions/` | Component-scoped ADRs — design choices that only affect this component. |
| `api/` | API reference documents for this component's endpoints (request/response shapes, auth requirements, error codes). |
| `gaps/` | Deferred work or known shortfalls inside this component. |
| `guidelines/` | Component-specific engineering conventions (e.g. project structure rules, how to add a new source). |
| `qanda/` | Question-and-answer notes, exploratory write-ups, and clarifications that are not polished enough for guidelines. |
| `engineering-notes/` | Investigative notes, workflow walkthroughs, and deep-dives into non-obvious behaviors — more detailed and contextual than runbooks. |
| `runbooks/` | Operational playbooks — step-by-step instructions for recurring operational tasks (diagnosing flakiness, implementing a new connector, handling incidents). |
| `solutions/` | Documented solutions to specific past problems, for reference if the same situation recurs. |
| `knowledge-base/` | Component-local reference material (testing patterns, library usage notes). |
| `architecture.md` | Top-level architecture document for this component. A single file, not a subdirectory. |

Not every component needs every subdirectory; create them as needed.
The `api/` and `engineering-notes/` subdirectories are most common in backend
components; `qanda/` appears where exploratory investigation is needed;
`runbooks/` appears in any component with operational complexity.

---

## Why the Split Matters for Parallel Agents

When agents work in parallel worktrees, each agent works on one component.
A component's own `docs/` is fully self-contained: the agent writing a
backend gap document never touches `web/docs/`. The root `docs/` is the only
shared write target, and only for cross-cutting artifacts that genuinely belong
there. This containment eliminates write conflicts and makes each agent's scope
unambiguous from the directory structure alone.

---

## Worked Example — ironbox

The ironbox monorepo is the canonical reference implementation. The trees below
are the actual state.

### Root `docs/` tree

```
docs/
├── decisions/          # product-level ADRs (05 entries, e.g. connectivity health, port allocation, this layout)
├── gaps/               # product-wide deferred work (2 entries)
├── guidelines/         # cross-cutting guidelines (1 entry: browser-testing.md)
├── knowledge-base/     # shared how-tos (2 entries: restore-to-custom-location, web-to-core-flow)
├── prompts/            # reusable agent prompt templates
├── superpowers/        # gitignored — brainstorming plugin working area
└── scratches/          # gitignored — throwaway notes
```

### `core/docs/` — backend component

```
core/docs/
├── architecture.md
├── future-architecture.md
├── decisions/          # 34+ component ADRs (technology stack, backup/restore locks, …)
├── api/                # 14 API reference files (backups, connections, jobs, workspaces, …)
├── gaps/               # 25 deferred work items
├── guidelines/         # how_to_add_new_source.md, project_structure.md
├── qanda/              # draft-connectivity-and-proofs.md
├── engineering-notes/  # 14 investigative write-ups (storage plan wiring, quiesce compensation, …)
├── runbooks/           # 10 operational playbooks (N+1 patterns, e2e flakiness, graceful shutdown, …)
├── solutions/          # source_connectivity_live_probe.md
└── knowledge-base/     # unit-testing-patterns, e2e-testing-patterns, integration-testing-patterns
```

### `web/docs/` — frontend component

```
web/docs/
├── architecture.md
├── decisions/          # 6 frontend ADRs (feature-colocated structure, linting, form composition, …)
├── gaps/               # 6 known shortfalls (accessibility, duplicate literals, ui-modernity, …)
├── guidelines/         # project_structure.md
└── runbooks/           # auth-lost-on-vite-reload.md
```

### `worker/docs/` — worker component

```
worker/docs/
├── architecture.md
├── decisions/          # 001-grpc-library.md
├── guidelines/         # project_structure.md
└── knowledge-base/     # task-execution-pipeline.md
```

Notice that `worker/` is a smaller, simpler component: it has no `api/`,
no `engineering-notes/`, no `runbooks/` beyond what it needs. The layout
contracts to what is present — the subdirectory convention is a ceiling,
not a mandate.

---

## Enforcement: Three-Layer Stack

No filesystem mechanism forces an agent to use the right folder; agents are
instruction-followers. Enforcement is therefore layered:

| Layer | Mechanism | Strength | Covers |
|---|---|---|---|
| Mechanical | `plansDirectory` in `.claude/settings.json` pointing to `docs/plans/` | Hard — the tool obeys it | Native plan-mode files |
| Instructional | `CLAUDE.md` states the layout convention and links this pattern | Soft — every agent session loads it; superpowers honors "user preferences override" | Specs, superpowers plans, ad-hoc writes |
| Detective | Project structure test (deferred in ironbox) that fails if `.plans/`, `superpowers/`, `ephemeral_plans/` reappear at the repo root | Hard — fails `cargo test` | Drift: re-appearance of ad-hoc directories |

The instructional layer does the bulk of the work. The mechanical and detective
layers are the seatbelt.

The `superpowers/` naming at `docs/superpowers/` is intentional: the
`brainstorming` skill hardcodes `docs/superpowers/specs/` as its default output
path. Keeping the name means the skill's output lands correctly with zero
override. Only `plans` output is redirected.

---

## Invariants

- **Root `docs/` holds only cross-cutting artifacts.** A component-specific ADR
  that only affects one package never lives at the root.
- **Each component's `docs/` holds only that component's artifacts.** A backend
  runbook never lives in `web/docs/`.
- **Durable design intent is tracked; ephemeral working state is gitignored.**
  `docs/superpowers/` and `docs/scratches/` are gitignored by explicit
  `.gitignore` entries, not by `.`-prefix convention.
- **Plans have one home: `docs/plans/` (tracked).** All three plan producers —
  native plan mode, superpowers `writing-plans`, and hand-authored plans — point
  there. There is no `.plans/`, `ephemeral_plans/`, or `docs/superpowers/plans/`
  in parallel.
- **`architecture.md` is a file at the component docs root, not a subdirectory.**
  One flat file per component, not a nested tree.
- **Subdirectory names are consistent across components.** `decisions/`, `gaps/`,
  `guidelines/` always mean the same thing regardless of which component's
  `docs/` they appear in.
- **No single-letter names and no abbreviations** in file or directory names
  (use `qanda/` in full as `qanda`, not `qa`; `engineering-notes/`, not `engnotes`).

---

## Anti-Patterns to Avoid

- **Scatter at the repo root.** `.plans/`, `superpowers/`, `ephemeral_plans/`,
  `.scratches/` at the root are the exact problem this layout solves. If they
  reappear, the detective layer should catch them.
- **Committing ephemeral working state.** Brainstorming specs and scratch notes
  are not design records. If a spec is worth keeping, promote its essence into
  an ADR under `decisions/` or a plan under `plans/`.
- **Putting a component ADR at the root.** An ADR that only answers *"which gRPC
  library does `core` use?"* belongs in `core/docs/decisions/`, not
  `docs/decisions/`.
- **Putting a product-wide gap inside one component.** A gap whose fix requires
  changes across multiple components belongs at `docs/gaps/`, not buried in
  `core/docs/gaps/`.
- **Mixing runbooks and engineering-notes.** Runbooks are step-by-step
  operational instructions for a repeatable task. Engineering notes are
  investigative write-ups explaining *why* something works the way it does.
  They serve different readers and should not be merged.
- **Omitting `architecture.md`.** Every component should have a single
  `architecture.md` at its docs root. Without it, a new agent has no starting
  point for understanding the component.
- **Creating subdirectories for content that doesn't exist yet.** Add a
  subdirectory when the first file is ready to live there; an empty
  `runbooks/` directory adds noise without value.

---

## Quick Reference

```
<repo-root>/
├── docs/                        # whole-product artifacts
│   ├── decisions/               # product ADRs (tracked)
│   ├── plans/                   # durable implementation plans (tracked)
│   ├── gaps/                    # product-wide deferred work (tracked)
│   ├── guidelines/              # cross-cutting guidelines (tracked)
│   ├── knowledge-base/          # shared reference material (tracked)
│   ├── prompts/                 # agent prompt templates (tracked)
│   ├── superpowers/             # brainstorming plugin working area (gitignored)
│   └── scratches/               # throwaway notes (gitignored)
│
├── <component>/docs/            # per-component artifacts (repeat for each component)
│   ├── architecture.md          # component architecture (tracked)
│   ├── decisions/               # component ADRs (tracked)
│   ├── api/                     # API reference (tracked, backend components)
│   ├── gaps/                    # component-scoped deferred work (tracked)
│   ├── guidelines/              # component conventions (tracked)
│   ├── qanda/                   # exploratory Q&A notes (tracked)
│   ├── engineering-notes/       # investigative write-ups (tracked)
│   ├── runbooks/                # operational playbooks (tracked)
│   ├── solutions/               # documented past solutions (tracked)
│   └── knowledge-base/          # component-local reference (tracked)
```

---

## Relationship to Other Patterns and Skills

- **[local_port_allocation_pattern](../decisions/local_port_allocation_pattern.md)**
  and **[frontend_api_type_mirroring_pattern](../decisions/frontend_api_type_mirroring_pattern.md)**
  — examples of the kind of cross-cutting product ADR that belongs in the root
  `docs/decisions/`.
- **[claude_md_pattern](claude_md_pattern.md)** — a sibling pattern in this
  directory covering what belongs in `CLAUDE.md`; the instructional enforcement
  layer described above depends on `CLAUDE.md` containing the artifact-layout
  convention and a link to this pattern.
- **`reconcile-docs` skill** — use after any code change to decide whether the
  change invalidates an existing ADR, gap, or runbook. The two-level layout
  makes the scope of reconciliation explicit: a backend-only change only
  requires checking `core/docs/` plus `docs/` for cross-cutting impact.
