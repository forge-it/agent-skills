Your task is to review the implementation of multiple plans <X> against the current codebase by dispatching one subagent per (plan, track) pair. All subagents run fully in parallel — they review disjoint concerns and do not interfere. Each subagent writes its findings to its own review file under <Y>.

The plans in <X> are typically a main plan plus follow-up plans that forked from it because of related work. Treat each plan independently.

The two tracks per plan are fixed:
- **backend** — rust code (typically under `core/`). Skills: rust-hexagonal-architecture, rust-design-idioms, rust-testing.
- **frontend** — vue code (typically under `web/`). Skills: frontend-vue-development, frontend-vue-code-style.

For each plan path in <X>:
- Read the plan briefly to determine which tracks apply. This is the only plan reading you do — do not start reviewing.
- If the plan touches rust code, dispatch a backend subagent for that plan.
- If the plan touches vue code in `web/`, dispatch a frontend subagent for that plan.
- A plan with backend-only work yields 1 subagent. A plan with both yields 2 subagents.

Total subagents = sum of applicable tracks across all plans. Examples:
- 3 plans, all backend-only → 3 subagents.
- 3 plans, all with backend + frontend → 6 subagents.
- 3 plans where only 1 has frontend work → 4 subagents.

Each subagent receives, and nothing else:
1. The single plan path it must review.
2. The output review file path it must write its findings to.
3. The track's review prompt, passed verbatim from the section below, with `<X>` substituted to the plan path and `<Y>` substituted to the output file path.

No summary of prior conversation. No cross-plan context. No cross-track context. No hints about other plans, other tracks, or the relationship between the main plan and follow-ups.

Rules:
- One subagent per (plan, track). The backend subagent for plan P reviews only rust code in the scope of plan P. The frontend subagent for plan P reviews only vue code in the scope of plan P.
- Full parallelism. Dispatch every applicable subagent in the same message (multiple tool calls in one response). They review disjoint concerns and do not interfere.
- Do not merge findings across plans, do not let one plan's subagent reach into another plan's scope. The main plan and its follow-ups are reviewed independently even though they are related.
- Cross-cutting concerns (rare — e.g. a shared API contract or a finding that spans plans) should be flagged inside whichever (plan, track) the operator decides owns them. Do not duplicate the finding across plans or across tracks.
- Each subagent writes to its own output file under <Y>, named `review-<plan-stem>-<track>.md`, where `<plan-stem>` is the plan's filename without extension and `<track>` is `backend` or `frontend`. Do not merge files. Do not produce a combined report.
- Pass the track's review prompt verbatim. Do not paraphrase, condense, summarise, or "improve" it — its framing is load-bearing. Only substitute the per-subagent `<X>` (plan path) and `<Y>` (output file path) values.
- Do not perform any review yourself. You orchestrate; the subagents review. The only plan reading you do is enough to decide whether a track applies for that plan.
- Do not edit, merge, or rewrite the review files after the subagents return.
- After all subagents return, list every output review file path to the operator, grouped by plan. Do not summarise findings.
- If a subagent fails or returns without writing its review file, surface the failure — do not retry silently and do not let another (plan, track) absorb its scope.

Loop terminates when every dispatched subagent has returned and its review file exists at the expected path.

---

## Backend track prompt (verbatim payload for each backend subagent)

Your task is to review the backend (rust) implementation of plan <X> against the current codebase and report any issues found to <Y>.

Skills to be used:
- rust-hexagonal-architecture
- rust-design-idioms
- rust-testing

Rules:
- Review only rust code (typically under `core/`). Do not flag frontend issues.
- Review only the scope of plan <X>. Do not flag issues that belong to other plans or to code untouched by this plan.
- Verify hexagonal architecture compliance — dependencies must point inward, no framework or transport concerns in domain, ports defined in application/domain with adapters in infrastructure.
- Verify project structure conventions per `core/docs/guidelines/project_structure.md` (concept-based folders, internal file layout, trait/struct naming, error files).
- Check SRP violations — this is the most important rule. Flag any file, struct, or function that mixes concerns.
- Check that no new migrations were created on pre-prod; modifications should stay in the initial migration. If a new migration exists, flag it.
- Compare the implementation against the plan — flag any divergence, missing pieces, or extra work not described in the plan.
- Check for broken file paths, stale references, or dead code (the codebase may have drifted during implementation).
- Check test coverage and adherence to the `rust-testing` skill and the `parallel_test_isolation_pattern` (unit, integration, e2e).
- Check naming conventions: `Default*` prefix for canonical implementations, trait gets the clean name, error enums live in `error.rs`, file names follow the role (`service.rs`, `orchestrator.rs`, `executor.rs`, etc.).
- Report architecture weak decisions, ambiguities, potential bugs, race conditions, or missing edge cases.
- Report any code that could be improved, clarified, or simplified without breaking the rules above.
- If you need to break any of these rules for practical reasons, flag it to the operator.

<X> = (the orchestrator fills this in — the plan path for this subagent)
<Y> = (the orchestrator fills this in — `review-<plan-stem>-backend.md` under the output directory)

---

## Frontend track prompt (verbatim payload for each frontend subagent)

Your task is to review the frontend (vue) implementation of plan <X> against the current codebase and report any issues found to <Y>.

Skills to be used:
- frontend-vue-development
- frontend-vue-code-style

Rules:
- Review only vue code (typically under `web/`). Do not flag backend issues.
- Review only the scope of plan <X>. Do not flag issues that belong to other plans or to code untouched by this plan.
- Verify project structure conventions per `web/docs/guidelines/project_structure.md` (feature-based folders, component naming, container/presenter split, import rules).
- Check SRP violations — this is the most important rule. Flag any file, component, composable, or function that mixes concerns.
- Compare the implementation against the plan — flag any divergence, missing pieces, or extra work not described in the plan.
- Check for broken file paths, stale references, or dead code (the codebase may have drifted during implementation).
- Check test coverage and adherence to frontend testing patterns.
- Check naming conventions for components, composables, stores, and types per `frontend-vue-code-style`.
- Report architecture weak decisions, ambiguities, potential bugs, accessibility issues, or missing edge cases.
- Report any code that could be improved, clarified, or simplified without breaking the rules above.
- If you need to break any of these rules for practical reasons, flag it to the operator.

<X> = (the orchestrator fills this in — the plan path for this subagent)
<Y> = (the orchestrator fills this in — `review-<plan-stem>-frontend.md` under the output directory)

---

<X> = plan paths, one per line — typically a main plan plus follow-up plans that forked from it
<Y> = output directory for review files
