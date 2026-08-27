---
name: syneto-release-notes-scoped
description: Use when producing or publishing a Syneto Central release notes entry restricted to repositories the operator names — a single-repository hotfix or any subset of the fleet — including asks phrased as "release notes for <repo>", "notes for just the rest-api fix", or "scoped release notes". Requires an explicit repository list; if the ask names no repositories, ask the operator for the list or use syneto-release-notes for the whole fleet. Syneto-specific: assumes the Central repository family under /home/cristi/Projects and the CEN Confluence space.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.1"
---

# Syneto Scoped Release Notes Skill

## Purpose

Produce the release notes entry for a Syneto Central release **restricted to the
repositories the operator names**, and publish it to the same Confluence page, in
the same format, as the fleet-wide skill. The usual case is a hotfix shipping from
one or two repositories while the rest of the fleet's range keeps accumulating.

## This Skill's Own Script — Never the Parent's

`acquire.sh` sits beside this SKILL.md. Resolve its absolute path first — the
working directory when this skill fires is the operator's project, not the skill
directory.

```bash
/home/cristi/Projects/agent-skills/software-engineering/syneto-release-notes-scoped/acquire.sh <repository> [<repository>...]
# explicit pair:      SYNETO_NOTES_PAIR="central-2.9 central-2.10" ... acquire.sh <repository>...
# offline dry run:    SYNETO_SKIP_FETCH=1 ... acquire.sh <repository>...
# tolerate SOME empty selected ranges:  SYNETO_ALLOW_EMPTY_SELECTION=1
```

**This skill never runs `syneto-release-notes/acquire.sh`.** The parent's script
takes no repository arguments and scans the whole fleet; running it here produces
a sixteen-repository corpus for a one-repository ask. If the operator has not
named any repository, **ask for the list** — a missing repository set is a
question to the operator, never a fallback to the fleet.

**If the script exits non-zero, stop. Do not publish. Report the stderr text.**
The script's own header enumerates its exit causes — they include several the
parent does not have (a selected repository whose pair does not resolve, a
selected fetch failure, an empty range in a selected repository). Read the stderr
text rather than the parent's cause list.

## The Parent Skill Is the Base Contract

Read
`/home/cristi/Projects/agent-skills/software-engineering/syneto-release-notes/SKILL.md`
before doing anything else in Stages 2–4. **Every rule there applies unless
amended below** — the page, the titles, the stage shape, the publish-and-verify
mechanics, and the audience are all the parent's. The table lists all eight rules
by number and title so none is silently dropped; the amendments follow.

| Parent rule | Status under scope |
|---|---|
| R1 — Never Touch a Worktree | **Unchanged.** |
| R2 — Fetch Before Reading | **Amended:** fetch failures split by scope (see below). |
| R3 — Discover Repositories, Never List Them | **Amended:** the operator list selects FROM discovery (see below). |
| R4 — One Theme Per Entry, Not One Ticket | **Amended:** brackets, theme grouping, and `[platform]` under scope (see below). |
| R5 — Ticket IDs: Subjects Only, SYN- and CENTRAL- Only | **Amended:** the subject union is scoped; OUTSIDE never promotes (see below). |
| R6 — Already-Published Tickets Are Excluded, Not Flagged | **Unchanged** — including its partial-scope exception, which scoped entries are the usual source of. |
| R7 — Mirror the Top Three Entries | **Amended:** a same-day entry is extended, not duplicated (see below). |
| R8 — Verify the Publish and Self-Report Failure | **Amended:** check 3 changes when extending a same-day entry (see below). |

## R3 Amended — The Operator List Selects From Discovery

The parent's R3 forbids a hand-maintained inclusion list because it silently
rots. The operator's repository list is not that: it is a **per-run selection
from discovery**, expiring with the run. What survives of R3:

- Discovery still runs fleet-wide inside `acquire.sh`, and still drives the
  branch pair, the quorum guard, and the `OUT OF SCOPE` bucket.
- A named repository that cannot resolve the pair even after fetching is
  **fatal**, never silently dropped — the script enforces this.
- `bi-tool` stays out of scope by decision. `central` participates only when the
  operator names it, but is always fetched and classified so its subject ids
  appear in the `OUT OF SCOPE` bucket.
- A retired repository named explicitly is emitted with a warning rather than
  refused — matching `promote.sh`: the retired list governs discovery, and an
  operator's explicit name is not discovery.

## Scope Semantics — OUTSIDE Records and Partial Shipping

The script emits one extra record type:

```
OUTSIDE	<repository>	<commit-count>	<space-separated subject ids>
```

`OUTSIDE` records describe contributing repositories **outside** the selection.
They exist for exactly three decisions and are never release content:

1. **Partial shipping (R5 amendment).** The subject union of R5 is computed over
   the **selected** `TICKETS` records only. A selected `TICKETS` id that also
   appears in any `OUTSIDE` ids is **partially shipping**: part of its work stays
   on the dev branch of an unselected repository. Include it in the entry, but
   apply the bracket, text, and provenance rules below. An id appearing only in
   `OUTSIDE` records is not in this release at all. An `XREF` id is never
   promoted by an `OUTSIDE` appearance — out-of-scope subjects are not shipping
   subjects.
2. **`[platform]` arbitration (R4 amendment).** The parent's "`[platform]`
   applies only when `central` is the sole contributor" is evaluated
   **fleet-wide**: if `central` is selected and sole contributor among the
   selected repositories, but the ticket also appears in a product repository's
   `OUTSIDE` ids, do not tag `[platform]` — the change has an unshipped product
   half. Treat it as partially shipping instead.
3. **The provenance report**, which lists what the scoped entry deliberately
   omits.

Note on `central`'s `OUTSIDE` ids: its range is not release-scoped (the parent's
R3 explains this) — it accumulates everything unpromoted, so its `OUTSIDE` ids
reach further back than the product range. Use them for the two decisions above,
never as evidence that a ticket is "in" the next release.

## R4 Amended — Brackets, Themes, and Entry Text Under Scope

- **The bracket lists selected repositories only** — what actually ships. An
  unselected repository never appears in a bracket, even when it owns the
  user-visible surface. The bracket is led by the selected repository nearest
  the user-visible surface; the rest follow in any stable order.
- **Themes group over selected tickets only.** A theme split across the scope
  boundary — some tickets selected, some only in `OUTSIDE` ids — is a partially
  shipping theme.
- **The entry text must say what actually ships.** The provenance report never
  reaches Confluence, so for any partially shipping ticket or theme the
  qualification goes **into the entry text**, in the page's established voice —
  describe the capability the selected repositories deliver now, not the full
  capability that finishes when the remainder ships. Publishing the unqualified
  claim tells stakeholders something works that does not yet.
- The parent's skip list (reverts, refactors, chores, doc edits) applies
  unchanged to the selected repositories' commits.

## R7 and R8 Amended — A Second Entry on the Same Day

Scoped hotfixes are the entries that can happen twice in one day, and the titles
carry only a date. If the page already has an entry with the identical title and
date:

- **Extend that entry's Features / Bug Fixes lists** with the new bullets — do
  not add a second entry with the same title. Two identical titles make the
  parent's R8 count ambiguous.
- R8 check 3 becomes: **the entry-title count is unchanged, and the target
  entry's bullet count increased by exactly the number of bullets added.**
  Checks 1 and 2 (entry present, links rendered as inline cards) are unchanged.

Otherwise R7 and R8 apply exactly as the parent states them — same titles
(`Production Hotfix Plan (YYYY-MM-DD)` / `Production Release Plan (YYYY-MM-DD)`),
same top-three-entries mirroring, never invent a new title for a scoped entry.

## R2 Amended — Fetch Failures Split by Scope

The script partitions fetch failures:

- A fetch failure in a **selected** repository is fatal — the script already
  stopped; do not work around it.
- Failures listed under `FETCH FAILURES — OUT OF SCOPE` degrade only the
  `OUTSIDE` bucket: partial-shipping detection may miss those repositories. Say
  so in the provenance report, and do not refuse to publish over them.

## Enrichment at Small Scale

The parent's Stage 2 fleet sizing assumes 40–50 tickets. A scoped run usually
has far fewer. **Below roughly eight tickets, enrich inline — no subagents.** At
or above that, batch as the parent describes.

## Handoff to Promotion

A scoped entry must ship through a **scoped** promotion. End the final report to
the operator with the exact invocation, so a later session cannot accidentally
promote the fleet:

```bash
/home/cristi/Projects/agent-skills/software-engineering/syneto-release-promote/promote.sh --check <repository> [<repository>...]
# pin the pair the notes described:
SYNETO_PROMOTE_PAIR="<prod> <dev>" ... promote.sh --check <repository>...
```

Name exactly the repositories in the published entry's brackets. If the operator
selected `central`, remind them the promote skill excludes `central` by default
(`SYNETO_INCLUDE_CENTRAL=1`, and it does not promote `central` on its own — it
runs on a separate cadence).

## Provenance Report Additions

Everything the parent's provenance report lists, plus:

- The selected repository set exactly as supplied, and anything normalised or
  deduplicated from it
- Out-of-scope contributing repositories with commit counts (the `OUTSIDE`
  bucket) — what this entry deliberately does not describe
- Partially shipping tickets and themes: the id, the selected repositories that
  ship, the out-of-scope repositories that do not, and how the entry text was
  qualified
- Selected repositories with empty ranges that were waived via
  `SYNETO_ALLOW_EMPTY_SELECTION=1`, with the script's already-promoted /
  nothing-in-range discrimination
- Retired repositories that were named explicitly and proceeded with a warning
- The exact scoped promote invocation handed to the operator

## Common Mistakes

| Mistake | Consequence |
|---|---|
| Running the parent's `acquire.sh` because no repositories were named | A fleet-wide corpus for a scoped ask; the entry describes work that is not shipping |
| Defaulting to all repositories instead of asking for the list | Same — the missing list is the operator's to supply |
| Grepping `^TICKETS` and catching `OUTSIDE` ids | Out-of-scope work published as shipping (the record name exists to prevent this — keep the anchored grep) |
| Bracketing an unselected repository because it owns the surface | The page claims a repository shipped that did not |
| Publishing the full capability claim for a partially shipping ticket | Stakeholders told a feature works before its surface ships |
| Promoting an `XREF` id because it appears in `OUTSIDE` subjects | Out-of-scope shipping status leaking into this entry |
| Tagging `[platform]` because `central` is the only selected contributor | The unshipped product half is hidden by scope |
| Adding a second same-titled entry on the same day | R8's title count turns ambiguous; the page grows duplicate titles |
| Handing off to an unscoped promote | The fleet ships against notes that describe one repository |
