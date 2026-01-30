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
| [general-workflow](software-engineering/general-workflow/SKILL.md) | Consultation-first approach for AI-assisted development |
| [git-workflow](software-engineering/git-workflow/SKILL.md) | Git branch naming, commits, and version control |
| [database-management](software-engineering/database-management/SKILL.md) | Database schema management and migration strategies |
| [python-code-style](software-engineering/python-code-style/SKILL.md) | Python code style for clean, maintainable code |
| [python-commands](software-engineering/python-commands/SKILL.md) | Python command-line interface best practices |
| [python-testing](software-engineering/python-testing/SKILL.md) | Python testing best practices using pytest |
| [rust-code-style](software-engineering/rust-code-style/SKILL.md) | Rust code style with hexagonal architecture |
| [rust-design-principles](software-engineering/rust-design-principles/SKILL.md) | SOLID, KISS, and design patterns for Rust |
| [rust-design-idioms](software-engineering/rust-design-idioms/SKILL.md) | Rust design idioms including newtype pattern and error handling |
| [rust-project-setup](software-engineering/rust-project-setup/SKILL.md) | Rust project setup with toolchain and cargo-make |
| [rust-testing](software-engineering/rust-testing/SKILL.md) | Rust testing best practices using cargo test |

## Project Structure

```
agent-skills/
├── README.md
└── software-engineering/
    ├── general-logging/
    │   └── SKILL.md
    ├── general-workflow/
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
    └── rust-testing/
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

Version: 0.0.1

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
