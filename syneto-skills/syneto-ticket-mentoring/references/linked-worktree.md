# The linked worktree

For a run whose repository's main checkout is on a branch other than the base at stage A: work
in progress, Cristian's or an earlier run's whose MR waits for review. Leave the main checkout
exactly as it is, whatever its status, and work in a linked worktree.

```text
git -C <repo> check-ignore -q .claude/worktrees/x    # fails: add the line to <repo>/.git/info/exclude first
git -C <repo> fetch origin <base>
git -C <repo> worktree add --no-track .claude/worktrees/<KEY> -b <KEY>-<short-slug> origin/<base>
```

`--no-track`, because otherwise the work branch tracks the base and git's own hints
("git pull", "git push origin HEAD:<base>") would merge the base in or push his commit
straight onto the release branch.

The worktree uses the main checkout's `<repo>/.venv`, called directly and never through
`poetry run`; run the import check under *Bootstrap* in the senior's
`references/separate-worktree.md` before the first test. A path under the main checkout there
is an escalation: the worktree stays, and nothing runs in it.

There is no merge-back: the run commits and pushes from the worktree, and stage J's cleanup
removes it as the senior's stage 11 does. Docker-backed tiers run there only where the
repository's *Linked worktree* line in `repository-traps.md` allows it; otherwise the MR says
they were not run.

## Resuming when the main checkout was taken

The ledger's `<checkout>` is the main checkout and it is now on another branch: someone took
it. Leave it.

- The ledger's `dirty:` line is empty: attach the run's branch in a linked worktree
  (`git -C <repo> worktree add .claude/worktrees/<KEY> <branch>`, then the import check
  above), record the new `<checkout>` in the ledger (`fork` stays), and continue.
- It lists files: they went with the checkout. Escalate.
