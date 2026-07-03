Your task is to run a complex staged review pipeline on plan <X> against the current codebase, built for a fleet of cheap reviewer models topped by one intelligent arbiter.

Model policy: every subagent in Stages 1–7 runs on the cheap open-source model. Stage 8 — the arbiter — runs on the most intelligent model available; if you, the orchestrator, are that model, do Stage 8 yourself instead of dispatching it.

Budget: at most 30 cheap subagents in total (2 + 10 + 6 + 3 + 1 + 7 + 1). The per-stage caps below enforce this.

Reading discipline: you may read the structured artifacts (plan map, codebase facts, clusters, synthesized review). Never read the raw review files, work-item reviews, or court verdicts — those flow between subagents. Pass every brief below verbatim, filling only the bracketed insertions.

Stage 1 — Grounding (2 subagents, parallel)

The fleet is cheap; it hallucinates paths and drowns in big scopes. Ground it first. Dispatch both subagents in a single message.

Mapper brief:

    Read plan <X> in full. Write to <Y>-plan-map.md a numbered list of work items WI-01, WI-02, … Each work item is one coherent unit of change the plan proposes (a feature slice, an endpoint, a refactor, a migration). For each work item record: a one-line summary, the exact plan section or lines it comes from, and every file path, module, endpoint, and component the plan associates with it. Do not judge the plan. Extract only. No preamble.

Fact-checker brief:

    Read plan <X> and list every file path, module, endpoint, and component it mentions. Check each against the actual codebase and write to <Y>-codebase-facts.md one line per item: EXISTS (plus the signature or shape you found there), MISSING, or MOVED (plus the new location if you can find it). Do not judge the plan. Verify only. No preamble.

Stage 2 — Review panel (10 subagents, parallel)

Launch all 10 in a single message. Ten independent perspectives, no cross-talk.

- Each subagent receives: (1) the plan path <X>, (2) its output path <Y>-plan-review-NN.md from the table below, (3) the contents of its prompt file with the placeholder lines at the bottom filled in, and (4) this grounding line appended: "Grounding files: <Y>-plan-map.md and <Y>-codebase-facts.md — use them to locate things quickly, but verify anything you rely on yourself." Nothing else.
- Pass each prompt verbatim. Do not paraphrase, condense, or "improve" it — the framing is load-bearing.
- If a prompt does not fit the project's stack, swap it and tell the user which one and why.

| NN | Prompt file | Extra placeholder fill |
|----|-------------|------------------------|
| 01 | /home/cristi/Projects/agent-skills/prompts/plan-review/single-language/plan-review-python-aggressive.md | — |
| 02 | /home/cristi/Projects/agent-skills/prompts/plan-review/single-language/plan-review-python.md | — |
| 03 | /home/cristi/Projects/agent-skills/prompts/plan-review/single-language/plan-review-vue-aggressive.md | — |
| 04 | /home/cristi/Projects/agent-skills/prompts/plan-review/single-language/plan-review-vue.md | — |
| 05 | /home/cristi/Projects/agent-skills/prompts/plan-review/single-language/plan-review-api-seam.md | <BACKEND> = Python |
| 06 | /home/cristi/Projects/agent-skills/prompts/plan-review/lenses/plan-review-security.md | — |
| 07 | /home/cristi/Projects/agent-skills/prompts/plan-review/lenses/plan-review-tests-and-migrations.md | — |
| 08 | /home/cristi/Projects/agent-skills/prompts/plan-review/lenses/plan-review-operational-readiness.md | — |
| 09 | /home/cristi/Projects/agent-skills/prompts/plan-review/generic/plan-review-loss-framing.md | — |
| 10 | /home/cristi/Projects/agent-skills/prompts/plan-review/generic/plan-review-day-off-bet.md | — |

Wait for all 10 to finish before Stage 3.

Stage 3 — Work-item sweep (up to 6 subagents, parallel)

The panel reviews by concern; this stage reviews by slice, so nothing hides between concerns.

Read <Y>-plan-map.md. If it has more than 6 work items, merge the smallest related ones so you dispatch at most 6 sweepers. Launch all sweepers in a single message, each with this brief:

    You review exactly one slice of plan <X>: [paste the work item entry (or merged entries) from <Y>-plan-map.md, including plan location and associated files]. Read that part of the plan and every associated file in the codebase. Report everything wrong with this slice: broken paths, wrong assumptions about existing code, missing pieces, mixed responsibilities, unstated risks, and anything an implementer would have to guess. State explicitly whether the slice is implementable as written. Each finding states: severity (Blocking/Important/Nit), the issue in one sentence, the plan location, the file:line citation, the concrete fix. Write to <Y>-plan-review-wi-NN.md. No hedging, no preamble.

Stage 4 — Citation check (3 subagents, parallel)

Cheap reviewers invent evidence; check all of it.

Split the review files from Stages 2 and 3 into 3 roughly equal batches. Launch 3 checkers in a single message, each with this brief:

    Read these review files: [list the batch]. For every finding in them verify only the evidence: (a) does the quoted plan text actually appear in <X>? (b) does the cited file exist, and does the cited location say what the finding claims? Verdict per finding: VALID, BROKEN (name the citation and why), or UNCHECKABLE. Do not judge whether the finding itself is right — only whether its evidence is real. Write to <Y>-citation-check-N.md one line per finding: source review file, finding summary, verdict, reason. No preamble.

Stage 5 — Clustering (1 subagent)

Dispatch one subagent with this brief:

    Read every review file <Y>-plan-review-*.md (including the wi- files) and every citation report <Y>-citation-check-*.md. Write <Y>-clusters.md. Merge findings that describe the same underlying issue into clusters CL-01, CL-02, … For each cluster record: the highest severity claimed, the issue in one sentence, the strongest citation, found-by k/M (list the review files; M is the total number of review files), citation health from the reports (VALID / BROKEN / UNCHECKABLE), and the affected work items (WI-NN). Do not add findings. Do not drop findings: anything that matches no cluster becomes its own cluster. Order by severity, then corroboration. Append a coverage matrix: work item × concern (architecture, contract, security, tests-migrations, operations) marking where at least one finding or an explicit all-clear exists, and where neither does. No preamble.

Stage 6 — Skeptic court (up to 7 subagents, parallel)

Read <Y>-clusters.md. Select up to 7 clusters: every Blocking first, then Important by corroboration. Skip clusters whose citation health is BROKEN — tag them EVIDENCE-BROKEN for the arbiter instead of sending them to court. Launch one skeptic per selected cluster, all in a single message, each with this brief:

    You are a skeptic. Here is a claimed problem with plan <X>: [paste the full cluster entry from <Y>-clusters.md]. Try to REFUTE it against the actual plan text and the actual codebase. Check the citation: does the cited code say what the cluster claims? Check the reasoning: does the problem actually follow? If the cluster survives your best attempt to kill it, your verdict is CONFIRMED, with the evidence that survived. If it does not, or you cannot verify it, your verdict is REFUTED, with the evidence or missing verification that killed it. Write to <Y>-court-CL-NN.md exactly: the verdict, then at most three sentences of evidence with file:line citations. No preamble.

Stage 7 — Synthesis (1 subagent)

Dispatch one subagent with this brief:

    Read <Y>-clusters.md and every court file <Y>-court-CL-*.md. Assemble <Y>-plan-review-synthesized.md mechanically — do not re-judge anything:
    1. Headline counts: clusters by severity, court verdicts, citation health.
    2. CONFIRMED — court-confirmed clusters, full detail, ordered by severity then corroboration.
    3. DISPUTED — clusters where the court verdict contradicts strong signals: REFUTED despite found-by 3 or more reviews, or CONFIRMED on UNCHECKABLE evidence. Present both sides verbatim.
    4. REFUTED — one line each plus the court's killing evidence.
    5. UNTRIED — clusters that never went to court (Nits, low corroboration), listed briefly.
    6. EVIDENCE-BROKEN — clusters whose citations failed the check, listed with what was broken.
    7. Coverage gaps — every work-item × concern cell with neither a finding nor an all-clear.
    8. Panel verdict tally.
    No preamble.

Stage 8 — Arbitration (1 subagent on the intelligent model, or you)

Give the intelligent model this brief:

    You are the arbiter. Read <Y>-plan-review-synthesized.md, then plan <X> itself. The synthesized review was produced by a fleet of cheap models: trust CONFIRMED entries unless something looks off, re-examine DISPUTED and EVIDENCE-BROKEN entries against the codebase yourself, and check the coverage gaps for anything the fleet missed that you can settle quickly. Write <Y>-plan-review-final.md — the definitive review: findings grouped Blocking / Important / Nit, each stating the issue in one sentence, the exact plan location, the codebase citation, and the concrete fix; a short section on what was checked and found sound; and a one-line verdict: ship as-is, ship after Blocking fixed, or rework before implementation. Resolve every DISPUTED cluster explicitly — say which side was right and why. No preamble.

<X> = 
<Y> = 
