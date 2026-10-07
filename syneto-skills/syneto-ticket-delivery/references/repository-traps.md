# Repository traps

What a brief for each repository must carry. Facts as of 2026-10-02. When a line disagrees
with the repository, the repository wins: fix this file in the same session.

`<repo>` is the main checkout. Its `.venv` also serves a linked worktree, and every gate runs
from the tree under test. Gate commands are CI's own, in their non-mutating form, so a
read-only final gate can run them; a command that rewrites files is marked as the writers'.

**Docker-backed suites** are shared infrastructure, run under SKILL.md's Docker rule (one
session at a time under `~/.cache/docker-tests.lock`, stack down at the end). The
orchestrator runs them, serially, never a worker, in the main worktree, after the merge-back
when there is a linked one (**parallel-worktrees-general**, *Test Safely*). The one exception
is rest-api in a linked worktree kept without a merge-back: see its *Linked worktree* line.
Docker is installed (since 2026-10-06). A shell started before his user joined the `docker`
group (`id -nG` has no `docker`) gets `permission denied` on `/var/run/docker.sock`: run
every command that reaches Docker through `sg docker -c "<command>"`, double quotes outside,
the pytest run of a Docker-backed tier included, because its fixtures call `docker compose`
themselves. Subagents inherit the same groups. Where `docker` is not on `PATH`, they cannot
run: the plan says "not runnable locally" where it would schedule one, and the stage 8
report lists it as not run, never as passed. Never install Docker yourself. The rest-api and
central-backend stacks share host ports (3306, 5672, 15672, 27017, 27018) and container
names (`mariadb`, `mongo-master`, `mongo-iam`, `rabbitmq-local-backend`), so only one can be
up at a time: when the other is up and you did not start it, ask him before taking it down.

## rest-api — `central/rest-api`

- **Stack:** Python, layered DDD. `python-*` agents; load python-ddd.
- **Gate**, from the root of the tree under test:
  `<repo>/.venv/bin/python -m pytest src/tests/unit && <repo>/.venv/bin/black src --check -l 120 && <repo>/.venv/bin/ruff check --no-fix src/central_rest_api src/tests`.
  Never a plain `ruff check`: `pyproject.toml` sets `fix = true`, so it edits files.
- **Linked worktree:** with SYN-3090's fix in the base (`central-2.10` since 2026-10-06;
  `git -C <worktree> grep -n PACKAGE_SRC_DIRECTORY -- src/central_rest_api/infrastructure/utils.py`
  prints a line), the unit gate runs from the worktree root as in the main checkout:
  `get_src_project_path()` follows the imported package, not the cwd's name. On a base
  without it, pytest must run from `<worktree>/src` with paths relative to `src/`
  (`tests/unit`): collection from the root dies with `StopIteration`. The Docker-backed tiers
  wait for the merge-back, except in a worktree he keeps without one, on a base with the fix,
  which is how SYN-3090 ran them: copy the gitignored `.env` in
  (`cp -n <repo>/.env <worktree>/.env`; every compose service reads it, and the dev dumps are
  tracked), then run `docker compose` and pytest from the worktree, both prefixed with
  `COMPOSE_PROJECT_NAME=rest-api`, so the stack has one project name whichever tree brings
  it up or down. Alembic then runs in-process and the e2e fixture starts the API with
  pytest's own interpreter. On an older base both go through `poetry run`, which builds an
  empty in-project `.venv` in the worktree: there they wait for the merge-back.
- **Docker-backed:** integration (`pytest src/tests/integration`) brings up `mariadb` and
  `minio`; e2e (`pytest src/tests/e2e`) brings up `mariadb` and `rabbitmq` and starts the API
  itself. The stack's containers: `mariadb`, `rabbitmq-local-backend`, `mongo-master`,
  `mongo-iam`, `mongo-serenity`, their `mongo_*_setup` containers, and minio, which has no
  fixed name (`<project>-minio-1`). The Mongo stores must run too: after the absence check,
  in every session, not once, bring them up with `docker compose up -d mongo-master
  mongo-master-setup mongo-iam mongo-iam-setup mongo-serenity mongo-serenity-setup minio`
  (each `-setup` container runs `rs.initiate`), so they come down with the rest. Never gate
  either tier on `docker ps` or `curl :8765`. The fixtures start their containers and never
  stop them (the `docker.compose.down` in `start_mariadb`,
  `src/tests/integration/conftest.py`, is commented out), so the teardown is yours. The e2e
  fixture first kills every process with a socket on port 8765 (`SERVICE_PORT`), SIGINT then
  SIGKILL: before an e2e run `lsof -i tcp:8765` must show nothing, or ask him. It stops its
  own API only when pytest reaches its teardown: after a killed run, check the port again.
- **Traps:** the unit tier's fake repository never runs SQL, and integration and e2e are not
  in CI. A query change therefore needs a compiled-SQL unit assertion and a real-MariaDB
  integration test, and the MR says which of the two actually ran. A new dismissible hub
  banner is a `BannerKey` enum member here, merged and deployed before the hub.

## central-backend — `central/central-backend`

- **Stack:** Python, not DDD. `python-*` agents; python-ddd does not apply.
- **Gate**, from the root of the tree under test:
  - Read-only: `<repo>/.venv/bin/python -m pre_commit run flake8 --files <changed central_backend/*.py>`,
    `uvx --from black==22.10.0 black --check -l 120 --target-version py310 <changed .py>` (the
    hook's pin; the venv's black 23.12.1 is stricter) and
    `<repo>/.venv/bin/ruff check --no-fix --ignore TCH001,TCH002 <changed .py>`.
  - Then `<repo>/.venv/bin/python -m pytest tests --ignore=tests/locking/integration`, with
    `.env` present (copied from `.env.template`).
  - When the change touches `central_backend/core` or `central_backend/licensing`, also CI's
    legacy suite, which `pytest` never collects:
    `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python <repo>/.venv/bin/python -m unittest $(find central_backend/core central_backend/licensing -name '*_test.py')`.
  - What CI runs first, `<repo>/.venv/bin/python -m pre_commit run --files <changed central_backend/*.py>`
    (the module is `pre_commit`), is the writers' only: its whitespace fixers, black and
    `ruff --fix` rewrite files. The writer runs it and reports
    `git status --short` afterwards.
  - Only `tests/locking/integration/` touches a store (MariaDB: `docker compose up -d
    mariadb`): Docker-backed. Every other category, `api/` and `assemblytests/` included, runs
    on `MagicMock` gateways and needs no store.
- **Venv:** pins Python 3.10, and its locked `mariadb` builds from source, which needs MariaDB
  Connector/C (`libmariadb-dev`, for `mariadb_config`); neither is on this machine. A venv
  needs both installed first, then `poetry env use <path>`.
- **Separate worktree:** its `*_pb2.py` / `*_grpc.py` are gitignored, so a linked worktree
  must generate them first (`separate-worktree.md`).
- **Traps:** no double-underscore attributes. Tests live in `tests/<domain>/<category>/`, plain
  pytest, never `unittest`.

## central-api — `central/central-api`

- **Stack:** Node 18.20.4 + TypeScript. No fleet agent: use general-purpose.
- **Node:** the shell's default node is 24, and `nvm` is not sourced, so yarn refuses the
  project's `engines`. Prefix every command, install and gate alike, with
  `PATH=$HOME/.nvm/versions/node/v18.20.4/bin:$PATH`. Never `--ignore-engines`.
- **Gate:** `yarn install --frozen-lockfile` when `node_modules` is missing, then
  `npm run test_unit` (compiles, then runs Jest over `build/`).
- **Traps:** the TypeScript `lib` is es2018, so no `Promise.allSettled`. The GitLab default
  branch is `central-2.9`: always set the MR target.

## central-iam — `central/central-iam`

- **Stack:** Node 12.22.12 + TypeScript, raw Mongo driver through kublar. No fleet agent:
  use general-purpose.
- **Node:** prefix every command, install and gate alike, with
  `PATH=$HOME/.nvm/versions/node/v12.22.12/bin:$PATH` (installed via nvm for SYN-3090).
- **Gate:** `npm ci` when `node_modules` is missing, then `npm run test-unit` (compiles,
  then runs the `*.test.js` built from the TypeScript sources). Baseline on 298358f was
  7 suites, 54 tests.
- **Traps:** `npm.syneto.eu` can answer 503 during `npm ci`; rerun once before sending an
  investigator. New indexes and schema work go in rest-api's `MONGO_INDEX_SPECS`
  (`src/central_rest_api/infrastructure/database/mongo_index_specs.py`), not here, even
  though central-iam's older repositories still create a few of their own on write.

## central-hub — `central/central-hub`

- **Stack:** React 18. `react-*` agents.
- **Install:** wherever `node_modules` is missing (always in a linked worktree), plain
  `npm ci` refuses (ERESOLVE: the lock's apollo-boost 0.4.9 accepts graphql up to 15, the
  lock has 16.6.0): use `npm ci --legacy-peer-deps`, never the README's
  `npm install --legacy-peer-deps`, which rewrites `package-lock.json`.
- **Gate:** `npm ci --legacy-peer-deps` when `node_modules` is missing, then `npx jest src/`
  (there is no `test` script; without `src/`, Jest picks up Cypress files).
- **Linked worktree:** with `"root": true` in `.eslintrc`
  (`central-2.10` since 2026-10-06, SYN-3090), ESLint stops at the worktree's own config and
  plain `npx eslint` works there (verified 2026-10-06). On a base without it, `npm run lint`
  aborts ("couldn't determine the plugin unused-imports uniquely") and the dev server shows
  the same conflict as a red overlay ('Plugin "unused-imports" was conflicted'), because
  ESLint climbs to the main checkout's copy; lint with
  `npx eslint --no-eslintrc -c .eslintrc "**/**/*.{js,jsx}"` (proven equivalent, 197 files).
- **Traps:** about 9 RAS deployment tests fail on a clean tree, so take the baseline first. The
  GitLab default branch is `central-2.9`: always set the MR target. The first pipeline on a new
  branch rebuilds the base and builder images, so a failure in those jobs is an image or
  apt-mirror problem, not the ticket's: the investigator curls the mirror before anything else.

## syneto-diana — `hyper/syneto-diana`

- **Stack:** Syneto OS Python. Implementor `python-implementor-syneto-expert`, which never
  commits and has no `-no-commit` variant; fixer `python-fixer-no-commit`.
- **Gate**, from the root of the tree under test:
  - `<repo>/.venv/bin/black --check . && <repo>/.venv/bin/ruff check --no-fix .`
  - CI's custom lint: `grep -rE --include='*.py' '(^|[^a-zA-Z])(List|Dict|Tuple|Set|FrozenSet|Type)\[' src/`
    must print nothing; use the builtin generics.
  - `make test` (about 11 minutes).
  - A single test file:
    `cd src && ROOT_PATH=/api/node OTEL_SDK_DISABLED=true <repo>/.venv/bin/python -m pytest tests/unit/<path>`.
    Both env vars are required, or OpenTelemetry can hang waiting for a collector.
  - In a linked worktree, `make test` goes through `poetry run`, so use the single-file form
    over `tests/unit` instead, from `<worktree>/src`.
- **Venv:** building it needs the private-index credentials described in `poetry.toml`.
- **Traps:**
  - **Never `make style` or `make lint`**: they reformat 282 files at line length 88 and call
    tools that are not installed.
  - Never commit `poetry.lock`.
  - `src/diana/api-docs/*.md` is served as the OpenAPI description, so a wrong sentence there
    ships to clients.

## central (deploy) — `infra/central`

- **Stack:** Pulumi Python. No fleet agent: use general-purpose.
- **Gate:** none locally.
- **Venv:** none, and none needed: stage 1 asks nothing about one, and its briefs carry no
  interpreter.
- **Traps:** the branch is the environment: only `dev-on-prem` and `production-on-prem` are
  live, the others are dead. New env vars copy how their neighbours get their values
  (per-environment helpers, `ServiceRegistry`), never per-branch literals.
