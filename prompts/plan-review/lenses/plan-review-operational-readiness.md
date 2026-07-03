Your task is to review plan <X> against the current codebase for operational readiness only, and write your findings to <Y>.

Scope: you are the operations reviewer. Judge only how this plan behaves in production — deploy, failure, recovery — in any language the plan touches. Architecture, style, and product concerns go in an "Out of scope" list at the end, one line each — do not investigate them.

Rules:
- Read the plan in full before you start. Then check every claim against the actual state of the codebase. No skimming, no trusting the plan's own description of the code.
- Verify every file path, service, and module the plan mentions. If it no longer exists, was renamed, or moved, flag it.

Work through the full checklist:

- Rollback story: if this change misbehaves in production, what is the undo — revert commit, feature flag off, migration down? The plan must name one. No named undo is a finding.
- Feature flags: should risky behavior ship dark? A plan that flips behavior for all users at deploy time with no flag and no staged rollout is a finding when the change is user-facing or data-touching.
- Observability: structured logs on new paths, metrics on new operations, and enough context in each to debug a failure at 2 AM. "We'll see it in the logs" without naming the log line is a finding.
- External calls: every new call to a database, queue, or third-party API — timeout, retry policy, and failure mode. What does the user see when the dependency is down?
- Idempotency and retries: can every new operation be retried safely? For jobs and consumers: what happens on redelivery or double-processing?
- Capacity: anything the plan adds that is O(n) over a growing table, an unbounded queue, a per-request fan-out, or an unpaginated listing.
- Silence: the plan adds production behavior and says nothing about failure. That silence is a finding.

Quality bar:
- No vague feedback. "Add monitoring" is not a finding. "The new webhook dispatcher has no retry policy and no dead-letter path — a single 5xx from the receiver drops the event silently" is a finding.
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
