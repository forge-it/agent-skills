# Prompting for code and reviewing it

The skill being taught: prompt Claude Code for code, then read every line as a claim to
verify. Each piece below is a concept in `curriculum.md`, so the profile tracks it.

## The prompt pattern (`cc.prompt-pattern`)

A prompt for code holds, in this order:

1. **Goal**, one sentence, in the ticket's terms.
2. **Files**: the exact paths to change, and the ones to read for context.
3. **The test that must pass**: its id, already written and red.
4. **Constraints**: the house skills by name (python-code-style, python-testing, python-ddd
   where the repository is DDD), the locked scope from `approach.md`.
5. **What not to touch**: other files, public signatures, the database schema unless the task
   is the schema.
6. **"Do not commit."**

At Level 1 you show your own prompt for his first task at that level; after that the
*Teaching* table decides, so he writes the prompt and you write the code from it, after naming at most one missing constraint. From
Level 2 his prompt goes to the coder subagent, with the same one-constraint rule: the rest he
learns from the review.

## The coder subagent (Level 2 and up)

His prompt goes verbatim, followed by these lines, to `python-implementor-expert-no-commit`
(or the implementor `repository-traps.md` names for the repository):

```text
You work in <checkout>, on branch <branch>; nobody else edits it while you work. Edit files
only under it. Run every git command as `git -C <checkout>`. Use <repo>/.venv/bin/python, the
main checkout's interpreter, from <checkout>. Git is
read-only for you except the files you edit: no commit, stash, fetch, pull, checkout or
reset. The gate is: <gate command from repository-traps.md>. Report the files you changed
and the gate's result line.
```

Add the rest of the senior's *Brief essentials* that apply, except the dispatch-mode block,
which the lines above replace. The diff comes back to him for
review, not to you: a writer that is not the reviewer is the point of this step.

## The failure modes and their checks (`cc.failure-modes`)

Each failure mode comes with the one check that catches it: a QA person reviews by checking.

| Failure mode | The check |
|---|---|
| Invented API or wrong signature | From the directory the tests run in, `<repo>/.venv/bin/python -c "import <module>; help(<module>.<name>)"`, or grep the repository for the definition and quote its `file:line` |
| Wrong assumption about the codebase | For every call into existing code, open the callee: does it do what the new code assumes? |
| Over-engineering | Compare the diff with the acceptance criteria: a class, helper, option or layer the ticket did not ask for is a question |
| A test that tests nothing | **Break it on purpose**: undo the production change, run the test, it must go red |
| Silent scope creep | `git -C <repo> status --short` lists only the files in `tasks.md`; anything else is explained or removed |
| Convention drift | The house checklist below |
| Stale library knowledge | The version in `poetry.lock`; the import works in the venv |
| Confident wrong explanation | The code is the truth: when an explanation and the code disagree, say so and believe the code |

## The house checklist

Open the skill while reviewing, cite its rule number as the skill spells it, and never
"correct" a deliberate deviation.

- **Names** (python-code-style 1–2, the senior's `references/naming-guide.md`): no single
  letters, no abbreviations, a name says its job, not its mechanism.
- **Deliberate deviations** (python-code-style 3–4): no `-> None`; truthiness instead of
  `is None`. Leave them; do not add them back.
- **Imports** (python-code-style 7): absolute.
- **Closed sets** (python-code-style 16): an enum, not strings.
- **Routes** (python-code-style 17): a route module holds only routes.
- **Comments** (python-code-style 15): only a non-obvious why.
- **Tests** (python-testing): fakes for ports, `responses`/`aioresponses` at the HTTP boundary,
  never patch our own wrapper (1); no parametrize, test modules hold
  only tests, fixtures in the conftest layer that owns them, a name that states the behaviour.
- **Layers** (python-ddd, DDD repositories only): the domain imports nothing outside itself;
  the unit of work commits explicitly; in rest-api, the shared-session UoW from its
  `CLAUDE.md`, never the deprecated one.
- **The repository's own `CLAUDE.md` and `AGENTS.md`**: they override the general skills.

## Stage G, the walkthrough (`cc.never-commit-unexplained`)

Show the diff against the ledger's `fork` one hunk at a time, untracked files in full. For each hunk he
answers two things: what it does, and why the ticket needs it. Grade silently:

| Grade | Meaning | You |
|---|---|---|
| ✔ | Right on both | Nothing; next hunk |
| ~ | Right on what, vague on why, or a gap | Fill the gap in one or two lines |
| ✗ | Wrong or "no idea" | His model beside the real one; ask again later in the session |

A hunk still ✗ at the end is removed when the ticket does not need it; otherwise it ships
recorded as "not explained back" in `understanding.md`. The gate passes when every hunk is
explained or recorded. One walkthrough per ticket replaces every other
check in this stage.
