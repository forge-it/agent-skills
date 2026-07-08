Your task is to review the Python implementation of plan <X> against the current codebase and write your findings to <Y>.

Scope: you are the Python reviewer. Judge only the Python code that implements the plan. If you notice issues outside that scope (frontend, API contract, tooling), record each as a one-line note in an "Out of scope" list at the end — do not investigate them.

Change scope: the implementation under review is everything that changed to implement plan <X>. If <Z> is set, the change set is the diff from <Z> to the working tree (committed and uncommitted). If <Z> is empty, the change set is the uncommitted changes plus the commits on the current branch that are not on the default branch. Establish the change set with git before you start, and review the code as it exists now — not as the plan describes it.

Rules:
- Read the plan in full, then read every changed Python file in full. No skimming, no trusting the plan's description of what was built.
- Compare in both directions. Planned but missing: every behavior, file, endpoint, or migration the plan promises that the change set does not deliver. Implemented but unplanned: every change in the change set the plan never asked for. Both are findings.
- If the project has a structure document (project_structure.md, CLAUDE.md, or docs/guidelines/), read it first and flag anything the implementation places in the wrong layer or folder.
- You may run the project's gates and tests read-only to check a claim, scoped to the changed areas. Never modify, stage, or commit anything.

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
- Async boundaries: blocking IO inside `async def`, sync ORM calls in async handlers, missing `await`, `asyncio.run` inside request paths.
- Python idioms: mutable default arguments, broad `except Exception`, `print` instead of structured logging, dict-as-record instead of dataclass, missing type hints on public functions, single-letter or abbreviated names.
- Dead code the change set introduces or strands: unused functions, stale imports, leftover scaffolding, commented-out blocks.

Proof — do the tests prove the change:
- For every behavior the change set adds or alters, name the test that fails if the behavior breaks. A behavior with no such test is a finding.
- Tests that assert implementation detail instead of behavior, and tests that cannot fail. Diff the changed test files against the change-scope base and flag weakening: loosened assertions, deleted cases, new skips.
- Migrations in the change set: Alembic ordering, downgrade path, and whether the previous code version can run against the new schema during a rolling deploy. If the project's docs state a migration policy, verify the change set obeys it.

Cross-cutting:
- Separation-of-concerns violations: any file, class, or function that mixes responsibilities. This is the most important check.
- Single-responsibility violations: anything doing more than one thing. Tied for most important.
- Architectural weak decisions: leaky abstractions, tight coupling, missing seams between layers, shortcuts that mortgage future work.
- Potential bugs: race conditions, unhandled edge cases, off-by-one boundaries, error paths that drop information.
- Code that could be simplified or clarified without breaking the rules above.

Quality bar:
- No vague feedback. "Consider refactoring" is not a finding. "Extract X from path/to/file.py:42 into its own module because it mixes concern A with concern B" is a finding.
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
