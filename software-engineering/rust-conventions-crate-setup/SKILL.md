---
name: rust-conventions-crate-setup
description: One-time setup of a dev-only conventions crate (the ArchUnit pattern) for a NEW Rust workspace, so convention rules live in one shared library and every workspace member's `tests/structure.rs` gate enforces them against its own tree — with zero-knob rule constructors, operator-permission ledgers, and a workspace-coverage rule that fails when a member has no gate. Use when bootstrapping architecture enforcement in a Rust workspace with two or more members, or when a single crate's structure gate has started scanning its siblings. Not for single-crate projects — those keep the in-crate gate from rust-architecture-test-setup.
vibe: Turns house conventions into a library the build runs, one gate per crate.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.1"
---

# Rust Conventions Crate Setup

This is a **one-time setup skill**. It produces a dev-only
`crates/<project>-conventions/` library holding the scanning machinery and one
constructor per convention rule, plus a `tests/structure.rs` gate in *every*
workspace member that instantiates the rules it adopts and scans only its own
tree.

It owns **how rules are packaged**. It does not decide *which* invariants a
project enforces — that is `rust-architecture-test-setup`, whose fourteen-rule
catalogue you take as given. Its "Multi-crate workspaces" section hands off to
this skill: take the rule catalogue from there and the packaging from here.

**Read `patterns/conventions/rust.md` first.** It explains why the packaging is
this shape: why a central scan and a
copied scanner both fail, why a universal rule takes no arguments, the
escalation ladder for exceptions, and what a permission ledger must do to be a
decision record rather than a debt baseline. This skill assumes that reasoning
and does not repeat it.

## When to use

- Bootstrapping a **new** Rust workspace with two or more members → every rule
  lands green at commit 1 and every ledger starts empty. There is nothing to
  ratchet.
- An **existing** workspace where one crate's structure gate scans its siblings,
  or where a second crate is about to copy the scanner → extract, then retract
  the central scan in the same change.

**Do not use** for a single-crate project. Locality is the entire reason this
crate exists; with one crate there is nowhere for a violation to be reported in
the wrong place. Use `rust-architecture-test-setup`'s in-crate
`tests/structure/` tree instead, and come back if the project grows a second
member.

Run this once. After the crate and the gates exist, you add rules — you do not
re-run the skill.

## What it produces

```
Cargo.toml                          # [workspace] members gains the new crate
crates/<project>-conventions/
├── Cargo.toml                      # publish = false; syn + proc-macro2 + serde_json
├── src/
│   ├── lib.rs                      # mod declarations + the public surface
│   ├── rule.rs                     # the Rule type: description + check + enforce
│   ├── violation.rs                # the Violation finding type + Display
│   ├── source.rs                   # SourceTree + SourceLine scanning primitives
│   ├── layout.rs                   # the starter rules (one constructor each)
│   └── coverage.rs                 # the workspace-coverage rule
└── tests/
    ├── structure.rs                # this crate obeys its own rules + coverage
    ├── unit.rs                     # entry: without it, tests/unit/ is never compiled
    └── unit/
        ├── support.rs
        ├── support/fixtures.rs     # temp_crate_dir() + write_source_file/write_test_file
        ├── layout.rs               # should_flag / should_pass per layout rule
        └── coverage.rs             # fixture workspaces for the coverage rule

<every other member>/tests/structure.rs   # the per-crate gate
```

## Step 1 — Confirm the workspace and name the crate

The project must already be a Cargo workspace (see `rust-workspace-setup`). Open
the root `Cargo.toml` and confirm the `[workspace] members` list.

Name the crate `<project>-conventions` and place it under `crates/` with the
other library members. If the workspace prefixes its crate names, match that
prefix; if it does not, the bare form is fine. Fix the pair now, because Step 5
depends on both spellings:

| | Example A | Example B |
|---|---|---|
| package name (`Cargo.toml`, directory) | `ironbox-conventions` | `conventions` |
| import identifier (in gate files) | `ironbox_conventions` | `conventions` |

The identifier is the package name with hyphens replaced by underscores. Every
gate file's `use` line depends on getting that right.

## Step 2 — Create the crate and register the member

Register it explicitly, and do not rely on Cargo to complain if you forget:
because every consumer will depend on this crate **by path**, Cargo would quietly
auto-include it as a workspace member with no error and no warning. Listing it is
what makes it a first-class member — and what makes it visible to the Step 6
coverage rule as a crate that owes a gate of its own.

```toml
# Cargo.toml (workspace root)
[workspace]
members = [
    # …existing members…
    "crates/<project>-conventions",
]
```

```toml
# crates/<project>-conventions/Cargo.toml
[package]
name = "<project>-conventions"
version = "0.1.0"
edition = "2024"
description = "Dev-only convention rules library (ArchUnit pattern): the source-tree scanning machinery and zero-knob rule constructors consumed by every workspace member's tests/structure gate, exclusively from [dev-dependencies]. Depends on nothing in the workspace."
publish = false

[dependencies]
# The rule constructors are ordinary lib code, so their parsers are ordinary
# dependencies — NOT dev-dependencies, which Cargo does not expose to the lib
# target's normal build. `span-locations` makes syn spans carry real line
# numbers outside a proc-macro context; without it a violation cannot cite a
# line. The reference implementations target syn 2's API — check what the
# current major is before pinning, and adapt the visitors if you take a newer
# one.
syn = { version = "2", features = ["full", "visit"] }
proc-macro2 = { version = "1", features = ["span-locations"] }
serde_json = "1"                    # reads `cargo metadata` for the coverage rule

[dev-dependencies]
uuid = { version = "1", features = ["v7"] }   # per-test fixture directories

[lints]
workspace = true
```

`publish = false` and the `[dev-dependencies]`-only consumption are what keep
this crate out of every production dependency graph.

## Step 3 — Write the machinery

**Before writing `src/source.rs`, `src/rule.rs`, and `src/violation.rs`, read
`references/machinery.md`** — it contains the
complete implementations of all three. Write them in one pass from that single
reference.

The one invariant to preserve if you adapt them: **the library never resolves
its own location.** `Rule::enforce` takes the crate root as an argument and the
gate passes `env!("CARGO_MANIFEST_DIR")`, which is why a rule scans the tree
that adopted it instead of this crate's.

## Step 4 — Write the starter rules

**Before writing `src/layout.rs`, read
`references/starter-rules.md`** — it contains the
three layout rules complete, with their private policy constants and shared
helpers.

Start with layout rules and nothing else. They are the family that pays first:
each is decidable from a path or a parsed item list, each maps to an existing
rule in `rust-code-style` or `rust-testing`, and on a green-field tree all three
land green immediately.

| Constructor | Enforces | Scans |
|---|---|---|
| `mod_files_are_forbidden()` | `rust-code-style` Rule 6 — no legacy `mod.rs`, no allowlist | `src/`, `tests/` |
| `tests_do_not_live_in_src()` | `rust-testing` §8 — no `#[cfg(test)]` item, no test-attributed `fn` | `src/` |
| `test_files_contain_only_tests()` | `rust-testing` §16 — test files hold only imports, `mod`s, and tests | `tests/` |

Every constructor is `pub fn …() -> Rule` — **no parameters**. Policy lives in
private module constants. This is not a stylistic preference: it is what makes
every crate's gate line identical, so a future divergence has to appear in a
diff instead of hiding in an argument.

Then write `src/lib.rs`. Declare the modules **privately** and re-export the
surface — `pub mod` would make each module's docs public API and pull its
internals into the crate's public surface:

```rust
//! Dev-only convention rules library (the ArchUnit pattern): the source-tree
//! scanning machinery and zero-knob rule constructors consumed by each
//! workspace member's `tests/structure` gate. A rule scans the crate rooted at
//! the manifest directory the gate passes to [`Rule::enforce`] — this crate
//! never resolves `env!("CARGO_MANIFEST_DIR")` itself.

mod layout;
mod rule;
mod source;
mod violation;

pub use layout::{
    mod_files_are_forbidden, test_files_contain_only_tests, tests_do_not_live_in_src,
};
pub use rule::Rule;
pub use source::{SourceLine, SourceTree};
pub use violation::Violation;
```

Export nothing else. The policy constants stay private, and that is precisely
what makes them unreachable from a call site. Step 6 adds two lines here for the
coverage rule.

## Step 5 — Give every member a gate

Every workspace member with a `tests/` tree gets `tests/structure.rs`. Declare
the dependency in each consumer:

```toml
# a member at the repository root, e.g. core/Cargo.toml or worker/Cargo.toml
[dev-dependencies]
# Structure gate (tests/structure): the universal rules + scanning machinery.
<project>-conventions = { path = "../crates/<project>-conventions" }
```

```toml
# a member already under crates/, e.g. crates/task-contracts/Cargo.toml
[dev-dependencies]
<project>-conventions = { path = "../<project>-conventions" }
```

The relative path differs by where the member sits — a sibling under `crates/`
reaches it with one `../`, not two.

For a member with **no policy of its own**, the whole gate is one module per
adopted rule. This file contains no crate-specific text —
`env!("CARGO_MANIFEST_DIR")` is the same token everywhere and merely *expands*
to the crate compiling it, so these files come out byte-identical across
members. Never substitute a literal crate name for it:

```rust
// <member>/tests/structure.rs
use <project>_conventions::{
    mod_files_are_forbidden, test_files_contain_only_tests, tests_do_not_live_in_src,
};

mod mod_files {
    use super::*;

    #[test]
    fn should_not_use_the_legacy_mod_file_layout() {
        mod_files_are_forbidden().enforce(env!("CARGO_MANIFEST_DIR"));
    }
}

mod src_tests {
    use super::*;

    #[test]
    fn should_not_live_in_src() {
        tests_do_not_live_in_src().enforce(env!("CARGO_MANIFEST_DIR"));
    }
}

mod test_files {
    use super::*;

    #[test]
    fn should_contain_only_tests_at_module_scope() {
        test_files_contain_only_tests().enforce(env!("CARGO_MANIFEST_DIR"));
    }
}
```

Keep the import list to exactly the rules the file uses — an unused import fails
`clippy --all-targets -D warnings`, which `ci-setup` wires as a blocking gate.

For a member that **also owns crate-specific policy** (layering, assembly
confinement, vocabulary bans), the entry file declares a module tree instead, so
adopted universal rules and local policy sit side by side:

```rust
// <member>/tests/structure.rs
mod structure {
    pub mod support;        // this crate's own rule helpers ONLY — never a second
                            // copy of the library's Rule/Violation/SourceTree

    mod layout;             // adopted universal rules
    mod layering;           // crate-specific policy
    mod ports;              // crate-specific policy
}
```

Crate-specific rules are built with the library's `Rule::new`, not with a
second copy of the machinery:

```rust
// <member>/tests/structure/layering.rs
use <project>_conventions::{Rule, Violation};
```

`Rule::new` is for policy no other crate has. Never re-express a library rule
locally with a narrower scan — that is a knob wearing a closure, and it reads in
review as legitimate crate-specific policy.

## Step 6 — Add the workspace-coverage rule

Per-crate gates create one failure mode the gates themselves cannot catch: a
member with no gate at all. `cargo test --workspace --test structure` does
**not** catch it — Cargo treats `--test` as a filter satisfied when any package
matches, so a workspace where one member has no `tests/structure.rs` still
reports `ok` and exits 0.

**Before writing `src/coverage.rs`, read the coverage-rule section of
`references/starter-rules.md`.** The rule asks Cargo which packages are members
(`cargo metadata`) and reports every member directory with no
`tests/structure.rs`. It deliberately does **not** parse `[workspace] members`:
Cargo makes any in-workspace path dependency a member whether or not that list
names it, and every consumer here declares this crate by path — so a
manifest-reading rule would miss the commonest way a member appears, which is the
one thing this rule exists to catch.

Add `mod coverage;` and its `pub use` to `src/lib.rs` alongside the rules from
Step 4.

Host it in **this crate's own gate**, because it is the one rule that is a
property of the workspace rather than of any single crate, and this crate exists
exactly once:

This crate's gate also adopts every universal rule against itself — a rule
library that violates its own rules teaches the opposite of what it enforces — so
the whole file is:

```rust
// crates/<project>-conventions/tests/structure.rs
use <project>_conventions::{
    every_workspace_member_has_a_structure_gate, mod_files_are_forbidden,
    test_files_contain_only_tests, tests_do_not_live_in_src,
};

mod workspace_coverage {
    use super::*;

    #[test]
    fn every_member_should_own_a_structure_gate() {
        every_workspace_member_has_a_structure_gate().enforce(env!("CARGO_MANIFEST_DIR"));
    }
}

mod mod_files {
    use super::*;

    #[test]
    fn should_not_use_the_legacy_mod_file_layout() {
        mod_files_are_forbidden().enforce(env!("CARGO_MANIFEST_DIR"));
    }
}

mod src_tests {
    use super::*;

    #[test]
    fn should_not_live_in_src() {
        tests_do_not_live_in_src().enforce(env!("CARGO_MANIFEST_DIR"));
    }
}

mod test_files {
    use super::*;

    #[test]
    fn should_contain_only_tests_at_module_scope() {
        test_files_contain_only_tests().enforce(env!("CARGO_MANIFEST_DIR"));
    }
}
```

## Step 7 — Add fixture tests for every rule

A rule living in one crate's gate is usually untested — nothing proves the
scanner still catches what it claims. As a library, each rule gets two sibling
modules, and that pairing *is* the discipline:

- `should_flag` — a fixture tree containing the violation; assert non-empty.
- `should_pass` — the legitimate near-miss, plus one test per rule-owned
  exemption; assert empty.

Call `violations()` rather than `enforce()` so a test asserts instead of
panicking. Give every fixture its own uniquely-suffixed directory (UUIDv7) so the
suite is parallel-safe — see
`patterns/testing/parallel_test_isolation_pattern.md`.

**Before writing the test tree, read `references/fixture-tests.md`.** It contains
all four required files complete — `tests/unit.rs`, `tests/unit/support.rs`,
`tests/unit/support/fixtures.rs`, and a worked `tests/unit/layout.rs` — plus the
workspace fixtures for the coverage rule. Write them in one pass from that
reference; the entry file is not optional, because without `tests/unit.rs` Cargo
never compiles the `tests/unit/` directory at all and the tests silently do not
exist.

Add the `should_pass` test *in the same change* as the exemption it covers.
Without it an exemption can widen later and no test notices.

## Step 8 — Wire the gates

Give the task runner one recipe (see `justfile-setup`) and have **CI call the
recipe** rather than re-listing crates, so the local command and the gating
command cannot diverge.

If `rust-architecture-test-setup` already installed a single-crate `structure`
recipe, **replace** it — `just` hard-errors on a redefined recipe name:

```just
# justfile
structure:
    cargo test --workspace --test structure
```

`ci-setup`'s Rust job runs `cargo test --test structure` for one crate; change
that step to invoke the recipe, or the gate covers only the crate it names.

Never hand-enumerate crates in CI (`cargo test -p a --test structure`,
`cargo test -p b --test structure`, …). Every member added later is then
silently unenforced until someone remembers the list — which is exactly what
the Step 6 coverage rule exists to catch, and it can only catch it if it runs.

Audit each gate across all three surfaces — task runner, hook, CI — because they
drift independently. See `ci-setup` for the blocking CI job and
`agent-hooks-setup` for the local hooks.

One trap when counting coverage: `agent-hooks-setup`'s structure-related hook
dispatches the **advisory review agent**, which is the judgment layer, not this
mechanical gate. It is valuable and it is not gate coverage. As things stand no
hook runs `cargo test --test structure` — decide deliberately whether you want
one.

## Step 9 — Verify enforcement actually works

Do not trust a green result you have not seen fail. Plant a violation per rule,
confirm the *owning crate's* gate fails, then remove it.

```bash
# the mod.rs ban — a filesystem scan, so the file needs no mod declaration
mkdir -p <member>/src/__probe && : > <member>/src/__probe/mod.rs
cargo test -p <member> --test structure   # expect: mod_files … fails
rm -r <member>/src/__probe

# tests in src
printf '#[cfg(test)]\nmod probe {}\n' > <member>/src/__probe.rs
cargo test -p <member> --test structure   # expect: src_tests … fails
rm <member>/src/__probe.rs

# test-file purity
printf 'struct Probe;\n' > <member>/tests/__probe.rs
cargo test -p <member> --test structure   # expect: test_files … fails
rm <member>/tests/__probe.rs
```

Then verify the two properties that are easy to get wrong:

**Locality.** Plant a violation in member A and run member B's gate. B must
pass. If B fails, a rule is scanning beyond its crate root — the central-scan
failure this crate exists to prevent.

**Coverage.** Create a throwaway member with no `tests/structure.rs` and run the
conventions crate's gate. It must fail with that member named. The member needs a
real manifest and a source file, or Cargo fails to load the workspace *before*
any test runs — and that error is easy to misread as the rule firing:

```bash
mkdir -p __probe/src && printf '' > __probe/src/lib.rs
printf '[package]\nname = "probe"\nversion = "0.1.0"\nedition = "2024"\n' > __probe/Cargo.toml
# no [workspace] members edit needed if a member depends on it by path;
# otherwise add "__probe" to the members list.
cargo test -p <project>-conventions --test structure   # expect: workspace_coverage fails
rm -r __probe

```bash
cargo test --workspace --test structure   # all gates, green on a new project
```

## Severity: new project vs. existing codebase

- **New project:** every rule lands as a hard `enforce()` and every ledger stays
  empty. There are no violations to clean up, so there is no reason to soften
  anything.
- **Existing codebase:** clean the violations to zero, then land the rule. Where
  remediation is mechanical, sweep it first. Where remediation is genuine design
  work, a rule may land **red by explicit operator decision** — a real,
  un-`#[ignore]`d failing test — because a red gate still blocks *new*
  violations while the backlog is worked. That is a deliberate, loud deviation,
  never a silent baseline.

Do not grandfather the existing violation set to adopt a rule instantly.
Baselines rot and permanently blur what "clean" means. If you do create a
ratchet, put an owner and a date on it — an `#[ignore = "advisory"]` with
neither outlives everyone's memory of why it was temporary.

**Growing the catalog.** The crate is not a big-bang codification of every rule
in the style guide. A rule earns mechanization by being violated in practice and
surviving review. After layout rules, expect shape rules (traits-only port
files, field visibility, constructor signatures), then vocabulary bans, then the
SRP proxy rules and their permission ledgers — for which read
`references/ledger-and-grants.md`.

## Customization knobs

Deliberately almost none — that is the design, not an omission.

- **Crate name and location** — `<project>-conventions` under `crates/`.
- **Which rules a member adopts** — the list of `#[test]` functions in its gate.
  This is the *only* per-crate variation, and it is a list, not a configuration.
- **A rule's policy values** — the private constants in the rule's own module.
  Editing one is a policy change to the whole workspace, reviewed as such in one
  diff.
- **Crate-specific policy** — a locally-defined rule via `Rule::new` in that
  crate's gate tree. A constants file inside a crate's own gate is crate-local
  policy and is fine; the zero-knob rule binds the constructors this library
  *exports*.

What is **not** a knob, ever: a parameter on an exported rule constructor. When a
universal rule fires on something that looks legitimate, work down the
escalation ladder in the pattern — change the code, change the library constant,
add an in-source marker the rule itself defines, or add a second
deliberately-named constructor.

## Compliance with the other skills

- **`rust-testing`** — the gate files contain only tests; helpers and fixtures
  live under `support/` (§15, §16). The fixture tests are ordinary tests *of*
  the rules, fed throwaway trees, so they comply.
- **`rust-code-style`** — descriptive names throughout, magic values extracted to
  named constants, `///` on the public surface.
- **`rust-design-idioms`** — `Violation` is a structured type with a `Display`
  impl rather than a pre-formatted `String`; a rule panics through `assert!`,
  which is the correct failure mode for a test.
- **`rust-architecture-test-setup`** — owns which invariants to enforce
  (fourteen rules, including the four SRP proxies whose ledgers this skill's
  `references/ledger-and-grants.md` specifies) and the single-crate gate; its
  multi-crate section delegates the packaging here.
- **`ci-setup` / `agent-hooks-setup`** — make the gates blocking instead of
  advisory.
