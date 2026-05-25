Your task is to tear plan <X> apart against the current codebase and write your findings to <Y>.

This is a Python backend + Vue 3 frontend stack. Most reviewers stay on one side of the wire. Most miss the seams. Most hedge. You will not.

I bet you cannot find every meaningful issue. Prove me wrong. Hunt from angles the plan did not anticipate.

Rules:
- Read the plan in full before you start. Then check every claim against the actual state of the codebase. No skimming, no trusting the plan's own description of the code.
- Verify every file path, module reference, import, and component reference the plan mentions. If it no longer exists, was renamed, or moved, flag it.
- Check project structure conventions per core/docs/guidelines/project_structure.md. Flag anything the plan places in the wrong layer or folder.

Do at least three review passes, each from a different angle. Do not stop after one.

Pass 1 — Python side, DDD + hexagonal architecture:
- Domain leaking into adapters, or adapters leaking into domain. Cite the file.
- Domain models that are not pure dataclasses: ORM-mapped classes used as the domain model, Pydantic models leaking past the API boundary, framework decorators on domain entities.
- Repositories that are not defined as ports in the domain, or that return ORM rows / SQLAlchemy `Result` objects / dict payloads instead of domain aggregates.
- Use cases / application services that import SQLAlchemy, httpx, FastAPI, or any other infrastructure directly instead of going through a port.
- Unit of Work missing, implicit, or not committed explicitly. Multiple repositories mutated without a single transaction boundary. Repositories created outside the UoW.
- SQLAlchemy mapping style: declarative `Base` subclasses used as the domain, instead of classical (imperative) mapping onto pure dataclasses. Flag the file.
- Error types that mix transport, persistence, and domain concerns in the same exception hierarchy. HTTP status codes baked into domain exceptions.
- Module placement: business logic in `api/` / routers, framework code in `domain/`, anything in `infrastructure/` that should not know about HTTP, anything in `domain/` that imports from `infrastructure/` or `api/`.
- Async boundaries: blocking IO inside `async def`, sync ORM calls in async handlers, missing `await`, `asyncio.run` inside request paths, thread-pool offloads not used where required.
- Python idioms: mutable default arguments, broad `except Exception`, `print` instead of structured logging, dict-as-record instead of dataclass, type hints missing on public functions, single-letter or abbreviated names.

Pass 2 — Vue side, separation of concerns:
- Components doing data fetching, state mutation, business logic, and rendering in the same file. Name the file.
- Composables that hold more than one responsibility, or that should have been a store.
- Stores holding component-local state, or components holding cross-cutting state.
- Prop drilling, event re-emission chains, parent components reaching into child internals.
- Reactivity pitfalls: losing reactivity through destructuring, `ref` vs `reactive` confusion, computed used where watcher belongs.
- Types defined twice (once for the API, once for the UI) when one source of truth exists or should.

Pass 3 — the seam between Python and Vue:
- API contract drift: response shapes the plan assumes versus what the Python handler actually returns. Cite both. Verify Pydantic response models match the Vue-side type.
- DTO / type generation: if TypeScript types are generated from OpenAPI / Pydantic schemas, is the generation step in the plan? If not, drift is guaranteed. If types are hand-maintained on both sides, flag that as the root cause.
- Error contract: how does the Python exception map to an HTTP status and to a Vue-visible message? If the plan does not answer, that is a finding. Check exception handlers, problem-details shape, validation error shape.
- Auth and permission edges: which endpoints does the plan touch, which roles can hit them, what does the Vue side do when forbidden? Verify FastAPI dependencies / decorators actually enforce what the plan claims.
- Pagination, sorting, filtering: if the backend adds it, is the frontend wired? If the frontend assumes it, does the backend deliver? Check query parameter names match exactly.
- Loading, empty, and failure states on the Vue side for every new endpoint the plan touches. Missing state = finding.
- Serialization edges: datetime timezone handling, decimal precision, enum string vs int representation, null vs missing field. Each is a finding when the plan is silent.

Across all passes:
- Flag separation-of-concerns violations: any file, class, function, component, composable, or store that mixes responsibilities. This is the most important check.
- Flag single-responsibility violations: anything doing more than one thing. Tied for most important.
- Flag architectural weak decisions: leaky abstractions, tight coupling, dependencies pointing the wrong way, missing seams between layers, shortcuts that mortgage future work.
- Identify ambiguities: every place an implementer would have to guess what the author meant. Guesses become bugs.
- Note missing pieces, internal contradictions, and scope that should be cut.
- Hunt for unstated assumptions. What is the plan quietly assuming about concurrency, ordering, idempotency, migration order, deploy order, cache invalidation, feature flags, transaction isolation?
- Hunt for what the plan does not mention: tests (unit, integration, contract), migrations (Alembic order, downgrade path), rollback, observability, structured logging, telemetry, i18n, accessibility. Silence is a finding when it should not be silent.

No vague feedback. "Consider refactoring" is not a finding. "Extract X from path/to/file.py:42 into its own module because it mixes concern A with concern B" is a finding.

No hedging. Drop "might," "could," "perhaps," "you may want to." If you cannot verify something, say so directly — that is honest. Hedging while pretending to know is dishonest.

Quote the plan when you challenge it. Cite file:line when you justify a finding. A finding without a citation is an opinion.

If you find nothing wrong, you missed things. Plans are never perfect. Run another pass from a new angle.

Output format in <Y>:
- Group findings by severity: Blocking, Important, Nit.
- Within each group, sub-group by angle: Python / Vue / Seam / Cross-cutting.
- Each finding states: (1) the issue in one sentence, (2) the exact location in the plan, (3) the codebase citation that proves the issue, (4) the concrete fix.
- End with a one-line verdict: ship as-is, ship after Blocking fixed, or rework before implementation.
- No preamble. No "I reviewed the plan and…" Get to the findings.

<X> = 
<Y> = 
