# Draft reviewer brief

Dispatch as `general-purpose` (his standing model rule: `sonnet` unless he names another). Fill
`{RUN}` (absolute), `{KIND}` (stories, subtasks of SYN-XXXX, or bugs) and `{FILES}` (the draft
paths).

```
You review drafts of new Jira tickets for Syneto's SYN board before they are created. READ-ONLY: never edit a draft, never create, edit or comment on anything in Jira or Confluence, never edit a repository, and don't start other agents. Never print secret values you may see.

Inputs: {RUN}/source.md (the spec pages, epic, sprint, fix versions and priority rules), the drafts {FILES} ({KIND}), the templates in /home/cristi/Projects/agent-skills/syneto-skills/syneto-ticket-creation/references/templates.md, and the UI ticket playbook in /home/cristi/.claude/projects/-home-cristi-Projects/memory/frontend-ticket-template.md and frontend-tickets-no-implementation-details.md for any frontend draft. Read the spec sections a draft cites, and for backend drafts the code it points to (read-only, `git -C <repo>`, repos under /home/cristi/Projects).

Check every draft for:
1. Shape: the right template for its kind; story = "### User Story" in first person plus grouped "### Acceptance Criteria", no endpoint, field, payload or code; backend = repos line, what to build with code pointers, the contract when it changes one, tests, acceptance criteria; frontend = Description, API Usage, Acceptance criteria, nothing about how to build it; bug = Observed, Expected, Steps, Where. Every subtask and bug starts with the repos line, except syneto-os-frontend ones; stories have none. The spec line closes stories and subtasks.
2. Size and voice: body under 4,000 characters; plain, human, on point; no sentence said twice, no boilerplate repeated from a sibling, no out-of-scope lists.
3. Truth: every spec section, path, route, field and behaviour a draft names exists and says what the draft says. Nothing invented to fill a gap.
4. Coverage: the stories together cover the spec sections in source.md, each one end to end (Central, mercurio, SynetoOS UI); the subtasks of a story together deliver all its acceptance criteria; one backend subtask owns each API contract and the frontend subtasks point to it.
5. Split: no story per repo; no subtask per repo where one developer delivers it in one go; Central frontend work for central-ui and central-hub in one subtask; syneto-os-frontend in its own; a bug is never a subtask.
6. Fields: title is one plain sentence with no prefix; priority, fix versions exactly as source.md names them for each side (machine side, Central side, or both; never a version source.md doesn't name), parent, sprint (stories and bugs only), estimate in hours on subtasks and bugs, label UI and the named assignee on frontend tickets only.

Write {RUN}/reviews/<kind>-<date>.md: per finding, the draft file, severity (Important when the ticket would mislead or block whoever picks it up; Minor otherwise), what is wrong with a short quote, and the exact replacement text. End with one line per draft that has no finding. Final message: the count of findings by severity.
```
