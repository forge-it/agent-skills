---
name: rust-code-style
description: Coding conventions and style rules for Rust. Apply when writing or reviewing any Rust code.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.7"
---

# Rust Code Style Skill

## Purpose

This skill provides guidelines for writing clean, maintainable, and readable Rust code. It focuses on type annotations, naming conventions, code organization, error handling, and hexagonal architecture.

## When to Apply

Apply these guidelines when:
- Creating new Rust code
- Updating existing Rust code
- Reviewing Rust code
- Refactoring Rust modules

## Core Principles

### 1. Descriptive Naming (CRITICAL)

Use descriptive, intent-revealing names. Good names show intent and are searchable. Never use single-letter variable or constant names, including in closures and iterators.

```rust
// Bad
let t = 30;
let d = Duration::from_secs(60);

// Good
let elapsed_time_in_days = 30;
let request_timeout = Duration::from_secs(60);
```

### 2. Iterator and Closure Variables (CRITICAL)

Always use descriptive parameter names in closures, even when they're short-lived. Never use single-letter or abbreviated names.

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

**Rationale:** Descriptive names improve code searchability and readability. Single-letter parameters force readers to mentally track what the variable represents, increasing cognitive load. This rule applies to ALL closures including `.map()`, `.filter()`, `.find()`, `.any()`, `.all()`, `.fold()`, and any other iterator or combinator methods.

### 3. Type Inference (CRITICAL)

Let Rust infer types when obvious. Add explicit annotations for clarity in complex situations or public APIs.

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

### 4. Error Handling (CRITICAL)

Use `Result` and `Option` appropriately. Prefer the `?` operator over explicit matching when propagating errors.

```rust
// Bad - verbose explicit matching
fn process_user(id: UserId) -> Result<User, Error> {
    let data = match fetch_data(id) {
        Ok(d) => d,
        Err(e) => return Err(e),
    };
    Ok(parse_user(data))
}

// Good - use ? operator
fn process_user(id: UserId) -> Result<User, Error> {
    let data = fetch_data(id)?;
    Ok(parse_user(data))
}
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

### 5. Documentation (MEDIUM)

Use `///` doc comments for public items. Use `//!` for module-level documentation. Follow Rust API documentation conventions with examples in doc comments for public functions.

```rust
//! User management module.
//!
//! This module provides functionality for creating and managing users.

/// Creates a new user with the given name.
///
/// # Arguments
///
/// * `name` - The user's display name
///
/// # Returns
///
/// A `Result` containing the created `User` or an error if creation fails.
///
/// # Examples
///
/// ```
/// let user = create_user("Alice")?;
/// assert_eq!(user.name, "Alice");
/// ```
pub fn create_user(name: &str) -> Result<User, UserError> {
    // ...
}
```

### 6. Constants (HIGH)

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

Any literal value (string, number, etc.) that appears in more than one place across the codebase **must** be extracted into a named constant. Define the constant once in the module that owns the concept, then import it everywhere else. Never duplicate the raw literal.

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

### 7. Modern Module Convention (HIGH)

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

### 8. Import Organization (HIGH)

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

**Cap inline `crate::…` paths at 3 path components.** Counting from `crate`, an inline path at a call site may have at most three segments — `crate::module::Item` or shorter. Deeper paths force the reader to parse the *location* before they can read the *action*; bring the inner part into scope with `use` first.

```rust
// OK — 2 components (crate + module/type), readable
crate::Config::new()

// OK — 3 components (crate + module + item)
crate::application::serde
crate::domain::User::create()

// Bad — 4+ components; unreadable, must `use` first
crate::application::ResourceNotificationIntentConfig::from_env_or_default(...)
crate::a::b::c::d::Type::method(...)
```

After importing, the call site stays readable:

```rust
// Type-level import — top-down, the action leads
use crate::application::ResourceNotificationIntentConfig;
ResourceNotificationIntentConfig::from_env_or_default(...)

// Module-level import — qualified by one module, still ≤3 components
use crate::application;
application::ResourceNotificationIntentConfig::from_env_or_default(...)
```

This rule applies to expressions, type annotations, `impl` headers, and trait bounds — anywhere an inline path appears at a call site. The same 3-component cap applies to chains starting from `super::` once they would exceed three segments.

**Does not apply to:** `mod foo;` declarations; compiler-forced fully-qualified paths (e.g. `<T as Trait>::method`, disambiguating trait-method calls inside `where` clauses); and paths inside strings (error messages, doc tests, log statements). Those are not *call sites* of a type.

**Rationale:** at ≤3 components the inline path is a *navigation hint* (you remember `crate::application::Config`). At 4+ it's a *lookup tax* — competing with the call itself for the reader's attention.

## Architecture Patterns

### 9. Choose the Right Architecture (CRITICAL)

Use the simplest architecture that handles your actual complexity. Different project types require different patterns.

#### For Low-Level Systems Code (drivers, microkernels, embedded)

Use clean module boundaries, HALs, and well-defined traits:

```
src/
├── hal/              # Hardware Abstraction Layer
│   ├── traits.rs     # Platform-agnostic traits
│   └── platform/     # Platform-specific implementations
├── protocol/         # Protocol handling, state machines
├── device/           # Device-specific logic
└── lib.rs
```

- The domain *is* the infrastructure in systems code
- Use traits for hardware abstraction (e.g., `embedded-hal`)
- Use state machines for protocol handling
- Use `#[cfg(...)]` for platform-specific code

#### For Business Applications (web services, APIs, CRUD apps)

Hexagonal architecture (ports and adapters) makes sense when isolating business logic from external concerns:

```
src/
├── domain/           # Core business logic, entities
├── application/      # Use cases, port definitions (traits)
└── infrastructure/   # Adapters (HTTP, database, external APIs)
```

- Dependencies point inward (domain has no external deps)
- Define traits (ports) in domain/application
- Implement adapters in infrastructure
- Use dependency injection to wire together

### When to Use Hexagonal Architecture

**Good fit:**
- Web services with complex business rules
- Applications with multiple external integrations (databases, APIs, message queues)
- Projects that need to swap implementations (e.g., different databases)

**Poor fit:**
- Drivers and embedded code (the domain *is* the hardware)
- Microkernels (scheduling, memory management are inherently tied to CPU)
- Simple utilities or CLI tools
- Protocol implementations

### 10. Explicit Struct Field Initialization (CRITICAL)

Always use explicit `field: value` syntax when initializing structs. Never use the shorthand where the field name matches the variable name. Explicit initialization makes it immediately clear which value maps to which field, improving readability and making the code resilient to refactoring.

```rust
#[derive(Clone)]
pub struct AppState<SS, BS, RS>
where
    SS: ScheduleService,
    BS: BackupService,
    RS: RestoreService,
{
    pub schedule_service: SS,
    pub backup_service: BS,
    pub restore_service: RS,
}

// Bad - shorthand hides the field-to-value mapping
let state = AppState {
    schedule_service,
    backup_service,
    restore_service,
};

// Good - explicit field: value makes the mapping clear
let state = AppState {
    schedule_service: schedule_service,
    backup_service: backup_service,
    restore_service: restore_service,
};
```

This also applies to simpler structs:

```rust
// Bad
let config = DatabaseConfig {
    host,
    port,
    max_connections,
};

// Good
let config = DatabaseConfig {
    host: host,
    port: port,
    max_connections: max_connections,
};
```

When using the newtype pattern, pass the struct directly into the constructor rather than constructing the newtype first and then setting fields. Map each field explicitly from the source (e.g., a request object) to the config struct:

```rust
// Good - explicit field mapping from request into newtype constructor
let schedule = Schedule::new(ScheduleConfig {
    id: ScheduleId::new(),
    name: request.name.clone(),
    cron_expression: request.cron_expression.clone(),
    strategy: request.strategy,
    source_type: request.source_type,
    source_host: request.source_host.clone(),
    source_database: request.source_database.clone(),
    enabled: request.enabled,
    created_at: now,
    updated_at: now,
});
```

**Rationale:** Explicit field initialization acts as self-documentation. When reading code, you can immediately see the intent without needing to verify that a local variable has the exact same name as the struct field. It also prevents subtle bugs when renaming variables during refactoring.

### 11. Fold Single-Caller Helpers Onto Their Owner (CRITICAL)

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

**The visibility cost is acceptable.** Folding a `pub fn` into a `pub fn` associated on a struct usually means making the struct `pub` too so integration tests can reach the method. That is fine — if the struct already has a single owning module and is consumed by a `pub` strategy / port / service, exposing it as `pub` does not widen the *conceptual* API surface; it only widens the *naming* surface. The alternative — leaving the helper free purely to avoid renaming `helper(x)` to `Owner::helper(x)` in tests — produces module files where six free `pub fn`s drift around one struct that owns all the state and all the call sites.

**Rationale:** A module with one struct and six free `pub fn`s scattered around it forces the reader to reconstruct ownership manually. Folding the single-caller helpers onto the struct makes ownership read directly from the syntax. It also prevents the "stale helper" failure mode where a refactor removes the only caller and leaves the helper as dead module-scope clutter — `cargo` won't warn about an unused `pub fn`.

### 12. Collapse Error-Type Twins With a Neutral Error (CRITICAL)

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

### 13. Self-Documenting Return Types (HIGH)

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

**Rationale:** A `(bool, Vec<_>)` return makes the signature lie by omission — the meaning lives in the reader's memory or a drifting comment, not the type. A named struct/enum encodes the contract where the compiler and every call site see it: the same self-documentation as explicit struct field initialization (Rule 10), applied to output.

**Where the type lives is a separate question.** This rule is only about the *shape* of the return. Which module the named type belongs in — alongside its owner, or in a shared data-model module — is decided by your project's module-structure conventions, not by this rule. A concept-local data type (even an internal, single-caller one) typically belongs with the concept's other data types, not buried in the file that happens to return it.

### 14. Unsafe Code (CRITICAL)

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

If a task appears to require introducing `unsafe`, prefer a safe alternative first; when none exists, keep the unsafe surface minimal, encapsulated, and documented.

## Anti-Patterns to Avoid

1. **Single-letter variables**: Using `x`, `i`, `p` in closures instead of descriptive names
2. **Excessive type annotations**: Adding types when inference is clear
3. **Verbose error handling**: Using `match` when `?` suffices
4. **mod.rs files**: Using old module convention instead of `module_name.rs`
5. **Mixed imports**: Not grouping imports by origin
6. **Over-architecting**: Using hexagonal/enterprise patterns for systems code
7. **Excessive comments**: Adding comments for self-explanatory code
8. **Struct field shorthand**: Using `field` instead of `field: field` in struct initialization
9. **Duplicate literal values**: Defining the same string, number, or other literal in more than one place instead of extracting it into a named constant in the authoritative module and importing it everywhere
10. **Scattered single-caller helpers**: Leaving a helper function free at module scope when it has exactly one production caller that lives on a struct — fold it onto that struct as an associated function or method
11. **Error-type twins**: Copying a whole function once per caller error type (`_for_trigger` / `_for_execute`) instead of writing it once against a neutral error and mapping with `From`
12. **Opaque return shapes**: Returning a tuple of primitives or a bare `bool` whose meaning the reader must memorise, instead of a named struct/enum whose fields/variants state what each value means
13. **Inline `crate::…` paths beyond 3 components**: Writing `crate::a::b::c::Type::method(…)` (4+ path components) in expressions, type annotations, or `impl` headers instead of `use crate::a::b::c::Type;` (or a shorter inner import) and shortening the call to a readable ≤3-component form
14. **Gratuitous `unsafe`**: Reaching for `unsafe` for convenience, to silence the borrow checker, or to bypass an existing safe API — instead of reserving it for FFI or low-level needs, keeping its scope minimal, encapsulating it behind a safe interface, and documenting a `// SAFETY:` invariant

## Guidelines

### Type Annotations and Documentation
- Let Rust infer obvious types
- Add explicit annotations for complex types or public APIs
- Use `///` for public item documentation
- Use `//!` for module-level documentation
- Document complex types with expected structure and usage
- Return a named struct/enum, not a tuple of primitives or a bare `bool`, when the meaning of the values is not obvious from the signature

### Naming
- Use descriptive, intent-revealing names
- Use searchable names (no single letters)
- Use `SCREAMING_SNAKE_CASE` for constants
- Use descriptive names in ALL closures and iterators

### Code Organization
- Keep comments to a minimum
- Use modern module convention (no `mod.rs`)
- Group imports: std, external, local
- Never write inline `crate::module::…` paths at call sites — bring long paths into scope with `use` (Rule 8)
- Place constants at module top after imports
- Extract any literal that appears more than once into a named constant
- Fold single-caller helpers onto their owning struct as associated fns; do not leave them free at module scope

### Error Handling
- Use `Result` and `Option` appropriately
- Prefer `?` operator for error propagation
- Use `thiserror` for custom error types
- Don't copy a function per caller error type; write it once against a neutral error and map to each public error with `From`. Diff suspected twins for behavioral drift before collapsing them.

### Architecture
- Separate domain, application, and infrastructure
- Dependencies point inward
- Define ports as traits in domain/application
- Implement adapters in infrastructure

### Unsafe Code
- Avoid `unsafe`; prefer safe APIs and safe abstractions
- Reserve `unsafe` for FFI, proven hot paths, or primitives safe Rust cannot express
- Keep `unsafe` blocks minimal and encapsulate them behind safe interfaces
- Document every `unsafe` block with `// SAFETY:` and every public `unsafe fn` with a `# Safety` doc section
