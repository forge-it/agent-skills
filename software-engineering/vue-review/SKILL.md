---
name: vue-review
description: Dispatches the vue-reviewer subagent for an advisory pre-commit review of changed Vue/TypeScript source (web/src/) — judgment-residue code-style and feature-architecture issues that ESLint, vue-tsc, and Prettier cannot catch. Run after the architecture-review hook blocks a commit, or proactively before opening a PR.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.2"
---

# Vue Review

Thin dispatcher. The review itself runs in the **`vue-reviewer` subagent** (Sonnet 4.6, read-only tools, isolated context) so the checklist and the file reads never load into this session — you only get the findings back.

## Steps

1. Launch the `vue-reviewer` subagent (Task/Agent tool, `subagent_type: vue-reviewer`). Tell it which changes to review — default: the staged set; if nothing is staged, the diff against the merge-base with the default branch. It computes its own diff and reads what it needs.
2. Relay its findings to the user verbatim, grouped by file.
3. Remind the user: findings are **advisory** — address what you agree with, then re-commit prefixed with `ARCH_REVIEW_OK=1` to clear the architecture-review hook.

All review logic — the `frontend-vue-code-style` patterns and the feature-architecture placement checks — lives in the `vue-reviewer` agent definition (`~/.claude/agents/vue-reviewer.md`). Edit it there, not here.
