# Machinery — `source.rs`, `rule.rs`, `violation.rs`

The three files every rule is built on. Write all three in one pass. They are
complete as given; nothing here needs adapting for a new project.

**The invariant to preserve if you do adapt them:** the library never resolves
its own location. `Rule::enforce` takes the crate root as an argument, and the
gate passes `env!("CARGO_MANIFEST_DIR")`. That is what makes a rule scan the tree
that adopted it rather than this crate's.

---

## `src/violation.rs`

Two constructors, and the type owns its own rendering so no rule ever
hand-formats a string. The four-argument form carries the offending source, which
is what lets a reader fix the violation without opening the file.

```rust
//! A single structure violation: where it is, what is wrong, and how it renders
//! in a test-failure message.

use std::fmt;

/// A structure-rule violation. Either tied to a specific line (carrying the
/// offending source) or to a file as a whole.
#[derive(Debug)]
pub struct Violation {
    file: String,
    line: Option<usize>,
    source: Option<String>,
    message: String,
}

impl Violation {
    /// A violation at a specific 1-based line, carrying the offending source.
    #[must_use]
    pub fn at_line(file: &str, line: usize, source: &str, message: &str) -> Self {
        Self {
            file: file.to_string(),
            line: Some(line),
            source: Some(source.trim().to_string()),
            message: message.to_string(),
        }
    }

    /// A violation about a file as a whole (no specific line).
    #[must_use]
    pub fn in_file(file: &str, message: &str) -> Self {
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
                write!(
                    formatter,
                    "{}:{line}: {} -> {source}",
                    self.file, self.message
                )
            }
            _ => write!(formatter, "{}: {}", self.file, self.message),
        }
    }
}
```

A real failure reads like this — one unwrapped line per violation:

```
core/src/infrastructure/api/job/handler.rs:129: inline crate::/super:: path exceeds 3 segments (rust-code-style Rule 7); bring the item into scope with use and shorten the call site -> Ok(Sse::new(stream).keep_alive(crate::infrastructure::api::sse::default_keep_alive()))
```

---

## `src/rule.rs`

A description paired with the check that finds its violations. `violations()` is
what fixture tests call; `enforce()` is what gates call.

```rust
//! A named structure invariant: a human-readable description paired with the
//! check that finds its violations. A gate instantiates a rule through an
//! intention-revealing constructor (or [`Rule::new`] for a gate-local rule)
//! and calls `enforce(env!("CARGO_MANIFEST_DIR"))` — the caller supplies its
//! own manifest directory; this crate never resolves one itself.

use std::path::PathBuf;

use crate::source::SourceTree;
use crate::violation::Violation;

/// What a rule does: given a crate's source tree, the violations it finds.
/// Named rather than written out in the field position because
/// `clippy::type_complexity` rejects the inline boxed-closure type under
/// `clippy --all-targets -D warnings`. (A workspace whose lint table sets
/// `type_complexity = "allow"` — as `rust-workspace-setup` prescribes — would
/// accept the inline form; the alias reads better regardless and costs nothing.)
type Check = Box<dyn Fn(&SourceTree) -> Vec<Violation>>;

/// A named structure invariant: a human-readable description paired with the
/// check that produces the violations.
pub struct Rule {
    description: String,
    check: Check,
}

impl Rule {
    pub fn new(
        description: impl Into<String>,
        check: impl Fn(&SourceTree) -> Vec<Violation> + 'static,
    ) -> Self {
        Self {
            description: description.into(),
            check: Box::new(check),
        }
    }

    /// The violations found in the crate rooted at `manifest_dir`.
    #[must_use]
    pub fn violations(&self, manifest_dir: impl Into<PathBuf>) -> Vec<Violation> {
        (self.check)(&SourceTree::from_manifest_dir(manifest_dir))
    }

    /// Runs the rule against the crate rooted at `manifest_dir` and fails the
    /// test on any violation.
    pub fn enforce(&self, manifest_dir: impl Into<PathBuf>) {
        let violations = self.violations(manifest_dir);
        let report = violations
            .iter()
            .map(ToString::to_string)
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

`Rule::new` is public on purpose: it lets a crate define policy no other crate
has, in its own gate tree, without touching this library. It is **not** a way to
re-express a library rule with a narrower scan.

---

## `src/source.rs`

The whole file-access API a rule gets, plus line classifiers for checks that do
not need a parse.

```rust
//! Source-reading primitives for structure rules: the source tree (locate a
//! crate's checked roots, walk them, read files, relativize paths) and
//! single-line classifiers. Rooted at the consuming gate's
//! `env!("CARGO_MANIFEST_DIR")`, so the working directory does not matter.

use std::path::{Path, PathBuf};

/// A crate's source tree: walks its checked roots for `.rs` files, reads
/// them, and renders paths relative to the crate root.
pub struct SourceTree {
    crate_root: PathBuf,
}

impl SourceTree {
    /// Roots the tree at the consuming crate's manifest directory — the
    /// caller's `env!("CARGO_MANIFEST_DIR")`, never this crate's own.
    pub fn from_manifest_dir(manifest_dir: impl Into<PathBuf>) -> Self {
        Self {
            crate_root: manifest_dir.into(),
        }
    }

    /// The crate root itself. Needed by rules whose subject is not a source
    /// file — the workspace-coverage rule walks up from here to find the
    /// workspace manifest.
    #[must_use]
    pub fn crate_root(&self) -> &Path {
        &self.crate_root
    }

    #[must_use]
    pub fn rust_files(&self) -> Vec<PathBuf> {
        Self::rust_files_under(&self.crate_root.join("src"))
    }

    /// Files under `src/<layer>/`, plus the sibling `src/<layer>.rs` facade
    /// file when it exists — without it a layer rule would miss violations in
    /// the file that declares the layer's modules.
    #[must_use]
    pub fn rust_files_in(&self, layer: &str) -> Vec<PathBuf> {
        let mut files = Self::rust_files_under(&self.crate_root.join("src").join(layer));
        let facade = self.crate_root.join("src").join(format!("{layer}.rs"));
        if facade.is_file() {
            files.push(facade);
            files.sort();
        }
        files
    }

    #[must_use]
    pub fn rust_files_in_roots(&self, roots: &[&str]) -> Vec<PathBuf> {
        let mut files = Vec::new();
        for root in roots {
            files.extend(Self::rust_files_under(&self.crate_root.join(root)));
        }
        files.sort();
        files
    }

    /// The crate directory's name (e.g. `core`), used to qualify rendered
    /// violation paths with the crate folder they live in.
    #[must_use]
    pub fn crate_dir_name(&self) -> String {
        self.crate_root
            .file_name()
            .map(|name| name.to_string_lossy().into_owned())
            .unwrap_or_default()
    }

    /// How a violation names a file: the crate folder followed by the
    /// crate-relative path, so a failure report identifies the file even when
    /// several crates' gates run in one session.
    #[must_use]
    pub fn reported_path(&self, file: &Path) -> String {
        format!("{}/{}", self.crate_dir_name(), self.relative_unix(file))
    }

    /// Reads a file, panicking with the path on failure — a structure rule
    /// has no meaningful recovery from an unreadable source file.
    #[must_use]
    pub fn read(&self, path: &Path) -> String {
        std::fs::read_to_string(path)
            .unwrap_or_else(|error| panic!("failed to read {}: {error}", path.display()))
    }

    #[must_use]
    pub fn relative(&self, path: &Path) -> String {
        path.strip_prefix(&self.crate_root)
            .unwrap_or(path)
            .display()
            .to_string()
    }

    #[must_use]
    pub fn relative_unix(&self, path: &Path) -> String {
        path.strip_prefix(&self.crate_root)
            .unwrap_or(path)
            .components()
            .map(|component| component.as_os_str().to_string_lossy().into_owned())
            .collect::<Vec<_>>()
            .join("/")
    }

    fn rust_files_under(directory: &Path) -> Vec<PathBuf> {
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
pub struct SourceLine<'line>(pub &'line str);

impl SourceLine<'_> {
    #[must_use]
    pub fn is_comment(&self) -> bool {
        self.0.trim_start().starts_with("//")
    }

    /// Detects a module-level (column-0) data/impl item. Trait members are
    /// indented and therefore ignored, so a hit means a non-trait item sits at
    /// the top level of a `port.rs`.
    #[must_use]
    pub fn module_level_item(&self) -> Option<&'static str> {
        let line = self.0;
        if line.starts_with([' ', '\t']) {
            return None;
        }
        let mut rest = line;
        if let Some(after_pub) = rest.strip_prefix("pub") {
            if after_pub.starts_with('(') {
                let close_paren = after_pub.find(')')?;
                rest = after_pub[close_paren + 1..].trim_start();
            } else if after_pub.starts_with([' ', '\t']) {
                rest = after_pub.trim_start();
            }
        }
        for keyword in ["struct", "enum", "union", "impl"] {
            if let Some(after_keyword) = rest.strip_prefix(keyword)
                && after_keyword.starts_with([' ', '\t', '<', '('])
            {
                return Some(keyword);
            }
        }
        None
    }
}
```

### Notes on the scanning choices

- **`collect` ignores unreadable directories** (`let Ok(entries) = … else { return }`)
  rather than panicking, so a rule scanning a root that does not exist — `tests/`
  in a crate with no tests — reports nothing instead of failing. `read` does the
  opposite and panics, because a file the walker just found but cannot read is a
  real problem.
- **Results are sorted** so violation order is stable across runs and machines.
  An unstable report makes a failing gate look like it changed when it did not.
- **`reported_path` prefixes the crate folder.** Use it whenever constructing a
  violation: `cargo test --workspace` interleaves ten crates' output, and a bare
  crate-relative path is then ambiguous.
