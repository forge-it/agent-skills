# Agent Skills

A collection of curated skills for AI-assisted software development. Each skill provides focused guidelines that can be loaded into AI coding assistants to ensure consistent, high-quality output.

## What are Skills?

Skills are structured markdown files containing best practices, guidelines, and conventions for specific development tasks. They help AI assistants understand project-specific rules and produce code that matches your team's standards.

Each skill includes:
- **Purpose**: What the skill helps with
- **When to Apply**: Conditions that trigger the skill
- **Core Principles**: Prioritized guidelines (CRITICAL, HIGH)
- **Examples**: Code samples demonstrating correct usage
- **Anti-Patterns**: Common mistakes to avoid

## Available Skills

### Software Engineering

| Skill | Description |
|-------|-------------|
| [general-logging](software-engineering/general-logging/SKILL.md) | Wide events logging pattern for powerful debugging and analytics |
| [code-change-workflow](software-engineering/code-change-workflow/SKILL.md) | Execution discipline for code-changing tasks: inspect, proceed or ask, verify, report |
| [technical-design-discussions](software-engineering/technical-design-discussions/SKILL.md) | Design conversations: verify sources, weigh trade-offs, recommend, record ADRs |
| [git-workflow](software-engineering/git-workflow/SKILL.md) | Git branch naming, commits, and version control |
| [database-management](software-engineering/database-management/SKILL.md) | Database schema management and migration strategies |
| [python-code-style](software-engineering/python-code-style/SKILL.md) | Python code style for clean, maintainable code |
| [python-commands](software-engineering/python-commands/SKILL.md) | Python command-line interface best practices |
| [python-testing](software-engineering/python-testing/SKILL.md) | Python testing best practices using pytest |
| [rust-code-style](software-engineering/rust-code-style/SKILL.md) | Rust code style with hexagonal architecture |
| [rust-design-principles](software-engineering/rust-design-principles/SKILL.md) | SOLID, KISS, and design patterns for Rust |
| [rust-design-idioms](software-engineering/rust-design-idioms/SKILL.md) | Rust design idioms including newtype pattern and error handling |
| [rust-project-setup](software-engineering/rust-project-setup/SKILL.md) | Rust project setup with toolchain and cargo-make |
| [rust-hexagonal-architecture](software-engineering/rust-hexagonal-architecture/SKILL.md) | Hexagonal architecture (ports and adapters) for Rust |
| [rust-testing](software-engineering/rust-testing/SKILL.md) | Rust testing best practices using cargo test |

> **Note:** the table above lists the original core skills only. The repository also contains setup skills, structure-and-style guard skills, Python DDD, and Vue skills not yet enumerated here.

### Greenfield Project Setup

Start a new project with [`greenfield-project-setup`](software-engineering/greenfield-project-setup/SKILL.md) — a thin orchestrator that brings up a python+vue, rust+vue, or combination monorepo correctly from commit 1. It detects the stack, walks an ordered phase sequence, delegates each phase to the skill or pattern that owns it, and runs a verification gate after each so a missing invariant fails at setup rather than months later.

It sequences these **one-shot setup skills** (each installs an invariant from commit 1):
[`rust-workspace-setup`](software-engineering/rust-workspace-setup/SKILL.md) ·
[`justfile-setup`](software-engineering/justfile-setup/SKILL.md) ·
[`ci-setup`](software-engineering/ci-setup/SKILL.md) ·
[`agent-hooks-setup`](software-engineering/agent-hooks-setup/SKILL.md)
— alongside the existing `rust-architecture-test-setup`, `python-import-linter-setup`, `frontend-vue-eslint-setup`, and `rust-project-setup`.

## Patterns

Language-agnostic backend / full-stack architecture patterns — each a concrete worked example (drawn from a real codebase) plus a cross-language mapping. Distinct from the language-specific skills above, which state rules; patterns show structures.

| Category | Pattern | What it captures |
|----------|---------|------------------|
| project_structure | [composition_pattern](patterns/project_structure/composition_pattern.md) | Composition Root: one place wires the object graph, pure construction |
| lifecycle | [bootstrap_pattern](patterns/lifecycle/bootstrap_pattern.md) | Startup side effects: idempotent seeding, fail-fast eager init |
| lifecycle | [runtime_pattern](patterns/lifecycle/runtime_pattern.md) | Background worker supervision + bounded graceful drain |
| scalability | [worker_pattern](patterns/scalability/worker_pattern.md) | Broker-backed worker as its own hexagonal app (scalable from day 1) |
| testing | [parallel_test_isolation_pattern](patterns/testing/parallel_test_isolation_pattern.md) | Parallel integration tests via per-test isolation |
| decisions | [local_port_allocation_pattern](patterns/decisions/local_port_allocation_pattern.md) | Non-overlapping port ranges (ADR) for parallel envs/worktrees |
| decisions | [frontend_api_type_mirroring_pattern](patterns/decisions/frontend_api_type_mirroring_pattern.md) | Keep frontend types in sync with the API contract (ADR) |
| documentation | [claude_md_pattern](patterns/documentation/claude_md_pattern.md) | CLAUDE.md navigation hierarchy + templates |
| documentation | [docs_artifact_layout_pattern](patterns/documentation/docs_artifact_layout_pattern.md) | Root + per-component `docs/` layout |
| documentation | [repo_root_files_pattern](patterns/documentation/repo_root_files_pattern.md) | Canonical root + per-component files (README, env, etc.) |
| automation | [dependency_audit_pattern](patterns/automation/dependency_audit_pattern.md) | Cross-stack dependency/security audit command |

## Project Structure

```
agent-skills/
├── README.md
└── software-engineering/
    ├── general-logging/
    │   └── SKILL.md
    ├── code-change-workflow/
    │   └── SKILL.md
    ├── git-workflow/
    │   └── SKILL.md
    ├── database-management/
    │   └── SKILL.md
    ├── python-code-style/
    │   └── SKILL.md
    ├── python-commands/
    │   └── SKILL.md
    ├── python-testing/
    │   └── SKILL.md
    ├── rust-code-style/
    │   └── SKILL.md
    ├── rust-design-principles/
    │   └── SKILL.md
    ├── rust-design-idioms/
    │   └── SKILL.md
    ├── rust-project-setup/
    │   └── SKILL.md
    ├── rust-hexagonal-architecture/
    │   └── SKILL.md
    ├── rust-testing/
    │   └── SKILL.md
    └── technical-design-discussions/
        └── SKILL.md
```

## Usage

### With Claude Code

Add skills to your project's `CLAUDE.md` file or reference them directly in conversations:

```markdown
# CLAUDE.md

Please follow the guidelines in:
- software-engineering/general-logging/SKILL.md
- software-engineering/python-testing/SKILL.md
```

### With Other AI Assistants

Copy the relevant SKILL.md content into your assistant's system prompt or project configuration.

## Skill Format

Each skill follows a consistent structure:

```markdown
---
name: skill-name
description: Brief description
license: MIT
metadata:
  author: email@example.com
  version: "0.0.1"
---

# Skill Name

## Purpose
What this skill helps with.

## When to Apply
Conditions that trigger this skill.

## Core Principles
### 1. Principle Name (CRITICAL|HIGH)
Explanation with code examples.

## Anti-Patterns to Avoid
Common mistakes.

## Guidelines
Quick reference rules.
```

## Contributing

1. Create a new directory under the appropriate category
2. Add a `SKILL.md` following the format above
3. Include practical examples and anti-patterns
4. Keep guidelines focused and actionable

## License

MIT
