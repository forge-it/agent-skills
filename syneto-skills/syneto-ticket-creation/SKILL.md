---
name: syneto-ticket-creation
description: >-
  Use when the operator wants new SYN Jira tickets written for Syneto work: stories from a
  functional specification, the technical subtasks under a story, or a bug found during or after
  development, including asks such as "write the stories", "turn the spec into tickets", "make
  the subtasks for this story", "file a bug", "ticket this", and when resuming such a batch in a
  later session. Syneto-specific: assumes the SYN Jira board through the Atlassian MCP and
  repositories under /home/cristi/Projects.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.1.0"
---

# Syneto Ticket Creation

## Purpose

Turn a functional and a technical specification into the tickets Syneto works from, in the
team's shape, so whoever picks one up can start without asking. Cristian is the reporter of
record: nothing reaches Jira that he hasn't seen and approved.

Syneto tickets come in three kinds, always in this order:

1. **Stories:** the functional spec, in the user's world.
2. **Technical subtasks** under each story: what drives that story to done.
3. **Bugs**, during or after development, in the current sprint.

Templates for every body: `references/templates.md`. Read it before drafting.

## The board

| | |
|---|---|
| Site, project | syneto.atlassian.net, cloudId `15c97e39-64e4-4518-8e86-e141a20215e1`, project `SYN` |
| Types used | Story (`10001`), Subtask (`10005`), Bug (`10003`), under the Epic (`10004`) he names. Never "Technical Task" (`10002`) |
| Parent | a story's parent is the epic; a subtask's parent is its story (`parent` on create) |
| Sprint | `customfield_10020` with the sprint's numeric id, on stories and bugs. A subtask can't take one: it inherits its story's |
| Fix version | the batch's two versions, recorded in `source.md` at intake, never taken from memory, an example or an older ticket: the OS release on machine-side tickets (syneto-os-frontend, mercurio and other syneto-* repos), the Central release on Central tickets, **both** when a ticket spans both sides (a story spanning both sides carries both). Set it on subtasks too, it doesn't inherit. Check each version exists before the first create: a JQL `fixVersion = "<name>"` errors when it doesn't |
| Priority | High, Medium or Low, from the batch's rules (see Intake) |
| Estimate | original estimate in hours, `timetracking: {"originalEstimate": "6h"}` (`references/templates.md`, Estimates) |
| Labels | `UI` on frontend tickets; nothing on the others |
| Body | GitHub-flavored Markdown, `contentFormat: "markdown"`, under 4,000 characters |

**Assignees**

| Ticket | Assignee |
|---|---|
| Central frontend (central-ui, central-hub) | Nicolas Vannier, accountId `60b734888cf9190069665ba1` |
| syneto-os-frontend | Robert Călin, accountId `557058:8583b083-d092-440b-b164-0d087267fe7a` |
| Everything else (stories, backend subtasks, bugs outside the frontend) | unassigned |

## How the work splits

**Stories** follow the functional spec: about one spec section per story, with small neighbouring
sections merged. A story covers its section end to end, on Central, in mercurio and in the
SynetoOS UI. Never one story per repo.

**Subtasks** are technical, and there are three kinds:

| Kind | Covers | Shape |
|---|---|---|
| Backend | the technical spec for that functionality; one subtask may span several backend services, Central and machine (rest-api, central-backend, mercurio, the deploy repo `central`…) | templates: Backend subtask |
| Central frontend | central-ui and central-hub together, one subtask for both when the story needs both | templates: Central frontend subtask (the UI playbook, plus the repos line) |
| syneto-os-frontend | its own subtasks, never merged with Central frontend work | templates: syneto-os-frontend subtask (the UI playbook) |

Split by deliverable, not by repo: a backend subtask holds what one developer delivers and
reviews in one go, and owns the API contract the frontend subtasks point to. Work that only
another team's repos need gets no ticket from us unless he says otherwise; the technical spec
keeps it as their requirement.

**Bugs** are separate Bug issues in the current sprint, linked to their story with `relates to`.
Never a subtask of the story.

## Stages

| # | Stage | Writes | Gate |
|---|---|---|---|
| 1 | Intake: specs, rules for the batch, the story map | `<run>/source.md`, `<run>/story-map.md` | his OK on the map |
| 2 | Draft stories, in chunks | `<run>/stories/NN.md` | — |
| 3 | Review the chunk, apply the findings | `<run>/reviews/stories-NN.md` | — |
| 4 | Present the chunk, create on his yes | `<run>/approved.md`, `<run>/created.md` | **his yes** |
| 5 | Draft the subtasks of a story, review, present, create | `<run>/tasks/<story>-NN.md` | **his yes** |
| 6 | Bugs, when he reports one | `<run>/bugs/NN.md` | **his yes** |

`<run>` is `~/.cache/ticket-delivery/<batch>` (`<batch>`: a short kebab-case name for the epic or
feature). Run `mkdir -p <run>/stories <run>/tasks <run>/bugs <run>/reviews` first. A later session
resumes from `approved.md`, `created.md` and the drafts: a draft listed in `created.md` is never
created again, and a draft changed after his yes needs his yes again.

### 1. Intake

Read the functional spec and the technical spec in full, and any decision log the batch has.
Write to `source.md`: the page URLs, the epic key, the sprint id, the fix version for each side (OS release and Central release, as he names them),
and the priority rules he gives (for example High = essential, Medium = nice-to-have usability,
Low = deferred to the next release). Ask him for any of these you can't find.

Then the story map: one line per planned story with its spec sections, priority, and the subtask
kinds it will need (backend, Central frontend, syneto-os-frontend). Show it and wait for his OK.

### 2. Draft stories

Draft in chunks of about five stories, in the spec's order. One file per story, front matter
first:

```
---
summary: "Allow the support tunnel only when the maintenance includes remote support"
priority: High
fix_versions: ["6.1.0", "central-2.9"]
parent: SYN-3331
sprint: 1043
estimate: (sum of its subtasks, filled after stage 5)
---
<the body, in the Story template>
```

### 3. Review

One reviewer per chunk with `references/reviewer-brief.md` (his standing model rule applies:
`sonnet`, unless he names another). It writes the review and edits nothing. Apply every finding
yourself; when one is wrong, leave the draft and say why in one line when presenting.

### 4. Present and create

Show every draft exactly as it will be posted, with its fields. Stop. One yes covers the chunk as
shown; a change means showing that draft again. Write `approved.md` at his yes, then create each
draft with `createJiraIssue` (`issueTypeName`, `summary`, `description`, `contentFormat:
"markdown"`, `parent`, `assignee_account_id` when the table names one, and in `additional_fields`:
`priority`, `fixVersions`, `labels`, `timetracking`, and `customfield_10020` for stories and
bugs). Append each key to `created.md` before the next call.

Read every created ticket back: fields set, parent right, the description rendered as headings
and lists (no literal `###` or `**`). Fix with `editJiraIssue`, never by creating again.

### 5. Subtasks

For each created story, draft its subtasks from the technical spec: the backend subtask first
(it owns the API contract), then Central frontend, then syneto-os-frontend. Give each one its
estimate and `estimate_reason`. Check the body length before review:
`python3 -c "import sys; print(len(open(sys.argv[1]).read().split('---',2)[2]))" <draft>` must
print under 4000. Review, present and create as in stages 3–4, then set the story's estimate to
the sum.

### 6. Bugs

From what he reports: draft one Bug (template), find the story it belongs to and the current
sprint's id, present, create on his yes, link it to the story with `relates to`.

## Never

- Create, edit or link anything in Jira without his yes on what you showed.
- Edit an existing ticket's description unless he asks; comment instead.
- Put an endpoint, field, payload or code in a story, or implementation detail in a frontend
  subtask (the API contract is the one exception).
- Slice stories by repo, or split a subtask per repo when one developer delivers it in one go.
- Invent a route, field or caller to fill a gap in the spec: say what's missing and ask him.
- File a bug as a subtask.
