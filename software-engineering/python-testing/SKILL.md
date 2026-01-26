---
name: python-testing
description: Python testing best practices using pytest with focus on clarity and maintainability
license: MIT
metadata:
  author: cristian.ciortea@proton.me
  version: "0.0.1"
---

# Python Testing Skill

Version: 0.0.1

## Purpose

This skill provides guidelines for writing effective Python tests using pytest. It focuses on clarity, maintainability, and business logic validation over implementation details.

## When to Apply

Apply these guidelines when:
- Writing or modifying Python unit tests
- Writing or modifying Python integration tests
- Writing or modifying Python e2e tests
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

## Anti-Patterns to Avoid

1. **Parametrized tests**: Using `pytest.mark.parametrize` instead of explicit test functions
2. **Class-level fixtures**: Defining fixtures inside test classes
3. **Scattered fixtures**: Fixtures in test files instead of `conftest.py`
4. **Testing logging**: Mocking or asserting on logger calls
5. **Function-level imports**: Importing inside test functions
6. **Docstrings in tests**: Adding docstrings or comments to test functions
7. **Testing timestamps**: Asserting exact timing instead of business outcomes

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
