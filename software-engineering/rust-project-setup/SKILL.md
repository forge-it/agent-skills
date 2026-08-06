---
name: rust-project-setup
description: Guidelines for bootstrapping a Rust project with consistent toolchain pinning, plus cargo-make task automation for single-crate Rust-only projects. Use when starting a new Rust project. For a monorepo or any project with a non-Rust component, the task runner is `just` — see `justfile-setup`; this skill then owns only the toolchain pin.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.1.0"
---

# Rust Project Setup

This skill owns two things, and only the first applies to every Rust project:
**toolchain pinning** (always), and **cargo-make task automation** (only for a
single-crate, Rust-only project — see the scope note on that section).

## rust-toolchain.toml (CRITICAL)

Always use a `rust-toolchain.toml` file to pin the Rust toolchain version. This ensures consistent builds across all developers and CI environments.

### Required Configuration

Every Rust project should have a `rust-toolchain.toml` in the project root:

```toml
[toolchain]
channel = "stable"
```

### Why This Matters

- Ensures all team members use the same Rust version
- Guarantees CI/CD builds match local development
- Prevents "works on my machine" issues
- Automatically switches toolchain when entering the project directory (with rustup)

### Adding Components (Optional)

If your project requires additional components:

```toml
[toolchain]
channel = "stable"
components = ["rustfmt", "clippy"]
```

### Adding Targets (Optional)

For cross-compilation:

```toml
[toolchain]
channel = "stable"
components = ["rustfmt", "clippy"]
targets = ["wasm32-unknown-unknown"]
```

---

## Cargo Make (HIGH — single-crate, Rust-only projects only)

> **Scope gate — read this before adopting anything below.** Use cargo-make
> **only** when the project is a single crate with no non-Rust component. The
> moment there is a second component — a frontend, a Python service, a worker
> binary, anything a `cargo` task cannot drive — **the task runner is `just` at
> the repository root** (`justfile-setup`), and this section does not apply.
>
> Why: a task runner is a *command surface*, and a project gets one. Two runners
> means two vocabularies for the same actions, contributors learning which
> directory to stand in, and documentation that has to explain the split. `just`
> is language-agnostic, so it can own the whole surface; cargo-make is
> Rust-centric and cannot. `just` also finds the root justfile from any
> subdirectory, so the "I'm already inside the crate" ergonomics that favour
> `cargo make` largely disappear.
>
> What cargo-make genuinely does better, conceded: `install_crate` auto-installs
> a missing tool (`cargo-llvm-cov`, `sqlx-cli`) before a task runs; its
> `condition`, profile, and platform-variant support express things `just`
> cannot; and it needs no POSIX shell, which matters on Windows. If a
> single-crate project wants those, this section is the right answer. A polyglot
> monorepo pays a permanent second-surface cost for them.
>
> On a project that uses `just`, tasks needing to run inside a crate use a
> recipe that changes directory (`cd core && cargo sqlx prepare`) — not a second
> runner.

Use cargo-make as a task runner for build automation, testing, and deployment workflows.

### Task Categories

Organize tasks into logical categories:
- **Build tasks**: compilation, optimization, release builds
- **Test tasks**: unit tests, integration tests, test coverage
- **Deployment tasks**: packaging, containerization, deployment scripts
- **Utility tasks**: formatting, linting, cleanup

```toml
# Makefile.toml

# =============================================================================
# Build Tasks
# =============================================================================

[tasks.build]
description = "Build the project in debug mode"
command = "cargo"
args = ["build"]

[tasks.build-release]
description = "Build the project in release mode"
command = "cargo"
args = ["build", "--release"]

[tasks.build-docker]
description = "Build Docker image for the project"
script = ["docker build -t myapp:latest ."]

# =============================================================================
# Test Tasks
# =============================================================================

[tasks.test]
description = "Run all tests"
command = "cargo"
args = ["test"]

[tasks.test-integration]
description = "Run integration tests only"
command = "cargo"
args = ["test", "--test", "*", "--", "--test-threads=1"]

[tasks.test-coverage]
description = "Run tests with coverage report"
command = "cargo"
args = ["tarpaulin", "--out", "Html"]

# =============================================================================
# Utility Tasks
# =============================================================================

[tasks.format]
description = "Format code using rustfmt"
command = "cargo"
args = ["fmt"]

[tasks.lint]
description = "Run clippy lints"
command = "cargo"
args = ["clippy", "--", "-D", "warnings"]

[tasks.clean]
description = "Clean build artifacts"
command = "cargo"
args = ["clean"]

[tasks.check]
description = "Check code without building"
command = "cargo"
args = ["check"]
```

### Task Naming (CRITICAL)

Use clear, descriptive task names following kebab-case convention.

```toml
# Good - clear, kebab-case names
[tasks.build-release]
[tasks.test-integration]
[tasks.deploy-staging]
[tasks.deploy-production]
[tasks.check-format]

# Bad - unclear or inconsistent names
[tasks.buildRelease]
[tasks.test_int]
[tasks.DEPLOY]
[tasks.doit]
```

Standard naming patterns:
- Build: `build`, `build-release`, `build-docker`
- Test: `test`, `test-integration`, `test-coverage`
- Deploy: `deploy`, `deploy-staging`, `deploy-production`
- Utility: `format`, `lint`, `clean`, `check`

### Task Documentation (CRITICAL)

Each task should have a clear description explaining its purpose and any required preconditions.

```toml
[tasks.deploy-production]
description = "Deploy to production environment. Requires AWS_PROFILE to be set."
dependencies = ["test", "build-release"]
script = [
    "aws s3 sync ./target/release s3://production-bucket/"
]
```

### Task Dependencies

Use task dependencies to create logical workflows. Complex tasks should compose simpler tasks rather than duplicating logic.

```toml
[tasks.ci]
description = "Run full CI pipeline"
dependencies = [
    "format",
    "lint",
    "test",
    "build-release"
]

[tasks.pre-commit]
description = "Run checks before committing"
dependencies = [
    "format",
    "lint",
    "test"
]

[tasks.release]
description = "Prepare a release build"
dependencies = [
    "clean",
    "test",
    "build-release"
]
```

### Default Task

Define a sensible default task (typically `build` or `check`) that runs when `makers` is invoked without arguments.

```toml
[tasks.default]
description = "Default task - run check"
alias = "check"

# Or with dependencies
[tasks.default]
description = "Default task - format, lint, and test"
dependencies = ["format", "lint", "test"]
```

### Environment Variables

Use environment variables for configuration that varies between environments.

```toml
[env]
RUST_BACKTRACE = "1"
DATABASE_URL = { value = "postgres://localhost/dev", condition = { env_not_set = ["DATABASE_URL"] } }

[tasks.test-with-db]
description = "Run tests with database"
env = { DATABASE_URL = "postgres://localhost/test" }
command = "cargo"
args = ["test"]

[tasks.deploy-staging]
description = "Deploy to staging"
env = { ENVIRONMENT = "staging" }
script = ["./scripts/deploy.sh"]

[tasks.deploy-production]
description = "Deploy to production"
env = { ENVIRONMENT = "production" }
script = ["./scripts/deploy.sh"]
```

### Cross-Platform Support

Ensure tasks work across different platforms when possible. Use cargo-make's platform-specific task variants when necessary.

```toml
[tasks.open-docs]
description = "Open documentation in browser"

[tasks.open-docs.linux]
command = "xdg-open"
args = ["target/doc/myapp/index.html"]

[tasks.open-docs.mac]
command = "open"
args = ["target/doc/myapp/index.html"]

[tasks.open-docs.windows]
command = "cmd"
args = ["/c", "start", "target/doc/myapp/index.html"]
```

### Error Handling

Tasks should fail fast and provide clear error messages when something goes wrong.

```toml
[tasks.verify-env]
description = "Verify required environment variables are set"
script = [
    '''
    if [ -z "$DATABASE_URL" ]; then
        echo "ERROR: DATABASE_URL is not set"
        exit 1
    fi
    if [ -z "$API_KEY" ]; then
        echo "ERROR: API_KEY is not set"
        exit 1
    fi
    echo "Environment verified"
    '''
]

[tasks.deploy]
description = "Deploy application"
dependencies = ["verify-env", "build-release"]
script = ["./scripts/deploy.sh"]
```

### Cargo Make Anti-Patterns

1. **Undocumented tasks**: Tasks without descriptions
2. **Duplicated logic**: Copying commands instead of using dependencies
3. **Unclear names**: Vague or inconsistent task naming
4. **Missing defaults**: No default task defined
5. **Hardcoded values**: Environment-specific values hardcoded in tasks
6. **Platform assumptions**: Tasks that only work on one OS
