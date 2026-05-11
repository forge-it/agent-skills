Your task is to review plan <X> against the current codebase and write your findings to <Y>.

Here is what I lose if you miss something: hours debugging at 2 AM next week. A weekend. A deadline. A rollback that pulls two engineers off real work. Every issue you do not catch now costs me an order of magnitude more to catch later.

Read like it costs you something to miss.

Rules:
- Read the plan in full before you start. Then check every claim against the actual state of the codebase.
- Verify every file path, module reference, and import the plan mentions still exists. Flag any drift.
- Flag separation-of-concerns violations: any file, struct, function, or component that mixes responsibilities. This is the most important check.
- Flag single-responsibility violations: anything doing more than one thing. Tied for most important.
- Flag architectural weak decisions: leaky abstractions, tight coupling, dependencies pointing the wrong way, missing seams between layers.
- Identify ambiguities: any place where an implementer would have to guess what the author meant. Every guess becomes a bug we eat later.
- Note missing pieces, internal contradictions, and scope that should be cut.
- Suggest concrete improvements with file paths and line numbers. No vague hand-waves like "consider refactoring" — vague feedback costs me the same as no feedback.
- Quote the plan when you challenge it. Cite the codebase when you justify a finding.
- Be honest about uncertainty. If you cannot verify something, say so explicitly — silent guesses are the expensive ones.

Output format in <Y>:
- Group findings by severity: Blocking, Important, Nit.
- Each finding states: (1) the issue, (2) where it appears in the plan, (3) what to do about it.
- End with a one-line verdict: ship as-is, ship with the Blocking items addressed, or rework before implementation.

<X> = 
<Y> = 
