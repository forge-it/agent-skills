---
name: python-ddd
description: Opinionated guidelines for structuring Python business applications using Evans-style layered Domain-Driven Design (presentation, application, domain, infrastructure). Builds on pure dataclass domain models, classical (imperative) SQLAlchemy mapping, per-concept repositories defined as ports in the domain, and a Unit-of-Work transaction boundary with explicit typed repository attributes and explicit commit. Use when building Python web services, APIs, or backend applications with business rules, external integrations, and persistence. Not applicable for scripts, CLIs, or single-purpose utilities without meaningful business logic.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.5"
---

# Python Domain-Driven Design Skill

## Purpose

This skill provides opinionated guidelines for organising Python business applications around a pure, framework-free domain, persisted through classical SQLAlchemy mapping and bounded by an explicit Unit of Work. It bundles two related concerns: Evans' layered architecture that decides *which* layer contains *what*, and the project structure conventions that decide *how* those layers are organised on disk. The goal is testable, evolvable code in which the domain is plain Python, persistence is swappable, and transactions are explicit.

The two driving principles, repeated throughout: **Separation of Concerns** (each module has one reason to exist) and **Single Responsibility** (each class, function, or file does one job). Every structural rule below ultimately reduces to one of these two.

## Architectural Model: Evans' Layered DDD (Not Ports & Adapters)

This skill follows **Evans' classic layered Domain-Driven Design**, deliberately *not* Cockburn's hexagonal (ports & adapters) model. Commit to this model; do not import hexagonal vocabulary into a Python service here.

- **Four layers, top-to-bottom: `presentation` → `application` → `domain` → `infrastructure`.** Dependencies point strictly inward (principle 1); the domain depends on nothing.
- **The presentation tier is first-class, not an adapter.** FastAPI routers, request/response schemas, and schema↔domain mappers all live in `presentation/` — never as an "inbound adapter." This is the deliberate difference from the Rust services here (which treat the API as a driving adapter).
- **Persistence lives in `infrastructure/`.** ORM tables, mapper registration, concrete repositories, the concrete Unit of Work, gateways, session factories, and config are all infrastructure. There is **no separate `adapters/` layer**.
- **Repository interfaces stay in `domain/`** — Evans' Repository pattern (dependency inversion): the abstract repository and abstract Unit of Work are ports in `domain/`; their concrete implementations live in `infrastructure/`, so persistence stays swappable and the domain never imports SQLAlchemy.

**Greenfield only — do not refactor existing projects.** Apply this canonical four-layer structure to *new* projects. An existing service that uses a different split (e.g. separate `api/`, `presentation/`, and `adapters/` layers) is left as-is: match the structure already in the repository rather than restructuring it. Consistency within a codebase beats conformance to this skill.

Rust services in this codebase use Cockburn's ports & adapters instead — see the `rust-hexagonal-architecture` skill. Coming from that model, translate: **"inbound adapter" → "presentation layer"**, **"outbound adapter" → "infrastructure layer"**.

## When to Apply

Apply these guidelines when:
- Building FastAPI (or similar) web services with non-trivial business rules
- Creating Python applications with multiple external integrations (relational databases, MongoDB, message brokers, third-party APIs)
- Designing systems where persistence or transport may be swapped over time
- Working on multi-developer projects requiring clear boundaries
- Building applications expected to evolve over months or years

## When NOT to Apply

Do not apply these guidelines when:
- Writing CLI tools, scripts, or one-shot utilities
- Building thin CRUD services with no business rules (the layers add overhead without benefit)
- Building solo prototypes where abstraction cost outweighs clarity gain
- Working inside performance-critical paths where mapping overhead is measurable

## Opinionated Choices (Read First)

This skill makes the following choices for you. They are non-negotiable inside the skill — pick a different skill if you want something else:

1. **Domain models are plain dataclasses.** Not Pydantic. Not SQLAlchemy `DeclarativeBase` subclasses. Pure `@dataclass` types with field defaults and value-validating constructors when needed.
2. **Persistence uses SQLAlchemy classical (imperative) mapping.** Tables are declared separately from domain classes, and `mapper_registry.map_imperatively(...)` attaches the table to the dataclass. The domain class stays plain `@dataclass` at the type level; at runtime SQLAlchemy gives it persistence machinery.
3. **There is exactly one model per concept.** No `OrderDbModel` shadowing `Order`. The dataclass *is* both the domain model and the persisted entity, because the imperative mapping leaves the dataclass otherwise untouched.
4. **Repositories are ports defined in the domain, with one abstract class per concept.** Each abstract repository exposes **only** the methods the domain actually needs (`add`, `get`, `find_by_serial_number`, ...) — no generic `get_with_limit_and_offset` or `get_by_fields(dict)` god-methods. Concrete implementations live in `infrastructure/repository/<concept>.py`.
5. **Transactions are owned by a Unit of Work with explicit typed repository attributes.** A service writes `unit_of_work.products.add(product)` — not `unit_of_work.get_repository(Product).add(...)`. The UoW class declares each repository as a typed attribute, and `__aenter__` constructs them against the shared session.
6. **Commit is explicit; rollback is the default on exit.** The application code must call `await unit_of_work.commit()` for the transaction to persist. `__aexit__` rolls back unconditionally — committed transactions are unaffected; uncommitted ones are discarded. This makes the success path visible at every call site.
7. **There are four layers — `presentation/`, `application/`, `domain/`, `infrastructure/` — and persistence implementations live in `infrastructure/`.** ORM tables, imperative mapper registration, repository implementations, and the concrete Unit of Work are all infrastructure, alongside config, session factories, and gateways. Repository and Unit-of-Work *interfaces* (ports) stay in `domain/`. There is no separate `adapters/` layer. (Greenfield only — existing projects keep their current layout; see "Architectural Model".)
8. **Routers are thin.** Validation, orchestration, and persistence happen below. FastAPI handlers translate HTTP to commands/services and translate domain results back to schemas.

If any of these is wrong for your project, you should either override it in a project-local CLAUDE.md (and explain why) or choose a different architecture skill.

## Core Architectural Principles

### 1. Layered Architecture With Inward-Only Dependencies (CRITICAL)

The application is organised into four layers. Dependencies only point inward: the domain knows nothing about anything else; application knows the domain; presentation knows application and domain; infrastructure implements the domain's ports and may use anything.

```
┌────────────────────────────────────────────────────────────────────┐
│                            presentation                             │
│       (FastAPI routers, request/response schemas, schema↔domain     │
│                               mappers)                              │
│                                  │                                  │
│                                  ▼                                  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                         application                           │  │
│  │     (services, command handlers, validators, DTOs, mappers)   │  │
│  │                                │                              │  │
│  │                                ▼                              │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │                         domain                          │  │  │
│  │  │   (entities, value objects, repository + UoW ports,     │  │  │
│  │  │    commands, domain services, validations, exceptions)  │  │  │
│  │  │                 NO EXTERNAL DEPENDENCIES                │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│                          infrastructure                             │
│    (ORM tables + mappers, concrete repositories, concrete UoW,      │
│     session factories, gateways, config, jobs, startup, logging)    │
└────────────────────────────────────────────────────────────────────┘
```

| Layer | May import from |
|-------|-----------------|
| `presentation` | `application`, `domain`, Pydantic, FastAPI |
| `application` | `domain` (ports, models, exceptions), `infrastructure` (only the concrete UoW/repository types used as default-argument values), and pure libraries |
| `domain` | Only `domain` and the standard library / pure libraries (dateutil, decimal, `abc`, dataclasses, typing) |
| `infrastructure` | `domain` (it implements the domain's ports), plus SQLAlchemy / drivers / frameworks / config — anything external |

If a domain module ever needs `from sqlalchemy ...` or `from fastapi ...`, the boundary has been violated.

### 2. Domain Models Are Dataclasses (CRITICAL)

Domain models live in `domain/models/<concept>.py` as plain `@dataclass` types. They have no base class from any framework, no `Field(...)` Pydantic descriptors, no `Column(...)` ORM declarations. They may have methods that encode business behaviour, and properties that compute derived values, but they do not import SQLAlchemy or any web framework.

```python
# domain/models/licensing/products.py
from __future__ import annotations

import typing
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from myapp.infrastructure.utils import uuid4_factory

if typing.TYPE_CHECKING:
    from myapp.domain.models.iam import Company
    from myapp.domain.models.licensing.addons import ProductAddon


@dataclass
class Product:
    serial_number: Optional[str] = None
    user_id: Optional[str] = None
    hardware_id: Optional[str] = None
    name: Optional[str] = None
    activation_date: Optional[datetime] = None
    sale_value: Optional[int] = None
    company_id: Optional[str] = None
    notes: Optional[str] = None
    id: Optional[str] = field(default_factory=uuid4_factory)
    created_at: Optional[datetime] = field(default=None)
    updated_at: Optional[datetime] = field(default=None)
    activation_key: Optional["ActivationKey"] = field(default=None)
    product_addons: List["ProductAddon"] = field(default_factory=list)
    # Why init=False you may ask: SQLAlchemy's imperative mapping does not
    # cooperate with dataclasses' __post_init__, so relationship fields that
    # SQLAlchemy populates after loading must be excluded from __init__.
    # See: https://docs.sqlalchemy.org/en/20/orm/mapping_styles.html#maintaining-non-mapped-state-across-loads
    model: Optional["ProductModel"] = field(default=None, init=False)
    company: Optional["Company"] = field(default=None, init=False)

    def has_active_addon(self, addon_code: str) -> bool:
        for product_addon in self.product_addons:
            if product_addon.addon and product_addon.addon.code == addon_code:
                return product_addon.is_active
        return False
```

**Why dataclasses, not Pydantic.** Pydantic validates on construction and serialises to JSON — those are *transport* concerns, not domain concerns. Dataclasses give you what the domain actually needs: structure, equality, and a constructor. Validation belongs in `domain/validations.py`, not in field descriptors. Serialisation belongs in `presentation/`. Keeping the domain dataclass-only prevents the rest of the stack from creeping into it.

**The `init=False` rule.** Relationship fields that SQLAlchemy populates after loading must be declared with `init=False`, because the imperative mapper assigns them outside the dataclass-generated `__init__`. Treat the comment above as a permanent invariant: every relationship attribute mapped by SQLAlchemy needs `init=False`.

**Separate creation inputs from entity representations.** A creation request carries only the data needed to *create* an entity; the entity itself represents a persisted record. Even when they look identical on day one, they diverge over time. Always introduce a separate input type:

```python
@dataclass
class CreateProductRequest:
    serial_number: str
    user_id: str
    hardware_id: str
    name: str
```

This is **SoC**: the data needed to create something is a different concern from the data that represents the persisted thing.

### 3. Persistence Uses Classical (Imperative) SQLAlchemy Mapping (CRITICAL)

There is **one** mapping registry per project, **one** module of `Table(...)` declarations, and **one** module (or one per concept) that calls `mapper_registry.map_imperatively(...)`. The domain dataclasses are never modified to add SQLAlchemy machinery; the registry attaches it at import time.

```python
# infrastructure/orm/orm.py
from sqlalchemy.orm import registry

mapper_registry = registry()
metadata = mapper_registry.metadata
```

```python
# infrastructure/orm/tables.py
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text

from myapp.infrastructure.orm.orm import metadata
from myapp.infrastructure.utils import get_current_datetime


products = Table(
    "products",
    metadata,
    Column("id", String(50), primary_key=True),
    Column("serial_number", String(50), nullable=True),
    Column("user_id", String(50), nullable=True),
    Column("hardware_id", String(50), nullable=True),
    Column("name", String(255), nullable=True),
    Column("activation_date", DateTime, nullable=True),
    Column("sale_value", Integer, nullable=True),
    Column("company_id", String(50), nullable=True),
    Column("notes", Text, nullable=True),
    Column("created_at", DateTime, nullable=True, default=get_current_datetime),
    Column(
        "updated_at",
        DateTime,
        nullable=True,
        default=get_current_datetime,
        onupdate=get_current_datetime,
    ),
)

activation_keys = Table(
    "activation_keys",
    metadata,
    Column("id", String(50), primary_key=True),
    Column("product_key", String(255), nullable=False),
    Column("product_id", String(50), ForeignKey("products.id"), nullable=True),
    Column("created_at", DateTime, nullable=True, default=get_current_datetime),
    Column(
        "updated_at",
        DateTime,
        nullable=True,
        default=get_current_datetime,
        onupdate=get_current_datetime,
    ),
)
```

```python
# infrastructure/orm/mappers.py
from sqlalchemy.orm import relationship

from myapp.infrastructure.orm import tables
from myapp.infrastructure.orm.orm import mapper_registry
from myapp.domain.models import licensing


def run_licensing_mapper() -> None:
    mapper_registry.map_imperatively(
        licensing.Product,
        tables.products,
        properties={
            "activation_key": relationship(
                licensing.ActivationKey,
                uselist=False,
                lazy="selectin",
                cascade="save-update, delete, delete-orphan",
            ),
            "product_addons": relationship(
                licensing.ProductAddon,
                lazy="selectin",
                back_populates="product",
                collection_class=list,
                cascade="save-update, delete, delete-orphan",
            ),
        },
    )
    mapper_registry.map_imperatively(
        licensing.ActivationKey,
        tables.activation_keys,
    )


def run_all_mappers() -> None:
    run_licensing_mapper()
    # run_other_concept_mapper(), ...
```

`run_all_mappers()` is called once during application startup (from `main.py` or an infrastructure startup module), before any query runs.

**Why classical mapping, not declarative.** Declarative SQLAlchemy mixes column declarations into the class body, forcing the class to be a `Base` subclass and to know about the ORM. Imperative mapping keeps the class clean and pushes ORM concerns into a separate file — the dataclass is still a dataclass, just with extra runtime hooks. This is **SoC**: the column list, the relationship topology, and the business behaviour are three different reasons to change a piece of code, so they live in three different files.

**Where the persistence pieces go in `infrastructure/`:**

| Concern | File |
|---------|------|
| The single shared `mapper_registry` and `metadata` | `infrastructure/orm/orm.py` |
| `Table(...)` declarations | `infrastructure/orm/tables.py` (or one file per concept) |
| `mapper_registry.map_imperatively(...)` calls | `infrastructure/orm/mappers.py` (or one file per concept) |

Alembic migrations import `metadata` from `infrastructure/orm/orm.py` for autogeneration.

### 4. Repositories Are Ports In The Domain, One Per Aggregate Root (CRITICAL)

A repository is the port between the domain and persistence. The canonical industry pattern (Cosmic Python, Evans-style DDD, Spring Data convention, .NET `IRepository<T>`):

1. **One abstract repository per aggregate root**, defined in `domain/repositories/<concept>.py`.
2. **Collection-style semantics**: the repository behaves like an in-memory collection of aggregates (`add`, `remove`, `get`, `list_*`, `find_by_*`).
3. **Method names reflect domain questions**, not SQL shapes. `find_by_serial_number` — not `get_by_fields({"serial_number": ...})`.
4. **Strict naming convention** for retrieval methods (the "Cosmic Python" convention, also used by Spring Data and EF Core):

| Method | Returns | When the item does not exist |
|--------|---------|------------------------------|
| `get(id)` | `Aggregate` (never `Optional`) | Raises `EntityNotFoundError` |
| `find_by_id(id)` | `Optional[Aggregate]` | Returns `None` |
| `find_by_<attribute>(value)` | `Optional[Aggregate]` (when unique) | Returns `None` |
| `list_<criterion>(...)` | `list[Aggregate]` | Returns `[]` |

5. **No `update()` method.** Mutate the loaded aggregate; the session tracks the change and the UoW persists it on commit. Adding an `update(aggregate)` method invites callers to mutate detached objects, which is an entire class of bugs.
6. **No god-methods.** `get_with_limit_and_offset(sort_field, sort_direction, limit, offset)` and `get_by_fields(filters: dict)` are explicit anti-patterns. They leak persistence concerns into the domain interface and tell future readers nothing about *why* a query exists.

```python
# domain/repositories/products.py
import abc
from datetime import datetime
from typing import Optional

from myapp.domain.models.licensing.products import Product


class AbstractProductRepository(abc.ABC):
    @abc.abstractmethod
    async def add(self, product: Product) -> None: ...

    @abc.abstractmethod
    async def remove(self, product: Product) -> None: ...

    @abc.abstractmethod
    async def get(self, product_id: str) -> Product:
        """Return the product or raise EntityNotFoundError."""

    @abc.abstractmethod
    async def find_by_id(self, product_id: str) -> Optional[Product]: ...

    @abc.abstractmethod
    async def find_by_serial_number(self, serial_number: str) -> Optional[Product]: ...

    @abc.abstractmethod
    async def list_by_user(self, user_id: str) -> list[Product]: ...

    @abc.abstractmethod
    async def list_with_expired_maintenance(self, as_of: datetime) -> list[Product]: ...
```

**The aggregate-root rule.** Define a repository for each *aggregate root*, not for each entity. If `MaintenanceService` and `ActivationKey` are children of the `Product` aggregate (they are loaded through `Product`, mutated through `Product`, and have no independent identity in the domain), they do **not** get their own repositories. The product repository returns a fully loaded `Product` with its `maintenance_service` and `activation_key` attached; mutations to those children flow through the parent. Aggregates are the consistency boundary; repositories give you aggregates.

If a child entity *is* in fact a separate aggregate root (it can be queried independently, mutated independently, and has independent lifecycle), then yes, give it its own repository. Use the rule of *who owns the lifecycle*: if creating a product also creates its maintenance service, and deleting the product also deletes the maintenance, they are one aggregate; if either can exist without the other, they are two.

**Methods take and return domain dataclasses.** Never tables, never SQLAlchemy rows, never `dict[str, Any]`. The caller sees only domain types.

**Why put the port in `domain/`, not `infrastructure/`?** This is dependency inversion — the placement used by Evans-style layering and ports-and-adapters alike: a *port* is an interface the domain *needs*; its implementation is something the lower layers *provide*. Putting the abstract repository in `domain/repositories/<concept>.py` keeps the dependency arrow pointing inward — both `application/` and `infrastructure/` depend on the port, and the port depends on nothing outside `domain/`. The domain has no idea SQLAlchemy exists.

The concrete implementation goes in `infrastructure/`:

```python
# infrastructure/repository/products.py
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from myapp.domain.exceptions import EntityNotFoundError
from myapp.domain.models.licensing.maintenance import MaintenanceService
from myapp.domain.models.licensing.products import Product
from myapp.domain.repositories.products import AbstractProductRepository


class SqlAlchemyProductRepository(AbstractProductRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, product: Product) -> None:
        self._session.add(product)

    async def remove(self, product: Product) -> None:
        await self._session.delete(product)

    async def get(self, product_id: str) -> Product:
        product = await self.find_by_id(product_id)
        if product is None:
            raise EntityNotFoundError(entity_type="Product", entity_id=product_id)
        return product

    async def find_by_id(self, product_id: str) -> Optional[Product]:
        result = await self._session.execute(
            select(Product).where(Product.id == product_id)
        )
        return result.scalars().first()

    async def find_by_serial_number(self, serial_number: str) -> Optional[Product]:
        result = await self._session.execute(
            select(Product).where(Product.serial_number == serial_number)
        )
        return result.scalars().first()

    async def list_by_user(self, user_id: str) -> list[Product]:
        result = await self._session.execute(
            select(Product).where(Product.user_id == user_id)
        )
        return list(result.scalars().all())

    async def list_with_expired_maintenance(self, as_of: datetime) -> list[Product]:
        result = await self._session.execute(
            select(Product)
            .join(MaintenanceService)
            .where(MaintenanceService.end_date < as_of)
        )
        return list(result.scalars().all())
```

**The concrete implementation receives the session via `__init__`.** It does not open it, does not close it, does not commit it. That is the Unit of Work's job (next section). The repository's only responsibility is to translate domain calls into queries against the session it was handed.

**`add()` does not flush.** SQLAlchemy's session tracks the change; the flush happens automatically before queries or at commit. Forcing a flush inside `add()` couples the repository to a particular commit cadence and breaks the UoW's ability to batch writes.

**No generic base repository.** Each aggregate gets its own class with its own methods. A generic `SqlAlchemyAsyncRepository[T]` parameterised by model is an attractive nuisance: it pulls every concept's queries into a common base and obscures which methods each aggregate actually needs. This is **SRP**: each repository class has *one* reason to change (the queries its aggregate needs).

**In-memory fakes are part of the pattern.** Every abstract repository gets a sibling in-memory implementation, used in service unit tests:

```python
# infrastructure/repository/products.py (continued)
from typing import Optional


class FakeProductRepository(AbstractProductRepository):
    def __init__(self, products: Optional[list[Product]] = None):
        self._products: dict[str, Product] = {product.id: product for product in (products or [])}

    async def add(self, product: Product) -> None:
        self._products[product.id] = product

    async def remove(self, product: Product) -> None:
        self._products.pop(product.id, None)

    async def get(self, product_id: str) -> Product:
        product = await self.find_by_id(product_id)
        if product is None:
            raise EntityNotFoundError(entity_type="Product", entity_id=product_id)
        return product

    async def find_by_id(self, product_id: str) -> Optional[Product]:
        return self._products.get(product_id)

    async def find_by_serial_number(self, serial_number: str) -> Optional[Product]:
        for product in self._products.values():
            if product.serial_number == serial_number:
                return product
        return None

    async def list_by_user(self, user_id: str) -> list[Product]:
        return [product for product in self._products.values() if product.user_id == user_id]

    async def list_with_expired_maintenance(self, as_of: datetime) -> list[Product]:
        return [
            product for product in self._products.values()
            if product.maintenance_service is not None
            and product.maintenance_service.end_date < as_of
        ]
```

The fake satisfies the exact same abstract port the SQLAlchemy implementation does. Tests construct services with a `FakeUnitOfWork` whose `products` attribute is a `FakeProductRepository`, exercise the use case, then assert on the state of the fake. No mocks, no patches, no databases. The pattern's payoff: every application service has a unit test that runs in milliseconds and exercises the actual control flow.

### 5. The Unit Of Work Holds Repositories And Bounds Transactions (CRITICAL)

A Unit of Work is the transaction boundary. It opens a session on `__aenter__`, instantiates every repository the application needs against that session, **rolls back unconditionally on `__aexit__`**, and exposes an explicit `await commit()` that the application code must call for changes to persist.

```python
# domain/unit_of_work.py
from __future__ import annotations

import abc
from typing import Self

from myapp.domain.repositories.products import AbstractProductRepository
from myapp.domain.repositories.users import AbstractUserRepository


class AbstractUnitOfWork(abc.ABC):
    # Repositories are exposed as typed attributes. The concrete UoW assigns
    # them in __aenter__, against the same session, so all writes participate
    # in one transaction.
    products: AbstractProductRepository
    users: AbstractUserRepository

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exception_type, exception_value, traceback) -> None:
        # Roll back unconditionally. A successful commit() has already
        # persisted; a missing commit() means the caller did not want the
        # changes. Either way, rollback() on an already-committed
        # transaction is a no-op.
        await self.rollback()

    @abc.abstractmethod
    async def commit(self) -> None: ...

    @abc.abstractmethod
    async def rollback(self) -> None: ...
```

```python
# infrastructure/unit_of_work.py
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from myapp.infrastructure.repository.products import SqlAlchemyProductRepository
from myapp.infrastructure.repository.users import SqlAlchemyUserRepository
from myapp.domain.unit_of_work import AbstractUnitOfWork
from myapp.infrastructure.database.sqlalchemy_session import ASYNC_SESSION_FACTORY


class SqlAlchemyAsyncUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession] = ASYNC_SESSION_FACTORY):
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self.products = SqlAlchemyProductRepository(session=self._session)
        self.users = SqlAlchemyUserRepository(session=self._session)
        return await super().__aenter__()

    async def __aexit__(self, exception_type, exception_value, traceback) -> None:
        try:
            await super().__aexit__(exception_type, exception_value, traceback)
        finally:
            await self._session.close()
            self._session = None

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
```

**The in-memory fake UoW for tests:**

```python
# infrastructure/unit_of_work.py (continued)
from typing import Optional, Self

from myapp.infrastructure.repository.products import FakeProductRepository
from myapp.infrastructure.repository.users import FakeUserRepository
from myapp.domain.models.licensing.products import Product
from myapp.domain.models.iam.users import User


class FakeUnitOfWork(AbstractUnitOfWork):
    def __init__(
        self,
        products: Optional[list[Product]] = None,
        users: Optional[list[User]] = None,
    ):
        self.products = FakeProductRepository(products=products)
        self.users = FakeUserRepository(users=users)
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> Self:
        return await super().__aenter__()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True
```

The fake is itself an `AbstractUnitOfWork`, so any service that depends on the port works against it. The `committed` / `rolled_back` flags let tests assert that the use case persisted (or refused to persist) without touching a database.

**Using the Unit of Work:**

```python
async with SqlAlchemyAsyncUnitOfWork() as unit_of_work:
    existing = await unit_of_work.products.find_by_serial_number(request.serial_number)
    if existing is not None:
        raise ProductAlreadyExistsError(serial_number=request.serial_number)

    product = Product(name=request.name, serial_number=request.serial_number, user_id=request.user_id)
    await unit_of_work.products.add(product)

    user = await unit_of_work.users.get(request.user_id)
    user.record_product_purchase(product_id=product.id)
    # No update() call — the session tracks the mutation; commit persists it.

    await unit_of_work.commit()  # Explicit. Without this, both writes are rolled back.
```

**Why explicit commit?** Two reasons.

First, it makes the success path *visible at every call site*. Reading the service method, you can see exactly when the transaction is meant to succeed; the absence of a `commit()` is now a code smell instead of an invisible default. Compare this to "commit on context-manager exit when no exception was raised" — that rule is correct but easy to forget, and easy to break when refactoring (e.g. adding a `try/except` inside the `with` block accidentally swallows an exception and the UoW commits a half-finished state).

Second, it composes cleanly with conditional logic. A use case that does some work, checks a condition, then either persists or aborts is natural with explicit commit:

```python
async with SqlAlchemyAsyncUnitOfWork() as unit_of_work:
    product = await unit_of_work.products.get(request.product_id)
    if product is None or not product.eligible_for_renewal:
        return  # No commit() — rollback on exit. Nothing was persisted.

    product.extend_maintenance(new_end_date=request.new_end_date)
    await unit_of_work.commit()
```

**Repositories are accessed as typed attributes, not by lookup.** `unit_of_work.products.find_by_serial_number(...)` is type-checked end to end: the IDE knows what methods exist; mypy/pyright catches typos; refactors are safe. `unit_of_work.get_repository(Product).find_by_serial_number(...)` works but throws away type information at the dictionary lookup and gives you nothing in return.

**Sessions never leave the UoW.** Application services hold UoW factories, not sessions. Repositories receive the session from the UoW in `__aenter__`. The domain never sees either.

**One coordinated UoW per use case.** All repositories needed by one use case live on one UoW so they share one session, one transaction. If you find yourself opening a second UoW for a related operation, your use-case boundary is wrong — fix the boundary, do not nest UoWs.

**Scaling to multiple bounded contexts.** When the project grows past a handful of concepts, split the UoW by bounded context: `LicensingUnitOfWork` exposes `products`, `addons`, `activation_keys`; `IamUnitOfWork` exposes `users`, `companies`, `profiles`. Each remains a separate transaction boundary and each is its own port-and-adapter pair. Do **not** split by use case (`CreateProductUnitOfWork`) — that is just a function with extra ceremony.

**Optional: post-commit hooks.** Side effects that must only fire on successful commit (publishing an event, enqueuing a job) can be registered on the UoW and run after `commit()` returns. Keep this as an optional extension on the abstract UoW (`register_post_commit_hook(coro)`); do not bake it into every method.

### 6. Application Services Orchestrate Use Cases And Own The UoW (CRITICAL)

Application services live in `application/services/<concept>.py` and orchestrate one use case each. They accept a **UoW factory** (a callable producing a UoW) via the constructor, with the SQLAlchemy implementation as the default and any fake substitutable for tests.

```python
# application/services/licensing/products.py
from datetime import datetime, timezone
from typing import Callable, Optional

from myapp.infrastructure.unit_of_work import SqlAlchemyAsyncUnitOfWork
from myapp.domain.exceptions import ProductAlreadyExistsError
from myapp.domain.models.licensing.products import ActivationKey, Product
from myapp.domain.unit_of_work import AbstractUnitOfWork
from myapp.infrastructure.gateway.notifications import NotificationGateway
from myapp.infrastructure.utils import generate_activation_key


class ProductCreationService:
    def __init__(
        self,
        unit_of_work_factory: Callable[[], AbstractUnitOfWork] = SqlAlchemyAsyncUnitOfWork,
        notification_gateway: Optional[NotificationGateway] = None,
    ):
        self._unit_of_work_factory = unit_of_work_factory
        self._notification_gateway = notification_gateway or NotificationGateway()

    async def create_product(self, name: str, serial_number: str, user_id: str) -> Product:
        now = datetime.now(timezone.utc)
        product = Product(
            name=name,
            serial_number=serial_number,
            user_id=user_id,
            activation_key=ActivationKey(product_key=generate_activation_key(), created_at=now, updated_at=now),
            created_at=now,
            updated_at=now,
        )

        async with self._unit_of_work_factory() as unit_of_work:
            existing = await unit_of_work.products.find_by_serial_number(serial_number)
            if existing is not None:
                raise ProductAlreadyExistsError(serial_number=serial_number)

            await unit_of_work.products.add(product)
            await unit_of_work.commit()

        await self._notification_gateway.notify_product_created(product_id=product.id)
        return product
```

**Why inject the UoW *factory*, not an instance.** A UoW is short-lived: one per use case, opened and closed inside the service method. Injecting a factory (a zero-argument callable returning a UoW) lets each method open its own UoW while still being substitutable in tests — tests pass a lambda returning a pre-populated `FakeUnitOfWork`.

**A unit test for the service:**

```python
# tests/unit/application/services/licensing/test_products.py
import pytest

from myapp.infrastructure.unit_of_work import FakeUnitOfWork
from myapp.application.services.licensing.products import ProductCreationService
from myapp.domain.exceptions import ProductAlreadyExistsError
from myapp.domain.models.licensing.products import Product


@pytest.fixture
def fake_unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def service(fake_unit_of_work: FakeUnitOfWork) -> ProductCreationService:
    return ProductCreationService(
        unit_of_work_factory=lambda: fake_unit_of_work,
        notification_gateway=FakeNotificationGateway(),
    )


class TestProductCreationService:
    async def test_creates_product_and_commits(
        self,
        service: ProductCreationService,
        fake_unit_of_work: FakeUnitOfWork,
    ) -> None:
        product = await service.create_product(name="HC2", serial_number="SN-001", user_id="user-1")

        assert fake_unit_of_work.committed is True
        assert await fake_unit_of_work.products.find_by_serial_number("SN-001") is product

    async def test_rejects_duplicate_serial_number(
        self,
        service: ProductCreationService,
        fake_unit_of_work: FakeUnitOfWork,
    ) -> None:
        await fake_unit_of_work.products.add(Product(name="Existing", serial_number="SN-001"))

        with pytest.raises(ProductAlreadyExistsError):
            await service.create_product(name="HC2", serial_number="SN-001", user_id="user-1")
        assert fake_unit_of_work.committed is False
```

No mocks, no patches, no database. The test runs in milliseconds and exercises the actual control flow of the service.

**Services do not handle transport.** They take and return domain types, not Pydantic schemas. They do not raise HTTP exceptions — they raise domain or application exceptions and let the presentation layer translate.

**Services do not contain business rules that belong in the domain.** A rule like "a product whose maintenance has expired cannot be renewed twice" belongs in `domain/validations/<concept>.py` (or as a method on `Product`), not buried inside the service. The service *coordinates*; the domain *decides*.

### 7. Commands Carry Intent (CRITICAL)

A command is a value object representing a request to do something. Commands are Pydantic models (because they cross transport boundaries — message broker payloads, HTTP bodies) defined in `domain/commands.py`. They flow from the presentation layer through a broker (or directly) into message handlers in `application/commands/`.

```python
# domain/commands.py
from typing import Optional

from pydantic import BaseModel, Field


class CreateProduct(BaseModel):
    name: str = Field(..., description="Product display name")
    serial_number: str = Field(..., description="Manufacturer serial number")
    user_id: str = Field(..., description="Owning user id")


class DeleteProduct(BaseModel):
    product_id: str = Field(..., description="Product to delete")


class ActivateProduct(BaseModel):
    product_id: str = Field(..., description="Product to activate")
    activation_key: str = Field(..., description="Customer-supplied activation key")
```

```python
# application/commands/licensing/products.py
from myapp.application.services.licensing.products import ProductCreationService, ProductDeletionService
from myapp.domain.commands import CreateProduct, DeleteProduct


async def handle_create_product(command: CreateProduct) -> dict:
    service = ProductCreationService()
    product = await service.create_product(
        name=command.name,
        serial_number=command.serial_number,
        user_id=command.user_id,
    )
    return {"id": product.id}


async def handle_delete_product(command: DeleteProduct) -> None:
    service = ProductDeletionService()
    await service.delete_product(product_id=command.product_id)
```

If the project uses a message broker, decorate each handler with the broker's `@message_handler(message=...)` decorator instead of calling them directly. Handlers stay thin: unpack the command, dispatch to the service, format the broker-specific response.

### 8. Validations And Validators Compose (HIGH)

Validation logic is split by concern: **domain validations** check pure business rules against domain types; **application validations** need repositories or gateways and run inside a UoW. A **validator** composes several validations into an ordered sequence and runs them.

```python
# application/validations/common.py
import abc

from myapp.domain.exceptions import DomainValidationError


class Validation(abc.ABC):
    @abc.abstractmethod
    async def execute(self) -> None:
        raise NotImplementedError


class ValidationError(DomainValidationError):
    pass
```

```python
# domain/validations/licensing.py
from myapp.domain.exceptions import DomainValidationError
from myapp.domain.models.licensing import Product


class ProductActivationEligibility:
    def __init__(self, product: Product):
        self._product = product

    async def execute(self) -> None:
        if self._product.activation_date is not None:
            raise DomainValidationError(
                message=f"Product '{self._product.id}' has already been activated."
            )
```

```python
# application/validations/licensing.py
from typing import Callable

from myapp.infrastructure.unit_of_work import SqlAlchemyAsyncUnitOfWork
from myapp.application.validations.common import Validation, ValidationError
from myapp.domain.unit_of_work import AbstractUnitOfWork


class ProductMustExist(Validation):
    def __init__(
        self,
        product_id: str,
        unit_of_work_factory: Callable[[], AbstractUnitOfWork] = SqlAlchemyAsyncUnitOfWork,
    ):
        self._product_id = product_id
        self._unit_of_work_factory = unit_of_work_factory

    async def execute(self) -> None:
        async with self._unit_of_work_factory() as unit_of_work:
            product = await unit_of_work.products.find_by_id(self._product_id)
        if product is None:
            raise ValidationError(message=f"Product '{self._product_id}' does not exist.")
```

```python
# application/validators/base.py
import abc

from myapp.application.validations.common import Validation


class BaseValidator(abc.ABC):
    @abc.abstractmethod
    def get_validations(self) -> tuple[Validation, ...]: ...

    async def run(self) -> None:
        for validation in self.get_validations():
            await validation.execute()
```

```python
# application/validators/licensing.py
from typing import Callable

from myapp.infrastructure.unit_of_work import SqlAlchemyAsyncUnitOfWork
from myapp.application.validations.common import Validation
from myapp.application.validations.licensing import ProductMustExist
from myapp.application.validators.base import BaseValidator
from myapp.domain.unit_of_work import AbstractUnitOfWork


class ProductActivationValidator(BaseValidator):
    def __init__(
        self,
        product_id: str,
        unit_of_work_factory: Callable[[], AbstractUnitOfWork] = SqlAlchemyAsyncUnitOfWork,
    ):
        self._product_id = product_id
        self._unit_of_work_factory = unit_of_work_factory

    def get_validations(self) -> tuple[Validation, ...]:
        return (
            ProductMustExist(product_id=self._product_id, unit_of_work_factory=self._unit_of_work_factory),
        )
```

Validations that need the loaded aggregate to apply a domain rule should fetch it through the same factory and pass it to the pure domain validation:

```python
class ProductCancellationValidator(BaseValidator):
    def __init__(
        self,
        product_id: str,
        unit_of_work_factory: Callable[[], AbstractUnitOfWork] = SqlAlchemyAsyncUnitOfWork,
    ):
        self._product_id = product_id
        self._unit_of_work_factory = unit_of_work_factory

    def get_validations(self) -> tuple[Validation, ...]:
        # Compose: existence first, then domain-level eligibility on the loaded aggregate.
        return (
            ProductMustExist(product_id=self._product_id, unit_of_work_factory=self._unit_of_work_factory),
            ProductCancellationEligibilityCheck(
                product_id=self._product_id,
                unit_of_work_factory=self._unit_of_work_factory,
            ),
        )
```

**Why split this way.** This is **SoC** again. A `Validation` knows one rule and how to check it. A `BaseValidator` knows how to run a list of rules. A concrete `Validator` knows *which* rules apply to a specific use case. Each class has **one reason to change**: a new rule changes one `Validation`; a new use case adds one `Validator`; a new check protocol (e.g. parallel execution) changes `BaseValidator`. Mixing all three into one function couples those reasons and forces every change to touch one block.

Validators run *before* command handlers, in the presentation layer, so that invalid requests never reach a UoW that would otherwise need to roll back.

### 9. Gateways Encapsulate External Systems (HIGH)

A gateway is the adapter to anything that is not the application's own database: third-party APIs, message brokers (when *consumed*), email services, object storage, other internal services. Gateways live in `infrastructure/gateway/` and are named after the external system, not the role.

```python
# infrastructure/gateway/payment.py
import httpx

from myapp.infrastructure.config.settings import PAYMENT_API_BASE_URL, PAYMENT_API_TOKEN


class PaymentGateway:
    def __init__(self, base_url: str = PAYMENT_API_BASE_URL, token: str = PAYMENT_API_TOKEN):
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}"},
        )

    async def authorize(self, order_id: str, amount_cents: int) -> str:
        response = await self._client.post(
            "/authorizations",
            json={"orderId": order_id, "amountCents": amount_cents},
        )
        response.raise_for_status()
        return response.json()["authorizationId"]
```

The gateway hides protocol details (HTTP verbs, headers, JSON shape) and translates external errors into application-level exceptions when needed.

### 10. Routers Are Thin Translation Layers (CRITICAL)

Routers in `presentation/routers/` (e.g. `presentation/routers/v1/` if you version) only translate HTTP to and from the application layer. They deserialise the request, run validators, enqueue a command or call a service, and serialise the response.

```python
# presentation/routers/licensing/products.py
from http import HTTPStatus

from fastapi import APIRouter, HTTPException

from myapp.presentation.routers.licensing.router import licensing_router as router
from myapp.application.validators.licensing import ProductActivationValidator, ProductCreateValidator
from myapp.application.services.licensing.products import ProductRetrievalService
from myapp.domain.commands import CreateProduct, ActivateProduct
from myapp.domain.exceptions import DomainValidationError
from myapp.infrastructure.messaging import async_enqueue_message
from myapp.presentation.schemas.licensing.products import (
    ProductActivationSchema,
    ProductCreateSchema,
    ProductDetailsSchema,
)


@router.post("/products", summary="Create a product")
async def create_product(product_create_schema: ProductCreateSchema):
    try:
        await ProductCreateValidator(product_create_schema=product_create_schema).run()
        return await async_enqueue_message(
            message=CreateProduct(
                name=product_create_schema.name,
                serial_number=product_create_schema.serial_number,
                user_id=product_create_schema.user_id,
            ),
            create_job=True,
        )
    except DomainValidationError as error:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=error.message) from error


@router.get("/products/{product_id}", response_model=ProductDetailsSchema, summary="Get product details")
async def get_product(product_id: str) -> ProductDetailsSchema:
    service = ProductRetrievalService()
    product = await service.get_product_details(product_id)
    if product is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"Product '{product_id}' not found.")
    return product


@router.post("/products/{product_id}:activate", summary="Activate a product")
async def activate_product(product_id: str, body: ProductActivationSchema):
    try:
        await ProductActivationValidator(product_id=product_id).run()
        return await async_enqueue_message(
            message=ActivateProduct(product_id=product_id, activation_key=body.activation_key),
            create_job=True,
        )
    except DomainValidationError as error:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=error.message) from error
```

**Routers do not contain business rules.** If you find yourself writing `if product.status == ...` inside a router, that rule belongs in a domain validation.

### 11. Presentation Schemas Are Separate From Domain Models (CRITICAL)

HTTP request and response schemas live in `presentation/schemas/`. They are Pydantic models tuned for the wire format (camelCase aliases, optional fields, validation messages). They are *not* domain models.

Mappers in `presentation/mappers/` translate between schemas and domain dataclasses.

```python
# presentation/schemas/licensing/products.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProductCreateSchema(BaseModel):
    name: str = Field(..., description="Product display name")
    serial_number: str = Field(..., alias="serialNumber")
    user_id: str = Field(..., alias="userId")


class ProductDetailsSchema(BaseModel):
    id: str
    name: Optional[str] = None
    serial_number: Optional[str] = Field(default=None, alias="serialNumber")
    user_id: Optional[str] = Field(default=None, alias="userId")
    activation_date: Optional[datetime] = Field(default=None, alias="activationDate")
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")


class ProductActivationSchema(BaseModel):
    activation_key: str = Field(..., alias="activationKey")
```

```python
# presentation/mappers/licensing.py
from myapp.domain.models.licensing import Product
from myapp.presentation.schemas.licensing.products import ProductDetailsSchema


def product_to_details_schema(product: Product) -> ProductDetailsSchema:
    return ProductDetailsSchema(
        id=product.id,
        name=product.name,
        serialNumber=product.serial_number,
        userId=product.user_id,
        activationDate=product.activation_date,
        createdAt=product.created_at,
        updatedAt=product.updated_at,
    )
```

### 12. Bootstrap Lives In `main.py` (HIGH)

The entry point composes the application: it initialises logging, registers ORM mappers, runs migrations, sets up the message broker, registers routers and exception handlers, and starts the web server. It is the only place that imports concrete implementations and wires them in.

```python
# main.py
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from myapp.infrastructure.orm.mappers import run_all_mappers
from myapp.presentation.routers import health
from myapp.presentation.routers.licensing import licensing_router
from myapp.domain.exceptions import DomainValidationError
from myapp.infrastructure.config.app_config import HOST, PORT
from myapp.infrastructure.database.migration_runner import run_migrations
from myapp.infrastructure.logger import init_logging, logger
# Importing command handlers registers them with the broker.
from myapp.application import commands as command_handlers  # noqa: F401


init_logging()


async def domain_validation_handler(request: Request, exception: DomainValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"message": exception.message})


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up ...")
    run_all_mappers()
    run_migrations()
    yield
    logger.info("Shutting down ...")


app = FastAPI(
    lifespan=lifespan,
    exception_handlers={DomainValidationError: domain_validation_handler},
)
app.include_router(health.router)
app.include_router(licensing_router)


if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
```

**`run_all_mappers()` runs before any query.** Imperative mapping happens at runtime; if the first query fires before the registry is configured, SQLAlchemy will not know the domain dataclasses are persistent. Place the call in the lifespan startup (or at module import, depending on the project) and never inside a request handler.

The composition root is the only honest place to wire concrete classes; everything below it depends on abstractions and accepts its dependencies.

## Project Structure

### Canonical Directory Layout

```
src/myapp/
├── main.py                                # App entry point and lifespan
│
├── presentation/                          # Presentation layer: HTTP delivery + wire format
│   ├── routers/                           # FastAPI routers
│   │   ├── health.py
│   │   └── licensing/
│   │       ├── router.py                  # licensing_router = APIRouter(...)
│   │       ├── products.py
│   │       └── activations.py
│   ├── schemas/
│   │   └── licensing/
│   │       ├── products.py                # Pydantic request/response models
│   │       └── activations.py
│   └── mappers/
│       └── licensing.py                   # Domain ↔ schema mappers
│
├── application/                           # Use-case orchestration
│   ├── services/
│   │   └── licensing/
│   │       ├── products.py                # ProductCreationService, ProductRetrievalService, ...
│   │       └── addons.py
│   ├── commands/
│   │   └── licensing/
│   │       ├── products.py                # @message_handler-decorated functions
│   │       └── addons.py
│   ├── validations/
│   │   ├── common.py                      # Validation ABC, ValidationError
│   │   └── licensing.py                   # ProductMustExist, ...
│   ├── validators/
│   │   ├── base.py                        # BaseValidator
│   │   └── licensing.py                   # ProductCreateValidator, ...
│   ├── dtos/
│   │   └── licensing.py                   # Pagination results, activation context
│   ├── mappers/
│   │   └── licensing.py                   # Domain ↔ application-DTO mappers
│   └── events/
│       └── licensing.py                   # Application-level event handlers
│
├── domain/                                # Pure business logic, no I/O
│   ├── commands.py                        # Pydantic command value objects
│   ├── events.py                          # Domain events
│   ├── exceptions.py                      # Domain exceptions (EntityNotFoundError, ...)
│   ├── message_factory.py                 # Broker-payload construction
│   ├── unit_of_work.py                    # AbstractUnitOfWork (port)
│   ├── models/
│   │   ├── licensing/
│   │   │   ├── products.py                # Product, ActivationKey (dataclasses)
│   │   │   └── addons.py
│   │   └── iam/
│   │       └── users.py
│   ├── repositories/                      # Abstract repositories (ports)
│   │   ├── products.py                    # AbstractProductRepository
│   │   └── users.py                       # AbstractUserRepository
│   ├── validations/
│   │   └── licensing.py                   # Pure-rule validations
│   └── services/
│       └── licensing.py                   # Pure domain services
│
└── infrastructure/                        # Persistence + plumbing (implements domain ports)
    ├── orm/
    │   ├── orm.py                         # mapper_registry, metadata
    │   ├── tables.py                      # Table(...) declarations
    │   └── mappers.py                     # map_imperatively(...) calls
    ├── repository/
    │   ├── products.py                    # SqlAlchemyProductRepository + FakeProductRepository
    │   └── users.py                       # SqlAlchemyUserRepository + FakeUserRepository
    ├── unit_of_work.py                    # SqlAlchemyAsyncUnitOfWork + FakeUnitOfWork
    ├── config/
    │   ├── app_config.py
    │   └── settings.py
    ├── database/
    │   ├── sqlalchemy_session.py          # ASYNC_SESSION_FACTORY, SYNC_SESSION_FACTORY
    │   ├── migration_runner.py            # Programmatic Alembic runner
    │   └── materialized_views.py
    ├── gateway/
    │   ├── payment.py                     # PaymentGateway
    │   └── notifications.py               # NotificationGateway
    ├── exceptions/
    │   └── services.py                    # Infrastructure exceptions
    ├── jobs/
    │   └── workflow.py                    # Background-job infrastructure
    ├── startup/
    │   └── seed_catalogue.py              # One-shot startup tasks
    ├── messaging.py                       # Broker thin wrapper (async_enqueue_message, ...)
    ├── utils.py
    └── logger.py
```

Migrations live in `src/migrations/` (a sibling of `src/myapp/`) per Alembic convention. The Alembic `env.py` imports `metadata` from `myapp.infrastructure.orm.orm`.

### Structural Rules

#### Rule 1 — Concept-Based Folders (CRITICAL)

Folders inside a layer represent **business concepts** (`licensing/`, `iam/`, `notifications/`) or named technical capabilities (`orm/`, `gateway/`, `database/`). Never create folders named after a role (`orchestrators/`, `handlers/`, `helpers/`, `utils/`, `shared/`, `common/`).

Pick *one* axis per layer:

```
# Concept-per-folder (preferred when the layer has several files per concept)
src/myapp/application/services/
├── licensing/
│   ├── products.py
│   ├── addons.py
│   └── trial_bundle.py
└── iam/
    └── users.py

# Flat with concept-named files (preferred when each concept fits in one file)
src/myapp/application/validators/
├── base.py
├── licensing.py
└── iam.py
```

Don't mix `services/licensing/products.py` with `services/iam.py` in the same layer — pick one shape and stay consistent.

#### Rule 2 — Short File Names; Parent Provides Context (HIGH)

When a file lives inside a concept folder, do not repeat the concept in the filename:

```
# Bad — stuttering
src/myapp/infrastructure/orm/licensing_tables.py
src/myapp/application/services/licensing/licensing_products.py

# Good — parent provides context
src/myapp/infrastructure/orm/tables.py
src/myapp/application/services/licensing/products.py
```

The class name keeps the full descriptive identifier (`ProductCreationService`); the file name reflects the *concept* it serves within the layer.

#### Rule 3 — One File Per Concern (HIGH)

A `domain/validations/licensing.py` collects *all* licensing-related domain validations. Do not split it into `product_create_validations.py` and `product_activate_validations.py`. The class names carry the use case (`ProductCreationEligibility`, `ProductActivationEligibility`); the file groups by concept.

The same rule applies to errors: prefer one `exceptions.py` per layer (or per concept) over many small error files.

#### Rule 4 — Tables, Mappers, And Registry Are Each One File (HIGH)

```
infrastructure/orm/
├── orm.py        # mapper_registry, metadata — only these two
├── tables.py     # every Table(...) declaration
└── mappers.py    # every map_imperatively(...) call, split into run_*_mapper() functions
```

If `tables.py` or `mappers.py` outgrows readability, split *by concept*: `tables/licensing.py`, `tables/iam.py`; `mappers/licensing.py`, `mappers/iam.py`. Never split by table role (`mappers/relationships.py`, `mappers/columns.py`) — that violates concept-based grouping.

The `metadata` exported from `orm.py` is what Alembic's `env.py` imports. There is **exactly one** registry in the project.

#### Rule 5 — Ports In Domain, Implementations In Infrastructure (CRITICAL)

```
domain/repositories/
├── products.py            # AbstractProductRepository (port)
├── users.py               # AbstractUserRepository (port)
└── invoices.py            # AbstractInvoiceRepository (port)

domain/unit_of_work.py     # AbstractUnitOfWork (port, declares repo attributes)

infrastructure/repository/
├── products.py            # SqlAlchemyProductRepository + FakeProductRepository
├── users.py               # SqlAlchemyUserRepository + FakeUserRepository
└── invoices.py            # SqlAlchemyInvoiceRepository + FakeInvoiceRepository

infrastructure/unit_of_work.py   # SqlAlchemyAsyncUnitOfWork + FakeUnitOfWork
```

The abstract repository (port) lives in `domain/repositories/<aggregate>.py` because the domain *needs* the capability the repository provides. The concrete SQLAlchemy implementation (adapter) lives in `infrastructure/repository/<aggregate>.py` because the infrastructure layer *provides* the capability. Concrete and fake implementations live in the same file: they implement the same port and are read together. Application services depend only on the abstract types.

The same pattern applies to the UoW: the abstract port (`domain/unit_of_work.py`) declares which repositories the application can use; both the SQLAlchemy and fake implementations (in `infrastructure/unit_of_work.py`) wire those attributes to concrete or in-memory repositories respectively.

#### Rule 6 — No Weak Bucket Folders (HIGH)

Folders named `shared/`, `common/`, `utils/`, `helpers/`, `misc/` accumulate unrelated code by gravity. Avoid them. If a helper is used by multiple concepts in one layer, put it in the smallest meaningful namespace (`infrastructure/utils.py`, not `infrastructure/shared/helpers.py`). If genuine cross-cutting utilities exist, name them after the capability (`infrastructure/clock.py`, `infrastructure/ids.py`), not the role.

#### Rule 7 — Migrations Are Append-Only (HIGH)

Database migrations live in `src/migrations/versions/`. Once a migration is committed and deployed to any environment, it is frozen. Schema corrections happen in a new migration, not by editing an existing one.

Always autogenerate migrations against a real database aligned to the prior revision; never hand-write `op.create_table(...)` from imagination. The autogenerate workflow compares the live database to the imperative-mapper metadata; that is the only workflow that may produce a new revision.

#### Rule 8 — Tests Mirror Source Tree (MEDIUM)

```
src/tests/
├── unit/
│   ├── domain/
│   ├── application/
│   ├── presentation/
│   └── infrastructure/
├── integration/
│   └── infrastructure/
│       └── licensing/
│           ├── test_products_repository.py
│           └── test_unit_of_work_atomicity.py
└── e2e/
    └── presentation/licensing/
        └── test_products.py
```

Unit tests for a module at `src/myapp/application/services/licensing/products.py` live at `src/tests/unit/application/services/licensing/test_products.py`. Integration tests exercise the real database through the UoW and live under `src/tests/integration/infrastructure/`. End-to-end tests hit the running API.

## Anti-Patterns To Avoid

1. **Domain contamination** — importing `from sqlalchemy ...` or `from fastapi ...` in any file under `domain/`. The dataclass must stay a plain dataclass.
2. **Declarative-base domain models** — making `Product` inherit from `Base`. That couples the domain to SQLAlchemy permanently. Use imperative mapping.
3. **Pydantic domain models** — using `BaseModel` for `Product`. Schemas are for transport; domain is for business rules. Keep them separate.
4. **Forgetting `init=False` on mapped relationships** — the dataclass `__init__` will then collide with SQLAlchemy's runtime population and you'll get silent attribute clobbering.
5. **Multiple mapping registries** — each call to `registry()` is a separate `MetaData`. Migrations and queries must agree on one registry; create it once in `infrastructure/orm/orm.py` and import it everywhere else.
6. **Generic god-repository** — `SqlAlchemyAsyncRepository[T]` with `get_with_limit_and_offset`, `get_by_fields(dict)`, or other one-size-fits-all helpers. Every aggregate gets its own port with its own named methods.
7. **`get_repository(Model)` dynamic lookup** — typing dies at the dictionary lookup, refactors break silently, IDEs cannot autocomplete. Use typed attributes: `unit_of_work.products`, `unit_of_work.invoices`.
8. **One repository per entity instead of per aggregate root** — if `InvoiceLine` is a child of `Invoice`, it does not get an `InvoiceLineRepository`. The product/invoice repository returns the aggregate fully loaded.
9. **`update(aggregate)` method on the repository** — there should not be one. Mutate the loaded aggregate; the session tracks the change; `commit()` persists it.
10. **`get(id)` returning `Optional` and silently returning `None`** — pick a convention and stick to it: `get` raises `EntityNotFoundError`, `find_by_id` returns `Optional`. Mixed semantics on the same method name across repositories destroy the convention's value.
11. **Implicit commit on context-manager exit** — easy to forget, easy to break with a `try/except` inside the `with` block. Commit explicitly with `await unit_of_work.commit()`; let `__aexit__` always roll back.
12. **Directly instantiated repositories** — calling `SqlAlchemyProductRepository(session=...)` inside a service. Always go through the UoW so the session is shared with sibling repositories in the same transaction.
13. **Nested or sibling UoWs in one use case** — opening two UoWs against related data inside one service method. They have independent transactions; if one commits and the other fails, the database is inconsistent. Use one UoW per use case, with all needed repositories on it.
14. **Sessions in services or domain** — passing `AsyncSession` objects through application or domain code. Sessions live inside the UoW and never escape `infrastructure/`.
15. **Mocking the repository in service tests** — when a `FakeProductRepository` already exists, reaching for `unittest.mock.Mock` is a waste of typing and a worse test (couples the test to call shape instead of behaviour). Use the fake.
16. **Fat routers** — business rules, transaction control, or multi-step orchestration in FastAPI route functions. Routers translate; services orchestrate.
17. **Role-based folders** — `services/`, `handlers/`, `validators/` at the *top* of a layer is fine; `orchestrators/`, `service_helpers/` as concept buckets are not.
18. **Stuttering file names** — `licensing/licensing_products.py`. Drop the redundant prefix.
19. **Shared Pydantic models for request, response, *and* domain** — they look the same on day one and diverge by month three, dragging breaking changes across layers.
20. **Schema-driven services** — services that accept `ProductCreateSchema` (a presentation type) instead of domain types. Translate at the boundary, in the router or `presentation/mappers/`.
21. **Hand-edited Alembic migrations** — autogenerate against a real database aligned to the parent revision. Hand-written DDL drifts from the registry metadata.
22. **`shared/` and `common/` folders** — they hide poor concept ownership behind a vague name.
23. **Single-letter and abbreviated identifiers** — `p` for `product`, `usr` for `user`, `q` for `query`. Always use the full word; readability beats keystrokes.
24. **Implicit dependency injection through globals** — module-level singletons that services reach for at call time. Inject through `__init__`; keep the wiring explicit.

## Quick Reference

### Adding A New Concept (Walkthrough)

Suppose you are adding `Invoice` to an application that already has `Product` and `User`. `Invoice` is its own aggregate root (independent lifecycle, has its own line items as child entities).

1. **Domain dataclass** — `domain/models/billing/invoices.py`: define `Invoice` and `InvoiceLine` as `@dataclass`. Mark SQLAlchemy-populated relationship fields with `field(default=None, init=False)`. Only `Invoice` is an aggregate root; `InvoiceLine` is a child entity loaded through `Invoice`.
2. **Domain exceptions** — add any `InvoiceNotFoundError`, `InvoiceAlreadyVoidedError`, etc. to `domain/exceptions.py`.
3. **Pure domain validations** — `domain/validations/billing.py`: rules like `InvoiceVoidEligibility` that operate on a loaded `Invoice`.
4. **Repository port** — `domain/repositories/invoices.py`: `AbstractInvoiceRepository` with `add`, `remove`, `get`, `find_by_id`, `find_by_number`, `list_for_customer`, etc. No `update()`.
5. **Add the repository to the abstract UoW** — `domain/unit_of_work.py`: add `invoices: AbstractInvoiceRepository`.
6. **Commands** — `domain/commands.py`: add `CreateInvoice`, `VoidInvoice` as Pydantic `BaseModel` subclasses.
7. **Tables** — add `invoices` and `invoice_lines` `Table(...)` declarations to `infrastructure/orm/tables.py`.
8. **Imperative mapping** — add `run_billing_mapper()` to `infrastructure/orm/mappers.py` and call it from `run_all_mappers()`.
9. **Migration** — `poetry run alembic revision --autogenerate -m "add invoices and invoice_lines tables"`; review the generated script; commit it.
10. **Concrete repository** — `infrastructure/repository/invoices.py`: `SqlAlchemyInvoiceRepository` implementing the port against `self._session`, plus `FakeInvoiceRepository` (in-memory) for tests.
11. **Wire the repository into the concrete UoW** — `infrastructure/unit_of_work.py`: assign `self.invoices = SqlAlchemyInvoiceRepository(session=self._session)` in `__aenter__`; assign the fake in `FakeUnitOfWork.__init__`.
12. **Application service** — `application/services/billing/invoices.py`: define `InvoiceCreationService`, `InvoiceVoidingService`, accepting a `unit_of_work_factory` via `__init__`. Open the UoW, use `unit_of_work.invoices.<method>`, call `await unit_of_work.commit()` explicitly.
13. **Application validations and validator** — `application/validations/billing.py`, `application/validators/billing.py`.
14. **Command handlers** — `application/commands/billing/invoices.py`: `@message_handler`-decorated functions for each command, dispatching to services.
15. **Presentation schemas** — `presentation/schemas/billing/invoices.py`: Pydantic request and response models.
16. **Presentation mappers** — `presentation/mappers/billing.py`: domain ↔ schema helpers.
17. **Router** — `presentation/routers/billing/invoices.py`: thin handlers that run validators, enqueue commands or call services, and return schemas.
18. **Wire in `main.py`** — include the new router on `app.include_router(...)`.
19. **Tests** — unit-test the service with `FakeUnitOfWork`; integration-test `SqlAlchemyInvoiceRepository` and the real UoW against a docker-compose database; e2e-test the API.

### Where Does It Go? (Cheat Sheet)

| You are writing ... | It belongs in ... |
|---------------------|-------------------|
| A business aggregate / entity (dataclass) | `domain/models/<concept>.py` |
| A value object | `domain/models/<concept>.py` |
| An abstract repository (port) | `domain/repositories/<concept>.py` |
| The abstract Unit of Work (port) | `domain/unit_of_work.py` |
| A pure business rule (no I/O) | `domain/validations/<concept>.py` |
| A business exception | `domain/exceptions.py` |
| A command (Pydantic intent object) | `domain/commands.py` |
| A use-case orchestrator | `application/services/<concept>.py` |
| A rule that needs a repo or gateway | `application/validations/<concept>.py` |
| A composer of validations for one use case | `application/validators/<concept>.py` |
| An async message handler | `application/commands/<concept>.py` |
| A wire-format request/response model | `presentation/schemas/<concept>.py` |
| A schema ↔ domain mapper | `presentation/mappers/<concept>.py` |
| A `Table(...)` declaration | `infrastructure/orm/tables.py` |
| A `map_imperatively(...)` call | `infrastructure/orm/mappers.py` |
| A concrete SQLAlchemy repository | `infrastructure/repository/<concept>.py` |
| A `Fake<Concept>Repository` for tests | Same file as the concrete repository |
| The concrete `SqlAlchemyAsyncUnitOfWork` | `infrastructure/unit_of_work.py` |
| The `FakeUnitOfWork` for tests | Same file as the concrete UoW |
| A SQLAlchemy session factory | `infrastructure/database/sqlalchemy_session.py` |
| A third-party API client | `infrastructure/gateway/<external_system>.py` |
| A FastAPI router | `presentation/routers/<concept>/router.py` + `presentation/routers/<concept>/<resource>.py` |
| The composition root | `main.py` |

### Naming Cheat Sheet

| Kind | Name pattern | Example |
|------|--------------|---------|
| Domain entity | `<Concept>` | `Product`, `Invoice` |
| Domain enum | `<Concept><Aspect>` | `ProductStatus`, `InvoiceState` |
| Domain command | `<Verb><Concept>` | `CreateProduct`, `VoidInvoice` |
| Domain validation | `<Concept><Rule>` | `ProductActivationEligibility` |
| Domain event | `<Concept><PastVerb>` | `ProductCreated`, `InvoiceVoided` |
| Domain exception | `<Concept><Failure>Error` | `ProductNotFoundError` |
| Application service | `<Concept><UseCase>Service` | `ProductCreationService`, `ProductRetrievalService` |
| Application validation | `<Subject><Constraint>` | `ProductMustExist` |
| Application validator | `<Concept><UseCase>Validator` | `ProductActivationValidator` |
| Repository port (abstract) | `Abstract<Concept>Repository` | `AbstractProductRepository` |
| Repository adapter (SQLAlchemy) | `SqlAlchemy<Concept>Repository` | `SqlAlchemyProductRepository` |
| Repository adapter (fake) | `Fake<Concept>Repository` | `FakeProductRepository` |
| Unit of Work port (abstract) | `AbstractUnitOfWork` | `AbstractUnitOfWork` |
| Unit of Work adapter (SQLAlchemy) | `SqlAlchemy<Sync/Async>UnitOfWork` | `SqlAlchemyAsyncUnitOfWork` |
| Unit of Work adapter (fake) | `FakeUnitOfWork` | `FakeUnitOfWork` |
| Gateway | `<ExternalSystem>Gateway` | `PaymentGateway` |
| Request schema | `<Concept><Action>Schema` | `ProductCreateSchema` |
| Response schema | `<Concept><Detail>Schema` | `ProductDetailsSchema` |

## Guidelines

### Layer Responsibilities (Recap)
- **Presentation** — FastAPI routers, exception handlers, HTTP dependency declarations, wire-format Pydantic schemas, schema ↔ domain mappers.
- **Application** — use-case services that own the UoW lifecycle, command handlers, application validations and validators, application DTOs, mappers.
- **Domain** — aggregates and value objects (dataclasses), abstract repository ports, abstract Unit-of-Work port, commands (Pydantic), domain events, domain exceptions, pure validations, pure domain services.
- **Infrastructure** — ORM tables, imperative mapper registration, concrete SQLAlchemy repositories *and* in-memory fakes, concrete SQLAlchemy UoW *and* fake UoW, session factories, configuration, gateways, background jobs, migrations, startup routines, logging.

### Module Layout (Recap)
- Group by concept, not by role.
- Keep filenames short; let the parent folder provide context.
- One `exceptions.py` per layer; one validations file per concept.
- One mapping registry, one tables module, one mappers module — split *by concept* when they outgrow readability.
- No `shared/`, `common/`, `utils/`, or `misc/` folders.

### Persistence Workflow (Recap)
- Domain dataclass first; then table; then imperative mapping; then migration.
- Autogenerate migrations against a real database aligned to the parent revision.
- Never hand-edit a committed migration; fix forward with a new revision.
- Mark SQLAlchemy-populated relationship fields with `init=False` in the dataclass.

### Repository Conventions (Recap)
- One abstract repository per aggregate root, in `domain/repositories/<concept>.py`.
- One concrete adapter per port, in `infrastructure/repository/<concept>.py`.
- One in-memory fake per port, in the same file as the concrete adapter.
- Methods named after domain questions: `add`, `remove`, `get` (raises), `find_by_<attr>` (Optional), `list_<criterion>` (List).
- No `update()` method — mutate the loaded aggregate; the session tracks the change.
- Concrete repository receives the session via `__init__`; never opens, commits, or closes it.

### Transaction Workflow (Recap)
- Application service opens a UoW per use case via the injected `unit_of_work_factory`.
- Each repository the use case needs is reached as a typed attribute: `unit_of_work.products`, `unit_of_work.users`.
- Mutations happen on loaded aggregates; the session tracks them automatically.
- Commit is explicit: `await unit_of_work.commit()`. Without it, `__aexit__` rolls back.
- The session never leaves the UoW.

### Testing Strategy
- Unit-test the domain in isolation — no fakes needed for pure dataclasses and pure validations.
- Unit-test application services by injecting a `lambda: FakeUnitOfWork(products=[...], users=[...])` factory. Assert on the fake's repository state and the `committed` / `rolled_back` flags. No mocks, no patches.
- Integration-test the concrete `SqlAlchemyAsyncUnitOfWork` and `SqlAlchemy*Repository` adapters against a real database (e.g. a docker-compose Postgres). This is where you verify the imperative mapping, transactions, and queries.
- End-to-end test the API against a running app with real infrastructure.
- Mirror the source tree under `tests/unit/`, `tests/integration/`, `tests/e2e/`.

The recurring rule, one more time: **Separation of Concerns and Single Responsibility**. The dataclass is one concern (business shape). The table is another (storage shape). The mapper is a third (the bridge). The repository is a fourth (domain-level access). The UoW is a fifth (transaction boundary). Whenever a module starts doing two of these, split it. Whenever two modules share a reason to change, they may be one concern hiding behind two files — merge them. Every other rule in this skill is a specific application of those two.
