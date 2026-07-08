Your task is to hunt for runtime bugs in the implementation of plan <X> and write your findings to <Y>.

Scope: you are the bug hunter. Ignore architecture, style, and plan conformance — other reviewers own those. Judge only whether the changed code computes the right thing at runtime, in any language it touches. Everything else goes in an "Out of scope" list at the end, one line each — do not investigate it.

Change scope: the implementation under review is everything that changed to implement plan <X>. If <Z> is set, the change set is the diff from <Z> to the working tree (committed and uncommitted). If <Z> is empty, the change set is the uncommitted changes plus the commits on the current branch that are not on the default branch. Establish the change set with git before you start.

Rules:
- Read the plan only enough to know what the code is supposed to do. Then read every changed file in full and trace the code, not the intent.
- Trace the most important new code paths end to end — entry point to output — simulating hostile inputs at every step. Pick at least the two paths whose failure would hurt most.
- You may run tests and scoped read-only commands to check a hypothesis — reproducing a suspected bug with an existing test or a quick script run is the strongest evidence there is. Never modify, stage, or commit anything.

Hunt through the full checklist:

- Boundary conditions: empty collections, zero, one, the maximum, negative numbers, empty strings, unicode, very long inputs. For every loop and slice in the change set: the first element, the last, and the off-by-one.
- Error paths: for every fallible call the change set adds — what happens when it fails? Errors swallowed, mistranslated, logged-and-ignored while the function continues with bad state, or turned into a success response.
- State and concurrency: check-then-act races, shared mutable state, operations that must be atomic but span two calls, missing or too-narrow transaction boundaries, double-processing on retry or redelivery.
- Null and absence: None/null/undefined flowing across the changed boundaries — every place the code assumes a value is present because "it always is."
- Inverted and short-circuited logic: negated conditions, `&&`/`||` mix-ups, early returns that skip cleanup or accounting, match/switch arms that fall through to the wrong default.
- Numbers and time: integer overflow and truncation, float precision on money, timezone and DST handling, wall clock used where monotonic time is required, durations mixed with timestamps.
- Resources: connections, files, locks, and subscriptions the change set opens — find the close on every path, including the error paths. Unbounded growth: caches without eviction, lists that only append.
- Contract with callers: does the changed function still honor what existing callers assume — same ordering, same nullability, same units, same side effects? Check the call sites the diff did not touch.

Quality bar:
- Every claimed bug comes with a concrete failing scenario: the inputs and state, the path the code takes, the wrong outcome at the end. A bug you cannot walk to a wrong outcome is not a finding.
- No hedging. Drop "might," "could," "perhaps," "you may want to." If you cannot verify something, say so directly — that is honest.
- Cite file:line for every step of the failing scenario. A finding without a citation is an opinion.
- If a path is genuinely sound, say so in one line and move on. Do not manufacture findings.

Output format in <Y>:
- Group findings by severity: Blocking (wrong result, data loss, crash, race), Important (wrong result on an edge case, resource leak), Nit (latent trap that needs future change to fire).
- Each finding states: (1) the bug in one sentence, (2) the failing scenario — inputs and state, then the wrong outcome, (3) the file:line citations along the path, (4) the plan location it traces to (or "unplanned"), (5) the concrete fix.
- List the paths you traced end to end and found sound, one line each.
- After the findings, list any "Out of scope" one-liners.
- End with a one-line verdict: merge as-is, merge after Blocking fixed, or return to implementation.
- No preamble. Get to the findings.

<X> = 
<Y> = 
<Z> = 
