export const meta = {
  name: 'software-editions-subtasks',
  description: 'Write the 75 software-editions technical subtasks: 1 Sonnet xhigh writer per subtask, then review, fix, review, fix (max 10 agents at a time); backend before frontend',
  phases: [
    { title: 'Write', detail: 'one writer per subtask', model: 'sonnet' },
    { title: 'Review 1', detail: 'one reviewer per subtask', model: 'sonnet' },
    { title: 'Fix 1', detail: 'one fixer per subtask with findings', model: 'sonnet' },
    { title: 'Review 2', detail: 'one reviewer per subtask', model: 'sonnet' },
    { title: 'Fix 2', detail: 'one fixer per subtask with findings', model: 'sonnet' },
  ],
}

// Worked example: the subtasks phase of the software-editions-6.1 batch (2026-10-21/22). To reuse it, copy it and
// change RUN, the page links and the role intro in CONTEXT, the code refs and the args (built from the
// approved map, see SKILL.md "The writing pipeline"). Keep the limiter, the review/fix chain and the schemas.

const RUN = '/home/cristi/.cache/ticket-delivery/software-editions-6.1'
const SKILL = '/home/cristi/Projects/agent-skills/syneto-skills/syneto-ticket-creation'
const MEM = '/home/cristi/.claude/projects/-home-cristi-Projects/memory'
const OPTS = { model: 'sonnet', effort: 'xhigh', agentType: 'general-purpose' }

let active = 0
const waiters = []
async function limited(fn) {
  while (active >= 10) await new Promise(r => waiters.push(r))
  active++
  try { return await fn() } finally { active--; const w = waiters.shift(); if (w) w() }
}
const run = (prompt, opts) => limited(() => agent(prompt, { ...OPTS, ...opts }))

const CENTRAL = ['rest-api', 'central-backend', 'central', 'central-ui', 'central-hub', 'automatic-operations-products']
const PRI = { H: 'High', M: 'Medium', L: 'Low' }
// the batch's machine-side fix version per priority (Cristi 2026-10-22: High 6.1.0.RC6, Medium and Low 6.1.1)
const MACHINE_VERSION = { High: '6.1.0.RC6', Medium: '6.1.1', Low: '6.1.1' }
// args: [id, priority letter, repos, start stage]. The start stage comes from scripts/pipeline_state.py
// (write when omitted), so a relaunch skips every stage that is already done without spending an agent.
const items = args.map(([id, p, repos, start]) => {
  const kind = id.split('-')[1].replace(/\d+$/, '')
  const story = id.split('-')[0]
  const fv = []
  if (repos.some(r => !CENTRAL.includes(r))) fv.push(MACHINE_VERSION[PRI[p]])
  if (repos.some(r => CENTRAL.includes(r))) fv.push('central-2.9')
  const assignee = kind === 'CF' ? 'Nicolas Vannier, accountId 60b734888cf9190069665ba1'
    : kind === 'OF' ? 'Robert Călin, accountId 557058:8583b083-d092-440b-b164-0d087267fe7a' : 'unassigned'
  return { id, story, kind, repos, priority: PRI[p], fixVersions: fv, assignee, labels: kind === 'B' ? [] : ['UI'], start: start || 'write' }
})

const CONTEXT = (role) => `You work on one Jira ticket draft for Syneto's SYN board: the "software editions" licensing work for SynetoOS 6.1.0 (machine side) and Central 2.9 (cloud side), epic SYN-3331. Your role: ${role}.

The stories are written and reviewed; this phase writes the technical subtasks under them.

Read before you work:
- The team's ticketing skill: ${SKILL}/SKILL.md and its templates ${SKILL}/references/templates.md. Follow them exactly; they win over your habits. (Its "show the operator, wait for yes" gates don't apply to you: the operator reviews everything at the end.)
- The batch facts: ${RUN}/source.md.
- The subtask index: ${RUN}/tasks/index.md. Every subtask's id, story, kind, repos, priority, fix versions and what it delivers, plus each story's owners (other teams). Tickets point at each other by these ids until they exist in Jira (for example "Full API contract: **03-B5**").
- The ticket map (approved, final): ${RUN}/stories/story-map.md, especially the notes and the "Delivery order" section (rollout steps of tech spec §5.7).
- Your story's draft: ${RUN}/stories/<NN>.md (final, reviewed). Your subtask delivers its part of that story's acceptance criteria.
- The functional spec ("Spec", v49): ${RUN}/specs/refetch-2026-10-21b/spec-cur.txt; real list numbering only in ${RUN}/specs/refetch-2026-10-21b/spec-v49.storage.html.
- Companion pages: ${RUN}/specs/refetch-2026-10-21/proposal-v42.txt ("License states and enforcement") and ${RUN}/specs/refetch-2026-10-20/model-licensing-2027-v3.1.md ("Licensing model 2027 v3.1").
- The technical specification: ${RUN}/tech-spec.md (revision 50, large: read the sections your subtask covers in full and search the rest). It holds every decision taken with the PO and the VPE (Appendix A, [Dnn]). A subtask is the tech spec cut down to what one developer needs for this piece.
- Decisions: ${RUN}/decisions.md. Decided items are final: never reopen one. The VPE is always right where an undecided disagreement remains.
- Frontend subtasks only: the UI ticket playbook ${MEM}/frontend-ticket-template.md and ${MEM}/frontend-tickets-no-implementation-details.md (what the user gets plus the API contract; nothing about how to build it), and the model ${RUN}/models/SYN-3007-frontend-subtask.md.
- REST endpoints in rest-api: house conventions are in the syneto-rest-api-design skill (Skill tool); the tech spec's contract wins where it is specific.

Code: the repos are under /home/cristi/Projects and were fetched today. Read them read-only with \`git -C <repo>\` at origin/central-2.10 (rest-api, central-backend, central-ui, central-hub), origin/release-6.1.0 (syneto-mercurio, syneto-os-frontend), origin/master (automatic-operations-products), and for the deploy repo \`central\` every environment branch (\`git -C /home/cristi/Projects/central branch -r\`; one branch per live environment, env vars hardcoded in Pulumi Python). Never run git fetch, checkout, or anything that changes a repo. Code pointers in a ticket are \`repo:path:line\` at the commit you read, named once (e.g. \`rest-api origin/central-2.10@abc1234\`); verify every pointer you write, because the tech spec's line numbers are from 2026-10-20 and may have moved. You may start at most 2 explorer subagents (Agent tool, subagent_type "Explore", model "sonnet", effort "xhigh"), read-only, to check facts.

Page links for the spec line (every ticket links all four pages, the epic's rule; name the exact sections it covers, functional spec first, technical spec second):
- Software editions spec: https://syneto.atlassian.net/wiki/spaces/PROD/pages/5662146563/Software+editions+spec
- License states and enforcement: https://syneto.atlassian.net/wiki/spaces/PROD/pages/5678956558/Software+editions+license+states+and+enforcement
- Licensing model 2027 v3.1: https://syneto.atlassian.net/wiki/spaces/PROD/pages/5661392953/Licensing+model+2027+--+v3.1
- Technical specification: https://syneto.atlassian.net/wiki/spaces/generics/pages/5684199426

Voice: a colleague writing to a colleague. Plain words, short sentences, concrete examples. No boilerplate, no restating the spec, nothing said twice, no content of a sibling subtask (name the sibling's id inline instead). Formal spec-template prose gets these tickets dismissed as AI slop. Never invent a route, field, setting, caller or screen to fill a gap: report it as a gap instead.

Rules:
- Write only the file(s) your role names. Read-only everywhere else: no edits to any repository, other drafts, the index, the map, the tech spec, the decisions or the ledger; nothing in Jira or Confluence.
- Never print or copy secret values. If you start any process, kill it only by its captured PID; never pkill or killall.
- The body (everything after the front matter) stays under 4,000 characters. Check it: python3 -c "import sys; print(len(open(sys.argv[1]).read().split('---',2)[2]))" <file>`

const WRITE_SCHEMA = { type: 'object', properties: {
  file: { type: 'string' }, bodyChars: { type: 'integer' }, estimateHours: { type: 'integer' },
  gaps: { type: 'array', items: { type: 'string' } }, explorersUsed: { type: 'integer' } },
  required: ['file', 'bodyChars', 'estimateHours', 'gaps'] }
const REVIEW_SCHEMA = { type: 'object', properties: {
  reviewFile: { type: 'string' }, important: { type: 'integer' }, minor: { type: 'integer' } },
  required: ['reviewFile', 'important', 'minor'] }
const FIX_SCHEMA = { type: 'object', properties: {
  fixLog: { type: 'string' }, applied: { type: 'integer' }, notApplied: { type: 'integer' }, bodyChars: { type: 'integer' }, estimateHours: { type: 'integer' } },
  required: ['fixLog', 'applied', 'notApplied', 'bodyChars'] }

const KIND_NAME = { B: 'backend subtask', CF: 'Central frontend subtask (central-ui and central-hub)', OF: 'syneto-os-frontend subtask' }
const SHAPE = {
  B: 'the skill\'s "Backend subtask" template: the repos line first ("**Repos:** …"), then **What to build** (with verified code pointers and the commit named once), **API contract** (only when this subtask adds or changes an endpoint or RPC; this subtask then owns it and frontend subtasks point here), **Data** (only when schema or stored data changes), **Tests** (by tier, one line each), **Acceptance criteria**, then the spec line',
  CF: 'the skill\'s "Central frontend subtask" template, per the UI playbook and SYN-3007: the repos line first ("**Repos:** …"), then **Description** (first person, what the user gets, up to about 13 lines, no links), **API Usage** (the endpoint, numbered steps of what the UI does with the verb and call in the sentence, bodies in json blocks, tables for fields and statuses, then "Full API contract: **<backend subtask id>**"), **Acceptance criteria** (checkable in the UI, at most 10), then the spec line. Nothing about how to build it (no state, components, refresh or storage decisions)',
  OF: 'the skill\'s "syneto-os-frontend subtask" template, per the UI playbook and SYN-3007: NO repos line; **Description** (first person, what the user gets, up to about 13 lines, no links), **API Usage** (the endpoint, numbered steps, bodies in json blocks, tables for fields and statuses, then "Full API contract: **<backend subtask id>**", or the tech spec section and owner when another team owns the contract), **Acceptance criteria** (checkable in the UI, at most 10), then the spec line. Nothing about how to build it',
}
const desc = (t) => `Subtask ${t.id}: a ${KIND_NAME[t.kind]} of story ${t.story} (${RUN}/stories/${t.story}.md). Its row in ${RUN}/tasks/index.md says what it delivers.
- Repos: ${t.repos.join(', ')}
- Priority: ${t.priority}
- Fix versions: ${JSON.stringify(t.fixVersions)}
- Assignee: ${t.assignee}
- Labels: ${JSON.stringify(t.labels)}`

const writePrompt = (t) => `${CONTEXT(`writer of subtask ${t.id}`)}

Your ticket: ${desc(t)}
${t.kind !== 'B' ? `The backend subtasks this one depends on are already written and reviewed: read the drafts in ${RUN}/tasks/ for your story's backend ids (and any other backend id the index or the delivery order makes you depend on), and point to the one that owns each contract you use.` : 'Frontend subtasks of your story will point to you for any contract you own: write it completely (route and verb, request and response bodies, status codes and what each means).'}

Write ${RUN}/tasks/${t.id}.md. Front matter first:
---
id: ${t.id}
summary: "<one plain sentence saying what changes for the user or the system; no repo or area prefix, no trailing period>"
type: Subtask
parent_story: "${t.story} (stories/${t.story}.md; the SYN key once created)"
priority: ${t.priority}
fix_versions: ${JSON.stringify(t.fixVersions)}
assignee: "${t.assignee}"
labels: ${JSON.stringify(t.labels)}
repos: ${JSON.stringify(t.repos)}
estimate: "<hours, e.g. 12h; a Jira day is 8h, write 12h not 1d 4h>"
estimate_reason: "<one line for the operator, never posted>"
---
Then the body in ${SHAPE[t.kind]}.

Return: the file path, the body length you measured, the estimate in hours, the gaps (things the sources don't settle; empty if none), and how many explorers you used.`

const reviewPrompt = (t, r) => `${CONTEXT(`reviewer of subtask ${t.id}, round ${r} of 2: read-only, you write only your review file`)}

Review the draft ${RUN}/tasks/${t.id}.md: ${desc(t)}
${r === 2 ? `Round 1's review is ${RUN}/reviews/tasks/${t.id}-r1.md and the fixer's log ${RUN}/reviews/tasks/${t.id}-r1-fixes.md (may be absent when round 1 found nothing). Don't re-raise a round-1 finding that was applied. Re-raise one only if the fix is wrong or incomplete, or if the fixer rejected it and you can show the rejection is wrong (quote the source).` : ''}

Check:
1. Shape: ${SHAPE[t.kind]}.
2. Size and voice: body under 4,000 characters (run the check); plain human voice; nothing said twice; no boilerplate; no sibling's content.
3. Truth: every code pointer, path, route, field, status code and behaviour exists and says what the draft says (open the code at the refs named above); the contract matches the tech spec; the Spec sections cited exist in v49 with that number. Nothing invented.
4. Coverage: the draft delivers everything its index row names, and its part of the story's acceptance criteria; it doesn't take a sibling subtask's work; ${t.kind === 'B' ? 'it fully specifies any contract it owns' : 'it points to the backend subtask (or the owner team and tech-spec section) that owns each contract it uses, and its API Usage matches that contract exactly'}.
5. Split: one developer can deliver it in one go; if it can't fit 4,000 characters it must be two subtasks (say so as an Important finding).
6. Fields: summary one plain sentence with no prefix; priority, fix versions, assignee, labels and repos exactly as given above; estimate in hours with a one-line reason, and plausible for the work.

Write ${RUN}/reviews/tasks/${t.id}-r${r}.md: per finding an id (F1, F2, …), severity (Important: would mislead or block whoever picks it up, or contradicts the code, the Spec, the tech spec or a decision; Minor: anything else), what is wrong with a short quote of the draft and of the source (code pointer, Spec section, tech-spec section and line, or decision id), and the exact replacement text. Plain language. If there is nothing to fix, write "No findings." and list the checks you ran.

Return: the review file path and the counts by severity.`

const fixPrompt = (t, r) => `${CONTEXT(`fixer of subtask ${t.id}, round ${r} of 2: you edit only the draft file and write only your fix log`)}

Apply round ${r}'s review ${RUN}/reviews/tasks/${t.id}-r${r}.md to the draft ${RUN}/tasks/${t.id}.md (${desc(t)}).
${r === 2 ? `For context, round 1's review and fix log are ${RUN}/reviews/tasks/${t.id}-r1.md and ${RUN}/reviews/tasks/${t.id}-r1-fixes.md.` : ''}
Apply every finding with its replacement text, or a better wording that fixes the same problem. When a finding is wrong (it contradicts the code, the Spec, the tech spec or a decision), leave the draft as it is for that finding and say why, quoting the source. If a finding says the subtask is too big to fit, don't split it yourself: tighten it to fit if you can and record the finding for the operator. Keep the template, the voice and the 4,000-character limit (measure after editing).

Write ${RUN}/reviews/tasks/${t.id}-r${r}-fixes.md: one line per finding id: applied / applied differently (how) / not applied (why, with the quote).

Return: the fix log path, how many findings you applied and didn't, the body length after your edits, and the estimate in hours after your edits.`

const STAGES = ['write', 'review1', 'fix1', 'review2', 'fix2', 'done']
async function chain(t) {
  const from = STAGES.indexOf(t.start)
  const at = (stage) => STAGES.indexOf(stage) >= from
  try {
    const w = at('write') ? await run(writePrompt(t), { label: `write:${t.id}`, phase: 'Write', schema: WRITE_SCHEMA }) : null
    const r1 = at('review1') ? await run(reviewPrompt(t, 1), { label: `review1:${t.id}`, phase: 'Review 1', schema: REVIEW_SCHEMA }) : null
    // a chain that starts at fix1 already has a review with findings on disk
    const f1 = (t.start === 'fix1' || (r1 && r1.important + r1.minor > 0)) ? await run(fixPrompt(t, 1), { label: `fix1:${t.id}`, phase: 'Fix 1', schema: FIX_SCHEMA }) : null
    const r2 = at('review2') ? await run(reviewPrompt(t, 2), { label: `review2:${t.id}`, phase: 'Review 2', schema: REVIEW_SCHEMA }) : null
    const f2 = (t.start === 'fix2' || (r2 && r2.important + r2.minor > 0)) ? await run(fixPrompt(t, 2), { label: `fix2:${t.id}`, phase: 'Fix 2', schema: FIX_SCHEMA }) : null
    return { id: t.id, w, r1, f1, r2, f2 }
  } catch (e) {
    log(`${t.id}: a stage failed (${String(e).slice(0, 120)})`)
    return { id: t.id, failed: true }
  }
}

// frontend subtasks wait for the backend subtasks that own their contracts
const EXTRA_DEPS = { '04': ['03', '12'], '05': ['03'], '06': ['03'], '07': ['03'], '08': ['03'], '09': ['03'], '10': ['03'], '11': ['03'], '12': ['03'], '15': ['14'], '19': ['03'], '21': ['01', '03'] }
const stories = [...new Set(items.map(t => t.story))]
const backendDone = {}
for (const s of stories) {
  backendDone[s] = Promise.all(items.filter(t => t.story === s && t.kind === 'B').map(chain))
}
const frontend = items.filter(t => t.kind !== 'B').map(async t => {
  await Promise.all([t.story, ...(EXTRA_DEPS[t.story] || [])].map(s => backendDone[s]))
  return chain(t)
})
log(`${items.length} subtasks (${items.filter(t => t.kind === 'B').length} backend first, ${items.filter(t => t.kind !== 'B').length} frontend after their backends); at most 10 agents at a time`)

const backendResults = (await Promise.all(stories.map(s => backendDone[s]))).flat()
const frontendResults = await Promise.all(frontend)
const all = [...backendResults, ...frontendResults]

const fmt = (r) => r ? `${r.important}I/${r.minor}m` : 'skipped or missing'
const summary = items.map(t => {
  const r = all.find(x => x && x.id === t.id)
  if (!r || r.failed) return { id: t.id, failed: true }
  const last = r.f2 || r.f1 || {}
  return { id: t.id, bodyChars: last.bodyChars || (r.w && r.w.bodyChars), estimateHours: last.estimateHours || (r.w && r.w.estimateHours),
    gaps: r.w ? r.w.gaps : null, r1: fmt(r.r1), f1: r.f1 ? `${r.f1.applied} applied, ${r.f1.notApplied} not` : '-',
    r2: fmt(r.r2), f2: r.f2 ? `${r.f2.applied} applied, ${r.f2.notApplied} not` : '-' }
})
const failed = summary.filter(x => x.failed).map(x => x.id)
if (failed.length) log(`Subtasks with a failed stage: ${failed.join(', ')}`)
return summary