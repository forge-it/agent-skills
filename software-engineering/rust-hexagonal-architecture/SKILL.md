---
name: rust-hexagonal-architecture
description: Hexagonal architecture (ports and adapters) patterns for Rust business applications
license: MIT
metadata:
  author: cristian.ciortea@proton.me
  version: "0.0.1"
---

# Hexagonal Architecture Skill

Version: 0.0.1

## Purpose

This skill provides guidelines for implementing hexagonal architecture (ports and adapters) in Rust applications. It focuses on organizing business applications around a central domain, with adapters managing external dependencies. This architecture enables testability, maintainability, and flexibility in swapping implementations.

## When to Apply

Apply these guidelines when:
- Building web services with complex business rules
- Creating applications with multiple external integrations (databases, APIs, message queues)
- Designing systems that need to swap implementations (e.g., different databases)
- Working on projects with multiple developers requiring clear boundaries
- Building applications expected to evolve significantly over time

## When NOT to Apply

Do not apply hexagonal architecture when:
- Writing drivers, embedded code, or microkernels (the domain *is* the hardware)
- Building simple utilities or CLI tools
- Creating CRUD applications with minimal business logic
- Working on high-performance systems where data transformation costs matter
- Building solo projects where mental overhead outweighs abstraction benefits

## Core Principles

### 1. Domain Models Are Canonical (CRITICAL)

Domain models represent your business concepts. They must be independent of transport formats (HTTP, gRPC) and persistence formats (database rows, JSON). Never let external concerns leak into domain types.

```rust
// Good - domain model with business invariants
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Author {
    id: AuthorId,
    name: AuthorName,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AuthorName(String);

impl AuthorName {
    pub fn new(name: &str) -> Result<Self, AuthorNameError> {
        if name.is_empty() {
            return Err(AuthorNameError::Empty);
        }
        if name.len() > 100 {
            return Err(AuthorNameError::TooLong(name.len()));
        }
        Ok(Self(name.to_string()))
    }
}

// Good - separate request model for creation
pub struct CreateAuthorRequest {
    pub name: AuthorName,
}
```

**Key distinction:** Separate request/creation models from persistent entity representations. APIs diverge from domain structures over time, and decoupling prevents cascading changes.

### 2. Ports Define Boundaries (CRITICAL)

Ports are traits that define the interface between your domain and external systems. They remain independent of implementation details. Define ports in the domain or application layer.

```rust
// Good - port defined as a trait
pub trait AuthorRepository: Clone + Send + Sync + 'static {
    fn create(
        &self,
        request: &CreateAuthorRequest,
    ) -> impl Future<Output = Result<Author, CreateAuthorError>> + Send;

    fn find_by_id(
        &self,
        id: &AuthorId,
    ) -> impl Future<Output = Result<Option<Author>, FindAuthorError>> + Send;

    fn find_by_name(
        &self,
        name: &AuthorName,
    ) -> impl Future<Output = Result<Option<Author>, FindAuthorError>> + Send;
}
```

**Trait bounds:** Require `Clone + Send + Sync + 'static` for integration with async runtimes like tokio and web frameworks like axum.

### 3. Adapters Implement Ports (CRITICAL)

Adapters are concrete implementations of ports. They handle the translation between your domain and external systems. Place adapters in the infrastructure layer.

```rust
// Good - adapter implementing the port
#[derive(Debug, Clone)]
pub struct SqliteAuthorRepository {
    pool: sqlx::SqlitePool,
}

impl SqliteAuthorRepository {
    pub async fn new(database_url: &str) -> Result<Self, sqlx::Error> {
        let pool = sqlx::SqlitePool::connect(database_url).await?;
        Ok(Self { pool })
    }
}

impl AuthorRepository for SqliteAuthorRepository {
    async fn create(
        &self,
        request: &CreateAuthorRequest,
    ) -> Result<Author, CreateAuthorError> {
        let id = AuthorId::new();
        
        let result = sqlx::query("INSERT INTO authors (id, name) VALUES (?, ?)")
            .bind(id.as_uuid())
            .bind(request.name.as_str())
            .execute(&self.pool)
            .await;

        match result {
            Ok(_) => Ok(Author::new(id, request.name.clone())),
            Err(sqlx::Error::Database(error)) if error.is_unique_violation() => {
                Err(CreateAuthorError::Duplicate {
                    name: request.name.clone(),
                })
            }
            Err(error) => Err(CreateAuthorError::Unknown(error.into())),
        }
    }

    // ... other methods
}
```

**Wrapping principle:** Encapsulate third-party crates within custom types. Never expose database-specific errors through the port interface.

### 4. Services Orchestrate Business Logic (CRITICAL)

Services coordinate operations across multiple ports. They handle cross-cutting concerns like metrics, notifications, and retry logic. Services should not contain transport or persistence logic.

**Naming convention:** The trait (port) gets the clean name (`AuthorService`) since it defines the abstraction. The concrete struct uses a descriptive prefix (`DefaultAuthorService`) so it's unambiguous even out of context — no import aliases or module-qualified paths needed.

```rust
// Port - the trait gets the clean name
pub trait AuthorService: Clone + Send + Sync + 'static {
    fn create_author(
        &self,
        request: &CreateAuthorRequest,
    ) -> impl Future<Output = Result<Author, CreateAuthorError>> + Send;
}

// Good - concrete service orchestrating business logic
#[derive(Clone)]
pub struct DefaultAuthorService<R, M, N>
where
    R: AuthorRepository,
    M: AuthorMetrics,
    N: AuthorNotifier,
{
    repository: R,
    metrics: M,
    notifier: N,
}

impl<R, M, N> DefaultAuthorService<R, M, N>
where
    R: AuthorRepository,
    M: AuthorMetrics,
    N: AuthorNotifier,
{
    pub fn new(repository: R, metrics: M, notifier: N) -> Self {
        Self {
            repository,
            metrics,
            notifier,
        }
    }
}

impl<R, M, N> AuthorService for DefaultAuthorService<R, M, N>
where
    R: AuthorRepository,
    M: AuthorMetrics,
    N: AuthorNotifier,
{
    pub async fn create_author(
        &self,
        request: &CreateAuthorRequest,
    ) -> Result<Author, CreateAuthorError> {
        let result = self.repository.create(request).await;

        match &result {
            Ok(author) => {
                self.metrics.record_creation_success().await;
                self.notifier.author_created(author).await;
            }
            Err(_) => {
                self.metrics.record_creation_failure().await;
            }
        }

        result
    }
}
```

### 5. Handlers Are Thin Translation Layers (CRITICAL)

HTTP handlers should only handle request/response translation. They deserialize transport data, convert to domain models, invoke services, and transform results back to HTTP responses.

```rust
// Good - thin handler doing only translation
pub async fn create_author<S: AuthorService>(
    State(state): State<AppState<S>>,
    Json(body): Json<CreateAuthorHttpRequest>,
) -> Result<impl IntoResponse, ApiError> {
    // Translate HTTP request to domain request
    let domain_request = body.try_into_domain()?;

    // Invoke service
    let author = state
        .author_service
        .create_author(&domain_request)
        .await?;

    // Translate domain response to HTTP response
    let response = CreateAuthorResponse::from(&author);
    Ok((StatusCode::CREATED, Json(response)))
}

// HTTP request type - separate from domain
#[derive(Deserialize)]
pub struct CreateAuthorHttpRequest {
    pub name: String,
}

impl CreateAuthorHttpRequest {
    pub fn try_into_domain(self) -> Result<CreateAuthorRequest, ValidationError> {
        let name = AuthorName::new(&self.name)?;
        Ok(CreateAuthorRequest { name })
    }
}
```

### 6. Dependencies Point Inward (CRITICAL)

The domain layer has no external dependencies. Application services depend on domain types and port traits. Infrastructure adapters depend on both domain and external crates. Never let domain code import from infrastructure.

```
┌─────────────────────────────────────────────────────────────┐
│                      Infrastructure                          │
│  (HTTP handlers, database adapters, external API clients)   │
│                            │                                 │
│                            ▼                                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                    Application                         │  │
│  │           (Services, use cases, port traits)          │  │
│  │                          │                             │  │
│  │                          ▼                             │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │                    Domain                        │  │  │
│  │  │    (Entities, value objects, domain errors)     │  │  │
│  │  │              (NO EXTERNAL DEPS)                  │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 7. Bootstrap in Main (HIGH)

The `main` function has two responsibilities: bring the application online and clean up once it's done. It constructs adapters, wires them into services, injects services into the server, and runs it. That's all.

**Why minimize main:** `main` composes unmockable dependencies and handles errors by logging and exiting. The less code here, the smaller this testing dead zone. Integration test setup is often subtly different from main — by wrapping the server in your own `HttpServer` type, both main and tests can spin up the app with the config they need, without duplication.

```rust
#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let config = Config::from_env()?;
    tracing_subscriber::fmt::init();

    // Create adapters — main knows *which* implementations to use
    let repository = SqliteAuthorRepository::new(&config.database_url).await?;
    let metrics = PrometheusMetrics::new();
    let notifier = EmailNotifier::new(&config.smtp_url);

    // Wire adapters into the service
    let author_service = DefaultAuthorService::new(repository, metrics, notifier);

    // Inject service into server and run
    let server_config = HttpServerConfig { port: &config.server_port };
    let http_server = HttpServer::new(author_service, server_config).await?;
    http_server.run().await
}
```

**No framework leakage in main.** Even if the server uses axum internally, main doesn't know about axum. The `HttpServer` wrapper encapsulates route configuration, middleware, ports, and timeouts. If axum changes its API, only `HttpServer` internals change — main stays untouched.

```rust
// main.rs imports — all proprietary, no third-party framework types
use hexarch::config::Config;
use hexarch::domain::author::service::DefaultAuthorService;
use hexarch::inbound::http::{HttpServer, HttpServerConfig};
use hexarch::outbound::email_client::EmailNotifier;
use hexarch::outbound::prometheus::PrometheusMetrics;
use hexarch::outbound::sqlite::SqliteAuthorRepository;
```

### 8. Error Types Bridge Layers (HIGH)

Create separate error types for each layer. Domain errors represent business rule violations. Transport errors map domain errors to HTTP responses without leaking implementation details.

```rust
// Domain error - represents business failures
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CreateAuthorError {
    Duplicate { name: AuthorName },
    Unknown(String),
}

impl std::fmt::Display for CreateAuthorError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            CreateAuthorError::Duplicate { name } => {
                write!(formatter, "author with name '{}' already exists", name)
            }
            CreateAuthorError::Unknown(message) => {
                write!(formatter, "unexpected error: {}", message)
            }
        }
    }
}

impl std::error::Error for CreateAuthorError {}

// Transport error - maps to HTTP responses
pub enum ApiError {
    BadRequest(String),
    Conflict(String),
    InternalServerError,
}

impl From<CreateAuthorError> for ApiError {
    fn from(error: CreateAuthorError) -> Self {
        match error {
            CreateAuthorError::Duplicate { name } => {
                ApiError::Conflict(format!("author '{}' already exists", name))
            }
            CreateAuthorError::Unknown(cause) => {
                tracing::error!("unexpected error: {}", cause);
                ApiError::InternalServerError
            }
        }
    }
}
```

## Project Structure

### Recommended Directory Layout (HIGH)

Use modern Rust module convention with `module_name.rs` files. Never use `mod.rs` files.

```
src/
├── lib.rs
├── domain.rs                 # mod domain { ... }
├── domain/
│   ├── author.rs             # mod author { ... }
│   └── author/
│       ├── model.rs          # Author, AuthorId, AuthorName
│       ├── error.rs          # CreateAuthorError, FindAuthorError
│       └── repository.rs     # AuthorRepository trait (port)
├── application.rs            # mod application { ... }
├── application/
│   └── author.rs             # mod author { ... }
│   └── author/
│       ├── service.rs        # AuthorService trait, DefaultAuthorService
│       └── ports.rs          # AuthorMetrics, AuthorNotifier traits
├── infrastructure.rs         # mod infrastructure { ... }
├── infrastructure/
│   ├── http.rs               # mod http { ... }
│   ├── http/
│   │   ├── router.rs
│   │   ├── handlers.rs       # mod handlers { ... }
│   │   ├── handlers/
│   │   │   └── author.rs     # HTTP handlers
│   │   ├── models.rs         # mod models { ... }
│   │   └── models/
│   │       └── author.rs     # HTTP request/response types
│   ├── persistence.rs        # mod persistence { ... }
│   ├── persistence/
│   │   ├── sqlite.rs         # mod sqlite { ... }
│   │   └── sqlite/
│   │       └── author.rs     # SqliteAuthorRepository
│   └── metrics.rs            # mod metrics { ... }
│   └── metrics/
│       └── prometheus.rs     # PrometheusMetrics adapter
└── bin/
    └── server/
        └── main.rs           # Bootstrap and wiring
```

### Alternative Flat Structure (MEDIUM)

For smaller projects, a flatter structure may suffice:

```
src/
├── lib.rs
├── domain.rs                 # All domain types
├── ports.rs                  # All port traits
├── services.rs               # All services
├── adapters.rs               # mod adapters { ... }
├── adapters/
│   ├── sqlite.rs
│   └── http.rs
└── main.rs
```

## Domain Boundary Guidelines

### Rule 1: Business Tangibility (HIGH)

Domains represent distinct business functions. A blogging platform might be a single domain; a large platform like Medium would have separate domains for blogging, identity, billing, and support.

### Rule 2: Atomic Operations (HIGH)

Entities that must change together in a single operation belong in the same domain. If deleting an author requires synchronously deleting their posts, both belong together. If posts can be orphaned temporarily, they can be separate domains.

```rust
// Same domain - must change atomically
impl DefaultAuthorService {
    pub async fn delete_author(&self, id: &AuthorId) -> Result<(), DeleteAuthorError> {
        // Transaction ensures atomicity
        self.repository.delete_with_posts(id).await
    }
}

// Separate domains - eventual consistency acceptable
impl DefaultAuthorService {
    pub async fn delete_author(&self, id: &AuthorId) -> Result<(), DeleteAuthorError> {
        self.repository.delete(id).await?;
        // Async event for other domain
        self.events.publish(AuthorDeleted { id: id.clone() }).await;
        Ok(())
    }
}
```

**Critical insight:** If you leak transactions into your business logic to perform cross-domain operations atomically, your domain boundaries are wrong.

### Rule 3: Start Large (HIGH)

Begin with large domains. Incorrect boundary assumptions are easier to correct within a monolith than across microservices. Decompose only when friction justifies complexity.

## Anti-Patterns to Avoid

1. **Domain contamination**: Adding serde traits to domain models that bypass constructors
2. **Leaky adapters**: Exposing database connection types through port interfaces
3. **Fat handlers**: Putting business logic in HTTP handlers
4. **Premature decomposition**: Splitting into microservices before boundaries stabilize
5. **Transaction leakage**: Passing database transactions through domain layer
6. **Umbrella errors**: Creating module-wide error enums instead of operation-scoped ones
7. **Skipping the service layer**: Having handlers call repositories directly
8. **Infrastructure in domain**: Importing sqlx, axum, or other infrastructure crates in domain modules

## Guidelines

### Layer Responsibilities
- **Domain**: Entities, value objects, domain errors, repository traits (ports)
- **Application**: Services, use case orchestration, application-level ports
- **Infrastructure**: HTTP handlers, database adapters, external API clients, metrics adapters

### Port Design
- Define ports as traits in domain or application layer
- Use `impl Future + Send` for async methods
- Require `Clone + Send + Sync + 'static` bounds for framework compatibility
- Return domain error types, not infrastructure errors

### Adapter Implementation
- Implement ports in infrastructure layer
- Wrap third-party crates in custom types
- Transform infrastructure errors to domain errors
- Keep adapter code focused on translation

### Service Design
- Accept ports via generics or trait objects
- Handle cross-cutting concerns (metrics, notifications)
- Coordinate multiple repository operations
- Keep services focused on single use cases

### Handler Design
- Deserialize transport format to domain types
- Invoke services with domain types
- Transform domain responses to transport format
- Map domain errors to transport errors

### Testing Strategy
- Mock ports for service unit tests
- Test adapters against real external systems
- Focus integration tests on critical paths
- Keep test setup simple with builder patterns

### Migration Path
- Start with monolith using hexagonal architecture
- Let domain boundaries emerge from observed friction
- Extract to microservices only after boundaries stabilize
- Changing port implementations is low-risk once boundaries are solid
