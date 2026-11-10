# The learner profile

`~/.cache-mentoring/profile.md` is the learner model. It is read in full at every session
start and is the only thing that decides whether a concept gets a lesson, a reminder, a
question or nothing (SKILL.md, *Teaching*). It is Markdown so Cristian can correct it in an
editor, and a fixed-column table so it parses reliably.

## Format

Front matter, then one table, one row per concept met so far. A concept with no row is new.

```text
---
learner: <name>
level: 0              # 0 Observer, 1 Tester, 2 Driver, 3 Independent
level_since: 2026-11-20
sessions: 7
pace: normal          # normal | fast; "just do it" sets fast, every session starts normal
clean_gates: 1        # tickets in a row with no ✗ left at the end of stage G
---
| id | state | seen | last | evidence | misconception |
|---|---|---|---|---|---|
| git.branch-from-base | mastered | 5 | 2026-11-20 | SYN-3120: typed the sequence from memory; SYN-3115: with the handbook | |
| pytest.fixture | practised | 2 | 2026-11-18 | SYN-3115: wrote `expired_product` after a nudge | believes a fixture runs once per module |
| ddd.repository-port | stuck | 3 | 2026-11-20 | SYN-3120: put SQL in the domain twice | confuses the port with its SQL implementation |
```

- `id`: from `curriculum.md`. A concept the curriculum lacks gets a new id in the same
  `<area>.<kebab-name>` shape, and a line in `~/.cache-mentoring/curriculum-added.md`, in
  `curriculum.md`'s format with the ticket that added it; read that file with
  `curriculum.md`.
- `state`: `introduced`, `practised`, `mastered`, `rusty` or `stuck`.
- `seen`: how many tickets it came up in. `last`: the ISO date it was last exercised.
- `evidence`: ticket key and one clause, newest first, at most three.
- `misconception`: the wrong belief he currently holds, in one line; cleared only once he gets
  it right again on a later day.

## Promotion and demotion

| From → to | When |
|---|---|
| new → introduced | You showed the worked example |
| introduced → practised | He did it himself with at most the pointer hint, and it worked: a green test, the right command, an explanation you accepted |
| practised → mastered | He did it alone, or explained it correctly when asked, **on a different day** from the practised evidence. The day gap is the spacing; one session never masters anything |
| mastered → rusty | At session start, `last` is more than 30 days ago |
| rusty → mastered | One correct retrieval answer or one correct use |
| rusty → practised | A wrong retrieval answer: a reminder of at most 10 lines, then he does it |
| introduced or practised → stuck | Failed after the hint ladder ran out, in two separate sessions |
| stuck → practised | Did it with a hint after your second worked example |
| mastered or rusty → practised, misconception filled | Evidence of a wrong belief: a wrong use, or a Cristian review comment naming one |
| introduced, practised or stuck: state kept, misconception filled | The same evidence |

A concept with no row gets none from a comment: it goes to `study-notes.md` with the
comment's first line and is taught as new at its next instance.

A multiple-choice answer alone never promotes past `practised`: promotion takes an act (he
did it, or said it in his own words). Multiple choice is for `rusty` retrieval only.

## Who writes it, when

You, at three moments, editing rows in place (never regenerate the file, so a line Cristian
edited by hand survives):

1. Right after a check or an attempt that changes a state or a misconception: the row, then
   a commit. Plain correct use of a known concept changes nothing until stage J.
2. At stage J, the ticket closed: `seen`, evidence, and `last` set to the ticket's last
   working day for every id on the ledger's `concepts:` line; `clean_gates` plus one when
   stage G ended with no ✗, else back to 0.
3. At stage J, reading Cristian's review comments on the MR: a comment that names a wrong
   belief or a missed rule fills `misconception` per the table above; a comment that only
   asks for a change is evidence, not a demotion. Quote the comment's first line in the
   evidence.

Commit subject shapes, so `git log` reads as his growth record:

```text
profile: pytest.fixture introduced → practised (SYN-3115)
profile: level 1 → 2 (his yes; criteria met: pytest.fixture, ddd.layers mastered)
handbook: pytest.fixture
glossary: fixture, conftest
study-notes: py.async-await deferred (SYN-3115)
session: 8 started, pace normal, rusty: git.squash-merge
ticket: SYN-3115 → E task 3 of 5
retro: SYN-3115
```

## Cristian's view

He reads `git -C ~/.cache-mentoring log -p profile.md`, or edits the file: a state, the
level, a misconception. Treat any edit of his as the truth, even when it contradicts your
evidence.

When he asks "show me the profile" in a session: the level, its entry criteria met and
missing, one line per concept that is not `mastered`, the open study notes, and nothing else.
