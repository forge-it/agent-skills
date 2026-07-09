Your task is to run a complex staged review pipeline on the implementation of Jira ticket <X> against the current codebase, built for a fleet of cheap reviewer models topped by one intelligent arbiter. The ticket plays the role a plan plays in the sibling pipeline: the spec of promised behaviors the implementation is judged against.

Model policy: every subagent in Stages 1–7 runs on the cheap open-source model. Stage 8 — the arbiter — runs on the most intelligent model available; if you, the orchestrator, are that model, do Stage 8 yourself instead of dispatching it.

Placeholders: <X> is the Jira ticket key (for example PROJ-123), <Y> is the output prefix, <Z> is the git base of the implementation — the ref the change set is diffed against. If <Z> is empty, the change set is the uncommitted changes plus the commits on the current branch that are not on the default branch.

Budget: at most 30 cheap subagents in total (3 + 8 + 6 + 3 + 1 + 8 + 1). Stage 0 costs none — you do it yourself. The per-stage caps below enforce this.

The fleet runs read-only: subagents may run gates and tests but never modify, stage, or commit anything.

Reading discipline: you may read the structured artifacts (materialized ticket, work-item map, change inventory, gate results, clusters, synthesized review). Never read the raw review files, work-item reviews, or court verdicts — those flow between subagents. Pass every brief below verbatim, filling only the bracketed insertions.

Stage 0 — Ticket materialization (you, the orchestrator — no subagents)

The fleet has no Jira access; it only ever sees a file. Materialize the ticket yourself before dispatching anything.

Fetch ticket <X> from Jira (Atlassian MCP: getJiraIssue with comments; also fetch its subtasks and linked issues one level deep). Write <Y>-ticket.md with these sections, in this order: Summary; Description; Acceptance criteria (if the ticket has a distinct field or section for them); Subtasks — one line each with key, summary, and status; Linked issues — one line each with key, summary, and link type; Comments — chronological, each with author, date, and full body. Reproduce ticket text verbatim; do not summarize, do not editorialize. Scope decisions recorded in comments stay in the Comments section — the mapper is instructed that later decisions supersede earlier text.

If the session has no Jira access, ask the operator to paste the full ticket content into the conversation — description, acceptance criteria, subtasks, linked issues, comments — and write <Y>-ticket.md from it with the same sections. Do not dispatch Stage 1 until <Y>-ticket.md exists.

Stage 1 — Grounding (3 subagents, parallel)

The fleet is cheap; it hallucinates paths and drowns in big scopes. Ground it first. Dispatch all three subagents in a single message.

Mapper brief:

    Read the materialized ticket at <Y>-ticket.md in full. Write to <Y>-plan-map.md a numbered list of work items WI-01, WI-02, … Each work item is one coherent behavior the ticket promises — drawn from the description, the acceptance criteria, the subtasks, and decisions recorded in comments. A later comment that changes scope supersedes earlier ticket text: record the promise as last agreed, and name the comment that changed it. For each work item record: a one-line summary, the exact ticket section or comment it comes from, any file path, module, endpoint, or component the ticket names (tickets rarely name files — leave this empty rather than guessing), and the acceptance criterion or expected behavior if the ticket states one. Do not judge anything. Extract only. No preamble.

Change-inventory brief:

    Establish the change set of the implementation with git: if <Z> is set, the change set is the diff from <Z> to the working tree (committed and uncommitted); if <Z> is empty, it is the uncommitted changes plus the commits on the current branch that are not on the default branch. Write to <Y>-change-inventory.md one line per changed file: the path, whether it was added, modified, or deleted, and a one-line summary of what changed in it. Mark test files, migration files, and configuration files as such. Do not judge anything. Inventory only. No preamble.

Gate-runner brief:

    Discover the project's quality gates from its task runner and docs (justfile, Makefile, CI config, CLAUDE.md). Run the standard set once — linter, type checker, import contracts, and the test suite — scoped to the changed areas if a full run is impractical, and note any scoping you did. Write to <Y>-gate-results.md one line per gate: the exact command, PASS or FAIL, and for failures the first error with file:line. Fix nothing, change nothing. Run and record only. No preamble.

Stage 2 — Review panel (8 subagents, parallel)

Launch all 8 in a single message. Eight independent perspectives, no cross-talk.

- Each subagent receives: (1) the materialized ticket path <Y>-ticket.md, (2) its output path <Y>-implementation-review-NN.md from the table below, (3) the contents of its prompt file with the placeholder lines at the bottom filled in — set the prompt's <X> to <Y>-ticket.md, its <Y> to the output path, its <Z> as given; this fill applies only to the three placeholder lines at the bottom of the prompt file, never to the grounding line below — and (4) this grounding line appended: "The plan this prompt refers to is Jira ticket [insert the Jira ticket key], materialized in full at <Y>-ticket.md — it promises behaviors and acceptance criteria, not file lists, and a later comment recording a scope decision supersedes earlier ticket text. Wherever this prompt says plan, read the materialized ticket: it is a ticket, not a plan document. Grounding files: <Y>-plan-map.md, <Y>-change-inventory.md, and <Y>-gate-results.md — use them to locate things quickly and to avoid re-running full gates, but verify anything you rely on yourself." Nothing else.
- Pass each prompt verbatim. Do not paraphrase, condense, or "improve" it — the framing is load-bearing.
- If a prompt does not fit the project's stack, swap it and tell the user which one and why.

| NN | Prompt file | Extra placeholder fill |
|----|-------------|------------------------|
| 01 | /home/cristi/Projects/agent-skills/prompts/code-implementation-review/single-language/implementation-review-python-aggressive.md | — |
| 02 | /home/cristi/Projects/agent-skills/prompts/code-implementation-review/single-language/implementation-review-python.md | — |
| 03 | /home/cristi/Projects/agent-skills/prompts/code-implementation-review/lenses/implementation-review-security.md | — |
| 04 | /home/cristi/Projects/agent-skills/prompts/code-implementation-review/lenses/implementation-review-tests-and-migrations.md | — |
| 05 | /home/cristi/Projects/agent-skills/prompts/code-implementation-review/lenses/implementation-review-operational-readiness.md | — |
| 06 | /home/cristi/Projects/agent-skills/prompts/code-implementation-review/generic/implementation-review-loss-framing.md | — |
| 07 | /home/cristi/Projects/agent-skills/prompts/code-implementation-review/lenses/implementation-review-divergence.md | — |
| 08 | /home/cristi/Projects/agent-skills/prompts/code-implementation-review/lenses/implementation-review-bug-hunt.md | — |

Wait for all 8 to finish before Stage 3.

Stage 3 — Work-item sweep (up to 6 subagents, parallel)

The panel reviews by concern; this stage reviews by slice, so nothing hides between concerns — and nothing hides outside the ticket.

Read <Y>-plan-map.md and <Y>-change-inventory.md. Assign every changed file to the work item whose behavior it implements or supports — tickets rarely name files, so assign by behavior, not by whether the ticket names the path. Changed files that serve no work item form one extra UNPLANNED slice. If the UNPLANNED slice is empty — every changed file assigned to a work item — skip the UNPLANNED sweeper; do not dispatch it. If the work items plus the UNPLANNED slice exceed 6, merge the smallest related work items so you dispatch at most 6 sweepers. A non-empty UNPLANNED slice is never dropped and never merged into a work item. Launch all sweepers in a single message. When filling each work-item sweeper brief, replace NN in its output path with the slice's work item number (WI-01 → wi-01; a merged slice uses its lowest number).

Work-item sweeper brief:

    You review exactly one slice of the implementation of Jira ticket <X>, materialized at <Y>-ticket.md: [paste the work item entry (or merged entries) from <Y>-plan-map.md and the changed files assigned to it from <Y>-change-inventory.md]. Read that part of the ticket and every assigned file in full. First judge delivery: state IMPLEMENTED, PARTIAL, MISSING, or DIVERGED, with the code citation that proves it. Then report everything wrong inside the slice: broken behavior, mixed responsibilities, missing error handling, unproven behaviors, missing or weakened tests, dead code. Each finding states: severity (Blocking/Important/Nit), the issue in one sentence, the file:line citation, the ticket location (or "unplanned"), the concrete fix. You may run tests read-only scoped to the slice; never modify a file. Write to <Y>-implementation-review-wi-NN.md. No hedging, no preamble.

UNPLANNED sweeper brief:

    You review the unplanned slice of the implementation of Jira ticket <X>, materialized at <Y>-ticket.md: the changed files that map to no work item in the ticket: [paste the list from <Y>-change-inventory.md]. Read each in full and determine what it does. Classify each change: necessary support work for the ticket, or scope creep. A ticket promises behaviors, not file lists — support work is anything the ticket's behaviors plausibly require. Scope creep is Nit by default; scope creep touching shared code, dependencies, configuration, or migrations is Important until the operator clears it. Also report anything broken inside these changes — brokenness keeps its natural severity; only the scope-creep classification is softened. Each finding states: severity, the issue in one sentence, the file:line citation, "unplanned", the concrete fix. Write to <Y>-implementation-review-wi-UN.md. No hedging, no preamble.

Stage 4 — Citation check (3 subagents, parallel)

Cheap reviewers invent evidence; check all of it.

Split the review files from Stages 2 and 3 into 3 roughly equal batches. Launch 3 checkers in a single message, each with this brief:

    Read these review files: [list the batch]. For every finding in them verify only the evidence: (a) does the quoted ticket text actually appear in <Y>-ticket.md? (b) does the cited file exist, and does the cited location say what the finding claims? (c) if the finding claims a gate or test result, does <Y>-gate-results.md or a scoped read-only re-run corroborate it? Verdict per finding: VALID, BROKEN (name the citation and why), or UNCHECKABLE. Do not judge whether the finding itself is right — only whether its evidence is real. Write to <Y>-citation-check-N.md one line per finding: source review file, finding summary, verdict, reason. No preamble.

Stage 5 — Clustering (1 subagent)

Dispatch one subagent with this brief:

    Read every review file <Y>-implementation-review-*.md (including the wi- files) and every citation report <Y>-citation-check-*.md. Write <Y>-clusters.md. Merge findings that describe the same underlying issue into clusters CL-01, CL-02, … For each cluster record: the highest severity claimed, the issue in one sentence, the strongest citation, found-by k/M (list the review files; M is the total number of review files), citation health from the reports (VALID / BROKEN / UNCHECKABLE), and the affected work items (WI-NN or UNPLANNED). Do not add findings. Do not drop findings: anything that matches no cluster becomes its own cluster. Order by severity, then corroboration. Append a work-item status table: each work item's IMPLEMENTED / PARTIAL / MISSING / DIVERGED status as stated by its sweep file, plus one line summarizing the UNPLANNED slice. Append a coverage matrix: work item × concern (ticket-conformance, architecture, security, tests-migrations, operations) marking where at least one finding or an explicit all-clear exists, and where neither does. No preamble.

Stage 6 — Skeptic court (up to 8 subagents, parallel)

Read <Y>-clusters.md. Select up to 8 clusters: every Blocking first, then Important by corroboration — but for queue ordering, treat a cluster that is pure scope creep (UNPLANNED, nothing broken) at its ticket severity, Important, even when a strict panel prompt claimed Blocking, so elevated creep findings never crowd real Blocking bugs out of court. Skip clusters whose citation health is BROKEN — tag them EVIDENCE-BROKEN for the arbiter instead of sending them to court. Launch one skeptic per selected cluster, all in a single message, each with this brief:

    You are a skeptic. Here is a claimed problem with the implementation of Jira ticket <X>, materialized at <Y>-ticket.md: [paste the full cluster entry from <Y>-clusters.md]. Try to REFUTE it against the actual code and the actual ticket text. Check the citation: does the cited code say what the cluster claims? Check the reasoning: does the problem actually follow? You may run the cited test or a scoped read-only command to settle the claim — never modify a file. If the cluster survives your best attempt to kill it, your verdict is CONFIRMED, with the evidence that survived. If it does not, or you cannot verify it, your verdict is REFUTED, with the evidence or missing verification that killed it. Write to <Y>-court-CL-NN.md exactly: the verdict, then at most three sentences of evidence with file:line citations. No preamble.

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

    You are the arbiter. Read <Y>-implementation-review-synthesized.md, then the materialized ticket <Y>-ticket.md itself. The synthesized review was produced by a fleet of cheap models: trust CONFIRMED entries unless something looks off, re-examine DISPUTED and EVIDENCE-BROKEN entries against the actual code yourself, re-examine every Blocking or Important cluster in UNTRIED — the court cap may have skipped it, not cleared it — and check the coverage gaps and the work-item status table for anything the fleet missed that you can settle quickly. You may run gates and tests read-only to settle a dispute; never modify a file. The panel prompts use strict plan-review severities, but this review is against a ticket, which promises behaviors rather than file lists — normalize scope-creep findings: pure scope creep is Nit; scope creep touching shared code, dependencies, configuration, or migrations is Important until the operator clears it; brokenness keeps its natural severity. Write <Y>-implementation-review-final.md — the definitive review: findings grouped Blocking / Important / Nit, each stating the issue in one sentence, the file:line citation, the ticket location (or "unplanned"), and the concrete fix; a work-item status roll-up stating plainly whether the ticket is fully implemented; a short section on what was checked and found sound; and a one-line verdict: merge as-is, merge after Blocking fixed, or return to implementation. Resolve every DISPUTED cluster explicitly — say which side was right and why. No preamble.

<X> = 
<Y> = 
<Z> = 
