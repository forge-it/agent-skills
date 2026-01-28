---
name: rust-testing
description: Rust testing best practices using cargo test with focus on clarity and maintainability
license: MIT
metadata:
  author: cristian.ciortea@proton.me
  version: "0.0.1"
---

# Rust Testing Skill

Version: 0.0.1

## Purpose

This skill provides guidelines for writing effective Rust tests. It focuses on clarity, maintainability, and business logic validation over implementation details.

## When to Apply

Apply these guidelines when:
- Writing or modifying Rust unit tests
- Writing or modifying Rust integration tests
- Setting up test infrastructure for new Rust projects

## Core Principles

### 1. Sophisticated Mocking (CRITICAL)

Use sophisticated mocking libraries like `mockall`, `wiremock`, or `httpmock` to simulate HTTP requests and external dependencies. Prefer these over manual mock implementations.

```rust
use mockall::predicate::*;
use mockall::mock;

mock! {
    UserRepository {}
    
    impl UserRepositoryTrait for UserRepository {
        fn find_by_id(&self, id: UserId) -> Result<User, Error>;
        fn save(&self, user: &User) -> Result<(), Error>;
    }
}

#[test]
fn test_get_user_returns_user_when_found() {
    let mut mock_repo = MockUserRepository::new();
    mock_repo
        .expect_find_by_id()
        .with(eq(UserId(123)))
        .returning(|_| Ok(User { id: UserId(123), name: "Alice".into() }));
    
    let service = UserService::new(mock_repo);
    let result = service.get_user(UserId(123));
    
    assert!(result.is_ok());
    assert_eq!(result.unwrap().name, "Alice");
}
```

### 2. HTTP Mocking with wiremock (CRITICAL)

Use `wiremock` for HTTP mocking in integration tests.

```rust
use wiremock::{MockServer, Mock, ResponseTemplate};
use wiremock::matchers::{method, path};

#[tokio::test]
async fn test_fetch_user_returns_user_data() {
    let mock_server = MockServer::start().await;
    
    Mock::given(method("GET"))
        .and(path("/users/123"))
        .respond_with(ResponseTemplate::new(200)
            .set_body_json(json!({"id": 123, "name": "John"})))
        .mount(&mock_server)
        .await;
    
    let client = ApiClient::new(&mock_server.uri());
    let result = client.fetch_user(123).await;
    
    assert!(result.is_ok());
    assert_eq!(result.unwrap().name, "John");
}
```

### 3. Async Testing (CRITICAL)

Use `#[tokio::test]` for async tests. Ensure the tokio runtime is configured appropriately in `Cargo.toml`.

```rust
// Cargo.toml
[dev-dependencies]
tokio = { version = "1", features = ["rt-multi-thread", "macros"] }

// tests/integration_test.rs
#[tokio::test]
async fn test_async_operation_completes_successfully() {
    let result = perform_async_operation().await;
    assert!(result.is_ok());
}
```

### 4. Business Logic Focus (CRITICAL)

Tests should focus on business logic rather than exact timing or implementation details. Exact timestamps are not important for business requirements.

```rust
// Bad - testing exact timestamp
#[test]
fn test_order_has_correct_timestamp() {
    let order = Order::new(items);
    assert_eq!(order.created_at, Utc::now()); // Flaky!
}

// Good - testing business logic
#[test]
fn test_order_calculates_correct_total() {
    let items = vec![
        Item { price: 1000, quantity: 2 },
        Item { price: 500, quantity: 1 },
    ];
    let order = Order::new(items);
    assert_eq!(order.total_cents, 2500);
}
```

### 5. Descriptive Naming (HIGH)

Use descriptive test names following the pattern: `test_<action>_<outcome>_<optional_case>`

```rust
// Good examples
#[test]
fn test_do_periods_overlap_returns_false_when_arguments_are_not_datetimes() {
    // ...
}

#[test]
fn test_upload_image_from_bytes_returns_the_overwritten_public_url() {
    // ...
}

#[test]
fn test_calculate_total_returns_zero_for_empty_cart() {
    // ...
}
```

### 6. All Tests in tests/ Directory (CRITICAL)

All tests must be placed in the `tests/` directory. Never use `#[cfg(test)]` modules in source files. This provides clear separation between production code and test code, and makes test coverage easier to track.

```
src/
├── main.rs
├── domain/
│   └── user.rs
└── infrastructure/
    └── db.rs

tests/
├── unit/                    # Unit tests mirror src/ structure
│   ├── domain/
│   │   └── user.rs          # Tests for src/domain/user.rs
│   └── infrastructure/
│       └── db.rs            # Tests for src/infrastructure/db.rs
├── integration/             # Integration tests mirror src/ structure
│   ├── domain/
│   │   └── user.rs
│   └── infrastructure/
│       └── db.rs
├── api/                     # API/E2E tests
│   ├── user_api.rs
│   └── order_api.rs
└── common/
    └── mod.rs               # Shared test utilities
```

### 7. Test Directory Structure Mirrors Source (CRITICAL)

The test directory structure must mirror the source directory structure. Tests for `src/infrastructure/db.rs` go in `tests/unit/infrastructure/db.rs`.

```rust
// tests/unit/infrastructure/db.rs
use myproject::infrastructure::db::DatabaseConnection;

#[test]
fn test_connection_pool_creates_connections() {
    let pool = DatabaseConnection::new_pool(5);
    assert_eq!(pool.size(), 5);
}

#[test]
fn test_connection_returns_error_for_invalid_config() {
    let result = DatabaseConnection::from_config(&InvalidConfig::default());
    assert!(result.is_err());
}
```

```rust
// tests/unit/domain/user.rs
use myproject::domain::user::User;

#[test]
fn test_new_creates_user_with_given_name() {
    let user = User::new("Alice");
    assert_eq!(user.name, "Alice");
}
```

### 8. Test Categories (HIGH)

Organize tests into three categories:

- **unit/**: Tests for individual functions and structs in isolation
- **integration/**: Tests that verify multiple components work together
- **api/**: End-to-end tests that exercise the full API

```rust
// tests/unit/domain/order.rs - Unit test
#[test]
fn test_order_calculates_total_correctly() {
    let order = Order::new(vec![item1, item2]);
    assert_eq!(order.total_cents, 2500);
}

// tests/integration/domain/order.rs - Integration test
#[tokio::test]
async fn test_order_persists_to_database() {
    let db = setup_test_db().await;
    let repo = OrderRepository::new(db);
    let order = Order::new(vec![item1]);
    
    repo.save(&order).await.unwrap();
    let loaded = repo.find_by_id(order.id).await.unwrap();
    
    assert_eq!(loaded.id, order.id);
}

// tests/api/order_api.rs - API test
#[tokio::test]
async fn test_create_order_endpoint_returns_201() {
    let app = spawn_test_app().await;
    let response = app.post("/orders").json(&order_request).send().await;
    assert_eq!(response.status(), 201);
}
```

### 9. Complex Test Organization (HIGH)

Within a test file, each struct impl or function gets its own dedicated test submodule when complex.

```rust
// tests/unit/domain/user.rs
use myproject::domain::user::User;

mod new {
    use super::*;
    
    #[test]
    fn test_new_creates_user_with_given_name() {
        let user = User::new("Alice");
        assert_eq!(user.name, "Alice");
    }
    
    #[test]
    fn test_new_generates_unique_id() {
        let user1 = User::new("Alice");
        let user2 = User::new("Bob");
        assert_ne!(user1.id, user2.id);
    }
}

mod validate {
    use super::*;
    
    #[test]
    fn test_validate_returns_error_for_empty_name() {
        let result = User::validate("");
        assert!(result.is_err());
    }
}
```

### 10. Fixtures and Setup (HIGH)

Use helper functions for test fixtures. Define shared fixtures in `tests/common/mod.rs`.

```rust
// tests/common/mod.rs
pub fn create_test_user() -> User {
    User {
        id: UserId(1),
        name: "Test User".to_string(),
        email: "test@example.com".to_string(),
    }
}

pub fn create_test_product() -> Product {
    Product {
        id: ProductId(1),
        name: "Widget".to_string(),
        price_cents: 1999,
    }
}

// tests/unit/domain/order.rs
mod common;

#[test]
fn test_create_order_with_valid_data() {
    let user = common::create_test_user();
    let product = common::create_test_product();
    // ...
}
```

## Anti-Patterns to Avoid

1. **Tests in source files**: Using `#[cfg(test)]` modules in `src/` instead of `tests/` directory
2. **Manual mocks**: Creating mock implementations by hand instead of using `mockall`
3. **Testing timestamps**: Asserting exact timing instead of business outcomes
4. **Comments in tests**: Adding doc comments or inline comments to test functions
5. **Testing logging**: Mocking or asserting on logger calls
6. **Scattered test helpers**: Duplicating test fixtures across test files
7. **Vague test names**: Using generic names like `test_user` or `test_order`
8. **Flat test structure**: Not mirroring the source directory structure in tests

## Guidelines

### Test Framework
- Use `cargo test` for all tests
- Use `#[tokio::test]` for async tests
- Use `mockall` for mocking traits
- Use `wiremock` or `httpmock` for HTTP mocking

### Mocking
- Use `mockall` for trait mocking
- Use `wiremock` for HTTP mocking
- Prefer sophisticated mocking libraries over manual implementations

### Structure
- All tests in `tests/` directory, never in source files
- Organize into `unit/`, `integration/`, and `api/` subdirectories
- Mirror source directory structure: `src/domain/user.rs` → `tests/unit/domain/user.rs`
- Dedicated submodule per function when complex
- Shared fixtures in `tests/common/mod.rs`

### Naming
- Pattern: `test_<action>_<outcome>_<optional_case>`
- Be descriptive and explicit
- Name should explain what is being tested

### Preservation
- Never modify the format or logic of existing tests
- Never test logging statements

### Documentation
- Tests must not contain doc comments or inline comments
