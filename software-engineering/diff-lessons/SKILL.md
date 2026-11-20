---
name: diff-lessons
description: "Use when the operator wants to learn the programming language of code agents wrote in a dirty worktree, branch or MR — /diff-lessons [target] [lang:<language>], \"teach me this C++\", \"explain the C# in this diff\", \"I don't understand this Rust\" — before reviewing or committing it. NOT for what the change does (change-briefing), a course on a whole topic (teach-schematic) or grading the approach (solution-verdict)."
argument-hint: "[target] [lang:<language>]"
---

# Diff lessons

One message, at most 7000 characters (twice change-briefing's cap). It teaches up to three
ideas of the language the changed code is written in: each one is in the diff, comes with a
picture, and is put in terms of the languages the reader already knows. An idea is taught
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

```
<language> lessons · <repo> <branch; for an MR "!<iid> <source branch>"; else "detached at <sha7>"> vs <base sha7> · <N> files, +<a> −<d> · <committed | uncommitted | committed + uncommitted>
standard: <C++20 | C# 12 | Rust 2021 | …> (<the file it came from>)

THE CODE IN ONE LINE
<one sentence, at most 2 lines: what the changed code does>

LESSON 1 · <slug>: <the idea, as a short name>
<path:line>, the code: added lines, `…` for lines left out, at most 6 lines
<what it is, at most 3 plain lines>
<diagram, at most 8 lines>
≈ <the closest thing in Rust or Python, in a snippet or a few words>
≠ <where that match misleads the reader>
check: <one question>

LESSON 2 …
LESSON 3 …

WORTH A SECOND LOOK
- <path:line> — <a concrete risk that lesson N exposes>        at most 3

NEXT TIME
<slug>, <slug> … (not taught yet) · moved from <language>: nothing new · also changed: <language> (<n> lines), run with lang:<language>
```

The header is change-briefing's header line two without `<k> new`, its counts those of the
whole change set; the `vs` base and the
`committed | uncommitted | committed + uncommitted` rule are its own, except for an
uncommitted tree against `HEAD` (section 1). A lesson's `path:line` and code come from the
head's tree. NEXT TIME's three items are each left out when empty, and the part reads `none`
when all are; `also changed` skips a language named in `moved from`. With no lessons, leave
out WORTH A SECOND LOOK.

One lesson, as it should read (match the shape, not the topic):

````
LESSON 1 · cpp/std-move: a cast, not a move
src/cache.cpp:12, 41-42
```cpp
void process(std::unique_ptr<Buffer> p) { … }
auto buf = std::make_unique<Buffer>(n);
process(std::move(buf));
```
A `unique_ptr` (made by `make_unique`, C++14) holds a heap value with one owner, freed when
the owner goes out of scope. `std::move` only marks `buf` as giveable: `process`'s by-value
parameter `p` is what takes the value.
```text
before the call           while process() runs
buf ──owns──► [Buffer]    buf ··· (empty)
                          p ──owns──► [Buffer]   freed after the call
```
≈ Rust `Box<Buffer>`, moved into `process(buf)`
≠ Rust refuses to compile a use of `buf` after the move; C++ compiles `buf->size()` and
  it is undefined behaviour, typically a crash, since `buf` is empty
check: while process() runs, is `buf` empty or full, and which line made it so?
````

- **Grounded.** A lesson's code is added lines of the change. An idea with no changed line
  using it is not a lesson, however useful.
- **Bridge.** `≈` and `≠` are both required. `≈ none: <what comes closest>` and
  `≠ none: <why the match holds>` are the forms for no counterpart and no false friend. The
  `≠` line is the false friend: where what the reader knows gives the wrong answer.
- **Picture.** The diagram shows what the idea does: who owns what, how long a value lives,
  who calls whom. An idea with no flow gets a before and after pair.
- **Check.** A question that the diagram or the code answers, and that a guess does not.
- **Terms.** Each language word the reader would ask about gets plain words once, where it
  first appears.
- **Facts.** A rule that differs between standards says which one (`since C++20`). A rule
  you are not sure of is looked up in the language's documentation when a documentation or
  web tool is available, else marked `(unverified)`.
- **WORTH A SECOND LOOK** names a risk that an idea taught in this message makes visible in
  the diff, with that lesson's number. With none, write `none found`.
- **Diagrams** go in ```` ```text ```` fences, no line over 70 columns.
- **Count it.** Write it to `diff-lessons-draft.md` in the session scratchpad, overwriting
  the last run's, and run `LC_ALL=en_US.UTF-8 wc -m` on it: at most 7000, each lesson about
  1500 or less. Over that, cut the longest lesson first, in this order: its `check:` to five
  words; its `≠` to one line; its "what it is" to two lines; its diagram to 6 lines; its code
  to 4 lines; then NEXT TIME to one line; then wording elsewhere; and last, when three
  lessons remain and the total is still over, lesson 3, moved to NEXT TIME, with any WORTH
  line that cites it dropped. Every other part stays.

## 4. After it

After printing, append one line per lesson shown to `~/.cache/diff-lessons/<key>.md` with
`>>`, never a rewrite (`mkdir -p` the folder; when the write fails, say so and go on):
`<slug> <ISO date> — <short name> (<repo>:<path>)`. The writes this skill makes are those
lines, the folder, the scratchpad draft, and change-briefing's one MR fetch.

Then stop and wait. Answer a question in the same way: plain words first, a picture when
there is a flow, `file:line` when it points into the code, a few lines. Give a `check:`
answer only when asked. A rerun on the same change teaches the next ideas; the earlier
lessons come back through `again`.

- `skip <slug>` or `I know <slug>`: append `<slug> <ISO date> — known`.
- `again <slug>`: teach that one idea now in the full lesson shape, appending nothing.

An edit to the code belongs to the workflow that owns the change, not to this skill.
