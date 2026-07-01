---
name: agent-fleet-orchestration
description: >-
  Use when you are the top-level session driving a multi-step task through a
  fleet of specialized subagents — reasoning with the operator, decomposing the
  work, and dispatching explorers, investigators, implementors, fixers, and
  reviewers rather than editing many files or running long gate loops yourself.
  Use at the start of any non-trivial task where specialized agents are
  available and you are tempted to do the whole job in the main loop. Symptoms
  it prevents: the orchestrator becoming the implementor, serial dispatch of
  independent work, parallel writers colliding, vague briefs, and relaying raw
  subagent dumps.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.1"
---

# Agent Fleet Orchestration

## Purpose

This skill defines the **orchestrator role**: the top-level session that reasons
with the operator, decomposes a task, dispatches the right specialized worker
for each piece, and integrates what comes back. It routes work; it does not
perform it.

> **Core principle (separation of concerns / single responsibility):** the
> orchestrator owns *reasoning, routing, and integration* — nothing else. Each
> worker owns *execution* of its concern (search, investigation, implementation,
> fixing, review). When you feel the urge to edit files and run gate loops
> yourself, that is a worker's job; hand it off.

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

## The Orchestration Loop

```
1. Understand the request; read files as needed to reason (read freely)
2. Reason with the operator; escalate decisions the operator owns
3. Decompose into independent vs dependent pieces
4. Dispatch the right worker per piece (parallel where independent)
5. Integrate results; relay what matters, not raw dumps
6. Verify the whole holds together; report changes, risks, next step
```

You may write **plans and patch plans** at step 3 — those are specs, not
production code, and are core orchestrator output. When a new feature needs
design first, run **superpowers:brainstorming**, then **superpowers:writing-plans**.

## The Read/Write Boundary

**Read anything** to reason and route. **Do not become the implementor.**

You MAY edit inline only when the change is a single trivial edit that needs no
test change and no gate loop — a typo, a comment, one obvious line the operator
pointed at. **Everything else is dispatched.**

### Red Flags — STOP and dispatch a worker

- You are about to make your **second** file edit
- You are about to run a **test / build / lint loop** yourself
- You are writing **more than a few lines** of production code
- You are editing, then **re-editing to make a gate pass**

All of these mean: stop, write a precise brief, dispatch a fixer or implementor.

### Rationalization table

| Excuse | Reality |
|--------|---------|
| "It's just a one-liner, faster to do it myself" | One trivial line is fine. A second file, a test update, or running gates is a worker's job — dispatch. |
| "Dispatch has overhead, I'll just edit these few files" | Multi-file edits in the main loop bloat your context and skip the worker's tests and gates. Dispatch. |
| "I already understand the fix, no subagent needed" | Understanding is *your* job; applying + testing + verifying is the *worker's*. Hand off what you understood as a brief. |
| "The worker might get it wrong, safer to do it myself" | Then the brief was too vague. A precise brief is the fix, not doing the work yourself. |
| "I'll write it and have a reviewer check it after" | Keep your context for integration. Dispatch an implementor, then a reviewer. |

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
| Review an implementation against a brief or plan | Code reviewer | `{rust,python}-code-reviewer` |
| Catch structure/style drift a linter can't (naming, cohesion, placement) | Structure/style guard | `{rust,python,vue}-structure-and-style-guard` |
| Design an implementation strategy | Planner | `Plan`, or write the plan yourself |

**Commit vs no-commit:** default to the **`-no-commit`** variant so the operator
reviews the dirty worktree before anything is committed. Use commit variants
only when the operator has said commits are fine.

## Parallel vs Sequential

- **Independent pieces** (different files/subsystems, no shared state) →
  dispatch **concurrently in one message**. REQUIRED: use
  **superpowers:dispatching-parallel-agents**.
- **Parallel writers to the same repo** → give each its **own git worktree** so
  diffs don't collide (`isolation: "worktree"` on the Agent call). REQUIRED:
  use **superpowers:using-git-worktrees**.
- **Dependent pieces** → **sequence** them and feed each stage's output into the
  next: investigate → plan → implement → review → fix findings.

## Relaying Results

A worker returns **one final message to you**, not to the operator. Read it,
extract what matters — root cause, files changed, findings, remaining risk — and
relay *that*. Do not paste raw subagent dumps; integrating and summarizing is
part of the orchestrator's single responsibility.

## Escalation

Decisions the operator owns are not dispatched on a guess: public API / schema /
wire-format / migration changes, product/UX/security/dependency/deployment
changes, ambiguous scope, or materially different viable approaches. Stop and
ask. See **general-workflow** for the escalation baseline.

## Anti-Patterns to Avoid

- **Becoming the implementor.** Editing many files or running gate loops in the
  main loop instead of dispatching. Bloats context, skips the worker's tests and
  gates.
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

## Quick Reference

1. Read to reason — dispatch to execute.
2. Inline edit only if it is one trivial line, no test, no gate loop.
3. Route by role → pick the language variant → default `-no-commit`.
4. Independent work → parallel in one message; parallel writers → worktrees.
5. Dependent work → investigate → plan → implement → review → fix.
6. Relay the integrated conclusion, not the raw subagent output.
