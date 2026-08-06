# Starter rules — `layout.rs` and `coverage.rs`

The rules to land first, complete. Three layout rules plus the workspace-coverage
rule.

Every constructor is `pub fn …() -> Rule` with **no parameters**. Policy lives in
private module constants, which is what makes every crate's gate line identical
and any future divergence visible in a diff.

---

## `src/layout.rs`

Three rules from the existing skills: `rust-code-style` Rule 6 (`mod.rs` ban),
`rust-testing` §8 (no tests in `src/`), `rust-testing` §16 (test files hold only
tests). The `mod.rs` ban needs no parser; the other two walk a parsed item list.

```rust
//! The universal layout rules — where code is allowed to live. A test file
//! holds only `use` imports, `mod` declarations, and test-attributed functions
//! at module scope (rust-testing §16); no module anywhere uses the legacy
//! `mod.rs` file (rust-code-style Rule 6); and no test lives under `src/`
//! (rust-testing §8). Zero-knob: the policy constants below are private to this
//! module, so every crate's gate is the same one-liner.

use syn::spanned::Spanned;

use crate::rule::Rule;
use crate::violation::Violation;

/// Directory names under a `tests/` tree whose files are helper modules by
/// design (rust-testing §15) — the rule does not scan them, in either layout
/// the testing skill allows (a directory, or a single-file sibling module).
const TEST_HELPER_DIR_NAMES: &[&str] = &["support", "common"];

/// Attribute paths that mark a module-scope `fn` in a test file as a test.
/// `#[ctor]` is deliberately absent: infra bring-up lives in
/// `support/infra.rs`, never in a test file.
const TEST_MARKER_ATTRIBUTE_PATHS: &[&str] = &["test", "tokio::test"];

/// The legacy Rust module-layout file name, forbidden everywhere.
const MOD_FILE_NAME: &str = "mod.rs";

/// The roots the `mod.rs` ban scans — a crate's production and test trees.
const MOD_FILE_SEARCH_ROOTS: &[&str] = &["src", "tests"];

const MOD_FILE_MESSAGE: &str = "`mod.rs` is the legacy module layout; declare the module from a \
     sibling `<module_name>.rs` file, or reach a cross-test-crate module with `#[path = \"...\"]`";

/// Attribute paths that can gate an item on the test cfg. A `#[cfg(test)]`
/// item in `src/` is a test module (or its scaffolding) living in production
/// code; `#[cfg_attr(test, ...)]` is the same smuggled through a conditional
/// attribute. Both forms are matched wherever they appear in `src/`.
const TEST_CFG_ATTRIBUTE_PATHS: &[&str] = &["cfg", "cfg_attr"];

const SRC_TEST_MESSAGE: &str = "tests never live in `src/` (rust-testing §8); move this to the crate's `tests/` tree, which \
     reaches production code through the crate's public surface";

/// Test files contain only tests at module scope.
///
/// A test file may hold `use` imports, `mod` declarations, and functions
/// carrying a test attribute — every helper, factory, fixture, constant, type,
/// and impl belongs in a `support/` or `common/` module. Scans
/// `<manifest_dir>/tests`.
#[must_use]
pub fn test_files_contain_only_tests() -> Rule {
    Rule::new(
        "test files must contain only tests at module scope (helpers live in support/)",
        |source_tree| {
            let mut violations = Vec::new();
            for file in source_tree.rust_files_in_roots(&["tests"]) {
                let crate_relative = source_tree.relative_unix(&file);
                let is_helper_module = crate_relative.split('/').any(|segment| {
                    TEST_HELPER_DIR_NAMES.contains(&segment)
                        || TEST_HELPER_DIR_NAMES
                            .iter()
                            .any(|name| segment == format!("{name}.rs"))
                });
                if is_helper_module {
                    continue;
                }
                let reported_path = source_tree.reported_path(&file);
                let contents = source_tree.read(&file);
                match syn::parse_file(&contents) {
                    Ok(parsed) => collect_non_test_items(
                        &parsed.items,
                        &reported_path,
                        &contents,
                        &mut violations,
                    ),
                    Err(error) => violations.push(Violation::in_file(
                        &reported_path,
                        &format!("failed to parse: {error}"),
                    )),
                }
            }
            violations
        },
    )
}

/// No module uses the legacy `mod.rs` file layout.
///
/// Every module is declared by a sibling `<module_name>.rs` file next to its
/// directory (rust-code-style Rule 6). The ban has no allowlist: a test tree
/// that must share a module across two test crates reaches it with
/// `#[path = "common/<file>.rs"] mod <name>;`, which needs no `mod.rs`. Scans
/// `<manifest_dir>/src` and `<manifest_dir>/tests`.
#[must_use]
pub fn mod_files_are_forbidden() -> Rule {
    Rule::new(
        "mod files are forbidden (rust-code-style Rule 6)",
        |source_tree| {
            source_tree
                .rust_files_in_roots(MOD_FILE_SEARCH_ROOTS)
                .into_iter()
                .filter(|file| {
                    file.file_name().and_then(|name| name.to_str()) == Some(MOD_FILE_NAME)
                })
                .map(|file| Violation::in_file(&source_tree.reported_path(&file), MOD_FILE_MESSAGE))
                .collect()
        },
    )
}

/// No test lives under `src/`.
///
/// Production sources carry no `#[cfg(test)]` module, no `#[cfg_attr(test, …)]`
/// item, and no test-attributed function (rust-testing §8). Every test — unit
/// tests included — belongs in the crate's `tests/` tree, reaching production
/// code through the crate's public surface. Scans `<manifest_dir>/src`.
#[must_use]
pub fn tests_do_not_live_in_src() -> Rule {
    Rule::new(
        "tests do not live in src (rust-testing §8)",
        |source_tree| {
            let mut violations = Vec::new();
            for file in source_tree.rust_files() {
                let reported_path = source_tree.reported_path(&file);
                let contents = source_tree.read(&file);
                match syn::parse_file(&contents) {
                    Ok(parsed) => {
                        collect_test_items(
                            &parsed.items,
                            &reported_path,
                            &contents,
                            &mut violations,
                        );
                    }
                    Err(error) => violations.push(Violation::in_file(
                        &reported_path,
                        &format!("failed to parse: {error}"),
                    )),
                }
            }
            violations
        },
    )
}

/// Walks a production file (recursing into nested `mod` blocks) and records
/// every item gated on the test cfg or carrying a test attribute.
fn collect_test_items(
    items: &[syn::Item],
    file: &str,
    contents: &str,
    violations: &mut Vec<Violation>,
) {
    for item in items {
        let attributes = item_attributes(item);
        if attributes.iter().any(is_test_cfg) || attributes.iter().any(is_test_marker) {
            push_test_layout_violation(item, file, contents, SRC_TEST_MESSAGE, violations);
            continue;
        }
        if let syn::Item::Mod(module) = item
            && let Some((_, nested_items)) = &module.content
        {
            collect_test_items(nested_items, file, contents, violations);
        }
    }
}

/// Every `syn::Item` variant that carries attributes. The arms mirror
/// [`item_kind_name`]'s enumeration of the same enum, so a `#[cfg(test)]` on
/// any item kind is visible to the scan; `_ => &[]` covers only the genuinely
/// attribute-free variants (`Item::Verbatim` and future additions).
fn item_attributes(item: &syn::Item) -> &[syn::Attribute] {
    match item {
        syn::Item::Const(inner) => &inner.attrs,
        syn::Item::Enum(inner) => &inner.attrs,
        syn::Item::ExternCrate(inner) => &inner.attrs,
        syn::Item::Fn(inner) => &inner.attrs,
        syn::Item::ForeignMod(inner) => &inner.attrs,
        syn::Item::Impl(inner) => &inner.attrs,
        syn::Item::Macro(inner) => &inner.attrs,
        syn::Item::Mod(inner) => &inner.attrs,
        syn::Item::Static(inner) => &inner.attrs,
        syn::Item::Struct(inner) => &inner.attrs,
        syn::Item::Trait(inner) => &inner.attrs,
        syn::Item::TraitAlias(inner) => &inner.attrs,
        syn::Item::Type(inner) => &inner.attrs,
        syn::Item::Union(inner) => &inner.attrs,
        syn::Item::Use(inner) => &inner.attrs,
        _ => &[],
    }
}

/// Whether an attribute makes its item exist *only* under the test cfg —
/// `#[cfg(test)]`, `#[cfg_attr(test, …)]`, or a compound at any nesting depth
/// such as `#[cfg(all(unix, any(test, windows)))]`.
///
/// `not(...)` inverts the meaning, so its contents are skipped: an item marked
/// `#[cfg(not(test))]` is the *production* branch of a swapped pair and must
/// not be flagged as a test living in `src/`.
fn is_test_cfg(attribute: &syn::Attribute) -> bool {
    if !TEST_CFG_ATTRIBUTE_PATHS
        .iter()
        .any(|path| attribute.path().is_ident(path))
    {
        return false;
    }
    let syn::Meta::List(list) = &attribute.meta else {
        return false;
    };
    predicate_names_test(list.tokens.clone())
}

/// Whether a cfg predicate's token stream names `test` in a position that
/// gates the item *on* the test cfg. Recurses through nested groups to any
/// depth, skipping the contents of a `not(...)` inversion.
fn predicate_names_test(tokens: proc_macro2::TokenStream) -> bool {
    let mut token_trees = tokens.into_iter().peekable();
    while let Some(token) = token_trees.next() {
        match token {
            proc_macro2::TokenTree::Ident(ident) if ident == "test" => return true,
            proc_macro2::TokenTree::Ident(ident) if ident == "not" => {
                // Consume the inverted group without inspecting it.
                if matches!(token_trees.peek(), Some(proc_macro2::TokenTree::Group(_))) {
                    token_trees.next();
                }
            }
            proc_macro2::TokenTree::Group(group) if predicate_names_test(group.stream()) => {
                return true;
            }
            _ => {}
        }
    }
    false
}

/// Walks the items of a test file (recursing into nested `mod` blocks) and
/// records every module-scope item that is not a `use`, a `mod`, or a
/// test-attributed function.
fn collect_non_test_items(
    items: &[syn::Item],
    file: &str,
    contents: &str,
    violations: &mut Vec<Violation>,
) {
    for item in items {
        match item {
            syn::Item::Use(_) => {}
            syn::Item::Mod(module) => {
                if let Some((_, nested_items)) = &module.content {
                    collect_non_test_items(nested_items, file, contents, violations);
                }
            }
            syn::Item::Fn(function) => {
                if !function.attrs.iter().any(is_test_marker) {
                    push_test_layout_violation(
                        item,
                        file,
                        contents,
                        &format!(
                            "module-scope `fn {}` has no test attribute; move it to a support module",
                            function.sig.ident
                        ),
                        violations,
                    );
                }
            }
            other => push_test_layout_violation(
                other,
                file,
                contents,
                &format!(
                    "module-scope `{}` is not a test; move it to a support module",
                    item_kind_name(other)
                ),
                violations,
            ),
        }
    }
}

fn push_test_layout_violation(
    item: &syn::Item,
    file: &str,
    contents: &str,
    message: &str,
    violations: &mut Vec<Violation>,
) {
    let line = item.span().start().line;
    let source = contents.lines().nth(line.saturating_sub(1)).unwrap_or("");
    violations.push(Violation::at_line(file, line, source, message));
}

fn is_test_marker(attribute: &syn::Attribute) -> bool {
    let path = attribute
        .path()
        .segments
        .iter()
        .map(|segment| segment.ident.to_string())
        .collect::<Vec<_>>()
        .join("::");
    TEST_MARKER_ATTRIBUTE_PATHS.contains(&path.as_str())
}

const fn item_kind_name(item: &syn::Item) -> &'static str {
    match item {
        syn::Item::Const(_) => "const",
        syn::Item::Enum(_) => "enum",
        syn::Item::ExternCrate(_) => "extern crate",
        syn::Item::ForeignMod(_) => "extern block",
        syn::Item::Impl(_) => "impl",
        syn::Item::Macro(_) => "macro",
        syn::Item::Static(_) => "static",
        syn::Item::Struct(_) => "struct",
        syn::Item::Trait(_) => "trait",
        syn::Item::TraitAlias(_) => "trait alias",
        syn::Item::Type(_) => "type alias",
        syn::Item::Union(_) => "union",
        _ => "item",
    }
}
```

### Three decisions in there worth understanding before you add a fourth rule

- **A parse failure is a violation, not a panic.** `syn::parse_file` returning
  `Err` reports `failed to parse: …` against the file. A rule that panicked
  instead would take the whole gate down on one malformed file and hide every
  other finding.
- **Recursion into inline `mod` blocks is deliberate.** Both item walks recurse,
  so a violation cannot hide one level down inside `mod inner { … }`.
- **`not(test)` is skipped, not matched.** `#[cfg(not(test))]` marks the
  *production* branch of a swapped pair. A rule that matched the token `test`
  anywhere in the predicate would flag production code as a test.

---

## `src/coverage.rs`

The rule that closes the gap the per-crate gates cannot see: a workspace member
with no gate at all. `cargo test --workspace --test structure` does **not**
catch that case — Cargo treats `--test` as a filter satisfied when any package
matches, so a member without `tests/structure.rs` is silently skipped and the
command still exits 0.

This rule is a property of the *workspace*, so it lives in the conventions
crate's own gate — the one crate that exists exactly once.

**Ask Cargo who the members are — do not re-derive it from the manifest.** This
is the one place where reading `[workspace] members` yourself is actively wrong,
and it fails in the exact configuration this skill creates. Cargo treats any
in-workspace **path dependency** as a member whether or not `members` lists it,
and every consumer here declares the conventions crate by path. So a crate can
join the workspace, be selected by `cargo test --workspace`, and never appear in
`members`. A manifest-reading rule reports no violation for it — the one rule
whose entire job is catching a gateless member would certify coverage it never
checked. Cargo also filters glob expansion by `exclude` and accepts several glob
spellings, each an additional way to be wrong.

```rust
//! The workspace-coverage rule: every workspace member owns a
//! `tests/structure.rs` gate. Membership comes from `cargo metadata`, which is
//! authoritative — see `workspace_layout` for why nothing here parses the
//! workspace manifest.

use std::path::{Path, PathBuf};
use std::process::Command;

use crate::rule::Rule;
use crate::violation::Violation;

/// The gate file every member must own, relative to its crate root.
const GATE_FILE: &str = "tests/structure.rs";

const MISSING_GATE_MESSAGE: &str = "workspace member has no `tests/structure.rs` gate; add one \
     adopting the universal rules, so this member is enforced locally and by \
     `cargo test --workspace --test structure`";

/// Every workspace member owns a `tests/structure.rs` gate.
#[must_use]
pub fn every_workspace_member_has_a_structure_gate() -> Rule {
    Rule::new(
        "every workspace member owns a tests/structure.rs gate",
        |source_tree| match workspace_layout(source_tree.crate_root()) {
            Ok(layout) => layout
                .member_directories
                .into_iter()
                .filter(|member| !member.join(GATE_FILE).is_file())
                .map(|member| {
                    Violation::in_file(
                        &gate_path_relative_to(&layout.workspace_root, &member),
                        MISSING_GATE_MESSAGE,
                    )
                })
                .collect(),
            Err(reason) => vec![Violation::in_file("Cargo.toml", &reason)],
        },
    )
}

struct WorkspaceLayout {
    workspace_root: PathBuf,
    member_directories: Vec<PathBuf>,
}

/// Asks Cargo which packages are workspace members. Cargo is the authority: a
/// path dependency inside the workspace is a member even when `[workspace]
/// members` never lists it, `exclude` filters glob expansion, and globs may be
/// written several ways. Re-deriving any of that from the manifest under-reports
/// missing gates, which would make this rule certify coverage it has not
/// checked.
fn workspace_layout(crate_root: &Path) -> Result<WorkspaceLayout, String> {
    let cargo = std::env::var("CARGO").unwrap_or_else(|_| "cargo".to_owned());
    let output = Command::new(cargo)
        .args(["metadata", "--format-version", "1", "--no-deps"])
        .current_dir(crate_root)
        .output()
        .map_err(|error| format!("could not run `cargo metadata`: {error}"))?;
    if !output.status.success() {
        return Err(format!(
            "`cargo metadata` failed: {}",
            String::from_utf8_lossy(&output.stderr).trim()
        ));
    }
    let metadata: serde_json::Value = serde_json::from_slice(&output.stdout)
        .map_err(|error| format!("could not parse `cargo metadata` output: {error}"))?;

    let workspace_root = metadata["workspace_root"]
        .as_str()
        .ok_or_else(|| "`cargo metadata` reported no workspace_root".to_owned())?;
    let member_ids: Vec<&str> = metadata["workspace_members"]
        .as_array()
        .map(|ids| ids.iter().filter_map(serde_json::Value::as_str).collect())
        .unwrap_or_default();
    let member_directories = metadata["packages"]
        .as_array()
        .map(|packages| {
            packages
                .iter()
                .filter(|package| {
                    package["id"]
                        .as_str()
                        .is_some_and(|id| member_ids.contains(&id))
                })
                .filter_map(|package| package["manifest_path"].as_str())
                .filter_map(|manifest| Path::new(manifest).parent().map(Path::to_path_buf))
                .collect()
        })
        .unwrap_or_default();

    Ok(WorkspaceLayout {
        workspace_root: PathBuf::from(workspace_root),
        member_directories,
    })
}

/// The gate file's path as a violation should name it: relative to the
/// workspace root, and without a leading separator when the member *is* the
/// workspace root.
fn gate_path_relative_to(workspace_root: &Path, member: &Path) -> String {
    let relative = member
        .strip_prefix(workspace_root)
        .unwrap_or(member)
        .components()
        .map(|component| component.as_os_str().to_string_lossy().into_owned())
        .collect::<Vec<_>>()
        .join("/");
    if relative.is_empty() {
        GATE_FILE.to_owned()
    } else {
        format!("{relative}/{GATE_FILE}")
    }
}
```

This needs `serde_json` in the crate's `[dependencies]`. It needs no `toml`
dependency — asking Cargo removes every reason to parse a manifest.

### Deliberate scope of this rule

- **It requires a gate from every member, including crates with no `tests/`
  tree.** A crate with nothing else to test still gets a gate adopting the
  universal rules; that is what makes the coverage claim total, and the gate is
  the same identical file the other leaf crates carry.
- **It checks all members, not `default-members`.** A member excluded from the
  default set still needs a gate.
- **It reports the missing file, not the directory** —
  `<member>/tests/structure.rs`, or plain `tests/structure.rs` when the
  workspace root is itself a package — so the violation names the artifact to
  create.
- **It invokes Cargo through `$CARGO`**, the environment variable Cargo sets for
  its own child processes, so the rule uses the same toolchain that is running
  the test rather than whatever `cargo` happens to be on `PATH`.
- **A Cargo failure becomes a violation, not a panic.** If `cargo metadata`
  cannot run, the gate fails loudly with the reason on `Cargo.toml` rather than
  passing silently — the one outcome this rule must never produce.

### Fixture tests for it

Same `should_flag` / `should_pass` pairing, but the fixtures are whole
*workspaces*: a root `Cargo.toml`, then member directories written with a
manifest and `src/lib.rs`, some with `tests/structure.rs` and some without. Five
cases are worth having, and the first is the one that matters most — it is the
case a manifest-reading implementation silently passes:

1. a member reachable **only as another member's path dependency**, absent from
   `members`, with no gate → reported;
2. a directory matched by a `members` glob but named in `exclude` → not
   reported;
3. `members = ["crates/*/"]` (trailing slash) → expands, and the gateless member
   is reported by its real path rather than by the literal glob;
4. a root manifest that is also a package, with no gate → reported as
   `tests/structure.rs`, no leading slash;
5. every member gated → no violations.
