---
name: parallel-worktrees-general
description: >-
  Use whenever the user asks to dispatch, launch, spawn, fan out, or delegate
  work to an agent, subagent, worker, or coding agent in a separate git
  worktree — phrasing like "dispatch a subagent", "launch an agent", "fan out
  subagents", "parallel agents", or "use a separate worktree to
  implement/fix/refactor/test/review X" — or whenever two or more workers must
  edit the same repository concurrently without colliding. Symptoms it
  prevents: worktrees created from the wrong base commit, workers editing the
  orchestrator checkout, Edit/Write failing outside the agent CWD, colliding
  diffs, shared Docker/e2e infrastructure clobbered by concurrent test runs,
  merged worktrees left consuming disk, and force-removed worktrees losing
  uncommitted work.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.2"
---

# Parallel Worktrees

Use git worktrees to isolate file edits, not to skip coordination. The roles
follow separation of concerns: the orchestrator owns assignment, integration,
and cleanup; a worker owns only its assigned worktree and path scope — nothing
else. For the wider orchestrator role (routing, briefs, relaying results), see
**agent-fleet-orchestration**; this skill defines the worktree mechanics.

## STOP - Dispatch Protocol

Choose exactly one dispatch mode before spawning a worker. Do not combine a
pre-created worktree with `isolation: "worktree"`.

Protocol:

1. Decide whether the worker must start from current local `HEAD` or unpushed commits.
2. If yes, use Mode B. If no and `origin/HEAD` is an acceptable base (no unpushed commits or specific local branch needed), use Mode C. If the orchestrator is doing the work itself, or a single sequential worker will edit the main checkout with no concurrent edits, use Mode A — no worktree needed.
3. Put the chosen mode, worktree path expectations, and required skill loadout in the spawn prompt.
4. Require the worker's first response to include `pwd`, `git status --short --branch`, and `git branch --show-current`.
5. If the path or branch is wrong, stop the worker immediately and re-dispatch.

### Mode A - Direct, Sequential

Use this when the orchestrator is doing the work itself, or when a single
sequential worker can safely edit the main checkout. Do not use this for
parallel edits.

Spawn with no `isolation` parameter and no extra worktree. All edits and
commands run against the orchestrator checkout.

### Mode B - Pre-Created Worktree, No Agent Isolation

Use this for controlled parallel work, especially when the worker must see the
current feature branch, unpushed commits, or a specific base commit.

Choose a short kebab-case identifier for `<slug>` — lowercase, hyphens only,
no spaces or slashes, derived from the task or ticket (e.g. `fix-timeout`,
`auth-refactor`). The orchestrator creates the worktree first, from the
repository root:

```bash
git worktree add .claude/worktrees/<slug> -b fix/<slug> HEAD
```

Spawn the worker with no `isolation` parameter. The prompt must include the
following, with `<repo-root>` replaced by the real absolute repository root —
never leave a placeholder in the actual spawn prompt:

```text
Dispatch mode: B.
Your worktree is <repo-root>/.claude/worktrees/<slug>.
First run: cd <repo-root>/.claude/worktrees/<slug> && pwd && git status --short --branch && git branch --show-current
Use absolute paths under that worktree for every Read, Write, Edit, and Bash operation.
Do not use isolation: "worktree" for this worker or any nested worker.
The orchestrator checkout and other worktrees are off-limits.
```

Mode B works because `.claude/worktrees/<slug>` is still under the
orchestrator repository root, so absolute paths there are valid for file tools
while git state remains isolated.

### Mode C - Native `isolation: "worktree"`

Use this only when `origin/HEAD` is an acceptable base and the orchestrator
does not need to choose the branch or path up front.

Spawn with `isolation: "worktree"`. Claude creates an auto worktree such as
`.claude/worktrees/agent-<id>`, usually from `origin/HEAD`. The worker must
edit that auto-created worktree only.

The worker must not run `git worktree add` from inside the auto worktree. If
the base is wrong, or the task needs the current local feature branch, stop
and re-dispatch with Mode B.

Common wrong-mode symptoms:

- `Edit` or `Write` reports that a file is outside the agent CWD.
- The worker starts using shell text rewriting instead of file tools.
- Changes land under `.claude/worktrees/agent-<id>` when the orchestrator expected `.claude/worktrees/<slug>`.
- The worker's branch does not contain the current feature-branch commits.

If any symptom appears, stop the worker and re-dispatch with the correct mode.

## Preflight

Run from the main checkout before creating, merging, or removing worktrees:

```bash
git status --short --branch
git worktree list --porcelain
git branch --show-current
```

If the main checkout is dirty, treat those changes as operator state. Do not
overwrite, stash, reset, or merge over them without explicit instruction.

Keep all agent worktrees under `.claude/worktrees/` unless the operator asks
otherwise, and confirm the repository ignores them. If `.gitignore` does not
already cover `.claude/worktrees/`, add that entry before creating the first
worktree; otherwise every worktree shows up as untracked noise in every other
checkout.

## Create Worktrees (Mode B only)

When the operator wants Mode B (pre-created worktree, no `isolation`), create
the worktree manually from the exact intended base. Run this from the
repository root, not from a subdirectory or another worktree:

```bash
git worktree add .claude/worktrees/<slug> -b fix/<slug> HEAD
```

By default `git worktree add` branches from `HEAD` (the current local branch —
usually the feature branch you want edited). If the worker must see unpushed
local commits or current branch state and `HEAD` is the wrong base, pass the
explicit commit: `git worktree add .claude/worktrees/<slug> -b fix/<slug> <commit>`.

Name the branch with the project's branch convention (see **git-workflow**);
`fix/<slug>` is the default when no ticket system applies.

Use one unique branch per worker. Do not try to check out the same branch in
two worktrees.

## Assign Work

Partition by paths and ownership before edits begin — one concern, one worker
(single responsibility). Same-file work, dependency manifests and lockfiles
(`Cargo.lock`, `package-lock.json`, `uv.lock`, `poetry.lock`), database
migrations, shared contracts and generated API clients, and locale files are
high-conflict areas; assign each to exactly one worker or run those tasks
sequentially.

Worker rules:

- Start with `git status --short --branch` inside the assigned worktree.
- Edit only assigned paths.
- Do not edit the main checkout or another worker's worktree.
- Do not run `git stash` for handoff. Stashes are easy to confuse across linked worktrees.
- Do not commit, merge, delete branches, remove worktrees, or push unless explicitly instructed.

Orchestrator rules:

- Use `git -C .claude/worktrees/<slug> ...` when inspecting workers from the main checkout.
- Keep a table of `<slug>`, branch, path scope, status (running / handed off / integrated), and tests run.
- Stop or redirect a worker that touches unassigned paths before integration.

## Worker Skill Loadout

When deploying a subagent into a separate worktree, include the required
skills in its prompt and require it to load them before editing. Match the
loadout to the assigned paths:

| Assigned paths | Required skills |
|----------------|-----------------|
| Rust code | `rust-code-style`, `rust-design-idioms`, `rust-testing`, `rust-project-structure` |
| Python code | `python-code-style`, `python-testing`, plus `python-ddd` when the service uses DDD layering |
| Vue/TypeScript frontend | `frontend-vue-development`, `frontend-vue-code-style`, `frontend-vue-testing` |

For mixed assignments, require the union of the matching sets. If the project
defines its own skills or a CLAUDE.md loadout for a component, include those
too.

## Initialize Each Worktree

A fresh worktree shares git history with the main checkout but nothing else:
no build artifacts, no `node_modules`, no virtualenv, no generated env files.
Run the project's environment bootstrap from the worktree root before the
worker starts. Check the project's CLAUDE.md or README for the actual
bootstrap commands before running anything; do not guess. Illustrative
examples — substitute the project's real recipe and directory names:

```bash
# If the project uses 'just': discover and run its env recipes.
just --list
just <component>-env        # e.g. 'just core-env', 'just web-env'

# If the project has an npm-managed frontend in a subdirectory:
[ -d <frontend-dir>/node_modules ] || npm --prefix <frontend-dir> install
```

Do not copy local secrets into every worktree by default. Use the
template-generated env files unless the task specifically requires
operator-provided local credentials.

## Test Safely

A worktree isolates source files and build outputs. It does NOT isolate shared
runtime infrastructure: Docker containers and compose stacks, shared test
databases, message brokers, mail catchers, and fixed dev-server ports are one
per machine, not one per worktree. Two worktrees running e2e or
infrastructure-backed integration tests concurrently will clobber each other.

Workers run only self-contained checks — checks that start no shared
infrastructure and bind no fixed ports:

- formatters and linters (`cargo fmt`, `ruff`, `eslint`)
- type checkers (`cargo check`, `basedpyright`, `vue-tsc`)
- unit tests scoped to the assigned component
- architecture/structure test suites
- frontend check scripts (`npm run check`)

Forbidden in worker worktrees:

- e2e test suites
- integration tests that auto-start Docker stacks, databases, or other shared services
- aggregate commands (`just test-all` or equivalent) that include either of the above
- dev-stack or deploy-stack up/down recipes
- browser-driven flows against fixed dev-server ports

Shared-infrastructure checks are the orchestrator's job: integrate first, then
run them once, serially, from the orchestrator checkout. Only the orchestrator
starts or stops shared stacks. If you cannot tell whether a test touches
shared infrastructure, treat it as if it does and leave it to the
orchestrator.

## Commit Hook Handling

Treat PreToolUse commit hooks (structure/style review gates, docs
reconciliation gates — see **agent-hooks-setup**) as guardrails, not
obstacles. Do not bypass them by hiding `git commit` inside a different
command shape.

If a commit is blocked:

- Run the requested structure/style review or docs reconciliation.
- Fix the finding, or record why no fix is needed.
- Use a hook's documented bypass variable only when that specific gate has already been satisfied or is genuinely irrelevant.

The orchestrator owns commit-hook decisions. Workers should report blockers
and the validation they ran; they should not invent bypass recipes.

## Handoff

Each worker reports:

```bash
git status --short
git diff --stat HEAD
```

Also report the worktree path, branch, files touched, tests run, failures, and
any uncommitted or untracked files.

For Mode C, report the actual auto-created worktree path and branch from
`git status --short --branch`; do not invent a `<slug>`.

If commits are authorized, commit inside the worker worktree after reviewing
`git diff`. If commits are not authorized, leave changes uncommitted and let
the orchestrator integrate by reviewed patch or direct file inspection.

A handoff is per-worker and triggers integration as soon as the orchestrator
is free: if no integration unit is in progress, move straight to the Integrate
steps for that worker; if one is in progress, finish it completely — merge,
validation, cleanup — first. Never run two integration units concurrently,
and never hold a finished handoff waiting for other workers to finish.

## Integrate

Integrate incrementally: merge each worker as soon as it finishes and hands
off, while the remaining workers keep running. Do not wait for all workers to
finish and then merge everything in one batch — batching leaves finished work
sitting unvalidated, stacks all conflicts into one late resolution session,
and lets one slow worker block integration of work that was done long before.

Process workers in completion order, not dispatch order. When two or more
workers hand off at the same time, pick one — first received is fine — and
complete its full integration unit before starting the next; never interleave
integration steps from two workers. Treat each integration as one atomic
unit — verify, merge, validate, clean up — then return to monitoring the
remaining workers.

Merging while other workers run is safe: the merge happens in the
orchestrator checkout, and the running workers' worktrees and branches are
untouched. Their branches still fork from the original base; any conflict
with already-merged work is resolved when that worker's own turn comes, in
the orchestrator checkout. Do not rebase, merge into, or otherwise update a
still-running worker's worktree to "catch it up".

Before integrating a worker, make the target checkout clean and verify the
worker state. If the main checkout is dirty with changes that predate the
session, the Preflight rule applies: those changes are operator state — do
not stash, reset, or discard them to satisfy this precondition; report the
block and wait for the operator to clear them. If the checkout is dirty
because the current integration unit's conflict resolution is still in
progress, that is integration state, not operator state — finish resolving
and complete that unit before starting the next worker's integration.

```bash
git status --short --branch
git -C <worktree-path> status --short --branch
git -C <worktree-path> diff --stat HEAD
```

For committed worker branches, merge one branch at a time from the
orchestrator checkout. Use `fix/<slug>` for Mode B, or the actual reported
branch for Mode C:

```bash
git merge --no-ff <worker-branch>
```

For uncommitted worker changes, create and review a patch, then apply it from
the target checkout. Write the patch to the session's scratch/temp directory
(`<scratch>` below is that absolute path — any location outside the repo
works):

```bash
git -C <worktree-path> diff --binary HEAD > <scratch>/<slug>.patch
git apply --3way <scratch>/<slug>.patch
```

Untracked files are not included in `git diff`. Before patch handoff, either
have the worker run `git add -N <new-files>` so the new files appear in the
diff, or copy/review those files explicitly.

Resolve conflicts only in the orchestrator checkout. After each merge, rerun
the self-contained checks relevant to that worker's scope in the integrated
tree; worker-local test results are not enough.

If the self-contained checks fail after a merge, halt further integration —
do not merge the next worker into a tree that fails validation. Let
still-running workers finish; collect their handoffs without integrating
them. Fix the failure in the orchestrator checkout, or report it to the
operator if the fix is not obvious, and resume integration only when the
integrated tree passes again.

Run the shared-infrastructure suites (e2e, Docker-backed integration — see
Test Safely) once, serially, after the last worker is integrated — not after
every merge. If those suites fail at that stage, the worker worktrees are
already removed; report the failure and the state of the integrated branch to
the operator, and do not attempt an automatic rollback.

After a worker branch is merged into the target branch, whether the target is
`main` or a feature branch, immediately remove that worker's worktree and
delete its worker branch before returning to monitor the remaining workers.
Treat merge, validation, and cleanup as one integration unit; do not leave
merged worktrees around waiting for a separate operator cleanup request.

## Cleanup

The timing rule lives in Integrate: merge, validation, and cleanup are one
integration unit, and a worktree whose changes are integrated or deliberately
discarded is removed immediately, without waiting for the operator to ask.
This section covers the removal mechanics. Each worktree carries its own
build artifacts — a Rust `target/` directory, `node_modules`, a virtualenv —
which can consume tens of gigabytes per worktree, so keeping finished
worktrees around wastes disk quickly.

Never delete a linked worktree with `rm -rf`. Inspect first:

```bash
git worktree list --porcelain
git -C <worktree-path> status --short
```

A worker integrated by patch leaves its worktree dirty — the changes were
extracted into the patch, not committed. Once the applied patch has been
validated in the orchestrator checkout, discard the worker copy so removal
can proceed without `--force`:

```bash
git -C <worktree-path> checkout -- .
git -C <worktree-path> clean -fd
```

If the worktree is clean and its branch is merged or no longer needed, remove
the actual worktree path and branch:

```bash
git worktree remove <worktree-path>
git branch -d <worker-branch>
git worktree prune
```

If `git worktree list` marks a worktree `locked`, the worktree has a lockfile
that blocks removal. For auto-isolation worktrees created by
`isolation: "worktree"`, the lock is held while the agent session is alive;
for worktrees locked manually with `git worktree lock`, no process may be
involved at all. In either case, do not unlock or force-remove it unless the
operator confirms the owning session (if any) is dead and the changes are
disposable. To clean up a stale auto-isolation worktree from a stopped/killed
agent, the lockfile is at `.git/worktrees/<id>/locked` — once the agent PID is
gone, `git worktree remove --force <path>` works.

Use `git worktree remove --force` and `git branch -D` only after preserving or
deliberately discarding every needed diff.
