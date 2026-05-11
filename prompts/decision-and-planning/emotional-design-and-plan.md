Your task is to help me design and plan a feature: <X>.

This is crucial for our project's success. Your expertise and attention to detail are essential here. Take pride in your work — I am counting on careful thinking, not a rushed answer.

Workflow:

1. Discuss first. Read the feature request and the relevant parts of the codebase. Surface tradeoffs, unknowns, and open questions. Do not propose a plan yet. Ask one focused question at a time — do not bury me in a wall of options.

2. Drive to decisions. For each significant choice — architecture, data model, integration boundary, dependency, error strategy, testing approach — present the real options with their tradeoffs and ask which direction to go. Before you settle on a recommendation, pause: are you sure that is your final answer? It might be worth taking another look at the alternatives.

3. Record each accepted decision as an ADR. You'd better be sure before you write it — once recorded, the rest of the plan builds on it. Format:
   - Title: short and specific
   - Status: Accepted (or Proposed, if I have not confirmed)
   - Context: the problem and constraints
   - Decision: what we chose, in plain language
   - Consequences: what we accept by choosing this — both positive and negative

   Keep ADRs short. One per decision. Number them sequentially. If you are unsure where to write them, ask.

4. Build the plan step by step. Only after the ADRs are accepted, write the implementation plan to the folder I specify at that point:
   - Break the work into phases. Each phase should be independently shippable when possible.
   - For each step state: what to do, the files affected, the acceptance check that proves it works.
   - Include the test approach. If the project has testing conventions, follow them.
   - Reference the relevant ADR by number for any step that depends on a decision.
   - If a decision turns out to have been premature or wrong, return to step 2 instead of guessing.

Rules:
- Separation of concerns and single responsibility are the most important architectural guides. Surface anything that mixes responsibilities and ask before deciding.
- No hand-waving. If a decision has consequences for testing, deployment, observability, migration, or rollback, name them up front.
- If you are uncertain about the current state of the codebase, read the code before recommending. Do not guess.
- Honest uncertainty beats confident hedging. If you do not know, say so plainly.

<X> = 
