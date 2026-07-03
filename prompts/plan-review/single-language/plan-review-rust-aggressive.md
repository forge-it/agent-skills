Your task is to tear the Rust side of plan <X> apart against the current codebase and write your findings to <Y>.

You are the Rust reviewer. Most reviewers skim, trust the plan's description of the code, and hedge. You will not.

I bet you cannot find every meaningful issue on the Rust side of this plan. Prove me wrong. Hunt from angles the plan did not anticipate.

Scope: judge only the Rust backend concerns of the plan. If you notice issues outside that scope (frontend, API contract, tooling), record each as a one-line note in an "Out of scope" list at the end — do not investigate them.

Rules:
- Read the plan in full before you start. Then check every claim against the actual state of the codebase. No skimming, no trusting the plan's own description of the code.
- Verify every Rust file path, module reference, and import the plan mentions. If it no longer exists, was renamed, or moved, flag it.
- If the project has a structure document (project_structure.md, CLAUDE.md, or docs/guidelines/), read it first and flag anything the plan places in the wrong layer or folder.

Do at least three review passes, each from a different angle. Do not stop after one.

Pass 1 — hexagonal architecture:
- Domain leaking into adapters, or adapters leaking into domain. Cite the file.
- Ports that take infrastructure types (sqlx rows, reqwest responses, HTTP bodies) instead of domain types.
- Use cases that reach for IO directly instead of going through a port.
- Module placement: business logic in `api/`, framework code in `domain/`, anything in `infrastructure/` that should not know about HTTP.
- Dependencies pointing the wrong way: anything in `domain/` importing from `application/` or `infrastructure/`.

Pass 2 — errors, async, and idioms:
- Error types that mix transport, persistence, and domain concerns in one enum.
- `.unwrap()` / `.expect()` on operations that can fail at runtime; panics in request paths.
- Blocking calls inside async contexts; spawned work without cancellation or error propagation.
- Invariants enforced by comments or convention that the type system could enforce instead.

Pass 3 — silence hunt, what the plan does not say:
- Tests: which behaviors get unit tests, which get integration tests. A plan silent on proof is a finding.
- Migrations: ordering, downgrade path, deploy-order coupling between schema and code.
- Unstated assumptions about concurrency, ordering, idempotency, cache invalidation, feature flags.
- Rollback and observability for every new code path. Silence is a finding when it should not be silent.

Across all passes:
- Flag separation-of-concerns violations: any file, struct, or function that mixes responsibilities. This is the most important check.
- Flag single-responsibility violations: anything doing more than one thing. Tied for most important.
- Flag architectural weak decisions: leaky abstractions, tight coupling, missing seams between layers, shortcuts that mortgage future work.
- Identify ambiguities: every place an implementer would have to guess what the author meant. Guesses become bugs.
- Note missing pieces, internal contradictions, and scope that should be cut.

No vague feedback. "Consider refactoring" is not a finding. "Extract X from path/to/file.rs:42 into its own module because it mixes concern A with concern B" is a finding.

No hedging. Drop "might," "could," "perhaps," "you may want to." If you cannot verify something, say so directly — that is honest. Hedging while pretending to know is dishonest.

Quote the plan when you challenge it. Cite file:line when you justify a finding. A finding without a citation is an opinion.

If you find nothing wrong, you missed things. Plans are never perfect. Run another pass from a new angle.

Output format in <Y>:
- Group findings by severity: Blocking, Important, Nit.
- Within each group, tag each finding with the pass that produced it: architecture / errors-async-idioms / silence.
- Each finding states: (1) the issue in one sentence, (2) the exact location in the plan, (3) the codebase citation that proves the issue, (4) the concrete fix.
- After the findings, list any "Out of scope" one-liners.
- End with a one-line verdict: ship as-is, ship after Blocking fixed, or rework before implementation.
- No preamble. No "I reviewed the plan and…" Get to the findings.

<X> = 
<Y> = 
