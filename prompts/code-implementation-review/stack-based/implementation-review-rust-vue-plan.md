Your task is to review the implementation of plan <X> against the current codebase and report any issues found to <Y>.

Skills to be used:
- rust-hexagonal-architecture
- rust-design-idioms
- rust-testing

If the plan included frontend work in web/, also use these skills:
- frontend-vue-development
- frontend-vue-code-style

Rules:
- Verify hexagonal architecture compliance — dependencies must point inward, no framework or transport concerns in domain, ports defined in application/domain with adapters in infrastructure.
- Verify project structure conventions per core/docs/guidelines/project_structure.md (concept-based folders, internal file layout, trait/struct naming, error files).
- Verify web project structure conventions per web/docs/guidelines/project_structure.md for frontend work (feature-based folders, component naming, container/presenter split, import rules).
- Check SRP violations — this is the most important rule. Flag any file, struct, or function that mixes concerns.
- Check that no new migrations were created on pre-prod; modifications should stay in the initial migration. If a new migration exists, flag it.
- Compare the implementation against the plan — flag any divergence, missing pieces, or extra work not described in the plan.
- Check for broken file paths, stale references, or dead code (the codebase may have drifted during implementation).
- Check test coverage and adherence to testing patterns documented in core/docs/knowledge-base/ (unit, integration, e2e).
- Check naming conventions: Default* prefix for canonical implementations, trait gets the clean name, error enums live in error.rs, file names follow the role (service.rs, orchestrator.rs, executor.rs, etc.).
- Report architecture weak decisions, ambiguities, potential bugs, race conditions, or missing edge cases.
- Report any code that could be improved, clarified, or simplified without breaking the rules above.
- If you need to break any of these rules for practical reasons, flag it to the operator.

<X> = 
<Y> = 
