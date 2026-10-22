# Review briefs

## Per-ticket review and fix (stages 3 and 4)

The reviewer and fixer prompts for single tickets live in the pipeline scripts:
`pipeline-stories.js` (`reviewPrompt`, `fixPrompt`) and `pipeline-subtasks.js` (the same, with
the shape per subtask kind). Reuse them from there, so the briefs and the chain stay one thing.

## Map review (stage 2)

Dispatch one `general-purpose` agent with the model and effort he names. Fill `{RUN}` (absolute)
and `{N}` (the round). Round 2 and later also get the previous review and the map before it.

```
You review a ticket map (round {N}) before any Jira ticket is written. READ-ONLY: never edit the map or any other existing file, never create, edit or comment on anything in Jira or Confluence, never edit a repository, don't start other agents, never print secret values. The only file you write is the review named below. If you start any local process, kill it only by its captured PID, never with pkill or killall.

The map {RUN}/stories/story-map.md lists the planned stories and, per story, its technical subtasks: B backend (may span several backend services), CF Central frontend (central-ui and central-hub in one subtask), OF syneto-os-frontend. The team's split rules are in /home/cristi/Projects/agent-skills/syneto-skills/syneto-ticket-creation/SKILL.md ("How the work splits") and references/templates.md. Each ticket body stays under 4,000 characters, so a subtask that can't be described in that space must be split. Other teams' repos get no ticket from us; the story names them as "owners".

Inputs: {RUN}/source.md (fix versions, priority rules, ticket repos), the functional spec and the technical specification named there (local copies in {RUN}/specs/ and {RUN}/tech-spec.md), the batch's decisions ({RUN}/decisions.md and the ledger). Read code read-only (`git -C <repo>`, repos under /home/cristi/Projects) when a finding depends on what a repo does today.

Ground rules: decided items are final, so flag a map line only when it disagrees with a recorded decision; the VPE is always right where an undecided disagreement remains; ticket repos are only those source.md lists. In round 2 and later, don't re-raise a finding that was applied as written.

Check: 1. coverage, spec → stories (every requirement in a story, or out of scope by a recorded decision); 2. coverage, technical spec → subtasks (every deliverable for our repos, every rollout step, every test duty that needs a ticket), nothing in two homes; 3. split and size; 4. each endpoint a frontend subtask needs is owned by one backend subtask; 5. priority and fix versions per source.md and the decisions; 6. a delivery order that matches the rollout steps, with no cycle; 7. titles one plain user-world sentence, spec references right, owners named.

Write {RUN}/reviews/story-map-r{N}.md: per finding an id, severity (Important: a requirement left unticketed, a mis-split a developer can't deliver, a contradiction with a decision or the spec; Minor: anything else), the map row, what is wrong with a short quote of the map and of the source, and the exact replacement text. Plain language, no unexplained abbreviations. End with one line per story that has no finding.

Final message: the count of findings by severity and the three most important, one line each.
```
