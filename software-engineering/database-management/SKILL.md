---
name: database-management
description: Database schema management and migration strategies for production systems
license: MIT
metadata:
  author: cristian.ciortea@proton.me
  version: "0.0.1"
---

# Database Management Skill

Version: 0.0.1

## Purpose

This skill provides guidelines for managing database schemas and migrations in production environments. It focuses on safe, incremental schema changes that maintain data integrity and support zero-downtime deployments.

## When to Apply

Apply these guidelines when:
- Designing new database schemas
- Planning schema changes for existing applications
- Creating database migrations
- Deploying schema changes to production
- Managing database evolution over time

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

### 3. Incremental Changes Only (CRITICAL)

**All migrations after the first must be incremental changes only.** Each migration should make a single, focused change to the schema. Never recreate the entire schema in subsequent migrations.

Guidelines:
- Keep each migration small and focused
- Prefer schema changes that are safe to apply while the application is running
- Do not drop/recreate production tables as part of “schema evolution”

Primary keys (CRITICAL):
- Prefer **UUIDv7** for primary keys when supported (for better index locality and write performance characteristics than fully random UUIDs)
- Use **UUIDv4** when UUIDv7 is not available
- Only use auto-incrementing integers when you have a clear reason and have evaluated trade-offs (predictability, sharding/merging difficulty, cross-system uniqueness)

### 4. Migration Types and Patterns

#### Additive Changes (Safe)
- Adding new tables
- Adding new columns (with default values or NULLable)
- Adding indexes
- Adding constraints that don't violate existing data

#### Destructive Changes (Require Care)
- Removing columns (deprecate first, remove later)
- Removing tables (ensure no dependencies)
- Changing column types (requires data migration)
- Adding NOT NULL constraints (requires default values)

#### Data Migrations (Separate from Schema)
- Always separate data migrations from schema migrations
- Use transactions for data migrations
- Include rollback plans

### 5. Production Migration Strategy

#### Zero-Downtime Principles (Expand/Contract) (CRITICAL)
For production systems, treat schema changes as a multi-deploy process. The safe default is the **expand/contract** pattern:

1. **Expand**: introduce new schema elements in a backward-compatible way (new nullable columns, new tables, new indexes)
2. **Dual compatibility**: deploy application code that can work with both old and new schema (feature flags help)
3. **Backfill**: migrate existing data in a controlled way (often outside a single transaction; in batches)
4. **Switch reads/writes**: move the application to the new schema
5. **Contract**: remove old schema elements only after verifying they are no longer used

Checklist:
- Expand: introduce new schema elements in a backward-compatible way (new nullable columns, new tables, new indexes)
- Dual compatibility: deploy application code that works with both old and new schema (feature flags help)
- Backfill: migrate existing data in controlled batches; make it resumable and observable
- Switch: move reads/writes to the new schema
- Contract: remove old schema elements only after verifying they are no longer used

#### Operational Safety Notes (CRITICAL)
- Some DDL operations can lock tables and block writes/reads depending on the database engine and version
- Prefer “online”/non-blocking variants where your database supports them (e.g., online index creation)
- For large tables, avoid long-running single-shot updates; backfill in batches and make the process resumable
- Keep migrations idempotent where possible (or rely on your migration tool’s exactly-once guarantees)

### 6. Migration File Naming and Organization

#### Folder Structure (CRITICAL)
**Choose one canonical migrations location per deployable service and enforce it.** The exact folder name and placement should follow your migration framework and repository layout (especially in monorepos).

Examples (all valid depending on framework/project):
- `migrations/` at the service root
- `db/migrate/` (common in some ecosystems)
- `src/<app>/migrations/` (framework-driven layouts)

Key rule: **there must be exactly one authoritative migrations location for the deployed unit**, and CI/CD should run migrations from that location.

```
project-root/
├── migrations/           # Example location (service root)
│   ├── 20260130191544_initial_schema.sql
│   ├── 20260130192015_add_user_roles.sql
│   └── 20260130192530_create_product_categories.sql
├── src/
│   └── ...
├── tests/
│   └── ...
└── ...
```

#### Naming Convention (CRITICAL)
Follow your migration tool’s naming and ordering convention and apply it consistently.

Acceptable common patterns include:
- Timestamp-based: `YYYYMMDDHHMMSS_description.sql`
- Sequential: `0001_description.sql`
- Tool-generated identifiers (when the framework enforces ordering)

Example (timestamp-based):
```
migrations/20260130191544_initial_schema.sql
migrations/20260130192015_add_user_roles.sql
migrations/20260130192530_create_product_categories.sql
migrations/20260130193045_add_order_shipping.sql
```

#### File Structure
```
migrations/
├── 20260130191544_initial_schema.sql
├── 20260130192015_add_user_roles.sql
├── 20260130192530_create_product_categories.sql
├── 20260130193045_add_order_shipping.sql
└── 20260130193500_add_user_preferences.sql
```

### 7. Migration Location Enforcement

#### Absolute Requirements (CRITICAL)
- **Exactly one canonical migrations location per deployable unit**
- **Do not scatter migrations across multiple folders** for the same deployed service
- The location must be configured in your migration tool and enforced in CI/CD
- In monorepos, the canonical location is typically at the **service root**, not necessarily the repository root

#### Project Layout Examples
```bash
# CORRECT - single canonical location (repo with one service)
/my-project/
├── migrations/
├── src/
├── tests/
└── ...

# CORRECT - monorepo with per-service migrations
/monorepo/
├── services/
│   ├── billing/
│   │   ├── migrations/
│   │   └── src/
│   └── identity/
│       ├── migrations/
│       └── src/
└── ...

# INCORRECT - multiple migration folders for the same deployed unit
/my-project/
├── migrations/
├── db/migrations/        # WRONG - ambiguous source of truth
└── ...
```

### 8. Rollback / Reversal Strategy (CRITICAL)

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

### 9. Testing Migrations

#### Pre-production Testing
1. Test on empty database (first migration)
2. Test on copy of production data
3. Test rollback procedures
4. Verify data integrity after migration

#### Migration Validation
```sql
-- After migration validation queries
SELECT COUNT(*) as user_count FROM users;
SELECT column_name FROM information_schema.columns WHERE table_name = 'users';
SELECT indexname FROM pg_indexes WHERE tablename = 'users';
```

## Anti-Patterns to Avoid

1. **Starting with non-empty database**: Always begin with empty database
2. **Large migrations after first**: Keep subsequent migrations small and focused
3. **Mixing schema and data changes**: Separate schema migrations from data migrations
4. **No rollback plan**: Always have a way to revert
5. **Direct production changes**: Never modify production schema directly
6. **Breaking existing queries**: Ensure migrations don't break running applications
7. **Long-running migrations in transaction**: Break large data migrations into batches
8. **Wrong migration folder location**: Never put migrations inside `src/` or other subdirectories
9. **Inconsistent naming**: Always use `YYYYMMDDHHMMSS_description.sql` format
10. **Multiple migration folders**: Only have one `migrations/` folder at project root

## Guidelines

### Folder Structure
- Use a single canonical migrations location per deployable unit (service)
- Do not split migrations for the same service across multiple folders
- Follow the naming/ordering convention required by your migration framework

### First Migration
- Create complete schema from scratch
- Include all tables, indexes, constraints
- Add initial data if necessary
- Test on empty database

### Subsequent Migrations
- One logical change per migration
- Keep migrations small and focused
- Prefer expand/contract for production changes
- Provide a reversal strategy (down migration when safe; otherwise forward-fix/feature-flag/backup strategy)
- Test with production-like data

### Production Deployment
- Deploy during low-traffic periods
- Monitor performance during migration
- Have rollback plan ready
- Verify application functionality after migration

### Migration Tools
- Use an established migration framework (Flyway, Liquibase, Alembic, Django migrations, Rails migrations, etc.)
- Configure the framework to look for migrations in the canonical location for the deployed unit
- Maintain the migration history table/versioning metadata
- Never skip migrations
- Apply migrations in order

### Data Integrity
- Use foreign key constraints
- Maintain referential integrity
- Preserve data during schema changes
- Validate data after migrations

## Process Flow

```
1. Design schema changes
2. Create migration file in `migrations/` folder with timestamp naming
3. Test on development database
4. Test on staging with production data
5. Schedule production deployment
6. Apply migration with monitoring
7. Verify application functionality
8. Document changes
```

### Migration Creation Steps
```
1. Generate timestamp: YYYYMMDDHHMMSS
2. Create file: migrations/YYYYMMDDHHMMSS_description.sql
3. Write SQL for the incremental change
4. Test migration on empty database
5. Test migration on production-like data
6. Create rollback plan if needed
```

### Migration Lifecycle
```
Empty DB → First Migration (complete schema) → Incremental Changes → Production Evolution
```

### Change Management
- Document every schema change
- Track migration dependencies
- Maintain compatibility with running application versions
- Plan for backward compatibility when removing features