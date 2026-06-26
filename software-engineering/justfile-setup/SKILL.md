---
name: justfile-setup
description: Use when bootstrapping a new monorepo that mixes Rust, Python, and/or Vue components and has no task-runner yet — or when a project already has ad-hoc scripts scattered across components and needs a single root-level entry point. Also use when CI keeps drifting out of sync with local commands, when contributors ask "how do I run the dev stack?", or when a new component is added and the existing dev/test/lint/prod recipe set needs extending.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.1"
---

# Justfile Setup

This is a **one-time setup skill**. It produces a single root `justfile` that
becomes the project's entry point for every routine task — dev loop, local-prod
stack, quality gate, and workspace test. The goal is the same as the architecture
gate skills: encode a convention once so contributors don't have to remember it.

A justfile is the right home for this because each recipe has **one
responsibility**: either it delegates to a component's own toolchain (`cargo`,
`uv`, `pnpm`) or it orchestrates the Docker Compose stack. When a recipe tries to
do both, it breaks the first principle — split it.

Run this skill once when a new monorepo is created. After the root `justfile`
exists, extend it by adding new recipes; do not re-run the skill.

## When to use

- **New monorepo** — wire the dev/test/lint/prod taxonomy from commit 1 so there
  is never a period where contributors invoke tooling differently per component.
- **Existing project with ad-hoc scripts** — consolidate scattered `Makefile`
  targets, `package.json` scripts called from the root, and bare `cargo`/`uv`
  commands into a single authoritative entry point.
- **New component added** — extend the existing `justfile` with the new
  component's dev/test/lint/prod recipes following the taxonomy below.

## What this skill produces

One file: `justfile` at the repository root.

The file is divided into clearly marked sections — one per concern. A project
that uses only Rust and Vue omits the Python section entirely; a Python-only
service omits the Rust and Vue sections. Each section is self-contained.

## Recipe taxonomy

Every recipe belongs to exactly one of the following categories. If a recipe
spans two categories, break it into two recipes and have the outer one call both.

| Category | Purpose | Recipe names |
|---|---|---|
| **Environment bootstrap** | Copy `.env.template` → `.env` when missing | `<component>-env` |
| **Network** | Create/destroy the shared Docker network | `local-deploy-network-up`, `local-deploy-network-down` |
| **Dev stack** | Start the full dev environment (all components + Docker deps) | `dev-up`, `dev-down` |
| **Per-component dev** | Start one component in isolation | `dev-<component>-up` |
| **Quality gate** | Lint, format-check, type-check for one component | `<component>-check` |
| **Test** | Run tests for one component | `dev-<component>-test` |
| **Full test** | Run every component's tests in sequence | `test-all` |
| **Format** | Apply auto-formatting | `fmt`, `fmt-rust`, `fmt-web`, `fmt-python` |
| **Local-prod deploy** | Build + run via Docker Compose with a prod-like config | `local-deploy-up`, `local-deploy-down`, `local-<component>-deploy-up/down` |
| **Production build** | Build the final Docker image for shipping | `prod-<component>-build` |
| **Utilities** | One-off helpers (key generation, client installs, etc.) | freeform names |

### Naming rules

- Names are lowercase, hyphen-separated, no abbreviations: `dev-core-up` not
  `dcu`; `local-web-deploy-up` not `lwdu`.
- A per-component recipe always embeds the component name: `dev-core-up`,
  `dev-web-up`, `dev-worker-up`.
- The `test-all` recipe is the single recipe CI calls for the full suite. It
  calls the per-component `dev-<component>-test` recipes in sequence. CI calls
  `test-all`; humans call whichever component test they need.

## Environment-file conventions

Each component has its own `.env` file that is **never committed** (`.gitignore`
it). The pattern used in ironbox, and the one to replicate:

| File | Purpose | Committed? |
|---|---|---|
| `<component>/.env.template` | Canonical list of required variables with safe defaults or blank values | Yes |
| `<component>/.env` | Developer's local values, never committed | No |
| `<component>/.env.deploy.local` | Values for the local-prod Docker Compose stack | No |

The `<component>-env` recipe creates `.env` from the template only when it does
not already exist:

```just
core-env:
  @if [ ! -f core/.env ]; then cp core/.env.template core/.env; fi
```

The leading `@` suppresses `just`'s default echo of the command line. Use it on
one-liner shell commands so the output stays clean; omit it on multi-line
`#!/usr/bin/env bash` recipes so contributors can see what ran.

## The template

The template below covers a monorepo with three components: a Rust backend
(`core`), a Vue frontend (`web`), and a Rust async worker (`worker`). Remove the
sections that do not apply. Each section is marked with a comment indicating
which stack it belongs to.

```just
set shell := ["bash", "-cu"]

# ── Default ──────────────────────────────────────────────────────────────────

default:
  @just --list

# ── Network (shared Docker network for local-prod stacks) ────────────────────

local-deploy-network-up:
  @docker network inspect <project>-local >/dev/null 2>&1 \
    || docker network create <project>-local >/dev/null

local-deploy-network-down:
  @docker network rm <project>-local >/dev/null 2>&1 || true

# ── Environment bootstrap ────────────────────────────────────────────────────

# [rust] core component
core-env:
  @if [ ! -f core/.env ]; then cp core/.env.template core/.env; fi

# [vue] web component
web-env:
  @if [ ! -f web/.env ]; then cp web/.env.template web/.env; fi

# [rust] worker component
worker-env:
  @if [ ! -f worker/.env ]; then cp worker/.env.template worker/.env; fi

# [python] python service component — replace `service` with actual directory name
service-env:
  @if [ ! -f service/.env ]; then cp service/.env.template service/.env; fi

# ── Dev/test Docker stack ────────────────────────────────────────────────────

dev-test-stack-up:
  docker compose -f core/docker/docker-compose.yaml up -d

dev-test-stack-down:
  docker compose -f core/docker/docker-compose.yaml down

# ── Per-component dev (run one component at a time) ──────────────────────────

# [rust] Start the core Rust service
dev-core-up:
  just core-env
  cd core && SERVICE_PORT="${SERVICE_PORT:-8700}" cargo run

# [vue] Start the Vue dev server (Vite HMR)
dev-web-up:
  just web-env
  npm --prefix web run dev

# [rust] Start the worker — must cd so dotenvy finds worker/.env
dev-worker-up:
  just worker-env
  cd worker && cargo run

# [python] Start the Python service
dev-service-up:
  just service-env
  cd service && uv run python -m <package_name>

# ── Full dev-up (all components + Docker deps) ───────────────────────────────

dev-up:
  #!/usr/bin/env bash
  set -euo pipefail
  CLEANED_UP=0
  cleanup() {
    if [ "$CLEANED_UP" -eq 1 ]; then return; fi
    CLEANED_UP=1
    kill "${CORE_PID:-}" "${WEB_PID:-}" "${WORKER_PID:-}" 2>/dev/null || true
    wait "${CORE_PID:-}" 2>/dev/null || true
    wait "${WEB_PID:-}" 2>/dev/null || true
    wait "${WORKER_PID:-}" 2>/dev/null || true
    just dev-test-stack-down
  }

  just dev-test-stack-up
  just core-env
  just web-env
  just worker-env

  # [rust] core — start in background
  (cd core && exec env SERVICE_PORT="${SERVICE_PORT:-8700}" cargo run) &
  CORE_PID=$!

  # [vue] web — start in background
  (exec npm --prefix web run dev) &
  WEB_PID=$!

  trap cleanup EXIT
  trap 'exit 0' INT
  trap 'exit 143' TERM

  # [rust] worker — wait until core's gRPC port answers before starting,
  # because the worker fails fast when the broker/gRPC control plane is
  # unreachable. Adjust the port to match your project's gRPC listen port.
  for _ in $(seq 1 120); do
    if (echo > /dev/tcp/127.0.0.1/8704) 2>/dev/null; then break; fi
    sleep 1
  done
  (cd worker && exec cargo run) &
  WORKER_PID=$!

  wait

dev-down:
  just dev-test-stack-down
  pkill -x <project>-core   || true
  pkill -x <project>-worker || true
  pkill -f "node .*/web/node_modules/.bin/vite" || true

# ── Quality gate (lint + format-check + type-check) ─────────────────────────

# [vue] Run eslint + prettier-check + vue-tsc — run before every commit
web-check:
  npm --prefix web run lint
  npm --prefix web run format:check
  npm --prefix web run check

# [python] Run ruff + mypy + import-linter — run before every commit
service-check:
  cd service && uv run ruff check .
  cd service && uv run mypy .
  cd service && uv run lint-imports

# [rust] cargo clippy + fmt-check — run before every commit
core-check:
  cargo clippy -p <core-crate-name> -- -D warnings
  cargo fmt -p <core-crate-name> -- --check

# ── Tests ────────────────────────────────────────────────────────────────────

# [rust] core unit + integration tests
dev-core-test:
  just core-env
  cargo test -p <core-crate-name>

# [vue] type-check counts as the web test in CI
dev-web-test:
  just web-env
  npm --prefix web run check

# [rust] worker tests
dev-worker-test:
  just worker-env
  cargo test -p <worker-crate-name>

# [python] pytest suite
dev-service-test:
  just service-env
  cd service && uv run pytest

# Full workspace test — this is the single recipe CI calls
test-all:
  just dev-core-test
  just dev-web-test
  just dev-worker-test
  just dev-service-test

# ── Formatting (auto-fix) ────────────────────────────────────────────────────

fmt:
  just fmt-rust
  just fmt-web
  just fmt-python

# [rust] rustfmt across the whole workspace
fmt-rust:
  cargo fmt --all

# [vue] prettier write
fmt-web:
  npm --prefix web run format

# [python] ruff format
fmt-python:
  cd service && uv run ruff format .

# ── Local-prod deploy (Docker Compose, prod-like config) ─────────────────────

# [rust] core local-prod
local-core-deploy-up:
  just local-deploy-network-up
  docker compose -f core/docker/docker-compose.local.yaml up --build -d

local-core-deploy-down:
  docker compose -f core/docker/docker-compose.local.yaml down

# [vue] web local-prod
local-web-deploy-up:
  just local-deploy-network-up
  docker compose -f web/docker/docker-compose.local.yaml up --build -d

local-web-deploy-down:
  docker compose -f web/docker/docker-compose.local.yaml down -v

# [rust] worker local-prod
local-worker-deploy-up:
  just local-deploy-network-up
  docker compose -f worker/docker/docker-compose.local.yaml up --build -d

local-worker-deploy-down:
  docker compose -f worker/docker/docker-compose.local.yaml down -v

# Full local-prod stack — starts core, web, then waits for core's HTTP port
# before starting the worker (compose `depends_on` cannot cross projects)
local-deploy-up:
  #!/usr/bin/env bash
  set -euo pipefail
  just local-core-deploy-up
  just local-web-deploy-up
  for attempt in $(seq 1 60); do
    if curl -s -o /dev/null "http://localhost:<core-http-port>"; then break; fi
    if [ "$attempt" -eq 60 ]; then
      echo "core did not answer — not starting the worker" >&2
      exit 1
    fi
    sleep 2
  done
  just local-worker-deploy-up

local-deploy-down:
  just local-worker-deploy-down
  just local-web-deploy-down
  just local-core-deploy-down
  just local-deploy-network-down

# ── Production image builds ──────────────────────────────────────────────────

# [rust] Build the production Docker image for core
prod-core-build:
  docker build -f core/docker/Dockerfile -t <project>-core:latest .

# [vue] Build the production Docker image for web
prod-web-build:
  docker build -f web/docker/Dockerfile -t <project>-web:latest web

# [rust] Build the production Docker image for worker
prod-worker-build:
  docker build -f worker/docker/Dockerfile -t <project>-worker:latest .

# ── Utilities ────────────────────────────────────────────────────────────────

# [vue] Install node_modules (run once after clone or package.json change)
web-install:
  npm --prefix web install

generate-32-byte-key:
  python3 -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"

generate-random-key:
  python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Replace all `<project>`, `<component>`, `<package_name>`, `<core-crate-name>`,
`<worker-crate-name>`, `<core-http-port>` tokens with the actual names before
committing.

## How recipes orchestrate per-component tooling

| Component type | Dev command | Test command | Lint/check command |
|---|---|---|---|
| Rust (Cargo workspace) | `cargo run` (in component dir) | `cargo test -p <crate>` | `cargo clippy -p <crate>` |
| Vue 3 (Vite + pnpm/npm) | `npm --prefix web run dev` | `npm --prefix web run check` | `npm --prefix web run lint` |
| Python (uv + pytest) | `uv run python -m <pkg>` | `uv run pytest` | `uv run ruff check . && uv run lint-imports` |

The root `justfile` never invokes `cargo build` directly for dev — it calls
`cargo run` which rebuilds as needed. It never calls `vite build` for dev — it
calls `vite` (the dev server). Those distinctions are the component toolchain's
job; the justfile only names which NPM/cargo script to invoke.

## The `dev-up` pattern: startup ordering

When the full stack has an ordering dependency (e.g., the worker must not start
until the broker and gRPC server are reachable), encode it in `dev-up` directly.
The ironbox pattern: start `core` and `web` in background, then poll a TCP port
with `/dev/tcp` until core answers, then start the worker. Adjust the port to
match your project's gRPC or health-check port.

Do not poll HTTP in dev-up — `/dev/tcp` is a lighter probe and works before
Axum's HTTP listener is ready if gRPC binds first. In `local-deploy-up` (Docker
Compose), use `curl` against the public HTTP port because that proves the full
boot sequence completed.

## CI integration

CI calls exactly two recipes from this justfile:

1. `just test-all` — full workspace test suite
2. The per-component check recipes (`just web-check`, `just service-check`,
   `just core-check`) — quality gate

The architecture gate skills install what these recipes run:

- `rust-architecture-test-setup` adds `cargo test --test structure` which is
  called by `dev-core-test` (via `cargo test -p <crate>`).
- `python-import-linter-setup` adds `lint-imports` which is called by
  `service-check`.
- `frontend-vue-eslint-setup` wires the ESLint architecture rules which are
  called by `web-check`.

The `*-testing` skills (`rust-testing`, `python-testing`) define what lives
inside the test suites that `dev-<component>-test` invokes.

Keep CI in sync by having it call the justfile recipes — never hard-code
`cargo test` or `npm run check` directly in the CI YAML. When a recipe changes
the CI YAML does not need to change. See `ci-setup` for the CI side of this
contract.

## Common mistakes and anti-patterns

**1. A recipe that does two things**

```just
# Wrong — builds AND deploys; you cannot deploy without building
deploy:
  docker build -f core/docker/Dockerfile -t core:latest .
  docker compose up -d
```

Split it: `prod-core-build` builds; `local-core-deploy-up` deploys. When you
need both, call them in sequence from an orchestrating recipe.

**2. Missing `cd` for `dotenvy`**

A Rust component that loads `.env` via `dotenvy::dotenv()` at startup resolves
the path relative to the working directory at run time. If you invoke it from
the repository root with `cargo run -p <crate>`, `dotenvy` looks for `.env` in
the root and silently finds nothing. The fix:

```just
dev-worker-up:
  just worker-env
  cd worker && cargo run   # cd so dotenvy finds worker/.env
```

**3. Hard-coding absolute paths in `pkill` patterns**

```just
# Wrong — breaks on every other developer's machine
dev-down:
  pkill -f "node /home/alice/Projects/myapp/web/node_modules/.bin/vite"
```

Use a relative pattern that matches only the distinctive part:

```just
dev-down:
  pkill -f "node .*/web/node_modules/.bin/vite" || true
```

**4. Omitting `|| true` on `pkill` / `docker network rm`**

Both commands exit non-zero when the process or network does not exist. Without
`|| true`, `just` treats this as a failure and aborts the recipe.

**5. Calling `test-all` in dev-up**

`test-all` is for CI and explicit local testing. `dev-up` starts the stack; it
does not run tests. They are separate concerns.

**6. Per-component justfiles**

Do not create `core/justfile`, `web/justfile`, etc. A centralized root justfile
is the single source of truth for "how do I run this project". Per-component
files split that truth across multiple locations and require contributors to know
which directory to `cd` into before calling `just`.

**7. Putting Docker Compose logic inside component toolchain scripts**

`package.json` scripts and `Cargo.toml` build scripts should not start Docker.
That is the justfile's job. The component toolchain handles one concern; the
justfile handles orchestration.

## Quick reference

| Recipe | What it does |
|---|---|
| `just` | List all recipes |
| `just dev-up` | Start the full dev stack (all components + Docker deps) |
| `just dev-down` | Stop the full dev stack |
| `just dev-<component>-up` | Start one component in isolation |
| `just dev-<component>-test` | Run one component's tests |
| `just test-all` | Run every component's tests (CI entry point) |
| `just <component>-check` | Lint + format-check + type-check one component |
| `just fmt` | Auto-format all components |
| `just local-deploy-up` | Start the full local-prod Docker Compose stack |
| `just local-deploy-down` | Stop the local-prod stack |
| `just prod-<component>-build` | Build the production Docker image for one component |
| `just <component>-env` | Create `<component>/.env` from template if missing |
| `just web-install` | Install `web/node_modules` |
