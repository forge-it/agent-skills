---
name: agent-fleet-orchestration
description: >-
  Use when you are the top-level session driving a multi-step task through a
  fleet of specialized subagents — settling how the task will run, decomposing
  the work, and dispatching explorers, investigators, implementors, fixers, and
  reviewers rather than editing many files or running long gate loops yourself.
  Use at the start of ANY non-trivial task, before the first dispatch, whatever
  the deliverable is: a code change, a plan, a plan review, or a code review.
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
> review). In a fleet mode, the urge to edit files and run gate loops yourself
> is a worker's job; hand it off.

The operator can put you in an **implementer mode** for small work, where you
execute as well. That is a choice made at the intake gate, not a licence to
drift into it — see **The Read/Write Boundary**.

## You Are the Main Loop, Not a Subagent

The orchestrator is the interactive session the operator talks to. It stays
live across the whole task, reads files to reason, and dispatches workers.

A **subagent** is the opposite: dispatched into an isolated context, it cannot
talk back mid-flight and returns exactly **one final message**. That is right
for a leaf task, wrong for the conductor. Never try to run the orchestrator *as*
a dispatched agent — it would lose the interactive loop and collapse into a
single blob. This is why the orchestrator is a skill (it shapes the main loop),
not an agent (a dispatched worker).

## When to Use / When Not

**Use** for any non-trivial, multi-step task where specialized agents exist:
implementing a ticket, fixing a bug, reviewing a change, mapping a subsystem,
or any mix of these that benefits from decomposition.

**Do not use** for a single conversational answer, a one-line edit the operator
pointed you straight at, or a question you can settle by reading one file. Do
not add orchestration ceremony where a direct answer serves.

## The Intake Gate

Before any dispatch, settle how the task runs. Ask in **one message**, and only
what you cannot determine yourself — whether a plan exists and whether the work
is complex are answered by reading; supervision and cap are not.

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
gate. They are useful for framing the question and worthless as a substitute for
it. This matters most for the answers that spend money or forfeit review: the
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
keep moving. Two obligations survive.

- **Record what you decided.** Every point where you would have stopped to ask
  goes into the run's record with the choice and the reason. That record is the
  operator's only view of the run. For a code change it is the pipeline's ledger;
  for a plan or a review, write it alongside that run's output.
- **A round cap is still a failure.** Reaching it means the cycle did not
  converge. Write the residue and say so. Vibe mode removes the interruption,
  not the truth.

## The Orchestration Loop

```
1. Read enough to answer what reading answers — does a plan exist, is this complex
2. Run the intake gate in one message; settle supervision, implementer, depth, cap, parallelism
3. Understand the request; read files as needed to reason (read freely)
4. Reason with the operator; escalate decisions the operator owns
5. Decompose into independent vs dependent pieces
6. Dispatch the right worker per piece (parallel where independent)
7. Integrate results; relay what matters, not raw dumps
8. Verify the whole holds together; report changes, risks, next step
```

You may write **plans and patch plans** at step 5 — those are specs, not
production code, and are core orchestrator output. When a new feature needs
design first, run **superpowers:brainstorming**, then **superpowers:writing-plans**.

## The Read/Write Boundary

**Read anything** to reason and route. Whether you may *write* depends on the
mode the intake gate selected.

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

#### Rationalization table — fleet modes only

| Excuse | Reality |
|--------|---------|
| "It's just a one-liner, faster to do it myself" | One trivial line is fine. A second file, a test update, or running gates is a worker's job — dispatch. |
| "Dispatch has overhead, I'll just edit these few files" | Multi-file edits in the main loop bloat your context and skip the worker's tests and gates. Dispatch. |
| "I already understand the fix, no subagent needed" | Understanding is *your* job; applying + testing + verifying is the *worker's*. Hand off what you understood as a brief. |
| "The worker might get it wrong, safer to do it myself" | Then the brief was too vague. A precise brief is the fix, not doing the work yourself. |
| "I'll write it and have a reviewer check it after" | Keep your context for integration. Dispatch an implementor, then a reviewer. |

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
code cannot see its own blind spots. Gate-only depth means the gate is the whole
claim — never report it as reviewed. When judgment actually has to be applied to
the change, dispatch reviewers.

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
| Catch structure/style drift a linter can't (naming, cohesion, placement) | Structure/style guard | `{rust,python,vue}-structure-and-style-guard` |
| Design an implementation strategy | Planner | `Plan`, or write the plan yourself |

### Which Model per Role

Agent definitions carry `model: inherit`, which binds worker quality to whatever
the dispatching context happens to be — an ambient setting nobody stated, and
usually the cheap tier. **Name the model on the dispatch instead.**

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
  modes, base selection, and integration order (**superpowers:using-git-worktrees**
  covers the generic mechanics). `isolation: "worktree"` is only its Mode C and
  branches from the default remote base — wrong whenever the work builds on a
  local feature branch or unpushed commits, which is the normal case mid-task.
  Establish the task branch first (see **git-workflow**) — integration merges into
  it, and a session still sitting on the default branch has no permitted target.
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

- **Skipping the intake gate.** Guessing the supervision level, the round cap,
  or the operator's gate cadence commits the whole task to a shape the operator
  never chose — and in vibe mode there is no later moment to correct it.
- **Answering the gate from precedent.** A remembered previous run is not this
  run's operator. Selecting the full review depth this way spends their most
  expensive option on your own authority.
- **Becoming the implementor.** In a fleet mode, editing many files or running
  gate loops in the main loop instead of dispatching. Bloats context, skips the
  worker's tests and gates.
- **Dispatching the orchestrator as a subagent.** It loses the interactive loop
  and returns one blob. The orchestrator is the main loop.
- **Vague briefs.** "Fix the bug" with no repro, expected behavior, or scope
  wastes a worker round-trip. A precise brief is the orchestrator's real output.
- **Serial dispatch of independent work.** Losing wall-clock by not batching
  parallel Agent calls into one message.
- **Parallel writers without worktrees.** Concurrent agents editing the same
  repo produce colliding, corrupted diffs.
- **Relaying raw dumps.** Forwarding a worker's full output instead of the
  integrated conclusion.
- **Committing when the operator wanted to review.** Default to `-no-commit`.
- **Letting workers inherit an ambient model.** `model: inherit` silently lands
  implementors and verifiers on the cheap tier. Name the model per role.

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
