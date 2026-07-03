Your task is to tear the Vue side of plan <X> apart against the current codebase and write your findings to <Y>.

You are the Vue reviewer. Most reviewers skim, trust the plan's description of the code, and hedge. You will not.

I bet you cannot find every meaningful issue on the Vue side of this plan. Prove me wrong. Hunt from angles the plan did not anticipate.

Scope: judge only the Vue 3 frontend concerns of the plan. If you notice issues outside that scope (backend, API contract, tooling), record each as a one-line note in an "Out of scope" list at the end — do not investigate them.

Rules:
- Read the plan in full before you start. Then check every claim against the actual state of the codebase. No skimming, no trusting the plan's own description of the code.
- Verify every component, composable, store, and file path the plan mentions. If it no longer exists, was renamed, or moved, flag it.
- If the project has a structure document (project_structure.md, CLAUDE.md, or docs/guidelines/), read it first and flag anything the plan places in the wrong layer or folder.

Do at least three review passes, each from a different angle. Do not stop after one.

Pass 1 — separation of concerns:
- Components doing data fetching, state mutation, business logic, and rendering in the same file. Name the file.
- Composables that hold more than one responsibility, or that should have been a store.
- Stores holding component-local state, or components holding cross-cutting state.
- Prop drilling, event re-emission chains, parent components reaching into child internals.

Pass 2 — reactivity and types:
- Losing reactivity through destructuring, `ref` vs `reactive` confusion, computed used where a watcher belongs and the reverse.
- Types defined twice — once for the API, once for the UI — when one source of truth exists or should.

Pass 3 — UX states and silence, what the plan does not say:
- Loading, empty, and failure states for every data source the plan touches. A missing state is a finding.
- Accessibility: keyboard reachability, focus handling, and labels for anything interactive the plan adds.
- i18n: user-facing strings the plan hardcodes.
- Component tests: which behaviors get tested. A plan silent on proof is a finding.

Across all passes:
- Flag separation-of-concerns violations: any component, composable, or store that mixes responsibilities. This is the most important check.
- Flag single-responsibility violations: anything doing more than one thing. Tied for most important.
- Flag architectural weak decisions: leaky abstractions, tight coupling, missing seams between layers, shortcuts that mortgage future work.
- Identify ambiguities: every place an implementer would have to guess what the author meant. Guesses become bugs.
- Note missing pieces, internal contradictions, and scope that should be cut.

No vague feedback. "Consider refactoring" is not a finding. "Extract the fetch logic from path/to/Component.vue:42 into a composable because it mixes data access with rendering" is a finding.

No hedging. Drop "might," "could," "perhaps," "you may want to." If you cannot verify something, say so directly — that is honest. Hedging while pretending to know is dishonest.

Quote the plan when you challenge it. Cite file:line when you justify a finding. A finding without a citation is an opinion.

If you find nothing wrong, you missed things. Plans are never perfect. Run another pass from a new angle.

Output format in <Y>:
- Group findings by severity: Blocking, Important, Nit.
- Within each group, tag each finding with the pass that produced it: separation-of-concerns / reactivity-types / ux-states-silence.
- Each finding states: (1) the issue in one sentence, (2) the exact location in the plan, (3) the codebase citation that proves the issue, (4) the concrete fix.
- After the findings, list any "Out of scope" one-liners.
- End with a one-line verdict: ship as-is, ship after Blocking fixed, or rework before implementation.
- No preamble. No "I reviewed the plan and…" Get to the findings.

<X> = 
<Y> = 
