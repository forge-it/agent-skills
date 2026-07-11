# Application Bootstrap — `main.py`

This file contains the complete `main.py` composition root. The normative rules governing bootstrap live in `software-engineering/python-ddd/SKILL.md` §13. This file lives at the project root (alongside `src/`) in a real project and is the **only** place that imports concrete implementations and wires them together.

## `main.py` — Composition Root

Order of operations in the lifespan startup: (1) `run_all_mappers()` before any query, (2) `run_migrations()` to align the database schema, (3) yield to serve requests. Exception handlers, routers, and the ASGI app are configured at module load time so they are available before the lifespan hook fires.

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
