---
name: react-structure-and-style-guard
description: Dispatches the react-structure-and-style-guard subagent for an advisory review of changed React/TypeScript source — the project-structure (feature-architecture) and code-style residue that ESLint, TypeScript, and Prettier can't catch (naming intent, component/hook design, placement). Run before a commit or PR, or when a commit-review gate asks for it.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.1"
---

# React Structure & Style Guard

Thin dispatcher. The review runs in the **`react-structure-and-style-guard`
subagent** (read-only tools, isolated context) so the checklist and the file
reads never load into this session — you only get the findings back.

## Steps

1. Launch the `react-structure-and-style-guard` subagent (Task/Agent tool,
   `subagent_type: react-structure-and-style-guard`). Tell it which changes to
   review — default: the staged set; if nothing is staged, the diff against the
   merge-base with the default branch. It computes its own diff and reads the
   project's `project_structure.md` / `CLAUDE.md`.
2. Relay its findings to the user verbatim, grouped by file.
3. Findings are **advisory** — address what you agree with. If the project gates
   commits behind this review, clear that gate per its convention once done.

The checklist — the `frontend-react-code-style` and `frontend-react-development`
rules it applies — lives in the subagent definition
(`~/.claude/agents/react-structure-and-style-guard.md`). Edit it there, not here.

The guard deliberately skips what the project's own gates already fail on:
cross-feature imports (`import/no-restricted-paths` or `eslint-plugin-boundaries`),
Rules of Hooks and the effect rules that `eslint-plugin-react-hooks` v7
`recommended` enforces, type errors, and formatting. It reports only the residue
those gates cannot encode.
