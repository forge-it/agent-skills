# Fixture tests — the `tests/unit` tree

Every rule gets two sibling modules: `should_flag` (the violation is reported)
and `should_pass` (the legitimate near-miss, and one case per rule-owned
exemption, report nothing). That pairing *is* the discipline — a rule with only
`should_flag` tests can over-fire forever without anyone noticing.

Four files, all required. **Without `tests/unit.rs` Cargo never compiles the
`tests/unit/` directory at all**, so the tests silently do not exist and the
`uuid` dev-dependency is dead weight.

```
tests/
├── structure.rs              # the crate's own gate (Step 6)
├── unit.rs                   # entry: declares the module tree
└── unit/
    ├── support.rs            # support facade
    ├── support/fixtures.rs   # temp_crate_dir + writers
    ├── layout.rs             # should_flag / should_pass per layout rule
    └── coverage.rs           # fixture *workspaces* for the coverage rule
```

`support/` is exempt from the test-purity rule by name (it is in the rule's
private helper-directory list), which is why helpers may live there and nowhere
else under `tests/`.

---

## `tests/unit.rs`

```rust
mod unit {
    pub mod support;

    mod coverage;
    mod layout;
}
```

## `tests/unit/support.rs`

```rust
//! Support for the rule tests: fixture-tree construction. Per rust-testing §15
//! the test files contain only tests; every helper lives here.

pub mod fixtures;
```

## `tests/unit/support/fixtures.rs`

```rust
//! Fixture trees for the rule tests: a uniquely-named temporary crate root per
//! test, plus writers that place a file inside its `src/` or `tests/` tree.

use std::path::{Path, PathBuf};

/// A fresh crate root under the OS temp directory, suffixed with a UUIDv7 so
/// tests running in parallel never share a tree.
#[must_use]
pub fn temp_crate_dir() -> PathBuf {
    let directory = std::env::temp_dir().join(format!(
        "conventions-fixture-{}",
        uuid::Uuid::now_v7().simple()
    ));
    std::fs::create_dir_all(&directory).expect("create fixture crate root");
    directory
}

/// Writes `contents` to `<crate_root>/src/<path_within_src>`.
pub fn write_source_file(crate_root: &Path, path_within_src: &str, contents: &str) {
    write_file(&crate_root.join("src").join(path_within_src), contents);
}

/// Writes `contents` to `<crate_root>/tests/<path_within_tests>`.
pub fn write_test_file(crate_root: &Path, path_within_tests: &str, contents: &str) {
    write_file(&crate_root.join("tests").join(path_within_tests), contents);
}

fn write_file(path: &Path, contents: &str) {
    let parent = path.parent().expect("fixture path has a parent");
    std::fs::create_dir_all(parent).expect("create fixture directory");
    std::fs::write(path, contents).expect("write fixture file");
}
```

Note the argument convention: the writers add the `src/` or `tests/` prefix, so a
call passes the path *within* that tree — `write_source_file(&dir, "order/mod.rs", "")`
creates `src/order/mod.rs`.

The fixtures are deliberately never cleaned up. A failing test's tree is
evidence, the OS reclaims the temp directory, and a `Drop` guard would delete
exactly the state you want to inspect.

## `tests/unit/layout.rs`

Note the header — the rule constructors come from the crate, the fixture helpers
from the support module. Omit either import and the file does not compile:

```rust
use <project>_conventions::{
    mod_files_are_forbidden, test_files_contain_only_tests, tests_do_not_live_in_src,
};

use super::support::fixtures::{temp_crate_dir, write_source_file, write_test_file};

mod mod_files {
    use super::*;

    mod should_flag {
        use super::*;

        #[test]
        fn a_mod_file_under_src() {
            let crate_root = temp_crate_dir();
            write_source_file(&crate_root, "order/mod.rs", "");

            let violations = mod_files_are_forbidden().violations(&crate_root);

            assert!(!violations.is_empty(), "expected a violation for src/order/mod.rs");
        }

        #[test]
        fn a_mod_file_under_tests() {
            let crate_root = temp_crate_dir();
            write_test_file(&crate_root, "support/mod.rs", "");

            let violations = mod_files_are_forbidden().violations(&crate_root);

            assert!(!violations.is_empty(), "the ban has no allowlist, not even for support/");
        }
    }

    mod should_pass {
        use super::*;

        #[test]
        fn a_sibling_module_file_next_to_its_directory() {
            let crate_root = temp_crate_dir();
            write_source_file(&crate_root, "order.rs", "mod line_item;\n");
            write_source_file(&crate_root, "order/line_item.rs", "");

            let violations = mod_files_are_forbidden().violations(&crate_root);

            assert!(violations.is_empty(), "unexpected violations: {violations:?}");
        }
    }
}

mod src_tests {
    use super::*;

    mod should_flag {
        use super::*;

        #[test]
        fn a_cfg_test_module() {
            let crate_root = temp_crate_dir();
            write_source_file(&crate_root, "order.rs", "#[cfg(test)]\nmod tests {}\n");

            let violations = tests_do_not_live_in_src().violations(&crate_root);

            assert!(!violations.is_empty(), "expected a violation for #[cfg(test)]");
        }
    }

    mod should_pass {
        use super::*;

        #[test]
        fn a_non_test_cfg_gate() {
            let crate_root = temp_crate_dir();
            write_source_file(&crate_root, "order.rs", "#[cfg(unix)]\nmod posix {}\n");

            let violations = tests_do_not_live_in_src().violations(&crate_root);

            assert!(violations.is_empty(), "non-test cfg gates are untouched: {violations:?}");
        }

        #[test]
        fn the_production_branch_of_a_swapped_pair() {
            let crate_root = temp_crate_dir();
            write_source_file(&crate_root, "clock.rs", "#[cfg(not(test))]\nmod real {}\n");

            let violations = tests_do_not_live_in_src().violations(&crate_root);

            assert!(violations.is_empty(), "not(test) is production: {violations:?}");
        }
    }
}

mod test_files {
    use super::*;

    mod should_flag {
        use super::*;

        #[test]
        fn a_module_scope_fn_without_a_test_attribute() {
            let crate_root = temp_crate_dir();
            write_test_file(&crate_root, "unit/order.rs", "fn helper() {}\n");

            let violations = test_files_contain_only_tests().violations(&crate_root);

            assert!(!violations.is_empty(), "expected a violation for a bare fn");
        }
    }

    mod should_pass {
        use super::*;

        #[test]
        fn imports_mods_and_tests() {
            let crate_root = temp_crate_dir();
            write_test_file(
                &crate_root,
                "unit/order.rs",
                "use std::collections::HashMap;\n\nmod order {\n    #[test]\n    fn should_total() {}\n}\n",
            );

            let violations = test_files_contain_only_tests().violations(&crate_root);

            assert!(violations.is_empty(), "unexpected violations: {violations:?}");
        }

        #[test]
        fn a_support_module_holding_helpers() {
            let crate_root = temp_crate_dir();
            write_test_file(&crate_root, "unit/support/fixtures.rs", "pub struct Builder;\n");

            let violations = test_files_contain_only_tests().violations(&crate_root);

            assert!(violations.is_empty(), "support/ is exempt: {violations:?}");
        }
    }
}
```

That last `should_pass` is the one people skip, and it is the one that matters:
it pins the rule's own exemption. **Add the `should_pass` test in the same change
as the exemption it covers** — otherwise an exemption can widen later and no test
notices.

## `tests/unit/coverage.rs`

The coverage rule's fixtures are whole *workspaces*, because that is its subject.
Build them with a manifest plus `src/lib.rs` per member, then run the rule from
inside one member:

```rust
use <project>_conventions::every_workspace_member_has_a_structure_gate;

use super::support::fixtures::temp_crate_dir;

fn member(workspace_root: &std::path::Path, directory: &str, manifest_extra: &str, gated: bool) {
    let member_root = workspace_root.join(directory);
    std::fs::create_dir_all(member_root.join("src")).expect("create member src");
    std::fs::write(
        member_root.join("Cargo.toml"),
        format!(
            "[package]\nname = \"{}\"\nversion = \"0.1.0\"\nedition = \"2021\"\n{manifest_extra}",
            directory.rsplit('/').next().expect("member name")
        ),
    )
    .expect("write member manifest");
    std::fs::write(member_root.join("src/lib.rs"), "").expect("write member lib");
    if gated {
        std::fs::create_dir_all(member_root.join("tests")).expect("create member tests");
        std::fs::write(member_root.join("tests/structure.rs"), "").expect("write member gate");
    }
}

mod should_flag {
    use super::*;

    /// The case a manifest-reading implementation silently passes: Cargo makes
    /// an in-workspace path dependency a member even when `members` omits it.
    #[test]
    fn a_member_reachable_only_as_a_path_dependency() {
        let workspace_root = temp_crate_dir();
        std::fs::write(
            workspace_root.join("Cargo.toml"),
            "[workspace]\nmembers = [\"listed\"]\nresolver = \"2\"\n",
        )
        .expect("write workspace manifest");
        member(
            &workspace_root,
            "listed",
            "\n[dev-dependencies]\nunlisted = { path = \"../crates/unlisted\" }\n",
            true,
        );
        member(&workspace_root, "crates/unlisted", "", false);

        let violations = every_workspace_member_has_a_structure_gate()
            .violations(workspace_root.join("listed"));

        assert_eq!(violations.len(), 1, "{violations:?}");
    }
}
```

Add the other four cases from the same shape: a directory matched by a glob but
named in `exclude` (must **not** be reported), `members = ["crates/*/"]` with a
trailing slash (must expand rather than report the literal glob), a root manifest
that is also a package (reported as `tests/structure.rs`, no leading slash), and
an all-gated workspace (no violations).
