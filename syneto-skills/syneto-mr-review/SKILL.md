---
name: syneto-mr-review
description: Use when the operator asks to review a GitLab merge request on gitlab.syneto.eu — a merge request URL or !number to review, picked findings to post as review notes, or the review to send to the merge request's author — and when resuming such a review in a later session. Syneto-specific: assumes glab authenticated to gitlab.syneto.eu, the SYN Jira board, repositories under /home/cristi/Projects, and Google Chat in the operator's Chrome.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.1.0"
---

# Syneto MR Review

## Purpose

Review one merge request the way Cristian reviews: a Sonnet fleet hunts, he decides which
findings are worth the author's time, and only those reach GitLab and the author. He is the
reviewer of record — every note and the Chat message go out under his name — so nothing
leaves the session that he has not picked or approved.

You orchestrate: set up, brief, verify, present, post. The fleet reviews, and every dispatch in
this skill runs on `model: "sonnet"` (his standing choice). Load **agent-fleet-orchestration**
once before the first dispatch; this skill already answers its intake gate — supervised, the
spec is `ticket.md`, the base is `base_commit`, and the briefs in `references/lens-briefs.md`
replace both the pipeline-variant choice and the code-implementation-review prompts — so the
three gates below are the only stops.

## Stages

| # | Stage | Writes | Gate |
|---|---|---|---|
| 1 | Set up the run | `~/.cache/mr-review/<repo>-<iid>/` | — |
| 2 | Review fleet: seven Sonnet lenses in parallel | `ledger-NN-*.md` | — |
| 3 | Synthesize, then verify every Critical and Important yourself | `ledger-synthesized.md` | — |
| 4 | Present the ledger | — | **his picks** |
| 5 | Post the picked findings as review notes | `notes/`, `posted.json` | — |
| 6 | Refine the notes he asks about | — | **he is satisfied** |
| 7 | Build the developer file, send it over Google Chat | `review-mr-<iid>.md`, `review-mr-<iid>.sent.md` | **his yes to the exact message** |

The scripts live in `scripts/` beside this file. Run them as `python3 -B` by absolute path,
`python3 -B /home/cristi/Projects/agent-skills/syneto-skills/syneto-mr-review/scripts/<name>.py`
(`-B` keeps Python from writing `__pycache__` into the skills repository); each has `--help`. A later session resumes from the run directory: `meta.json` and the ledgers
carry the review, and `posted.json` says what is live.

### 1. Set up

`setup_review.py <MR URL>` fetches both branches, puts a detached worktree on the MR head at
`<run>/wt` (the operator's own checkout is never touched), and writes `meta.json` and
`mr-description.md`. Rerun it after the author pushes: it moves the worktree to the new head
and keeps the notes.

The run directory must be shared with the session: the lenses write their ledgers there and
Chrome uploads the developer file from there. When `~/.cache/mr-review` is not among the
session's working directories, ask him to run `/add-dir ~/.cache/mr-review`.

Materialize the ticket into `<run>/ticket.md`, verbatim, with the Atlassian MCP's
`getJiraIssue` (summary, description, comments, subtasks, links, as markdown). The server's
name changes between sessions, so find the tool by searching for `getJiraIssue`. When the
story has a parent, add the parent's description: open questions and design decisions often
live there and nowhere else. With no ticket key, ask him for the spec; with none at all, lens
07 judges migration and contract only, and the ledger says so.

### 2. Review fleet

Dispatch the seven lenses in `references/lens-briefs.md` in one message. Between them they
cover his hunt list, and their shared preamble carries his scope rule: **new or changed code
only**, never pre-existing code. A finding that breaks that rule is dropped in stage 3.

Which skills apply depends on the repository: fill the briefs from its row of the stack table.
For a repository not in the table, read its CLAUDE.md and layout, and ask him when it is
unclear.

No virtualenv in the repository (common after a machine migration) makes it a static review:
the briefs say so, and so does everything you present.

### 3. Synthesize and verify

Once all seven ledgers exist, dispatch the synthesizer brief. Then read the cited lines of
every Critical and Important finding yourself: the fleet is cheap, and a false positive posted
on a colleague's MR costs him credibility.

### 4. Present — gate

Show the Critical and Important findings in full (Finding N — Severity — title, Where, Impact,
Description, Recommended fix), then one table row per Minor and Nit (number, severity,
category, title, anchor), the ledger path, and the static-review caveat when it applies. Every
finding keeps its exact `file:line` and quoted line, explained in plain words; he rejects
unexplained jargon. Then stop.

His picks come as a severity class ("all critical + important"), numbers ("1 3 5 6"),
categories ("all SRP, all docs"), or a mix. A category pick matches the ledger's **Category**
field exactly. A finding whose content fits the named class but whose category differs (test
constants filed under tests, a placement issue filed under DDD when he said SRP) is not
posted: name it in the post report as "possibly also in that class" and let him add it.

### 5. Post

Write one file per picked finding, `<run>/notes/NN.md`, where NN is the ledger number:

```
---
finding: 4
path: src/central_rest_api/api/hardware.py
line: 285
---
**Important — pagination links drop the `serialNumber` / `status` filters**

**Impact:** …

**Description:** …

**Recommended fix:** …
```

`path` and `line` come from the finding's Anchor; leave both out when the Anchor is `general`.
Notes are English, dev to dev, in plain words, with the severity in the title (and the
category in parentheses when the title does not make it obvious). The ledger's machinery stays
out of GitLab: no lens names, no "found by", no "Finding N" — the developer has no ledger, so
point at other places as `path:line`.

Run `post_notes.py <run>` — a dry run that prints where each note will land and preflights
every body against the GitLab firewall — read the plan, then `post_notes.py <run> --post`. Any
line of a file the MR changes lands inline, added or unchanged alike; a line in a file outside
the diff becomes a general note prefixed with its `path:line`. The script refuses new anchored
notes when the MR head moved since setup, and records what is live in `posted.json`, so a
rerun skips unchanged notes and updates edited ones in place.

The gateway in front of gitlab.syneto.eu answers bodies that look like SQL injection with an
HTML 403 instead of a GitLab error, for the preflight and for any manual `glab api` call alike.
Known trigger: `time (`.

Report a table of finding → where it landed (inline or general), any "possibly also"
findings, and the MR link.

### 6. Refine — gate

He reads the notes and asks for changes. Edit `notes/NN.md` and rerun `post_notes.py <run>
--post`; it updates those notes in place. When a change alters what a finding says rather than
its wording, make the same change in `ledger-synthesized.md`, so the developer file agrees
with GitLab.

When he withdraws a note, delete it on GitLab (`glab api --hostname <hostname> --method DELETE
projects/<project_id>/merge_requests/<iid>/notes/<note_id>`, the id from `posted.json`), then
drop its `posted.json` entry and its `notes/NN.md`: the developer file is built from `notes/`.

### 7. Send the developer the review — gate

`build_final_markdown.py <run>` writes `review-mr-<iid>.md`: only the findings that have note
files, taken from the synthesized ledger, renumbered 1..N, with Anchor and Found-by dropped. A
warning about an unresolved "Finding N" reference means an edit by hand before sending.

The Chat message is one line, in the language he uses in that conversation (read the thread;
with most of the team it is Romanian), and carries no finding details — the file does. Its
shape: greeting, "reviewed !<iid> (<ticket>)", the attached markdown with the N points to fix,
also posted as notes on the MR, the link.

```
Salut <Prenume>, am făcut review la !<iid> (<SYN-key>). Ți-am atașat markdown-ul cu cele <N> puncte de rezolvat, le găsești și ca note pe MR: <MR link>
```

Show him the recipient (Chat name and email), the exact text, and the attachment path, and
wait for an explicit yes. An earlier request ("send it to the author when it's done") is not approval
of a text he has not seen, and his yes covers that exact text only.

Then, with the claude-in-chrome tools:

1. `tabs_context_mcp`. He runs Chrome on more than one machine: when the browser in use is not
   the one he expects, `list_connected_browsers` and let him choose.
2. chat.google.com → search `<author_username>@syneto.eu` → open the conversation whose result
   shows that address. Chat display names can differ from GitLab names, so trust only the
   email, and ask him when nothing matches.
3. `find` the composer's "Upload file" input and `file_upload` the review file. A refusal
   about files the session may read means the run directory is not shared (stage 1).
4. Click the composer and type the message in a single `type` action. Never press Enter (it
   sends) or Shift+Enter (Chat jumps the cursor to the start and the lines come out reversed),
   which is why the message is one line.
5. Verify with `javascript_tool`: `[...document.querySelectorAll('div[contenteditable="true"]')].map(element => element.innerText.trim()).filter(Boolean)`
   must equal the approved text, and the attachment chip must show the file name.
6. Click Send, take a screenshot, and confirm the message and the file appear in the thread.
   When he would rather send it himself, stop after step 5 and tell him it is ready.

Once it is sent, copy the file to `review-mr-<iid>.sent.md`: a later rebuild overwrites
`review-mr-<iid>.md`, and the copy keeps what the developer actually received.

In auto mode the permission classifier may refuse to open the conversation. That is the gate
working: tell him what was refused and wait for him to allow it.

When he closes the review, remove the worktree with `git -C <repository> worktree remove
<run>/wt`. Keep the run directory: its notes and `posted.json` still allow later edits.

## Stack table

| Repository | `{STYLE_SKILL}` | `{TEST_SKILL}` | `{ARCHITECTURE_LINE}` for lens 03 | `{REVIEWER_AGENT}` |
|---|---|---|---|---|
| Python, layered DDD (rest-api) | python-code-style | python-testing | Load python-ddd. Business rules (state transitions, invariants, which record is current) live in the domain, not in SQL, the application layer, or routers; repository ports sit in the domain and adapters implement them; the Unit of Work commits explicitly; presentation schemas, application DTOs, and domain models stay apart. | python-code-reviewer |
| Python, other (central-backend, …) | python-code-style | python-testing | python-ddd does not apply. Judge placement against the repository's own layout and CLAUDE.md. | python-code-reviewer |
| Vue | frontend-vue-code-style | frontend-vue-testing | Load frontend-vue-development: feature layout, container and presenter split, the typed API boundary. | vue-code-reviewer |
| React | frontend-react-code-style | frontend-react-testing | Load frontend-react-development: feature layout, state ownership, the typed API boundary. | react-code-reviewer |
| Rust | rust-code-style | rust-testing | Load rust-hexagonal-architecture and rust-project-structure: dependencies point inward, ports hold traits only. | rust-code-reviewer |
