---
name: python-testing
description: Guidelines for writing effective Python tests with pytest. Use whenever writing, modifying, reviewing, or debugging Python tests — including adding test coverage for a new feature or bug fix, fixing a failing test, or setting up test infrastructure.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.6"
---

# Python Testing Skill

## Purpose

This skill provides guidelines for writing effective Python tests using pytest. It focuses on clarity, maintainability, and business logic validation over implementation details.

## When to Apply

Apply these guidelines when:
- Writing or modifying Python unit tests
- Writing or modifying Python integration tests
- Writing or modifying Python e2e tests
- Adding test coverage for a new feature or bug fix
- Fixing or debugging a failing Python test
- Reviewing Python tests
- Setting up test infrastructure for new Python projects

## Core Principles

### 1. Sophisticated Mocking (CRITICAL)

Use sophisticated mocking libraries like `responses`, `aioresponses`, or `aiomock` to simulate requests. Prioritize these complex mocking solutions over simple `unittest.mock`.

```python
import responses

@responses.activate
def test_fetch_user_returns_user_data():
    responses.add(
        responses.GET,
        "https://api.example.com/users/123",
        json={"id": 123, "name": "John"},
        status=200,
    )
    
    result = fetch_user(123)
    
    assert result["name"] == "John"
```

### 2. Business Logic Focus (CRITICAL)

Tests should focus on business logic rather than exact timing or implementation details. Exact timestamps are not important for business requirements.

### 3. No Parametrize (CRITICAL)

Avoid `pytest.mark.parametrize` entirely. It obscures what is being tested and reduces code clarity. Always favor individual test functions over parametrization.

```python
# Bad - obscures test intent
@pytest.mark.parametrize("input,expected", [(1, 2), (2, 4), (3, 6)])
def test_double(input, expected):
    assert double(input) == expected

# Good - clear and explicit
def test_double_returns_two_for_one():
    assert double(1) == 2

def test_double_returns_four_for_two():
    assert double(2) == 4

def test_double_returns_six_for_three():
    assert double(3) == 6
```

### 4. Descriptive Naming (HIGH)

Use descriptive test names following the pattern: `test_<action>_<outcome>_<optional_case>`

```python
# Good examples
def test_do_periods_overlap_should_return_false_when_arguments_are_not_datetimes():
    ...

def test_upload_image_from_bytes_should_return_the_overwritten_public_url():
    ...

def test_calculate_total_returns_zero_for_empty_cart():
    ...
```

### 5. Module-Level Fixtures (HIGH)

Always define pytest fixtures at module level, never as class-level fixtures. Prefer defining fixtures in `conftest.py` rather than in individual test files.

```python
# conftest.py
import pytest

@pytest.fixture
def authenticated_user():
    return User(id=1, name="Test User", authenticated=True)

@pytest.fixture
def sample_product():
    return Product(id=1, name="Widget", price=1999)
```

### 6. Organized Structure (HIGH)

- Each class method or function gets its own dedicated test class
- Each class gets its own dedicated test module
- Each module gets its own dedicated test directory

```
tests/
├── services/
│   ├── test_user_service.py
│   │   ├── TestGetUser
│   │   ├── TestCreateUser
│   │   └── TestDeleteUser
│   └── test_order_service.py
└── utils/
    └── test_helpers.py
```

### 7. The Conftest Layering Pattern (HIGH)

Pytest's `conftest.py` hierarchy is the native mechanism for scoping test infrastructure. Each test category (`unit/`, `integration/`, `api/`) gets its own `conftest.py` with fixtures appropriate to that level. Infrastructure composes through fixture dependencies — not through imports from support modules.

Each `conftest.py` layer has a distinct responsibility:

| Layer | Concern | Typical fixtures |
|---|---|---|
| `tests/conftest.py` | Environment | DB engine, testcontainers, event loop (`autouse`, session-scoped) |
| `tests/unit/conftest.py` | Isolation | Fakes, in-memory adapters, patched dependencies |
| `tests/integration/conftest.py` | State | DB session, transaction rollback (`autouse`), seeding helpers |
| `tests/api/conftest.py` | HTTP | Test client, auth headers, request builders |

Data shapes use `factory_boy` — declare factory classes in a `factories.py` at the appropriate level:

```
tests/
├── conftest.py              # Session-scoped: engine, testcontainers (autouse)
├── factories.py             # factory_boy declarations shared across all tests
├── unit/
│   ├── conftest.py          # Fakes, in-memory adapters
│   └── services/
│       └── test_user_service.py
├── integration/
│   ├── conftest.py          # DB session, transaction rollback (autouse), seeders
│   ├── factories.py         # Integration-specific factory_boy classes
│   └── infrastructure/
│       └── test_user_repository.py
└── api/
    ├── conftest.py          # Test client, auth headers
    ├── helpers.py           # Response assertion utilities
    └── routes/
        └── test_users.py
```

Seeders and builders are fixtures in `conftest.py` that compose other fixtures — not standalone modules:

```python
# tests/integration/conftest.py

@pytest.fixture(autouse=True)
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    transaction.rollback()
    connection.close()

@pytest.fixture
def seeded_user(db_session, user_factory):
    user = user_factory.create()
    db_session.add(user)
    db_session.flush()
    return user
```

Only things that are **not** fixtures belong in standalone modules: assertion helpers (`helpers.py`), shared constants (`constants.py`), and factory declarations (`factories.py`).

### 8. Test Modules Contain Only Tests (CRITICAL)

A test module (`test_*.py`) must **not** define module-level helper functions (including private helpers named `_helper`, `_insert_*`, `_build_*`, `_count_*`, `_get_*`, etc.). The only callable definitions in that file should be **tests**: functions whose names start with `test_`, and optional **test classes** grouping those methods.

Put shared logic elsewhere:

| Need | Where it belongs |
|---|---|
| Setup/teardown or reusable seeded state | **Fixtures** in the appropriate layer `conftest.py` |
| DB queries, HTTP assertions, builders used across files | **`helpers.py`** next to that test category (e.g. `tests/integration/helpers.py`) |
| `factory_boy` models | **`factories.py`** at that level |
| Shared literals used in many tests | **`constants.py`** at that level |
| Verbose entity/DTO setup obscuring the scenario | **Factory functions** in `helpers.py` / **`factories.py`**, or **`conftest.py` fixtures** — keep `test_*` bodies minimal (see [Minimal test bodies](#9-minimal-test-bodies-high)) |

Inline small setup inside a **single** test is allowed when it is not reused—express it in the test body, not as a separate named function in the module.

```python
# Bad - helper function defined in test module (forbidden)
def _insert_jobs(session_maker, entities):
    ...

def test_cleanup_removes_old_jobs(mariadb_sync_session_maker):
    _insert_jobs(mariadb_sync_session_maker, [...])

# Good - fixture in conftest.py or helper in tests/integration/helpers.py
# test_job_retention_cleanup.py contains only Test* classes and test_* functions
```

### 9. Minimal test bodies (HIGH)

The body of each `test_*` function should stay **short and readable**: arrange → act → assert should be obvious at a glance. Do **not** paste large entity/DTO constructors, repeated dict literals, or multi-field `Model(...)` calls inline—those obscure what behaviour is under test.

Extract setup data to:

| Situation | Prefer |
|---|---|
| Same shape reused across tests | **Factory functions** in `helpers.py` or **`factories.py`** (`factory_boy` when appropriate) |
| Shared lifecycle or DB seeding | **`conftest.py` fixtures** that yield ready-made entities or ids |
| One-off values that clarify the scenario only | Keep in the test, but keep **only** the distinctive fields—defaults belong in a factory |

```python
# Bad - twelve lines of Job(...) before the action under test; unreadable
def test_retention_removes_old_completed_jobs():
    old_job = Job(id=..., type="...", status=..., retries=0, config={}, ...)
    ...

# Good - intent visible; defaults live in helpers
def test_retention_removes_old_completed_jobs(mariadb_sync_session_maker, svc):
    base_time = get_current_datetime()
    cutoff_old = base_time - timedelta(days=61)
    insert_job_entities_sync(
        mariadb_sync_session_maker,
        [
            build_completed_job("job-old", cutoff_old),
            build_completed_job("job-recent", base_time - timedelta(days=30)),
        ],
    )
    svc.run_daily_retention_cleanup()
    assert get_job_by_id_sync(mariadb_sync_session_maker, "job-old") is None
```

## Anti-Patterns to Avoid

1. **Helper functions in test modules**: Defining any non-test callable at module scope in `test_*.py` (move to `conftest.py` fixtures, `helpers.py`, or `factories.py`)
2. **Parametrized tests**: Using `pytest.mark.parametrize` instead of explicit test functions
3. **Class-level fixtures**: Defining fixtures inside test classes
4. **Scattered fixtures**: Fixtures in test files instead of `conftest.py`
5. **Testing logging**: Mocking or asserting on logger calls
6. **Function-level imports**: Importing inside test functions
7. **Docstrings in tests**: Adding docstrings or comments to test functions
8. **Testing timestamps**: Asserting exact timing instead of business outcomes
9. **Bloated test bodies**: Many lines of entity/DTO/model literals or repetitive field lists inside `test_*` — use fixtures, factory functions in `helpers.py`, or `factories.py` so the test shows *what differs* for this scenario, not every default field

## Guidelines

### Test Framework
- Use pytest exclusively for all tests
- Do not use the `@pytest.mark.asyncio` decorator (use automatic option in `pyproject.toml`)

### Mocking
- Use `responses` for HTTP mocking
- Use `aioresponses` for async HTTP mocking
- Use `aiomock` for async mocking

### Structure
- One test class per function/method being tested
- One test module per class being tested
- One test directory per module being tested
- Define all fixtures in `conftest.py`
- Test modules contain **only** test classes and `test_*` functions—no module-level helper functions (see [Test Modules Contain Only Tests](#8-test-modules-contain-only-tests-critical))
- Each `test_*` body stays **minimal**: no long entity literals—use factories/fixtures (see [Minimal test bodies](#9-minimal-test-bodies-high))

### Naming
- Pattern: `test_<action>_<outcome>_<optional_case>`
- Be descriptive and explicit
- Name should explain what is being tested

### Preservation
- Never modify the format or logic of existing tests
- Never test logging statements

### Imports
- Never use function-level imports in tests
- Use absolute imports only
