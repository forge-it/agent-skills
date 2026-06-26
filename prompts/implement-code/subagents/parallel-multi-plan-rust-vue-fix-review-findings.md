Your task is to fix every unaddressed finding across all review files for one or more implementation plans <X>, by dispatching subagents per finding. The work must not contradict the original plans.

The plans in <X> are typically a main plan plus follow-up plans that forked from it because of related work. Treat each plan independently.

Review files are produced by the upstream review orchestrator and live under <Y>, named `review-<plan-stem>-<domain>.md`, where `<plan-stem>` is the plan filename without extension and `<domain>` is `backend` or `frontend`. For each plan in <X>, look in <Y> for both files; whichever exist define the plan's tracks.

The two domains are fixed:
- **backend** — rust code, typically under `core/`.
- **frontend** — vue code, typically under `web/`.

Both domains use the same worker prompt: `<agent-skills>/prompts/implement-code/stack-based/implement-rust-vue-task.md`. The domain is fixed by which review file the finding came from.

## Parallelism model

Code fixes are writes. Multiple subagents writing to the same directory at the same time race on the same files. The parallelism model below keeps writes safe while extracting all the parallelism that is actually safe.

- **Across domains: parallel.** Backend (`core/`) and frontend (`web/`) touch disjoint directories with disjoint test suites. A backend subagent and a frontend subagent may run concurrently.
- **Within a domain, across plans: serial.** All backend review files share `core/`; all frontend review files share `web/`. Running two subagents in the same domain concurrently would race. Process plans in the order listed in <X> — main plan first, then follow-ups, on the assumption that follow-ups build on the main plan.
- **Within a (plan, domain) track, across findings: serial.** Dispatch one finding, wait, verify, mark fixed, then dispatch the next finding in that track.

Max concurrency at any time: 1 backend subagent + 1 frontend subagent.

Examples:
- 3 plans, all with backend + frontend → 6 review files → backend queue (3 review files, serial) || frontend queue (3 review files, serial).
- 3 plans, all backend-only → 3 review files → backend queue only (3 review files, serial). No frontend queue.
- 3 plans where only 1 has frontend → 4 review files → backend queue (3 review files, serial) || frontend queue (1 review file).

## Per-subagent inputs

Each subagent receives, and nothing else:
1. The single finding text it must fix (verbatim).
2. The path of the review file the finding came from.
3. The plan path the review file belongs to (so the subagent can avoid contradicting that plan).
4. The contents of `<agent-skills>/prompts/implement-code/stack-based/implement-rust-vue-task.md`, passed verbatim.

No summary of prior conversation. No batching. No merging of findings. No hints about other findings, other tracks, or other plans.

## Rules

- One subagent per finding. The subagent fixes exactly that finding and nothing else — no opportunistic refactors, no neighbouring cleanups, no fixing the next finding "while we're here".
- The finding's domain is fixed by the review file it came from. A `review-*-backend.md` finding only touches rust code under `core/`. A `review-*-frontend.md` finding only touches vue code under `web/`. Cross-cutting findings (rare) should be flagged to the operator rather than dispatched.
- Plan scope: the finding's plan is fixed by the review file's `<plan-stem>`. Do not let a subagent fixing a plan-A finding wander into code that belongs only to plan B. If a finding genuinely requires changes that overlap with another plan's scope, stop and ask the operator.
- After each subagent returns:
  1. Verify the relevant tests still pass. Backend domain: backend test suite only. Frontend domain: frontend test suite only. If tests fail, stop that domain queue and surface the failure to the operator — do not dispatch the next finding in that domain. The other domain may continue.
  2. Re-read the finding and confirm the code change actually addresses it. If it does not, dispatch a follow-up subagent for the same finding with the new context (what the previous attempt got wrong). Do not mark it fixed.
  3. Mark the finding as fixed in its review file. Append `[FIXED]` to the finding's heading, or move the finding under a `## Resolved` section — whichever fits the file's existing structure. Edit the review file in place.
- Do not contradict the plan a finding belongs to. If a finding seems to conflict with its plan, stop that domain queue and ask the operator before dispatching.
- Do not skip, reorder, or defer a finding without explicit operator permission. "Deferred" means the operator confirmed the finding will be handled later; mark it `[DEFERRED]` in the review file with the operator's reason.
- Pass the worker prompt verbatim. Do not paraphrase, condense, summarise, or "improve" it — its framing is load-bearing.
- Do not read, merge, edit, or rewrite findings across files beyond marking them fixed or deferred. Treat each plan's findings independently even when plans are related follow-ups.
- Plan ordering within a domain matters: the main plan's findings are typically the foundation that follow-ups build on. Process plans in the order provided in <X>; within a plan, process findings top-to-bottom in the review file.
- If a review file expected by the naming convention does not exist for a plan, that plan simply has no track in that domain — do not error out.

Loop terminates when every finding in every existing review file is marked `[FIXED]` or `[DEFERRED]`. The backend domain queue and the frontend domain queue terminate independently.

<X> = plan paths, one per line — typically a main plan plus follow-up plans that forked from it (same plan list as the upstream review orchestrator)
<Y> = directory containing the review files produced by the upstream review orchestrator
