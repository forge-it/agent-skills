# Canonical Directory Layout

This file contains the full annotated directory tree for a four-layer Python DDD project. The normative rules governing this layout live in `software-engineering/python-ddd/SKILL.md` under "Project Structure". Use this tree as the reference when creating a new project, adding a concept, or verifying the location of any piece.

## Annotated Tree

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
│   │   ├── licensing/
│   │   │   ├── products.py                # ProductCreationService, ProductRetrievalService, ...
│   │   │   └── addons.py
│   │   └── support/                       # a downstream context consuming iam via an ACL
│   │       ├── companies.py               # SupportCompanyService (depends on ACL ports)
│   │       └── customer_directory.py      # CustomerDirectory (ACL port) + IamCustomerDirectory + fake
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
│   │   ├── licensing.py                   # Pagination results, activation context
│   │   └── support.py                     # Read DTOs projected from other contexts (ACL output)
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
