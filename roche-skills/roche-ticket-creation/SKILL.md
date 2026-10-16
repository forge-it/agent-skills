---
name: roche-ticket-creation
description: >-
  Use when the operator wants one or more new NIFS Jira tickets on the RDNX board — "create a
  ticket for this", "open an enabler", "file a bug", "make tickets from these findings", "turn
  this gap into a ticket", "ticket this follow-up" — from his description, a docs/gaps entry,
  a review finding, an RFD or ADR section, a CI or test failure, or any other source, and when
  resuming such a batch in a later session. Roche-specific: assumes the NIFS project's RDNX
  board on navify.atlassian.net through the Atlassian MCP and repositories under ~/Projects.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.1.0"
---

# Roche Ticket Creation

## Purpose

Turn work that needs doing into NIFS tickets on the RDNX board that someone else can pick up
without asking: the right type, a title in the team's shape, a body in the type's template,
an honest estimate, and the links that place it. Cristian is the reporter of record, so
nothing reaches Jira that he has not seen and approved.

You draft, have one reviewer check the drafts, present them, and create them on his yes.
Read sources and code yourself; dispatch only the reviewer.

**Models.** His global instructions set them, and they win over any skill or agent
definition. Pass `model` and `effort` explicitly:

| Role | Model and effort |
|---|---|
| Draft reviewer (stage 3) | `sonnet` at `medium` |

A model or effort he asks for on this batch wins over it. Record it in `<run>/meta-notes.md`.

## The board

| | |
|---|---|
| Site | navify.atlassian.net, cloudId `3ccaad2c-2e75-4a7c-b9aa-c3eddcd6a020` |
| Project, board | `NIFS`, board RDNX id `22713` |
| Board filter | `project = NIFS AND component = RDNX AND type IN (Bug, Enabler, Story)` |
| Component | `RDNX`, always: Jira refuses a create without a component, and a ticket without `RDNX` never appears on the board |
| Assignee | Cristian, accountId `712020:8d29777e-28f3-4096-9c5a-027a637bd6b7` (from `atlassianUserInfo`) |
| Sprint | the board's active sprint, resolved at stage 5: `getJiraBoardSprintData` (through `executeRead`) with `boardId` `22713` and `includeIssues` false gives `resolvedSprint.id`. When it reports no active sprint, ask him which sprint (from `sprints`) or the backlog, before creating |
| Story points | `customfield_10014` |
| Body | GitHub-flavored Markdown with `contentFormat: "markdown"`, in the Description field only. Never Jira wiki markup, and never the `Task Description` custom field |

Only three types are created: **Enabler**, **Bug** and **Story**. They are the board filter's
types. Sub-tasks do not match the filter and would never show on the board, so work too big
for one ticket becomes several Enablers (or Stories) linked with `relates to`, never
Sub-tasks.

| Type | When |
|---|---|
| Enabler | technical work that needs no testing after development: infrastructure, architecture, tooling, CI, docs, refactors |
| Bug | existing behaviour that is wrong against what is specified (RFD, ADR, proto, ticket) |
| Story | development that is tested after it is built: a capability a consumer (REC, an operator, a calling service) can observe |

When the type is unclear, propose one with a one-line reason and let him decide in stage 4.

## Stages

| # | Stage | Writes | Gate |
|---|---|---|---|
| 1 | Intake: read the source, check for duplicates, split | `~/.cache/roche-ticket-creation/<batch>/source.md` | — |
| 2 | Draft every ticket | `drafts/NN.md` | — |
| 3 | Review the drafts, apply the findings | `review.md` | — |
| 4 | Present the batch | `approved.md` | **his yes** |
| 5 | Create, place in the sprint, link, verify | `created.md` | — |

`<batch>` is a short kebab-case slug of what the batch is about, plus the date
(`ci-pipeline-2026-10-16`); `<run>` is `~/.cache/roche-ticket-creation/<batch>`. Run
`mkdir -p <run>/drafts` first. When `~/.cache/roche-ticket-creation` is not among the
session's working directories, ask him to run `/add-dir ~/.cache/roche-ticket-creation`
(it refuses a path that does not exist, hence the `mkdir` first).

The run directory carries the batch across sessions. A later session resumes from
`approved.md` (what he approved), `created.md` (what exists in Jira) and `drafts/`. With no
`approved.md`: when `review.md` is missing, finish the drafts that `source.md`'s split lists,
then run stage 3; otherwise resume at stage 4 and present the batch again. A draft modified after
`approved.md` was written needs his yes again.

### 1. Intake

Read the source in full and write it to `source.md`, verbatim, with where it came from:

| Source | What to read |
|---|---|
| His description | his words, then the code and docs they touch, read-only |
| A `docs/gaps/NNNN-*.md` entry | the entry, and the code it cites |
| A review finding (roche-mr-review, an agent review) | the finding with its `path:line`, the MR, and the cited lines |
| An RFD or ADR section | that section only (`docs/rfds/0001-*.md` is about 400 KB: search it for the symbols in play) |
| A CI, test or QA failure | the failing job or test id, its output, the commit it ran on |
| Anything else | what he points at; ask when it is unclear what the ticket must achieve |

Before drafting, search the board for a ticket that already covers the work:
`searchJiraIssuesUsingJql` with `filter = 88390 AND statusCategory != Done AND text ~ "<two or three key terms>"`.
A match goes to him in stage 4 as "possibly already covered by NIFS-n", and that draft is
not created unless he says so.

Split the work into tickets that can each be delivered and reviewed on their own: one
problem per ticket. A Story or Enabler worth more than 8 points is too big: split it. Append the split to
`source.md`, one line per planned draft.

### 2. Draft

Write one file per ticket, `drafts/NN.md`, numbered from 01:

```
---
type: Enabler
summary: "[CI] Add the merge request pipeline"
points: 3
points_reason: one line, for him only, never posted
links:
  - relates to NIFS-13631
  - is blocked by draft 01
labels: []
---
<the body, in the type's template from references/templates.md>
```

`references/templates.md` holds the title rule, each type's template, the estimation scale
and the linking rules. Follow it exactly: a missing section is a finding in stage 3. Each
`links` entry is one of the wordings in its *Links* table, then a key (`NIFS-n`) or
`draft NN` for another draft of this batch. A link between two drafts is listed in one of
them only.

Write for a developer who has not seen the source: plain English, the concrete file, crate,
RPC, recipe or doc each time (as `path` or `path:line` at the commit you read, and name that commit once, as
`<branch>@<short sha>` (`main@…` when you read main), at the end of the body), and no conversation history. Product and technical content only: never business context, never why
a technology was chosen for non-technical reasons, and never a docs/gaps entry argued as a
design reason. A ticket from a docs/gaps entry names the entry's path in its body.

### 3. Review

Dispatch the reviewer in `references/reviewer-brief.md` once per batch, on `sonnet` at
`medium`, after every draft exists. It writes `review.md` and edits nothing.

Apply every finding to the drafts yourself, without asking which. When a finding is wrong
(it misreads the source or the code), leave the draft and say why in one line in stage 4.

### 4. Present — gate

Show every draft in full: type, title, points (with `points_reason`), links, labels, and
the body exactly as it will be posted. Then list any "possibly already covered by NIFS-n"
match, any finding you did not apply and why, and a type you chose on judgment. Then stop.

One yes covers the whole batch as shown. When he asks for a change, edit the draft and show
that draft again; his yes covers the batch as it then stands. An earlier "create tickets for
these" is not approval of drafts he has not seen.

At his yes, write `approved.md` at once: the date and the draft numbers he approved, and
none he left out, such as a "possibly already covered" draft he did not ask for. When an
approved draft links to a `draft NN` he left out, ask him in the same turn whether that link
goes to the existing ticket that covers it or is dropped, and record his answer in
`approved.md`.

### 5. Create

On a resumed batch, before creating a draft that `created.md` does not list, search
`filter = 88390 AND reporter = currentUser() AND created >= -14d AND summary ~ "<two or three title words>"`.
A match with the draft's title is that draft: record it in `created.md` and do not create it.

For each draft in `approved.md`, in order:

1. `createJiraIssue`: `cloudId`, `projectKey` `NIFS`, `issueType`, `summary`, `description`
   (the body), `contentFormat` `markdown`, `assignee` (the accountId above),
   `additional_fields` `{"components": [{"name": "RDNX"}], "customfield_10014": <points>}`
   plus `labels` when the draft has any, and `assignToSprint` with the sprint's numeric id.
   Never `"active"`: NIFS has many boards, so name the RDNX sprint by its id.
2. Append to `created.md` at once, before any other call: draft number, key, URL, and the sprint id the create placed it
   in (or `backlog` when he chose it). A draft
   already in `created.md` is never created again.
3. When the response says `sprintAssignment.assigned: false`, the ticket exists: never
   create it again. Move it with `transitionJiraIssue` (`sprintId` only), report it, and
   record the sprint in `created.md`.

When every draft is created, make the links. For each `links` entry, resolve `draft NN` to
its key from `created.md`, and call `createJiraIssueLink` through `executeWrite` with the
`linkType`, `inwardIssue` and `outwardIssue` that `references/templates.md` gives for its
wording. Append each link to `created.md` as it is made. On a resumed batch, make only the
links and sprint moves that `created.md` does not record.

Then read every created ticket back with `getJiraIssue`, `view` `full`,
`responseContentFormat` `html`: the compact and evidence views omit `components`, and a
Markdown read-back shows `##` and `**` even when they rendered. Check that `components` is
`RDNX`, the `Sprint` custom field holds the sprint's id, `assignee.accountId` is his,
`Story Points` is the draft's points, every link in `created.md` is in `issuelinks` and points the right way (on the ticket
given as `inwardIssue`, the entry has that `type.name` and shows the other ticket as
`outwardIssue`), and the
description has `<h2>` headings and no literal `##` or `**` outside `<code>` and `<pre>`. Fix a wrong field with
`editJiraIssue`, a wrong sprint with `transitionJiraIssue` (`sprintId` only) and a missing
link with `createJiraIssueLink`, never by creating again. The sprint to check against is the
one `created.md` records; a ticket recorded as `backlog` has no sprint.

Leave the status as Jira sets it. Moving a ticket on is the delivery skill's job.

Report a table of draft → key → title → points → link, and anything that needed a fix.

## Never

- Delete a ticket. A ticket that turns out wrong is fixed with `editJiraIssue`; one that is
  no longer wanted is for him to reject.
- Change what a Done ticket requires. New or changed behaviour after delivery is a new ticket,
  linked to the old one with `relates to`.
- Create a Sub-task, an Epic, a Feature, a Task or any type outside the three.
