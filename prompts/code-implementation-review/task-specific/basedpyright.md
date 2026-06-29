Run `basedpyright --pythonpath .venv/bin/python --project ~/pyrightconfig.json .` and fix every issue it reports until it passes with no errors or warnings.

For each type error/warning:
- Fix the code to satisfy the type checker (add type annotations, fix mismatched types, handle Optional values, etc.)
- Do NOT weaken pyrightconfig.json settings unless it is necessary and reasonable; ask first
- Do NOT add `# type: ignore` or `# pyright: ignore` comments unless there is genuinely no better fix and you have the operator's permission
- If the issue is in a third-party library's types, prefer adding a minimal type stub or a cast over suppressing the warning

Re-run basedpyright after each batch of fixes and repeat until it exits with 0 errors and 0 warnings.
After all basedpyright errors and warnings are fixed, run tests to check if we did not break anything.
