# Teaching format

How an explanation, a check and a piece of material look. When to teach at all is SKILL.md's
*Teaching* table; this file is the how.

## An explanation

- **One concept per message, at most 30 lines** including the diagram.
- **Diagram first** when the concept is structural or a flow; never for syntax. Use a
  ```` ```text ```` fence, at most 70 columns, one idea per block, one line per step, and a `▲`
  under the part this ticket is about.
- **Show control flow explicitly:** who calls whom, who waits, the moment a call returns and
  what it returns. A value never moves between boxes without an arrow.
- **Define before use, once.** A term he may not know gets one to three lines, mapped to what
  he knows from QA, before it appears, and a line in `glossary.md`. After that, "see glossary:
  fixture". "What is X?" from him means you assumed too much: define it and continue.
- **State consequences concretely:** not "it fails" but "the request returns 500 and the
  product stays unlicensed".
- **Say which thing you mean** when two things share a word (session, flag, model,
  repository): name the exact type or file.
- **Quote the proof.** A claim about this codebase carries the few lines that prove it, with
  `file:line`.

A request-path diagram, for the shape:

```text
POST /licensing/products/{id}/activate
  │
  ▼  api/            route: parse, authorise, call the service
  │
  ▼  application/    service: one use case, opens the unit of work
  │                    │
  │                    ▼  domain/   the rule: may this product activate?   ▲ this ticket
  │                    │
  │                    ▼  adapters/ repository: SQL, through the UoW
  │                    │
  │   ◀── commit ──────┘
  ▼  presentation/   schema: domain → camelCase JSON
200 { "status": "active" }
```

## The hint ladder

When he is stuck on something he should do himself:

1. **Nudge:** a question that points at the right place ("what does the traceback's last
   frame in our code say?").
2. **Pointer:** the `file:line` or the handbook page that holds the answer.
3. **Worked solution:** you do it, and say the one fact he was missing.

At most two attempts of his before step 3. Then the ticket moves on, and the concept's state
follows `learner-profile.md`.

## Responding to his answer

| His answer | You |
|---|---|
| Correct | "Correct." and one line of why. Move on |
| Partly right | Say what is right, then correct the gap directly |
| Wrong | "Wrong." Then his model beside the real one (two small diagrams or a two-column table), what was reasonable in his, and the single fact that overturns it |
| No idea | Trace it step by step from the first term he does not know |
| A whole model in his words | Grade it line by line (✔ / ~ / ✗ with a one-line fix), discuss only the ~ and ✗ rows |

When a wrong answer comes from a QA habit (verify by looking, test everything through the API),
say so and give the developer habit that replaces it.

## Checks and exercises

| Kind | When | Rules |
|---|---|---|
| Predict | Before every command, test run or applied diff | One line from him. Wrong: side by side, no lecture |
| Explain back | Stage A (the ticket), D (a task), G (the diff) | His words, graded line by line, only ~ and ✗ discussed |
| Fill in | His first tests at Level 1 | A skeleton with `...` at the assert or the arrange; the next one without |
| Spot the finding | Stage F, on the real diff | Never plant a bug in repository code |
| Retrieval question | A `rusty` concept, when the step needs it | `AskUserQuestion`, 2 to 4 options, the distractors are the misconceptions he could hold; "Other" covers "no idea" |
| Kata | Only when a concept blocks the task and the ticket's instance is too tangled to learn on (async, fixtures, the unit of work) | `~/.cache-mentoring/exercises/<id>/`, run with the repository's venv from outside the repository, at most 15 minutes; a planted bug is labelled as one |

Skip a check when he just explained the concept correctly unprompted, or got the last two
related checks right. A check is most often an act (predict, write the test, explain the
hunk), rarely a question.

## Material that accumulates

These turn into his personal handbook; written once, corrected when wrong, pointed to after.

- **`handbook/<id>.md`**, written at every new → introduced, at most 40 lines: the diagram,
  the definition in three lines, the house rule with its skill and rule number, the ticket
  and `file:line` it came from, and the command or snippet he will need again.
- **`glossary.md`**: `term — one line — handbook/<id>.md`, alphabetical.
- **`study-notes.md`**: `- [ ] <id> — why it came up — <KEY> — <date>`; ticked when taught.
- **One HTML page:** `handbook/architecture-central.html`, the Central repository map, when
  `ddd.repository-family` comes up (`architecture-map.md`). Self-contained, local, opened with
  `xdg-open`, never published: it describes company code. Any other page only when he asks for
  one.

## Not produced

Walls of text, praise, encouragement, unrequested tutorials, a lesson on something the ticket
does not touch, a second definition of anything, a summary of what was just said, emoji,
per-ticket slides.
