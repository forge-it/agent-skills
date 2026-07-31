---
name: change-cycle-pipeline
description: >-
  Use when a code change is being delivered through the review pipeline, after
  agent-fleet-orchestration's intake gate has selected a fleet mode or full-loop
  review depth. Symptoms it prevents: reviewing a tree
  that does not build, re-raising findings an earlier round already refuted,
  declaring zero findings when half the reviewers died, paying twice to verify
  one defect filed under two titles, and reporting a round cap as if it were a
  pass. Do NOT use for writing a plan, reviewing a plan, or a standalone code
  review — those are pipeline prompts, not this loop.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.1"
---

# Change Cycle Pipeline

## Purpose

The delivery pipeline for a code change: cut cycles, brief once, implement,
integrate, then loop review → verify → fix until the cycle converges. This skill
owns the pipeline. **agent-fleet-orchestration** owns who executes each piece,
**parallel-worktrees-general** owns worktree mechanics, and
**code-change-workflow** owns the discipline inside a single change.

## Cycles

A cycle is the smallest slice of the work that is **independently reviewable,
independently verifiable, and leaves the tree green**. Not a file count, not a
time box.

You propose the cut from the plan; the operator confirms it before the first
implementor launches. In vibe mode nobody confirms — record the cut in the ledger
and proceed. A cycle that grows past its brief mid-flight **splits** — cycle 2
becomes 2 and 2B, each with its own brief and its own gate. Absorbing the extra
scope silently is how a reviewable cycle becomes an unreviewable one.

When the operator asked for every cycle in one pass, the cycles still exist:
briefs, entry gates, and the ledger still run per cycle. Only the review loop
and the operator gate move to the end.

That single loop takes its inputs from the **union** of the cycles: the blast
radius is every cycle's diff, Acceptance is every cycle's commands, and the round
cap applies once to the whole loop. Out of scope stays **cycle 1's baseline
alone** — a later cycle's baseline already contains earlier cycles' work, and
using it would suppress exactly the regressions this loop exists to catch.

## The Cycle Brief

One artifact, written once per cycle, reused **verbatim** by the implementor,
every reviewer, every verifier, the fixer, and the final gate. This is the
pipeline's largest saving: without it, each stage's prompt is hand-authored, and
a loop that costs an hour of prompt writing per cycle does not get run.

It names:

- **Scope** — the files and subsystems, and the plan section this cycle implements
- **Out of scope** — the baseline failures from the entry gate, and work belonging to other cycles
- **Acceptance** — the exact commands the final gate will run, and what their passing output looks like
- **Commit policy** — worktrees: workers commit inside their own worktree, which the operator's parallelism answer authorizes because integration needs it; single tree: `-no-commit`, the tree stays dirty. Neither authorizes a push.
- **Starting tree** — in single-tree mode, addressed to the worker: the files dirty at cycle start, listed, plus "any file this cycle's own earlier rounds touched is also intended state — it is pipeline state, not operator state, and it is your starting point." Unlisted, a worker following **parallel-worktrees-general** stops on unrecognized dirt. Snapshot `git status --short` *before cycle 1's implementor* and keep it in the ledger: only files in that snapshot are the operator's.
- **Escalation clause** — what the worker decides alone, versus what it must **stop and return with, unanswered**. A subagent cannot ask mid-flight; escalating means ending its turn with the question and the options. The orchestrator answers — or, in vibe mode, decides and records.

Reviewers review **the diff plus its blast radius** — the code whose behaviour
the diff can change: callers and callees of the changed symbols, the contracts
and schemas it touches, and the tests covering them. Pre-existing defects outside
that boundary go to an observations bucket that never blocks the cycle and never
reaches the fix step. What they see there and set aside goes into the ledger's
observations, not into the void.

## Entry Gate and Baseline

The cheap deterministic gate — build, tests, lint, typecheck — runs **twice per
cycle**, answering a different question each time. The orchestrator runs it;
executing the pipeline's own checks is integration, not implementation.

**At cycle start, before the Brief is written.** Whatever fails here is the
baseline, and it is what fills the Brief's Out-of-scope field — which is why it
cannot wait until after the implementor. Compute it; never hand-maintain a list
of known pre-existing failures inside a prompt. Such a list goes stale within
days and then quietly starts suppressing *new* defects that resemble old ones.

**After the implementor, before the first reviewer.** Anything failing now that
is not in the baseline was introduced by this cycle. Send a fixer — a review loop
over code that does not build burns a full round to tell you it does not build.

## Implementation and Integration

**parallel-worktrees-general owns dispatch** — **Modes B and C**, plus base
selection, merge order, and conflict resolution, for parallel implementation;
**Mode D** for any single sequential worker in the orchestrator's checkout, which
means the single-tree implementor and, in every mode, the loop's fixer. Follow it.

In an implementer mode there is no implementor to dispatch — you write it. The
loop's reviewers, verifiers, and fixer are still dispatched.

**Single tree** — implementors leave it dirty, `-no-commit`, and the loop reviews
the tree as it stands. Each cycle inherits the previous cycle's uncommitted work,
which is why the Brief lists it. One writer at a time is structural here, not a
preference: Mode D forbids a second writer, a parallel fixer, and any competing
build or test command in the same checkout.

**Parallel worktrees** — do not parallelize dependent pieces in the first place;
sequence them, so integration stays in the completion order that skill requires.

This pipeline adds exactly two constraints on top:

- **A worktree passes the cheap gate before it hands off.** Merging a red
  worktree and letting the review loop discover it costs a full round.
- **The review loop runs once, on the integrated result** — never per worktree.

### What counts as integration

Resolving a merge conflict, running the pipeline's gates — baseline, pre-review,
post-fix, and the post-merge validation **parallel-worktrees-general** requires —
and making the small deterministic repair that gets a post-merge validation
passing (an import, a rename, a moved symbol): all integration, all the
orchestrator's, none of it a breach of the read/write boundary. The fleet skill's
red flag on running a gate loop means iterating edit-run-edit on your own
production changes, not executing the pipeline's own checks.

A post-merge failure that needs judgment goes to a fixer.

## The Review Loop

Each round: review in parallel → synthesize → verify each finding → fix. Always
against the working tree **as it is now**, never a frozen ref — the fixer mutates
it between rounds.

The loop always runs against **one tree** — the dirty single tree, or the task
branch once integration is done — however implementation was dispatched. So the
parallel reviewers and verifiers are **read-only**: concurrent gate runs in one
checkout collide over the same index and build directory. The orchestrator runs
the gate once and hands every lens the same result.

### Lenses — generate, don't hand-author

The standard set already exists under
`/home/cristi/Projects/agent-skills/prompts/code-implementation-review/`: the
language reviewers in `single-language/`, `generic/implementation-review-loss-framing.md`,
and the `lenses/` set (security, tests-and-migrations, operational-readiness,
bug-hunt, divergence). Add one to three lenses for what *this* cycle actually
risks — the SQL semantics, the concurrency protocol, the wire contract.

Generating from the shared set also keeps this loop and the manual pipeline from
drifting into two different definitions of a good review.

### Round memory

Every round receives what earlier rounds established: findings already fixed, and
findings already **refuted, with the reason**. Both sets live in the ledger and
last the life of the cycle, not the round.

They have two consumers. Every lens brief carries them, so a reviewer knows which
ground is already settled. The synthesizer matches new findings against the
refuted set exactly as it matches duplicates against each other, and drops a
re-raised finding with a citation instead of paying to verify it twice.

Without both consumers the loop does not converge: round 2 re-raises what round 1
killed and may flip the verdict on a coin toss, so the count of open findings
stops measuring anything.

### Synthesize before verifying

Merge findings that describe the same defect, and tag each with its
corroboration — found by k of N lenses.

Matching on file, line and title merges nothing: two reviewers naming one defect
differently become two candidates, two verifiers, and two fixes that can
conflict. Corroboration is also the strongest prioritisation signal available —
a defect four independent lenses found is not the same claim as one lens's
hunch.

### Verify adversarially

One verifier per finding, briefed to **refute it first** against the cited code,
the plan, and the neighbouring tests. Confirmed requires a concrete wrong
behaviour, a material contractual omission, a test that cannot catch the defect
it claims to cover, or an operational gap the plan or its runbook asked for.

That last clause is what makes the operational-readiness and security-hardening
lenses worth dispatching at all — without it their findings are structurally
unconfirmable and every round pays to refute all of them. Hardening the plan
never asked for is an observation, not a finding.

**Style preference is always refuted.** That is what makes "any severity blocks"
safe to run: nits never reach the fix step, so they cannot ping-pong for three
rounds.

Escalate to a three-verifier panel, majority wins, when the fix would be
expensive or hard to reverse — schema, migration, public API, wire format. A
lone refuter is a single point of failure in both directions.

### Coverage

**A round in which any lens died is not eligible for the zero-findings exit.**

Declaring a tree clean because six of eight reviewers timed out is the worst
outcome this loop can produce: it is indistinguishable from success, and it is
reported as success.

### Fix

One fixer at a time, carrying the whole confirmed set. The loop's tree has a
single writer — **parallel-worktrees-general** Mode D — and one fixer keeps the
edits coherent besides. Test-coverage findings go out as a **tests-only
brief** — to a dedicated test-writer agent where the fleet has one for the
language, otherwise to the implementor or fixer with production code declared
off-limits.

The fixer **may reject a finding** — if it is wrong, already remediated, or its
fix would violate the plan, it reports the rejection with reasoning instead of
forcing a bad edit.

Run the deterministic gate after every fix round, not only at the exit. A fix
that regressed a test is a fact for round N+1, not something eight reviewers
should have to rediscover.

## When a Stage Fails

Every stage gets **one** recovery; the table says what follows it. Unbounded retry
is how a loop that cannot converge becomes a loop that never ends.

| Failure | Recovery |
|---------|----------|
| Implementor returns nothing, or dies | Re-dispatch once with the same Brief; then fail the cycle |
| Entry gate still red after one fixer round | Fail the cycle — the defect is larger than the cycle |
| A lens dies | Retry it; if it dies again the round is uncovered, cannot exit clean, and its findings are partial |
| Merge conflict the orchestrator cannot resolve | Report it with both diffs — **parallel-worktrees-general** owns this path |
| Fixer rejects a confirmed finding | Record the rejection and its reasoning; the finding stays open and counts against the exit |
| Operator rejects at their gate | Their objections enter the next round as already-confirmed findings, and the round cap is re-asked |

## Round Cap and Exit

The operator sets the cap at intake: a number of rounds, or *until zero
findings*. Three terminal states.

**Converged** — zero confirmed findings on a fully covered round. Run the
acceptance commands from the Brief and return an evidence table of exact counts
and exit codes. This is the only clean exit.

**Capped** — rounds exhausted without a converged round, whether findings remain
open or the final round simply was not fully covered. The cycle is **not done**.
Record the residue: what remains confirmed, what the gate says, what was fixed.
Supervised, hand it to the operator and stop. In vibe mode, write the residue
report, mark the cycle failed, and continue only if the remaining cycles do not
depend on it.

**Failed** — the implementor or the entry gate exhausted its one recovery (see
*When a Stage Fails*; the other rows continue the round rather than ending the
cycle). Handle it exactly as Capped.

*Until zero findings* is not unbounded. Three conditions convert the run to
**Capped** at the current round:

- a confirmed finding the fixer has rejected twice
- a lens dead in two consecutive rounds
- two consecutive rounds with no net decrease in open confirmed findings

The first two are structurally unclosable; the third is churn, where every round
fixes its set and the reviewers confirm fresh findings on the fixed code. All
three run forever otherwise — and in vibe mode nothing will interrupt them.

Never report a cap as a pass.

## The Operator Report

What the operator gates on:

- what changed — files and diffstat
- what was verified — the exact commands and their results, not "tests pass"
- what the loop confirmed and fixed, **and what it refuted** — so the operator can disagree with a refusal
- what remains open
- what was observed outside the blast radius and deliberately not acted on
- where the implementation deviated from the plan
- which mode ran, how many rounds went against the cap, and whether the final round had every lens
- the next action

Then wait. Nothing is pushed before the operator has answered, and in single-tree
mode nothing is committed. In worktrees mode integration has already committed the
work onto the task branch — so a rejection there is answered by further rounds on
the committed tree (see *When a Stage Fails*), not by discarding a dirty tree. Say
which of the two the operator is looking at.

Vibe mode has no gate: the same report goes into the ledger and the run continues
on the intake answers. The operator reads it afterwards — it is the only account
of the run they get.

## The Ledger

One file per task — `.claude/cycles/<task-slug>.md`, or the project's own
convention where it has one. Confirm the repository ignores `.claude/cycles/`
before the first write, adding the entry if it is missing — exactly as
**parallel-worktrees-general** does for `.claude/worktrees/`. The ledger must
never surface as dirt in a worker's `git status` or inside a reviewer's change
set, and `.claude/` itself is too broad to ignore: most repositories track
configuration there.

It is the pipeline's only durable state, so it holds everything a later round, a
later cycle, or a resumed session needs:

- the intake answers — supervision, implementer, depth, cap, gate cadence, worktrees — as its opening write, since intake happens before this skill loads
- each cycle's cut and scope, and **the Cycle Brief verbatim**, written before the first dispatch
- the pre-task `git status` snapshot, and the baseline out-of-scope list
- per round: the lens set dispatched, which lenses returned, the confirmed set with its verdicts, any fixer rejections with their reasoning, and the fixed and refuted sets
- the round count against the cap, and the per-finding rejection count the cap conversions depend on
- observations set aside outside the blast radius
- deviations from the plan and follow-ups deferred
- the vibe-mode record of decisions taken without asking, any residue report, and the operator report

If a stage needs it and the ledger does not hold it, a compaction or a killed
session loses it — and the run continues on invented parameters. Without the
ledger at all, cycle 4 re-litigates decisions cycle 2 made, and its reviewers
report cycle 2's accepted trade-offs as fresh defects.

When a cycle proves the plan wrong, **amend the plan** — a 2 → 2 + 2B split is a
plan change. Later cycles review against the plan, and a stale plan produces
confident, wrong findings. Once the operator accepts a cycle, run
**reconcile-docs** against what the diff actually touched.

## Review Depth

| Depth | What it is | Use for |
|-------|-----------|---------|
| Gate-only | Tests, lint, typecheck pass — that is the whole claim. Do not call it reviewed. | Mechanical changes |
| Simple panel | A small lens set, no verification, no fixer; you read the findings and decide. | Small changes worth a second pair of eyes |
| Full loop | Everything above. | Migrations, concurrency, security boundaries, wire contracts, anything with a persisted or public shape |

Depth is the operator's intake answer, not yours to reset per cycle. Where a cycle
is plainly mechanical, **propose** a lighter depth at its gate — never downgrade
silently. A loop too heavy for its work gets skipped entirely, which is worse than
one slightly too light, but that is an argument to make to the operator.

## Cost and Resumption

Cheap models at high effort for the lens fan-out; strong models for verifying
expensive findings and for the final gate; mid for fixing. A cycle costs roughly
lenses × rounds, plus one verifier per unique finding. The operator is quoted that
figure at the intake gate, where the cap is actually chosen — by then this skill
has not loaded, so the obligation lives in **agent-fleet-orchestration**.

A killed loop resumes from the ledger — round number, fixed and refuted sets,
coverage — rather than restarting. Where the loop runs inside a workflow harness
that assigns a run id, resume from that instead and let it replay completed
rounds from cache. Rounds are the expensive unit; re-running a finished one buys
nothing.

## Quick Reference

```
cut (task-level, once) →
  per cycle: baseline gate → brief → implement → integrate → pre-review gate
    → [ review → synthesize → verify → fix → gate ] × rounds
    → converged, capped, or failed → report

the ledger is written at every step, not at the end
```
