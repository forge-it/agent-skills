---
name: change-briefing
description: "Use when the operator wants to be caught up on a change before reviewing it — /change-briefing, \"brief me on this ticket\", \"catch me up on this branch\", \"what did the agents do\", \"explain this merge request before I review\" — most often at a ticket delivery's review gate, also on any branch, merge request, commit range or uncommitted tree that agents wrote. NOT for teaching a whole topic (teach-schematic), for the review itself or posting review notes (roche-mr-review), or for reviewing the code itself."
argument-hint: "[ticket key | branch | MR | commit range] [page]"
---

# Change briefing

One message, at most 3000 characters, in the parts below, so the operator reviews a change
agents wrote knowing what it solves, why it has this shape, and what to veto. Diagrams
carry it.

## 1. Find the change

The target is the argument when one is given: a ticket key, branch, MR (`!n` or URL) or
commit range. Otherwise it is the ticket this session is delivering, else the current
repository's branch and uncommitted tree. When none of these resolves, or the change set
below is empty, ask one question: which change.

Settle four things first; the header prints them:

- **The checkout** holding the change:
  - a ticket: the ledger's last *Checkout holding the change* entry, while
    `git -C <checkout> branch --show-current` prints the ledger's work branch. A ledger can
    name a worktree removed since, or the main checkout, which moves on to the next ticket;
    then go by the work branch, as below.
  - a branch: the worktree `git worktree list` shows it checked out in, if any.
  - an MR: `wt/` in `~/.cache/roche-mr-review/<repo>-<iid>/` when roche-mr-review set one
    up; else run `git -C <repo> fetch origin <source branch>`, the one state change this
    skill makes, and the MR's head is `origin/<source branch>`.
  - else the current repository.
- **The head:** the checkout's working tree, dirty files included, when the checkout is on
  the change's branch or the target is the current tree. For a commit range, an MR, or a
  branch no checkout has, its last commit. Below, `<head>` is `HEAD` for a working tree,
  else that commit; `<range>` is `<base>` for a working tree, else `<base> <head>`.
- **The base, as a commit:** the SHA the ledger records as the base, its *Review base* entry
  when it has one, else its base line (`base main @ 572b1de` is `572b1de`;
  `base: <branch> (… at a8e1f19)` is `a8e1f19`). That SHA is stale when
  `git -C <checkout> log --merges --first-parent --format=%h <sha>..<head>` prints a commit,
  because the change merged its target in since; then use the merge-base below. With no
  ledger: an MR's `base_commit` (its folder's `meta.json`, else its `diff_refs` from the
  forge API), or a range's left end. Else `git -C <checkout> merge-base <head> <target>`,
  where `<target>` is `origin/<the MR's target branch>`, else what
  `git -C <checkout> symbolic-ref --short refs/remotes/origin/HEAD` prints. When none works,
  ask. Never a branch tip, which moves past the change, and never `git remote set-head`.
- **The change set:** `git -C <checkout> diff --numstat <range>`, plus, for a working tree,
  the untracked files that `git -C <checkout> status --short --untracked-files=all` lists.
  Untracked files count as new, and each one's `wc -l` adds to the `+`; the other new files
  are what `git -C <checkout> diff --diff-filter=A --name-only <range>` lists. The header
  says `committed` when commits lie between base and head, `uncommitted` when the status
  lists a path, `committed + uncommitted` when both hold.

Read only: no edits, builds, tests, or git commands that change state, except the MR fetch
above.

## 2. Read the story, then the code

| Source | Read it for |
|---|---|
| This session's conversation, when it delivered the change | the problem, the options, what the operator said, what changed on the way |
| A ticket-delivery run folder, `~/.cache/roche-ticket-delivery/<KEY>/` or `~/.cache/ticket-delivery/<KEY>/`. A run is named after its first ticket or parent story; for any other ticket, `grep -l <KEY> ~/.cache/*ticket-delivery/*/ledger.md` finds it | `ticket.md`: problem, background terms, acceptance criteria. `options.md`: chosen and rejected options, the locked scope. `ledger.md`: base, checkout, and every decision it records as the operator's. `plan.md`: its headings, plus in full any section whose heading says *amendments* or *operator decisions*; the rest can be huge |
| An MR folder from roche-mr-review, `~/.cache/roche-mr-review/<repo>-<iid>/` | `ticket.md`: the spec. `mr-description.md`: the author's account. `meta.json`: `ticket_key`, `source_branch`, `merge_request_iid` |
| The Jira ticket and the MR description, when neither folder exists | the problem, the chosen option |
| The diff and the untracked files | what changed, every `file:line` |
| An ADR, RFD or doc the ticket cites | why |

The operator's decisions are the locked scope, what the ledger and the plan's amendments
record as theirs, and what this session shows them saying. The plan is the agents' work: it
counts as the operator's only where one of those records approval. Every claim about code
comes from the diff or the current tree. Whatever the code does beyond the operator's
decisions, plan or no plan, goes under AGENT CALLS.

## 3. Write the briefing

Exactly these parts, in this order:

```
<KEY, or the branch when there is no ticket> · <title, at most 8 words>
<repo> <branch; for an MR "!<iid> <source branch>"; else "detached at <sha7>"> vs <base sha7> · <N> files, <k> new (+<a> −<d>) · <committed | uncommitted | committed + uncommitted>

PROBLEM
<at most 3 lines: what was wrong or missing, who hits it, what it risked>

WHERE IT LIVES
<diagram: the touched components marked *, and the ones they call or are called by>

BEFORE → AFTER
<diagram: the flow that changed>

CHOSEN
✔ <the option the operator picked> — <why, one line>
  ↳ then <what the operator changed later> — <why> (operator, <date>)
✘ <option rejected> — <why not, one line>        one line per rejected option

TRADEOFFS
- <a cost, risk, limit, or deferred item with its ticket or gap id>, one line each

AGENT CALLS — veto here
- <path:line> — <a decision the operator never made: a departure from the plan or the
  locked scope, scope read one way, work beyond the acceptance criteria, a structure or
  name picked>

START AT <path:line> — <why it is the core>, then <path>
```

- **Count it.** Write it to the session scratchpad and run `LC_ALL=en_US.UTF-8 wc -m` on
  the file (characters, not bytes): at most 3000. Over that, cut in this order: TRADEOFFS
  beyond five lines, the reasons on ✘ lines, words in PROBLEM, diagram labels, then each
  AGENT CALLS entry down to its `path:line` and the decision in five words. Every part
  stays, and AGENT CALLS keeps every entry.
- **Diagrams** go in ```` ```text ```` fences, so the terminal keeps their alignment. Boxes
  `[name]`, arrows `──>` labelled with what flows, no line over 70 columns. BEFORE → AFTER
  is two stacked blocks, `before:` then `after:`, one step per line. Each step the change
  replaced or added is marked `*`, with its `file:line` at the right edge: the current
  tree's line, or in `before:` the base's line, written `old file:line`, when the file changed.
- **CHOSEN** has one ✔ per ticket. A `↳` line is for a change of approach the operator
  approved; a change the agents made alone is an AGENT CALLS line.
- **AGENT CALLS** lists a decision the operator could veto because it has a cost or an
  alternative. The mechanical consequence of a decision the operator made is not one.
- A part with nothing true to say is one line: `AGENT CALLS — none found`. When no options
  were recorded, give the obvious alternative and why not, marked `(my reading)`.
- **A reference** is a `file:line`, a ticket key, or a gap, ADR or RFD id. Everything else
  a run labels (triage ids, finding numbers, round numbers, amendment numbers) is said as
  the decision itself, in plain words.
- **A term** gets a gloss of at most 12 words at its first use when the ticket or a doc it
  cites defines it as background, or when this change coins it (a new case, flag, file or
  type): `pinned rule = lists the exact arguments; loose = the command alone`.
- Name the exact thing — function, flag, file, field — never "the handler" or "the config".
- Anything inferred rather than read in a source is marked `(my reading)`.
- Consequences are concrete: "each run builds one more image", not "slower".

Several tickets on one branch: one briefing for the change. The header lists every key,
PROBLEM gives one line per ticket (`<KEY> — <problem>`), and CHOSEN one ✔ per ticket.
Tickets on separate branches: one briefing per branch. A change across several
repositories: one header line, one WHERE IT LIVES and one BEFORE → AFTER per repository,
inside the same cap.

## 4. After it

Stop and wait. Answer each question the same way: a diagram when there is a flow,
`file:line`, a few lines. When an answer shows the briefing was wrong, say so ("the briefing
was wrong about X") and give the correction.

A rename, veto or change the operator asks for belongs to the workflow that owns the change
(a ticket delivery's refactor-or-commit stage), not to this skill. With no such workflow,
ask who makes the edit.

## Page mode

With `page` in the arguments, or when the operator asks for something visual, also write the
briefing as one self-contained HTML file, `briefing-<KEY, else the branch with each / as
->.html`, in the run folder when there is one, else the session scratchpad, and open it
(`open` on macOS, `xdg-open` on Linux). Same parts, no character cap. Diagrams are inline
SVG. BEFORE → AFTER is one step-through over the `before:` steps, then the `after:` steps: Prev and Next highlight one
step at a time and show its `file:line` and one plain sentence on what it does. Load
**artifact-design** and **artifact-diagramming** for the design, the light and dark tokens
and the SVG, but write a complete document yourself: `<!doctype html>`,
`<meta charset="utf-8">`, a viewport meta, a `<title>`, system fonts, no external script or
stylesheet. Their rules to leave out the document tags and to link Google Fonts are for a
published page. It stays a local file, since it quotes the company's code; publish it as an
Artifact only when the operator asks.
