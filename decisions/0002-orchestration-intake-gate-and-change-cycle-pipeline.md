# ADR 0002: Orchestration intake gate and the change-cycle pipeline

- **Status:** Accepted
- **Date:** 2026-07-31
- **Affects:** `agent-fleet-orchestration` (0.0.1 → 0.0.2), new `change-cycle-pipeline` (0.0.1), `code-change-workflow` (0.1.0 → 0.1.1)

## Context

The way non-trivial work actually runs in this fleet had never been written
down. In practice it takes one of nine shapes — vibe or supervised, orchestrator
or fleet implementing, review depth from gate-only to a full review → verify →
fix loop, an operator gate per cycle or at the end, and a plan / plan-review /
code-review branch that changes code at all.

Three problems followed from leaving that unwritten.

**Nothing owned the intake decision.** Supervision level, round cap, and gate
cadence were settled ad hoc per task, or not at all.

**Nothing owned the delivery pipeline.** Cycle cutting, the shared brief,
integration of parallel worktrees, and the review loop lived only in
hand-authored workflow scripts, re-written per phase. The reference
implementation (`phase-02b-full-review-x.js` in the ironbox repo) carried four
defects that a written pipeline would have prevented:

1. Round-local dedup and unused history — round 2 re-raises what round 1
   refuted, re-pays for verification, and can flip the verdict.
2. A round where reviewers died could still return `stopped: 'zero-findings'`.
3. Dedup keyed on `file:line:title` merges nothing, so one defect under two
   titles becomes two candidates, two verifiers, and two possibly-conflicting
   fixes — and corroboration, the strongest prioritisation signal, is lost.
4. Reaching the round cap had no defined failure semantics.

**Three of the nine shapes contradicted an existing skill.** The orchestrator
implements in three of them, while `agent-fleet-orchestration`'s Red Flags table
said, unconditionally, to stop and dispatch at the second file edit.

## Decision

**The intake gate and mode selection go in `agent-fleet-orchestration`.** It is
already the entry point for every non-trivial task, and the gate runs before the
deliverable is even known — putting it elsewhere would make the fleet skill
point at another skill to decide whether the fleet skill applies.

**The delivery pipeline goes in a new `change-cycle-pipeline` skill.** Only the
code-change shapes need it; loading ~300 lines of cycle and loop machinery for a
plan review is waste (ADR 0001 principle 3, progressive disclosure).

**The read/write boundary becomes mode-scoped, edited where it lives.** In fleet
modes it is unchanged. In implementer modes the orchestrator writes, and the old
red-flag threshold becomes a *promotion trigger*: second file, a test change, or
a gate loop means promote to a fleet mode and say so. Fixing this in the fleet
skill rather than overriding it from the new skill keeps two accepted documents
from disagreeing.

**The gate asks along eight orthogonal axes, not from a nine-item menu.**
Supervision, implementer, review depth, pipeline variant for a plan or code
review, spec input for those same deliverables, round cap, operator gate cadence,
and parallelism — three or four questions in practice, since most are conditional
on the deliverable. All nine observed shapes are reachable as combinations, and
unnamed combinations stay legitimate.

**Vibe mode has no escalation.** Full power to the orchestrator, per the
operator's explicit decision. Two obligations survive: record every decision that
would otherwise have been a question, and never report a round cap as a pass.

**The operator's parallelism answer is a ceiling, not a floor.** Serial work runs
serially regardless, with a one-line disclosure — the override is sanctioned, the
silence is not.

**The round cap is an operator parameter** (N rounds, or until zero findings),
asked at intake, and reaching it is a failure with a residue report.

## Rejected alternatives

**Everything into `code-change-workflow`** — the file the request originally
named. Rejected: it is the leaf contract for a single change, including a
one-line fix with no fleet, and it is loaded as an always-on skill by at least
one agent. Orchestration content there is read by workers that cannot act on it,
and it would duplicate the fleet skill on parallelism, worktrees, and commit
policy. Its real advantage — one file to find, and the trigger conditions do
overlap — is bought back by a three-line pointer.

**Everything into `agent-fleet-orchestration`.** Genuinely simpler to locate, and
no cross-skill delegation to keep consistent. Rejected on load cost: a ~400-line
skill read in full for a plan review that needs none of the pipeline.

**Everything into the new skill, leaving the fleet skill untouched.** Rejected
outright: the new skill would permit orchestrator-as-implementor while the
untouched fleet skill still forbade it.

**A nine-mode menu as the intake interface.** Maps directly onto how the shapes
were described, which is a real advantage for talking about them — the mode table
in the fleet skill keeps that vocabulary. Rejected as the *interface*: a
nine-item menu on every task, and each new combination needs a new mode number.

## Consequences

- Every non-trivial task opens with an explicit gate. Cheap, and it is the only
  interactive moment vibe mode has.
- Per-cycle prompt authoring largely disappears: the Cycle Brief is written once
  and reused verbatim by implementor, reviewers, verifiers, fixer, and gate,
  replacing the hand-written `SCOPE` constant pattern.
- Review lenses are generated from `prompts/code-implementation-review/` instead
  of hand-authored per phase, so the automated loop and the manual pipeline stop
  drifting apart.
- Existing hand-written workflow scripts still carry the four defects. They are
  corrected when next touched; the pipeline skill is now the authority.
- `code-change-workflow` keeps its scope and gains a pointer. Per ADR 0001 the
  rewrite freeze applies to rewrites of existing skills, so the fleet skill was
  extended in its own voice rather than restyled, and only the new skill is
  written to the ADR 0001 pattern.
