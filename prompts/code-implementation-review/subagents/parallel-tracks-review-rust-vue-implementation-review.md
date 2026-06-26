Your task is to review the implementation of plan <X> against the current codebase by dispatching one subagent per review track. Tracks run in parallel — they review disjoint directories with disjoint concerns, so they do not interfere. Each subagent writes its findings to its own review file under <Y>.

The two tracks are fixed:
- **backend** — rust code (typically under `core/`). Skills: rust-hexagonal-architecture, rust-design-idioms, rust-testing.
- **frontend** — vue code (typically under `web/`). Skills: frontend-vue-development, frontend-vue-code-style.

If the plan has no frontend work in `web/`, dispatch only the backend track. If the plan has no backend work, dispatch only the frontend track. Otherwise dispatch both in parallel.

Each subagent receives, and nothing else:
1. The original plan path <X>.
2. The output review file path it must write its findings to.
3. The track's review prompt, passed verbatim from the section below.

No summary of prior conversation. No cross-track context. No hints about the other track's rules.

Rules:
- One subagent per track. The backend subagent reviews only rust code and flags only backend issues. The frontend subagent reviews only vue code and flags only frontend issues.
- Across tracks: parallel. Dispatch both subagents in the same message (multiple tool calls in one response) when both tracks apply. The tracks review disjoint directories with disjoint concerns and do not interfere.
- Cross-cutting concerns (rare — e.g. a shared API contract) should be flagged inside whichever track the operator decides owns them. Do not duplicate the finding across tracks.
- Each track writes to its own output file under <Y>: `review-backend.md` for the backend track, `review-frontend.md` for the frontend track. Do not merge findings across files. Do not produce a combined report.
- Pass the track's review prompt verbatim. Do not paraphrase, condense, summarise, or "improve" it — its framing is load-bearing.
- Do not perform any review yourself. You orchestrate; the subagents review. Do not read the codebase to "sanity-check" findings before they are written.
- Do not edit, merge, or rewrite the review files after the subagents return.
- After all subagents return, list the output review file paths to the operator. Do not summarise the findings.
- If a subagent fails or returns without writing its review file, surface the failure to the operator — do not retry silently and do not let the other track absorb its scope.

Loop terminates when every dispatched track's subagent has returned and its review file exists at the expected path.

---

## Backend track prompt (verbatim payload for the backend subagent)

Your task is to review the backend (rust) implementation of plan <X> against the current codebase and report any issues found to <Y>.

Skills to be used:
- rust-hexagonal-architecture
- rust-design-idioms
- rust-testing

Rules:
- Review only rust code (typically under `core/`). Do not flag frontend issues.
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

<X> = (the orchestrator fills this in)
<Y> = (the orchestrator fills this in — `review-backend.md` under the output directory)

---

## Frontend track prompt (verbatim payload for the frontend subagent)

Your task is to review the frontend (vue) implementation of plan <X> against the current codebase and report any issues found to <Y>.

Skills to be used:
- frontend-vue-development
- frontend-vue-code-style

Rules:
- Review only vue code (typically under `web/`). Do not flag backend issues.
- Verify project structure conventions per `web/docs/guidelines/project_structure.md` (feature-based folders, component naming, container/presenter split, import rules).
- Check SRP violations — this is the most important rule. Flag any file, component, composable, or function that mixes concerns.
- Compare the implementation against the plan — flag any divergence, missing pieces, or extra work not described in the plan.
- Check for broken file paths, stale references, or dead code (the codebase may have drifted during implementation).
- Check test coverage and adherence to frontend testing patterns.
- Check naming conventions for components, composables, stores, and types per `frontend-vue-code-style`.
- Report architecture weak decisions, ambiguities, potential bugs, accessibility issues, or missing edge cases.
- Report any code that could be improved, clarified, or simplified without breaking the rules above.
- If you need to break any of these rules for practical reasons, flag it to the operator.

<X> = (the orchestrator fills this in)
<Y> = (the orchestrator fills this in — `review-frontend.md` under the output directory)

---

<X> = original plan path
<Y> = output directory for review files
