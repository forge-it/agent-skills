---
name: rust-testing
description: Guidelines for writing effective Rust tests. Use when writing or modifying Rust unit, integration, or end-to-end (API) tests.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.9"
---

# Rust Testing Skill

## Purpose

This skill provides guidelines for writing effective Rust tests. It focuses on clarity, maintainability, business logic validation, and testing strategies for hexagonal architecture applications, across three categories: unit, integration, and end-to-end (e2e).

## When to Apply

Apply these guidelines when:
- Writing or modifying Rust unit tests
- Writing or modifying Rust integration tests
- Writing or modifying Rust end-to-end (API) tests
- Setting up test infrastructure for new Rust projects
- Testing services and adapters in hexagonal architecture applications

## Core Principles

### 1. Mocking — Unit Tests Only (CRITICAL)

Mocking belongs to **unit tests**. Prefer **hand-written, stateful mock implementations of ports** (Section 5) — they fit hexagonal ports naturally, work with native `async fn` traits, and let tests control return values and track calls. `mockall` is acceptable for simple, stateless expectation-style mocks; `wiremock` or `httpmock` stand up fake HTTP endpoints for client-adapter unit tests (Section 2). Whatever the tool, mock definitions live in `tests/unit/support/mocks.rs`, never at the top of a test file (Section 16).

**Never mock in integration tests.** Integration tests exist precisely to exercise the *real* external system — a database, message broker, gRPC server, object store. A mock there proves nothing the unit test did not already prove, and it hides the real wiring, serialization, and translation bugs integration tests are meant to catch. If a "real" dependency is unavailable, the test belongs at the unit level (with a mock) or at the end-to-end level (against the full stack) — not as a mock wearing an integration test's name. See Section 6.

```rust
// tests/unit/support/mocks.rs — a mockall mock for a simple stateless port
use mockall::mock;

mock! {
    pub UserRepository {}

    impl UserRepository for UserRepository {
        async fn find_by_id(&self, id: UserId) -> Result<User, FindUserError>;
        async fn save(&self, user: &User) -> Result<(), SaveUserError>;
    }
}
```

```rust
// tests/unit/application/user_service.rs
use mockall::predicate::eq;

use super::super::support::mocks::MockUserRepository;

mod get_user {
    use super::*;

    #[tokio::test]
    async fn should_return_user_when_found() {
        let mut repository = MockUserRepository::new();
        repository
            .expect_find_by_id()
            .with(eq(UserId(123)))
            .returning(|_| Ok(User { id: UserId(123), name: "Alice".into() }));

        let service = UserService::new(repository);

        let user = service.get_user(UserId(123)).await.expect("user should be found");

        assert_eq!(user.name, "Alice");
    }
}
```

### 2. HTTP Mocking with wiremock — Unit Tests Only (CRITICAL)

Use `wiremock` (or `httpmock`) to **unit-test an outbound HTTP client adapter** in isolation: it stands up a fake endpoint so the adapter's request building and response parsing can be asserted without the real service. This is a *unit* test — the real service is absent. The **integration** test of that same adapter runs against the real external service, never a fake (see Section 6).

```rust
// tests/unit/infrastructure/api_client.rs
use serde_json::json;
use wiremock::matchers::{method, path};
use wiremock::{Mock, MockServer, ResponseTemplate};

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

        let user = client.fetch_user(123).await.expect("fetch_user should succeed");

        assert_eq!(user.name, "John");
    }
}
```

### 3. Async Testing (CRITICAL)

Use `#[tokio::test]` for async tests. The dev-dependency needs the `macros` and `rt-multi-thread` features:

```toml
# Cargo.toml
[dev-dependencies]
tokio = { version = "1", features = ["macros", "rt-multi-thread"] }
```

`#[tokio::test]` runs on a single-threaded current-thread runtime by default, which is correct for most tests. Use `#[tokio::test(flavor = "multi_thread")]` only when the test genuinely needs concurrent workers (e.g. the code under test spawns tasks that must run in parallel with the test body).

```rust
// tests/unit/application/sync_service.rs
use myproject::application::sync::service::SyncService;

use super::super::support::mocks::MockSyncGateway;

mod synchronize {
    use super::*;

    #[tokio::test]
    async fn should_succeed_when_gateway_accepts_the_batch() {
        let service = SyncService::new(MockSyncGateway::default());

        service.synchronize().await.expect("synchronize should succeed");
    }
}
```

### 4. Business Logic Focus (CRITICAL)

Tests should focus on business logic rather than exact timing or implementation details. Exact timestamps are not important for business requirements.

```rust
mod new {
    use super::*;

    // Bad - asserting wall-clock time is inherently flaky
    #[test]
    fn has_correct_timestamp() {
        let order = Order::new(items);
        assert_eq!(order.created_at, Utc::now());
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

When a timestamp **is** part of the behaviour under test, do not assert against `Utc::now()` — inject a clock port and control it:

```rust
mod new_at {
    use super::*;

    #[test]
    fn should_stamp_created_at_from_the_injected_clock() {
        let clock = FixedClock::at_noon();

        let order = Order::new_at(vec![], &clock);

        assert_eq!(order.created_at, clock.now());
    }
}
```

### 5. Mock Ports for Service Tests (CRITICAL)

In hexagonal architecture, services become testable by injecting mock implementations of ports (repository traits, external service traits). The **canonical pattern is a hand-written mock**: a small struct that allows controlling return values and tracking calls. Hand-written mocks live in `tests/unit/support/mocks.rs` (Section 15) — a test file never defines them at module scope (Section 16). Reach for `mockall` instead only when the mock is stateless and purely expectation-based (Section 1).

```rust
// tests/unit/support/mocks.rs — the canonical home for hand-written port mocks
use std::sync::Arc;

use tokio::sync::Mutex;

#[derive(Clone, Default)]
pub struct MockAuthorRepository {
    pub authors: Arc<Mutex<Vec<Author>>>,
    pub create_result: Arc<Mutex<Option<Result<Author, CreateAuthorError>>>>,
}

impl MockAuthorRepository {
    pub fn with_create_result(result: Result<Author, CreateAuthorError>) -> Self {
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

    async fn find_by_id(&self, id: &AuthorId) -> Result<Option<Author>, FindAuthorError> {
        let authors = self.authors.lock().await;
        Ok(authors.iter().find(|author| author.id() == id).cloned())
    }
}

#[derive(Clone, Default)]
pub struct MockMetrics {
    pub success_count: Arc<Mutex<u64>>,
    pub failure_count: Arc<Mutex<u64>>,
}

impl AuthorMetrics for MockMetrics {
    async fn record_creation_success(&self) {
        *self.success_count.lock().await += 1;
    }

    async fn record_creation_failure(&self) {
        *self.failure_count.lock().await += 1;
    }
}

#[derive(Clone, Default)]
pub struct MockNotifier {
    pub notified_authors: Arc<Mutex<Vec<AuthorId>>>,
}

impl AuthorNotifier for MockNotifier {
    async fn author_created(&self, author: &Author) {
        self.notified_authors.lock().await.push(author.id().clone());
    }
}
```

```rust
// tests/unit/application/author_service.rs
use super::super::support::mocks::{MockAuthorRepository, MockMetrics, MockNotifier};

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

        service.create_author(&request).await.expect("create_author should succeed");

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

        assert!(matches!(result, Err(CreateAuthorError::Duplicate { .. })));
        assert_eq!(*metrics.failure_count.lock().await, 1);
        assert_eq!(*metrics.success_count.lock().await, 0);
    }
}
```

### 6. Test Scope by Layer (CRITICAL)

Different layers in hexagonal architecture require different testing approaches:

- **Unit tests**: Test domain logic and services with mocked ports. Focus on business logic orchestration.
- **Integration tests**: Test against real external systems (databases, message brokers, gRPC servers, object stores) — **never mocks or fakes**. The typical subject is an adapter (correct translation between domain and infrastructure). An application service wired to real adapters is also a legitimate integration test when the behaviour under test spans the service and the infrastructure together — those live under `tests/integration/application/`.
- **End-to-end tests (e2e)**: Test critical paths through the full stack. The `api/` subdomain exercises HTTP request/response through the real in-process server (Section 13). Keep e2e minimal and focused on happy paths.

```rust
// Unit test - service with mocked repository
mod get_author {
    use super::*;

    #[tokio::test]
    async fn should_return_not_found_when_author_missing() {
        let repository = MockAuthorRepository::default();
        let service = AuthorService::new(repository, MockMetrics::default(), MockNotifier::default());

        let result = service.get_author(&AuthorId::new()).await;

        assert!(matches!(result, Err(GetAuthorError::NotFound(_))));
    }
}

// Integration test - adapter against the real database (per-test database, Section 17)
mod create {
    use super::*;

    #[tokio::test]
    async fn should_persist_author() {
        let test_database = TestDatabase::new().await;
        let repository = PostgresAuthorRepository::new(test_database.pool().clone());
        let request = CreateAuthorRequest {
            name: AuthorName::new(unique_name("author-create")).unwrap(),
        };

        let created = repository.create(&request).await.unwrap();
        let found = repository.find_by_id(created.id()).await.unwrap();

        assert_eq!(found, Some(created));

        test_database.teardown().await;
    }
}

// End-to-end API test - full HTTP request against the in-process server (Section 13)
mod create_author_endpoint {
    use super::*;

    #[tokio::test]
    async fn should_return_201() {
        let test_app = TestApp::new().await;

        let response = test_app.client
            .post(test_app.url("/authors"))
            .json(&json!({"name": "E2E Test Author"}))
            .send()
            .await
            .unwrap();

        assert_eq!(response.status(), 201);

        test_app.teardown().await;
    }
}
```

### 7. Descriptive Naming (HIGH)

Each function or method being tested gets its own `mod` named after it. Inside the mod, test names use the pattern `should_<expected_behavior>` or `should_<expected_behavior>_when_<condition>`. The `test_` prefix must not be used — the mod already provides context. The full path reads naturally: `calculate_total::should_return_zero_for_empty_cart`.

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

All tests must be placed in the `tests/` directory. Never use `#[cfg(test)]` modules in source files. This provides clear separation between production code and test code.

This layout has a prerequisite: **the crate must expose a library target** (`src/lib.rs`), because external test binaries can only import a library — a binary-only crate (`src/main.rs` alone) cannot be tested from `tests/` at all. Keep `src/main.rs` a thin wrapper over the library. Everything under test must be reachable through the crate's public surface — the same `pub` visibility rule rust-project-structure defines for the concept surface (`pub` = other layers, `tests/`, downstream crates).

```
src/
├── lib.rs                   # Library target — tests/ can only import a library
├── main.rs                  # Thin binary wrapper over the library
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
├── common/                  # Cross-category helpers shared by integration and e2e
│   ├── mod.rs               # The only mod.rs allowed under tests/ (Section 15)
│   ├── infra.rs             # #[ctor] Docker stack bring-up, TestDatabase
│   ├── builders.rs          # Service construction (build_*)
│   ├── factories.rs         # Cross-level domain object builders (create_*)
│   ├── fixtures.rs          # Cross-level prerequisite persistence (save_*)
│   └── helpers.rs           # Unique-name helpers, general utilities
├── unit.rs                  # Module entry point for unit tests
├── unit/
│   ├── support.rs           # pub mod mocks; pub mod factories; ...
│   ├── support/
│   │   └── mocks.rs         # Hand-written port mocks — unit only
│   ├── domain/
│   │   └── salaries.rs      # Tests for src/domain/salaries.rs
│   └── application/
│       └── salary_service.rs # Service tests with mocked ports
├── integration.rs           # Module entry point for integration tests
├── integration/
│   ├── support.rs           # Adds integration-specific helpers, re-exports common
│   ├── support/
│   │   └── fixtures.rs
│   ├── infrastructure/
│   │   └── db.rs            # Adapter tests against the real database
│   └── application/
│       └── backup_flow.rs   # Service-with-real-adapters tests
├── e2e.rs                   # Module entry point for end-to-end tests
└── e2e/
    └── api/                 # First e2e subdomain; workflow subdomains grow beside it
        ├── support.rs       # pub mod infra; (TestApp lives here)
        ├── support/
        │   └── infra.rs
        ├── health.rs
        └── salaries.rs
```

### 9. Module Entry Point Files (CRITICAL)

Each test category requires a module entry point file (`unit.rs`, `integration.rs`, `e2e.rs`) that declares its submodules. This is how Rust discovers and compiles the test files.

The wrapper module (`mod unit { … }`) is load-bearing: the entry point file is the crate root of its test binary, and the wrapper is what makes Rust resolve the submodule files under `tests/unit/…` instead of directly under `tests/`. Do not remove it. `mod common;` is declared without a wrapper — it resolves to `tests/common/mod.rs` — and only by the entry points that use it (integration and e2e).

```rust
// tests/unit.rs
mod unit {
    mod support;

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
mod common;

mod integration {
    mod support;

    mod infrastructure {
        mod db;
    }

    mod application {
        mod backup_flow;
    }
}
```

```rust
// tests/e2e.rs
mod common;

mod e2e {
    mod api {
        mod support;

        mod health;
        mod salaries;
    }
}
```

### 10. Test Naming Convention — No `_test` Suffix (CRITICAL)

Test files and test modules must never use a `_test` suffix. Test files mirror the source file name exactly. Test modules are named after the function or type being tested. The `tests/` directory and the subdirectory category (`unit/`, `integration/`, `e2e/`) already provide the test context. Adding a `_test` suffix is redundant and unidiomatic in Rust.

```
tests/
├── unit/
│   ├── domain/
│   │   ├── salaries.rs         # Good: mirrors src/domain/salaries.rs
│   │   └── salaries_test.rs    # Bad: never suffix with _test
│   └── application/
│       └── salary_service.rs   # Good: mirrors src/application/salary_service.rs
└── e2e/
    └── api/
        └── health.rs           # Good: no _test suffix
```

```rust
// Good — module named after the function being tested
mod calculate_total {
    use super::*;

    #[test]
    fn should_return_zero_for_empty_cart() { /* ... */ }
}

// Bad — never suffix test modules with _test
mod calculate_total_test {
    use super::*;

    #[test]
    fn should_return_zero_for_empty_cart() { /* ... */ }
}
```

### 11. Test Directory Structure Mirrors Source (CRITICAL)

The test directory structure must mirror the source directory structure, inside the category that matches the test's scope:

- Unit tests of **pure infrastructure logic** (config validation, parsing, mapping) go under `tests/unit/infrastructure/`: `src/infrastructure/config.rs` → `tests/unit/infrastructure/config.rs`.
- **Adapter tests against the real system** go under `tests/integration/infrastructure/`: `src/infrastructure/db.rs` → `tests/integration/infrastructure/db.rs` (Section 6).

```rust
// tests/unit/infrastructure/config.rs
use myproject::infrastructure::config::{ConfigError, DatabaseConfig};

mod from_env {
    use super::*;

    #[test]
    fn should_return_error_when_url_is_missing() {
        let variables = EnvVariables::default();

        let result = DatabaseConfig::from_env(&variables);

        assert!(matches!(result, Err(ConfigError::MissingUrl)));
    }
}
```

### 12. Test Categories (HIGH)

Organize tests into categories:

- **unit/**: Tests for individual functions, structs, and services with mocked dependencies. Subdirectories mirror `src/` (`domain/`, `application/`, and `infrastructure/` for pure logic).
- **integration/**: Everything that exercises real external systems — adapter tests under `integration/infrastructure/`, and application services wired to real adapters under `integration/application/`.
- **e2e/**: Full-stack tests, organized into subdomains that each own a `support/` module. `api/` (HTTP request/response through the real in-process server) is the canonical first subdomain; workflow subdomains (e.g. `backup/`, `billing/`) are added beside it as the product grows.

"API tests" and "e2e tests" are not two different categories: API tests are the `e2e/api/` subdomain. Section 6 defines what each category asserts and shows one example per category; Section 8 shows the directory layout.

### 13. End-to-End Test Harness — TestApp (HIGH)

E2E API tests run the application **in-process**: a `TestApp` struct in `tests/e2e/api/support/infra.rs` builds the real service graph on a per-test `TestDatabase`, binds the real router to **port 0** (the OS assigns a free port), and exposes a pre-configured `reqwest::Client`. Never spawn the compiled server binary from tests, and never hardcode a port — fixed ports collide across parallel tests, CI jobs, and git worktrees (Section 17).

Heavyweight side-effect executors that a workflow subdomain covers separately may be wired as no-op implementations in the API harness — the API tests assert HTTP behaviour, not the pipelines behind it.

```rust
// tests/e2e/api/support/infra.rs
// TestApp runs the real router in-process: real repositories on a per-test
// database, an OS-assigned port, and explicit teardown.
use myproject::infrastructure::api::router::build_router;

use crate::common::builders::build_services;
use crate::common::infra::TestDatabase;

pub struct TestApp {
    pub client: reqwest::Client,
    base_url: String,
    server_handle: tokio::task::JoinHandle<()>,
    test_database: TestDatabase,
}

impl TestApp {
    pub async fn new() -> Self {
        let test_database = TestDatabase::new().await;
        let services = build_services(test_database.pool().clone());

        let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let address = listener.local_addr().unwrap();
        let server_handle = tokio::spawn(async move {
            axum::serve(listener, build_router(services)).await.unwrap();
        });

        Self {
            client: reqwest::Client::new(),
            base_url: format!("http://{address}"),
            server_handle,
            test_database,
        }
    }

    pub fn url(&self, path: &str) -> String {
        format!("{}{path}", self.base_url)
    }

    pub async fn teardown(self) {
        self.server_handle.abort();
        self.test_database.teardown().await;
    }
}
```

```rust
// tests/e2e/api/health.rs
use super::support::infra::TestApp;

mod health_endpoint {
    use super::*;

    #[tokio::test]
    async fn should_return_200() {
        let test_app = TestApp::new().await;

        let response = test_app.client
            .get(test_app.url("/health"))
            .send()
            .await
            .unwrap();

        assert_eq!(response.status(), 200);

        test_app.teardown().await;
    }
}
```

Every test constructs its own `TestApp` and ends with `test_app.teardown().await` — teardown is explicit, never left to `Drop`. The shared Docker stack behind the tests (database server, object store, mail catcher) is brought up once per test binary by the `#[ctor]` in `tests/common/infra.rs` (Section 15) — `#[ctor]` is for infrastructure bring-up only, never for starting the application server.

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
            Income::new(Some("5000")).expect("income should parse from a valid string");
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
            IncomeType::new(Some("net")).expect("net should be a valid income type");
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
            Currency::new(Some("dollar")).expect("dollar should be a valid currency");
        }
    }
}

mod salary {
    use super::*;

    mod new {
        use super::*;

        #[test]
        fn should_create_with_all_required_fields() {
            Salary::new(Some("5000"), Some("net"), Some("ron"), None, None)
                .expect("salary should build from all required fields");
        }
    }
}
```

### 15. The Support Module Pattern (HIGH)

Test helpers live in two scopes; test files themselves contain only tests (Section 16).

**Scope 1 — `tests/common/`** holds the helpers shared **across categories** (integration and e2e): infrastructure bring-up (`#[ctor]` for the Docker stack, `TestDatabase`), cross-level builders, factories, and fixtures. Its entry point is `tests/common/mod.rs` — the **only** `mod.rs` allowed under `tests/` (the architecture gate enforces exactly this exception). Entry points that use it declare `mod common;` (Section 9).

```rust
// tests/common/mod.rs
pub mod builders;
pub mod factories;
pub mod fixtures;
pub mod helpers;
pub mod infra;
```

**Scope 2 — per-category `support/`** modules hold category-specific helpers: `tests/unit/support/`, `tests/integration/support/`, and one per e2e subdomain (`tests/e2e/api/support/`). A category support file may re-export from common so tests have one import surface:

```rust
// tests/integration/support/fixtures.rs
pub use crate::common::fixtures::*;

// integration-specific fixtures are added below the re-export
```

A large subtree may own a nested `support/` of its own (e.g. `tests/integration/infrastructure/gateway/source/support/`) with the same file-per-concern rules.

Within any support module, each file has a single, distinct job:

| File | Concern | Knows about... | Output |
|---|---|---|---|
| `infra.rs` | Environment | Docker stack, admin connections, `TestDatabase` | A running stack + an isolated per-test database |
| `builders.rs` | Service Construction | Application services, Adapters, Config | A configured service ready to use |
| `factories.rs` | Data Shapes | Domain Structs, Business Rules | A struct in memory |
| `fixtures.rs` | State | Factories + Infra + Repositories | A row in the actual database |
| `mocks.rs` | Test Doubles | Traits, Ports, External interfaces | Mock structs implementing traits — **unit support only** (integration uses real infra, Section 1) |
| `helpers.rs` | Test Utilities | Assertions, Conversions, Unique names | Convenience functions for test code |
| `constants.rs` | Shared Values | Test defaults, Magic strings, Limits | Reusable constants across tests |

`mocks.rs` exists **only** under `tests/unit/support/` — an integration `support/` never contains mocks:

```
tests/unit/support/
├── mocks.rs         # Hand-written port mocks (Mock*) — see Section 5
├── factories.rs
├── helpers.rs
└── constants.rs

tests/integration/support/
├── fixtures.rs      # save_* fixtures; re-exports common fixtures
├── factories.rs
├── helpers.rs
└── constants.rs     # Note: no mocks.rs — integration tests never mock
```

```rust
// tests/unit/support.rs
pub mod mocks;
pub mod factories;
pub mod helpers;
pub mod constants;
```

```rust
// tests/integration/support.rs — no mocks module
pub mod fixtures;
pub mod factories;
pub mod helpers;
pub mod constants;
```

**infra.rs — shared stack + per-test database.** The Docker stack (compose file with env-substitutable host ports) starts once per test binary via `#[ctor]`; each test then creates its own uniquely named database (Section 17):

```rust
// tests/common/infra.rs
// The Docker stack starts once per test binary; each test creates its own
// UUIDv7-named database and drops it in teardown.
use ctor::ctor;
use sqlx::postgres::PgPoolOptions;
use sqlx::PgPool;

#[ctor]
fn start_docker_stack() {
    let output = std::process::Command::new("docker")
        .args(["compose", "-f", "docker/docker-compose.yaml", "up", "-d", "--wait"])
        .output()
        .expect("docker compose should be runnable");
    assert!(output.status.success(), "docker compose up failed");
}

pub struct TestDatabase {
    pool: PgPool,
    name: String,
}

impl TestDatabase {
    pub async fn new() -> Self {
        let name = format!("myproject_test_{}", uuid::Uuid::now_v7().simple());
        let admin_pool = PgPoolOptions::new()
            .connect(&admin_database_url())
            .await
            .unwrap();
        sqlx::query(&format!(r#"CREATE DATABASE "{name}""#))
            .execute(&admin_pool)
            .await
            .unwrap();

        let pool = PgPoolOptions::new()
            .connect(&test_database_url(&name))
            .await
            .unwrap();
        sqlx::migrate!().run(&pool).await.unwrap();

        Self { pool, name }
    }

    pub fn pool(&self) -> &PgPool {
        &self.pool
    }

    pub async fn teardown(self) {
        self.pool.close().await;
        let admin_pool = PgPoolOptions::new()
            .connect(&admin_database_url())
            .await
            .unwrap();
        sqlx::query(&format!(r#"DROP DATABASE "{}" WITH (FORCE)"#, self.name))
            .execute(&admin_pool)
            .await
            .unwrap();
    }
}

fn admin_database_url() -> String {
    std::env::var("TEST_DATABASE_ADMIN_URL")
        .expect("TEST_DATABASE_ADMIN_URL must be set in .env")
}

fn test_database_url(name: &str) -> String {
    let server_url = std::env::var("TEST_DATABASE_SERVER_URL")
        .expect("TEST_DATABASE_SERVER_URL must be set in .env");
    format!("{server_url}/{name}")
}
```

If the project has static reference data, seed it in `TestDatabase::new()` right after the migrations run. For simple sqlx projects, `#[sqlx::test]` provides managed per-test databases out of the box; the `TestDatabase` pattern is preferred because it also controls naming, seeding, and teardown.

```rust
// tests/common/factories.rs
use uuid::Uuid;

pub fn create_test_schedule() -> Schedule {
    Schedule {
        id: ScheduleId::new(),
        name: format!("schedule-{}", Uuid::now_v7()),
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
```

```rust
// tests/common/fixtures.rs
use super::factories::create_test_schedule;
use super::infra::TestDatabase;

pub async fn save_prerequisite_schedule(test_database: &TestDatabase) -> Schedule {
    let schedule = create_test_schedule();
    sqlx::query("INSERT INTO schedules (id, name, cron) VALUES ($1, $2, $3)")
        .bind(&schedule.id)
        .bind(&schedule.name)
        .bind(&schedule.cron)
        .execute(test_database.pool())
        .await
        .unwrap();
    schedule
}
```

```rust
// tests/common/builders.rs
// Builders construct fully configured application services ready for testing.
// In common/integration scope they wire REAL dependencies (encryption,
// repositories backed by the TestDatabase). Mock-wired builders belong to
// unit support.

pub fn build_encryption_service() -> EncryptionService {
    let config = EncryptionConfig {
        algorithm: Algorithm::Aes256Gcm,
        key: SecretKey::from_bytes(&[0u8; 32]),
    };
    EncryptionService::new(config)
}

pub fn build_secret_service(
    repository: impl SecretRepository,
    encryption: EncryptionService,
) -> SecretService<impl SecretRepository> {
    SecretService::new(repository, encryption)
}
```

```rust
// tests/common/helpers.rs
// General-purpose test utilities that simplify common testing patterns.
// These are convenience functions, not domain-specific.

pub fn unique_email(prefix: &str) -> String {
    format!("{prefix}-{}@example.com", uuid::Uuid::now_v7())
}

pub fn unique_name(prefix: &str) -> String {
    format!("{prefix}-{}", uuid::Uuid::now_v7())
}

pub fn assert_json_contains(body: &serde_json::Value, key: &str, expected: &str) {
    let actual = body.get(key)
        .unwrap_or_else(|| panic!("key '{}' not found in JSON body", key))
        .as_str()
        .unwrap_or_else(|| panic!("key '{}' is not a string", key));
    assert_eq!(actual, expected);
}

pub async fn retry_until<ConditionFn, ConditionFuture>(
    max_attempts: u32,
    delay_milliseconds: u64,
    condition: ConditionFn,
) -> bool
where
    ConditionFn: Fn() -> ConditionFuture,
    ConditionFuture: std::future::Future<Output = bool>,
{
    for _ in 0..max_attempts {
        if condition().await {
            return true;
        }
        tokio::time::sleep(std::time::Duration::from_millis(delay_milliseconds)).await;
    }
    false
}
```

```rust
// tests/integration/support/constants.rs
pub const TEST_BUCKET_PREFIX: &str = "myproject-test";
pub const MAX_RETRY_ATTEMPTS: u32 = 3;
pub const DEFAULT_TIMEOUT_MILLISECONDS: u64 = 5000;
```

**Usage in tests** — one `super` per directory level between the test file and the category root; cross-category helpers come from `crate::common`:

```rust
// tests/integration/infrastructure/db.rs
use crate::common::factories::create_test_backup;
use crate::common::infra::TestDatabase;

use super::super::support::fixtures::save_prerequisite_schedule;

mod create_backup {
    use super::*;

    #[tokio::test]
    async fn should_persist_backup_for_existing_schedule() {
        let test_database = TestDatabase::new().await;
        let schedule = save_prerequisite_schedule(&test_database).await;
        let backup = create_test_backup(&schedule.id);
        let repository = PgBackupRepository::new(test_database.pool().clone());

        let saved = repository.save(&backup).await.unwrap();

        assert_eq!(saved.schedule_id, schedule.id);

        test_database.teardown().await;
    }
}
```

### 16. Test Files Contain Only Tests (CRITICAL)

A test file holds only `use` imports and the `mod <thing> { … }` test blocks — **no free helper functions, factories, fixtures, or constants at module scope.** Every reusable helper, value factory, fixture, environment/connection setup, and shared constant lives in the category's `support/` module or in `tests/common/` (Section 15) and is imported with `use super::support::…` / `use crate::common::…`. This includes mock definitions: `mock!` invocations and hand-written mock structs live in `tests/unit/support/mocks.rs`, never at the top of a test file.

This is **not** conditional on the helper being shared across multiple files — it holds for a single test file too. A reader opening the file should see the behaviours under test, not a preamble of plumbing.

The rule targets **module-scope items** (free `fn` / `const` / `static` / type definitions). It does not constrain a test's own body: building local values inside a test (`let request = …;`) *is* the test. The line is simply: a named, file-level helper or constant belongs in `support/`.

```rust
// Bad — tests/integration/broker.rs with helpers crowding the top of the file
const CONSUME_TIMEOUT: Duration = Duration::from_secs(5);

fn broker_url() -> String { /* … */ }
async fn open_channel() -> Channel { /* … */ }
fn create_envelope(id: &str) -> Envelope { /* … */ }

mod consume {
    use super::*;

    #[tokio::test]
    async fn should_deliver_a_published_message() { /* … */ }
}

// Good — the same file holds only tests; helpers live in support/
use super::support::constants::CONSUME_TIMEOUT;
use super::support::factories::create_envelope;
use super::support::infra::{broker_url, open_channel};

mod consume {
    use super::*;

    #[tokio::test]
    async fn should_deliver_a_published_message() { /* … */ }
}
```

### 17. Test Isolation and Parallelism (CRITICAL)

`cargo test` runs the tests inside a binary in parallel. Every test must be parallel-safe by construction — never by luck, and never by ordering:

- **Every test owns its resources.** Suffix every resource a test creates with a UUIDv7: databases (`myproject_test_<uuidv7>`), buckets, users, emails, object keys. Never reuse a static, shared, mutable name. Unique-name helpers (`unique_email`, `unique_name`) live in `support/`/`common/` helpers (Section 15).
- **Never bind a fixed port.** Bind port 0 and read the assigned address back (the `TestApp` pattern, Section 13). Fixed ports collide across parallel tests, CI jobs, and git worktrees.
- **No fixed shared paths.** When a test writes into a shared fixture (an SSH target, a mounted volume), write into a per-test subdirectory, never a fixed path.
- **Tear down what you create.** A test that creates external state ends with explicit teardown (`test_database.teardown().await`, bucket deletion). For a resource with a deterministic name, also ensure it is absent *before* the act, so a previously failed run cannot interfere.
- **`#[serial(...)]` is a last resort.** Use the `serial_test` crate's `#[serial(<group>)]` only for a genuine shared singleton that cannot be namespaced per test (a shared mail inbox, a global database lock). Treat every new serial group as a red flag, and record which singleton it guards. `serial_test` is process-local: it serializes tests within one test process only, not across processes.

```rust
// tests/e2e/api/auth.rs
use serde_json::json;
use serial_test::serial;

use crate::common::helpers::unique_email;

use super::support::infra::TestApp;

mod register_endpoint {
    use super::*;

    #[tokio::test]
    #[serial(mail_inbox)]
    async fn should_send_verification_email() {
        let test_app = TestApp::new().await;
        let email = unique_email("register");

        test_app.clear_mail_inbox().await;

        let response = test_app.client
            .post(test_app.url("/auth/register"))
            .json(&json!({"email": email, "password": "strongpass123!"}))
            .send()
            .await
            .unwrap();

        assert_eq!(response.status(), 201);
        let raw_email = test_app.wait_for_mail_message(&email).await;
        assert!(raw_email.contains("verify-email"));

        test_app.teardown().await;
    }
}
```

## Anti-Patterns to Avoid

1. **Tests in source files**: Using `#[cfg(test)]` modules in `src/` instead of `tests/` directory
2. **Missing module entry points**: Forgetting to create `unit.rs`, `integration.rs`, or `e2e.rs` to declare submodules
3. **Using _test suffix**: Adding a `_test` suffix to test files or test modules — test files mirror the source file name exactly and test modules are named after the function/type being tested, since `tests/` already provides context
4. **Testing timestamps**: Asserting exact timing instead of business outcomes — inject a clock port when time is part of the behaviour (Section 4)
5. **Comments in test files**: Doc comments or inline comments anywhere in a test file — a comment signals a naming or structure problem; support files may carry a brief orientation header
6. **Testing logging**: Mocking or asserting on logger calls
7. **Scattered test helpers**: Duplicating test fixtures and mock implementations across test files
8. **Kitchen-sink helper file**: Piling infrastructure, factories, fixtures, builders, mocks, and helpers into one file — split by concern across `tests/common/` and per-category `support/` files (Section 15)
9. **Vague test names**: Using generic names like `test_user` or `test_order`
10. **Flat test structure**: Not mirroring the source directory structure in tests
11. **Out-of-process e2e servers**: Spawning the compiled server binary from e2e tests, or hardcoding a server port — run the server in-process on port 0 via the `TestApp` harness (Section 13)
12. **Testing services against real databases**: Unit tests for services should use mocked ports, not real adapters
13. **Skipping adapter integration tests**: Adapters must be tested against real external systems to verify correct translation
14. **Over-relying on end-to-end tests**: Keep e2e tests minimal and focused on critical paths; most logic should be tested at unit level
15. **Mocking in integration tests**: Using `mockall`, `wiremock`, `httpmock`, or a hand-written fake in an integration test. Integration tests run against real infrastructure; mocking tools are unit-test tools (Sections 1, 2). If the real dependency cannot be stood up, the test is a unit test or an e2e test — not an integration test.
16. **Helpers in test files**: Free helper functions, value factories, fixtures, or constants at module scope inside a test file. Test files are tests-only — move them to `support/` or `tests/common/` (Section 16).
17. **Fixed or shared resource names**: Static database/bucket/user names, fixed ports, or fixed shared paths in tests — every resource is UUIDv7-suffixed and every port OS-assigned (Section 17)
18. **Bare `is_ok` assertions**: Asserting only `assert!(result.is_ok())` as the final assertion hides the error and the value — extract with `.expect("context")` and assert on the value, or match the error variant with `matches!`

## Quick Reference

### Test Framework
- Use `cargo test` for all tests; `cargo nextest` also works — note that `#[ctor]` bring-up runs once per *process*, and nextest runs each test in its own process, so keep the ctor idempotent and cheap when the stack is already running
- Use `#[tokio::test]` for async tests; `flavor = "multi_thread"` only when the test needs real concurrency
- Prefer hand-written port mocks (Section 5); `mockall` for simple stateless expectations (unit tests)
- Use `wiremock` or `httpmock` to stand up fake HTTP endpoints (unit tests for client adapters)
- Use `serial_test`'s `#[serial(<group>)]` only for genuine shared singletons (Section 17)

### Assertions
- Extract success values with `.expect("context")` and assert on the value with `assert_eq!`
- Assert error variants with `assert!(matches!(result, Err(Error::Variant { .. })))`
- Setup plumbing may `.unwrap()` freely — the production `.unwrap()` ban (rust-code-style) does not apply to test code
- A bare `assert!(result.is_ok())` is never a sufficient final assertion (anti-pattern 18)

### Mocking Strategy
- Mocking is for **unit tests only** — never in integration tests (which use real infrastructure)
- Hand-written stateful mocks are the canonical pattern; they control return values and track calls
- `mockall` is acceptable for simple stateless expectation-style mocks
- All mock definitions live in `tests/unit/support/mocks.rs` (see Sections 5, 15, 16)

### Test Scope by Layer
- **Unit tests**: Test domain logic and services with mocked ports
- **Integration tests**: Real external systems, never mocks — adapters (`integration/infrastructure/`) and services wired to real adapters (`integration/application/`)
- **E2E tests**: Full stack in subdomains (`e2e/api/` first); critical paths only, keep minimal
- Most business logic should be tested at the unit level with mocked dependencies

### Structure
- All tests in `tests/` directory, never in source files; the crate needs a `src/lib.rs` library target
- Create module entry point files: `tests/unit.rs`, `tests/integration.rs`, `tests/e2e.rs`
- Test files and test modules must never use a `_test` suffix
- Organize into `unit/`, `integration/`, and `e2e/` subdirectories; e2e subdomains each own a `support/`
- Mirror source directory structure: `src/domain/salaries.rs` → `tests/unit/domain/salaries.rs`; adapters: `src/infrastructure/db.rs` → `tests/integration/infrastructure/db.rs`
- Cross-category helpers in `tests/common/` (entry `tests/common/mod.rs` — the only allowed `mod.rs`); category-specific helpers in per-category `support/` (Section 15)
- `mocks.rs` is unit-support only — an integration `support/` has no mocks
- Test files contain only tests — every module-scope helper, factory, fixture, and constant lives in `support/` or `common/` (Section 16)
- Import grouping in test files follows the same std / external / local convention as production code (rust-code-style)

### Naming
- Each function/method gets its own `mod` named after it
- Inside the mod, test names use `should_<expected_behavior>` or `should_<expected_behavior>_when_<condition>`
- The `test_` prefix must not be used — the mod provides context
- Full path reads naturally: `create_order::should_validate_inventory`
- Standalone function: one mod, test cases inside
- Single-struct file: function mods at top level (file = struct context)
- Multi-struct file: struct mod → function mod → test cases (see Section 14)

### Hexagonal Architecture Testing
- Services are tested with mocked ports (repositories, external services)
- Adapters are tested against real external systems in integration tests
- Handlers are tested via e2e API tests or with mocked services
- Domain logic is tested in isolation without any mocking

### Isolation
- Every created resource is UUIDv7-suffixed; never a static shared mutable name
- Servers bind port 0; tests read the assigned address back
- Explicit teardown of every created external resource; ensure-absent-before-act for deterministic names
- `#[serial]` only for genuine singletons; every new serial group is a red flag (Section 17)

### Preservation
- When modifying existing tests, follow the file's established conventions; do not reformat or restructure existing passing tests unless the task explicitly requires it
- Never test logging statements

### Documentation
- Test files must not contain doc comments or inline comments — a comment in a test signals a naming or structure problem
- Support files (`support/`, `common/`) may carry a brief header comment for orientation
