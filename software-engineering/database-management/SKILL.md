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

**The database must be empty before the first migration.** Never start with pre-existing tables or data. The first migration should create the complete initial schema from scratch.

```sql
-- CORRECT: First migration creates everything
-- migrations/20260130191544_initial_schema.sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    content TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- INCORRECT: Starting with existing tables
-- The database should NOT have any tables before the first migration runs
```

### 2. First Migration is Comprehensive (CRITICAL)

**The first migration should create all tables, indexes, constraints, and initial data.** This migration is typically large and establishes the complete foundation of your application's data model.

```sql
-- migrations/20260130191544_initial_schema.sql
-- This is a complete, self-contained schema definition

-- Core user tables
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    email VARCHAR(320) NOT NULL UNIQUE,
    username VARCHAR(50) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE user_profiles (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    full_name VARCHAR(255),
    avatar_url TEXT,
    bio TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Application domain tables
CREATE TABLE products (
    id BIGSERIAL PRIMARY KEY,
    sku VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    is_available BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE orders (
    id BIGSERIAL PRIMARY KEY,
    order_number VARCHAR(50) NOT NULL UNIQUE,
    user_id BIGINT NOT NULL REFERENCES users(id),
    total_amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at);

-- Initial data (if needed)
INSERT INTO users (email, username, hashed_password) VALUES
('admin@example.com', 'admin', 'hashed_password_here');
```

### 3. Incremental Changes Only (CRITICAL)

**All migrations after the first must be incremental changes only.** Each migration should make a single, focused change to the schema. Never recreate the entire schema in subsequent migrations.

```sql
-- CORRECT: Incremental changes in separate migrations

-- migrations/20260130192015_add_user_roles.sql
ALTER TABLE users ADD COLUMN role VARCHAR(50) NOT NULL DEFAULT 'user';
CREATE INDEX idx_users_role ON users(role);

-- migrations/20260130192530_create_product_categories.sql
CREATE TABLE product_categories (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

ALTER TABLE products ADD COLUMN category_id BIGINT REFERENCES product_categories(id);
CREATE INDEX idx_products_category_id ON products(category_id);

-- migrations/20260130193045_add_order_shipping.sql
ALTER TABLE orders ADD COLUMN shipping_address TEXT;
ALTER TABLE orders ADD COLUMN shipping_method VARCHAR(100);
ALTER TABLE orders ADD COLUMN shipping_cost DECIMAL(10,2) DEFAULT 0;

-- INCORRECT: Recreating tables in later migrations
-- migrations/20260130193500_recreate_users.sql (WRONG!)
-- DROP TABLE users; -- NEVER do this in production!
-- CREATE TABLE users (...); -- This belongs in the first migration only
```

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

#### Zero-Downtime Principles
1. **Add columns as NULLable first**, then backfill data, then add NOT NULL constraint
2. **Remove columns in multiple steps**: stop using, verify, then remove
3. **Change types carefully**: add new column, migrate data, switch, remove old
4. **Use feature flags** to control new schema usage

```sql
-- Safe column addition pattern
-- Step 1: Add column as NULLable
ALTER TABLE users ADD COLUMN phone_number VARCHAR(20);

-- Step 2: Backfill data (in application code or separate migration)
UPDATE users SET phone_number = 'default' WHERE phone_number IS NULL;

-- Step 3: Add NOT NULL constraint (after all data is populated)
ALTER TABLE users ALTER COLUMN phone_number SET NOT NULL;

-- Safe column removal pattern
-- Step 1: Stop using the column in application code
-- Step 2: Verify no code uses the column (monitor for errors)
-- Step 3: Remove the column
ALTER TABLE users DROP COLUMN old_column_name;
```

### 6. Migration File Naming and Organization

#### Folder Structure (CRITICAL)
**The `migrations/` folder is always at the top level of the project.** It exists at the same level as other top-level directories like `src/`, `tests/`, `docs/`, etc.

```
project-root/
├── migrations/           # Top-level migrations folder
│   ├── 20260130191544_initial_schema.sql
│   ├── 20260130192015_add_user_roles.sql
│   └── 20260130192530_create_product_categories.sql
├── src/
│   └── ...
├── tests/
│   └── ...
├── docs/
│   └── ...
└── Cargo.toml           # or package.json, pyproject.toml, etc.
```

#### Naming Convention (CRITICAL)
Always use the format: `YYYYMMDDHHMMSS_description.sql` (14-digit timestamp followed by underscore and description)

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

### 7. Folder Convention Enforcement

#### Absolute Requirement
- **Always** use `migrations/` as the top-level folder name
- **Never** nest migrations inside `src/`, `app/`, or other subdirectories
- **Never** use different folder names like `db/migrations/`, `database/migrations/`, etc.
- The `migrations/` folder must be directly accessible from the project root

#### Project Layout Examples
```bash
# CORRECT - migrations at top level
/my-project/
├── migrations/
├── src/
├── tests/
└── Cargo.toml

# CORRECT - migrations at top level with other common directories
/my-project/
├── migrations/
├── src/
├── tests/
├── docs/
├── scripts/
└── pyproject.toml

# INCORRECT - migrations nested
/my-project/
├── src/
│   ├── migrations/      # WRONG - should be at top level
│   └── ...
└── Cargo.toml

# INCORRECT - different folder name
/my-project/
├── db/                  # WRONG - should be migrations/
│   └── migrations/
└── Cargo.toml
```

### 8. Rollback Strategy

Every migration should have a corresponding rollback plan. For complex migrations, create separate rollback files.

```sql
-- Migration: migrations/20260130192530_create_product_categories.sql
CREATE TABLE product_categories (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

ALTER TABLE products ADD COLUMN category_id BIGINT REFERENCES product_categories(id);

-- Rollback: migrations/20260130192530_create_product_categories_rollback.sql
ALTER TABLE products DROP COLUMN category_id;
DROP TABLE product_categories;
```

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
- **Always** use `migrations/` at project root level
- **Never** nest or rename the migrations folder
- **Always** use timestamp-based naming: `YYYYMMDDHHMMSS_description.sql`

### First Migration
- Create complete schema from scratch
- Include all tables, indexes, constraints
- Add initial data if necessary
- Test on empty database

### Subsequent Migrations
- One logical change per migration
- Keep migrations small and focused
- Include both up and down directions
- Test with production-like data

### Production Deployment
- Deploy during low-traffic periods
- Monitor performance during migration
- Have rollback plan ready
- Verify application functionality after migration

### Migration Tools
- Use established migration frameworks (Flyway, Liquibase, Django migrations, etc.)
- Ensure the framework supports top-level `migrations/` folder
- Configure the framework to look for migrations in the correct location
- Maintain migration history table
- Never skip migrations
- Apply migrations in order
- Use established migration frameworks (Flyway, Liquibase, Django migrations, etc.)
- Maintain migration history table
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