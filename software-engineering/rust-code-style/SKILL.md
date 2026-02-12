---
name: rust-code-style
description: Rust code style guidelines for clean, maintainable, and readable code with hexagonal architecture
license: MIT
metadata:
  author: cristian.ciortea@proton.me
  version: "0.0.1"
---

# Rust Code Style Skill

Version: 0.0.1

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

Use descriptive, intent-revealing names. Good names show intent and are searchable. Never use single-letter variable or constant names except for closures with obvious context.

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

## Anti-Patterns to Avoid

1. **Single-letter variables**: Using `x`, `i`, `p` in closures instead of descriptive names
2. **Excessive type annotations**: Adding types when inference is clear
3. **Verbose error handling**: Using `match` when `?` suffices
4. **mod.rs files**: Using old module convention instead of `module_name.rs`
5. **Mixed imports**: Not grouping imports by origin
6. **Over-architecting**: Using hexagonal/enterprise patterns for systems code
7. **Excessive comments**: Adding comments for self-explanatory code
8. **Struct field shorthand**: Using `field` instead of `field: field` in struct initialization

## Guidelines

### Type Annotations and Documentation
- Let Rust infer obvious types
- Add explicit annotations for complex types or public APIs
- Use `///` for public item documentation
- Use `//!` for module-level documentation
- Document complex types with expected structure and usage

### Naming
- Use descriptive, intent-revealing names
- Use searchable names (no single letters except in trivial closures)
- Use `SCREAMING_SNAKE_CASE` for constants
- Use descriptive names in ALL closures and iterators

### Code Organization
- Keep comments to a minimum
- Use modern module convention (no `mod.rs`)
- Group imports: std, external, local
- Place constants at module top after imports

### Error Handling
- Use `Result` and `Option` appropriately
- Prefer `?` operator for error propagation
- Use `thiserror` for custom error types

### Architecture
- Separate domain, application, and infrastructure
- Dependencies point inward
- Define ports as traits in domain/application
- Implement adapters in infrastructure
