---
name: python-project-setup
description: Use when bootstrapping a NEW Python project or a new Python component in a monorepo from commit 1 — pinning the interpreter to the mandatory greenfield floor of CPython 3.14 (`.python-version` plus `requires-python`), adopting `uv` with a committed `uv.lock`, laying out `src/` behind a real `[build-system]`, declaring dev tooling in a PEP 735 `[dependency-groups]` group, and configuring the linter and type checker to fail instead of advise. Triggers — a component directory has no `pyproject.toml` yet; `uv sync` is not yet the single command that produces a working environment; the interpreter version is whatever each developer happens to have; lint and type checks run but nothing ever fails. Not for the task runner (`justfile-setup`), layering (`python-ddd`), import contracts (`python-import-linter-setup`), or uv workspace mechanics (`patterns/conventions/python.md`).
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.3"
---

# Python Project Setup

One-time setup skill — the Python half of phase 1 (*workspace + toolchain*) in
`greenfield-project-setup`. Its Rust sibling is `rust-project-setup`.

It owns exactly five things:

1. **Interpreter pinning** — `.python-version` and `requires-python`.
2. **`uv` as the package manager**, with a committed `uv.lock`.
3. **The `pyproject.toml` shape at commit 1** — `[project]`, `[build-system]`,
   and a `src/` layout.
4. **Dev tooling in `[dependency-groups]`** (PEP 735), never in extras.
5. **Linter and type-checker configuration that fails the build**, pinned so
   every developer and CI run the same versions.

Everything else — command invocation, layering, which lint rules apply, what the
tests look like — belongs to a skill listed at the bottom.

Every behavioral claim below was reproduced against **uv 0.7.20, ruff 0.16.2,
mypy 1.18.2**. Three are tool-version-bound and are the ones to re-check on an
upgrade: ruff's `target-version` inference from `requires-python`, hatchling's
wheel-inference failure on a name mismatch, and `[tool.uv] dev-dependencies`
still being accepted as the legacy form.

> **Scope gate — this skill adds no task runner and no second command surface.**
> `just` is the project's single command surface; the rationale lives in
> `justfile-setup`. No `[tool.poe]`, no `tox`/`nox` task aliases, no `Makefile`,
> no `[project.scripts]` entry that exists only to wrap `ruff` or `mypy`. A
> `[project.scripts]` console entry point for the application itself is fine —
> `uv init --package` writes one.

---

## Interpreter Pinning (CRITICAL)

**The greenfield floor is CPython 3.14.** A new project or a new component pins
3.14 or newer — never `>=3.13` or lower, regardless of what the machine happens
to have installed. Two declarations are required, and they are not redundant.

```
service/.python-version          →  3.14
service/pyproject.toml           →  [project] requires-python = ">=3.14"
```

**`.python-version` selects the interpreter.** uv resolves the Python request in
priority order: an explicit `--python` argument, then `.python-version`, then
`requires-python`. Without the pin file the third case applies and uv selects
**an interpreter of its own choosing** — by default a uv-*managed* installation
(`python-preference = "managed"`), otherwise one discovered on `PATH`. Not "the
newest", not "the lowest that satisfies the floor", not the system `python3`:
reproduced with floor `>=3.11` and 3.14.6, 3.13.14, 3.13.5, 3.13.1, 3.12.3 and
3.11.15 all discoverable, uv chose **3.13.1**. The version is a property of the
machine's uv state, not of the repository, and nothing reports which one you got.

**`requires-python` is a resolution and metadata constraint**, not an interpreter
selector. It bounds resolution — every locked version must support the whole
declared range; is recorded in `uv.lock` as its own `requires-python` field, so
changing the floor invalidates the lockfile; ships in the distribution metadata
as `Requires-Python: >=3.14`; and supplies ruff's `target-version` when absent.

### Keep the pin equal to the floor

Pin the minor version the floor names — `.python-version` of `3.14` with
`requires-python = ">=3.14"`. Two things break when they disagree.

**A pin below the floor is a hard error**, exit code **2**, on every project
command. (The capture below was taken against a `>=3.13` floor, before 3.14
became the mandated baseline; the behaviour is the same at any floor.)

```
$ uv sync
Using CPython 3.11.15 interpreter at: /usr/bin/python3.11
error: The Python request from `.python-version` resolved to Python 3.11.15,
which is incompatible with the project's Python requirement: `>=3.13`
(from `project.requires-python`)
Use `uv python pin` to update the `.python-version` file to a compatible version
```

That one is loud, so it fixes itself.

**A pin above the floor is silent, and therefore the dangerous case.** Pin
`3.13` with `requires-python = ">=3.11"` and nothing fails, but the two halves of
the toolchain now target different versions. Verified on a file using
`typing.override` (added in 3.12): **mypy passed** — with no `python_version`
configured it checks against the interpreter it runs under, 3.13, not the
declared 3.11 floor — and **ruff inferred `target-version = 3.11`** from
`requires-python`, whose rules do not model stdlib availability either. So a
3.11-incompatible file passes every local gate while the manifest promises 3.11
support, until a 3.11 environment runs the code. An application has no reason to
declare a range wider than the version it runs.

### Bootstrap command

```bash
uv init --package --name backend-service --python 3.14 service
```

That writes both declarations consistently, plus `src/backend_service/`, a
`[build-system]`, and a `[project.scripts]` entry point. `--package` is what
makes it a real distribution; without it uv creates an application project with
no `[build-system]`. Commit both files: `.python-version` is a repository
invariant, not a personal preference.

---

## uv and the Committed Lockfile (CRITICAL)

`uv` is the package manager. One tool resolves, locks, installs, and runs — the
project never mixes in `pip install`, `poetry`, or a hand-managed `venv`.

**Commit `uv.lock`.** It is a cross-platform lockfile holding the exact resolved
version of every dependency for all platform and marker combinations; uv's own
guidance is that it belongs in version control and is never hand-edited. For an
application it *is* the reproducibility contract: the same commit produces the
same environment on every machine, in CI, and in the production image. (A library
cannot dictate its consumers' versions, so its lockfile governs only its own
development environment — commit it anyway, for that.)

**Never commit `.venv`, and do not assume uv wrote a `.gitignore` for you.**
`uv init --vcs git` generates one only when it also initializes the repository.
Run inside an existing git repository — the "adding a Python component to an
existing monorepo" trigger — it writes **no `.gitignore` at all** (reproduced).
Confirm the repository-root file already covers the component, or write
`service/.gitignore` with `.venv/`, `__pycache__/`, `*.egg-info/`, `build/`, and
`dist/`. `uv.lock` must **not** appear in any `.gitignore` on the path to it.

### `--locked` and `--frozen` in CI

Picking the wrong one turns a reproducibility check into a no-op.

| Flag | Behavior | Where it belongs |
|---|---|---|
| `uv sync --locked` | Re-resolves, compares against the existing `uv.lock`, and **fails if the lockfile would change**. Exits 2. | Every CI job. It is the assertion that the lockfile matches the manifests. |
| `uv sync --frozen` | Installs from `uv.lock` as-is, validating nothing. | Only where validation is impossible — e.g. a Docker layer that has the manifests but not yet the member sources. |
| `uv sync` | Re-resolves and **rewrites** `uv.lock`. | Local development only. |

**CI must run `uv sync --locked`**, so a developer who edits
`[project.dependencies]` without running `uv lock` gets a failing build instead
of a job that quietly re-resolves and installs something no one reviewed.
`ci-setup`'s Python job installs with `uv sync --locked` and takes the
interpreter from `.python-version` — never `pip install -e ".[dev]"`, since dev
tooling is not an extra and pip writes into an environment the lockfile is meant
to describe, and never a hardcoded `python-version:`, which makes the interpreter
a property of the workflow instead of the repository.

---

## The `pyproject.toml` at Commit 1 (CRITICAL)

One manifest, four required tables. This is the single copy of the block; later
sections refer back to it instead of repeating it.

```toml
[project]
name = "backend-service"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = []

[dependency-groups]
dev = [
    "ruff==0.16.2",
    "mypy==1.18.2",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "PTH", "TID", "PLC0415"]

[tool.ruff.lint.flake8-tidy-imports]
ban-relative-imports = "all"

[tool.mypy]
strict = true
files = ["src"]
```

**Getting the exact pins.** The versions above are the ones verified for this
skill. Do not copy them blindly and do not leave a range — resolve the current
versions, then rewrite each specifier as `==` at the version `uv.lock` reports
and run `uv lock` to record the narrowed specifier:

```bash
uv add --dev ruff mypy             # resolves them and records them in uv.lock
grep -A1 '^name = "ruff"' uv.lock  # → version = "0.16.2"
grep -A1 '^name = "mypy"' uv.lock  # → version = "1.18.2"
```

**Layout.** `pyproject.toml`, `.python-version`, the committed `uv.lock`, and
`src/backend_service/__init__.py`. Where tests live is *not* this skill's
decision: `python-ddd` owns it and places unit tests **inside** the package root
at `src/tests/unit/...`. Follow that skill; this one only needs `src/` to exist
behind a build backend.

### Why `src/` and not a flat layout

The flat layout *hides* a packaging bug rather than causing one. Verified, with
no `[build-system]` declared in either case:

| Layout | `import backend_service` from the project root | What it means |
|---|---|---|
| Flat (`backend_service/` at the root) | **Succeeds** — resolved from the current directory, and `importlib.metadata.version("backend-service")` raises `PackageNotFoundError` | The distribution is not installed at all. Every local run, every test, every REPL session works anyway. The failure waits for the container. |
| `src/` | **Fails** — `ModuleNotFoundError: No module named 'backend_service'` | The defect is loud at commit 1, before there is any code to salvage. |

With `src/` the *only* way an import works is through a real installation, so
what you test locally is what ships. Adding a `[build-system]` makes `uv sync`
install the project (the lockfile records it as `source = { editable = "." }`)
and imports resolve from the venv.

### `[build-system]` is not optional

A `pyproject.toml` with no `[build-system]` is locked by uv as **virtual**
(`source = { virtual = "." }`): uv declines to install it, `uv sync` succeeds
with no warning, and the problem surfaces later as a `ModuleNotFoundError` in
whatever depends on it. Declare a build backend for anything whose code is
imported.

### Three different names

The component directory (`service/`, in the repository layout and `justfile`
recipes), the distribution name (`backend-service`, in `[project] name`, the wheel
filename, and consumers' `Requires-Dist`), and the import package
(`backend_service`, in `src/` and every `import` statement) are independent.
Hatchling infers the wheel contents from `src/<import_package>` **only when the
import package matches the normalized distribution name**; when they differ the
build fails and must be told explicitly, with
`[tool.hatch.build.targets.wheel] packages = ["src/service_core"]`. The default —
import package equal to the distribution name with hyphens replaced by
underscores — needs no such table. Prefer it.

---

## Dev Dependencies Go in `[dependency-groups]` (CRITICAL)

Development tooling goes in the PEP 735 `dev` group shown in the manifest above.
**Never** in `[project.optional-dependencies]`.

The reason is structural, not stylistic: **a dependency group never appears in a
built distribution; an extra does.** PEP 735 (Final, 2024-10-10) states that
build backends **MUST NOT** include dependency-group data in built distributions
as package metadata. Verified by building both from one manifest — the wheel's
`METADATA` carried

```
Provides-Extra: lint
Requires-Dist: ruff>=0.16; extra == 'lint'
```

for the extra, and **nothing at all** for the identical `dev` group. Ship a wheel
whose dev tools live in an extra and they are advertised in your public
dependency metadata forever; a consumer can install them, and a mistyped extra
name can drag your linter into their production image.

Mechanics:

- `dev` is synced **by default**. `uv sync` installs it; `uv sync --no-dev` omits
  it, which is what a production image uses. Additional default groups go in
  `[tool.uv] default-groups`.
- `uv add --dev <package>` writes to `[dependency-groups] dev` and is the
  correct way to add tooling.
- `[tool.uv] dev-dependencies` is the **legacy** form. uv still merges it into
  the `dev` group and emits no warning about it, so nothing will tell you it is
  the wrong table — do not write it in a new project.
- Extras remain correct for genuinely optional *runtime* features a consumer may
  want. Dev tooling is never that.

---

## Lint and Type Checking Must Fail (CRITICAL)

Two tools cover everything: **ruff is both the linter (`ruff check`) and the
formatter (`ruff format`)** — no separate `black`, no separate `isort`, and import
sorting is ruff's `I` family — and **mypy** is the type checker. Both are
configured in the manifest, pinned in the dev group, and must exit non-zero on a
violation. **Advisory-only lint is an anti-pattern in this library**: a check
that cannot fail does not hold a convention, it describes one.

Three requirements, all load-bearing:

**1. Pinned to an exact version in the dev group.** `ruff==0.16.2`, not
`ruff>=0.16`. A range means a developer who synced last month and CI disagree
about what a violation is, and a rule added in a patch release turns a green
branch red with no source change. Bump the pin deliberately, in its own commit,
with the resulting fixes.

**2. Configured in `pyproject.toml`** — the `[tool.ruff]`, `[tool.ruff.lint]` and
`[tool.mypy]` tables above, with no `.ruff.toml`, `mypy.ini`, or `setup.cfg`
alongside them. `target-version` is deliberately absent: ruff infers it from
`requires-python` (verified — `>=3.13` resolves to target version 3.13), and one
declaration of the target beats two that can drift.

**3. Verified to actually fail.** Confirmed exit codes:

| Command | Clean tree | Planted violation |
|---|---|---|
| `uv run ruff check .` | 0 (`All checks passed!`) | **1** |
| `uv run ruff format --check .` | 0 | **1** (`File would be reformatted`) |
| `uv run mypy` | 0 | **1** |

Never suppress these with `--exit-zero`, `|| true`, or a `continue-on-error` CI
step. If a rule is wrong, remove the rule.

### Which rules to select

`python-code-style-v1` owns the style rules themselves but names no ruff codes,
so the mapping from its prose rules to enforceable families is made here and is
already in the `select` above:

| House rule | Mechanized by |
|---|---|
| Pathlib over `os.path` | `PTH` (flake8-use-pathlib) |
| Absolute imports only | `TID` **plus** `ban-relative-imports = "all"` — the default (`"parents"`) permits `from . import x`, verified |
| No function-level imports | `PLC0415` (`import-outside-top-level`), selected as a single code because the whole `PLC` family is far broader |
| Errors, unused names, import order, modern syntax, bug patterns, simplification | `E`, `F`, `I`, `UP`, `B`, `SIM` |

**Never enable the `ANN` family.** It contradicts `python-code-style-v1`, which
forbids writing `-> None`: `ANN201` reports `Missing return type annotation for
public function` with `help: Add return type annotation: None` (verified). Two
gates demanding opposite things means one of them gets suppressed everywhere.

### The type-check invocation, and `[tool.mypy] files`

**The manifest decides the scope; the invocation carries no path.** Run
`uv run mypy` — bare. An explicit path **overrides** `files`: with
`files = ["src"]` and an error planted in `tests/`, `uv run mypy` exits 0 while
`uv run mypy .` exits 1 (verified). The bare form is what `justfile-setup`'s
component check recipe and `ci-setup`'s Python job invoke, so what a developer
verifies is exactly what the task runner and CI check.

What `files` holds depends on the layout `python-ddd` gives you:

- **Tests inside the package root** (`src/tests/unit/...`, the `python-ddd`
  convention) — `files = ["src"]` already covers them and `strict = true`
  type-checks tests from commit 1. Nothing to add later; expect strict findings
  in test modules and fix them rather than loosening the setting.
- **Tests in a top-level `tests/`** — `files = ["src", "tests"]`, with `"tests"`
  added in the same change that adds the first test module, not before.

That ordering matters because of one trap: `files` must list only directories
containing at least one `.py` file. Both a missing directory and an existing but
empty one make mypy exit **2** before checking anything:

```
mypy: can't read file 'tests': No such file or directory
There are no .py[i] files in directory 'tests'
```

Exit code 2 is a *usage* error, not a clean run — a CI step that only checks for
"not 1" reads it as success.

### The type checker

`mypy` in `strict` mode is this library's default, and what its CI and `justfile`
templates invoke. `basedpyright` (or `pyright`) is an acceptable substitute — the
three requirements are unchanged: pinned in the dev group, configured in
`pyproject.toml` (`[tool.basedpyright]`), and failing the build. Configure only
one; two type checkers means two sets of suppression comments.

---

## Single Package or uv Workspace (HIGH)

Decide this once, at commit 1, because converting later moves every path.

**Start with a single package** when the component ships one distribution: one
`pyproject.toml`, one `uv.lock`, one `src/<import_package>/`, everything above and
nothing more. This is the default and covers most services.

**Adopt a uv workspace** when two or more distributions live in the repository (a
service and a background worker, say), when shared code must be consumed by two
or more members without copying it, or when a dev-only package (a conventions
rules library) must be usable by every member yet never ship.

The mechanics then — workspace and source tables, the shared `.venv` and the one
lockfile every member shares, the `--package` traps, why every depended-upon
member needs an explicit `[build-system]`, and production/Docker packaging with
`--no-editable` and the `--frozen`-then-`--locked` layering — are documented in
**`patterns/conventions/python.md`**, sections *uv Workspaces — the packaging
substrate* and *Production: shipping members that are not dev-only*. Read them
there; duplicated prose drifts, and the copy that is wrong is the one someone
follows.

The one thing this skill adds: **the interpreter pin is a single
`.python-version` at the workspace root**, not one per member. A workspace shares
one environment, so a per-member pin has nothing of its own to select; uv's
discovery walks up from the member directory and finds the root file.

---

## Verification (CRITICAL)

The orchestrator's phase-1 gate is "`uv sync` succeeds", and this skill's own
evidence proves that gate insufficient on its own: `uv sync` exits **0** on a
`src/` layout with no `[build-system]`, and the import still fails. That is why
steps 3 and 5 exist. Never report phase 1 complete on `uv sync` alone.

Run the sequence from the component directory. **Every step asserts** — copy the
failure branches as written; a step that only prints its exit code is not a
check.

```bash
# Assert helper. `set -e` will NOT do instead: steps 5 and 8 expect a non-zero
# exit, which set -e would treat as fatal.
fail() { echo "FAIL $1"; exit 1; }

# 1. THE GATE — a working environment from the manifest alone.
uv sync       || fail "1: uv sync"
test -d .venv || fail "1: no .venv created"

# 2. The pin is actually in effect.
pinned_version="$(cat .python-version)"
running_version="$(uv run python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
test "$running_version" = "$pinned_version" || fail "2: pinned $pinned_version, running $running_version"

# 2b. The floor is at or above the mandated greenfield baseline. A ban that lives
#     only in prose is not a ban; this is what makes it one.
uv run python - <<'FLOOR' || fail "2b: requires-python floor is below 3.14"
import pathlib, re, sys, tomllib

requirement = tomllib.loads(pathlib.Path("pyproject.toml").read_text())["project"]["requires-python"]
floor = re.search(r"(\d+)\.(\d+)", requirement)
sys.exit(0 if floor and (int(floor.group(1)), int(floor.group(2))) >= (3, 14) else 1)
FLOOR

# 3. The project is really installed — src/ + [build-system] are wired. The
#    import succeeding is the whole signal; do NOT print __file__ to "prove"
#    installation, because under an editable install it is the source path
#    either way and cannot distinguish installed from shadowed by cwd.
uv run python -c "import backend_service" || fail "3: not importable — missing [build-system]?"
uv run python -c "import importlib.metadata as metadata; metadata.version('backend-service')" \
  || fail "3: distribution metadata absent — not installed"

# 4. The lockfile exists, is not ignored, and is honored.
test -f uv.lock             || fail "4: no uv.lock"
git check-ignore -q uv.lock && fail "4: uv.lock is gitignored"
git check-ignore -q .venv   || fail "4: .venv is NOT gitignored"
uv sync --locked            || fail "4: uv sync --locked failed"

# 5. The lockfile check can actually fail (proves --locked is not decorative).
#    tomli-w because no project already declares it; staging the manifest first
#    gives the undo a baseline even before the first commit. Undo via git, never
#    `uv remove` — on an existing project that discards a real pin and re-locks.
git add pyproject.toml
uv add --dev --frozen tomli-w      # edits the manifest, not the lock
uv sync --locked; lock_check_status=$?
test "$lock_check_status" -eq 2 || fail "5: expected exit 2 from --locked, got $lock_check_status"
# expected: error: The lockfile at `uv.lock` needs to be updated, but
#           `--locked` was provided. To update the lockfile, run `uv lock`.
git checkout -- pyproject.toml
uv sync --locked || fail "5: not restored after undo"

# 6. Tooling passes on a clean tree.
uv run ruff check .          || fail "6: ruff check"
uv run ruff format --check . || fail "6: ruff format"
uv run mypy                  || fail "6: mypy"

# 7. Tooling FAILS on a planted violation — the check that matters most.
printf 'import os\n' > src/backend_service/planted_violation.py
uv run ruff check . ; ruff_status=$?
printf 'def broken() -> int:\n    return "text"\n' > src/backend_service/planted_violation.py
uv run mypy ; mypy_status=$?
rm src/backend_service/planted_violation.py
test "$ruff_status" -eq 1 || fail "7: ruff did not fail (got $ruff_status)"
test "$mypy_status" -eq 1 || fail "7: mypy did not fail (got $mypy_status)"

# 8. A pin below the floor is a hard error. Choose a below-floor minor version
#    `uv python list` already shows as installed — otherwise uv must download it,
#    and under UV_PYTHON_DOWNLOADS=0 the step fails for an unrelated reason.
cp .python-version .python-version.backup
echo "3.11" > .python-version
uv sync; mismatch_status=$?
cp .python-version.backup .python-version && rm .python-version.backup
test "$mismatch_status" -eq 2 || fail "8: expected exit 2 on pin below floor, got $mismatch_status"

# 9. Clean again.
uv sync --locked && uv run ruff check . && uv run mypy \
  && echo "phase 1 complete" || fail "9: tree not clean"
```

Step 7 is not ceremony. A gate nobody has seen fail is a gate nobody knows
works, and the two most common commit-1 defects — an empty `select` list and a
type checker pointed at the wrong directory — both look exactly like a passing
build.

## Anti-Patterns to Avoid

1. **A pin and a floor that disagree**, or no `.python-version` at all. With no
   pin, uv picks an interpreter of its own choosing and nothing reports which.
   Below the floor it is a hard error; above it, mypy checks the interpreter it
   runs under while ruff targets the floor, so version-incompatible code passes
   every local gate.
2. **A greenfield floor below 3.14.** `>=3.13` or lower on new work is banned, no
   matter what the developer's machine has installed. It silently forfeits stdlib
   the patterns depend on — `uuid.uuid7()`, and with it the time-ordered resource
   names the parallel-test-isolation orphan sweep uses — and it starts the project
   already owing an upgrade.
3. **The wrong `uv sync` flag in CI.** `--frozen` validates nothing, so the job
   passes with a lockfile that no longer matches the manifests; bare `uv sync`
   *rewrites* the lockfile, so the build installs a resolution no one reviewed.
   CI takes `--locked`, always. Equally: an uncommitted or gitignored `uv.lock`
   leaves no reproducibility contract to check.
4. **`pip install` or a hand-made `venv`** inside a uv project — including
   `pip install -e ".[dev]"` in a workflow. It writes into an environment the
   lockfile is supposed to describe, and the drift stays invisible until
   `uv sync` removes it.
5. **Passing a path to the type checker** (`uv run mypy .`). The explicit path
   overrides `[tool.mypy] files`, so the invocation, not the manifest, decides
   the scope — and the two disagree the moment a directory is added.

## Relationship to Other Skills and Patterns

- **`greenfield-project-setup` (skill)** — the orchestrator; this skill is its
  phase-1 Python delegate. Its gate is `uv sync` succeeds; see Verification for
  why that alone is not enough.
- **`justfile-setup` (skill)** — owns the task runner, every command name, and
  the rationale for a single command surface. Its Python recipes invoke what
  this skill configures (`uv run ruff check .`, `uv run mypy`, `uv run pytest`).
- **`python-ddd` (skill)** — phase 2. Owns what goes *inside* `src/`, including
  where tests live (`src/tests/`), which decides what `[tool.mypy] files` holds.
- **`python-import-linter-setup` (skill)** — phase 3. Owns the architecture gate
  and its `[tool.importlinter]` contracts, including adding `import-linter` to
  the dev group.
- **`patterns/conventions/python.md` (pattern)** — owns uv workspace mechanics
  (`[tool.uv.workspace]`, `[tool.uv.sources]`, the shared lockfile and its
  caveats, the `--package` trap) and production packaging (Docker layering,
  `--no-editable`, `--frozen` then `--locked`). Cite it; never copy it.
