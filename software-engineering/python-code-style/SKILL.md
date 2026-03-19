---
name: python-code-style
description: Defines code style conventions for Python. Use it when writing or reviewing Python code.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.9"
---

# Python Code Style Skill

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

Use descriptive, intent-revealing names. Good names show intent and are searchable. Never use single-letter variable or constant names, including in loops and comprehensions.

```python
# Bad
t = 30
d = {"n": "John", "a": 25}

# Good
elapsed_time_in_days = 30
user_data = {"name": "John", "age": 25}
```

### 2. Loop and Comprehension Variables (CRITICAL)

Never use single-letter variables in loops or comprehensions. Always use descriptive names that show intent.

The collection variable and the loop variable must be consistent: the collection must be the plural form of the loop variable. Never use a generic or mismatched name for the collection while using a specific name for the loop variable.

```python
# Bad - single-letter variables
[p for p in products if p.get("name") == target_name]
for i in items:
    process(i)

# Bad - collection name doesn't match loop variable
hosts = get_compute_hosts()
for compute_host in hosts:
    process(compute_host)

networks = get_network_cards()
for network_card in networks:
    process(network_card)

# Good - collection and loop variable are consistent
[product for product in products if product.get("name") == target_name]
for item in items:
    process(item)

compute_hosts = get_compute_hosts()
for compute_host in compute_hosts:
    process(compute_host)

network_cards = get_network_cards()
for network_card in network_cards:
    process(network_card)
```

### 3. Type Hints (CRITICAL)

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

### 4. Truthy/Falsy Checks (CRITICAL)

Prefer truthy/falsy checks over explicit `None` comparisons when checking for missing/empty values.

```python
# Bad
if product.company_id is None or product.user_id is None:
    raise ValueError("Missing required fields")

# Good
if not product.company_id or not product.user_id:
    raise ValueError("Missing required fields")
```

### 5. Google Style Docstrings (HIGH)

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

### 6. Constants at Module Top (HIGH)

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

Any literal value (string, number, etc.) that appears in more than one place across the codebase **must** be extracted into a named constant. Define the constant once in the module that owns the concept, then import it everywhere else. Never duplicate the raw literal.

```python
# Bad - same string defined independently in two modules
# startup/node_models.py
NODE_MODEL_CATALOG = (
    NodeModel(name="s1.medium", ...),
)

# services/datacenter_settings.py
DEFAULT_NODE_MODEL_NAME = "s1.medium"   # duplicate!

# Bad - same tuple of values repeated in test infra
# conftest.py
AVAILABLE_NAMES = ("s1.small", "s1.medium", "s1.large")   # duplicate!

# Good - single definition in the authoritative module
# startup/node_models.py
NODE_MODEL_NAME_SMALL = "s1.small"
NODE_MODEL_NAME_MEDIUM = "s1.medium"
NODE_MODEL_NAME_LARGE = "s1.large"

NODE_MODEL_CATALOG = (
    NodeModel(name=NODE_MODEL_NAME_SMALL, ...),
    NodeModel(name=NODE_MODEL_NAME_MEDIUM, ...),
    NodeModel(name=NODE_MODEL_NAME_LARGE, ...),
)

# services/datacenter_settings.py  — imports, never re-defines
from vulcan.infrastructure.startup.node_models import NODE_MODEL_NAME_MEDIUM

DEFAULT_NODE_MODEL_NAME = NODE_MODEL_NAME_MEDIUM

# conftest.py  — imports, never re-defines
from vulcan.infrastructure.startup.node_models import (
    NODE_MODEL_NAME_LARGE,
    NODE_MODEL_NAME_MEDIUM,
    NODE_MODEL_NAME_SMALL,
)

AVAILABLE_NAMES = (NODE_MODEL_NAME_SMALL, NODE_MODEL_NAME_MEDIUM, NODE_MODEL_NAME_LARGE)
```

### 7. Absolute Imports (HIGH)

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

### 8. Preserve Logical Blank Lines (HIGH)

Never remove blank lines that separate logical sections within functions. These blank lines are intentional and serve to visually group related operations. When refactoring or rewriting code, preserve the existing logical groupings.

```python
# Good - blank lines separate logical sections
def process_order(order: Order):
    # Validation section
    validate_order(order)
    check_inventory(order.items)

    # Processing section
    total = calculate_total(order.items)
    apply_discounts(order, total)

    # Persistence section
    save_order(order)
    send_confirmation(order.user_id)
```

### 9. No Single-Use One-Liner Helpers (HIGH)

Never create one-liner helper methods or functions that are only used in a single place. Inline the logic directly where it's needed. One-liner functions only make sense when reused in multiple places or when they provide meaningful abstraction for complex logic.

```python
# Bad - unnecessary one-liner helper used once
def get_user_name(user: User) -> str:
    return user.profile.display_name

def greet_user(user: User):
    name = get_user_name(user)
    print(f"Hello, {name}")

# Good - inline the logic
def greet_user(user: User):
    print(f"Hello, {user.profile.display_name}")
```

### 10. Tuples and Sets for Immutable Collections (HIGH)

Use tuples for ordered immutable collections and sets for unique immutable collections. Never use lists for constant data that will not be mutated. Lists are mutable, consume more memory, and carry the wrong semantic intent when the data is fixed.

```python
# Bad - list used for a constant collection of values
DOCKER_COMPOSE_SERVICES = ["postgres", "minio"]
SUPPORTED_FORMATS = ["pdf", "docx", "html"]

# Good - tuple signals immutability and is more efficient
DOCKER_COMPOSE_SERVICES = ("postgres", "minio")
SUPPORTED_FORMATS = ("pdf", "docx", "html")

# Good - set when uniqueness and membership testing matter
ALLOWED_ROLES = {"admin", "editor", "viewer"}
```

### 11. DTOs for Dictionaries with More Than 3 Fields (CRITICAL)

Never return or pass raw dictionaries with more than 3 key-value pairs. Define a dataclass DTO instead foor simple cases or msgspec.Struct for performance-critical (serialization-heavy). This enforces type safety, enables IDE support, and makes the data contract explicit.

```python
# Bad - raw dict with more than 3 fields
def build_payment(raw: dict) -> dict:
    return {
        "payment_type": "tax",
        "recipient_name": raw["beneficiary"],
        "recipient_iban": raw["iban"],
        "amount": float(raw["amount"]),
        "currency": "RON",
        "reference": raw["name"],
    }

# Good - DTO with typed fields
from pydantic import BaseModel

class ScrapedPayment(BaseModel):
    payment_type: str
    recipient_name: str
    recipient_iban: str
    amount: float
    currency: str
    reference: str

def build_payment(raw: dict) -> ScrapedPayment:
    return ScrapedPayment(
        payment_type="tax",
        recipient_name=raw["beneficiary"],
        recipient_iban=raw["iban"],
        amount=float(raw["amount"]),
        currency="RON",
        reference=raw["name"],
    )
```

### 12. Composition over Inheritance (CRITICAL)

Prefer composing objects by holding explicit dependencies rather than inheriting from a base class. Inheritance couples classes tightly and hides where behaviour comes from. Shared logic should live in module-level functions (when stateless) or be injected as a dependency.

Only use inheritance for true is-a relationships (e.g. a framework base class like `pydantic.BaseModel`). Never create a base class solely to share helper methods or common instance attributes between sibling classes.

When shared helpers depend on a repository or other collaborator, extract them as module-level functions that accept the collaborator as an explicit parameter.

```python
# Bad - base class exists only to share helpers between siblings
class BaseDatacenterSettingsService:
    def __init__(self):
        self._node_model_repository = NodeModelRepository()

    def _resolve_node_model(self, name: str | None = None) -> NodeModel:
        model_name = name or DEFAULT_NODE_MODEL_NAME
        return self._node_model_repository.find_by_name(model_name)

class DatacenterSettingsCreationService(BaseDatacenterSettingsService):
    def __init__(self):
        super().__init__()
        self._repository = DatacenterSettingsRepository()

class DatacenterSettingsEditingService(BaseDatacenterSettingsService):
    def __init__(self):
        super().__init__()
        self._repository = DatacenterSettingsRepository()

# Good - shared logic is a module-level function; each service owns its dependencies
def _resolve_node_model(node_model_repository: NodeModelRepository, name: str | None = None) -> NodeModel:
    model_name = name or DEFAULT_NODE_MODEL_NAME
    return node_model_repository.find_by_name(model_name)

class DatacenterSettingsCreationService:
    def __init__(self):
        self._repository = DatacenterSettingsRepository()
        self._node_model_repository = NodeModelRepository()

class DatacenterSettingsEditingService:
    def __init__(self):
        self._repository = DatacenterSettingsRepository()
        self._node_model_repository = NodeModelRepository()
```

### 13. Assert Statements Must Include Error Messages (CRITICAL)

Every `assert` statement must include a descriptive error message. A bare `assert` without a message produces an unhelpful `AssertionError` with no context when it triggers.

```python
# Bad - no message, useless in production logs
assert node_model is not None
assert len(items) > 0

# Good - descriptive message explains what went wrong
assert node_model is not None, f"Node model '{model_name}' not found"
assert len(items) > 0, "Expected at least one item in the collection"
```

### 14. Pathlib over os.path (HIGH)

Always prefer `pathlib.Path` over `os.path`, `os.makedirs`, `os.remove`, `os.rename`, `os.rmdir`, and manual `open()` for file read/write. Pathlib provides a cleaner, object-oriented API for filesystem operations.

```python
# Bad - os.path and os module functions
import os

os.makedirs("/tmp/cache", exist_ok=True)
config_path = os.path.join("/tmp/cache", "config.yaml")
if os.path.exists(config_path):
    with open(config_path) as config_file:
        content = config_file.read()
os.remove(config_path)

# Good - pathlib
from pathlib import Path

cache_dir = Path("/tmp/cache")
cache_dir.mkdir(parents=True, exist_ok=True)
config_path = cache_dir / "config.yaml"
if config_path.exists():
    content = config_path.read_text()
config_path.unlink(missing_ok=True)
```

## Anti-Patterns to Avoid

1. **Single-letter variables**: Using `x`, `i`, `p` instead of descriptive names
2. **Mismatched collection/loop names**: Using a generic collection name (e.g., `hosts`) with a specific loop variable (e.g., `compute_host`) — the collection must be the plural of the loop variable (e.g., `compute_hosts`)
3. **Redundant None returns**: Adding `-> None` to void functions
4. **Explicit None checks**: Using `is None` when truthy/falsy works
5. **Relative imports**: Using `.` or `..` in imports
6. **Function-level imports**: Importing inside functions
7. **Excessive comments**: Adding comments for self-explanatory code
8. **Lists for immutable data**: Using a list for any constant or immutable collection instead of a tuple (ordered) or set (unique)
9. **Removing logical blank lines**: Deleting blank lines that separate code sections
10. **Single-use one-liner helpers**: Creating helper functions used only once
11. **os.path over pathlib**: Using `os.path`, `os.makedirs`, `os.remove` instead of `pathlib.Path`
12. **Bare asserts**: Using `assert` without an error message — always include a descriptive string
13. **Raw dicts with more than 3 fields**: Passing or returning `dict` with more than 3 keys instead of a typed dataclass DTO
14. **Duplicate literal values**: Defining the same string, number, or tuple literal in more than one place instead of extracting it into a named constant in the authoritative module and importing it everywhere
15. **Inheritance for shared helpers**: Creating a base class solely to share helper methods or common attributes between sibling classes — use module-level functions and direct dependency ownership instead

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
- Use tuples for ordered immutable collections, sets for unique immutable collections — never lists for constant data
- Use `pathlib.Path` for all filesystem operations — never `os.path`, `os.makedirs`, `os.remove`, `os.rename`
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
