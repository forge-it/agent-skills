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
  version: "0.0.8"
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

#### Create from a per-run template, not by migrating per test

The example above migrates and seeds **every** test database. That is the
expensive way to honour the invariant, and the cost is worth knowing before you
copy it. Measured against a stock PostgreSQL 17.10 with a real 7-file, ~100 KB
migration set (median of 15):

| Path | median |
|---|---|
| `CREATE DATABASE` + apply all migrations (the example above) | **292 ms** |
| `CREATE DATABASE … TEMPLATE <migrated template>` | **99 ms** |
| `CREATE DATABASE` alone — the irreducible floor | **46 ms** |

So build the migrated-and-seeded template **once per test binary**, then create
each test database from it, with the isolation guarantee unchanged — each test
still owns a private, uniquely-named database.

**The size of the win is proportional to what your migrations do**, because both
paths pay the same fixed cost (the connects plus `CREATE`/`DROP DATABASE`). Only
the migrate-per-test path pays for the migration statements on top. Measured:
~194 ms and ~3× against the 7-file, ~100 KB set above; only **24%** (95 ms → 72 ms)
against a 2-file toy schema. Measure your own set before quoting a number.

**Building it exactly once is language-specific.** In Rust a
`tokio::sync::OnceCell` suffices — `cargo test` runs a binary's tests as threads
in one process, so no lock and no marker file are needed (verified: 16
concurrent `TestDatabase::new()` calls, initializer body ran once). But note that
**every file directly under `tests/` compiles to its own binary**, each with its
own statics, so a suite split across N integration-test files builds N templates
— still far cheaper than per-test migration, but consolidate the
database-backed tests into one target if you want literally one. In Python the
equivalent needs the lock-**and-marker** mechanism described under *Mapping to
Python*, because pytest-xdist workers are separate processes.

**Close the template's connection pool before cloning from it.** PostgreSQL
refuses to copy a template that any other session is connected to:
`source database "…" is being accessed by other users`, SQLSTATE **55006**.
Build the template, seed it, close the pool, *then* hand the name out.

Two further properties of this cost, because they bound what parallelism can buy:

- **The floor is fixed, not schema-driven.** An empty template still costs tens
  of milliseconds, because a PostgreSQL template is megabytes of catalog to
  copy. A smaller schema does not make it cheap.
- **`CREATE`/`DROP DATABASE` contends inside one server.** Four concurrent
  workers yielded ~2.5× throughput with per-operation latency roughly doubling —
  safe, but sublinear. Threads in one test process all share one PostgreSQL, so
  adding threads does not reduce the per-test floor. Giving each *process* its
  own stack does parallelize it, at the cost of one database server per stack.

**One teardown hazard.** `DROP DATABASE … WITH (FORCE)` forces an immediate
checkpoint. In a burst of creates with no intervening checkpoint, the first drop
pays to flush everything: one measured run took **26 seconds**, having fsynced
22,514 files. After an explicit `CHECKPOINT` the same drop took 21–36 ms. If
teardown ever appears to hang, this is the first thing to check; the fixture
server's `checkpoint_timeout` and `max_wal_size` are the knobs.

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
  `ironbox_test_<uuidv7>`, fully migrated and seeded. This is the **expensive
  form** — migrating per test rather than cloning a per-run template; see
  *Create from a per-run template* below before copying it.
- `unique_email("user-find")` produces a name that will never collide with
  any other test running at the same time.
- `test_database.teardown()` drops the database with `WITH (FORCE)` so
  active connections do not block cleanup.
- Both tests in `find_by_id` can run fully concurrently; they operate in
  completely separate databases.

---

## Mapping to Python

The example above is one *implementation* of the invariants below, not the invariants
themselves. Python keeps every one — but one structural difference reorders the work:
Rust's harness runs tests as **threads in one process**, while `pytest` with
`pytest-xdist` runs them in separate **worker processes**. That changes what "unique
per test" must key on, what a shared fixture actually shares, and what survives a crash.

**Stack lifetime this mapping assumes: one machine-wide stack, brought up once per
*run* and left running.** That is a third lifetime, and the document uses all three —
be explicit about which one is in force. Half 1's `ctor` model brings the stack up once
per *process*, which is safe in Rust only because a `cargo test` run is exactly one
process; under `-n <N>` "once per process" would mean `N` concurrent `docker compose up`
calls against one stack, which is why Python needs the lock-and-marker fixture below and
Rust does not. *Why This Matters* posits a stricter lifetime again — one stack per
parallel agent — under which the stack lock becomes unnecessary but stays harmless.

### Structural mapping

| Concern | Rust (ironbox) | Python |
|---|---|---|
| Stack startup, once | `#[ctor::ctor] start_docker_services()` — once per test process | a session-scoped `autouse` fixture in `tests/conftest.py` — but **once per xdist worker**, not once per run (see *Fixture scope*); the cross-process once-per-run mechanism is a file lock **plus a marker file** — a lock alone gives mutual exclusion, not once-only |
| Readiness gating | `wait_for_postgres_ready()` etc., blocking before the first test | the same wait loops inside that fixture, one function per service — tests never call `docker compose` themselves |
| Per-test database | `TestDatabase::new()` / `.teardown()` | a **function-scoped `yield` fixture** in `tests/integration/conftest.py` that creates *from the template*, yields, and drops — never migrating per test |
| Unique resource names | `uuid::Uuid::now_v7()` suffix | `uuid.uuid7()` — stdlib from **Python 3.14**, which the greenfield baseline mandates, so new projects just call it. On an older codebase use the `uuid-utils` package; `uuid.uuid4()` satisfies uniqueness but is not time-ordered, so it forfeits the resource *age* the orphan sweep below relies on |
| Semantic-label helper | `unique_email(prefix)` | the same helper, in `tests/utils/helpers.py` — never defined in a test module (see `python-testing`, *Test Modules Contain Only Tests*) |
| Serialized singletons | `#[serial(...)]` from `serial_test` | `@pytest.mark.xdist_group(name="…")` run under `--dist loadgroup`, which places every member of a group on **one** worker — the group is ordered inside that worker only, so with `-n <N>` a *single* run already has `N` processes on the stack, and a true singleton needs one stack per run |
| Ephemeral e2e port | `app.bind("0.0.0.0:0")` | bind a `socket` to port `0`, read `getsockname()[1]`, then hand **that same socket** to the server |
| Fixture host ports | `${VAR:-default}` in compose, default matching `dev_environment.rs` | unchanged — compose is language-neutral; the Python side reads the value from the environment through a settings object |
| Test-process identity | not needed (one process) | the `worker_id` fixture / `PYTEST_XDIST_WORKER` — the new concern this table exists for |

### Test-process identity is the foundation

`pytest-xdist` supplies the identity, and it is available whether or not `-n` was passed:

- The **`worker_id`** fixture is `"gw0"`, `"gw1"`, … under `-n <N>`, and `"master"`
  when xdist is not distributing. It is session-scoped, so a session-scoped fixture
  may depend on it.
- **`PYTEST_XDIST_WORKER`** carries the same value in the worker's environment
  (`PYTEST_XDIST_WORKER_COUNT` carries `<N>`), so any child process the test spawns —
  `docker compose`, a subprocess server, a CLI under test — inherits the identity
  without being passed it. Both variables are **absent** in a non-distributed run.
- **`testrun_uid`** is one value shared by every worker of a single run: the only
  identity token that means "this run" rather than "this worker".

**Key every isolated resource on run identity + worker identity + a uniqueness suffix.**
This document mandates exactly **one** name format, spelled out once under *Cleanup that
survives failure* below — use it verbatim and never invent a second format. The argument
for those three parts: not a process id, because the OS reuses pids and one worker process
runs hundreds of tests, so a pid is neither unique per test nor a stable owner label; and
not a bare random value, because that is unique but anonymous, so when a worker is killed
nothing identifies which leftovers were its. Run identity lets a sweep tell a live run
from an orphan, worker identity makes an orphan attributable, and the uniqueness suffix
makes the name collision-free.

### Per-test database isolation — three options, one default

| Option | Mechanism | Cannot isolate |
|---|---|---|
| **Fresh database per test** (the default) | `CREATE DATABASE <name> TEMPLATE <migrated_template>` on a connection with `isolation_level="AUTOCOMMIT"`; `DROP DATABASE … WITH (FORCE)` in teardown | nothing at the database level; costs **two orders of magnitude** more per test than rollback — see *What the default costs* below |
| Fresh schema per test | one connection, `CREATE SCHEMA <name>`, per-test `search_path`; `DROP SCHEMA … CASCADE` | anything cluster-wide (roles, extensions, database settings), and any code that hardcodes a schema-qualified name escapes the boundary silently |
| Transaction rollback | outer `connection.begin()`, `Session(bind=connection)`, rollback in teardown | see the three hard limits below |

`CREATE DATABASE` **must** run on an autocommit connection — on a default SQLAlchemy
connection it fails with `CREATE DATABASE cannot run inside a transaction block`.
Creating from an already-migrated template keeps the per-test cost at one `CREATE`
instead of a full migration run; the template must have no other sessions connected,
so dispose the engine that migrated it.

Rollback isolation is the cheapest and is **not equivalent**:

1. **DDL is engine-dependent, not universally rollback-safe.** On PostgreSQL 17 DDL
   inside the outer transaction does roll back. On MariaDB 11.8 a DDL statement
   implicitly commits — and a row inserted *before* that DDL survived the outer
   rollback. The isolation boundary is destroyed with no error.
2. **Code that opens its own connection or engine sees nothing.** Uncommitted rows
   are invisible outside the test's connection, so anything driven through a
   subprocess, a background task with its own engine, or a separate server process
   reads an empty database.
3. **Commit visibility across connections cannot be tested at all** — the behaviour
   under test is the thing the isolation mechanism suppresses.

One breakage commonly *attributed* to rollback isolation is not real in SQLAlchemy 2.0:
a `Session(bind=connection)` joins the outer transaction under
`join_transaction_mode="conditional_savepoint"` (the default), so a `session.commit()`
issued by the code under test releases a savepoint and the outer rollback still undoes
it. Do not cite that as the reason.

#### What the default costs

Measured on one machine — PostgreSQL 17.10 in Docker on a local NVMe SSD, median of 12
runs per row. Treat the *shape* as transferable and the absolute numbers as not:

| Template schema | Rollback per test | Fresh database per test | Ratio |
|---|---|---|---|
| 1 table, 0 rows | 0.97 ms | 85.8 ms | 88× |
| 20 tables, 0 rows | 1.00 ms | 98.7 ms | 99× |
| 100 tables, 0 rows | 1.06 ms | 130.4 ms | 123× |
| 100 tables, 5 000 rows | 0.89 ms | 134.3 ms | 151× |

Three consequences, and the recommendation depends on all three:

- **It is two orders of magnitude, not one.** Budget **80–135 ms per test** for the
  default, against roughly 1 ms for rollback.
- **The dominant term is a fixed floor, not schema size.** An *empty* template — zero
  tables — still measured 87 ms per test, because a PostgreSQL template is ~7.4 MiB of
  catalog that `CREATE DATABASE` copies regardless. Schema size only adds on top, so a
  small-schema project does not get a cheap version of this.
- **`CREATE`/`DROP DATABASE` is a machine-wide serialization point,** so adding workers
  does not buy proportional throughput: four concurrent workers roughly doubled
  per-operation latency (74 ms → 144 ms) and returned only 2.5× the throughput of one
  worker — about 25 databases per second machine-wide. It is nevertheless
  concurrency-**safe**: zero failures at 1, 2, 4, and 8 workers. Safe, but flat.

**This bounds the speed-up promised earlier.** *Why This Matters for Parallel Worktrees
and Fast CI* says the suite duration drops to the duration of the single slowest test —
that holds for the test *bodies*, not for this fixture. At ~25 databases per second
machine-wide, 500 per-test databases is roughly **20 seconds** of floor that no number of
workers removes. Read the earlier claim as "the slowest test **plus** the serialized cost
of provisioning every test's database".

**The choice is not per language — it is per persistence design.** Rollback
isolation is available exactly when the caller can supply the connection that the
repositories and the unit of work use. Python usually can, because a unit of work
that takes a `session_factory` already exposes that seam; a Rust adapter that
connects its own pool from a URL does not, and one that takes an executor does.
Nothing about either language decides it. If your layer has no such seam, a
per-test database is your only option until you add one — and adding it later
means touching every adapter, which is why the seam is a day-1 decision.

**Where the seam exists, default to rollback for the integration tier** —
repository, mapper, and unit-of-work tests. Not because it is merely cheaper, but
because 88–151× on a floor no parallelism removes means a suite of any size would
otherwise have to escape the default immediately, and a default most projects must
escape is a warning wearing the wrong label.

**Use a real per-test database for the three categories rollback cannot serve**,
and note the criterion is *not* "read-only": a test that writes through the
repository and reads it back is safe, because a `commit()` under test is undone
too. The disqualifying properties are the ones above — DDL under test on an engine
that implicitly commits it, any access that does not go through the fixture's
connection (a second engine, a subprocess, an out-of-process server), and
cross-connection commit visibility as the behaviour under test. In practice that
is the e2e tier and MySQL/MariaDB DDL tests.

Record the choice per tier with the measurement that justified it. The two
mechanisms are **additive**: the categories above need a real database forever, so
the per-test-database machinery below stays regardless.

### Fixture scope is the correctness knob

Scopes are `function`, `class`, `module`, `package`, `session`. Per-test isolation
means the isolated resource is **`function`**-scoped (the default); anything wider is
shared state, which is the exact failure this pattern exists to prevent.

**The trap: `session` scope means "once per worker", not "once per run."** Each xdist
worker is its own process and builds its own copy — a session fixture ran twice under
`-n 2`. That is correct for per-worker-owned things (an engine, a connection pool, a
readiness wait). Anything that must truly happen **once per run** needs a cross-process
mechanism — and **a file lock alone is not that mechanism.** A lock gives mutual
exclusion, not once-only. Measured with four workers released simultaneously, a lock-only
fixture ran the work **4 times**; lock-plus-marker ran it **once**. For the template
database the lock-only form does not merely waste work, it fails: the three serialized
workers each then hit `DuplicateDatabase: database "…" already exists`.

**The mechanism is a lock plus a marker file.** The lock holder takes the lock, checks the
marker, does the work, writes the marker; every other worker takes the lock, sees the
marker, and skips. This is the standard `pytest-xdist` idiom and the only form that is
once-per-run.

**The two once-per-run cases need different keys — do not give them one key:**

| Work | Key the lock and marker on | Why |
|---|---|---|
| Creating the migrated template database | `testrun_uid` | The template is a per-run artifact, so one per run is exactly right. |
| `docker compose up` on a machine-wide stack | the **compose project name** (stack identity) | The stack is not a per-run artifact. Keying it on `testrun_uid` guarantees two concurrent runs never exclude each other — and concurrent worktrees are the case this pattern exists to serve. |

Put the lock and the marker in `tmp_path_factory.getbasetemp().parent`. In a
**distributed** run that is the one directory every worker of the run shares — verified:
all four workers reported the same `/tmp/pytest-of-<user>/pytest-0`, each with its own
`popen-gw<N>` beneath it. In a **non-distributed** run it escapes one level further to
`/tmp/pytest-of-<user>`, which every run on the machine shares — which is what a
stack-identity lock wants anyway, and harmless for a `testrun_uid`-keyed one because the
key still differs per run.

```python
# tests/conftest.py — once per RUN, not once per worker.
# FileLock comes from the `filelock` package, pinned in the PEP 735 `dev` group.
@pytest.fixture(scope="session")
def template_database_name(tmp_path_factory, testrun_uid):
    # Sorts outside the ironbox_test_% sweep prefix; the operator sweep drops it.
    template_name = f"ironbox_tmpl_{testrun_uid[:8]}"
    shared_directory = tmp_path_factory.getbasetemp().parent
    marker_path = shared_directory / f"{testrun_uid}.template-ready"
    with FileLock(str(shared_directory / f"{testrun_uid}.template.lock")):
        if not marker_path.exists():        # the lock ALONE is not once-per-run
            create_and_migrate_template(template_name)
            marker_path.write_text(template_name)
    return template_name
```

`create_and_migrate_template` belongs in `tests/utils/helpers.py`: `CREATE DATABASE` on an
autocommit connection, run the migrations, then **dispose** the engine — the template must
have no other session connected before any worker creates a database from it.

For async suites, **configure auto mode and the loop scopes in `pyproject.toml`** —
per-test markers are what `python-testing` forbids, and configuration is what makes the
setting uniform instead of remembered:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
asyncio_default_test_loop_scope = "session"
```

All three keys are real options in pytest-asyncio 1.4.0 (`pytest --help`, *asyncio*
section). Under auto mode a plain `@pytest.fixture` on an async fixture works, and no
`@pytest.mark.asyncio` is needed anywhere.

**What the loop-scope keys buy you** is the thing that bites otherwise: a fixture and
the test consuming it must run on the *same* event loop, and with the default
function-scoped loop a session-scoped async fixture's loop is not the test's loop — a
connection opened there is bound to a loop that is no longer running. Setting both
defaults to the same scope removes the mismatch for every fixture at once.

(Left at pytest-asyncio's own defaults, the plugin is in **strict** mode, where an
async fixture must use `@pytest_asyncio.fixture` and each scope must be declared per
decorator. That is the form to recognise in an existing suite, not the one to write.)

### Where ports come from

The numbers come from
[`../decisions/local_port_allocation_pattern.md`](../decisions/local_port_allocation_pattern.md)
— the ADR owns them, the environment template projects them, and test code reads the
projection. The Python-side plumbing is only that: a settings object (or `os.environ`)
read inside a session-scoped fixture, never a literal in a test.

For an end-to-end server, bind first and read back — never "find a free port, then bind
it later", which races another worker between the two steps:

```python
# tests/api/conftest.py — inside a function-scoped yield fixture
listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listening_socket.bind(("127.0.0.1", 0))   # the kernel assigns the port
bound_port = listening_socket.getsockname()[1]
```

Hand **that same socket** to the server — `uvicorn.Server.run(sockets=[listening_socket])`
serves on it, and `bound_port` is what the test client connects to; the fixture's
teardown closes it. When the test needs no real socket at all, `httpx.ASGITransport`
runs the application in-process and no port is involved.

### Cleanup that survives failure

- **A `yield` fixture's teardown runs after a failing test**, so an assertion failure
  does not leak the database. But an exception raised in *setup*, before the `yield`,
  means the teardown half never runs — so create the resource as the last statement
  before `yield`, and never register cleanup for something not yet created.
- **A killed worker runs no teardown at all.** A worker that dies mid-test (`SIGKILL`,
  an OOM kill, a cancelled CI job) leaves its database and its ports behind; xdist
  reports `worker 'gw0' crashed while running <nodeid>` and the post-`yield` code never
  executes. No fixture — and no `pytest_sessionfinish` in that worker — closes this hole.
- **The practical answer is a name prefix plus a sweep.** Name every isolated resource
  **`<project>_test_<testrun_uid[:8]>_<worker_id>_<uuid7().hex>`** — for example
  `ironbox_test_fa03dd4e_gw0_019ff641d7e273a2aa86344998fb0771`, 58 characters. The prefix
  makes orphans findable
  (`SELECT datname FROM pg_database WHERE datname LIKE '<project>_test_%'`), the run
  segment tells a sweep which names belong to a *live* run, and the time-ordered UUIDv7
  gives each name an age. Drop with `WITH (FORCE)` — a plain `DROP DATABASE` fails with
  `database … is being accessed by other users` whenever a leaked connection survives.
- **The run segment is truncated to 8 characters because PostgreSQL identifiers are
  limited to 63 bytes — and it truncates past that *silently*, with no error.** A full
  32-hex `testrun_uid` plus a full 32-hex `uuid7` is 82 characters, and the 19 bytes
  PostgreSQL discards are the entire random tail: two *distinct* names both store as
  `…_gw0_019ff63b35a07` and the second `CREATE DATABASE` fails with `DuplicateDatabase`.
  Check the arithmetic against your own project prefix — 63 bytes, minus the 48 fixed bytes
  (`_test_` is 6, run segment 8, two separators 2, uuid7 hex 32), minus the worker segment,
  leaves **9 characters for `<project>`** in the worst case, `worker_id` being `master` in
  a non-distributed run and the longest value it takes.
- **Never shorten the `uuid7` to buy room — shorten the project prefix instead.** A
  UUIDv7's randomness lives entirely in its *tail*: within one millisecond CPython 3.14
  holds the first 20 hex characters constant, so `uuid7().hex[:16]` yielded **1 distinct
  value out of 361** generated in that millisecond. A prefix slice of a UUIDv7 is a
  timestamp, not an identifier.
- **The template database is dropped by the same operator sweep, never inside a session.**
  No worker can drop it in session teardown while its siblings are still creating databases
  from it, and a killed worker drops nothing — so every run leaks a ≥7.4 MiB template.
  That is why the template name must sort *outside* the per-test prefix:
  `<project>_tmpl_<testrun_uid[:8]>` does not match `<project>_test_%`, so the sweep can
  reclaim stale per-test databases without ripping a live run's template out from under it,
  and can reclaim stale templates as a separate, explicitly chosen step.
- **Make the sweep an explicit operator command** — the `db-sweep` recipe in `justfile-setup` — never an automatic
  start-of-session step: a prefix sweep cannot tell a leaked database from a concurrent
  run's live one, and at session start it would drop the other worktree's databases out
  from under it.

The per-test fixture that puts all of the above together — function-scoped, so the database
is created and dropped per test, and split in two so the test's own engine is disposed
before the drop runs:

```python
# tests/integration/conftest.py — one database per test
@pytest.fixture
def test_database_url(worker_id, testrun_uid, template_database_name):
    database_name = f"ironbox_test_{testrun_uid[:8]}_{worker_id}_{uuid.uuid7().hex}"
    admin_engine = create_engine(ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:       # AUTOCOMMIT: CREATE DATABASE
        connection.execute(text(                     # cannot run in a transaction
            f'CREATE DATABASE "{database_name}" TEMPLATE "{template_database_name}"'
        ))
    yield f"{BASE_DATABASE_URL}/{database_name}"     # created last before yield
    with admin_engine.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)'))
    admin_engine.dispose()


@pytest.fixture
def database_engine(test_database_url):
    engine = create_engine(test_database_url)
    yield engine
    engine.dispose()        # release connections before the fixture above drops
```

---

## Quick Reference — Invariants

- **Each test creates and destroys its own database.** Acquire it at the start
  and release it at the end of every database test — `TestDatabase::new()` /
  `teardown()` in the Rust example, a function-scoped `yield` fixture in Python.
  Never reuse a database across tests.
- **Every resource name ends in a complete, untruncated UUIDv7.** Database names,
  object keys, entity names with unique constraints — all of them. Never use a
  static, shared, mutable name, and never truncate the UUID to fit an identifier
  limit (63 bytes for a PostgreSQL name) — shorten the other name segments
  instead; see *Mapping to Python*.
- **End-to-end test servers bind port `0`.** The OS assigns a free port;
  the test reads it back. No test hardcodes a host port.
- **New fixtures use env-substitutable host ports.** The `${VAR:-default}`
  form in docker-compose, with the default matching the `dev_environment`
  constant. Never add a bare literal host port to a new service.
- **New test code references fixtures by service name, not container name.**
  Use `docker compose exec <service>` instead of `docker exec
  <literal-container-name>` so the same helper works against any stack
  instance.
- **Every serialized-test group is documented.** (`#[serial(...)]` in the Rust
  example.) It marks a cross-test shared singleton. Record it in the
  integration-testing knowledge base alongside the singleton it guards.
- **Serialization is local to one test process.** `serial_test` orders tests
  within a single `cargo test` process and does not protect against two separate
  processes running against the same shared stack. Where the runner is itself
  multi-process, that limit bites inside a single run — see *Mapping to Python*.

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
- **`python-testing`, `python-project-setup`, and [Python
  conventions](../conventions/python.md)** — the Python delegates for the mapping
  above: the conftest layering and support-module routing the isolation fixtures
  must follow (`python-testing`), the PEP 735 `dev` dependency group where
  `pytest`, `pytest-xdist`, and `pytest-asyncio` are pinned
  (`python-project-setup`), and the uv workspace layout that decides where a
  member's `tests/` tree and its `conftest.py` hierarchy sit (Python
  conventions). **These two documents diverge on the isolation default, and the
  divergence is real rather than a wording difference:** `python-testing`'s
  `tests/integration/conftest.py` ships an `autouse=True` transaction-rollback
  `db_session` fixture project-wide, whereas this pattern's default is a fresh database
  per test. A project must choose one of the two deliberately instead of inheriting both;
  the trade-off is the measured cost in *What the default costs* above.
- **`ci-setup`** — CI runs the integration suite; this pattern is what makes
  the suite safe to run in a CI job without serializing every test. Apply
  `ci-setup` to wire the docker-stack startup into the CI job.
- **`justfile-setup`** — the `just test-integration` and `just up` recipes
  that bring the Docker stack up and run the suite. The justfile is the
  developer-facing entry point to the workflow this pattern describes.
