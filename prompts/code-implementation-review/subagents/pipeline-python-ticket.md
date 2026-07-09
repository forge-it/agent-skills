Your task is to run a staged review pipeline on the implementation of Jira ticket <X> against the current codebase. The ticket plays the role a plan plays in the sibling pipeline: the spec of promised behaviors the implementation is judged against.

The pipeline has a preparation step and three stages: Stage 0 materializes the ticket (you do it yourself), Stage 1 dispatches a parallel review panel, Stage 2 synthesizes the panel's findings into one report, Stage 3 adversarially verifies the serious findings. Run the stages in order, completing each before starting the next.

Placeholders: <X> is the Jira ticket key (for example PROJ-123), <Y> is the output prefix, <Z> is the git base of the implementation — the ref the change set is diffed against. If <Z> is empty, the change set is the uncommitted changes plus the commits on the current branch that are not on the default branch.

(Note for the human dispatching this prompt — Stage 0 always runs; delete stages from the bottom for a cheaper run: Stages 0–1 only = raw parallel reviews; Stages 0–2 = consolidated report; all four = verified report.)

Stage 0 — Ticket materialization (you, the orchestrator — no subagents)

The panel has no Jira access; it only ever sees a file. Materialize the ticket yourself before dispatching anything.

Fetch ticket <X> from Jira (Atlassian MCP: getJiraIssue with comments; also fetch its subtasks and linked issues one level deep). Write <Y>-ticket.md with these sections, in this order: Summary; Description; Acceptance criteria (if the ticket has a distinct field or section for them); Subtasks — one line each with key, summary, and status; Linked issues — one line each with key, summary, and link type; Comments — chronological, each with author, date, and full body. Reproduce ticket text verbatim; do not summarize, do not editorialize.

If the session has no Jira access, ask the operator to paste the full ticket content into the conversation — description, acceptance criteria, subtasks, linked issues, comments — and write <Y>-ticket.md from it with the same sections. Do not dispatch Stage 1 until <Y>-ticket.md exists.

Stage 1 — Panel

Launch 6 subagents in parallel to review the implementation of ticket <X>. Six independent perspectives, no cross-talk, no shared context beyond the materialized ticket and the change scope.

Rules:
- Dispatch all 6 subagents in a single message. Parallel, not sequential.
- Each subagent receives: (1) the materialized ticket path <Y>-ticket.md, (2) its output path <Y>-implementation-review-NN.md where NN comes from the table below, (3) the contents of its prompt file with the placeholder lines at the bottom filled in — set the prompt's <X> to <Y>-ticket.md, its <Y> to the output path, its <Z> as given; this fill applies only to the three placeholder lines at the bottom of the prompt file, never to the grounding line below — and (4) this grounding line appended: "The plan this prompt refers to is Jira ticket [insert the Jira ticket key], materialized in full at <Y>-ticket.md — it promises behaviors and acceptance criteria, not file lists, and a later comment recording a scope decision supersedes earlier ticket text. Wherever this prompt says plan, read the materialized ticket: it is a ticket, not a plan document." Nothing else beyond these four items. No summary of prior conversation, no hints, no framing.
- Pass each prompt verbatim. Do not paraphrase, condense, or "improve" it — the framing in each prompt is load-bearing.
- The reviewers may run gates and tests read-only — their prompts say so. Do not grant them write access to the codebase.
- Do not read, merge, or edit the review files. The panel's raw output belongs to the user.
- If a prompt below does not fit the project's stack, swap it before dispatching and tell the user which one you swapped and why.

| NN | Prompt file | Extra placeholder fill |
|----|-------------|------------------------|
| 01 | /home/cristi/Projects/agent-skills/prompts/code-implementation-review/single-language/implementation-review-python-aggressive.md | — |
| 02 | /home/cristi/Projects/agent-skills/prompts/code-implementation-review/single-language/implementation-review-python.md | — |
| 03 | /home/cristi/Projects/agent-skills/prompts/code-implementation-review/generic/implementation-review-loss-framing.md | — |
| 04 | /home/cristi/Projects/agent-skills/prompts/code-implementation-review/lenses/implementation-review-security.md | — |
| 05 | /home/cristi/Projects/agent-skills/prompts/code-implementation-review/lenses/implementation-review-tests-and-migrations.md | — |
| 06 | /home/cristi/Projects/agent-skills/prompts/code-implementation-review/lenses/implementation-review-operational-readiness.md | — |

Wait for all 6 to finish before starting Stage 2.

Stage 2 — Synthesis

Dispatch ONE fresh subagent — do not do this work yourself — with exactly this brief:

    Read the review files <Y>-implementation-review-01.md through <Y>-implementation-review-06.md. They are 6 independent reviews of the implementation of Jira ticket <X>, materialized at <Y>-ticket.md. Write a synthesis to <Y>-implementation-review-synthesis.md:
    - Merge findings that describe the same underlying issue into one entry that names every review that found it (by file number) and keeps the strongest citation.
    - Tag every entry with its corroboration: found-by k/6.
    - Where reviews disagree — one calls something sound, another calls it a flaw — record the disagreement as a disagreement. Never silently resolve it.
    - Order entries by severity (Blocking, Important, Nit), then by corroboration within each severity.
    - Do not add findings of your own. Do not drop any panel finding: every finding from every review appears, either merged into an entry or as its own entry.
    - End with a verdict tally: each review's one-line verdict and the count per verdict.

Do not edit the synthesis when it returns. Wait for it to finish before starting Stage 3.

Stage 3 — Adversarial verification

Read <Y>-implementation-review-synthesis.md — only this file, and only to enumerate its Blocking and Important findings. Nits skip verification.

The panel prompts use strict plan-review severities, but this review is against a ticket, which promises behaviors rather than file lists. Normalize scope-creep findings as you enumerate: a finding whose only issue is pure scope creep (unplanned work, nothing broken) counts as Nit and skips verification; scope creep touching shared code, dependencies, configuration, or migrations counts as Important. Brokenness keeps its natural severity. Record every downgrade you make — it appears in the verified report.

For each Blocking or Important finding, dispatch one skeptic subagent — all skeptics in a single message, in parallel — each with exactly this brief, with the finding pasted in:

    You are a skeptic. Here is a claimed problem with the implementation of Jira ticket <X>, materialized at <Y>-ticket.md: [paste the full finding, including its code citation and ticket location]. Try to REFUTE it against the actual code and the actual ticket text. Check the citation: does the cited code say what the finding claims? Check the reasoning: does the problem actually follow? You may run the cited test or a scoped read-only command to settle the claim — never modify a file. If the finding survives your best attempt to kill it, your verdict is CONFIRMED, with the evidence that survived. If it does not, or you cannot verify it, your verdict is REFUTED, with the evidence or the missing verification that killed it. Report exactly: the verdict, then at most three sentences of evidence with file:line citations. Nothing else.

Assemble the skeptic verdicts verbatim into <Y>-implementation-review-verified.md: each finding followed by its verdict and evidence, ordered Blocking then Important, corroboration tags preserved. After the verified findings, list every severity downgrade from the scope-creep normalization: the finding in one line, its panel severity, its ticket severity. Close the file with one line stating the CONFIRMED and REFUTED counts and a final recommendation: merge as-is, merge after CONFIRMED Blocking fixed, or return to implementation.

<X> = 
<Y> = 
<Z> = 
