# Permission ledgers and reasoned grants

Read this when you add your **first rule that needs a recorded exception** —
typically the SRP proxy rules (function and file line budgets, argument-count
confinement, multi-port cohesion). Do not build a ledger before a rule needs
one: an empty mechanism invites entries.

A ledger is what gives "ask the operator for permission before breaking this" a
mechanical meaning. Without it, nothing distinguishes a granted violation from an
unnoticed one.

## The four semantics

- **Exact keys.** A violation is silenced only by its exact key —
  `<crate-dir>/<src path>::<fn name>` for a function, `<crate-dir>/<src path>`
  for a whole file. No globs, no prefixes, no wildcards.
- **The diff is the request.** Ledgers live *inside* the library, private to
  their module. A PR that edits one is the permission request, reviewed as such.
- **A stale grant fails the gate.** When the underlying violation disappears,
  the grant must be handed back.
- **Ledgers start empty.** They accumulate only individually understood
  decisions — never a bulk snapshot of what the tree happened to contain. That
  is the deliberate rejection of a frozen baseline: a red gate is loud debt, a
  baseline is silent debt.

## The ledger module

Every `GRANTED_*` constant lives in one file, so an operator edits exactly one
place. All are `pub(super)` — invisible outside the rule family, unreachable from
any gate.

```rust
//! The operator-grant permission registry: every `GRANTED_*` entry lives here,
//! and stale-grant bookkeeping too. An operator adding or removing a grant
//! edits exactly this file.

use std::collections::HashSet;

use crate::violation::Violation;

/// Operator-granted long functions. Key: `<crate-dir>/<src path>::<fn name>`.
pub(super) const GRANTED_LONG_FUNCTIONS: &[&str] = &[];

/// Operator-granted argument-count allowances. Key: `<crate-dir>/<src path>`
/// (a grant covers the whole file).
pub(super) const GRANTED_ARGUMENT_COUNT_ALLOWANCES: &[&str] = &[];

/// Operator-granted long files. Key: `<crate-dir>/<src path>`.
pub(super) const GRANTED_LONG_FILES: &[&str] = &[];

/// A grant scoped to this crate that matched no violation is stale — the
/// underlying code was fixed, so the permission must be handed back.
pub(super) fn append_stale_grants(
    granted: &[&str],
    crate_dir: &str,
    matched_grants: &HashSet<String>,
    violations: &mut Vec<Violation>,
) {
    let path_prefix = format!("{crate_dir}/");
    let type_prefix = format!("{crate_dir}::");
    for grant in granted {
        let scoped_to_this_crate =
            grant.starts_with(&path_prefix) || grant.starts_with(&type_prefix);
        if scoped_to_this_crate && !matched_grants.contains(*grant) {
            violations.push(Violation::in_file(
                grant,
                "stale ledger grant: no matching violation remains — remove the entry",
            ));
        }
    }
}
```

Two details make it work. **Scoping is by key prefix** — `<crate>/` for path
keys, `<crate>::` for type keys — so each crate's gate run audits only its own
entries out of one shared array. And **a key enters `matched_grants` only where a
rule suppresses a real violation**, which is what makes "unmatched ⇒ stale" true
by construction, with no second bookkeeping step anyone can forget.

## The consult-and-record protocol

Every ledger-backed rule follows the same three-step shape. Record the key at the
moment of suppression — not when reading the ledger, and not in a separate pass:

```rust
// The protocol, in the shape every ledger-backed rule repeats.
let mut matched_grants = HashSet::new();
let mut violations = Vec::new();

for finding in scan(source_tree) {
    let grant_key = format!("{}/{}::{}", crate_dir, file, name);
    if GRANTED_LONG_FUNCTIONS.contains(&grant_key.as_str()) {
        matched_grants.insert(grant_key);   // suppressed — and recorded as used
        continue;
    }
    violations.push(Violation::at_line(&file, line, source, MESSAGE));
}

append_stale_grants(
    GRANTED_LONG_FUNCTIONS,
    &crate_dir,
    &matched_grants,
    &mut violations,
);
violations
```

The `append_stale_grants` call is not optional. A ledger without it is a
write-only list that silently outlives the code it was granted for.

## When a decision needs a reason, not just a key

Some rules detect something that is *legitimate about half the time*. The
canonical case: a concrete type implementing two or more non-plumbing ports. One
cohesive adapter may correctly serve several consumer-specific ports (Interface
Segregation); another accumulates unrelated ones (an SRP violation). Syntax
cannot tell those apart.

For such a rule, a bare "this type is allowed" entry is not enough — it would let
one approval silently authorize an unrelated third port later, and it loses why
cohesion was accepted. Give the grant structure:

```rust
#[derive(Debug)]
pub struct MultiPortCohesionGrant {
    pub type_key: &'static str,            // "<crate-dir>/<decl file>::<TypeName>"
    pub ports: &'static [&'static str],    // sorted, exact
    pub rationale: &'static str,           // nonempty, durable
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
) -> Result<(), MultiPortDecisionError> {
    if grants.len() > 1 {
        return Err(MultiPortDecisionError::DuplicateGrant);
    }
    if actual_ports.len() < 2 {
        return if grants.is_empty() { Ok(()) } else { Err(MultiPortDecisionError::StaleGrant) };
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
```

Keep this a **pure function**, in its own module, separate from the scanner that
finds the ports. That is what lets fixture tests exercise every branch without a
source tree — and without exposing a configurable public rule.

The branch **order** is load-bearing. Duplicate grants are rejected before arity
is considered. A subject that has dropped below two ports while its grant
survives is `StaleGrant`, not silently acceptable. Only then does an absent grant
become `Unclassified`. The sorted and nonempty-rationale checks run *before* the
set comparison, so a malformed grant reports as malformed instead of
masquerading as a mismatch.

Requiring the port set sorted and exact is the point: adding a port invalidates
the grant automatically and the type returns to adjudication.

### Testing a private decision function

Isolate it in its own module and pull that module into the test tree directly, so
the tests reach production logic without the library exposing it:

```rust
// tests/unit/support/grant.rs
mod production {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/src/srp_discipline/grant.rs"));
}
```

Then one test per branch: exact match → `Ok`; two ports and no grant →
`Unclassified`; an added third port → `PortSetMismatch`; down to one port with a
grant still present → `StaleGrant`; blank rationale → `EmptyRationale`; two
grants for one type → `DuplicateGrant`; an unsorted pair →
`UnsortedOrDuplicatePorts`.

## Adjudicating before you grant

When a detection needs a human decision, it has exactly three outcomes. Never let
a heuristic pick one silently — automatic analysis is evidence for the reviewer,
not a verdict.

**Grant** when the ports are different views or directional capabilities of *one*
mechanism or one jointly-owned invariant, and splitting would add wrappers or
spread shared state without creating an independent change boundary. Evidence
(suggestive, not conclusive): a secondary implementation is pure delegation to
the primary; every port operates on the same synchronized state and jointly
preserves one stated invariant; the ports are directional capabilities of one
named mechanism sharing its lifecycle and helpers.

**Split** when the ports represent independent reasons to change: materially
disjoint collaborator subsets; different transaction, lifecycle, failure, or
ownership boundaries; distinct policies sharing only a generic dependency such as
a pool. Sharing a cheap handle — an `Arc`, a pool, a clock, an event bus — is not
a cohesion argument. Do not replace the original with behavior-free wrappers
around the same object; each resulting type must own its behavior and only its
relevant collaborators.

**Stay red** when the evidence establishes neither. Read the ports, the impl
bodies, the collaborators, the call sites, the transaction boundaries, and the
wiring first. Neither an automatic grant nor a blind split is allowed.

## Keep the ledger and the decision record in sync

The ledger is the mechanism; the ADR is the reasoning. They drift, and the
mechanism is the half that keeps working — so the record is the half you lose.
Amend the decision record in the same change that edits a ledger, naming the
subject, the approved set, and why. A reader who trusts a stale ADR will believe
cases are open that were settled months ago.
