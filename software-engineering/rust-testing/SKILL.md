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
│   └── salaries.rs
└── infrastructure/
    └── db.rs

tests/
├── unit.rs                  # Module entry point for unit tests
├── unit/
│   ├── domain/
│   │   └── salaries_test.rs # Tests for src/domain/salaries.rs
│   └── salary_calculation_service_test.rs
├── api.rs                   # Module entry point for API tests
├── api/
│   ├── conftest.rs          # Shared setup/teardown for API tests
│   ├── health_test.rs
│   └── salaries_test.rs
└── common/
    └── mod.rs               # Shared test utilities
```

### 7. Module Entry Point Files (CRITICAL)

Each test category requires a module entry point file (`unit.rs`, `api.rs`) that declares its submodules. This is how Rust discovers and compiles the test files.

```rust
// tests/unit.rs
mod unit {
    mod salary_calculation_service_test;

    mod domain {
        mod salaries_test;
    }
}
```

```rust
// tests/api.rs
mod api {
    mod conftest;
    mod health_test;
    mod salaries_test;
}
```

### 8. Test File Naming Convention (CRITICAL)

All test files must end with `_test.rs` suffix. This makes it immediately clear which files contain tests.

```
tests/
├── unit/
│   ├── domain/
│   │   └── salaries_test.rs    # Good: _test.rs suffix
│   └── user_service_test.rs    # Good: _test.rs suffix
├── api/
│   ├── conftest.rs             # Exception: shared config
│   └── health_test.rs          # Good: _test.rs suffix
```

### 9. Test Directory Structure Mirrors Source (CRITICAL)

The test directory structure must mirror the source directory structure. Tests for `src/infrastructure/db.rs` go in `tests/unit/infrastructure/db_test.rs`.

```rust
// tests/unit/infrastructure/db_test.rs
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

### 10. Test Categories (HIGH)

Organize tests into categories:

- **unit/**: Tests for individual functions and structs in isolation
- **api/**: End-to-end tests that exercise the full API against a running server

```rust
// tests/unit/domain/order_test.rs - Unit test
#[test]
fn test_order_calculates_total_correctly() {
    let order = Order::new(vec![item1, item2]);
    assert_eq!(order.total_cents, 2500);
}

// tests/api/orders_test.rs - API test
#[tokio::test]
async fn test_create_order_endpoint_returns_201() {
    let client = reqwest::Client::new();
    let response = client
        .post(format!("{}/orders", LOCALHOST))
        .json(&order_request)
        .send()
        .await
        .expect("Failed to send request");
    assert_eq!(response.status(), 201);
}
```

### 11. API Test Configuration with conftest.rs (HIGH)

Use a `conftest.rs` file in the `api/` directory for shared API test setup and teardown. Use `ctor` and `dtor` for server lifecycle management.

```rust
// tests/api/conftest.rs
use ctor::{ctor, dtor};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::thread;
use std::time::Duration;

pub const LOCALHOST: &str = "http://localhost:8000";

static SERVER_PROCESS: Mutex<Option<Child>> = Mutex::new(None);

fn start_server_process() -> Child {
    let binary_path = std::env::current_exe()
        .expect("Failed to get test binary path")
        .parent()
        .and_then(|path| path.parent())
        .expect("Failed to get target/debug directory")
        .join("myproject-backend");

    Command::new(binary_path)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start test server")
}

fn wait_for_server_ready(process: &mut Child) {
    let client = reqwest::blocking::Client::new();
    let max_attempts = 30;

    for attempt in 1..=max_attempts {
        if let Ok(response) = client.get(&format!("{}/health", LOCALHOST)).send() {
            if response.status().is_success() {
                println!("Test server ready after {} attempts", attempt);
                return;
            }
        }
        thread::sleep(Duration::from_millis(500));
    }
    panic!("Test server failed to become ready");
}

#[ctor]
fn setup_api_tests() {
    let mut server_process = start_server_process();
    wait_for_server_ready(&mut server_process);
    *SERVER_PROCESS.lock().unwrap() = Some(server_process);
}

#[dtor]
fn teardown_api_tests() {
    if let Some(mut server_process) = SERVER_PROCESS.lock().unwrap().take() {
        let _ = server_process.kill();
        let _ = server_process.wait();
    }
}
```

```rust
// tests/api/health_test.rs
use super::conftest::LOCALHOST;

#[tokio::test]
async fn test_health_endpoint_returns_200() {
    let client = reqwest::Client::new();
    let response = client
        .get(format!("{}/health", LOCALHOST))
        .send()
        .await
        .expect("Failed to send request");
    assert_eq!(response.status(), 200);
}
```

### 12. Complex Test Organization (HIGH)

Within a test file, each struct or type gets its own dedicated test submodule. This provides clear organization when testing multiple related types in one file.

```rust
// tests/unit/domain/salaries_test.rs
use myproject::domain::models::salaries::{Currency, Income, IncomeType, Salary};

mod income {
    use super::*;

    #[test]
    fn should_create_income_from_valid_string() {
        let result = Income::new(Some("5000"));
        assert!(result.is_ok());
    }

    #[test]
    fn should_fail_when_income_is_negative() {
        let result = Income::new(Some("-100"));
        assert!(result.is_err());
    }
}

mod income_type {
    use super::*;

    #[test]
    fn should_create_net_income_type_lowercase() {
        let result = IncomeType::new(Some("net"));
        assert!(result.is_ok());
    }

    #[test]
    fn should_fail_when_income_type_is_invalid() {
        let result = IncomeType::new(Some("gross"));
        assert!(result.is_err());
    }
}

mod currency {
    use super::*;

    #[test]
    fn should_create_dollar_currency_lowercase() {
        let result = Currency::new(Some("dollar"));
        assert!(result.is_ok());
    }
}

mod salary {
    use super::*;

    #[test]
    fn should_create_salary_with_all_required_fields() {
        let result = Salary::new(Some("5000"), Some("net"), Some("ron"), None, None);
        assert!(result.is_ok());
    }
}
```

### 13. Fixtures and Setup (HIGH)

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

// tests/unit/domain/order_test.rs
mod common;

#[test]
fn test_create_order_with_valid_data() {
    let user = common::create_test_user();
    // ...
}
```

## Anti-Patterns to Avoid

1. **Tests in source files**: Using `#[cfg(test)]` modules in `src/` instead of `tests/` directory
2. **Missing module entry points**: Forgetting to create `unit.rs` or `api.rs` to declare submodules
3. **Missing _test.rs suffix**: Not using the `_test.rs` suffix for test files
4. **Manual mocks**: Creating mock implementations by hand instead of using `mockall`
5. **Testing timestamps**: Asserting exact timing instead of business outcomes
6. **Comments in tests**: Adding doc comments or inline comments to test functions
7. **Testing logging**: Mocking or asserting on logger calls
8. **Scattered test helpers**: Duplicating test fixtures across test files
9. **Vague test names**: Using generic names like `test_user` or `test_order`
10. **Flat test structure**: Not mirroring the source directory structure in tests
11. **Missing conftest.rs**: Not centralizing API test setup/teardown

## Guidelines

### Test Framework
- Use `cargo test` for all tests
- Use `#[tokio::test]` for async tests
- Use `mockall` for mocking traits
- Use `wiremock` or `httpmock` for HTTP mocking
- Use `ctor`/`dtor` for API test server lifecycle

### Mocking
- Use `mockall` for trait mocking
- Use `wiremock` for HTTP mocking
- Prefer sophisticated mocking libraries over manual implementations

### Structure
- All tests in `tests/` directory, never in source files
- Create module entry point files: `tests/unit.rs`, `tests/api.rs`
- All test files must end with `_test.rs` suffix
- Organize into `unit/` and `api/` subdirectories
- Mirror source directory structure: `src/domain/salaries.rs` → `tests/unit/domain/salaries_test.rs`
- Dedicated submodule per struct/type when testing multiple types in one file
- Shared fixtures in `tests/common/mod.rs`
- API test configuration in `tests/api/conftest.rs`

### Naming
- Pattern: `should_<expected_behavior>_when_<condition>` or `test_<action>_<outcome>_<optional_case>`
- Be descriptive and explicit
- Name should explain what is being tested

### Preservation
- Never modify the format or logic of existing tests
- Never test logging statements

### Documentation
- Tests must not contain doc comments or inline comments
