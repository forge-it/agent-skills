export const meta = {
  name: 'software-editions-stories',
  description: 'Write the 28 software-editions stories: 1 Sonnet xhigh writer per story, then review, fix, review, fix (max 10 agents at a time)',
  phases: [
    { title: 'Write', detail: 'one writer per story', model: 'sonnet' },
    { title: 'Review 1', detail: 'one reviewer per story', model: 'sonnet' },
    { title: 'Fix 1', detail: 'one fixer per story with findings', model: 'sonnet' },
    { title: 'Review 2', detail: 'one reviewer per story', model: 'sonnet' },
    { title: 'Fix 2', detail: 'one fixer per story with findings', model: 'sonnet' },
  ],
}

// Worked example: the stories phase of the software-editions-6.1 batch (2026-10-21/22). To reuse it, copy it and
// change RUN, the page links and the role intro in CONTEXT, the code refs and the args (built from the
// approved map, see SKILL.md "The writing pipeline"). Keep the limiter, the review/fix chain and the schemas.

const RUN = '/home/cristi/.cache/ticket-delivery/software-editions-6.1'
const SKILL = '/home/cristi/Projects/agent-skills/syneto-skills/syneto-ticket-creation'
const OPTS = { model: 'sonnet', effort: 'xhigh', agentType: 'general-purpose' }

// at most 10 agents of ours at a time (Cristi's rule; explorers the agents start don't count)
let active = 0
const waiters = []
async function limited(fn) {
  while (active >= 10) await new Promise(r => waiters.push(r))
  active++
  try { return await fn() } finally { active--; const w = waiters.shift(); if (w) w() }
}
const run = (prompt, opts) => limited(() => agent(prompt, { ...OPTS, ...opts }))

const CONTEXT = (role) => `You work on one Jira ticket draft for Syneto's SYN board: the "software editions" licensing work for SynetoOS 6.1.0 (machine side) and Central 2.9 (cloud side), epic SYN-3331. Your role: ${role}.

Read before you work:
- The team's ticketing skill: ${SKILL}/SKILL.md and its templates ${SKILL}/references/templates.md. Follow them exactly; they win over your habits. (Its stage gates about showing drafts to the operator chunk by chunk don't apply to you: the operator reviews everything at the end.)
- The batch facts: ${RUN}/source.md (fix versions, priority rules, sprint, epic, ticket repos, assignees).
- The ticket map (approved, final): ${RUN}/stories/story-map.md. Your ticket's row, its neighbours (so you don't take their content), the notes under each table, and the "Delivery order" section.
- The functional spec ("Spec", v49): ${RUN}/specs/refetch-2026-10-21b/spec-cur.txt. Its real list numbering (§6.1.2, §6.3.1.4, …) is visible only in ${RUN}/specs/refetch-2026-10-21b/spec-v49.storage.html: cite sections by that numbering.
- The companion pages: ${RUN}/specs/refetch-2026-10-21/proposal-v42.txt ("License states and enforcement") and ${RUN}/specs/refetch-2026-10-20/model-licensing-2027-v3.1.md ("Licensing model 2027 v3.1").
- The technical specification: ${RUN}/tech-spec.md (revision 50, large: read the sections your ticket covers in full and search the rest). It records every decision taken with the PO and the VPE (Appendix A, [Dnn]); where it and the pages disagree, it holds the decision.
- Decisions: ${RUN}/decisions.md. Decided items are final: never reopen one. The VPE is always right where an undecided disagreement remains.
- The team's model tickets: ${RUN}/models/SYN-2348-story.md (a story) and ${RUN}/models/SYN-3007-frontend-subtask.md (a frontend subtask).

Page links for the spec line (every ticket links all four pages, the epic's rule; name the exact sections it covers where it draws on a page, functional spec first, technical spec second):
- Software editions spec: https://syneto.atlassian.net/wiki/spaces/PROD/pages/5662146563/Software+editions+spec
- License states and enforcement: https://syneto.atlassian.net/wiki/spaces/PROD/pages/5678956558/Software+editions+license+states+and+enforcement
- Licensing model 2027 v3.1: https://syneto.atlassian.net/wiki/spaces/PROD/pages/5661392953/Licensing+model+2027+--+v3.1
- Technical specification: https://syneto.atlassian.net/wiki/spaces/generics/pages/5684199426

Voice: a colleague writing to a colleague. Plain words, short sentences, concrete examples. No boilerplate ("This ticket aims to…"), no restating the spec, nothing said twice. Formal spec-template prose gets these tickets dismissed as AI slop. Never invent a route, field, setting, caller or screen to fill a gap: if the Spec and the tech spec don't say it, report it as a gap instead.

Rules:
- Write only the file(s) your role names. Read-only everywhere else: no edits to any repository, other drafts, the map, the tech spec, the decisions or the ledger; nothing in Jira or Confluence (no create, edit, comment or transition).
- To check what a repo does today you may start at most 2 explorer subagents (Agent tool, subagent_type "Explore", model "sonnet", effort "xhigh"), read-only, with absolute repo paths under /home/cristi/Projects and \`git -C <repo>\` at branch central-2.10 (Central repos) or release-6.1.0 (syneto-* repos). You may also read code yourself the same way.
- Never print or copy secret values. If you start any process, kill it only by its captured PID; never pkill or killall.
- The body (everything after the front matter) stays under 4,000 characters. Check it: python3 -c "import sys; print(len(open(sys.argv[1]).read().split('---',2)[2]))" <file>`

const WRITE_SCHEMA = { type: 'object', properties: {
  file: { type: 'string' }, bodyChars: { type: 'integer' },
  gaps: { type: 'array', items: { type: 'string' } }, explorersUsed: { type: 'integer' } },
  required: ['file', 'bodyChars', 'gaps'] }
const REVIEW_SCHEMA = { type: 'object', properties: {
  reviewFile: { type: 'string' }, important: { type: 'integer' }, minor: { type: 'integer' } },
  required: ['reviewFile', 'important', 'minor'] }
const FIX_SCHEMA = { type: 'object', properties: {
  fixLog: { type: 'string' }, applied: { type: 'integer' }, notApplied: { type: 'integer' }, bodyChars: { type: 'integer' } },
  required: ['fixLog', 'applied', 'notApplied', 'bodyChars'] }

const row = (s) => `Story ${s.nn} of the map.
- Map title: ${s.title}
- Spec sections: ${s.spec}
- Priority: ${s.priority}
- Fix versions: ${JSON.stringify(s.fixVersions)}
- Planned technical subtasks (the work behind it; the story describes behaviour, not these): ${s.plannedSubtasks}
${s.notes ? '- Notes: ' + s.notes : ''}`

const writePrompt = (s) => `${CONTEXT('story writer')}

Your ticket: ${row(s)}

Write ${RUN}/stories/${s.nn}.md. Front matter first:
---
summary: "<the map's title, or a plainer user-world sentence with the same meaning>"
priority: ${s.priority}
fix_versions: ${JSON.stringify(s.fixVersions)}
parent: SYN-3331
sprint: 1043
estimate: "(sum of its subtasks, filled after the subtasks)"
spec_sections: [<the Spec sections it covers, v49 numbering>]
<links: only if the notes give them>
---
Then the body in the skill's Story template: "### User Story" in first person ("**As a <who>**, I want …, so that …", then up to about 13 lines of plain prose covering the whole behaviour end to end: Central, the machine and the SynetoOS UI), "### Acceptance Criteria" grouped under "####" areas, about 10 bullets in all, each one something a person can check in the product, then the spec line. No endpoint, path, field name, payload, table, code or repo name in a story. Cover the Spec sections end to end, including what other teams' work (the owners) makes visible to the user; don't take content that belongs to a neighbouring story (name the neighbour inline when a reader needs the pointer).

Return: the file path, the body length you measured, the gaps (things the sources don't settle; empty if none), and how many explorers you used.`

const reviewPrompt = (s, r) => `${CONTEXT(`reviewer, round ${r} of 2: read-only, you write only your review file`)}

Review the draft ${RUN}/stories/${s.nn}.md: ${row(s)}
${r === 2 ? `Round 1's review is ${RUN}/reviews/stories/${s.nn}-r1.md and the fixer's log ${RUN}/reviews/stories/${s.nn}-r1-fixes.md (may be absent when round 1 found nothing). Don't re-raise a round-1 finding that was applied. Re-raise one only if the fix is wrong or incomplete, or if the fixer rejected it and you can show the rejection is wrong (quote the source).` : ''}

Check:
1. Shape: the Story template exactly (User Story in first person, grouped Acceptance Criteria of about 10 checkable bullets, the spec line last linking all four pages); no endpoint, path, field, payload, table, code or repo name.
2. Size and voice: body under 4,000 characters (run the check); plain human voice; nothing said twice; no boilerplate; no out-of-scope lists.
3. Truth: every Spec section cited exists in v49 with that number and says what the draft says; every behaviour matches the tech spec and the decisions. Nothing invented.
4. Coverage: the draft covers its Spec sections end to end (Central, machine, SynetoOS UI, and what other teams' work makes visible) and takes no neighbour story's content (see the map).
5. Fields: summary is one plain user-world sentence with no prefix; priority, fix versions, parent SYN-3331, sprint 1043 as the map and source.md say; links as the map's notes say.

Write ${RUN}/reviews/stories/${s.nn}-r${r}.md: per finding an id (F1, F2, …), severity (Important: would mislead or block whoever picks it up, or contradicts the Spec, the tech spec or a decision; Minor: anything else), what is wrong with a short quote of the draft and of the source (Spec section, tech-spec section and line number, or decision id), and the exact replacement text. Plain language. If there is nothing to fix, write "No findings." and list the checks you ran.

Return: the review file path and the counts by severity.`

const fixPrompt = (s, r) => `${CONTEXT(`fixer, round ${r} of 2: you edit only the draft file and write only your fix log`)}

Apply round ${r}'s review ${RUN}/reviews/stories/${s.nn}-r${r}.md to the draft ${RUN}/stories/${s.nn}.md (${row(s)}).
${r === 2 ? `For context, round 1's review and fix log are ${RUN}/reviews/stories/${s.nn}-r1.md and ${RUN}/reviews/stories/${s.nn}-r1-fixes.md.` : ''}
Apply every finding with its replacement text, or a better wording that fixes the same problem. When a finding is wrong (it contradicts the Spec, the tech spec, a decision or the code), leave the draft as it is for that finding and say why, quoting the source. Keep the template, the voice and the 4,000-character limit (measure after editing).

Write ${RUN}/reviews/stories/${s.nn}-r${r}-fixes.md: one line per finding id: applied / applied differently (how) / not applied (why, with the quote).

Return: the fix log path, how many findings you applied and didn't, and the body length after your edits.`

const stories = args
log(`${stories.length} stories; at most 10 agents at a time`)

// Each story may carry `start` (from scripts/pipeline_state.py): a relaunch then skips every stage
// that is already done without spending an agent. Omitted means write.
const STAGES = ['write', 'review1', 'fix1', 'review2', 'fix2', 'done']
const at = (s, stage) => STAGES.indexOf(stage) >= STAGES.indexOf(s.start || 'write')
const results = await pipeline(stories,
  (_, s) => at(s, 'write') ? run(writePrompt(s), { label: `write:${s.nn}`, phase: 'Write', schema: WRITE_SCHEMA }) : null,
  async (w, s) => ({ w, r1: at(s, 'review1') ? await run(reviewPrompt(s, 1), { label: `review1:${s.nn}`, phase: 'Review 1', schema: REVIEW_SCHEMA }) : null }),
  async (acc, s) => ({ ...acc, f1: (s.start === 'fix1' || (acc.r1 && acc.r1.important + acc.r1.minor > 0))
    ? await run(fixPrompt(s, 1), { label: `fix1:${s.nn}`, phase: 'Fix 1', schema: FIX_SCHEMA }) : null }),
  async (acc, s) => ({ ...acc, r2: at(s, 'review2') ? await run(reviewPrompt(s, 2), { label: `review2:${s.nn}`, phase: 'Review 2', schema: REVIEW_SCHEMA }) : null }),
  async (acc, s) => ({ ...acc, f2: (s.start === 'fix2' || (acc.r2 && acc.r2.important + acc.r2.minor > 0))
    ? await run(fixPrompt(s, 2), { label: `fix2:${s.nn}`, phase: 'Fix 2', schema: FIX_SCHEMA }) : null }),
)

const summary = stories.map((s, i) => {
  const r = results[i]
  if (!r) return { nn: s.nn, failed: true }
  return { nn: s.nn, bodyChars: (r.f2 || r.f1 || r.w || {}).bodyChars, gaps: r.w ? r.w.gaps : null,
    r1: r.r1 ? `${r.r1.important}I/${r.r1.minor}m` : 'missing', f1: r.f1 ? `${r.f1.applied} applied, ${r.f1.notApplied} not` : '-',
    r2: r.r2 ? `${r.r2.important}I/${r.r2.minor}m` : 'missing', f2: r.f2 ? `${r.f2.applied} applied, ${r.f2.notApplied} not` : '-' }
})
const failed = summary.filter(x => x.failed).map(x => x.nn)
if (failed.length) log(`Stories with a dead stage: ${failed.join(', ')}`)
return summary