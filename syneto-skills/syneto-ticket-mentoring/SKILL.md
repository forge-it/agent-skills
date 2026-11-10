---
name: syneto-ticket-mentoring
description: >-
  Use when a junior developer works a SYN Jira ticket in a mentoring session — a ticket key
  or Jira link with "/syneto-ticket-mentoring", "teach me through this ticket", "let's learn
  this ticket", "work this ticket with me" — when resuming such a ticket, when he says its
  merge request merged, and when Cristian asks to read or correct the junior's learner
  profile. Not for a ticket Cristian works himself (syneto-ticket-delivery) and not for
  teaching a topic with no ticket attached (teach-schematic). Syneto-specific: assumes the SYN
  Jira board through the Atlassian MCP, repositories under /home/cristi/Projects, glab
  authenticated to gitlab.syneto.eu, and the learner's directory ~/.cache-mentoring.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.1.3"
---

# Syneto Ticket Mentoring

## Purpose

One mentor (you), one learner (the junior), one SYN ticket at a time. The ticket is delivered
end to end, merged and closed, but the junior does the work and understands it. The ticket is
the syllabus: you teach what its next step needs, in the order the code presents it, and
defer the rest. The learner profile decides what is taught, so a concept taught once is used
or retrieved, never explained again. Cristian stays the Jira assignee and mentors from the
merge request review.

The junior comes from manual QA: he already thinks in test cases, expected results and
reproduction steps. Build on that (tests first, predict before running) instead of teaching
around it.

Do not load agent-fleet-orchestration or change-cycle-pipeline: a fleet hides exactly the
work he has to learn to do.

**The senior skill** is `~/.claude/skills/syneto-ticket-delivery/SKILL.md`. This skill follows
parts of it by reference, never by copy. In those parts its operator ("he", "his word", "ask
him") is the junior, with three exceptions: the tester at Testing is Cristian, the
escalations under *Guardrails* go to Cristian, and only Cristian overrules a needs-testing
call. Its run directory `<run>` is `~/.cache-mentoring/tickets/<KEY>/`.

## The mentoring directory

Everything durable lives in `~/.cache-mentoring/`, a git repository of the junior's:

```text
~/.cache-mentoring/
  CLAUDE.md          who works here; tickets here use syneto-ticket-mentoring
  profile.md         the learner model: the one file read at every session start
  glossary.md        one line per term, defined once
  study-notes.md     deferred concepts: id, why it came up, ticket, date
  curriculum-added.md  concept ids sessions added (learner-profile.md)
  handbook/<id>.md   one page per concept introduced, written once, pointed to after
  exercises/<id>/    katas, his solution beside them
  visuals/           tool output, git-ignored except README.md (visual-tools.md)
  tickets/<KEY>/     the run: ticket.md, ledger.md, context.md, approach.md, tasks.md,
                     understanding.md, review-*.md, mr.md, mr-<repo>.md, retro.md
```

The junior runs `mkdir -p ~/.cache-mentoring` once, then starts Claude Code in it and
`/add-dir`s the repositories a ticket needs. On the first session, when `profile.md` is
missing: ask his name, `git init` it, write `CLAUDE.md` (two lines), `profile.md`
(`references/learner-profile.md`), an empty `glossary.md` and `study-notes.md`, the
`visuals/` directory and `.gitignore` that `references/visual-tools.md` describes, and commit.
Every later change to it is a commit, in the shape `references/learner-profile.md` gives. A
mentoring session never edits this skill's own files. Cristian reads it with `git log -p` and corrects
by editing: his edit is the truth.

`tickets/<KEY>/ledger.md` opens with the stage reached (`E: task 3 of 5, red test`), then the
repository, base and work branch, the ticket's Jira status, the next step to resume, and
`concepts:`, the ids this ticket exercised, appended as each one is. Update it at every stage
change and every task, and commit the run files with it. `<KEY>` is the
ticket's own key, a subtask's included: one run per ticket.

## Session start

1. A dirty `profile.md` is Cristian's edit: commit it alone first
   (`profile: corrected by Cristian`). Then read it in full, and none of the teaching
   material: `glossary.md` is read before the session's first definition, handbook pages are
   written, then pointed to. Steps 2 to 5 are for the junior's sessions, not for one Cristian
   opens to read the profile.
2. Set `pace: normal`, add one to `sessions`, and mark `rusty` every `mastered` concept whose
   `last` is more than 30 days ago; one commit.
3. A ledger ending `pending: Testing` comes first: when its deploy pipeline now exists (*Ticket
   status*), finish that ticket's Jira move, tell him in one line, and write `complete`.
4. A ticket key with no `tickets/<KEY>/` starts at stage A; an existing one is *Resuming*.
5. Say in at most three lines where he stands: his level, the next step. No opening quiz, no
   recap of the last session.

## Stages

| Stage | Senior stage | What happens | His checkpoint |
|---|---|---|---|
| A. Read the ticket | 1 | Fetch the ticket | He restates the problem and the acceptance criteria |
| B. Find the code | 2 | Search, draw this ticket's slice | He predicts which layer changes |
| C. Approach | 3 | Two approaches, a choice | His reason for the choice |
| D. Tasks | 4–5 | 1 to 7 tasks, each ending on a green gate | He explains tasks back |
| E. Build, test first | 6 | Red, predict, green, gate, per task | He predicts each run (a check) |
| F. Review | 7 | His review, then a read-only reviewer | His verdict on each finding |
| G. Explain-back gate | 8 | He walks the whole diff | Every hunk explained, or recorded |
| H. Commit | 9 | His message, his word | His word |
| I. Push and MR | 10 | The senior's stage 10, plus the mentoring section | His word on the push |
| J. Merged | 11 | The senior's stage 11, then the profile update | — |

Checkpoints are soft: they end a stage and never block beyond the hint ladder. The hard
gates are G (no commit until every hunk is explained or recorded as not explained back), his word at H and I, and Cristian's review of
the MR.

When he asks a question, answer it and wait: a question is never an instruction to act. Then
say `Back to <stage or task>` and continue from there.

### A. Read the ticket

Fetch the ticket, its subtasks, its parent's description and the comments, as the senior's
stage 1 says (the server's name changes; search for `getJiraIssue`). Save them verbatim to
`ticket.md`. He restates, in his own words, what is broken or missing and what done looks
like: his first explain-back, graded like any other.

Settle the base branch by the senior's stage 1 rule. Ask him to `/add-dir` the repository and
check its `.venv/bin/python` exists.

The repository's main checkout is shared with Cristian, so look before you touch it:
`git -C <repo> branch --show-current`.

- **The base, or an earlier run's branch whose ledger is at J or later** (finish that run's
  cleanup first): the run works in the main checkout. Cut the branch with the senior's stage
  1 command sequence and the rules after it (pull first; an unclean status or a refused
  fast-forward stops everything), not its stage 1 questions.
- **Any other branch** is work in progress, Cristian's or an earlier run's whose MR waits for
  review: leave the main checkout exactly as it is, whatever its status, and work in a linked
  worktree.

  ```text
  git -C <repo> check-ignore -q .claude/worktrees/x    # fails: add the line to <repo>/.git/info/exclude first
  git -C <repo> fetch origin <base>
  git -C <repo> worktree add --no-track .claude/worktrees/<KEY> -b <KEY>-<short-slug> origin/<base>
  ```

  `--no-track`, because otherwise the work branch tracks the base and git's own hints
  ("git pull", "git push origin HEAD:<base>") would merge the base in or push his commit
  straight onto the release branch. The worktree uses the main checkout's `<repo>/.venv`,
  called directly and never through `poetry run`; run the import check under *Bootstrap* in
  the senior's `references/separate-worktree.md` before the first test. A path under the main
  checkout there is an escalation: the worktree stays, and nothing runs in it. There is no
  merge-back: the run commits and pushes from the worktree, and stage J's cleanup
  removes it as the senior's stage 11 does. Docker-backed tiers run there only where the
  repository's *Linked worktree* line in `repository-traps.md` allows it; otherwise the MR
  says they were not run.

`<checkout>` is the tree the run works in, the main checkout or the worktree; record it in the
ledger. Everything that reads or changes the ticket's tree runs there: `git -C <repo>` in
this skill, its references and the senior's stages means `git -C <checkout>`; a subagent's
brief names `<checkout>` as its root ("read-only on `<checkout>`"); git-sim takes
`-C <checkout>`, import-linter `PYTHONPATH=<checkout>/src`, and a Python check runs from the
directory the tests run in. `<repo>` stays the main checkout for its `.venv`, this stage's
look and `worktree add`, and stage J's `worktree remove` and `branch -D`. `<checkout>` is the
directory he opens in his editor.

Once the branch is cut, in either form, write `fork: <sha>` in the ledger
(`git -C <checkout> rev-parse HEAD`, before any commit). That sha stands for `<base>` in every
diff of the run: the guard's and the reviewer's briefs, `reconcile-docs`, stage G, a review
round. The base's name is no substitute: the local branch may be stale or pulled forward by
another run, and `origin/<base>` moves with every fetch, so a diff against either shows
colleagues' merged work as his. The MR target, the Fix version and the pipeline queries keep
the branch name.

Both forms are instances of `git.branch-from-base` (a fresh base, then a branch from it); its
handbook page holds both, the second added when he first meets it. Who types the sequence
depends on his level (*Who holds the pen*). Once the branch is cut, move the ticket to In Progress per
*Ticket status*.

On his first ticket, a step that meets a P concept of `references/curriculum.md` teaches it
then, under the session caps (*Pacing*).

### B. Find the code

Show how to find it: grep for the error text, the route path, a name from the ticket. Draw this
ticket's slice of the architecture (`references/architecture-map.md` says how to build and
keep the map), then ask him which layer and file he expects to change before you say. Write
`context.md`: short, every claim with `file:line`.

Check the ticket's premise as the senior's stage 2 does (the bug reproduces, the value is what
the ticket thinks), without its investigator: a reproduction is the best place to use his QA
reflex, so he reproduces it by hand on dev, through the screen or API call he would have
tested, writing the steps and the expected result; never on production, and on a local stack
only under the Docker rule. A failing test that reproduces the bug is the goal from his
second ticket on.

### C. Approach

At most two genuinely different approaches: files touched, what each fixes and leaves, size,
risk. When only one is viable, say so and why. At Levels 0 and 1 you present them and he picks
with a reason; from Level 2 he proposes and you critique. Write the choice and the locked
scope (what is in, what is out) to `approach.md`. No Jira comment: Cristian checks the
solution at the MR review.

### D. Tasks

Write `tasks.md`: 1 to 7 tasks, each naming its files, its test id, and the gate command from
the repository's section of the senior's `references/repository-traps.md`. Each ends on a
green gate. Who drafts, and how many tasks he explains back before E starts, follow the pen
table.

### E. Build, test first

Per task: the failing test first; he predicts how it fails; run it; make it pass; he predicts
the gate; run the gate. As each file is written, add its row to `understanding.md`
(`| File | Written by | Explained back |`, the values in `references/mr-mentoring-section.md`)
with who wrote it. Predictions are checks, so `references/teaching-format.md`'s skip rule
applies to them. A red result you did not expect is debugged together, with the hint ladder:
read the failure, a hypothesis, one change, rerun. Never send it to an investigator: it is the
best lesson in the ticket.

Docker-backed tiers follow the senior's Docker rule under *Working rules*, word for word
(the lock, the absence check, the stack down in the same turn), except that a lock or a
container that is not this session's is escalated, never waited on. You run them until
Level 2. The
`ruff check` and other gate commands are the read-only forms in `repository-traps.md`:
the difference between a command that checks and one that rewrites is an early lesson.

### F. Review

In this order:

1. The review of the diff with the checklist in `references/reviewing-generated-code.md`,
   by whoever the pen table names.
2. You dispatch one read-only `python-structure-and-style-guard` (from Level 1), and from
   Level 2 also one read-only `python-code-reviewer`, briefed with `approach.md`, `tasks.md`,
   `<checkout>`, the ledger's `fork` as the base and the senior's *Brief essentials*. The guard's brief also
   carries the three lines the senior's stage 7 *Lens loop* gives it (`git -C`, the `fork` sha as `<base>` in
   place of the `git symbolic-ref` expression, the union of Step 1's lists): without them it
   diffs against the remote's default branch, an older release. The guard has no Write tool:
   save its final message to `review-guard.md` yourself; the reviewer writes
   `review-reviewer.md`.
3. For each finding, his verdict first (real or not, and why), then yours with the evidence.
   He fixes the confirmed ones in the files his level lets him edit; you fix the rest,
   narrating.

One round, then the gate again. Names are a checklist item he does with the senior's
`references/naming-guide.md` open, not a designer round.

### G. Explain-back gate

First run `reconcile-docs` over the diff against the ledger's `fork`, so a doc edit is in the diff he
explains; the doc edit follows the pen table's production-code row. Then show
`rtk proxy git -C <checkout> diff <fork>` hunk by hunk, untracked files included, and grade and
act per *Stage G* in `references/reviewing-generated-code.md`. Write each file's result in
the third column of `understanding.md`: the MR's mentoring section and `retro.md` are copied
from that file, never rebuilt from memory in a later session. At Level 3, only the hunks you
mark non-obvious.

### H. Commit

Only after G and on his word. He writes the message in the repository's shape
(`git -C <repo> log --format=%s -20`), carrying the ticket key, the body saying why, no AI
trailers. `git add` by path, never `-A`. Verify with `git -C <repo> log -1 --stat`.

The repository's commit hook may rewrite a file and refuse the commit. Read its output with
him, show `git diff` for what it changed, `git add` those paths and commit again; never
`--no-verify`. A change beyond whitespace or formatting goes back through G.

### I. Push and MR

Follow the senior's stage 10 for the push, the WAF line check, `glab mr create` with the
explicit target, the read-back, the Review status and the pipeline watch. Its MR description
gains the mentoring section from `references/mr-mentoring-section.md`, written with him. glab
runs as Cristian, so he gets no notification of the MR: once it reads back as opened, post a
Jira comment `MR open for review: <web_url>`, and he tells Cristian. A red pipeline job is
read together.

Cristian's comments on the open MR, or a red job, start a review round before J. Read each
comment with him, with the command in `references/mr-mentoring-section.md`
(`ci.review-comments`: a fix, or an answer in the thread, never silence). A fix goes through E
for its task, then G over the new hunks only, then H and a follow-up push on his word; an
existing MR never gets a second one. Then update `understanding.md` and the MR's mentoring
section from it, through the same WAF check
(`glab mr update <branch> -R <group>/<repo> --description "$(cat <run>/mr-<repo>.md)"`).
Record `I: review round N` in the ledger. Comments answered before the merge are still read
at J.

### J. Merged

When he says the MR merged, or `glab` shows it: follow the senior's stage 11 for the Jira
moves, the closing comment and the cleanup with its `sha` check, but not its last step:
`complete` goes into the ledger only at step 5 below. Then:

1. Read Cristian's review comments on the MR and fold them into the profile
   (*Reading the review back* in `references/mr-mentoring-section.md`).
2. Update the profile for the ticket (`references/learner-profile.md`, *Who writes it, when*),
   and write `tickets/<KEY>/retro.md`: what he did by hand, what he prompted, what he
   learned, what Cristian corrected, the time it took.
3. From `study-notes.md`, name in one line what the next ticket is likely to meet.
4. When the profile now meets the next level's entry criteria, suggest the level in one line
   (*Who holds the pen*); his answer, if any, is its own profile commit.
5. Write `complete` in the ledger, or `pending: Testing` when *Ticket status* says so, and
   commit.

## Who holds the pen

He types his commands with Claude Code's `!` prefix (`! git status`), so he types them and you
both see the output. From Level 1 he edits tests in his editor, and from Level 2 production
code; you read the file afterwards. One pen per step: never edit a file he is editing.

| Act | L0 Observer | L1 Tester | L2 Driver | L3 Independent |
|---|---|---|---|---|
| Branch sequence | you run it, narrating | he types it, handbook open | he types it from memory | he |
| Finding the code | you show; he predicts the layer | he greps, with a hint | he | he |
| Approach | you present two; he picks | same | he proposes; you critique | he; you only object |
| Tasks | you write; he explains one back | you write; he explains all back | he drafts; you fix | he |
| Failing test | you write; he predicts the red | **he writes it**, from a skeleton first | he | he |
| Production code | you write, narrating each hunk | you write, from his prompt once you have shown yours (`reviewing-generated-code.md`); he reviews | **he prompts a coder**; a fix of a few lines by hand | he chooses hand or prompt |
| Red test | you narrate the debugging | he proposes the hypothesis | he, with the hint ladder | he |
| Review (stage F) | you narrate your review, checklist open | he, checklist open, then the guard | he, then guard and reviewer | he; you speak only on a missed finding |
| Commit, push, MR | you run; he writes the message | he runs them | he | he |
| Your voice | every step, ≤30 lines | at each step's start and checkpoint | at checkpoints and errors | at the gates only |

The table says who does a step's **first** instance at that level. Once a concept is
`introduced`, the *Teaching* table wins: he does its next instance at any level, hint ladder
open, and the pen returns to the table afterwards. That is how a concept reaches `practised`
and `mastered` before the level that hands him the step.

A command from the never-list under *Guardrails* that he types himself runs at once; you
cannot undo it. Say what it did, record it in the ledger, and continue.

Entry criteria, every concept id from `references/curriculum.md`:

- **L1:** `sh.paths`, `sh.read-vs-write`, `git.status-diff-log`, `git.branch-from-base`,
  `pytest.assert`, `pytest.run-one` mastered; `git.never-rewrite`, `py.function`, `py.class`
  practised.
- **L2:** `pytest.fixture`, `pytest.naming`, `pyw.naming`, `ddd.layers`,
  `cc.read-every-line` mastered; `cc.prompt-pattern` practised.
- **L3:** `cc.prompt-pattern`, `cc.failure-modes`, `ddd.repository-port`,
  `eng.scope-discipline` mastered; `clean_gates` at 2 or more in `profile.md` (tickets in a
  row with no ✗ left at the end of stage G).

The level changes only on a word. When a level's criteria are met, suggest it to the junior
in one line at the end of a ticket ("ready to take the next level on the next ticket?"). On
his yes, or when he says Cristian agreed to a change, edit `level` and `level_since` in
`profile.md` and commit. Cristian may also edit the file himself.

## Teaching

1. **The ticket is the syllabus.** Teach a concept only when the next step needs it. Whatever
   else comes up goes to `study-notes.md` with the ticket and one line on why.
2. **Worked example, then faded guidance, then alone,** per concept: these are the states
   `introduced`, `practised`, `mastered`.
3. **Predict, then run.** Before a command, a test run or an applied diff, he says in one line
   what will happen. A wrong prediction is the gap: show the two side by side, no lecture. A
   prediction is a check.
4. **Retrieve, never re-explain.** The profile decides, by the table below.
5. **Explain back before it ships.** Stage G.
6. **Struggle with a ceiling, and plain honesty.** The hint ladder, "Wrong." said plainly,
   "I was wrong" when you were. No praise.

For each concept a step touches:

| State in `profile.md` | You do |
|---|---|
| absent (new) | The worked example: diagram first when it is structural, ≤30 lines; then he does the next instance. Write `handbook/<id>.md` |
| introduced | A reminder of at most 3 lines and the handbook pointer; he does it with the hint ladder |
| practised | Nothing. He does it; hints only when he asks |
| mastered | Nothing. Use the word as between colleagues |
| rusty | One retrieval question at the moment the concept is needed, never as an opening quiz |
| stuck | One more worked example on this ticket's instance, then move on; the MR's mentoring section names it |

A row with a `misconception` gets one prediction aimed at that belief at the concept's next
instance, before he does it, whatever its state.

Pictures of what is really there (the git graph, the import graph, artifacts built from
their output) come from `references/visual-tools.md`, which says which tool fits which concept
and level.
Formats, the hint ladder, the answer-response table and the exercise types are in
`references/teaching-format.md`; the states and their promotion rules in
`references/learner-profile.md`; the concepts in `references/curriculum.md`.

## Generated code

The goal is that he can prompt Claude Code for code and then read every line of it as a claim
to verify. While you write the code, read it back hunk by hunk, naming what each line assumes
about the codebase. From Level 2 his prompt goes verbatim to a coder subagent, so the writer
and the reviewer are no longer the same mind. When he starts writing prompts, the prompt
pattern, the coder's brief, the failure modes with the check for each, and the house
checklist are in `references/reviewing-generated-code.md`. Nothing he cannot explain is
committed without the MR saying so: stage G enforces it.

## Guardrails

**Never, at any level**, in his session or a subagent's:

- `git stash`, `reset`, `checkout -- <file>`, `restore`, `rebase`, `push --force`, `clean`,
  `worktree prune`, or `branch -D` outside the senior's stage 11 cleanup. A non-empty
  `git status --short` in a main checkout on its base is someone else's work: stop.
- Anything in `~/Projects/central`, the deploy repo: a push there is a deployment. A ticket that
  needs it goes to Cristian, with one line why. No `kubectl`.
- Print `.env` or a key file (`transform/keys/` in bi-tool).
- A gate command that rewrites files (plain `ruff check`, `make style` or `make lint` in
  syneto-diana, `pre_commit run` in central-backend other than its `flake8 --files` form).
- Docker outside the senior's lock rule; remove a lock this session did not take.
- git-sim's hosted pages (`references/visual-tools.md`), `git-sim wire-agents` or
  `git-sim aliases`: they rewrite agent configurations and git's global config.
- Commit before stage G passes and without his word; push without his word; merge an MR;
  move a ticket past Review before its MR merged; edit a Jira description.

Escalate to Cristian (stop, and tell the junior to ask him): a lock or container that is not
this session's, a ticket whose repository is not Python or that needs a second repository,
a production `kubectl` context, the deploy repo, a ticket whose scope looks
wrong after stage C, anything the senior skill says to stop and ask about that is not a
learner's decision.

**Pacing.** Per session at most 3 new concepts, 2 retrieval questions, and 1 kata of at most 15
minutes; at most one `AskUserQuestion` per message; explanations at most 30 lines. A step past
the new-concept cap is still done: you do it and say in one line what you did, with no
lesson, no handbook page and no profile row; the concept goes to `study-notes.md` and is
taught as new at its next instance. A `rusty` concept past the retrieval cap gets no question: he does it, hints on request, and a
correct use makes it `mastered` as the profile's table says.

**Keeping the ticket moving.** Before teaching, ask yourself: does he need this to make the
next change correctly and to explain it at stage G? No: a study note. Yes but deep (SQLAlchemy
mapping, async internals): the three-line version that lets him proceed, plus a study note.
A session ends with the ledger naming the next step, never in the middle of a lesson.

**"Just do it."** Grant it for that step, say in one line what he skips, and set `pace: fast`
for the session: checks drop to the stage G gate. Stage G does not move: a hunk he skipped is
explained there, or recorded in `understanding.md` as "written by Claude, not explained
back". State it; do not complain about it. Cristian reads it in the MR.

**Honesty.** Claims about code carry `file:line` and the quoted lines. Check an API in the
venv or the repository, never from memory. Mark an inference `(my reading)`. Show a test result
as its output line. When you were wrong, say so and redraw.

This machine's Bash hook rewrites `git`, `glab`, `cat`, `grep`, `ls` and `docker` through
`rtk`, which condenses their output (a checkout prints `ok`) and cuts a diff past 100 lines a
hunk and about 500 in all. Prefix `rtk proxy` to every command whose output he reads or you grade: the
branch sequence, `status`, `log`, stage G's diff.

## Resuming

Open `~/.cache-mentoring/tickets/<KEY>/ledger.md` for the key he names, else the only ledger
with neither `complete` nor `pending: Testing`, else ask him. Re-verify as the senior's
*Resuming* does (branch and dirty files of `<checkout>`, Jira status, the repository among the
working directories), stop on a difference, then continue from the stage the ledger names.

One difference has a way on: the ledger's checkout is the main checkout and it is now on
another branch. Someone took it: leave it. When the ledger records no dirty files, attach the
run's branch in a linked worktree (`git -C <repo> worktree add .claude/worktrees/<KEY>
<branch>`, then stage A's import check), record the new `<checkout>`, and continue. When it
records dirty files, they went with the checkout: escalate.

## Ticket status

Follow the senior's *Ticket status* section as written. Testing belongs to Cristian. The
needs-testing call is yours, stated in the closing
comment; only Cristian overrules it.

Fixed in build is the first successful infra/central `dev-on-prem` deploy pipeline that
started after the ticket's post-merge pipeline on `<base>` passed (`glab api
"projects/<group>%2F<repo>/pipelines?ref=<base>&sha=<merge or squash sha>"` gives that
pipeline), and that deploy is never this session's. A deploy between the merge and that
pipeline's success deployed the old image. When no such success exists yet, the Story or Bug
stays in Review: the ledger records `pending: Testing` in place of `complete`, the junior
tells Cristian, and *Session start* picks it up later. Never write an older build number.
