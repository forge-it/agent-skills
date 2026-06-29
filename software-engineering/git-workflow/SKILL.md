---
name: git-workflow
description: Defines safe Git workflow conventions for agents. Use whenever creating or naming branches, inspecting or staging changes, writing commit messages, creating commits, pushing branches, force-pushing, or otherwise working with Git state.
metadata:
  version: "0.0.4"
---

# Git Workflow Skill

## Non-Negotiable Rules

- Create commits only when explicitly prompted.
- Push only after explicit permission for that push operation.
- Never add `Co-Authored-By:`, `Made-By:`, or any other trailer that attributes an AI tool to a commit.
- Preserve user changes. Do not stage, revert, or rewrite unrelated work.
- Do not use `git add .` or `git add -A` blindly. Stage only the intended paths or hunks.
- Never use `git push --force`. Use `git push --force-with-lease` only after discussing the risk and receiving command-specific permission.

## Branch Naming

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

Keep ticket IDs in the project's normal casing. Write the descriptive slug in lowercase with hyphens.

## Commit Workflow

Before proposing or creating a commit, inspect the actual Git state:

```bash
git status --short
git diff
git diff --cached
```

Use the diff that will actually be committed:

- If changes are already staged, base the commit message on `git diff --cached`.
- If no changes are staged and the user asked you to commit, stage only the intended files or hunks, then re-check `git diff --cached`.
- If staged and unstaged changes both exist, keep the commit message scoped to staged changes and call out unstaged changes separately.
- Never infer the commit message from file names, branch names, or prior discussion alone.

## Commit Message Format

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

## Message Proportionality

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

## Process Flow

```
1. git status --short          # Inspect working tree state
2. git diff                    # Review unstaged changes
3. git diff --cached           # Review staged changes
4. Stage intended changes      # Only after a commit prompt
5. Re-check git diff --cached  # Confirm exactly what will be committed
6. Write the message           # Match scope to staged changes
7. git commit                  # Commit only when prompted
```

Keep commits focused and atomic. Do not batch unrelated changes into one commit.

## Push Safety

Before asking for push permission, inspect the target:

```bash
git status -sb
git remote -v
git branch --show-current
git branch -vv
```

State the remote, local branch, upstream branch, and exact push command. Push only after the user explicitly approves that command.
