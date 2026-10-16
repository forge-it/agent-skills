# Draft reviewer brief

Dispatch as `general-purpose` on `sonnet` at `medium`. Fill `{RUN}` (absolute) and `{REPO}`
(the repository the tickets are about, absolute, or "none").

```
You review drafts of new Jira tickets for the NIFS project's RDNX board before they are created. READ-ONLY: never edit a draft, never create, edit or comment on anything in Jira, never edit the repository, and do not dispatch subagents.

Inputs: {RUN}/source.md (what the tickets come from), {RUN}/drafts/*.md (one ticket each: front matter, then the body), and the rules in ~/src/agent-skills/roche-skills/roche-ticket-creation/references/templates.md. Repository: {REPO}; run every git command as `git -C {REPO}`, and read code and docs there to check what the drafts claim.

Check every draft for:
1. Template: the type is Enabler, Bug or Story; the title follows the title rule; every section of the type's template is present and filled, with no placeholder text left.
2. Truth: every path, crate, RPC, recipe, error text and behaviour the draft names exists and says what the draft says, in the repository or the source.
3. Content: one problem per ticket; the scope matches the source (nothing the source asks for is missing, nothing it does not ask for is added); an Enabler states its benefit; acceptance criteria are observable and checkable against a merge request; a Story's criteria are testable Given/When/Then; a Story with only implementation content should be an Enabler; a Bug states one defect with its expected behaviour's source.
4. Readability: a developer who has not seen the source can start from the ticket alone; plain English; no unexplained jargon; no conversation history.
5. Size and estimate: the points fit the work on the scale 1, 2, 3, 5, 8; more than 8 needs a split, and say how.
6. Links: every ticket the source names is linked, with the link type the rules give.
7. Never in a ticket: business context, non-technical reasons for a technology choice, a docs/gaps entry used as a design argument.

Write {RUN}/review.md: per finding, the draft number, severity (Important when the ticket would mislead or block whoever picks it up; Minor otherwise), what is wrong with a quote, and the exact replacement text. End with one line per draft that has no finding. Your final message: the count of findings by severity.
```
