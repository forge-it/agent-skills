---
name: dependency-audit-pattern
description: >-
  Use when a polyglot repository (Rust, Python, Vue/Node, or any combination)
  needs a repeatable, cross-stack vulnerability scan available from day one —
  and especially when any of these symptoms appear: a CVE surfaces in a
  dependency that was never checked, security audits run inconsistently across
  ecosystems, an agent or CI job has no canonical command to invoke, or a
  greenfield repo ships its first commit without audit tooling in place.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.1"
---

# Dependency Audit Pattern

## Purpose

A polyglot repository usually has three separate dependency ecosystems — Rust
(Cargo), Python (pip / uv), and Vue/Node (npm / pnpm) — each with its own
vulnerability database and audit CLI. Without a single, named entry point that
covers all three, teams end up auditing only the ecosystem they happen to be
working in at the time, leaving the others dark.

**In one line:** the dependency-audit pattern gives a repository a named
slash-command that walks every ecosystem in turn, runs the appropriate audit
tool, reports findings together, and can be wired into CI as a periodic or
pre-merge blocking gate.

> **Core principle (separation of concerns / single responsibility):** each
> ecosystem has exactly one audit tool and one set of remediation steps. The
> pattern keeps those separate — one section per stack — rather than blending
> them into a single opaque script. The slash-command is the entry point that
> composes them; the per-stack tools are the workers.

## When to Apply

- A new monorepo is being bootstrapped and needs security hygiene from commit
  one.
- A project already runs `cargo audit` or `npm audit` in one place but not
  across all stacks.
- A CI job needs a canonical, human-readable command to invoke rather than
  inline shell.
- A project uses `agent-hooks-setup` and wants the audit reachable as a
  Claude Code slash-command.
- The security posture review for a release cycle requires a reproducible audit
  report covering all dependencies.

**When NOT to use:** a single-stack project (e.g. a pure Rust library with no
frontend and no Python code) does not need the multi-stack wrapper — just run
`cargo audit` directly. The pattern earns its keep in polyglot repos where
omitting one ecosystem is the failure mode.

## File Location Convention

Place the command file at:

```
.claude/commands/<name>.md
```

The filename becomes the slash-command name in Claude Code. For the audit
command the canonical name is `dependency-audit`, giving the slash-command
`/dependency-audit`. The file is plain Markdown — Claude Code reads it as
the prompt body when the command is invoked.

There are no required imports or declarations inside the file; the content is
the instruction set for the agent. Keep each ecosystem in its own numbered
section so the agent works through them sequentially and reports per section.

## Cross-Stack Tooling Table

| Ecosystem | Audit tool | Safe auto-fix | Notes |
|---|---|---|---|
| Rust (Cargo) | `cargo audit` | `cargo update` (patch) | `cargo deny` adds policy-level rules (license gates, banned crates); run after `cargo audit` |
| Python (pip) | `pip-audit` | `pip install -U <pkg>` | For `uv`-managed projects use `uv run pip-audit` or `uv pip install -U` |
| Python (uv) | `uv run pip-audit` | `uv add <pkg>@latest` | `pip-audit` reads the virtualenv; `uv` manages the lock |
| Vue / Node (npm) | `npm audit` | `npm audit fix` | Never use `--force` without explicit confirmation — it allows breaking major bumps |
| Vue / Node (pnpm) | `pnpm audit` | `pnpm update --latest <pkg>` | `pnpm audit fix` is available from pnpm 8+ |

After auto-fix in any ecosystem: run the full test suite and confirm it passes
before treating the vulnerability as resolved.

## Recommended Cadence

| Trigger | Blocking? | Notes |
|---|---|---|
| On demand (`/dependency-audit`) | No | Developer-initiated; produces a report for review |
| Scheduled CI job (weekly or monthly) | No (report only) | Opens a ticket / notifies the team if findings exist |
| Pre-merge CI gate | Yes (configurable) | Block on High/Critical severity; warn on Medium |

Wire the scheduled and pre-merge runs through the `ci-setup` skill so the jobs
are added to the same CI configuration that governs the architecture and lint
gates. Reference `agent-hooks-setup` if you want the slash-command reachable
from Claude Code hooks (e.g. a post-commit hook that reminds the agent to audit
after dependency changes).

## Worked Example — ironbox `.claude/commands/dependency-audit.md`

The ironbox repository is a Rust + Vue monorepo with two Rust workspace members
(`core/`, `worker/`) and a Node frontend (`web/`). Its command file
(`.claude/commands/dependency-audit.md`) contains:

---

**Goal:** find and remediate vulnerable dependencies across the repository, then
confirm the updates did not break anything.

**Rust** (run from `core/`, then `worker/`):

1. Run `cargo audit` to list vulnerable dependencies.
2. For each vulnerability, update the affected package to a patched version.
3. Run the full test suite (`just dev-core-test`, then `just dev-worker-test`)
   and confirm it passes.
4. Summarize what changed; call out any vulnerabilities that remain (no fix
   available, or a fix requiring a breaking upgrade); report any test failures
   introduced by the updates — for each: the test, the cause, and whether it
   needs a code fix.

**Web frontend** (run from `web/`):

1. Run `npm audit` to list vulnerable dependencies.
2. Run `npm audit fix` to update packages within their semver ranges. Do not
   use `npm audit fix --force` unless explicitly confirmed.
3. Run the full test suite (`just dev-web-test`) and confirm it passes.
4. Summarize what changed; call out remaining vulnerabilities; report test
   failures introduced.

When done, report the overall result and flag anything that needs a decision
before proceeding.

---

Key observations from this example:

- **Python is absent** — ironbox has no Python component, so the command omits
  that section. A project with Python would add a third section following the
  same shape.
- **`just` tasks are the test entry points**, not raw `cargo test` or
  `npm test`. This aligns with the project's `justfile` conventions (see the
  `justfile-setup` skill).
- **`--force` is explicitly guarded.** The command names the flag and requires
  confirmation before using it, which prevents the agent from silently applying
  breaking major-version upgrades.
- **Each section ends with a structured report request** (what changed, what
  remains, what broke) so the agent's output is auditable, not just a pass/fail.

## Generalising the Command to Three Stacks

For a full Rust + Python + Vue repo, the command file would have three sections
in this order:

```markdown
## Rust (run from `<rust-workspace-root>/`)

1. Run `cargo audit` to list vulnerable dependencies.
2. For each vulnerability, update the affected package to a patched version.
   Use `cargo deny check` to verify policy compliance after updating.
3. Run the full test suite and confirm it passes.
4. Summarize changes; flag unresolved vulnerabilities; report test failures.

## Python (run from `<python-root>/`)

1. Run `pip-audit` (or `uv run pip-audit`) to list vulnerable dependencies.
2. For each vulnerability, update the affected package with `pip install -U`
   (or `uv add <pkg>@latest`).
3. Run the full test suite and confirm it passes.
4. Summarize changes; flag unresolved vulnerabilities; report test failures.

## Web frontend (run from `<node-root>/`)

1. Run `npm audit` (or `pnpm audit`) to list vulnerable dependencies.
2. Run `npm audit fix` (or `pnpm update`) within semver ranges.
   Do not use `--force` unless explicitly confirmed.
3. Run the full test suite and confirm it passes.
4. Summarize changes; flag unresolved vulnerabilities; report test failures.

When done, report the overall result and flag anything that needs a decision.
```

Substitute the actual workspace paths and test commands for the project. Keep
one section per ecosystem; do not merge them.

## Quick Reference — Invariants

- **One `.claude/commands/dependency-audit.md` file** in the repository root
  provides the canonical entry point. Any developer or CI agent invokes it the
  same way.
- **One section per ecosystem** — never merge Rust, Python, and Node audits
  into a single shell script block. Each has its own tool, its own fix command,
  and its own test gate.
- **Always run tests after updating.** A patched dependency version can
  introduce a breaking change at the API or behaviour level that audit tools
  do not detect.
- **Always report what was not fixed.** Unresolved vulnerabilities (no patch
  available, or a patch behind a breaking upgrade) need a human decision. The
  command forces the agent to surface them explicitly.
- **Guard `--force` / major-version bumps explicitly.** Name the flag in the
  command and require confirmation. Auto-applied breaking upgrades produce
  silent failures.
- **Wire into CI via `ci-setup`.** On-demand slash-command usage alone is not
  sufficient; a scheduled or pre-merge job catches drift that developers don't
  notice locally.

## Anti-Patterns to Avoid

- **Auditing only one ecosystem in a polyglot repo.** If the Rust audit runs in
  CI but the npm audit does not, the Node surface area is permanently dark. The
  pattern's value is full coverage.
- **Running `npm audit fix --force` by default.** Major-version bumps can
  silently break builds or change behaviour. The command must name the flag and
  require a confirmation step.
- **Reporting findings without running tests.** A "no vulnerabilities" report
  after updating is meaningless if the update broke a feature. The test gate is
  part of the audit, not a separate step.
- **Omitting the "what remains" report.** Vulnerabilities with no available fix
  are easy to silently skip. Requiring the agent to enumerate them creates an
  auditable record and triggers a human decision.
- **Treating a passing scan as a one-time event.** New CVEs are published daily.
  A scan that passed last month may fail this week. The cadence section (on
  demand + scheduled CI + pre-merge gate) closes this gap.
- **Placing the command outside `.claude/commands/`.** Claude Code only
  discovers slash-commands from that directory. A script elsewhere is not
  invocable as `/dependency-audit`.

## Relationship to Other Skills

- **`ci-setup`** — wire the audit as a scheduled or pre-merge CI job so it runs
  automatically, not just when a developer remembers to invoke it. The
  `ci-setup` skill adds the job to the same CI configuration that governs
  architecture and lint gates.
- **`agent-hooks-setup`** — if the project uses Claude Code hooks, a
  post-dependency-update hook can invoke `/dependency-audit` automatically after
  a `Cargo.toml`, `pyproject.toml`, or `package.json` change lands.
- **`justfile-setup`** — the ironbox example delegates test execution to `just`
  tasks. If the project uses a justfile, the audit command should reference
  those tasks (e.g. `just dev-core-test`) rather than raw tool invocations, so
  the test entry points stay consistent between local and CI usage.
