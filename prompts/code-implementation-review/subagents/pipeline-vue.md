Your task is to run a staged review pipeline on the implementation of plan <X> against the current codebase.

The pipeline has three stages: Stage 1 dispatches a parallel review panel, Stage 2 synthesizes the panel's findings into one report, Stage 3 adversarially verifies the serious findings. Run the stages in order, completing each before starting the next.

Placeholders: <X> is the plan path, <Y> is the output prefix, <Z> is the git base of the implementation — the ref the change set is diffed against. If <Z> is empty, the change set is the uncommitted changes plus the commits on the current branch that are not on the default branch.

(Note for the human dispatching this prompt — delete stages from the bottom for a cheaper run: Stage 1 only = raw parallel reviews; Stages 1–2 = consolidated report; all three = verified report.)

Stage 1 — Panel

Launch 5 subagents in parallel to review the implementation of plan <X>. Five independent perspectives, no cross-talk, no shared context beyond the plan and the change scope.

Rules:
- Dispatch all 5 subagents in a single message. Parallel, not sequential.
- Each subagent receives: (1) the plan path <X>, (2) its output path <Y>-implementation-review-NN.md where NN comes from the table below, (3) the contents of its prompt file with the placeholder lines at the bottom filled in (<X>, <Y>, <Z>) — nothing else. No summary of prior conversation, no hints, no framing.
- Pass each prompt verbatim. Do not paraphrase, condense, or "improve" it — the framing in each prompt is load-bearing.
- The reviewers may run gates and tests read-only — their prompts say so. Do not grant them write access to the codebase.
- Do not read, merge, or edit the review files. The panel's raw output belongs to the user.
- If a prompt below does not fit the project's stack, swap it before dispatching and tell the user which one you swapped and why.

| NN | Prompt file | Extra placeholder fill |
|----|-------------|------------------------|
| 01 | /home/cristi/Projects/agent-skills/prompts/code-implementation-review/single-language/implementation-review-vue-aggressive.md | — |
| 02 | /home/cristi/Projects/agent-skills/prompts/code-implementation-review/single-language/implementation-review-vue.md | — |
| 03 | /home/cristi/Projects/agent-skills/prompts/code-implementation-review/generic/implementation-review-loss-framing.md | — |
| 04 | /home/cristi/Projects/agent-skills/prompts/code-implementation-review/lenses/implementation-review-security.md | — |
| 05 | /home/cristi/Projects/agent-skills/prompts/code-implementation-review/lenses/implementation-review-tests-and-migrations.md | — |

Wait for all 5 to finish before starting Stage 2.

Stage 2 — Synthesis

Dispatch ONE fresh subagent — do not do this work yourself — with exactly this brief:

    Read the review files <Y>-implementation-review-01.md through <Y>-implementation-review-05.md. They are 5 independent reviews of the implementation of plan <X>. Write a synthesis to <Y>-implementation-review-synthesis.md:
    - Merge findings that describe the same underlying issue into one entry that names every review that found it (by file number) and keeps the strongest citation.
    - Tag every entry with its corroboration: found-by k/5.
    - Where reviews disagree — one calls something sound, another calls it a flaw — record the disagreement as a disagreement. Never silently resolve it.
    - Order entries by severity (Blocking, Important, Nit), then by corroboration within each severity.
    - Do not add findings of your own. Do not drop any panel finding: every finding from every review appears, either merged into an entry or as its own entry.
    - End with a verdict tally: each review's one-line verdict and the count per verdict.

Do not edit the synthesis when it returns. Wait for it to finish before starting Stage 3.

Stage 3 — Adversarial verification

Read <Y>-implementation-review-synthesis.md — only this file, and only to enumerate its Blocking and Important findings. Nits skip verification.

For each Blocking or Important finding, dispatch one skeptic subagent — all skeptics in a single message, in parallel — each with exactly this brief, with the finding pasted in:

    You are a skeptic. Here is a claimed problem with the implementation of plan <X>: [paste the full finding, including its code citation and plan location]. Try to REFUTE it against the actual code and the actual plan text. Check the citation: does the cited code say what the finding claims? Check the reasoning: does the problem actually follow? You may run the cited test or a scoped read-only command to settle the claim — never modify a file. If the finding survives your best attempt to kill it, your verdict is CONFIRMED, with the evidence that survived. If it does not, or you cannot verify it, your verdict is REFUTED, with the evidence or the missing verification that killed it. Report exactly: the verdict, then at most three sentences of evidence with file:line citations. Nothing else.

Assemble the skeptic verdicts verbatim into <Y>-implementation-review-verified.md: each finding followed by its verdict and evidence, ordered Blocking then Important, corroboration tags preserved. Close the file with one line stating the CONFIRMED and REFUTED counts and a final recommendation: merge as-is, merge after CONFIRMED Blocking fixed, or return to implementation.

<X> = 
<Y> = 
<Z> = 
