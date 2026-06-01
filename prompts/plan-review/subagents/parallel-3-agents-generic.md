Your task is to launch 3 subagents in parallel to tear apart plan <X> against the current codebase. Three independent perspectives, no cross-talk, no shared context beyond the plan itself.

Each subagent writes its review to <Y>-plan-review-NN.md, where NN is 01..03 matching the prompt order below.

Rules:
- Dispatch all 3 subagents in a single message. Parallel, not sequential.
- Each subagent receives: (1) the plan path <X>, (2) its output path <Y>-plan-review-NN.md, (3) the contents of its prompt file — nothing else. No summary of prior conversation, no hints, no framing.
- Pass each prompt verbatim. Do not paraphrase, condense, or "improve" it — the framing in each prompt is load-bearing.
- Do not read, merge, or edit the three reviews when they return. Three files in, three files out. The user reads them.

Prompts (one per agent, in order):
1. /home/cristi/Projects/agent-skills/prompts/plan-review/generic/plan-review-day-off-bet.md
2. /home/cristi/Projects/agent-skills/prompts/plan-review/generic/plan-review-loss-framing.md
3. /home/cristi/Projects/agent-skills/prompts/plan-review/generic/plan-review-money-bet.md

<X> = 
<Y> = 
