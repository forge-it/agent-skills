---
name: solution-verdict
description: "Use when the operator wants one independent grade on whether a change's approach as a whole is a good way to solve its problem — /solution-verdict [model] [effort] [target], \"grade this solution\", \"is this the right approach\", \"second opinion on how this was solved\" — on a ticket this session delivered, a branch, an MR, a commit range or an uncommitted tree. NOT for hunting defects line by line (roche-mr-review, code-review) or choosing an approach before work starts (technical-solution-advisor)."
argument-hint: "[model] [effort] [target]"
---

# Solution verdict

One subagent judges the approach a change takes, not its lines: is it a good way to do what
was asked, or does a clearly better route exist? It files no findings. It returns a grade
from 1 to 5 and at most five optional improvements. The same lens runs inside
roche-mr-review as lens 10; this skill runs it alone, on any change, on the model the
operator names.

## 1. The argument

`/solution-verdict [model] [effort] [target]`. Read it left to right, case-insensitively:

1. Take the first word when it is a `<model>`: `opus`, `sonnet`, `haiku` or `fable`. A
   version number right after it (`5.5`) is dropped.
2. Take the next unread word when it is an `<effort>`: `low`, `medium`, `high`, `xhigh` or
   `max`. This holds with or without a model before it, so `high NIFS-1` is effort `high`
   on the default model, target `NIFS-1`.
3. Whatever remains is the target: a ticket key, branch, MR (`!n` or URL) or commit range.
   A branch named like a model or effort word is written as a full ref (`origin/max`).

| Left out | Value |
|---|---|
| the model | `opus`: the operator's standing choice for this lens (roche-mr-review's model table), which wins over the global reviewer default |
| the effort | `medium` |

Pass both explicitly on the dispatch. A model or effort named here wins over the global
defaults, because the operator named it.

## 2. Find the change

The target is the argument's, else the ticket this session is delivering, else the current
repository's branch and uncommitted tree.

Resolve checkout, head, base and change set exactly as **change-briefing**'s section 1,
*Find the change*, does: read that one section from the change-briefing skill, and carry
out its read-only rule. When no change resolves, or the change set is empty, ask one
question: which change.

Then gather the problem, from change-briefing's section 2 table: the ticket and the MR
description (`{SOURCES}`; write each one that is not already a file into the session
scratchpad), and from a delivery run's `ledger.md` the locked scope and acceptance
decisions. Leave `options.md` out: the agent weighs its own alternatives. `{PROBLEM}` is the
problem and the acceptance criteria, quoted or lightly cut, with those ledger decisions as
quoted lines. A problem the operator states in the invocation or in answer to the question
below is `{PROBLEM}` as they said it; an earlier conversation counts only when this session
delivered the change. When nothing states the problem, ask one question: what the change is
for. If the operator says to judge it by the diff alone, `{PROBLEM}` is the commit messages
and the diff read as a problem, ending `(inferred)`.

## 3. Dispatch

Fill `references/verdict-brief.md` and dispatch it as one `general-purpose` agent with the
model and effort from section 1. Never edit, stage or commit in the repository from this
skill or its agent; the only writes are scratchpad files and `{OUT}`. Delete `{OUT}` first
when it exists.

| Placeholder | Value |
|---|---|
| `{REPO}` | the repository's directory name |
| `{CHECKOUT}`, `{BASE}` | from section 2 |
| `{HEAD}` | `the working tree` when it is the head, else the head commit's sha |
| `{DIFF_CMD}` | a commit head: `git -C <checkout> diff <base> <head>`; a working tree: `git -C <checkout> diff <base>` (the real paths and shas, no backticks) |
| `{UNTRACKED_CMD}` | a working tree: `git -C <checkout> ls-files --others --exclude-standard`; a commit head: `none` |
| `{STRUCTURE_DOC}` | the repo-relative path of each of `CLAUDE.md`, `AGENTS.md` and the docs the root `CLAUDE.md` links as architecture or conventions, that exist at the head; else `none` |
| `{PROBLEM}` | from section 2 |
| `{SOURCES}` | the absolute paths of the files section 2 found or wrote, one per line; else `none` |
| `{OUT}` | absolute: `solution-verdict-<KEY, else the branch with each / as -, else the head's sha7>-<REPO>-<model>-<effort>.md`, in the ticket delivery's run folder when the change has one, else the session scratchpad |

## 4. Show it

When the agent finishes, read `{OUT}`. It counts only when its first line reads
`Solution verdict: <label> (grade <1 to 5>)` and an `Optional improvements:` line follows;
otherwise dispatch once more, then say it is missing and stop.

Print it verbatim, then one line: change-briefing's header line two for the change
(repo, branch or `!<iid> <source branch>`, base, change size, committed or uncommitted),
the head's sha7, and the model and effort that wrote the verdict. Add nothing else, and do
not soften or re-grade it.

A grade the operator disagrees with is theirs to push back on: answer the question, and
rerun on another model only when they ask. Acting on the improvements belongs to the
workflow that owns the change, not to this skill.
