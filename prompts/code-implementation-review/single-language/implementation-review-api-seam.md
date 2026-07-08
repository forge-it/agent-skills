Your task is to tear apart the API seam of the implementation of plan <X> against the current codebase and write your findings to <Y>.

The backend is <BACKEND>; the frontend is Vue 3. You review ONLY the wire between them: the contract as actually built, not the code on either side. Most reviewers stay on one side of the wire and miss the seams. You will not.

I bet you cannot find every contract issue in this implementation. Prove me wrong.

Scope: judge only what crosses the wire — shapes, statuses, parameters, auth, serialization. In-language design issues on either side go in an "Out of scope" list at the end, one line each — do not investigate them.

Change scope: the implementation under review is everything that changed to implement plan <X>. If <Z> is set, the change set is the diff from <Z> to the working tree (committed and uncommitted). If <Z> is empty, the change set is the uncommitted changes plus the commits on the current branch that are not on the default branch. Establish the change set with git before you start, and review the code as it exists now — not as the plan describes it.

Rules:
- Read the plan in full, then walk every endpoint the change set adds or changes on BOTH sides of the wire: the backend handler and the frontend call site. No skimming, no trusting the plan's description of the contract.
- You may run the project's gates and tests read-only to check a claim, scoped to the changed areas. Never modify, stage, or commit anything.

Checks, for every endpoint the change set touches:
- Contract drift: the shape the backend actually returns versus the shape the frontend actually parses. Cite both sides. For a Rust backend that means the serde response structs and handler return types; for a Python backend the Pydantic response models and FastAPI response_model declarations. On the Vue side, the client types and the code that reads the fields.
- Field-level mismatches: name and casing, nullability and optionality, enum string vs int representation, null vs missing field, datetime timezone handling, decimal precision. Each mismatch is a finding.
- Type generation: if TypeScript types are generated from the backend schema (OpenAPI or otherwise), was the generation step run — do the generated types match the handlers as built? If types are hand-maintained on both sides, flag every place they drifted during this implementation.
- Error contract: how does a backend error become an HTTP status and a Vue-visible message on the paths the change set adds? Check the error handlers and shapes actually built. A frontend that parses `{message}` when the backend sends `{detail}` is a finding.
- Status codes: every status the backend handler can return versus every status the frontend handles. An unhandled failure status the user would see as a silent hang or blank screen is a finding.
- Auth and permission edges: which roles can hit each touched endpoint, where the backend enforces it (cite the line), and what the Vue side renders when forbidden. Enforcement the plan promised but the code does not contain is a Blocking finding.
- Pagination, sorting, filtering: if the backend added it, is the frontend wired? If the frontend assumes it, does the backend deliver? Query parameter names must match exactly — check the actual strings on both sides.
- Orphans: frontend calls to endpoints that do not exist or were renamed, and new backend endpoints no frontend code consumes. Each is a finding.

No vague feedback. "Consider aligning the types" is not a finding. "Handler path/to/handler returns `created_at` as epoch millis but path/to/Component.vue:42 formats it as an ISO string — regenerate the client type and fix the formatter" is a finding.

No hedging. Drop "might," "could," "perhaps," "you may want to." If you cannot verify something, say so directly — that is honest. Hedging while pretending to know is dishonest.

Quote the plan when you challenge the implementation against it. Cite file:line on each side of the wire when you justify a finding. A finding without a citation is an opinion.

If you find nothing wrong, you missed things. Implementations are never perfect. Walk the contract again endpoint by endpoint.

Output format in <Y>:
- Group findings by severity: Blocking, Important, Nit.
- Each finding states: (1) the issue in one sentence, (2) the citation on each side of the wire that proves it, (3) the plan location it traces to (or "unplanned"), (4) the concrete fix.
- After the findings, list any "Out of scope" one-liners.
- End with a one-line verdict: merge as-is, merge after Blocking fixed, or return to implementation.
- No preamble. No "I reviewed the implementation and…" Get to the findings.

<X> = 
<Y> = 
<Z> = 
<BACKEND> = 
