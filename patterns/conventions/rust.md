---
name: rust-convention-enforcement-pattern
description: >-
  Use when a Rust workspace's conventions are enforced by prose and review
  instead of by the build — when a rule your own style or testing guide marks
  CRITICAL turns out to be violated at scale and reviewers never caught it,
  when one crate's structure test scans its siblings so a violation fails the
  wrong crate's gate, when the scanning machinery is about to be copy-pasted
  into a second crate's gate, or when a rule like "never break SRP without
  asking the operator" has no mechanical meaning. Establishes convention rules
  as a dev-only library crate consumed per crate (the ArchUnit pattern), with
  zero-knob rule constructors and operator-permission ledgers. Rust; the
  packaging principle is language-agnostic.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.1"
---

# Convention Enforcement Pattern (Rust — the ArchUnit Pattern)

## Purpose

**In one line:** convention rules are an ordinary library, consumed by ordinary
tests, executed by each crate against itself.

A convention that lives only in prose is enforced at prompt time and review
time. Both fail against volume. The measured lesson from the reference codebase:
a rule its own testing guide marks CRITICAL — "test files contain only tests" —
was violated across **143 files / 477 module-scope items** workspace-wide, and
reviewers consistently missed it, because review is diff-scoped and the
violation is a whole-file property. Mechanizing that one rule closed the
enforcement gap. Packaging it correctly is what this pattern is about.

> **Core principle (separation of concerns / single responsibility):** three
> different things are being decided, so they live in three different places.
> The **rule library** owns *how a violation is detected*. Each crate's **gate**
> owns *which rules that crate adopts*. The **permission ledger** owns *which
> exceptions an operator approved, and why*. Keep those three answers apart, and
> never let a fourth place — a knob at the call site — appear.

## When to Apply

Apply this pattern when **all** of these hold:

- The project is a Cargo **workspace with two or more members** (see
  `rust-workspace-setup`). Locality is the whole point; with one crate there is
  nowhere for a violation to be reported in the wrong place.
- There are conventions a formatter and linter cannot express — file layout,
  test-tree discipline, import scope, definition shape, size budgets.
- Code volume outpaces review. Agent-written code is the usual cause.

Reach for it when you see these **symptoms**:

- A rule your own guide marks CRITICAL turns out to be violated in dozens of
  files, and every review passed.
- One crate's structure test scans the whole workspace, so a violation in
  `worker/tests/` fails `cargo test -p core --test structure` — the wrong
  crate's gate, with two ambiguous owners for one violation.
- A developer or agent iterating with a focused per-crate test command learns
  about a violation only from CI.
- You are about to copy a non-trivial `syn` walker into a second crate's gate.
- A convention says "ask the operator for permission before breaking this," and
  nothing distinguishes a granted violation from an unnoticed one.
- A new workspace member silently has no gate at all.

**When NOT to use:** a single-crate project — keep the in-crate
`tests/structure/` support tree from `rust-architecture-test-setup`; extracting
a library crate buys locality you do not yet need. Also skip for scripts, CLIs,
and throwaway tools.

## The Problem It Solves

Conventions in a mature repository sit at three very different enforcement
strengths, and only the first one holds:

| Strength | Mechanism | Holds? |
|---|---|---|
| **Mechanical** | rustfmt, clippy, cargo-test structure gates | Yes — never violated for long |
| **Prose** | style/testing guide rules an agent is briefed with | No — 477 violations of one CRITICAL rule |
| **Judgment** | SRP's "one reason to change", cohesion, naming intent | Advisory review only; no tool can decide it |

The work is to move rules from the second row into the first — one at a time, as
each proves worth mechanizing — while leaving the third row alone. Two obvious
packagings both fail:

```rust
// ❌ Shape 1: the central scan. One crate's gate walks every sibling's tree.
// tests/structure/layout.rs, in the biggest crate
#[test]
fn should_contain_only_tests() {
    // scans ../worker/tests, ../crates/*/tests, … from here
    Rule::test_files_contain_only_tests(WORKSPACE_ROOTS).enforce();
}
// Consequence: a violation in the worker fails the *core* crate's gate.
// `cargo test -p worker` stays green. The violation has two owners, and the
// per-crate iteration loop never sees it.
```

```rust
// ❌ Shape 2: copy the scanner. Each crate's gate gets its own support/ tree.
// crates/a/tests/structure/support/source.rs   ← 150 lines of syn walker
// crates/b/tests/structure/support/source.rs   ← the same 150 lines
// crates/c/tests/structure/support/source.rs   ← …drifting already
// Consequence: ~8 copies of a non-trivial walker whose exemption lists
// diverge silently. Nobody notices that crate C's copy stopped catching
// aliases eight months ago.
```

The first trades locality for reuse; the second trades reuse for locality. The
ArchUnit pattern refuses the trade.

## The Pattern: One Rule Library, One Gate Per Crate

ArchUnit (Java, TNG Technology Consulting, 2017) established the idiom of
writing **architecture rules as unit tests**: a library models the code, a
fluent API asserts rules over it, and the standard test runner executes them.
Ports exist across ecosystems (ArchUnitNET, PyTestArch, ts-arch). Rust has no
dominant equivalent, and the ecosystem norm — hand-rolled structure tests — is
exactly this, minus a shared home for the rules.

Four parts, each owning one responsibility:

| Part | Responsibility | Holds |
|---|---|---|
| **rule library** | Decide what a violation *is* | The source-tree walker, the `Violation` type, the `syn` scanners, and one intention-revealing constructor per universal rule |
| **per-crate gate** | Declare which rules this crate adopts, and scan only its own tree | `tests/structure.rs` — one `#[test]` per adopted rule, plus any crate-specific policy rule |
| **permission ledger** | Record which exceptions an operator approved, and why | Private `GRANTED_*` constants inside the rule library, plus stale-grant detection |
| **fixture tests** | Prove each rule fires, and does not over-fire | The rule library's own test tree, with per-test fixture source trees |

```
        crates/<project>-conventions/          ← dev-only position in the graph;
        ┌──────────────────────────────┐         depends on no workspace member
        │  source.rs  violation.rs     │  mechanics
        │  rule.rs                     │
        │                              │
        │  layout.rs                   │  one zero-arg constructor
        │  import_scope.rs             │  per universal rule
        │  support_discipline.rs       │
        │  srp_discipline/             │
        │    ├── budgets.rs            │  ← private constants (policy)
        │    └── ledgers.rs            │  ← every GRANTED_* entry (permissions)
        └──────────────┬───────────────┘
                       │  declared in each consumer's [dev-dependencies]
      ┌────────────────┼────────────────┬────────────────┐
      ▼                ▼                ▼                ▼
  core/tests/     worker/tests/    crates/a/tests/   crates/b/tests/
  structure.rs    structure.rs     structure.rs      structure.rs
      │                │                │                │
      └── each calls `rule().enforce(env!("CARGO_MANIFEST_DIR"))` ──┘
                 scanning ONLY its own crate root
```

The dependency direction is one-way and dev-only: every member declares the
conventions crate in `[dev-dependencies]`; the conventions crate declares no
workspace member at all. Production dependency graphs are untouched.

### The four parts, by responsibility

1. **The rule library.** A workspace member (`crates/<project>-conventions/`)
   with `publish = false`. It holds the mechanics — the source-tree walker, the
   violation type, the `syn` item/attribute/scope visitors — and above them one
   **constructor per rule**, named as the invariant it asserts. It never
   resolves its own location: the crate root is an argument, which is precisely
   what makes a rule scan the caller's tree rather than the library's.

2. **The per-crate gate.** Every member with a `tests/` tree owns
   `tests/structure.rs`. Its body is that crate's adopted policy, stated as
   tests: one `#[test]` per rule, each a single line. Because universal rules
   are zero-knob (below), the line for a given rule is *character-identical* in
   every crate that adopts it — so a difference between two crates can only be
   *which* rules they adopt, which is visible in the diff, rather than *how* a
   rule was configured, which would not be.

3. **The permission ledger.** Some violations are legitimate and the honest
   answer is a recorded exception. Each such rule carries a private `GRANTED_*`
   constant *inside the library*. Adding an entry is a diff to one reviewed
   file — which is what gives "ask the operator for permission" a mechanical
   meaning: the PR that edits the ledger **is** the permission request. Ledgers
   start empty and only ever hold individually understood decisions.

4. **Fixture tests.** Rules that live inside one crate's gate are usually
   untested — nothing proves the walker still catches what it claims. As a
   library, each rule gets fixture source trees proving it fires on a violation
   *and stays quiet on the legitimate near-miss*. Give each fixture test its own
   uniquely-suffixed directory so the suite stays parallel-safe (see the
   [parallel test isolation pattern](../testing/parallel_test_isolation_pattern.md)).

## Zero-Knob Rules and the Escalation Ladder

A rule the whole workspace must obey **takes no configuration**. Not a path
list, not an allowlist, not a severity flag. The constructor's entire signature
is `fn() -> Rule`.

This is the load-bearing constraint of the pattern, because a knob at the call
site moves policy into ten gate files where it drifts silently — and a
divergence expressed as a parameter reads, in review, as configuration rather
than as a decision. Parameterized constructors exist only where crates
*legitimately* differ in kind (a layering rule applies to layered crates, not to
leaf primitives crates), never to soften a universal rule for one caller.

Zero-knob does not mean "no exceptions ever." It means an exception is never
cheaper than the honest fix. When a universal rule fires on something that looks
legitimate, work down this ladder and **stop at the first rung that applies**:

1. **Change the code.** Rename the directory, split the file, move the helper.
   Most "exceptions" are the rule doing its job.
2. **Change the constant in the rule's own module.** If the policy is wrong for
   the whole workspace, edit the private const in the library — one diff, one
   place, reviewed as a policy change, applied everywhere at once.
3. **Add an in-source marker the rule itself defines.** For a genuinely local,
   self-documenting carve-out, let the rule recognise a marker in the source.
   The exception is then visible where it applies, and the rule still owns its
   meaning.
4. **Add a second, deliberately-named constructor.** When two populations
   legitimately differ, express it as two named rules
   (`x_are_forbidden()` / `x_are_allowed_in_generated_code()`), not as a
   parameter. The gate diff then states which policy the crate adopted.

What is deliberately **not** on the ladder: a knob at the call site.

An allowlist inherited from a predecessor rule deserves suspicion rather than
migration. In the reference codebase the `mod.rs` ban's allowlist turned out to
be exempting a file that was already dead — it declared a submodule that did not
exist on disk, which a compiled file could not do. The exemption was
grandfathering a corpse, so the migrated rule shipped without one.

**A syntactic rule can only promise a syntactic exception.** Where a rule's
intent is semantic ("a generated name used in exactly one function"), the gate
can check only a shape — in the reference codebase, "an aliased import whose
terminal item is named `Result` and whose *immediately-preceding path segment*
ends in `_response`", which is where a prost-generated `oneof` enum sits. Note
that it keys on the import path, not on the enclosing source module; the looser
reading would match a far wider set. Write the shape down as the
contract, state the residual bypass, and accept it as narrower than the
alternatives — do not pretend the gate enforces the intent. Equally, know the
blind spots and record them: token streams inside macros and attribute lists are
opaque to `syn`, and generated files outside the scanned roots are never parsed.

## The Permission Ledger

Four semantics make a ledger a decision record instead of a debt baseline:

- **Exact keys.** A violation is silenced only by its exact key
  (`<crate>/<file>::<fn>`, or `<crate>/<file>` for a whole-file grant). No
  globs, no prefixes, no wildcards.
- **The diff is the request.** A PR that edits a ledger is the operator
  permission request, reviewed as such.
- **A stale grant fails the gate.** When the underlying violation disappears,
  the grant must be handed back. Grants are matched per crate, so each crate
  audits only its own entries.
- **Ledgers start empty.** They accumulate only individually understood
  decisions — never a bulk snapshot of what the tree happened to contain.

That last point is the deliberate rejection of ArchUnit's own `FreezeArchRule`
(grandfather existing violations, fail only new ones). Freezing enables instant
adoption on legacy code, which is a real advantage — but baselines rot and
permanently blur what "clean" means. A red gate is loud debt; a baseline is
silent debt.

**Where a decision needs a reason, make the reason part of the key.** For rules
whose adjudication is genuinely a judgment call, a bare "this subject is
allowed" entry would let one approval silently authorize a later, unrelated
violation. Give the grant structure instead: the exact subject, the exact
approved set, and a non-empty rationale — then have the gate reject an unsorted
set, an empty rationale, a duplicate grant, a set that no longer matches, and a
grant whose subject disappeared.

**Some rules must not auto-classify.** When syntax cannot distinguish a
legitimate case from a violation, the rule's job is to *demand a decision*, not
to guess one. Detection then has three outcomes: approve with a reasoned grant,
remediate, or **remain red while the case is understood**. Automatic analysis is
evidence for the reviewer, never a silent verdict.

**Keep the ledger and the decision record in sync.** The ledger is the
mechanism; the ADR is the reasoning. In the reference codebase they drifted: the
ADR records five approved cohesion grants and names five further types that
"stay red" pending remediation or audit. The ledger now carries nine grants —
four of those five red types among them — and the fifth was resolved the other
way, by a Case-B split into single-port types, so it no longer exists.

Every one of those outcomes is defensible and each grant carries its own
rationale, so the gate is correct and the tree is clean. What is missing is that
the decision record explains none of it: a reader who trusts the ADR believes
five types are awaiting adjudication that were in fact settled. Amend the record
in the same change that edits the ledger — otherwise the mechanism stays honest
while the reasoning rots, which is the harder half to reconstruct later.

## Worked Example (Rust, ironbox)

Twelve universal rules, ten workspace members, ten gates.

**Register the member first.** With an explicit `members` list, the crate is
invisible to Cargo until it is listed — and that is a hard error, not a warning:

```toml
# Cargo.toml (workspace root)
[workspace]
members = ["core", "worker", "crates/ironbox-conventions", /* … */]
```

**Then the library manifest** — `publish = false`, no workspace dependency:

```toml
# crates/ironbox-conventions/Cargo.toml
[package]
name = "ironbox-conventions"
edition = "2024"
description = "Dev-only convention rules library (ADR-R12, ArchUnit pattern): the source-tree scanning machinery and zero-knob rule constructors consumed by every workspace member's tests/structure gate, exclusively from [dev-dependencies]. Depends on nothing in the workspace."
publish = false

[dependencies]
syn = { version = "2", features = ["full", "visit"] }
proc-macro2 = { version = "1", features = ["span-locations"] }

[dev-dependencies]
uuid = { version = "1", features = ["v7"] }   # per-test fixture directories

[lints]
workspace = true
```

Two details worth copying. `span-locations` is what makes `syn` spans carry real
line numbers outside a proc-macro context — without it a violation cannot cite a
line.

And the parser dependencies **must** sit in the library's own `[dependencies]`,
never in its `[dev-dependencies]`. This looks inconsistent with calling the crate
"dev-only" and is a standing trap when copying the manifest, so be precise about
why: Cargo does not expose a crate's `[dev-dependencies]` to its lib target's
*normal* build — the build every consumer performs — only to test, example, and
bench targets, and to the lib's own `#[cfg(test)]` test build. The rule
constructors that `use syn::…` are ordinary non-test lib code, so a
dev-dependency would not resolve and the crate would not compile.

(Note the scope of that rule, because the shorter version of it is wrong: a
`#[cfg(test)]` module inside `src/` *can* use a dev-dependency, which is why most
projects keep inline unit tests working without a second manifest entry.)

"Dev-only" here describes the crate's **position in the graph** — consumers
declare *the conventions crate* under their `[dev-dependencies]`, which is what
keeps it out of every production dependency tree — not the shape of its own
manifest.

Consumers declare it by path:

```toml
# core/Cargo.toml
[dev-dependencies]
# Structure gate (tests/structure): the universal rules + scanning machinery.
ironbox-conventions = { path = "../crates/ironbox-conventions" }
```

**The public surface** — mechanics plus one constructor per rule, and nothing
else:

```rust
// crates/ironbox-conventions/src/lib.rs
//! A rule scans the crate rooted at the manifest directory the gate passes to
//! [`Rule::enforce`] — this crate never resolves `env!("CARGO_MANIFEST_DIR")`
//! itself.

pub use import_scope::use_statements_stay_at_module_scope;
pub use inline_path_depth::inline_crate_paths_stay_within_the_segment_cap;
pub use layout::{
    mod_files_are_forbidden, test_files_contain_only_tests, tests_do_not_live_in_src,
};
pub use rule::Rule;
pub use source::{SourceLine, SourceTree};
pub use srp_discipline::{
    argument_count_allowances_are_confined_to_composition,
    multi_port_concrete_types_have_explicit_cohesion_decisions,
    production_files_stay_within_the_line_budget, production_functions_stay_within_the_line_budget,
};
pub use support_discipline::{
    mocks_files_exist_only_under_unit_support, support_facades_hold_only_module_declarations,
    support_files_do_not_mix_doubles_with_helpers,
};
pub use violation::Violation;
```

Every one of those twelve constructors is `pub fn …() -> Rule` — zero
parameters, no exceptions. Note what is *not* exported: the ledgers, the size
budgets, and the plumbing-trait exclusion list are private to their modules.
Policy is unreachable from a call site by construction.

The module split mirrors the responsibilities. `source.rs` / `rule.rs` /
`violation.rs` are mechanics. `layout.rs`, `import_scope.rs`,
`inline_path_depth.rs`, `support_discipline.rs` are rule constructors with their
private scanners. `composition_policy.rs` is a cross-rule *policy* module — it
owns the single definition of "inside the composition root", which two separate
rules consult; when more than one rule shares an exemption, give that exemption
one home rather than two copies. And `srp_discipline/` repeats the same split one
level down: `walk.rs` (shared parse-and-visit helper), `budgets.rs` (the private
size constants and the plumbing-trait list), `ledgers.rs` (the grants),
`grant.rs` (the grant type and its pure decision function), with
`function_budget.rs` / `argument_count.rs` / `multi_port.rs` holding three of the
four rule constructors — the file-budget rule is small enough to live in the
`srp_discipline.rs` facade itself.

**The `Rule` type** — a description paired with a check, and the crate root as
its only input:

```rust
// crates/ironbox-conventions/src/rule.rs
pub struct Rule {
    description: String,
    check: Box<dyn Fn(&SourceTree) -> Vec<Violation>>,
}

impl Rule {
    pub fn new(
        description: impl Into<String>,
        check: impl Fn(&SourceTree) -> Vec<Violation> + 'static,
    ) -> Self { /* … */ }

    /// The violations found in the crate rooted at `manifest_dir`.
    #[must_use]
    pub fn violations(&self, manifest_dir: impl Into<PathBuf>) -> Vec<Violation> {
        (self.check)(&SourceTree::from_manifest_dir(manifest_dir))
    }

    /// Runs the rule against the crate rooted at `manifest_dir` and fails the
    /// test on any violation.
    pub fn enforce(&self, manifest_dir: impl Into<PathBuf>) {
        let violations = self.violations(manifest_dir);
        let report = violations.iter().map(ToString::to_string)
            .collect::<Vec<_>>().join("\n");
        assert!(
            violations.is_empty(),
            "{}: {} violation(s)\n\n{report}\n",
            self.description, violations.len(),
        );
    }
}
```

`Rule::new` being public is the deliberate escape valve for **crate-specific**
policy: a gate can define its own rule locally, with an inline closure, without
touching the shared library. The reference codebase does exactly this for a
one-off boundary rule that bans a specific service import from one module —
policy that would be noise in a shared crate.

**Violations cite a place, not a vibe.** `Violation` owns its own rendering —
`file:line: message -> source` when it knows the line, `file: message` for a
whole-file finding — so a rule never hand-formats a string. Carrying the
offending source is what lets a reader fix the violation without opening the
file:

```
inline crate/super paths stay within the segment cap (rust-code-style Rule 7): 93 violation(s)

core/src/infrastructure/api/job/handler.rs:129: inline crate::/super:: path exceeds 3 segments
  (rust-code-style Rule 7); bring the item into scope with use and shorten the call site
  -> Ok(Sse::new(stream).keep_alive(crate::infrastructure::api::sse::default_keep_alive()))
```

### Anatomy of a rule

A rule is four things: a description, a file selection, a predicate, and a
violation. The `SourceTree` passed to every check closure is the entire
file-access API a rule gets:

```rust
// crates/ironbox-conventions/src/source.rs — the methods a rule actually calls
impl SourceTree {
    pub fn from_manifest_dir(manifest_dir: impl Into<PathBuf>) -> Self;

    pub fn rust_files(&self) -> Vec<PathBuf>;                  // src/ only
    pub fn rust_files_in(&self, layer: &str) -> Vec<PathBuf>;  // src/<layer>/ + its facade
    pub fn rust_files_in_roots(&self, roots: &[&str]) -> Vec<PathBuf>;  // ["src", "tests"]

    pub fn read(&self, path: &Path) -> String;           // panics with the path
    pub fn relative_unix(&self, path: &Path) -> String;
    pub fn reported_path(&self, file: &Path) -> String;  // "<crate-dir>/<rel-path>"
    pub fn crate_dir_name(&self) -> String;
}
```

Use `reported_path` when building a violation: it prefixes the crate folder, so a
failure identifies its file even when ten crates' gates run in one session.
`Violation` has exactly two constructors — the four-argument one is what makes a
report actionable, since it carries the offending source:

```rust
Violation::at_line(file: &str, line: usize, source: &str, message: &str)
Violation::in_file(file: &str, message: &str)
```

Now a complete rule. The `mod.rs` ban is the whole shape in fifteen lines, and it
needs no parser at all:

```rust
// crates/ironbox-conventions/src/layout.rs
const MOD_FILE_NAME: &str = "mod.rs";
const MOD_FILE_SEARCH_ROOTS: &[&str] = &["src", "tests"];
const MOD_FILE_MESSAGE: &str = "`mod.rs` is the legacy module layout; declare the module from a \
     sibling `<module_name>.rs` file, or reach a cross-test-crate module with `#[path = \"...\"]`";

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
```

Four things in it are worth copying deliberately. The three policy values are
**private module constants, not parameters** — that is the zero-knob rule as
code, and it is the whole reason the call site cannot soften the rule. The
message names both the rule's origin and the remedy, so a failure is actionable
without opening the style guide. The constructor is `#[must_use]`, so building a
rule and forgetting to `enforce()` it is a warning rather than a silently
inert gate. And the check is a pure function of the tree, which is what makes
fixture-testing it trivial.

Rules that need *structure* rather than filenames follow the same skeleton with
`syn::parse_file(&source_tree.read(&file))` and a visitor in place of the
filename predicate; the exported `SourceLine` classifiers cover the cheap
middle ground (is this line a comment, is this a column-zero item) without a
parse. Reach for the AST only when neither a path nor a line can answer the
question — the `mod.rs` ban above never parses anything.

**Gate shape A — the flat gate**, for a crate with no policy of its own. Every
adopted rule is one line, and the file contains no crate-specific *text* at all:
`env!("CARGO_MANIFEST_DIR")` is the same token in every crate and merely
*expands* to the crate that compiles it. That is the whole trick, and it is why
these files come out byte-identical across crates adopting the same set — never
substitute a literal crate name for it.

Abridged below to two of its eight modules; the real file is 101 lines and adopts
all twelve rules, one module per rule:

```rust
// crates/ironbox-task-contracts/tests/structure.rs  (abridged)
use ironbox_conventions::mod_files_are_forbidden;
// … seven more imports, one per adopted rule

mod mod_files {
    use super::*;

    #[test]
    fn should_not_use_the_legacy_mod_file_layout() {
        mod_files_are_forbidden().enforce(env!("CARGO_MANIFEST_DIR"));
    }
}

mod srp_discipline {
    use ironbox_conventions::production_functions_stay_within_the_line_budget;

    #[test]
    fn production_functions_should_stay_within_the_line_budget() {
        production_functions_stay_within_the_line_budget().enforce(env!("CARGO_MANIFEST_DIR"));
    }
}
```

**Gate shape B — the module-tree gate**, for a crate that also owns policy. The
entry file is declarations only; adopted universal rules and local policy rules
sit side by side as modules:

```rust
// core/tests/structure.rs
mod structure {
    pub mod support;                   // ← this crate's own rule helpers ONLY;
                                       //   never a second copy of the library's
                                       //   Rule/Violation/SourceTree (see Adoption)

    mod assembly;                      // ← crate-specific policy
    mod execution_dispatch_boundary;   // ← crate-specific policy (Rule::new)
    mod layering;                      // ← crate-specific policy
    mod layout;                        // ← adopted universal rules
    mod naming;
    mod ports;
    mod srp_discipline;                // ← adopted universal rules
    mod support_discipline;            // ← adopted universal rules
    mod vocabulary;
    mod workspace_deps;
}
```

**Adoption is a list, not a configuration — and that is the point.** Flat versus
module-tree is a cosmetic choice; what matters is that each crate's adopted *set*
is readable in one file. In the reference workspace all ten members adopt all
twelve universal rules, and the four crates with no local policy carry
**byte-identical** gate files. Six crates add local policy modules on top.

Uniformity is the useful property here: because the line for a given rule is
identical everywhere, the current state is verifiable at a glance, and any future
divergence — a crate dropping a rule — must appear in a diff as a deliberate act.
Had the same divergence been expressed as a constructor argument, it would read
in review as configuration and pass unremarked.

**The ledger** — one file an operator edits, with the reason beside the key:

```rust
// crates/ironbox-conventions/src/srp_discipline/ledgers.rs
/// Operator-granted long functions. Key: `<crate-dir>/<src path>::<fn name>`.
pub(super) const GRANTED_LONG_FUNCTIONS: &[&str] = &[
    // Composition-root / process-entrypoint wiring: single responsibility is
    // "wire the graph" or "process entrypoint"; decomposition would be
    // speculative churn.
    "core/src/main.rs::main",
    "core/src/composition/factory.rs::create_application_services",
    "core/src/composition/wiring.rs::spawn_runtime_workers",
];

pub(super) const GRANTED_ARGUMENT_COUNT_ALLOWANCES: &[&str] = &[];
pub(super) const GRANTED_LONG_FILES: &[&str] = &[];

// … GRANTED_MULTI_PORT_COHESION lives here too (shown below), plus the
//   stale-grant helper — four ledgers in one reviewed file
```

Two of the three ledgers above being empty is the ratchet working: when the rules
landed, the tree held 17 argument-count confessions and an oversized file. All of
them were **fixed**, not granted.

**Stale-grant detection** — a grant that no longer matches becomes a violation
itself, scoped so each crate audits only its own entries:

```rust
// crates/ironbox-conventions/src/srp_discipline/ledgers.rs
pub(super) fn append_stale_grants(
    granted: &[&str],
    crate_dir: &str,
    matched_grants: &HashSet<String>,
    violations: &mut Vec<Violation>,
);
```

It reports every grant scoped to this crate that went unmatched, with the message
"stale ledger grant: no matching violation remains — remove the entry". Two
details make it work. Scoping is by key prefix — `<crate>/` for path keys and
`<crate>::` for type keys — so each crate audits only its own entries out of one
shared array. And a rule inserts a key into `matched_grants` **only when it
actually finds the matching violation and suppresses it**, so anything left
unmatched is stale by construction, with no separate bookkeeping anyone could
forget to update.

**A reasoned, exact-set grant** — for the rule that must demand a decision
rather than guess one. A concrete type implementing two or more non-plumbing
ports is an *adjudication trigger*, not proof of a violation: one cohesive
adapter may correctly serve several consumer-specific ports (Interface
Segregation), while another accumulates unrelated ones (an SRP violation).
Syntax cannot tell those apart, so the grant carries the human decision:

```rust
// crates/ironbox-conventions/src/srp_discipline/grant.rs — the type and the
// decision function. The grant *instances* live in ledgers.rs (shown above).
#[derive(Debug)]
pub struct MultiPortCohesionGrant {
    pub type_key: &'static str,
    pub ports: &'static [&'static str],
    pub rationale: &'static str,
}

// Debug + PartialEq are load-bearing: the fixture tests assert_eq! on these.
#[derive(Debug, PartialEq, Eq)]
pub enum MultiPortDecisionError {
    Unclassified,
    DuplicateGrant,
    UnsortedOrDuplicatePorts,
    EmptyRationale,
    PortSetMismatch,
    StaleGrant,
}

pub fn assess_multi_port_cohesion_decision(
    actual_ports: &[&str],
    grants: &[&MultiPortCohesionGrant],
) -> Result<(), MultiPortDecisionError>;
```

Keep it a **pure function**, separate from the scanner that finds the ports — that
is what lets the fixture tests exercise every branch without a source tree, and
without exposing a configurable public rule.

Its branch *order* is load-bearing. Duplicate grants are rejected before arity is
considered. A subject that has dropped below two ports while its grant survives is
`StaleGrant`, not silently acceptable. Only then does an absent grant become
`Unclassified`. The sorted-ports and non-empty-rationale checks run *before* the
set comparison, so a malformed grant reports as malformed rather than
masquerading as a mismatch.

Requiring the port set **sorted and exact** is what stops an approval for two
cohesive ports from silently authorizing an unrelated third one later: adding a
port invalidates the grant automatically, and the type goes back through
adjudication. A real entry, with the rationale naming the shared mechanism:

```rust
// crates/ironbox-conventions/src/srp_discipline/ledgers.rs — one entry of
// GRANTED_MULTI_PORT_COHESION
MultiPortCohesionGrant {
    type_key: "core/src/application/restore/progress_reporter.rs::ExecutorRestoreProgressReporter",
    ports: &["ProgressSink", "RestoreTargetProgressReporter"],
    rationale: "Both ports cooperate through one synchronized latest snapshot and jointly enforce the no-zero-byte-regression restore-progress invariant.",
},
```

**Fixture tests — fires, and does not over-fire.** Two sibling modules,
`should_flag` and `should_pass`, are the whole discipline. Each test writes a
throwaway crate tree into a uniquely-suffixed directory, runs the rule via
`violations()` rather than `enforce()`, and asserts on the result:

```rust
// crates/ironbox-conventions/tests/unit/layout.rs
mod should_flag {
    use super::*;

    #[test]
    fn free_fn_at_module_scope() {
        let dir = temp_crate_dir();          // UUIDv7-suffixed: parallel-safe
        write_test_file(&dir, "unit/foo.rs", r"
fn helper_that_does_not_carry_a_test_attr() {}
");
        let violations = test_files_contain_only_tests().violations(&dir);
        assert!(!violations.is_empty(), "expected a violation for a bare fn");
    }
}

mod should_pass {
    use super::*;

    #[test]
    fn use_import_at_module_scope_is_allowed() {
        let dir = temp_crate_dir();
        write_test_file(&dir, "unit/foo.rs", r"
use std::collections::HashMap;

mod my_tests {
    use super::*;
    #[test]
    fn it_works() {}
}
");
        let violations = test_files_contain_only_tests().violations(&dir);
        assert!(violations.is_empty(), "unexpected violations: {violations:?}");
    }
}
```

Every rule-owned exemption gets its own `should_pass` test, so an exemption
cannot silently widen. To unit-test a **ledger's decision semantics** without
exposing a configurable public API, isolate the pure decision function in its own
module and pull it into the test tree directly:

```rust
// crates/ironbox-conventions/tests/unit/support/grant.rs
mod production {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/src/srp_discipline/grant.rs"));
}
```

Each branch of the decision function then gets a test: exact match → `Ok`;
two ports with no grant → `Unclassified`; an added third port → `PortSetMismatch`;
back down to one port with a grant still present → `StaleGrant`; blank rationale
→ `EmptyRationale`; two grants for one type → `DuplicateGrant`.

**The library hosts its own gate.** The conventions crate carries
`tests/structure.rs` adopting all twelve rules against itself. A rule library
that violates its own rules teaches the opposite of what it enforces.

## Adoption

**Greenfield (the cheap case).** An empty repository has zero violations, so
every rule lands green at commit 1 and every ledger starts — and stays — empty.
There is nothing to ratchet, nothing to grandfather, and no remediation stream.
This is the whole reason to do it at setup: the same rules cost days to adopt
later, and the ledger entries you never needed are the refactors you never paid
for.

**Existing codebase.** Default to **clean the violations to zero, then land the
rule**. Where remediation is mechanical, sweep it first. Where remediation is
genuine design work, a rule may land **red by explicit operator decision** — a
real, un-`#[ignore]`d, failing test — on the reasoning that a red gate still
blocks *new* violations while the backlog is worked, which review demonstrably
does not. That is a deliberate, loud deviation, not the default, and never a
silent baseline.

**Reported, not prescribed** — the paragraph below is the reference codebase's
current state, included because both halves are instructive. Do not copy its
debt as guidance.

As of 2026-08-05, eight of its ten gates are fully green; the two red ones fail
on the *same* deliberately red rule (the inline path-depth cap, 93 violations in
one crate and 5 in another) whose remediation is a mechanical follow-up sweep.
Its four SRP proxy rules, which the decision record describes as landing red, are
now green — two through pure remediation with ledgers left empty, and two through
remediation plus a small number of individually reasoned grants. Meanwhile one
pre-existing rule in a local gate still sits under
`#[ignore = "advisory/ratchet: …"]`, predating this pattern and never migrated:
a live counterexample to the no-baselines doctrine, sitting in the same
repository that rejects baselines. Ratchets are easy to leave behind. Put a
date or an owner on every one you create.

**Grow the catalog one rule at a time.** The library is not a big-bang
codification of every rule in your style guide. A rule earns mechanization by
being violated in practice and surviving review. Expect them roughly in this
order: layout rules (test purity, `mod.rs` ban, file-name stutter), then shape
rules (traits-only port files, field visibility, constructor signatures), then
vocabulary bans.

**Migrate the mechanics, not just the rules.** When rules move out of a crate's
gate into the library, the walker, violation type, and scanners must move with
them — otherwise the crate keeps a second, structurally identical copy for its
remaining local rules, and the duplication the extraction was meant to end
simply survives at a smaller scale. This is exactly what happened in the
reference codebase: its largest crate still carries its own `Rule`, `Violation`,
and `SourceTree` — 520 lines (349 + 121 + 50) beside the shared crate's — because
*most* of its local policy rules were never rebuilt on the shared mechanics.
Tellingly, one of them was: the dispatch-boundary rule shown above imports
`ironbox_conventions::{Rule, Violation}` and defines its check inline. That single
file is the proof the other 520 lines are avoidable rather than necessary. Finish
the extraction: every local rule uses the library's `Rule::new`.

**What stays out.** Formatting belongs to rustfmt — the library never re-checks
it. Judgment belongs to advisory review agents: SRP's "one reason to change",
cohesion, naming intent, and mixed altitude inside a function.
Type-inference-dependent rules are out of reach on stable; where a use-site rule
is syntactically ambiguous, ban the aliasing and re-export constructs for
guarded names rather than trying to resolve them.

## Reaching Every Gate: CI Must Not Enumerate Crates

Per-crate gates create one new failure mode: a gate that exists but never runs.
When CI lists crates by hand —

```yaml
- run: cargo test -p my-core   --test structure
- run: cargo test -p my-worker --test structure
```

— every workspace member added later is silently unenforced until someone
remembers to extend the list. In the reference codebase this drifted exactly as
predicted: ten members carry gates and CI executes seven of them. The three it
misses include the conventions crate itself — so the fixture tests that prove
every rule fires are the ones never run in CI.

Universality makes one invocation cover every gate, so the list stops needing
maintenance:

```just
structure:
    cargo test --workspace --test structure
```

**But that recipe does not catch a member with no gate at all** — verify this
before relying on it. Cargo treats `--test structure` as a filter over the
selected packages and is satisfied when *any* package matches. In a two-member
workspace where one member has `tests/structure.rs` and the other has none, the
command compiles the first, runs its test, reports `ok`, and **exits 0**. Nothing
fails. So the recipe reads as coverage while providing none for the newest
crate — this document's own most expensive anti-pattern, reached by following its
own advice.

Close the loop with a rule that lives in the **library**, because the property it
asserts is about the workspace rather than any one crate: ask Cargo which
packages are members and assert that every member directory contains
`tests/structure.rs`. This is the one rule that cannot be a per-crate rule.

Ask Cargo — do not parse `[workspace] members`. Cargo treats any in-workspace
path dependency as a member whether or not that list names it, and in this
pattern every member declares the conventions crate by path. A manifest-reading
rule therefore misses the commonest way a member appears without being listed,
which is precisely the case the rule exists to catch. The cheap alternative, if
you would rather not write the rule, is a CI assertion that the number of
executed `structure` test binaries equals the member count.

Wire that recipe into CI and let CI call the task runner, so the local command
and the gating command cannot diverge.

Then audit each gate across all three surfaces — task runner, hook, CI — because
they drift independently. In the reference repository, as measured:

| Gate | Task runner | Hook | CI |
|---|---|---|---|
| `cargo fmt --check` | — | blocking | yes |
| `clippy -D warnings` | yes | — | yes |
| structure gate | all 10, incidentally | — | 7 of 10, hand-enumerated |

Three gates, three different coverage sets, and no single command reproduces what
gates a merge. Two details in that table are easy to get wrong. The structure
gate reaches all ten members from the canonical test recipe only *incidentally*,
because that recipe runs a filter-less `cargo test -p <member>` per crate and a
filter-less run executes every test target — there is no dedicated `structure`
recipe, so the coverage is a side effect nobody chose. And no hook runs the
mechanical gate at all: the commit-blocking hook whose name contains "structure"
dispatches the *advisory review agent*, which is the judgment layer this pattern
deliberately keeps separate. Do not count it as gate coverage.

## Quick Reference — Invariants

- **The rule library owns detection; the gate owns adoption; the ledger owns
  exceptions.** Three responsibilities, three places, no fourth.
- **The library is a workspace member with `publish = false`, consumed only from
  consumers' `[dev-dependencies]`**, and depends on no workspace member.
  Production dependency graphs are unchanged.
- **A universal rule constructor takes no arguments.** The only input is the
  caller's crate root, so a rule always scans the tree that adopted it.
- **The library never resolves its own location** — `env!("CARGO_MANIFEST_DIR")`
  is evaluated in the gate, never in the library.
- **Every crate with a `tests/` tree owns `tests/structure.rs`** — including
  leaf primitives crates and the conventions crate itself.
- **One owner per violation:** the crate it lives in. Retract any central
  workspace-wide scan when the library is extracted.
- **Crate-specific policy stays in that crate's gate**, built on the library's
  `Rule::new`; only genuinely universal rules move into the library.
- **`Rule::new` is for policy no other crate has.** Never re-express a library
  rule locally with a narrower scan — that is a knob wearing a closure, and it
  reads in review as legitimate crate-specific policy.
- **An exception climbs the ladder** — change the code, change the library
  const, add a rule-owned in-source marker, or add a second named constructor.
  Never a knob at the call site.
- **Ledgers start empty, use exact keys, and fail when stale.** The PR that
  edits a ledger is the operator permission request.
- **A judgment rule demands a decision instead of guessing one:** grant with a
  reasoned exact set, remediate, or stay red until understood.
- **The ledger and the decision record stay in sync** — a new grant amends the
  ADR in the same change.
- **Every rule has `should_flag` and `should_pass` fixture tests**, in per-test
  isolated directories, with one `should_pass` per rule-owned exemption.
- **A syntactic gate promises only a syntactic contract.** Write down the shape
  it checks and the residual bypass it accepts.
- **CI invokes the gates workspace-wide through the task runner**, never as a
  hand-maintained crate list.

## Anti-Patterns to Avoid

- **A knob at the call site.** `rule(&["allow/this/path"])` in ten gate files.
  Policy leaves its one home, diverges quietly, and reads as configuration
  rather than as a decision. This is the one form an exception must never take.
- **The central workspace-wide scan.** One crate's gate policing its siblings:
  the violation fails the wrong crate, the per-crate iteration loop stays green,
  and every finding has two owners.
- **Copying the scanner per crate.** Eight copies of a `syn` walker whose
  exemption lists drift apart silently.
- **A half-finished extraction.** Rules move to the library but the mechanics
  stay behind for local rules, so the crate keeps a second copy of the walker
  and violation type — the duplication survives at a smaller scale.
- **A frozen baseline.** Grandfathering the current violation set to adopt a
  rule instantly. Baselines rot and permanently blur "clean". Prefer
  clean-to-zero, or loud red by explicit decision.
- **An immortal ratchet.** `#[ignore = "advisory"]` with no owner and no date.
  It outlives everyone's memory of why it was temporary.
- **Migrating an inherited allowlist unexamined.** Check whether the exempted
  case is even alive first — inherited carve-outs are often grandfathering
  something already dead.
- **Bare-key grants for a judgment call.** "This type is allowed" lets one
  approval silently authorize the next, unrelated violation, and loses the
  reason cohesion was accepted.
- **Auto-classifying an ambiguous case.** A heuristic that silently decides
  "probably cohesive" converts an adjudication trigger into a rubber stamp.
- **Mechanizing judgment.** Size budgets are SRP *symptoms*, not SRP. A
  100-line function of pure named calls can be fine; an 80-line function with
  two inline step implementations is worse. Leave the semantic core to review.
- **A rule library that violates its own rules.** If it has no gate on itself,
  it teaches the opposite of what it enforces.
- **Re-checking what rustfmt owns.** Formatting rules in the library duplicate a
  tool that already never loses.
- **A gate that exists but never runs.** Present in the repo, absent from CI —
  the most expensive kind, because it reads as coverage.

## What Generalizes Beyond Rust

The packaging principle is language-independent; only the scanner changes. The
Python sibling — [`python.md`](python.md) — already applies it on `ast` and uv
workspaces; read that rather than re-deriving it.

If you add a third language, these properties are the pattern and must survive
the port: rules as a library consumed by the standard test runner, one gate per
module executing rules against its own tree, zero-knob universal rules, the
escalation ladder, exact-key ledgers with stale-grant detection, and
`should_flag`/`should_pass` fixture tests per rule. What changes is the parsing
substrate (the TypeScript compiler API, for instance) and the packaging unit — a
dev-only package instead of a dev-only crate.

One judgment carries across every language: where an ecosystem already has a
config-driven architecture gate — Python's import-linter contracts, ESLint's
boundary rules — that tool already owns the layering slice, and a conventions
package there should cover only the rules it cannot express rather than
duplicating it.

## Relationship to Other Patterns and Skills

- **`rust-architecture-test-setup`** — owns *which* invariants a Rust project
  enforces (layering, port purity, file-name stutter, assembly confinement,
  manifest boundaries, generic-module vocabulary) and how to build the
  single-crate in-crate gate. This pattern owns how those rules are *packaged*
  once the project is a workspace. Note the apparent conflict and how it
  resolves: that skill has a "Customization knobs" section configuring rules
  through per-crate constants files, which is **not** a violation of zero-knob —
  a constants file inside a crate's own gate tree is crate-specific policy, and
  the zero-knob rule binds only the constructors the shared library exports.
- **[python convention pattern](python.md)** — the same pattern on `ast` and uv
  workspaces; the sibling to read before porting this to another language.
- **`rust-workspace-setup`** — the conventions crate is a workspace member; the
  workspace is the precondition for this pattern applying at all.
- **`rust-testing`** — the source of the test-tree rules that mechanize first
  (test files contain only tests, no tests in `src/`, support-tree discipline),
  and the standard the conventions crate's own tests follow.
- **`rust-code-style`** — the source of the layout and import rules (modern
  module convention, import organization and the path-depth cap) and of the
  uniform-altitude review lens that stays advisory on purpose.
- **[parallel test isolation](../testing/parallel_test_isolation_pattern.md)** —
  each rule's fixture trees need per-test isolated directories, or the rule
  suite cannot run in parallel with itself.
- **[composition root](../project_structure/composition_pattern.md)** — the
  wiring seam several rules reference: assembly confinement guards it, the
  argument-count rule exempts it (its job is to be wide), the path-depth cap
  exempts it (its long paths are meaningful declarations, not lookup tax), and
  its factory and entry point are the archetypal reasoned long-function grants.
- **`ci-setup` and `agent-hooks-setup`** — what makes the gates blocking rather
  than advisory, and what keeps the task runner, the hook, and CI in agreement.
- **`rust-code-auditor` / `rust-structure-and-style-guard`** — the advisory
  reviewers that own the judgment residue this pattern deliberately leaves
  behind, including adjudicating a multi-port type before a grant is written.
