---
name: database-management
description: Guidelines for managing database schemas and migrations safely. Use when creating or modifying database schemas, writing migration files, or planning schema changes for production deployments.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.4"
---

# Database Management Skill

## Purpose

This skill provides guidelines for managing database schemas and migrations in production environments. It focuses on safe, incremental schema changes that maintain data integrity and support zero-downtime deployments.

## Operating Mode Decision Flow

When touching database schema or migrations, first determine the operating mode:

1. **Greenfield, before production deployment, no real shared data**
   - Start from an empty database.
   - Build the schema exclusively through the initial migration.
   - Fold schema changes back into the initial migration instead of accumulating throwaway migrations.

2. **Brownfield, existing database without a reliable migration history**
   - Do not pretend the database is empty.
   - Choose and document one adoption strategy: baseline, schema capture, or parallel database/schema with gradual migration.
   - From that point onward, make schema changes reproducible from source control.

3. **Production, already deployed, or any real shared data exists**
   - Treat applied migrations as immutable.
   - Create a new focused incremental migration for each schema change.
   - Prefer backward-compatible changes and expand/contract rollout for risky changes.

Then classify the change:

- **Additive changes**: new tables, nullable columns, indexes, or constraints that existing data already satisfies are usually the safest.
- **Destructive changes**: dropping columns/tables, changing types, or tightening constraints should be staged and usually need expand/contract.
- **Large data changes**: prefer a separate, batched, resumable backfill instead of one long blocking migration.

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

Primary keys (CRITICAL):
- Prefer **UUIDv7** for primary keys when supported (for better index locality and write performance characteristics than fully random UUIDs)
- Use **UUIDv4** when UUIDv7 is not available
- Only use auto-incrementing integers when you have a clear reason and have evaluated trade-offs (predictability, sharding/merging difficulty, cross-system uniqueness)

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
- Prefer online/non-blocking variants where the database supports them, such as concurrent index creation.
- For populated tables, prefer staged constraint changes: add nullable or non-validated shape first, backfill/validate, then enforce.
- For large tables, avoid long-running single-shot updates; prefer batched, resumable, observable backfills.
- Keep migrations idempotent where practical, or rely on the migration tool’s exactly-once guarantees.
- Apply migrations through the established migration tool, not by ad hoc production SQL.

### 6. Migration File Naming and Organization

**Choose one canonical migrations location per deployable service and enforce it.** The exact folder name and placement should follow your migration framework and repository layout (especially in monorepos).

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

Every migration must have a documented reversal strategy, but **not every migration should be rolled back via “down” SQL**.

Choose the safest option for the change:
- **Down migration** (safe for additive changes like new tables/columns/indexes when no data is lost)
- **Forward-fix** (preferred when rollback risks data loss; revert application behavior via feature flags and ship a corrective migration)
- **Backup/restore** (for catastrophic cases; ensure you can restore and recover)
- **Expand/contract reversal** (switch application back to old schema path, then clean up later)

Guidelines:
- Require a documented reversal strategy for every migration.
- Prefer **down migrations** only when they are demonstrably safe (typically additive changes where no data is lost).
- Prefer **forward-fix** when rollback risks data loss or inconsistency (revert application behavior via feature flags, then ship a corrective migration).
- Ensure you have a **backup/restore** plan for catastrophic recovery.

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

## Practical Workflow

1. Inspect the project’s migration tool, canonical migrations location, naming convention, and current migration history.
2. Determine whether the target database is greenfield pre-production, brownfield adoption, or production/shared-data.
3. For greenfield pre-production changes, edit the initial migration and reset only local/dev migration state as needed.
4. For production/shared-data changes, create a new incremental migration in the canonical location.
5. Separate schema changes from large data backfills when the data work may be long-running or operationally risky.
6. Add or document validation queries and a reversal strategy.
7. Test on an empty database when bootstrapping matters, and on production-like data when evolving an existing database.
8. Apply migrations through the configured migration framework in order.

## Anti-Patterns to Avoid

1. Treating a brownfield database as if it were empty.
2. Editing, deleting, reordering, or squashing migrations that may already have run in shared environments.
3. Maintaining multiple source-of-truth migration folders for the same deployed unit.
4. Bypassing the migration framework with direct production schema changes.
5. Dropping/recreating production tables to perform ordinary schema evolution.
6. Making a production schema change that breaks the currently deployed application version.
7. Assuming DDL lock behavior or transactional DDL support without checking the database engine and version.
8. Running large backfills as one unobservable, non-resumable operation.
9. Adding or tightening constraints on populated tables without validating existing data.
10. Forcing a timestamp or sequential naming convention when the project’s migration tool requires a different convention.
