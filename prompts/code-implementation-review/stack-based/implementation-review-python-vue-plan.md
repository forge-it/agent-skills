Your task is to review the implementation of plan <X> against the current codebase and report any issues found to <Y>.

Skills to be used:
- python-code-style
- python-testing
- python-commands
- rest-api-design
- database-management
- general-logging
- git-workflow
- python-ddd

If the plan included frontend work in web/, also use these skills:
- frontend-vue-development
- frontend-vue-code-style

Rules:
- Verify hexagonal architecture compliance per python-ddd — dependencies must point inward, no framework or transport concerns in the domain, repository ports defined in the domain layer with adapters in the adapters layer, Unit-of-Work transaction boundary respected with explicit commit.
- Verify domain modeling per python-ddd — pure dataclass aggregates, classical (imperative) SQLAlchemy mapping, one repository port per aggregate root, factory-based UoW injection with typed repository attributes.
- Verify REST API conventions per rest-api-design for any endpoints touched.
- Verify web project structure conventions per web/docs/guidelines/project_structure.md for frontend work (feature-based folders, component naming, container/presenter split, import rules).
- Check SRP violations — this is the most important rule. Flag any file, class, or function that mixes concerns.
- Check that no new migrations were created on pre-prod; modifications should stay in the initial migration. If a new migration exists, flag it.
- Compare the implementation against the plan — flag any divergence, missing pieces, or extra work not described in the plan.
- Check for broken file paths, stale references, or dead code (the codebase may have drifted during implementation).
- Check test coverage and adherence to testing patterns per python-testing (unit, integration, e2e), including use of fakes (FakeUnitOfWork, in-memory repositories) where appropriate.
- Check naming conventions per python-code-style: no single-letter variables, no abbreviations, snake_case for functions and modules. Repository methods follow the get/find_by/list_/add/remove pattern with no update() method.
- Check that Python commands are run inside the project venv per python-commands.
- Check log structure per general-logging.
- Report architecture weak decisions, ambiguities, potential bugs, race conditions, or missing edge cases.
- Report any code that could be improved, clarified, or simplified without breaking the rules above.
- If you need to break any of these rules for practical reasons, flag it to the operator.
- For each issue you find, add a recommended solution to the review.

Skills path: <agent-skills>/software-engineering/

<X> = 
<Y> = 
