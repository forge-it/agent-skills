---
name: database-management
description: Use when creating or modifying database schemas, writing migration files, or planning schema changes for a deployed system — deciding whether a change folds into the initial migration or ships as an incremental one, staging a risky change as expand/contract, or choosing how a migration is reversed.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.5"
---

# Database Management Skill

## Purpose

Guidelines for managing database schemas and migrations so that schema changes stay safe, incremental, reproducible from source control, and compatible with zero-downtime deployments.

## Operating Mode Decision Flow

Before touching a schema or a migration, inspect the project's migration tool, its canonical migrations location, its naming convention, and the current migration history. Then determine the operating mode:

1. **Greenfield, before production deployment, no real shared data**
   - Start from an empty database.
   - Build the schema exclusively through the initial migration.
   - Fold schema changes back into the initial migration instead of accumulating throwaway migrations (principles 2 and 4).

2. **Brownfield, existing database without a reliable migration history**
   - Do not pretend the database is empty.
   - Choose and document one adoption strategy: baseline, schema capture, or parallel database/schema with gradual migration (principle 1).
   - From that point onward, make schema changes reproducible from source control.

3. **Production, already deployed, or any real shared data exists**
   - Treat applied migrations as immutable.
   - Create a new focused incremental migration for each schema change (principle 3).
   - Prefer backward-compatible changes and expand/contract rollout for risky changes (principle 5).

Then classify the change:

- **Additive changes**: new tables, nullable columns, indexes, or constraints that existing data already satisfies are usually the safest.
- **Destructive changes**: dropping columns/tables, changing types, or tightening constraints should be staged and usually need expand/contract.
- **Large data changes**: prefer a separate, batched, resumable backfill instead of one long blocking migration.

Whatever the mode, every migration carries a documented reversal strategy (principle 7), is tested for its mode (principle 8), and is applied through the migration tool in order — never by ad hoc SQL against a shared environment.

## Core Principles

### 1. Pre-migration State (CRITICAL)

**Greenfield services should start from an empty database and build the schema exclusively through migrations.** This ensures consistent environments and reliable onboarding.

**Brownfield systems (existing databases) require an adoption strategy.** Do not pretend the database is empty. Choose one approach and document it:
- **Baseline**: mark an existing schema version as the starting point, then apply incremental migrations going forward
- **Schema capture**: capture the current schema as an initial migration (often generated), then proceed incrementally
- **Parallel database/schema**: create a new database/schema and migrate traffic/data gradually

Key requirement: **for a given deployed unit, schema changes must be reproducible from source control and consistently applied across environments.**

### 2. First Migration is Self-Contained (CRITICAL)

**The first migration must be sufficient to bootstrap a new environment.** In a greenfield service, this typically means creating the initial schema (tables, indexes, constraints) needed for the application to start.

Guidelines:
- Keep the initial migration understandable; it is the foundation for all environments
- Avoid dialect-specific features unless you explicitly document them as required prerequisites
- Be careful with “automatic” fields (e.g., `updated_at`): the database will not update them automatically unless you implement that behavior (via application code or database mechanisms)

### 3. Incremental Changes After Production (CRITICAL)

**After production deployment, all new migrations must be incremental changes only.** Each migration should make a single, focused change to the schema. Never recreate the entire schema as part of production schema evolution.

Guidelines:
- Keep each migration small and focused
- Prefer schema changes that are safe to apply while the application is running
- Never edit, reorder, delete, or squash migrations that may already have run in a shared environment
- Do not drop/recreate production tables as part of “schema evolution”

### 4. Development Phase: Single Migration Strategy (CRITICAL)

**During the development phase (before production deployment), do not create additional migration files.** Instead, merge all schema changes into the initial schema migration. This keeps the migration history clean and avoids accumulating throwaway migrations that will never run incrementally in production.

Guidelines:
- When a schema change is needed, modify the initial migration file directly to include the new tables, columns, or indexes
- Delete any extra migration files that were created
- Reset the migration version tracker in the development database to point to the initial migration
- Only start creating incremental migrations once the service has been deployed to production and real data exists

**This rule does not apply once the service is in production.** After production deployment, follow the incremental changes principle (section 3).

### 5. Production Migration Strategy (Recommended Default)

For production systems, treat schema changes as a multi-deploy process. The safe default is the **expand/contract** pattern:

1. **Expand**: introduce new schema elements in a backward-compatible way (new nullable columns, new tables, new indexes)
2. **Dual compatibility**: deploy application code that can work with both old and new schema (feature flags help)
3. **Backfill**: migrate existing data in a controlled way (often outside a single transaction; in batches)
4. **Switch reads/writes**: move the application to the new schema
5. **Contract**: remove old schema elements only after verifying they are no longer used

These are strong recommendations, not universal hard rules. Database engines, migration tools, table sizes, traffic patterns, and operational windows differ. If a project uses a different safe approach, follow the local standard and document the reason.

Operational recommendations:
- Check the database engine and version before assuming DDL lock behavior or transactional DDL support.
- Set a short `lock_timeout` (and a `statement_timeout`) on the migration session and retry on failure. A DDL statement waiting for a lock queues behind any long-running transaction, and every query behind it stalls until the lock is granted or abandoned; failing fast confines the outage to the migration instead of the application.
- Prefer online/non-blocking variants where the database supports them, such as concurrent index creation.
- For populated tables, prefer staged constraint changes: add nullable or non-validated shape first, backfill/validate, then enforce.
- For large tables, avoid long-running single-shot updates; prefer batched, resumable, observable backfills.
- Keep migrations idempotent where practical, or rely on the migration tool’s exactly-once guarantees.
- Apply migrations through the established migration tool, not by ad hoc production SQL.

### 6. Migration File Naming and Organization

**Choose one canonical migrations location per deployable service and enforce it.** The exact folder name and placement should follow your migration framework and repository layout (especially in monorepos). The tool is the stack’s: Alembic for a `python-ddd` service, sqlx migrations for the Rust stacks. Its naming and ordering convention wins over any preference stated here.

Examples (all valid depending on framework/project):
- `migrations/` at the service root
- `db/migrate/` (common in some ecosystems)
- `src/<app>/migrations/` (framework-driven layouts)

Rules:
- There must be exactly one authoritative migrations location for a deployed unit.
- Do not scatter migrations for the same service across multiple folders.
- Configure the migration tool and CI/CD to run migrations from the canonical location.
- In monorepos, the canonical location is typically at the service root, not necessarily the repository root.
- Follow the migration tool’s naming and ordering convention consistently.

Acceptable common patterns include:
- Timestamp-based: `YYYYMMDDHHMMSS_description.sql`
- Sequential: `0001_description.sql`
- Tool-generated identifiers (when the framework enforces ordering)

### 7. Rollback / Reversal Strategy (CRITICAL)

Every migration must have a documented reversal strategy, but **not every migration should be rolled back via “down” SQL**. Choose the safest option for the change:

- **Down migration** — only when demonstrably safe: additive changes where no data is lost (new tables, columns, indexes).
- **Forward-fix** — preferred when rollback risks data loss or inconsistency: revert application behavior via feature flags, then ship a corrective migration.
- **Expand/contract reversal** — switch the application back to the old schema path, then clean up later.
- **Backup/restore** — for catastrophic cases; keep a tested restore plan regardless of the option chosen.

### 8. Testing Migrations

Test according to the operating mode:

- For greenfield services, verify a new empty database can be fully bootstrapped from migrations.
- For production changes, test the incremental migration against production-like data.
- Test application compatibility before and after the migration.
- Test the documented reversal strategy where practical.
- Verify data integrity after migration and backfill steps.

Example PostgreSQL validation queries:
```sql
SELECT COUNT(*) as user_count FROM users;
SELECT column_name FROM information_schema.columns WHERE table_name = 'users';
SELECT indexname FROM pg_indexes WHERE tablename = 'users';
```

### 9. Primary Keys (CRITICAL)

- Prefer **UUIDv7** for primary keys: time-ordered, so index locality and write performance beat fully random UUIDs while cross-system uniqueness is kept.
- Generate it where the stack does: PostgreSQL 18 ships `uuidv7()`, Python 3.14 ships `uuid.uuid7()`, and Rust generates it with the `uuid` crate’s `v7` feature. On an older engine, generate in the application rather than falling back to the database’s random UUID.
- Use **UUIDv4** only where UUIDv7 is genuinely unavailable on both sides.
- Use auto-incrementing integers only with a clear reason and evaluated trade-offs (predictability, sharding/merging difficulty, cross-system uniqueness).
