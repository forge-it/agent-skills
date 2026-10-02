# Separate worktree

Read this only when he picks the separate worktree at stage 6. It is
**parallel-worktrees-general** Mode B with three deviations: the branch is `<KEY>-wt`, the
ignore line goes to `.git/info/exclude`, and the merge back is an uncommitted patch applied
with plain `git apply`.

## Create

With the main worktree on the work branch:

```
git -C <repo> worktree add .claude/worktrees/<KEY> -b <KEY>-wt HEAD
```

When the repository's `.gitignore` does not cover `.claude/worktrees/`, add that line to
`<repo>/.git/info/exclude`, never to `.gitignore`: the ticket's diff stays clean.

## Bootstrap

A linked worktree starts with no dependencies.

- **Node:** install them in the worktree with the repository's own command, under the
  repository's Node version (see its section in `repository-traps.md`): for central-api,
  `PATH=$HOME/.nvm/versions/node/v18.20.4/bin:$PATH yarn install --frozen-lockfile`; for
  central-hub, `npm ci`.
- **Python:** the worktree uses the main checkout's `<repo>/.venv`. Every command calls
  `<repo>/.venv/bin/<tool>` directly, from the directory the gate runs in (the repository's
  section in `repository-traps.md` names it). Never `poetry run`, and never a `make` target
  that calls it: Poetry finds the venv from the project directory and builds a new, empty one
  inside the worktree.

  For central-backend, first generate its gitignored gRPC modules, from `<worktree>`:
  `PATH=<repo>/.venv/bin:$PATH python -m grpc_tools.protoc -I. -Iprotolib/src/protoc-gen-validate --python_out=. --grpclib_python_out=. $(find . -path ./protolib -prune -o -name '*.proto' -print)`
  (`compile.sh`'s own command without `poetry run`; the `PATH` entry is how protoc finds
  grpclib's plugin). Without them every test fails to import.

  Before the first worker, run
  `<repo>/.venv/bin/python -c "import <package>; print(<package>.__file__)"` from the
  directory the **test** command runs in: `<worktree>/src` for syneto-diana (`diana`), the
  worktree root for rest-api (`central_rest_api`) and central-backend (`central_backend`).
  An ImportError, or a path under the worktree, is fine. A path under the main checkout means the gate would
  test the main checkout's code: stop, tell him, and offer the main worktree instead (then
  remove the linked one as *Cleanup* describes). A venv built by `poetry install` carries an
  editable path to the main checkout unless `pyproject.toml` sets `package-mode = false`,
  which is why the directory matters.

## Briefs

Every implementor, fixer and investigator gets the worktree path, the Mode B dispatch block
from **parallel-worktrees-general**, the interpreter, and the gate directory. Every reviewer
and verifier gets the same with "read-only on `<worktree>`" in place of the block.

## Merge back

When the code review loop ends, converged or capped. An open finding travels in the
report, not in a worktree. The workers did not commit, so the merge is a patch, applied
uncommitted to the main worktree's work branch:

```
git -C <worktree> add -N <each new file>
git -C <worktree> diff --binary HEAD > <run>/<KEY>.patch
git -C <repo> apply <run>/<KEY>.patch
```

Plain `apply`, not `--3way`: the main worktree has not moved, and `--3way` stages the change.
When it does not apply cleanly, stop and tell him.

Before removing anything, every path in `git -C <worktree> status --short --untracked-files=all`
must appear in `git -C <repo> status --short --untracked-files=all` (plain `--short` shows a
new directory as one `?? dir/` line). A missing path means the patch left it out and the
worktree holds its only copy: stop and tell him. This comparison is the validation *Cleanup*
asks for before it discards the worker copy.

Then remove the linked worktree and its branch as **parallel-worktrees-general** *Cleanup*
describes (the patch is applied, and its file stays in `<run>`). Only then run the gate once
in the main worktree: while the linked worktree exists, central-api's Jest glob also
collects `.claude/worktrees/<KEY>/build`. A red result goes into the stage 8 report as open:
nothing is fixed before he has seen the tree.

From here on the main worktree is the only tree: later workers run there in Mode D, and
their brief lists the patch's files as their starting tree.
