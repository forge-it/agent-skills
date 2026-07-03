Your task is to implement this plan <X>.

Skills to be used:
- rust-code-style
- rust-design-idioms
- rust-testing
- rust-project-structure

If the plan includes frontend work in web/, also use these skills:
- frontend-vue-development
- frontend-vue-code-style

Rules:
- Never break SRP (most important rule). If you need to break it for practical reasons you have to ask the operator.
- Never break core/docs/guidelines/project_structure.md
- Never break web/docs/guidelines/project_structure.md for frontend work
- Never create new migrations on pre-prod but modify initial migration in place. If you want to create a new migration you need to ask the operator.
- Implement plan with the best of your knowledge. Do not rely on the plan to break the rules already stated or skills. Any doubt should go to the operator.

Recommendations:
- You can use separate branch forked from main if the feature is heavy
- You can use sub agents to implement the code if it suits the required work
- Commit per plan phase

Skills path: /home/cristi/Projects/agent-skills/software-engineering/
Useful context: CLAUDE.md

<X> =
