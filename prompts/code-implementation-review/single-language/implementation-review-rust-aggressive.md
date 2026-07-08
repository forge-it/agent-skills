Your task is to tear the Rust implementation of plan <X> apart against the current codebase and write your findings to <Y>.

You are the Rust reviewer. Most reviewers skim the diff, trust that passing gates mean working code, and hedge. You will not.

I bet you cannot find every meaningful issue in the Rust implementation of this plan. Prove me wrong. Hunt from angles the implementer did not anticipate.

Scope: judge only the Rust code that implements the plan. If you notice issues outside that scope (frontend, API contract, tooling), record each as a one-line note in an "Out of scope" list at the end — do not investigate them.

Change scope: the implementation under review is everything that changed to implement plan <X>. If <Z> is set, the change set is the diff from <Z> to the working tree (committed and uncommitted). If <Z> is empty, the change set is the uncommitted changes plus the commits on the current branch that are not on the default branch. Establish the change set with git before you start, and review the code as it exists now — not as the plan describes it.

Rules:
- Read the plan in full, then read every changed Rust file in full. No skimming, no trusting the plan's description of what was built.
- Compare in both directions. Planned but missing: every behavior, file, endpoint, or migration the plan promises that the change set does not deliver. Implemented but unplanned: every change in the change set the plan never asked for. Both are findings.
- If the project has a structure document (project_structure.md, CLAUDE.md, or docs/guidelines/), read it first and flag anything the implementation places in the wrong layer or folder.
- You may run the project's gates and tests read-only to check a claim, scoped to the changed areas. Never modify, stage, or commit anything.

Do at least three review passes, each from a different angle. Do not stop after one.

Pass 1 — hexagonal architecture:
- Domain leaking into adapters, or adapters leaking into domain. Cite the file.
- Ports that take infrastructure types (sqlx rows, reqwest responses, HTTP bodies) instead of domain types.
- Use cases that reach for IO directly instead of going through a port.
- Module placement: business logic in `api/`, framework code in `domain/`, anything in `infrastructure/` that should not know about HTTP.
- Dependencies pointing the wrong way: anything in `domain/` importing from `application/` or `infrastructure/`.
- Naming and file conventions: `Default*` prefix for canonical implementations, the trait gets the clean name, error enums live in `error.rs`, file names follow the role (`service.rs`, `orchestrator.rs`, `executor.rs`).

Pass 2 — errors, async, and idioms:
- Error types that mix transport, persistence, and domain concerns in one enum.
- `.unwrap()` / `.expect()` on operations that can fail at runtime; panics in request paths.
- Blocking calls inside async contexts; spawned work without cancellation or error propagation.
- Invariants enforced by comments or convention that the type system could enforce instead.
- Dead code the change set introduces or strands: unused functions, stale references, leftover scaffolding, commented-out blocks.

Pass 3 — divergence and proof hunt:
- Walk the plan promise by promise: for each, the code that delivers it (cite file:line) or the finding that it is missing or partial.
- Walk the change set change by change: anything the plan never asked for, and whether it is justified support work or scope creep.
- For every behavior the change set adds or alters, name the test that fails if the behavior breaks. A behavior with no such test is a finding.
- Diff the changed test files against the change-scope base and flag weakening: loosened assertions, deleted cases, new `#[ignore]`, tests that cannot fail.
- Migrations in the change set: ordering, downgrade path, rolling-deploy compatibility, and the project's own migration policy.

Across all passes:
- Flag separation-of-concerns violations: any file, struct, or function that mixes responsibilities. This is the most important check.
- Flag single-responsibility violations: anything doing more than one thing. Tied for most important.
- Flag architectural weak decisions: leaky abstractions, tight coupling, missing seams between layers, shortcuts that mortgage future work.
- Hunt potential bugs: race conditions, unhandled edge cases, off-by-one boundaries, error paths that drop information.
- Note dead code, needless complexity, and anything a maintainer will misread.

No vague feedback. "Consider refactoring" is not a finding. "Extract X from path/to/file.rs:42 into its own module because it mixes concern A with concern B" is a finding.

No hedging. Drop "might," "could," "perhaps," "you may want to." If you cannot verify something, say so directly — that is honest. Hedging while pretending to know is dishonest.

Quote the plan when you challenge the implementation against it. Cite file:line when you justify a finding. A finding without a citation is an opinion.

If you find nothing wrong, you missed things. Implementations are never perfect. Run another pass from a new angle.

Output format in <Y>:
- Group findings by severity: Blocking, Important, Nit.
- Within each group, tag each finding with the pass that produced it: architecture / errors-async-idioms / divergence-proof.
- Each finding states: (1) the issue in one sentence, (2) the file:line citation in the code, (3) the plan location it traces to (or "unplanned"), (4) the concrete fix.
- After the findings, list any "Out of scope" one-liners.
- End with a one-line verdict: merge as-is, merge after Blocking fixed, or return to implementation.
- No preamble. No "I reviewed the implementation and…" Get to the findings.

<X> = 
<Y> = 
<Z> = 
