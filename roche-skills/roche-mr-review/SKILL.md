---
name: roche-mr-review
description: Use when the operator asks to review a GitLab merge request on code.roche.com — a merge request URL or !number to review, picked findings to post as review notes, or the review file for the merge request's author — and when resuming such a review in a later session. Roche-specific: assumes glab authenticated to code.roche.com, NIFS tickets through the Atlassian MCP, and repositories under ~/Projects.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.1.0"
---

# Roche MR Review

## Purpose

Review one merge request the way Cristian reviews: a fleet hunts, he decides which findings
are worth the author's time, and only those reach GitLab. He is the reviewer of record —
every note goes out under his name — so nothing leaves the session that he has not picked or
approved.

You orchestrate: set up, run the gate, brief, verify, present, post. Load
**agent-fleet-orchestration** once before the first dispatch. This skill already answers its
intake gate: supervised, the spec is `ticket.md`, the base is `base_commit`, and the briefs
in `references/lens-briefs.md` replace both the pipeline-variant choice and the
code-implementation-review prompts. So the two gates below, his picks and his satisfaction
with the notes, are the only stops.

**Models.** His global instructions set them, and they win over any skill or agent
definition. Pass `model` and `effort` explicitly on every dispatch:

| Role | Model and effort |
|---|---|
| The eight lenses, the synthesizer | `sonnet` at `medium` |
| Refuters (stage 4) | `haiku` at `max`, always |

A model or effort he asks for on this review wins over these. Record it in `meta-notes.md`
in the run directory.

## Stages

| # | Stage | Writes | Gate |
|---|---|---|---|
| 1 | Set up the run | `~/.cache/roche-mr-review/<repo>-<iid>/` | — |
| 2 | Run the repository's gate on the MR head | `gate.md` | — |
| 3 | Review fleet: eight lenses in parallel | `ledger-NN-*.md` | — |
| 4 | Synthesize, refute every Critical and Important, verify the survivors yourself | `ledger-synthesized.md`, `refute-K.md` | — |
| 5 | Present the ledger | — | **his picks** |
| 6 | Post the picked findings as review notes | `notes/`, `posted.json` | — |
| 7 | Refine the notes he asks about | — | **he is satisfied** |
| 8 | Build the developer file; do not send it | `review-mr-<iid>.md` | — |

The scripts live in `scripts/` beside this file. They need Python 3.11 or later, and the
Mac's `/usr/bin/python3` is 3.9, so run them as
`uv run -q --no-project --python 3.13 python -B ~/src/agent-skills/roche-skills/roche-mr-review/scripts/<name>.py`
(`-B` keeps Python from writing `__pycache__` into the skills repository). Each has `--help`.
A later session resumes from the run directory: `meta.json`, `gate.md` and the ledgers carry
the review, and `posted.json` says what is live.

Every repository has an entry in `references/repository-facts.md`: its stack, its gate, its
structure document and its traps. For a repository with no entry, read its CLAUDE.md,
README, justfile and layout, propose an entry to him, and add it once he agrees.

### 1. Set up

Given only `!<iid>`, build the URL from the repository's entry in
`references/repository-facts.md`: `https://code.roche.com/<project path>/-/merge_requests/<iid>`.
Ask him which repository when it is unclear.

`setup_review.py <MR URL>` fetches both branches, puts a detached worktree on the MR head at
`<run>/wt` (the operator's own checkout is never touched), and writes `meta.json` and
`mr-description.md`. It takes the ticket key (`NIFS-<n>`) from the MR title, source branch
or description, in that order, and prints any other keys it saw: ask him which of them
belong to the spec. Pass `--ticket <KEY>` when none carries it.

**A later round.** Rerun `setup_review.py` after the author pushes: it moves the worktree to
the new head and keeps `notes/` and `posted.json`. Reviewing the new head is a new round in
the same run directory. Before its gate, move `gate.md`, `ledger-*.md`, `refute-*.md` and
`review-mr-<iid>.md` into `<run>/round-<N>/`, where N counts the rounds already done. Fill
the synthesizer's `{FIRST}` with one more than the highest finding number in `posted.json` or `notes/`, compared as numbers, so no new finding takes a posted
finding's number and `post_notes.py` never updates a live note with a new finding's text.
Before the new round, ask him about any `notes/NN.md` with no `posted.json` entry: post it
or delete it. A note already posted is edited or withdrawn only on his word.

The run directory must be shared with the session, because the lenses write their ledgers
there. When `~/.cache/roche-mr-review` is not among the session's working directories, ask
him to run `/add-dir ~/.cache/roche-mr-review`. The directory is under `$HOME`, so Colima
mounts the worktree into Docker.

Materialize the ticket into `<run>/ticket.md`, verbatim, with the Atlassian MCP (cloudId
`3ccaad2c-2e75-4a7c-b9aa-c3eddcd6a020`, as markdown): `getJiraIssue` with view `evidence`
for the summary, description, subtasks, links and parent, then every comment with
`listJiraIssueComments` through `executeRead`, paging until the last page. `getJiraIssue`
reports only how many comments there are, and decisions are often agreed in comments. The
server's name changes between sessions, so find the tools by searching for `getJiraIssue`.
With several keys in the spec, materialize each. When the ticket has a parent, add the parent's
description: open questions and design decisions often live there and nowhere else. With no
ticket key, ask him for the spec. With none at all, lens 07 judges contract and migration
only, and the ledger says so.

### 2. Gate

Run the gate that the repository's entry in `references/repository-facts.md` names, once,
yourself, from `<run>/wt`, with any preparation the entry lists (fixtures, a build cache of
its own). No lens builds or tests anything: they all read `gate.md`.

When the gate uses Docker, follow the Docker rule in `references/repository-facts.md`: take
the shared lock, note the containers already there, run in the background, and end the
session in the same turn. A cold gate under emulation can outlast the Bash tool's 10-minute
foreground limit.

Write `<run>/gate.md`: the exact command, the head commit it ran on, the exit status of every
step (and which steps never ran, when the entry's gate stops at the first failure), and for
a red gate every failing step with its failing test ids or diagnostics, verbatim. When the
gate cannot run here (no entry, Docker unavailable, the entry says not runnable), write that
in `gate.md`: the review is static, and everything you present says so.

### 3. Review fleet

Dispatch the eight lenses in `references/lens-briefs.md` in one message. Between them they
cover his hunt list, and their shared preamble carries his scope rule: **new or changed code
only**, never pre-existing code. A finding that breaks that rule is dropped in stage 4.

Fill the briefs from the repository's entry: its stack row (from the stack table below), its
structure document, and its facts.

### 4. Synthesize, refute, verify

Once all eight ledgers exist, dispatch the synthesizer brief. When a lens died or wrote no
ledger, move any partial ledger it left to `ledger-NN-<slug>.md.partial` (rust-code-reviewer
will not write over an existing file) and re-dispatch that lens once before the synthesizer.
When it fails again, the synthesizer runs without it and the headline names the missing lens.

Then dispatch one refuter per Critical and Important finding numbered `{FIRST}` or above in
`ledger-synthesized.md` (never one under *Posted in earlier rounds*: those are already
decided and live on GitLab), all in one message, each on `haiku` at `max`, with its own
`<run>/refute-K.md` (K is the finding's ledger number) and the refuter brief from
`references/lens-briefs.md` that fits the finding:

| Finding | Brief |
|---|---|
| SRP, architecture, naming, constants/enums, style; a tests finding about how a test is written (placement, naming, shape, shared state, magic values) | rule-finding brief |
| everything else, including a tests finding that a promised behaviour is untested or that a test asserts the wrong thing | behaviour brief |

The behaviour brief would refute a rule finding for having no wrong behaviour, and the rule
brief would refute a coverage finding for breaking no rule.

Read each REFUTED and LOWER verdict against the cited lines before you act on it. When its
evidence is only that the refuter could not verify the claim (a race, a cancellation path,
an FFI lifetime: things a refuter cannot build or run), keep the finding at its severity and
present it as uncertain. Otherwise a REFUTED finding moves to the ledger's *Dropped* section
with the refuter's reason, and a LOWER one takes the severity the refuter shows.

Then read the cited lines of every surviving Critical and Important finding yourself: the
fleet is cheap, and a false positive posted on a colleague's MR costs him credibility. A
finding you cannot confirm goes to him as uncertain, never as fact.

### 5. Present — gate

On a later round, first list the posted findings, one line each with their *On the new head*
status, so he can say which threads to answer or resolve; then show only this round's
findings.

Show the Critical and Important findings in full (Finding N — Severity — title, Where, Impact,
Description, Recommended fix), then one table row per Minor and Nit (number, severity,
category, title, anchor), one line per Critical or Important finding the refuters dropped
(title and the refuter's reason, so he can disagree), the ledger path, the gate result, and
the static-review caveat when it applies. Every finding keeps its exact `file:line` and quoted line, explained in plain
words; he rejects unexplained jargon. Then stop.

His picks come as a severity class ("all critical + important"), numbers ("1 3 5 6"),
categories ("all SRP, all docs"), or a mix. A category pick matches the ledger's **Category**
field exactly. A finding whose content fits the named class but whose category differs (test
constants filed under tests, a placement issue filed under architecture when he said SRP) is
not posted: name it in the post report as "possibly also in that class" and let him add it.

### 6. Post

Write one file per picked finding, `<run>/notes/NN.md`, where NN is the ledger number:

```
---
finding: 4
path: core/src/application/plan.rs
line: 185
---
**Important — a plan whose TTL expired is still applied**

**Impact:** …

**Description:** …

**Recommended fix:** …
```

`path` and `line` come from the finding's Anchor; leave both out when the Anchor is `general`.
Notes are English, dev to dev, in plain words, with the severity in the title (and the
category in parentheses when the title does not make it obvious). The ledger's machinery stays
out of GitLab: no lens names, no "found by", no "Finding N". The developer has no ledger, so
point at other places as `path:line`.

Run `post_notes.py <run>`, a dry run that prints where each note will land and preflights
every body against GitLab's markdown endpoint. Read the plan, then run
`post_notes.py <run> --post`. Any line of a file the MR changes lands inline, added or
unchanged alike; a line in a file outside the diff becomes a general note prefixed with its
`path:line`. The script refuses new anchored notes when the MR head moved since setup, and
records what is live in `posted.json`, so a rerun skips unchanged notes and updates edited
ones in place.

The preflight creates nothing. A gateway in front of GitLab can answer a body that looks like
SQL injection with an HTML 403 instead of a GitLab error; the script reports which lines it
blocks, and you reword those lines, never retry the same body.

Report a table of finding → where it landed (inline or general), any "possibly also"
findings, and the MR link.

### 7. Refine — gate

He reads the notes and asks for changes. Edit `notes/NN.md` and rerun `post_notes.py <run>
--post`: it updates those notes in place. When a change alters what a finding says rather than
its wording, make the same change in `ledger-synthesized.md`, so the developer file agrees
with GitLab.

When he withdraws a note, delete it on GitLab (`glab api --hostname code.roche.com --method
DELETE projects/<project_id>/merge_requests/<iid>/notes/<note_id>`, the id from
`posted.json`), then drop its `posted.json` entry and its `notes/NN.md`: the developer file
is built from `notes/`.

### 8. The developer file — not sent

`build_final_markdown.py <run>` writes `review-mr-<iid>.md`: only the findings that have note
files, taken from the synthesized ledger, renumbered 1..N, with Anchor and Found-by dropped. A
warning about an unresolved "Finding N" reference means an edit by hand. On a later round,
pass `--leave-out` with the posted findings whose *On the new head* line says fixed.

Sending it to the developer is **disabled**: never send it, over Teams or anything else.
Give him the file's path; he sends it himself if he wants to. Sending over Microsoft Teams
will be added to this stage later.

When he closes the review, remove the worktree with
`git -C <repository> worktree remove <run>/wt`, and any build cache the repository's entry
says the gate created for this run. Tell him of any shared image the gate rebuilt from the
MR's files (the entry names them). Keep the run directory: its notes and `posted.json`
still allow later edits.

## Stack table

| Stack | `{STYLE_SKILL}` | `{TEST_SKILL}` | `{ARCHITECTURE_LINE}` for lens 03 | `{REVIEWER_AGENT}` |
|---|---|---|---|---|
| Rust | rust-code-style | rust-testing | Load rust-design-principles (single responsibility), rust-hexagonal-architecture and rust-project-structure: dependencies point inward, ports hold traits only. Where the repository's structure document says otherwise, it wins. | rust-code-reviewer |

For any other stack, ask him which skills and reviewer agent apply, and add a row once he
agrees.
