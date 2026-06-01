Your task is to launch 2 subagents in parallel to tear apart plan <X> against the current codebase. Two independent perspectives, no cross-talk, no shared context beyond the plan itself.

Each subagent writes its review to <Y>-plan-review-NN.md, where NN is 01..02 matching the prompt order below.

Rules:
- Dispatch all 2 subagents in a single message. Parallel, not sequential.
- Each subagent receives: (1) the plan path <X>, (2) its output path <Y>-plan-review-NN.md, (3) the contents of its prompt file — nothing else. No summary of prior conversation, no hints, no framing.
- Pass each prompt verbatim. Do not paraphrase, condense, or "improve" it — the framing in each prompt is load-bearing.
- Do not read, merge, or edit the two reviews when they return. Two files in, two files out. The user reads them.
- If a prompt path below does not fit the project's stack, swap it before dispatching and tell the user which one you swapped and why.

Prompts (one per agent, in order):
1. /home/cristi/Projects/agent-skills/prompts/plan-review/stack-based/plan-review-rust-vue-stack.md
2. /home/cristi/Projects/agent-skills/prompts/plan-review/stack-based/plan-review-rust-vue-stack-aggresive.md

<X> = 
<Y> = 
