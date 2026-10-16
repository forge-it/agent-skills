# Ticket templates

The team's conventions for RDNX tickets, adapted from the SDSM *WoW - Backlog items* pages
for an internal technical project. The user-facing Epic and Feature model there is not
used.

## Title

`[Area] Imperative description`

- `[Area]`: the part of the system the work is in, proposed for each ticket from what it
  touches: a crate or component (`[adapter]`, `[core]`, `[proto]`), a concern (`[CI]`,
  `[docs]`, `[tests]`, `[packaging]`) or an RPC (`[InstallGroup]`). Reuse an area an open
  ticket on the board already uses for the same part, so titles stay searchable.
- Then an imperative, sentence case, no trailing period: `[CI] Add the merge request pipeline`,
  `[adapter] Return an error when the repository cache is corrupt`.
- At most about 70 characters. The title says what changes, not how it is built.

## Enabler

The body says WHY: an Enabler with no stated benefit (cost, risk, speed, unblocked work) is
incomplete.

```
## Problem definition
What problem this solves and why it matters now: what it costs, risks or blocks today.

## Solution definition
The chosen solution, briefly, in terms of what changes (crates, files, recipes, docs).

## Possible solutions
- <the chosen one> (chosen): why
- <an alternative>: why not

## Initial scope
- In: …
- Out: …

## Acceptance criteria
- [ ] <a checkable statement: a behaviour, a file or doc that exists, a command that passes>
- [ ] the repository's gate is green (`just quality-gate` in rdnx); drop this line for work
      that changes no repository
```

Acceptance criteria are what a reviewer ticks off against the merge request: each one names
something observable, never an activity ("investigate", "look into").

## Bug

```
## Observed
What happens: the error text, exit code or log lines, quoted.

## Expected
What should happen, and where that is specified (RFD, ADR, proto, ticket), as a path or key.

## Steps to reproduce
1. …
2. …

## Environment
Commit or image tag, host (REC, lab, local Docker), configuration.

## Impact
Who is affected and how badly; the workaround, if any.
```

A Bug states one defect. Two symptoms with one cause are one Bug; one symptom with two
causes is two Bugs once both causes are known.

## Story

A Story is tested after it is built, so every acceptance criterion must be testable.

```
As <the consumer: REC, an operator, a calling service>,
I want <the capability>,
so that <the value it gives them>.

## Acceptance criteria
- Given <context>
  When <action>
  Then <observable outcome>
- …
```

The criteria say what is accepted, never how it is built. A Story whose only content is an
implementation step is an Enabler.

## Story points

Give a real estimate: the effort for one developer to deliver and get the work reviewed, on
the scale 1, 2, 3, 5, 8. About 2–4 days is a 3 or a 5. More than 8 means split the ticket.
He changes the number when he disagrees. `points_reason` says in one line what drives the
number; it stays in the draft.

## Links

`createJiraIssueLink` takes the site's link-type name and reads
"`inwardIssue` <outward wording> `outwardIssue`", so with `Blocks` the inward issue blocks
the outward one:

| Front matter wording | Meaning | `linkType` | `inwardIssue` | `outwardIssue` |
|---|---|---|---|---|
| `relates to X` | related work, a split of one piece of work, a follow-up of a Done ticket | `Relates` | this | X |
| `blocks X` | this must finish before X can start | `Blocks` | this | X |
| `is blocked by X` | X must finish before this can start | `Blocks` | X | this |
| `resolves X` | this fixes Bug X | `Resolve` | this | X |
| `is driven by X` | requirement or decision X drives this | `Requirement: Drive` | X | this |
| `duplicates X` | this duplicates X | `Duplicate` | this | X |

Link to every ticket the source names. A ticket from a review finding links to the ticket of
the MR it came from with `Relates`.
