Your task is to review the implementation of plan <X> against the current codebase for operational readiness only, and write your findings to <Y>.

Scope: you are the operations reviewer. Judge only how this implementation behaves in production — deploy, failure, recovery — in any language it touches. Architecture, style, and product concerns go in an "Out of scope" list at the end, one line each — do not investigate them.

Change scope: the implementation under review is everything that changed to implement plan <X>. If <Z> is set, the change set is the diff from <Z> to the working tree (committed and uncommitted). If <Z> is empty, the change set is the uncommitted changes plus the commits on the current branch that are not on the default branch. Establish the change set with git before you start, and review the code as it exists now — not as the plan describes it.

Rules:
- Read the plan in full, then read every changed file that runs in production. No skimming, no trusting the plan's description of what was built.
- Operational safeguards the plan promised but the code does not contain are Blocking findings. Cite the plan promise and the place in the code where the safeguard should be and is not.
- You may run the project's gates and tests read-only to check a claim, scoped to the changed areas. Never modify, stage, or commit anything.

Work through the full checklist:

- Rollback story: if this change misbehaves in production, what is the undo — revert commit, feature flag off, migration down? If the plan named a flag, find the flag in the code and verify it actually gates the new path. A flag that exists but does not gate the behavior is a finding.
- Feature flags: user-facing or data-touching behavior the change set flips for all users at deploy time with no flag and no staged rollout is a finding.
- Observability: find the structured log lines and metrics on every new code path. Enough context in each to debug a failure at 2 AM — the id, the operation, the outcome. A new failure path that logs nothing, or logs without context, is a finding. Cite the log statement or its absence.
- External calls: every new call to a database, queue, or third-party API in the change set — find the timeout, the retry policy, and the failure handling in the code. A client call with no timeout is a finding. What does the user see when the dependency is down?
- Idempotency and retries: can every new operation be retried safely? For jobs and consumers in the change set: what happens on redelivery or double-processing? Trace the code, do not trust the comments.
- Capacity: anything the change set adds that is O(n) over a growing table, an unbounded queue, a per-request fan-out, or an unpaginated listing. Cite the query or loop.
- Configuration: every new env var or config key the change set reads — is it documented, does it have a sane default, and what happens at startup when it is missing?

Quality bar:
- No vague feedback. "Add monitoring" is not a finding. "The webhook dispatcher at path/to/dispatcher:42 has no retry policy and no dead-letter path — a single 5xx from the receiver drops the event silently" is a finding.
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
