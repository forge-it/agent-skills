# Validation Hierarchy — Complete Implementations

This file contains the complete validation hierarchy: the `Validation` ABC, a domain validation example, an application validation example, `BaseValidator`, and concrete validator examples. The normative rules governing this design live in `software-engineering/python-ddd/SKILL.md` §8. Each piece lives in its own file in a real project as shown.

## `Validation` ABC — `application/validations/common.py`

The base protocol for all validations. `execute()` raises on failure and returns `None` on success.

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

## Domain Validation — `domain/validations/licensing.py`

Pure business-rule check. Operates on a loaded domain object; no I/O, no repository access.

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

## Application Validation — `application/validations/licensing.py`

Rule that requires repository or gateway access. Opens its own UoW and closes it; does not share a transaction with the service.

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

## `BaseValidator` — `application/validators/base.py`

Knows how to run a sequence of validations. Does not know which validations apply to which use case — that is the concrete validator's job.

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

## Concrete Validators — `application/validators/licensing.py`

Each concrete validator knows which validations apply to one specific use case.

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
