---
name: vue-structure-and-style-guard
description: Dispatches the vue-structure-and-style-guard subagent for an advisory review of changed Vue/TypeScript source — the project-structure (feature-architecture) and code-style residue that ESLint, vue-tsc, and Prettier can't catch (naming, component/composable design, placement). Run before a commit or PR, or when a commit-review gate asks for it.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.3"
---

# Vue Structure & Style Guard

Thin dispatcher. The review runs in the **`vue-structure-and-style-guard`
subagent** (Sonnet 4.6, read-only tools, isolated context) so the checklist and
the file reads never load into this session — you only get the findings back.

## Steps

1. Launch the `vue-structure-and-style-guard` subagent (Task/Agent tool,
   `subagent_type: vue-structure-and-style-guard`). Tell it which changes to
   review — default: the staged set; if nothing is staged, the diff against the
   merge-base with the default branch. It computes its own diff and reads the
   project's `project_structure.md` / `CLAUDE.md`.
2. Relay its findings to the user verbatim, grouped by file.
3. Findings are **advisory** — address what you agree with. If the project gates
   commits behind this review, clear that gate per its convention once done.

The checklist — the `frontend-vue-code-style` and `frontend-vue-development`
rules it applies — lives in the subagent definition
(`~/.claude/agents/vue-structure-and-style-guard.md`). Edit it there, not here.
