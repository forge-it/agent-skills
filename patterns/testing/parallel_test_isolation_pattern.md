---
name: parallel-test-isolation-pattern
description: >-
  Use when integration or end-to-end tests share a Docker-backed fixture stack
  and tests start interfering with each other: flaky failures that disappear
  when tests run serially, order-dependent teardown, cross-test state leakage
  through a shared database or shared inbox, or CI jobs that cannot be
  parallelized because they all hit the same container. Also use when adding a
  new fixture service or a new test to an existing project, to ensure the new
  work does not introduce a shared mutable resource that will block future
  parallelism.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.1"
---

# Parallel Test Isolation Pattern

## Purpose

Integration and end-to-end tests need real infrastructure — databases,
object stores, message brokers, SSH targets. That infrastructure runs as a
shared Docker stack. The moment two tests touch the same mutable resource in
that stack (the same database, the same S3 bucket, the same inbox), they
interfere: one test's setup corrupts another test's assertions, teardown races,
and results become order-dependent.

**In one line:** every test owns a fully isolated copy of every resource it
touches — no test can observe the side-effects of any other test running
concurrently.

This isolation is what makes it safe to run an entire integration suite with
`cargo test` in parallel (Rust's default), and what will eventually make it
safe to run suites in separate git worktrees (or separate CI agents) against
independent stacks.

> **Core principle (separation of concerns / single responsibility):** each
> test is responsible for creating and destroying exactly the resources it
> needs. Tests do not share mutable state. A test that relies on another
> test's setup or teardown is not a test — it is a fragment of a longer
> script, and it cannot run in parallel.

## When to Apply

- You are writing a new integration or end-to-end test that will use a shared
  Docker fixture stack.
- You are adding a new Docker service (fixture) to an existing stack.
- Tests in your suite are flaky when run with `--test-threads=N` but pass
  serially — this is the classic symptom of shared mutable state.
- You want to run the integration suite from multiple git worktrees at the
  same time (parallel agent or developer workflows).
- CI is slow because integration tests must run serially; you want to
  parallelize them.

**When NOT to use:** pure unit tests with no external infrastructure, or
short-lived batch scripts with no test parallelism requirements.

---

## The Two Halves

The pattern has two independent concerns. Each must be right; getting only one
is not enough.

### Half 1 — Local Infrastructure via Docker Compose

The Docker stack provides the physical services the tests need: one shared,
long-lived process per service type (one PostgreSQL instance, one MinIO, one
RabbitMQ, etc.). Tests connect to these services, but they do **not** assume
exclusive ownership of any service-level resource.

#### How the stack starts

The test binary starts the stack automatically via a `#[ctor::ctor]` function
— a Rust constructor attribute that runs before the test harness. This means
every `cargo test` invocation brings the stack up exactly once per process and
blocks until every service reports healthy. Tests never call `docker compose`
themselves.

```
tests/common/infra.rs  →  #[ctor::ctor] start_docker_services()
                          →  docker compose -f docker/docker-compose.yaml up -d
                          →  wait_for_postgres_ready()
                          →  wait_for_minio_ready()
                          →  ... (one wait function per service)
```

The `wait_for_*` functions poll the service until it is truly ready — not just
running — before the first test is allowed to proceed.

#### Stack composition (ironbox example)

`core/docker/docker-compose.yaml` defines the test stack. It covers 15
containers:

| Band | Host port range | Services |
|---|---|---|
| Databases (primary) | 8710–8712 | PostgreSQL 17 (main), PostgreSQL 16 backup target, PostgreSQL 17 backup target |
| Databases (non-Postgres) | 8720–8731 | MySQL 8, MySQL 5.7, MongoDB 7 (standalone), MongoDB 7 (replica set) |
| Object storage / emulators | 8740–8744 | MinIO, Mailpit SMTP, Mailpit HTTP, fake-GCS, Azurite |
| Message broker | 8780–8781 | RabbitMQ AMQP, RabbitMQ management |
| SSH machines | 8760–8762 | Linux source machine, Linux storage-vault machine, Windows storage-vault machine |

All ports within one band are reserved in a companion port-allocation doc; see
[`../decisions/local_port_allocation_pattern.md`](../decisions/local_port_allocation_pattern.md).

#### New-fixture guardrail (ADR-R04)

The stack was built before env-substitutable ports were mandated. New fixtures
added from this point on must follow the guardrail: host ports declared as
env-substitutable values, not bare literals. The RabbitMQ service demonstrates
the correct form:

```yaml
# core/docker/docker-compose.yaml  (the rabbitmq service)
ports:
  - "${IRONBOX_RABBITMQ_AMQP_HOST_PORT:-8780}:5672"
  - "${IRONBOX_RABBITMQ_MANAGEMENT_HOST_PORT:-8781}:15672"
```

The `:-` default matches the constant in `dev_environment.rs` and the value in
`.env`, so existing workflows are unchanged. The substitutable form is what
allows a future per-worktree offset scheme to drive the port without touching
the compose file.

Do not add bare literal host ports (`"8750:9999"`) to new services.

---

### Half 2 — Per-Test Isolation

The shared Docker stack provides one physical PostgreSQL server. Tests must
not all write to the same database on that server — that is the mutable
shared-state trap. The isolation mechanism is: **each test creates its own
named resource, uses it, then destroys it.**

#### The isolation boundary: one database per test

In ironbox, every database integration test creates a fresh PostgreSQL database
with a UUIDv7-based name, runs all migrations against it, seeds reference data,
and drops it when the test completes. The `TestDatabase` struct in
`tests/common/infra.rs` encapsulates this lifecycle:

```rust
// tests/common/infra.rs

pub struct TestDatabase {
    database_name: String,
    pool: PostgresPool,
}

impl TestDatabase {
    pub async fn new() -> Self {
        let config = &*DATABASE_CONFIG;
        // UUIDv7 suffix guarantees no name collision across concurrent tests
        let database_name = format!("ironbox_test_{}", uuid::Uuid::now_v7().simple());

        // 1. Connect to the admin database and create the isolated test database
        let admin_url = format!("{}/{}", config.base_url, config.database_name);
        let admin_pool = PgPool::connect(&admin_url).await
            .expect("failed to connect to main database");

        sqlx::query(&format!("CREATE DATABASE {database_name}"))
            .execute(&admin_pool).await
            .expect("failed to create test database");

        admin_pool.close().await;

        // 2. Run all migrations against the new database
        let test_url = format!("{}/{database_name}", config.base_url);
        let test_pool = PgPool::connect(&test_url).await
            .expect("failed to connect to test database");

        sqlx::migrate!("./migrations")
            .run(&test_pool).await
            .expect("failed to run migrations on test database");

        // 3. Seed static reference data (tiers, etc.)
        TierSeeder::new(test_pool.clone())
            .seed().await
            .expect("seed tiers in test DB");

        // ... wrap pool and return
        Self { database_name, pool }
    }

    pub async fn teardown(self) {
        // DROP DATABASE ... WITH (FORCE) kills active connections so nothing blocks cleanup
        sqlx::query(&format!(
            "DROP DATABASE IF EXISTS {} WITH (FORCE)",
            self.database_name
        ))
        .execute(&admin_pool).await
        .expect("failed to drop test database");
    }
}
```

Every test that needs the database follows the same three-line shape:

```rust
#[tokio::test]
async fn should_return_created_user() {
    let test_database = TestDatabase::new().await;   // own world created
    // ... test body ...
    test_database.teardown().await;                  // own world destroyed
}
```

Because every test database has a unique name, hundreds of tests can run
concurrently against the same PostgreSQL instance with no interference.

#### Unique names for everything else

The isolation boundary extends to every other resource a test touches:

**Object storage (MinIO / S3).** Object keys include a UUIDv7 suffix:

```rust
let object_key = format!("test-upload-{}.bin", uuid::Uuid::now_v7());
let byte_count = backend.store(&object_key, stream).await.unwrap();
```

**Named entities with uniqueness constraints.** Any column with a unique
constraint (email, source name, storage vault name) uses a helper that
combines a semantic label with a UUIDv7 suffix:

```rust
fn unique_email(prefix: &str) -> String {
    format!("{prefix}-{}@ironbox.local", uuid::Uuid::now_v7())
}

fn unique_source_name(prefix: &str) -> String {
    format!("{prefix}-{}", uuid::Uuid::now_v7())
}
```

The semantic label appears in failure output; the UUID suffix prevents
concurrent tests from colliding on the same name.

**Object storage buckets (MinIO provisioner).** Provisioner tests that need a
clean bucket use a deterministic UUID so the bucket name is predictable and
can be cleaned up at the end:

```rust
fn test_user_identifier(uuid_string: &str) -> UserId {
    UserId::from_uuid(Uuid::parse_str(uuid_string).expect("test UUID should be valid"))
}

let user_id = test_user_identifier("11111111-1111-7111-8111-111111111111");
let bucket_name = expected_bucket_name(&user_id);   // "ironbox-<uuid>"

ensure_bucket_absent(&bucket_name).await;           // wipe any leftover state
// ... act ...
provisioner.delete_bucket(&bucket_name).await.unwrap();  // teardown
```

**End-to-end API server port.** The end-to-end `TestApp` binds the HTTP
server to host port `0`, which asks the OS for an ephemeral free port, then
reads back the assigned address. No test hardcodes a port number, so any
number of test apps can run concurrently:

```rust
// The server binds to port 0; the OS assigns a free port.
// The test reads back the actual address after binding.
let bound_address = app.bind("0.0.0.0:0").await.expect("failed to bind");
```

#### Genuinely shared singletons (the serial exception)

A small set of resources cannot be per-test — MongoDB's fsyncLock is a
server-wide operation; the mailpit inbox is a single SMTP endpoint. These are
marked `#[serial(...)]` from the `serial_test` crate, which serializes them
within one `cargo test` process.

**Important:** `serial_test` is process-local. It serializes tests within one
`cargo test` invocation. It does not synchronize across two separate processes
(two worktrees, two CI agents) hitting the same container. As long as a single
shared stack is in use, cross-process parallelism for these tests is not safe.

Every `#[serial(...)]` group should be documented in the integration-testing
knowledge base alongside the singleton it guards, so the cost of full
multi-stack parallelism is visible.

---

## Why This Matters for Parallel Worktrees and Fast CI

A shared mutable test database forces tests to run serially: each test must
wait for the previous one to finish and clean up before it can begin. At scale
this makes the suite linear in the number of tests — a 500-test suite where
each test takes 100ms adds up to 50 seconds even if the database could serve
all 500 simultaneously.

Per-test isolation eliminates this bottleneck within one process. With
`TestDatabase::new()` and UUIDv7 names, all 500 tests run at once; the suite
duration drops to the duration of the single slowest test.

The same principle extends to the worktree / CI-agent level: if each parallel
agent gets its own Docker stack (its own PostgreSQL instance, its own MinIO,
its own RabbitMQ), then the `serial_test` cross-process problem disappears
too. Each process owns its own "shared" singleton; there are no real
cross-process collisions. That per-stack parameterization is the deferred
target in ADR-R04.

---

## Worked Example — Full Database Repository Test

```rust
// core/tests/integration/infrastructure/database/user_repository.rs

fn create_repository(test_database: &TestDatabase) -> PostgresUserRepository {
    PostgresUserRepository::new(test_database.pool().clone())
}

fn unique_email(prefix: &str) -> String {
    format!("{prefix}-{}@ironbox.local", uuid::Uuid::now_v7())
}

mod find_by_id {
    use super::*;

    #[tokio::test]
    async fn should_return_none_when_not_found() {
        let test_database = TestDatabase::new().await;
        let repository = create_repository(&test_database);

        let result = repository.find_by_id(&UserId::new()).await.unwrap();

        assert!(result.is_none());
        test_database.teardown().await;
    }

    #[tokio::test]
    async fn should_return_created_user() {
        let test_database = TestDatabase::new().await;
        let repository = create_repository(&test_database);
        let request = factories::create_test_user_request(&unique_email("user-find"));

        let created = repository.create(&request).await.unwrap();
        let found = repository.find_by_id(created.id()).await.unwrap().unwrap();

        assert_eq!(found.id(), created.id());
        assert_eq!(found.email(), created.email());

        test_database.teardown().await;
    }
}
```

What this demonstrates:
- `TestDatabase::new()` creates a fresh database named
  `ironbox_test_<uuidv7>`, fully migrated and seeded.
- `unique_email("user-find")` produces a name that will never collide with
  any other test running at the same time.
- `test_database.teardown()` drops the database with `WITH (FORCE)` so
  active connections do not block cleanup.
- Both tests in `find_by_id` can run fully concurrently; they operate in
  completely separate databases.

---

## Quick Reference — Invariants

- **Each test creates and destroys its own database.** Use `TestDatabase::new()`
  / `teardown()` at the start and end of every database test. Never reuse a
  database across tests.
- **Every resource name includes a UUIDv7 suffix.** Database names, object
  keys, entity names with unique constraints — all of them. Never use a
  static, shared, mutable name.
- **End-to-end test servers bind port `0`.** The OS assigns a free port;
  the test reads it back. No test hardcodes a host port.
- **New fixtures use env-substitutable host ports.** The `${VAR:-default}`
  form in docker-compose, with the default matching the `dev_environment`
  constant. Never add a bare literal host port to a new service.
- **New test code references fixtures by service name, not container name.**
  Use `docker compose exec <service>` instead of `docker exec
  <literal-container-name>` so the same helper works against any stack
  instance.
- **Every `#[serial(...)]` group is documented.** It marks a cross-test
  shared singleton. Record it in the integration-testing knowledge base
  alongside the singleton it guards.
- **`serial_test` is process-local.** It does not protect against two separate
  `cargo test` processes running against the same shared stack.

---

## Anti-Patterns to Avoid

- **Shared mutable test database.** All tests write to one database and rely
  on test ordering or a global setup/teardown. Any two tests touching the same
  row can interfere; the suite cannot run in parallel.
- **Static names without UUIDv7 suffix.** `"test-user@ironbox.local"` as a
  literal email in a test. The second concurrent test that inserts the same
  email will hit a unique-constraint error.
- **Hardcoded host ports in test code.** `let address = "127.0.0.1:8080"`.
  Two tests trying to bind the same port at the same time will fail; two
  stacks on the same host will collide.
- **Bare literal host ports in new compose services.**
  `"8750:9999"` in a new service definition. This cannot be parameterized
  for a multi-stack setup without editing the compose file.
- **`docker exec <literal-container-name>` in test helpers.** This ties the
  helper to the single hardcoded stack. It cannot work against a
  parameterized per-worktree stack without changing the helper.
- **Order-dependent tests.** Test B assumes Test A's data is already present.
  This is test coupling masquerading as setup. Extract the shared setup into
  a fixture function and call it from both tests.
- **Missing teardown.** Tests that create databases or buckets but never drop
  them accumulate state that can interfere with subsequent runs and fill disk.
  Use `WITH (FORCE)` for database drops to avoid blocking on active connections.
- **`ironbox_seed_clone_<label>` pattern (the documented anti-example).** These
  databases are deliberately not UUID-suffixed and are dropped and recreated by
  concurrent tests, causing races. Do not add more static-label seed databases.

---

## Relationship to Other Skills and Patterns

- **[`../decisions/local_port_allocation_pattern.md`](../decisions/local_port_allocation_pattern.md)** —
  the companion port-allocation pattern. Port allocation underpins isolation:
  env-substitutable host ports in the compose file are the mechanism that will
  allow a future per-stack offset scheme to assign non-overlapping ports to
  parallel stacks. Read this before adding a new service to the fixture stack.
- **`rust-testing`** — Rust-specific test conventions; applies inside the
  isolation boundary established here (naming, assertion style, module layout).
- **`python-testing`** — Python-specific test conventions; the same isolation
  principles apply (per-test database, UUIDv4/v7 resource names).
- **`ci-setup`** — CI runs the integration suite; this pattern is what makes
  the suite safe to run in a CI job without serializing every test. Apply
  `ci-setup` to wire the docker-stack startup into the CI job.
- **`justfile-setup`** — the `just test-integration` and `just up` recipes
  that bring the Docker stack up and run the suite. The justfile is the
  developer-facing entry point to the workflow this pattern describes.
