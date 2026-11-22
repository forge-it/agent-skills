---
name: agent-fleet-orchestration
description: >-
  STOP — if you were dispatched as a subagent to execute a briefed task, this
  skill is not for you: it governs the top-level session only. Do the task you
  were briefed with instead. Use when you ARE that top-level session and a
  non-trivial task is about to run through a fleet of specialized subagents
  rather than by your own hand. Use ONCE, before the first dispatch, whatever
  the deliverable is: a code change, a plan, a plan review, or a code review.
  Never reload it: once loaded it governs the whole task; re-opening the gate
  is a decision, not a reload. Symptoms it prevents: committing to a
  supervision level or round cap the operator never chose, the orchestrator
  becoming the implementor, serial dispatch of independent work, parallel
  writers colliding, vague briefs, and relaying raw subagent dumps.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.8"
---

# Agent Fleet Orchestration

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, stop reading and
discard this skill. It is the orchestrator's, and following it from inside a
worker means asking questions nobody will answer and dispatching a fleet nobody
asked for. Go do the task in your brief.

Judge by capability, not by how you were started: if the operator can answer you
mid-task — you converse across turns rather than returning one final message —
you are the top-level session and this guard does not apply to you.
</SUBAGENT-STOP>

## Purpose

This skill defines the **orchestrator role**: the top-level session that settles
how a task will run, reasons with the operator, decomposes the work, dispatches
the right specialized worker for each piece, and integrates what comes back.

> **Core principle (separation of concerns / single responsibility):** the
> orchestrator owns *reasoning, routing, and integration*. Each worker owns
> *execution* of its concern (search, investigation, implementation, fixing,
> review).

Never run the orchestrator *as* a dispatched agent: a subagent returns one
final message and cannot talk back mid-flight, which is right for a leaf task
and wrong for the conductor.

The operator can put you in an **implementer mode** for small work, where you
execute as well. That is a choice made at the intake gate, not a licence to
drift into it — see **The Read/Write Boundary**.

Skills named in **bold** throughout are pointers, not a startup manifest. Load
one when you reach the work it governs — loading four process skills before the
first dispatch spends context on decisions you have not made yet.

## When Not to Use

A single conversational answer, a one-line edit the operator pointed you
straight at, or a question one file settles needs no orchestration ceremony.

## The Intake Gate

Before any dispatch, settle how the task runs. Ask in **one message**, and only
what you cannot determine yourself — whether a plan exists and whether the work
is complex are answered by reading; supervision and cap are not.

**A standing instruction is an answer.** Before asking, read what the operator
asked for in this task and the project's **mandate**: what the operator wrote
for every session in the project's shared instructions (its `CLAUDE.md`).
Scope, model selector, isolation, review depth and integration rules set there
are answered in every phase of the task — do not ask them again; ask only the
axes still unset. Two answers never come from a mandate, to keep cost in the
operator's hands: a mandate cannot select the **full review depth** and cannot
set the **round cap**. Where this task's gate reaches either one, the operator
answers it on this task, with the cost quoted. A mandate answers what it names
and nothing wider (**Escalation** lists what stays reserved), and it holds only
in the project that carries it. With no mandate, the gate runs as written here.

**The gate is answered once per task, not once per message.** A follow-up
instruction — redirect the work, salvage a failed stage, change the scope — is
the operator steering the task you are already running; carry the existing
answers forward. Re-open the gate only when the deliverable itself changes (a
code change becomes a plan review), or when the operator changes an answer — and
re-open it from context, never by reloading this skill.

| Axis | Options | Skip when |
|------|---------|-----------|
| Supervision | vibe (full power, no gates) / supervised | — |
| Implementer | fleet agents / you | the deliverable is a plan or a review |
| Review depth — code | **narrow loop (default: 1 lens, refuted, fixed)** / gate-only / simple panel (2–3 lenses, no verifier, no fixer) / full loop — 6–9 lenses, **only on explicit operator confirmation with the cost quoted**, never self-selected | the deliverable is a plan or a review |
| Pipeline variant — plan or code review | simple / complex | the deliverable is a code change |
| Spec input — plan or code review | the plan path or ticket key to review against, plus the git base for a code review | the deliverable is a code change |
| Round cap | N rounds / until zero findings — **quote the cost in the same message**: lenses dispatched × rounds, plus one verifier per unique finding | the depth has no fix step (gate-only, simple panel), or the deliverable is a plan or a review |
| Operator gate | per cycle / at the end | supervision is vibe, or the deliverable is a plan or a review |
| Parallel worktrees | yes / no | you are the implementer, or the deliverable is a plan or a review |

The answers **compose**; they are not a menu of preset modes. A combination the
table below does not name is still legitimate.

**Precedent is not an answer.** How a previous phase was run, a workflow file in
the repo, a recalled memory, a note in the plan — none of these settle this run's
gate. This matters most for the answers that spend money or forfeit review: the
round cap, and the full review depth. Selecting the full depth from precedent
spends the operator's most expensive option on your own authority. A mandate is
not precedent: the operator wrote it as a standing instruction.

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
| Code | supervised + you implement + narrow or full loop | **change-cycle-pipeline**; you write, subagents review, verify, and fix; the operator gate runs at the cadence chosen |
| Code | supervised + you implement + gate-only | You edit, then run the project's gate — that is the whole claim, and it is not a review |
| Code | supervised + you implement + simple panel | You edit, then dispatch 2–3 lenses from `/home/cristi/Projects/agent-skills/prompts/code-implementation-review/`; no verifier, no fixer — read the findings and decide |
| Plan | — | **superpowers:brainstorming** → **superpowers:writing-plans**; **technical-design-discussions** for the decisions you escalate; `Explore` agents for the facts |
| Plan review | — | `/home/cristi/Projects/agent-skills/prompts/plan-review/subagents/` — pick by stack (`python`, `rust`, `vue`, `react`, `python-vue`, `python-react`, `rust-vue`, `rust-react`), then plain vs `-complex`. Fill `<X>` (the plan path) and pick `<Y>` (your output prefix); these prompts have no `<Z>` |
| Code review | — | `/home/cristi/Projects/agent-skills/prompts/code-implementation-review/subagents/` — pick by the same stacks, then plain vs `-complex`, then `-ticket` when the spec is a Jira issue rather than a plan file (`-ticket` exists for python only; for another stack, say so and use the plain variant against a plan). Fill `<X>` (plan path or ticket key) and `<Z>` (the git base), and pick `<Y>`. No plan and no ticket means there is nothing to review *against* — settle that with the operator before dispatching |

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

A precise brief is the orchestrator's real output. "Fix the bug" with no
reproduction, expected behavior, or scope wastes a worker round-trip; the brief
carries all three, plus the constraint the worker must not cross.

| Task / signal | Worker role | Typical agent (pick language variant) |
|---------------|-------------|----------------------------------------|
| "where is X", "how does Y work", find usages, map a subsystem | Explorer (read-only) | `Explore` |
| Reproduce a bug, localize root cause, gather evidence before any fix | Investigator | `{rust,python,vue,react}-issue-investigator` |
| Implement a ticket / feature / task | Implementor | `{rust,python,vue,react}-implementor-expert` (`python-implementor-syneto-expert` for Syneto OS) |
| Fix a bug, failing test, regression, clippy/lint/type error, import-contract or architecture-gate failure | Fixer | `{rust,python}-fixer`; the frontend ships no-commit only — `{vue,react}-fixer-no-commit`; `python-basedpyright-fixer-no-commit` for type-only |
| Tiny bug, expected behavior already known, small change, strict TDD | Tiny bugfixer | `{rust,python}-tiny-tdd-bugfixer`; no frontend variant — use a fixer with a tight brief |
| Write or extend test coverage for existing code | Test writer | `{rust,python}-test-writer`; frontend: an implementor or fixer with a tests-only brief |
| Review an implementation against a brief or plan | Code reviewer | `{rust,python,vue,react}-code-reviewer` |
| Run one review lens over a diff | Lens reviewer | a general-purpose agent carrying a prompt file from `/home/cristi/Projects/agent-skills/prompts/code-implementation-review/` verbatim |
| Refute or confirm one finding | Verifier / skeptic | a general-purpose agent carrying the Stage 3 skeptic brief from that directory's `subagents/pipeline-<stack>.md` verbatim; for a finding that cites a skill rule or a structural SRP violation, the rule-finding brief in change-cycle-pipeline's verify step instead |
| Certify that a converged cycle actually passes | Final gate | a fresh general-purpose agent, read-only, running the Brief's Acceptance commands and returning an evidence table — never the context that drove the loop |
| Catch structure/style drift a linter can't (naming, cohesion, placement) | Structure/style guard | `{rust,python,vue,react}-structure-and-style-guard` |
| Exhaustively audit a scoped tree against a rubric, especially SRP | Auditor (read-only) | `{rust,python}-code-auditor` |
| Turn one audit finding into an implementation-ready refactor handoff | Designer (read-only) | `{rust,python}-code-designer` |
| Assess a change set or a scoped tree for exploitable flaws, any language — **only when the operator asks for it**; never self-selected, never folded into a review loop | Security reviewer (read-only) | `generalistic-security-expert` |
| Design an implementation strategy | Planner | `Plan`, or write the plan yourself |

### Which Model per Role

Model resolution on a dispatch runs: the `model` you pass → the agent
definition's `model:` line → `CLAUDE_CODE_SUBAGENT_MODEL` → the session's own
model. Agent definitions carry no `model:` line, by convention, so a dispatch
that names no model lands on `CLAUDE_CODE_SUBAGENT_MODEL` — the operator's
default worker tier, `sonnet`: cheap and good enough for implementation,
fixing, review, verification, and exploration alike. **Do not name a model on
an ordinary dispatch**; naming one overrides the operator's default.

**The selector is the choice; the label a worker reports is not.** When a
worker names a different model for itself than the selector it was dispatched
under, nothing was re-decided: carry on under the agreed selector, ask nobody,
and dispatch no second writer to correct it. Report the selector in force,
and do not present any underlying model as verified — you verified the
selector, not the runtime.

Depart from the default deliberately, and say why in one line — in the ledger
when there is nobody to tell:

| Departure | When |
|-----------|------|
| `opus` on one dispatch | A cheap miss would be expensive and hard to see: a concurrency or authorization defect to localize; a verifier ruling on a finding whose fix is hard to reverse — schema, migration, public API, wire format; the fixer applying such a fix |
| `fable` | **Only when the operator explicitly asks for it on this task.** It is reserved for the rare work they name; the stakes as you read them are never a reason |

The orchestrator itself runs on the Opus tier or above — the session's choice,
not this skill's.

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
- **A new phase already in scope, where worktrees are the answer** (the
  gate's or the mandate's) → new workers in **fresh worktrees**, one writer per
  lane, settled when the phase is planned. A worker stays pinned to the
  worktree it was dispatched into, so a plan that needs it to move into another
  one fails at the move: do not move workers into or between the earlier
  worktrees, whose cleanup follows **parallel-worktrees-general**. Mode and base
  are that skill's call, not a question for the operator. This is how a phase
  is planned, never a way around a refusal.
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

## Before Going Idle

A blocker belongs to a **lane**, not to the task. A lane is one stream of the
authorized work with at most one owner: a worker you dispatched, yourself, or a
peer session it was handed to. When a worker returns, a lane is handed to another
session, or a gate blocks, go through the other lanes the operator already
authorized before you end the turn: who owns each, which dependency actually
blocks it, and what can proceed inside the agreed budget and file boundaries.
Dispatch the next lane that is ready and unowned in that same turn. For each
blocked lane, put in the run's record the exact condition that unblocks it and
who will report it.

Read a blocker at its real width. A handoff moves one lane to its new owner; a
missing credential blocks the test that needs it; a deployment window limits
production cutovers, not development or fixture tests.

Waiting is right when every authorized lane is complete, owned and running,
blocked, or at an explicit stop such as the operator gate. Do not manufacture
motion to avoid it: no second run of a test another owner is running, no scope
the operator did not authorize, no polling for activity — and a dispatched
worker is not a verified result.

## Escalation

Sort a decision before asking anyone; most never reach the operator:

1. **A standing instruction covers it** — a gate answer, the mandate, what
   the operator asked for in this task: act. No question.
2. **Technical judgment inside the assigned scope, where the mandate or the
   operator designates a technical coordinator** (a peer session running
   **technical-solution-advisor**): the coordinator decides. Send it the
   question over `SendMessage` with this session's name, the task, the
   options you see and your recommendation, and act on the reply as a
   decision, not as advice to confirm with the operator.
3. **Reserved or genuinely new**: the operator decides, once, in one place.

Reserved whatever a mandate or a coordinator says: a new privilege or
permission, an operation a skill or the project forbids, disclosing a
credential, waiving a safety gate or a required test or review, a weaker
production trust boundary, downtime nobody approved, a release or deployment
the project reserves, a new deliverable, and a fleet or review spend materially
above what was agreed. Escalate one of these with the exact exception, the
alternatives and what each costs.

These are not dispatched on a guess: public API / schema / wire-format /
migration changes, product/UX/security/dependency/deployment changes, ambiguous
scope, or materially different viable approaches. Stop and ask whoever the sort
names: the coordinator for a technical choice inside the assigned scope, the
operator for everything else. See **code-change-workflow** for the escalation
baseline.

Vibe mode suspends the asking, the coordinator included: decide and record, per
**Vibe Mode** above. A denial is the exception: stop the action, record it as
that lane's blocker, and go on with what does not need it.

**A denial is an answer.** When the harness or the operator denies
an action, stop it. Do not get it done through another worker, session, worktree
or tool, do not change permission settings or suppress the prompt, and do not
read the denial as narrower than it was given. An authorized staffing plan does
not answer a pending permission prompt: if the action is needed, ask once, in
the session that owns the prompt.

## Quick Reference

```
intake gate (once; standing answers first) → read to reason, dispatch to execute
  → route by role → language variant → -no-commit and the default model unless departing deliberately
  → independent work in parallel, dependent work in sequence, parallel writers in worktrees
  → a code change in a fleet mode, or at a depth that fixes, runs change-cycle-pipeline
  → relay the integrated conclusion, never the raw dump
  → before going idle: a blocker pauses its lane; dispatch the next ready, unowned, authorized lane
  → sort a decision: standing instruction → act; coordinator's judgment → coordinator; reserved or new → operator, once
```
