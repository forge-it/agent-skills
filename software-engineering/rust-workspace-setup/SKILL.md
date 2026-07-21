---
name: rust-workspace-setup
description: Use when bootstrapping a new Rust monorepo workspace from commit 1 — when the project has more than one binary crate (e.g. an API server and a background worker), when shared types must be consumed by two or more members without duplicating code, or when a single-crate layout would force one binary to carry another's compile-time dependencies. Triggers — a team wants shared wire contracts between a backend service and a worker process; a shared infrastructure primitive crate must stay independent of both consumers; the Cargo.toml at the repository root has no `[workspace]` section yet. Not applicable for single-crate projects (see rust-project-setup).
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.1"
---

# Rust Workspace Setup

This is a **one-time setup skill**. It produces a repository root `Cargo.toml` and a
member-crate layout that can grow without coupling. The guiding principle is
**separation of concerns at the crate boundary** — each member crate owns one
responsibility and exposes only what its dependents need. A workspace that does not
enforce this from the first commit accumulates cross-cutting `use` statements until
splitting is more expensive than tolerating the mess.

The templates here are grounded in a real workspace: an API backend (`core/`), an async
background worker (`worker/`), and shared crates under `crates/` — a task-contracts
crate that owns the gRPC wire types exchanged between the API and the worker, a
connectors-runtime crate shared by both, and a kubernetes-primitives crate that is a
dependency of the connectors-runtime crate but carries no service logic.

The cross-language note: Python's equivalent is `uv workspaces` (a `uv.toml`
`[workspace]` table with a `members` list). The principles — shared dependency
declarations, one-way boundaries, shared lint config — translate directly. The rest of
this skill is Rust-specific.

---

## Repository layout

```
my-project/                          ← workspace root (no src/, no bin/)
├── Cargo.toml                       ← [workspace] manifest only
├── rust-toolchain.toml              ← toolchain pin (see rust-project-setup)
├── rustfmt.toml                     ← shared formatter config
├── core/                            ← API/backend binary crate
│   └── Cargo.toml
├── worker/                          ← async background-worker binary crate
│   └── Cargo.toml
└── crates/                          ← shared library crates
    ├── task-contracts/              ← wire types shared by core ↔ worker
    │   └── Cargo.toml
    ├── connectors-runtime/          ← probe/connectivity logic shared by core ↔ worker
    │   └── Cargo.toml
    └── kubernetes-primitives/       ← pure k8s manifest primitives (no service logic)
        └── Cargo.toml
```

The workspace root carries **no `src/` directory** and **no `[lib]` or `[[bin]]`
section**. Its only job is to declare the workspace, own the lint table, hoist shared
profiles, and provide a `[workspace.dependencies]` table that prevents version skew.

---

## Step 1 — Workspace root `Cargo.toml`

```toml
# Workspace manifest. The root carries no source code — members live in
# core/, worker/, and crates/.
[workspace]
resolver = "2"
members = [
    "core",
    "worker",
    "crates/task-contracts",
    "crates/connectors-runtime",
    "crates/kubernetes-primitives",
]

# ---------------------------------------------------------------------------
# Shared lint table — members opt in via `[lints] workspace = true`.
# ---------------------------------------------------------------------------
[workspace.lints.rust]
unsafe_code = "deny"

[workspace.lints.clippy]
all      = { level = "warn", priority = -1 }
pedantic = { level = "warn", priority = -1 }
nursery  = { level = "warn", priority = -1 }
# Adjust suppressions to your project's honest needs — do not silence
# diagnostics wholesale to keep the clippy section small.
missing_errors_doc  = "allow"
missing_panics_doc  = "allow"
type_complexity     = "allow"

# ---------------------------------------------------------------------------
# Shared build profiles — Cargo silently ignores member-level profile tables.
# Move them here from member Cargo.toml files when adding workspace support.
# ---------------------------------------------------------------------------
[profile.release]
lto            = true
codegen-units  = 1
panic          = "abort"
strip          = true

[profile.dev]
debug = true

# ---------------------------------------------------------------------------
# Shared dependency versions — members reference these as
# `serde = { workspace = true }` or `serde = { workspace = true, features = ["derive"] }`.
# Declare only versions that are shared across two or more members.
# ---------------------------------------------------------------------------
[workspace.dependencies]
tokio       = { version = "1",   features = ["full"] }
serde       = { version = "1",   features = ["derive"] }
serde_json  = "1"
uuid        = { version = "1",   features = ["v7", "serde"] }
chrono      = { version = "0.4", features = ["serde"] }
tracing     = "0.1"

# Internal crates — declared here so members can reference them without
# repeating the path.
task-contracts         = { path = "crates/task-contracts" }
connectors-runtime     = { path = "crates/connectors-runtime" }
kubernetes-primitives  = { path = "crates/kubernetes-primitives" }
```

### Why `resolver = "2"` is required

Resolver v2 is mandatory for workspaces that mix `std` and `no_std` members, or that
have members with different feature combinations of the same dependency. Without it,
Cargo v1's feature unification merges features across all members, silently enabling
capabilities in members that did not request them.

### Why profiles live only in the root

Cargo reads `[profile.*]` tables only from the workspace root and **silently ignores**
them in member `Cargo.toml` files. If you have profile overrides in member manifests
today, move them to the root when converting to a workspace.

---

## Step 2 — Toolchain and formatter files

These two files live at the repository root and are shared by every member.

### `rust-toolchain.toml`

Pin a specific stable release. "stable" without a version drifts with whatever rustup
updates to, making `cargo check` output non-reproducible across machines.

```toml
[toolchain]
channel    = "1.87.0"
components = ["rustfmt", "clippy"]
```

See `rust-project-setup` for the full rationale.

### `rustfmt.toml`

The 2024 edition style guide is the sensible baseline:

```toml
edition       = "2024"
style_edition = "2024"
```

Add project-specific overrides only when the default produces output the team actively
dislikes — a long list of overrides is a maintenance burden.

---

## Step 3 — Member crate layout and `Cargo.toml` patterns

### The task-contracts crate (shared wire types)

This crate owns the types that cross the API ↔ worker boundary: gRPC stubs, message
DTOs, and any enumerations the two sides must agree on. It depends on nothing internal.

```toml
# crates/task-contracts/Cargo.toml
[package]
name        = "task-contracts"
version     = "0.1.0"
edition     = "2024"
publish     = false
description = "Shared wire contracts between the API backend and the worker: message DTOs and any shared enumerations."

[dependencies]
serde      = { workspace = true }
serde_json = { workspace = true }
uuid       = { workspace = true }
chrono     = { workspace = true }

[lints]
workspace = true
```

Key rules for this crate:
- No dependency on `core/` or `worker/` — ever. The arrow is always inward.
- No infrastructure crates (no `sqlx`, no `axum`, no `kube`). Contracts are pure data.
- Keep the public surface minimal; every field that crosses the wire is a commitment.

### The API backend crate

```toml
# core/Cargo.toml
[package]
name        = "my-project-core"
version     = "0.1.0"
edition     = "2024"
publish     = false
description = "HTTP API and background scheduler for my-project."

[dependencies]
tokio      = { workspace = true }
serde      = { workspace = true }
serde_json = { workspace = true }
uuid       = { workspace = true }
tracing    = { workspace = true }

# Internal shared crates
task-contracts        = { workspace = true }
connectors-runtime    = { workspace = true }
kubernetes-primitives = { workspace = true }

# Backend-specific dependencies (not shared — declared locally)
axum     = "0.8"
sqlx     = { version = "0.8", features = ["runtime-tokio", "postgres", "uuid", "chrono", "migrate"] }

[features]
default = []
# Gate infrastructure-fixture tests in CI (no external cluster available).
ci = []

[lints]
workspace = true
```

### The worker crate

```toml
# worker/Cargo.toml
[package]
name        = "my-project-worker"
version     = "0.1.0"
edition     = "2024"
publish     = false
description = "Async background-task worker for my-project."

[dependencies]
tokio      = { workspace = true, features = ["macros", "rt-multi-thread", "signal", "sync", "time"] }
tracing    = { workspace = true }
serde_json = { workspace = true }

# Internal shared crates — the worker never depends on core/.
task-contracts     = { workspace = true }
connectors-runtime = { workspace = true }

[lints]
workspace = true
```

The worker must **never** depend on `core/`. All types the worker and the API share must
live in a shared crate under `crates/`. This is the single-responsibility rule applied
at the crate boundary: the worker's job is task execution, not re-hosting API logic.

### Shared library crates under `crates/`

A crate belongs under `crates/` when:
- Two or more members need it, **and**
- It has no transitive dependency on either of those members (no circular paths).

A crate that is only needed by one member belongs inside that member, not in `crates/`.
Moving a crate to `crates/` when only one consumer uses it is premature extraction that
adds maintenance overhead for no benefit.

---

## Step 4 — Opt-in workspace lints

Every member crate that should be held to the workspace lint policy adds exactly one
line:

```toml
[lints]
workspace = true
```

A crate that omits this line is not linted by the workspace rules — useful for vendored
or generated code that you don't own. For all first-party crates, `workspace = true` is
the default.

---

## Step 5 — Consuming workspace dependencies in members

Two patterns:

```toml
# 1. Take the version and all declared workspace features as-is:
serde = { workspace = true }

# 2. Take the version but add extra features on top:
tokio = { workspace = true, features = ["macros", "rt-multi-thread"] }
```

You cannot remove workspace-declared features from a member — you can only add more.
This means the features listed under `[workspace.dependencies]` should be the
**minimum** set required by any consumer. Do not add `features = ["full"]` to the
workspace entry for a crate like `tokio` if most members only need a subset; it inflates
compile times for every member.

---

## Step 6 — Verify the workspace compiles clean

```bash
# Check all members in one pass:
cargo check --workspace

# Run the full test suite across all members:
cargo test --workspace

# Lint all members:
cargo clippy --workspace -- -D warnings

# Format check:
cargo fmt --check
```

The `--workspace` flag is the shorthand for "all members". Prefer it over per-member
invocations in CI so new members are automatically included.

---

## Anti-Patterns

1. **Putting source in the workspace root.** The root manifest's job is coordination,
   not implementation. Source in the root means `cargo test --workspace` includes the
   root as a member, which causes confusing output and breaks the mental model that the
   root is "above" the members.

2. **Version-pinning the same dependency differently in two members.** Cargo will merge
   the requirement sets but may select different patch versions for `cargo update`, which
   produces non-reproducible builds across developer machines. Hoist to
   `[workspace.dependencies]` the moment a dependency is shared.

3. **Worker depending on core.** When the worker needs a type from the API backend, the
   fix is to extract it to a shared crate, not to add `core = { path = "../core" }` in
   the worker's manifest. A dependency from worker → core pulls in every backend
   dependency (axum, sqlx, the full HTTP stack) into the worker binary.

4. **Profiles in member manifests.** Cargo silently ignores `[profile.*]` in any
   manifest that is not the workspace root. This is a silent misconfiguration: the
   member author believes a profile applies; it does not.

5. **One mega-crate under `crates/` that "shares everything."** Each crate under
   `crates/` should have one clear responsibility. A catch-all shared crate grows until
   it is indistinguishable from a second `core/`, and its compile time inflates every
   consumer.

6. **`features = ["full"]` in `[workspace.dependencies]` for feature-rich crates.** As
   noted in Step 5, workspace features are a floor, not a ceiling. Setting them too high
   penalises every member that doesn't need the extras.

---

## Quick Reference

| Task | Command |
|---|---|
| Check all members | `cargo check --workspace` |
| Test all members | `cargo test --workspace` |
| Lint all members | `cargo clippy --workspace -- -D warnings` |
| Format all members | `cargo fmt` |
| Format check (CI) | `cargo fmt --check` |
| Build release | `cargo build --release --workspace` |
| Add a new member | Add path to `members` in root `Cargo.toml`, create `<member>/Cargo.toml` |
| Add a shared dep | Add to `[workspace.dependencies]`, reference with `workspace = true` in members |

---

## Cross-references

- **rust-project-setup** — toolchain pinning and `cargo-make` build automation for
  single-crate projects; the `rust-toolchain.toml` section applies unchanged to
  workspaces.
- **rust-project-structure** — module, file, and folder conventions inside a member
  crate.
- **rust-hexagonal-architecture** — layering (domain / application / infrastructure)
  inside a member crate; the crate-split workspace pattern described in
  `rust-architecture-test-setup` maps one layer per workspace member.
- **rust-architecture-test-setup** — the `tests/structure/` cargo-test gate; run it per
  member that uses hexagonal layers. `SourceTree` resolves via `CARGO_MANIFEST_DIR` so
  it naturally scopes to the member crate. Its **manifest dependency gate** is what
  keeps the workspace's dependency directions permanent: give every shared library
  crate an in-crate gate forbidding its consumers, and give the worker a gate
  forbidding the core crate and direct database drivers.
- **justfile-setup** — workspace-level task runner; `just check` can invoke
  `cargo check --workspace` rather than per-member commands.

The `task-contracts` crate is the **API ↔ worker broker boundary** — the only place
where the two binary members may share types. Keep it thin. Any logic that belongs to
the domain of the API or the worker must stay in its respective member crate.
