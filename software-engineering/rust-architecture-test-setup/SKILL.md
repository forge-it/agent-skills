---
name: rust-architecture-test-setup
description: One-time setup of a `tests/structure/` cargo-test gate for a Rust hexagonal-architecture project, so the layering invariants (dependencies point inward — domain → application → infrastructure) and the project-structure conventions (`port.rs` holds traits only, file names don't stutter, `mod.rs` stays out of `src/` and `tests/` except `tests/common/`, the domain stays framework-free) are enforced by `cargo test` — and therefore CI — instead of by review. Use when bootstrapping a new Rust hexagonal project's architecture enforcement, or adding it to an existing one. Assumes a layered hexagonal codebase (domain/application/infrastructure under `src/`).
vibe: Turns the architecture doc into a build that fails when someone crosses a layer.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.1"
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

Five rules, drawn from the two architecture skills:

1. **Dependencies point inward** — a file under `domain/` must not reference
   `application` or `infrastructure`; a file under `application/` must not reference
   `infrastructure`. (`rust-hexagonal-architecture`, "Dependencies Point Inward".)
2. **The domain is framework-free** — no file under `domain/` may `use` an
   infrastructure crate (`sqlx`, `axum`, …).
3. **`port.rs` holds traits only** — value types belong in `model.rs`, errors in
   `error.rs`. (`rust-project-structure`, "Data Types Live in `model.rs`".)
4. **File names don't stutter** — `backup/executor.rs`, never
   `backup/backup_executor.rs`. (`rust-project-structure`, "Short Module Names".)
5. **No legacy `mod.rs` layout** — `mod.rs` is forbidden under `src/` and `tests/`,
   except for the shared test helper entry point `tests/common/mod.rs`.

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

```rust
//! Shared values for the structure invariants: the layer names, the inward-only
//! dependency rules, the infrastructure crates the domain must never import, the
//! legacy module-layout exceptions, and the magic strings the checks match
//! against.

/// The architectural layers, by their directory name under `src/`.
pub const DOMAIN_LAYER: &str = "domain";
pub const APPLICATION_LAYER: &str = "application";
pub const INFRASTRUCTURE_LAYER: &str = "infrastructure";

/// Layers `domain/` must never reference (the domain depends on nothing).
pub const DOMAIN_FORBIDDEN_LAYERS: &[&str] = &[APPLICATION_LAYER, INFRASTRUCTURE_LAYER];

/// Layers `application/` must never reference.
pub const APPLICATION_FORBIDDEN_LAYERS: &[&str] = &[INFRASTRUCTURE_LAYER];

/// External infrastructure crates that must not leak into the framework-free
/// domain. Extend this list to match the project's actual infrastructure
/// dependencies.
pub const INFRASTRUCTURE_CRATES: &[&str] = &[
    "sqlx",
    "sea_orm",
    "diesel",
    "axum",
    "actix_web",
    "hyper",
    "tonic",
    "reqwest",
    "tokio_postgres",
    "mongodb",
    "mysql_async",
    "redis",
    "kube",
    "lapin",
    "rdkafka",
    "aws_sdk_s3",
    "object_store",
];

/// File name that, by convention, holds a concept's trait definitions (ports).
pub const PORT_FILE_NAME: &str = "port.rs";

/// Legacy Rust module-layout file name. It is forbidden except at explicitly
/// allowed paths.
pub const MOD_FILE_NAME: &str = "mod.rs";

/// Roots scanned by the legacy `mod.rs` layout rule.
pub const MOD_FILE_SEARCH_ROOTS: &[&str] = &["src", "tests"];

/// Exact crate-relative paths where `mod.rs` remains allowed.
pub const MOD_FILE_ALLOWED_PATHS: &[&str] = &["tests/common/mod.rs"];

/// Marker identifying NoOp stub types, which may live next to their trait.
pub const NOOP_STUB_MARKER: &str = "NoOp";

/// Path prefix that references another module by its crate-absolute path.
pub const CRATE_PATH_PREFIX: &str = "crate::";

/// Keyword that introduces a `use` import statement.
pub const USE_KEYWORD: &str = "use";
```

### `tests/structure/support/source.rs`

```rust
//! Source-reading primitives for the structure tests: the source tree (locate
//! `src/` and other checked roots, walk them, read files, relativize paths) and
//! single-line classifiers. Resolved from `CARGO_MANIFEST_DIR`, so the working
//! directory does not matter.

use std::path::{Path, PathBuf};

/// The crate's source tree: locates `src/`, walks it for `.rs` files, reads
/// them, and renders paths relative to the crate root.
pub(crate) struct SourceTree {
    crate_root: PathBuf,
}

impl SourceTree {
    pub(crate) fn new() -> Self {
        Self {
            crate_root: PathBuf::from(env!("CARGO_MANIFEST_DIR")),
        }
    }

    pub(crate) fn rust_files(&self) -> Vec<PathBuf> {
        self.rust_files_under(&self.crate_root.join("src"))
    }

    pub(crate) fn rust_files_in(&self, layer: &str) -> Vec<PathBuf> {
        self.rust_files_under(&self.crate_root.join("src").join(layer))
    }

    pub(crate) fn rust_files_in_roots(&self, roots: &[&str]) -> Vec<PathBuf> {
        let mut files = Vec::new();
        for root in roots {
            files.extend(self.rust_files_under(&self.crate_root.join(root)));
        }
        files.sort();
        files
    }

    pub(crate) fn read(&self, path: &Path) -> String {
        std::fs::read_to_string(path)
            .unwrap_or_else(|error| panic!("failed to read {}: {error}", path.display()))
    }

    pub(crate) fn relative(&self, path: &Path) -> String {
        path.strip_prefix(&self.crate_root)
            .unwrap_or(path)
            .display()
            .to_string()
    }

    pub(crate) fn relative_unix(&self, path: &Path) -> String {
        path.strip_prefix(&self.crate_root)
            .unwrap_or(path)
            .components()
            .map(|component| component.as_os_str().to_string_lossy().into_owned())
            .collect::<Vec<_>>()
            .join("/")
    }

    fn rust_files_under(&self, directory: &Path) -> Vec<PathBuf> {
        let mut files = Vec::new();
        Self::collect(directory, &mut files);
        files.sort();
        files
    }

    fn collect(directory: &Path, files: &mut Vec<PathBuf>) {
        let Ok(entries) = std::fs::read_dir(directory) else {
            return;
        };
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                Self::collect(&path, files);
            } else if path.extension().and_then(|extension| extension.to_str()) == Some("rs") {
                files.push(path);
            }
        }
    }
}

/// A single source line, with the classification queries the rules need.
pub(crate) struct SourceLine<'line>(pub(crate) &'line str);

impl SourceLine<'_> {
    pub(crate) fn is_comment(&self) -> bool {
        self.0.trim_start().starts_with("//")
    }

    /// Detects a module-level (column-0) data/impl item. Trait members are
    /// indented and therefore ignored, so a hit means a non-trait item sits at
    /// the top level of a `port.rs`.
    pub(crate) fn module_level_item(&self) -> Option<&'static str> {
        let line = self.0;
        if line.starts_with(|character: char| character == ' ' || character == '\t') {
            return None;
        }
        let mut rest = line;
        if let Some(after_pub) = rest.strip_prefix("pub") {
            if after_pub.starts_with('(') {
                let Some(close_paren) = after_pub.find(')') else {
                    return None;
                };
                rest = after_pub[close_paren + 1..].trim_start();
            } else if after_pub.starts_with(|character: char| character == ' ' || character == '\t') {
                rest = after_pub.trim_start();
            }
        }
        for keyword in ["struct", "enum", "union", "impl"] {
            if let Some(after_keyword) = rest.strip_prefix(keyword) {
                if after_keyword.starts_with(|character: char| matches!(character, ' ' | '\t' | '<' | '(')) {
                    return Some(keyword);
                }
            }
        }
        None
    }
}
```

### `tests/structure/support/violation.rs`

```rust
//! A single structure violation: where it is, what is wrong, and how it renders
//! in a test-failure message.

use std::fmt;

/// A structure-rule violation. Either tied to a specific line (carrying the
/// offending source) or to a file as a whole.
pub(crate) struct Violation {
    file: String,
    line: Option<usize>,
    source: Option<String>,
    message: String,
}

impl Violation {
    /// A violation at a specific 1-based line, carrying the offending source.
    pub(crate) fn at_line(file: &str, line: usize, source: &str, message: &str) -> Self {
        Self {
            file: file.to_string(),
            line: Some(line),
            source: Some(source.trim().to_string()),
            message: message.to_string(),
        }
    }

    /// A violation about a file as a whole (no specific line).
    pub(crate) fn in_file(file: &str, message: &str) -> Self {
        Self {
            file: file.to_string(),
            line: None,
            source: None,
            message: message.to_string(),
        }
    }
}

impl fmt::Display for Violation {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match (self.line, &self.source) {
            (Some(line), Some(source)) => {
                write!(formatter, "{}:{line}: {} -> {source}", self.file, self.message)
            }
            _ => write!(formatter, "{}: {}", self.file, self.message),
        }
    }
}
```

### `tests/structure/support/rules.rs`

```rust
//! The structure invariants, each modeled as a named `Rule` — a description
//! paired with the check that finds its violations. A test instantiates a rule
//! by its intention-revealing constructor and calls `enforce()`; what each rule
//! checks is stated by the constructor name and description, not buried inside a
//! scanning function.

use super::constants::{
    CRATE_PATH_PREFIX, DOMAIN_LAYER, MOD_FILE_ALLOWED_PATHS, MOD_FILE_NAME,
    MOD_FILE_SEARCH_ROOTS, NOOP_STUB_MARKER, PORT_FILE_NAME, USE_KEYWORD,
};
use super::source::{SourceLine, SourceTree};
use super::violation::Violation;

/// A named structure invariant: a human-readable description paired with the
/// check that produces the violations.
pub struct Rule {
    description: String,
    check: Box<dyn Fn(&SourceTree) -> Vec<Violation>>,
}

impl Rule {
    /// Files under `layer` must not reference any of `forbidden_layers` through
    /// a `crate::<layer>` path — the one-way (inward) dependency direction.
    pub fn layer_depends_inward_only(
        layer: &'static str,
        forbidden_layers: &'static [&'static str],
    ) -> Self {
        Self {
            description: format!("`{layer}` must not import {}", forbidden_layers.join("/")),
            check: Box::new(move |source_tree| {
                let mut violations = Vec::new();
                for file in source_tree.rust_files_in(layer) {
                    let contents = source_tree.read(&file);
                    for (line_index, line) in contents.lines().enumerate() {
                        if SourceLine(line).is_comment() {
                            continue;
                        }
                        for forbidden_layer in forbidden_layers {
                            if line.contains(&format!("{CRATE_PATH_PREFIX}{forbidden_layer}")) {
                                violations.push(Violation::at_line(
                                    &source_tree.relative(&file),
                                    line_index + 1,
                                    line,
                                    &format!("`{layer}` must not depend on `{forbidden_layer}`"),
                                ));
                            }
                        }
                    }
                }
                violations
            }),
        }
    }

    /// `domain/` must not `use` any infrastructure crate — the domain stays
    /// framework-free.
    pub fn domain_free_of_infrastructure_crates(
        infrastructure_crates: &'static [&'static str],
    ) -> Self {
        Self {
            description: "domain must stay framework-free (no infrastructure crates)".to_string(),
            check: Box::new(move |source_tree| {
                let mut violations = Vec::new();
                for file in source_tree.rust_files_in(DOMAIN_LAYER) {
                    let contents = source_tree.read(&file);
                    for (line_index, line) in contents.lines().enumerate() {
                        let trimmed = line.trim_start();
                        for crate_name in infrastructure_crates {
                            let imports_crate = trimmed
                                .starts_with(&format!("{USE_KEYWORD} {crate_name}::"))
                                || trimmed.starts_with(&format!("{USE_KEYWORD} {crate_name} "))
                                || trimmed == format!("{USE_KEYWORD} {crate_name};").as_str();
                            if imports_crate {
                                violations.push(Violation::at_line(
                                    &source_tree.relative(&file),
                                    line_index + 1,
                                    line,
                                    "domain must stay framework-free",
                                ));
                            }
                        }
                    }
                }
                violations
            }),
        }
    }

    /// File names must not repeat their parent directory — `backup/executor.rs`,
    /// never `backup/backup_executor.rs`.
    pub fn file_names_do_not_repeat_parent() -> Self {
        Self {
            description: "file names must not repeat the parent directory".to_string(),
            check: Box::new(|source_tree| {
                let mut violations = Vec::new();
                for file in source_tree.rust_files() {
                    let (Some(stem), Some(parent)) = (
                        file.file_stem().and_then(|stem| stem.to_str()),
                        file.parent()
                            .and_then(|parent| parent.file_name())
                            .and_then(|name| name.to_str()),
                    ) else {
                        continue;
                    };
                    if stem.starts_with(&format!("{parent}_")) {
                        violations.push(Violation::in_file(
                            &source_tree.relative(&file),
                            &format!("file name repeats parent `{parent}/` -> drop the `{parent}_` prefix"),
                        ));
                    }
                }
                violations
            }),
        }
    }

    /// `mod.rs` is the legacy Rust module layout. It is forbidden under `src/`
    /// and `tests/` except for explicitly allowed shared test-helper entry
    /// points such as `tests/common/mod.rs`.
    pub fn mod_files_are_limited_to_allowed_paths() -> Self {
        Self {
            description: "mod.rs files are forbidden except in allowed paths".to_string(),
            check: Box::new(|source_tree| {
                let mut violations = Vec::new();
                let allowed_paths = MOD_FILE_ALLOWED_PATHS.join(", ");
                for file in source_tree.rust_files_in_roots(MOD_FILE_SEARCH_ROOTS) {
                    if file.file_name().and_then(|name| name.to_str()) != Some(MOD_FILE_NAME) {
                        continue;
                    }
                    let relative_file = source_tree.relative_unix(&file);
                    if MOD_FILE_ALLOWED_PATHS.contains(&relative_file.as_str()) {
                        continue;
                    }
                    violations.push(Violation::in_file(
                        &relative_file,
                        &format!("`mod.rs` is only allowed at {allowed_paths}"),
                    ));
                }
                violations
            }),
        }
    }

    /// `port.rs` files hold trait definitions only — value types belong in
    /// `model.rs`, errors in `error.rs`. NoOp stubs may stay next to their trait
    /// (rust-project-structure: "NoOp stubs live close to the trait").
    pub fn port_files_hold_traits_only() -> Self {
        Self {
            description: "port.rs must hold traits only (data in model.rs, errors in error.rs)"
                .to_string(),
            check: Box::new(|source_tree| {
                let mut violations = Vec::new();
                for file in source_tree.rust_files() {
                    if file.file_name().and_then(|name| name.to_str()) != Some(PORT_FILE_NAME) {
                        continue;
                    }
                    let contents = source_tree.read(&file);
                    for (line_index, line) in contents.lines().enumerate() {
                        if line.contains(NOOP_STUB_MARKER) {
                            continue;
                        }
                        if let Some(keyword) = SourceLine(line).module_level_item() {
                            violations.push(Violation::at_line(
                                &source_tree.relative(&file),
                                line_index + 1,
                                line,
                                &format!(
                                    "`port.rs` holds traits only; move this `{keyword}` to model.rs/error.rs"
                                ),
                            ));
                        }
                    }
                }
                violations
            }),
        }
    }

    /// Source locations violating this rule.
    pub(crate) fn violations(&self) -> Vec<Violation> {
        (self.check)(&SourceTree::new())
    }

    /// Runs the rule against the source tree and fails the test on any violation.
    pub fn enforce(&self) {
        let violations = self.violations();
        let report = violations
            .iter()
            .map(|violation| violation.to_string())
            .collect::<Vec<_>>()
            .join("\n");
        assert!(
            violations.is_empty(),
            "{}: {} violation(s)\n\n{report}\n",
            self.description,
            violations.len(),
        );
    }
}
```

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
