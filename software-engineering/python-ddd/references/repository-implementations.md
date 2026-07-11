# Repository Implementations — Concrete and Fake

This file contains the complete `SqlAlchemyProductRepository` and `FakeProductRepository` implementations. The normative rules governing repository design live in `software-engineering/python-ddd/SKILL.md` §4. Both implementations live together in `infrastructure/repository/products.py` in a real project; the abstract port they implement lives in `domain/repositories/products.py`.

## `SqlAlchemyProductRepository` — Concrete Infrastructure Adapter

Receives the `AsyncSession` from the Unit of Work via `__init__`. Never opens, commits, or closes the session — that is the UoW's responsibility. `add()` does not flush; the session tracks the change and the UoW persists it on commit.

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

## `FakeProductRepository` — In-Memory Fake for Tests

Satisfies the same abstract port. Used in service unit tests via `FakeUnitOfWork`. No database, no session — the state lives in a plain dict. Tests construct it with pre-populated products and assert on its state after the use case runs.

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
