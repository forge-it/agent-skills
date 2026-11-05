---
name: agent-sync
description: >-
  Use only when the operator explicitly asks to load agent-sync for this session: several
  orchestrator sessions share one repository checkout and must take turns integrating into the
  default branch, pushing it, and using a shared resource such as the Docker stack for
  integration tests. Never self-select it; a project that does not name it works without it.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.1.0"
---

# Agent Sync

Several top-level sessions (orchestrators) start in the same checkout of one repository. Each
dispatches workers into its own worktrees, and all of them land work on the default branch
(`main` below). This skill makes them take turns without the operator acting as the mutex. It
adds no session: the coordination lives in two scripts every session calls.

| Script | Job |
|---|---|
| `scripts/lockctl.py` | named locks per repository: who holds them, waiting, releasing, safe stealing |
| `scripts/nag.py` | repeated herdr notification until the operator answers |

Call them by absolute path (`~/.claude/skills/agent-sync/scripts/lockctl.py`). Lock state lives
in `<git-common-dir>/agent-sync/`, so every worktree of the repository sees the same locks, and
nothing is tracked or written into the working tree. Each subcommand's `--help` says what it
prints. Exit 75 means busy (held by someone else, the wait ran out, a steal refused, a nag id
taken). `lockctl.py run` passes its command's exit code through, so a 75 from `run` is
lockctl's own only when stderr says `lock <name> is held by`.

## What loading this skill changes in other skills

Loading agent-sync is the operator's standing grant, for this session, of exactly these
departures. Everything else in those skills stands.

| Skill | Rule | Under agent-sync |
|---|---|---|
| git-workflow | push only after per-push approval | push `main` inside an integration unit without asking; never `--force` or `--force-with-lease` |
| git-workflow, agent-fleet-orchestration | commits only when prompted; `-no-commit` workers by default | workers in worktrees may commit on their own branch (use the commit variants); a `-no-commit` worker's diff is committed on its branch, in its worktree, before its unit, so patch integration is never used; the orchestrator commits merges on `main` inside a unit |
| agent-fleet-orchestration | establish a task branch first; never merge into a shared branch | the shared checkout stays on `main` and is never switched; worker branches merge into `main` inside a unit |
| parallel-worktrees-general | Mode A (orchestrator edits) and Mode D (worker in the current checkout) | off: nobody edits the shared checkout outside a unit; resolving a merge conflict inside a unit is the only direct edit |
| parallel-worktrees-general | Mode B bases a worktree on `HEAD` | `git fetch`, then base it on `origin/main`: the shared `HEAD` may carry another session's unpushed merge |
| parallel-worktrees-general | never rebase a running worker | a running worker may rebase its own worktree onto `origin/main` when told to |
| parallel-worktrees-general | Docker-backed suites and stack up/down are forbidden in worker worktrees and run once after the last merge | a worker runs the stack suite in its worktree before its unit, only as the single `lockctl.py run stack` command its brief gives it (see The stack lock) |

## The two locks

| Lock | Guards | Held for |
|---|---|---|
| `integrate` | the shared checkout's HEAD, index and working tree, and the push of `main` | one integration unit |
| `stack` | the project's Docker stack for integration tests | one test session |

When both are needed, take `integrate` first, then `stack`; never wait on `integrate` while
holding `stack`.

A lock belongs to the session (the `claude` process that acquired it) and to the worktree it was
taken from, and frees itself when that process exits or crashes. Workers are subagents inside
their orchestrator's process, so the worktree is what tells them apart: **only the orchestrator
calls `acquire`**; a worker uses `run` alone, which takes and drops the lock around one command.

A lock does **not** free itself on a compaction, `/clear` or `/resume` inside the same process,
and a resumed conversation may wrongly believe it holds one. So: you hold a lock only if
`lockctl.py check <lock>` says so. After any of those events, run `lockctl.py status` and
release anything you hold outside a running unit. Run `check` before every mutating step of a
unit (merge, commit, push); if it fails, the lock was stolen or lost: stop the unit without
touching the checkout and start over from acquire.

**Waiting and the Bash tool.** A foreground Bash call ends at 10 minutes at most. Wait with
`--wait 9m` and a 10-minute tool timeout. When it returns 75, read `status` and decide: wait
again, or ask the advisor. Anything that runs longer (a stack suite, a long gate) goes through
`lockctl.py run <lock> -- <command>` with `run_in_background`; a lock with a live `run` command
is never stolen, even when herdr shows the pane idle.

## The integration unit

Outside a unit an orchestrator only reads the shared checkout, and reads it with
`git --no-optional-locks` (a plain `git status` briefly takes `.git/index.lock`, which fails
another session's merge or commit). On "index.lock exists" outside step 2, wait and retry;
never delete the file. Everything that writes the checkout is a unit, run start to finish:

1. `lockctl.py acquire integrate --wait 9m --purpose "merge <worker-branch>"`
2. `git fetch`, then check what you inherit. A `.git/index.lock` with no git process running in
   this checkout, a merge in progress, or commits on `main` ahead of `@{u}` that are all
   reachable from worker branches that still exist mean the previous unit died: delete that
   stale `index.lock`, `git merge --abort` if needed, then `git reset --keep @{u}` (the worker
   branches survive, because cleanup happens only after a push). Any other tracked change or
   commit ahead of `@{u}` is operator state: release and ask the advisor.
3. `git merge --ff-only @{u}`.
4. Merge one worker branch as **parallel-worktrees-general** prescribes (`git merge --no-ff`),
   resolving conflicts here. When the repository's CLAUDE.md asks for linear history instead,
   the worker rebases onto `origin/main` in its worktree before you acquire, and here you only
   run `git merge --ff-only <worker-branch>`; if that fails, `main` moved: leave the unit and
   have the worker rebase again.
5. Run the project gate on the result (`lockctl.py run integrate -- <gate>` when it may take
   long).
6. `git push`. A non-fast-forward rejection means someone pushed from outside: `git reset --hard
   @{u}`, back to 3. Any other rejection (hook, protection, auth) is not retried: leave the unit
   early and escalate.
7. `git reset --hard @{u}` to drop anything the gate rewrote, confirm `git status --porcelain
   --untracked-files=no` is empty, `lockctl.py release integrate`, then remove the worker's
   worktree and branch.

After step 2, every tracked change in the shared checkout is the unit's own, which is why
`git reset --hard @{u}` is safe in steps 6 and 7 and when leaving early, and nowhere else.

**Leaving a unit early.** A conflict you cannot resolve, a gate failure that needs a worker, a
push you cannot make, or anything that needs a wait: `git merge --abort` if a merge is in
progress, then `git reset --hard @{u}`, so the checkout is back at the last pushed `main`;
release, then fix in the worker's worktree and integrate again later. Never release with a merge
in progress, a tracked change, or an unpushed commit on `main`, and never hold `integrate` while
waiting for a worker, the advisor or the operator.

**Freshness comes from dispatch, not from a rebase step.** `git fetch`, then create every worker
from `origin/main`, so new work contains everything integrated so far and nothing unpushed. A
worker running from an older base resolves its conflicts in its own unit. When `main` has moved
past a long-running worker's base and touched files it owns, tell it to `git fetch` and `git
rebase origin/main` in its own worktree at its next checkpoint, so its merge stays small.

## The stack lock

The stack suite runs in the worker's worktree, after the worker has committed its work and
rebased onto `origin/main`, and before its integration unit. That keeps the slow suite out of `integrate`, at the price that
`main` may move between the suite and the merge; the unit's gate covers that gap. When the
repository's CLAUDE.md says the stack suite must gate `main` itself, run it inside the unit
instead, in the order `integrate` then `stack`.

Every holder must drive the same stack: use one compose project name from every worktree
(`COMPOSE_PROJECT_NAME`, or the project's recipe), or a reset in one worktree misses the
containers another left behind. Every use starts with a reset (`docker compose down -v`, or the
project's recipe) before bringing the stack up: a previous holder may have died mid-run, and a
free lock plus a reset is what makes the stack safe.

A worker gets the exact command in its brief, reset included, and runs it with
`run_in_background`:

```
~/.claude/skills/agent-sync/scripts/lockctl.py run stack --wait 9m --purpose "<branch> suite" -- \
  sh -c '<reset> && <bring up> && <suite>'
```

An orchestrator that needs several commands on the stack (bring up, run suites, debug) may
`acquire stack` from the shared checkout, run each long command through `run stack -- …`, then
`release stack`.

## Stealing

`lockctl.py status` shows each lock's holder (herdr pane, worktree, branch, purpose, held for,
herdr state, idle time, live `run` commands) and whether it can be stolen. `steal` succeeds only
when the script judges it safe:

| Holder | Result |
|---|---|
| session gone | the lock is already free; `acquire` takes it |
| a live `run` command under the lock | refused |
| herdr shows the holder pane idle or done, unchanged for 10 min, and (for `integrate`) the shared checkout has no tracked changes and no merge or rebase in progress | allowed: the holder forgot to release |
| holder working, checkout dirty or mid-merge, or herdr unavailable | refused |

A waiting `acquire` may take a freed lock before the thief; `steal` then exits 75 and names the
winner. On a refusal you think is wrong, do not delete lock files or kill processes: ask the
advisor. `steal --force` only on the operator's word for that lock.

## Escalation

Route anything you cannot settle (a conflict whose intent you do not understand, a refused steal,
a design question) to the advisor session the operator named, over `SendMessage`. The advisor is
the only session that calls the operator, with `nag.py`. Without an advisor, nag the operator
yourself: `nag.py start <id> --title "<pane>: <question>"`, and `nag.py stop <id>` once they
answer.
