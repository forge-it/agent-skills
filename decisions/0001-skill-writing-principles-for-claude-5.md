# ADR 0001: Skill-writing principles for Claude 5 models

- **Status:** Proposed — experimental, NOT yet approved. Approval requires observed behavioral proof from the `python-code-style-v1` live test. Until then, no other skill may be rewritten to this pattern.
- **Date:** 2026-07-29
- **Pilot:** `software-engineering/python-code-style-v1/SKILL.md` (455 → 100 lines rewrite of `python-code-style`, which is disabled via `SKILL.md.disabled` for the duration of the test)

## Context

The existing skills were written for older, less capable models: heavy repetition (the same rule stated in Core Principles, Anti-Patterns, and Guidelines sections), many Bad/Good example pairs, and absolute prohibitions everywhere. Anthropic's context-engineering guidance for the Claude 5 generation reports that this style over-constrains newer models — they removed ~80% of Claude Code's system prompt with no measurable loss — and recommends intent over rules, fewer examples, and progressive disclosure.

Skills in this repo are not standalone documents: guard agents and CI gates cite skill rules by number and severity tag, and Cristian holds some conventions as absolute regardless of model capability. A rewrite pattern must respect that infrastructure.

## Decision

Skills (re-)written for Claude 5 models follow six principles:

1. **Judgment over rules.** State the intent behind a convention instead of an absolute prohibition that is sometimes wrong. Keep hard rules only for deliberate house invariants — and explicitly mark those as deliberate deviations from ecosystem norms, especially the ones a well-trained model will instinctively "correct" (no `-> None`, truthiness instead of `is None`). Where an absolute needs an escape hatch, name the escape hatch instead of softening the rule (e.g. "restructure the modules instead of hiding the import inside the function").
2. **Interfaces over examples.** Bad/Good example pairs constrain the model's exploration space. Prefer expressive rule statements. Budget: at most one compact example per rule, and only where the rule is genuinely ambiguous without it (e.g. which module owns a shared constant; what replaces a helper base class).
3. **Progressive disclosure.** SKILL.md stays lean. Heavy reference material moves to satellite files under `references/`, loaded on demand. A skill small enough after rewriting needs no satellites.
4. **Say it once.** Never state the same rule in multiple sections. Anti-Patterns and Guidelines sections that restate the numbered rules are deleted, after verifying every distinct behavioral requirement they carried is still derivable from the rules (the pilot lost comment minimalism this way and had to restore it as a new rule).
5. **Encode opinions, not the obvious.** Spend tokens on house-specific conventions and gotchas. Delete what a capable model already knows and what tooling already enforces (what type hints are, import-grouping mechanics ruff handles, pathlib API walkthroughs).
6. **Trigger-focused frontmatter description.** The `description` says when to use the skill; it never summarizes the content or workflow. Keep it byte-compatible with the original where the trigger conditions are unchanged.

### Constraints that override the principles

- **Rule numbers, titles, and CRITICAL/HIGH severity tags are stable identifiers** — guard agents and CI gates cite them. Rewrites keep them exactly; new rules are appended at the end, never renumbered. The rewritten skill states this constraint in its own preamble.
- **The naming convention (no single-letter variables, no abbreviations) stays absolute** — it is a personal invariant, not a judgment call.
- **Semantic changes to a rule are the author's decision, not the rewriter's.** A rewrite compresses; it does not change what a rule accepts or rejects without explicit approval (in the pilot: the rule 11 wire-boundary carve-out and pydantic-as-DTO were deferred and approved separately).

### Rewrite workflow

1. Write the rewrite into a parallel `<skill>-v1/` directory; the original stays untouched.
2. Two review rounds, each by a fresh Fable reviewer briefed with these principles and the override constraints; the rewriter applies accepted findings between rounds and defers semantic questions to the author.
3. Disable the original (rename to `SKILL.md.disabled`) so only one variant triggers during the live test.
4. The author evaluates behavior in real work and decides: promote the rewrite, or restore the original and delete it.

## Consequences

- Rewritten skills drop to roughly a quarter of their size, reducing per-task context cost for every Python/Rust/Vue task that loads them.
- The model gains latitude where rules used to be wrongly absolute; house invariants gain explicit "deliberate deviation" protection against being normalized away.
- Review agents keep working unchanged across the migration because rule citations stay stable.
- Until approval, the repo runs mixed-style: one experimental skill, the rest legacy. The README link and any by-name references to a disabled original are broken for the test window.
- If approved, this ADR governs the rewrite of the remaining skills and the "write for less capable models" authoring guidance is retired. If rejected, `python-code-style-v1/` is deleted and the original restored.
