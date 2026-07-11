# SQLAlchemy ORM Mapping — Three-File Implementation

This file contains the complete classical (imperative) SQLAlchemy mapping split across its three canonical files. The normative rules governing this split live in `software-engineering/python-ddd/SKILL.md` §3. All three files live under `infrastructure/orm/` in a real project.

## `infrastructure/orm/orm.py` — Registry and Metadata

The single shared registry and metadata object for the entire project. Import `mapper_registry` wherever `map_imperatively(...)` is called; import `metadata` from Alembic's `env.py` for autogenerate.

```python
# infrastructure/orm/orm.py
from sqlalchemy.orm import registry

mapper_registry = registry()
metadata = mapper_registry.metadata
```

## `infrastructure/orm/tables.py` — Table Declarations

All `Table(...)` declarations for the project. Split by concept file (`tables/licensing.py`, `tables/iam.py`) only when this file outgrows readability; never split by role.

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

## `infrastructure/orm/mappers.py` — Imperative Mapping Calls

All `mapper_registry.map_imperatively(...)` calls. Organise into one `run_<concept>_mapper()` function per concept; call all of them from `run_all_mappers()`, which `main.py` calls once during startup before any query runs.

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
