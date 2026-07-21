---
name: code-change-workflow
description: "Execution discipline for tasks whose deliverable is an edit to an existing codebase — implementing a feature, fixing a bug or failing test, refactoring, or debugging with intent to fix. Covers inspecting code and Git state first, proceeding directly on narrow reversible work, asking before user-owned decisions, protecting uncommitted work, and verifying before reporting done. Use when about to write or modify code. Do NOT use when no files will change: assessing a plan or spec, weighing architectures, or answering questions about code is technical-design-discussions."
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.1.0"
---

# Code Change Workflow Skill

## Purpose

Default workflow: inspect, make the smallest safe change, verify, and report. Escalate only when the next decision is ambiguous, risky, irreversible, or belongs to product or architecture ownership.

## Core Principles

### Inspect Before Acting

Read the relevant code, tests, configuration, and current Git state before changing files. Let the existing system shape the solution.

Prefer targeted commands:

```bash
git status --short
rg "pattern"
rg --files
```

Avoid broad recursive listings. Exclude high-noise generated directories such as `.git/`, `target/`, `node_modules/`, `__pycache__/`, `dist/`, `build/`, and `.venv/`. Do not blanket-exclude lockfiles such as `poetry.lock` or `uv.lock`; they often identify tooling.

### Proceed Directly for Low-Risk Work

Implement without asking first when the request is clear and the change is narrow, reversible, and consistent with existing patterns: focused bug fixes, failing test repairs, behavior-preserving refactors, documentation fixes, tests for existing behavior, or explicit mechanical updates.

### Ask Before Risky or User-Owned Decisions

Pause before changing:

- public APIs, CLIs, schemas, wire formats, or migrations
- product behavior, UX, pricing, policy, or compatibility
- security, authentication, authorization, or privacy posture
- dependencies, major upgrades, licensing, deployment, infrastructure, or cost-bearing systems
- destructive Git/filesystem state
- broad rewrites with materially different viable approaches

When asking, present the smallest useful set of options with trade-offs and recommend one if the evidence supports it.

If the decision opens into a genuine design conversation — multiple viable architectures, contested trade-offs, unstated deployment or scale context — switch to the technical-design-discussions skill, lock the decision there, then resume this workflow.

### Make Assumptions Explicit

Do not block on every missing detail. Make conservative assumptions when they are low-risk and easy to correct. Ask only when a wrong assumption would cause waste, break a contract, damage data, or commit the user to a direction they did not choose.

### Protect Existing Work

Assume uncommitted changes may belong to the user. Do not revert, overwrite, stage, or reformat unrelated files. If unrelated changes are present, work around them. If they block the requested task, explain the conflict and ask how to proceed.

### Verify Before Reporting Done

Run the smallest relevant verification command after changing files: a focused test, typecheck, linter, formatter check, build, or smoke test. If verification cannot be run, report exactly what was skipped and why.

## Anti-Patterns to Avoid

- Uninspected edits before reading relevant code and Git state
- Over-consulting on narrow, obvious, reversible work
- Silent changes to contracts, architecture, data, dependencies, or deployment behavior
- Hidden assumptions, unrelated refactors, formatting churn, or user-work damage
- Claims of completion without verification or an explicit reason verification was skipped

## Guidelines

- Prefer existing patterns over new abstractions.
- Keep changes proportional to the request.
- Ask focused questions only when the answer materially affects implementation.
- Give short progress updates during longer work.
- Report changed files, assumptions, verification, and remaining risk.

### Process Flow

```
1. Receive request/problem
2. Inspect relevant files, tests, configuration, and Git state
3. Identify the smallest safe approach
4. Proceed directly for low-risk work, or ask when the decision belongs to the user
5. Implement the scoped change
6. Verify with the smallest relevant check
7. Report what changed, what was verified, and any remaining risk
```
