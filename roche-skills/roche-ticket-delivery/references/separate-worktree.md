# Separate worktree

Read this only when he picks the separate worktree at stage 6. It is
**parallel-worktrees-general** Mode B with four deviations:
- the branch is `<KEY>-wt`
- the ignore line goes to `.git/info/exclude`
- the worktree's Docker gate gets its own target volume
- the merge back is an uncommitted patch applied with plain `git apply`

## Create

With the main worktree on the work branch:

```
git -C <repo> worktree add .claude/worktrees/<KEY> -b <KEY>-wt HEAD
```

When the repository does not ignore `.claude/worktrees/`, add that line to
`<repo>/.git/info/exclude`, never to `.gitignore`: the ticket's diff stays clean. The path is
under `$HOME`, so Colima mounts it into Docker.

## Bootstrap

A linked worktree starts without git-ignored files. For rdnx that means:
- no `target/`: the gate builds into a Docker volume anyway
- no generated adapter fixtures (`libdnf5-adapter/tests/fixtures/generated/`): the gate's
  adapter tests panic without them. Under the lock, run
  `DOCKER_DEFAULT_PLATFORM=linux/amd64 just test-adapter-fixtures` from `<worktree>` before
  the first gate
- no generated test repositories: the other `*-fixtures` recipes rebuild them when a suite
  needs them
- no `evidence/`

Run the gate from `<worktree>` with its own target volume, `rdnx-target-<KEY>`, as
`repository-traps.md` (rdnx, *Linked worktree*) describes. The first run builds that volume
from cold: expect a long first gate.

## Briefs

Every implementor, fixer and investigator gets:
- the worktree path and the Mode B dispatch block from **parallel-worktrees-general**
- the exact gate command for the worktree, with its target volume
- the statement that you hold the Docker lock

Every reviewer and verifier gets the same, with "read-only on `<worktree>`" in place of the
block.

## Merge back

Merge back when the code review loop ends, converged or capped. An open finding travels in
the report, not in a worktree. The workers did not commit, so the merge is a patch, applied
uncommitted to the main worktree's work branch:

```
git -C <worktree> add -N <each new file>
git -C <worktree> diff --binary HEAD > <run>/<KEY>.patch
git -C <repo> apply <run>/<KEY>.patch
```

Use plain `apply`, not `--3way`: the main worktree has not moved, and `--3way` stages the
change. When it does not apply cleanly, stop and tell him.

Before removing anything, every path in
`git -C <worktree> status --short --untracked-files=all` must appear in
`git -C <repo> status --short --untracked-files=all`. Plain `--short` shows a new directory
as one `?? dir/` line. A missing path means the patch left it out and the worktree holds its
only copy: stop and tell him. This comparison is the validation that *Cleanup* asks for
before it discards the worker copy.

Then discard the worker copy and remove it: `git -C <worktree> reset --hard`,
`git -C <worktree> clean -fd`, `git -C <repo> worktree remove .claude/worktrees/<KEY>`,
`git -C <repo> branch -d <KEY>-wt`, and `docker volume rm rdnx-target-<KEY>`. Never run
`git worktree prune`, which **parallel-worktrees-general** *Cleanup* ends with: it touches
other tickets' worktrees (SKILL.md, stage 11). The patch file stays in `<run>`. Only then, under the Docker lock, run the gate and any
Docker suite the plan schedules, once in the main worktree. A red result goes into the stage
8 report as open: nothing is fixed before he has seen the tree.

From here on the main worktree is the only tree. Later workers run there in Mode D, and their
brief lists the patch's files as their starting tree.
