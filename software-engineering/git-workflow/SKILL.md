---
name: git-workflow
description: Git workflow guidelines for branches, commits, and version control best practices
license: MIT
metadata:
  author: cristian.ciortea@proton.me
  version: "0.0.1"
---

# Git Workflow Skill

Version: 0.0.1

## Purpose

This skill provides guidelines for working with Git version control. It focuses on branch naming, commit message quality, and safe push practices.

## When to Apply

Apply these guidelines when:
- Creating new branches
- Writing commit messages
- Preparing to push changes
- Working with version control

## Core Principles

### 1. Diff-Based Commits (CRITICAL)

Before creating a commit message, always examine the actual `git diff` to see specific changes. Never make assumptions based on file names or branch names alone. Digest the information and extract the essence of what was implemented.

```bash
# Always run this first
git diff

# Then create a commit message based on what you actually see
```

### 2. Never Push Without Permission (CRITICAL)

**NEVER use `git push` without explicit permission.** Always ask for explicit permission before every single `git push` operation.

### 3. Commit Only When Prompted (CRITICAL)

Only create commits when explicitly prompted to do so. Never commit automatically.

### 4. Branch Naming (HIGH)

Create branches using the pattern: `<TICKET-NUMBER>-<what-problem-is-fixed>`

For projects without ticket systems, use the pattern: `<prefix>/<what-problem-is-fixed>`

```bash
# With ticket numbers
git checkout -b PROJ-123-fix-login-timeout
git checkout -b FEAT-456-add-user-export
git checkout -b BUG-789-handle-null-response

# Without ticket numbers (use prefix)
git checkout -b fix/login-timeout
git checkout -b feat/add-user-export
git checkout -b chore/update-dependencies

# Bad examples
git checkout -b fix-stuff
git checkout -b new-feature
git checkout -b johns-branch
```

### 5. Commit Message Format (HIGH)

Structure commits as: `"<TICKET-NUMBER>: What are the main changes and why"`

If the ticket number is not found in the branch name, ask for it explicitly. If the project does not use tickets, use conventional commit prefixes instead:

- `fix:` - Bug fixes
- `feat:` - New features
- `chore:` - Maintenance tasks (refactoring, dependencies, config)
- `wip:` - Work in progress (multiple related changes not yet complete)

```bash
# With ticket numbers
git commit -m "PROJ-123: Fix session timeout by extending token TTL to 24 hours"
git commit -m "FEAT-456: Add CSV export for user data with pagination support"
git commit -m "BUG-789: Handle null API response in order processing"

# Without ticket numbers (use conventional prefixes)
git commit -m "fix: resolve session timeout by extending token TTL to 24 hours"
git commit -m "feat: add CSV export for user data with pagination support"
git commit -m "chore: update dependencies to latest versions"
git commit -m "wip: initial implementation of payment processing"

# Bad examples
git commit -m "fix bug"
git commit -m "updates"
git commit -m "WIP"
```

### 6. Message Proportionality (HIGH)

Make commit messages proportional to changes:
- Small changes (typos, minor fixes) = short, concise messages
- Large changes (new features, major refactoring) = detailed messages

```bash
# Small change - short message
git commit -m "PROJ-123: Fix typo in error message"

# Large change - detailed message
git commit -m "FEAT-456: Implement user authentication system

- Add JWT token generation and validation
- Create login and logout endpoints
- Add password hashing with bcrypt
- Include refresh token rotation
- Add rate limiting for auth endpoints"
```

## Anti-Patterns to Avoid

1. **Blind commits**: Committing without reviewing `git diff`
2. **Auto-pushing**: Pushing without explicit permission
3. **Auto-committing**: Committing without being prompted
4. **Generic messages**: Using "fix", "update", "changes" without context
5. **Missing prefix**: Commits without ticket number or conventional prefix
6. **Disproportionate messages**: Long messages for tiny changes or vice versa

## Guidelines

### Branch Naming
- With tickets: `<TICKET-NUMBER>-<what-problem-is-fixed>`
- Without tickets: `<prefix>/<what-problem-is-fixed>`
- Use lowercase with hyphens
- Be descriptive about the problem being solved

### Commit Messages
- With tickets: `<TICKET-NUMBER>: What are the main changes and why`
- Without tickets: `<prefix>: What are the main changes and why`
- Prefixes: `fix:`, `feat:`, `chore:`, `wip:`
- Always check `git diff` before writing the message
- Ask for ticket number if not found in branch name (for projects that use tickets)
- Match message length to change scope

### Process Flow
```
1. git diff                    # Review actual changes
2. Digest the changes          # Understand what was done
3. Create proportional message # Match scope to message
4. Wait for commit prompt      # Don't commit automatically
5. git commit                  # Commit when prompted
6. Ask permission              # Before any push
7. git push                    # Only after permission
```

### Commit Timing
- Only commit when explicitly asked
- Never batch multiple unrelated changes
- Keep commits focused and atomic

### Push Safety
- Always ask before pushing
- Never use `git push --force` without discussion
- Verify the correct remote and branch
