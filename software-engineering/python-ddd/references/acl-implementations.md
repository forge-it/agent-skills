# Anti-Corruption Layer Implementations

This file contains the complete ACL pattern: the consumer's read DTO, the capability port (`CustomerDirectory`), the concrete adapter (`IamCustomerDirectory`), the in-memory fake (`FakeCustomerDirectory`), and the consuming service (`SupportCompanyService`). The normative rules governing this design live in `software-engineering/python-ddd/SKILL.md` §10. All pieces live under the `support` context in a real project as shown.

## Read DTO — `application/dtos/support.py`

Application-owned projection of data from another context. This is **not** a domain model (the context does not own this entity) and **not** a schema (not wire-format). Named in the consumer's own language; `support_dtos.Company` and `iam.Company` coexist — module-qualified imports disambiguate.

```python
# application/dtos/support.py — read projections assembled from other contexts (ACL output)
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Company:                       # referenced as support_dtos.Company — NOT iam.Company
    id: str
    name: str
    vat_number: Optional[str] = None
    country: Optional[str] = None
    # Later: support contacts, products, maintenance status — Support's shape, not IAM's.
```

## Capability Port — `application/services/support/customer_directory.py`

Named for the capability in the consumer's language, not after the supplier. Returns the consumer's own DTO, never the upstream's model. Choosing `Directory` / `Reader` / `Lookup` (not `Repository`) signals read-only lookup of a foreign source.

```python
# application/services/support/customer_directory.py — the ACL port
import abc
from typing import Optional

from myapp.application.dtos import support as support_dtos


class CustomerDirectory(abc.ABC):
    """Support's read-only lookup of customer companies. Named for the capability,
    not for IAM — the supplier never appears in Support's own language."""

    @abc.abstractmethod
    async def find_company(self, company_id: str) -> Optional[support_dtos.Company]: ...
```

## Concrete Adapter and Fake — `application/services/support/customer_directory.py` (continued)

`IamCustomerDirectory` is the **only file in the `support` context allowed to import `iam.*`**. It opens the upstream UoW, reads through its repositories, and translates in a private method. `FakeCustomerDirectory` mirrors the fake-repository pattern from §4 — lets the consumer be tested with no upstream database.

```python
# application/services/support/customer_directory.py (continued) — the ACL adapter
from typing import Callable, Optional

from myapp.application.dtos import support as support_dtos
from myapp.domain.models import iam                       # the ONLY iam import in the support context
from myapp.domain.unit_of_work import AbstractUnitOfWork
from myapp.infrastructure.unit_of_work import SqlAlchemyAsyncUnitOfWork


class IamCustomerDirectory(CustomerDirectory):            # adapter MAY name the source
    def __init__(
        self,
        iam_unit_of_work_factory: Callable[[], AbstractUnitOfWork] = SqlAlchemyAsyncUnitOfWork,
    ):
        self._iam_unit_of_work_factory = iam_unit_of_work_factory

    async def find_company(self, company_id: str) -> Optional[support_dtos.Company]:
        async with self._iam_unit_of_work_factory() as unit_of_work:
            company = await unit_of_work.companies.find_by_id(company_id)
        return self._translate(company) if company is not None else None

    @staticmethod
    def _translate(company: iam.Company) -> support_dtos.Company:   # iam.Company stays in this file
        return support_dtos.Company(
            id=company.id,
            name=company.name,
            vat_number=company.vat_number,
            country=company.country,
        )


class FakeCustomerDirectory(CustomerDirectory):           # for unit-testing the consumer
    def __init__(self, companies: Optional[list[support_dtos.Company]] = None):
        self._companies = {company.id: company for company in (companies or [])}

    async def find_company(self, company_id: str) -> Optional[support_dtos.Company]:
        return self._companies.get(company_id)
```

## Consuming Service — `application/services/support/companies.py`

Depends on the **capability port** (`CustomerDirectory`), not the upstream or the adapter. Accepts the port via `__init__` (default the real adapter). Unit-testable with `FakeCustomerDirectory(companies=[...])` — no upstream database involved. When the support view spans several foreign contexts, compose additional ACL ports here.

```python
# application/services/support/companies.py
from typing import Optional

from myapp.application.dtos import support as support_dtos
from myapp.application.services.support.customer_directory import (
    CustomerDirectory,
    IamCustomerDirectory,
)


class SupportCompanyService:
    def __init__(self, customer_directory: Optional[CustomerDirectory] = None):
        self._customer_directory = customer_directory or IamCustomerDirectory()

    async def get_company(self, company_id: str) -> Optional[support_dtos.Company]:
        # When the support view is assembled from several sources, this method
        # composes them — e.g. a ProductsReader (another ACL port) merged into
        # the same support_dtos.Company. Each foreign source is its own port.
        return await self._customer_directory.find_company(company_id)
```
