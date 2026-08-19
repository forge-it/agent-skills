---
name: ci-setup
description: Use when bootstrapping CI for a new monorepo with Rust, Python, and Vue components — or when a project's advisory gates (local linters, architecture tests, import contracts) need to start failing the build instead of just printing warnings. Also use when any of these symptoms appear: architecture violations slip past review, lint warnings accumulate without consequence, a component type (Rust/Python/Vue) has no dedicated CI job, or pull requests merge without a single blocking quality check.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.5"
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
| Rust | `rust-check` | `just core-check` → clippy `-D warnings`, `fmt --check`, and `cargo test --workspace --test structure` (hexagonal layering) |
| Vue | `web-check` | `just web-check` → ESLint feature-architecture boundaries, format check, `vue-tsc` |
| Python | `python-check` | `just service-check` → `ruff format --check`, `ruff check`, `mypy`, `lint-imports`, and `pytest src/tests/architecture` (conventions gate: gate coverage and the interpreter floor) |

**Every job invokes a `just` recipe, never a raw command.** That is the whole
anti-drift mechanism: a gate can only be added, changed, or weakened in the
recipe, where the developer running it locally sees the same change. A CI file
that re-spells the commands is a second source of truth, and the two diverge
silently — which is the failure this skill exists to prevent. One job per
*component*, not per gate: a Rust formatting failure still cannot cancel the Vue
job, while a finer per-gate split would put the gate list back in this file.

The structure gate is documented in `rust-architecture-test-setup`.
The ESLint boundary rules are documented in `frontend-vue-eslint-setup`.
The import-linter contracts are documented in `python-import-linter-setup`.

These three skills install the local check; this skill makes it a build-breaker.

## Workflow template

The template below is a reference for a Rust + Python + Vue monorepo. Adapt job
names, package names (`-p <your-crate>`), and working-directory prefixes to match
your project, and delete the jobs for components your repository does not have —
that applies equally to all three stacks.

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

  rust-check:
    name: rust check
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
          components: rustfmt, clippy

      - name: Cache Rust artifacts
        uses: actions/cache@v4
        with:
          path: |
            ~/.cargo/registry/index/
            ~/.cargo/registry/cache/
            ~/.cargo/git/db/
            target/
          key: ${{ runner.os }}-check-${{ hashFiles('Cargo.lock') }}
          restore-keys: |
            ${{ runner.os }}-check-

      - name: Install just
        uses: taiki-e/install-action@v2
        with:
          tool: just

      - name: Quality gate
        # Exactly what a developer runs locally. clippy -D warnings, fmt --check,
        # and the hexagonal structure gate all live in the recipe, so CI cannot
        # drift from the local command by editing this file.
        run: just core-check

  # ── Vue ───────────────────────────────────────────────────────────────────

  web-check:
    name: web check
    runs-on: ubuntu-latest
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
        run: npm ci --prefix web

      - name: Install just
        uses: taiki-e/install-action@v2
        with:
          tool: just

      - name: Quality gate
        # ESLint feature-architecture boundaries, prettier check, vue-tsc.
        run: just web-check

  # ── Python ────────────────────────────────────────────────────────────────

  python-check:
    name: python check
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v8
        with:
          working-directory: service
          enable-cache: true
        # No python-version input: the action reads the pin from
        # service/.python-version, so the interpreter is a property of the
        # repository rather than of this workflow file.

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
        # ruff format --check, ruff check, mypy (no path — the manifest owns the
        # scope), lint-imports, and the conventions gate.
        run: just service-check
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

- One job per **component**, so a Rust failure never cancels the Vue job and
  reviewers see the exact failure domain.
- Not one job per **gate**. A finer split would have to name each gate here, which
  is precisely the second source of truth this skill exists to remove. The cost of
  collapsing is coarser attribution *within* a component; the recipe mitigates it
  by running cheapest-first, so a formatting slip still reports before the compile.
- Each job carries a single cache key, since there is now one Rust job rather than
  three racing to write the same key.

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

## Invoking just recipes (the anti-drift mechanism)

CI invokes `just` recipes, not raw commands — this is not an optional pairing but
the reason the workflow can be trusted. A gate can then only be added, changed, or
weakened in the recipe, where the developer running it locally sees the same
change. If a project has no task runner, install one (`justfile-setup`) before
wiring CI; a workflow that re-spells the commands is a second source of truth and
the two diverge silently.

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
| Sharing one cargo cache key across several Rust jobs | Parallel jobs race to write the same key; one job's cached artifacts corrupt another's | One Rust job, one key — or scope the key per job if you do split |
| Running integration tests in the same job as static analysis | Static-analysis jobs must not require external services; they become flaky when the Docker stack is slow | Separate jobs; gate integration tests behind a feature flag |
| Treating lint warnings as non-blocking | Warnings accumulate; once there are hundreds, no one fixes them | Set `lint` rules to `error` at the ESLint level and `-D warnings` in Clippy |
| Hardcoding the Rust toolchain version | The CI toolchain diverges from `rust-toolchain.toml`; different results locally vs. CI | Read the channel from `rust-toolchain.toml` at runtime (see template) |
| Installing architecture gates locally but not in CI | The gates are advisory — developers learn to ignore them | Every gate that runs locally must also run in CI with a non-zero exit on failure |
| Re-spelling gate commands in the workflow instead of invoking a recipe | The workflow becomes a second source of truth; a gate added locally is silently absent in CI, or weakened in CI without touching the recipe | Every job runs `just <component>-check`; the gate list lives in the recipe |
| Ordering a component's gates slowest-first | A formatting slip waits behind a full compile before reporting | Order the recipe cheapest-first (`fmt --check`, then clippy, then the structure gate) |

## Quick reference — CI jobs

| Job | Trigger | Blocking | Local equivalent |
|-----|---------|----------|-----------------|
| `rust-check` | push / PR | yes | `just core-check` |
| `web-check` | push / PR | yes (error-level rules) | `just web-check` |
| `python-check` | push / PR | yes | `just service-check` |
| integration tests | tag push (release) | yes (gates image build) | `just test-integration` with Docker stack |

## Cross-references

- `rust-architecture-test-setup` — installs the `tests/structure/` gate that
  `core-check` runs.
- `python-import-linter-setup` — installs the `lint-imports` contracts that
  `service-check` runs.
- `frontend-vue-eslint-setup` — installs the ESLint boundary rules that
  `web-check` runs.
- `justfile-setup` — owns every recipe these jobs invoke. A gate is only reachable
  from CI once it is in a recipe.
- `rust-testing` and `python-testing` — cover how to structure tests so the
  feature-flag split between unit and integration tests works correctly.
