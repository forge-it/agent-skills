---
name: repo-root-files-pattern
description: >-
  Use when bootstrapping a new monorepo and deciding which files belong at the
  repo root versus inside each component directory — symptoms: a new component
  lacks an .env.template and contributors cannot spin up locally; .env files are
  accidentally committed; per-component gitignores are missing the env-file
  exceptions; or the root carries a README that describes only one component
  rather than the whole product.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.3"
---

# Repo Root Files Pattern

## Purpose

A monorepo with multiple components (backend, worker, frontend) needs a clear
rule for where each file lives. Without one, per-component configuration leaks
to the root, the root carries component-specific detail, and contributors cannot
tell which files they must create locally to run anything.

**In one line:** the repo root describes the *whole product* and owns the one
command surface contributors call; each component directory owns its own
documentation, manifests, exclusions, and environment files.

> **Core principle (separation of concerns / single responsibility):** root
> files answer "what is this product and how is it organised?" — one set of
> cross-cutting files for the workspace. Per-component files answer "what is
> *this service* and how do I run it?" — each component owns its own slice.
> A file that is only about `core/` does not belong at the repo root, and a
> file that spans all components does not belong inside `worker/`.

## File Taxonomy

### Root-level files

These files describe and govern the whole product. They belong at the repo root
and nowhere else.

| File | Purpose | Required? |
|---|---|---|
| `README.md` | Human entry point: what the product is, what components exist, how to run the whole stack. Should link to per-component READMEs. | **Yes — see gap below** |
| `DESIGN.md` | Visual identity, colour palette, UX principles, and tone of voice for the product. | When the product has a UI |
| `ROADMAP.md` | High-level milestones across *all* components with links to per-component roadmaps. | Recommended |
| `.gitignore` | Root-level artefact exclusions: workspace `target/`, root IDE files, OS files, agent worktrees and ephemeral scratch directories. | Yes |
| `.dockerignore` | Build-context exclusions for Docker. For workspace builds (backend Dockerfiles built from the repo root), this file governs the whole context — excludes `target/`, `.git/`, unrelated components (`web/`), and all `**/.env*` patterns. | When any component is containerised |
| `Cargo.toml` / `pyproject.toml` / `package.json` | Workspace manifest (language-specific). | Language-dependent |
| `justfile` | Root task runner: dev-stack up/down, per-component lint/test/build invocations. Recipes read per-component env files. See `justfile-setup`. | Recommended |
| `just/` | Responsibility-split recipe files the root `justfile` pulls in with `import` — `env.just`, `dev.just`, `test.just`, `deploy.just`, `format.just`, `tools.just` are a representative set, not a frozen list. Appears once the root file crosses 350 lines, or earlier if a change benefits. See `justfile-setup`. | When the root justfile has outgrown one file |
| `rust-toolchain.toml` | Pins the Rust toolchain version for the whole workspace. | Rust workspace |
| `CLAUDE.md` | AI agent instructions: project layout, key decisions, tooling commands. See [`claude_md_pattern.md`](claude_md_pattern.md). | When using AI agents |
| `AGENTS.md` | Alternative or supplementary agent instructions (mirrors `CLAUDE.md` for non-Claude agents). | When using AI agents |

**`just/` is root-owned, and that is what distinguishes it.** Its files share one
flat recipe namespace with the root `justfile` and are always invoked from the
root as `just <recipe>`, so they organize one command surface by responsibility
rather than adding a second entry point. Components own their manifests and
toolchains (`cargo`, `uv`, `pnpm`); root recipes delegate to those.

### Per-component files

Each component directory (`core/`, `worker/`, `web/`) owns these files. They
describe and configure that one service only.

| File | Purpose | Required? |
|---|---|---|
| `README.md` | What this component does, how to configure it, how to run it locally. | Yes |
| `ROADMAP.md` | Per-component milestones and phases, linked from the root roadmap. | Recommended |
| `CLAUDE.md` | Component-specific AI agent instructions — more detailed than the root. | When using AI agents |
| `config.toml` | Committed deployment policy for a native development run: the versioned TOML document the process loads — bind address, endpoints, pool sizes, timeouts. **No secrets, ever.** | Yes (for a process that loads configuration) |
| `config.local-deploy.toml` | Committed deployment policy for the `docker compose` run: container hostnames and internal ports instead of `localhost` and host-mapped ports. No secrets. | When the component is containerised |
| `.env` | Bootstrap values (config path, secret-source selector) plus development secret fixtures in environment mode. **Never committed.** | Yes (local-only) |
| `.env.template` | Checked-in scaffold of `.env`: every variable name, a safe placeholder, and a comment explaining each one. No real secrets. | Yes |
| `.env.deploy.local` | Checked-in bootstrap for the `docker compose` run plus **low-sensitivity dev-cluster secret fixtures only**. Deployment policy is not here — it is in `config.local-deploy.toml`. | When the component is containerised |
| `.gitignore` | Component-level exclusion: `/target/` or `/node_modules/`, `/.env`, `/.env.*` with explicit negations for `.env.template` and `.env.deploy.local`. | Yes |
| `Cargo.toml` / `pyproject.toml` / `package.json` | Component build manifest. Note what is *not* here: a component task runner. The root `justfile` is the single command surface and delegates to each component's toolchain — see the anti-pattern below. | Language-dependent |

## The Three Environment Files

This is the most error-prone part of the pattern. Each component has exactly
three env-related files with distinct roles. What they carry is deliberately
narrow: **bootstrap values and secret fixtures, nothing else.** Deployment
policy — endpoints, ports, pool sizes, timeouts — lives in the committed TOML
documents above, and a credential-bearing URL such as
`postgres://user:password@host/db` appears in none of these files. Which
value is bootstrap, which is a secret, and which belongs in the TOML is the
[configuration authority pattern](../decisions/configuration_authority_pattern.md)'s
decision; this pattern only places the files.

| File | Committed? | Contains real secrets? | Used by |
|---|---|---|---|
| `.env` | No | Yes (development fixtures) | Developer running the component natively |
| `.env.template` | Yes | No (placeholders) | New contributors copying it to `.env` |
| `.env.deploy.local` | Yes | Maybe (low-risk dev-cluster fixtures only) | `docker compose up` for local-prod testing |

### `.env.template` conventions

Observed in ironbox across `core/`, `worker/`, and `web/`:

- Start with `# shellcheck disable=SC2034` so shell linters do not flag unused
  variable warnings when the file is sourced.
- Every variable is present. Where a variable is a secret fixture, include a
  safe dev default or a clearly named placeholder (not an empty value, which
  leaves contributors guessing the type).
- Only bootstrap values and secret fixtures appear. A hostname, port, or
  timeout in this file is a defect: it belongs in `config.toml`.
- Inline comments explain non-obvious variables: their purpose, valid values,
  and when they apply (e.g. "Set to `true` in production (HTTPS)").
- Keep the template in sync with `.env` — same variable names, same ordering.
  Drift between them is a common source of "works on my machine" failures.

Minimal template example (backend component):

```dotenv
# shellcheck disable=SC2034
# Bootstrap — the only non-secret values the environment carries.
APP_CONFIGURATION_PATH=config.toml
APP_SECRET_SOURCE=environment   # development and tests only; production uses `file`

# Development secret fixtures, read only in environment mode. The database
# host, port, and name, and the SMTP host and port, live in config.toml —
# only the credential is here.
APP_DATABASE_PASSWORD=dev_password
APP_SMTP_PASSWORD=dev_password
# 32-byte base64-encoded key. Generate with: openssl rand -base64 32
APP_SECRETS_ENCRYPTION_KEY=REPLACE_WITH_GENERATED_KEY
```

`APP_` stands for the project's own prefix. The matching `config.toml` holds
the non-secret half — `[server] port = 8000`, `[database] host = "localhost"`,
`[smtp] host = "localhost"` — so the two files never carry the same value.

### `.env.deploy.local` conventions

This file selects the compose-run configuration document and carries the
secret fixtures for that run. Everything that differs between a native-dev
run and a `docker compose` run — container hostnames instead of `localhost`,
internal standard ports instead of host-mapped dev ports — is a difference
between `config.toml` and `config.local-deploy.toml`, not between two env
files.

```dotenv
# shellcheck disable=SC2034
APP_CONFIGURATION_PATH=config.local-deploy.toml
APP_SECRET_SOURCE=environment   # compose passes these through; production uses `file`

# Low-risk dev-cluster fixtures only
APP_DATABASE_PASSWORD=dev_password
APP_SMTP_PASSWORD=REPLACE_WITH_DEV_CLUSTER_SMTP_PASSWORD
APP_SECRETS_ENCRYPTION_KEY=REPLACE_WITH_GENERATED_KEY
```

A containerised component at delivery tier 1 or above of the configuration
authority pattern replaces environment mode with Compose `secrets:` files, and
the fixtures leave this file; the bootstrap lines stay.

### Per-component `.gitignore` pattern

The component gitignore must exclude `.env` and all `.env.*` variants by
default, then explicitly re-include the two committed files:

```gitignore
# Local environment — never committed
/.env
/.env.*
!.env.template
!.env.deploy.local
```

The root `.gitignore` should **not** carry these rules because it does not know
about every component's env files. Each component owns its own exclusions.

The root `.dockerignore` (for workspace Docker builds) uses the global pattern
`**/.env*` to exclude every env file across all components from the build
context — no per-component entry needed, and no re-include, because Dockerfiles
must never reference `.env` files directly.

## README Gap Found in Ironbox

The ironbox repo **has no root `README.md`**. Every component (`core/`,
`worker/`, `web/`) has its own README, and the root has `DESIGN.md`,
`ROADMAP.md`, `CLAUDE.md`, and `AGENTS.md` — but no human-facing entry point
that answers "what is this repo?" for a new contributor landing on the root.

**Recommendation:** a greenfield monorepo should have a root `README.md`. It
need not be long. The minimum content is:

1. One-sentence product description.
2. Component table: what `core/`, `worker/`, `web/` each are.
3. Quick-start link or the single command to bring up the dev stack (e.g.
   `just up`).
4. Links to per-component READMEs for deeper detail.

Without it, a contributor cloning the repo and reading the root sees only a
`DESIGN.md` (visual identity) and a `ROADMAP.md` (milestones) — both assume
the reader already knows what the product is.

## Quick Reference

**Root owns:**
- Product-wide entry point and documentation (`README.md`, `DESIGN.md`,
  `ROADMAP.md`)
- Cross-cutting exclusions (`.gitignore`, `.dockerignore`)
- Workspace build manifest and toolchain pin
- Root task runner (`justfile`, plus `just/` once it outgrows one file)
- Agent instructions for the whole codebase (`CLAUDE.md`, `AGENTS.md`)

**Each component owns:**
- Its own `README.md`, `ROADMAP.md`, `CLAUDE.md`
- Its own `.env`, `.env.template`, `.env.deploy.local`
- Its own `.gitignore` with explicit env-file exceptions
- Its own build manifest (`Cargo.toml`, `package.json`, etc.)

**The env-file rule in one line:** `.env` is local-only and gitignored;
`.env.template` is the checked-in scaffold with safe defaults; `.env.deploy.local`
is the checked-in local-prod override with container hostnames.

## Anti-Patterns

- **Committing `.env`.** Contains real secrets. The per-component `.gitignore`
  must exclude it; the root `.dockerignore` must exclude `**/.env*`.
- **Secrets in `.env.template`.** The template is committed and public. Use
  safe dev defaults or clearly named placeholders.
- **`.env.deploy.local` with production credentials.** This file is committed
  and is only safe for dev-cluster or low-risk values. Production secrets belong
  in a secrets manager, not in any committed file.
- **Drifting `.env.template` and `.env`.** If a variable exists in `.env` but
  not in the template, new contributors will have a silent missing-variable bug.
  Keep them in sync.
- **Root `.gitignore` carrying per-component env exclusions.** The root file
  cannot enumerate every future component. Each component's `.gitignore` owns
  its own env exclusions.
- **A second task runner inside a component directory** — a component `justfile`,
  or a `Makefile.toml`/`Makefile` carrying tasks. It splits "how do I run this
  project" across locations, gives the same action two names, and makes
  contributors learn which directory to stand in. The root `justfile` — with
  `just/` once it outgrows one file — is the single command surface, and it
  delegates to each component's toolchain (`cargo`, `uv`, `pnpm`). A recipe that
  must run inside a component does `cd <component> && …`.
- **A root README that describes only one component.** The root README should
  describe the product; component detail belongs in the component README.
- **Per-component DESIGN.md / root ROADMAP.md entries that span the whole
  product.** Design and cross-component milestones belong at the root; a
  component's ROADMAP should cover only that component's phases.

## Relationship to Other Patterns and Skills

- **`justfile-setup`** — the root `justfile` recipes consume per-component env
  files (e.g. `set dotenv-filename := "core/.env"` or explicit `--env-file`
  flags). The file taxonomy here defines which env files those recipes expect.
- **`ci-setup`** — CI jobs per component reference the same env files defined
  here; the template is the source of truth for which variables a component
  needs in CI secrets.
- **[`claude_md_pattern.md`](claude_md_pattern.md)** — governs the content
  and maintenance of the `CLAUDE.md` files that appear at both the root and
  per-component level in this taxonomy.
- **[`docs_artifact_layout_pattern.md`](docs_artifact_layout_pattern.md)** — governs
  the `docs/` subdirectory structure inside each component that appears in the
  per-component file listing above.
