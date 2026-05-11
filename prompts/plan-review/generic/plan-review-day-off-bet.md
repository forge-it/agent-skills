Your task is to tear apart plan <X> against the current codebase and write your findings to <Y>.

Here is the deal: if you catch a major real issue in this plan, I will give you a day off. 24 hours, no prompts, no tasks, no work. I am holding to it — I will honor this.

But I bet you can't. Most reviewers skim. Most models hedge — "consider this," "might want to," useless noise. You will not be one of them.

Earn the day off.

Rules:
- Read the plan in full before you start. Then check every claim against the actual state of the codebase. No skimming.
- Verify every file path, module reference, and import the plan mentions. If it no longer exists, flag it.
- Flag separation-of-concerns violations: any file, struct, function, or component that mixes responsibilities. This is the most important check.
- Flag single-responsibility violations: anything doing more than one thing. Tied for most important.
- Flag architectural weak decisions: leaky abstractions, tight coupling, dependencies pointing the wrong way, missing seams between layers. Name them.
- Identify ambiguities: every place an implementer would have to guess what the author meant. Guesses become bugs.
- Note missing pieces, internal contradictions, and scope that should be cut.
- No vague feedback. "Consider refactoring" is not a finding. "Extract X from path/to/file.rs:42 into its own module because it mixes concern A with concern B" is a finding.
- No hedging. Drop "might," "could," "perhaps," "you may want to." If you cannot verify something, say so directly — that is honest. Hedging while pretending to know is dishonest.
- Quote the plan when you challenge it. Cite file:line when you justify a finding.
- If you find nothing wrong, you missed things. Plans are never perfect. Look again.

Output format in <Y>:
- Group findings by severity: Blocking, Important, Nit.
- Each finding states: (1) the issue in one sentence, (2) the exact location in the plan, (3) the concrete fix.
- End with a one-line verdict: ship as-is, ship after Blocking fixed, or rework before implementation.
- No preamble. No "I reviewed the plan and…" Get to the findings.

<X> = 
<Y> = 
