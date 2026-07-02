---
name: rust-code-style
description: Coding conventions and style rules for Rust. Apply when writing or reviewing any Rust code.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.9"
---

# Rust Code Style Skill

Conventions for writing clean, maintainable, readable Rust. This skill covers code style only — for choosing an architecture (hexagonal ports/adapters vs. systems layouts) see the rust-hexagonal-architecture and rust-design-principles skills; for module and folder layout see rust-project-structure.

## Core Principles

### 1. Descriptive Naming (CRITICAL)

Use descriptive, intent-revealing, searchable names. Never use single-letter or abbreviated names — for variables, constants, or closure and iterator parameters. This applies to every closure, including `.map()`, `.filter()`, `.find()`, `.fold()`, and any other combinator. *Exception:* generic type parameters (`T`, `E`, `K`, `V`, `S`) and lifetimes (`'a`, `'b`) follow established Rust convention and are exempt.

```rust
// Bad
let t = 30;
let d = Duration::from_secs(60);

// Good
let elapsed_time_in_days = 30;
let request_timeout = Duration::from_secs(60);
```

```rust
// Bad
products.iter().filter(|p| p.price > 100)
items.iter().find(|i| i.name == target_name)
paths.iter().filter_map(|p| p.parent())

// Good
products.iter().filter(|product| product.price > 100)
items.iter().find(|item| item.name == target_name)
paths.iter().filter_map(|path| path.parent())
```

**Rationale:** Single-letter names force the reader to mentally track what each variable represents and defeat search.

### 2. Type Inference (HIGH)

Let Rust infer types when obvious. Add explicit annotations for clarity in complex or ambiguous situations.

```rust
// Bad - unnecessary type annotation
let count: i32 = 0;
let name: String = String::from("hello");

// Good - let Rust infer obvious types
let count = 0;
let name = String::from("hello");

// Good - explicit annotation for clarity in complex situations
let users: HashMap<UserId, Vec<Order>> = HashMap::new();
```

### 3. Error Handling (CRITICAL)

Use `Result` and `Option` appropriately. Prefer the `?` operator over explicit matching when propagating errors.

```rust
// Bad - verbose explicit matching
fn process_user(id: UserId) -> Result<User, Error> {
    let data = match fetch_data(id) {
        Ok(data) => data,
        Err(error) => return Err(error),
    };
    Ok(parse_user(data))
}

// Good - use ? operator
fn process_user(id: UserId) -> Result<User, Error> {
    let data = fetch_data(id)?;
    Ok(parse_user(data))
}
```

Never call `.unwrap()` in production code, and never use `.unwrap()`/`.expect()` as convenience error handling. Reserve `.expect("...")` for invariants the surrounding code already guarantees — where a panic means a programming error — and state the invariant in the message. Every other fallible path propagates with `?`.

```rust
// Bad - panics on any failure
let user = fetch_user(id).unwrap();

// Good - propagate the error
let user = fetch_user(id)?;

// Good - invariant guaranteed above; the message states it
let first_batch = batches.first().expect("batches is non-empty: checked at loop entry");
```

For custom error types, use `thiserror` if the project already has it as a dependency in `Cargo.toml`:

```rust
// With thiserror (only if already in Cargo.toml)
#[derive(Debug, thiserror::Error)]
pub enum UserError {
    #[error("user not found: {0}")]
    NotFound(UserId),
    #[error("invalid user data: {0}")]
    InvalidData(String),
}
```

### 4. Documentation (MEDIUM)

Use `///` doc comments for public items. Use `//!` for module-level documentation. Follow Rust API documentation conventions with examples in doc comments for public functions. Keep inline `//` comments to a minimum: a comment explains *why*, not *what* — self-explanatory code needs no narration.

```rust
//! User management module.
//!
//! This module provides functionality for creating and managing users.

/// Creates a new user with the given name.
///
/// # Examples
///
/// ```
/// # fn main() -> Result<(), Box<dyn std::error::Error>> {
/// let user = create_user("Alice")?;
/// assert_eq!(user.name, "Alice");
/// # Ok(())
/// # }
/// ```
pub fn create_user(name: &str) -> Result<User, UserError> {
    // ...
}
```

### 5. Constants (CRITICAL)

Define constants using `SCREAMING_SNAKE_CASE`. Place all constants at the top of the module after use statements.

```rust
use std::time::Duration;

use crate::config::Config;

const API_BASE_URL: &str = "https://api.example.com/v1";
const MAX_RETRY_ATTEMPTS: u32 = 3;
const DEFAULT_TIMEOUT: Duration = Duration::from_secs(30);

pub fn make_request(endpoint: &str) -> Result<Response, Error> {
    // ...
}
```

Any literal value (string, number, etc.) that appears in more than one place across the codebase **must** be extracted into a named constant. Define the constant once in the module that owns the concept, then import it everywhere else. Never duplicate the raw literal. Test code is not exempt: a literal duplicated across test modules is the same violation.

```rust
// Bad - same string defined independently in two modules
// handlers/backup.rs
const BACKUP_STATUS_ACTIVE: &str = "active";

// services/scheduler.rs
const STATUS_ACTIVE: &str = "active";  // duplicate!

// Good - single definition in the authoritative module
// domain/backup.rs
pub const BACKUP_STATUS_ACTIVE: &str = "active";
pub const BACKUP_STATUS_FAILED: &str = "failed";
pub const BACKUP_STATUS_ARCHIVED: &str = "archived";

// handlers/backup.rs
use crate::domain::backup::BACKUP_STATUS_ACTIVE;
```

### 6. Modern Module Convention (HIGH)

Use the modern Rust module convention with `module_name.rs` files. Never use `mod.rs` files.

```
src/
├── main.rs
├── lib.rs
├── user.rs           # Good: module_name.rs
├── user/
│   ├── repository.rs
│   └── service.rs
└── order.rs
```

### 7. Import Organization (HIGH)

Group use statements in the following order with blank lines between groups:
1. Standard library (`std::`)
2. External crates
3. Local crate modules (`crate::`, `super::`)

```rust
use std::collections::HashMap;
use std::sync::Arc;

use serde::{Deserialize, Serialize};
use tokio::sync::RwLock;

use crate::domain::User;
use crate::infrastructure::Repository;
```

**Placement — keep all `use` statements at module top**, in the groups above. Do not scatter imports inside functions, `impl` blocks, or other inner scopes.

*One exception:* a function-local `use` is allowed **only** to alias a generated name that shadows a prelude item and is used in exactly one function — e.g. a tonic/prost oneof result type named `Result`, which collides with `std::result::Result`. Import it, aliased, inside the one decode function that matches on it:

```rust
fn map_resource_target(
    response: worker_v1::FetchResolvedResourceTargetResponse,
) -> Result<ResourceTargetOutcome, ControlPlaneError> {
    use worker_v1::fetch_resolved_resource_target_response::Result as TargetResult;
    match response.result { /* … */ }
}
```

This keeps the collision-prone `Result` out of the module namespace and puts the alias beside its only use. It is not a licence for convenience-scoped imports: anything that is not a prelude-shadowing generated name used in exactly one function goes at module top.

**Cap inline `crate::…` paths at 3 segments.** Count every `::` segment from `crate` through the final type or function name — method calls via `.` do not count. An inline path at a call site may have at most three segments; deeper paths force the reader to parse the *location* before they can read the *action* — bring the inner part into scope with `use` first.

```rust
// OK — 3 segments (crate + type + associated fn), at the limit
crate::Config::new()

// OK — 3 segments (crate + module + item)
crate::application::serde
crate::domain::User

// Bad — 4+ segments; unreadable, must `use` first
crate::domain::User::create()
crate::application::ResourceNotificationIntentConfig::from_env_or_default(...)
crate::a::b::c::d::Type::method(...)
```

After importing, the call site stays readable:

```rust
use crate::application::ResourceNotificationIntentConfig;
ResourceNotificationIntentConfig::from_env_or_default(...)
```

This rule applies to expressions, type annotations, `impl` headers, and trait bounds — anywhere an inline path appears at a call site. The same 3-segment cap applies to chains starting from `super::`.

**Does not apply to:** `mod foo;` declarations; compiler-forced fully-qualified paths (e.g. `<T as Trait>::method`, disambiguating trait-method calls inside `where` clauses); and paths inside strings (error messages, doc tests, log statements). Those are not *call sites* of a type.

**Rationale:** at ≤3 segments the inline path is a *navigation hint* (you remember `crate::application::Config`). At 4+ it's a *lookup tax* — competing with the call itself for the reader's attention.

### 8. Fold Single-Caller Helpers Onto Their Owner (CRITICAL)

If a helper function — pure or async — has **exactly one production call site** and that call site lives on a struct (a method, an `impl` block, an associated function), fold the helper in as an associated function or method on that struct. Do not leave it as a free function in the module just because it happens to be pure or because it's currently `pub` for test access.

Cohesion beats free-function-purity. Readers should not have to scroll through a module hunting for "where does this helper live and who calls it?" — the answer should be "it's on the struct that uses it, because nothing else does."

```rust
// Bad — pure helper scattered at module scope with one production caller
pub fn pod_is_workload_exec_candidate(pod: &Pod, pvc_name: &str) -> bool {
    if !active_pod_references_pvc(pod, pvc_name) {
        return false;
    }
    pod_is_running_and_ready(pod)
}

fn pod_is_running_and_ready(pod: &Pod) -> bool { /* ... */ }

pub struct WorkloadReadinessGate<'a> { /* ... */ }

impl<'a> WorkloadReadinessGate<'a> {
    async fn wait_until_ready(mut self) -> Result<WaitOutcome, RestoreTargetError> {
        // ... uses pod_is_workload_exec_candidate, the only production caller ...
    }
}

// Good — single-caller helpers folded onto the owning struct
pub struct WorkloadReadinessGate<'a> { /* ... */ }

impl<'a> WorkloadReadinessGate<'a> {
    pub fn pod_is_workload_exec_candidate(pod: &Pod, pvc_name: &str) -> bool {
        if !active_pod_references_pvc(pod, pvc_name) {
            return false;
        }
        Self::pod_is_running_and_ready(pod)
    }

    fn pod_is_running_and_ready(pod: &Pod) -> bool { /* ... */ }

    async fn wait_until_ready(mut self) -> Result<WaitOutcome, RestoreTargetError> {
        // ... calls Self::pod_is_workload_exec_candidate ...
    }
}
```

**When to apply:**
- The helper has exactly one production caller.
- That caller is itself a method or associated function on a struct (or *is* a struct's `impl` block).
- Tests don't count as additional callers — they're observers, not owners.

**When *not* to apply:**
- The helper has two or more production call sites across different owners. Leave it free, or move it to a shared module if the callers cluster around one concept.
- There is no natural owning struct (the helper is genuinely module-level dispatch).

**The visibility cost is acceptable.** Folding a helper onto a struct often means making the struct `pub` so integration tests can reach the method. That widens the *naming* surface, not the *conceptual* API — accept it rather than leaving free `pub fn`s drifting around the one struct that owns all the state and call sites.

**Rationale:** Ownership should read directly from the syntax, not be reconstructed by the reader. Folding also prevents the stale-helper failure mode — a refactor removes the only caller and leaves dead module-scope clutter, since `cargo` won't warn about an unused `pub fn`.

### 9. Collapse Error-Type Twins With a Neutral Error (CRITICAL)

When two call paths need the same logic but return different error types, do **not** copy the whole function once per error type. These "twins" — identical bodies differing only in which error variant they build — are the duplication that quietly explodes a file: every shared check, loader, and helper sprouts a `_for_x` / `_for_y` copy, because copying "just" satisfies the type checker.

Write the logic **once**, returning a neutral error scoped to the operation, and provide `From<NeutralError>` for each caller's error type. `?` (or `.into()`) translates at the boundary, so the only real difference — the variant mapping — lives in one small `From` impl instead of N duplicated bodies.

```rust
// Bad — one full copy per caller error type
async fn check_quota_for_trigger(&self, s: &Schedule) -> Result<(), TriggerError> {
    /* 15 lines */ Err(TriggerError::QuotaExceeded(s.id().clone()))
}
async fn check_quota_for_execute(&self, s: &Schedule) -> Result<(), ExecuteError> {
    /* same 15 lines */ Err(ExecuteError::QuotaExceeded(s.id().clone()))
}

// Good — logic once; divergence collapses into From impls
enum AdmissionError { QuotaExceeded(ScheduleId), Database(String) }

async fn check_quota(&self, s: &Schedule) -> Result<(), AdmissionError> {
    /* 15 lines, once */ Err(AdmissionError::QuotaExceeded(s.id().clone()))
}

impl From<AdmissionError> for TriggerError { /* 1:1 variant map */ }
impl From<AdmissionError> for ExecuteError { /* 1:1 variant map */ }

// callers — same call, each picks its own From:
self.check_quota(s).await?;                 // ? when propagating directly

if let Err(error) = self.check_quota(s).await {
    self.release_lock(s.id()).await;        // .into() when you must clean up first
    return Err(error.into());
}
```

**When to apply:** 2+ call sites run the same logic but return different error enums and the bodies differ only by the variant constructed — the usual cause of `_for_trigger` / `_for_execute` method explosions. The neutral error only needs the variants those shared paths actually emit (typically the intersection the public errors already share).

**Check for drift before collapsing.** Twins copied long ago often diverge silently — one path gains a guard the other lacks (e.g. one verifies workspace ownership, the other forgot to). Diff the bodies first; if behavior differs, decide the single correct behavior and fix it *before* unifying — don't freeze an inconsistency into the neutral version.

**Rationale:** A duplicated method per error type is the cheapest duplication to introduce and the most expensive to carry — it multiplies across every shared helper and hides latent behavioral drift between the copies. A neutral error keeps the logic single-sourced and reduces the inter-path difference to a declarative variant map.

### 10. Self-Documenting Return Types (HIGH)

When a function returns multiple values, or a bare `bool`/primitive whose meaning isn't obvious from the signature, return a **named type**: a struct whose fields name each value, or an enum whose variants name each outcome. The reader should learn the contract from the signature, not by memorising what each tuple position or `true` means. The cost is one small declaration; the payoff is that every call site reads the meaning off the names.

```rust
// Bad — caller must remember the bool means "the read succeeded", and that
// (true, []) ("nothing to probe") differs from (false, []) ("a read failed").
async fn resolve_connectivity(&self, /* ... */) -> (bool, Vec<ConnectivitySubject>) {
    // ...
}
let (connectivity_available, connectivity_subjects) = self.resolve_connectivity(/* ... */).await;

// Good — the type names the contract; the signature is the documentation.
struct ConnectivityResolution {
    available: bool, // true = every board read succeeded; false = one failed, board omitted
    subjects: Vec<ConnectivitySubject>,
}
async fn resolve_connectivity(&self, /* ... */) -> ConnectivityResolution {
    // ...
}
let connectivity = self.resolve_connectivity(/* ... */).await;
// connectivity.available / connectivity.subjects — self-explaining at every use
```

**Apply when:** the function returns 2+ values where a primitive's role isn't self-evident from position; a bare `bool` whose meaning the function name doesn't already state; or distinct combinations carry distinct meaning (`(true, [])` vs `(false, [])`) — model mutually-exclusive outcomes as an enum.

**Don't apply when:** the name already says it (`fn len(&self) -> usize`, `fn is_empty(&self) -> bool`) or for idiomatic stdlib shapes (`Result<T, E>`, `Option<T>`, a map's `(key, value)`, `split_at`'s `(left, right)`).

**Rationale:** A `(bool, Vec<_>)` return makes the signature lie by omission — the meaning lives in the reader's memory or a drifting comment, not the type. A named struct/enum encodes the contract where the compiler and every call site see it.

**Where the type lives** is decided by the project's module-structure conventions (see the rust-project-structure skill), not by this rule — a concept-local data type typically belongs with the concept's other data types, not buried in the file that happens to return it.

### 11. Unsafe Code (CRITICAL)

Avoid `unsafe`. Safe Rust is the default; reach for `unsafe` only when there is no safe alternative — an FFI boundary, a low-level primitive the standard library cannot express, or a proven, measured hot path. Never use `unsafe` for convenience, to silence the borrow checker, or to skip a safe API that already exists.

When `unsafe` is genuinely unavoidable:

- Keep the `unsafe` block as small as possible — wrap only the operations that actually require it, never the surrounding safe logic.
- Encapsulate it behind a safe abstraction so callers never touch `unsafe` and cannot violate its invariants.
- Document every `unsafe` block with a `// SAFETY:` comment, and every public `unsafe fn` with a `# Safety` doc section, stating the invariant the caller or the code must uphold and why it holds here.

```rust
// Bad - unsafe used to bypass safe indexing, with no justification
let value = unsafe { *slice.get_unchecked(index) };

// Good - a safe API expresses the same intent
let value = slice[index]; // or slice.get(index) when the index may be absent

// Good - unsafe genuinely required, minimal scope, invariant documented
// SAFETY: `raw_pointer` came from `Box::into_raw` above and is neither aliased
// nor freed elsewhere, so reconstructing the Box here is sound.
let recovered = unsafe { Box::from_raw(raw_pointer) };
```

## Anti-Patterns to Avoid

1. **Single-letter variables** — `x`, `i`, `p` in closures or anywhere else instead of descriptive names (Rule 1)
2. **Excessive type annotations** — annotating types inference already makes obvious (Rule 2)
3. **Verbose error handling** — explicit `match` where `?` suffices (Rule 3)
4. **Gratuitous `.unwrap()`** — unwrapping in production paths instead of propagating with `?` (Rule 3)
5. **Excessive comments** — narrating *what* self-explanatory code does instead of *why* (Rule 4)
6. **`mod.rs` files** — old module convention instead of `module_name.rs` (Rule 6)
7. **Mixed imports** — `use` statements not grouped std / external / local (Rule 7)
8. **Function-scoped imports** — `use` inside a function, `impl`, or block; sole exception in Rule 7
9. **Inline `crate::…` paths beyond 3 segments** — instead of bringing the item into scope with `use` (Rule 7)
10. **Duplicate literal values** — the same literal defined in more than one place instead of one named constant imported everywhere (Rule 5)
11. **Scattered single-caller helpers** — a free module-scope helper whose only production caller lives on a struct (Rule 8)
12. **Error-type twins** — `_for_x` / `_for_y` copies of the same body, differing only in the error variant built (Rule 9)
13. **Opaque return shapes** — a tuple of primitives or a bare `bool` instead of a named struct/enum (Rule 10)
14. **Gratuitous `unsafe`** — `unsafe` for convenience or to silence the borrow checker (Rule 11)
