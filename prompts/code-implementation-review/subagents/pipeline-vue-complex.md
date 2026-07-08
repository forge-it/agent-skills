Your task is to run a complex staged review pipeline on the implementation of plan <X> against the current codebase, built for a fleet of cheap reviewer models topped by one intelligent arbiter.

Model policy: every subagent in Stages 1–7 runs on the cheap open-source model. Stage 8 — the arbiter — runs on the most intelligent model available; if you, the orchestrator, are that model, do Stage 8 yourself instead of dispatching it.

Placeholders: <X> is the plan path, <Y> is the output prefix, <Z> is the git base of the implementation — the ref the change set is diffed against. If <Z> is empty, the change set is the uncommitted changes plus the commits on the current branch that are not on the default branch.

Budget: at most 30 cheap subagents in total (3 + 7 + 7 + 3 + 1 + 8 + 1). The per-stage caps below enforce this.

The fleet runs read-only: subagents may run gates and tests but never modify, stage, or commit anything.

Reading discipline: you may read the structured artifacts (plan map, change inventory, gate results, clusters, synthesized review). Never read the raw review files, work-item reviews, or court verdicts — those flow between subagents. Pass every brief below verbatim, filling only the bracketed insertions.

Stage 1 — Grounding (3 subagents, parallel)

The fleet is cheap; it hallucinates paths and drowns in big scopes. Ground it first. Dispatch all three subagents in a single message.

Mapper brief:

    Read plan <X> in full. Write to <Y>-plan-map.md a numbered list of work items WI-01, WI-02, … Each work item is one coherent unit of change the plan promises (a feature slice, a view, a component, a refactor). For each work item record: a one-line summary, the exact plan section or lines it comes from, every file path, component, composable, and store the plan associates with it, and the acceptance criterion or expected behavior if the plan states one. Do not judge anything. Extract only. No preamble.

Change-inventory brief:

    Establish the change set of the implementation with git: if <Z> is set, the change set is the diff from <Z> to the working tree (committed and uncommitted); if <Z> is empty, it is the uncommitted changes plus the commits on the current branch that are not on the default branch. Write to <Y>-change-inventory.md one line per changed file: the path, whether it was added, modified, or deleted, and a one-line summary of what changed in it. Mark test files and configuration files as such. Do not judge anything. Inventory only. No preamble.

Gate-runner brief:

    Discover the project's quality gates from its task runner and docs (justfile, Makefile, package.json scripts, CI config, CLAUDE.md). Run the standard set once — linter, type checker, and the unit test suite — scoped to the changed areas if a full run is impractical, and note any scoping you did. Write to <Y>-gate-results.md one line per gate: the exact command, PASS or FAIL, and for failures the first error with file:line. Fix nothing, change nothing. Run and record only. No preamble.

Stage 2 — Review panel (7 subagents, parallel)

Launch all 7 in a single message. Seven independent perspectives, no cross-talk.

- Each subagent receives: (1) the plan path <X>, (2) its output path <Y>-implementation-review-NN.md from the table below, (3) the contents of its prompt file with the placeholder lines at the bottom filled in (<X>, <Y>, <Z>), and (4) this grounding line appended: "Grounding files: <Y>-plan-map.md, <Y>-change-inventory.md, and <Y>-gate-results.md — use them to locate things quickly and to avoid re-running full gates, but verify anything you rely on yourself." Nothing else.
- Pass each prompt verbatim. Do not paraphrase, condense, or "improve" it — the framing is load-bearing.
- If a prompt does not fit the project's stack, swap it and tell the user which one and why.

| NN | Prompt file | Extra placeholder fill |
|----|-------------|------------------------|
| 01 | /home/cristi/Projects/agent-skills/prompts/code-implementation-review/single-language/implementation-review-vue-aggressive.md | — |
| 02 | /home/cristi/Projects/agent-skills/prompts/code-implementation-review/single-language/implementation-review-vue.md | — |
| 03 | /home/cristi/Projects/agent-skills/prompts/code-implementation-review/lenses/implementation-review-security.md | — |
| 04 | /home/cristi/Projects/agent-skills/prompts/code-implementation-review/lenses/implementation-review-tests-and-migrations.md | — |
| 05 | /home/cristi/Projects/agent-skills/prompts/code-implementation-review/generic/implementation-review-loss-framing.md | — |
| 06 | /home/cristi/Projects/agent-skills/prompts/code-implementation-review/lenses/implementation-review-divergence.md | — |
| 07 | /home/cristi/Projects/agent-skills/prompts/code-implementation-review/lenses/implementation-review-bug-hunt.md | — |

Wait for all 7 to finish before Stage 3.

Stage 3 — Work-item sweep (up to 7 subagents, parallel)

The panel reviews by concern; this stage reviews by slice, so nothing hides between concerns — and nothing hides outside the plan.

Read <Y>-plan-map.md and <Y>-change-inventory.md. Assign every changed file to the work item it implements; changed files that belong to no work item form one extra UNPLANNED slice. If the UNPLANNED slice is empty — every changed file assigned to a work item — skip the UNPLANNED sweeper; do not dispatch it. If the work items plus the UNPLANNED slice exceed 7, merge the smallest related work items so you dispatch at most 7 sweepers. A non-empty UNPLANNED slice is never dropped and never merged into a work item. Launch all sweepers in a single message. When filling each work-item sweeper brief, replace NN in its output path with the slice's work item number (WI-01 → wi-01; a merged slice uses its lowest number).

Work-item sweeper brief:

    You review exactly one slice of the implementation of plan <X>: [paste the work item entry (or merged entries) from <Y>-plan-map.md and the changed files assigned to it from <Y>-change-inventory.md]. Read that part of the plan and every assigned file in full. First judge delivery: state IMPLEMENTED, PARTIAL, MISSING, or DIVERGED, with the code citation that proves it. Then report everything wrong inside the slice: broken behavior, mixed responsibilities, missing loading/empty/failure states, unproven behaviors, missing or weakened tests, dead code. Each finding states: severity (Blocking/Important/Nit), the issue in one sentence, the file:line citation, the plan location (or "unplanned"), the concrete fix. You may run tests read-only scoped to the slice; never modify a file. Write to <Y>-implementation-review-wi-NN.md. No hedging, no preamble.

UNPLANNED sweeper brief:

    You review the unplanned slice of the implementation of plan <X>: the changed files that map to no work item in the plan: [paste the list from <Y>-change-inventory.md]. Read each in full and determine what it does. Classify each change: necessary support work for the plan, or scope creep. Scope creep is at least Important; unplanned changes to shared code, dependencies, configuration, or migrations are Blocking until the operator clears them. Also report anything broken inside these changes. Each finding states: severity, the issue in one sentence, the file:line citation, "unplanned", the concrete fix. Write to <Y>-implementation-review-wi-UN.md. No hedging, no preamble.

Stage 4 — Citation check (3 subagents, parallel)

Cheap reviewers invent evidence; check all of it.

Split the review files from Stages 2 and 3 into 3 roughly equal batches. Launch 3 checkers in a single message, each with this brief:

    Read these review files: [list the batch]. For every finding in them verify only the evidence: (a) does the quoted plan text actually appear in <X>? (b) does the cited file exist, and does the cited location say what the finding claims? (c) if the finding claims a gate or test result, does <Y>-gate-results.md or a scoped read-only re-run corroborate it? Verdict per finding: VALID, BROKEN (name the citation and why), or UNCHECKABLE. Do not judge whether the finding itself is right — only whether its evidence is real. Write to <Y>-citation-check-N.md one line per finding: source review file, finding summary, verdict, reason. No preamble.

Stage 5 — Clustering (1 subagent)

Dispatch one subagent with this brief:

    Read every review file <Y>-implementation-review-*.md (including the wi- files) and every citation report <Y>-citation-check-*.md. Write <Y>-clusters.md. Merge findings that describe the same underlying issue into clusters CL-01, CL-02, … For each cluster record: the highest severity claimed, the issue in one sentence, the strongest citation, found-by k/M (list the review files; M is the total number of review files), citation health from the reports (VALID / BROKEN / UNCHECKABLE), and the affected work items (WI-NN or UNPLANNED). Do not add findings. Do not drop findings: anything that matches no cluster becomes its own cluster. Order by severity, then corroboration. Append a work-item status table: each work item's IMPLEMENTED / PARTIAL / MISSING / DIVERGED status as stated by its sweep file, plus one line summarizing the UNPLANNED slice. Append a coverage matrix: work item × concern (plan-conformance, separation-of-concerns, reactivity-types, ux-states, security, tests) marking where at least one finding or an explicit all-clear exists, and where neither does. No preamble.

Stage 6 — Skeptic court (up to 8 subagents, parallel)

Read <Y>-clusters.md. Select up to 8 clusters: every Blocking first, then Important by corroboration. Skip clusters whose citation health is BROKEN — tag them EVIDENCE-BROKEN for the arbiter instead of sending them to court. Launch one skeptic per selected cluster, all in a single message, each with this brief:

    You are a skeptic. Here is a claimed problem with the implementation of plan <X>: [paste the full cluster entry from <Y>-clusters.md]. Try to REFUTE it against the actual code and the actual plan text. Check the citation: does the cited code say what the cluster claims? Check the reasoning: does the problem actually follow? You may run the cited test or a scoped read-only command to settle the claim — never modify a file. If the cluster survives your best attempt to kill it, your verdict is CONFIRMED, with the evidence that survived. If it does not, or you cannot verify it, your verdict is REFUTED, with the evidence or missing verification that killed it. Write to <Y>-court-CL-NN.md exactly: the verdict, then at most three sentences of evidence with file:line citations. No preamble.

Stage 7 — Synthesis (1 subagent)

Dispatch one subagent with this brief:

    Read <Y>-clusters.md, every court file <Y>-court-CL-*.md, and <Y>-gate-results.md. Assemble <Y>-implementation-review-synthesized.md mechanically — do not re-judge anything:
    1. Headline counts: clusters by severity, court verdicts, citation health, gates passed and failed.
    2. Work-item status table and the UNPLANNED summary, copied from <Y>-clusters.md.
    3. CONFIRMED — court-confirmed clusters, full detail, ordered by severity then corroboration.
    4. DISPUTED — clusters where the court verdict contradicts strong signals: REFUTED despite found-by 3 or more reviews, or CONFIRMED on UNCHECKABLE evidence. Present both sides verbatim.
    5. REFUTED — one line each plus the court's killing evidence.
    6. UNTRIED — clusters that never went to court. For each: cluster id, severity, one-line summary, and the reason it was not tried (Nit, low corroboration, or court cap reached). Blocking and Important untried clusters get full detail, not a brief line.
    7. EVIDENCE-BROKEN — clusters whose citations failed the check, listed with what was broken.
    8. Coverage gaps — every work-item × concern cell with neither a finding nor an all-clear.
    9. Panel verdict tally.
    No preamble.

Stage 8 — Arbitration (1 subagent on the intelligent model, or you)

Give the intelligent model this brief:

    You are the arbiter. Read <Y>-implementation-review-synthesized.md, then plan <X> itself. The synthesized review was produced by a fleet of cheap models: trust CONFIRMED entries unless something looks off, re-examine DISPUTED and EVIDENCE-BROKEN entries against the actual code yourself, re-examine every Blocking or Important cluster in UNTRIED — the court cap may have skipped it, not cleared it — and check the coverage gaps and the work-item status table for anything the fleet missed that you can settle quickly. You may run gates and tests read-only to settle a dispute; never modify a file. Write <Y>-implementation-review-final.md — the definitive review: findings grouped Blocking / Important / Nit, each stating the issue in one sentence, the file:line citation, the plan location (or "unplanned"), and the concrete fix; a work-item status roll-up stating plainly whether the plan is fully implemented; a short section on what was checked and found sound; and a one-line verdict: merge as-is, merge after Blocking fixed, or return to implementation. Resolve every DISPUTED cluster explicitly — say which side was right and why. No preamble.

<X> = 
<Y> = 
<Z> = 
