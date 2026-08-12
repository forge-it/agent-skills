---
name: python-convention-enforcement-pattern
description: >-
  Use when a Python project's critical conventions live only in prose — a
  skill file, CLAUDE.md, a style guide — and any of these symptoms are
  present: the same violation is introduced repeatedly by different authors
  or agents and reviewers keep missing it; a rule is "enforced" by asking
  people to remember it; a monorepo has several packages that each evolve
  separately with no per-package gate; helper functions and fixtures
  accumulate at module scope inside test modules; one package imports
  another it never declared and nothing complains; or someone proposes a
  central scanner that audits every package from one place. Produces a
  dev-only conventions distribution inside a uv workspace (the ArchUnit
  pattern: rules as a library, enforcement local to each package), plus the
  workspace and production-packaging recipe that makes it work from
  commit 1.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.3"
---

# Python Convention Enforcement Pattern

## Purpose

**In one line:** package your conventions as a dev-only distribution in a uv
workspace, and have *every* package run those rules against *its own* source
tree as ordinary `pytest` tests — rules defined once, enforced N times.

The trap is treating a machine-decidable rule as a review responsibility. A
rule that lives only in a skill file or a style guide is enforced by memory,
and memory fails at scale: the same violation lands repeatedly, review catches
it inconsistently, and the rule quietly becomes advisory. Every violation that
survives review is evidence that the rule was in the wrong medium.

Two facts drive the design:

1. **Decidability, not topic, sets the boundary.** "A module-scope helper
   exists in a test module", "`port.py` contains a non-ABC class", "a domain
   dataclass exposes a mutable field" are 100% decidable from the AST. Naming
   intent, cohesion, and abstraction quality are not. The first group must
   never be review's job; the second can never leave it.
2. **Locality beats deduplication.** Packages evolve separately. A violation
   in `services/worker` must fail `services/worker`'s own test run — not a
   sibling's, and not only in CI.

> **Core principle:** machine-decidable rules are enforced by the test suite,
> in the package that owns the code. Judgment rules stay with human (or
> advisory-agent) review. A rule that can be checked and isn't is technical
> debt in the enforcement layer, not in the code.

There is one Python-specific stake that makes this pattern **load-bearing
rather than nice-to-have**. In a compiled workspace, the build system enforces
the dependency graph: a crate cannot use what it did not declare. The default
`uv sync` installs every workspace member into one shared virtual environment,
so any member can `import` any other regardless of what its `pyproject.toml`
declares — and that is how everybody develops locally. (A per-member
`uv sync --package X` does narrow the environment to X's closure, so the
undeclared import fails there; nobody works that way, and CI that runs members
serially thrashes the environment doing it.) In the flow people actually use,
**a checker is the only thing standing between you and accidental cross-package
imports.** In Python, the gate *is* the boundary.

> **Greenfield baseline:** every new Python project requires **CPython 3.13 or
> newer**. The implementation below deliberately uses the Python 3.13
> `Path.rglob(..., recurse_symlinks=True)` API; do not copy it into an older
> project without adapting the traversal.

## The ArchUnit Pattern (general view)

ArchUnit is a Java library (TNG Technology Consulting, open-sourced 2017) built
on one idea: **architecture rules should be unit tests, not wiki pages.** It
loads a queryable model of your code and expresses rules as fluent assertions
that JUnit runs like any other test:

```java
noClasses().that().resideInAPackage("..application..")
    .should().dependOnClassesThat().resideInAPackage("..infrastructure..")
```

The properties worth copying:

- **Rule families, not one-off scripts.** Dependency rules; a layered
  architecture DSL; onion/hexagonal templates; naming, annotation, and
  placement rules; and *slices* — automatic dependency-cycle detection between
  feature modules.
- **Reusable rule libraries.** Organisations ship an internal rules artifact;
  every service depends on it in test scope and runs the rules against itself.
  **This is the core of the pattern** — shared definitions, local execution —
  and it is what the conventions package below implements.
- **Rules are diffable code.** A weakened rule shows up in a pull request.

Two ArchUnit features to know about and consciously *not* adopt:

- **`FreezingArchRule`** wraps an existing rule, snapshots current violations
  into a committed store, and fails only new ones — so a rule can be adopted on
  a legacy codebase immediately. Genuine advantage, and still the wrong trade
  here: baselines rot, and "the rule passes" stops meaning "the code is clean".
  Clean to zero instead (see *Adopting on an existing codebase*).
- **Diagram-as-rule** (`adhereToPlantUmlDiagram()` — enforce that code
  dependencies match a component diagram). Impressive; rarely worth the upkeep.

Ports exist across ecosystems — ArchUnitNET (C#), ts-arch (TypeScript),
arch-go (Go), and for Python **PyTestArch** and **pytest-archon**.

**One asymmetry to understand before choosing tools.** ArchUnit reads compiled
bytecode, so it sees *resolved* types. Python has no equivalent artifact, and
its dynamism means full resolution is not cheaply available either. The Python
implementation therefore works at **source level** via the stdlib `ast` module
and compensates the same way other ports do: for import-dependency rules,
delegate to a real import-graph tool (`import-linter`); for everything else,
check *declarations* — which are exact in the AST — and close the syntactic
escape hatches rather than trying to resolve names.

## The Enforcement Ladder in Python

Python's ladder is unusually friendly: **every rung you should actually use is
stable** (tiers 1–3). There is no equivalent of a compiler-internals plugin
requiring a nightly toolchain, so custom static analysis is a normal
engineering task rather than a maintenance liability.

| Tier | Tool | Owns | Stable? |
|------|------|------|---------|
| 1. Config-only | **ruff** (`flake8-tidy-imports.banned-api`, `per-file-ignores`, import conventions), **import-linter** contracts in `pyproject.toml` | banned APIs, banned imports, layering, package independence, module cycles | ✅ |
| 2. Custom lint plugin | **flake8 plugin** (public entry-point API), **pylint checker**, **semgrep** / **ast-grep** YAML rules | rules you want reported *in the editor* at edit time | ✅ |
| 3. Architecture-as-tests | **pytest + `ast`** via the conventions package | declaration shape, placement, layout, vocabulary — the residue tiers 1–2 can't express | ✅ |
| 4. Type-level | **mypy plugin API** | rules needing inferred types | ⚠️ upstream calls it experimental: "backwards incompatible changes may be made without a deprecation period" |

Routing rules to tiers:

- **Anything import-shaped → tier 1, always.** `import-linter` builds a real
  import graph (statically, via `grimp` — it does not execute your code) and
  its contracts express a DDD stack declaratively, catching *transitive*
  violations a per-file scan cannot, and reporting the full chain. The contract
  set is broader than most readers expect — `layers`, `forbidden`,
  `independence`, `acyclic_siblings`, `protected` — and `acyclic_siblings` is
  precisely the ArchUnit "slices / cycle detection" property. Custom contract
  types are pluggable via `contract_types` too, so this tier is less
  config-only-limited than it looks. Never hand-roll layering checks in `ast`.
- **Banned APIs and per-directory prohibitions → tier 1.** Ruff's `banned-api`
  (TID251) plus scoping handles "never `datetime.now()` in the domain" class
  rules with config alone, three different ways: a negated glob in
  `per-file-ignores`, explicit non-domain globs, or a hierarchical
  `.ruff.toml` inside the domain package. Ruff has no third-party plugin
  support *yet* — upstream considers a plugin system in scope — so today treat
  it as a closed linter: adopt its rules and its knobs, write nothing custom
  into it.
- **Declaration shape, placement, layout, vocabulary → tier 3**, the
  conventions package. This is the residue and the reason the pattern exists.
- **Tier 2 is optional and additive.** Reach for it when a rule deserves an
  editor squiggle rather than a test failure. Don't run the same rule in two
  tiers.
- **Tier 4 only when a rule is genuinely un-approximable.** Most "needs types"
  rules are really "needs the declaration", which tier 3 has exactly.

**On PyTestArch / pytest-archon:** both are credible ArchUnit ports, both
scoped to the import-dependency dimension — which `import-linter` does better
and more declaratively. Neither addresses declaration-shape rules, which is the
actual reason to own a package. Both have also been quiet for roughly a year
(pytest-archon 0.0.7, 2025-09; PyTestArch 4.0.1, 2025-08). Skip them unless you
specifically want their rule DSL.

## uv Workspaces — the packaging substrate

A uv workspace is the direct analogue of a Cargo workspace: several
distributions in one repository, one lockfile, one resolution.

```
pyproject.toml                       # virtual workspace root (no [project] needed)
uv.lock                              # ONE lockfile for every member
packages/
  ironbox-conventions/               # the dev-only rules library
  ironbox-shared/                    # a production shared library
services/
  api/
  worker/
```

```toml
# pyproject.toml — workspace root
[tool.uv.workspace]
members = ["packages/*", "services/*"]

[dependency-groups]                  # PEP 735 — dev-only, never shipped
dev = ["pytest>=8", "ruff", "import-linter", "ironbox-conventions"]

[tool.uv.sources]                    # inherited by every member
ironbox-conventions = { workspace = true }
```

```toml
# services/api/pyproject.toml — a member
[project]
name = "api"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = ["ironbox-shared>=0.1", "fastapi[standard]"]   # standard; SHIPS in metadata

[dependency-groups]
dev = ["pytest>=8", "ironbox-conventions"]

[tool.uv.sources]                                              # uv-only; not in built metadata
ironbox-shared      = { workspace = true }
ironbox-conventions = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Root sources are inherited by all members**, so the member block above is
technically redundant — but a member's `[tool.uv.sources]` *replaces* the root
entry for that name rather than merging with it. Declaring per member is the
unambiguous form and the one to prefer; just know the duplication is a choice,
not a requirement.

```sh
uv sync                              # resolve + install every member into ONE .venv
cd services/api && uv run pytest     # run a member's suite (see the trap below)
uv build --package ironbox-shared    # build a distribution for one member
```

**Five caveats, three of which bite:**

1. **It is a uv feature, not a packaging standard.** `[tool.uv.workspace]` and
   `[tool.uv.sources]` have no PEP behind them; pip and poetry do not
   understand either. (`[dependency-groups]` *is* standard — PEP 735.) If the
   repo is not all-in on uv, fall back to plain editable path dependencies.
2. **One shared `.venv`, not one per member.** Two members needing conflicting
   versions of the same third-party package can never be *installed* together.
   They can be *locked* together via `[tool.uv] conflicts` (package-level
   conflicts are preview) and synced one member at a time; if both must be live
   simultaneously, uv's own guidance is path dependencies instead of a
   workspace.
3. **The dependency graph is unenforced in the default flow.** Because of (2),
   `worker` can `import api` with no declaration and nothing fails under a
   plain `uv sync`. See *Purpose* — this is why tier 1 is not optional.
4. **`uv run --package X` does not change directory**, and
   **`uv sync --package X` prunes the shared environment** to X's closure. The
   first is a live trap (below); the second makes serial per-member CI runs
   reinstall the world between members.
5. **A member is installed only if uv treats it as a package.** `[tool.uv]
   package = false` makes uv lock it as *virtual*, silently decline to install
   it, and surface the problem as `ModuleNotFoundError` in the dependent —
   `uv lock` and `uv sync` both succeed with no warning. Give every
   depended-upon member an explicit `[build-system]`.

> **The `--package` trap, concretely.** `uv run --package api pytest` runs from
> the *workspace root*, so pytest collects every member. Since this pattern
> puts an identically-named gate file in each one, collection aborts:
> `import file mismatch: imported module 'test_conventions' has this __file__
> attribute … which is not the same as the test file we want to collect`. Use
> `cd services/api && uv run pytest` (which also gives you a per-member
> rootdir, i.e. real locality) or `uv run --package api --directory services/api
> pytest`.

## The Conventions Package

```
packages/ironbox-conventions/
  pyproject.toml
  src/ironbox_conventions/
    __init__.py        # public surface: rule constructors + package_root, nothing else
    py.typed           # consumers type-check their gate files against real types
    _machinery.py      # Violation, Rule, package_root, uv.lock reading — no policy
    layout.py          # the day-1 test-layout rules
    workspace.py       # the coverage rule: every member carries a gate
  tests/               # fixture source trees proving each rule fires / stays quiet
```

Additional *style*-topic modules (`shape.py`, `vocabulary.py`, …) appear **later,
one rule at a time** — never on day 1. `workspace.py` is the exception: its single
rule is what makes every other rule reach every member, so it ships with the
gates. Two layers, and the split is the whole design: `_machinery.py` holds
**mechanics** (scanning, violation rendering, assertion), the topic modules hold
**policy** (what is allowed). Consumers only ever touch the rule constructors.

The per-package gate is a one-liner, identical in every member:

```python
# services/api/tests/architecture/test_conventions.py
from ironbox_conventions import (
    members_carry_convention_gates,
    module_filenames_follow_canonical_pattern,
    modules_contain_only_tests,
    package_root,
    pytest_references_use_canonical_names,
)


def test_members_carry_convention_gates():
    members_carry_convention_gates().enforce(package_root(__file__))


def test_modules_contain_only_tests():
    modules_contain_only_tests().enforce(package_root(__file__))


def test_module_filenames_follow_canonical_pattern():
    module_filenames_follow_canonical_pattern().enforce(package_root(__file__))


def test_pytest_references_use_canonical_names():
    pytest_references_use_canonical_names().enforce(package_root(__file__))
```

Four properties of this shape are load-bearing:

- **No separate test target.** Plain `pytest` in that package collects
  `tests/architecture/` automatically, so the gate rides along on every local
  run — the fastest possible feedback for zero configuration. (It is also why
  the runner must `cd` into the member; see the `--package` trap.)
- **No public name in the conventions package may begin with `test`.** pytest's
  `python_functions` default is the prefix `"test"`, and pytest collects names
  *imported into* a test module, not just those defined there. A constructor
  called `test_modules_contain_only_tests` would be collected as a phantom test
  in every gate file, pass silently while inflating the count, and — under the
  common `filterwarnings = ["error"]` — fail outright with
  `PytestReturnNotNoneWarning`, for a reason unrelated to the code being
  checked. Hence `modules_contain_only_tests()`.
- **`package_root(__file__)` resolves the caller's own package** by walking up
  to the nearest `pyproject.toml`, which in a workspace is the *member*, not
  the workspace root. It is *identity*, not configuration — the one argument a
  rule may take. (Frame inspection could make the call truly zero-argument;
  don't — a gate must be obvious, not clever.) **It is the only root helper the
  package exports, and every rule takes it** — including the workspace-scoped
  coverage rule, which derives the workspace from it internally. A second
  `*_root(__file__)` helper would be indistinguishable at the call site and one
  copy-paste away from a silent vacuous pass — see *Coverage* below.
- **The gate file satisfies its own rule** — imports plus one test function.
  The pattern dogfoods.

### Zero-knob rules

A universal rule takes **no policy parameters**. Compare:

```python
modules_contain_only_tests()                                       # ✅ zero-knob

modules_contain_only_tests(                                        # ❌ knobbed
    helper_dirs=["utils", "support", "shared"],
    allow_module_constants=True,
)
```

Exemptions are not *removed* by this — they are *relocated* into the rule's
**definition**, one value for the whole workspace, because they are part of
what the convention *is*. This rule's exemption mechanism is the canonical `python-testing` skill's own
filename discipline: it scans **only** `test_*.py`, so `conftest.py` and
`utils/*.py` are never test modules and are never examined. `*_test.py` is
pytest's other default but is **not** an allowed project test-module name;
`module_filenames_follow_canonical_pattern()` flags it rather than leaving it
as a silent bypass. **There is no path allowlist, so no ancestor-directory
match can disable the gate** — a directory-name check compared against
`path.parts` is one stray parent directory away from silently skipping
everything.

With call-site knobs, one package quietly widens its exemptions during an
unrelated fix; its gate stays green while the rule now means something weaker
there, and nothing surfaces it unless someone diffs gate files across every
package. The rule's name starts lying.

To be fair to the knobbed form: per-package configuration eases gradual
adoption on a legacy tree. Handle that differently — a package that is not
clean yet **visibly does not call the rule**, which is a diff a reviewer can
question, rather than a weakened rule that looks fully adopted.

**Escalation ladder when a package "really needs" an exception:**

1. **It usually needs a rename.** A support module called
   `tests/api/test_helpers.py` will be scanned, because it is named like a test
   module; wanting it exempted is precisely the drift the rule exists to stop.
   The fix is to move it to its mandated home, `tests/api/utils/helpers.py`.
2. **Real and general** → change the constant in the conventions package. One
   diff, uniform effect, reviewable as a workspace decision.
3. **Real, item-level, and local** → an in-source marker the rule itself
   defines and documents, visible at the exempted site.
4. **Real and structurally package-specific** (rare) → a second,
   deliberately-named constructor whose existence documents the exception
   publicly — never a parameter that lets the universal one be bent.

The invariant behind all four: **an exemption must be visible either in the
rule's single definition or at the exempted site — never in per-package
configuration, which is visible at neither.**

## Anatomy of a Rule (`ast`)

> These modules run as written (executed on CPython 3.13–3.14 against both
> compliant and violating fixture trees). They intentionally require the
> greenfield Python ≥3.13 baseline for symlink-safe traversal and encode *this
> repository's* test conventions — see `python-testing`. Re-read the constants
> and the allowed-construct list against your own conventions before adopting.

Machinery — mechanics only, no policy:

```python
# src/ironbox_conventions/_machinery.py
from __future__ import annotations

import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

LOCKFILE_NAME = "uv.lock"
MEMBER_SOURCE_KEYS = ("editable", "virtual")


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    message: str

    def render(self, root: Path) -> str:
        return f"{self.path.relative_to(root)}:{self.line}: {self.message}"


@dataclass(frozen=True)
class Rule:
    description: str
    check: Callable[[Path], list[Violation]]

    def enforce(self, root: Path) -> None:
        violations = self.check(root)
        if not violations:
            return
        rendered = "\n".join(violation.render(root) for violation in violations)
        raise AssertionError(
            f"{self.description}: {len(violations)} violation(s)\n{rendered}"
        )


def package_root(marker: str) -> Path:
    """The package owning `marker` — nearest ancestor holding a pyproject.toml."""
    for candidate in Path(marker).resolve().parents:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise RuntimeError(f"no pyproject.toml above {marker}")


def enclosing_workspace_directory(package_directory: Path) -> Path:
    """The uv workspace owning a package — nearest `uv.lock` at or above it.

    Deliberately NOT re-exported from `__init__.py`: gate files pass
    `package_root(__file__)` only, and the one workspace-scoped rule calls this.
    The candidate list starts with `package_directory` itself, because in the
    `editable = "."` topology the root package *is* the workspace directory.
    """
    for candidate in (package_directory, *package_directory.parents):
        if (candidate / LOCKFILE_NAME).is_file():
            return candidate
    raise RuntimeError(
        f"no {LOCKFILE_NAME} at or above {package_directory} — a workspace-wide "
        f"rule must never pass vacuously; commit the lockfile before wiring this gate"
    )


def locked_member_directories(workspace_directory: Path) -> list[Path]:
    """Members as uv itself recorded them: the names in `[manifest] members`.

    Source kinds are only the name → directory mapping: `editable` and `virtual`
    packages own a tree, `directory` (an in-repo path dependency) and `registry`
    (a third-party distribution) do not. Source kind never decides membership —
    an out-of-glob path dependency with `[tool.uv] package = false` also locks as
    `virtual`, and it is not a member.
    """
    lockfile = workspace_directory / LOCKFILE_NAME
    if not lockfile.is_file():
        raise RuntimeError(f"{workspace_directory} has no {LOCKFILE_NAME}; run `uv lock`")
    locked_workspace = tomllib.loads(lockfile.read_text(encoding="utf-8"))
    member_names = locked_workspace.get("manifest", {}).get("members")
    if member_names is None:
        raise RuntimeError(
            f"{lockfile} has no `[manifest] members`: this is a single-package "
            f"project, not a uv workspace, so this rule has no subject — delete "
            f"the members_carry_convention_gates() call from this gate file"
        )
    directory_by_member_name = {
        locked_package["name"]: locked_package["source"][source_key]
        for locked_package in locked_workspace.get("package", [])
        for source_key in MEMBER_SOURCE_KEYS
        if source_key in locked_package.get("source", {})
    }
    member_directories: list[Path] = []
    for member_name in member_names:
        if member_name not in directory_by_member_name:
            raise RuntimeError(
                f"{lockfile} names member `{member_name}` in `[manifest] members`, "
                f"but no [[package]] entry gives its directory; run `uv lock`"
            )
        relative_directory = directory_by_member_name[member_name]
        member_directory = workspace_directory / relative_directory
        if not member_directory.is_dir():
            raise RuntimeError(
                f"stale {LOCKFILE_NAME}: member `{member_name}` is locked at "
                f"{relative_directory!r}, absent under {workspace_directory}; "
                f"run `uv lock`"
            )
        member_directories.append(member_directory)
    return sorted(set(member_directories))
```

Policy — the archetypal first rule, **test modules contain only tests**:

```python
# src/ironbox_conventions/layout.py
from __future__ import annotations

import ast
from pathlib import Path

from ._machinery import Rule, Violation

TESTS_DIR_NAME = "tests"
CANONICAL_TEST_MODULE_GLOB = "test_*.py"             # python-testing's canonical pattern
NON_CANONICAL_TEST_MODULE_GLOB = "*_test.py"          # pytest allows it; this project forbids it
TEST_FUNCTION_PREFIX = "test_"
TEST_CLASS_PREFIX = "Test"
MODULE_MARKER_NAME = "pytestmark"
PYTEST_MODULE_NAMES = frozenset({"pytest", "pytest_asyncio"})
IMPORT_GUARD_CALLS = frozenset({"pytest.importorskip", "importorskip"})
MODULE_SKIP_CALLS = frozenset({"pytest.skip", "skip"})
IMPORT_EXCEPTION_NAMES = frozenset({"ImportError", "ModuleNotFoundError"})
FIXTURE_DECORATORS = frozenset({"fixture", "pytest.fixture", "pytest_asyncio.fixture"})
XUNIT_METHOD_NAMES = frozenset(
    {"setup_method", "teardown_method", "setup_class", "teardown_class"}
)


def modules_contain_only_tests() -> Rule:
    # The name must NOT start with `test`: pytest would collect this constructor
    # as a phantom test in every gate file that imports it.
    return Rule(
        description=(
            "test modules (test_*.py) must contain only tests; fixtures belong in "
            "conftest.py and every other support definition in utils/"
        ),
        check=_check_test_module_contents,
    )


def module_filenames_follow_canonical_pattern() -> Rule:
    """Reject pytest's permitted-but-project-noncanonical `*_test.py` form."""
    return Rule(
        description="test modules must use python-testing's canonical test_*.py filename pattern",
        check=_check_test_module_filenames,
    )


def pytest_references_use_canonical_names() -> Rule:
    """Keep pytest references syntactic; convention rules deliberately do not resolve aliases."""
    return Rule(
        description="pytest imports must use canonical names without aliases",
        check=_check_pytest_references,
    )


def _check_test_module_contents(root: Path) -> list[Violation]:
    tests_dir = _tests_dir(root)
    violations: list[Violation] = []
    for path in sorted(tests_dir.rglob(CANONICAL_TEST_MODULE_GLOB, recurse_symlinks=True)):
        violations += _scan_module(path, check_contents=True, check_pytest_references=False)
    return violations


def _check_test_module_filenames(root: Path) -> list[Violation]:
    tests_dir = _tests_dir(root)
    return [
        Violation(
            path,
            1,
            "test module uses pytest's allowed but project-noncanonical `*_test.py` "
            "name; rename it to `test_*.py`",
        )
        for path in sorted(
            tests_dir.rglob(NON_CANONICAL_TEST_MODULE_GLOB, recurse_symlinks=True)
        )
        if not path.name.startswith(TEST_FUNCTION_PREFIX)
    ]


def _check_pytest_references(root: Path) -> list[Violation]:
    violations: list[Violation] = []
    for path in sorted(_tests_dir(root).rglob("*.py", recurse_symlinks=True)):
        violations += _scan_module(path, check_contents=False, check_pytest_references=True)
    return violations


def _tests_dir(root: Path) -> Path:
    tests_dir = root / TESTS_DIR_NAME
    if not tests_dir.is_dir():
        raise RuntimeError(
            f"{root} has no {TESTS_DIR_NAME}/ directory — a gate that cannot fail is "
            f"worse than no gate; create it. (The coverage rule makes this branch "
            f"near-unreachable: the gate file itself lives under {TESTS_DIR_NAME}/.)"
        )
    return tests_dir


def _scan_module(
    path: Path,
    check_contents: bool,
    check_pytest_references: bool,
) -> list[Violation]:
    try:
        # Bytes, not text: lets CPython handle a BOM and PEP 263 coding cookies,
        # which `read_text(encoding="utf-8")` turns into bogus parse failures.
        module = ast.parse(path.read_bytes(), filename=str(path))
    except (SyntaxError, ValueError, OSError) as error:
        return [Violation(path, 1, f"cannot be parsed as Python: {error}")]
    violations: list[Violation] = []
    if check_pytest_references:
        violations += _canonical_pytest_import_violations(path, module.body)
    if check_contents:
        violations += _scan(path, module.body, scope="module scope")
    return violations


def _canonical_pytest_import_violations(path: Path, body: list[ast.stmt]) -> list[Violation]:
    """Keep pytest references syntactic so the layout rule never needs alias resolution."""
    violations: list[Violation] = []
    for node in body:
        match node:
            case ast.Import(names=names):
                for imported_name in names:
                    if (
                        imported_name.name in PYTEST_MODULE_NAMES
                        and imported_name.asname is not None
                    ):
                        violations.append(
                            Violation(
                                path,
                                node.lineno,
                                f"import `{imported_name.name}` without an alias; "
                                "convention rules require canonical pytest names",
                            )
                        )
            case ast.ImportFrom(module=module, names=names) if module in PYTEST_MODULE_NAMES:
                for imported_name in names:
                    if imported_name.asname is not None:
                        violations.append(
                            Violation(
                                path,
                                node.lineno,
                                f"import `{imported_name.name}` from `{module}` without an alias; "
                                "convention rules require canonical pytest names",
                            )
                        )
            case _:
                continue
    return violations


def _scan(path: Path, body: list[ast.stmt], scope: str) -> list[Violation]:
    violations: list[Violation] = []
    for node in body:
        match node:
            case ast.Import() | ast.ImportFrom() | ast.Pass():
                continue
            case ast.Expr(value=ast.Constant(value=str())):              # docstring
                continue
            case ast.If() | ast.Try():
                violations += _scan_guard(path, node)
            case _ if _is_module_marker(node) or _is_pytest_directive(node):
                continue
            case ast.FunctionDef(name=name) | ast.AsyncFunctionDef(name=name) if (
                name.startswith(TEST_FUNCTION_PREFIX) and not _is_fixture(node)
            ):
                continue
            case ast.ClassDef(name=name) if name.startswith(TEST_CLASS_PREFIX):
                violations += _scan(path, node.body, scope="test class body")
            case _:
                violations.append(Violation(path, node.lineno, _describe(node, scope)))
    return violations


def _scan_guard(path: Path, node: ast.stmt) -> list[Violation]:
    """Guards hold imports — plus `name = None` only in an import-exception arm."""
    scope = "try block" if isinstance(node, ast.Try) else "module-scope if"
    violations: list[Violation] = []
    for inner_body, allows_import_fallback in _guard_bodies(node):
        remaining = [
            statement
            for statement in inner_body
            if not (allows_import_fallback and _is_import_fallback(statement))
        ]
        violations += _scan(path, remaining, scope=scope)
    return violations


def _guard_bodies(node: ast.stmt) -> list[tuple[list[ast.stmt], bool]]:
    bodies = [(getattr(node, "body", []), False), (getattr(node, "orelse", []), False)]
    if isinstance(node, ast.Try):
        bodies += [
            (handler.body, _is_import_exception_handler(handler))
            for handler in node.handlers
        ]
        bodies.append((node.finalbody, False))
    return bodies


def _is_import_exception_handler(handler: ast.ExceptHandler) -> bool:
    if isinstance(handler.type, ast.Tuple):
        return all(
            _dotted_name(exception_type) in IMPORT_EXCEPTION_NAMES
            for exception_type in handler.type.elts
        )
    return _dotted_name(handler.type) in IMPORT_EXCEPTION_NAMES


def _is_import_fallback(node: ast.stmt) -> bool:
    """`orjson = None` in an import-exception arm is part of the import shim."""
    if not isinstance(node, (ast.Assign, ast.AnnAssign)):
        return False
    return isinstance(node.value, ast.Constant) and node.value.value is None


def _is_module_marker(node: ast.stmt) -> bool:
    # Deliberately not a `match`: `ast.Name(id=MODULE_MARKER_NAME)` would be a
    # capture pattern binding every name, not a comparison against the constant.
    if isinstance(node, ast.Assign):
        targets: list[ast.expr] = node.targets
    elif isinstance(node, ast.AnnAssign):
        targets = [node.target]
    else:
        return False
    return (
        len(targets) == 1
        and isinstance(targets[0], ast.Name)
        and targets[0].id == MODULE_MARKER_NAME
    )


def _is_pytest_directive(node: ast.stmt) -> bool:
    """`pytest.importorskip(...)` and `pytest.skip(..., allow_module_level=True)`
    are only legal in the module they guard — they cannot move to conftest.py."""
    call = _directive_call(node)
    if call is None:
        return False
    name = _dotted_name(call.func)
    if name in IMPORT_GUARD_CALLS:
        return True
    return name in MODULE_SKIP_CALLS and any(
        keyword.arg == "allow_module_level"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value is True
        for keyword in call.keywords
    )


def _directive_call(node: ast.stmt) -> ast.Call | None:
    match node:
        case ast.Expr(value=ast.Call() as call):                     # bare call
            return call
        case ast.Assign(value=ast.Call() as call) | ast.AnnAssign(value=ast.Call() as call):
            return call
        case _:
            return None


def _is_fixture(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(_dotted_name(d) in FIXTURE_DECORATORS for d in node.decorator_list)


def _dotted_name(node: ast.expr) -> str:
    match node:
        case ast.Call(func=inner):
            return _dotted_name(inner)
        case ast.Attribute(value=value, attr=attr):
            return f"{_dotted_name(value)}.{attr}"
        case ast.Name(id=name):
            return name
        case _:
            return ""


def _describe(node: ast.stmt, scope: str) -> str:
    match node:
        case ast.FunctionDef(name=name) | ast.AsyncFunctionDef(name=name):
            if _is_fixture(node):
                return f"{scope}: fixture `{name}` — fixtures belong in conftest.py"
            if name in XUNIT_METHOD_NAMES:
                return f"{scope}: `{name}` — setup belongs in a conftest.py fixture"
            return f"{scope}: `def {name}` is not a test; move it to utils/"
        case ast.ClassDef(name=name):
            return f"{scope}: `class {name}` is not a test class; move it to utils/"
        case ast.Assign() | ast.AnnAssign():
            return f"{scope}: constant or data literal; move it to utils/constants.py"
        case _:
            return f"{scope}: `{type(node).__name__}` is not a test; move it to utils/"
```

These details generalise to every rule you add:

- **Scope by the canonical convention's naming discipline, not a path
  allowlist.** Matching `python-testing`'s `test_*.py` pattern is what makes
  `conftest.py` and `utils/` exempt. A directory-name allowlist compared
  against `path.parts` matches *ancestors* too — a checkout at
  `~/support/myrepo/` would skip every file and the gate would pass while
  enforcing nothing.
- **Turn an ecosystem/per-project mismatch into a visible gate.** Pytest also
  collects `*_test.py`; the canonical skill forbids it. The filename rule flags
  it explicitly instead of treating it as either a legitimate test module or a
  silent bypass.
- **Whitelist, never blacklist.** Enumerate what is *allowed* at module scope
  and reject everything else. A blacklist is always one construct behind.
- **Recurse into every nested scope you allow.** Skipping an allowed node
  wholesale is a bypass: `if TYPE_CHECKING:` with a helper inside it would sail
  through. Allowed containers are scanned with the same rules, so a guard block
  may hold only imports — plus a `name = None` fallback in an
  `except ImportError` / `except ModuleNotFoundError` arm (including a tuple
  made entirely of those two exceptions). `except Exception: cache = None` is
  not an import shim and must flag.
- **Fixtures are violations, not tests.** The convention routes them to
  `conftest.py` at the narrowest appropriate scope, so the rule flags any
  `@pytest.fixture` in a test module *and* inside a test class. Two traps here:
  the decorator set is an explicit allowlist of dotted names, because a
  `.endswith("fixture")` match would silently bless `@my_fixture` on a plain
  helper; and the fixture check must run *before* the `test_`-prefix
  acceptance, or the ubiquitous `@pytest.fixture def test_client()` slips
  through unseen.
- **Keep pytest references canonical instead of resolving aliases.** The rule
  intentionally rejects `import pytest as pt` and `from pytest import fixture
  as pytest_fixture`: aliases make `pt.importorskip(...)` and
  `@pytest_fixture` invisible to a syntactic checker. This is a deliberately
  narrow convention — a separate rule owns the import shape rather than turning
  the layout rule into a miniature name resolver.
- **Exempt what genuinely cannot move.** `pytestmark`, `pytest.importorskip`
  (bare *or* assigned), and `pytest.skip(..., allow_module_level=True)` must be
  module-level statements *in that file* — pytest documents them that way. The
  latter is exempted only when `allow_module_level` is the literal `True`, not
  merely when a same-named keyword appears. A rule whose remediation is
  impossible teaches people to suppress it.
- **Unparseable input is a violation, not a crash — and "unparseable" is
  narrower than it looks.** Read bytes so CPython handles BOMs and PEP 263
  coding cookies; catch `OSError` too, or a directory named `test_data.py` or
  an unreadable file turns a violation report into a traceback that names
  neither the rule nor the package.
- **`match` has a footgun that silently weakens rules.** A bare name inside a
  class pattern — `ast.Name(id=MODULE_MARKER_NAME)` — is a *capture* pattern
  that binds anything, not a comparison against the constant; the arm matches
  every assignment and the rule quietly stops firing. Compare with `isinstance`
  (as `_is_module_marker` does) or use a dotted value pattern. This is exactly
  why every rule needs a fires-on-violation test, not only a
  stays-quiet-on-clean one.
- **Follow symlinked test trees.** The greenfield baseline is Python ≥3.13, so
  every traversal uses `Path.rglob(..., recurse_symlinks=True)`. Without it, a
  symlinked test subtree is silently skipped — exactly the skipped-tree failure
  this gate exists to prevent.
- **`ast` discards comments.** For a comment-aware rule (e.g. "`# type: ignore`
  needs a justification"), use `tokenize` for the cheap case or **libcst** for
  the serious one. libcst is concrete-syntax, lossless, and has a codemod
  framework — which is also your **auto-fix** story.

### Coverage: the rule that keeps every gate reachable

Per-member gates create one new failure mode: **a member with no gate at all.**
`uv sync` succeeds, every gated member passes, CI is green — and every rule in the
library is silently optional for that tree. A recipe step cannot catch that, so it
is a rule, and it lives in the **library** because the property is the
*workspace's*, not one tree's. Reading the lockfile is *mechanics* and stays in
`_machinery.py`.

```python
# src/ironbox_conventions/workspace.py
from __future__ import annotations

from pathlib import Path

from ._machinery import (
    Rule,
    Violation,
    enclosing_workspace_directory,
    locked_member_directories,
)

CONVENTION_GATE_RELATIVE_PATH = Path("tests") / "architecture" / "test_conventions.py"


def members_carry_convention_gates() -> Rule:
    """Every uv workspace member must own the gate that runs these rules on it."""
    return Rule(
        description=(
            f"every uv workspace member must carry {CONVENTION_GATE_RELATIVE_PATH}; "
            "without it every rule here is silently optional for that member's tree"
        ),
        check=_check_every_member_carries_the_gate,
    )


def _check_every_member_carries_the_gate(package_directory: Path) -> list[Violation]:
    """Takes the caller's own package root, exactly like every other rule."""
    workspace_directory = enclosing_workspace_directory(package_directory)
    reporting_gate_path = package_directory / CONVENTION_GATE_RELATIVE_PATH
    return [
        Violation(
            reporting_gate_path,
            1,
            f"workspace member `{member_directory.relative_to(workspace_directory)}` "
            f"has no {CONVENTION_GATE_RELATIVE_PATH}; every rule here is silently "
            f"optional for that member until it does",
        )
        for member_directory in locked_member_directories(workspace_directory)
        if not (member_directory / CONVENTION_GATE_RELATIVE_PATH).is_file()
    ]
```

**Ask uv for its own member list; never infer one.** uv has no `cargo metadata`
equivalent (0.7.20 exposes no such subcommand), so its resolved view lives in
`uv.lock` — written there literally, as the member *names* under `[manifest]
members`. Source kinds are only the name → directory mapping, because inferring
membership *from* them over-fires: an out-of-glob path dependency that sets
`[tool.uv] package = false` also locks as `virtual`, and demanding a gate from a
directory that never receives the conventions package (no `workspace = true`
source reaches it) is a finding nobody can remediate. `editable = "."` is a root
with its own `[project]`, so that root is named in `members` and needs a gate too;
a *virtual* root has no `[project]` name, never appears in `members`, owns no
source tree, and needs none. **`[manifest]` is absent from the lockfile of a
single-package, non-workspace project, and may be present carrying only
`constraints`** — both raise, telling the reader to delete the call, because this
pattern supports single-package layouts and the alternative (treating the lone
package as the only member) would assert only that the file making the call has a
gate, which running it already proves: a pass carrying no information.

Be accurate about why the lockfile beats expanding the `[tool.uv.workspace]`
globs yourself: **uv does not promote path dependencies to members** — unlike
Cargo, whose promotion is exactly why the Rust rule *must* ask Cargo rather than
read the manifest — so glob expansion would also be correct here today. The
lockfile wins only because asking a tool for its own answer survives that tool
changing its rules.

**Every gate calls it with `package_root(__file__)`**, like every other rule; the
rule walks up to `uv.lock` itself. Do not expose a workspace-root helper for it:
two identically-shaped `*_root(__file__)` calls in one gate file are one
copy-paste from handing a *per-package* rule the workspace root, where it scans
`<workspace>/tests/**`, never sees the member's violating file, and passes
vacuously — and this rule's own remediation creates `<workspace>/tests/` in the
`editable = "."` topology. Deriving the root internally costs report precision:
the violation's path is the *reporting* member's gate, so an editor jump lands on
that file rather than the missing one, and the message names the absent sibling
instead. Every member reports the same finding, so each already owns "the
workspace is incomplete"; the standing cost is a TOML parse per member and one
failure reported N times. Its limit: it asserts the gate *file* exists, not that
the file calls every rule — a residue that stays a visible diff, and the reason
staged adoption below is legal.

**The rule needs the whole workspace tree on disk in every member's run.** A
narrowed per-member CI checkout or Docker context reports a correct lockfile as
stale, and a member-local `uv.lock` stops the upward walk at that member and
evaluates the wrong workspace — never commit one.

### Testing the rules

The conventions package needs its own tests, and they must build fixture trees
in `tmp_path` — **never commit deliberately-violating `.py` files**, which
would trip the package's own gate, ruff, and any type checker:

```python
# tests/test_layout.py
from pathlib import Path

import pytest

from ironbox_conventions import modules_contain_only_tests


def test_flags_module_scope_helper(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_thing.py").write_text(
        "def make_user():\n    return 1\n\n\ndef test_thing():\n    assert make_user()\n"
    )
    with pytest.raises(AssertionError, match="make_user"):
        modules_contain_only_tests().enforce(tmp_path)


def test_accepts_compliant_module(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_thing.py").write_text(
        "def test_thing(user):\n    assert user\n"
    )
    modules_contain_only_tests().enforce(tmp_path)
```

The coverage rule's fixture is a *workspace*: a hand-written `uv.lock` plus gate
files, enforced from a *member's* package root so the upward walk is exercised.
The lockfile literal stays inside the test body — a module-scope constant is
exactly what `modules_contain_only_tests()` flags, and this package runs its own
rules.

```python
# tests/test_workspace.py
from pathlib import Path

import pytest

from ironbox_conventions import members_carry_convention_gates


def test_flags_member_without_gate(tmp_path: Path) -> None:
    (tmp_path / "uv.lock").write_text(
        'version = 1\n'
        '[manifest]\nmembers = ["alpha", "gamma", "root"]\n'
        '[[package]]\nname = "root"\nsource = { editable = "." }\n'
        '[[package]]\nname = "alpha"\nsource = { editable = "packages/alpha" }\n'
        '[[package]]\nname = "gamma"\nsource = { virtual = "packages/gamma" }\n'
        '[[package]]\nname = "delta"\nsource = { virtual = "outside/delta" }\n'
        '[[package]]\nname = "beta"\nsource = { directory = "outside/beta" }\n'
        '[[package]]\nname = "pytest"\nsource = { registry = "https://pypi.org" }\n'
    )
    for member_relative_path in (
        "packages/alpha",
        "packages/gamma",
        "outside/delta",
        "outside/beta",
    ):
        (tmp_path / member_relative_path).mkdir(parents=True)
    for gated_relative_path in (".", "packages/alpha"):
        gate_directory = tmp_path / gated_relative_path / "tests" / "architecture"
        gate_directory.mkdir(parents=True)
        (gate_directory / "test_conventions.py").write_text("")
    with pytest.raises(AssertionError, match="packages/gamma"):
        members_carry_convention_gates().enforce(tmp_path / "packages" / "alpha")
```

The quiet direction writes the same lockfile and adds `packages/gamma`'s gate,
leaving `outside/delta` and `outside/beta` without one — so passing also proves
that neither a `directory` source nor an out-of-glob `virtual` one is treated as a
member. Three more tests forbid the vacuous passes, all `pytest.raises`: an empty
`tmp_path` → `RuntimeError, match="uv.lock"`; a lockfile with no `[manifest]` →
`RuntimeError, match="single-package"`; a `members` entry whose directory is
absent → `RuntimeError, match="stale"`.

Every rule gets both directions — it fires on the violation and stays quiet on
the compliant equivalent, including against a tree laid out exactly as your
testing convention prescribes, which is the cheapest way to catch over-firing.

## Production: shipping members that are not dev-only

The conventions package never ships. A shared *production* library does, and
the mechanism is a two-layer declaration:

```toml
[project]
dependencies = ["ironbox-shared>=0.1"]        # standard — SHIPS in wheel metadata

[tool.uv.sources]
ironbox-shared = { workspace = true }          # uv-only — resolution, not metadata
```

Wheel `METADATA` is generated from `[project]`, so a built wheel carries
exactly `Requires-Dist: ironbox-shared>=0.1` and no trace of the workspace
source. (The sdist still ships your `pyproject.toml`, `[tool.uv]` tables and
all — harmless, but it is why nothing is literally being removed.)

**Strategy 1 — container image, no publishing. The default for services.**
Copy the workspace into the build context and let uv install the sibling from
source; the root lockfile makes it reproducible.

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /bin/uv     # pin a version you verified
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0

# dependency layer — cached until a manifest or the lockfile moves.
# EVERY member manifest must be copied: uv cannot resolve the workspace without
# them, and `--locked` below will refuse to run. Add a member, add a line.
COPY pyproject.toml uv.lock ./
COPY packages/ironbox-conventions/pyproject.toml packages/ironbox-conventions/
COPY packages/ironbox-shared/pyproject.toml      packages/ironbox-shared/
COPY services/api/pyproject.toml                 services/api/
COPY services/worker/pyproject.toml              services/worker/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-workspace --package api

# source layer
COPY packages/ironbox-shared packages/ironbox-shared
COPY services/api            services/api
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable --package api

FROM python:3.13-slim
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0"]
```

Details that are easy to get wrong — confirm flag names against the uv version
you pin, as they have moved before:

- `--package api` selects the member to install.
- `--no-install-workspace` gives the cacheable dependency-only layer.
  `--no-install-project` skips only the root and still builds and installs
  siblings — the wrong flag in a workspace.
- **`--no-editable`** matters most. By default uv installs workspace members
  editable, so without it the image ships a path pointer into a discarded build
  stage instead of real code.
- **`--frozen` in the dependency layer, `--locked` in the source layer.**
  `--frozen` means "don't update the lock" and validates nothing — correct
  while member *sources* are still absent. `--locked` *asserts* the lock
  matches the manifests, which is what makes "reproducible" true. It needs
  every member's `pyproject.toml` present, which is why the dependency layer
  copies all of them: omit one and you get either
  `references a workspace in tool.uv.sources … but is not a workspace member`
  or `The lockfile at 'uv.lock' needs to be updated, but --locked was provided`.
- **Keep the builder and runtime bases identical** (both `python:3.13-slim`
  here). A copied `.venv` records its interpreter path in `pyvenv.cfg`; mixing
  a uv-provided builder image with a different runtime base works only by
  coincidence of layout and breaks silently on musl or a relocated interpreter.
- Add `.venv` to `.dockerignore`, or the host environment will be copied over
  the built one.

**Strategy 2 — publish to an index.** Only when consumers live in *other
repositories*: `uv build --package ironbox-shared` → private index
(Artifactory, devpi, GitHub/GitLab registry). Production then resolves normally
with no workspace involvement, at the cost of real release discipline — semver,
changelogs, cross-repo bump coordination. Inside one repo it buys nothing.

**Strategy 3 — build wheels, ship the files.** Middle ground for when an index
is unavailable but artifact separation is required. Awkward enough to reserve
for that specific constraint.

**Dev-only stays dev-only, structurally — and the guarantee is normative.**
PEP 735 (Final, 2024-10-10) states that build backends **MUST NOT** include
dependency-group data in built distributions as package metadata. Unlike
extras, groups simply do not exist in a wheel, so the conventions package
cannot leak into production even if someone installs the wheel directly;
`--no-dev` covers the container path. Two independent mechanisms, no special
handling needed. (The same PEP blesses the virtual root: a `pyproject.toml`
with only `[dependency-groups]` and no other tables is valid.)

**The one trap: a published wheel needs published dependencies.** Build and
publish `api` while `ironbox-shared` stays workspace-local, and the wheel is
*uninstallable* anywhere else — its metadata names a distribution no index has.
Path sources hide this inside the repo and it surfaces at the consumer. Publish
the whole dependency closure, or none of it.

**Corollary:** if you never publish, a member's version number is decorative.
Pin it at `0.1.0`, never touch it, and let the lockfile be the contract.

## Greenfield Recipe (commit 1 → first rule)

1. **Create the uv workspace.** Virtual root (`[tool.uv.workspace]`, no
   `[project]`), members under `packages/*` and `services/*`, one `uv.lock`.
   Give every depended-upon member an explicit `[build-system]`.
2. **Install tier 1 first — it is the biggest win per unit of effort.** Ruff
   config plus `import-linter` contracts in the root `pyproject.toml`
   (`layers` for the DDD stack, `forbidden` for a framework-free domain,
   `independence` for feature isolation, `acyclic_siblings` for cycles). See
   the `python-import-linter-setup` skill. Do this *before* writing any custom
   rule, or you will hand-roll something `grimp` already does better.
3. **Create `packages/<project>-conventions`** with `_machinery.py`, `py.typed`,
   and **exactly three coupled layout rules** — `modules_contain_only_tests()`,
   `module_filenames_follow_canonical_pattern()`, and
   `pytest_references_use_canonical_names()`. Together they enforce
   `python-testing` §7's contents and `test_*.py` filename surface while
   keeping pytest references syntactic rather than alias-resolved. Resist
   seeding any *additional* style rule; each one is code you own forever. No
   public name may start with `test`. Add `workspace.py` with
   `members_carry_convention_gates()` in the same commit (plus
   `enclosing_workspace_directory` and `locked_member_directories` in
   `_machinery.py`): it is not a style rule, so the restraint above does not
   cover it, and step 6 needs it. Export `package_root` and no other root helper.
4. **Give it its own `tmp_path` fixture tests**, both directions per rule, plus
   one fixture tree copied from your testing convention's own layout example
   that must produce **zero** violations. The coverage rule's fixture is a
   hand-written `uv.lock` plus gate files rather than a source tree.
5. **Wire every member**:
   `[dependency-groups] dev = [..., "<project>-conventions"]` plus
   `[tool.uv.sources] <project>-conventions = { workspace = true }`.
6. **Add the identical gate file** to every member under
   `tests/architecture/test_conventions.py` — including the conventions package
   itself, so it dogfoods — and have every one of them call the step-3 coverage
   rule, so the instruction is enforced rather than remembered. A member added a
   year later with no gate then fails every existing member's suite instead of
   passing unnoticed.
7. **Wire the runner and CI per member**: `cd <member> && uv run pytest`, one
   recipe and one CI job each, so a violation fails that member's own run.
   Never a single job that scans everything, and never `uv run --package X
   pytest` from the root — see the `--package` trap. The coverage rule guarantees
   every member *has* a gate; it cannot see whether CI invokes it, so generate
   this job list from `uv.lock` — or assert its length against the member count
   — instead of hand-maintaining it.
8. **Record an ADR** in `docs/decisions/`: the topology (rules as a library,
   enforcement per package), the zero-knob principle, the rejected alternatives
   (central scanner, per-package copies, frozen baselines), and — explicitly —
   that the rule set **grows one rule family at a time**. A tightly-coupled
   family such as test-module layout may need contents, filename, and canonical
   pytest-reference rules together; do not turn that into an excuse to codify
   the style guide.

The scope statement in step 8 is not boilerplate. The failure mode of a
conventions package is a big-bang attempt to codify an entire style guide,
producing brittle rules nobody trusts. Migrate a rule from prose to code when
it has *demonstrably* been violated and missed — with one day-1 exception, the
coverage rule, which ships unprovoked because it is what makes every other rule
reach every member, and because the Rust sibling's history already demonstrated
the gap it closes.

## Adopting on an Existing Codebase

1. **Write the rule and run it once — its failure output is the inventory.**
   The rule is its own audit tool; do not hand-count first.
2. **Separate true violations from over-firing before touching any code.** The
   first run of a new rule is as much a test of the rule as of the tree; a rule
   that flags a compliant layout must be fixed before the cleanup starts, or
   the cleanup will damage correct code.
3. **Triage by cluster** (per package, per test category) and remediate in
   batches, each verified independently.
4. **Land the rule and the cleanup together**, at zero violations. No
   allowlist, no baseline file, no frozen snapshot — those make "green" stop
   meaning "clean".
5. **A package that cannot be cleaned this cycle keeps its gate file and visibly
   omits the offending rule's call**, with a tracking note. The file is not
   optional — `members_carry_convention_gates()` requires it, and it calls that
   rule from day one — so adoption is staged one *call* at a time inside a gate
   that already exists. Never a silent exemption, never a deleted gate file.
6. **Expect the rule to find more than you predicted.** That number *is* the
   argument for mechanising it.

## Worked Example — provenance and honesty

This recipe is derived from a production Rust implementation and mapped to
Python; the mapping is a design, not a shipped codebase. Stated plainly so the
next reader calibrates correctly:

- **Battle-tested (Rust half, `ironbox`):** a `tests/structure` cargo-test gate
  grown over many rules, then an ADR ("per-crate convention enforcement via a
  shared rules crate") that extracted the mechanics into a dev-only workspace
  crate with zero-knob constructors and per-crate gates. The trigger was
  concrete: a single test-layout rule, written after the convention had lived in
  a skill file for months, found **477 violations across 143 files** on first
  run — in a codebase that had passed review throughout. Remediation ran in
  per-cluster batches to zero; a `syn`-based AST walk replaced an earlier text
  scan; an interim workspace-wide scanner was deliberately *retracted* in favour
  of per-crate gates so each crate owns its violations — with one exception kept
  in the library, the workspace-coverage rule, because gate presence is a property
  of the workspace. See the sibling [rust convention pattern](rust.md).
- **Mapped here (Python half):** the uv-workspace substrate, the tier ladder
  with `import-linter` absorbing tier 1, the `ast` rule implementation, and the
  production-packaging recipe. The topology and principles transfer unchanged;
  the tooling is entirely different, and the packaging caveats (single venv,
  unenforced dependency graph, the `--package` trap, publish-closure) are
  Python-specific additions with no Rust counterpart.
- **What has actually been executed, precisely:** the two `ast` modules, on
  CPython 3.13–3.14, against compliant and violating fixture trees including
  the layout `python-testing` prescribes; the gate file, under real pytest; the
  workspace and `uv sync` flag sequences, against a real multi-member uv
  workspace; and the coverage rule plus its fixture tests, on CPython 3.13
  against a `uv.lock` (`version = 1`, `revision = 2`) generated by uv 0.7.20 with
  an `editable = "."` root, an `editable` member, a `virtual` member, a `registry`
  dependency and two out-of-glob path dependencies — one `directory`, one
  `virtual`, the second of which a source-kind guess wrongly calls a member while
  `[manifest] members` correctly omits it. It fired on exactly the member without
  a gate, went silent once every member had one, and raised on every loud path (no
  lockfile above the caller; `[manifest]` absent, and present without `members`; a
  locked member directory absent from disk). What has *not*: this stack running in
  anger in a production repository. Verify against your tree.

The 477-violation number is the single most useful datum in this pattern: it is
what "the rule lives only in prose and reviewers keep missing it" costs, in one
codebase, for one rule.

## Quick Reference — Invariants

- **Rules are a library; enforcement is local.** Defined once in the
  conventions package, executed by every package against its own tree, from
  inside that package's directory — with exactly one exception, the coverage rule
  below, whose subject is the workspace rather than any one package's tree.
- **Every member carries the gate file** — the conventions package included — and
  a *rule* asserts it, not the recipe. It lives in the library because the
  property is the workspace's; it takes `package_root(__file__)` like every other
  rule and walks up to `uv.lock` itself; and it runs from every member's gate so
  no one member is load-bearing. Membership comes from **`[manifest] members`**,
  uv's own list — never inferred from source kinds, since an out-of-glob path
  dependency with `[tool.uv] package = false` also locks as `virtual`. The rule
  asserts the gate *file* exists, not that it calls every rule: an empty file
  satisfies it.
- **Machine-decidable rules never belong to review.** If it can be checked,
  check it.
- **No public name in the conventions package starts with `test`** — pytest
  would collect it as a phantom test in every gate file that imports it.
- **Import-shaped rules go to `import-linter`**, never to hand-rolled `ast`.
- **Universal rules are zero-knob.** Exemptions live in the rule's definition
  or at the exempted site — never in per-package configuration.
- **Scope by `python-testing`'s canonical naming discipline, not a path
  allowlist** — scan `test_*.py`, and flag pytest's alternative `*_test.py`
  form explicitly.
- **Whitelist what is allowed**, reject the rest, and recurse into every
  container you allow.
- **A rule that cannot fail is worse than no rule.** Vacuous passes (missing
  directory, skipped tree, swallowed parse error, unfindable or stale `uv.lock`)
  are defects — raise instead of returning an empty result.
- **A rule whose remediation is impossible is a defect too**, and teaches
  suppression.
- **The conventions package is a dev dependency group**, never a production
  dependency; PEP 735 makes that structural.
- **`[project.dependencies]` ships; `[tool.uv.sources]` does not.** Publish the
  whole dependency closure or none of it.
- **`--no-editable` in production images**, `--frozen` then `--locked`, every
  member manifest copied, identical builder and runtime bases.
- **Zero violations at landing.** No baselines, no allowlists, no freezes.
- **One rule at a time.** The package earns rules; it does not start with them —
  the coverage rule is the one stated day-1 exception, since it asserts that the
  other rules are reachable at all rather than adding a convention of its own.
- **Every rule is tested in both directions**, including against a tree laid
  out exactly as the convention prescribes.

## Anti-Patterns to Avoid

- **Leaving a critical rule in prose only.** The named failure mode. Prose
  rules are enforced by memory, and the violation rate is not the problem — the
  *survival* rate through review is.
- **A rule that contradicts the convention it claims to mechanise.** Transplant
  a rule's constants from another language's codebase and it will flag the
  layout your own guide mandates. Validate a new rule against the convention's
  own example tree before shipping it.
- **A central scanner that audits every package from one place.** Loses
  locality: a package's violation fails a sibling's suite (or only CI), and
  ownership becomes ambiguous. Its real advantage — no duplication — is not
  worth that. The coverage rule is not an exception to this: it inspects the
  *workspace's* shape (which members carry a gate), never a sibling's source,
  and a member cannot own the finding that it does not exist.
- **A member with no gate at all.** The most expensive hole, because it reads as
  coverage: everything passes while the whole rule set is optional for one tree.
  Close it with a rule, never with a line in the setup recipe.
- **Call-site knobs on universal rules.** Silent, invisible weakening. The gate
  stays green while the rule stops meaning the same thing.
- **Baseline / freeze files.** They rot, and they redefine "green" as "no worse
  than last year".
- **Rules in a root `conftest.py` instead of a package.** Unversioned,
  unshareable across repositories, and it puts policy in a fixture file.
- **Committing deliberately-violating fixture files** to test the rules — they
  trip the package's own gate. Build trees in `tmp_path`.
- **A rule whose remediation is impossible.** If the flagged construct cannot
  legally move (`pytestmark`, `pytest.importorskip`, module-level
  `pytest.skip`), the rule teaches suppression instead of compliance.
- **Reimplementing layering in `ast`** when `import-linter` expresses it
  declaratively and catches transitive cases.
- **Reaching for a mypy plugin** for a rule the declaration already answers.
- **`# noqa` / exemption sprawl** as the response to a rule firing. Fix the
  code, or change the rule in one place, deliberately.
- **Seeding the package with a whole style guide.** Brittle rules nobody
  trusts; each rule is permanent maintenance.

## Relationship to Other Patterns and Skills

- **[rust convention pattern](rust.md)** — the sibling implementation and the
  origin of this recipe (cargo workspace + `syn` + per-crate `tests/structure`).
- **`python-testing` (skill)** — the authority this pattern's first rule
  mechanises: test modules hold only tests, fixtures live in `conftest.py` at
  the narrowest scope, and every other support definition has a home under
  `utils/`. The rule's constants must track that skill, not the other way
  around.
- **`python-import-linter-setup` (skill)** — installs tier 1, the prerequisite
  step 2 of the greenfield recipe.
- **`python-ddd` (skill)** — supplies the layering and declaration-shape rules
  that become tier 1 contracts and tier 3 residents.
- **`python-structure-and-style-guard` (agent/skill)** — the advisory tier for
  judgment rules (naming intent, cohesion, placement quality) that must never
  be mechanised.
- **`greenfield-project-setup` (skill)** — sequences this pattern as a day-1
  phase so no later plan has to retrofit enforcement.
- **[docs artifact layout](../documentation/docs_artifact_layout_pattern.md)** —
  where the topology ADR from step 8 lives.
