---
name: bootstrap-pattern
description: >-
  Use when a backend must do work at process startup before it serves traffic —
  seeding reference data or a default admin account, establishing eager
  fail-fast connections, running preflight checks — and you need to decide where
  those side effects live, keep them safe to repeat on every reboot, and keep
  them out of both the composition root and main(). Language-agnostic; Rust
  example included.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.1"
---

# Bootstrap (Startup Tasks) Pattern

## Purpose

**Bootstrap** is the startup phase that prepares *the world* before a service
accepts traffic: seeding required data, opening eager connections, running
preflight checks. It is the side-effecting counterpart to the composition root.

**In one line:** bootstrap answers *what must be true of the world before we
serve traffic?* — it is side-effecting, runs once at startup, and consumes the
already-composed object graph.

That last clause is the key relationship: bootstrap runs *after* construction
and depends on the services the composition root produced (a seeder needs the
repositories and services; it does not build them). So bootstrap lives in the
**infrastructure layer** and is invoked by the entry point as an explicit phase
— never inside the composition root, which must stay pure. (See the companion
[composition root pattern](../project_structure/composition_pattern.md) for the
construction side and the boundary between the two.)

> **Core principle (separation of concerns / single responsibility):**
> *constructing* the graph, *preparing* the world, and *serving* requests are
> three different jobs. Bootstrap owns the middle one and only that one.

## When to Apply

Apply when the service needs side effects at boot:

- **Reference / seed data** must exist for the app to function — a catalog of
  plans/tiers/roles, a default admin account, feature flags.
- **A dependency must be proven live at boot**, not on first use — a pub/sub
  `LISTEN` channel, a broker connection, a cache warm-up.
- **Preflight checks** must pass before serving — required external tools
  present, schema migrated, config coherent.

**When NOT to use:** if startup is just "connect pool, serve" with no data to
seed and nothing to verify eagerly, you don't need a bootstrap module — a couple
of lines in the entry point suffice. Also, **do not** put request-time logic
here: bootstrap runs once, at boot, then never again.

## The Three Sub-Patterns

### 1. Idempotent seeding

A seeder runs on **every** boot, so it must be safe to run when the data already
exists. Two complementary techniques:

- **Database-level:** `INSERT … ON CONFLICT (id) DO NOTHING` (or the engine's
  upsert). Operator-edited rows survive a reseed.
- **Application-level:** attempt the create, and treat the "already exists"
  error as success — skip and move on.

The test for a correct seeder: running it twice leaves the same state as running
it once.

### 2. Dependency-ordered composite seeder

When several things must be seeded, aggregate them behind one `StartupSeeder`
that runs the sub-seeders **in dependency order** (seed the tier catalog before
the accounts that reference a tier). One object owns the order, so the entry
point makes a single `seeder.run()` call.

This is also where each task's **failure policy** is decided explicitly, and the
policies differ on purpose:

- **Abort boot** when the task is a hard precondition — e.g. the tier catalog is
  the runtime source of truth; booting without it is unsafe, so a failure
  `panic`s / returns `Err` and stops startup.
- **Log and continue** when the task is best-effort — e.g. provisioning extras
  for a seed account can fail without making the service unusable.

Decide per task; don't apply one blanket policy.

### 3. Fail-fast eager initialization

For a dependency the service can't work without, establish it **eagerly at
boot** rather than lazily on first use. A failed eager connect aborts startup
with a clear error; a lazy connection that breaks later degrades the feature
*silently*. Prepare the risky resource in bootstrap, then hand the live handle
to the runtime so the rest of the system only ever sees a ready resource.

## Worked Example (Rust)

**Idempotent, fail-fast seeder** (database-level idempotency; failure aborts
boot because the catalog is a hard precondition):

```rust
pub struct TierSeeder { pool: PgPool }

impl TierSeeder {
    pub async fn seed(&self) -> Result<(), TierSeedError> {
        for tier in Tier::all() {
            sqlx::query(
                "INSERT INTO tiers (id, display_name, /* … */)
                 VALUES ($1, $2, /* … */)
                 ON CONFLICT (id) DO NOTHING",   // <-- safe to re-run every boot
            )
            .bind(tier.id().as_str())
            // …
            .execute(&self.pool)
            .await
            .map_err(|error| TierSeedError::Database(error.to_string()))?;  // <-- propagate => abort boot
        }
        Ok(())
    }
}
```

**Application-level idempotency + best-effort sub-step** (skip when the account
already exists; tolerate a provisioning failure):

```rust
async fn seed_account(&self, account: &SeedAccount) {
    let created = self.user_repository.create(&request).await;
    let mut user = match created {
        Ok(user) => user,
        Err(UserRepositoryError::DuplicateEmail { .. }) => {
            tracing::debug!(email = account.email, "default account exists, skipping");
            return;                                   // <-- idempotent: already seeded
        }
        Err(error) => panic!("failed to create seed account: {error}"),  // <-- hard failure
    };

    // Best-effort extra: a failure is logged, not fatal.
    if let Err(error) = self.provisioner.provision(user.id(), account.tier).await {
        tracing::error!(%error, "failed to provision storage for seed account");
    }
}
```

**Composite seeder** — runs sub-seeders in dependency order behind one entry
point:

```rust
pub struct StartupSeeder { tier_seeder: TierSeeder, account_seeder: AccountSeeder }

impl StartupSeeder {
    pub async fn run(self) {
        // Tiers first: accounts reference a tier.
        self.tier_seeder.seed().await
            .expect("tier seed must succeed: the tiers table is the source of truth");
        self.account_seeder.seed().await;            // best-effort within
    }
}
```

**Fail-fast eager initialization** — prove the wake-up path is live before
serving; return the live handle for the runtime to use:

```rust
/// Panics on a failed initial connect/subscribe — the path must be live to boot.
pub async fn prepare(database_url: &str) -> (ConnectivitySseHub, PgListener) {
    let hub = ConnectivitySseHub::new();
    let mut listener = PgListener::connect(database_url).await
        .expect("failed to establish the LISTEN connection");   // <-- fail fast at boot
    listener.listen(CONNECTIVITY_EVENTS_CHANNEL).await
        .expect("failed to LISTEN on the channel");
    (hub, listener)                                  // <-- hand the ready handle to the runtime
}
```

**The entry point** sequences the phases — and bootstrap sits clearly between
construction and launch:

```rust
async fn main() {
    let config = load_config();                          // 1. config
    run_migrations(&pool).await;                         //    (schema preflight)
    let services = create_application_services(/* … */); // 2. compose (pure)

    StartupSeeder::new(/* consumes services */).run().await;  // 3. bootstrap (side effects)
    let (hub, listener) = bootstrap::prepare(&url).await;     //    eager fail-fast

    serve(build_app_state(services, hub), listener).await;    // 4. launch
}
```

## Mapping to Other Backend Languages

The phase and its rules are language-agnostic; only the mechanism changes.

| Concept | Rust | Python | Other |
|---------|------|--------|-------|
| Bootstrap location | `infrastructure/bootstrap/` | a `bootstrap`/`startup` module in infrastructure | a startup module, outside domain/application |
| Idempotent seed (DB) | `ON CONFLICT DO NOTHING` | `INSERT … ON CONFLICT` / `session.merge` | engine upsert |
| Idempotent seed (app) | match the duplicate error, skip | catch `IntegrityError` / check-exists, skip | catch-and-skip |
| Composite + ordering | a `StartupSeeder` struct | a `run_startup()` coroutine calling seeders in order | an init orchestrator |
| Eager fail-fast | `prepare()` panics on connect failure | raise on startup (e.g. FastAPI lifespan / `@app.on_event("startup")`) | a startup hook that raises |
| Invoked from | `main` after composition | the ASGI lifespan / app factory, after building services | the entry point |

In a Python DDD service, the natural home is the framework's startup hook
(FastAPI `lifespan`): build services via the composition package, then `await
run_startup_seeders(services)` and open eager connections — raising on a hard
failure so the process never reports healthy with a broken dependency.

## Quick Reference — Invariants

- **Bootstrap runs once at startup**, before serving — never on the request path.
- **Every seeder is idempotent** — running it twice equals running it once.
- **A composite seeder runs sub-seeders in dependency order**, behind one call.
- **Failure policy is decided per task**: abort boot for hard preconditions, log
  and continue for best-effort tasks.
- **Risky dependencies are initialized eagerly and fail fast**, not lazily and
  silently.
- **Bootstrap lives in infrastructure and consumes the composed graph** — it
  depends on built services/ports; it does not build them.
- **The composition root stays pure**: it constructs, bootstrap side-effects.
  The entry point sequences them.

## Anti-Patterns to Avoid

- **Seeding inside the composition root.** Makes construction impure and
  un-testable. Construction builds; bootstrap prepares.
- **Non-idempotent seeders.** A seeder that throws or duplicates on the second
  boot turns every restart into an incident.
- **Lazy initialization of a must-have dependency.** Deferring a risky connect
  to first use trades a loud boot failure for a silent runtime outage.
- **One blanket failure policy.** Aborting boot on a best-effort task (or
  swallowing a hard precondition failure) — decide each explicitly.
- **Startup logic stranded in `main`.** A growing pile of seed/connect/verify
  statements in the entry point. Extract them into a bootstrap module the entry
  point calls in one or two lines.
- **Bootstrap doing request-time work.** If it runs more than once, it isn't
  bootstrap.

## Relationship to Other Skills

- **[composition root pattern](../project_structure/composition_pattern.md)** —
  the construction phase bootstrap runs after and depends on; defines the
  composition/bootstrap boundary in detail.
- **[runtime worker supervision pattern](runtime_pattern.md)** — the next
  lifecycle phase: background workers start after seeding completes
  (compose → bootstrap → run + drain).
- **`rust-hexagonal-architecture` / `python-ddd`** — bootstrap is an
  infrastructure-layer concern that consumes application services through ports.
- **`database-management`** — schema migration is the preflight that runs before
  seeding; seeders assume the schema already exists.
