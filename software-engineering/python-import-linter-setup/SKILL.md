---
name: python-import-linter-setup
description: One-time setup of import-linter contracts (in pyproject.toml) for a NEW python-ddd project, so the layered architecture (presentation → application → domain, a framework-free domain, infrastructure that only implements ports) is enforced by `lint-imports` — and therefore CI — from the first commit. Use when bootstrapping a new Python DDD backend's architecture enforcement, or adding it to a Python service that has none.
vibe: Turns the DDD layering doc into a check that fails when an import points the wrong way.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.1"
---

# Python Import-Linter Architecture Setup

This is a **one-time setup skill**. It adds an `import-linter` contract set to
`pyproject.toml` that makes the layered architecture from `python-ddd` a thing
the build *checks*, not a thing people *remember*. A boundary written only in a
doc rots — someone does `from myapp.infrastructure.db import session` inside a
domain model in a hurry, review misses it, and six months later the domain
can't be tested without a database. Encoded as an import-linter contract, the
same mistake fails `lint-imports` and blocks the merge.

You do not hand-roll an AST scanner (that is what the Rust gate does, because
Rust has no equivalent tool). Python has the purpose-built tool: `import-linter`
builds the real import graph with `grimp` (static analysis — it parses, it does
**not** execute your code, so no database, broker, or services need to be
running) and checks declarative contracts. It follows re-exports and `__init__`
aggregation that a naive `grep` would miss.

This is the Python sibling of `frontend-vue-eslint-setup` (ESLint boundary
rules) and `rust-architecture-test-setup` (a `tests/structure/` cargo gate) —
same goal, ecosystem-native mechanism.

## When to use

- Bootstrapping a **new** python-ddd backend → enforce hard-fail from the first
  commit (a greenfield project has zero violations, so there is nothing to
  ratchet). This is the skill's default.
- Adding enforcement to an **existing** Python service that has none → see
  [Severity](#severity-new-project-vs-existing-codebase); `import-linter` is
  pass/fail with no "warn" tier, so you ratchet with `ignore_imports`.

Run this once. After the contracts exist in `pyproject.toml`, you do not re-run
this skill — you only edit the contract list as the architecture grows.

## What it enforces

The four-layer model from `python-ddd`, with dependencies pointing strictly
inward:

```
presentation  →  application  →  domain
                                    ▲
                  infrastructure ───┘   (implements the domain's ports)
```

- **`domain` depends on nothing** — not on the other layers, and not on any
  framework (SQLAlchemy, FastAPI, the DB driver). It is plain Python.
- **`application` depends on `domain`** (and may import the *concrete* Unit of
  Work / repositories from `infrastructure` as default-argument values — the one
  sanctioned inward exception in the skill).
- **`presentation` depends on `application` and `domain`** — never straight into
  `infrastructure`.
- **`infrastructure` implements the domain's ports** — it depends on `domain`
  and external libraries, never on `application` or `presentation`.

These encode separation of concerns and single responsibility: each layer has
one reason to exist, and the dependency arrows only ever point one way.

## Step 1 — Confirm your package root and layers

`import-linter` needs the importable root package and the layer sub-packages to
exist and be discoverable.

- **`root_package`** is whatever you `import` — often the distribution package
  (`myapp`), or literally `src` if the project uses a `src/` directory *as* the
  package (run `lint-imports` from the directory that contains it).
- The four layers are sub-packages: `myapp.presentation`, `myapp.application`,
  `myapp.domain`, `myapp.infrastructure`. Each needs an `__init__.py`.

If your project splits transport into separate `api/` (routers, middleware) and
`presentation/` (schemas, serializers) packages, that is a 5-layer variant — see
[Customization](#customization-knobs). The canonical four-layer set is below.

## Step 2 — Install import-linter

```bash
uv add --dev import-linter      # or: pip install import-linter
```

The CLI is `lint-imports`. With uv: `uv run lint-imports` (or, to try it without
committing the dependency first, `uv run --with import-linter lint-imports`).

## Step 3 — Add the contracts to `pyproject.toml`

Drop this in **verbatim**, then replace `myapp` with your `root_package` and tune
the framework list in contract 2 (Step-by-step reasons for every line are in
[Understanding the contracts](#understanding-the-contracts-so-you-can-adapt-them)).

```toml
[tool.importlinter]
root_package = "myapp"
include_external_packages = true   # required: contract 2 names external libraries

# 1. Layered architecture — dependencies point strictly inward.
#    Infrastructure is DELIBERATELY not in this chain (see "Understanding").
[[tool.importlinter.contracts]]
name = "Layered architecture (presentation -> application -> domain)"
type = "layers"
layers = [
    "myapp.presentation",
    "myapp.application",
    "myapp.domain",
]

# 2. The domain stays framework-free and never reaches into infrastructure.
[[tool.importlinter.contracts]]
name = "Domain is framework-free"
type = "forbidden"
source_modules = ["myapp.domain"]
forbidden_modules = [
    "myapp.infrastructure",
    # The project's infrastructure & transport libraries — TUNE THIS LIST.
    # NOT pydantic: domain commands / value objects may legitimately use it.
    "sqlalchemy",
    "fastapi",
    "httpx",
]

# 3. Infrastructure implements the domain's ports — it must not depend on the
#    layers above it. (infrastructure -> domain stays allowed.)
[[tool.importlinter.contracts]]
name = "Infrastructure depends only inward"
type = "forbidden"
source_modules = ["myapp.infrastructure"]
forbidden_modules = [
    "myapp.application",
    "myapp.presentation",
]

# 4. Presentation talks to application/domain — never straight into infrastructure.
#    allow_indirect_imports: presentation -> application -> infrastructure.uow is
#    the skill-sanctioned UoW default-arg chain, so only DIRECT leaks are flagged.
[[tool.importlinter.contracts]]
name = "Presentation never imports infrastructure directly"
type = "forbidden"
source_modules = ["myapp.presentation"]
forbidden_modules = ["myapp.infrastructure"]
allow_indirect_imports = true
```

## Step 4 — Run it and wire the gate

```bash
uv run lint-imports        # exits non-zero on any broken contract
```

Wire that command into whatever already runs your fast checks — a `just`
recipe, a Makefile target, a `pre-commit` hook — and into CI **next to `ruff`
and `mypy`**:

```bash
# justfile
lint-backend:
    uv run ruff check .
    uv run lint-imports          # <- the architecture gate
```

`lint-imports` is hermetic (static graph, no services), so it is a cheap CI job:
checkout → `uv sync` → `uv run lint-imports`. Without that CI step the contracts
only report locally and the boundary is not actually gated.

## Step 5 — Verify a contract actually fires

Do not trust a contract you have not seen break. Temporarily plant a violation,
run, confirm, revert:

```bash
# Add a forbidden import to any domain module, then lint:
echo "import sqlalchemy" >> myapp/domain/<some_module>.py
uv run lint-imports        # expect: "Domain is framework-free" BROKEN
git checkout -- myapp/domain/<some_module>.py
```

You should see contract 2 report the illegal `myapp.domain... -> sqlalchemy`
import. If it stays green, `root_package` is wrong or the layer package path
does not match — fix that before trusting the gate.

## Understanding the contracts (so you can adapt them)

Two contract types do all the work, and the split between them is the whole
trick:

- A **`layers`** contract is an ordered list, highest first. Higher layers may
  import lower ones; lower layers may **not** import higher ones. So
  `presentation > application > domain` forbids `domain → application`,
  `domain → presentation`, and `application → presentation` in one stroke.

- A **`forbidden`** contract says "modules in `source_modules` must not import
  anything in `forbidden_modules`" — direct *and* indirect, unless you set
  `allow_indirect_imports`.

**Why `infrastructure` is not in the `layers` chain.** This is the DDD wrinkle.
In dependency-flow terms infrastructure is the "lowest" layer (everything can
end up depending on it), so the naive move is to append it:
`presentation > application > domain > infrastructure`. That is **wrong** — a
`layers` contract lets higher layers import lower ones, so it would *permit*
`domain → infrastructure`, the exact thing you must forbid. Meanwhile
`application → infrastructure` (importing the concrete UoW as a default arg) must
stay *allowed*. You can't get both from one ordered chain. So infrastructure is
kept out of the chain and pinned with explicit `forbidden` contracts:
`domain ✗ infrastructure` (contract 2) and `infrastructure ✗ application,
presentation` (contract 3). `application → infrastructure` is forbidden nowhere,
so it stays legal.

**Why `include_external_packages = true`.** Contract 2 names external libraries
(`sqlalchemy`, `fastapi`) in `forbidden_modules`. `import-linter` refuses to run
a forbidden contract against external modules unless this top-level flag is set —
without it you get a hard error, not a silent pass.

**Why `allow_indirect_imports` on contract 4.** A presentation router imports an
application service, and that service imports `infrastructure.uow` for its
default argument (the sanctioned pattern). Following indirect imports, contract 4
would flag presentation for that legitimate transitive path —
`presentation → application → infrastructure.uow` — drowning the real signal.
`allow_indirect_imports = true` restricts the contract to **direct**
`presentation → infrastructure` imports, which are the genuine leaks (a router
opening a DB session itself instead of going through a service).

## Severity: new project vs. existing codebase

- **New project:** every contract hard-fails from commit one. A greenfield
  python-ddd project has zero violations, so there is nothing to soften — and
  `python-ddd` is greenfield-only by design.
- **Existing project with violations:** `import-linter` has no "warn" tier, so
  you ratchet differently. Turn on the `Domain is framework-free` contract first
  (usually closest to clean), and baseline the others with documented
  per-contract exceptions:

  ```toml
  ignore_imports = [
      "myapp.presentation.routers.auth -> myapp.infrastructure.db",  # TODO: route via auth service
  ]
  ```

  Run, fix violations, delete each `ignore_imports` line as you clear it, until
  the list is empty. Add a note to `CLAUDE.md`: "architecture is import-linted;
  do not add new `ignore_imports`." Never leave an unexplained `ignore_imports`
  permanently — a frozen exception is a boundary everyone has learned to ignore.

## Customization knobs

- **`root_package`** — set to the package you actually import (`myapp`, or `src`
  for a `src`-as-package layout). `lint-imports` must run from the directory that
  makes it importable.
- **The framework list (contract 2)** — list the project's real infrastructure
  and transport libraries: the ORM (`sqlalchemy`), web framework (`fastapi`), DB
  driver (`aiosqlite`, `asyncpg`), migration tool (`alembic`), message-broker
  client (`nats`, `aio_pika`), HTTP client (`httpx`), cloud SDKs. **Do not** list
  `pydantic` — the skill uses Pydantic for domain commands and value objects. Add
  it only if your project keeps the domain strictly dataclass-only.
- **5-layer variant (separate `api/` + `presentation/`).** If transport is split
  — `api/` (routers, middleware, app) above `presentation/` (schemas,
  serializers) — make `api` the top layer and forbid it from infrastructure too:

  ```toml
  layers = ["myapp.api", "myapp.presentation", "myapp.application", "myapp.domain"]
  # ...plus a 5th contract mirroring contract 4 for myapp.api:
  [[tool.importlinter.contracts]]
  name = "API never imports infrastructure directly"
  type = "forbidden"
  source_modules = ["myapp.api"]
  forbidden_modules = ["myapp.infrastructure"]
  allow_indirect_imports = true
  ```

  (Genuine composition wiring belongs in `main.py`, which sits outside the layer
  packages and is unaffected.)
- **Bounded contexts.** When the project splits into contexts (`myapp.billing`,
  `myapp.identity`), add an `independence` contract so they don't import each
  other, and/or repeat the layer contract per context.

## Compliance with the python-ddd & code-style skills

- This gate enforces `python-ddd` §1 (inward-only layer dependencies) and the
  framework-free domain. It does **not** restructure anything — it fails the
  build when an import violates the model you already chose.
- Pair it with `python-code-style` (run `ruff` + `mypy` alongside `lint-imports`).
- `import-linter` only sees **imports**. The judgment-residue invariants — domain
  models are dataclasses not Pydantic/`DeclarativeBase`, repository method naming
  (`get`/`find_by_`/`list_`), no god-methods, correct UoW usage, thin routers —
  are not import-shaped and need a review pass (the analog of the
  `rust-review` / `vue-review` subagents), not this gate.
