---
name: syneto-ticket-delivery
description: >-
  Use when the operator hands over one or more SYN Jira tickets to be worked end to end — a
  ticket key or Jira link with "let's do this ticket", "tackle this ticket", "take SYN-1234",
  "work this one", "pick up these subtasks" — when resuming such a ticket in a later session,
  and when he says a ticket's merge request merged. Syneto-specific: assumes the SYN Jira
  board through the Atlassian MCP, repositories under /home/cristi/Projects, and glab
  authenticated to gitlab.syneto.eu.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.1.4"
---

# Syneto Ticket Delivery

## Purpose

Take a SYN ticket from "here it is" to "merged and Done": you orchestrate (read, brief,
verify, report, never implement, never diagnose a failure yourself), a fleet of subagents
does the work, and Cristian decides at the gates below.

Load **agent-fleet-orchestration** once, before the first dispatch. This skill already
answers its intake gate, so do not ask it again:

| Axis | Answer |
|---|---|
| Supervision | supervised |
| Implementer | fleet |
| Plan review | max 2 rounds; round 2 re-checks only what round 1 changed |
| Code review | **change-cycle-pipeline** narrow loop, max 3 rounds, checkers take up to three findings each (stage 7) |
| Operator gates | stages 3, 6, 8, 9, plus every push |
| Gate cadence | at the end: every cycle is implemented in turn, then one review loop over their union (stage 7, one cap of 3), then one stage 8 report |
| Worktree | his answer at stage 6: the main worktree, or a separate one merged back into it; `-no-commit` workers either way, and the main worktree ends dirty |

Re-open one of these only when he changes it.

**Models.** Name no model on any dispatch: every subagent lands on his Sonnet default, and
agent-fleet-orchestration's Opus departures do not apply here. `opus` or `fable` only when he
asks for it on this ticket, recorded in `ledger.md`.

## Stages

| # | Stage | Writes | Gate |
|---|---|---|---|
| 1 | Read the tickets, move them to In Progress, cut the branches | `ticket.md`, `ledger.md` | — |
| 2 | Gather context, read-only | `context-NN-<topic>.md` | — |
| 3 | Three options and a recommendation | `options.md` | **his choice** |
| 4 | Plan the chosen option | `plan.md` | — |
| 5 | Review the plan, max 2 rounds | `plan-review-rN-<lens>.md`, `plan.rN.md` | — |
| 6 | Implement, in the worktree he picks | the dirty tree | **his worktree choice, before it starts** |
| 7 | Review the code, max 3 rounds | `code-review-rN-<lens>.md` | — |
| 8 | Report, tree left dirty | — | **his review** |
| 9 | Refactor or commit | commits | **his word** |
| 10 | Push, hand over the MR, move to Review | `mr.md` | **his word on the push** |
| 11 | Merged: move to Done, clean up | Jira comment | — |

Everything lives in a run directory, `~/.cache/ticket-delivery/<KEY>/`, never the session
scratchpad. `<KEY>` is the parent story's key when every ticket is a subtask of one story,
else the first ticket's key. `ledger.md` is written at stage 1 and opens with the stage
reached; the repositories with their base and work branches, and their merge and deploy
order when there is one; the worktree choice once made; and each ticket's status with the
repositories it covers, plus any pending deploy push with its condition. Update the stage
line at every stage change, a ticket's status at every move, and inside stages 5 and 7 at
every round (`5: round 2 dispatched, triage pending`, then `5: round 2 triaged,
plan revised`). From stage 6 it is also **change-cycle-pipeline**'s ledger, kept here so
nothing is added to a repository's `.gitignore`. Its last line is `complete` once every
ticket is Done, no push is pending, and stage 11's cleanup has run.

Working rules, at every stage:

- When he asks a question, answer it and wait. A question is never an instruction to act.
- When his message makes a running agent's work obsolete, ask him whether to stop it, or
  re-brief it with SendMessage. Never stop it on your own call.
- Every failure (a red test, a broken container, an unexpected error) goes to an issue
  investigator; you verify its answer before it reaches him, a ticket or an MR.

### 1. Read the tickets

Fetch each ticket with the Atlassian MCP's `getJiraIssue` (the server's name changes between
sessions, so find the tool by searching for `getJiraIssue`): summary, description, comments,
subtasks, links. Fetch every subtask in full too, and the parent's description when there is
one: decisions often live only there.

Settle the repositories and the base branch. The base is the one he names. Unnamed, it is
the branch the ticket's Fix version corresponds to: a Central version is the branch name
(`central-2.10`), and a Syneto OS version `X.Y.Z` is the branch `release-X.Y.Z`.
`git -C <repo> ls-remote --heads origin <base>` must print the branch; when it prints
nothing, that version has no branch yet. "central" means rest-api, central-api and
central-backend, not the deploy repo. For each Python repository except the deploy repo
(nothing runs there locally), check that `<repo>/.venv/bin/python` exists.

Then ask, in **one** message, everything that applies:
- `/add-dir <path>` for `~/.cache/ticket-delivery` and each repository in scope that is not
  among the session's working directories (a session opened inside one repository sees only
  that one). `/add-dir` refuses a path that does not exist, so `mkdir -p
  ~/.cache/ticket-delivery/<KEY>` before you ask.
- which subtasks this work covers, when he handed over only the parent: subtasks can belong
  to another team
- the base, when he named none and the Fix version gives none, gives two, disagrees with
  him, or has no branch on origin; never fall back to the previous release
- whether to create a missing venv, with what building it needs (the repository's section
  in `references/repository-traps.md`); never brief a worker with an interpreter that is
  not there

The tickets in scope are the ones he handed over plus the subtasks he confirms. Write
`ticket.md` (verbatim) and `ledger.md`, then move every ticket in scope to **In Progress**
(see *Ticket status*).

Then cut the work branch in each repository, yourself, before any gatherer reads the code.
**Always pull first.** Never branch from the local base without pulling, and never from
`origin/<base>` after a fetch. Run these literally:

```
git -C <repo> status --short     # must be empty: his uncommitted work is not yours to move
git -C <repo> checkout central-2.10
git -C <repo> pull --ff-only
git -C <repo> rev-list --left-right --count central-2.10...origin/central-2.10   # 0 and 0, tab-separated
git -C <repo> checkout -b <KEY>-<short-slug> central-2.10
```

When the base is another branch, it replaces `central-2.10` in every line. When the base has
no local branch yet, replace the checkout line with `git -C <repo> fetch origin <base>` and
`git -C <repo> checkout --track origin/<base>`, then go on from the pull. Same branch name in
every repository. When the status is not empty or the pull refuses to fast-forward, stop and
tell him: never stash, reset or merge to get past it. A repository that stage 2 adds to the
scope gets the same sequence then.

**The deploy repo `~/Projects/central` gets no work branch.** The branch is the environment,
and only `dev-on-prem` and `production-on-prem` are live. Run only these, on the environment
he names, and never `checkout -b`:

```
git -C ~/Projects/central status --short     # must be empty
git -C ~/Projects/central checkout dev-on-prem
git -C ~/Projects/central pull --ff-only
```

### 2. Gather context

Dispatch gatherers in parallel, one per repository or open question: general-purpose
agents, briefed read-only on the repositories, each writing only its own
`context-NN-<topic>.md`. Give each an **exhaustive** mandate: every reference to the code in
play, including docs, api-docs, packaging, CI, the deploy repo and the tests, with
`file:line` for each claim.

Check the ticket's premise too: the bug reproduces, the producer it depends on is released,
the flag has the value you think. A code default is not the deployed value: read it on the
two live deploy branches without touching his checkout,
`glab api "projects/infra%2Fcentral/repository/files/<url-encoded path>/raw?ref=dev-on-prem"`
and the same for `production-on-prem`, never on the dead ones. A reproduction goes to an
issue investigator: one per repository, never beside another writer in that checkout, told
to change no git state and to leave `git status --short` exactly as it found it.

No subagent runs `kubectl`. When runtime state matters beyond the two branches, run
`kubectl config current-context` yourself first. A context naming production means stop and
ask him; never `exec` there. On the dev cluster, `kubectl exec <pod> -- env | grep <VAR>` is
read-only evidence that outranks the branch.

Read the cited lines behind every claim your options will rest on before you build on it.

### 3. Options — gate

Present three genuinely different approaches. For each: what it changes (repositories,
files), what it fixes and what it leaves, size, risk, and how hard it is to reverse. Then
your recommendation and the reason. When only one approach is viable, say so and name what
you rejected and why: never pad with straw men.

Ask with `AskUserQuestion`, recommended option first. Record his choice in `options.md` as a
**locked scope**: what is in, what is out. The planner and every reviewer get it.

### 4. Plan

Dispatch a planner (general-purpose) with `ticket.md`, the context files, the locked scope,
and the brief essentials. Tell it to load **superpowers:writing-plans** with three
overrides: the plan goes to `<run>/plan.md` and nowhere in a repository; no task has a
commit step, because the tree stays dirty; and it returns when the file is written, without
offering execution options. The plan holds:

- **real code**, never a description of code: placeholders are where implementors invent
- exact files, and the exact test command for each task
- tasks that each end on a green suite
- the verified facts the plan rests on, each with `file:line`
- for a ticket spanning repositories, their merge and deploy order and why
- open questions for him

Read it against the locked scope before review, and copy any merge and deploy order into
`ledger.md`.

### 5. Plan review

At most two rounds: round 1 reviews the whole plan, round 2 checks only what round 1's
triage changed. A reviewer re-reads the whole plan at every step it takes, so a full round
costs millions of tokens, and a second full round costs more than the first because the
plan has grown (SYN-3101: about 5M, 7M and 10M for three full rounds).

**Round 1** is one reviewer per stack the plan touches, plus one lens per area it touches,
all dispatched in one message. Each is a general-purpose agent carrying a prompt from
`/home/cristi/Projects/agent-skills/prompts/plan-review/` verbatim: fill its `<X> =` line
with `<run>/plan.md` and its `<Y> =` line with `<run>/plan-review-r1-<lens>.md`, and add one
line after them, `Locked scope: <run>/options.md`.

- a reviewer per stack: `single-language/plan-review-<stack>.md` for python, rust, vue or
  react; `generic/plan-review-loss-framing.md` for any other stack (central-api, the deploy
  repo)
- a lens from `lenses/`: operational readiness for a cronjob, a deployment, config or an
  alert; security for authorization, tenancy or exposed data; tests and migrations for a
  schema change

The `subagents/` pipeline runs only when he asks for it: it costs too much for a routine
round.

Then triage every finding. First copy the plan the round reviewed to `<run>/plan.rN.md`.
Take a reviewer's **diagnosis** without necessarily taking its **fix**: a correct problem
whose prescribed fix leaves a task ending red gets a different fix. Revise `plan.md`, and
append to it a **Review history** section: each finding, its verdict, and what you changed
or why you did not. That section is how round 2 avoids raising anything twice.

A round 1 with no Blocking or Important finding ends the review. Otherwise run **round 2**:
only the reviewers and lenses whose round 1 file holds a Blocking or Important finding, all
in one message, each with the same prompt, `<Y> =` `<run>/plan-review-r2-<lens>.md`, the
locked-scope line, and these lines after it, paths filled:

```
This is a re-check round; where these lines disagree with the prompt above, they win.
Your round 1 findings are in <run>/plan-review-r1-<lens>.md. See what changed since with
`diff -u <run>/plan.r1.md <run>/plan.md`, and read the plan's Review history section.
For each of your round 1 findings, say whether the revision, or the Review history's
reason for not changing it, settles it. Then review only the changed hunks, against the
code, for defects the change introduced. Do not re-review what the diff leaves untouched;
open the rest of the plan only for the context of a change.
```

Triage round 2 the same way, then stop. What round 2's triage changed is not reviewed
again, so it goes to him at stage 6 as changed after the last review (`diff -u
<run>/plan.r2.md <run>/plan.md` shows it); what is still open goes as open, never as
passed. A third round runs only when he asks for it.

### 6. Implementation — gate

Show him the cycle cut (which plan tasks form each cycle, the files each touches, its gate
command), what the review changed (marking what changed after the last round), anything
still open, and the open questions. Then ask with `AskUserQuestion` where the
implementation runs:

- **Main worktree**: **parallel-worktrees-general** Mode D. The workers edit the
  repository's own checkout, on the work branch, one writer at a time.
- **Separate worktree**: Mode B. The workers edit a linked worktree; after the code review
  the change is merged back into the main worktree.

His answer confirms the cycle cut and is the go-ahead; record it in `ledger.md`. For the
separate worktree, follow `references/separate-worktree.md` beside this file.

Then run **change-cycle-pipeline** with the cycles he just saw: one brief per cycle, the
implementor the repository's section of `references/repository-traps.md` names, `-no-commit`,
or general-purpose briefed "do not commit" in those words. Independent repositories can run
in parallel; inside one repository, one writer at a time.

### 7. Code review

**change-cycle-pipeline**'s narrow loop, cap 3. Each lens carries its prompt verbatim with
`<X> =` `<run>/plan.md`, `<Y> =` `<run>/code-review-rN-<lens>.md` and `<Z> =` the base
(left empty, it diffs against a guessed default branch). When a change adds or edits tests, dispatch that stack's
structure-and-style guard (`python-`, `react-`, `vue-` or `rust-`) beside the lens in every
round: the runtime lens cannot see test-structure violations.

**Checkers take findings in threes, not one each.** This replaces the pipeline's verify
step; its other rules (merge duplicates first, drop what an earlier round refuted) still
hold. Every checker reads the same diff, so one per finding pays for that reading once per
finding, while one checker for the whole round lets one verdict colour the next. Group the
round's merged findings, every severity, into checkers of up to three, keeping findings on
the same file or code path together, and dispatch them all in one message. Each gets these
lines, paths filled and `<out>` its own
`<run>/code-review-rN-verdicts-K.md` (K numbers the round's checkers), then the findings
pasted in full with their citations and plan locations:

```
You are a skeptic. Below are claimed problems with the implementation of plan
<run>/plan.md in <repo>, diffed against <base>. Judge each one on its own: a verdict on
one finding is no evidence about another. Try to REFUTE each against the actual code, the
plan text and the neighbouring tests: does the cited code say what the finding claims,
and does the problem actually follow? You may run the cited test or a scoped read-only
command; never modify a file. CONFIRMED needs a concrete wrong behaviour, a material
contractual omission, a test that cannot catch the defect it claims to cover, or an
operational gap the plan asked for. Style preference and hardening the plan never asked
for are REFUTED, and so is anything you cannot verify. Write to <out>, per finding: its
title, the verdict, then at most three sentences of evidence with file:line citations.
```

A finding whose fix touches a schema, a migration, a public API or a wire format still
gets the pipeline's three-checker panel, majority wins: three more checkers in the same
message, each with these lines, its own `<out>` and that finding alone.

A red gate is the pipeline's "send a fixer" step, with an investigator first: an issue
investigator of the matching stack, briefed with the failing test id and the command that
reproduces it, never your hunch. It runs alone in that tree and leaves `git status --short`
as it found it. Then the fixer, carrying the investigator's root cause.

With a separate worktree, merge it back when the loop ends, converged or capped, as
`references/separate-worktree.md` describes, before the report.

### 8. Report — gate

First dispatch a writer (Mode D, in the main worktree) told to load **reconcile-docs** over
the whole diff against the base named explicitly, so it never runs `git remote set-head`.
**change-cycle-pipeline** runs that step after his acceptance; here it runs before his
review, so every doc edit is in the tree he reads and nothing is edited after his word at
stage 9.

Then give him **change-cycle-pipeline**'s operator report plus `git -C <repo> status --short` for
each repository (a diffstat omits new files). Every finding in plain words with its exact
`file:line`. The tree stays dirty. Then stop.

### 9. Refactor or commit — gate

Refactors he asks for go to a fixer or implementor in Mode D, followed by the gate and a
fresh stage 8 report.

Commit only when he says so, and only in the repositories he names. When another repository
looks ready too, say so in one line and wait. One commit per repository unless he says
otherwise. The subject takes the repository's own shape (`git -C <repo> log --format=%s -20`
shows it) and carries the keys of the tickets the diff implements: the subtasks when there
are any, else the ticket itself. The body says why; no AI trailers.

"Commit and push <repo>" is his approval for both stages 9 and 10 in that repository: show
the exact push command as you run it, and do not ask again. In the deploy repo it still
holds the push while what the ledger's order makes it wait on is not done (an unmerged MR,
an image not yet published): say so, and push once it is.

### 10. Push and the merge request

Push only on his word, only what he named: `git -C <repo> push -u origin <branch>`. Then
write `<run>/mr.md`, ready to paste:

- **title:** the commit subject
- **description:** dev to dev, in plain words: what changed and why, how it was tested, the
  risk, and the ticket link. When the ledger records a merge or deploy order, state it and
  why, in the same words in every MR of the ticket.
- **link:** the MR must target the base explicitly, because a project's default branch is
  not always the dev branch. Hand him
  `https://gitlab.syneto.eu/<group>/<repo>/-/merge_requests/new?merge_request%5Bsource_branch%5D=<branch>&merge_request%5Btarget_branch%5D=<base>`,
  or, when he asked you to open it,
  `glab mr create -R <group>/<repo> --source-branch <branch> --target-branch <base> --title "<title>" --description "<description>"`,
  then read the target back with `glab mr view <branch> -R <group>/<repo>`.

`<group>/<repo>` comes from `git -C <repo> remote get-url origin`. Hand him the three, with
any order first. A ticket moves to **Review** once every code repository it covers has had
its MR link handed over; the MR itself may not exist yet, so record its URL in `ledger.md`
and `mr.md` when you learn it. Until then the ticket stays In Progress, and the report names
the repository still unpushed.

Arm one Monitor per pipeline the push started, each reporting jobs as they finish, and send
an investigator on the first blocking failure. The ids come from
`glab api "projects/<group>%2F<repo>/pipelines?sha=<pushed sha>"`, repeated every 15 seconds
until the list is not empty; after two minutes, tell him no pipeline started.

**A push to the deploy repo is a deployment**: CI runs `pulumi up` on the branch pushed.
There is no MR, so the deploy repo does not count toward Review; it counts toward Done once
its branch is pushed. When you ask for that push, say "this deploys to `<branch>`" and name
what it waits on, such as the image the code repository's post-merge pipeline publishes.
Push that branch only on his explicit word for it. A word that waits ("after the MR
merges") goes into `ledger.md` as a pending push with its condition, and stage 11 runs it.
When
the deploy repo is a ticket's only repository, ask him at the push which status the ticket
takes, and record his answer in `ledger.md`.

### 11. Merged — Done

When he says a repository's MR merged, or `glab mr view <branch> -R <group>/<repo> -F json`
shows `state: merged`, mark that repository merged in `ledger.md`.

Then run any pending deploy push the ledger records. Its image exists once the post-merge
pipeline passes: `glab api "projects/<group>%2F<repo>/pipelines?ref=<base>&sha=<merge_commit_sha>"`
(`squash_commit_sha` when that is null), watched by a Monitor until `success`; `pulumi up`
pins the image digest it finds, so an earlier push deploys the old image. Then
`git -C ~/Projects/central status --short --branch` must match the ledger and
`pull --ff-only` must succeed; when either fails, stop and tell him. Commit the reviewed
change if it is still uncommitted (his word for the push covers that commit), push with the
command shown, and arm its Monitor.

Once every code repository a ticket covers is merged and its deploy branch, if it has one,
is pushed, move the ticket to **Done** without asking, subtasks
before their parent. Comment on each: per repository, the commit that landed
(`squash_commit_sha` when that output's `squash` is true, else `merge_commit_sha`; squash is
chosen per MR, so read it every time) and its `target_branch`, then the acceptance criteria
as a checklist. Fetch nothing into his checkout for this. Comment on tickets; never edit a
description he did not ask you to edit.

Then clean up each code repository once its MR is merged, without asking. Touch only what
the ledger records for this ticket: its work branch, and its linked worktree when one
survived (no merge-back, or a resumed run). Everything else in the repository belongs to
someone else however stale it looks (another ticket's worktree, a review checkout, an entry
git marks `prunable`), so never run `git worktree prune`.

First prove nothing is lost. The local branch tip must equal the `sha` field of
`glab mr view <branch> -R <group>/<repo> -F json`, the commit GitLab merged, and
`git -C <path> status --short` must be empty in every checkout on that branch. For a linked
worktree, also list what still runs inside it (his terminal, his editor's language server,
a dev server):

```
for p in /proc/[0-9]*; do c=$(readlink "$p/cwd" 2>/dev/null); case "$c" in <worktree>*) echo "$(basename "$p") $(tr '\0' ' ' < "$p/cmdline")";; esac; done
```

When a check fails or a process shows up, stop and tell him what you found: never remove
a tree from under his tools. Then, in this order:

- a linked worktree: `git -C <repo> worktree remove .claude/worktrees/<KEY>`
- a main checkout still on the work branch (the main-worktree choice, or after a
  merge-back): `git -C <repo> checkout <base>`, then `git -C <repo> pull --ff-only`. A main
  checkout on any other branch is someone else's work: leave it.
- the branch: `git -C <repo> branch -D <branch>`. `-D`, because git never sees a squash-merged
  branch as merged; the `sha` check above is what makes it safe.

The remote branch is GitLab's to delete on merge: delete it only on his word. Keep the run
directory, it is the record. Then write `complete` in `ledger.md`.

## Resuming

List `~/.cache/ticket-delivery/*/ledger.md`. Open the run whose directory or ticket list
carries the key he names, else the only one not marked `complete`, else ask him. Before acting,
re-verify:
- `git -C <repo> status --short --branch` matches the ledger's branch and dirty files
- each ticket's status in Jira matches the ledger
- every repository in the ledger is among this session's working directories

When something differs, stop and tell him before any dispatch or transition. Stage 11 is
the exception: moving to Done needs only `glab` and Jira, and the cleanup runs its own
checks, so skip the branch and working-directory checks there. Then continue from the stage the ledger names. In stage 5 or 7, a round whose
review files exist but that the ledger does not record as triaged is untriaged: triage it,
never re-run it.

## Ticket status

| When | Move to |
|---|---|
| Stage 1, he hands you the tickets | In Progress |
| Stage 10, every code repository the ticket covers has had its MR link handed over | Review |
| Stage 11, every one of those MRs is merged and any deploy branch is pushed | Done |

Never reuse a transition id: fetch `getTransitionsForJiraIssue` for each issue **at its
current status** and match the target status by name, because a wrong id succeeds into a
plausible wrong state (from In Progress, `4` is Review on a Story but "No review needed" →
Done on a Subtask). Read the status back after every move.

- Anything that is not a Subtask (a Story, a Bug) will not move to In Progress until Fix
  versions is set: set the version that corresponds to the base (stage 1) with
  `editJiraIssue` first. When no version matches, ask him.
- From Review, a Subtask has "Review OK" → Done; prefer it after a merge.
- A parent moves to Review or Done only once every one of its subtasks, including any
  outside this run, is at that status or past it; until then it stays In Progress, and the
  report names the subtask holding it.

## Brief essentials

Every dispatch that touches a repository carries:

- the absolute repository root (`~/Projects` itself is not a repository) and `git -C <repo>`
  for every git command
- the interpreter: `<repo>/.venv/bin/python` of the main checkout, also in a linked
  worktree, with the directory it must run from
- absolute paths for the files to open
- scope, out of scope, and the locked scope from stage 3
- for a dispatch that edits files (implementor, fixer, investigator): the dispatch-mode block
  from **parallel-worktrees-general** (Mode D or Mode B); for any other: "read-only on
  `<repo>`"
- "git is read-only for you except the files you edit: no commit, stash, fetch, pull,
  checkout or reset; a fetch here can move HEAD. No `kubectl`."
- that repository's section of `references/repository-traps.md` beside this file: its gate,
  its traps, and its agent
