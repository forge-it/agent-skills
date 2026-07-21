# Support Scanning Primitives

This file contains the complete implementations for `tests/structure/support/constants.rs`, `tests/structure/support/source.rs`, `tests/structure/support/violation.rs`, and `tests/structure/support/manifest.rs`. `/home/cristi/Projects/agent-skills/software-engineering/rust-architecture-test-setup/SKILL.md` is the normative source — the rules for when and how the scanning primitives are used live there (Step 2). These implementations are provided here for direct reference by agents setting up the architecture gate.

## constants.rs — Layer names, forbidden lists, and shared magic strings

Target path: `tests/structure/support/constants.rs`

```rust
// tests/structure/support/constants.rs
//! Shared values for the structure invariants: the layer names, the inward-only
//! dependency rules, the infrastructure crates the domain must never import, the
//! legacy module-layout exceptions, and the magic strings the checks match
//! against.

/// The architectural layers, by their directory name under `src/`. The
/// composition root (`src/composition.rs` + `src/composition/`) is the
/// outermost wiring seam: it may import every layer, and no layer may import
/// it. On a crate without a `composition` module these rules are inert.
pub const DOMAIN_LAYER: &str = "domain";
pub const APPLICATION_LAYER: &str = "application";
pub const INFRASTRUCTURE_LAYER: &str = "infrastructure";
pub const COMPOSITION_LAYER: &str = "composition";

/// Layers `domain/` must never reference (the domain depends on nothing).
pub const DOMAIN_FORBIDDEN_LAYERS: &[&str] =
    &[APPLICATION_LAYER, INFRASTRUCTURE_LAYER, COMPOSITION_LAYER];

/// Layers `application/` must never reference.
pub const APPLICATION_FORBIDDEN_LAYERS: &[&str] = &[INFRASTRUCTURE_LAYER, COMPOSITION_LAYER];

/// Layers `infrastructure/` must never reference. Infrastructure implements
/// adapters; it never assembles them — assembly is the composition root's job.
pub const INFRASTRUCTURE_FORBIDDEN_LAYERS: &[&str] = &[COMPOSITION_LAYER];

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

/// Gates the concept-facade rule: a `<name>.rs` fronting a sibling `<name>/`
/// folder must hold only module docs, `mod` declarations, `pub mod` for
/// subfolders, and `pub use <file>::*;` globs. Enable for application crates —
/// services, binaries, and workspace members consumed only inside the
/// repository (set `publish = false` in their Cargo.toml). Disable for a crate
/// published to a registry: there the module hierarchy is legitimately public
/// API and a glob facade is a semver hazard.
pub const ENFORCE_CONCEPT_FACADE: bool = true;

/// Path prefix that references another module by its crate-absolute path.
pub const CRATE_PATH_PREFIX: &str = "crate::";

/// Keyword that introduces a `use` import statement.
pub const USE_KEYWORD: &str = "use";

/// What counts as "inside the composition root" for the assembly rules.
/// Entries ending in `/` are prefixes; other entries are exact file paths.
pub const COMPOSITION_PATHS: &[&str] = &["src/composition.rs", "src/composition/"];

/// Exact constructor-call strings of concrete adapter/provider types whose
/// assembly is a composition-root concern (e.g. `"PostgresOrderRepository::new("`).
/// Starts empty; extend it (together with the two lists below, in the same
/// change) whenever the project designates a new composition-only type.
pub const COMPOSITION_ONLY_CONSTRUCTION_MARKERS: &[&str] = &[];

/// Bare type names of those concrete adapters. Outside the composition root and
/// the implementation modules below, these names may not appear at all — not as
/// imports, not as aliases, not in signatures.
pub const COMPOSITION_ONLY_TYPE_MARKERS: &[&str] = &[];

/// Crate-relative source files that legitimately define the concrete types
/// above (their implementation modules). They may name their own types, but may
/// not hide them behind `type` aliases or `use … as` re-exports.
pub const ADAPTER_IMPLEMENTATION_PATHS: &[&str] = &[];

/// This crate's manifest, and the workspace root manifest that `workspace = true`
/// dependency declarations inherit from. Adjust the relative depth per member:
/// `../Cargo.toml` for a top-level member, `../../Cargo.toml` for `crates/<name>`.
pub const CRATE_MANIFEST: &str = "Cargo.toml";
pub const WORKSPACE_MANIFEST: &str = "../Cargo.toml";

/// Effective package names this crate's Cargo.toml must never declare a
/// dependency on. Per-crate: a worker binary lists the core crate and every
/// direct database driver family (e.g. "my-core", "sqlx", "tokio-postgres",
/// "diesel", "sea-orm"); a shared library crate lists its consumers so the
/// dependency direction can never invert. Empty list = rule inert.
pub const MANIFEST_FORBIDDEN_DEPS: &[&str] = &[];

/// Generic-machinery vocabulary rule (opt-in). `GENERIC_MODULE_PATHS` entries
/// ending in `/` are prefixes, others exact files (e.g. "src/application/task/"
/// plus its facade "src/application/task.rs"); the markers are the lowercase
/// product-concept words the generic module must never mention. Both empty by
/// default = rule inert.
pub const GENERIC_MODULE_PATHS: &[&str] = &[];
pub const GENERIC_MODULE_FORBIDDEN_MARKERS: &[&str] = &[];
```

## source.rs — SourceTree and SourceLine scanning primitives

Target path: `tests/structure/support/source.rs`

```rust
// tests/structure/support/source.rs
//! Source-reading primitives for the structure tests: the source tree (locate
//! `src/` and other checked roots, walk them, read files, relativize paths) and
//! single-line classifiers. Resolved from `CARGO_MANIFEST_DIR`, so the working
//! directory does not matter.

use std::path::{Path, PathBuf};

use super::constants::INFRASTRUCTURE_LAYER;

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

    /// Whether the crate-relative unix path matches one of `paths`: entries
    /// ending in `/` are prefixes, other entries are exact file paths.
    pub(crate) fn matches_any(relative_path: &str, paths: &[&str]) -> bool {
        paths.iter().any(|path| {
            relative_path == *path || (path.ends_with('/') && relative_path.starts_with(path))
        })
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

    /// The sibling folder this module file fronts (`order/` for `order.rs`),
    /// if one exists on disk.
    pub(crate) fn fronted_folder(&self, module_file: &Path) -> Option<PathBuf> {
        let stem = module_file.file_stem()?;
        let folder = module_file.parent()?.join(stem);
        folder.is_dir().then_some(folder)
    }

    /// Whether a module file names an addressable namespace rather than a
    /// concept: a layer file directly under `src/` (`src/application.rs`) or
    /// an adapter-family file directly under `src/infrastructure/`
    /// (`src/infrastructure/database.rs`). The facade rule exempts both.
    pub(crate) fn is_namespace_module_file(&self, file: &Path) -> bool {
        let source_root = self.crate_root.join("src");
        let Ok(relative) = file.strip_prefix(&source_root) else {
            return false;
        };
        let component_count = relative.components().count();
        component_count == 1 || (component_count == 2 && relative.starts_with(INFRASTRUCTURE_LAYER))
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

/// Reads a file addressed relative to the crate root (`CARGO_MANIFEST_DIR`),
/// e.g. `Cargo.toml` or `../Cargo.toml` for the manifest gate.
pub(crate) fn read_crate_file(crate_relative_path: &str) -> String {
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join(crate_relative_path);
    std::fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("failed to read {}: {error}", path.display()))
}

/// A single source line, with the classification queries the rules need.
pub(crate) struct SourceLine<'line>(pub(crate) &'line str);

impl<'line> SourceLine<'line> {
    pub(crate) fn is_comment(&self) -> bool {
        self.0.trim_start().starts_with("//")
    }

    /// The code portion of the line — everything before a trailing `//`
    /// comment. The assembly scanners match markers against this, so a comment
    /// that merely mentions a concrete type is never a false hit. Returns
    /// `&'line str` (not `&self`-bound) so it works on a temporary
    /// `SourceLine(line)`.
    pub(crate) fn code(&self) -> &'line str {
        self.0.split("//").next().unwrap_or_default()
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

    /// Whether the line is an attribute (`#[...]` / `#![...]`).
    pub(crate) fn is_attribute(&self) -> bool {
        self.0.trim_start().starts_with('#')
    }

    /// The module name declared by a private `mod <name>;` line.
    pub(crate) fn private_module_declaration(&self) -> Option<&str> {
        Self::terminated_module_name(self.0.trim().strip_prefix("mod ")?)
    }

    /// The module name declared by a `pub mod <name>;` line.
    pub(crate) fn public_module_declaration(&self) -> Option<&str> {
        Self::terminated_module_name(self.0.trim().strip_prefix("pub mod ")?)
    }

    /// The module name re-exported by a `pub use <name>::*;` glob line.
    pub(crate) fn glob_reexport(&self) -> Option<&str> {
        let after_use = self.0.trim().strip_prefix("pub use ")?;
        let name = after_use.strip_suffix("::*;")?.trim();
        Self::is_module_name(name).then_some(name)
    }

    fn terminated_module_name(rest: &str) -> Option<&str> {
        let name = rest.strip_suffix(';')?.trim();
        Self::is_module_name(name).then_some(name)
    }

    fn is_module_name(name: &str) -> bool {
        !name.is_empty()
            && name
                .chars()
                .all(|character| character.is_ascii_alphanumeric() || character == '_')
    }
}
```

## violation.rs — Violation finding type

Target path: `tests/structure/support/violation.rs`

```rust
// tests/structure/support/violation.rs
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

## manifest.rs — Cargo.toml dependency-gate scanner (TOML-backed)

Target path: `tests/structure/support/manifest.rs`

Requires `toml` in `[dev-dependencies]` (verify the current version on crates.io
before pinning). A lexical grep over the manifest is not enough: a forbidden
crate can hide behind a dependency rename (`core_alias = { package = "my-core" }`),
behind `workspace = true` inheritance, or inside a `[target.'…'.dependencies]`
table — this scanner resolves all three to the *effective* package name before
matching. Omit this file (and `workspace_deps.rs`) on single-crate projects.

```rust
// tests/structure/support/manifest.rs
//! Effective Cargo.toml dependency gate: resolves every dependency declaration
//! (including package renames, `workspace = true` inheritance, and
//! target-specific tables) to its effective package name and reports the ones
//! on the forbidden list.

use toml::{Table, Value};

pub fn forbidden_dependency_violations(
    manifest_path: &str,
    workspace_manifest_path: &str,
    manifest: &str,
    workspace_manifest: &str,
    forbidden_packages: &[&str],
) -> Vec<String> {
    let manifest_table = manifest
        .parse::<Table>()
        .unwrap_or_else(|error| panic!("failed to parse {manifest_path}: {error}"));
    let workspace_table = workspace_manifest
        .parse::<Table>()
        .unwrap_or_else(|error| panic!("failed to parse {workspace_manifest_path}: {error}"));
    let workspace_dependencies = workspace_table
        .get("workspace")
        .and_then(Value::as_table)
        .and_then(|workspace| workspace.get("dependencies"))
        .and_then(Value::as_table);

    dependency_declarations(&manifest_table)
        .into_iter()
        .filter_map(|declaration| {
            let package_name =
                effective_package_name(declaration.key, declaration.value, workspace_dependencies)?;
            forbidden_packages
                .contains(&package_name.as_str())
                .then(|| {
                    format!(
                        "{manifest_path}: {}.{} declares forbidden package `{package_name}`{}",
                        declaration.table_path,
                        declaration.key,
                        is_workspace_inherited(declaration.value)
                            .then(|| format!(" (resolved through {workspace_manifest_path})"))
                            .unwrap_or_default(),
                    )
                })
        })
        .collect()
}

struct DependencyDeclaration<'value> {
    key: &'value str,
    value: &'value Value,
    table_path: String,
}

fn dependency_declarations(table: &Table) -> Vec<DependencyDeclaration<'_>> {
    let mut declarations = Vec::new();
    collect_dependency_table_declarations(table, "", &mut declarations);
    declarations
}

fn collect_dependency_table_declarations<'value>(
    table: &'value Table,
    prefix: &str,
    declarations: &mut Vec<DependencyDeclaration<'value>>,
) {
    for dependency_table_name in ["dependencies", "dev-dependencies", "build-dependencies"] {
        if let Some(dependencies) = table.get(dependency_table_name).and_then(Value::as_table) {
            let table_path = join_path(prefix, dependency_table_name);
            declarations.extend(
                dependencies
                    .iter()
                    .map(|(key, value)| DependencyDeclaration {
                        key,
                        value,
                        table_path: table_path.clone(),
                    }),
            );
        }
    }

    if let Some(targets) = table.get("target").and_then(Value::as_table) {
        for (target_name, target_value) in targets {
            if let Some(target_table) = target_value.as_table() {
                let target_prefix = join_path(&join_path(prefix, "target"), target_name);
                collect_dependency_table_declarations(target_table, &target_prefix, declarations);
            }
        }
    }
}

fn effective_package_name(
    dependency_key: &str,
    dependency_value: &Value,
    workspace_dependencies: Option<&Table>,
) -> Option<String> {
    if is_workspace_inherited(dependency_value) {
        let workspace_dependency = workspace_dependencies?.get(dependency_key)?;
        return effective_package_name(dependency_key, workspace_dependency, None);
    }
    dependency_value
        .as_table()
        .and_then(|details| details.get("package"))
        .and_then(Value::as_str)
        .map(ToOwned::to_owned)
        .or_else(|| Some(dependency_key.to_string()))
}

fn is_workspace_inherited(dependency_value: &Value) -> bool {
    dependency_value
        .as_table()
        .and_then(|details| details.get("workspace"))
        .and_then(Value::as_bool)
        .unwrap_or(false)
}

fn join_path(prefix: &str, segment: &str) -> String {
    if prefix.is_empty() {
        segment.to_string()
    } else {
        format!("{prefix}.{segment}")
    }
}
```
