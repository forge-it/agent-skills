---
name: ci-setup
description: >-
  Use when bootstrapping CI for a new monorepo with Rust, Python, and Vue or
  React components — or when a project's advisory gates (local linters,
  architecture tests, import contracts) need to start failing the build instead
  of just printing warnings. Also use when any of these symptoms appear:
  architecture violations slip past review, lint warnings accumulate without
  consequence, a component type (Rust/Python/web) has no dedicated CI job, or
  pull requests merge without a single blocking quality check.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.9"
---

# CI Setup

This is a **one-time setup skill**. It produces a GitHub Actions workflow that
makes every architectural and quality invariant blocking from the first commit
on a new monorepo.

The per-language setup skills — `rust-architecture-test-setup`,
`python-import-linter-setup`, `frontend-vue-eslint-setup` — install local gates.
Those gates are **advisory until CI runs them**: a developer can ignore a failing
`cargo test --test structure` locally; CI cannot be ignored. `agent-hooks-setup`
is the other half of the same idea — the per-commit echo of these gates on the
agent's machine — and it is bypassable by design, so it does not replace this.

Two rules shape the workflow, and everything below follows from them:

- **Every job invokes a `just` recipe, never a raw command.** A gate can then only
  be added, changed, or weakened in the recipe, where the developer running it
  locally sees the same change. A workflow that re-spells the commands is a second
  source of truth, and the two diverge silently. If the project has no task runner,
  install one first (`justfile-setup`) and use the recipe names it actually
  defines: a step naming a recipe that does not exist fails at the first run,
  which is the cheap failure.
- **One job per component, not per gate.** A Rust formatting failure never cancels
  a web lint job that would have passed, and reviewers see which component broke.
  A finer per-gate split would have to name each gate here, which is exactly the
  second source of truth the first rule removes. The cost is coarser attribution
  within a component, and a fail-fast recipe reports only its first failure; the
  recipe running cheapest-first shortens time-to-first-failure, and if the second
  round-trip bites, make the recipe record every failure and exit non-zero at the
  end.

## When to use

- Bootstrapping a **new** monorepo → wire every gate from commit 1. There are no
  existing violations, so hard-failing is free.
- Adding CI to an existing project → run the workflow against the current state
  first. Jobs that fail reveal the gap between the written rules and the actual
  codebase. Fix the violations before enabling blocking status checks, or mark the
  affected local gates advisory (see the individual setup skills) and schedule the
  cleanup.

Run this once. After the workflow exists and passes, you do not re-run the skill.

## What CI enforces

| Component | Job | Recipe | Gates, cheapest first |
|-----------|-----|--------|-----------------------|
| Rust | `rust-check` | `just core-check` | `fmt --all --check`, `clippy --all-targets --all-features -D warnings`, `cargo test --workspace --test structure` (hexagonal layering; workspace-wide so no crate is left unchecked) |
| Web — Vue or React | `web-check` | `just web-check` | ESLint feature-architecture boundaries, format check, `vue-tsc` or `tsc` |
| Python | `python-check` | `just service-check` | `ruff format --check`, `ruff check`, `basedpyright`, `lint-imports`, `pytest tests/architecture` (conventions gate: gate coverage and the interpreter floor) |
| All | `integration` | `just test-all` | Unit and integration suites against the local Docker stack, after the three static jobs pass |

The structure gate is documented in `rust-architecture-test-setup`, the
import-linter contracts in `python-import-linter-setup`, and the ESLint boundary
rules in `frontend-vue-eslint-setup`; a React project mirrors that ESLint setup
with `typescript-eslint` and `tsc --noEmit` until a React setup skill exists.
Those skills install the local check; this skill makes it a build-breaker.

## Workflow template

A reference for a Rust + Python + web monorepo. Adapt job and recipe names, and
delete the jobs for components the repository does not have. Crate selection and
directory handling live in the recipes, not here. Every toolchain is read from
the repository's own pin — `rust-toolchain.toml`, `service/.python-version` — so
the workflow never states a version the repository does not; Node has no pin
file in this layout, so the workflow names the current Active LTS (24 today; 26
becomes LTS on 2026-10-28).

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

# Least privilege for GITHUB_TOKEN; a job that needs more declares it itself.
permissions:
  contents: read

# A new push to the same pull request cancels the run it supersedes.
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

env:
  CARGO_TERM_COLOR: always

jobs:

  # ── Rust ──────────────────────────────────────────────────────────────────

  rust-check:
    name: rust check
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v7

      - name: Install Rust toolchain
        # Reads channel and components from rust-toolchain.toml when no
        # `toolchain` input is given, and configures Swatinem/rust-cache: keyed
        # by toolchain and lockfile, target/ pruned so the cache stays useful.
        uses: actions-rust-lang/setup-rust-toolchain@v2

      - name: Install just
        uses: taiki-e/install-action@v2
        with:
          tool: just

      - name: Quality gate
        run: just core-check

  # ── Web ───────────────────────────────────────────────────────────────────

  web-check:
    name: web check
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v7

      - name: Install Node.js
        uses: actions/setup-node@v7
        with:
          node-version: "24"
          cache: npm
          cache-dependency-path: web/package-lock.json

      - name: Install dependencies
        run: npm ci --prefix web

      - name: Install just
        uses: taiki-e/install-action@v2
        with:
          tool: just

      - name: Quality gate
        run: just web-check

  # ── Python ────────────────────────────────────────────────────────────────

  python-check:
    name: python check
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v7

      - name: Install uv
        # setup-uv publishes no moving major tag past v7: pin the full version
        # (or the commit SHA its README shows). No python-version input: the
        # action reads service/.python-version.
        uses: astral-sh/setup-uv@v10.2.0
        with:
          working-directory: service
          enable-cache: true

      - name: Install dependencies
        # --locked fails the job if uv.lock no longer matches the manifests.
        # Never `pip install -e ".[dev]"`: dev tooling is not an extra, and pip
        # writes into an environment the lockfile is meant to describe.
        # See python-project-setup.
        run: cd service && uv sync --locked

      - name: Install just
        uses: taiki-e/install-action@v2
        with:
          tool: just

      - name: Quality gate
        run: just service-check

  # ── Integration ───────────────────────────────────────────────────────────

  integration:
    name: integration tests
    runs-on: ubuntu-latest
    # Cheapest first across jobs too: a formatting slip should not pay for a
    # Docker stack. The price is later feedback on a change that passes static.
    needs: [rust-check, web-check, python-check]
    steps:
      - name: Checkout code
        uses: actions/checkout@v7

      - name: Install Rust toolchain
        uses: actions-rust-lang/setup-rust-toolchain@v2

      - name: Install Node.js
        uses: actions/setup-node@v7
        with:
          node-version: "24"
          cache: npm
          cache-dependency-path: web/package-lock.json

      - name: Install web dependencies
        run: npm ci --prefix web

      - name: Install uv
        uses: astral-sh/setup-uv@v10.2.0
        with:
          working-directory: service
          enable-cache: true

      - name: Install Python dependencies
        run: cd service && uv sync --locked

      - name: Install just
        uses: taiki-e/install-action@v2
        with:
          tool: just

      - name: Start the test stack
        run: just dev-test-stack-up

      - name: Tests
        # Unit and integration suites for every component. Readiness waits and
        # per-test isolation live in the test support, not in this file — see
        # parallel_test_isolation_pattern.
        run: just test-all

      - name: Stop the test stack
        if: always()
        run: just dev-test-stack-down
```

## Caching

Each toolchain action owns its cache, keyed by the file that decides its
contents: `setup-rust-toolchain` delegates to `Swatinem/rust-cache` (toolchain
plus `Cargo.lock`, with `target/` pruned); `setup-node` keys on
`web/package-lock.json`; `setup-uv` keys on `uv.lock`. There is nothing to
hand-roll, and one job per component means one cache per component. If you ever
split a component across jobs, give each job its own `cache-key`: two jobs
saving under one key do not corrupt each other — the second save is simply
rejected — but neither benefits from the other's work.

## Integration tests and the local Docker stack

The three `*-check` jobs are the static-analysis tier: no external services, so
they can never be flaky for infrastructure reasons. The `integration` job is the
one place the Docker Compose stack runs in CI. It calls the same recipes a
developer runs — `dev-test-stack-up`, `test-all`, `dev-test-stack-down` — and
nothing else: readiness waits, per-test databases, and port allocation belong to
the test support and the isolation pattern, which is what makes the suite safe to
run in parallel on a CI runner. It runs on the same pull-request and push
triggers as the static tier, so a change cannot merge on static checks alone.

The release pipeline (triggered on `v*` tag pushes) builds and pushes Docker
images after CI has passed. That is a separate workflow file with its own
concerns — CI and release have no shared jobs.

## Adding a component

A new component type — a second service, another web application, a gRPC
gateway — gets a job of its own, named for the component, that installs its
toolchain and runs its `<component>-check` recipe, which you add in
`justfile-setup` first:

```yaml
<component>-check:
  name: <component> check
  runs-on: ubuntu-latest
  steps:
    - name: Checkout code
      uses: actions/checkout@v7
    # ... toolchain setup for that component
    - name: Install just
      uses: taiki-e/install-action@v2
      with:
        tool: just
    - name: Quality gate
      run: just <component>-check
```

Add its test recipe to `test-all`; the `integration` job picks it up without a
workflow change.

## Common mistakes

| Mistake | Why it is a problem | Fix |
|---------|---------------------|-----|
| Running integration tests inside a static job | The static tier must not need external services; it turns flaky when the stack is slow | Keep them in the `integration` job |
| Treating lint warnings as non-blocking | Warnings accumulate; once there are hundreds, nobody fixes them | ESLint rules at `error`, Clippy with `-D warnings` |
| Stating a toolchain version in the workflow | CI diverges from the repository's pin; different results locally and in CI | Read it from `rust-toolchain.toml` and `.python-version`; name only what the repository has no pin for |
| Pinning a third-party action to a major tag that does not exist | The run fails before the first step | Check the action's published refs; some, like `setup-uv`, publish only full versions and SHAs |
| Wiring a `local-<component>-deploy-check` recipe into a CI job, `test-all`, or `<component>-check` | Its precondition — a running local-prod deploy — is normally absent, so the job fails for a reason unrelated to the change, and the recipe gets weakened until it passes | A deployment check is not a gate: a gate's precondition is the source tree, which CI always has; this one's precondition is a running deploy, which CI does not. Deployment checks are operator-invoked only (`patterns/testing/deployment_check_pattern.md`). CI calls `test-all` and the `<component>-check` recipes and nothing from the deploy family |

## Quick reference

| Job | Trigger | Blocking | Local equivalent |
|-----|---------|----------|------------------|
| `rust-check` | push / PR | yes | `just core-check` |
| `web-check` | push / PR | yes | `just web-check` |
| `python-check` | push / PR | yes | `just service-check` |
| `integration` | push / PR, after the three above | yes | `just dev-test-stack-up && just test-all` |

## Cross-references

- `justfile-setup` — owns every recipe these jobs invoke. A gate is only reachable
  from CI once it is in a recipe.
- `agent-hooks-setup` — the per-commit echo of these gates on the agent's
  machine; bypassable, so CI stays the authority.
- `rust-architecture-test-setup` — installs the `tests/structure/` gate that
  `core-check` runs.
- `python-import-linter-setup` — installs the `lint-imports` contracts that
  `service-check` runs.
- `python-project-setup` — pins and configures, in `pyproject.toml`, the `ruff`
  and `basedpyright` gates that `service-check` runs.
- `frontend-vue-eslint-setup` — installs the ESLint boundary rules that
  `web-check` runs.
- `patterns/testing/parallel_test_isolation_pattern.md` — what makes `test-all`
  safe to run in parallel on a CI runner.
- `rust-testing` and `python-testing` — the test layout and support structure
  the `integration` job relies on.
