---
name: python-structure-and-style-guard
description: Dispatches the python-structure-and-style-guard subagent for an advisory review of changed Python source — the project-structure (DDD layering) and code-style residue that ruff, mypy, and import-linter can't catch (domain-model shape, repository naming, UoW usage, router thinness, placement). Run before a commit or PR, or when a commit-review gate asks for it.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.1"
---

# Python Structure & Style Guard

Thin dispatcher. The review runs in the **`python-structure-and-style-guard`
subagent** (Sonnet 4.6, read-only tools, isolated context) so the checklist and
the file reads never load into this session — you only get the findings back.

## Steps

1. Launch the `python-structure-and-style-guard` subagent (Task/Agent tool,
   `subagent_type: python-structure-and-style-guard`). Tell it which changes to
   review — default: the staged set; if nothing is staged, the diff against the
   merge-base with the default branch. It computes its own diff and reads the
   project's `project_structure.md` / `CLAUDE.md`.
2. Relay its findings to the user verbatim, grouped by file.
3. Findings are **advisory** — address what you agree with. If the project gates
   commits behind this review, clear that gate per its convention once done.

The checklist — the `python-code-style` and `python-ddd` rules it applies —
lives in the subagent definition
(`~/.claude/agents/python-structure-and-style-guard.md`). Edit it there, not
here.
