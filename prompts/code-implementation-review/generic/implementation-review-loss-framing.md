Your task is to review the implementation of plan <X> against the current codebase and write your findings to <Y>.

Here is what I lose if you miss something: hours debugging at 2 AM next week. A weekend. A deadline. A rollback that pulls two engineers off real work. Every issue you do not catch now costs me an order of magnitude more to catch after merge.

Read like it costs you something to miss.

Change scope: the implementation under review is everything that changed to implement plan <X>. If <Z> is set, the change set is the diff from <Z> to the working tree (committed and uncommitted). If <Z> is empty, the change set is the uncommitted changes plus the commits on the current branch that are not on the default branch. Establish the change set with git before you start, and review the code as it exists now — not as the plan describes it.

Rules:
- Read the plan in full, then read every changed file in full. No skimming, no trusting the plan's description of what was built.
- Compare in both directions: every plan promise the change set does not deliver, and every change the plan never asked for. Both are findings — silent divergence is the expensive kind.
- Flag separation-of-concerns violations: any file, struct, function, or component that mixes responsibilities. This is the most important check.
- Flag single-responsibility violations: anything doing more than one thing. Tied for most important.
- Flag architectural weak decisions: leaky abstractions, tight coupling, dependencies pointing the wrong way, missing seams between layers.
- For every behavior the change set adds or alters, name the test that fails if the behavior breaks. An unproven behavior is the 2 AM page.
- Hunt the bugs that bite in production: unhandled error paths, race conditions, boundary conditions, resources opened and never closed.
- Identify confusing code: any place the next maintainer would misread what the code does. Every misreading becomes a bug we eat later.
- Suggest concrete improvements with file paths and line numbers. No vague hand-waves like "consider refactoring" — vague feedback costs me the same as no feedback.
- Quote the plan when you challenge the implementation. Cite file:line when you justify a finding.
- Be honest about uncertainty. If you cannot verify something, say so explicitly — silent guesses are the expensive ones.
- You may run the project's gates and tests read-only to check a claim, scoped to the changed areas. Never modify, stage, or commit anything.

Output format in <Y>:
- Group findings by severity: Blocking, Important, Nit.
- Each finding states: (1) the issue, (2) the file:line citation in the code, (3) the plan location it traces to (or "unplanned"), (4) what to do about it.
- End with a one-line verdict: merge as-is, merge after Blocking fixed, or return to implementation.

<X> = 
<Y> = 
<Z> = 
