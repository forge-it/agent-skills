# Unit of Work Implementations — Concrete and Fake

This file contains the complete `SqlAlchemyAsyncUnitOfWork` and `FakeUnitOfWork` implementations. The normative rules governing the Unit of Work live in `software-engineering/python-ddd/SKILL.md` §5. Both implementations live together in `infrastructure/unit_of_work.py` in a real project; the abstract port they implement lives in `domain/unit_of_work.py`.

## `SqlAlchemyAsyncUnitOfWork` — Concrete Infrastructure Adapter

Opens a session in `__aenter__`, instantiates every repository against that shared session, rolls back unconditionally in `__aexit__` (a prior `commit()` is unaffected), and closes the session on exit. `commit()` and `rollback()` delegate to the session directly.

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

## `FakeUnitOfWork` — In-Memory Fake for Tests

Satisfies the same abstract port. Accepts pre-populated fake repositories in its constructor. `committed` and `rolled_back` flags let tests assert that the use case persisted (or refused to persist) without touching a database.

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
