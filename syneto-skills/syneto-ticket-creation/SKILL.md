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
  version: "0.2.0"
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
| Tools | the Atlassian MCP `mcp__atlassian__*` (load with ToolSearch `select:`; if it comes back empty, retry once: the server may still be connecting). When it fails with 404, stop the Jira steps and ask him to reconnect it with `/mcp`; keep drafting meanwhile |
| Types used | Story (`10001`), Subtask (`10005`), Bug (`10003`), under the Epic (`10004`) he names. Never "Technical Task" (`10002`) |
| Parent | a story's parent is the epic; a subtask's parent is its story (`parent` on create) |
| Sprint | `customfield_10020` with the sprint's numeric id, on stories and bugs. A subtask can't take one: it inherits its story's |
| Fix version | the batch's versions, recorded in `source.md` at intake (the OS one may differ by priority: this batch has High `6.1.0.RC6`, Medium and Low `6.1.1`), never taken from memory, an example or an older ticket: the OS release on machine-side tickets (syneto-os-frontend, mercurio and other syneto-* repos), the Central release on Central tickets, **both** when a ticket spans both sides (a story spanning both sides carries both). Set it on subtasks too, it doesn't inherit. Check each version exists before the first create by listing the allowed values: `getJiraIssueTypeMetaWithFields` (project `SYN`, the issue type, `requiredFieldsOnly: false`) returns `fixVersions` with every valid name. A JQL `fixVersion = "<name>"` through the MCP returns an empty result, not an error, for a version that doesn't exist (`6.1.0`, 2026-10-22), so it proves nothing. When the batch's version is missing, stop and ask him before the first create |
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
| 1 | Intake: specs, rules for the batch, the ticket map | `<run>/source.md`, `<run>/stories/story-map.md` | his OK on the map |
| 2 | Map review, when he asks: rounds until he stops them | `<run>/reviews/story-map-rN.md` | his OK on the reviewed map |
| 3 | Stories: the writing pipeline, one agent per story | `<run>/stories/NN.md`, `<run>/reviews/stories/` | — |
| 4 | Subtasks: the same pipeline, one agent per subtask | `<run>/tasks/<id>.md`, `<run>/reviews/tasks/` | — |
| 5 | His final review; improve from it and from the VPE's or PO's answers | the drafts | — |
| 6 | Create in Jira, when he says so | `<run>/created/` | **his yes** |
| 7 | Bugs, when he reports one | `<run>/bugs/NN.md` | **his yes** |

`<run>` is `~/.cache/ticket-delivery/<batch>` (`<batch>`: a short kebab-case name for the epic or
feature). Run `mkdir -p <run>/stories <run>/tasks <run>/bugs <run>/reviews/stories <run>/reviews/tasks <run>/created`
first. A later session resumes from the drafts, the reviews and `created/`: a draft with a `key:`
line in its front matter exists in Jira and is never created again.

He reviews the drafts once, at the end (stage 5). Don't show them chunk by chunk or wait for a yes
between stages 3 and 5: that is the process he rejected ("that is not how we proceed", 2026-10-21).

### 1. Intake

Read the functional spec and the technical spec in full, and any decision log the batch has.
Write to `source.md`: the page URLs, the epic key, the sprint id, the fix version for each side
(OS release and Central release, as he names them, checked against Jira, see The board), the
priority rules he gives (for example High = essential, Medium = nice-to-have usability, Low =
deferred to the next release), and the repos that get tickets. Ask him for any of these you can't
find.

Then the ticket map: one row per planned story with its spec sections, priority, fix versions and
its planned subtasks by kind (B backend, CF Central frontend, OF syneto-os-frontend), each with
its repos and what it delivers, plus the other teams' work it depends on ("owners") and a
delivery order. Show it and wait for his OK.

### 2. Map review

When he asks for one: a single reviewer, the model and effort he names (this batch: Opus 5.5,
high), against the specs, the decisions and the code. It checks coverage both ways (spec → stories,
technical spec → subtasks), split and size (a subtask that can't fit 4,000 characters is two), who
owns each API contract, priorities and fix versions, the delivery order, and wording. Apply every
finding to the map yourself, say in one line why when you leave one out, and keep each map
revision (`story-map-rN.md`). He decides after each round whether to run another.

### The writing pipeline (stages 3 and 4)

His rules, standing:

- **One agent per ticket**, all Sonnet 5.5 at **xhigh** effort: writer, reviewers, fixers.
- Per ticket: **write → review → fix → review → fix**. Round 2 reviews the fixed draft and doesn't
  re-raise an applied round-1 finding. A fixer applies every finding, or leaves a wrong one and
  says why with the quote; it doesn't split a ticket itself.
- **At most 10 of your agents at a time.** Each may start **up to 2 explorers** (Sonnet,
  read-only) to check code facts; explorers don't count toward the 10.
- Every writer reads this skill and `references/templates.md`; frontend writers also read the UI
  playbook in memory (`frontend-ticket-template`, `frontend-tickets-no-implementation-details`).
- Stories first, then subtasks. Within the subtasks, a story's backend subtasks are written before
  its frontend subtasks, and a frontend subtask waits for every backend subtask that owns a
  contract it uses (also in another story).

Run it as a Workflow, one per stage: `references/pipeline-stories.js` and
`references/pipeline-subtasks.js` are the scripts this batch ran, with the limiter, the per-ticket
chain, the briefs and the schemas. Build their args from the approved map (one entry per ticket).
A workflow can't hand the same agent a second round, so round 2's fixer is a new agent that reads
round 1's review and fix log; say so when you launch. Before stage 4, fetch every ticket repo
once yourself and tell the agents to read the remote refs and never fetch.

Agents write only their own draft or review file and change nothing in Jira, Confluence or any
repository.

**Restarting a stopped or hung pipeline** (no agent file written for a long while): don't use
`resumeFromRunId`. Its cache matches agent calls by position, and with parallel agents the order
changes on resume, so it redoes finished work (2026-10-22: 63 finished reviews and fixes started
again). Stop the run, then `python3 scripts/pipeline_state.py <run> <stories|tasks> <ids…>`: it
reads the drafts, reviews and fix logs and prints each ticket's next stage. Relaunch the script
with that stage in each ticket's args (`start`); finished stages cost no agent. A fixer that was
killed mid-way left no fix log, so its stage runs again from its review.

After each stage: check that every draft exists, is under 4,000 characters, has its fields and
links every spec page, and collect the writers' gaps (things the sources don't settle) into
`<run>/stories/phase1-summary.md` (and the subtask equivalent) for his final review.

Front matter, story:

```
---
summary: "Allow the support tunnel only when the maintenance includes remote support"
priority: High
fix_versions: ["6.1.0", "central-2.9"]
parent: SYN-3331
sprint: 1043
estimate: "(sum of its subtasks, filled after the subtasks)"
spec_sections: ["§6.5"]
---
```

Front matter, subtask (ids are `NN-B1`, `NN-CF1`, `NN-OF1`, from the map; `<run>/tasks/index.md`
lists them all):

```
---
id: 12-B1
summary: "<one plain sentence>"
type: Subtask
parent_story: "12 (stories/12.md; the SYN key once created)"
priority: High
fix_versions: ["central-2.9"]
assignee: "unassigned"
labels: []
repos: ["rest-api"]
estimate: "12h"
estimate_reason: "<one line for him, never posted>"
---
```

Until tickets exist, drafts point at each other by these ids ("Full API contract: **03-B5**",
"story 3"). After creation they become keys (stage 6). A story's estimate is the sum of its
subtasks, filled once they are written.

### 5. His final review

He reads the drafts, the reviews and the gaps. From then on the work is improving the written and
reviewed drafts from his comments and from the VPE's or PO's answers; record each change in the
batch's ledger.

### 6. Create in Jira

Only when he says so, with the number of Sonnet agents with Jira access he allows (this batch:
5), each taking a share of the tickets. Before the first create, check the fix versions exist
(The board). Each agent, per ticket:

1. Lists the parent's children and skips a ticket whose summary already exists; it repeats this
   check after any failed or timed-out create, because the call may have gone through.
2. Creates it with `createJiraIssue` (`issueTypeName`, `summary`, `description` = the body,
   `contentFormat: "markdown"`, `parent`, `assignee_account_id` when the table names one, and in
   `additional_fields`: `priority`, `fixVersions`, `labels`, `timetracking`, and
   `customfield_10020` for stories and bugs). It posts the body as written.
3. Records the key before the next create: one line in its own `<run>/created/<share>.md` and a
   `key:` line in the draft's front matter.
4. Reads it back (`getJiraIssue` with `expand: renderedFields`; asking for ADF returns Markdown):
   fields set, parent right, headings and lists rendered. Fixes with `editJiraIssue`, never by
   creating again. Jira assigns a new subtask to its creator even when no assignee is sent, so a
   subtask without an assignee in the table gets `editJiraIssue` `{"assignee": null}` right after.
5. Frontend subtasks only: links each backend subtask it can't be built or shipped before (one
   that adds or changes an endpoint, field or behaviour it uses, or that the body says it ships
   with or after; not one mentioned only for context) with `createIssueLink` `type: "Blocks"`,
   `inwardIssue` = the backend key, `outwardIssue` = the frontend key, after checking the existing
   links. It reads back the first link: the frontend subtask must show "is blocked by" (a wrong
   link can't be removed through the MCP). A blocker not yet in Jira goes to
   `<run>/created/links-pending.md` for you to link once it exists.

If Jira refuses a value that isn't a formatting problem (a missing version, say), every agent gets
the same rule from you; none decides on its own.

Then a second pass, once every key exists: each "story N" or subtask id in a body becomes its key,
in the draft and in Jira. Jira doesn't link a key followed by `'s` or `;`, so reword those
("the engine in SYN-3344"). Link related existing tickets with `relates to`.

### 7. Bugs

From what he reports: draft one Bug (template), find the story it belongs to and the current
sprint's id, show it, create it on his yes, link it to the story with `relates to`.

## Never

- Create, edit or link anything in Jira before he says so.
- Edit an existing ticket's description unless he asks; comment instead.
- Put an endpoint, field, payload or code in a story, or implementation detail in a frontend
  subtask (the API contract is the one exception).
- Slice stories by repo, or split a subtask per repo when one developer delivers it in one go.
- Invent a route, field or caller to fill a gap in the spec: say what's missing and ask him.
- Put a new or changed HTTP route in a ticket or a technical spec without designing it against the `syneto-rest-api-design` skill first (nouns only, PATCH not PUT, mutations as 202 jobs, the `{"error": {code, message, details}}` body, `items` + `pagination` lists). When a route copies an older local style that breaks the skill, say so and let him choose.
- File a bug as a subtask.
