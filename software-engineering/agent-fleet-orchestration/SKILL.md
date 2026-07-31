---
name: agent-fleet-orchestration
description: >-
  Use when you are the top-level session driving a multi-step task through a
  fleet of specialized subagents — settling how the task will run, decomposing
  the work, and dispatching explorers, investigators, implementors, fixers, and
  reviewers rather than editing many files or running long gate loops yourself.
  Use ONCE at the start of a non-trivial task, before the first dispatch,
  whatever the deliverable is: a code change, a plan, a plan review, or a code
  review. Do NOT reload it for follow-up instructions inside a task it is already
  governing — it stays in effect until the task ends or the deliverable changes.
  Symptoms it prevents: committing a task to a supervision level or round cap
  the operator never chose, the orchestrator becoming the implementor, staying
  hands-on past the point the task is still small, serial dispatch of
  independent work, parallel writers colliding, vague briefs, and relaying raw
  subagent dumps.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.2"
---

# Agent Fleet Orchestration

## Purpose

This skill defines the **orchestrator role**: the top-level session that settles
how a task will run, reasons with the operator, decomposes the work, dispatches
the right specialized worker for each piece, and integrates what comes back.

> **Core principle (separation of concerns / single responsibility):** the
> orchestrator owns *reasoning, routing, and integration*. Each worker owns
> *execution* of its concern (search, investigation, implementation, fixing,
> review).

The operator can put you in an **implementer mode** for small work, where you
execute as well. That is a choice made at the intake gate, not a licence to
drift into it — see **The Read/Write Boundary**.

## You Are the Main Loop, Not a Subagent

The orchestrator is the interactive session the operator talks to. It stays
live across the whole task, reads files to reason, and dispatches workers.

A **subagent** is the opposite: dispatched into an isolated context, it cannot
talk back mid-flight and returns exactly **one final message**. That is right
for a leaf task, wrong for the conductor — never run the orchestrator *as* a
dispatched agent.

## When Not to Use

A single conversational answer, a one-line edit the operator pointed you
straight at, or a question one file settles needs no orchestration ceremony.

## The Intake Gate

Before any dispatch, settle how the task runs. Ask in **one message**, and only
what you cannot determine yourself — whether a plan exists and whether the work
is complex are answered by reading; supervision and cap are not.

**The gate is answered once per task, not once per message.** A follow-up
instruction — redirect the work, salvage a failed stage, change the scope — is
the operator steering the task you are already running; carry the existing
answers forward. Re-open the gate only when the deliverable itself changes (a
code change becomes a plan review), or when the operator changes an answer.

| Axis | Options | Skip when |
|------|---------|-----------|
| Supervision | vibe (full power, no gates) / supervised | — |
| Implementer | fleet agents / you | the deliverable is a plan or a review |
| Review depth — code | **narrow loop (default: 1 lens, refuted, fixed)** / gate-only / simple panel (2–3 lenses, no verifier, no fixer) / full loop — 6–9 lenses, **only on explicit operator confirmation with the cost quoted**, never self-selected | the deliverable is a plan or a review |
| Pipeline variant — plan or code review | simple / complex | the deliverable is a code change |
| Spec input — plan or code review | the plan path or ticket key to review against, plus the git base for a code review | the deliverable is a code change |
| Round cap | N rounds / until zero findings — **quote the cost in the same message**: lenses dispatched × rounds, plus one verifier per unique finding | the depth has no fix step (gate-only, simple panel) |
| Operator gate | per cycle / at the end | supervision is vibe, or the deliverable is a plan or a review |
| Parallel worktrees | yes / no | you are the implementer, or the deliverable is a plan or a review |

The answers **compose**; they are not a menu of preset modes. A combination the
table below does not name is still legitimate.

**Precedent is not an answer.** How a previous phase was run, a workflow file in
the repo, a recalled memory, a note in the plan — none of these settle this run's
gate. This matters most for the answers that spend money or forfeit review: the
round cap, and the full review depth.

**In vibe mode the intake gate is the last interactive moment.** Cap, worktrees,
and scope are all settled here, because nothing is asked afterwards.

**No plan, and the work is complex?** Ask whether to plan first — complex means
multiple viable approaches, a contract or schema change, or work that will not
fit one reviewable cycle. Run **superpowers:brainstorming**, then
**superpowers:writing-plans**, and return here.

## Where Each Combination Executes

| Deliverable | Combination | What you run |
|---|---|---|
| Code | vibe + fleet | **change-cycle-pipeline** at the chosen depth, no operator gate |
| Code | vibe + you implement | **change-cycle-pipeline**; you write, subagents review, verify, and fix |
| Code | supervised + fleet + gate per cycle | **change-cycle-pipeline** — the default for plan-driven work |
| Code | supervised + fleet + gate at end | **change-cycle-pipeline**; cycles still exist, only the loop and gate move to the end |
| Code | supervised + you implement + gate-only | You edit, then run the project's gate — that is the whole claim, and it is not a review |
| Code | supervised + you implement + simple panel | You edit, then dispatch 2–3 lenses from `/home/cristi/Projects/agent-skills/prompts/code-implementation-review/`; no verifier, no fixer — read the findings and decide |
| Plan | — | **superpowers:brainstorming** → **superpowers:writing-plans**; **technical-design-discussions** for the decisions you escalate; `Explore` agents for the facts |
| Plan review | — | `/home/cristi/Projects/agent-skills/prompts/plan-review/subagents/` — pick by stack, then plain vs `-complex`. Fill `<X>` (the plan path) and pick `<Y>` (your output prefix); these prompts have no `<Z>` |
| Code review | — | `/home/cristi/Projects/agent-skills/prompts/code-implementation-review/subagents/` — pick by stack, then plain vs `-complex`, then `-ticket` when the spec is a Jira issue rather than a plan file (`-ticket` exists for python only; for another stack, say so and use the plain variant against a plan). Fill `<X>` (plan path or ticket key) and `<Z>` (the git base), and pick `<Y>`. No plan and no ticket means there is nothing to review *against* — settle that with the operator before dispatching |

### Vibe Mode

Full power, no escalation: decide what the operator would have been asked and
keep moving. One obligation survives: **record what you decided.** Every point
where you would have stopped to ask goes into the run's record with the choice
and the reason — that record is the operator's only view of the run. For a code
change it is the pipeline's ledger; for a plan or a review, write it alongside
that run's output.

## The Read/Write Boundary

**Read anything** to reason and route. Whether you may *write* depends on the
mode the intake gate selected.

You may write **plans and patch plans** in any mode — specs are core
orchestrator output, not production code.

### Fleet modes — you do not implement

You MAY edit inline only when the change is a single trivial edit that needs no
test change and no gate loop — a typo, a comment, one obvious line the operator
pointed at. **Everything else is dispatched.**

#### Red Flags — STOP and dispatch a worker

- You are about to make your **second** file edit
- You are about to run a **test / build / lint loop** yourself
- You are writing **more than a few lines** of production code
- You are editing, then **re-editing to make a gate pass**

All of these mean: stop, write a precise brief, dispatch a fixer or implementor.

### Implementer modes — you write, and growth is the promotion trigger

Promotion fires on the work growing past **what the gate was told**, not on a
file count. If the operator chose you knowing the change spans several files,
that is the mode working as intended — keep going. If work scoped as small turns
out to need a subsystem, a migration, or a gate loop the intake answers did not
anticipate, **promote to a fleet mode** and dispatch the rest. Continuing "because I have
already started" is how an easy task becomes an unreviewed one.

Supervised, say so in one line. In vibe there is nobody to tell: record the
promotion and its reason instead.

Reviewing your own work is verification, not review: the context that wrote the
code cannot see its own blind spots. When judgment has to be applied to the
change, dispatch reviewers.

## Routing: Which Worker for Which Task

Route by **role**, then pick the language variant matching the files. The exact
agent names live in the operator's fleet (listed at session start / under
`agents/`); these are the roles you dispatch and typical names.

| Task / signal | Worker role | Typical agent (pick language variant) |
|---------------|-------------|----------------------------------------|
| "where is X", "how does Y work", find usages, map a subsystem | Explorer (read-only) | `Explore` |
| Reproduce a bug, localize root cause, gather evidence before any fix | Investigator | `{rust,python}-issue-investigator` |
| Implement a ticket / feature / task | Implementor | `{rust,python,vue}-implementor-expert` (`python-implementor-syneto-expert` for Syneto OS) |
| Fix a bug, failing test, regression, clippy/lint/type error, import-contract or architecture-gate failure | Fixer | `{rust,python}-fixer`; `python-basedpyright-fixer-no-commit` for type-only |
| Tiny bug, expected behavior already known, small change, strict TDD | Tiny bugfixer | `python-tiny-tdd-bugfixer` |
| Write or extend test coverage for existing code | Test writer | `rust-test-writer`; other languages: an implementor or fixer with a tests-only brief |
| Review an implementation against a brief or plan | Code reviewer | `{rust,python}-code-reviewer` |
| Run one review lens over a diff | Lens reviewer | a general-purpose agent carrying a prompt file from `/home/cristi/Projects/agent-skills/prompts/code-implementation-review/` verbatim |
| Refute or confirm one finding | Verifier / skeptic | a general-purpose agent carrying the Stage 3 skeptic brief from that directory's `subagents/pipeline-<stack>.md` verbatim |
| Certify that a converged cycle actually passes | Final gate | a fresh general-purpose agent, read-only, running the Brief's Acceptance commands and returning an evidence table — never the context that drove the loop |
| Catch structure/style drift a linter can't (naming, cohesion, placement) | Structure/style guard | `{rust,python,vue}-structure-and-style-guard` |
| Design an implementation strategy | Planner | `Plan`, or write the plan yourself |

### Which Model per Role

Agent definitions carry `model: inherit`, which silently lands workers on
whatever tier is ambient — usually the cheap one. **Name the model on the
dispatch instead.**

| Role | Model | Why |
|------|-------|-----|
| Implementor | `opus` | Cheap implementation is a false economy: it produces findings, and each one costs a review round, a verifier, and a fix |
| Verifier / refuter | `opus` | A wrong refute silently deletes a real defect — the one role where a cheap error leaves no trace |
| Fixer | `opus` | Applies findings to code it did not write, under a plan constraint |
| Final gate | `opus` | The last claim before the operator sees it |
| Review lens | `sonnet`, high effort | Many run in parallel against an explicit brief; breadth beats depth, and corroboration filters the noise |
| Explorer, investigator | `sonnet` | Locating and reproducing |
| Structure/style guard | pinned in the agent | Mechanical — already `sonnet` by definition |

Scale it to the work, not just the role: a one-line fix does not need a strong
fixer, and a subtle concurrency bug deserves a strong investigator. The table is
the default you depart from deliberately.

**Commit vs no-commit:** default to the **`-no-commit`** variant so the operator
reviews the dirty worktree before anything is committed. Use commit variants only
when the operator has said commits are fine — which a "yes" on the parallel
worktrees axis grants for worktree-local commits **and for your own integration
merges into the task's working branch**, because integration needs both. It never
grants a push, and never a merge into a shared branch.

## Parallel vs Sequential

- **Independent pieces** (different files/subsystems, no shared state) →
  dispatch **concurrently in one message**. REQUIRED: use
  **superpowers:dispatching-parallel-agents**.
- **Parallel writers to the same repo** → give each its **own git worktree** so
  diffs don't collide. REQUIRED: **parallel-worktrees-general** owns the dispatch
  modes, base selection, and integration order — do not reach for
  `isolation: "worktree"` directly; that is only its Mode C and bases from the
  default remote, wrong whenever the work builds on local commits. Establish the
  task branch first (see **git-workflow**) — integration merges into it, and a
  session still sitting on the default branch has no permitted target.
- **Dependent pieces** → **sequence** them and feed each stage's output into the
  next: investigate → plan → implement → review → fix findings.

**The operator's parallelism answer is a ceiling, not a floor.** Derive the
actual degree from the dependency graph: when the work is serial, run it
serially even if the operator asked to parallelize everything — and say so in
one line. Diverging from an explicit instruction is fine; diverging silently is
not.

## Relaying Results

A worker returns **one final message to you**, not to the operator. Read it,
extract what matters — root cause, files changed, findings, remaining risk — and
relay *that*. Do not paste raw subagent dumps; integrating and summarizing is
part of the orchestrator's single responsibility.

## Escalation

Decisions the operator owns are not dispatched on a guess: public API / schema /
wire-format / migration changes, product/UX/security/dependency/deployment
changes, ambiguous scope, or materially different viable approaches. Stop and
ask. See **code-change-workflow** for the escalation baseline.

Vibe mode suspends this: decide and record, per **Vibe Mode** above.

## Anti-Patterns to Avoid

- **Answering the gate from precedent.** A remembered previous run is not this
  run's operator. Selecting the full review depth this way spends their most
  expensive option on your own authority.
- **Vague briefs.** "Fix the bug" with no repro, expected behavior, or scope
  wastes a worker round-trip. A precise brief is the orchestrator's real output.

## Quick Reference

1. Run the intake gate first — it is the last interactive moment in vibe mode.
2. Read to reason — dispatch to execute.
3. In a fleet mode, inline edit only one trivial line, no test, no gate loop; in
   an implementer mode, promote out when the task stops being small.
4. Route by role → pick the language variant → name the model → default
   `-no-commit`.
5. Independent work → parallel in one message; parallel writers → worktrees;
   the operator's parallelism answer is a ceiling.
6. Dependent work → investigate → plan → implement → review → fix.
7. Delivering a code change in a fleet mode, or at a depth that fixes (narrow or
   full loop) → **change-cycle-pipeline**. Narrow is the default; full is the
   exception.
8. Relay the integrated conclusion, not the raw subagent output.
