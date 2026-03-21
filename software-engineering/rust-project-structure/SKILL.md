---
name: rust-project-structure
description: Conventions for organising modules, files, and folders inside a Rust project. Use when creating new modules, restructuring existing code, or reviewing folder layout in layered Rust applications.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.1"
---

# Project Structure Skill

## Purpose

This skill provides conventions for organising modules inside `src/`. It covers concept-based folder layout, internal file naming, trait and error placement, and layer-specific adaptations. These rules apply on top of a layered architecture (e.g. hexagonal / ports-and-adapters) and complement code-style and design-principle guidelines.

## When to Apply

Apply these guidelines when:
- Creating new modules or concept folders
- Restructuring or reorganising existing source code
- Adding new components (services, orchestrators, executors, providers) to a concept
- Reviewing folder layout for consistency
- Working in a layered Rust codebase (domain / application / infrastructure or similar)

## When NOT to Apply

Do not apply when:
- The project is a flat, single-file utility or script
- Working on a library crate with no layered architecture
- The project already follows a different, well-established convention that the team has agreed on

## Core Principles

### 1. Concept-Based Folders (CRITICAL)

Every top-level folder inside a layer represents a **business concept** or a clearly named shared capability (e.g. `order/`, `payment/`, `notification/`, `encryption/`). Never create folders named after a component role (e.g. ~~`orchestrator/`~~, ~~`executor/`~~, ~~`scheduler/`~~, ~~`handler/`~~).

If a concept needs an orchestrator, executor, or scheduler, that component lives **inside** the concept folder.

```
# Bad — folders named after roles
src/application/
├── orchestrators/
│   ├── order.rs
│   └── payment.rs
├── executors/
│   ├── order.rs
│   └── payment.rs
└── services/
    ├── order.rs
    └── payment.rs

# Good — folders named after concepts
src/application/
├── order/
│   ├── port.rs
│   ├── service.rs
│   ├── orchestrator.rs
│   └── executor.rs
└── payment/
    ├── port.rs
    ├── service.rs
    └── orchestrator.rs
```

Nested folders are allowed when they model a focused sub-capability of the parent concept (e.g. `destination/file/`). A sub-capability follows the same local structure rules as any other concept.

### 2. Internal File Layout (CRITICAL)

Each concept folder follows this canonical structure:

| File | Contains | Required? |
|------|----------|-----------|
| `port.rs` | **All** traits (ports) for this concept — services, orchestrators, executors, providers | Yes, when this layer defines local traits for the concept |
| `service.rs` | `Default*` implementation of the main service trait | Only if the concept has a main service impl |
| `error.rs` | **All** error enums for this concept — service errors, orchestrator errors, execution errors | Only if the concept defines concept-local errors |
| `orchestrator.rs` | `Default*Orchestrator` implementation | No |
| `executor.rs` | `Default*Executor` implementation | No |
| `provider.rs` | `Default*Provider` implementation | No |
| `provisioner.rs` | `Default*Provisioner` implementation | No |
| `sweeper.rs` | Periodic cleanup runner with a `tick()` method | No |
| `manager.rs` | Periodic enforcement runner with a `tick()` method | No |
| Other files | Concept-specific helpers (e.g. `progress.rs`, `validation.rs`) | No |

### 3. One Trait File Per Concept (CRITICAL)

If a layer defines traits for a concept, **all** of them go in `port.rs`. Do not split traits across `port.rs`, `orchestrator.rs`, `handler.rs`, etc. Do not create placeholder `port.rs` files in layers that only implement traits defined elsewhere.

```rust
// Good — all traits for the concept in one file
// src/application/order/port.rs

pub trait OrderService: Clone + Send + Sync + 'static {
    fn create_order(
        &self,
        request: &CreateOrderRequest,
    ) -> impl Future<Output = Result<Order, CreateOrderError>> + Send;
}

pub trait OrderExecutor: Clone + Send + Sync + 'static {
    fn execute(
        &self,
        order: &Order,
    ) -> impl Future<Output = Result<OrderResult, ExecuteOrderError>> + Send;
}

pub trait OrderNotifier: Clone + Send + Sync + 'static {
    fn notify_completed(
        &self,
        order: &Order,
    ) -> impl Future<Output = Result<(), NotifyError>> + Send;
}
```

### 4. One Error File Per Concept (HIGH)

All error enums for a concept go in `error.rs`. Do not create `orchestrator_error.rs`, `executor_error.rs`, etc.

```rust
// Good — all errors for the concept in one file
// src/application/order/error.rs

#[derive(Debug)]
pub enum CreateOrderError {
    Duplicate { name: OrderName },
    InvalidInput(String),
    Unknown(String),
}

#[derive(Debug)]
pub enum ExecuteOrderError {
    NotFound { id: OrderId },
    AlreadyExecuted { id: OrderId },
    Unknown(String),
}
```

### 5. Naming: Trait Gets the Clean Name, Struct Gets the Prefix (HIGH)

The trait (port) gets the clean, unqualified name (`OrderService`). The concrete struct gets a descriptive prefix (`DefaultOrderService`).

If a layer contains **multiple concrete adapters** for the same upstream trait, use an explicit adapter name based on the external system or protocol (`PostgresOrderRepository`, `RedisOrderCache`) instead of `Default*`.

```rust
// Single canonical implementation
pub trait OrderService { /* ... */ }            // trait — clean name
pub struct DefaultOrderService { /* ... */ }    // struct — Default prefix

// Multiple adapters for the same trait
pub trait OrderRepository { /* ... */ }         // trait — clean name
pub struct PostgresOrderRepository { /* ... */ } // struct — technology prefix
pub struct SqliteOrderRepository { /* ... */ }   // struct — technology prefix
```

### 6. Files Named After the Role, Not the Prefix (HIGH)

The service impl goes in `service.rs`, the orchestrator impl goes in `orchestrator.rs`, the executor impl goes in `executor.rs`. Do not use `default_orchestrator.rs` — the `Default` prefix belongs on the struct, not the file.

```
# Bad
src/application/order/
├── default_service.rs
├── default_orchestrator.rs
└── default_executor.rs

# Good
src/application/order/
├── service.rs          # contains DefaultOrderService
├── orchestrator.rs     # contains DefaultOrderOrchestrator
└── executor.rs         # contains DefaultOrderExecutor
```

### 7. Short Module Names — Let the Parent Provide Context (HIGH)

When a file lives inside a concept folder, its name should not repeat the concept. Use `handler.rs` inside `order/`, not `order_handler.rs` — the full path `order::handler` already reads clearly. The struct inside keeps its full descriptive name (`OrderHandler`).

```
# Bad — stuttering names
src/infrastructure/api/order/
├── order_handler.rs
├── order_request.rs
└── order_response.rs

# Good — parent provides context
src/infrastructure/api/order/
├── handler.rs          # contains OrderHandler
├── request.rs          # contains CreateOrderRequest, UpdateOrderRequest
└── response.rs         # contains OrderResponse
```

### 8. NoOp Stubs Live Close to the Trait (MEDIUM)

Keep NoOp/stub implementations close to the port they implement — either in the same file as the trait or in the matching implementation file. Do not hide a provider stub in `service.rs` and do not create separate `noop_*.rs` files.

### 9. Cross-Cutting Components Need a Capability Name (MEDIUM)

If multiple concepts share infrastructure, extract a shared module named after the **capability** it exposes, never after the consuming role.

```
# Bad — named after the role
src/application/executor/
    encryption.rs    # used by order executor and payment executor

# Good — named after the capability
src/application/encryption/
    port.rs
    service.rs
```

### 10. Concept Folders Without a Service or Port Are Suspect (MEDIUM)

If a folder has no `service.rs` or `port.rs` (e.g. a `lock/` folder with only `sweeper.rs`), consider whether the sweeper belongs inside the concept it cleans up (e.g. the `schedule/` concept for schedule lock sweeping).

## Infrastructure Layer Adaptations

The infrastructure layer follows the same core principles, with these additional allowances:

### Adapter-Family Folders at the Top Level

Infrastructure may use **adapter-family** or **technical-capability** folders at the top level when that is the cleanest primary axis. Examples: `api/`, `database/`, `gateway/`, `runtime/`, `bootstrap/`, `session/`, `crypto/`, `config/`, `event/`.

Inside an adapter family, organize the next level by concept whenever practical (e.g. `api/order/`, `database/order/`, `gateway/source/`).

```
src/infrastructure/
├── api/                    # HTTP adapter family
│   ├── order/
│   │   ├── handler.rs
│   │   ├── request.rs
│   │   └── response.rs
│   └── payment/
│       ├── handler.rs
│       └── response.rs
├── database/               # Persistence adapter family
│   ├── order/
│   │   └── repository.rs   # PostgresOrderRepository
│   └── payment/
│       └── repository.rs
├── gateway/                # External system adapters
│   ├── source/
│   │   └── stripe.rs
│   └── destination/
│       └── s3.rs
├── runtime/                # Long-lived loop wrappers
│   └── order/
│       └── sweeper.rs
└── bootstrap/              # Startup-only initialization
    └── seeder.rs
```

### Avoid Weak Folder Buckets

Avoid generic folders like `provider/`, `handler/`, `repository/`, `service/`, `shared/`, or `common/` that merely collect unrelated concerns by role. Prefer stronger adapter boundaries (`api/`, `database/`) or named capabilities (`credentials/`, `multipart_upload/`).

### Runtime and Bootstrap Separation

- Put long-lived loop wrappers and background runners under `runtime/`, grouped by the concept they drive.
- Put startup-only seeders, bootstrap coordinators, and one-shot initialization tasks under `bootstrap/`.

### Missing `port.rs` Is Natural in Infrastructure

Infrastructure often implements ports defined in `domain/` or `application/` rather than defining new local traits. Missing `port.rs` should not be treated as a structural violation.

### Technology-Named Modules for Single Providers

When a capability currently has a single provider-specific implementation, naming the top-level folder after the external system is acceptable (e.g. `minio/`, `stripe/`). Revisit when a broader capability folder would clearly improve clarity.

### Shared Helpers in the Smallest Owning Namespace

Place shared helpers in the smallest meaningful owning namespace. If only Kubernetes source adapters use a helper, keep it under `gateway/source/kubernetes/`. If multiple destination adapters use an I/O helper, `gateway/destination/io.rs` is better than `gateway/destination/shared/`.

## Anti-Patterns to Avoid

1. **Role-based folders**: Grouping by `services/`, `handlers/`, `repositories/` instead of business concepts
2. **Stuttering module names**: `order/order_handler.rs` instead of `order/handler.rs`
3. **Scattered traits**: Splitting traits for a single concept across multiple files
4. **Scattered errors**: Creating `service_error.rs`, `executor_error.rs` instead of a single `error.rs`
5. **Weak bucket folders**: `shared/`, `common/`, `utils/` collecting unrelated concerns
6. **File names matching struct prefixes**: `default_service.rs` instead of `service.rs`
7. **Orphan concept folders**: Folders with only a sweeper or runner and no port or service
8. **NoOp files**: Separate `noop_provider.rs` files instead of keeping stubs near the trait

## Quick Reference

### Adding a New Concept

1. Create a folder named after the business concept under the appropriate layer
2. Add `port.rs` with all traits for this concept (if defining traits)
3. Add `error.rs` with all error enums (if defining errors)
4. Add `service.rs` with the `Default*` implementation
5. Add additional role files (`orchestrator.rs`, `executor.rs`) only as needed

### Adding a Component to an Existing Concept

1. If the component introduces new traits, add them to the existing `port.rs`
2. If the component introduces new errors, add them to the existing `error.rs`
3. Create a new file named after the role (e.g. `executor.rs`)
4. Name the struct with the concept prefix and role suffix (`OrderExecutor` trait, `DefaultOrderExecutor` struct)

### Adding an Infrastructure Adapter

1. Place it under the appropriate adapter-family folder (`api/`, `database/`, `gateway/`)
2. Organize by concept inside the adapter family
3. Use technology-specific struct names (`PostgresOrderRepository`, not `DefaultOrderRepository`)
4. No need for a `port.rs` — the trait lives in domain or application
