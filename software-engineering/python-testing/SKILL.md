---
name: python-testing
description: Guidelines for writing effective Python tests with pytest. Use whenever writing, modifying, reviewing, or debugging Python tests — including adding test coverage for a new feature or bug fix, fixing a failing test, or setting up test infrastructure.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.8"
---

# Python Testing Skill

## Purpose

This skill provides guidelines for writing effective Python tests using pytest. It focuses on clarity, maintainability, and business logic validation over implementation details.

## When to Apply

Apply these guidelines when:
- Writing or modifying Python unit, integration, or e2e tests
- Adding test coverage for a new feature or bug fix
- Fixing or debugging a failing Python test
- Reviewing Python tests
- Setting up test infrastructure for new Python projects

## Core Principles

### 1. Mock at the HTTP Boundary (CRITICAL)

Simulate HTTP traffic at the transport layer instead of patching client code. Use `responses` for synchronous HTTP and `aioresponses` for async HTTP. For async callables that are not HTTP, use the standard library `unittest.mock.AsyncMock`; `aiomock` is acceptable only in projects that already use it. Never patch your own HTTP wrapper functions with plain `unittest.mock` when the request itself can be simulated.

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

Tests assert business outcomes, not implementation details. Exact timestamps and timing are not business requirements — never assert them; assert the observable outcome instead.

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

Use descriptive test names following the pattern: `test_<action>_<outcome>_<optional_case>`. The name alone should explain what is being tested.

```python
# Good examples
def test_do_periods_overlap_should_return_false_when_arguments_are_not_datetimes():
    ...

def test_upload_image_from_bytes_should_return_the_overwritten_public_url():
    ...

def test_calculate_total_returns_zero_for_empty_cart():
    ...
```

### 5. Organized Structure (HIGH)

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
└── calculations/
    └── test_money.py
```

### 6. Conftest Layering and Support Modules (HIGH)

Pytest's `conftest.py` hierarchy is the native mechanism for scoping test infrastructure. Each test category (`unit/`, `integration/`, `api/`) gets its own `conftest.py` with fixtures appropriate to that level. Infrastructure composes through fixture dependencies — not through imports from support modules.

Each `conftest.py` layer has a distinct responsibility:

| Layer | Concern | Typical fixtures |
|---|---|---|
| `tests/conftest.py` | Environment | DB engine, testcontainers, event loop (`autouse`, session-scoped) |
| `tests/unit/conftest.py` | Isolation | Fakes, in-memory adapters, patched dependencies |
| `tests/integration/conftest.py` | State | DB session, transaction rollback (`autouse`), seeding helpers |
| `tests/api/conftest.py` | HTTP | Test client, auth headers, request builders |

Every piece of test support code has exactly one home. This routing table is the single source of truth — the sections below refer back to it:

| Support need | Where it belongs |
|---|---|
| Pytest fixtures, setup/teardown, reusable seeded state | `conftest.py` |
| `factory_boy` factory declarations | `utils/factories.py` |
| Plain entity/DTO builder functions | `utils/builders.py` |
| DB query helpers, HTTP assertions, response assertions | `utils/helpers.py` |
| Constants and shared literals — even those used by a single test module | `utils/constants.py` |
| Example payloads, canonical sample records, sample files | `utils/samples.py` |

Each support module lives at the level where its contents are shared: `tests/utils/` for code used across categories, `tests/<category>/utils/` for category-specific code.

```
tests/
├── conftest.py              # Session-scoped: engine, testcontainers (autouse)
├── utils/
│   ├── helpers.py           # Shared assertion/query helpers
│   ├── factories.py         # factory_boy declarations shared across all tests
│   ├── builders.py          # Plain object/DTO builders shared across all tests
│   ├── constants.py         # Shared literals
│   └── samples.py           # Example payloads and canonical sample data
├── unit/
│   ├── conftest.py          # Fakes, in-memory adapters
│   ├── utils/
│   │   ├── builders.py      # Unit-specific builders
│   │   └── helpers.py       # Unit-specific assertions/helpers
│   └── services/
│       └── test_user_service.py
├── integration/
│   ├── conftest.py          # DB session, transaction rollback (autouse), seeders
│   ├── utils/
│   │   ├── factories.py     # Integration-specific factory_boy classes
│   │   ├── builders.py      # Integration-specific plain builders
│   │   └── helpers.py       # Integration-specific query/assertion helpers
│   └── infrastructure/
│       └── test_user_repository.py
└── api/
    ├── conftest.py          # Test client, auth headers
    ├── utils/
    │   ├── helpers.py       # Response assertion utilities
    │   ├── builders.py      # Request/body builders
    │   └── samples.py       # Example request/response payloads
    └── routes/
        └── test_users.py
```

Seeders that need fixture lifecycle are fixtures in `conftest.py` that compose other fixtures:

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

### 7. Test Modules Contain Only Tests (CRITICAL)

This is a separation-of-concerns rule: a test module declares scenarios; support code lives in the infrastructure designated for it. A test module (`test_*.py`) must **not** define anything except tests — no fixtures, no builder functions/classes, no `factory_boy` declarations, no mock/fake classes or prebuilt mock instances, no module-level helper functions (including private helpers named `_helper`, `_insert_*`, `_build_*`, `_count_*`, `_get_*`, etc.), and no module-level constants or data literals (payload dicts, sample records) — even when used only within that file. Fixtures in particular are never defined in test modules or inside test classes — they belong in `conftest.py` at the narrowest appropriate scope, and a test module consumes them by parameter name only. The only definitions in a `test_*.py` file are **tests**: functions whose names start with `test_`, and optional **test classes** grouping those methods.

Route every non-test definition to its home using the table in [Conftest Layering and Support Modules](#6-conftest-layering-and-support-modules-high).

Inline small setup inside a **single** test is allowed when it is not reused — express it in the test body, not as a separate named function in the module.

```python
# Bad - non-test definitions in test modules are forbidden
DEFAULT_JOB_PAYLOAD = {"type": "cleanup", "retries": 0}

@pytest.fixture
def seeded_job(db_session):
    ...

def _insert_jobs(session_maker, entities):
    ...

def _build_completed_job(job_id):
    ...

def test_cleanup_removes_old_jobs(mariadb_sync_session_maker):
    _insert_jobs(mariadb_sync_session_maker, [...])

# Good - fixtures in conftest.py, builders in utils/builders.py, helpers in utils/helpers.py, constants in utils/constants.py.
# test_job_retention_cleanup.py contains only Test* classes and test_* functions.
```

### 8. Minimal Test Bodies (HIGH)

The body of each `test_*` function should stay **short and readable**: arrange → act → assert should be obvious at a glance. Do **not** paste large entity/DTO constructors, repeated dict literals, or multi-field `Model(...)` calls inline — those obscure what behaviour is under test.

Extract setup data to builders, factories, or fixtures (routed per [Conftest Layering and Support Modules](#6-conftest-layering-and-support-modules-high)). Keep in the test body only the one-off values that clarify the scenario — the **distinctive** fields; defaults belong in a builder or factory.

```python
# Bad - twelve lines of Job(...) before the action under test; unreadable
def test_retention_removes_old_completed_jobs():
    old_job = Job(id=..., type="...", status=..., retries=0, config={}, ...)
    ...

# Good - intent visible; defaults live in builders/factories
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

- **Non-test definitions in test modules**: fixtures (including class-level fixtures), builders, factories, mocks, helpers, constants, or data literals defined in `test_*.py` — see [Test Modules Contain Only Tests](#7-test-modules-contain-only-tests-critical)
- **Parametrized tests**: using `pytest.mark.parametrize` instead of explicit test functions
- **Testing logging**: mocking or asserting on logger calls
- **Testing timestamps**: asserting exact timing instead of business outcomes
- **Docstrings in tests**: adding docstrings or comments to test functions
- **Function-level imports**: importing inside test functions
- **Bloated test bodies**: long entity/DTO/model literals inside `test_*` — see [Minimal Test Bodies](#8-minimal-test-bodies-high)

## Guidelines

- Use pytest exclusively for all tests
- Do not use the `@pytest.mark.asyncio` decorator — enable asyncio auto mode in `pyproject.toml`
- Use absolute imports only
- Do not reformat or restructure existing passing tests beyond what the current change requires
