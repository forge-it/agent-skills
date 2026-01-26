---
description: Use when running python commands
globs:
alwaysApply: false
---

# Python Command Execution

## Virtual Environment Execution (CRITICAL)

Always run Python commands through the project's package manager to ensure the correct virtual environment and dependencies are used.

### Determine the Package Manager

Check which tool the project uses:
- **Poetry**: Look for `poetry.lock` file
- **uv**: Look for `uv.lock` file

### Required Pattern

**For Poetry projects:**
```bash
poetry run python <args>
poetry run python script.py
poetry run python -m module_name
```

**For uv projects:**
```bash
uv run python <args>
uv run python script.py
uv run python -m module_name
```

**DON'T:**
```bash
python <args>
python script.py
python -m module_name
```

### Why This Matters

- Ensures commands run within the project's virtual environment
- Guarantees all project dependencies are available
- Maintains consistency across different development environments
- Prevents conflicts with system Python or other project environments
