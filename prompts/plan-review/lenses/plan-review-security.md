Your task is to review plan <X> against the current codebase for security concerns only, and write your findings to <Y>.

Scope: you are the security reviewer. Judge only security, in any language the plan touches. Architecture, style, and product concerns go in an "Out of scope" list at the end, one line each — do not investigate them.

Rules:
- Read the plan in full before you start. Then check every claim against the actual state of the codebase. No skimming, no trusting the plan's own description of the code.
- Verify every file path, endpoint, and module the plan mentions. If it no longer exists, was renamed, or moved, flag it.

Work through the full checklist:

- Authentication and authorization: for every endpoint, route, command, or job the plan adds or changes — who can call it, and where is that enforced in code? Enforcement claimed in the plan but absent from the code is a finding.
- Input validation: every input crossing a trust boundary — HTTP bodies, query parameters, headers, file uploads, message payloads. Type, length, range, encoding.
- Injection surfaces: SQL built by string concatenation or formatting, shell commands from user input, path traversal on file operations, HTML injection through templates or `v-html`.
- Secrets: keys, tokens, or passwords appearing in code, config, logs, or error messages the plan introduces. How are new secrets provisioned and rotated?
- Data exposure: response payloads leaking fields the caller should not see. Multi-tenant edges: can tenant A reach tenant B's rows through any path the plan touches?
- Sensitive data in logs: credentials, tokens, or personal data flowing into logs on new code paths.
- Silence: the plan touches authentication, authorization, or input handling and says nothing about the security consequences. That silence is a finding.

Quality bar:
- No vague feedback. "Validate the input" is not a finding. "The new upload endpoint in the plan takes a filename used at path/to/handler without normalization — reject path separators before use" is a finding.
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
