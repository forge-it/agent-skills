Run the project's basedpyright check and fix every issue it reports until it passes with no errors or warnings.

Which command to run — take the first that applies:
1. The command the operator gave you, when there is one.
2. The project's documented type-check command — a `just <component>-check` recipe or equivalent. Run the basedpyright step it contains, as written.
3. When the repository configures basedpyright itself (a `[tool.basedpyright]` table in `pyproject.toml`, or a committed `pyrightconfig.json` in the directory the check runs from), run it bare from that directory inside the project environment: `uv run basedpyright`. The in-tree configuration owns the scope — pass no path and no `--project`; a `--project` pointing at any other file replaces the repository's configuration entirely. If both a `pyrightconfig.json` and a `[tool.basedpyright]` table exist, the JSON file wins and the table is inert — treat the JSON file as the configuration and say so in your report.
4. Only if the repository ships no basedpyright configuration at all, fall back to `basedpyright --pythonpath .venv/bin/python --project ~/pyrightconfig.json .`, and say in your report that the repository has no in-tree configuration, so the run reproduces nothing CI can check.

If the chosen command is invalid for the repository (a different package manager, virtualenv, or interpreter), adapt only enough to use the repository's documented virtualenv, interpreter, or config path.

For each type error/warning:
- Fix the code to satisfy the type checker (add type annotations, fix mismatched types, handle Optional values, etc.)
- Do NOT weaken the type-checker configuration (`[tool.basedpyright]` or `pyrightconfig.json`) unless it is necessary and reasonable; ask first
- Do NOT add `# type: ignore` or `# pyright: ignore` comments unless there is genuinely no better fix and you have the operator's permission
- If the issue is in a third-party library's types, prefer adding a minimal type stub or a cast over suppressing the warning

Re-run basedpyright after each batch of fixes and repeat until it exits with 0 errors and 0 warnings.
After all basedpyright errors and warnings are fixed, run tests to check if we did not break anything.
