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
| [logging](software-enginnering/logging/SKILL.md) | Wide events logging pattern for powerful debugging and analytics |
| [python-testing](software-enginnering/python-testing/SKILL.md) | Python testing best practices using pytest |
| [python-code-style](software-enginnering/python-code-style/SKILL.md) | Python code style for clean, maintainable code |
| [git-workflow](software-enginnering/git-workflow/SKILL.md) | Git branch naming, commits, and version control |
| [general-workflow](software-enginnering/general-workflow/SKILL.md) | Consultation-first approach for AI-assisted development |

## Project Structure

```
agent-skills/
├── README.md
└── software-enginnering/
    ├── general-workflow/
    │   └── SKILL.md
    ├── git-workflow/
    │   └── SKILL.md
    ├── logging/
    │   └── SKILL.md
    ├── python-code-style/
    │   └── SKILL.md
    └── python-testing/
        └── SKILL.md
```

## Usage

### With Claude Code

Add skills to your project's `CLAUDE.md` file or reference them directly in conversations:

```markdown
# CLAUDE.md

Please follow the guidelines in:
- software-enginnering/logging/SKILL.md
- software-enginnering/python-testing/SKILL.md
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
