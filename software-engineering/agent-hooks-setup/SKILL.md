---
name: agent-hooks-setup
description: Use when bootstrapping a new project so the agent is automatically guarded from commit 1 — preventing structural drift, formatting debt, and uncommitted documentation gaps without relying on review to catch them. Also use when a project has accumulated formatting violations, undocumented changes, or repeated structure-and-style findings that could have been caught automatically.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.3"
---

# Agent Hooks Setup

This is a **one-time setup skill**. It wires three Claude Code `PreToolUse` hooks
and one Git `pre-commit` hook so the agent is guided and guarded automatically —
before any code lands — rather than after review finds a problem.

The principle behind every hook here is **separation of concerns at the commit
boundary**: each hook has exactly one job, fires on exactly one event, and blocks
(or warns) for exactly one class of problem. A single script that checks formatting
*and* docs *and* structure would be harder to bypass selectively and harder to
understand when it fires. One responsibility per script. The plumbing the scripts
share — reading the payload, recognizing a commit, honouring a bypass — lives in
one sourced helper, so a fix to it lands once instead of drifting three ways.

The same rules enforced here should mirror what CI enforces (see `ci-setup`).
Hooks are the local, per-commit echo of the CI gate — they catch violations at
the earliest possible moment so the agent does not push a broken commit. They
are bypassable and local-only; they do not replace the CI gate.

## When to use

- Bootstrapping a **new project** — install all hooks from scratch; there are no
  existing violations, so every check hard-fails from commit 1.
- Adding hooks to an **existing project** — install the hooks, run them against the
  current tree, fix or acknowledge violations, then commit.

Run this once. After the hooks exist, do not re-run the skill.

## Quick Reference

| Hook | Event | Trigger | Effect |
|------|-------|---------|--------|
| `pretooluse-structure-and-style-guard.sh` | `PreToolUse` (Bash) | `git commit` while the working tree holds unreviewed source changes | **Blocks** until the matching `{rust,vue,react,python}-structure-and-style-guard` has run |
| `pretooluse-cargo-fmt.sh` | `PreToolUse` (Bash) | `git commit` while the workspace fails `cargo fmt --all -- --check` | **Blocks** until the workspace is rustfmt-clean |
| `pretooluse-reconcile-docs.sh` | `PreToolUse` (Bash) | `git commit` while the working tree changes code but no documentation | **Blocks** until docs are reconciled or bypassed |
| `pre-commit` | Git `pre-commit` | any `git commit` touching Rust/web files | **Warns** (never blocks) — format reminder + docs reminder |

The three `PreToolUse` hooks are the real guards. The Git `pre-commit` hook is a
warning-only echo for commits made outside Claude Code (e.g. by the developer
directly).

## How the hooks decide

A `PreToolUse` hook fires just before Claude executes a tool. It receives the
tool-call JSON on `stdin` — the Bash command is `.tool_input.command`, the
session's working directory is `.cwd` — and answers with its exit code:

- `exit 0` — the call continues through the normal permission flow.
- `exit 2` — **block** the call; the hook's `stderr` is fed back to the agent,
  which must respond to it.
- Any other exit code, or a hook that exceeds its `timeout` — the call proceeds
  (fail open). A non-executable script fails open the same way.

A hook may instead print a JSON object whose `hookSpecificOutput.permissionDecision`
is `allow`, `deny`, or `ask`. The templates use exit 2 because it is simpler in
bash and already feeds the message to the agent; reach for the JSON form when a
hook should ask rather than block.

Three decisions shape every script below.

**Match the commit inside the script.** The hooks are registered on the `Bash`
matcher, so they see every Bash call. Each script pattern-matches
`*"git commit"*` and exits 0 for anything else, which makes it a no-op on every
non-commit call.

**Inspect the working tree, not the index.** When the agent runs
`git add … && git commit` as one command, the hook fires before `git add` has
executed, so `git diff --cached` is empty and a staged-only check fails open on
exactly the commits the agent makes most. The `PreToolUse` hooks therefore read
`git status --porcelain` (staged + unstaged + untracked). The trade-off is
over-blocking: a docs-only commit is blocked while unrelated source sits dirty
in the tree. Accept it — the bypass tokens exist for that case. Only the Git
`pre-commit` hook, which runs after staging, reads the index.

**Move into the session's directory first.** Inside a git worktree,
`$CLAUDE_PROJECT_DIR` still names the main checkout; the worktree the commit
targets is the payload's `.cwd`. The shared helper changes into it before any
git command runs.

## Step 1 — Create the hook directory

```
tools/
└── hooks/
    ├── pre-commit
    ├── pretooluse-common.sh
    ├── pretooluse-cargo-fmt.sh
    ├── pretooluse-reconcile-docs.sh
    ├── pretooluse-structure-and-style-guard.sh
    └── reconcile-docs-check.sh
```

All scripts must be executable: `chmod +x tools/hooks/*`.

## Step 2 — Hook scripts

### `tools/hooks/pretooluse-common.sh`

Sourced by the three `PreToolUse` hooks; never registered or run on its own.

```bash
#!/usr/bin/env bash

# Shared preamble for the PreToolUse hooks. Source it; do not run it.
#
#   require_git_commit_command  reads the tool-call JSON from stdin, sets
#                               COMMAND, moves into the session's cwd (the
#                               worktree the commit targets), and exits 0 —
#                               allow — when the call is not a git commit.
#   bypassed TOKEN_NAME         succeeds when TOKEN_NAME=value sits at command
#                               position before `git commit`, alone or among
#                               other NAME=value assignments, or is exported in
#                               the hook's own environment.

function payload_field() {
  local PAYLOAD=${1}
  local FIELD=${2}

  command -v jq > /dev/null 2>&1 || return 1
  printf '%s' "${PAYLOAD}" | jq -r "${FIELD} // empty" 2> /dev/null
}

function require_git_commit_command() {
  local PAYLOAD
  PAYLOAD=$(cat)

  # Without jq, match against the raw payload; the substring test still works.
  COMMAND=$(payload_field "${PAYLOAD}" '.tool_input.command') || COMMAND=${PAYLOAD}
  [ -z "${COMMAND}" ] && exit 0

  case "${COMMAND}" in
    *"git commit"*) ;;
    *) exit 0 ;;
  esac

  local SESSION_CWD
  SESSION_CWD=$(payload_field "${PAYLOAD}" '.cwd')
  if [ -n "${SESSION_CWD}" ] && [ -d "${SESSION_CWD}" ]; then
    cd "${SESSION_CWD}" || exit 0
  fi

  command -v git > /dev/null 2>&1 || exit 0
}

function bypassed() {
  local TOKEN_NAME=${1}
  local BYPASS_RE="${TOKEN_NAME}=[^[:space:]]+([[:space:]]+[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]+)*[[:space:]]+git[[:space:]]+commit"

  [[ ${COMMAND} =~ ${BYPASS_RE} ]] && return 0
  [ -n "${!TOKEN_NAME}" ] && return 0
  return 1
}
```

---

### `tools/hooks/reconcile-docs-check.sh`

Shared detector — a change set that touches code but no documentation. The Git
`pre-commit` hook calls it with `--staged`; the `PreToolUse` hook with
`--working-tree`.

```bash
#!/usr/bin/env bash

# Detects a change set that touches code but no documentation.
#
# Usage: reconcile-docs-check.sh [--staged | --working-tree]
#   --staged        the index (default) — for the Git pre-commit hook, which
#                   runs after staging.
#   --working-tree  staged + unstaged + untracked — for the PreToolUse hook,
#                   which fires before a chained `git add … && git commit`
#                   has staged anything.
#
# Exit codes:
#   0  clean   — nothing changed, only docs, or docs alongside code.
#   3  tripped — code with no doc changes; the offending files go to stdout.

function is_doc_path() {
  local CHANGED_PATH=${1}

  case "${CHANGED_PATH}" in
    docs/* | */docs/*) return 0 ;;
  esac

  case "${CHANGED_PATH##*/}" in
    README.md | ROADMAP.md | CHANGELOG.md | CLAUDE.md) return 0 ;;
  esac

  return 1
}

case "${1:---staged}" in
  --staged) CHANGED_FILES=$(git diff --cached --name-only 2> /dev/null) || exit 0 ;;
  --working-tree) CHANGED_FILES=$(git status --porcelain --untracked-files=all 2> /dev/null | grep -v '^!!' | cut -c4-) || exit 0 ;;
  *) echo "usage: ${0##*/} [--staged | --working-tree]" >&2; exit 0 ;;
esac
[ -z "${CHANGED_FILES}" ] && exit 0

CODE_FILES=""
DOCS_PRESENT=""

while IFS= read -r CHANGED_FILE; do
  [ -z "${CHANGED_FILE}" ] && continue
  if is_doc_path "${CHANGED_FILE}"; then
    DOCS_PRESENT="yes"
  else
    CODE_FILES="${CODE_FILES}${CHANGED_FILE}"$'\n'
  fi
done <<< "${CHANGED_FILES}"

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
regardless of who makes it: a format reminder when Rust or web files are staged,
and a docs reminder when code is staged with no documentation changes.

```bash
#!/usr/bin/env bash

# Git pre-commit hook — warning only, never blocks. A format reminder when Rust
# or web files are staged, and a docs reminder when code is staged with no
# documentation changes. Detection lives in reconcile-docs-check.sh.

COLOR_RESET='\033[0m'
YELLOW='\033[0;33m'

HOOK_DIR=$(CDPATH='' cd -- "$(dirname -- "${0}")" && pwd)
CHECK_SCRIPT="${HOOK_DIR}/reconcile-docs-check.sh"

# Adapt the pattern to your project's source layout.
if git diff --cached --name-only | grep -qE '\.rs$|^web/'; then
  {
    printf "\n${YELLOW}⚠  format:${COLOR_RESET} staged Rust/web changes — run the project formatter if you haven't.\n"
    printf "   Not auto-run on commit; warning only — the commit will proceed.\n"
  } >&2
fi

[ -x "${CHECK_SCRIPT}" ] || exit 0

CODE_FILES=$("${CHECK_SCRIPT}" --staged)
[ ${?} -eq 3 ] || exit 0

{
  printf "\n${YELLOW}⚠  reconcile-docs:${COLOR_RESET} staged code changes with no documentation changes:\n"
  printf '%s\n' "${CODE_FILES}" | sed 's/^/      /'
  printf "   Consider running the reconcile-docs skill.\n"
  printf "   Warning only — the commit will proceed.\n\n"
} >&2

exit 0
```

---

### `tools/hooks/pretooluse-structure-and-style-guard.sh`

**Blocks a `git commit` while the working tree holds source that has not been
reviewed** by the structure-and-style guard for its language. The hook does not
run the review: it detects *that* a review is needed and names the skill; the
skill dispatches the guard subagent, which returns findings; the agent addresses
them, or decides they do not apply, and re-commits with the bypass token.
Detection, review, and decision stay in three places.

| Source area | Guard skill | Residue it catches |
|---|---|---|
| Rust (`.rs` anywhere) | `rust-structure-and-style-guard` | rust-code-style, rust-project-structure, rust-testing — what rustfmt and clippy cannot see |
| Vue (`web/src/`) | `vue-structure-and-style-guard` | frontend-vue-code-style, frontend-vue-development — what ESLint, vue-tsc and Prettier cannot see |
| React (`web/src/`) | `react-structure-and-style-guard` | frontend-react-code-style, frontend-react-development — what ESLint, TypeScript and Prettier cannot see |
| Python (`.py` anywhere) | `python-structure-and-style-guard` | python-code-style, python-ddd — what ruff, basedpyright and import-linter cannot see |

The knobs at the top of the script — the source patterns and `WEB_FRAMEWORK` —
are the only project-specific part.

```bash
#!/usr/bin/env bash

# Claude Code PreToolUse hook (matcher: Bash). Blocks `git commit` while the
# working tree holds source that has not had a structure-and-style review.
# Bypass: STRUCTURE_STYLE_GUARD_OK=1 at command position before `git commit`.

HOOK_DIR=$(CDPATH='' cd -- "$(dirname -- "${0}")" && pwd)
source "${HOOK_DIR}/pretooluse-common.sh"

# Adapt to your project: where each language's source lives, and which
# frontend framework web/ uses (vue | react).
RUST_SOURCE_RE='\.rs$'
RUST_TESTS_RE='(^|/)tests/.*\.rs$'
WEB_SOURCE_RE='^web/src/'
WEB_FRAMEWORK='vue'
PYTHON_SOURCE_RE='\.py$'

require_git_commit_command
bypassed STRUCTURE_STYLE_GUARD_OK && exit 0

ALL_CHANGED=$(git status --porcelain --untracked-files=all 2> /dev/null | grep -v '^!!' | cut -c4-)
[ -z "${ALL_CHANGED}" ] && exit 0

HAS_RUST=$(printf '%s\n' "${ALL_CHANGED}" | grep -cE "${RUST_SOURCE_RE}")
HAS_RUST_TESTS=$(printf '%s\n' "${ALL_CHANGED}" | grep -cE "${RUST_TESTS_RE}")
HAS_WEB=$(printf '%s\n' "${ALL_CHANGED}" | grep -cE "${WEB_SOURCE_RE}")
HAS_PYTHON=$(printf '%s\n' "${ALL_CHANGED}" | grep -cE "${PYTHON_SOURCE_RE}")

[ "${HAS_RUST}" -eq 0 ] && [ "${HAS_WEB}" -eq 0 ] && [ "${HAS_PYTHON}" -eq 0 ] && exit 0

SKILLS=""

if [ "${HAS_RUST}" -gt 0 ]; then
  RUST_DIMS="rust-code-style · project_structure.md"
  [ "${HAS_RUST_TESTS}" -gt 0 ] && RUST_DIMS="${RUST_DIMS} · rust-testing"
  SKILLS="${SKILLS}  /rust-structure-and-style-guard  — ${RUST_DIMS}"$'\n'
fi

if [ "${HAS_WEB}" -gt 0 ]; then
  SKILLS="${SKILLS}  /${WEB_FRAMEWORK}-structure-and-style-guard — frontend-${WEB_FRAMEWORK}-code-style · project_structure.md"$'\n'
fi

if [ "${HAS_PYTHON}" -gt 0 ]; then
  SKILLS="${SKILLS}  /python-structure-and-style-guard — python-code-style · python-ddd · project_structure.md"$'\n'
fi

SOURCE_FILES=$(printf '%s\n' "${ALL_CHANGED}" | grep -E "${RUST_SOURCE_RE}|${WEB_SOURCE_RE}|${PYTHON_SOURCE_RE}" | sed 's/^/  /')

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
Python-only or frontend-only projects.

```bash
#!/usr/bin/env bash

# Claude Code PreToolUse hook (matcher: Bash). Blocks `git commit` while the
# Rust workspace fails `cargo fmt --all -- --check`; the check is workspace-wide.
# Bypass: CARGO_FMT_OK=1 at command position before `git commit`, for the rare
# commit that must land unformatted (e.g. a checkpoint mid-conflict-resolution).

HOOK_DIR=$(CDPATH='' cd -- "$(dirname -- "${0}")" && pwd)
source "${HOOK_DIR}/pretooluse-common.sh"

require_git_commit_command
bypassed CARGO_FMT_OK && exit 0

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

**Blocks a `git commit` while the working tree changes code with no documentation
change**, so the agent reconciles docs before the commit lands. Delegates
detection to `reconcile-docs-check.sh`.

```bash
#!/usr/bin/env bash

# Claude Code PreToolUse hook (matcher: Bash). Blocks `git commit` while the
# working tree changes code but no documentation. Detection lives in
# reconcile-docs-check.sh. Bypass: RECONCILE_DOCS_OK=1 at command position
# before `git commit`, when no docs are genuinely warranted.

HOOK_DIR=$(CDPATH='' cd -- "$(dirname -- "${0}")" && pwd)
source "${HOOK_DIR}/pretooluse-common.sh"

require_git_commit_command
bypassed RECONCILE_DOCS_OK && exit 0

CHECK_SCRIPT="${HOOK_DIR}/reconcile-docs-check.sh"
[ -x "${CHECK_SCRIPT}" ] || exit 0

CODE_FILES=$("${CHECK_SCRIPT}" --working-tree)
[ ${?} -eq 3 ] || exit 0

{
  echo "Commit blocked by reconcile-docs: the change set touches code but no documentation:"
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

Create or update `.claude/settings.json` at the project root — the shared file,
so the team and every worktree get the same hooks:

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
            "statusMessage": "reconcile-docs: checking docs vs code"
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

- `$CLAUDE_PROJECT_DIR` is the project root as Claude Code sees it; relative
  paths and `$(pwd)` break when the agent's working directory differs from it.
- `timeout` is in seconds and a timed-out hook fails open. `cargo fmt` on a large
  workspace can be slow; give it 60.
- Omit `pretooluse-cargo-fmt.sh` entirely for non-Rust projects.
- Three entries, three responsibilities — do not merge them.

## Step 4 — Install the Git pre-commit hook

```bash
git config core.hooksPath tools/hooks
```

Git now runs `tools/hooks/pre-commit` straight from the versioned directory: no
symlink into `.git/hooks`, and it works in every worktree of the clone, where
`.git` is a file and a symlink recipe breaks. The setting is per clone, so put
the command in the project's bootstrap recipe (see `justfile-setup`) rather than
in a README paragraph.

## Step 5 — Verify each hook fires

Do not trust a green result you have not seen fail.

### Verify structure-and-style-guard

```bash
# Touch any source file, then try to commit — expect a block
echo "// probe" >> src/main.rs
git add src/main.rs && git commit -m "probe"
# Expected: "Commit blocked by structure-and-style-guard: ..."
git checkout src/main.rs
```

Run the guard skill the message names, address its findings, then commit with
the bypass. Two tripped hooks are satisfied by two tokens in one command:

```bash
STRUCTURE_STYLE_GUARD_OK=1 git commit -m "your message"
STRUCTURE_STYLE_GUARD_OK=1 RECONCILE_DOCS_OK=1 git commit -m "your message"
```

### Verify cargo-fmt (Rust only)

```bash
printf '\nfn badly_formatted()   {}\n' >> src/main.rs
git add src/main.rs && git commit -m "probe"
# Expected: "Commit blocked by cargo-fmt: ..."
cargo fmt --all
git add src/main.rs && git commit -m "your message"
```

### Verify reconcile-docs

```bash
echo "// probe" >> src/main.rs
git add src/main.rs && git commit -m "probe"
# Expected: "Commit blocked by reconcile-docs: ..."
# Either add a doc change, or bypass
RECONCILE_DOCS_OK=1 git commit -m "refactor: internal only"
```

## Bypass tokens

Each blocking hook accepts a bypass variable placed **at command position before
`git commit`** — alone or among other `NAME=value` assignments, so
`STRUCTURE_STYLE_GUARD_OK=1 RECONCILE_DOCS_OK=1 git commit -m "…"` satisfies
both hooks at once. A token that only appears inside the commit message does not
match. The bypass is also what ends the block loop once the agent has consciously
acted on a guard's findings.

| Hook | Bypass token | When to use |
|------|--------------|-------------|
| structure-and-style-guard | `STRUCTURE_STYLE_GUARD_OK=1` | After the guard skill has run and findings are addressed; or for comment-only changes, reverts, config-only changes |
| cargo-fmt | `CARGO_FMT_OK=1` | When deliberately committing with an unformatted tree (e.g. mid-conflict-resolution checkpoint) |
| reconcile-docs | `RECONCILE_DOCS_OK=1` | Internal refactors where no docs are genuinely warranted |

Never export a bypass token from a shell profile: the hooks also honour the
variable in their own environment, and every later commit would pass silently.

## Customization knobs

### Source area patterns

The variables at the top of `pretooluse-structure-and-style-guard.sh` are the
only project-specific part. Adapt them to your layout:

| Knob | Example |
|---|---|
| `RUST_SOURCE_RE`, any crate | `'\.rs$'` (default) |
| `RUST_SOURCE_RE`, only named crates | `'^(core\|worker\|api)/.*\.rs$'` |
| `WEB_SOURCE_RE`, frontend in `web/` | `'^web/src/'` |
| `WEB_FRAMEWORK` | `vue` or `react` — selects the guard skill the block message names |
| `PYTHON_SOURCE_RE`, flat layout | `'\.py$'` |
| `PYTHON_SOURCE_RE`, `src/` layout | `'^src/.*\.py$'` |

### Documentation file recognition

Extend `is_doc_path()` in `reconcile-docs-check.sh` for any project-specific doc
patterns (e.g. `openapi.yaml`, `architecture/`, wiki files):

```bash
case "${CHANGED_PATH}" in
  docs/* | */docs/* | architecture/*) return 0 ;;
esac

case "${CHANGED_PATH##*/}" in
  README.md | ROADMAP.md | CHANGELOG.md | CLAUDE.md | openapi.yaml) return 0 ;;
esac
```

### Formatter hook for non-Rust projects

Copy `pretooluse-cargo-fmt.sh`, replace the `cargo fmt` check with
`ruff format --check` for Python or `prettier --check` for a frontend, and give
it its own bypass token. The shared preamble already handles the payload, the
commit match, and the bypass; the copy only carries its one check.

### Another hook on another event

The same shape serves any further guard the project wants — for example a
reminder to run the dependency audit after a `Cargo.toml`, `pyproject.toml`, or
`package.json` change. Source the helper, keep exactly one check per script, and
register it under its own event and matcher in `.claude/settings.json`.
