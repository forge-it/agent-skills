---
name: python-code-style-v1
description: Defines code style conventions for Python. Use whenever writing, reviewing, refactoring, or fixing any Python code — implementing a feature, fixing a bug, writing or modifying tests, or making any other change to a .py file.
license: UNLICENSED
metadata:
  author: Cristian
  version: "1.1.0"
---

# Python Code Style Skill

House conventions for Python. Several rules deliberately differ from mainstream Python habits (no `-> None`, truthiness instead of `is None`, docstrings only where they add information) — follow them even when the wider ecosystem or your instinct says otherwise. Anything not covered here is left to your judgement: match the surrounding code.

Rule numbers and titles are stable identifiers — review agents and CI gates cite them. Never renumber; add new rules at the end.

## Rules

### 1. Descriptive Naming (CRITICAL)

Names reveal intent and are searchable. Never use single-letter names or abbreviations — not for variables, constants, parameters, loop variables, or comprehension variables. `elapsed_time_in_days`, not `t`.

### 2. Loop and Comprehension Variables (CRITICAL)

The collection name is the plural of the loop variable: `for compute_host in compute_hosts`, `[product for product in products if ...]`. When they don't match, rename the collection — never downgrade the loop variable to something generic.

### 3. Type Hints (CRITICAL)

Annotate all function parameters and return values — with one deviation from common style: functions that always return `None` get no return annotation at all. Never write `-> None`; do not "fix" its absence.

### 4. Truthy/Falsy Checks (CRITICAL)

Check for missing or empty values with truthiness (`if not product.company_id`), not explicit `None` comparison. Reserve `is None` for the rare case where `None` and a legitimate falsy value (`0`, `""`, an empty collection) must be told apart.

### 5. Google Style Docstrings (HIGH)

Docstrings use Google style, and exist only where they add information the signature cannot carry: the shape of a complex data structure, or a usage example on a public method. Never narrate what the code already says.

### 6. Constants at Module Top (HIGH)

Constants are `UPPERCASE_WITH_UNDERSCORES`, defined at the top of the module directly after the imports.

A literal value that appears in more than one place across the codebase must become a named constant defined once — in the module that owns the concept — and imported everywhere else. Never re-define the raw literal:

```python
# presentation/http.py — owns the concept, defines the constant
IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"

# presentation/routers/backups.py — imports it, never repeats the literal
from vulcan.presentation.http import IDEMPOTENCY_KEY_HEADER

idempotency_key = request.headers.get(IDEMPOTENCY_KEY_HEADER)
```

This covers *standalone* literals. When the literal is one alternative in a closed set — a status, kind, or mode — a family of constants is the wrong fix; the set becomes an enum (Rule 16).

### 7. Absolute Imports (HIGH)

Absolute imports only, always at module level — no relative imports, no function-level imports. If a function-level import seems necessary to break an import cycle, restructure the modules instead of hiding the import inside the function. Every new package gets an `__init__.py`.

### 8. Preserve Logical Blank Lines (HIGH)

Blank lines inside a function group related operations into logical sections. When editing or refactoring, preserve those groupings — never compact code by deleting them or merging sections.

### 9. No Single-Use One-Liner Helpers (HIGH)

A one-liner function or method called from exactly one place is indirection, not abstraction — inline it. One-liners earn their existence through reuse or by naming genuinely complex logic.

### 10. Tuples and Sets for Immutable Collections (HIGH)

Constant collections are never lists. Ordered data → tuple; uniqueness or membership testing → set.

### 11. DTOs for Dictionaries with More Than 3 Fields (CRITICAL)

Never pass or return a raw `dict` with more than 3 keys. Define a typed DTO instead — a dataclass for the simple case, `pydantic.BaseModel` when the data needs validation, `msgspec.Struct` when the path is serialization-heavy and performance-critical. The point is an explicit, IDE-visible data contract. A raw dict is acceptable only at the exact wire boundary where a library demands one — convert to and from the DTO immediately on either side.

### 12. Composition over Inheritance (CRITICAL)

Classes hold their dependencies explicitly; they don't inherit behaviour. Inheritance is reserved for true is-a relationships, such as framework base classes (`pydantic.BaseModel`). Never create a base class solely to share helper methods or common attributes between siblings — extract the shared logic into a module-level function that takes its collaborators as parameters:

```python
# Shared logic: a module-level function with an explicit collaborator...
def _resolve_node_model(node_model_repository: NodeModelRepository, name: str | None = None) -> NodeModel:
    return node_model_repository.find_by_name(name or DEFAULT_NODE_MODEL_NAME)

# ...and each of the sibling services (creation, editing) owns its dependencies — no base class
class DatacenterSettingsCreationService:
    def __init__(self):
        self._repository = DatacenterSettingsRepository()
        self._node_model_repository = NodeModelRepository()
```

### 13. Assert Statements Must Include Error Messages (CRITICAL)

Every `assert` carries a message describing what went wrong: `assert node_model, f"Node model '{model_name}' not found"`. A bare assert is useless in a production log.

### 14. Pathlib over os.path (HIGH)

All filesystem operations go through `pathlib.Path` — never `os.path`, `os.makedirs`, `os.remove`, `os.rename`, or bare `open()` for reading and writing files.

### 15. Minimal Comments (HIGH)

Comments exist only for what the code cannot say: a constraint, an invariant, a non-obvious why. Never comment what the code already says, and keep comments to a minimum overall.

### 16. Closed Sets Are Enums (CRITICAL)

When a value can only be one of a fixed set of alternatives — a status, kind, mode, state, direction, or unit — the set is an `enum.StrEnum` (`IntEnum` for numeric codes, plain `Enum` when the value is opaque). Never a `str` annotation with a family of sibling constants beside it (`BACKUP_STATUS_ACTIVE = "active"`, …), and never bare string literals compared inline. A constant family names each *value* but never the *set*: the annotation stays `str`, so a typo or a stale fourth value type-checks, and nothing points at the branches a new alternative must reach. Close every `match` on the set with `typing.assert_never` in a `case _:` arm — that arm is what turns an added member into a type-check failure.

```python
class BackupStatus(StrEnum):
    ACTIVE = "active"
    FAILED = "failed"
    ARCHIVED = "archived"

def retention_days(status: BackupStatus) -> int:
    match status:
        case BackupStatus.ACTIVE:
            return 30
        case BackupStatus.FAILED:
            return 7
        case BackupStatus.ARCHIVED:
            return 365
        case _:
            assert_never(status)             # a new member fails type-checking here
```

Compare with `==` (`status == BackupStatus.ARCHIVED`), never `is` and never `.value`. Members are strings, so they serialize as their value and pass anywhere a `str` is expected — but a value that arrived as a raw string (a plain text column, a JSON payload) is only *equal* to its member, never identical to it, so `is` fails silently and no type checker flags it. Coerce once at that boundary (`BackupStatus(raw_status)`) and pass members inward. Per-member behaviour belongs on the enum as a method or property, not in an `if` ladder repeated at each call site. `Literal["..."]` is acceptable only for a keyword argument that never leaves its own signature.

**Not applicable** when the set isn't closed — values come from a database table, a config file, or user input (tenant names, tag keys, a catalogue that grows) — or for a single standalone value with no siblings, which is a constant (Rule 6).
