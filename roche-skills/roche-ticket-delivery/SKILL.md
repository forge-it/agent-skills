---
name: roche-ticket-delivery
description: >-
  Use when the operator hands over one or more NIFS Jira tickets from the RDNX board to be
  worked end to end — a ticket key or Jira link with "let's do this ticket", "tackle this
  ticket", "take NIFS-1234", "work this one", "pick up these subtasks" — when resuming such a
  ticket in a later session, and when he says a ticket's merge request merged. Roche-specific:
  assumes the NIFS project's RDNX board on navify.atlassian.net through the Atlassian MCP,
  repositories under ~/Projects, and glab authenticated to code.roche.com.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.1.0"
---

# Roche Ticket Delivery

## Purpose

Take a NIFS ticket from the RDNX board from "here it is" to "merged" and into its post-merge
status. You orchestrate: you read, brief, verify and report. You never implement, except the
takeover under *Models*, and never diagnose a failure yourself. A fleet of subagents does the work, and Cristian decides at the
gates below.

Load **agent-fleet-orchestration** once, before the first dispatch. This skill already
answers its intake gate, so do not ask it again:

| Axis | Answer |
|---|---|
| Supervision | supervised |
| Implementer | fleet |
| Plan review | max 2 rounds; round 2 re-checks only what round 1 changed |
| Code review | **change-cycle-pipeline** narrow loop, max 3 rounds, one `haiku` checker per finding at effort `max` (stage 7) |
| Operator gates | stages 3, 6, 8, 9, plus every push |
| Gate cadence | at the end: every cycle is implemented in turn, then one review loop over their union (stage 7, one cap of 3), then one stage 8 report |
| Worktree | his answer at stage 6: the main worktree, or a separate one merged back into it unless he keeps it without a merge-back. Workers are `-no-commit` either way, and the checkout holding the change ends dirty |

Re-open one of these only when he changes it.

**Models.** His global instructions set the models, and they win over any skill or agent
definition. Pass `model` and `effort` explicitly on every dispatch:

| Role | Model and effort |
|---|---|
| Implementors, fixers, test writers | `sonnet`, `xhigh` |
| Plan reviewers, code-review lenses, structure-and-style guards | `sonnet` at `medium`, or `haiku` at `max` when the review is simple. Say which in one line |
| Stage 7 checkers (refuters) | `haiku`, `max`, always |
| Gatherers, the planner, issue investigators, the stage 8 docs writer, the final-gate agent | what he names. Ask once at stage 1 and record it in `ledger.md` |

A model or effort he asks for on a ticket wins over these defaults on every dispatch it
covers, the checkers included. Record it in `ledger.md`. When an implementor, fixer or test
writer fails the same task twice, do the task yourself. This replaces
change-cycle-pipeline's "fail the cycle" in those rows: a second failed dispatch of the same
task (no result, no required handoff, or the same gate still red) means you take the task
over, under the Docker lock, in the checkout holding the change. The stage 8 report says you
did. Before you write, load the skills that the repository's *Agents* line in
`references/repository-traps.md` names for workers, read `docs/layout.md` as its
`project_structure.md`, and `docs/testing.md` (*Structure rules*) for the rules its gate
enforces. Run the gate as the worker's brief says.

## Where things are

| What | Where |
|---|---|
| Jira site | `navify.atlassian.net`, cloudId `3ccaad2c-2e75-4a7c-b9aa-c3eddcd6a020` |
| Project and board | project `NIFS`, which other teams share. Board `RDNX`, Scrum, id `22713`. Sprints are named `RDNX PI<n>.<m>` |
| Confluence | space `nIfS` ("navify Integrator - Services Module"), mixed case. Never `iEdge`, `LA` or `NDIP` |
| Code | Roche GitLab, `code.roche.com`, via `glab`. Group and project from `git -C <repo> remote get-url origin`. rdnx is `remix/nifs/rdnx` |
| Repositories | `~/Projects/<name>`. rdnx is `~/Projects/rdnx`, default branch `main` |

## Stages

| # | Stage | Writes | Gate |
|---|---|---|---|
| 1 | Read the tickets, cut the branches, move them to In Progress | `ticket.md`, `ledger.md` | — |
| 2 | Gather context, read-only | `context-NN-<topic>.md` | — |
| 3 | Three options and a recommendation | `options.md` | **his choice** |
| 4 | Plan the chosen option | `plan.md` | — |
| 5 | Review the plan, max 2 rounds | `plan-review-rN-<lens>.md`, `plan.rN.md` | — |
| 6 | Implement, in the worktree he picks | the dirty tree | **his worktree choice, before it starts** |
| 7 | Review the code, max 3 rounds | `code-review-rN-<lens>.md` | — |
| 8 | Report, tree left dirty | — | **his review** |
| 9 | Refactor or commit | commits | **his word** |
| 10 | Push, create the MR, move to In Code Review | `mr.md` | **his word on the push** |
| 11 | Merged: post-merge status, clean up | Jira comment | — |

Everything lives in a run directory, `~/.cache/roche-ticket-delivery/<KEY>/`. Never use the
session scratchpad or the repository tree for it. `<KEY>` is the parent story's key when every
ticket is a subtask of one story, else the first ticket's key.

`ledger.md` is written at stage 1. It opens with the stage reached, then holds:
- the repositories with their base and work branches, and their merge order when there is one
- each ticket's issue type and its post-merge status (see *Ticket status*)
- the models he named for gatherers, the planner, investigators, the stage 8 docs writer
  and the final-gate agent, and any model or effort he set for this ticket
- container names he chose to keep when the Docker check found them (see *Working rules*)
- the worktree choice, once made
- the checkout holding the change, and its `git status --short --untracked-files=all`
  after each writer returns
- each ticket's status, with the repositories it covers

Update the stage line at every stage change, a ticket's status at every move, and inside
stages 5 and 7 at every round, naming the set dispatched
(`7: round 2 dispatched (rust, guard), triage pending`, then
`7: round 2 checkers dispatched (1 <title>, 2 <title>, ...)`, then `7: round 2 triaged`).
From stage 6 the ledger is also **change-cycle-pipeline**'s ledger.
It is kept here so nothing is added to a repository's `.gitignore`. Its last line is
`complete` once every ticket has reached its post-merge status and stage 11's cleanup has run.

Working rules, at every stage:

- When he asks a question, answer it and wait. A question is never an instruction to act.
- When his message makes a running agent's work obsolete, ask him whether to stop it, or
  re-brief it with SendMessage. Never stop it on your own call.
- Every failure (a red test, a broken container, an unexpected error) goes to an issue
  investigator. You verify its answer before it reaches him, a ticket or an MR.
- Agents' working files go in the run directory or the session scratchpad, never in the
  repository tree. Every brief names that directory and says that the only repository files
  the agent may create or change are its deliverables.
- A git worktree lives only at `<repo>/.claude/worktrees/<name>`, inside the repository it
  belongs to. Never put one in the session scratchpad, whatever another skill defaults to:
  that is where he and stage 11 look for it, and Colima mounts only `$HOME` into Docker.
  Create one only with `git -C <repo> worktree add .claude/worktrees/<name>`. Never use
  EnterWorktree or an `isolation: "worktree"` dispatch: both build in the session's own
  repository, from the remote's default branch. You create the separate worktree he asks for
  (`references/separate-worktree.md`) and your own `--detach` checks, and remove the checks
  once done. A subagent creates only the temporary worktree its brief allows.
- Docker runs one session at a time on this machine, under a lock, and ends with its
  containers gone. Docker runs in Colima, an aarch64 VM with 4 CPUs and 8 GiB that he also
  works in. rdnx's gate and suites share named images, volumes (`rdnx-target`,
  `rdnx-cargo-registry`, `rdnx-seed`) and fixed container names (`rdnx-systest-*`,
  `rdnx-reclike-*`, `rdnx-fixbuild*`). A second session would build into the same target
  volume and remove the other's containers.
  - **Take the lock** before anything Docker runs: `mkdir ~/.cache/docker-tests.lock`. It
    fails while another session holds the lock. Then run
    `echo "<KEY> pid=$PPID <tree> $(date -Iseconds)" > ~/.cache/docker-tests.lock/owner`.
    When `mkdir` fails, read `owner`, tell him who holds the lock, and wait in a background
    Bash (`until [ ! -d ~/.cache/docker-tests.lock ]; do sleep 30; done`). Never remove a
    lock you did not take, even when its owner looks dead: ask him.
  - **Check that no container is left:** `docker ps -a --filter name=rdnx-` must list
    nothing except the names `ledger.md` says he keeps. Any other container belongs to
    nobody holding the lock, either his own or one left behind. The run would reuse it, write into it or replace it, so ask him first.
    When he lets the run go ahead, record in `ledger.md` the names he keeps, and leave those
    out of the removal at the end. Before a suite that replaces or reuses one of them (the
    smoke suite recreates `rdnx-repo`; the system suite reuses `rdnx-systest-repo` with its
    old bind mount), tell him and wait. When he lets it go ahead, drop that name from the
    kept list in `ledger.md` and from the subagent Docker lines: what the suite leaves is
    this session's, and the session end removes it.
  - **Run long commands in the background.** A cold gate takes about a quarter of an hour,
    longer than the Bash tool's 10-minute foreground limit. Run the gate, a fixtures recipe
    and every suite with `run_in_background`, and wait for its exit.
  - **End the session in the same turn, whether the run passed, failed or was killed.**
    Every container that `docker ps -a --filter name=rdnx- --format '{{.Names}}'` lists now,
    except the ones the ledger says he keeps, was started by this session. The smoke suite
    leaves `rdnx-repo` running by design, and the system suite leaves `rdnx-systest-repo`.
    Remove them with `docker rm -f <names>`. Confirm the filter lists only the kept names,
    and that `docker ps -q --filter volume=<v>` lists nothing for every target volume this
    session used (the gate's container has no name). When it lists a container, the gate
    behind it is still running: if its run is alive, wait for it to exit; if its run was
    killed, `docker rm -f` it. Then check again, and only then run
    `rm -r ~/.cache/docker-tests.lock`. Named volumes, networks and images stay: they are
    caches.

  A subagent runs Docker only under your lock. Take the lock and run the container check
  before dispatching it, and end the session after its report. Its brief carries the
  repository's Docker lines and, in place of this rule, the **subagent Docker lines**: "The
  orchestrator holds the Docker lock and ends the Docker session. Never create or remove
  `~/.cache/docker-tests.lock`, and never stop or remove a container. Never run a suite that
  replaces or reuses `<names the ledger says he keeps, or: none>`. Run the gate, a fixtures
  recipe and every suite with `run_in_background`, and wait for its exit." With several Docker-running dispatches in flight, end the session only after the last of
  them reports. Two dispatches whose Docker runs share a volume or a container name never
  run in parallel.

### 1. Read the tickets

Fetch each ticket with the Atlassian MCP's `getJiraIssue`, view `evidence`: summary,
description, comments, subtasks, links, issue type and sprint. The server's name changes
between sessions, so find the tool by searching for `getJiraIssue`. Fetch every subtask in
full too, and the parent's description when there is one: decisions often live only there.

Check that each ticket is on the RDNX board:
`executeRead getJiraBoardIssueData` with `boardId: 22713`, `dataset: "all"`,
`jql: "key = <KEY>"` must return it. A NIFS ticket that is not on the board belongs to
another team: stop and ask him.

Record each ticket's issue type. It sets the branch prefix and the post-merge status (see
*Ticket status*):

| Issue type | Meaning (the architect's rule) | Branch prefix |
|---|---|---|
| Enabler | development that needs no testing | `feat/` |
| Story | development that is tested afterwards | `feat/` |
| Bug | a defect | `fix/` |

Most rdnx tickets are Enablers or Bugs; NIFS-13632 (the CI pipeline) is a Story. A
`Sub-task` takes its parent's branch prefix. Its post-merge status is Done, by the Enabler
route, whatever its parent's type: the Sub-task workflow offers no In Testing Dev. Any other
type: ask him which prefix and post-merge status it takes. When the tickets in scope differ in type, ask which prefix the shared
branch takes.

Settle the repositories and the base branch. The base is the one he names. When he names
none, the base is `main`. `git -C <repo> ls-remote --heads origin <base>` must print the
branch. Also run `git -C <repo> ls-remote --heads origin '*<KEY>*'`: a teammate may already
have pushed a branch for this ticket (NIFS-13631 has
`feature/NIFS-13631-setup-claude-structure`).

Then ask, in **one** message, everything that applies:
- `/add-dir <path>` for `~/.cache/roche-ticket-delivery` and each repository in scope that is
  not among the session's working directories. A session opened inside one repository sees
  only that one. `/add-dir` refuses a path that does not exist, so run
  `mkdir -p ~/.cache/roche-ticket-delivery/<KEY>` before you ask.
- which subtasks this work covers, when he handed over only the parent: subtasks can belong
  to another team
- the base, when he named none and `main` disagrees with him or with the ticket
- whether to continue on an existing remote branch for the key, or cut a new one
- the model and effort for gatherers, the planner, investigators, the stage 8 docs writer
  and the final-gate agent
- the branch prefix and post-merge status, for any type the table above does not cover or
  when the tickets in scope differ in type, and the post-merge status for a Bug

The tickets in scope are the ones he handed over plus the subtasks he confirms. Write
`ticket.md` (verbatim) and `ledger.md`.

Then cut the work branch in each repository yourself, before any gatherer reads the code.
**Always pull first.** Never branch from the local base without pulling, and never from
`origin/<base>` after a fetch. Run these literally:

```
git -C <repo> status --short     # must be empty: his uncommitted work is not yours to move
git -C <repo> checkout main
git -C <repo> pull --ff-only
git -C <repo> rev-list --left-right --count main...origin/main   # 0 and 0, tab-separated
git -C <repo> checkout -b <prefix><KEY>-<short-slug> main
```

When the base is another branch, it replaces `main` in every line. When the base has no local
branch yet, replace the checkout line with `git -C <repo> fetch origin <base>` and
`git -C <repo> checkout --track origin/<base>`, then go on from the pull. When he chose to
continue on an existing remote branch, check it out with `--track` and pull it, instead of
the `checkout -b`. Use the same branch name in every repository.

Once the work branch is cut in every repository in scope, move every ticket in scope to
**In Progress** (see *Ticket status*). While a repository stops on its status or its pull,
the tickets stay where they are.

When the status is not empty, the pull refuses to fast-forward, or `rev-list` prints
anything but `0` and `0`, stop and tell him. Never
stash, reset or merge to get past it. Then make sure the repository ignores
`.claude/worktrees/`, where every worktree of the run lives: when
`git -C <repo> check-ignore -q .claude/worktrees/x` fails, add `.claude/worktrees/` to
`<repo>/.git/info/exclude`, never to `.gitignore`. A repository that stage 2 adds to the
scope gets the same sequence then.

### 2. Gather context

Dispatch gatherers in parallel, one per repository or open question: general-purpose agents,
briefed read-only on the repositories, each writing only its own `context-NN-<topic>.md`.
Give each an **exhaustive** mandate: every reference to the code in play, including docs
(`docs/rfds`, `docs/adrs`, `docs/engineering-notes`, `docs/gaps`), packaging, Docker, the
`just` recipes, the test suites and CI, with `file:line` for each claim. `docs/rfds/0001-*.md` is about 400 KB, and `architecture.md`,
`layout.md` and `operations.md` are 50-60 KB each: search them for the symbols in play and
read only the matching sections, never whole. Pages in the `nIfS`
space count as context when the ticket links them; read them with `getConfluenceContent`.

Check the ticket's premise too: the bug reproduces, the behaviour the ticket assumes exists,
the libdnf5 call does what the ticket thinks. A reproduction goes to an issue investigator:
one per repository, never beside another writer in that checkout, told to change no git
state and to leave `git status --short` exactly as it found it. It runs Docker only under
your lock.

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
and the brief essentials. Tell it to load **superpowers:writing-plans** with four overrides:
- the plan goes to `<run>/plan.md` and nowhere in a repository
- its header names no execution skill, because this skill's workers execute it
- no task has a commit step, because the tree stays dirty
- it returns when the file is written, without offering execution options

The plan holds:
- **real code**, never a description of code: placeholders are where implementors invent
- exact files, and the exact gate command for each task
- tasks that each end on a green gate
- the verified facts the plan rests on, each with `file:line`
- for a ticket spanning repositories, their merge order and why
- open questions for him

Read it against the locked scope before review, and copy any merge order into `ledger.md`.

### 5. Plan review

At most two rounds: round 1 reviews the whole plan, round 2 checks only what round 1's
triage changed. A reviewer re-reads the whole plan at every step it takes, so a full round
costs millions of tokens, and a second full round costs more than the first because the plan
has grown.

**Round 1** is one reviewer per stack the plan touches, plus one lens per area it touches,
all dispatched in one message. Each is a general-purpose agent carrying a prompt from
`~/src/agent-skills/prompts/plan-review/` verbatim. Fill its `<X> =` line with
`<run>/plan.md` and its `<Y> =` line with `<run>/plan-review-r1-<lens>.md`, and add one line
after them: `Locked scope: <run>/options.md`.

- a reviewer per stack: `single-language/plan-review-rust.md` for Rust;
  `generic/plan-review-loss-framing.md` for anything else (Dockerfiles, `just` recipes,
  shell test harnesses, CI)
- a lens from `lenses/`: operational readiness for a socket, a service unit, config, CI or
  a deployment artefact; security for authorization, privilege, repository signatures or
  exposed data; tests and migrations for a change to on-disk state or a wire format

The `subagents/` pipeline runs only when he asks for it: it costs too much for a routine
round.

Then triage every finding. First copy the plan the round reviewed to `<run>/plan.rN.md`.
Take a reviewer's **diagnosis** without necessarily taking its **fix**: a correct problem
whose prescribed fix leaves a task ending red gets a different fix. Revise `plan.md`, and
append to it a **Review history** section: each finding, its verdict, and what you changed
or why you did not. That section is how round 2 avoids raising anything twice.

A round 1 with no Blocking or Important finding ends the review. Otherwise run **round 2**:
only the reviewers and lenses whose round 1 file holds a Blocking or Important finding, all
in one message. Each gets the same prompt, `<Y> =` `<run>/plan-review-r2-<lens>.md`, the
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

Triage round 2 the same way, then stop. What round 2's triage changed is not reviewed again,
so it goes to him at stage 6 as changed after the last review
(`diff -u <run>/plan.r2.md <run>/plan.md` shows it). What is still open goes to him as open,
never as passed. A third round runs only when he asks for it.

### 6. Implementation — gate

Show him:
- the cycle cut: which plan tasks form each cycle, the files each touches, its gate command
- what the review changed, marking what changed after the last round
- anything still open, and the open questions

Then ask with `AskUserQuestion` where the implementation runs:

- **Main worktree**: **parallel-worktrees-general** Mode D. The workers edit the
  repository's own checkout, on the work branch, one writer at a time.
- **Separate worktree**: Mode B. The workers edit a linked worktree; after the code review
  the change is merged back into the main worktree.

His answer confirms the cycle cut and is the go-ahead; record it in `ledger.md`. For the
separate worktree, follow `references/separate-worktree.md` beside this file.

Then run **change-cycle-pipeline** with the cycles he just saw: one brief per cycle. Use the
implementor that the repository's section of `references/repository-traps.md` names, in its
`-no-commit` form, or a general-purpose agent briefed "do not commit" in those words.
Independent repositories can run in parallel; inside one repository, one writer at a time.
The gate runs in Docker, so each worker runs it under your lock. Each implementor's brief
also says: "Do not load reconcile-docs: stage 8 reconciles docs over the whole diff. Edit a
doc only when the plan task names it."

### 7. Code review

Run **change-cycle-pipeline**'s narrow loop, cap 3. Each lens carries its prompt verbatim with
`<X> =` `<run>/plan.md`, `<Y> =` `<run>/code-review-rN-<lens>.md` and `<Z> =` the base. Never
leave `<Z>` empty: it would diff against a guessed default branch. Lens prompts are under
`~/src/agent-skills/prompts/code-implementation-review/`; the `/home/cristi/...` path in
change-cycle-pipeline is another machine's. Use `single-language/implementation-review-rust.md`
for Rust, `generic/implementation-review-loss-framing.md` for anything else, or one of
`lenses/` chosen for what the change risks. Add after the `<Z> =` line: "The change is in
<checkout holding the change>: run every git command as `git -C <that path>`, and read
files there."

The workers never stage, so a diff against the base leaves out every new file. Every lens
and checker brief carries: "The change set also includes every untracked file that
`git -C <checkout> ls-files --others --exclude-standard` lists: review each as a file this
change adds."

When a change adds or edits Rust, dispatch `rust-structure-and-style-guard` beside the lens in
every round: the runtime lens cannot see structure and test-layout violations. The guard
works out its own diff, so its brief carries these lines: "Run every git command as
`git -C <checkout holding the change>`. In Step 1, use `<base>` in place of the
`git symbolic-ref` expression; never guess the default branch. The change set is the union
of Step 1's three lists, not the staged set." The guard has no Write tool: save its final
message verbatim to `<run>/code-review-rN-guard.md` yourself as soon as it returns, before
triage.

The round's gate result is the last writer's gate transcript, or a gate you run under the
lock. No lens or guard builds or tests anything: the host has no libdnf5, and the Docker
gate needs the lock. Add to every lens and guard brief: "Never run cargo, just or docker:
the gate result for this tree is <path>. A claim that only a build or a test could prove
goes under Open Questions with the exact command. Do not dispatch subagents; review the
whole set yourself."

**One checker per finding, on `haiku`.** This is the pipeline's verify step with the brief
below in place of its own. Its other rules still hold: merge duplicates first, and drop what
an earlier round refuted. A checker holding several findings lets one verdict colour the
next, while on `haiku` reading the same diff once per finding stays cheap, even at `max`
effort. Dispatch one general-purpose checker per merged finding, every severity, all in one
message, each with model `haiku` and effort `max`. Each gets these lines, with the paths
filled and `<out>` its own `<run>/code-review-rN-verdict-K.md` (K numbers the round's
checkers), then its finding pasted in full with its citations and plan location:

```
You are a skeptic. Below is a claimed problem with the implementation of plan
<run>/plan.md in <checkout holding the change>, diffed against <base>. Run every git command
as `git -C <checkout holding the change>`. Try to REFUTE it against the actual code,
the plan text and the neighbouring tests: does the cited code say what the finding claims,
and does the problem actually follow? Other checkers are working in this tree at the same
time. Never run cargo, just or docker: every build and test here runs in a shared Docker
volume. Use only scoped read-only commands (git diff, git show, grep, reading files); never
modify a file. CONFIRMED needs a concrete wrong behaviour, a material contractual omission,
a test that cannot catch the defect it claims to cover, or an operational gap the plan
asked for. Style preference and hardening the plan never asked for are REFUTED, and so is
anything you cannot verify. Write to <out>: the finding's title, the verdict, then at most
three sentences of evidence with file:line citations.
```

A finding from `rust-structure-and-style-guard`, or one that names a rule rather than a
behaviour (rust-code-style Rule N, rust-project-structure Principle N, rust-testing Section
N, a structural SRP violation), gets these lines instead of the ones above. The brief above
would refute it as style preference:

```
You are a skeptic. Below is a claimed rule violation in the change in <checkout holding the
change>, diffed against <base>. Run every git command as
`git -C <checkout holding the change>`. Try to REFUTE it: open the named rule in
~/src/agent-skills/software-engineering/<skill>/SKILL.md and the repository's
docs/layout.md. CONFIRMED needs the cited lines to be added or moved by this change, and to
break the rule as its text states it, with no sanction in docs/layout.md or a
conventions-crate ledger. REFUTED when the rule does not say that, the lines are not in the
change, or the repository documents the exception. Never run cargo, just or docker; never
modify a file. Write to <out>: the finding's title, the verdict, then at most three
sentences of evidence with file:line citations.
```

A finding whose fix touches a public API, the gRPC proto (`package_management.v1`), on-disk
state or a wire format gets the pipeline's three-checker panel, majority wins: three
checkers instead of one, in the same message, each with the brief that fits it, its own
`<out>` and that finding.

A red gate is the pipeline's "send a fixer" step, with an investigator first: an issue
investigator of the matching stack, briefed with the failing test id and the command that
reproduces it, never your hunch. It runs alone in that tree, under your Docker lock, and
leaves `git status --short` as it found it. Then the fixer, carrying the investigator's root
cause.

With a separate worktree, merge it back when the loop ends, converged or capped, as
`references/separate-worktree.md` describes, before the report. When its status check of the
main checkout fails (another branch, or any dirty path), ask him first: he may keep the
worktree without a merge-back, recorded in `ledger.md`. When he keeps it and the work branch
is not checked out in the main checkout, run `git -C <worktree> switch <branch>` and
`git -C <worktree> branch -d <KEY>-wt`: both
branches point at the same commit, so the dirty tree carries over. Record it in
`ledger.md`. From then on the worktree is on the work branch, and stages 9-11 use it. When
the work branch is checked out in the main checkout, stop and ask him.

### 8. Report — gate

First dispatch a writer in the checkout holding the change: Mode D in the main worktree, or
Mode B in a linked worktree he kept without a merge-back. Tell it to load **reconcile-docs**
over the whole diff against the base, named explicitly, so it never runs
`git remote set-head`. Brief it with the repository's *Docs* lines from
`references/repository-traps.md`. **change-cycle-pipeline** runs this step after his
acceptance. Here it runs before his review, so every doc edit is in the tree he reads and
nothing is edited after his word at stage 9.

Then give him **change-cycle-pipeline**'s operator report, every finding in plain words with
its exact `file:line`. Its next action is his review, so it ends with this block for each
repository the change touches:

```
Review <repository name> in <absolute path of the checkout holding the change>
  <main worktree | linked worktree>, branch <branch>, against <base>
  <git -C <that path> status --short --untracked-files=all, verbatim>
```

Run that status in the path you name. Its paths must be the files this report lists as
changed: that proves the path holds this ticket's change, and it lists each new file a
diffstat omits. The tree stays dirty. Then stop.

### 9. Refactor or commit — gate

Refactors he asks for go to a fixer or implementor in the checkout holding the change, in the
same mode as stage 8's writer, followed by the gate and a fresh stage 8 report.

Commit only when he says so, and only in the repositories he names. When another repository
looks ready too, say so in one line and wait. Make one commit per repository unless he says
otherwise. The subject is the ticket key, a space, then a subject in the repository's own
shape (`git -C <repo> log --format=%s -20` shows it): `NIFS-13632 Add the CI pipeline`. With
subtasks, the key is the subtasks' keys. The body says why. It ends with the
`Co-Authored-By:` trailer line that the session's attribution reminder gives, exactly as
given.

Before committing, `git -C <repo> status --short --untracked-files=all` must show only the
change's files: nothing from an agent's scratch.

"Commit and push <repo>" is his approval for both stages 9 and 10 in that repository. Show the
exact push command as you run it, and do not ask again. Creating the MR is part of stage 10
and needs no further word.

### 10. Push and the merge request

Push only on his word, only what he named: `git -C <repo> push -u origin <branch>`. Then write
the MR, per repository: the description alone in `<run>/mr-<repo>.md`, and in `<run>/mr.md`
its title, the description, and, once created, its URL.

- **title:** the commit subject
- **description:** dev to dev, in plain words: what changed and why, how it was tested, the
  risk, and the ticket link (`https://navify.atlassian.net/browse/<KEY>`). When the ledger
  records a merge order, state it and why, in the same words in every MR of the ticket. It
  ends with the attribution line the session's reminder gives for pull request descriptions.
- **the merge request:** create it yourself, targeting the base explicitly:
  `glab mr create -R <group>/<repo> --source-branch <branch> --target-branch <base> --title "<title>" --description "$(cat <run>/mr-<repo>.md)" --yes`.
  Read it back with `glab mr view <branch> -R <group>/<repo> -F json`: `target_branch` must
  be `<base>` and `state` must be `opened`. Hand him its `web_url`. When creation errors,
  check with `glab mr list -R <group>/<repo> --source-branch <branch>` before retrying: an
  error does not prove no MR was created. When an MR already exists for the branch (a
  follow-up push), do not create another: hand over its `web_url`. Only when creation still
  fails, hand him the form link
  `https://code.roche.com/<group>/<repo>/-/merge_requests/new?merge_request%5Bsource_branch%5D=<branch>&merge_request%5Btarget_branch%5D=<base>`
  and say why.

`<group>/<repo>` comes from `git -C <repo> remote get-url origin`. Hand him the MR URLs, with
any order first. A ticket moves to **In Code Review** once every repository it covers has an
open MR. Record each URL in `ledger.md` and `mr.md`. Until then the ticket stays In Progress,
and the report names the repository still without one.

When the repository has a `.gitlab-ci.yml` on the pushed branch, arm one Monitor per pipeline
the push started, each reporting jobs as they finish, and send an investigator on the first
blocking failure. The ids come from
`glab api "projects/<project path with every / as %2F>/pipelines?sha=<pushed sha>"` (rdnx:
`projects/remix%2Fnifs%2Frdnx/...`, or its numeric id `605898`), repeated every 15 seconds
until the list is not empty. After two minutes, tell him no pipeline started. Without a
`.gitlab-ci.yml`, say in one line that the repository has no CI, and arm nothing.

### 11. Merged — post-merge status

When he says a repository's MR merged, or `glab mr view <branch> -R <group>/<repo> -F json`
shows `state: merged`, mark that repository merged in `ledger.md`.

Once every repository a ticket covers is merged, move the ticket to its post-merge status
from `ledger.md` without asking, subtasks before their parent (see *Ticket status*). Comment
on each ticket, in Markdown (`contentFormat: "markdown"`), with:
- per repository, the commit that landed and its `target_branch`. Read the `squash` field of
  that `glab mr view` output every time, because squash is chosen per MR: when it is true,
  the commit is `squash_commit_sha`, else `merge_commit_sha`
- the acceptance criteria, as a checklist

Fetch nothing into his checkout for this. Comment on tickets; never edit a description he
did not ask you to edit.

Then clean up each repository once its MR is merged, without asking. Touch only what the
ledger records for this ticket: its work branch, and its linked worktree when one survived
(no merge-back, or a resumed run). Everything else in the repository belongs to someone else,
however stale it looks: another ticket's worktree, a review checkout, an entry git marks
`prunable`. So never run `git worktree prune`.

First prove nothing is lost:
- the local branch tip must equal the `sha` field of
  `glab mr view <branch> -R <group>/<repo> -F json`, the commit GitLab merged
- `git -C <path> status --short` must be empty in every checkout on that branch
- for a linked worktree, list what still runs inside it, such as his terminal, his editor's
  language server or a container: `lsof -d cwd 2>/dev/null | grep -F "<worktree>"` and
  `docker ps --no-trunc --format '{{.Names}} {{.Mounts}}' | grep -F "<worktree>"`

When a check fails or a process shows up, stop and tell him what you found: never remove a
tree from under his tools. Then, in this order:

- a linked worktree: `git -C <repo> worktree remove .claude/worktrees/<KEY>`, then
  `docker volume rm rdnx-target-<KEY>` when the worktree had its own target volume
- a main checkout still on the work branch (the main-worktree choice, or after a
  merge-back): `git -C <repo> checkout <base>`, then `git -C <repo> pull --ff-only`. A main
  checkout on any other branch is someone else's work: leave it.
- the branch: `git -C <repo> branch -D <branch>`. Use `-D`, because git never sees a
  squash-merged branch as merged; the `sha` check above is what makes it safe.

The remote branch is GitLab's to delete on merge: delete it only on his word. Keep the run
directory, it is the record. Then write `complete` in `ledger.md`.

## Resuming

List `~/.cache/roche-ticket-delivery/*/ledger.md`. Open the run whose directory or ticket list
carries the key he names, else the only one not marked `complete`, else ask him. Before
acting, re-verify:
- `git -C <checkout> status --short --branch --untracked-files=all` matches the ledger's
  branch and dirty files.
  `<checkout>` is the linked worktree whenever the ledger records one not yet removed, else
  `<repo>`. The dirty files to match are the ledger's last recorded status of that checkout
- each ticket's status in Jira matches the ledger
- every repository in the ledger is among this session's working directories

When something differs, stop and tell him before any dispatch or transition. Stage 11 is the
exception: the status move needs only `glab` and Jira, and the cleanup runs its own checks,
so skip the branch and working-directory checks there. Then continue from the stage the
ledger names. In stage 5 or 7, a round the ledger does not record as triaged is untriaged.
Compare its files with the set the ledger names. Re-dispatch only the reviewers, or the
checkers by their recorded number, whose file is missing, in one message, then triage the
round. Never re-run one whose file
exists.

## Ticket status

| When | Move to |
|---|---|
| Stage 1, once the work branch is cut in every repository in scope | In Progress |
| Stage 10, every repository the ticket covers has an open MR | In Code Review |
| Stage 11, every one of those MRs is merged | the post-merge status in `ledger.md` |

| Issue type | Post-merge status |
|---|---|
| Enabler | Done. From In Code Review the workflow offers no Done, and neither does In Testing Dev or In Testing: only In Progress does. So the route is In Code Review → In Progress → Done, listing the transitions at each step |
| Story | In Testing Dev. Testers take it from there; never move it further |
| Sub-task | Done, by the Enabler route, whatever its parent's type |
| Bug, or any other type | his answer at stage 1 |

Never reuse a transition id. For each issue, call `executeRead listJiraIssueTransitions`
**at its current status**, match the target status by the transition's `to.name`, and pass
that id to `transitionJiraIssue`. A wrong id succeeds into a plausible wrong state. The
transition names do not always match their target (from To Do, the transition to To Do is
named `To Do (2)`). When the target is not among the transitions, say which ones are
offered and ask him: never chain intermediate moves on your own. The Enabler route in the
table above is a sanctioned chain, and so is Backlog → To Do (transition `To Do (2)`) → In
Progress at stage 1. A ticket already at the target status is left as it is. Read the status
back after every move.

- When a transition is refused for a required field, set the field with `editJiraIssue`
  only when the ticket or the board gives its value. Otherwise ask him.
- A parent moves to In Code Review or past it only once every one of its subtasks, including
  any outside this run, is at that status or past it. Until then it stays In Progress, and
  the report names the subtask holding it. For a parent Story, a subtask at Done counts as
  past In Testing Dev.
- Every Jira body (comment, description edit) is GitHub-flavoured Markdown with
  `contentFormat: "markdown"`, never wiki markup.

## Brief essentials

Every dispatch that touches a repository carries:

- the absolute repository root (`~/Projects` itself is not a repository), the checkout the
  dispatch works in (`<repo>`, or the linked worktree under Mode B), and
  `git -C <that checkout>` for every git command
- absolute paths for the files to open
- scope, out of scope, and the locked scope from stage 3
- the run directory or scratchpad for its working files, and the repository files it may
  create or change (only its deliverables)
- for a dispatch that edits files (implementor, fixer, investigator): the dispatch-mode
  block from **parallel-worktrees-general** (Mode D or Mode B). For any other dispatch:
  "read-only on `<repo>`". The final-gate agent's brief adds: "The recipes you run may
  write their git-ignored outputs (`evidence/`, the generated fixtures and test
  repositories). Change no other file."
- this git rule: "git is read-only for you except the files you edit: no commit, stash,
  fetch, pull, checkout or reset (a fetch here can move HEAD), no EnterWorktree, no
  `git clone`. Before checking another revision, look at the brief's Out of scope: a
  failure it lists already fails without your change, so report it and do not re-check it
  at `HEAD`. Prove a new test can fail by running it before you write the implementation,
  not at `HEAD`. When you still need another revision on disk (a bisect, a failure the
  brief does not list), add a temporary
  worktree with `git -C <repo> worktree add --detach .claude/worktrees/<name> <rev>` and
  remove it with `git -C <repo> worktree remove` before you report. In rdnx, a temporary
  worktree has no generated fixtures: before running the gate there, run
  `DOCKER_DEFAULT_PLATFORM=linux/amd64 just test-adapter-fixtures` in it, and give it its own target volume
  `rdnx-target-<KEY>-<name>`, removed with `docker volume rm` together with the worktree. A
  test that fails there only for lack of fixtures proves nothing about `HEAD`. This
  temporary `--detach` worktree is the one exception to the dispatch block's 'Do not create
  or enter a worktree' and 'other worktrees are off-limits': create it only for a check at
  another revision, never edit in it, and remove it before you report."
- the `model` and `effort` from *Models*
- that repository's section of `references/repository-traps.md` beside this file: its gate,
  its traps, its docs rules and its agents. When the brief may run Docker, also the
  subagent Docker lines under *Working rules*
- for a dispatch that is not briefed to run Docker (gatherers, the planner, plan reviewers,
  lenses, guards, checkers, the stage 8 writer): "Never run cargo, just or docker: they
  share Docker state with other sessions."
