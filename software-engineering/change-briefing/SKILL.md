---
name: change-briefing
description: "Use when the operator wants to be caught up on a change before reviewing it — /change-briefing, \"brief me on this ticket\", \"catch me up on this branch\", \"what did the agents do\", \"explain this merge request before I review\" — most often at a ticket delivery's review gate, also on any branch, merge request, commit range or uncommitted tree that agents wrote. NOT for teaching a whole topic (teach-schematic), for the review itself or posting review notes (roche-mr-review), or for reviewing the code itself."
argument-hint: "[ticket key | branch | MR | commit range] [page]"
---

# Change briefing

One message, at most 3500 characters. Its first half makes the change understood by a reader
who knows programming but not this repo or its domain: the point, how the system works, the
problem, what was asked, what was done. Its second half makes it reviewable: the option
chosen, the trade-offs, what to veto, where to start.

## 1. Find the change

The target is the argument when one is given: a ticket key, branch, MR (`!n` or URL) or
commit range. Otherwise it is the ticket this session is delivering, else the current
repository's branch and uncommitted tree. When none of these resolves, or the change set
below is empty, ask one question: which change.

Settle four things first. `<target>` below is the branch the change goes into:
`origin/<the MR's target branch>`, else `origin/<the ledger's base branch>`, else what
`git -C <checkout> symbolic-ref --short refs/remotes/origin/HEAD` prints.

- **The checkout** holding the change:
  - a ticket: the ledger's last *Checkout holding the change* entry, while
    `git -C <checkout> branch --show-current` prints the ledger's work branch. A ledger can
    name a worktree removed since, or the main checkout, which moves on to the next ticket;
    then `<checkout>` is the repository the ledger lists, and the change is found by its
    work branch, or by its commit once merged, as below.
  - a branch: the worktree `git worktree list` shows it checked out in, if any.
  - an MR: `wt/` in `~/.cache/roche-mr-review/<repo>-<iid>/` when roche-mr-review set one
    up; else run `git -C <repo> fetch origin <source branch>`, the one state change this
    skill makes, and the MR's head is `origin/<source branch>`.
  - else the current repository.
- **The head:** the checkout's working tree, dirty files included, when the checkout is on
  the change's branch or the target is the current tree. Otherwise a commit:
  - merged (the ledger's stage or the MR says so): the `squash_commit_sha`, else the
    `merge_commit_sha`, that the ledger or MR records; else the one commit that
    `git -C <checkout> log --no-merges --format=%h --grep <KEY> <target>` prints, or for a
    merge commit the same with `--merges --first-parent` in place of `--no-merges`. Several
    or none: ask.
  - a branch: its last commit, `origin/<branch>` when no local branch has it.
  - a commit range or an MR: its last commit.

  Below, `<head>` is `HEAD` for a working tree, else that commit; `<range>` is `<base>` for a
  working tree, else `<base> <head>`.
- **The base, as a commit:**
  - a commit range: its left end. A merged change: `<head>^1`.
  - otherwise the SHA a record gives: the ledger's base line (`base main @ 572b1de` is
    `572b1de`; `base: <branch> (… at a8e1f19)` is `a8e1f19`), or an MR's `base_commit` (its
    folder's `meta.json`, else its `diff_refs` from the forge API). Check it against `<mb>`,
    what `git -C <checkout> merge-base <head> <target>` prints: when `<mb>` differs and
    `git -C <checkout> merge-base --is-ancestor <sha> <mb>` succeeds, the change was rebased
    onto its target or merged it in since, and `<mb>` is the base. With no record, `<mb>`
    is the base.
  - when none works, ask. Never a branch tip, which moves past the change, and never
    `git remote set-head`.
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
| A ticket-delivery run folder, `~/.cache/roche-ticket-delivery/<KEY>/` or `~/.cache/ticket-delivery/<KEY>/`. A run is named after its first ticket or parent story; for any other ticket, `grep -l <KEY> ~/.cache/*ticket-delivery/*/ledger.md` finds it | `ticket.md`: the background (how the system really runs, and its terms), the problem, the acceptance criteria. `options.md`: chosen and rejected options, the locked scope. `ledger.md`: base, checkout, and every decision it records as the operator's. `plan.md`: its headings, plus in full any section whose heading says *amendments* or *operator decisions*, and each open question those sections settle by number (`Q2, Q4-Q8: the defaults stand`); the rest can be huge |
| An MR folder from roche-mr-review, `~/.cache/roche-mr-review/<repo>-<iid>/` | `ticket.md`: the spec. `mr-description.md`: the author's account. `meta.json`: `ticket_key`, `source_branch`, `merge_request_iid` |
| The Jira ticket and the MR description, when neither folder exists | the problem, the chosen option |
| The diff and the untracked files | what changed, every `file:line` |
| A test's output or evidence file, when a test checks the change | the thing itself as it really looks (a generated rule, a request, a log line) and the latest result |
| An ADR, RFD or doc the ticket cites | why, and how the system runs for its real users |

The operator's decisions are the locked scope, what the ledger and the plan's amendments
record as theirs, and what this session shows them saying. The plan is the agents' work: it
counts as the operator's only where one of those records approval. Every claim about code
comes from the diff or from `<head>`'s tree (`git -C <checkout> show <head>:<path>` when the
checkout is not on it). Whatever the code does beyond the operator's decisions, plan or no
plan, goes under AGENT CALLS.

## 3. Write the briefing

Exactly these parts, in this order:

```
<KEY, or the branch when there is no ticket> · <what the change does, at most 8 plain words>
<repo> <branch; for an MR "!<iid> <source branch>"; else "detached at <sha7>"> vs <base sha7> · <N> files, <k> new (+<a> −<d>) · <committed | uncommitted | committed + uncommitted>[, merged <date> as <sha7>]

IN ONE LINE
<one sentence, at most 3 lines: what changes for whom, and how it is proven or shipped>

1 HOW IT WORKS
<diagram, at most 8 lines: the system as its real users run it, who or what calls whom,
 with a ▲ line under the part this change is about, saying so>

2 PROBLEM
<at most 3 lines: what is wrong today, and what it lets happen>

3 WHAT THE TICKET ASKS                  (no ticket: 3 WHAT THE CHANGE IS FOR)
a. <a deliverable> — <why>                                         at most 3 lines

4 WHAT WE DID
<the one concrete thing the change is about (a rule, a command, a signature, a payload),
 before → after, at most 4 lines with └─ glosses; left out when there is no such thing>
<the new behaviour as at most 6 steps, each with its expected result (→ works ✔,
 → refused ✔, → same as before ✔); each step names the file that carries it, once, in
 parentheses>
unchanged: <what a reader would expect to change and does not>

──── for the review ────
CHOSEN
✔ <the option the operator picked> — <why, one line>
  ↳ then <what the operator changed later> — <why> (operator, <date>)
✘ <option rejected> — <why not, one line>        one line per rejected option

TRADEOFFS
- <a cost, risk, limit, or deferred item with its ticket or gap id>       at most 3

AGENT CALLS — veto here
- <path:line> — <a decision the operator never made: a departure from the plan or the
  locked scope, scope read one way, work beyond the acceptance criteria, a structure or
  name picked>

START AT <path:line> — <why it is the core>, then <path>
```

The first half, as it should read (NIFS-13999; match the shape, not the topic):

```
IN ONE LINE
The operator guide now shows "app may run exactly this rdnx command" instead of "app may
run rdnx as root however it likes"; a new test proves that rule still lets REC start rdnx
and blocks everything else.

1 HOW IT WORKS
REC's container, in production
  REC (runs as normal user "app")
    │ "start rdnx for me, as root"
    ▼
  sudo ── reads a rule file: what may "app" run as root?
    │       ▲ this change is about that rule
    ▼
  rdnx serve …  (runs as root, installs packages)

2 PROBLEM
The rule says "app may run rdnx as root, with any arguments". Anyone who breaks into REC
can start rdnx as root with another install directory, another repository, or caller
checks off. The design doc (RFD-0001) says: allow only REC's exact command line.

3 WHAT THE TICKET ASKS
a. put that safer rule in the operator guide — the people building REC's container copy it
b. prove it works — so the guide never ships a rule that breaks REC or is mis-written

4 WHAT WE DID
before: app ALL=(root) NOPASSWD: /usr/local/bin/rdnx
        └─ no arguments listed = any arguments allowed
after:  app ALL=(root) NOPASSWD: /usr/local/bin/rdnx serve …
        └─ only REC's exact list; anything else is refused
A new test scenario, `pinned` (tests/reclike/run.sh), in a container built like REC's:
  exact rule in place: REC starts rdnx through sudo   → works   ✔
  one argument added, removed or changed              → refused ✔
  sudo /bin/sh, sudo rpm, sudo dnf                    → refused ✔
The rule is generated from the scenario's own arguments (tests/reclike/sudoers_rule.py);
the guide's old rule becomes the exact-list template (docs/operations.md).
unchanged: the REC-like image and its eight other scenarios keep the any-arguments rule
```

- **Write for an outsider.** The reader knows programming, not this repo, its tests or its
  domain. Say what a flag, file or term does: "another install directory", not
  `--installroot`. Before counting, reread the message as that reader: each word they would
  have to ask about gets plain words or a gloss.
- **HOW IT WORKS** draws the system as its real users run it: production, not the test
  harness or the repo layout, which belong in WHAT WE DID. For a tooling change the users
  are the developers: draw what they run and what it calls.
- **Code names.** In the first half, a name the reader will meet in the code or docs (a
  scenario, flag, function, error code, file, doc id, or a domain term the code uses)
  appears once, right after its plain words: "a new test scenario, `pinned`
  (tests/reclike/run.sh)", "the design doc (RFD-0001)". The second half gives exact
  references after the plain words: a `file:line`, a gap, ADR, RFD, error or ticket id, the
  exact function, flag or field, never "the handler" or "the config". Everything a run
  labels (triage ids, finding numbers, round numbers, amendment numbers, question numbers)
  is said as the decision itself.
- **Count it.** Write it to the session scratchpad and run `LC_ALL=en_US.UTF-8 wc -m` on
  the file (characters, not bytes): at most 3500. Over that, cut in this order: TRADEOFFS
  to two lines; the ✘ lines beyond the two strongest, folded into one
  `✘ also rejected: <a>; <b>` line without reasons; each ↳ line to its change in five
  words; each ✘ reason to five words; each AGENT CALLS entry to its `path:line` and the
  decision in five words; then wording anywhere. Every part stays, AGENT CALLS keeps every
  entry, and WHAT WE DID keeps its before → after.
- **Diagrams** go in ```` ```text ```` fences, so the terminal keeps their alignment, with
  no line over 70 columns.
- **CHOSEN** has one ✔ per ticket. A `↳` line is for a change of approach the operator
  approved; a change the agents made alone is an AGENT CALLS line. A ✘ reason is that
  option's own cost or weakness, never "the operator picked another"; when no record gives
  one, write one marked `(my reading)`.
- **AGENT CALLS** lists a decision the operator could veto because it has a cost or an
  alternative. The mechanical consequence of a decision the operator made is not one.
- A part with nothing true to say is one line: `AGENT CALLS — none found`. When no options
  were recorded, give the obvious alternative and why not, marked `(my reading)`.
- Anything inferred rather than read in a source is marked `(my reading)`.
- Consequences are concrete: "each run builds one more image", not "slower".

Several tickets on one branch: one briefing for the change. The header lists every key;
PROBLEM and WHAT THE TICKET ASKS give one line per ticket (`<KEY> — …`), and CHOSEN one ✔
per ticket. Tickets on separate branches: one briefing per branch. A change across several
repositories: one header line per repository, and WHAT WE DID says which steps happen in
which, inside the same cap.

## 4. After it

Stop and wait. Answer each question the same way: plain words first, a diagram when there
is a flow, `file:line` when it points into the code, a few lines. A question about what a
word means, or why something exists, shows the briefing assumed too much: answer from HOW IT
WORKS, in domain words, before the detail. When an answer shows the briefing was wrong, say
so ("the briefing was wrong about X") and give the correction.

A rename, veto or change the operator asks for belongs to the workflow that owns the change
(a ticket delivery's refactor-or-commit stage), not to this skill. With no such workflow,
ask who makes the edit.

## Page mode

With `page` in the arguments, or when the operator asks for something visual, also write the
briefing as one self-contained HTML file, `briefing-<KEY, else the branch with each / as
->.html`, in the run folder when there is one, else the session scratchpad, and open it
(`open` on macOS, `xdg-open` on Linux). Same parts, no character cap. Diagrams are inline
SVG, with the ▲ part of HOW IT WORKS highlighted. WHAT WE DID's steps are a step-through:
Prev and Next highlight one step at a time and show its file and one plain sentence on what
it does. Load **artifact-design** and **artifact-diagramming** for the design, the light and
dark tokens and the SVG, but write a complete document yourself: `<!doctype html>`,
`<meta charset="utf-8">`, a viewport meta, a `<title>`, system fonts, no external script or
stylesheet. Their rules to leave out the document tags and to link Google Fonts are for a
published page. It stays a local file, since it quotes the company's code; publish it as an
Artifact only when the operator asks.
