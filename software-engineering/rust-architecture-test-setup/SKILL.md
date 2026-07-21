---
name: rust-architecture-test-setup
description: One-time setup of a `tests/structure/` cargo-test gate for a Rust hexagonal-architecture project, so the layering invariants (dependencies point inward — domain → application → infrastructure, and no layer imports the composition root), the project-structure conventions (`port.rs` holds traits only, file names don't stutter, `mod.rs` stays out of `src/` and `tests/` except `tests/common/`, concept module files stay glob facades in application crates, the domain stays framework-free), the composition-root wiring seam (concrete adapter assembly never escapes `src/composition/`), workspace dependency boundaries (a shared library crate stays consumer-free; a worker binary stays core-free and free of direct database drivers), and generic-machinery vocabulary (designated generic modules never name product concepts) are enforced by `cargo test` — and therefore CI — instead of by review. Use when bootstrapping a new Rust hexagonal project's architecture enforcement, or adding it to an existing one. Assumes a layered hexagonal codebase (domain/application/infrastructure under `src/`).
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

Ten rules. Rules 1–6 come from the two architecture skills; rules 7–10 come from
the composition-root wiring seam and the workspace boundaries that emerged once
the reference codebase grew a worker fleet and shared library crates (its
ADR-R06/ADR-R11 era) — decisions that are far cheaper to enforce from commit 1
than to retrofit:

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
7. **No layer imports the composition root** — `composition/` is the outermost
   wiring seam (see `patterns/project_structure/composition_pattern.md`): it may
   import everything, and nothing may import it. In particular
   `infrastructure/` implements adapters but never *assembles* them — a
   `use crate::composition::…` inside any layer is a violation. On a crate with
   no `composition` module the rule is inert (nothing can reference it), so it
   is safe to keep on everywhere.
8. **Concrete adapter assembly stays in the composition root** — designated
   concrete adapter/provider types are constructed (`Type::new(…)`) only under
   `src/composition/`; outside composition (and the implementation modules that
   define them) their names may not appear at all, and the implementation
   modules may not hide them behind `type` aliases or `use … as` re-exports.
   Driven by marker lists in `constants.rs` that start empty and grow as the
   project designates composition-only types.
9. **Workspace dependency boundaries hold** — (workspace projects) a crate's
   `Cargo.toml` must not declare designated forbidden dependencies: a shared
   library crate never depends on its consumers (it stays core-free and
   contracts-free), and a worker binary never depends on the core crate or a
   direct database driver. The check parses the manifest as TOML, so package
   renames (`core_alias = { package = "my-core" }`), workspace-inherited
   (`workspace = true`) and target-specific dependency tables are all caught.
10. **Generic machinery stays concept-free** — a designated generic module
    (e.g. a worker's `application/task/` runtime machinery) must not name
    product concepts (`backup`, `restore`, …), so adding a product feature
    never widens the generic layer. Driven by path/marker lists that start
    empty (inert until populated).

It assumes the canonical hexagonal layers `domain/`, `application/`,
`infrastructure/` under `src/`, plus the `composition` wiring root. Adapt the
layer set in `constants.rs` (see [Customization](#customization-knobs)).

## Step 1 — Confirm your layers

Open `src/` and confirm the top-level layer directories. The default rules assume
`domain/`, `application/`, `infrastructure/`, and the wiring root `composition`
(`src/composition.rs` + `src/composition/`, per the composition pattern). The
forbidden lists in `constants.rs` encode the inward-only direction including
composition; a crate that wires everything in `bin/main.rs` and has no
`composition` module keeps the same constants — the composition rules are simply
inert there.

## Step 2 — Create the structure test

`cargo` auto-discovers `tests/<name>.rs` as a test target and resolves its inline
`mod <name> { … }` tree into `tests/<name>/…`. So the files are:

```
tests/
├── structure.rs                 # entry: declares the module tree
└── structure/
    ├── assembly.rs              # tests-only: composition-only assembly rules + their rule-logic tests
    ├── facade.rs                # tests-only: concept-module-file facade rule
    ├── layering.rs              # tests-only: dependency-direction rules (incl. composition seam)
    ├── naming.rs                # tests-only: file-name stutter + mod.rs rules
    ├── ports.rs                 # tests-only: port.rs-traits-only rule
    ├── vocabulary.rs            # tests-only: generic-machinery-stays-concept-free rule
    ├── workspace_deps.rs        # tests-only: manifest dependency-boundary rule (workspace projects)
    └── support/
        ├── constants.rs         # layer names, forbidden lists, marker lists, magic strings
        ├── manifest.rs          # Cargo.toml dependency-gate scanner (TOML-backed)
        ├── source.rs            # SourceTree + SourceLine (scanning primitives)
        ├── rules.rs             # the Rule type + the named invariants
        └── violation.rs         # the Violation finding type
```

This layout follows `rust-testing`: the test files contain **only** tests; every
helper, constant, and type lives under `support/` (Sections 15–16).

The manifest gate parses `Cargo.toml` as TOML, so add the parser to the test
dependencies (verify the current version on crates.io before pinning):

```toml
# Cargo.toml
[dev-dependencies]
toml = "0.9"
```

On a single-crate project with no workspace boundaries to guard, omit
`workspace_deps.rs` and `support/manifest.rs` (and the `toml` dependency)
entirely — and with them the two module declarations that mount them: drop
`mod workspace_deps;` from `tests/structure.rs` and `pub mod manifest;` from
`tests/structure/support.rs`, or the crate will not compile.

### `tests/structure.rs`

```rust
#![allow(clippy::all, clippy::pedantic, clippy::nursery)]

mod structure {
    pub mod support;

    mod assembly;
    mod facade;
    mod layering;
    mod naming;
    mod ports;
    mod vocabulary;
    mod workspace_deps;
}
```

### `tests/structure/support.rs`

```rust
//! Support for the structure tests. Per the rust-testing skill (Section 15/16)
//! the test files contain only tests; the rules, scanning utilities, violation
//! type, and constants live here.

pub mod constants;
pub mod manifest;
pub mod rules;
pub mod source;
pub mod violation;
```

### `tests/structure/support/constants.rs`

**Before writing `tests/structure/support/constants.rs`, read `references/support-scanning-primitives.md`** — it contains the complete implementations of all four support files (`constants.rs`, `source.rs`, `violation.rs`, and `manifest.rs`); write all four in one pass from this single reference.

### `tests/structure/support/source.rs`

Covered by `references/support-scanning-primitives.md` (see `constants.rs` above).

### `tests/structure/support/violation.rs`

Covered by `references/support-scanning-primitives.md` (see `constants.rs` above).

### `tests/structure/support/manifest.rs`

Covered by `references/support-scanning-primitives.md` (see `constants.rs` above).

### `tests/structure/support/rules.rs`

**Before writing `tests/structure/support/rules.rs`, read `references/support-rules-implementation.md`** — it contains the complete `Rule` type, all named constructors, the rule-logic helpers, and the `enforce()` method.

### `tests/structure/layering.rs`

```rust
use super::support::constants::{
    APPLICATION_FORBIDDEN_LAYERS, APPLICATION_LAYER, DOMAIN_FORBIDDEN_LAYERS, DOMAIN_LAYER,
    INFRASTRUCTURE_CRATES, INFRASTRUCTURE_FORBIDDEN_LAYERS, INFRASTRUCTURE_LAYER,
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
    fn should_not_depend_on_infrastructure_or_composition() {
        Rule::layer_depends_inward_only(APPLICATION_LAYER, APPLICATION_FORBIDDEN_LAYERS).enforce();
    }
}

mod infrastructure_layer {
    use super::*;

    #[test]
    fn should_not_depend_on_composition() {
        Rule::layer_depends_inward_only(INFRASTRUCTURE_LAYER, INFRASTRUCTURE_FORBIDDEN_LAYERS)
            .enforce();
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

### `tests/structure/assembly.rs`

The enforcement tests run the composition-only assembly rules against the source
tree; the rule-logic tests exercise the scanners against inline snippets, so a
regression in the scanner itself (e.g. it stops catching aliases) is caught even
while the codebase is clean:

```rust
use super::support::rules::Rule;

mod concrete_adapter_assembly {
    use super::*;

    #[test]
    fn should_construct_designated_adapters_only_in_composition() {
        Rule::concrete_assembly_is_limited_to_composition().enforce();
    }

    #[test]
    fn should_name_designated_adapter_types_only_in_composition_or_their_implementations() {
        Rule::concrete_types_are_limited_to_composition().enforce();
    }

    #[test]
    fn should_not_hide_designated_adapter_types_behind_aliases_in_implementations() {
        Rule::adapter_implementations_do_not_hide_concrete_types().enforce();
    }
}

mod assembly_rule_logic {
    use super::*;

    #[test]
    fn should_report_a_construction_call_found_in_a_source_snippet() {
        let violations = Rule::assembly_violations_in_source(
            "let provider = PostgresOrderRepository::new(pool);",
            &["PostgresOrderRepository::new("],
        );

        assert_eq!(violations, vec!["PostgresOrderRepository::new("]);
    }

    #[test]
    fn should_report_a_type_hidden_behind_an_alias() {
        let violations = Rule::type_alias_violations_in_source(
            "type Repository = PostgresOrderRepository<Postgres>;",
            &["PostgresOrderRepository"],
        );

        assert_eq!(violations, vec!["PostgresOrderRepository"]);
    }

    #[test]
    fn should_ignore_a_commented_construction_expression() {
        let violations = Rule::assembly_violations_in_source(
            "// PostgresOrderRepository::new(pool);",
            &["PostgresOrderRepository::new("],
        );

        assert!(violations.is_empty());
    }
}
```

### `tests/structure/vocabulary.rs`

Inert until `GENERIC_MODULE_PATHS` / `GENERIC_MODULE_FORBIDDEN_MARKERS` in
`constants.rs` are populated (see [Customization](#customization-knobs)):

```rust
use super::support::rules::Rule;

mod generic_machinery {
    use super::*;

    #[test]
    fn should_not_name_product_concepts() {
        Rule::generic_module_stays_concept_free().enforce();
    }
}
```

### `tests/structure/workspace_deps.rs`

Workspace projects only. Each crate that owns a dependency boundary gets this
test with its own forbidden list — see
[Multi-crate workspaces](#multi-crate-workspaces-where-each-gate-lives) for
which crate owns which boundary:

```rust
use super::support::constants::{CRATE_MANIFEST, MANIFEST_FORBIDDEN_DEPS, WORKSPACE_MANIFEST};
use super::support::manifest::forbidden_dependency_violations;
use super::support::source::read_crate_file;

mod manifest_dependency_boundary {
    use super::*;

    #[test]
    fn should_not_declare_forbidden_dependencies() {
        let manifest = read_crate_file(CRATE_MANIFEST);
        let workspace_manifest = read_crate_file(WORKSPACE_MANIFEST);
        let violations = forbidden_dependency_violations(
            CRATE_MANIFEST,
            WORKSPACE_MANIFEST,
            &manifest,
            &workspace_manifest,
            MANIFEST_FORBIDDEN_DEPS,
        );
        assert!(
            violations.is_empty(),
            "this crate must not depend on the forbidden packages {MANIFEST_FORBIDDEN_DEPS:?}.\nviolations:\n{}",
            violations.join("\n")
        );
    }
}
```

## Step 3 — Wire the gate

Add `cargo test --test structure` to CI (see `ci-setup`). Give the project's
task runner a recipe so it runs with the rest of the suite — with `just` (see
`justfile-setup`):

```just
# justfile
structure:
    cargo test --test structure

check: format clippy structure test
```

or with `cargo-make`:

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
blocks the merge. Without that CI step the rules only report locally. On a
workspace, `cargo test --workspace --test structure` fails if any member lacks
the target, so run each crate's gate via its own recipe line (or plain
`cargo test --workspace`, which runs every discovered test target).

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

For the composition-seam rule, probe an infrastructure file that imports the
wiring root:

```bash
printf 'use crate::composition::Services;\n' > src/infrastructure/__probe.rs
cargo test --test structure   # expect: infrastructure_layer::should_not_depend_on_composition fails
rm src/infrastructure/__probe.rs
```

The assembly rules are probed the same way once their marker lists are populated
(drop a `<Marker>::new(…)` line in a file outside `src/composition/`); until the
lists have entries the enforcement tests are inert, but the `assembly_rule_logic`
tests still prove the scanners work. For the manifest rule, temporarily add one
of the forbidden packages to `[dev-dependencies]` and confirm
`manifest_dependency_boundary::should_not_declare_forbidden_dependencies` fails,
then remove it.

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

  The marker-driven rules (8–10) need no ratchet on an existing codebase: their
  lists start empty, so they enforce nothing until you designate the first
  composition-only type, forbidden dependency, or generic module — designate them
  one at a time as you clean each one up.

## How it works (the scan)

The mechanism, in one sentence: **each rule reads the files it owns (`src/`;
`tests/` for the `mod.rs` rule; `Cargo.toml` for the manifest rule) and checks
*where a file lives* against *what it references*, *how it is named*, or *what
it declares*.**

- `SourceTree` (in `source.rs`) locates the crate via `CARGO_MANIFEST_DIR` (so the
  test is independent of the working directory), walks `src/` or any configured
  roots for `.rs` files, reads them, and renders paths relative to the crate root.
- `SourceLine` classifies a single line: `is_comment()` (skip `//` lines so a comment
  mentioning another layer isn't a false hit), `code()` (the portion before any
  trailing `//` comment, which is what the assembly scanners match against), and
  `module_level_item()` (a column-0 `struct`/`enum`/`union`/`impl` — trait members
  are indented, so a hit means a non-trait item at the top level of a `port.rs`).
- `manifest.rs` parses `Cargo.toml` as TOML and resolves each dependency
  declaration to its *effective* package name — following `package = "…"`
  renames, `workspace = true` inheritance (through the workspace manifest), and
  `[target.'…'.dependencies]` tables — before matching it against the forbidden
  list. A lexical grep would miss all three.
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

- **Layers** — `constants.rs` owns the layer names and the forbidden lists; the
  lists encode the inward-only direction, and the defaults already include the
  `composition` wiring root as the outermost element (forbidden to every other
  layer). If the project renames a layer or adds another one, adjust the names
  and lists and mirror the per-layer tests in `layering.rs`.
- **Infrastructure crates** — extend `INFRASTRUCTURE_CRATES` to match what the project
  actually depends on. It can only ever flag a real `use`, so a generous list is safe.
- **Assembly markers** — `COMPOSITION_ONLY_CONSTRUCTION_MARKERS` (exact
  constructor-call strings, e.g. `"PostgresOrderRepository::new("`),
  `COMPOSITION_ONLY_TYPE_MARKERS` (the bare type names), and
  `ADAPTER_IMPLEMENTATION_PATHS` (the crate-relative files that legitimately
  define those types) drive rule 8. All three start empty — the rule costs
  nothing until the project designates its first composition-only adapter.
  Whenever a new concrete provider/adapter family is added, extend all three in
  the same change. `COMPOSITION_PATHS` owns what counts as "inside composition"
  (default `src/composition.rs` + `src/composition/`).
- **Forbidden dependencies** — `MANIFEST_FORBIDDEN_DEPS` drives rule 9 and is
  per-crate: in a worker binary list the core crate and every direct database
  driver family (`sqlx`, `tokio-postgres`, `diesel`, `sea-orm`, …); in a shared
  library crate list its consumers (the core crate, the wire-contracts crate) so
  the dependency direction can never invert. Empty list = rule inert.
- **Generic-module vocabulary** — rule 10 activates when you populate
  `GENERIC_MODULE_PATHS` (e.g. `"src/application/task/"` plus its facade
  `"src/application/task.rs"`) and `GENERIC_MODULE_FORBIDDEN_MARKERS` (the
  lowercase product-concept words, e.g. `"backup"`, `"restore"`). Typical use:
  a worker's generic task runtime must never name the product operations it
  dispatches, so adding a product feature never widens the generic layer.
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

## Multi-crate workspaces: where each gate lives

On a workspace (see `rust-workspace-setup`), the gate is **per crate**, and each
crate carries only the rules that guard a boundary it owns:

- **Every layered binary crate** (the API core, the worker) gets the full
  `tests/structure/` target described above, each with its own constants —
  the worker's manifest gate forbids the core crate and every direct database
  driver (the worker is stateless and owns no persistence; see
  `patterns/scalability/worker_pattern.md`), while the core's gate carries the
  layering, assembly, and facade rules.
- **Every shared library crate that must stay consumer-free** (an execution
  library both the core and the worker call into, a wire-contracts crate) gets
  at least an in-crate `tests/structure/` with the manifest gate, forbidding its
  consumers — that is what keeps the dependency direction `core → library`
  permanent instead of aspirational.
- **The in-crate gate is the source of truth** for a crate's forbidden list. A
  consumer crate may *mirror* the same list in its own gate for
  defense-in-depth; if it does, document that the two lists must stay identical
  and which file is authoritative.

This is how the reference codebase runs it: the core, the worker, and the shared
execution crate each carry their own `tests/structure/` target, and
`cargo test --workspace` runs all of them.

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
  every helper, constant, and type lives under `support/` split by concern. The
  `assembly_rule_logic` tests in `assembly.rs` are ordinary tests *of* the support
  helpers (fed inline snippets), not helpers themselves — they comply.
- **`rust-code-style`** — descriptive names everywhere (incl. closures), magic strings
  extracted to `constants.rs`, `///` on the public surface.
- **`rust-design-idioms`** — `Violation` is a structured type with a `Display` impl
  rather than a pre-formatted `String`; errors aren't needed here (test helpers
  `panic!`, which is the correct failure mode for a test).
