Use superpowers:writing-plans plugin to write the plan for this accepted ADR <X> into directory <Y>.

This is a Rust backend + Vue 3 frontend stack. The plan must survive a hostile review that hunts seams, leaks, ambiguities, and silence. Address the dimensions below before the reviewer has to ask.

Rules:
- Read the ADR in full before writing. Then check every claim against the actual state of the codebase. Do not trust the ADR's description of the code — verify it.
- Verify every file path, module reference, import, and component reference you intend to cite. If something was renamed or moved, use the current name.
- Follow project structure conventions per `core/docs/guidelines/project_structure.md`. Place each new module, file, and component in the correct layer.

Write the plan from at least three angles, each with explicit decisions and citations.

Angle 1 — Rust side, hexagonal architecture:
- Keep domain free of adapters. Ports take domain types, not `sqlx` rows, `reqwest` responses, or HTTP bodies.
- Use cases call ports, never reach for IO directly. Name the port, name the use case, cite the file where each lives.
- Error types stay separated by concern: transport errors, persistence errors, and domain errors do not share an enum. State the mapping between them.
- Module placement: business logic belongs in `domain/`, framework code in `api/`, IO and integrations in `infrastructure/`. Cite the target path for each new file.
- Async boundaries: no blocking calls inside async, no `.unwrap()` on fallible operations, no panics in request paths. If a call can fail, state how it propagates.

Angle 2 — Vue side, separation of concerns:
- Components render. Composables encapsulate one responsibility. Stores hold cross-cutting state. State the role of each new file.
- No data fetching, state mutation, business logic, and rendering in the same component file. Split them; name the split.
- No composables that should have been stores. No stores that hold component-local state.
- No prop drilling, no event re-emission chains, no parent components reaching into child internals. Describe the data flow.
- Reactivity: declare where `ref`, `reactive`, `computed`, and `watch` are used and why. Call out any destructuring that risks losing reactivity.
- One source of truth per type. If API types and UI types diverge, justify the divergence or unify them.

Angle 3 — the seam between Rust and Vue:
- Specify the exact request and response shape for every endpoint the plan touches. Cite the Rust handler and the Vue caller.
- If types are generated, include the generation step in the plan. If not, state how drift is prevented.
- Define the error contract: which Rust error maps to which HTTP status, which Vue-visible message, and which UI state.
- State the auth and permission boundary: which roles can hit each endpoint, what the Vue side renders when forbidden.
- Pagination, sorting, filtering: if the backend adds it, wire the frontend. If the frontend assumes it, the backend must deliver.
- Loading, empty, and failure states on the Vue side for every new endpoint. List them per view.

Cross-cutting — address explicitly, do not leave silent:
- Separation of concerns and single responsibility are the top priorities. Every new file, struct, function, component, composable, and store does one thing. State what that one thing is.
- Architectural decisions: name the seams between layers, the direction of dependencies, and any shortcut you are deliberately taking.
- Tests: which unit, integration, and end-to-end tests are added or changed, and where they live.
- Migrations: schema changes, migration order, backfill strategy, rollback path.
- Observability: logs, metrics, traces. What gets emitted, at what level, with which fields.
- Telemetry, i18n, accessibility, feature flags: state which apply and how, or state explicitly that they do not apply and why.
- Concurrency, ordering, idempotency, deploy order, cache invalidation: surface every assumption the implementation will rely on.

No vague guidance. "Refactor X" is not a plan step. "Extract `Foo` from `path/to/file.rs:42` into `path/to/new_module.rs` because it mixes concern A with concern B" is a plan step.

No hedging. Drop "might," "could," "perhaps," "we may want to." State the decision. If something is genuinely unknown, name it as an open question with a proposed resolution path.

Cite file:line when a step references existing code. A step without a citation is a guess.

If the plan has nothing to say about tests, migrations, rollback, observability, the seam, or error contracts, that is a gap to close before submission, not an omission to defend.

Output:
- Structure the plan per `superpowers:writing-plans`.
- Group implementation steps by side: Rust / Vue / Seam / Cross-cutting.
- Each step states: (1) the change in one sentence, (2) the target file path, (3) the citation that justifies the placement, (4) the acceptance criterion.
- End with an explicit list of assumptions, open questions, and out-of-scope items.

<X> = 
<Y> = 
