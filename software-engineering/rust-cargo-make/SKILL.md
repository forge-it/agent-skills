---
name: rust-cargo-make
description: Cargo-make task runner best practices for Rust build automation
license: MIT
metadata:
  author: cristian.ciortea@proton.me
  version: "0.0.1"
---

# Cargo Make Skill

Version: 0.0.1

## Purpose

This skill provides guidelines for using cargo-make as a task runner for Rust projects. It focuses on task organization, naming conventions, and best practices for build automation, testing, and deployment workflows.

## When to Apply

Apply these guidelines when:
- Setting up cargo-make for a new Rust project
- Adding new build, test, or deployment tasks
- Organizing existing Makefile.toml tasks
- Working with CI/CD pipelines using cargo-make

## Core Principles

### 1. Task Categories (CRITICAL)

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

### 2. Task Naming (CRITICAL)

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

### 3. Task Documentation (CRITICAL)

Each task should have a clear description explaining its purpose and any required preconditions.

```toml
[tasks.deploy-production]
description = "Deploy to production environment. Requires AWS_PROFILE to be set."
dependencies = ["test", "build-release"]
script = [
    "aws s3 sync ./target/release s3://production-bucket/"
]
```

### 4. Task Dependencies (HIGH)

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

### 5. Default Task (HIGH)

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

### 6. Environment Variables (HIGH)

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

### 7. Cross-Platform Support (HIGH)

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

### 8. Error Handling (HIGH)

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

## Anti-Patterns to Avoid

1. **Undocumented tasks**: Tasks without descriptions
2. **Duplicated logic**: Copying commands instead of using dependencies
3. **Unclear names**: Vague or inconsistent task naming
4. **Missing defaults**: No default task defined
5. **Hardcoded values**: Environment-specific values hardcoded in tasks
6. **Platform assumptions**: Tasks that only work on one OS

## Guidelines

### Task Organization
- Group tasks by category with comments
- Use dependencies to compose complex workflows
- Keep individual tasks focused and simple
- Define a sensible default task

### Naming Conventions
- Use kebab-case for all task names
- Follow standard prefixes: build-, test-, deploy-, etc.
- Be descriptive but concise

### Documentation
- Every task needs a description
- Document required environment variables
- Note any preconditions or dependencies

### Environment Handling
- Use env section for configuration
- Support environment-specific overrides
- Never hardcode secrets or environment-specific values

### Cross-Platform
- Test tasks on all target platforms
- Use platform-specific variants when needed
- Prefer cross-platform commands when possible

### Error Handling
- Fail fast on errors
- Provide clear error messages
- Verify preconditions in dependent tasks
