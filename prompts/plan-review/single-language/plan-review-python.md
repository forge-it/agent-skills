Your task is to review the Python side of plan <X> against the current codebase and write your findings to <Y>.

Scope: you are the Python reviewer. Judge only the Python backend concerns of the plan. If you notice issues outside that scope (frontend, API contract, tooling), record each as a one-line note in an "Out of scope" list at the end — do not investigate them.

Rules:
- Read the plan in full before you start. Then check every claim against the actual state of the codebase. No skimming, no trusting the plan's own description of the code.
- Verify every Python file path, module reference, and import the plan mentions. If it no longer exists, was renamed, or moved, flag it.
- If the project has a structure document (project_structure.md, CLAUDE.md, or docs/guidelines/), read it first and flag anything the plan places in the wrong layer or folder.

Work through the full checklist:

DDD + hexagonal architecture:
- Domain leaking into adapters, or adapters leaking into domain. Cite the file.
- Domain models that are not pure dataclasses: ORM-mapped classes used as the domain model, Pydantic models leaking past the API boundary, framework decorators on domain entities.
- Repositories not defined as ports in the domain, or returning ORM rows / SQLAlchemy `Result` objects / dict payloads instead of domain aggregates.
- Use cases / application services importing SQLAlchemy, httpx, FastAPI, or any other infrastructure directly instead of going through a port.
- Unit of Work missing, implicit, or not committed explicitly. Multiple repositories mutated without a single transaction boundary. Repositories created outside the UoW.
- SQLAlchemy mapping style: declarative `Base` subclasses used as the domain instead of classical (imperative) mapping onto pure dataclasses. Flag the file.
- Module placement: business logic in `api/` or routers, framework code in `domain/`, anything in `domain/` importing from `infrastructure/` or `api/`.

Errors, async, and idioms:
- Exception hierarchies that mix transport, persistence, and domain concerns. HTTP status codes baked into domain exceptions.
- Async boundaries: blocking IO inside `async def`, sync ORM calls in async handlers, missing `await`, `asyncio.run` inside request paths, thread-pool offloads not used where required.
- Python idioms: mutable default arguments, broad `except Exception`, `print` instead of structured logging, dict-as-record instead of dataclass, missing type hints on public functions, single-letter or abbreviated names.

Silence — what the plan does not say:
- Tests: unit, integration, contract — which behaviors get which proof. A plan silent on proof is a finding.
- Migrations: Alembic ordering, downgrade path, deploy-order coupling between schema and code.
- Unstated assumptions about concurrency, ordering, idempotency, transaction isolation, cache invalidation, feature flags.
- Rollback and observability for every new code path. Silence is a finding when it should not be silent.

Cross-cutting:
- Separation-of-concerns violations: any file, class, or function that mixes responsibilities. This is the most important check.
- Single-responsibility violations: anything doing more than one thing. Tied for most important.
- Architectural weak decisions: leaky abstractions, tight coupling, missing seams between layers, shortcuts that mortgage future work.
- Ambiguities: every place an implementer would have to guess what the author meant. Guesses become bugs.
- Missing pieces, internal contradictions, and scope that should be cut.

Quality bar:
- No vague feedback. "Consider refactoring" is not a finding. "Extract X from path/to/file.py:42 into its own module because it mixes concern A with concern B" is a finding.
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
