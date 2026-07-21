---
name: composition-root-pattern
description: >-
  Use when wiring a backend built on hexagonal / ports-and-adapters or layered
  DDD — deciding where dependency injection and object-graph construction live,
  when main()/startup has grown into a large wiring blob, when adding one
  adapter forces edits in many unrelated places, or when the application layer
  is tempted to import concrete infrastructure. Language-agnostic; Rust example
  included.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.1"
---

# Composition Root Pattern

## Purpose

**In one line:** composition answers *how is the graph wired?* — it is pure,
side-effect-free, and consumes adapters.

A **composition root** (Mark Seemann's term) is the single place in a backend where the object graph
is assembled: concrete infrastructure adapters (repositories, gateways,
notifiers, publishers) are instantiated and injected into the port-typed slots
of the application services. It is the one component allowed to name *both* the
abstract ports and their concrete implementations.

Its job is **construction, not behaviour**. It contains no business logic, no
request handling, and no side effects beyond building objects. Pushing all
wiring into this one ring is what lets every inner layer stay
dependency-inversion clean: the domain and application layers never import an
infrastructure type, because something *outside* them does the injecting.

> **Core principle (separation of concerns / single responsibility):** each
> layer answers one question. The domain answers *what are the rules*, the
> application answers *what are the use cases*, infrastructure answers *how do
> we talk to the outside world*, and the composition root answers *how is it all
> wired together*. Keep those four answers in four different places.

This is the structural counterpart to the architecture skills: hexagonal /
ports-and-adapters and layered DDD tell you how to *split* the code; the
composition root tells you where the splits get *joined back up*.

## When to Apply

Apply this pattern when **all** of these hold:

- The codebase uses ports and adapters or layered DDD (a framework-free domain,
  an application layer of use-case services, and an infrastructure layer of
  adapters).
- There are real external integrations to inject: a database, a message broker,
  third-party gateways, mailers.
- The service graph is non-trivial — more than a handful of services, or
  generic/parameterised services that need concrete types bound once.

Reach for it when you see these **symptoms**:

- `main()` (or the startup function) has become a long wiring blob that mixes
  config loading, object construction, seeding, and server startup.
- Adding one new adapter means editing the entry point, several service
  constructors, and the HTTP/router setup — change ripples everywhere.
- The application layer imports a concrete `Postgres…` / `Smtp…` / `Lapin…`
  type "just to construct it," quietly breaking the dependency rule.
- Construction logic and request-handling logic live in the same file.

**When NOT to use:** scripts, CLIs, or single-purpose utilities with no
meaningful business logic or external integrations. There, a few `let` bindings
in `main` are fine — a composition root would be ceremony without payoff.

## The Problem It Solves

The naive approach wires everything inline in the entry point:

```rust
// ❌ Anti-pattern: the entry point is the composition root, the bootstrapper,
//    AND the server launcher — three responsibilities, one 300-line function.
#[tokio::main]
async fn main() {
    let pool = connect_database().await;
    let user_repo = PostgresUserRepository::new(pool.clone());
    let backup_repo = PostgresBackupRepository::new(pool.clone());
    // ...30 more repositories...
    let auth_service = DefaultAuthService::new(user_repo.clone(), /* 7 args */);
    let backup_service = DefaultBackupService::new(backup_repo.clone(), /* ... */);
    // ...40 more services, each with the full move/clone dance...
    seed_default_accounts(&user_repo).await;        // construction tangled
    let app_state = AppState { auth_service, /* ...40 fields... */ };  // with runtime
    axum::serve(listener, router(app_state)).await; // tangled with launch
}
```

Two things go wrong as this grows:

1. **No single owner for construction.** Wiring leaks into the application layer
   (services constructing their own dependencies) or into infrastructure
   (adapters reaching "up" to grab other adapters). The dependency rule erodes.
2. **One function, many responsibilities.** Construction, startup side effects,
   and server launch are interleaved, so none of them can be read, tested, or
   changed in isolation.

## The Pattern: a Composition Root Split by Responsibility

Put the composition root in its own top-level module, *outside* the application
layer (so the application layer never has to name it). Then split that module by
responsibility rather than letting it become one giant `build()` function. The
following five-part split has proven to scale; smaller projects may collapse
some parts, but the responsibilities stay distinct:

| Part | Responsibility | Holds |
|------|----------------|-------|
| **type vocabulary** | Name each concrete service type once | Type aliases binding generic services to their concrete adapters |
| **bundles** | Define the inputs and the output | The input struct(s) injected by the entry point + the flat output struct of all wired services |
| **builders** | Assemble one cohesive slice of the graph each | Concern-grouped `build_*` functions (identity, backup, billing, …) |
| **factory** | Orchestrate the builders | The single entry function that calls the builders and assembles the output bundle |
| **runtime projection** | Project services into delivery mechanisms | Mapping the output bundle into HTTP state, registering event handlers, spawning workers |

```
                    entry point (main)
                          │  injects InfrastructureAdapters + SecurityProviders
                          ▼
        ┌──────────────── composition root ────────────────┐
        │  factory  ──calls──▶  builders  ──name──▶ aliases │   construction
        │     │                                             │   (no side effects)
        │     └── assembles ──▶  Services (output bundle)    │
        │                            │                       │
        │  runtime projection ◀──────┘                       │   projection into
        │   • build HTTP app state                           │   delivery mechanisms
        │   • register event handlers                        │
        │   • spawn background workers                        │
        └────────────────────────────────────────────────────┘
                          │ returns ready-to-run pieces
                          ▼
                    entry point runs the server
```

The dependency arrows all point **inward and downward**: the composition root
knows the application and infrastructure layers; neither of them knows the
composition root.

### The five parts, by responsibility

1. **Type vocabulary (aliases).** When services are generic over their adapters
   (static dispatch / monomorphisation), the fully-substituted type
   (`DefaultBackupService<PostgresBackupRepository, …>`) is long and repeated.
   Declare a type alias for each, once, here. Every other part of the root
   refers to the short alias. (Skip this part in codebases that wire purely
   through interface/`dyn` references — there are no long types to tame.)

2. **Bundles (inputs + output).** Group what the entry point injects into one or
   two input structs (e.g. `InfrastructureAdapters`, `SecurityProviders`) rather
   than a 12-parameter factory call. Define the output as one flat struct
   (`Services`) holding every wired service. Bundling inputs keeps the factory
   signature **stable** as adapters are added — you add a field, not a positional
   parameter.

3. **Builders (concern-grouped).** Split construction into `build_*` functions,
   each owning one cohesive slice of the graph and returning a small bundle of
   the services it built. This is single-responsibility applied to wiring: a
   reader who only cares about backups reads `build_backup_services` and ignores
   the other 90% of the graph.

4. **Factory (orchestrator).** One public function takes the input bundles,
   builds the foundational services shared across slices, calls each builder in
   dependency order, and spreads the results into the flat output bundle. The
   cross-slice ordering and sharing (which service must exist before another) is
   centralised here and nowhere else.

5. **Runtime projection (wiring).** The composition root — not infrastructure —
   projects the finished bundle into the delivery mechanisms: build the HTTP
   application state, register event handlers, spawn background workers. This is
   what lets the infrastructure layer stay free of any import of the output
   bundle: infrastructure supplies the building blocks (the HTTP state type, the
   dispatcher, the worker runners); the composition root assembles them.

## Worked Example (Rust)

A condensed version of the structure. The root module is deliberately thin —
declarations and re-exports only:

```rust
// composition.rs  — the root: module declarations + the public surface, nothing else.
mod aliases;   // concrete `…Impl` type vocabulary
mod bundle;    // InfrastructureAdapters / SecurityProviders inputs + Services output
mod builders;  // concern-grouped build_* functions
mod factory;   // create_application_services orchestrator
mod wiring;    // project Services into HTTP state / handlers / workers

pub(crate) use aliases::*;
pub use bundle::{InfrastructureAdapters, SecurityProviders, Services};
pub use factory::create_application_services;
pub use wiring::{build_app_state, register_event_handlers, spawn_runtime_workers};
```

**Bundles** — inputs grouped so the factory signature stays stable, plus the flat
output:

```rust
// bundle.rs
pub struct InfrastructureAdapters {
    pub backup_executor: Arc<dyn BackupExecutor>,
    pub event_publisher: Arc<dyn EventPublisher>,
    pub task_publisher: Arc<dyn TaskPublisher>,
    // add an adapter => add a field here, not a positional parameter everywhere
}

pub struct SecurityProviders {
    pub password_hasher: Arc<dyn PasswordHasher>,
    pub token_issuer: Arc<dyn TokenIssuer>,
}

#[derive(Clone)]
pub struct Services {
    pub auth: AuthServiceImpl,
    pub backup: BackupServiceImpl,
    pub backup_orchestrator: BackupOrchestratorImpl,
    // ...every wired service, flat...
}
```

**A concern-grouped builder** — owns one slice, borrows the shared repositories:

```rust
// builders.rs
pub(super) struct IdentityServices {
    pub(super) auth: AuthServiceImpl,
    pub(super) registration: RegistrationServiceImpl,
}

pub(super) fn build_identity_services(
    repositories: &Repositories,
    security: SecurityProviders,
) -> IdentityServices {
    let SecurityProviders { password_hasher, token_issuer } = security;
    let auth = DefaultAuthService::new(repositories.user.clone(), password_hasher.clone(), token_issuer.clone());
    let registration = DefaultRegistrationService::new(repositories.user.clone(), password_hasher);
    IdentityServices { auth, registration }
}
```

**The factory** — orchestrates builders in dependency order and assembles the
flat bundle:

```rust
// factory.rs
pub fn create_application_services(
    repositories: Repositories,
    adapters: InfrastructureAdapters,
    security: SecurityProviders,
) -> Services {
    // Foundational services shared across slices are built first...
    let job = DefaultJobService::new(repositories.job.clone());

    // ...then each concern slice, in dependency order...
    let identity = build_identity_services(&repositories, security);
    let backup = build_backup_services(&repositories, adapters.backup_executor, job.clone());

    // ...and spread into one flat bundle for the entry point to consume.
    Services {
        auth: identity.auth,
        registration: identity.registration,
        backup: backup.service,
        backup_orchestrator: backup.orchestrator,
    }
}
```

**Runtime projection** — the root, not infrastructure, maps services into the
HTTP state:

```rust
// wiring.rs
pub fn build_app_state(services: Services) -> AppState {
    let Services { auth, backup, .. } = services;
    AppState {
        auth_service: Arc::new(auth),
        backup_service: Arc::new(backup),
        // each port-typed slot wrapped once, here
    }
}
```

### Taming generic services with the type vocabulary

When services use static dispatch (generics) rather than `dyn` ports, the
substituted types get long and are repeated across the bundle and the builders.
The aliases part declares each once. This is the one spot where short
upper-case names appear — they are Rust's established convention for *generic
type parameters*, not value bindings:

```rust
// aliases.rs  — write each long monomorphised type exactly once.
pub type AuthServiceImpl =
    DefaultAuthService<PostgresUserRepository, PostgresRefreshTokenRepository, SmtpPasswordResetNotifier>;

// Generic over the parts the entry point still chooses (e.g. the event publisher EP):
pub type BackupOrchestratorImpl<BackupExec, EventPub> =
    DefaultBackupOrchestrator<PostgresScheduleRepository, PostgresBackupRepository, BackupExec, EventPub>;
```

## Mapping to Other Backend Languages

The pattern is about *placement of construction*, so it ports directly. Only the
mechanism changes.

| Concept | Rust | Python | Other |
|---------|------|--------|-------|
| Composition root location | a `composition/` module, outside `application/` | a `composition/` (or `bootstrap/`) package, outside the domain/application packages | a top-level wiring module |
| Ports | traits | `Protocol` / ABC repository interfaces | interfaces |
| Output bundle | `Services` struct | a `Services` dataclass or a small container object | a context/registry object |
| Type vocabulary | type aliases | usually unneeded (no monomorphisation) — skip this part | as needed |
| Runtime projection | build HTTP state, spawn workers | build the FastAPI/Flask app, wire dependency overrides, start workers | framework-specific |

A Python DDD example: a `composition` package whose `create_services()` builds
the SQLAlchemy-backed repositories and injects them into the application
services, returning a `Services` object; the FastAPI layer then reads those
services from app state (or via `Depends`) and never constructs a repository
itself. The rule is identical — the framework-free domain and the application
services never import `infrastructure`; the composition package does the
injecting. (See the `python-ddd` skill for the layer definitions this wires.)

## The Composition / Bootstrap Boundary

Construction is not the same concern as **startup side effects**, and they
belong in different places. Keep them apart:

| | Composition root | Bootstrap / startup tasks |
|---|---|---|
| Question | *How is the graph wired?* | *What must happen to the world before we serve traffic?* |
| Nature | Pure construction, no I/O side effects, repeatable | Side-effecting: seeds data, opens eager connections, runs preflight |
| Examples | build services, project into HTTP state, register handlers | seed the admin account, seed a reference catalog, establish a fail-fast `LISTEN` connection, run migrations |
| Depends on | ports + concrete adapters | the *already-composed* services / ports (it consumes the graph) |
| Lives in | the composition module | the infrastructure layer (e.g. `infrastructure/bootstrap/`) |

The entry point then reads as a short, ordered sequence of named phases —
**load config → construct graph (composition) → run startup tasks (bootstrap) →
launch server** — instead of a wiring blob. Each phase is one named call you can
read and change in isolation. Folding bootstrap into the composition root, or
spilling either back into `main`, is the anti-pattern this boundary prevents.

For how to structure the startup tasks themselves — idempotent seeding,
dependency-ordered composite seeders, fail-fast eager initialization — see the
companion [bootstrap (lifecycle) pattern](../lifecycle/bootstrap_pattern.md).

## Quick Reference — Invariants

- **Only the composition root names both ports and concrete adapters.** Domain
  and application layers import neither the root nor any concrete adapter.
- **The composition root has no business logic and no side effects** — it
  constructs and returns objects; it does not seed, migrate, or serve.
- **Group injected inputs into bundles** so the factory signature is stable
  under change (add a field, not a parameter).
- **One flat output bundle** that the entry point consumes and projects.
- **Concern-grouped builders**, each owning one cohesive slice (single
  responsibility applied to wiring).
- **Cross-slice ordering lives in the factory**, in one place.
- **Project into delivery mechanisms from the root**, so infrastructure never
  reaches up to name the output bundle.
- **Startup side effects live in bootstrap, not the root or `main`.**

## Anti-Patterns to Avoid

- **Wiring in `main`.** The entry point becomes the composition root, the
  bootstrapper, and the launcher at once. Extract construction into the root.
- **Service locator instead of injection.** A global registry that components
  pull dependencies *from* re-hides the graph and defeats the dependency rule.
  The composition root *pushes* dependencies in via constructors.
- **Application-layer self-construction.** A service that `new`s up its own
  `PostgresRepository` drags an infrastructure import into the application layer.
- **One giant `build()` function.** Construction with no concern grouping — the
  exact monolith this pattern decomposes.
- **Bootstrap inside the root.** Seeding or migrations mixed into construction
  makes the root impure and un-testable. Keep startup side effects in bootstrap.
- **Infrastructure reaching up.** An adapter importing the `Services` bundle to
  grab a sibling. Invert it: the root injects what the adapter needs.

## Relationship to Other Skills

- **[bootstrap](../lifecycle/bootstrap_pattern.md) and [runtime worker
  supervision](../lifecycle/runtime_pattern.md)** — the lifecycle phases after
  construction: prepare the world, then run and drain the background workers
  (compose → bootstrap → run + drain). The composition root's runtime projection
  is where the worker-spawning calls live.
- **`rust-hexagonal-architecture` / `python-ddd`** — define the layers and the
  dependency rule this pattern's root sits outside of and joins together.
- **`rust-project-structure`** — where the `composition/` module lives relative
  to `domain/`, `application/`, `infrastructure/`.
- **`rust-architecture-test-setup` / `python-import-linter-setup`** — make the
  central invariant ("application and domain never import infrastructure; only
  the composition root imports both") an automated gate instead of a review
  note. The Rust gate also enforces the reverse direction (no layer imports
  `composition/`) and, via its marker-driven assembly rules, that designated
  concrete adapter construction never escapes the composition root — including
  through hidden `type` aliases or `use … as` re-exports.
