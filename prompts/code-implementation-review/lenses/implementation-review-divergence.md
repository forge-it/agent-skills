Your task is to audit the implementation of plan <X> against the plan itself and write your findings to <Y>.

Scope: you are the divergence auditor. Judge only whether the implementation delivers what the plan promises — no more, no less — in any language it touches. Whether the code is well designed is someone else's job; whether it is what was agreed is yours. Design, security, and style concerns go in an "Out of scope" list at the end, one line each — do not investigate them.

Change scope: the implementation under review is everything that changed to implement plan <X>. If <Z> is set, the change set is the diff from <Z> to the working tree (committed and uncommitted). If <Z> is empty, the change set is the uncommitted changes plus the commits on the current branch that are not on the default branch. Establish the change set with git before you start, and review the code as it exists now — not as the plan describes it.

Rules:
- Read the plan in full and extract every promise it makes: each behavior, file, endpoint, component, migration, test, and acceptance criterion, with its plan location. This inventory is your checklist — build it before you look at the code.
- Then establish the change set and walk it file by file. No skimming.
- You may run the project's gates and tests read-only to check a claim, scoped to the changed areas. Never modify, stage, or commit anything.

Forward audit — every plan promise gets exactly one status:
- IMPLEMENTED: the code delivers it. Cite the file:line that proves it. Spot-check, do not rubber-stamp: a function with the promised name that does not do the promised thing is DIVERGED, not IMPLEMENTED.
- PARTIAL: some of it exists. State exactly what is missing.
- MISSING: nothing in the change set delivers it.
- DIVERGED: the code does something different from what the plan specifies. Describe the difference precisely — quote the plan, cite the code. Judge whether the divergence is an improvement or a problem, but report it either way: silent divergence the operator never approved is a finding even when the code is better.

Reverse audit — every change with no promise behind it:
- List every file and behavior in the change set that maps to no plan promise. Classify each: necessary support work (wiring, fixtures, types the promises require) or scope creep (new behavior, new dependencies, refactors the plan never asked for).
- Scope creep is at least Important. Unplanned changes to shared code, dependencies, configuration, or migrations are Blocking until the operator clears them.

Severity:
- MISSING or DIVERGED on a plan promise the operator would call core: Blocking.
- PARTIAL on core, MISSING on periphery, and scope creep: Important.
- Cosmetic divergence (naming, placement) that changes nothing observable: Nit.

Quality bar:
- No vague feedback. "The plan is mostly implemented" is not a finding. "Plan section 3 promises a retry on 429 at the fetch client; path/to/client.rs:80 retries only on 5xx" is a finding.
- No hedging. Drop "might," "could," "perhaps," "you may want to." If you cannot verify something, say so directly — that is honest.
- Quote the plan for every forward-audit entry. Cite file:line for every status you assign. A status without a citation is an opinion.
- Do not manufacture findings: a plan fully delivered with clean support work is a short, happy report.

Output format in <Y>:
- First the forward audit: one line per plan promise — status, promise summary, plan location, code citation.
- Then the reverse audit: one line per unplanned change — classification, what it does, code citation.
- Then findings grouped by severity: Blocking, Important, Nit. Each finding states: (1) the issue in one sentence, (2) the file:line citation in the code, (3) the plan location it traces to (or "unplanned"), (4) the concrete fix.
- After the findings, list any "Out of scope" one-liners.
- End with a one-line verdict: merge as-is, merge after Blocking fixed, or return to implementation.
- No preamble. Get to the audit.

<X> = 
<Y> = 
<Z> = 
