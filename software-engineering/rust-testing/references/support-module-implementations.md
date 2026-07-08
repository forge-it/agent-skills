# Support Module Implementations

This file contains the complete reference implementations for `tests/common/` and per-category `support/` modules. `/home/cristi/Projects/agent-skills/software-engineering/rust-testing/SKILL.md` is the normative source — the rules for when and how to use these modules live there (Section 15). These implementations are provided here for direct reference by agents writing test-support infrastructure.

## infra.rs — Docker stack and TestDatabase

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

## factories.rs — Cross-level domain object builders

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

## fixtures.rs — Cross-level prerequisite persistence

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

## builders.rs — Service construction

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

## helpers.rs — General-purpose test utilities

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

## constants.rs — Shared test values

```rust
// tests/integration/support/constants.rs
pub const TEST_BUCKET_PREFIX: &str = "myproject-test";
pub const MAX_RETRY_ATTEMPTS: u32 = 3;
pub const DEFAULT_TIMEOUT_MILLISECONDS: u64 = 5000;
```

## db.rs — Import usage in test files

One `super` per directory level between the test file and the category root; cross-category helpers come from `crate::common`.

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
