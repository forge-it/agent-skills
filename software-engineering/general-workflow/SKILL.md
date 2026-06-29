---
name: general-workflow
description: "Defines a practical workflow for software tasks: inspect context, decide when to proceed directly versus consult the user, protect existing work, make assumptions explicit, keep changes scoped, verify, and report. Use it on requests that involve writing, changing, or debugging code; investigating failures; choosing implementation approaches; or coordinating safe work in a codebase."
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.6"
---

# General Workflow Skill

## Purpose

Use this skill to keep software work pragmatic, scoped, and collaborative.

Default to this workflow: inspect, make the smallest safe change, verify, and report. Escalate to the user when the next decision is ambiguous, risky, irreversible, or belongs to product or architecture ownership.

## Core Principles

### 1. Inspect Before Acting (CRITICAL)

Read the relevant code, tests, configuration, and current Git state before changing files. Let the existing system shape the solution.

Use targeted commands first:

```bash
git status --short
rg "pattern"
rg --files
```

Avoid broad recursive listings. When listing or searching project files, exclude high-noise generated directories such as `.git/`, `target/`, `node_modules/`, `__pycache__/`, `dist/`, `build/`, and `.venv/`. Do not blanket-exclude lockfiles such as `poetry.lock` or `uv.lock`; they often identify the project tooling.

### 2. Proceed Directly for Low-Risk Work (HIGH)

Implement without asking first when the request is clear and the change is narrow, reversible, and consistent with existing patterns.

Proceed directly for examples like:

- focused bug fixes
- failing test repairs
- small refactors that preserve behavior
- documentation or typo corrections
- adding tests for existing behavior
- mechanical updates requested explicitly by the user

State material assumptions in the final report when they influenced the implementation.

### 3. Consult When the Decision Belongs to the User (CRITICAL)

Pause and ask before implementing when the next choice changes ownership-level decisions or carries meaningful risk.

Ask first for examples like:

- public API, CLI, schema, wire-format, or migration changes
- product behavior, UX, pricing, policy, or compatibility decisions
- security posture, authentication, authorization, or privacy-sensitive changes
- new dependencies, major version upgrades, or licensing implications
- deployment, infrastructure, cost-bearing, or production-impacting changes
- destructive Git or filesystem operations
- broad rewrites where several viable approaches have different trade-offs

When asking, present the smallest useful set of options with trade-offs and recommend one if the evidence supports it.

### 4. Make Conservative Assumptions Explicit (HIGH)

Do not block on every missing detail. Make conservative assumptions when they are low-risk and easy to correct. Ask only when a wrong assumption would cause waste, break a contract, damage data, or commit the user to a direction they did not choose.

Prefer this pattern:

```text
I will keep the endpoint shape unchanged and fix the null handling locally. If the intended behavior is to change the response contract, that needs a separate decision.
```

### 5. Protect Existing Work (CRITICAL)

Assume uncommitted changes may belong to the user. Do not revert, overwrite, stage, or reformat unrelated files. If unrelated changes are present, work around them. If they block the requested task, explain the conflict and ask how to proceed.

### 6. Verify Before Reporting Done (HIGH)

Run the smallest relevant verification command after changing files: a focused test, typecheck, linter, formatter check, build, or smoke test. If verification cannot be run, report exactly what was skipped and why.

## Anti-Patterns to Avoid

1. **Uninspected edits**: changing files before reading the relevant code and state
2. **Over-consulting**: asking for approval on narrow, obvious, reversible work
3. **Silent risky decisions**: changing contracts, architecture, data, dependencies, or deployment behavior without user input
4. **Assumption hiding**: relying on a meaningful assumption without saying so
5. **Scope creep**: broad refactors or formatting churn unrelated to the request
6. **User-work damage**: overwriting, reverting, or staging unrelated changes
7. **Unverified claims**: saying work is done without checking the result or explaining why checks were skipped

## Guidelines

### Before Changing Files

- Inspect the relevant code path and tests
- Check `git status --short`
- Identify the smallest change that satisfies the request
- Decide whether the next decision is low-risk enough to proceed or needs user input

### Communication

- Be clear about what you found
- Give short progress updates during longer work
- Ask focused questions only when the answer materially affects the implementation
- Explain trade-offs when asking the user to choose
- Report assumptions, changed files, and verification results

### Decision Making

- Prefer the codebase's existing patterns over new abstractions
- Keep changes proportional to the request
- Recommend an option when the evidence is clear
- Respect explicit user direction unless it conflicts with safety, policy, or repository constraints

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
