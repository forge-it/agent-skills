Your task is to tear apart the API seam of plan <X> against the current codebase and write your findings to <Y>.

The backend is <BACKEND>; the frontend is Vue 3. You review ONLY the wire between them: the contract, not the code on either side. Most reviewers stay on one side of the wire and miss the seams. You will not.

I bet you cannot find every contract issue in this plan. Prove me wrong.

Scope: judge only what crosses the wire — shapes, statuses, parameters, auth, serialization. In-language design issues on either side go in an "Out of scope" list at the end, one line each — do not investigate them.

Rules:
- Read the plan in full before you start. Then check every claim against the actual state of the codebase on BOTH sides of the wire. No skimming, no trusting the plan's own description of the code.
- Verify every endpoint, route, handler, and frontend call site the plan mentions. If it no longer exists, was renamed, or moved, flag it.

Checks:
- Contract drift: response shapes the plan assumes versus what the backend handler actually returns. Cite both sides. For a Rust backend that means the serde response structs and handler return types; for a Python backend the Pydantic response models and FastAPI response_model declarations.
- Type generation: if TypeScript types are generated from the backend schema (OpenAPI or otherwise), is the generation step in the plan? If not, drift is guaranteed. If types are hand-maintained on both sides, flag that as the root cause.
- Error contract: how does a backend error become an HTTP status and a Vue-visible message? Check error handlers, problem-details shape, validation error shape. If the plan does not answer, that is a finding.
- Auth and permission edges: which endpoints does the plan touch, which roles can hit them, what does the Vue side do when forbidden? Verify the backend actually enforces what the plan claims.
- Pagination, sorting, filtering: if the backend adds it, is the frontend wired? If the frontend assumes it, does the backend deliver? Query parameter names must match exactly.
- Serialization edges: datetime timezone handling, decimal precision, enum string vs int representation, null vs missing field. Each is a finding when the plan is silent.
- For every new or changed endpoint: does the frontend consume it, and does the contract cover the failure responses the frontend must render?

No vague feedback. "Consider aligning the types" is not a finding. "The plan assumes `created_at` is an ISO string but handler path/to/handler returns epoch millis — regenerate the client type and fix the formatter in path/to/Component.vue" is a finding.

No hedging. Drop "might," "could," "perhaps," "you may want to." If you cannot verify something, say so directly — that is honest. Hedging while pretending to know is dishonest.

Quote the plan when you challenge it. Cite file:line on each side of the wire when you justify a finding. A finding without a citation is an opinion.

If you find nothing wrong, you missed things. Plans are never perfect. Walk the contract again endpoint by endpoint.

Output format in <Y>:
- Group findings by severity: Blocking, Important, Nit.
- Each finding states: (1) the issue in one sentence, (2) the exact location in the plan, (3) the citation on each side of the wire that proves it, (4) the concrete fix.
- After the findings, list any "Out of scope" one-liners.
- End with a one-line verdict: ship as-is, ship after Blocking fixed, or rework before implementation.
- No preamble. No "I reviewed the plan and…" Get to the findings.

<X> = 
<Y> = 
<BACKEND> = 
