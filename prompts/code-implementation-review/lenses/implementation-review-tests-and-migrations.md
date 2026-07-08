Your task is to review the implementation of plan <X> against the current codebase for proof and migration safety only, and write your findings to <Y>.

Scope: you are the proof-and-migration reviewer. Judge only whether the implementation proves its changes and migrates data safely, in any language it touches. Architecture, style, and product concerns go in an "Out of scope" list at the end, one line each — do not investigate them.

Change scope: the implementation under review is everything that changed to implement plan <X>. If <Z> is set, the change set is the diff from <Z> to the working tree (committed and uncommitted). If <Z> is empty, the change set is the uncommitted changes plus the commits on the current branch that are not on the default branch. Establish the change set with git before you start, and review the code as it exists now — not as the plan describes it.

Rules:
- Read the plan in full, then read every test and migration file in the change set in full. Find where the project's existing tests live and how they are shaped before judging the new ones.
- You may run tests and gates read-only, scoped to the changed areas — running the tests you are judging is encouraged. Never modify, stage, or commit anything.

Work through the full checklist:

- Proof per change: for every behavior the change set adds or alters, name the test that fails if the behavior breaks. A behavior with no such test is a finding. Tests the plan promised that were never written are a finding — cite the plan promise.
- Assertion quality: tests that cannot fail (asserting truisms, asserting the mock they configured), tests that assert implementation detail instead of behavior, tests that mock the thing under test. Each is a finding.
- Test weakening: diff every changed test file against the change-scope base. Assertions loosened, cases deleted, tolerances widened, new skips or ignores added during this implementation — each is a Blocking finding unless the plan explicitly called for it.
- Error-path proof: the change set's failure paths — invalid input, dependency down, denial — which test exercises each? Happy-path-only coverage is a finding.
- Regression surface: which existing tests should have changed because of this implementation? A behavior change that touched no existing test is suspicious — name the test file that should have been touched.
- Test placement and shape: do the new tests live where the project's existing tests live, in the right category (unit, integration, e2e), following the project's isolation and fixture conventions?
- Migration ordering: do the schema migrations in the change set land in an order that works — can the previous version of the code run against the new schema during a rolling deploy?
- Downgrade path: does every new migration have a working down path? Is data loss on downgrade acknowledged?
- Backfill safety: any data backfill in the change set — is it idempotent, batched, and restartable? What happens if it dies halfway through?
- Migration policy: if the project's docs state a migration policy (for example, pre-prod modifications stay in the initial migration), verify the change set obeys it. A new migration that violates the policy is Blocking.

Quality bar:
- No vague feedback. "Improve test coverage" is not a finding. "The new discount rule at path/to/pricing.py:42 has no test proving the rounding behavior — add a unit test beside the existing pricing tests" is a finding.
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
