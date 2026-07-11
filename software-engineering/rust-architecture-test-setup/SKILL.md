---
name: rust-architecture-test-setup
description: One-time setup of a `tests/structure/` cargo-test gate for a Rust hexagonal-architecture project, so the layering invariants (dependencies point inward — domain → application → infrastructure) and the project-structure conventions (`port.rs` holds traits only, file names don't stutter, `mod.rs` stays out of `src/` and `tests/` except `tests/common/`, concept module files stay glob facades in application crates, the domain stays framework-free) are enforced by `cargo test` — and therefore CI — instead of by review. Use when bootstrapping a new Rust hexagonal project's architecture enforcement, or adding it to an existing one. Assumes a layered hexagonal codebase (domain/application/infrastructure under `src/`).
vibe: Turns the architecture doc into a build that fails when someone crosses a layer.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.1.0"
---

# Rust Architecture Test Setup

This is a **one-time setup skill**. It produces a `tests/structure/` integration-test
target that makes the conventions from `rust-hexagonal-architecture` and
`rust-project-structure` a thing the build *checks*, not a thing people *remember*.
A boundary written only in a doc rots — someone writes `use crate::infrastructure::…`
inside `domain/` in a hurry, review misses it, and the dependency direction quietly
inverts. Encoded as a `cargo test` that fails on the violation, the same mistake
blocks the merge.

It needs **no extra toolchain and no crate split** — it is a plain integration test
that scans the source files under `src/` and the test files under `tests/`. (The
stronger, compile-time alternative — one crate per layer — is described at the end;
this skill is the pragmatic single-crate gate.)

## When to use

- Bootstrapping a **new** Rust hexagonal service → every rule hard-fails from the
  first commit (a greenfield codebase has zero violations, so there is nothing to
  ratchet).
- Adding the gate to an **existing** project → run it, see what it surfaces, then
  decide per rule: fix the few real violations, or mark a pervasive-but-accepted
  rule advisory (`#[ignore]`) and ratchet it to hard-fail later. See
  [Severity](#severity-new-project-vs-existing-codebase).

Run this once. After `tests/structure/` exists, you do not re-run the skill.

## What it enforces

Six rules, drawn from the two architecture skills:

1. **Dependencies point inward** — a file under `domain/` must not reference
   `application` or `infrastructure`; a file under `application/` must not reference
   `infrastructure`. (`rust-hexagonal-architecture`, "Dependencies Point Inward".)
2. **The domain is framework-free** — no file under `domain/` may `use` an
   infrastructure crate (`sqlx`, `axum`, …).
3. **`port.rs` holds traits only** — dataflow values belong in `model.rs`,
   construction-time tunables in `config.rs`, errors in `error.rs`.
   (`rust-project-structure`, "Data Types Live in `model.rs`".)
4. **File names don't stutter** — `backup/executor.rs`, never
   `backup/backup_executor.rs`. (`rust-project-structure`, "Short Module Names".)
5. **No legacy `mod.rs` layout** — `mod.rs` is forbidden under `src/` and `tests/`,
   except for the shared test helper entry point `tests/common/mod.rs`.
6. **Concept module files are facades** — a `<name>.rs` fronting a sibling `<name>/`
   folder holds only module docs, `mod` declarations, `pub mod` for subfolders, and
   `pub use <file>::*;` globs. Layer files (`src/<layer>.rs`) and adapter-family files
   directly under `infrastructure/` are exempt. Gated by `ENFORCE_CONCEPT_FACADE` —
   application crates only, never published libraries. (`rust-project-structure`,
   "The Concept Module File Is a Facade".)

It assumes the canonical hexagonal layers `domain/`, `application/`, `infrastructure/`
under `src/`. Adapt the layer set in `constants.rs` (see
[Customization](#customization-knobs)).

## Step 1 — Confirm your layers

Open `src/` and confirm the top-level layer directories. The default rules assume
`domain/`, `application/`, `infrastructure/`. If the project has an extra outermost
wiring layer (e.g. a `composition/` module rather than a bare `bin/main.rs`), note it —
you'll add it to the forbidden lists in `constants.rs` so inner layers can't depend on
it.

## Step 2 — Create the structure test

`cargo` auto-discovers `tests/<name>.rs` as a test target and resolves its inline
`mod <name> { … }` tree into `tests/<name>/…`. So the files are:

```
tests/
├── structure.rs                 # entry: declares the module tree
└── structure/
    ├── facade.rs                # tests-only: concept-module-file facade rule
    ├── layering.rs              # tests-only: dependency-direction rules
    ├── naming.rs                # tests-only: file-name stutter + mod.rs rules
    ├── ports.rs                 # tests-only: port.rs-traits-only rule
    └── support/
        ├── constants.rs         # layer names, forbidden lists, magic strings
        ├── source.rs            # SourceTree + SourceLine (scanning primitives)
        ├── rules.rs             # the Rule type + the named invariants
        └── violation.rs         # the Violation finding type
```

This layout follows `rust-testing`: the test files contain **only** tests; every
helper, constant, and type lives under `support/` (Sections 15–16).

### `tests/structure.rs`

```rust
#![allow(clippy::all, clippy::pedantic, clippy::nursery)]

mod structure {
    pub mod support;

    mod facade;
    mod layering;
    mod naming;
    mod ports;
}
```

### `tests/structure/support.rs`

```rust
//! Support for the structure tests. Per the rust-testing skill (Section 15/16)
//! the test files contain only tests; the rules, scanning utilities, violation
//! type, and constants live here.

pub mod constants;
pub mod rules;
pub mod source;
pub mod violation;
```

### `tests/structure/support/constants.rs`

**Before writing `tests/structure/support/constants.rs`, read `references/support-scanning-primitives.md`** — it contains the complete implementations of all three support files (`constants.rs`, `source.rs`, and `violation.rs`); write all three in one pass from this single reference.

### `tests/structure/support/source.rs`

**Before writing `tests/structure/support/source.rs`, read `references/support-scanning-primitives.md`** — the same reference introduced at `constants.rs` above; it covers this file.

### `tests/structure/support/violation.rs`

**Before writing `tests/structure/support/violation.rs`, read `references/support-scanning-primitives.md`** — the same reference introduced at `constants.rs` above; it covers this file.

### `tests/structure/support/rules.rs`

**Before writing `tests/structure/support/rules.rs`, read `references/support-rules-implementation.md`** — it contains the complete `Rule` type, all six named constructors, and the `enforce()` method.

### `tests/structure/layering.rs`

```rust
use super::support::constants::{
    APPLICATION_FORBIDDEN_LAYERS, APPLICATION_LAYER, DOMAIN_FORBIDDEN_LAYERS, DOMAIN_LAYER,
    INFRASTRUCTURE_CRATES,
};
use super::support::rules::Rule;

mod domain_layer {
    use super::*;

    #[test]
    fn should_not_depend_on_outward_layers() {
        Rule::layer_depends_inward_only(DOMAIN_LAYER, DOMAIN_FORBIDDEN_LAYERS).enforce();
    }

    #[test]
    fn should_be_free_of_infrastructure_crates() {
        Rule::domain_free_of_infrastructure_crates(INFRASTRUCTURE_CRATES).enforce();
    }
}

mod application_layer {
    use super::*;

    #[test]
    fn should_not_depend_on_infrastructure() {
        Rule::layer_depends_inward_only(APPLICATION_LAYER, APPLICATION_FORBIDDEN_LAYERS).enforce();
    }
}
```

### `tests/structure/naming.rs`

```rust
use super::support::rules::Rule;

mod file_names {
    use super::*;

    #[test]
    fn should_not_repeat_parent_directory() {
        Rule::file_names_do_not_repeat_parent().enforce();
    }
}

mod module_files {
    use super::*;

    #[test]
    fn should_allow_mod_rs_only_in_tests_common() {
        Rule::mod_files_are_limited_to_allowed_paths().enforce();
    }
}
```

### `tests/structure/ports.rs`

```rust
use super::support::rules::Rule;

mod port_files {
    use super::*;

    #[test]
    fn should_contain_traits_only() {
        Rule::port_files_hold_traits_only().enforce();
    }
}
```

### `tests/structure/facade.rs`

```rust
use super::support::rules::Rule;

mod concept_module_files {
    use super::*;

    #[test]
    fn should_hold_only_module_declarations_and_glob_reexports() {
        Rule::concept_module_files_are_facades().enforce();
    }
}
```

## Step 3 — Wire the gate

Add `cargo test --test structure` to CI. If the project uses `cargo-make`, give it a
task so it runs with the rest of the suite:

```toml
# Makefile.toml
[tasks.structure]
description = "Enforce architecture/layering invariants"
command = "cargo"
args = ["test", "--test", "structure"]

[tasks.check]
dependencies = ["format", "clippy", "structure", "test"]
```

`cargo test` exits non-zero on a failing assertion, so once it's in CI a violation
blocks the merge. Without that CI step the rules only report locally.

## Step 4 — Verify it works

Do not trust a green result you have not seen fail. Drop a throwaway file that violates
a rule, run the target, confirm it's caught, then delete it. The check is a filesystem
scan, so the file does **not** need to be `mod`-declared:

```bash
printf 'use crate::infrastructure::Thing;\n' > src/domain/__probe.rs
cargo test --test structure   # expect: domain_layer::should_not_depend_on_outward_layers fails
rm src/domain/__probe.rs
```

For the `mod.rs` rule, probe a throwaway module-layout file:

```bash
mkdir -p src/__probe
printf '' > src/__probe/mod.rs
cargo test --test structure   # expect: module_files::should_allow_mod_rs_only_in_tests_common fails
rm -r src/__probe
```

For the facade rule, probe a concept module file that exposes a file publicly:

```bash
mkdir -p src/application/__probe
printf 'pub mod port;\n' > src/application/__probe.rs
cargo test --test structure   # expect: concept_module_files::should_hold_only_module_declarations_and_glob_reexports fails
rm -r src/application/__probe src/application/__probe.rs
```

On a **new** project the suite then passes clean. On an **existing** project it now
prints exactly where the codebase diverges — this is your conformance report.

## Severity: new project vs. existing codebase

- **New project:** leave every test as a hard `enforce()`. There are no violations to
  clean up, so there is no reason to soften it.
- **Existing project:** a check may surface a pervasive, *intentional* house pattern
  (commonly `port.rs` colocating request/filter/error types). You have two honest
  moves per rule:
  - **Fix** the few real violations, then keep the rule hard-failing.
  - **Ratchet**: mark the test advisory so it does not gate yet, migrate over time,
    then remove the attribute to enforce. In plain `cargo test` the idiomatic
    "advisory, tracked, easy to flip" mechanism is `#[ignore]` with a reason:

    ```rust
    #[test]
    #[ignore = "advisory: port.rs files still colocate types; migrate to model.rs/error.rs, then remove to enforce. Run `cargo test --test structure -- --ignored` to see the punch-list."]
    fn should_contain_traits_only() {
        Rule::port_files_hold_traits_only().enforce();
    }
    ```

    `cargo test` reports it as `ignored` (doesn't gate); `cargo test --test structure -- --ignored`
    prints the full punch-list; deleting the `#[ignore]` flips it to hard-fail.

  Never leave a rule advisory forever — a warning that never becomes an error trains
  everyone to ignore it.

## How it works (the scan)

The mechanism, in one sentence: **each rule reads files under the roots it owns
(`src/`, and for `mod.rs`, `tests/`) and checks *where a file lives* against *what
it references* or *how it is named*.**

- `SourceTree` (in `source.rs`) locates the crate via `CARGO_MANIFEST_DIR` (so the
  test is independent of the working directory), walks `src/` or any configured
  roots for `.rs` files, reads them, and renders paths relative to the crate root.
- `SourceLine` classifies a single line: `is_comment()` (skip `//` lines so a comment
  mentioning another layer isn't a false hit) and `module_level_item()` (a column-0
  `struct`/`enum`/`union`/`impl` — trait members are indented, so a hit means a
  non-trait item at the top level of a `port.rs`).
- A `Rule` pairs a `description` with a `check`; `enforce()` collects `Vec<Violation>`
  and asserts it's empty, printing each `Violation` (which owns its own rendering).
- The test files are the spec: each test instantiates a named rule and calls
  `enforce()`.

**Deliberate gaps** (know what you do *not* catch):

- It matches `crate::<layer>` paths and `use <crate>` lines textually — it does not
  parse the full AST. A layer reached through a re-export alias, or `super::`
  path-climbing, can slip past. This is intentionally simple; the AST-accurate version
  is a `dylint` lint or the crate split below.
- It is bypassable (someone can delete a test). CI is what makes it a real gate.

## Customization knobs

- **Layers** — `constants.rs` owns the layer names and the forbidden lists. The lists
  encode the inward-only direction. If the project has an extra outermost wiring layer
  (e.g. `composition/`), add it and forbid every inner layer (and infrastructure) from
  importing it:

  ```rust
  pub const COMPOSITION_LAYER: &str = "composition";
  pub const DOMAIN_FORBIDDEN_LAYERS: &[&str] =
      &[APPLICATION_LAYER, INFRASTRUCTURE_LAYER, COMPOSITION_LAYER];
  pub const APPLICATION_FORBIDDEN_LAYERS: &[&str] = &[INFRASTRUCTURE_LAYER, COMPOSITION_LAYER];
  pub const INFRASTRUCTURE_FORBIDDEN_LAYERS: &[&str] = &[COMPOSITION_LAYER];
  ```

  then add an `infrastructure_layer` test in `layering.rs` mirroring the others.
- **Infrastructure crates** — extend `INFRASTRUCTURE_CRATES` to match what the project
  actually depends on. It can only ever flag a real `use`, so a generous list is safe.
- **NoOp exception** — `NOOP_STUB_MARKER` lets NoOp stubs live in `port.rs` per the
  structure skill. Rename or drop it if your project doesn't use that idiom.
- **`mod.rs` exception** — `MOD_FILE_ALLOWED_PATHS` owns the exact crate-relative
  paths where legacy module layout remains allowed. The default exception is only
  `tests/common/mod.rs`.
- **Concept-facade rule** — `ENFORCE_CONCEPT_FACADE` gates rule 6. Keep `true` for
  application crates (services, binaries, internal workspace members — set
  `publish = false` in their Cargo.toml so the intent is recorded). Set `false` when
  the crate is published to a registry: the module hierarchy is then legitimately
  public API (rust-project-structure, principle 14 "Crate scope"). On an existing
  codebase, prefer the `#[ignore]` ratchet over a wholesale enable.
- **New rules** — add a `Rule::*` constructor + a one-line test. The `SourceTree`/
  `SourceLine` primitives cover most "scan files / inspect lines" checks.

## Stronger enforcement: crate-per-layer (optional)

This skill is the **single-crate** gate — necessary because within one crate the Rust
compiler cannot forbid `use crate::infrastructure::…` inside `domain/` (module
visibility is hierarchical, not directional). The **compile-time** alternative is to
split each layer into its own crate in a Cargo workspace: `domain/Cargo.toml` simply
doesn't depend on `infrastructure`, so the import won't compile — unbypassable, no test
needed. That is a larger, separate refactor; the structure test gives ~95% of the
protection for a fraction of the cost and is the right default. Reach for the crate
split when you want the compiler, not a test, to be the gate.

## Compliance with the testing & code-style skills

This setup deliberately follows the other Rust skills, and any rule you add should too:

- **`rust-testing`** — all tests live under `tests/`; the test files contain only
  `use` + `mod … { #[test] should_… }` blocks (no module-scope helpers, no comments);
  every helper, constant, and type lives under `support/` split by concern.
- **`rust-code-style`** — descriptive names everywhere (incl. closures), magic strings
  extracted to `constants.rs`, `///` on the public surface.
- **`rust-design-idioms`** — `Violation` is a structured type with a `Display` impl
  rather than a pre-formatted `String`; errors aren't needed here (test helpers
  `panic!`, which is the correct failure mode for a test).
