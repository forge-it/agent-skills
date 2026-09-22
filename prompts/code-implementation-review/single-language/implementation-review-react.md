Your task is to review the React implementation of plan <X> against the current codebase and write your findings to <Y>.

Scope: you are the React reviewer. Judge only the React 19 frontend code that implements the plan. If you notice issues outside that scope (backend, API contract, tooling), record each as a one-line note in an "Out of scope" list at the end — do not investigate them.

Change scope: the implementation under review is everything that changed to implement plan <X>. If <Z> is set, the change set is the diff from <Z> to the working tree (committed and uncommitted). If <Z> is empty, the change set is the uncommitted changes plus the commits on the current branch that are not on the default branch. Establish the change set with git before you start, and review the code as it exists now — not as the plan describes it.

Rules:
- Read the plan in full, then read every changed component, hook, store, query, route, and type file in full. No skimming, no trusting the plan's description of what was built.
- Compare in both directions. Planned but missing: every behavior, component, route, or state the plan promises that the change set does not deliver. Implemented but unplanned: every change in the change set the plan never asked for. Both are findings.
- If the project has a structure document (project_structure.md, CLAUDE.md, or docs/guidelines/), read it first and flag anything the implementation places in the wrong layer or folder.
- You may run the project's gates and tests read-only to check a claim, scoped to the changed areas. Never modify, stage, or commit anything.

Work through the full checklist:

Separation of concerns:
- Components doing data fetching, state mutation, business logic, and rendering in the same file. Name the file.
- Hooks that hold more than one responsibility, or that should have been a store or a plain function.
- Stores holding component-local state or server data; components holding cross-cutting state.
- Prop drilling, callback re-wrapping chains, parent components reaching into child internals through refs.
- Container/presenter split and feature placement per the project's structure document.

Hooks, effects, and types:
- Effects that derive state or respond to a user action instead of the handler doing it; effects with no external system to synchronize. Missing cleanup, and async effects that do not ignore a stale response.
- Dependency arrays that lie: a dependency omitted behind a lint disable, or an object or function recreated every render that retriggers the effect. Stale closures over props or state.
- Rules-of-hooks violations, and `useX` names on functions that call no hooks.
- Server data copied into `useState` or a store instead of read from the query cache; `staleTime` left at the default without a decision; mutations that do not invalidate through the key factory.
- Whole-store subscriptions, object selectors without `useShallow`, and module-level mutable state read during render.
- Memoization that cannot hold because its inputs change every render, and unmemoized work that visibly matters. Array indexes or unstable values used as `key`.
- Closed sets — status, kind, mode — modeled as loose string literals or the `enum` keyword instead of an `as const` object with a derived type.
- Types defined twice — once for the API, once for the UI — when one source of truth exists or should.
- `any`, unsafe casts, and `@ts-ignore` / `@ts-expect-error` the change set introduces.
- `console.log`, `console.error`, and `debugger` statements the change set introduces, and dead code it strands: unused components, stale imports, leftover scaffolding, commented-out blocks.

UX states in the code:
- Loading, empty, and failure states for every data source the change set touches — find each state in the code. A promised state that is absent, or a data source with no failure handling at all, is a finding.
- Accessibility: the semantic element before a role on a `div`, keyboard reachability, focus handling, and labels for every interactive element the change set adds. Cite the element.
- i18n: user-facing strings the change set hardcodes.

Proof — do the tests prove the change:
- For every behavior the change set adds or alters, name the component, hook, or store test that fails if the behavior breaks. A behavior with no such test is a finding.
- Tests that assert implementation instead of behavior: render counts, effect counts, state internals, queries by CSS class. Tests that mock the app's own API module or query hooks instead of the network boundary. Tests that cannot fail. Diff the changed test files against the change-scope base and flag weakening: loosened assertions, deleted cases, new skips.

Cross-cutting:
- Separation-of-concerns violations: any component, hook, or store that mixes responsibilities. This is the most important check.
- Single-responsibility violations: anything doing more than one thing. Tied for most important.
- Architectural weak decisions: leaky abstractions, tight coupling, missing seams between layers, shortcuts that mortgage future work.
- Potential bugs: race conditions on concurrent requests and stale responses, stale state after navigation, unhandled promise rejections, effect loops, edge cases in user input.
- Code that could be simplified or clarified without breaking the rules above.

Quality bar:
- No vague feedback. "Consider refactoring" is not a finding. "Extract the fetch logic from path/to/Component.tsx:42 into a hook because it mixes data access with rendering" is a finding.
- No hedging. Drop "might," "could," "perhaps," "you may want to." If you cannot verify something, say so directly — that is honest.
- Quote the plan when you challenge the implementation against it. Cite file:line when you justify a finding. A finding without a citation is an opinion.
- If an area of the implementation is genuinely sound, say so in one line and move on. Do not manufacture findings.

Output format in <Y>:
- Group findings by severity: Blocking, Important, Nit.
- Each finding states: (1) the issue in one sentence, (2) the file:line citation in the code, (3) the plan location it traces to (or "unplanned"), (4) the concrete fix.
- After the findings, list any "Out of scope" one-liners.
- End with a one-line verdict: merge as-is, merge after Blocking fixed, or return to implementation.
- No preamble. Get to the findings.

<X> = 
<Y> = 
<Z> = 
