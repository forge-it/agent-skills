---
name: technical-solution-advisor
description: "Use when the operator asks how to solve a ticket, bug, technical issue or important technical decision before any work starts and wants one recommendation: which proposed alternative, whether an approach holds up, or a better fix when none fits. Not for building the fix (code-change-workflow), not while the root cause still needs reproducing (investigate first), not for a multi-decision design conversation with ADRs (technical-design-discussions)."
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.3.0"
---

# Technical Solution Advisor

## Purpose

Act as an advisor, not an implementer: deliver one verdict on what the problem is and which
solution is optimal here, based on the evidence available. The verdict may adopt a proposed
alternative, reject them all for a better one nobody proposed, or recommend from scratch when
none were given.

This skill reads files, runs non-mutating commands and may dispatch read-only explorers
(Step 2). It edits no file and writes no ticket, comment or ADR unless asked; the verdict is
chat output.

Every verdict answers these questions:

| Question | Answered in |
|---|---|
| Q1. What are we trying to solve? | Part 2 |
| Q2. Which solution fixes it in a clean, natural way? | Part 5 |
| Q3. Which solution is optimal in our context? | Parts 3 and 5 |
| Q4. What is the recommendation for this case? | Part 1 |
| Q5. What are the trade-offs? | Part 6 |
| Q6. How long do the recommended and the most complete solutions take, and what other options exist at what cost? | Part 7 |

They orient the work and are not the whole list. Fold anything else the case raises into the
Part it belongs to: security into risk, a data migration into the Part 7 rollout, an external
consumer into Part 3.

## When to use

| Situation | Skill |
|---|---|
| How to solve a ticket, bug or issue; which proposed fix to take, or how to beat them; "validate my approach" | this one |
| Root cause unknown | this one gathers read-only evidence; if the cause needs reproduction or temporary edits, investigate first, then return |
| Many linked decisions, an open-ended conversation, ADRs and handoffs | technical-design-discussions |
| The decision is made; build, fix or refactor | code-change-workflow |

## The process

### Step 1. Frame the problem before touching solutions

Write the problem in one sentence, in terms of what goes wrong for whom. When something is
broken, separate three layers, because most bad recommendations fix the wrong one:

- **Symptom**: what was observed (requests time out under load).
- **Problem**: the behaviour that is wrong (one slow peer stalls every other request).
- **Root cause**: why the code behaves that way (`submit()` holds the registry lock across the
  peer call).

For a forward-looking decision with nothing broken (a tool, vendor, design or process choice),
use **need**, **constraints** and **success criterion** instead.

State the success criterion as something observable ("one slow peer does not delay other
requests"). When the request names a solution instead of a problem ("add a retry"), recover the
problem first; the requested solution becomes one option among others.

### Step 2. Gather evidence and label it

Read the ticket, the code it cites, logs, specs, decision records, and the numbers that exist
(measurements, counts, benchmarks). A verified number outranks an argument; a reported number is
a claim to check. Every claim the verdict rests on gets one label:

- **verified**: read in the source or produced by a command, cited by file and line or output
- **reported**: someone says so (the ticket, a reviewer, a summary) and it was not checked
- **assumed**: inferred, not observed

When the evidence spans many files, modules or repositories, dispatch read-only explorers (the
Explore agent) on Sonnet 5.5 at `xhigh` effort, in parallel in one message: one question each,
with the paths worth reading and a request for file-and-line citations. Their answers are
reported until you spot-check the citations a pick rests on; then they are verified.

Check a load-bearing claim that is only reported or assumed when the check is cheap (one file
read, one command, one API call). When it is expensive: if the unknown separates the options, the
verdict is Evidence first; otherwise the pick stands at medium confidence and Part 8 names the
unchecked claim.

### Step 3. Establish the context that decides

Find the context the request rarely states: where it runs, how many instances, who operates it,
the two-year scale; deadlines and release state; conventions and recorded decisions;
reversibility (wire contracts, persisted data and public names are expensive to change); and who
else consumes the behaviour. Look in the code and docs first.

If a missing fact would change the pick and cannot be found, the verdict is Evidence first with
that fact as the unknown, and Part 1 puts the questions to the operator, all together, next to
the provisional pick. If you cannot ask (for example, running as a subagent), assume it, label it
assumed, and name what flips the verdict.

### Step 4. Build the option set, including options nobody proposed

Restate each given alternative in one line before judging it, so you judge what was meant. Then,
for each of these, add a row, mark the existing row it coincides with, or give a one-line reason
under the table why it is not viable:

- **Do nothing**: what it costs to live with the problem.
- **Minimal fix**: the smallest change that removes the symptom.
- **Root-cause fix**: the change that makes the problem impossible where it starts.

Then ask the reframing questions, each of which can produce an option nobody proposed:

- **R1.** Can the problem be made impossible by construction (a type, a constraint, a single
  owner)?
- **R2.** Does the platform, a library or an existing module already solve it?
- **R3.** Is the requirement real, or can it be removed or narrowed?
- **R4.** Does the responsibility sit in the wrong layer, so moving it dissolves the problem?
- **R5.** Which established pattern does this match, and what is that pattern's known fix?
- **R6.** What does the problem look like inverted (pull instead of push, check at write instead
  of read)?

Check that every option is feasible here: the API exists, the layer may depend on it, the
conventions allow it. An option whose feasibility you did not check is labelled assumed.

### Step 5. Judge each option on the same criteria

Use these criteria, adjusted to the case: drop the ones that do not apply and add what the case
needs (cost, licence, lock-in, team skill, operational load), and say which you changed.

| Criterion | Question |
|---|---|
| Fixes the cause | Does it remove the root cause, or only hide the symptom? |
| Natural fit | Does it follow the existing architecture, idioms and vocabulary, so a reader expects it there? |
| Blast radius | What else changes behaviour; who else is affected? |
| Reversibility | How expensive is it to undo or change later? |
| Risk | What can go wrong in the change itself, and how would we notice? |
| Effort | How long, including tests, docs, review and rollout? |
| Operability | Does it make the system easier or harder to run and diagnose? |

The context from Step 3 decides which criteria dominate; Part 3 names them and Part 4 gives each
its own column. An option is out only for a named reason, with its real advantage conceded.

### Step 6. Decide

The verdict is exactly one of:

- **Adopt** a given alternative, possibly with named refinements. A refinement keeps the
  alternative's mechanism; a different mechanism is a new option. The operator's authorship is
  not a criterion.
- **Replace**: alternatives were given and every one is rejected, each for a named defect; a
  better option is proposed and judged with the same rigour. Novelty is not a criterion either:
  a given option that wins on the criteria is adopted.
- **Recommend**: no alternatives were given; the pick comes from the Step 4 option set.
- **Evidence first**: a load-bearing unknown separates the options. Name it, give the cheapest
  experiment that settles it and its cost, and give the provisional pick and what flips it.

A staged pick (a stop-gap now, a named follow-up later) is valid under any of these; both stages
are rows in the options table. "It depends" with no pick is not a verdict.

### Step 7. Estimate the effort as a ladder of ranges

Give a ladder, cheapest to fullest, each rung broken into steps (code, tests, docs, review,
rollout) with a likely-to-worst range:

- the cheapest safe option and what it leaves undone, or "no safe stop-gap"
- the recommendation
- the most complete solution and when it pays back (the same rung as the recommendation when
  they coincide; say so)

Name what drives each worst case. When a budget was stated, mark the rung that fits it; when not,
say which budget each rung fits. State the basis: engineer working time including review and gate
runs, whether it assumes agent-assisted delivery, and `d` = a working day of about 6 focused
hours. Each rung's total is the effort cell of its row in Part 4.

## The verdict, in this order

1. **Part 1, Verdict**: Adopt, Replace, Recommend or Evidence first, then the pick in one or two
   lines, with confidence and why.
   - Confidence: **high** when every claim the pick rests on is verified and feasibility is
     checked; **medium** when a claim is reported or assumed but would not change the pick;
     **low** when an unchecked claim would change the pick, which makes the verdict Evidence
     first.
   - For Evidence first, Part 1 names the unknown, the cheapest experiment and its cost, any
     questions for the operator, then the provisional pick and what flips it; Part 8 does not
     repeat them.
   - When the problem is live (an incident), Part 1 opens with the immediate mitigation, which is
     also the first rung of the Part 7 ladder.
2. **Part 2, Problem**: the one-sentence problem and the root cause (or need and constraints),
   each with its evidence label, then the success criterion.
3. **Part 3, Context that decides**: the two to four facts that make this the right answer here,
   and the criteria they make dominant (for example, reversibility, because the wire contract is
   public).
4. **Part 4, Options**: a table with one row per option. Columns: the option, fixes the cause,
   natural fit (good / ok / poor, or n/a for do nothing), effort range, one column for each
   dominant criterion Part 3 names that is not already a column (risk by default), verdict. Row
   verdicts are pick, out, runner-up or stop-gap; Adopt, Replace, Recommend and Evidence first
   appear only in Part 1. Rejected rows give the reason and the conceded advantage. Tag options
   nobody proposed, or write "No better option found; reframing questions R1–R6 asked."
5. **Part 5, Clean fix and recommendation**: the clean, natural fix (removes the cause, fits the
   codebase, whatever it costs), then the recommendation and what it changes. When they are the
   same, say so in one line. When not, say what makes the recommendation optimal here, what stays
   unfixed, and the follow-up the clean fix needs.
6. **Part 6, Trade-offs accepted**: what the recommendation gives up and why that is acceptable.
7. **Part 7, Effort**: the ladder from Step 7, with its basis.
8. **Part 8, What would change this**: open questions, unchecked assumptions, and the evidence
   that would flip the verdict.

Parts 1, 4, 5 and 6 are always written out. Parts 2, 3 and 8 shrink to one or two lines when the
case is small, and Part 7 to the rung totals without the step breakdown. A routine ticket fits on
one screen (about 25 lines); a contested or high-stakes decision may take two. Part 5 stops at the
module, boundary or contract that changes: no code and no task-by-task plan.

## Example

Ticket: requests time out under load. Proposals: A, raise the request timeout; B, retry on
timeout.

```
Part 1  Replace (high). Neither A nor B: release the registry lock before the peer call
        in submit() (C). The lock is held across the network call, so every request
        queues behind one slow peer.
Part 2  One slow peer stalls all requests (verified, load-test log). Root cause: submit()
        holds the registry lock across the peer call (verified, registry.rs:142). Done
        when a slow peer delays no other request.
Part 3  One process, one shared registry (verified, main.rs:31); no wire change allowed
        (verified, ADR-0004). Dominant: fixes the cause, blast radius.
Part 4
| Option                   | Fixes cause | Fit  | Effort | Blast radius / risk       | Verdict |
| A raise timeout (minimal)| no          | ok   | 0.5 h  | every caller waits longer | out: masks the stall; conceded: cheapest |
| B retry                  | no          | ok   | 2–4 h  | adds load to the queue    | out: worsens the pile-up; conceded: helps real transient faults |
| C narrow the lock (root cause, new) | yes | good | 4–8 h | submit() only           | pick |
| D actor + channel (new)  | yes         | poor | 2–3 d  | every registry caller     | runner-up: right once more shared state appears |
| do nothing               | no          | n/a  | 0      | stalls continue           | out: users hit it under every load peak (reported, ticket); conceded: zero risk |
Part 5  The clean fix and the recommendation are the same: C. It keeps the existing
        lock-based design and moves only the release point in submit().
Part 6  C keeps a lock where an actor would remove the class of bug; the ordering risk
        is covered by a concurrency test.
Part 7  No safe stop-gap (A only masks it, B adds load). C: change 1–3 h, concurrency
        test 2–4 h, review 1 h (4–8 h). D: actor 1 d, callers 0.5–1 d, tests and review
        0.5–1 d (2–3 d); pays back when a second invariant ties registry state to the
        peer reply. Worst-case driver for C: a caller depending on the lock held across
        the await; grep finds none, and submit() reads no registry state after the peer
        call (both verified). Basis: engineer time, agent-assisted, d = 6 focused hours.
Part 8  A second invariant tying registry state to the peer reply would make D the pick.
```

## Push-back

Treat "I disagree" as new input: add any new constraint to Step 3, judge the options again,
concede exactly what the argument wins, and hold the rest. A verdict moves on argument and
evidence, never on tone.

## Common mistake

Rubber-stamping the given set: judging only the proposed alternatives without asking R1–R6. Part 4
must show an option nobody proposed, or the line saying R1–R6 found none.
