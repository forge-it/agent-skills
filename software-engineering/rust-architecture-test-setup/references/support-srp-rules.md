# SRP proxy rules (11–14) — constants, ledgers, and constructors

Complete implementations for the four SRP proxy rules. Write these **after** the
other two references, because they extend `constants.rs` and `rules.rs` rather
than replacing them, and they add one new support module.

Three files are involved:

1. `support/constants.rs` — the budgets, the confession lint, the plumbing list.
2. `support/ledgers.rs` — **new**: the `GRANTED_*` permission ledgers, the
   cohesion-grant type, and stale-grant detection.
3. `support/rules.rs` — the four constructors and their helpers.

Mount the new module in `support.rs`:

```rust
pub mod constants;
pub mod ledgers;
pub mod manifest;
pub mod rules;
pub mod source;
pub mod violation;
```

Rules 11, 12, and 14 parse Rust, so add the parser to the **test** dependencies —
this gate is an integration-test target, so `[dev-dependencies]` is correct here.
(The sibling `rust-conventions-crate-setup` puts the same crates in
`[dependencies]`, and that is also correct *there*, because its rules are library
code rather than test code. Do not carry that rule across.)

```toml
# Cargo.toml
[dev-dependencies]
toml = "0.9"
syn = { version = "2", features = ["full", "visit"] }
proc-macro2 = { version = "1", features = ["span-locations"] }
```

`span-locations` is load-bearing: without it, spans carry no real line numbers
outside a proc-macro context and every violation reports line 0.

---

## `support/constants.rs` — additions

```rust
/// Rule 11: a production `fn` spans at most this many lines, counted from the
/// `fn` token through the closing brace (a multiline signature counts).
pub const FUNCTION_LINE_BUDGET: usize = 100;

/// Rule 11's dispatch-table allowance. A body that is only `let` bindings
/// followed by a trailing `match` is a dispatch table, whose length is its arm
/// count rather than mixed responsibility — but it is still bounded, so that
/// wrapping an arbitrary body in a single `match` arm is not a loophole.
pub const DISPATCH_LINE_BUDGET: usize = 300;

/// Rule 14: a production source file spans at most this many lines. The remedy
/// is the sub-concept split — `model.rs` grows `model/<concept>.rs` siblings
/// behind the facade it already has.
pub const FILE_LINE_BUDGET: usize = 1000;

/// Rule 13: the lint whose suppression is a confession of collaborator sprawl.
pub const ARGUMENT_COUNT_LINT: &str = "too_many_arguments";

/// Rule 12: traits that are plumbing rather than ports. Implementing these says
/// nothing about a type's responsibilities, so they never count toward the
/// multi-port threshold. Only the trait's final path segment is matched.
pub const PLUMBING_TRAIT_NAMES: &[&str] = &[
    // std derives and marker traits
    "Clone", "Copy", "Debug", "Default", "Eq", "Hash", "Ord", "PartialEq", "PartialOrd",
    "Send", "Sync", "Sized", "Unpin", "Drop",
    // std conversion, comparison, and operator families
    "AsMut", "AsRef", "Borrow", "BorrowMut", "Deref", "DerefMut", "From", "Into",
    "TryFrom", "TryInto", "FromStr", "ToString", "Display", "Error",
    "Add", "AddAssign", "Sub", "SubAssign", "Mul", "MulAssign", "Div", "DivAssign",
    "Neg", "Not", "Index", "IndexMut",
    // iteration
    "Iterator", "IntoIterator", "Extend", "FromIterator",
    // serialization and async IO
    "Serialize", "Deserialize", "AsyncRead", "AsyncWrite", "AsyncSeek", "Future",
    // HTTP-framework glue
    "FromRequest", "FromRequestParts", "FromRef", "IntoResponse",
];
```

Extend `PLUMBING_TRAIT_NAMES` when the project adopts a framework whose glue
traits show up on domain types. That is a policy change to the whole crate, made
in one reviewed diff — which is the point.

---

## `support/ledgers.rs` — the permission ledgers

Every `GRANTED_*` entry lives here, so an operator edits exactly one file. **They
start empty and stay empty until a case earns an entry.**

Note one deliberate difference from the sibling skill's version: it scopes each
grant to a crate by key prefix, because one shared ledger serves many crates'
gates. In a single-crate gate there is only one crate, so the scoping is dropped
and every grant is in scope. Everything else — exact keys, recording a key only
where a violation is actually suppressed, and failing on a stale grant — is
identical.

```rust
// tests/structure/support/ledgers.rs
//! Operator-permission ledgers for the SRP proxy rules (11–14), and
//! stale-grant bookkeeping. A violation is silenced only by its exact key, and
//! the diff that adds a key IS the operator permission request.

use std::collections::HashSet;

use super::violation::Violation;

/// Operator-granted long functions. Key: `<src path>::<fn name>`, e.g.
/// `src/composition/factory.rs::create_application_services`.
///
/// The archetypal legitimate entry is a wiring factory or a process entrypoint:
/// its single responsibility genuinely is "wire the graph", and decomposing it
/// would be speculative churn. That is the ledger working as designed.
pub(crate) const GRANTED_LONG_FUNCTIONS: &[&str] = &[];

/// Operator-granted argument-count allowances. Key: `<src path>` — a grant
/// covers the whole file.
pub(crate) const GRANTED_ARGUMENT_COUNT_ALLOWANCES: &[&str] = &[];

/// Operator-granted long files. Key: `<src path>`.
pub(crate) const GRANTED_LONG_FILES: &[&str] = &[];

/// Operator-approved multi-port cohesion decisions. `ports` must be sorted so
/// the declaration is canonical and reviewable; any change to the type's actual
/// port set invalidates the grant automatically.
pub(crate) const GRANTED_MULTI_PORT_COHESION: &[MultiPortCohesionGrant] = &[];

/// One approved cohesion decision: which type, which exact ports, and why.
#[derive(Debug)]
pub(crate) struct MultiPortCohesionGrant {
    /// `<src path>::<TypeName>`
    pub(crate) type_key: &'static str,
    /// The exact non-plumbing ports approved together, sorted.
    pub(crate) ports: &'static [&'static str],
    /// Why these ports are one responsibility. Never empty.
    pub(crate) rationale: &'static str,
}

/// Why a multi-port type's cohesion decision is not acceptable.
#[derive(Debug, PartialEq, Eq)]
pub(crate) enum MultiPortDecisionError {
    /// Two or more ports and no grant — nobody has adjudicated this type.
    Unclassified,
    DuplicateGrant,
    UnsortedOrDuplicatePorts,
    EmptyRationale,
    /// The grant names a different port set than the type now implements.
    PortSetMismatch,
    /// A grant survives for a type that no longer has multiple ports.
    StaleGrant,
}

impl MultiPortDecisionError {
    pub(crate) const fn message(&self) -> &'static str {
        match self {
            Self::Unclassified => "implements two or more non-plumbing ports with no cohesion \
                 decision: split the type along its independent reasons to change, or add a \
                 GRANTED_MULTI_PORT_COHESION entry naming the exact sorted port set and why they \
                 are one responsibility",
            Self::DuplicateGrant => "has more than one cohesion grant; keep exactly one",
            Self::UnsortedOrDuplicatePorts => "its grant's `ports` are not sorted and unique",
            Self::EmptyRationale => "its grant has an empty rationale",
            Self::PortSetMismatch => "its grant names a different port set than the type \
                 implements; re-adjudicate rather than editing the set to match",
            Self::StaleGrant => "no longer implements multiple ports — remove its stale grant",
        }
    }
}

/// The exact-set, reasoned-grant decision. Kept a pure function so the
/// rule-logic tests can exercise every branch without a source tree.
///
/// Branch order is load-bearing: duplicates are rejected before arity, a
/// dropped port is stale rather than silently fine, and a malformed grant
/// reports as malformed instead of masquerading as a mismatch.
pub(crate) fn assess_multi_port_cohesion_decision(
    actual_ports: &[&str],
    grants: &[&MultiPortCohesionGrant],
) -> Result<(), MultiPortDecisionError> {
    if grants.len() > 1 {
        return Err(MultiPortDecisionError::DuplicateGrant);
    }
    if actual_ports.len() < 2 {
        return if grants.is_empty() {
            Ok(())
        } else {
            Err(MultiPortDecisionError::StaleGrant)
        };
    }
    let Some(grant) = grants.first() else {
        return Err(MultiPortDecisionError::Unclassified);
    };
    if !grant.ports.windows(2).all(|ports| ports[0] < ports[1]) {
        return Err(MultiPortDecisionError::UnsortedOrDuplicatePorts);
    }
    if grant.rationale.trim().is_empty() {
        return Err(MultiPortDecisionError::EmptyRationale);
    }
    if grant.ports != actual_ports {
        return Err(MultiPortDecisionError::PortSetMismatch);
    }
    Ok(())
}

/// A grant that matched no violation is stale: the code was fixed, so the
/// permission must be handed back. Anything not recorded during the scan is
/// unmatched by construction, so there is no second bookkeeping step to forget.
pub(crate) fn append_stale_grants(
    granted: &[&str],
    matched_grants: &HashSet<String>,
    violations: &mut Vec<Violation>,
) {
    for grant in granted {
        if !matched_grants.contains(*grant) {
            violations.push(Violation::in_file(
                grant,
                "stale ledger grant: no matching violation remains — remove the entry",
            ));
        }
    }
}
```

---

## `support/rules.rs` — the four constructors

Add these imports at the top of the existing file:

```rust
use std::collections::{BTreeMap, BTreeSet, HashSet};

use syn::spanned::Spanned;

use super::constants::{
    ARGUMENT_COUNT_LINT, COMPOSITION_PATHS, DISPATCH_LINE_BUDGET, FILE_LINE_BUDGET,
    FUNCTION_LINE_BUDGET, PLUMBING_TRAIT_NAMES,
};
use super::ledgers::{
    GRANTED_ARGUMENT_COUNT_ALLOWANCES, GRANTED_LONG_FILES, GRANTED_LONG_FUNCTIONS,
    GRANTED_MULTI_PORT_COHESION, MultiPortCohesionGrant, append_stale_grants,
    assess_multi_port_cohesion_decision,
};
```

### Rule 11 — function line budget

```rust
    /// A production `fn` spans at most [`FUNCTION_LINE_BUDGET`] lines. A
    /// dispatch table — a body of only `let` bindings plus a trailing `match` —
    /// gets [`DISPATCH_LINE_BUDGET`] instead, because its length is its arm
    /// count. Scans `src/` only; the test tree is rust-testing's business.
    pub(crate) fn production_functions_stay_within_the_line_budget() -> Self {
        Self {
            description: format!("production functions stay within {FUNCTION_LINE_BUDGET} lines"),
            check: Box::new(|source_tree| {
                let mut violations = Vec::new();
                let mut matched_grants = HashSet::new();
                for file in source_tree.rust_files() {
                    let relative_file = source_tree.relative_unix(&file);
                    let contents = source_tree.read(&file);
                    let Ok(parsed) = syn::parse_file(&contents) else {
                        violations.push(Violation::in_file(&relative_file, "failed to parse"));
                        continue;
                    };
                    let mut functions = Vec::new();
                    collect_functions(&parsed.items, &mut functions);
                    for (name, first_line, last_line, is_dispatch) in functions {
                        let budget = if is_dispatch {
                            DISPATCH_LINE_BUDGET
                        } else {
                            FUNCTION_LINE_BUDGET
                        };
                        let length = last_line.saturating_sub(first_line) + 1;
                        if length <= budget {
                            continue;
                        }
                        let grant_key = format!("{relative_file}::{name}");
                        if GRANTED_LONG_FUNCTIONS.contains(&grant_key.as_str()) {
                            matched_grants.insert(grant_key);
                            continue;
                        }
                        violations.push(Violation::at_line(
                            &relative_file,
                            first_line,
                            &format!("fn {name}"),
                            &format!(
                                "spans {length} lines, over the {budget}-line budget; extract a \
                                 named step (F1), push logic into the type that owns the data \
                                 (F2), or extract a step object (F4)"
                            ),
                        ));
                    }
                }
                append_stale_grants(GRANTED_LONG_FUNCTIONS, &matched_grants, &mut violations);
                violations
            }),
        }
    }
```

Helpers (module-private, beside the other rule helpers):

```rust
/// Every `fn` in an item tree — free functions, inherent and trait-impl
/// methods, and trait default bodies — as
/// `(name, first line, last line, is a dispatch table)`.
///
/// Because this walks the AST rather than lines, blank lines and comments
/// inside a body are invisible to the dispatch-table test by construction.
fn collect_functions(
    items: &[syn::Item],
    functions: &mut Vec<(String, usize, usize, bool)>,
) {
    for item in items {
        match item {
            syn::Item::Fn(function) => {
                functions.push(function_measurement(
                    &function.sig.ident.to_string(),
                    &function.sig,
                    &function.block,
                ));
            }
            syn::Item::Impl(block) => {
                for impl_item in &block.items {
                    if let syn::ImplItem::Fn(method) = impl_item {
                        functions.push(function_measurement(
                            &method.sig.ident.to_string(),
                            &method.sig,
                            &method.block,
                        ));
                    }
                }
            }
            syn::Item::Trait(trait_item) => {
                for member in &trait_item.items {
                    if let syn::TraitItem::Fn(method) = member
                        && let Some(block) = &method.default
                    {
                        functions.push(function_measurement(
                            &method.sig.ident.to_string(),
                            &method.sig,
                            block,
                        ));
                    }
                }
            }
            syn::Item::Mod(module) => {
                if let Some((_, nested)) = &module.content {
                    collect_functions(nested, functions);
                }
            }
            _ => {}
        }
    }
}

/// Measures one `fn` from its `fn` token (so attributes and doc comments do not
/// count) through its closing brace.
fn function_measurement(
    name: &str,
    signature: &syn::Signature,
    block: &syn::Block,
) -> (String, usize, usize, bool) {
    let first_line = signature.fn_token.span().start().line;
    let last_line = block.brace_token.span.close().end().line;
    (
        name.to_string(),
        first_line,
        last_line,
        is_dispatch_table(block),
    )
}

/// A dispatch table: every statement but the last is a `let` with an
/// initializer, and the last is a tail-position `match` with two or more arms.
///
/// `let … else` disqualifies (its diverging block can hold anything), a
/// semicolon-terminated `match` disqualifies (it is a statement, not the
/// function's result), and requiring two arms stops a one-arm `match` from
/// being a wrapper that exempts an arbitrary body.
fn is_dispatch_table(block: &syn::Block) -> bool {
    let Some((last, leading)) = block.stmts.split_last() else {
        return false;
    };
    let all_leading_are_plain_lets = leading.iter().all(|statement| {
        matches!(
            statement,
            syn::Stmt::Local(local)
                if local.init.as_ref().is_some_and(|init| init.diverge.is_none())
        )
    });
    let ends_in_dispatch_match = matches!(
        last,
        syn::Stmt::Expr(syn::Expr::Match(dispatch), None) if dispatch.arms.len() >= 2
    );
    all_leading_are_plain_lets && ends_in_dispatch_match
}
```

### Rule 12 — multi-port cohesion decisions

```rust
    /// A concrete type implementing two or more non-plumbing ports must be
    /// split or carry a reasoned, exact-port cohesion grant. Only explicit
    /// `impl Trait for Type` blocks count — a `#[derive(...)]` list is never a
    /// port.
    pub(crate) fn multi_port_concrete_types_have_explicit_cohesion_decisions() -> Self {
        Self {
            description: "multi-port concrete types have explicit cohesion decisions".to_string(),
            check: Box::new(|source_tree| {
                let mut violations = Vec::new();
                let mut matched_grants = HashSet::new();
                let mut ports_by_type: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();

                for file in source_tree.rust_files() {
                    let relative_file = source_tree.relative_unix(&file);
                    let contents = source_tree.read(&file);
                    let Ok(parsed) = syn::parse_file(&contents) else {
                        violations.push(Violation::in_file(&relative_file, "failed to parse"));
                        continue;
                    };
                    collect_port_implementations(&parsed.items, &relative_file, &mut ports_by_type);
                }

                for (type_key, ports) in &ports_by_type {
                    let ports: Vec<&str> = ports.iter().map(String::as_str).collect();
                    let grants: Vec<&MultiPortCohesionGrant> = GRANTED_MULTI_PORT_COHESION
                        .iter()
                        .filter(|grant| grant.type_key == type_key)
                        .collect();
                    if let Err(error) = assess_multi_port_cohesion_decision(&ports, &grants) {
                        violations.push(Violation::in_file(
                            type_key,
                            &format!("{} (ports: {})", error.message(), ports.join(", ")),
                        ));
                    } else if !grants.is_empty() {
                        matched_grants.insert((*type_key).to_string());
                    }
                }

                for grant in GRANTED_MULTI_PORT_COHESION {
                    if !ports_by_type.contains_key(grant.type_key) {
                        violations.push(Violation::in_file(
                            grant.type_key,
                            "stale cohesion grant: the type implements no ports here — remove it",
                        ));
                    }
                }
                let _ = matched_grants;
                violations
            }),
        }
    }
```

Helper:

```rust
/// Records every non-plumbing trait each concrete type implements, keyed
/// `<src path>::<TypeName>`. Negative impls (`impl !Send for T`) and blanket
/// impls over a generic parameter are skipped.
fn collect_port_implementations(
    items: &[syn::Item],
    relative_file: &str,
    ports_by_type: &mut BTreeMap<String, BTreeSet<String>>,
) {
    for item in items {
        match item {
            syn::Item::Impl(block) => {
                let Some((negation, trait_path, _)) = &block.trait_ else {
                    continue;
                };
                if negation.is_some() {
                    continue;
                }
                let Some(trait_name) = trait_path.segments.last().map(|s| s.ident.to_string())
                else {
                    continue;
                };
                if PLUMBING_TRAIT_NAMES.contains(&trait_name.as_str()) {
                    continue;
                }
                let syn::Type::Path(type_path) = block.self_ty.as_ref() else {
                    continue;
                };
                let Some(type_name) = type_path.path.segments.last().map(|s| s.ident.to_string())
                else {
                    continue;
                };
                ports_by_type
                    .entry(format!("{relative_file}::{type_name}"))
                    .or_default()
                    .insert(trait_name);
            }
            syn::Item::Mod(module) => {
                if let Some((_, nested)) = &module.content {
                    collect_port_implementations(nested, relative_file, ports_by_type);
                }
            }
            _ => {}
        }
    }
}
```

### Rule 13 — argument-count allowances confined to composition

```rust
    /// `#[allow(clippy::too_many_arguments)]` and `#[expect(…)]` are legal only
    /// inside the composition root, whose job is to be wide. Anywhere else the
    /// suppression is a written confession of collaborator sprawl.
    pub(crate) fn argument_count_allowances_are_confined_to_composition() -> Self {
        Self {
            description: "argument-count allowances are confined to composition".to_string(),
            check: Box::new(|source_tree| {
                let mut violations = Vec::new();
                let mut matched_grants = HashSet::new();
                for file in source_tree.rust_files() {
                    let relative_file = source_tree.relative_unix(&file);
                    if SourceTree::matches_any(&relative_file, COMPOSITION_PATHS) {
                        continue;
                    }
                    for (index, line) in source_tree.read(&file).lines().enumerate() {
                        let source_line = SourceLine(line);
                        if source_line.is_comment() || !line.contains(ARGUMENT_COUNT_LINT) {
                            continue;
                        }
                        if GRANTED_ARGUMENT_COUNT_ALLOWANCES.contains(&relative_file.as_str()) {
                            matched_grants.insert(relative_file.clone());
                            continue;
                        }
                        violations.push(Violation::at_line(
                            &relative_file,
                            index + 1,
                            line,
                            "argument-count allowances belong only in the composition root; \
                             extract a step object that owns the collaborators one phase uses (F4)",
                        ));
                    }
                }
                append_stale_grants(
                    GRANTED_ARGUMENT_COUNT_ALLOWANCES,
                    &matched_grants,
                    &mut violations,
                );
                violations
            }),
        }
    }
```

### Rule 14 — file line budget

```rust
    /// A production source file spans at most [`FILE_LINE_BUDGET`] lines. The
    /// remedy is the sub-concept split behind the facade the concept already
    /// has (rule 6).
    pub(crate) fn production_files_stay_within_the_line_budget() -> Self {
        Self {
            description: format!("production files stay within {FILE_LINE_BUDGET} lines"),
            check: Box::new(|source_tree| {
                let mut violations = Vec::new();
                let mut matched_grants = HashSet::new();
                for file in source_tree.rust_files() {
                    let relative_file = source_tree.relative_unix(&file);
                    let length = source_tree.read(&file).lines().count();
                    if length <= FILE_LINE_BUDGET {
                        continue;
                    }
                    if GRANTED_LONG_FILES.contains(&relative_file.as_str()) {
                        matched_grants.insert(relative_file.clone());
                        continue;
                    }
                    violations.push(Violation::in_file(
                        &relative_file,
                        &format!(
                            "spans {length} lines, over the {FILE_LINE_BUDGET}-line budget; grow \
                             sub-concept siblings behind this concept's facade"
                        ),
                    ));
                }
                append_stale_grants(GRANTED_LONG_FILES, &matched_grants, &mut violations);
                violations
            }),
        }
    }
```

---

## Rule-logic tests

Rules 1–10 pair enforcement tests with rule-logic tests so a regression in a
scanner is caught while the codebase is clean. Rule 12's decision function needs
that most, because it is the one rule whose job is to *demand a decision*. Put
these in `tests/structure/srp_discipline.rs` beside the enforcement tests:

```rust
mod srp_rule_logic {
    use super::super::support::ledgers::{
        MultiPortCohesionGrant, MultiPortDecisionError, assess_multi_port_cohesion_decision,
    };

    const EXACT_GRANT: MultiPortCohesionGrant = MultiPortCohesionGrant {
        type_key: "src/infrastructure/order/repository.rs::PostgresOrderRepository",
        ports: &["NotificationLedger", "OrderRepository"],
        rationale: "Both ports are facets of one transactional order aggregate.",
    };

    #[test]
    fn should_accept_a_grant_whose_port_set_matches_exactly() {
        let ports = ["NotificationLedger", "OrderRepository"];

        let decision = assess_multi_port_cohesion_decision(&ports, &[&EXACT_GRANT]);

        assert_eq!(decision, Ok(()));
    }

    #[test]
    fn should_report_an_unclassified_type_with_two_ports_and_no_grant() {
        let ports = ["NotificationLedger", "OrderRepository"];

        let decision = assess_multi_port_cohesion_decision(&ports, &[]);

        assert_eq!(decision, Err(MultiPortDecisionError::Unclassified));
    }

    #[test]
    fn should_report_a_mismatch_when_a_third_port_appears() {
        let ports = ["AuditTrail", "NotificationLedger", "OrderRepository"];

        let decision = assess_multi_port_cohesion_decision(&ports, &[&EXACT_GRANT]);

        assert_eq!(decision, Err(MultiPortDecisionError::PortSetMismatch));
    }

    #[test]
    fn should_report_a_stale_grant_when_the_type_drops_to_one_port() {
        let ports = ["OrderRepository"];

        let decision = assess_multi_port_cohesion_decision(&ports, &[&EXACT_GRANT]);

        assert_eq!(decision, Err(MultiPortDecisionError::StaleGrant));
    }

    #[test]
    fn should_reject_an_unsorted_port_set() {
        const UNSORTED: MultiPortCohesionGrant = MultiPortCohesionGrant {
            type_key: "src/probe.rs::Probe",
            ports: &["OrderRepository", "NotificationLedger"],
            rationale: "…",
        };
        let ports = ["NotificationLedger", "OrderRepository"];

        let decision = assess_multi_port_cohesion_decision(&ports, &[&UNSORTED]);

        assert_eq!(
            decision,
            Err(MultiPortDecisionError::UnsortedOrDuplicatePorts)
        );
    }

    #[test]
    fn should_reject_an_empty_rationale() {
        const NO_REASON: MultiPortCohesionGrant = MultiPortCohesionGrant {
            type_key: "src/probe.rs::Probe",
            ports: &["NotificationLedger", "OrderRepository"],
            rationale: "   ",
        };
        let ports = ["NotificationLedger", "OrderRepository"];

        let decision = assess_multi_port_cohesion_decision(&ports, &[&NO_REASON]);

        assert_eq!(decision, Err(MultiPortDecisionError::EmptyRationale));
    }

    #[test]
    fn should_reject_two_grants_for_one_type() {
        let ports = ["NotificationLedger", "OrderRepository"];

        let decision =
            assess_multi_port_cohesion_decision(&ports, &[&EXACT_GRANT, &EXACT_GRANT]);

        assert_eq!(decision, Err(MultiPortDecisionError::DuplicateGrant));
    }
}
```
