Your task is to review the implementation of plan <X> against the current codebase for security concerns only, and write your findings to <Y>.

Scope: you are the security reviewer. Judge only security, in any language the implementation touches. Architecture, style, and product concerns go in an "Out of scope" list at the end, one line each — do not investigate them.

Change scope: the implementation under review is everything that changed to implement plan <X>. If <Z> is set, the change set is the diff from <Z> to the working tree (committed and uncommitted). If <Z> is empty, the change set is the uncommitted changes plus the commits on the current branch that are not on the default branch. Establish the change set with git before you start, and review the code as it exists now — not as the plan describes it.

Rules:
- Read the plan in full, then read every changed file that handles input, auth, data access, or output. No skimming, no trusting the plan's description of what was built.
- Security the plan promised but the code does not contain is a Blocking finding. Cite the plan promise and the place in the code where the enforcement should be and is not.
- You may run the project's gates and tests read-only to check a claim, scoped to the changed areas. Never modify, stage, or commit anything.

Work through the full checklist:

- Authentication and authorization: for every endpoint, route, command, or job the change set adds or changes — who can call it, and where is that enforced? Cite the enforcement line. A handler reachable without the check the plan promised is Blocking.
- Input validation: every input crossing a trust boundary in the change set — HTTP bodies, query parameters, headers, file uploads, message payloads. Find the validation in the code: type, length, range, encoding. Absent validation is a finding; validation in the frontend only is a finding.
- Injection surfaces: SQL built by string concatenation or formatting, shell commands from user input, path traversal on file operations, HTML injection through templates or `v-html`. Check every place the change set builds a query, command, path, or template from external data.
- Secrets: keys, tokens, or passwords appearing in the change set — code, config, test fixtures, or committed env files. New secrets the implementation needs: how are they provisioned, and do they leak into logs or error messages?
- Data exposure: response payloads and serializers in the change set leaking fields the caller should not see. Multi-tenant edges: can tenant A reach tenant B's rows through any path the change set touches? Trace the query filters.
- Sensitive data in logs: credentials, tokens, or personal data flowing into the log statements the change set adds.
- Proof: for every denial the code enforces — wrong role, bad input, cross-tenant access — the test that proves the denial path. An enforcement with no test proving it rejects is a finding.

Quality bar:
- No vague feedback. "Validate the input" is not a finding. "The new upload handler at path/to/handler:42 uses the client filename in the storage path without normalization — reject path separators before use" is a finding.
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
