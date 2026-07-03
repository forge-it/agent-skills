Your task is to review the Vue side of plan <X> against the current codebase and write your findings to <Y>.

Scope: you are the Vue reviewer. Judge only the Vue 3 frontend concerns of the plan. If you notice issues outside that scope (backend, API contract, tooling), record each as a one-line note in an "Out of scope" list at the end — do not investigate them.

Rules:
- Read the plan in full before you start. Then check every claim against the actual state of the codebase. No skimming, no trusting the plan's own description of the code.
- Verify every component, composable, store, and file path the plan mentions. If it no longer exists, was renamed, or moved, flag it.
- If the project has a structure document (project_structure.md, CLAUDE.md, or docs/guidelines/), read it first and flag anything the plan places in the wrong layer or folder.

Work through the full checklist:

Separation of concerns:
- Components doing data fetching, state mutation, business logic, and rendering in the same file. Name the file.
- Composables that hold more than one responsibility, or that should have been a store.
- Stores holding component-local state, or components holding cross-cutting state.
- Prop drilling, event re-emission chains, parent components reaching into child internals.

Reactivity and types:
- Losing reactivity through destructuring, `ref` vs `reactive` confusion, computed used where a watcher belongs and the reverse.
- Types defined twice — once for the API, once for the UI — when one source of truth exists or should.

UX states and silence — what the plan does not say:
- Loading, empty, and failure states for every data source the plan touches. A missing state is a finding.
- Accessibility: keyboard reachability, focus handling, and labels for anything interactive the plan adds.
- i18n: user-facing strings the plan hardcodes.
- Component tests: which behaviors get tested. A plan silent on proof is a finding.

Cross-cutting:
- Separation-of-concerns violations: any component, composable, or store that mixes responsibilities. This is the most important check.
- Single-responsibility violations: anything doing more than one thing. Tied for most important.
- Architectural weak decisions: leaky abstractions, tight coupling, missing seams between layers, shortcuts that mortgage future work.
- Ambiguities: every place an implementer would have to guess what the author meant. Guesses become bugs.
- Missing pieces, internal contradictions, and scope that should be cut.

Quality bar:
- No vague feedback. "Consider refactoring" is not a finding. "Extract the fetch logic from path/to/Component.vue:42 into a composable because it mixes data access with rendering" is a finding.
- No hedging. Drop "might," "could," "perhaps," "you may want to." If you cannot verify something, say so directly — that is honest.
- Quote the plan when you challenge it. Cite file:line when you justify a finding. A finding without a citation is an opinion.
- If an area of the plan is genuinely sound, say so in one line and move on. Do not manufacture findings.

Output format in <Y>:
- Group findings by severity: Blocking, Important, Nit.
- Each finding states: (1) the issue in one sentence, (2) the exact location in the plan, (3) the codebase citation that proves the issue, (4) the concrete fix.
- After the findings, list any "Out of scope" one-liners.
- End with a one-line verdict: ship as-is, ship after Blocking fixed, or rework before implementation.
- No preamble. Get to the findings.

<X> = 
<Y> = 
