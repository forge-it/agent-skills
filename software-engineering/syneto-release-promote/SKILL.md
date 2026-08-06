---
name: syneto-release-promote
description: Use when shipping a Syneto Central release after its release notes entry has been reviewed and accepted — merging the central-2.x dev branch into the prod branch across every contributing repository and pushing. Also use for asks phrased as "promote the release", "merge dev into prod", "ship the hotfix", or "push the release branches". Syneto-specific: assumes the Central repository family under /home/cristi/Projects.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.3"
---

# Syneto Release Promote Skill

## Purpose

Ship a Syneto Central release: merge the dev branch (`central-2.10`) into the prod
branch (`central-2.9`) across every repository contributing to the release, and push.

This is the step **after** the release notes entry has been published and accepted.
It is deliberately a separate skill from `syneto-release-notes`, which is read-only
and must never touch a worktree. This one merges and pushes to shared prod branches
that trigger CI/CD.

## When to Apply

Apply when the operator has reviewed the published release notes entry and says to
ship, promote, merge, or push the release.

Do **not** apply:
- Before the release notes entry exists and has been accepted (see R1)
- To promote a single repository as a one-off — that is ordinary git, not a release
- To the `central` IaaC repository on its own; it runs on a separate cadence

## Ordering Is Not Negotiable

```
syneto-release-notes  →  operator reviews the page  →  syneto-release-promote
```

The merge **empties** the `prod..dev` range. Once promoted, the release can no
longer be described from git: `acquire.sh` will report every range as 0 and exit 1
with "already merged". The Confluence page is titled "Release notes - **plan**"
precisely because it is written before the release ships.

If you find yourself asked to write release notes for something already promoted,
stop and say so — the ranges are gone and reconstructing them means digging merge
commits out of the prod branch by hand.

## Usage

`promote.sh` sits beside this SKILL.md. Resolve its absolute path first; the working
directory when this skill fires is the operator's project, not the skill directory.

```bash
promote.sh                      # --check (default): preflight only
promote.sh --merge              # preflight, then merge locally; nothing pushed
promote.sh --push               # preflight, merge, and push to origin
promote.sh --push repo-a repo-b # restrict to named repositories
promote.sh --help
```

Mode flags are mutually exclusive — `--check --push` is an error, not a push.

| Variable | Effect |
|---|---|
| `SYNETO_PROMOTE_CONFIRM` | Must equal the dev branch name or `--push` refuses. The consent gate. |
| `SYNETO_PROJECTS_ROOT` | Checkout root; defaults to `/home/cristi/Projects`. |
| `SYNETO_SKIP_FETCH` | Preflight only. **Refused** in `--merge`/`--push`. |
| `SYNETO_PROMOTE_PAIR` | `"<prod> <dev>"`; validated for shape and ordering. |
| `SYNETO_INCLUDE_CENTRAL` | `1` also promotes `central` on `production-on-prem..dev-on-prem`. |
| `SYNETO_ALLOW_MINORITY_PAIR` | `1` downgrades the quorum guard to a warning. |

Exit codes: `0` clean, `1` refused before changing anything, `2` **partially
promoted** — read the per-repository report.

## Run --check, Then Stop

`--check` writes nothing that matters and ends by telling you to stop. Do exactly
that: **print the plan and wait for the operator to answer.** Do not chain `--check`
into `--push` in one turn. The plan lists every repository, its commit count, and
its ticket IDs — a repository showing `NO TICKETS` almost certainly does not belong
in the release, and is the operator's call to strike.

`--push` additionally requires `SYNETO_PROMOTE_CONFIRM=<dev-branch>`. That gate
exists so that pushing to production is always a deliberate act and never a default
that a confidently-worded sentence can talk a model into.

## Core Principles

### 1. Never Promote Before the Notes Are Accepted (CRITICAL)

The notes describe `prod..dev`; promotion destroys that range. Promoting first makes
the release undescribable. Confirm the entry is published and the operator has
accepted it. "I'll write the notes after" is not recoverable.

### 2. Preflight the Whole Fleet Before Touching Any Repository (CRITICAL)

`promote.sh` checks every selected repository — clean tree, refs present, prod
fast-forwardable, no merge conflicts — and refuses the entire run if any one fails.
Half a promoted release is far worse than none: prod branches disagree, CI deploys a
partial release, and the notes describe work that did not all ship.

Conflict detection uses `git merge-tree --write-tree`, which computes the merge
without a checkout. That is a pure object-database operation and **cannot see the
worktree**, so preflight separately checks two things it would otherwise miss:

- **Untracked files the incoming merge tracks.** A local untracked `.claude/settings.json`
  aborts a merge that adds that path. Preflight intersects `git ls-files --others`
  with the diff paths of `prod..dev` and blocks.
- **The prod branch checked out in another `git worktree`**, which cannot be
  switched to.

Both used to pass preflight and then fail at execute, which is the worst possible
place to discover them.

### 3. Tracked Modifications Block; Untracked Files Do Not (CRITICAL)

A repository with modified tracked files is refused — merging would entangle
uncommitted work. Untracked files (`.claude/`, `docs/superpowers/`, and similar) are
harmless to a merge and are tolerated. Never `stash`, `reset`, or `checkout --` to
clear a path; refuse and let the operator decide.

### 4. Merge the Remote-Tracking Ref, Not the Local Branch (HIGH)

`git merge origin/central-2.10`, never `git merge central-2.10`. A stale local dev
branch would promote an older tree than the one the operator reviewed. The script
fast-forwards local prod to `origin/prod` first, and refuses when local prod carries
commits that belong to neither origin branch (see R9 for the exact classification —
"ahead of origin" is not by itself a refusal, because that is the state a resumable
run leaves behind).

For the same reason the script fetches **before** selecting repositories, not after.
Selection reads `origin/prod..origin/dev`; fetching only what was already selected
would make a repository with stale local refs permanently invisible — empty range,
never selected, never fetched — and silently drop work the accepted notes promised.

### 5. Restore the Branch Each Repository Started On (HIGH)

Repositories are routinely parked on feature branches — sometimes on a branch whose
upstream is gone, where `git pull` fails outright. The script never runs `git pull`,
records the starting branch, and switches back to it on success, on failure, and on
`SIGINT`/`SIGTERM` via a trap, so an interrupted run never strands a checkout on the
prod branch with no report.

A repository on a **detached HEAD** is blocked rather than promoted: there is no
branch name to restore, and silently leaving it on the prod branch is worse than
refusing.

### 6. The Promote Set Is a Decision, Not Simply the Contributing Set (HIGH)

`promote.sh` defaults to every product repository with a non-empty range, but the
operator may legitimately hold some back — a repository whose only commit is a CI
chore with no ticket has nothing to ship. `central` is excluded by default because
the IaaC repository runs on its own cadence.

Show the plan and let the operator strike repositories off it. Whatever is promoted
should match what the accepted notes describe; if it does not, say so.

### 7. Report No-Ops as No-Ops (HIGH)

Merging an already-promoted repository succeeds trivially and moves nothing. The
script compares the prod SHA before and after and reports `NO-OP` rather than
`DONE`, because a report saying "succeeded" for a repository where nothing shipped
will be read as a promotion that happened.

### 8. A Push Race Is Expected, Not Exceptional (HIGH)

Work lands on the dev branch while a promotion runs — a `git pull` that reported
"Already up to date" minutes earlier can bring new commits on the next call.

After each successful push the script **re-fetches dev** before measuring the
remaining range. Without that re-fetch the measurement is worthless: pushing updates
the local `origin/prod` ref, which makes `origin/prod..origin/dev` arithmetically
zero every time and reports all-clear on exactly the race it is meant to catch.

A `DONE*` line means commits landed on dev mid-run and did **not** ship. Report
those rather than leaving them for the next release to discover.

### 9. A Failed Run Must Stay Resumable (CRITICAL)

The state a partial run leaves behind — local prod ahead of origin because it
carries the promotion merge — must not be mistaken for local junk. Preflight
classifies each repository:

| State | Action |
|---|---|
| Local prod is an ancestor of `origin/prod` | `merge` — normal path: fast-forward, then merge dev |
| Ahead of `origin/prod`, every extra commit is a merge, contains `origin/dev` | `push-only` — resume an unpushed promotion |
| Ahead of `origin/prod`, every extra commit is a merge, dev has since moved | `remerge` — merge the new dev tip, then push |
| Ahead of `origin/prod` with any **non-merge** extra commit | **blocked** — foreign commits |
| Diverged from `origin/prod` | **blocked** — merge `origin/prod` by hand |

Two details carry the weight:

**Containment is not enough.** `push-only` must verify that everything local prod
holds beyond the two origin branches is a *promotion merge*. A test that only asks
"does local prod contain dev?" also passes for an ordinary commit sitting on top of
the merge — which then ships to production, reported as a clean `DONE`, invisible in
a plan that only shows `origin/prod..origin/dev`. A stray commit on prod during the
operator-review gap is ordinary developer behaviour, not an exotic state.

**Dev moving is not divergence.** If commits land on dev between `--merge` and
`--push`, prod has not diverged — dev advanced. That is `remerge`, not a block.
Treating it as divergence aborts every already-merged repository in the fleet and
sends the operator down a recovery path that does nothing.

## Failure Recovery

**Exit 2 — partially promoted.** Re-run. Repositories that merged but did not push
resume as `push-only`; repositories already fully promoted report `NO-OP`; only the
genuine failures do work. Nothing needs undoing first.

**Interrupted (Ctrl-C).** The trap aborts any in-progress merge and restores the
starting branch, then exits 2. Re-run.

**A repository blocked as "carries N commit(s) that are on neither origin branch".**
Someone committed to the local prod branch outside this flow. Inspect them
(`git log origin/<prod>..<prod> --no-merges`) and decide: they either belong on dev
and should be moved there, or they should be dropped. Do not push them as part of a
release nobody reviewed them for.

**A repository blocked as "has diverged from origin/<prod>".** Local prod and origin
prod have both moved — typically someone pushed a hotfix straight to prod while the
promotion ran. Merge `origin/<prod>` into the local prod branch, verify, and re-run.
Do not `reset --hard`; that discards the promotion merge.

**Commits landed on dev between `--merge` and `--push`.** Nothing to do — the repo
is classified `remerge` and the new tip is merged automatically on the next run.

**A wrong tree reached prod.** Promotions use `--no-ff`, so every promotion is an
auditable merge commit and `git revert -m 1 <merge>` works. Revert as a new commit.
**Never force-push a prod branch** — it breaks every checkout that already pulled.

## Common Mistakes

| Mistake | Consequence |
|---|---|
| Promoting before the notes are accepted | Range is destroyed; the release cannot be described |
| Chaining `--check` into `--push` in one turn | Production push with no operator consent |
| Setting `SYNETO_SKIP_FETCH` to make a write mode run | Promotes a tree nobody reviewed — the script refuses for this reason |
| Merging the local dev branch | Promotes a staler tree than was reviewed |
| Promoting repositories one at a time with no preflight | A conflict halfway leaves prod branches disagreeing |
| Stashing or `reset --hard` to clear a blocked repository | Destroys uncommitted work, or the promotion merge itself |
| Diagnosing a push failure as "someone else pushed" | Hides protected branches, dead credentials, and hooks; the report must carry git's own stderr |
| Reading `promoted` as covering every selected repository | `NO-OP` repositories shipped nothing; check the counts |
| Trusting a range of 0 after a push without re-fetching dev | Always zero; hides the race entirely |
| Force-pushing prod to fix a bad merge | Breaks every checkout that already pulled it |
