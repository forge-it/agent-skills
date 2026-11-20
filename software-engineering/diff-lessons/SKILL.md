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
Python. The learning list picks the language in section 2 and decides what counts as new.
For a Rust or Python diff, the lesson is a *corner*: an idea the code relies on that a daily
user rarely writes (`unsafe`, `Pin`, a descriptor, a metaclass), bridged to the other of the
two languages, or to C++ or C# where that is the nearer match. Edit this section when the
reader's languages change.

## 1. The argument and the change

`lang:<language>` can stand anywhere in the argument (a git ref cannot hold a `:`). Take it
out; what is left is the target. Language names map to one key, used for the slug, the
record's file name, the header and `lang:`: `c++`, `cpp` → `cpp`; `c#`, `csharp`, `cs` →
`csharp`; `rs` → `rust`; `py` → `python`; any other language is its lowercase name.

- **No target, and the working tree has uncommitted changes:** the change is that tree
  against `HEAD`: `git diff HEAD` plus the untracked files that
  `git status --short --untracked-files=all` lists, each counted as new with its `wc -l`.
- **Otherwise:** the target is change-briefing's, resolved as its section 1, *Find the
  change*, does: read that one section from the change-briefing skill and follow it.

When nothing resolves, ask one question: which change. When the change resolves but no
source code changed, say so and stop.

**The language.** Count added lines per language over source files only, by extension:
C++ `.cpp .cc .cxx .hpp .hh .inl` (and `.h` when the repository's other sources are C++), C#
`.cs .razor`, Rust `.rs`, Python `.py`, else the file's well-known language. Leave out
lockfiles, docs, build files (`CMakeLists.txt`, `*.csproj`, `*.sln`, `Cargo.toml`), paths
under `obj/ bin/ third_party/ vendor/ node_modules/`, `*.g.cs`, `*.Designer.cs`, files whose
first lines say auto-generated, and anything `git check-attr linguist-generated
linguist-vendored` marks; binary entries and the old side of a rename do not count. Of the
reader's learning languages that changed, take the one with most added lines (a tie: more
files, then alphabetical); when none changed, the largest language overall. `lang:` overrides
this. When the chosen language yields fewer than two lessons (section 2), move to the next
language by added lines, and say so in NEXT TIME.

**The standard**, read from the head's tree (`git -C <checkout> show <head>:<path>`, the
working tree for an uncommitted change), in the changed file's nearest ancestor directory
that has the file, else the root: C++ `CMAKE_CXX_STANDARD`, `cxx_std_NN` or `-std=` in
`CMakeLists.txt`; C# `LangVersion`, else the default of `TargetFramework` (`net6.0` C# 10,
`net7.0` 11, `net8.0` 12, `net9.0` 13, `net10.0` 14); Rust `edition` in `Cargo.toml`; Python
`requires-python` in `pyproject.toml`. Nothing found: `standard: not found`.

## 2. Choose the lessons

Read the first column of `~/.cache/diff-lessons/<key>.md`, the slugs already taught or
known (a missing file means none). An idea qualifies when all four hold:

- a changed line uses it;
- removing or changing it changes what the code does or whether it compiles;
- the record has no equivalent slug;
- it has no counterpart in Rust or Python, or has a lookalike that behaves differently.

One construct per idea. Its slug is `<key>/<the language's own term>`, e.g. `cpp/unique_ptr`,
`cpp/std-move`, `csharp/async-await`, never a bundle. Before coining a slug, read the
record's slugs and reuse the one that means the same.

Take `min(3, qualifying)` ideas. Order: the idea the change depends on most first; among
equals, the more basic idea first, so a later lesson builds on an earlier one. The ideas
that qualified and were not taught go on the NEXT TIME line. With fewer than two lessons,
print the one or none there is, then the line
`NOTHING NEW — every idea this change depends on was taught; ask "again <slug>" to revisit one.`

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
<slug>, <slug> … (not taught yet; one line) · <also changed: <language> (<n> lines), run with lang:<language>>
```

The header's second half is change-briefing's header line two: the same base, the same
`committed | uncommitted | committed + uncommitted` rule, `, merged <date> as <sha7>` for a
merged change. A lesson's `path:line` and code come from the head's tree.

One lesson, as it should read (match the shape, not the topic):

````
LESSON 1 · cpp/unique_ptr: one owner, freed by itself
src/cache.cpp:12, 41-42
```cpp
void process(std::unique_ptr<Buffer> p) { … }
auto buf = std::make_unique<Buffer>(n);
process(std::move(buf));
```
`unique_ptr` holds a heap value with exactly one owner; the value is freed when the owner
goes out of scope. `std::move` only marks `buf` as giveable: `process`'s by-value parameter
`p` is what takes the value.
```text
before the call           while process() runs
buf ──owns──► [Buffer]    buf ··· (empty)
                          p ──owns──► [Buffer]   freed when process returns
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
- **WORTH A SECOND LOOK** names a risk that a taught idea makes visible in the diff, with
  that lesson's number. With none, write `none found`.
- **Diagrams** go in ```` ```text ```` fences, no line over 70 columns.
- **Count it.** Write it to `diff-lessons-draft.md` in the session scratchpad, overwriting
  the last run's, and run `LC_ALL=en_US.UTF-8 wc -m` on it: at most 7000, and a lesson of at
  most 1500. Over that, cut in this order: each `check:` to five words; NEXT TIME to one
  line; each `≠` to one line; each "what it is" to two lines; wording; then lesson 3, moved
  to NEXT TIME. Every other part stays.

## 4. After it

After printing, append one line per lesson shown to `~/.cache/diff-lessons/<key>.md` with
`>>`, never a rewrite (`mkdir -p` the folder; when the write fails, say so and go on):
`<ISO date> <slug> — <short name> (<repo>:<path>)`. The writes this skill makes are that
line, the scratchpad draft, and change-briefing's one MR fetch.

Then stop and wait. Answer a question in the same way: plain words first, a picture when
there is a flow, `file:line` when it points into the code, a few lines. Give a `check:`
answer only when asked. A rerun on the same change teaches the next ideas; the earlier
lessons come back through `again`.

- `skip <slug>` or `I know <slug>`: append `<ISO date> <slug> — known`.
- `again <slug>`: teach that one idea now in the full lesson shape, appending nothing.

An edit to the code belongs to the workflow that owns the change, not to this skill.
