# Ticket templates

Every body is GitHub-flavored Markdown, sent with `contentFormat: "markdown"`, and stays under
**4,000 characters**. Write for one developer who hasn't seen the spec: plain words, a colleague's
voice, concrete examples, nothing said twice, and no sibling's content repeated. Name a
neighbouring ticket inline ("the toggle itself is SYN-XXXX") instead of an out-of-scope list.

**Titles**, every type: one plain sentence saying what changes for the user or the system, no
repo or area prefix, no trailing period. For example: `Show update check errors in the UI
instead of silently falling back to "No updates available"`.

**The spec line** closes stories, backend subtasks and Central frontend subtasks:

```
Specs: [Software editions spec §6.5](<page url>) · [Technical specification §6.10](<page url>)
```

Link the exact sections the ticket covers, functional spec first, technical spec second. A
syneto-os-frontend subtask carries the same line.

**The repos line** opens every subtask and every bug, before anything else, listing the repos the
ticket touches:

```
**Repos:** rest-api, central-backend
```

Only stories and syneto-os-frontend tickets (subtasks and bugs) have no repos line.

## Story

A functional slice of the spec, in the user's world. No endpoint, path, field name, payload,
table or code: those belong to the subtasks. Model: SYN-2348.

```
### User Story

**As a <who: a SynetoOS administrator, a Hub user, Syneto Support…>**, I want <what>, so that
<why it matters to them>.

<Up to about 13 lines in all: what they do and see, in first person, plain prose. Cover the
whole section: the Central side, the machine and the SynetoOS UI.>

### Acceptance Criteria

#### <area, e.g. "Central Support">

* <short, checkable by a user or a tester>
* …

#### <next area>

* …

Specs: […](…) · […](…)
```

About 10 bullets in all, grouped by area under `####` headings. Each one is something a person can
check in the product, never a build step.

## Backend subtask

The technical spec for this piece of the story, cut down to what the developer needs. It may span
several backend services, on Central and on the machine (rest-api, central-backend, mercurio…).
Implementation detail belongs here: where in the code, what changes, the contract, the data, the
tests.

```
**Repos:** rest-api, central-backend, syneto-mercurio

**What to build**

<Short paragraphs: the behaviour, and where it goes, with `repo:path:line` pointers at the commit
you read. Name the commit once at the end of this section: `rest-api central-2.10@abc1234`.>

**API contract**

<Only when this ticket adds or changes an endpoint or RPC. Route and verb, request and response
bodies in ```json blocks, status codes and what each means. This ticket owns the contract: the
frontend subtasks point here.>

**Data**

<Only when the schema or stored data changes: the migration, the data step, the order.>

**Tests**

<The cases that prove it, by test tier, one line each.>

**Acceptance criteria**

- <checkable against the merge request>
- …

Specs: […](…) · […](…)
```

Leave out a section that has nothing to say. The whole body stays under 4,000 characters; when
it can't, the subtask is two subtasks.

## Central frontend subtask (central-ui and central-hub)

One subtask can cover both apps. Follow the UI ticket playbook in memory (`frontend-ticket-template`
and `frontend-tickets-no-implementation-details`): what the user gets and the API contract,
nothing about how to build it. Model: SYN-3007, with the repos line first.

```
**Repos:** central-ui, central-hub

**Description**

As <who>, I want … I want … And once …   (up to 13 lines, first person, no links)

**API Usage**

Endpoint: `<path>`

1. <what the UI is doing, e.g. Load the current state>
   <the verb and call in the sentence; bodies in ```json; tables for fields and statuses>
2. …

Full API contract: **SYN-XXXX**.   (the backend subtask that owns it)

**Acceptance criteria**

* <checkable in the UI, at most 10>

Specs: […](…) · […](…)
```

## syneto-os-frontend subtask

Its own subtask, never merged with Central frontend work. Exactly the UI playbook and SYN-3007:
**Description**, **API Usage**, **Acceptance criteria**, then the spec line. No repos line.

## Bug

A separate Bug issue, never a subtask, placed in the current sprint and linked to the story it
belongs to with `relates to`.

```
**Repos:** <every bug except a syneto-os-frontend one>

**Observed**

<What happens: the message, the screen, the log line, quoted.>

**Expected**

<What should happen, and the ticket or spec section that says so.>

**Steps to reproduce**

1. …

**Where**

<Environment, version or image, machine or account, date.>
```

One defect per Bug.

## Estimates

Original estimate in hours, on every subtask and Bug: `timetracking: {"originalEstimate": "6h"}`.
A Jira day is 8 hours, so write `12h`, not `1d 4h`. A story carries the sum of its subtasks. Each
draft keeps a one-line `estimate_reason` for Cristi, never posted.
