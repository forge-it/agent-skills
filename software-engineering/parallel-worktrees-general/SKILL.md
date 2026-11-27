---
name: parallel-worktrees-general
description: >-
  STOP — if you were dispatched as a subagent to execute a briefed task, this
  skill is not for you: it governs the dispatching orchestrator only, and the
  mode and path rules you need are already in your brief. Do the task you were
  briefed with instead.
  Use whenever the user asks to dispatch, launch, spawn, fan out, or delegate
  work to an agent, subagent, worker, or coding agent in a separate git
  worktree — phrasing like "dispatch a subagent", "launch an agent", "fan out
  subagents", "parallel agents", or "use a separate worktree to
  implement/fix/refactor/test/review X" — or whenever two or more workers must
  edit the same repository concurrently without colliding. Symptoms it
  prevents: worktrees created from the wrong base commit, workers accidentally
  editing the orchestrator checkout when an isolated worktree was intended
  (Mode D is the sanctioned single-writer exception), Edit/Write failing
  outside the agent CWD, colliding diffs, shared Docker/e2e infrastructure
  clobbered by concurrent test runs,
  merged, cherry-picked, or abandoned worktrees left consuming disk, and
  force-removed worktrees losing unintegrated source edits.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.5"
---

# Parallel Worktrees

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, stop reading and
discard this skill. It teaches the orchestrator how to hand work out; following
it from inside a worker means dispatching a fleet nobody asked for, into a
checkout you were told to be the only writer in. Your dispatch mode, worktree
path, and path scope are already in your brief. Go do the task in your brief.

Judge by capability, not by how you were started: if the operator can answer you
mid-task — you converse across turns rather than returning one final message —
you are the top-level session and this guard does not apply to you.
</SUBAGENT-STOP>

Use git worktrees to isolate file edits, not to skip coordination. The roles
follow separation of concerns: the orchestrator owns assignment, integration,
and cleanup; a worker owns only its assigned worktree and path scope — nothing
else. For the wider orchestrator role (routing, briefs, relaying results), see
**agent-fleet-orchestration**; this skill defines the worktree mechanics.

## STOP - Dispatch Protocol

Choose exactly one of the four dispatch modes before acting — whether the
orchestrator edits directly (Mode A) or a worker is spawned (Modes B, C, D).
Every dispatched worker (Modes B, C, D) is a native `Agent` dispatch — never
a nested CLI invocation of the agent binary; Mode A is the only non-agent
mode. Do not combine a pre-created worktree with `isolation: "worktree"`.

| Situation                                                             | Mode |
| --------------------------------------------------------------------- | ---- |
| Orchestrator performs a trivial edit itself                           | A    |
| One sequential worker must edit the existing current checkout         | D    |
| Parallel / controlled worker needs a selected base and isolated files | B    |
| Native isolated sandbox based from acceptable remote/default base     | C    |

> Mode D is the only mode for a subagent that must modify the current
> orchestrator checkout. Spawn it as a native `Agent` with no `isolation`
> parameter and `run_in_background: false` — passing `isolation` would send
> the worker to a separate worktree or remote environment instead of the
> current checkout.

Protocol:

1. Decide whether the work edits the current orchestrator checkout. A trivial edit the orchestrator makes itself is Mode A; a dispatched worker that must edit the current checkout is Mode D.
2. Otherwise, decide whether the worker must start from current local `HEAD` or unpushed commits. If yes, use Mode B. If no and `origin/HEAD` is an acceptable base (no unpushed commits or specific local branch needed), use Mode C.
3. Put the chosen mode, worktree path expectations, and required skill loadout in the spawn prompt.
4. Require the worker's first response to include `pwd`, `git status --short --branch`, and `git branch --show-current`.
5. If the path or branch is wrong, stop the worker immediately and re-dispatch.

### Mode A - Orchestrator Direct Edit

Use this only when the orchestrator itself makes a trivial, safe edit directly
in the current checkout. Mode A is not a worker dispatch mode: nothing is
spawned and no worktree is involved.

If a worker must be dispatched to edit the current checkout, that is Mode D,
not Mode A.

### Mode D - Current Checkout Native Worker

Use this for exactly one sequential worker that must edit the orchestrator's
current checkout — for example, when the operator explicitly says "work in the
current worktree" or "do not use a separate worktree."

Mode D is mutually exclusive with Modes B and C. It is never safe for parallel
writers: the worker shares the orchestrator's files, git index, build
artifacts, and branch. No second writer, no parallel review fixer, and no
simultaneous build/test command competing for the same build directory may run
alongside it.

Spawn it as a native `Agent` with **no `isolation` parameter** and
**`run_in_background: false`**. Without isolation the agent inherits the
orchestrator CWD — the primary checkout — so its file tools target it directly
(the same mechanism Mode B relies on for `.claude/worktrees/` paths). The
synchronous spawn enforces the single-writer rule structurally: the
orchestrator is blocked until the worker finishes and cannot edit files or run
competing build commands mid-run. Continue the same worker across turns with
`SendMessage`, keeping the same one-writer discipline — but note that
`SendMessage` does not block like the initial spawn: after a continuation,
wait for the worker's response before doing any file-editing, staging, or
build work in the primary checkout.

Preflight before launch:

```bash
git status --short --branch
git worktree list --porcelain
git branch --show-current
```

The current checkout must be clean unless the operator has explicitly
identified the existing dirty files as the worker's intended starting state.
Never use Mode D over unrecognized operator changes.

The spawn prompt must include:

```text
Dispatch mode: D.
You are editing the current primary checkout:
<absolute-primary-checkout-path>

First run: pwd && git status --short --branch && git branch --show-current

Do not create or enter a worktree. Do not use isolation: "worktree" for
this worker or any nested worker. Do not create or switch branches.
Do not stage, commit, push, merge, reset, restore, or revert unless the
operator explicitly authorizes it. Leave changes unstaged for orchestrator
review.

You are the single writer in this checkout. Do not dispatch any worker
that edits files — not in parallel and not sequentially. A nested native
worker inherits this same CWD, git index, branch, and build directory,
which is exactly the collision Mode D exists to prevent. Read-only
explorers are the only dispatch permitted.
```

Mode-D worker rules:

- Edit only the assigned paths.
- Do not create or use a worktree or branch.
- Do not stage, commit, push, merge, stash, reset, restore, or clean. The worker leaves its diff unstaged unless separately authorized.
- Do not run integration/e2e or shared-infrastructure commands (see Test Safely) unless the orchestrator specifically delegates and serializes them.
- Report `git status --short`, `git diff --stat HEAD`, files changed, tests run, failures, and any unresolved decision.
- The orchestrator must not edit the assigned paths, stage files, or run competing build/test commands against the same checkout while this worker is active.

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
You are the single writer in this worktree: do not dispatch any worker
that edits files. Read-only explorers are the only dispatch permitted.
The orchestrator checkout and other worktrees are off-limits.
Build only into the project's standard output directories (target/, dist/,
node_modules/, .venv/); never create an extra untracked build directory or
virtualenv.
```

Put that last line in every Mode C prompt too.

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
checkout. A worktree the session creates anywhere else — a sibling directory
such as `<repo>-<ticket>`, a path under `/tmp` — is still the session's to
clean up under Cleanup, the moment its work lands or is abandoned;
`git worktree list` shows it whatever its path.

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
- Build only into the project's standard output directories; never create an extra untracked
  build directory (a second `target-<name>/`, an alternate virtualenv).

Orchestrator rules:

- Use `git -C .claude/worktrees/<slug> ...` when inspecting workers from the main checkout.
- Keep a table of `<slug>`, branch, path scope, status (running / handed off / integrated), and tests run.
- Stop or redirect a worker that touches unassigned paths before integration.

### Mode D ownership

Mode D has one writer: the native worker. The synchronous spawn blocks the
orchestrator while the worker runs; between runs (for example before a
`SendMessage` continuation) the orchestrator may inspect and coordinate but
must not edit the worker's assigned paths, stage files, or run competing
build/test commands from the same checkout. For `SendMessage` continuations
this is enforced by convention, not by the tool's blocking semantics — after
a continuation, hold off all checkout writes until the worker's response
arrives.

A Mode-D worker has no merge or patch handoff. Its handoff is the unstaged
diff in the current checkout. The orchestrator reviews and validates that
diff in place, then either requests fixes, stages/commits after operator
authorization, or discards nothing without explicit direction.

## Worker Skill Loadout

When dispatching a native agent worker (Modes B, C, or D), include the
required skills in its prompt and require it to load them before editing.
Match the loadout to the assigned paths:

| Assigned paths | Required skills |
|----------------|-----------------|
| Rust code | `rust-code-style`, `rust-design-idioms`, `rust-testing`, `rust-project-structure` |
| Python code | `python-code-style`, `python-testing`, plus `python-ddd` when the service uses DDD layering |
| Vue/TypeScript frontend | `frontend-vue-development`, `frontend-vue-code-style`, `frontend-vue-testing` |
| React/TypeScript frontend | `frontend-react-development`, `frontend-react-code-style`, `frontend-react-testing` |

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

Build into the project's standard output directories (`target/`, `dist/`,
`node_modules/`, `.venv/`). Never create an extra untracked build directory
inside a worktree (a second `target-<name>/`, an alternate virtualenv): each
one duplicates gigabytes and shows up as untracked clutter at cleanup.

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

For Mode D, there is no worktree path or worker branch to report: the handoff
is the unstaged diff in the primary checkout, reviewed in place (see
Integrate).

If commits are authorized, commit inside the worker worktree (Modes B and C)
after reviewing `git diff`. If commits are not authorized, leave changes
uncommitted and let the orchestrator integrate by reviewed patch or direct
file inspection. Mode D commits happen only in the primary checkout, by the
orchestrator, after operator authorization.

A handoff is per-worker and triggers integration as soon as the orchestrator
is free: if no integration unit is in progress, move straight to the Integrate
steps for that worker; if one is in progress, finish it completely — merge,
validation, cleanup — first. Never run two integration units concurrently,
and never hold a finished handoff waiting for other workers to finish.

## Integrate

The merge/patch integration below applies to Modes B and C only. For Mode D,
inspect the primary checkout directly:

```bash
git status --short --branch
git diff --stat HEAD
git diff --check
```

Do not run `git merge`, generate a worktree patch, remove a worktree, or
delete a branch for Mode D: there is no separate worker branch or worktree.
Review, tests, and any eventual staging/commit happen in the primary checkout
only after the worker stops.

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

After a worker's work lands on the target branch — merged, cherry-picked,
squashed, rebased, or applied as a patch, whether the target is `main` or a
feature branch — or is deliberately discarded, immediately remove that
worker's worktree and delete its worker branch before returning to monitor
the remaining workers. Treat merge, validation, and cleanup as one integration
unit; do not leave finished worktrees around waiting for a separate operator
cleanup request. This holds for every `isolation: "worktree"` (Mode C)
`agent-*` worktree too: the orchestrator that dispatched it owns its removal.

## Cleanup

Mode D creates no linked worktree, so it has no worktree cleanup step. Do not
run `git worktree remove` as part of a Mode-D completion. Everything below
applies to Modes B and C, and to any other worktree the session created,
wherever it lives.

The timing rule lives in Integrate: a worktree whose work landed or was
deliberately discarded is removed immediately, without waiting for the
operator to ask. Operator preference: force-remove a verified worktree rather
than leave it on disk. Each worktree carries its own build and dependency
artifacts — `target/`, `node_modules/`, `.venv/`, build output — worth tens of
gigabytes, so one left behind is expensive whatever the language.

### Verify, then force-remove

Check three things, from the main checkout:

1. **The work landed or was abandoned.** Any one of these is enough:
   - `git merge-base --is-ancestor <worker-branch> <target>` succeeds;
   - `git cherry <target> <worker-branch>` prints no `+` line (every commit
     has a patch-equivalent on the target, as after a cherry-pick or rebase);
   - you integrated it yourself this session by squash, cherry-pick, or patch,
     and the integrated tree passed validation;
   - the forge shows its pull or merge request merged, and the branch tip
     equals the head commit the forge merged (a squash merge done there);
   - every file the branch touched already matches the target (a squash or
     cherry-pick done earlier, by anyone):
     `git diff --quiet <target> <worker-branch> -- $(git diff --name-only
     $(git merge-base <target> <worker-branch>) <worker-branch>)` succeeds;
   - the work was deliberately discarded or superseded.

   A failed ancestry check alone never means the work is missing: after a
   cherry-pick, squash, or rebase it fails although the work is on the target.
   Try the other evidence before stopping.
2. **No unintegrated source edits.** A branch with no commits passes check 1
   trivially, so for an uncommitted worker this check is the only guard. Read
   `git -C <worktree-path> status --short --untracked-files=all`. A modified,
   deleted, or untracked source file blocks removal unless its content is
   already where the work landed:
   - on the target: `git -C <worktree-path> show <target>:<path> 2>/dev/null
     | cmp -s - <worktree-path>/<path>` succeeds (for a deletion,
     `git -C <worktree-path> cat-file -e <target>:<path>` fails);
   - in the checkout a patch was applied to:
     `cmp -s <worktree-path>/<path> <checkout>/<path>` succeeds.

   Not `git diff <target> -- <path>`: it skips untracked files and reports a
   new file as matching. Untracked or ignored build, dependency, env, and log
   artifacts — `target*/`, `build/`, `dist/`, `node_modules/`, `.venv/`,
   `.env`, scratch logs — never block removal.
3. **Nothing still uses the path.** No live agent session owns it (the worker
   returned or was stopped), and no process or container has it as working
   directory or bind mount:

   ```bash
   lsof -d cwd 2>/dev/null | grep -F "<worktree-path>"
   docker ps --no-trunc --format '{{.Names}} {{.Mounts}}' | grep -F "<worktree-path>"
   ```

   Rebind or stop a shared stack that mounts it before removing.

Then remove it, whatever untracked artifacts it still holds:

```bash
git worktree unlock "<worktree-path>" 2>/dev/null || true
git worktree remove --force "<worktree-path>"
git worktree prune
git branch -D "<worker-branch>" 2>/dev/null || true
```

If `remove --force` itself fails (root-owned files a container wrote, say),
report the error and the path; do not fall back to `rm -rf`.

`unlock` is needed because `isolation: "worktree"` worktrees are locked, and a
single `--force` refuses a locked worktree. `--force` removes untracked and
ignored artifacts with the directory; plain `git worktree remove` refuses
over any untracked file that is not gitignored (an ad-hoc `target-x/`, a
stray log) and leaves the whole tree behind. `-D` because a squashed or
cherry-picked branch never looks merged to git. Where a project skill forbids
`git worktree prune` (it can touch other sessions' entries), skip it:
`remove` already drops this worktree's own entry.

Never delete a linked worktree with `rm -rf`: outside the few scratch paths
the permission rules allow, the harness denies it; everywhere it skips the
checks above and leaves the worktree registered (a dangling, possibly locked
entry). `git worktree remove --force` deletes the same files through git.

Stop and report, instead of removing, when check 1 finds no evidence the
work landed or was abandoned, check 2 finds an unintegrated source edit, or
check 3 finds a live owner. Nothing else keeps a finished worktree on disk.
An `agent-*` tree's lock belongs to the subagent you dispatched: once that
subagent has returned or been stopped, the lock is stale and the tree is yours
to remove. What is not yours: a worktree neither you nor a worker you
dispatched created, or one locked by a live session that is not your worker.

### Parking a worktree

When a worktree must stay on disk without active work (on hold, waiting on an
operator decision, an open pull request), clear its heavy caches first:
`cargo clean`, or the project's clean recipe (`just clean`, `make clean`,
`npm run clean`). Not `git clean -X`: it also deletes ignored local files
such as `.env`.
