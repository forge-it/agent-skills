---
name: python-code-style
description: Python code style guidelines for clean, maintainable, and readable code
license: MIT
metadata:
  author: cristian.ciortea@proton.me
  version: "0.0.1"
---

# Python Code Style Skill

Version: 0.0.1

## Purpose

This skill provides guidelines for writing clean, maintainable, and readable Python code. It focuses on type hints, naming conventions, code organization, and consistent style.

## When to Apply

Apply these guidelines when:
- Creating new Python code
- Updating existing Python code
- Reviewing Python code
- Refactoring Python modules

## Core Principles

### 1. Descriptive Naming (CRITICAL)

Use descriptive, intent-revealing names. Good names show intent and are searchable. Never use single-letter variable or constant names.

```python
# Bad
t = 30
d = {"n": "John", "a": 25}
[p for p in products if p.get("name") == target_name]

# Good
elapsed_time_in_days = 30
user_data = {"name": "John", "age": 25}
[product for product in products if product.get("name") == target_name]
```

### 2. Type Hints (CRITICAL)

Use type hints to describe function parameters and return values. Never add the `-> None` return type hint to functions that always return `None`.

```python
# Bad - redundant None return type
def process_user(user_id: int) -> None:
    send_notification(user_id)

# Good - no redundant return type
def process_user(user_id: int):
    send_notification(user_id)

# Good - meaningful return type
def get_user(user_id: int) -> User:
    return User.objects.get(id=user_id)
```

### 3. Truthy/Falsy Checks (CRITICAL)

Prefer truthy/falsy checks over explicit `None` comparisons when checking for missing/empty values.

```python
# Bad
if product.company_id is None or product.user_id is None:
    raise ValueError("Missing required fields")

# Good
if not product.company_id or not product.user_id:
    raise ValueError("Missing required fields")
```

### 4. Google Style Docstrings (HIGH)

When writing docstrings, use Google style. Use docstrings only to describe complex data structures or provide usage examples for public methods.

```python
def process_order(order_data: dict) -> dict:
    """Process an order and return the result.
    
    Args:
        order_data: Order information containing:
            - user_id (int): The customer's ID
            - items (list[dict]): List of items, each with:
                - product_id (int): Product identifier
                - quantity (int): Number of items
            - shipping_address (str): Delivery address
    
    Returns:
        dict: Processing result containing:
            - order_id (int): Generated order ID
            - status (str): One of "pending", "confirmed", "failed"
            - total_cents (int): Total price in cents
    
    Example:
        >>> result = process_order({"user_id": 1, "items": [{"product_id": 10, "quantity": 2}]})
        >>> print(result["status"])
        "confirmed"
    """
```

### 5. Constants at Module Top (HIGH)

Define constants using UPPERCASE_WITH_UNDERSCORES. Place all constants at the top of the module immediately after import statements.

```python
import os
from datetime import datetime

API_BASE_URL = "https://api.example.com/v1"
MAX_RETRY_ATTEMPTS = 3
DEFAULT_TIMEOUT_SECONDS = 30

def make_request(endpoint: str):
    ...
```

### 6. Absolute Imports (HIGH)

Never use relative imports. Always use absolute imports. Never use function-level imports.

```python
# Bad - relative import
from .utils import helper
from ..models import User

# Bad - function-level import
def process():
    from myapp.utils import helper
    helper.do_something()

# Good - absolute import at module level
from myapp.utils import helper
from myapp.models import User
```

## Anti-Patterns to Avoid

1. **Single-letter variables**: Using `x`, `i`, `p` instead of descriptive names
2. **Redundant None returns**: Adding `-> None` to void functions
3. **Explicit None checks**: Using `is None` when truthy/falsy works
4. **Relative imports**: Using `.` or `..` in imports
5. **Function-level imports**: Importing inside functions
6. **Excessive comments**: Adding comments for self-explanatory code
7. **Lists for immutable data**: Using lists when tuples or sets are appropriate

## Guidelines

### Type Hints and Documentation
- Use type hints for function parameters and return values
- Never add `-> None` return type hint
- Use Google style docstrings
- Document complex data structures in docstrings
- Provide usage examples for public methods

### Naming
- Use descriptive, intent-revealing names
- Use searchable names (no single letters)
- Use UPPERCASE_WITH_UNDERSCORES for constants
- Use descriptive names in loops and comprehensions

### Code Organization
- Keep comments to a minimum
- Use tuples or sets instead of lists for immutable/unique data
- Use absolute imports only
- No function-level imports
- Group imports: stdlib, third-party, local (with blank lines between)
- Always create `__init__.py` for new packages

### Import Order
```python
# Standard library imports
import os
import sys
from datetime import datetime

# Third-party imports
import requests
from pydantic import BaseModel

# Local application imports
from myapp.models import User
from myapp.utils import helper
```

### Conditionals
- Prefer truthy/falsy checks over explicit None comparisons
- Use `if not value` instead of `if value is None`
