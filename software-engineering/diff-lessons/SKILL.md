---
name: diff-lessons
description: "Use when the operator wants to learn the programming language of code agents wrote in a dirty worktree, branch or MR — /diff-lessons, \"teach me this C++\", \"explain the C# in this diff\", \"I don't understand this Rust\", \"what should I learn from this change\" — before reviewing or committing it. NOT for what the change does (change-briefing), a course on a whole topic (teach-schematic) or grading the approach (solution-verdict)."
argument-hint: "[target] [lang:<language>]"
---

# Diff lessons

One message, at most 7000 characters (twice change-briefing's cap). It teaches three or four
ideas of the language the changed code is written in: each one is in the diff, comes with a
picture, and is put in terms of the languages the reader already knows. An idea is taught
once, so the reader learns a language one change at a time.

## The reader

Knows Rust and Python well; is learning C++ and C# (November 2026). Every lesson bridges to
Rust or Python. For a Rust or Python diff, skip what a daily user knows and teach the corner
the code leans on. Edit this section when the reader's languages change.

## 1. Find the change and its language

The target and its resolution are change-briefing's section 1, *Find the change*: read that
one section from the change-briefing skill and follow it, read-only. The default is the same:
the ticket this session is delivering, else the current repository's branch and uncommitted
tree.

The language is the one with the most added lines in the change set, counting source files
only (not lockfiles, generated or vendored code, docs, or build files). `lang:<language>` in
the argument overrides it. The other languages the change touches go on one closing line.
When no source file changed, or no change resolves, ask one question: which change.

Read the build files for the language's standard: `CMakeLists.txt` or `.clang-format` for
C++, `*.csproj` `LangVersion` and `TargetFramework` for C#, else say `not found`.

## 2. Choose the lessons

Read `~/.cache/diff-lessons/<language>.md`, the record of ideas already taught (a missing
file means none). An idea qualifies as a lesson when all four hold:

- a changed line uses it;
- the code's behaviour depends on it: it is not boilerplate the reader can skip;
- the record has no line for its slug;
- a Rust or Python programmer would misread it or not know it.

Take three qualifying ideas, four when each is short. Order: the idea the change depends on
most first; among equals, the more basic idea first, so a later lesson builds on an earlier
one. Slugs are `<language>/<idea in kebab-case>`, e.g. `cpp/unique-ptr-move`. An idea the
diff uses that did not make the cut goes on the NEXT TIME line. When fewer than two ideas
qualify, say the diff holds nothing new for the reader, teach the one or none that does, and
offer `again <idea>`.

## 3. Write the lessons

Exactly these parts, in this order:

```
<language> lessons · <repo> <branch, else "detached at <sha7>"> · <N> files, +<a> −<d> · <committed | uncommitted | committed + uncommitted>
standard: <C++20 | C# 12 on .NET 8 | …> (<the build file it came from>, else "not found")

THE CODE IN ONE LINE
<one sentence, at most 2 lines: what the changed code does>

LESSON 1 · <the idea, as a short name>
<path:line>, the code, at most 6 lines, from the diff
<what it is, at most 3 plain lines>
<diagram, at most 8 lines>
≈ <the closest thing in Rust or Python, in a snippet or a few words>
≠ <where that match misleads the reader>
check: <one question the diff answers>

LESSON 2 …
LESSON 3 …

WORTH A SECOND LOOK
- <path:line> — <a concrete risk these ideas expose>        at most 3

NEXT TIME
<ideas in this diff not taught yet, one line> · also changed: <language> (<n> lines), run with lang:<language>
```

One lesson, as it should read (match the shape, not the topic):

````
LESSON 1 · unique_ptr: one owner, freed by itself
src/cache.cpp:42
```cpp
auto buf = std::make_unique<Buffer>(n);
return process(std::move(buf));
```
`unique_ptr` holds a heap value with exactly one owner; the value is freed when the owner
goes out of scope. `std::move` hands the ownership to `process`.
```text
before the call           during process()
buf ──owns──► [Buffer]    buf ··· (empty)
                          p ──owns──► [Buffer]  freed when process returns
```
≈ Rust `Box<Buffer>`, moved into `process(buf)`
≠ Rust refuses to compile a use of `buf` after the move; C++ compiles `buf->size()` and
  crashes at run time, since `buf` is now empty
check: what does `buf` hold on line 43?
````

- **Grounded.** Every lesson's code is lines of the change, with their `path:line`. An idea
  with no changed line using it is not a lesson, however useful.
- **Bridge.** `≈` and `≠` are both required. With no equivalent, write
  `≈ none: <what comes closest>`. The `≠` line is the false friend: the place where what the
  reader knows from Rust or Python gives the wrong answer.
- **Terms.** Each language word the reader would ask about gets plain words once, where it
  first appears.
- **Facts.** A rule of the language that differs between standards says which one
  (`since C++20`). A rule you are not sure of is looked up in the language's documentation,
  or marked `(unverified)`.
- **WORTH A SECOND LOOK** names a risk that the taught ideas make visible in the diff, in the
  code's own terms: the hole is one the lessons explain. With none, write `none found`.
- **Diagrams** go in ```` ```text ```` fences, no line over 70 columns, and show what the idea
  does: who owns what, how long a value lives, who calls whom, a state before and after.
- **Count it.** Write it to the session scratchpad and run `LC_ALL=en_US.UTF-8 wc -m` on the
  file: at most 7000. Over that, cut in this order: each `check:` to five words; NEXT TIME to
  one line; the fourth lesson, moved to NEXT TIME; each `≠` line to one line; wording. Every
  other part stays.

## 4. After it

Append one line per lesson shown to `~/.cache/diff-lessons/<language>.md` (create the folder
and file when absent): `<date> <slug> — <short name> (<repo>:<path>)`. This is the one write
this skill makes besides the scratchpad file.

Then stop and wait. Answer a question in the same way: plain words first, a picture when
there is a flow, `file:line` when it points into the code, a few lines. Give a `check:`
answer only when asked.

- `skip <idea>` or `I know <idea>`: append `<date> <slug> — known`.
- `again <idea>`: teach it in full as the first lesson of the next run, whatever the record
  says.

An edit to the code belongs to the workflow that owns the change, not to this skill.
