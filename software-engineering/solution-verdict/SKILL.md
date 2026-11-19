---
name: solution-verdict
description: "Use when the operator wants one independent grade on whether a change's approach as a whole is a good way to solve its problem — /solution-verdict [model], \"grade this solution\", \"is this the right approach\", \"second opinion on how this was solved\", \"verdict on this branch\" — on a ticket this session delivered, a branch, an MR, a commit range or an uncommitted tree. NOT for hunting defects line by line (roche-mr-review, code-review), for choosing an approach before work starts (technical-solution-advisor), or for catching the operator up on a change (change-briefing)."
argument-hint: "[model] [effort]"
---

# Solution verdict

One subagent judges the approach a change takes, not its lines: is it a good way to do what
was asked, or does a clearly better route exist? It files no findings. It returns a grade
from 1 to 5 and at most five optional improvements. The same lens runs inside
roche-mr-review as lens 10; this skill runs it alone, on any change, on the model the
operator names.

## 1. The argument

`/solution-verdict [model] [effort]`. The argument picks the subagent, not the change.

| Argument | Subagent |
|---|---|
| none | `opus` at `medium` |
| `<model>` | that model at `medium` |
| `<model> <effort>` | that model at that effort |

`<model>` is one of `opus`, `sonnet`, `haiku`, `fable`; `<effort>` one of `low`, `medium`,
`high`, `xhigh`, `max`. Anything else: ask one question. Pass both explicitly on the
dispatch. A model named here wins over the global defaults, because the operator named it.

## 2. Find the change

The target is the ticket this session is delivering, else the current repository's branch
and uncommitted tree. The operator can name another in the same message (a ticket key,
branch, MR or commit range): follow that.

Resolve checkout, head, base and change set exactly as **change-briefing**'s section 1,
*Find the change*, does; read that section from the change-briefing skill and stop there.
Its read-only rule holds here too. When no change resolves, or the change set is empty, ask
one question: which change.

Then collect the problem's sources, from change-briefing's section 2 table: the ticket, the
MR description, the delivery run's `options.md` and `ledger.md`, and this session's
conversation. Write what they say the problem is into `{PROBLEM}`, as the operator's words
where the conversation has them. A change with no written problem gets `{PROBLEM}` from the
commit messages and the diff, marked `(inferred)`.

## 3. Dispatch

Fill `references/verdict-brief.md` and dispatch it as one `general-purpose` agent with the
model and effort from section 1. Never edit, stage or commit from this skill or its agent.

| Placeholder | Value |
|---|---|
| `{REPO}` | the repository's directory name |
| `{CHECKOUT}`, `{HEAD}`, `{BASE}` | from section 2; `{HEAD}` is `the working tree` when it is the head |
| `{DIFF_CMD}` | `git -C {CHECKOUT} diff <range>` (`<range>` as change-briefing defines it), plus the untracked files for a working tree |
| `{STRUCTURE_DOC}` | the repository's structure document (`CLAUDE.md`, `AGENTS.md`, `docs/architecture*`), else `CLAUDE.md` |
| `{PROBLEM}` | from section 2 |
| `{SOURCES}` | the absolute paths of the files section 2 found, one per line, else `none` |
| `{OUT}` | `solution-verdict-<KEY, else the branch with each / as ->.md`, in the run folder when the change has one, else the session scratchpad; absolute |

## 4. Show it

When the agent finishes, read `{OUT}` and print it verbatim, then one line: the model and
effort that wrote it and the change it judged (`<repo> <branch or !iid> vs <base sha7>`).
Add nothing, and do not soften or re-grade it.

When the agent dies or `{OUT}` is missing, dispatch it once more, then say it is missing and
stop. A grade the operator disagrees with is theirs to push back on: answer the question,
and rerun with another model only when they ask.

Acting on the improvements belongs to the workflow that owns the change, not to this skill.
