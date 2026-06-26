---
name: agent-hooks-setup
description: Use when bootstrapping a new project so the agent is automatically guarded from commit 1 — preventing structural drift, formatting debt, and uncommitted documentation gaps without relying on review to catch them. Also use when a project has accumulated formatting violations, undocumented changes, or repeated structure-and-style findings that could have been caught automatically. Applicable to any project type; the hook templates are language-aware but language-independent in structure.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.1"
---

# Agent Hooks Setup

This is a **one-time setup skill**. It wires three Claude Code `PreToolUse` hooks
and one Git `pre-commit` hook so the agent is guided and guarded automatically —
before any code lands — rather than after review finds a problem.

The principle behind every hook here is **separation of concerns at the commit
boundary**: each hook has exactly one job, fires on exactly one event, and blocks
(or warns) for exactly one class of problem. A single script that checks formatting
*and* docs *and* structure would be harder to bypass selectively and harder to
understand when it fires. One responsibility per script.

The same rules enforced here should mirror what CI enforces (see
`ci-setup`). Hooks are the local, per-commit echo of the CI gate — they catch
violations at the earliest possible moment so the agent does not push a broken
commit.

## When to use

- Bootstrapping a **new project** — install all hooks from scratch; there are no
  existing violations, so every check hard-fails from commit 1.
- Adding hooks to an **existing project** — install the hooks, run them against the
  current tree, fix or acknowledge violations, then commit.

Run this once. After the hooks exist, do not re-run the skill.

## Quick Reference

| Hook | Event | Trigger | Effect |
|------|-------|---------|--------|
| `pretooluse-structure-and-style-guard.sh` | `PreToolUse` (Bash) | `git commit` touching source files | **Blocks** until `rust-structure-and-style-guard` / `vue-structure-and-style-guard` / `python-structure-and-style-guard` is run |
| `pretooluse-cargo-fmt.sh` | `PreToolUse` (Bash) | `git commit` while workspace fails `cargo fmt --all -- --check` | **Blocks** until the workspace is rustfmt-clean |
| `pretooluse-reconcile-docs.sh` | `PreToolUse` (Bash) | `git commit` staging code with no documentation changes | **Blocks** until docs are reconciled or bypassed |
| `pre-commit` | Git `pre-commit` | any `git commit` touching Rust/web files | **Warns** (never blocks) — format reminder + docs reminder |

The three `PreToolUse` hooks are the real guards. The Git `pre-commit` hook is a
warning-only echo for commits made outside Claude Code (e.g. by the developer
directly).

## How Claude Code hooks work

Claude Code hooks intercept tool calls. A `PreToolUse` hook fires just before
Claude executes a tool. It receives the tool's JSON payload on `stdin`; it
controls execution by its exit code:

- `exit 0` — allow the tool call to proceed.
- `exit 2` — **block** the tool call; the hook's `stderr` is fed back to the agent
  as an error message (the agent sees it and must respond).
- Any other exit code — allow the tool call (fail open).

Because these hooks match `"Bash"`, they intercept every Bash call. Each script
reads the tool-call JSON, extracts the `tool_input.command` string, pattern-matches
it against `*"git commit"*`, and exits 0 immediately for anything else. The check
is effectively a no-op on every non-commit Bash call.

## Worktree behaviour

All three `PreToolUse` hooks use `git status --porcelain` (working-tree inspection)
instead of `git diff --cached` (staged-only inspection). This is deliberate: when
Claude runs `git add ... && git commit` as a chained command, the `PreToolUse`
hook fires before the staging step has executed, so `--cached` would always be
empty and the hooks would fail open silently for every chained commit. Working-tree
inspection is correct for both chained and split workflows and works correctly
across git worktrees.

## Step 1 — Create the hook directory

```
tools/
└── hooks/
    ├── pre-commit
    ├── pretooluse-cargo-fmt.sh
    ├── pretooluse-reconcile-docs.sh
    ├── pretooluse-structure-and-style-guard.sh
    └── reconcile-docs-check.sh
```

All scripts must be executable (`chmod +x`).

## Step 2 — Hook scripts

### `tools/hooks/reconcile-docs-check.sh`

Shared helper — detects whether staged changes touch code but no documentation.
Both the Git `pre-commit` hook and the `PreToolUse` hook delegate to this script.
It operates on whatever repository or worktree the current working directory is in.

```bash
#!/bin/env bash

# Exit codes:
#   0  clean   — nothing staged, only docs staged, or docs alongside code.
#   3  tripped — code staged with no doc changes; offending files go to stdout.

function is_doc_path() {
  local STAGED_PATH=${1}

  case "${STAGED_PATH}" in
    docs/* | */docs/*) return 0 ;;
  esac

  case "${STAGED_PATH##*/}" in
    README.md | ROADMAP.md | CHANGELOG.md | CLAUDE.md) return 0 ;;
  esac

  return 1
}

STAGED_FILES=$(git diff --cached --name-only) || exit 0
[ -z "${STAGED_FILES}" ] && exit 0

CODE_FILES=""
DOCS_PRESENT=""

while IFS= read -r STAGED_FILE; do
  [ -z "${STAGED_FILE}" ] && continue
  if is_doc_path "${STAGED_FILE}"; then
    DOCS_PRESENT="yes"
  else
    CODE_FILES="${CODE_FILES}${STAGED_FILE}"$'\n'
  fi
done <<< "${STAGED_FILES}"

[ -z "${CODE_FILES}" ] && exit 0
[ -n "${DOCS_PRESENT}" ] && exit 0

printf '%s' "${CODE_FILES}"
exit 3
```

**What counts as documentation:** any file under a `docs/` directory at any level,
or a file named `README.md`, `ROADMAP.md`, `CHANGELOG.md`, or `CLAUDE.md`. Extend
`is_doc_path()` for additional doc patterns your project uses.

---

### `tools/hooks/pre-commit`

Git `pre-commit` hook — **warning only, never blocks**. Runs for every commit
regardless of who makes it (the developer or the agent). Provides two reminders:

1. A format reminder when Rust or web files are staged.
2. A docs reminder when code is staged with no documentation changes.

```bash
#!/bin/env bash

COLOR_RESET='\033[0m'
YELLOW='\033[0;33m'

HOOK_DIR=$(CDPATH='' cd -- "$(dirname -- "${0}")" && pwd)
CHECK_SCRIPT="${HOOK_DIR}/reconcile-docs-check.sh"

# Format reminder: fires when Rust or web files are staged.
# Adapt the grep pattern to match your project's source layout.
if git diff --cached --name-only | grep -qE '\.rs$|^web/'; then
  {
    printf "\n${YELLOW}⚠  format:${COLOR_RESET} staged Rust/web changes — run the project formatter if you haven't.\n"
    printf "   Not auto-run on commit; warning only — the commit will proceed.\n"
  } >&2
fi

# Docs reminder: delegates to reconcile-docs-check.sh.
[ -x "${CHECK_SCRIPT}" ] || exit 0

CODE_FILES=$("${CHECK_SCRIPT}")
[ ${?} -eq 3 ] || exit 0

{
  printf "\n${YELLOW}⚠  reconcile-docs:${COLOR_RESET} staged code changes with no documentation changes:\n"
  printf '%s\n' "${CODE_FILES}" | sed 's/^/      /'
  printf "   Consider running the reconcile-docs skill.\n"
  printf "   Warning only — the commit will proceed.\n\n"
} >&2

exit 0
```

Install this as `.git/hooks/pre-commit` (or symlink it):

```bash
ln -sf ../../tools/hooks/pre-commit .git/hooks/pre-commit
chmod +x tools/hooks/pre-commit
```

---

### `tools/hooks/pretooluse-structure-and-style-guard.sh`

**Blocks a `git commit` when the change set touches source files that have not
been reviewed** by the appropriate structure-and-style guard skill.

Each language area maps to one skill:

- Rust source (`src/`, `tests/`) → `rust-structure-and-style-guard`
- Vue/TypeScript source (`web/src/`) → `vue-structure-and-style-guard`
- Python source (`src/`, `tests/`) → `python-structure-and-style-guard`

The script below is the generalized template. Adapt the `HAS_RUST`, `HAS_WEB`,
and `HAS_PYTHON` grep patterns to match where your project's source lives.

```bash
#!/bin/env bash

# Claude Code PreToolUse hook (matcher: Bash).
#
# Blocks `git commit` when the change set touches Rust, Vue, or Python source
# without a structure-and-style review. Reads the tool-call JSON from stdin;
# exit code 2 blocks the tool call and feeds stderr back to the agent.
#
# Bypass: prefix the commit with STRUCTURE_STYLE_GUARD_OK=1 once the review is
# done, or when no review is genuinely needed (comment-only change, revert,
# config-only change).

function extract_command() {
  local PAYLOAD=${1}

  if command -v jq > /dev/null 2>&1; then
    printf '%s' "${PAYLOAD}" | jq -r '.tool_input.command // empty' 2> /dev/null
  else
    printf '%s' "${PAYLOAD}"
  fi
}

PAYLOAD=$(cat)
COMMAND=$(extract_command "${PAYLOAD}")
[ -z "${COMMAND}" ] && exit 0

case "${COMMAND}" in
  *"git commit"*) ;;
  *) exit 0 ;;
esac

BYPASS_RE='STRUCTURE_STYLE_GUARD_OK=[^[:space:]]*[[:space:]]+git[[:space:]]+commit'
[[ ${COMMAND} =~ ${BYPASS_RE} ]] && exit 0
[ -n "${STRUCTURE_STYLE_GUARD_OK}" ] && exit 0

command -v git > /dev/null 2>&1 || exit 0

# Working-tree inspection (staged + unstaged + untracked). See skill docblock
# for why --cached is wrong for chained `git add ... && git commit` calls.
ALL_CHANGED=$(git status --porcelain 2>/dev/null | grep -v '^!!' | cut -c4-)
[ -z "${ALL_CHANGED}" ] && exit 0

# Adapt these patterns to your project's source layout.
HAS_RUST=$(printf '%s\n' "${ALL_CHANGED}" | grep -cE '^(src|core|worker)/(src|tests)/')
HAS_WEB=$(printf '%s\n' "${ALL_CHANGED}" | grep -cE '^web/src/')
HAS_PYTHON=$(printf '%s\n' "${ALL_CHANGED}" | grep -cE '\.(py)$')
HAS_RUST_TESTS=$(printf '%s\n' "${ALL_CHANGED}" | grep -cE '^(src|core|worker)/tests/')

[ "${HAS_RUST}" -eq 0 ] && [ "${HAS_WEB}" -eq 0 ] && [ "${HAS_PYTHON}" -eq 0 ] && exit 0

SKILLS=""

if [ "${HAS_RUST}" -gt 0 ]; then
    RUST_DIMS="rust-code-style · project_structure.md"
    if [ "${HAS_RUST_TESTS}" -gt 0 ]; then
        RUST_DIMS="${RUST_DIMS} · rust-testing"
    fi
    SKILLS="${SKILLS}  /rust-structure-and-style-guard  — ${RUST_DIMS}"$'\n'
fi

if [ "${HAS_WEB}" -gt 0 ]; then
    SKILLS="${SKILLS}  /vue-structure-and-style-guard   — frontend-vue-code-style · project_structure.md"$'\n'
fi

if [ "${HAS_PYTHON}" -gt 0 ]; then
    SKILLS="${SKILLS}  /python-structure-and-style-guard — python-code-style · python-ddd · project_structure.md"$'\n'
fi

SOURCE_FILES=$(printf '%s\n' "${ALL_CHANGED}" | grep -E '^(src|core|worker)/(src|tests)/|^web/src/|\.py$' | sed 's/^/  /')

{
  echo "Commit blocked by structure-and-style-guard: the change set touches source that has not been reviewed:"
  echo
  printf '%s\n' "${SOURCE_FILES}"
  echo
  echo "Run the guard skill(s) to review code-style and project_structure.md compliance:"
  printf '%s' "${SKILLS}"
  echo
  echo "Address findings you agree with, then re-commit prefixed with STRUCTURE_STYLE_GUARD_OK=1"
  echo "to bypass this check. Also use STRUCTURE_STYLE_GUARD_OK=1 when no review is genuinely"
  echo "needed (e.g. a comment-only change, a revert, or a change exclusively to generated or"
  echo "config files)."
} >&2

exit 2
```

---

### `tools/hooks/pretooluse-cargo-fmt.sh`

**Blocks a `git commit` while the Rust workspace fails `cargo fmt --all -- --check`**,
so formatting debt never accumulates. Only relevant for Rust projects; omit for
Python-only or Vue-only projects.

```bash
#!/bin/env bash

# Claude Code PreToolUse hook (matcher: Bash).
#
# Blocks `git commit` while the Rust workspace fails `cargo fmt --all -- --check`.
# Reads the tool-call JSON from stdin; exit code 2 blocks the tool call.
#
# The check is workspace-wide and inspects the working tree (not just staged
# files): in a chained `git add ... && git commit`, staging has not happened yet
# when this hook fires, so --cached would be empty and the check would fail open.
#
# Bypass: prefix the commit with CARGO_FMT_OK=1 for the rare commit that must
# land with the tree unformatted (e.g. checkpointing work mid-conflict-resolution).

function extract_command() {
  local PAYLOAD=${1}

  if command -v jq > /dev/null 2>&1; then
    printf '%s' "${PAYLOAD}" | jq -r '.tool_input.command // empty' 2> /dev/null
  else
    printf '%s' "${PAYLOAD}"
  fi
}

PAYLOAD=$(cat)
COMMAND=$(extract_command "${PAYLOAD}")
[ -z "${COMMAND}" ] && exit 0

case "${COMMAND}" in
  *"git commit"*) ;;
  *) exit 0 ;;
esac

BYPASS_RE='CARGO_FMT_OK=[^[:space:]]*[[:space:]]+git[[:space:]]+commit'
[[ ${COMMAND} =~ ${BYPASS_RE} ]] && exit 0
[ -n "${CARGO_FMT_OK}" ] && exit 0

command -v cargo > /dev/null 2>&1 || exit 0

FMT_OUTPUT=$(cargo fmt --all -- --check 2> /dev/null)
[ ${?} -eq 0 ] && exit 0

UNFORMATTED_FILES=$(printf '%s\n' "${FMT_OUTPUT}" | sed -n 's/^Diff in \([^:]*\).*/\1/p' | sort -u)

{
  echo "Commit blocked by cargo-fmt: the Rust workspace is not rustfmt-clean:"
  printf '%s\n' "${UNFORMATTED_FILES}" | sed 's/^/  /'
  echo
  echo "Run \`cargo fmt --all\`, stage the result, then commit again."
  echo "To deliberately commit with an unformatted tree, re-run the commit"
  echo "prefixed with CARGO_FMT_OK=1 to bypass this check."
} >&2

exit 2
```

---

### `tools/hooks/pretooluse-reconcile-docs.sh`

**Blocks a `git commit` that stages code with no documentation changes**, so the
agent reconciles docs before the commit lands. Delegates detection to
`reconcile-docs-check.sh`.

```bash
#!/bin/env bash

# Claude Code PreToolUse hook (matcher: Bash).
#
# Blocks `git commit` that stages code with no documentation changes.
# Reads the tool-call JSON from stdin; exit code 2 blocks the tool call.
#
# Bypass: prefix the commit with RECONCILE_DOCS_OK=1 when no docs are genuinely
# needed (e.g. an internal refactor). This also prevents a block loop once the
# agent has consciously decided no docs are warranted.

function extract_command() {
  local PAYLOAD=${1}

  if command -v jq > /dev/null 2>&1; then
    printf '%s' "${PAYLOAD}" | jq -r '.tool_input.command // empty' 2> /dev/null
  else
    printf '%s' "${PAYLOAD}"
  fi
}

PAYLOAD=$(cat)
COMMAND=$(extract_command "${PAYLOAD}")
[ -z "${COMMAND}" ] && exit 0

case "${COMMAND}" in
  *"git commit"*) ;;
  *) exit 0 ;;
esac

BYPASS_RE='RECONCILE_DOCS_OK=[^[:space:]]*[[:space:]]+git[[:space:]]+commit'
[[ ${COMMAND} =~ ${BYPASS_RE} ]] && exit 0
[ -n "${RECONCILE_DOCS_OK}" ] && exit 0

HOOK_DIR=$(CDPATH='' cd -- "$(dirname -- "${0}")" && pwd)
CHECK_SCRIPT="${HOOK_DIR}/reconcile-docs-check.sh"
[ -x "${CHECK_SCRIPT}" ] || exit 0

CODE_FILES=$("${CHECK_SCRIPT}")
[ ${?} -eq 3 ] || exit 0

{
  echo "Commit blocked by reconcile-docs: the staged change set touches code but no documentation:"
  printf '%s\n' "${CODE_FILES}" | sed 's/^/  /'
  echo
  echo "Run the reconcile-docs skill to update any warranted docs (ADRs, API references,"
  echo "READMEs, ROADMAP, gaps/), then commit again."
  echo "If no docs are genuinely needed (e.g. an internal refactor), re-run the commit"
  echo "prefixed with RECONCILE_DOCS_OK=1 to bypass this check."
} >&2

exit 2
```

## Step 3 — Register the hooks in `.claude/settings.json`

Create or update `.claude/settings.json` at the project root:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/tools/hooks/pretooluse-reconcile-docs.sh",
            "timeout": 10,
            "statusMessage": "reconcile-docs: checking staged docs vs code"
          },
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/tools/hooks/pretooluse-cargo-fmt.sh",
            "timeout": 60,
            "statusMessage": "cargo-fmt: checking workspace formatting"
          },
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/tools/hooks/pretooluse-structure-and-style-guard.sh",
            "timeout": 10,
            "statusMessage": "structure-and-style-guard: checking touched source areas"
          }
        ]
      }
    ]
  }
}
```

Key points:

- `$CLAUDE_PROJECT_DIR` is set by Claude Code to the project root; use it instead
  of relative paths or `$(pwd)` so the hook resolves correctly regardless of the
  working directory when the agent runs.
- The `timeout` value for `pretooluse-cargo-fmt.sh` is 60 seconds — `cargo fmt`
  on a large workspace can be slow. Set `timeout` conservatively; a timed-out hook
  fails open (exit 0 equivalent).
- Omit `pretooluse-cargo-fmt.sh` entirely for non-Rust projects.
- All three hooks have independent matchers and responsibilities — do not merge them.

## Step 4 — Install the Git pre-commit hook

```bash
ln -sf ../../tools/hooks/pre-commit .git/hooks/pre-commit
chmod +x tools/hooks/pre-commit
```

The Git hook warns the developer when committing outside Claude Code. It shares
`reconcile-docs-check.sh` with the `PreToolUse` hook, so the detection logic stays
in one place.

## Step 5 — Verify each hook fires

### Verify structure-and-style-guard

Make a trivial source change without running the guard, then attempt a commit:

```bash
# Touch any source file
echo "// probe" >> src/main.rs
# Try to commit — expect a block
git add src/main.rs && git commit -m "probe"
# Expected: "Commit blocked by structure-and-style-guard: ..."
# Clean up
git checkout src/main.rs
```

Run the appropriate guard skill (e.g. `/rust-structure-and-style-guard`), address
any findings, then commit with the bypass:

```bash
STRUCTURE_STYLE_GUARD_OK=1 git commit -m "your message"
```

### Verify cargo-fmt (Rust only)

```bash
# Introduce a formatting violation
printf '\nfn badly_formatted()   {}\n' >> src/main.rs
git add src/main.rs && git commit -m "probe"
# Expected: "Commit blocked by cargo-fmt: ..."
# Fix it
cargo fmt --all
git add src/main.rs && git commit -m "your message"
```

### Verify reconcile-docs

```bash
# Stage a code file with no docs
echo "// probe" >> src/main.rs
git add src/main.rs && git commit -m "probe"
# Expected: "Commit blocked by reconcile-docs: ..."
# Either add a doc change, or bypass
RECONCILE_DOCS_OK=1 git commit -m "refactor: internal only"
```

Do not trust a green result you have not seen fail.

## Bypass tokens

Each blocking hook accepts a bypass environment variable that must be placed
**immediately before** `git commit` in the command string. The regex requires the
token to directly precede `git commit`, so a token that only appears inside the
commit message is correctly rejected.

| Hook | Bypass token | When to use |
|------|--------------|-------------|
| structure-and-style-guard | `STRUCTURE_STYLE_GUARD_OK=1` | After the guard skill has run and findings are addressed; or for comment-only changes, reverts, config-only changes |
| cargo-fmt | `CARGO_FMT_OK=1` | When deliberately committing with an unformatted tree (e.g. mid-conflict-resolution checkpoint) |
| reconcile-docs | `RECONCILE_DOCS_OK=1` | Internal refactors where no docs are genuinely warranted |

Example:

```bash
STRUCTURE_STYLE_GUARD_OK=1 git commit -m "fix: address guard findings"
```

The bypass also prevents a block loop: once the agent has consciously run the
guard skill and decided no further action is needed, it can proceed.

## Customization knobs

### Source area patterns

The `HAS_RUST`, `HAS_WEB`, and `HAS_PYTHON` patterns in
`pretooluse-structure-and-style-guard.sh` are the only project-specific part. Adapt
them to your layout:

| Project type | Example pattern |
|---|---|
| Rust single-crate | `'^src/'` |
| Rust workspace with named crates | `'^(core\|worker\|api)/'` |
| Vue frontend in `web/` | `'^web/src/'` |
| Python flat layout | `'\\.py$'` |
| Python `src/` layout | `'^src/.*\\.py$'` |

### Documentation file recognition

Extend `is_doc_path()` in `reconcile-docs-check.sh` for any project-specific doc
patterns (e.g. `openapi.yaml`, `architecture/`, wiki files):

```bash
case "${STAGED_PATH}" in
  docs/* | */docs/* | architecture/*) return 0 ;;
esac

case "${STAGED_PATH##*/}" in
  README.md | ROADMAP.md | CHANGELOG.md | CLAUDE.md | openapi.yaml) return 0 ;;
esac
```

### Formatter hook for non-Rust projects

The `pretooluse-cargo-fmt.sh` template uses `cargo fmt`. For Python, replace the
body with `ruff format --check`; for Vue/TypeScript, with `prettier --check`.
Keep the same structure: read stdin, extract command, match `*"git commit"*`,
check the formatter, block on failure, bypass with a project-specific token.

## Common Mistakes / Anti-Patterns

| Mistake | Why it is wrong | Fix |
|---------|-----------------|-----|
| Using `git diff --cached` instead of `git status --porcelain` in the guard hook | `--cached` is empty when the hook fires before staging in a chained `git add && git commit` — the hook silently fails open | Use `git status --porcelain` to inspect the working tree |
| Merging all checks into one script | Violates single responsibility — harder to bypass selectively, harder to extend, harder to diagnose | One script per concern |
| Using relative paths in `settings.json` commands | Breaks when Claude Code's working directory differs from the project root | Use `$CLAUDE_PROJECT_DIR/...` |
| A too-short `timeout` for `cargo fmt` | Claude Code kills the hook process and fails open; the check never runs | Give `cargo fmt` at least 60 seconds |
| Not testing that the hook actually blocks | A hook that exits 0 unconditionally looks correct but guards nothing | Always verify with a deliberate violation before trusting a green result |
| Applying these hooks without a corresponding CI gate | Hooks are bypassable and local-only; they do not replace CI | Add the same checks to CI (see `ci-setup`) |
| Forgetting to `chmod +x` the scripts | The hook silently fails open (non-executable scripts exit non-zero in a way Claude Code treats as pass-through) | `chmod +x tools/hooks/*.sh tools/hooks/pre-commit` |
| Setting `STRUCTURE_STYLE_GUARD_OK=1` as a persistent environment variable in the shell profile | Every subsequent commit bypasses the guard silently — the hook checks `[ -n "${STRUCTURE_STYLE_GUARD_OK}" ]` and exits 0 | Use the bypass only inline, immediately before `git commit` |

## How the guard skill dispatch works

The `pretooluse-structure-and-style-guard.sh` hook does not run the review itself.
It blocks the commit and names the skill to run. The agent then:

1. Runs the named skill — e.g. `/rust-structure-and-style-guard`, which dispatches
   the `rust-structure-and-style-guard` subagent. That subagent reads the diff,
   applies the `rust-code-style` and `rust-project-structure` rules, and returns
   findings.
2. Addresses the findings (or consciously decides they are not applicable).
3. Re-commits with `STRUCTURE_STYLE_GUARD_OK=1` to bypass the now-satisfied guard.

This separation of concerns is intentional: the hook detects *that* a review is
needed; the skill performs the review; the agent decides what to do with the
findings. No single script conflates detection, review, and decision.

The skills dispatched are:

- `rust-structure-and-style-guard` — Rust source (code-style + project structure +
  test layout residue that rustfmt/clippy cannot catch)
- `vue-structure-and-style-guard` — Vue/TypeScript source (feature-architecture +
  component/composable design residue that ESLint/Prettier cannot catch)
- `python-structure-and-style-guard` — Python source (DDD layering + domain-model
  shape + UoW usage residue that ruff/mypy/import-linter cannot catch)
