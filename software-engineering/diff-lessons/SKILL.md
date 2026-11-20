---
name: diff-lessons
description: "Use when the operator wants to learn the programming language of code agents wrote in a dirty worktree, branch or MR — /diff-lessons [target] [lang:<language>], \"teach me this C++\", \"explain the C# in this diff\", \"I don't understand this Rust\" — before reviewing or committing it. NOT for what the change does (change-briefing), a course on a whole topic (teach-schematic) or grading the approach (solution-verdict)."
argument-hint: "[target] [lang:<language>]"
---

# Diff lessons

One message, at most 16000 characters (four and a half times change-briefing's cap). It teaches up to three
ideas of the language the changed code is written in: each one is in the diff, starts from the
problem it solves, comes with a picture and a step-by-step reading, and is put in terms of the
languages the reader already knows. An idea is taught
once, so the reader learns a language one change at a time.

## The reader

Knows Rust and Python well. **Learning: C++ and C#.** Every lesson bridges to Rust or
Python. The learning list orders the languages in section 1. For a Rust or Python diff the
lesson is a *corner*, bridged to the other of the two, or to C++ or C# where that is the
nearer match (section 2 says which ideas qualify). Edit this section when the reader's
languages change.

## 1. The argument, the change, the language

`lang:<language>` can stand anywhere in the argument (a git ref cannot hold a `:`); take it
out, and what is left is the target. An empty `lang:` counts as absent. When the whole
target is one of these names: `c++ cpp c# csharp cs rust rs python py c go java kotlin
typescript ts javascript js`, and `git rev-parse --verify` fails on it, it is a `lang:` too
(`/diff-lessons c++`), unless an explicit `lang:` is present. Names map to one key, used for
the slug, the record's file name, the header and `lang:`: `c++`, `cpp` → `cpp`; `c#`,
`csharp`, `cs` → `csharp`; `rs` → `rust`; `py` → `python`; `ts` → `typescript`; `js` →
`javascript`; the rest are themselves.

**The change.**

- No target, and the working tree has uncommitted changes: that tree against `HEAD`. It is
  `git diff HEAD` plus the untracked files that
  `git status --short --untracked-files=all` lists, each counted as new with its `wc -l`.
  The header says `vs <HEAD sha7>` and `uncommitted`.
- Otherwise: the target is change-briefing's, resolved as its section 1, *Find the change*.
  Open `../change-briefing/SKILL.md` (a sibling directory), read that one section, and
  follow it; do not invoke the skill. When the file is missing, ask for the change as a
  branch, MR or commit range.

When nothing resolves, ask one question: which change. When the change has no added line in
a source file, say "no source code changed" and stop.

**Source files** are these extensions and no others: C++ `.cpp .cc .cxx .hpp .hh .inl`, and
`.h` when the repository has a `.cpp`, `.cc` or `.cxx` file (else C); C# `.cs .razor`; Rust
`.rs`; Python `.py`; C `.c`; Go `.go`; Java `.java`; Kotlin `.kt`; TypeScript `.ts .tsx`;
JavaScript `.js .jsx`. Leave out paths under `third_party/ vendor/ node_modules/`,
`*.g.cs`, `*.Designer.cs`, files whose first 5 lines say auto-generated, anything
`git check-attr linguist-generated linguist-vendored` marks, and binary entries; a rename
counts under its new path. (Untracked build output is already left out by `.gitignore`.)
With `lang:` naming a language that has no added line, say `no <language> in this change;
it changed: <language> (<n> lines)` and stop.

**The language.** Rank the languages by added lines in source files: the reader's learning
languages first, by added lines (a tie: more files, then alphabetical), then the others the
same way. Evaluate them in that order and stop at the first with at least two qualifying
ideas (section 2). When none reaches two, take the one with the most qualifying ideas (a
tie: first in rank order). With `lang:`, take that language and never fall through. A
language passed over is named in NEXT TIME as `moved from <language>: <its slugs>`, or
`nothing new` when it had none.

**The standard**, read from the head's tree (`git -C <checkout> show <head>:<path>`; the
working tree for an uncommitted change), in the changed file's nearest ancestor directory
that holds the file, else the root. Look up from the chosen language's changed file with the
most added lines, walking from its directory up to the root: the first file of the row that
contains the setting wins. For C#, that is `LangVersion` in the nearest `.csproj`, then the
nearest props file, then `TargetFramework(s)`. When the language's other changed files give
another standard, add ` (+ others differ)`.

| Language | Where | Value |
|---|---|---|
| C++ | `CMakeLists.txt`: `CMAKE_CXX_STANDARD`, `cxx_std_NN`, `-std=c++NN` or `-std=gnu++NN` | `C++NN` |
| C# | `*.csproj` or `Directory.Build.props`: `LangVersion` (a number), else `TargetFramework`, or the highest of `TargetFrameworks`: `net6.0` C# 10, `net7.0` 11, `net8.0` 12, `net9.0` 13, `net10.0` 14 | `C# N` |
| Rust | `edition` in `Cargo.toml`; `edition.workspace = true` reads the workspace root's | `Rust <edition>` |
| Python | `requires-python` in `pyproject.toml` | as written |

Anything else (`latest`, `preview`, `netstandard2.0`, `net48`, no file): `standard: not found`.

## 2. Choose the lessons

Read the first word of each line of `~/.cache/diff-lessons/<key>.md`, the slugs taught or
known (a missing file means none). An idea qualifies when all four hold:

- a changed line uses it;
- removing or changing it changes what the code does or whether it compiles;
- its slug is not in the record;
- for `cpp` and `csharp`: it has no counterpart in Rust or Python, or has a lookalike that
  behaves differently. For `rust`, `python` and any other language: no line of the head's
  tree outside the changed files uses its keyword or API, so it is not yet in the codebase
  the reader knows. The test is `git grep -w -F -e <name> <head> -- <source extensions>` with
  the changed paths excluded; a hit in a comment or a string does not count.

One construct per idea, never a bundle. Its slug is `<key>/<name>`: lowercase, `::` written
as `-`, the language's keyword or type name otherwise verbatim (`cpp/unique_ptr`,
`cpp/std-move`, `csharp/async`). Before coining one, read the record's slugs and reuse the one
that names the same construct.

Take `min(3, qualifying)` ideas. Order: the idea the change depends on most first; among
equals, the more basic idea first, so a later lesson builds on an earlier one. Ideas that
qualified and were not taught go on the NEXT TIME line. With fewer than two lessons, print the
one or none there is. With none, add after NEXT TIME the line
`NOTHING NEW — no idea in this change is new to you (taught earlier, known, or the same in Rust or Python).`

## 3. Write the lessons

Exactly these parts, in this order; with fewer than three lessons, those that exist:

````
```text
╭────────────────────────────────────────────────────────────────────╮
│ <LANGUAGE> LESSONS · <repo> <branch> vs <base sha7> · <state>      │
│ <N> files, +<a> −<d> · <standard> (<file>) · record: <n> → <n+k>   │
╰────────────────────────────────────────────────────────────────────╯
```

THE CODE IN ONE LINE
<one sentence, at most 2 lines: what the changed code does>

## ══ LESSON 1 ══ <the rule to remember, at most 8 words>
<path:first line> · `<slug>` · reach <10 cells> <m> of <N> added lines
```<cpp | csharp | rust | python | …>
<NN> <► or space> <the code, its own indentation kept>      added lines, ` …` for a gap, at most 10
```
THE PROBLEM
<what goes wrong without this idea: at most 4 lines of 78 columns>

IN PLAIN WORDS
<the idea, assuming the reader never saw it: at most 6 lines>

READ IT LIKE THIS
```text
<@line rows, at most 12 lines>
```
<one numbered step per @ row, at most 6, at most 2 lines each>

WHY <C++ | C#> IS BUILT THIS WAY
<the design reason, at most 3 lines>

≈ <the closest thing in Rust or Python, in a snippet or a few words>
```text
╭────────────────────────────────────────────────────────────────────╮
│ <✔ or ≠> <Rust or Python>  <what the language you know does>       │
│ <✘ or ≠> <C++ or C#>       <what this one does instead>            │
╰────────────────────────────────────────────────────────────────────╯
```

RULE OF THUMB
<what to do in practice: at most 2 lines>

SEE IT AGAIN
<where else the reader will meet it: at most 2 lines>

? <one question>

LESSON 2 …
LESSON 3 …

```text
╭─ WORTH A SECOND LOOK ──────────────────────────────────────────────╮
│ <✘ or ≠> <path:line> — (<n>) <a concrete risk lesson n exposes>    │
╰────────────────────────────────────────────────────────────────────╯
```

NEXT TIME
- not taught yet: <slug>, <slug> …
- moved from <language>: <its slugs, or nothing new>
- also changed: <language> (<n> lines), run with lang:<language>
````

The banner is change-briefing's header line two without `<k> new`, split over two rows: `<branch>`
is the branch, `!<iid> <source branch>` for an MR, else `detached at <sha7>`; `<state>` is
`committed`, `uncommitted` or `committed + uncommitted`; `<standard>` reads `C++20`, `C# 12`,
`Rust 2021` or `not found`. Its counts are those of the whole change set; the `vs` base and the
`committed | uncommitted | committed + uncommitted` rule are its own, except for an
uncommitted tree against `HEAD` (section 1). A lesson's `path:line` and code come from the
head's tree. `record: <n> → <n+k>` counts the lines of `~/.cache/diff-lessons/<key>.md`
before this message and after it (n plus the lessons shown). NEXT TIME's three items are each
left out when empty, and the part reads `none` when all are; `also changed` skips a language
named in `moved from`. WORTH A SECOND LOOK has at most 3 rows. With no lessons, leave it out.

One message, as it should read (match the shape, not the topic):

````
```text
╭────────────────────────────────────────────────────────────────────╮
│ C++ LESSONS · cpp-demo main vs 3a65e50 · uncommitted               │
│ 1 file, +34 −1 · C++20 (CMakeLists.txt) · record: 0 → 1            │
╰────────────────────────────────────────────────────────────────────╯
```

THE CODE IN ONE LINE
A Cache owns heap Buffers by key; main hands one in, then reads it again.

## ══ LESSON 1 ══ one owner: std::move hands it over
src/cache.cpp:30 · `cpp/std-move` · reach ███░░░░░░░ 3 of 34 added lines
```cpp
30   auto buf = std::make_unique<Buffer>(64);
31   cache.put("a", std::move(buf));
32 ► std::cout << buf->size() << "\n";
```
THE PROBLEM
A heap value (memory you ask for at run time) must be freed exactly once:
twice crashes, never leaks. C++ has no borrow checker to police that, so a
value gets one owner object, and a rule decides who the owner is.

IN PLAIN WORDS
`unique_ptr<Buffer>` is that owner. It holds the Buffer and frees it when
the `unique_ptr` itself goes out of scope. It cannot be copied, only handed
over. `std::move(buf)` is the hand-over, but the name misleads: it moves
nothing. It only says "buf may be emptied now"; the function parameter that
receives it does the emptying.

READ IT LIKE THIS
```text
@30  buf ──owns──► [Buffer]
@31  buf ··· (empty)
     items_["a"] ──owns──► [Buffer]        ◄ freed when the cache dies
@32  buf->size()  ✘ reads through an empty pointer
```
1. Line 30 builds the Buffer on the heap; `buf` owns it.
2. Line 31 hands it to `put`: the cache's map owns it now, `buf` is empty.
3. Line 32 still uses `buf`. It compiles; at run time it reads through null.

WHY C++ IS BUILT THIS WAY
A move is a plain cast, so it costs nothing at run time and old copying
code keeps working. The price: nothing stops you touching a moved-from name.

≈ Rust `Box<Buffer>`, moved into `cache.put("a", buf)`
```text
╭────────────────────────────────────────────────────────────────────╮
│ ✔ Rust  line 32 is a compile error (use after move)                │
│ ✘ C++   line 32 compiles; buf is empty, so it crashes at run time  │
╰────────────────────────────────────────────────────────────────────╯
```

RULE OF THUMB
After `std::move(x)`, treat `x` as unusable until you assign to it again.

SEE IT AGAIN
Every `unique_ptr` or `vector` passed by value from a local variable.

? what does `buf` hold on line 32, and which line emptied it?

```text
╭─ WORTH A SECOND LOOK ──────────────────────────────────────────────╮
│ ✘ src/cache.cpp:32 — (1) buf is used after std::move; it is empty  │
╰────────────────────────────────────────────────────────────────────╯
```

NEXT TIME
- not taught yet: cpp/explicit, cpp/const-member
````

- **Grounded.** A lesson's code is added lines of the change. An idea with no changed line
  using it is not a lesson, however useful.
- **Bridge.** `≈` then a pair, always. Pair `✔`/`✘` when the known language guards what the
  new one leaves open: the `✔` line says how Rust or Python stops it or answers it, the `✘`
  line says the new language accepts it without error or warning, then misbehaves or answers
  differently. Pair `≠`/`≠` when the new language only differs (a compile error with another
  cause, another name, another rule). `✔` or the first `≠` is the Rust or Python row; `✘` or
  the second `≠` is the new language's row; both sit in the box. `≈ none: <what comes closest>` and `≠ none: <why the match holds>` stay for no
  counterpart and no false friend.
- **Boxes.** The banner, the `✔`/`✘` pair and WORTH A SECOND LOOK are each a box in a
  ```` ```text ```` fence, exactly 70 columns wide: a top of `╭`, `─` and `╮` (WORTH's top
  carries its title after `╭─ `), rows of `│ `, the text padded with spaces to 66 columns, and
  ` │`, and a bottom of `╰`, `─` and `╯`. A row's text is plain: no backticks; to fit 66 columns, drop articles and filler words first. What does not fit
  in 66 columns continues on the next row, indented 2 spaces; a long branch name in the
  banner is cut with `…`.
- **Reach bar.** A 10-cell bar, `█` filled and `░` empty: the share of the language's added
  source lines that use the idea (`m`: the added lines where the idea is at work, not a line that only names its keyword in
  another role;
  `N`: all added source lines of the language), rounded to the nearest cell and at least one, then
  `<m> of <N> added lines`.
- **Picture.** Rows are snapshots: `@<line>` is the state after that source line ran;
  continuation rows are indented 5 spaces. Time runs down the page, never across. The last
  `@` row of a `✘` lesson is the line the `►` marks. An idea with no flow gets two rows,
  `without <x>` and `with <x>`; a branch gets one row per condition, labelled by it. The words, every arrow carrying one:

```text
name                   a variable
[Type]                 a value on the heap
(file, open)           an outside resource (file, socket, lock) and its state
a ──owns──► [T]        a decides when it dies and frees it
a ──refs──► [T]        one of several holders; the runtime frees it when none is left
a ··points at··► [T]   a view: no say in its lifetime (C++ T* and &, Rust &)
a ··· (empty)          points at nothing: moved-from, null
A ──calls──► B         who runs whom
@31  ◄ note  ✘         the state after line 31 · a remark · where the trap bites
```

- **Code.** `<NN>` is the file's own line number, right-aligned, from
  `git -C <checkout> show <head>:<path> | cat -n`. A stretch of skipped lines is one row,
  `…`, in the gutter column. `►` marks one line: where the `✘` bites, else where the idea is
  first used. A code line over 76 columns with its gutter is cut with
  `…`.
- **Check.** `? ` and a question that the diagram or the code answers, and that a guess does
  not.
- **Teaching order.** Each lesson goes from the problem to the rule: THE PROBLEM says what
  goes wrong without the idea, in the language's own terms and with no jargon the reader has
  not met; IN PLAIN WORDS names the mechanism and assumes the reader never saw it; READ IT
  LIKE THIS walks the diagram, one numbered step per `@` row, each a plain sentence that
  names the line; WHY says the design reason (what the language bought, what it cost);
  RULE OF THUMB is what to do in practice; SEE IT AGAIN names where else the reader will meet
  the idea. Each language word the reader would ask about gets plain words once, where it
  first appears.
- **Facts.** A rule that differs between standards says which one (`since C++20`). A rule
  you are not sure of is looked up in the language's documentation when a documentation or
  web tool is available, else marked `(unverified)`.
- **WORTH A SECOND LOOK** names a risk that an idea taught in this message makes visible in
  the diff, with that lesson's number `(n)`. With none, write `none found`.
- **Glyphs.** ASCII; inside code fences the source's own characters; and outside them only
  box drawing and block elements (`─ │ ╭ ╮ ╰ ╯ █ ░`), arrows (`→ ↳`) and
  `► ◄ ▲ ▼ ✔ ✘ ≈ ≠ − — · … ×`. Never emoji (✅ ❌ ⚠️) or CJK, which print two columns wide,
  and no trailing spaces. Diagrams go in ```` ```text ```` fences, no line over 70 columns.
- **Count it.** Write it to `diff-lessons-draft.md` in the session scratchpad, overwriting
  the last run's, and run `python3 -I <this skill's directory>/scripts/check_lessons.py` on
  it. It prints `chars: <n>` and one line per violation: more than 16000 characters, a lesson
  over about 5000, a diagram or box line over 70 columns, a box row that is not exactly 70, a
  glyph outside the list above, a double-width character, a trailing space. Fix every
  violation and run it again until it prints none (a clean run prints only the `chars:` line). Over the size limits, cut the longest
  lesson first, in this order: its SEE IT AGAIN; its WHY to one line; its RULE OF THUMB to one
  line; its IN PLAIN WORDS to four lines; its code to 8 lines; its diagram to 10 rows; its `?`
  to five words; then NEXT TIME to one line; then wording elsewhere; and last, when three
  lessons remain and the total is still over, lesson 3, moved to NEXT TIME, with any WORTH row
  that cites it dropped. Never cut THE PROBLEM, the numbered steps, the `≈` line, the `✔`/`✘`
  box, the `►` or the lesson heading: they are what teaches.

## 4. After it

After printing, append one line per lesson shown to `~/.cache/diff-lessons/<key>.md` with
`>>`, never a rewrite (`mkdir -p` the folder; when the write fails, say so and go on):
`<slug> <ISO date> — <short name> (<repo>:<path>)`. The writes this skill makes are those
lines, the folder, the scratchpad draft, and change-briefing's one MR fetch.

Then stop and wait. Answer a question in the same way: plain words first, a picture when
there is a flow, `file:line` when it points into the code, a few lines. Give the `?`
answer only when asked. A rerun on the same change teaches the next ideas; the earlier
lessons come back through `again`.

- `skip <slug>` or `I know <slug>`: append `<slug> <ISO date> — known`.
- `again <slug>`: teach that one idea now in the full lesson shape, appending nothing.

An edit to the code belongs to the workflow that owns the change, not to this skill.
