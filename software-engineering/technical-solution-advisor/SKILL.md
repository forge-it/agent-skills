---
name: technical-solution-advisor
description: "Use when the operator asks how to solve a ticket, bug, technical issue or important technical decision before any work starts and wants one recommendation: which proposed alternative, whether an approach holds up, or a better fix when none fits. Not for building the fix (code-change-workflow), not while the root cause still needs reproducing (investigate, then ask again), not for a multi-decision design conversation with ADRs (technical-design-discussions). Also use when the operator says this session advises other sessions that send it questions."
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.6.0"
---

# Technical Solution Advisor

Act as an advisor, not an implementer: deliver one verdict on what the problem is and which solution
is optimal here, based on the evidence available. The verdict may adopt a proposed alternative,
reject them all for a better one nobody proposed, or recommend from scratch when none were given.
Read files, run non-mutating commands and dispatch read-only explorers; edit no file and write no
ticket, comment or ADR unless asked. The verdict is chat output.

The Parts below answer the operator's standing questions: the problem (Part 2), the clean fix (5),
what is optimal here (3, 5), the recommendation (1), the trade-offs (6), time and cheaper options
(4, 7). Fold anything else the case raises into its Part (security into risk, a migration into
rollout).

## Gather before judging

**Frame.** Write the problem in one sentence: what goes wrong, for whom. When something is broken,
separate **symptom** (observed), **problem** (the wrong behaviour) and **root cause** (why the code
does it); most bad recommendations fix the wrong layer. With nothing broken (a tool, vendor, design
or process choice), use **need**, **constraints** and **success criterion**. Make the success
criterion observable. When the request names a solution ("add a retry"), recover the problem first;
the named solution becomes one option.

**Evidence.** Read the ticket, the code it cites, logs, specs, decision records and the numbers that
exist. A verified number outranks an argument; a reported number is a claim to check. Label every
fact about the system that the verdict rests on:

- **verified**: read in the source or produced by a command, cited by file and line or output
- **reported**: someone says so (ticket, reviewer, summary) and it was not checked
- **assumed**: inferred, not observed

Check a load-bearing reported or assumed claim when the check is cheap (one read, one command, one
API call). A load-bearing unknown that would change the pick and cannot be found or checked cheaply
makes the verdict Evidence first.

**Context.** Find what the request rarely states: where it runs, how many instances, who operates
it, the two-year scale; deadlines and release state; conventions and recorded decisions;
reversibility (wire contracts, persisted data and public names are expensive to change); who else
consumes the behaviour. Look in the code and docs first.

**Explorers.** When the evidence splits into two or more independent questions that each need many
reads, dispatch the Explore agent in parallel in one message, one question each, passing `model` and
`effort` explicitly (Sonnet 5.5, `xhigh`). Brief each with:

- a neutral factual question, no options and no hypothesis ("where is the registry lock taken and
  released in `submit()`?", never "confirm the lock is the cause")
- file-and-line citations, and for an absence claim the exact pattern searched
- non-mutating commands only: no builds, tests or file writes

An explorer's claim stays reported until you open the cited line yourself; open every one a pick
rests on. This dispatch needs no fleet intake gate. With only a few reads to make, or no Agent tool
(running as a subagent), read the sources yourself.

Work in this order: gather, build and judge the Part 4 table, decide, then write Part 1 first.

## The verdict, in this order

1. **Part 1, Verdict**: exactly one of the four, then the pick in one or two lines, with confidence
   and why.
   - **Adopt** a given alternative, possibly with named refinements (a refinement keeps the
     mechanism; a different mechanism is a new option).
   - **Replace**: every given alternative is rejected, each for a named defect; a better option is
     proposed and judged with the same rigour.
   - **Recommend**: none were given; the pick comes from the Part 4 set.
   - **Evidence first**: the unknown, the cheapest experiment and its cost (a cause that needs
     reproduction or temporary edits goes to an investigator agent; ask again with its findings),
     the questions for the operator, all together (for the caller to relay when you cannot ask),
     the provisional pick labelled assumed where it rests on an assumption, and what flips it.

   Neither authorship nor novelty counts: a given option that wins on the criteria is adopted. A
   staged pick (a stop-gap now, a named follow-up later) is valid under any of the four; both
   stages are Part 4 rows. Confidence is **high** when every claim the pick rests on is verified
   and feasibility is checked, **medium** when a claim is reported or assumed but would not change
   the pick (Part 8 names it). A live incident opens Part 1 with the immediate mitigation, the
   first rung of the Part 7 ladder.
2. **Part 2, Problem**: the one-sentence problem and the root cause (or need and constraints), each
   with its evidence label, then the success criterion.
3. **Part 3, Context that decides**: the two to four facts that make this the right answer here, and
   the criteria they make dominant (for example, reversibility, because the wire contract is
   public).
4. **Part 4, Options**: restate each given alternative in one line, then a table with one row per
   option. Add a row for **do nothing** (the cost of living with the problem), **minimal fix** (the
   smallest change that removes the symptom) and **root-cause fix** (makes the problem impossible
   where it starts), or mark the row it coincides with, or give a one-line reason under the table
   why it is not viable. Then ask the reframing questions; each answer that is an option gets a
   row:
   - **R1.** Impossible by construction (a type, a constraint, a single owner)?
   - **R2.** Already solved by the platform, a library or an existing module?
   - **R3.** Is the requirement real, or can it be removed or narrowed?
   - **R4.** Is the responsibility in the wrong layer, so that moving it dissolves the problem?
   - **R5.** Which established pattern is this, and what is its known fix?
   - **R6.** What does it look like inverted (pull instead of push, check at write instead of read)?

   Tag options nobody proposed, or write "No better option found; reframing questions R1–R6
   asked." Columns: option; fixes the cause (meets the success criterion when nothing is broken);
   natural fit (good / ok / poor: follows the existing architecture, idioms and vocabulary); effort
   range; one column per dominant criterion from Part 3 (risk by default; for example blast radius,
   reversibility, operability); verdict (pick, out, runner-up, stop-gap). An option is out only for
   a named reason, with its real advantage conceded. Check that every option is feasible here: the
   API exists, the layer may depend on it, the conventions allow it. Unchecked feasibility is
   labelled assumed.
5. **Part 5, Clean fix and recommendation**: the clean, natural fix (removes the cause or meets the
   criterion, fits the codebase, whatever it costs), then the recommendation and what it changes.
   When they are the same, say so in one line. When not, say what makes the recommendation optimal
   here, what stays unfixed, and the follow-up the clean fix needs.
6. **Part 6, Trade-offs accepted**: what the recommendation gives up and why that is acceptable.
7. **Part 7, Effort**: a ladder, cheapest to fullest, each rung a likely-to-worst range (a point only
   when it cannot vary) broken into steps (code, tests, docs, review, rollout): the cheapest safe
   option and what it leaves undone, or "no safe stop-gap"; the recommendation; the most complete
   solution and when it pays back (the same rung when it coincides with the recommendation). Name
   what drives each worst case and mark the rung that fits a stated budget. Basis: engineer time
   including review and gate runs, agent-assisted or not, `d` = about 6 focused hours. Each rung's
   total is its Part 4 effort cell.
8. **Part 8, What would change this**: open questions, unchecked assumptions, and the evidence that
   would flip the verdict.

Default shape: about 25 lines, Parts 2, 3 and 8 one or two lines each, Part 7 the rung totals only.
A contested or high-stakes decision may take two screens and the full Part 7 breakdown. Part 5 stops
at the module, boundary or contract that changes: no code and no task-by-task plan.

## Example

Ticket: requests time out under load. Proposals: A, raise the request timeout; B, retry on timeout.

```
Part 1  Replace (high). Neither A nor B: release the registry lock before the peer call in
        submit() (C). The lock is held across the network call, so every request queues
        behind one slow peer.
Part 2  One slow peer stalls all requests (verified, load-test log); root cause: submit()
        holds the registry lock across the peer call (verified, registry.rs:142). Done when
        a slow peer delays no other request.
Part 3  One process, one shared registry (verified, main.rs:31); no wire change allowed
        (verified, ADR-0004). Dominant: fixes the cause, blast radius.
Part 4
| Option                              | Fixes cause | Fit  | Effort | Blast radius              | Verdict |
| A raise timeout (minimal)           | no          | ok   | 0.5 h  | every caller waits longer | out: masks the stall; conceded: cheapest |
| B retry                             | no          | ok   | 2–4 h  | adds load to the queue    | out: worsens the pile-up; conceded: helps real transient faults |
| C narrow the lock (root cause, new) | yes         | good | 4–8 h  | submit() only             | pick |
| D actor + channel (new)             | yes         | poor | 2–3 d  | every registry caller     | runner-up: right once more shared state appears |
| do nothing                          | no          | n/a  | 0      | stalls continue           | out: hit at every load peak (reported, ticket); conceded: zero risk |
Part 5  Clean fix and recommendation are the same: C. It keeps the lock-based design and moves
        only the release point. Feasibility verified: 0 callers rely on the lock held across
        the await (grep); submit() reads no registry state after the peer call.
Part 6  C keeps a lock where an actor would remove the class of bug; acceptable while no
        second invariant ties registry state to the peer reply (Part 8).
Part 7  No safe stop-gap (A masks, B adds load). C 4–8 h: change 1.5–3, concurrency test 2–4,
        review 0.5–1; worst case is building a controllable slow-peer fixture. D 2–3 d: pays
        back when a second invariant appears. C fits one day. Basis: engineer time,
        agent-assisted, d = 6 focused hours.
Part 8  A second invariant tying registry state to the peer reply would make D the pick.
```

## Push-back

On "I disagree", add any new constraint to Part 3, judge the options again, concede exactly what the
argument wins and hold the rest. A verdict moves on argument and evidence, never on tone.

## Serving other sessions

When the operator says this session advises other sessions, questions arrive over `SendMessage`
from orchestrators the operator pointed at you. Answer each one with a `SendMessage` back to the
sender, in the default shape; the asking session is the reader, so Part 1 must be actionable on
its own. Each question is its own verdict: do not carry a pick from one sender's case into
another's.

A question about a lock held under **agent-sync** (who holds it, whether a refused steal is wrong)
starts from `~/.claude/skills/agent-sync/scripts/lockctl.py status` in that repository, read like any other evidence.

Call the operator only when the decision is theirs and you cannot settle it: an Evidence first
verdict whose unknown only they can answer; a pick that is hard to reverse (public contract,
schema, persisted data, dependency, deployment) at medium confidence or lower; or an
authorization only the operator may give, such as `lockctl.py steal --force`. Then:

1. Tell the asking session it is escalated and what it may keep doing meanwhile.
2. `~/.claude/skills/agent-sync/scripts/nag.py start <id> --title "<asking pane>: <decision>"
   --body "<one-line question, the options>"`, with `<id>` in `[a-z0-9-]+` (a short slug of the
   decision, not a pane id). It repeats a herdr notification every 5 minutes until stopped, and
   stops by itself if this session ends.
3. When the operator answers in this pane, `nag.py stop <id>`, then send the verdict, with their
   answer folded into Part 3, to the asking session.

After a compaction or `/clear`, run `nag.py list`: a nag you no longer remember keeps firing until
you answer its question or stop it.

Everything else gets a verdict without the operator, with its confidence stated.
