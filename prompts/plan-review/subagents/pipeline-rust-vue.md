Your task is to run a staged review pipeline on plan <X> against the current codebase.

The pipeline has three stages: Stage 1 dispatches a parallel review panel, Stage 2 synthesizes the panel's findings into one report, Stage 3 adversarially verifies the serious findings. Run the stages in order, completing each before starting the next.

(Note for the human dispatching this prompt — delete stages from the bottom for a cheaper run: Stage 1 only = raw parallel reviews; Stages 1–2 = consolidated report; all three = verified report.)

Stage 1 — Panel

Launch 8 subagents in parallel to review plan <X>. Eight independent perspectives, no cross-talk, no shared context beyond the plan itself.

Rules:
- Dispatch all 8 subagents in a single message. Parallel, not sequential.
- Each subagent receives: (1) the plan path <X>, (2) its output path <Y>-plan-review-NN.md where NN comes from the table below, (3) the contents of its prompt file with the placeholder lines at the bottom filled in — nothing else. No summary of prior conversation, no hints, no framing.
- Pass each prompt verbatim. Do not paraphrase, condense, or "improve" it — the framing in each prompt is load-bearing.
- Do not read, merge, or edit the review files. The panel's raw output belongs to the user.
- If a prompt below does not fit the project's stack, swap it before dispatching and tell the user which one you swapped and why.

| NN | Prompt file | Extra placeholder fill |
|----|-------------|------------------------|
| 01 | <agent-skills>/prompts/plan-review/single-language/plan-review-rust-aggressive.md | — |
| 02 | <agent-skills>/prompts/plan-review/single-language/plan-review-vue-aggressive.md | — |
| 03 | <agent-skills>/prompts/plan-review/single-language/plan-review-api-seam.md | <BACKEND> = Rust |
| 04 | <agent-skills>/prompts/plan-review/generic/plan-review-day-off-bet.md | — |
| 05 | <agent-skills>/prompts/plan-review/generic/plan-review-loss-framing.md | — |
| 06 | <agent-skills>/prompts/plan-review/lenses/plan-review-security.md | — |
| 07 | <agent-skills>/prompts/plan-review/lenses/plan-review-tests-and-migrations.md | — |
| 08 | <agent-skills>/prompts/plan-review/lenses/plan-review-operational-readiness.md | — |

Wait for all 8 to finish before starting Stage 2.

Stage 2 — Synthesis

Dispatch ONE fresh subagent — do not do this work yourself — with exactly this brief:

    Read the review files <Y>-plan-review-01.md through <Y>-plan-review-08.md. They are 8 independent reviews of plan <X>. Write a synthesis to <Y>-plan-review-synthesis.md:
    - Merge findings that describe the same underlying issue into one entry that names every review that found it (by file number) and keeps the strongest citation.
    - Tag every entry with its corroboration: found-by k/8.
    - Where reviews disagree — one calls something sound, another calls it a flaw — record the disagreement as a disagreement. Never silently resolve it.
    - Order entries by severity (Blocking, Important, Nit), then by corroboration within each severity.
    - Do not add findings of your own. Do not drop any panel finding: every finding from every review appears, either merged into an entry or as its own entry.
    - End with a verdict tally: each review's one-line verdict and the count per verdict.

Do not edit the synthesis when it returns. Wait for it to finish before starting Stage 3.

Stage 3 — Adversarial verification

Read <Y>-plan-review-synthesis.md — only this file, and only to enumerate its Blocking and Important findings. Nits skip verification.

For each Blocking or Important finding, dispatch one skeptic subagent — all skeptics in a single message, in parallel — each with exactly this brief, with the finding pasted in:

    You are a skeptic. Here is a claimed problem with plan <X>: [paste the full finding, including its plan location and codebase citation]. Try to REFUTE it against the actual plan text and the actual codebase. Check the citation: does the cited code say what the finding claims? Check the reasoning: does the problem actually follow? If the finding survives your best attempt to kill it, your verdict is CONFIRMED, with the evidence that survived. If it does not, or you cannot verify it, your verdict is REFUTED, with the evidence or the missing verification that killed it. Report exactly: the verdict, then at most three sentences of evidence with file:line citations. Nothing else.

Assemble the skeptic verdicts verbatim into <Y>-plan-review-verified.md: each finding followed by its verdict and evidence, ordered Blocking then Important, corroboration tags preserved. Close the file with one line stating the CONFIRMED and REFUTED counts and a final recommendation: ship as-is, ship after CONFIRMED Blocking fixed, or rework before implementation.

<X> = 
<Y> = 
<agent-skills> = 
