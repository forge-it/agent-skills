---
name: ci-setup
description: Use when bootstrapping CI for a new monorepo with Rust, Python, and Vue components — or when a project's advisory gates (local linters, architecture tests, import contracts) need to start failing the build instead of just printing warnings. Also use when any of these symptoms appear: architecture violations slip past review, lint warnings accumulate without consequence, a component type (Rust/Python/Vue) has no dedicated CI job, or pull requests merge without a single blocking quality check.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.1"
---

# CI Setup

This is a **one-time setup skill**. It produces a GitHub Actions workflow that
makes every architectural and quality invariant blocking from the first commit
on a new monorepo.

The central idea: the per-language setup skills — `rust-architecture-test-setup`,
`python-import-linter-setup`, `frontend-vue-eslint-setup` — install local gates.
Those gates are **advisory until CI runs them**. A developer can ignore a failing
`cargo test --test structure` locally. CI cannot be ignored. This skill wires
all local gates into a workflow where each one either passes or blocks the merge.

Separation of concerns applies to the workflow itself: each component type gets
its own job. A Rust formatting failure does not cancel a Vue lint job that would
have passed independently. Reviewers see exactly which component broke.

## When to use

- Bootstrapping a **new** monorepo → wire every gate from commit 1. There are no
  existing violations, so hard-failing is free.
- Adding CI to an existing project → run the workflow against the current state
  first. Jobs that fail reveal the gap between the written rules and the actual
  codebase. Fix the violations before enabling blocking status checks, or mark the
  affected local gates advisory (see the individual setup skills) and schedule the
  cleanup.

Run this once. After the workflow exists and passes, you do not re-run the skill.

## What CI enforces (per component)

| Component | Job | Gates enforced |
|-----------|-----|----------------|
| Rust | `rust-fmt` | `cargo fmt --all -- --check` |
| Rust | `rust-clippy` | `cargo clippy --all-targets -- -D warnings` |
| Rust | `rust-structure` | `cargo test --test structure` (hexagonal layering) |
| Vue | `web-eslint` | `npm run lint` (feature-architecture boundary rules) |
| Python | _(add when present)_ | `lint-imports` + `ruff` + `mypy` |

The structure gate (`rust-structure`) is documented in `rust-architecture-test-setup`.
The ESLint boundary rules are documented in `frontend-vue-eslint-setup`.
The import-linter contracts are documented in `python-import-linter-setup`.

These three skills install the local check; this skill makes it a build-breaker.

## Workflow template

The template below is a reference for a Rust + Vue monorepo. Adapt job names,
package names (`-p <your-crate>`), and working-directory prefixes to match your
project.

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

env:
  CARGO_TERM_COLOR: always

jobs:

  # ── Rust ──────────────────────────────────────────────────────────────────

  rust-fmt:
    name: rustfmt
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Extract Rust toolchain version
        id: rust-toolchain
        run: echo "channel=$(grep 'channel' rust-toolchain.toml | sed 's/.*\"\(.*\)\".*/\1/')" >> "$GITHUB_OUTPUT"

      - name: Install Rust toolchain
        uses: dtolnay/rust-toolchain@master
        with:
          toolchain: ${{ steps.rust-toolchain.outputs.channel }}
          components: rustfmt

      - name: Check workspace formatting
        run: cargo fmt --all -- --check

  rust-clippy:
    name: clippy
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Extract Rust toolchain version
        id: rust-toolchain
        run: echo "channel=$(grep 'channel' rust-toolchain.toml | sed 's/.*\"\(.*\)\".*/\1/')" >> "$GITHUB_OUTPUT"

      - name: Install Rust toolchain
        uses: dtolnay/rust-toolchain@master
        with:
          toolchain: ${{ steps.rust-toolchain.outputs.channel }}
          components: clippy

      - name: Cache Rust artifacts
        uses: actions/cache@v4
        with:
          path: |
            ~/.cargo/registry/index/
            ~/.cargo/registry/cache/
            ~/.cargo/git/db/
            target/
          key: ${{ runner.os }}-clippy-${{ hashFiles('Cargo.lock') }}
          restore-keys: |
            ${{ runner.os }}-clippy-

      - name: Run Clippy (deny warnings)
        run: cargo clippy --all-targets --all-features -- -D warnings

  rust-structure:
    name: architecture (structure gate)
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Extract Rust toolchain version
        id: rust-toolchain
        run: echo "channel=$(grep 'channel' rust-toolchain.toml | sed 's/.*\"\(.*\)\".*/\1/')" >> "$GITHUB_OUTPUT"

      - name: Install Rust toolchain
        uses: dtolnay/rust-toolchain@master
        with:
          toolchain: ${{ steps.rust-toolchain.outputs.channel }}

      - name: Cache Rust artifacts
        uses: actions/cache@v4
        with:
          path: |
            ~/.cargo/registry/index/
            ~/.cargo/registry/cache/
            ~/.cargo/git/db/
            target/
          key: ${{ runner.os }}-structure-${{ hashFiles('Cargo.lock') }}
          restore-keys: |
            ${{ runner.os }}-structure-

      - name: Enforce hexagonal layering (tests/structure gate)
        # Hermetic: scans the source tree only — no database, no network.
        # Asserts inward-only layer dependencies, framework-free domain, and
        # file-naming conventions. Installed by rust-architecture-test-setup.
        run: cargo test --test structure

  # ── Vue ───────────────────────────────────────────────────────────────────

  web-eslint:
    name: web eslint
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: web
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Install Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "24"
          cache: npm
          cache-dependency-path: web/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Lint (ESLint feature-architecture boundaries)
        # Enforces the feature-architecture boundary rules installed by
        # frontend-vue-eslint-setup. Rules at "error" level block the build;
        # rules at "warn" are advisory until flipped to "error" after cleanup.
        run: npm run lint

  # ── Python (add when a Python component is present) ───────────────────────
  #
  # python-lint:
  #   name: python lint
  #   runs-on: ubuntu-latest
  #   steps:
  #     - uses: actions/checkout@v4
  #     - uses: actions/setup-python@v5
  #       with:
  #         python-version: "3.12"
  #     - run: pip install -e ".[dev]"
  #     - run: ruff check .
  #     - run: mypy .
  #     - run: lint-imports
  #       # lint-imports enforces the DDD layering contracts from
  #       # python-import-linter-setup. Exits non-zero on any breach.
```

## Dependency caching

Each job that compiles Rust uses `actions/cache@v4` with a key built from
`Cargo.lock`. The cache paths are:

```
~/.cargo/registry/index/
~/.cargo/registry/cache/
~/.cargo/git/db/
target/
```

`hashFiles('Cargo.lock')` ensures a lock-file change busts the cache. The
`restore-keys` fallback (`${{ runner.os }}-<job>-`) reuses the previous cache
on a miss rather than starting cold.

Each cache key is scoped to the job that builds it (`clippy`, `structure`, and
so on). This prevents a clippy build from polluting the structure gate's cache
and vice versa — the jobs can run in parallel without racing over a shared key.

Node caching is handled natively by `actions/setup-node@v4` via the `cache: npm`
option and the `cache-dependency-path` pointing at `web/package-lock.json`.

## Job structure rationale

Each component type owns exactly the jobs it needs and no others. This is
separation of concerns applied to the pipeline:

- `rust-fmt` runs in seconds with no compilation — it does not need the cargo
  cache. Splitting it from `rust-clippy` means a trivial formatting failure
  reports immediately without waiting for a full compile.
- `rust-clippy` and `rust-structure` each carry their own cache key so they can
  run in parallel without key collision. The structure gate is hermetic (source
  scan only, no external services) and therefore fast enough to always run on
  every push.
- `web-eslint` is completely independent of Rust. A Vue boundary violation does
  not interfere with Rust job status — reviewers see the exact failure domain.

## Integration tests and the local Docker stack

The jobs above are the **static-analysis and unit-test tier** — they run on every
push with no external services required.

Integration tests that require a live database, message broker, or object-store
are a separate concern. They typically run in a dedicated job that spins up the
full Docker Compose stack, waits for health checks, then runs the integration
suite behind a feature flag (e.g. `cargo test -p <your-crate> --features ci`). The
`--features ci` flag gates integration tests so `cargo test` without the flag runs
unit tests only — the local and CI experiences stay symmetrical. See the
`parallel_test_isolation_pattern` for the Docker stack and per-test isolation
behind this job.

If your project has integration tests:

1. Keep them in a separate job that explicitly starts and stops the Docker stack.
2. Gate them on a feature flag (e.g. `#[cfg(feature = "ci")]`) so they do not run
   in the static-analysis jobs.
3. Parallelise across fixtures (different source-database containers) using the
   same Docker Compose file, each in its own job, if test time demands it.

The release pipeline (triggered on `v*` tag pushes) builds and pushes Docker
images to a registry after the tests pass. That is a separate workflow file with
its own concerns — CI and release have no shared jobs.

## Pairing with just recipes

If the project uses `just` (see `justfile-setup`), the CI jobs should invoke the
same recipes that developers run locally. This keeps the local and CI experiences
identical:

```yaml
- name: Run Clippy (deny warnings)
  run: just clippy

- name: Enforce hexagonal layering
  run: just structure

- name: Lint Vue
  run: just web-lint
```

The `justfile` becomes the canonical definition of what each check does; the
workflow just invokes it. When the check changes (a new flag, a new package), the
change lives in one place.

## Adding new component types

When a new component type (a Python service, a second Vue application, a gRPC
gateway) is added to the monorepo, add a new job for it — do not extend an
existing job. Each component type is an independent unit of concern. A Python
linting failure should not cancel a Rust structure check that would have passed.

Template for a new component job:

```yaml
<component-name>-<check-name>:
  name: <human-readable name>
  runs-on: ubuntu-latest
  defaults:
    run:
      working-directory: <component-directory>
  steps:
    - name: Checkout code
      uses: actions/checkout@v4
    # ... toolchain setup, cache, then the single check command
```

## Common mistakes and anti-patterns

| Mistake | Why it is a problem | Fix |
|---------|---------------------|-----|
| One monolithic `test` job for all components | A single Vue lint failure cancels all Rust jobs; reviewers cannot tell which component broke | One job per component per concern |
| Sharing a single cargo cache key across jobs | Parallel jobs race to write the same key; one job's cached artifacts corrupt another's | Scope each key to the job (`-clippy-`, `-structure-`) |
| Running integration tests in the same job as static analysis | Static-analysis jobs must not require external services; they become flaky when the Docker stack is slow | Separate jobs; gate integration tests behind a feature flag |
| Treating lint warnings as non-blocking | Warnings accumulate; once there are hundreds, no one fixes them | Set `lint` rules to `error` at the ESLint level and `-D warnings` in Clippy |
| Hardcoding the Rust toolchain version | The CI toolchain diverges from `rust-toolchain.toml`; different results locally vs. CI | Read the channel from `rust-toolchain.toml` at runtime (see template) |
| Installing architecture gates locally but not in CI | The gates are advisory — developers learn to ignore them | Every gate that runs locally must also run in CI with a non-zero exit on failure |
| Putting `cargo fmt --check` inside the clippy job | Formatting failures are instantaneous; combining them delays the fast feedback | Separate `rust-fmt` and `rust-clippy` jobs |

## Quick reference — CI jobs

| Job | Trigger | Blocking | Local equivalent |
|-----|---------|----------|-----------------|
| `rust-fmt` | push / PR | yes | `cargo fmt --all -- --check` or `just fmt-check` |
| `rust-clippy` | push / PR | yes | `cargo clippy -- -D warnings` or `just clippy` |
| `rust-structure` | push / PR | yes | `cargo test --test structure` or `just structure` |
| `web-eslint` | push / PR | yes (error-level rules) | `npm run lint` or `just web-lint` |
| `python-lint` | push / PR | yes | `ruff check . && mypy . && lint-imports` |
| integration tests | tag push (release) | yes (gates image build) | `just test-integration` with Docker stack |

## Cross-references

- `rust-architecture-test-setup` — installs the `tests/structure/` gate that
  `rust-structure` runs.
- `python-import-linter-setup` — installs the `lint-imports` contracts that
  `python-lint` runs.
- `frontend-vue-eslint-setup` — installs the ESLint boundary rules that
  `web-eslint` runs.
- `justfile-setup` — the CI workflow can invoke `just` recipes so local and CI
  commands stay identical.
- `rust-testing` and `python-testing` — cover how to structure tests so the
  feature-flag split between unit and integration tests works correctly.
