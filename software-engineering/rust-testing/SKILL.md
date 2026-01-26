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

### 6. Test Module Organization (HIGH)

Place unit tests in a `#[cfg(test)]` module at the bottom of the source file. Place integration tests in the `tests/` directory.

```rust
// src/user.rs
pub struct User {
    pub id: UserId,
    pub name: String,
}

impl User {
    pub fn new(name: &str) -> Self {
        Self {
            id: UserId::generate(),
            name: name.to_string(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_new_creates_user_with_given_name() {
        let user = User::new("Alice");
        assert_eq!(user.name, "Alice");
    }
}
```

### 7. Complex Test Organization (HIGH)

Each struct impl or function gets its own dedicated test submodule when complex.

```rust
#[cfg(test)]
mod tests {
    use super::*;
    
    mod new {
        use super::*;
        
        #[test]
        fn test_new_creates_user_with_given_name() {
            // ...
        }
        
        #[test]
        fn test_new_generates_unique_id() {
            // ...
        }
    }
    
    mod validate {
        use super::*;
        
        #[test]
        fn test_validate_returns_error_for_empty_name() {
            // ...
        }
    }
}
```

### 8. Integration Test Organization (HIGH)

Integration tests go in `tests/` directory with one file per feature area.

```
tests/
├── user_api.rs       # User API integration tests
├── order_api.rs      # Order API integration tests
├── auth.rs           # Authentication integration tests
└── common/
    └── mod.rs        # Shared test utilities
```

### 9. Fixtures and Setup (HIGH)

Use helper functions for test fixtures. Define shared fixtures in a common test utilities module.

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

// tests/order_api.rs
mod common;

#[test]
fn test_create_order_with_valid_data() {
    let user = common::create_test_user();
    let product = common::create_test_product();
    // ...
}
```

## Anti-Patterns to Avoid

1. **Manual mocks**: Creating mock implementations by hand instead of using `mockall`
2. **Testing timestamps**: Asserting exact timing instead of business outcomes
3. **Comments in tests**: Adding doc comments or inline comments to test functions
4. **Testing logging**: Mocking or asserting on logger calls
5. **Scattered test helpers**: Duplicating test fixtures across test files
6. **Vague test names**: Using generic names like `test_user` or `test_order`

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
- Unit tests in `#[cfg(test)]` module at bottom of source file
- Integration tests in `tests/` directory
- One test file per feature area for integration tests
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
