---
name: change-cycle-pipeline
description: >-
  STOP — if you were dispatched as a subagent to execute a briefed task, this
  skill is not for you: it governs the orchestrator running the loop, not the
  workers inside it. Do the task you were briefed with instead. Use when a code
  change is being delivered
  through the review pipeline, after
  agent-fleet-orchestration's intake gate has selected a fleet mode, or a review
  depth that verifies and fixes — the default narrow loop, or the full loop.
  Symptoms it prevents: reviewing a tree
  that does not build, re-raising findings an earlier round already refuted,
  declaring zero findings when half the reviewers died, paying twice to verify
  one defect filed under two titles, and reporting a round cap as if it were a
  pass. Do NOT use for writing a plan, reviewing a plan, or a standalone code
  review — those are pipeline prompts, not this loop.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.2"
---

# Change Cycle Pipeline

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, stop reading and
do not follow this skill. It is the orchestrator's view of the loop you are one
stage in. Go do the task in your brief.
</SUBAGENT-STOP>

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
every reviewer, every verifier, the fixer, and the final gate. It names:

- **Scope** — the files and subsystems, and the plan section this cycle implements
- **Out of scope** — the baseline failures from the entry gate, and work belonging to other cycles
- **Acceptance** — the exact commands the final gate will run, and what their passing output looks like
- **Commit policy** — worktrees: workers commit inside their own worktree; single tree: `-no-commit`, the tree stays dirty. Neither authorizes a push.
- **Starting tree** — in single-tree mode, addressed to the worker: the files dirty at cycle start, listed, plus "any file this cycle's own earlier rounds touched is also intended state — it is pipeline state, not operator state, and it is your starting point." Unlisted, a worker following **parallel-worktrees-general** stops on unrecognized dirt. Snapshot `git status --short` *before cycle 1's implementor* and keep it in the ledger: only files in that snapshot are the operator's.
- **Escalation clause** — what the worker decides alone, versus what it must **stop and return with, unanswered**. The orchestrator answers — or, in vibe mode, decides and records.

Reviewers review **the diff plus its blast radius** — the code whose behaviour
the diff can change: callers and callees of the changed symbols, the contracts
and schemas it touches, and the tests covering them. Pre-existing defects outside
that boundary go to the ledger's observations bucket, which never blocks the
cycle and never reaches the fix step.

## Entry Gate and Baseline

The cheap deterministic gate — build, tests, lint, typecheck — runs **twice per
cycle**, answering a different question each time. The orchestrator runs it (see
*What counts as integration*).

**At cycle start, before the Brief is written** — whatever fails here is the
baseline, and it fills the Brief's Out-of-scope field. Compute it; a
hand-maintained list of known failures goes stale and quietly starts suppressing
*new* defects that resemble old ones.

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
which is why the Brief lists it.

**Parallel worktrees** — this pipeline adds exactly two constraints on top:

- **A worktree passes the cheap gate before it hands off.**
- **The review loop runs once, on the integrated result** — never per worktree.

### What counts as integration

Resolving a merge conflict, running the pipeline's **working gates** — baseline,
pre-review, post-fix, post-merge — and making the small deterministic repair that
gets a post-merge validation passing (an import, a rename, a moved symbol): all
integration, all the orchestrator's, none of it a breach of the read/write
boundary. The fleet skill's red flag on gate loops means iterating on your own
production changes, not executing the pipeline's checks. A post-merge failure that
needs judgment goes to a fixer.

The **final gate** is not one of these. A working gate is an instrument that
informs the loop; the final gate is the attestation the operator acts on, and the
context that drove the loop to convergence is the wrong one to certify it — the
same self-review problem the fleet skill names. Dispatch it.

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

The lens set already exists under
`/home/cristi/Projects/agent-skills/prompts/code-implementation-review/`: the
language reviewers in `single-language/`, `generic/implementation-review-loss-framing.md`,
and the `lenses/` set (security, tests-and-migrations, operational-readiness,
bug-hunt, divergence).

At the default narrow depth you dispatch **one**, chosen for what the change
risks rather than reflexively the language reviewer — tests-and-migrations for a
migration, security for an authorization change, divergence when a written plan
was implemented ambiguously. At full depth you dispatch the set, plus one to three
written for this cycle: the SQL semantics, the concurrency protocol, the wire
contract.

They are not the same thing as the `subagents/pipeline-*.md` prompts in that
directory — those are a **one-shot review report**, the deliverable for a plan or
code review, and they stop at verified findings, skipping nits. This loop
verifies every severity, fixes what it confirms, and repeats.

### Round memory

Every round receives what earlier rounds established: findings already fixed, and
findings already **refuted, with the reason**. Both sets live in the ledger and
last the life of the cycle, not the round.

They have two consumers. Every lens brief carries them, so a reviewer knows which
ground is already settled. The synthesizer matches new findings against the
refuted set exactly as it matches duplicates against each other, and drops a
re-raised finding with a citation instead of paying to verify it twice.

### Synthesize before verifying

Merge findings that describe the same defect, and tag each with its
corroboration — found by k of N lenses.

Matching on file, line and title merges nothing — two reviewers naming one defect
differently become two verifiers and two fixes that can conflict. Corroboration
is the strongest prioritisation signal the loop has.

### Verify adversarially

One verifier per finding, briefed to **refute it first** against the cited code,
the plan, and the neighbouring tests. Confirmed requires a concrete wrong
behaviour, a material contractual omission, a test that cannot catch the defect
it claims to cover, or an operational gap the plan or its runbook asked for.

Hardening the plan never asked for is an observation, not a finding.

**Style preference is always refuted** — nits never reach the fix step, so they
cannot ping-pong across rounds.

Escalate to a three-verifier panel, majority wins, when the fix would be
expensive or hard to reverse — schema, migration, public API, wire format.

### Coverage

**A round in which any lens died is not eligible for the zero-findings exit.**

### Fix

One fixer at a time, carrying the whole confirmed set — the loop's tree has a
single writer. Test-coverage findings go out as a **tests-only brief**,
production code declared off-limits; the fleet's routing table names the
test-writer.

The fixer **may reject a finding** — if it is wrong, already remediated, or its
fix would violate the plan, it reports the rejection with reasoning instead of
forcing a bad edit.

**The fix handoff has a required shape.** Per confirmed finding: its disposition
(fixed, already remediated, or rejected with reasoning), the files changed for it
or why nothing changed, and the focused verification actually run with its result.
A handoff missing that shape is a **failed stage, not a completed one** — see
*When a Stage Fails*.

Run the deterministic gate after every fix round, not only at the exit. A fix
that regressed a test is a fact for round N+1, not something eight reviewers
should have to rediscover.

## When a Stage Fails

Every stage gets **one** recovery; the table says what follows it.

| Failure | Recovery |
|---------|----------|
| Implementor returns nothing, or dies | Re-dispatch once with the same Brief; then fail the cycle |
| Entry gate still red after one fixer round | Fail the cycle — the defect is larger than the cycle |
| A lens dies | Retry it; if it dies again the round is uncovered, cannot exit clean, and its findings are partial |
| Merge conflict the orchestrator cannot resolve | Report it with both diffs — **parallel-worktrees-general** owns this path |
| Fixer rejects a confirmed finding | Record the rejection and its reasoning; the finding stays open and counts against the exit |
| Fixer returns without the required handoff shape | Re-dispatch once with the contract restated; then fail the cycle. Never count an unsubstantiated "done" as a fixed round |
| Operator rejects at their gate | Their objections enter the next round as already-confirmed findings, and the round cap is re-asked |

## Round Cap and Exit

The operator sets the cap at intake: a number of rounds, or *until zero
findings*. Three terminal states.

**Converged** — zero confirmed findings on a fully covered round. Dispatch the
final gate: a fresh agent that runs the Brief's Acceptance commands and returns an
evidence table of exact counts and exit codes. This is the only clean exit.

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
on the intake answers.

## The Ledger

One file per task — `.claude/cycles/<task-slug>.md`, or the project's own
equivalent. Before the first write: add `.claude/cycles/` to `.gitignore` if it
is not already ignored, mirroring the existing `.claude/worktrees/` entry, then
create the directory. Do not widen this to `.claude/` — it holds tracked
configuration. Both steps are the pipeline's own setup, not a change to the
project: an unignored ledger surfaces as dirt in every worker's `git status`
and every reviewer's change set.

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

When a cycle proves the plan wrong, **amend the plan** — a 2 → 2 + 2B split is a
plan change. Later cycles review against the plan, and a stale plan produces
confident, wrong findings. Once the operator accepts a cycle, run
**reconcile-docs** against what the diff actually touched.

## Review Depth

Depth sets **how wide the review is and whether findings get closed**. The round
cap sets how many times it repeats. They are independent answers.

| Depth | Lenses | Verify | Fix | Use for |
|-------|--------|--------|-----|---------|
| Gate-only | — | — | — | Mechanical changes. Tests, lint, typecheck pass is the whole claim; do not call it reviewed |
| Simple panel | 2–3 | no | no | Breadth without machinery — you read the raw findings and decide. One round |
| **Narrow loop — the default** | 1 | one refuter per finding | one fixer | **Ordinary work.** Full shape, width 1: findings are adversarially checked and actually closed |
| Full loop | 6–9 | one refuter per finding, a panel for expensive fixes | one fixer | The exception — see below |

**The full loop is never self-selected.** Six to nine lenses per round plus a
verifier per finding is the most expensive thing this pipeline can do, so it
runs only when the operator confirms it *for this change*, with that cost
quoted. Memory of an earlier phase, a workflow file, a line in the plan, your
own read of the risk — reasons to **propose**, never confirmation; a declined
proposal is a decision, not an obstacle.

Propose it when a missed defect would be expensive to reverse — migrations and
persisted shapes, security or authorization boundaries, concurrency, wire
contracts across repos — or when the risk surface plainly exceeds one lens.
Propose it mid-cycle too: if the single lens confirms findings in more than one
category, the change is wider than the lens and the depth was the wrong bet.

In vibe mode there is nobody to confirm, so the intake depth stands for the whole
run. Where you would have proposed an upgrade, record the reason in the ledger and
continue at the depth you were given.

Depth is the operator's intake answer, not yours to reset per cycle. Where a
cycle is plainly mechanical, **propose** a lighter depth at its gate — never
downgrade silently.

## Cost and Resumption

**agent-fleet-orchestration** carries the model per role — name it on every
dispatch — and owns quoting the cycle cost at the intake gate, where the cap is
chosen before this skill has loaded.

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
