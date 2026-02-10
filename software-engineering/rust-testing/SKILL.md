---
name: rust-testing
description: Rust testing best practices using cargo test with focus on clarity, maintainability, and hexagonal architecture testability
license: MIT
metadata:
  author: cristian.ciortea@proton.me
  version: "0.0.3"
---

# Rust Testing Skill

Version: 0.0.3

## Purpose

This skill provides guidelines for writing effective Rust tests. It focuses on clarity, maintainability, business logic validation, and testing strategies for hexagonal architecture applications.

## When to Apply

Apply these guidelines when:
- Writing or modifying Rust unit tests
- Writing or modifying Rust integration tests
- Setting up test infrastructure for new Rust projects
- Testing services and adapters in hexagonal architecture applications

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

mod get_user {
    use super::*;

    #[test]
    fn should_return_user_when_found() {
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
}
```

### 2. HTTP Mocking with wiremock (CRITICAL)

Use `wiremock` for HTTP mocking in integration tests.

```rust
use wiremock::{MockServer, Mock, ResponseTemplate};
use wiremock::matchers::{method, path};

mod fetch_user {
    use super::*;

    #[tokio::test]
    async fn should_return_user_data() {
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
}
```

### 3. Async Testing (CRITICAL)

Use `#[tokio::test]` for async tests. Ensure the tokio runtime is configured appropriately in `Cargo.toml`.

```rust
// Cargo.toml
[dev-dependencies]
tokio = { version = "1", features = ["rt-multi-thread", "macros"] }

// tests/integration_test.rs
mod perform_async_operation {
    use super::*;

    #[tokio::test]
    async fn should_complete_successfully() {
        let result = perform_async_operation().await;
        assert!(result.is_ok());
    }
}
```

### 4. Business Logic Focus (CRITICAL)

Tests should focus on business logic rather than exact timing or implementation details. Exact timestamps are not important for business requirements.

```rust
mod new {
    use super::*;

    // Bad - testing exact timestamp
    #[test]
    fn has_correct_timestamp() {
        let order = Order::new(items);
        assert_eq!(order.created_at, Utc::now()); // Flaky!
    }

    // Good - testing business logic
    #[test]
    fn should_calculate_correct_total() {
        let items = vec![
            Item { price: 1000, quantity: 2 },
            Item { price: 500, quantity: 1 },
        ];
        let order = Order::new(items);
        assert_eq!(order.total_cents, 2500);
    }
}
```

### 5. Mock Ports for Service Tests (CRITICAL)

In hexagonal architecture, services become testable by injecting mock implementations of ports (repository traits, external service traits). Create mock implementations that allow controlling return values and tracking calls.

```rust
use std::sync::Arc;
use tokio::sync::Mutex;

// Mock implementation of a repository port
#[derive(Clone, Default)]
struct MockAuthorRepository {
    authors: Arc<Mutex<Vec<Author>>>,
    create_result: Arc<Mutex<Option<Result<Author, CreateAuthorError>>>>,
}

impl MockAuthorRepository {
    fn with_create_result(result: Result<Author, CreateAuthorError>) -> Self {
        Self {
            create_result: Arc::new(Mutex::new(Some(result))),
            ..Default::default()
        }
    }
}

impl AuthorRepository for MockAuthorRepository {
    async fn create(
        &self,
        request: &CreateAuthorRequest,
    ) -> Result<Author, CreateAuthorError> {
        if let Some(result) = self.create_result.lock().await.take() {
            return result;
        }
        
        let author = Author::new(AuthorId::new(), request.name.clone());
        self.authors.lock().await.push(author.clone());
        Ok(author)
    }

    async fn find_by_id(&self, id: &AuthorId) -> Result<Option<Author>, FindError> {
        let authors = self.authors.lock().await;
        Ok(authors.iter().find(|a| a.id() == id).cloned())
    }
}

// Mock for metrics port
#[derive(Clone, Default)]
struct MockMetrics {
    success_count: Arc<Mutex<u64>>,
    failure_count: Arc<Mutex<u64>>,
}

impl AuthorMetrics for MockMetrics {
    async fn record_creation_success(&self) {
        *self.success_count.lock().await += 1;
    }

    async fn record_creation_failure(&self) {
        *self.failure_count.lock().await += 1;
    }
}

// Test using mocked ports
mod create_author {
    use super::*;

    #[tokio::test]
    async fn should_record_success_metric() {
        let repository = MockAuthorRepository::default();
        let metrics = MockMetrics::default();
        let notifier = MockNotifier::default();

        let service = AuthorService::new(repository, metrics.clone(), notifier);
        let request = CreateAuthorRequest {
            name: AuthorName::new("Test Author").unwrap(),
        };

        let result = service.create_author(&request).await;

        assert!(result.is_ok());
        assert_eq!(*metrics.success_count.lock().await, 1);
        assert_eq!(*metrics.failure_count.lock().await, 0);
    }

    #[tokio::test]
    async fn should_record_failure_metric_on_duplicate() {
        let repository = MockAuthorRepository::with_create_result(
            Err(CreateAuthorError::Duplicate { 
                name: AuthorName::new("Existing").unwrap() 
            })
        );
        let metrics = MockMetrics::default();
        let notifier = MockNotifier::default();

        let service = AuthorService::new(repository, metrics.clone(), notifier);
        let request = CreateAuthorRequest {
            name: AuthorName::new("Existing").unwrap(),
        };

        let result = service.create_author(&request).await;

        assert!(result.is_err());
        assert_eq!(*metrics.failure_count.lock().await, 1);
        assert_eq!(*metrics.success_count.lock().await, 0);
    }
}
```

### 6. Test Scope by Layer (CRITICAL)

Different layers in hexagonal architecture require different testing approaches:

- **Unit tests**: Test services with mocked ports. Focus on business logic orchestration.
- **Integration tests**: Test adapters against real external systems (databases, APIs). Focus on correct translation between domain and infrastructure.
- **End-to-end tests**: Test critical paths through the full stack. Keep these minimal and focused on happy paths.

```rust
// Unit test - service with mocked repository
mod get_author {
    use super::*;

    #[tokio::test]
    async fn should_return_not_found_when_author_missing() {
        let repository = MockAuthorRepository::default(); // Empty repository
        let service = AuthorService::new(repository, MockMetrics::default(), MockNotifier::default());

        let result = service.get_author(&AuthorId::new()).await;

        assert!(matches!(result, Err(GetAuthorError::NotFound(_))));
    }
}

// Integration test - adapter against real database
mod create {
    use super::*;

    #[tokio::test]
    async fn should_persist_author() {
        let pool = setup_test_database().await;
        let repository = SqliteAuthorRepository::new(pool);

        let request = CreateAuthorRequest {
            name: AuthorName::new("Integration Test Author").unwrap(),
        };
        let created = repository.create(&request).await.unwrap();
        let found = repository.find_by_id(created.id()).await.unwrap();

        assert_eq!(found, Some(created));
    }
}

// End-to-end test - full HTTP request
mod create_author_endpoint {
    use super::*;

    #[tokio::test]
    async fn should_return_201() {
        let app = spawn_test_app().await;
        
        let response = app.client
            .post(&format!("{}/authors", app.address))
            .json(&json!({"name": "E2E Test Author"}))
            .send()
            .await
            .unwrap();

        assert_eq!(response.status(), 201);
    }
}
```

### 7. Descriptive Naming (HIGH)

Each function or method being tested gets its own `mod` named after it. Inside the mod, test names use the pattern `should_<expected_behavior>` or `should_<expected_behavior>_when_<condition>`. The `test_` prefix is not needed because the mod already provides context. The full path reads naturally: `calculate_total::should_return_zero_for_empty_cart`.

Three levels of nesting depending on context:
- **Standalone function** (e.g. `do_periods_overlap`): one mod named after the function, test cases inside
- **Single struct per file** (e.g. `order.rs`): function mods at top level (the file already represents the struct)
- **Multiple structs per file** (e.g. `salaries.rs`): struct mod → function mod → test cases (see Section 14)

```rust
// Good examples - each function gets its own mod
mod do_periods_overlap {
    use super::*;

    #[test]
    fn should_return_false_when_arguments_are_not_datetimes() {
        // ...
    }

    #[test]
    fn should_return_true_when_periods_intersect() {
        // ...
    }
}

mod upload_image_from_bytes {
    use super::*;

    #[test]
    fn should_return_the_overwritten_public_url() {
        // ...
    }
}

mod calculate_total {
    use super::*;

    #[test]
    fn should_return_zero_for_empty_cart() {
        // ...
    }
}
```

### 8. All Tests in tests/ Directory (CRITICAL)

All tests must be placed in the `tests/` directory. Never use `#[cfg(test)]` modules in source files. This provides clear separation between production code and test code, and makes test coverage easier to track.

```
src/
├── main.rs
├── domain.rs                # mod domain { ... }
├── domain/
│   └── salaries.rs
├── application.rs           # mod application { ... }
├── application/
│   └── salary_service.rs
├── infrastructure.rs        # mod infrastructure { ... }
└── infrastructure/
    └── db.rs

tests/
├── unit.rs                  # Module entry point for unit tests
├── unit/
│   ├── domain/
│   │   └── salaries.rs      # Tests for src/domain/salaries.rs
│   └── application/
│       └── salary_service.rs # Service tests with mocked ports
├── integration.rs           # Module entry point for integration tests
├── integration/
│   └── infrastructure/
│       └── db.rs            # Adapter tests against real database
├── api.rs                   # Module entry point for API tests
├── api/
│   ├── conftest.rs          # Shared setup/teardown for API tests
│   ├── health.rs
│   └── salaries.rs
├── support.rs               # Exposes infra and fixtures modules
└── support/
    ├── infra.rs             # Docker, TestDatabase, Connection Pooling
    └── fixtures.rs          # Factories (create_*) and Seeding (save_*)
```

### 9. Module Entry Point Files (CRITICAL)

Each test category requires a module entry point file (`unit.rs`, `integration.rs`, `api.rs`) that declares its submodules. This is how Rust discovers and compiles the test files.

```rust
// tests/unit.rs
mod unit {
    mod domain {
        mod salaries;
    }

    mod application {
        mod salary_service;
    }
}
```

```rust
// tests/integration.rs
mod integration {
    mod infrastructure {
        mod db;
    }
}
```

```rust
// tests/api.rs
mod api {
    mod conftest;
    mod health;
    mod salaries;
}
```

### 10. Test File Naming Convention (CRITICAL)

Test files mirror the source file name exactly — no `_test` suffix. The `tests/` directory and the subdirectory category (`unit/`, `integration/`, `api/`) already provide the test context. Adding a `_test` suffix is redundant and unidiomatic in Rust.

```
tests/
├── unit/
│   ├── domain/
│   │   └── salaries.rs         # Good: mirrors src/domain/salaries.rs
│   └── application/
│       └── salary_service.rs   # Good: mirrors src/application/salary_service.rs
├── api/
│   ├── conftest.rs             # Exception: shared config
│   └── health.rs               # Good: no _test suffix
```

### 11. Test Directory Structure Mirrors Source (CRITICAL)

The test directory structure must mirror the source directory structure. Tests for `src/infrastructure/db.rs` go in `tests/unit/infrastructure/db.rs`.

```rust
// tests/unit/infrastructure/db.rs
use myproject::infrastructure::db::DatabaseConnection;

mod new_pool {
    use super::*;

    #[test]
    fn should_create_connections() {
        let pool = DatabaseConnection::new_pool(5);
        assert_eq!(pool.size(), 5);
    }
}

mod from_config {
    use super::*;

    #[test]
    fn should_return_error_for_invalid_config() {
        let result = DatabaseConnection::from_config(&InvalidConfig::default());
        assert!(result.is_err());
    }
}
```

### 12. Test Categories (HIGH)

Organize tests into categories:

- **unit/**: Tests for individual functions, structs, and services with mocked dependencies
- **integration/**: Tests for adapters against real external systems (databases, APIs)
- **api/**: End-to-end tests that exercise the full API against a running server

```rust
// tests/unit/domain/order.rs - Unit test for domain logic
mod new {
    use super::*;

    #[test]
    fn should_calculate_total_correctly() {
        let order = Order::new(vec![item1, item2]);
        assert_eq!(order.total_cents, 2500);
    }
}

// tests/unit/application/order_service.rs - Unit test for service with mocked ports
mod create_order {
    use super::*;

    #[tokio::test]
    async fn should_validate_inventory() {
        let repository = MockOrderRepository::default();
        let inventory = MockInventoryService::with_available_stock(10);
        let service = OrderService::new(repository, inventory);

        let result = service.create_order(&order_request).await;

        assert!(result.is_ok());
    }
}

// tests/integration/persistence/sqlite_order_repository.rs - Integration test for adapter
mod save {
    use super::*;

    #[tokio::test]
    async fn should_persist_and_retrieve_order() {
        let pool = setup_test_database().await;
        let repository = SqliteOrderRepository::new(pool);

        let order = create_test_order();
        repository.save(&order).await.unwrap();
        let found = repository.find_by_id(order.id()).await.unwrap();

        assert_eq!(found, Some(order));
    }
}

// tests/api/orders.rs - End-to-end API test
mod create_order_endpoint {
    use super::*;

    #[tokio::test]
    async fn should_return_201() {
        let client = reqwest::Client::new();
        let response = client
            .post(format!("{}/orders", LOCALHOST))
            .json(&order_request)
            .send()
            .await
            .expect("Failed to send request");
        assert_eq!(response.status(), 201);
    }
}
```

### 13. API Test Configuration with conftest.rs (HIGH)

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
// tests/api/health.rs
use super::conftest::LOCALHOST;

mod health_endpoint {
    use super::*;

    #[tokio::test]
    async fn should_return_200() {
        let client = reqwest::Client::new();
        let response = client
            .get(format!("{}/health", LOCALHOST))
            .send()
            .await
            .expect("Failed to send request");
        assert_eq!(response.status(), 200);
    }
}
```

### 14. Complex Test Organization (HIGH)

Within a test file, each struct or type gets its own dedicated test submodule, and each function being tested gets a nested submodule within it. This provides clear organization when testing multiple related types in one file.

```rust
// tests/unit/domain/salaries.rs
use myproject::domain::models::salaries::{Currency, Income, IncomeType, Salary};

mod income {
    use super::*;

    mod new {
        use super::*;

        #[test]
        fn should_create_from_valid_string() {
            let result = Income::new(Some("5000"));
            assert!(result.is_ok());
        }

        #[test]
        fn should_fail_when_negative() {
            let result = Income::new(Some("-100"));
            assert!(result.is_err());
        }
    }
}

mod income_type {
    use super::*;

    mod new {
        use super::*;

        #[test]
        fn should_accept_net_lowercase() {
            let result = IncomeType::new(Some("net"));
            assert!(result.is_ok());
        }

        #[test]
        fn should_fail_when_invalid() {
            let result = IncomeType::new(Some("gross"));
            assert!(result.is_err());
        }
    }
}

mod currency {
    use super::*;

    mod new {
        use super::*;

        #[test]
        fn should_accept_dollar_lowercase() {
            let result = Currency::new(Some("dollar"));
            assert!(result.is_ok());
        }
    }
}

mod salary {
    use super::*;

    mod new {
        use super::*;

        #[test]
        fn should_create_with_all_required_fields() {
            let result = Salary::new(Some("5000"), Some("net"), Some("ron"), None, None);
            assert!(result.is_ok());
        }
    }
}
```

### 15. The Support Module Pattern (HIGH)

Use a `tests/support/` folder instead of a single `common.rs` file. This separates infrastructure concerns (Docker, databases, connection pools) from domain data concerns (factories, seeding), and scales cleanly as the test suite grows.

```
tests/
├── integration_schedule.rs
├── integration_backup.rs
├── support.rs           // Exposes the modules below
└── support/
    ├── infra.rs         // Docker, TestDatabase, Connection Pooling
    └── fixtures.rs      // Factories (create_*) and Seeding (save_*)
```

**`tests/support/infra.rs`** — manages the physical world. It doesn't know what a "Schedule" is; it only knows about Postgres, Docker, and ports. If you switch from Docker to a local DB, or change connection pool settings, you only touch this file.

```rust
// tests/support/infra.rs
use testcontainers::{clients::Cli, images::postgres::Postgres, Container};
use sqlx::PgPool;

pub struct TestDatabase {
    pub pool: PgPool,
    _container: Container<'static, Postgres>,
}

impl TestDatabase {
    pub async fn new() -> Self {
        let docker = Cli::default();
        let container = docker.run(Postgres::default());
        let port = container.get_host_port_ipv4(5432);
        let url = format!("postgres://postgres:postgres@localhost:{}/test", port);

        let pool = PgPool::connect(&url).await.unwrap();
        sqlx::migrate!().run(&pool).await.unwrap();

        Self { pool, _container: container }
    }

    pub async fn truncate_all(&self) {
        sqlx::query("TRUNCATE schedules, backups CASCADE")
            .execute(&self.pool)
            .await
            .unwrap();
    }
}
```

**`tests/support/fixtures.rs`** — manages domain state. Contains factories (`create_*`) for building domain objects with sensible defaults, and seeding functions (`save_*`) that persist prerequisite data through a `TestDatabase`. These functions require a running DB (provided by infra), but their logic is about business rules (defaulting fields, linking foreign keys).

```rust
// tests/support/fixtures.rs
use crate::support::infra::TestDatabase;

// Factories — build domain objects in memory
pub fn create_test_schedule() -> Schedule {
    Schedule {
        id: ScheduleId::new(),
        name: "Test Schedule".to_string(),
        cron: "0 0 * * *".to_string(),
    }
}

pub fn create_test_backup(schedule_id: &ScheduleId) -> Backup {
    Backup {
        id: BackupId::new(),
        schedule_id: schedule_id.clone(),
        status: BackupStatus::Pending,
    }
}

// Seeding — persist prerequisite data into the database
pub async fn save_prerequisite_schedule(db: &TestDatabase) -> Schedule {
    let schedule = create_test_schedule();
    sqlx::query("INSERT INTO schedules (id, name, cron) VALUES ($1, $2, $3)")
        .bind(&schedule.id)
        .bind(&schedule.name)
        .bind(&schedule.cron)
        .execute(&db.pool)
        .await
        .unwrap();
    schedule
}

pub async fn save_prerequisite_backup(db: &TestDatabase, schedule_id: &ScheduleId) -> Backup {
    let backup = create_test_backup(schedule_id);
    sqlx::query("INSERT INTO backups (id, schedule_id, status) VALUES ($1, $2, $3)")
        .bind(&backup.id)
        .bind(&backup.schedule_id)
        .bind(&backup.status)
        .execute(&db.pool)
        .await
        .unwrap();
    backup
}
```

**`tests/support.rs`** — exposes the sub-modules.

```rust
// tests/support.rs
pub mod infra;
pub mod fixtures;
```

**Usage in tests:**

```rust
// tests/integration_schedule.rs
mod support;

use support::infra::TestDatabase;
use support::fixtures::{save_prerequisite_schedule, create_test_backup};

mod create_backup {
    use super::*;

    #[tokio::test]
    async fn should_persist_backup_for_existing_schedule() {
        let db = TestDatabase::new().await;
        let schedule = save_prerequisite_schedule(&db).await;

        let backup = create_test_backup(schedule.id());
        let repository = PgBackupRepository::new(db.pool.clone());
        let saved = repository.save(&backup).await.unwrap();

        assert_eq!(saved.schedule_id(), schedule.id());
    }
}
```

## Anti-Patterns to Avoid

1. **Tests in source files**: Using `#[cfg(test)]` modules in `src/` instead of `tests/` directory
2. **Missing module entry points**: Forgetting to create `unit.rs`, `integration.rs`, or `api.rs` to declare submodules
3. **Using _test.rs suffix**: Adding a `_test` suffix to test files — test files should mirror the source file name exactly since `tests/` already provides context
4. **Testing timestamps**: Asserting exact timing instead of business outcomes
5. **Comments in tests**: Adding doc comments or inline comments to test functions
6. **Testing logging**: Mocking or asserting on logger calls
7. **Scattered test helpers**: Duplicating test fixtures and mock implementations across test files
8. **Overloaded common.rs**: Putting infrastructure (Docker, DB pools) and domain fixtures (factories, seeding) in a single `common.rs` file — use `tests/support/` with separate `infra.rs` and `fixtures.rs` instead
9. **Vague test names**: Using generic names like `test_user` or `test_order`
10. **Flat test structure**: Not mirroring the source directory structure in tests
11. **Missing conftest.rs**: Not centralizing API test setup/teardown
12. **Testing services against real databases**: Unit tests for services should use mocked ports, not real adapters
13. **Skipping adapter integration tests**: Adapters must be tested against real external systems to verify correct translation
14. **Over-relying on end-to-end tests**: Keep API tests minimal and focused on critical paths; most logic should be tested at unit level

## Guidelines

### Test Framework
- Use `cargo test` for all tests
- Use `#[tokio::test]` for async tests
- Use `mockall` for mocking traits
- Use `wiremock` or `httpmock` for HTTP mocking
- Use `ctor`/`dtor` for API test server lifecycle

### Mocking Strategy
- Use `mockall` for simple trait mocking with expectations
- Create custom mock implementations for ports when you need stateful behavior
- Mock implementations should allow controlling return values and tracking calls
- Place shared mock implementations in `tests/support/` (see Section 15)

### Test Scope by Layer
- **Unit tests**: Test domain logic and services with mocked ports
- **Integration tests**: Test adapters against real external systems (databases, message queues)
- **API tests**: Test critical end-to-end paths only; keep minimal
- Most business logic should be tested at the unit level with mocked dependencies

### Structure
- All tests in `tests/` directory, never in source files
- Create module entry point files: `tests/unit.rs`, `tests/integration.rs`, `tests/api.rs`
- Test files mirror source file names exactly — no `_test` suffix
- Organize into `unit/`, `integration/`, and `api/` subdirectories
- Mirror source directory structure: `src/domain/salaries.rs` → `tests/unit/domain/salaries.rs`
- Mirror source directory structure for adapters: `src/infrastructure/db.rs` → `tests/integration/infrastructure/db.rs`
- Dedicated submodule per struct/type when testing multiple types in one file
- Shared test infrastructure in `tests/support/infra.rs`, fixtures and factories in `tests/support/fixtures.rs`
- API test configuration in `tests/api/conftest.rs`

### Naming
- Each function/method gets its own `mod` named after it
- Inside the mod, test names use `should_<expected_behavior>` or `should_<expected_behavior>_when_<condition>`
- No `test_` prefix needed — the mod provides context
- Full path reads naturally: `create_order::should_validate_inventory`
- Standalone function: one mod, test cases inside
- Single-struct file: function mods at top level (file = struct context)
- Multi-struct file: struct mod → function mod → test cases (see Section 14)

### Hexagonal Architecture Testing
- Services are tested with mocked ports (repositories, external services)
- Adapters are tested against real external systems in integration tests
- Handlers are tested via API tests or with mocked services
- Domain logic is tested in isolation without any mocking

### Preservation
- Never modify the format or logic of existing tests
- Never test logging statements

### Documentation
- Tests must not contain doc comments or inline comments
