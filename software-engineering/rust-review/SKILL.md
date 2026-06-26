---
name: rust-review
description: Dispatches the rust-reviewer subagent for an advisory pre-commit review of changed Rust source (core/ or worker/) — judgment-residue code-style and project-structure issues that clippy, rustfmt, and the tests/structure gate cannot catch. Run after the architecture-review hook blocks a commit, or proactively before opening a PR.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.2"
---

# Rust Review

Thin dispatcher. The review itself runs in the **`rust-reviewer` subagent** (Sonnet 4.6, read-only tools, isolated context) so the checklist and the file reads never load into this session — you only get the findings back.

## Steps

1. Launch the `rust-reviewer` subagent (Task/Agent tool, `subagent_type: rust-reviewer`). Tell it which changes to review — default: the staged set; if nothing is staged, the diff against the merge-base with the default branch. It computes its own diff and reads what it needs.
2. Relay its findings to the user verbatim, grouped by file.
3. Remind the user: findings are **advisory** — address what you agree with, then re-commit prefixed with `ARCH_REVIEW_OK=1` to clear the architecture-review hook.

All review logic — the `rust-code-style` R-rules, the project-structure placement checks, the `rust-testing` checks — lives in the `rust-reviewer` agent definition (`~/.claude/agents/rust-reviewer.md`). Edit it there, not here.
