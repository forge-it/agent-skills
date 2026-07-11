# Support Rules Implementation

This file contains the complete implementation for `tests/structure/support/rules.rs`. `/home/cristi/Projects/agent-skills/software-engineering/rust-architecture-test-setup/SKILL.md` is the normative source — the description of what each `Rule` constructor enforces and how the six rules map to the architecture invariants lives there (Step 2). This implementation is provided here for direct reference by agents setting up the architecture gate.

## rules.rs — Rule type, six named constructors, and enforce()

Target path: `tests/structure/support/rules.rs`

```rust
// tests/structure/support/rules.rs
//! The structure invariants, each modeled as a named `Rule` — a description
//! paired with the check that finds its violations. A test instantiates a rule
//! by its intention-revealing constructor and calls `enforce()`; what each rule
//! checks is stated by the constructor name and description, not buried inside a
//! scanning function.

use super::constants::{
    CRATE_PATH_PREFIX, DOMAIN_LAYER, ENFORCE_CONCEPT_FACADE, MOD_FILE_ALLOWED_PATHS,
    MOD_FILE_NAME, MOD_FILE_SEARCH_ROOTS, NOOP_STUB_MARKER, PORT_FILE_NAME, USE_KEYWORD,
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

    /// `port.rs` files hold trait definitions only — dataflow values belong in
    /// `model.rs`, construction-time tunables in `config.rs`, errors in
    /// `error.rs`. NoOp stubs may stay next to their trait
    /// (rust-project-structure: "NoOp stubs live close to the trait").
    pub fn port_files_hold_traits_only() -> Self {
        Self {
            description: "port.rs must hold traits only (data in model.rs, config in config.rs, errors in error.rs)"
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
                                    "`port.rs` holds traits only; move this `{keyword}` to model.rs, config.rs, or error.rs"
                                ),
                            ));
                        }
                    }
                }
                violations
            }),
        }
    }

    /// A module file that fronts a sibling folder (`order.rs` next to `order/`)
    /// is a facade: module docs, attributes, `mod <file>;` declarations,
    /// `pub mod <subfolder>;`, and `pub use <file>::*;` globs — nothing else.
    /// Layer module files (`src/<layer>.rs`) and adapter-family module files
    /// directly under `infrastructure/` are exempt: their children are
    /// addressable namespaces (rust-project-structure: "The Concept Module File
    /// Is a Facade"). Gated by `ENFORCE_CONCEPT_FACADE` — application crates
    /// only, never published libraries.
    pub fn concept_module_files_are_facades() -> Self {
        Self {
            description: "concept module files must hold only `mod` declarations and `pub use <file>::*;` globs"
                .to_string(),
            check: Box::new(|source_tree| {
                let mut violations = Vec::new();
                if !ENFORCE_CONCEPT_FACADE {
                    return violations;
                }
                for file in source_tree.rust_files() {
                    let Some(fronted_folder) = source_tree.fronted_folder(&file) else {
                        continue;
                    };
                    if source_tree.is_namespace_module_file(&file) {
                        continue;
                    }
                    let contents = source_tree.read(&file);
                    for (line_index, line) in contents.lines().enumerate() {
                        let source_line = SourceLine(line);
                        if line.trim().is_empty()
                            || source_line.is_comment()
                            || source_line.is_attribute()
                            || source_line.private_module_declaration().is_some()
                            || source_line.glob_reexport().is_some()
                        {
                            continue;
                        }
                        let message = match source_line.public_module_declaration() {
                            Some(subfolder) if fronted_folder.join(subfolder).is_dir() => continue,
                            Some(subfolder) => format!(
                                "`pub mod {subfolder};` exposes a file — declare `mod {subfolder};` and re-export with `pub use {subfolder}::*;`"
                            ),
                            None => "a concept module file holds only `mod` declarations and `pub use <file>::*;` globs"
                                .to_string(),
                        };
                        violations.push(Violation::at_line(
                            &source_tree.relative(&file),
                            line_index + 1,
                            line,
                            &message,
                        ));
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
