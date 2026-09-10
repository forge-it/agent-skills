---
name: rust-design-idioms
description: Rust-specific design idioms for encoding invariants in the type system and structuring errors. Use when modeling domain types, state machines and ordered workflows, resource acquisition and release, operations gated on a permission check, exclusive resources shared by async tasks, public trait surfaces, parsers over large inputs, or error handling in Rust code.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.5"
---

# Design Idioms Skill

## Purpose

This skill provides guidelines for applying Rust-specific design idioms. It focuses on patterns that leverage Rust's type system to create safer, more expressive code. These idioms help eliminate runtime errors by encoding invariants in the type system.

The rule behind every idiom here: **do not write code that checks whether the program is in a valid state when the types can make the invalid state impossible to construct.** Each idiom is still subject to the KISS test in rust-design-principles: reach for it when the bug it prevents is real in this codebase, not because the mechanism is available.

## When to Apply

Apply these guidelines when:
- Modeling domain concepts with specific validation rules
- Preventing invalid states at compile time
- Working with primitive types that have semantic meaning
- Designing APIs that are hard to misuse
- Defining error types for functions and libraries
- Composing errors from multiple sources
- Enforcing an ordered workflow (initialize, then resolve, then run) at compile time
- Modeling mutually exclusive states that carry different data
- Acquiring something that must be released: locks, transactions, temporary files, reservations
- Gating an operation on proof that a permission or safety check passed
- Exposing a trait others may call but must not implement, or adding methods to a type from another crate
- Sharing one exclusive resource between several async tasks
- Parsing large inputs without allocating

## Core Idioms

### 1. Newtype Pattern (CRITICAL)

Use newtypes to create thin wrapper structs around existing types. This enables type-safe domain modeling and prevents mixing up values of the same underlying type.

```rust
// Bad - primitive obsession, easy to mix up arguments
fn create_user(email: String, password: String) -> User {
    // Which is which? Easy to pass in wrong order
}

// Caller can accidentally swap arguments
create_user(password, email); // Compiles but wrong!

// Good - distinct types prevent mistakes
struct EmailAddress(String);
struct Password(String);

fn create_user(email: EmailAddress, password: Password) -> User {
    // Type system ensures correct argument order
}

// This won't compile - types don't match
create_user(password, email); // Compile error!
```

The same protection applies when two values share an underlying type but mean different things. `u64` cannot tell bytes from milliseconds; `Uuid` cannot tell a user from an order.

```rust
// Bad - every id is a Uuid, so any id fits any parameter
fn load_user(id: Uuid) -> Result<User, LoadError> { /* ... */ }
let order_id: Uuid = order.id();
load_user(order_id); // Compiles. Loads nothing, or the wrong thing.

// Good - one newtype per meaning
struct UserId(Uuid);
struct OrderId(Uuid);
struct TenantId(Uuid);
struct Bytes(u64);
struct Milliseconds(u64);
struct Port(u16);

fn load_user(id: UserId) -> Result<User, LoadError> { /* ... */ }
load_user(order_id); // Compile error: expected UserId, found OrderId
```

### 2. Parse, Don't Validate (CRITICAL)

Enforce validation in constructors so that if an instance exists, it's guaranteed valid. This eliminates defensive checks throughout business logic.

```rust
// Bad - validate everywhere, hope nothing slips through
fn send_email(email: &str) -> Result<(), Error> {
    if !is_valid_email(email) {
        return Err(Error::InvalidEmail);
    }
    // Send email...
}

fn add_to_mailing_list(email: &str) -> Result<(), Error> {
    if !is_valid_email(email) {
        return Err(Error::InvalidEmail);
    }
    // Add to list...
}

// Good - parse once at construction, trust the type afterward
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EmailAddress(String);

#[derive(Debug, Clone, PartialEq, Eq, Error)]
#[error("{0} is not a valid email address")]
pub struct EmailAddressError(String);

impl EmailAddress {
    pub fn new(raw_email: &str) -> Result<Self, EmailAddressError> {
        if is_valid_email(raw_email) {
            Ok(Self(raw_email.to_string()))
        } else {
            Err(EmailAddressError(raw_email.to_string()))
        }
    }
}

// Business logic is clean - no validation needed
fn send_email(email: &EmailAddress) -> Result<(), Error> {
    // Email is guaranteed valid by construction
}

fn add_to_mailing_list(email: &EmailAddress) -> Result<(), Error> {
    // No defensive checks needed
}
```

### 3. Private Inner Types (CRITICAL)

Keep the wrapped field private to prevent bypassing validation. Never expose the inner type directly.

```rust
// Bad - public inner field allows bypassing validation
pub struct EmailAddress(pub String);

// Anyone can create invalid instances
let invalid = EmailAddress("not-an-email".to_string());

// Good - private inner field enforces construction through validated path
pub struct EmailAddress(String);

impl EmailAddress {
    pub fn new(raw: &str) -> Result<Self, EmailAddressError> {
        // Validation logic here
    }
    
    // Provide controlled access to inner value
    pub fn as_str(&self) -> &str {
        &self.0
    }
}
```

### 4. Canonical Constructor (CRITICAL)

All ways to construct the newtype should delegate to a single canonical constructor. Never duplicate validation logic.

```rust
// Bad - duplicated validation logic
impl EmailAddress {
    pub fn new(raw: &str) -> Result<Self, EmailAddressError> {
        if is_valid_email(raw) {
            Ok(Self(raw.to_string()))
        } else {
            Err(EmailAddressError(raw.to_string()))
        }
    }
}

impl TryFrom<String> for EmailAddress {
    type Error = EmailAddressError;
    
    fn try_from(value: String) -> Result<Self, Self::Error> {
        // Duplicated validation - bug waiting to happen
        if is_valid_email(&value) {
            Ok(Self(value))
        } else {
            Err(EmailAddressError(value))
        }
    }
}

// Good - single source of truth for validation
impl EmailAddress {
    pub fn new(raw: &str) -> Result<Self, EmailAddressError> {
        if is_valid_email(raw) {
            Ok(Self(raw.to_string()))
        } else {
            Err(EmailAddressError(raw.to_string()))
        }
    }
}

impl TryFrom<String> for EmailAddress {
    type Error = EmailAddressError;
    
    fn try_from(value: String) -> Result<Self, Self::Error> {
        Self::new(&value) // Delegates to canonical constructor
    }
}

impl TryFrom<&str> for EmailAddress {
    type Error = EmailAddressError;
    
    fn try_from(value: &str) -> Result<Self, Self::Error> {
        Self::new(value) // Delegates to canonical constructor
    }
}
```

### 5. Essential Trait Implementations (HIGH)

Implement common traits to make newtypes ergonomic. This prevents downstream users from needing their own wrappers due to the Orphan Rule.

```rust
// Good - comprehensive trait implementations
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct UserId(Uuid);

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct AccountNumber(String);

// Implement Display manually for custom formatting
impl std::fmt::Display for EmailAddress {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "{}", self.0)
    }
}
```

**Standard derives to consider:**
- `Debug` - Almost always needed
- `Clone` - Usually needed for value types
- `PartialEq, Eq` - For equality comparisons
- `PartialOrd, Ord` - If ordering makes sense
- `Hash` - If used as HashMap/HashSet key

Capability tokens (Idiom 20) are the exception: never derive `Clone` or `Default` on one, since each is a way to obtain a token without the check.

### 6. Conversion Traits (HIGH)

Implement conversion traits for ergonomic interoperability. Use `From` for infallible conversions and `TryFrom` for fallible ones.

```rust
// Good - conversion traits for ergonomic API
impl From<EmailAddress> for String {
    fn from(email: EmailAddress) -> Self {
        email.0
    }
}

impl TryFrom<&str> for EmailAddress {
    type Error = EmailAddressError;
    
    fn try_from(value: &str) -> Result<Self, Self::Error> {
        Self::new(value)
    }
}

// Usage becomes ergonomic
let email: EmailAddress = "user@example.com".try_into()?;
let raw: String = email.into();
```

### 7. Accessor Traits (MEDIUM)

Use `AsRef` for borrowing access to the inner type. Use `Deref` cautiously as it significantly expands the public interface.

```rust
// Good - AsRef for controlled access
impl AsRef<str> for EmailAddress {
    fn as_ref(&self) -> &str {
        &self.0
    }
}

// Now works with any function expecting &str
fn log_string(value: impl AsRef<str>) {
    println!("{}", value.as_ref());
}

log_string(&email); // Works!
```

**Deref Considerations:**

```rust
// Careful - Deref exposes all inner type methods
impl std::ops::Deref for EmailAddress {
    type Target = str;
    
    fn deref(&self) -> &Self::Target {
        &self.0
    }
}

// Now ALL str methods are available on EmailAddress
email.len();           // Ok
email.to_uppercase();  // Maybe not intended
email.split('@');      // Probably not intended
```

Only implement `Deref` when you intentionally want to expose the inner type's full interface.

### 8. Unchecked Constructors for Trusted Data (MEDIUM)

When data comes from trusted sources where validation already occurred (like database reads), provide an unchecked constructor following standard library conventions.

```rust
impl EmailAddress {
    pub fn new(raw: &str) -> Result<Self, EmailAddressError> {
        if is_valid_email(raw) {
            Ok(Self(raw.to_string()))
        } else {
            Err(EmailAddressError(raw.to_string()))
        }
    }
    
    /// Creates an EmailAddress without validation.
    /// 
    /// # Safety
    /// 
    /// The caller must ensure the input is a valid email address.
    /// Use only for data from trusted sources (e.g., database reads)
    /// where validation was performed on write.
    pub fn new_unchecked(raw: String) -> Self {
        Self(raw)
    }
}

// Usage - only from trusted sources
let email_from_db = EmailAddress::new_unchecked(row.email);
```

### 9. Preserve Invariants in Mutations (HIGH)

If the newtype has invariants, ensure all mutable operations maintain those constraints.

```rust
// Good - NonEmptyVec maintains its invariant
pub struct NonEmptyVec<T>(Vec<T>);

impl<T> NonEmptyVec<T> {
    pub fn new(first: T) -> Self {
        Self(vec![first])
    }
    
    pub fn push(&mut self, item: T) {
        self.0.push(item); // Safe - can only add elements
    }
    
    // Returns Option to prevent removing last element
    pub fn pop(&mut self) -> Option<T> {
        if self.0.len() > 1 {
            self.0.pop()
        } else {
            None // Preserve non-empty invariant
        }
    }
    
    pub fn first(&self) -> &T {
        // Safe - guaranteed to have at least one element
        &self.0[0]
    }
}
```

### 10. Config Structs for Complex Construction (CRITICAL)

When a constructor or function takes more than 3-4 arguments, use a config struct instead of positional parameters. Long positional argument lists are unreadable, error-prone, and resist refactoring — even when every argument has a distinct type.

```rust
// Bad - positional argument soup
let schedule = Schedule::new(
    ScheduleId::new(),
    ScheduleName::new("daily-postgres-backup")?,
    CronExpression::new("0 0 2 * * *")?,
    BackupStrategy::Dump,
    SourceType::PostgreSql,
    Some(Host::new("db-host")?),
    Some(DatabaseName::new("production")?),
    None,
    Some(SecretName::new("postgres-credentials")?),
    DestinationGatewayType::S3,
    None,
    Some(BucketName::new("my-backups")?),
    Some(Directory::new("/postgres/daily")?),
    Some(SecretName::new("aws-credentials")?),
    Some(RetentionCount::new(24)?),
    Some(RetentionCount::new(7)?),
    Some(RetentionCount::new(4)?),
    Some(RetentionCount::new(6)?),
    true,
    now,
    now,
);
// No human can tell which None/Some is which.
// Swapping two arguments may still compile.
// Rust's type system cannot save you from argument order.

// Good - config struct with named fields
let schedule = Schedule::new(ScheduleConfig {
    id: ScheduleId::new(),
    name: ScheduleName::new("daily-postgres-backup")?,
    cron: CronExpression::new("0 0 2 * * *")?,
    backup_strategy: BackupStrategy::Dump,
    source: SourceConfig::PostgreSql {
        host: Host::new("db-host")?,
        database: DatabaseName::new("production")?,
        secret: SecretName::new("postgres-credentials")?,
    },
    destination: DestinationConfig::S3 {
        bucket: BucketName::new("my-backups")?,
        directory: Directory::new("/postgres/daily")?,
        secret: SecretName::new("aws-credentials")?,
    },
    retention: RetentionConfig {
        daily: Some(RetentionCount::new(24)?),
        weekly: Some(RetentionCount::new(7)?),
        monthly: Some(RetentionCount::new(4)?),
        yearly: Some(RetentionCount::new(6)?),
    },
    enabled: true,
    created_at: now,
    updated_at: now,
});
// Every field is labeled. Related fields are grouped.
// Impossible to silently swap arguments.
// A kind plus the Options that depend on it (source_type + host/database/secret)
// is one enum with per-variant data, not a struct of Options (Idiom 18).
```

**Why this matters:**
- Named fields are self-documenting — no need to count parameter positions
- Related fields can be grouped into sub-structs for clarity
- Adding or removing fields is a compiler-guided refactor, not a silent bug
- `None, None, Some(...), None` sequences become meaningful: `weekly: None, monthly: Some(...)`
- Code review becomes possible — reviewers can actually verify correctness

**When positional arguments are fine:**
- 1 argument — always fine, no ambiguity possible
- 2-3 arguments — fine when each has a distinct type and the call reads clearly

**When to use a config struct:**
- Constructors or functions with more than 3-4 parameters
- Any function with multiple `Option` parameters
- Any function with multiple parameters of the same type (even newtypes don't help when you have `Some(SecretName)` twice)

### 11. Structured Error Types (CRITICAL)

Design error types as enums that codify all possible failure states. This makes function signatures self-documenting and enables programmatic error handling via pattern matching.

```rust
// Bad - dynamic error loses structure
fn parse_date(input: &str) -> Result<Date, Box<dyn std::error::Error>> {
    // Callers can't pattern match on specific failures
}

// Good - structured enum captures all failure modes
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DateError {
    InvalidMonth(u8),
    InvalidDay { month: u8, day: u8 },
    InvalidYear(i32),
}

impl std::fmt::Display for DateError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            DateError::InvalidMonth(month) => {
                write!(formatter, "month {} is not in range 1-12", month)
            }
            DateError::InvalidDay { month, day } => {
                write!(formatter, "day {} is invalid for month {}", day, month)
            }
            DateError::InvalidYear(year) => {
                write!(formatter, "year {} is out of supported range", year)
            }
        }
    }
}

impl std::error::Error for DateError {}

fn parse_date(input: &str) -> Result<Date, DateError> {
    // Callers can handle specific cases
}
```

### 12. Manual Error Types by Default (CRITICAL)

Implement the `std::error::Error` trait manually by default. Manual implementation gives full control over error types, avoids hidden macro magic, and keeps dependencies minimal — prefer it in greenfield code and wherever the project has not already standardized on an error crate.

If the project already depends on `thiserror` or `anyhow` (check `Cargo.toml`), follow the project and use them: consistency within a codebase beats the manual-implementation preference. Do not add `thiserror` or `anyhow` as a *new* dependency just to avoid writing the trait by hand.

```rust
// Default (greenfield, or no error crate already in use) - manual implementation
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MyError {
    InvalidInput(String),
    NotFound { id: u64 },
}

impl std::fmt::Display for MyError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            MyError::InvalidInput(input) => {
                write!(formatter, "invalid input: {}", input)
            }
            MyError::NotFound { id } => {
                write!(formatter, "resource with id {} not found", id)
            }
        }
    }
}

impl std::error::Error for MyError {}

// Acceptable when the project ALREADY depends on thiserror
#[derive(Debug, thiserror::Error)]
pub enum MyError {
    #[error("invalid input: {0}")]
    InvalidInput(String),
    #[error("resource with id {id} not found")]
    NotFound { id: u64 },
}
```

### 13. Compose Errors with Wrapper Enums (HIGH)

When a function can fail with multiple error types, create a wrapper enum that composes them. Implement `From` for automatic conversion with the `?` operator.

```rust
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DateError {
    InvalidMonth(u8),
    InvalidDay { month: u8, day: u8 },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TimeError {
    InvalidHour(u8),
    InvalidMinute(u8),
}

// Wrapper enum composes both error types
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DateTimeError {
    Date(DateError),
    Time(TimeError),
}

impl std::fmt::Display for DateTimeError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            DateTimeError::Date(error) => write!(formatter, "{}", error),
            DateTimeError::Time(error) => write!(formatter, "{}", error),
        }
    }
}

impl std::error::Error for DateTimeError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            DateTimeError::Date(error) => Some(error),
            DateTimeError::Time(error) => Some(error),
        }
    }
}

// From implementations enable ? operator
impl From<DateError> for DateTimeError {
    fn from(error: DateError) -> Self {
        DateTimeError::Date(error)
    }
}

impl From<TimeError> for DateTimeError {
    fn from(error: TimeError) -> Self {
        DateTimeError::Time(error)
    }
}

// Now ? works seamlessly
fn parse_datetime(date_str: &str, time_str: &str) -> Result<DateTime, DateTimeError> {
    let date = parse_date(date_str)?;  // DateError -> DateTimeError
    let time = parse_time(time_str)?;  // TimeError -> DateTimeError
    Ok(DateTime { date, time })
}
```

### 14. Scoped Error Types (HIGH)

Design error types scoped to specific operations rather than creating module-wide umbrella errors. Each function or type should have errors capturing only relevant failure modes.

```rust
// Bad - umbrella error for entire module
pub enum BackupError {
    IoError(std::io::Error),
    NetworkError(NetworkError),
    ParseError(ParseError),
    ValidationError(String),
    CompressionError(CompressionError),
    EncryptionError(EncryptionError),
    // Every function returns this, most variants impossible for most functions
}

// Good - scoped errors per operation
pub enum BackupCreateError {
    SourceNotFound(PathBuf),
    InsufficientSpace { required: u64, available: u64 },
    CompressionFailed(CompressionError),
}

pub enum BackupRestoreError {
    BackupNotFound(BackupId),
    DestinationNotWritable(PathBuf),
    IntegrityCheckFailed { expected: Hash, actual: Hash },
}

pub enum BackupListError {
    RepositoryNotAccessible(PathBuf),
}
```

### 15. Error Context Without Losing Structure (MEDIUM)

Add context to errors while preserving the ability to match on specific variants. Use wrapper variants or dedicated context fields.

```rust
// Good - context as wrapper variant
#[derive(Debug)]
pub enum FileProcessError {
    Read { path: PathBuf, source: std::io::Error },
    Parse { path: PathBuf, line: usize, source: ParseError },
    Validation { path: PathBuf, source: ValidationError },
}

impl std::fmt::Display for FileProcessError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            FileProcessError::Read { path, .. } => {
                write!(formatter, "failed to read file: {}", path.display())
            }
            FileProcessError::Parse { path, line, .. } => {
                write!(formatter, "parse error in {} at line {}", path.display(), line)
            }
            FileProcessError::Validation { path, .. } => {
                write!(formatter, "validation failed for {}", path.display())
            }
        }
    }
}

impl std::error::Error for FileProcessError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            FileProcessError::Read { source, .. } => Some(source),
            FileProcessError::Parse { source, .. } => Some(source),
            FileProcessError::Validation { source, .. } => Some(source),
        }
    }
}
```

### 16. Library vs Application Error Handling (MEDIUM)

Libraries should return structured, specific error types. Applications can use more dynamic approaches internally but should never expose them in public APIs.

```rust
// Library code - always structured errors
pub fn parse_config(path: &Path) -> Result<Config, ConfigError> {
    // Returns specific, matchable error type
}

// Application code - can use Box<dyn Error> internally for convenience
fn main() {
    if let Err(error) = run() {
        eprintln!("Error: {}", error);
        let mut source = error.source();
        while let Some(cause) = source {
            eprintln!("Caused by: {}", cause);
            source = cause.source();
        }
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let config = parse_config(Path::new("config.toml"))?;
    // Internal application code can be more flexible
    Ok(())
}
```

### 17. Typestate: Encode Workflow Position in the Type (CRITICAL)

When an object must pass through an ordered sequence of steps, and calling a step out of order is a programming error, make the current step part of the object's type. Each transition consumes `self` and returns the next step's type, so the compiler rejects out-of-order calls and rejects reuse of a stale step.

```rust
// Bad - runtime flags; every method re-checks the sequence, every caller must remember it
struct PackageTransaction {
    handle: TransactionHandle,
    repositories_loaded: bool,
    resolved: bool,
}

impl PackageTransaction {
    fn run(&mut self) -> Result<TransactionReport, RunError> {
        if !self.repositories_loaded {
            return Err(RunError::RepositoriesNotLoaded);
        }
        if !self.resolved {
            return Err(RunError::NotResolved);
        }
        // ...
    }
}

// Good - the step is the type; an out-of-order call is a missing method
use std::marker::PhantomData;

struct Created;
struct RepositoriesLoaded;
struct Resolved;

struct PackageTransaction<Step> {
    handle: TransactionHandle,
    _step: PhantomData<Step>,
}

impl PackageTransaction<Created> {
    fn new(handle: TransactionHandle) -> Self {
        Self { handle, _step: PhantomData }
    }

    fn load_repositories(self) -> Result<PackageTransaction<RepositoriesLoaded>, LoadError> {
        self.handle.load_repositories()?;
        Ok(PackageTransaction { handle: self.handle, _step: PhantomData })
    }
}

impl PackageTransaction<RepositoriesLoaded> {
    fn resolve(self) -> Result<PackageTransaction<Resolved>, ResolveError> {
        self.handle.resolve()?;
        Ok(PackageTransaction { handle: self.handle, _step: PhantomData })
    }
}

impl PackageTransaction<Resolved> {
    fn run(self) -> Result<TransactionReport, RunError> {
        // `self` is consumed: the same transaction cannot run twice
        self.handle.run()
    }
}

// Compiles - the only order that exists
let report = PackageTransaction::new(handle)
    .load_repositories()?
    .resolve()?
    .run()?;

// Does not compile - PackageTransaction<Created> has no run()
PackageTransaction::new(handle).run();
```

Shape rules:
- Marker types are empty structs (`struct Resolved;`). Keep them private unless callers must name the state in their own signatures.
- `PhantomData<Step>` records the marker without storing a value. It occupies zero bytes; the state exists only at compile time.
- Transitions take `self` by value, never `&mut self`. With `&mut self` the old type stays alive after the call and the compiler can no longer prevent reuse.
- When a step carries data the earlier steps do not have (a resolved plan), give the marker type a field (`struct Resolved { plan: TransactionPlan }`) and store the marker as a real field, `step: Step`, in place of `_step: PhantomData<Step>`. The earlier markers stay empty. The walkthrough shows this shape.

**Builders with required fields** are typestate applied to construction: `RequestBuilder<MissingUrl>` becomes `RequestBuilder<HasUrl>` after `.url(...)`, and only `RequestBuilder<HasUrl>` has `build()`. Use this only when construction has ordered or mandatory steps that a plain struct cannot express. When the fields are independent and all known up front, Idiom 10 (config struct) is the answer: a struct literal already makes every required field mandatory, without a generic parameter per field.

**When NOT to apply:**
- The sequence has one step, or the steps may legally run in any order. A plain method set is enough.
- The state changes at runtime on information the compiler cannot see (a job that becomes `Running`, then `Failed` or `Completed` depending on what happened). That is a runtime state machine: one enum (Idiom 18), not typestate.
- Objects in different steps must live in one collection or behind one `dyn` trait. The type would have to be erased, which removes the guarantee.

The full walkthrough (why a generic parameter carries the state, what `PhantomData` does, why `self` and not `&mut self`, how to map a real workflow) is in `references/typestate-walkthrough.md`.

**Rationale:** A boolean flag records a fact the compiler cannot read, so every method re-checks it and every caller must remember the order. Typestate turns "was this called too early?" into a missing method at compile time, and consuming `self` turns "was this called twice?" into a use-after-move error.

### 18. Mutually Exclusive States Are One Enum (CRITICAL)

When several `bool` or `Option` fields together describe which state something is in, and only some combinations are meaningful, replace them with one enum whose variants carry only the data valid in that state.

```rust
// Bad - three flags give eight combinations; three are meaningful
struct Job {
    id: JobId,
    running: bool,
    failed: bool,
    completed: bool,
    started_at: Option<Instant>,
    error: Option<JobError>,
    output: Option<JobOutput>,
}
// running && failed && completed compiles. What does it mean?
// completed == true with output == None compiles too, and someone will unwrap() it.

// Good - one value is one valid state; each state owns exactly its own data
enum JobState {
    Pending,
    Running { started_at: Instant },
    Failed { error: JobError },
    Completed { output: JobOutput },
}

struct Job {
    id: JobId,
    state: JobState,
}

impl Job {
    fn output(&self) -> Option<&JobOutput> {
        match &self.state {
            JobState::Completed { output } => Some(output),
            JobState::Pending | JobState::Running { .. } | JobState::Failed { .. } => None,
        }
    }
}
```

Signs that flags should become an enum:
- Two or more `bool` fields where setting one implies clearing another.
- An `Option` field that is `Some` only while some `bool` is `true`.
- A comment, assertion, or validation function documenting which combinations are allowed.

**Construction-time config is not exempt.** A config struct (Idiom 10) holding a kind field plus `Option`s that are `Some` only for some kinds has the same disease. The kind becomes an enum and the dependent fields move onto its variants: `SourceConfig::PostgreSql { host, database, secret }`, not `source_type` beside three `Option`s.

**Boundary with rust-code-style Rule 13.** Rule 13 turns a closed set of *string names* into an enum. This idiom turns a set of *flag and optional fields* into an enum and moves each state's data onto its variant. The smell for Rule 13 is `status == "failed"`; the smell for this idiom is `if job.failed && !job.completed`.

**Boundary with Idiom 17.** `JobState` changes at runtime on information the compiler does not have, so the enum is the right tool. Typestate is for sequences fixed at compile time (load, then resolve, then run) where a wrong order is a programming error, not a runtime outcome.

**Rationale:** Independent flags let the representable states grow as two to the power of the flag count while the meaningful states stay few. The gap is where bugs live: code that must handle, or silently ignores, combinations that should never exist. The enum makes the representable set equal to the meaningful set, and each variant's payload proves the data is present without an `unwrap()`.

### 19. RAII Guards: Release in Drop (HIGH)

When acquiring something that must be released (a lock, a transaction, a temporary file, a reservation, a mount, a metrics timer), return a guard value whose `Drop` performs the release. Release then happens on every exit path, including `?` early returns and panics, without the caller remembering it.

```rust
// Bad - release is the caller's job; the early return leaks the lock
fn apply_upgrade(lock: &RepositoryLock) -> Result<(), UpgradeError> {
    lock.acquire()?;
    let plan = build_plan()?;      // Err here: the lock is never released
    execute(plan)?;
    lock.release();
    Ok(())
}

// Good - the guard releases when it goes out of scope, on every path
struct RepositoryLockGuard<'lock> {
    lock: &'lock RepositoryLock,
}

impl Drop for RepositoryLockGuard<'_> {
    fn drop(&mut self) {
        self.lock.release();
    }
}

impl RepositoryLock {
    fn acquire(&self) -> Result<RepositoryLockGuard<'_>, LockError> {
        self.try_lock()?;
        Ok(RepositoryLockGuard { lock: self })
    }
}

fn apply_upgrade(lock: &RepositoryLock) -> Result<(), UpgradeError> {
    let _guard = lock.acquire()?;
    let plan = build_plan()?;      // Err here: _guard drops, the lock is released
    execute(plan)?;
    Ok(())
}                                  // success: _guard drops here
```

**Commit-or-rollback guards.** A transaction guard rolls back in `Drop` unless `commit(self)` ran. `commit` consumes the guard, so nothing can touch the transaction after it.

```rust
struct Transaction<'connection> {
    connection: &'connection Connection,
    committed: bool,
}

impl Transaction<'_> {
    fn commit(mut self) -> Result<(), CommitError> {
        self.connection.execute("COMMIT")?;
        self.committed = true;
        Ok(())
    }
}

impl Drop for Transaction<'_> {
    fn drop(&mut self) {
        if !self.committed {
            // Drop cannot return an error; a failed rollback can only be reported
            if let Err(rollback_error) = self.connection.execute("ROLLBACK") {
                tracing::error!("transaction rollback failed: {rollback_error}");
            }
        }
    }
}
```

Shape rules:
- Bind the guard to a named variable: `let _guard = lock.acquire()?;`. Writing `let _ = lock.acquire()?;` drops the guard on that same line and releases immediately.
- `Drop` cannot return an error and cannot `.await`. When release can fail in a way the caller must handle, or must await, provide an explicit `release(self) -> Result<(), ReleaseError>` (or `async fn release(self)`) and keep `Drop` as the best-effort fallback that reports.
- A guard never outlives what it guards: borrow the resource (`&'lock RepositoryLock`) or hold an `Arc` to it.

**When NOT to apply:** the resource already has a guard from the standard library or the runtime (`File`, `TcpStream`, `MutexGuard`, `RwLockReadGuard`). Do not wrap what is already released on drop.

**Rationale:** Cleanup written as a trailing statement runs only on the path the author was thinking about. Cleanup in `Drop` runs on the paths nobody was thinking about.

### 20. Capability Tokens: Require Proof, Not a Check (HIGH)

When an operation is allowed only after some check passed (an authorization decision, maintenance mode, an exclusive lock, a reboot approval), make the check return a token type that only it can construct, and make the operation take the token as a parameter. Code that did not run the check has no token and cannot call the operation.

```rust
// Bad - the operation trusts every caller to have checked
fn delete_package(user: &User, package: &Package) -> Result<(), DeleteError> {
    // Did the handler call user.can_write()? Every reviewer must verify every call site.
}

// Good - the operation demands proof; the proof can only come from the check
pub struct WritePermission {
    _private: (),   // no public constructor: only this module can create one
}

pub fn authorize_write(user: &User, policy: &Policy) -> Result<WritePermission, Forbidden> {
    if policy.allows_write(user) {
        Ok(WritePermission { _private: () })
    } else {
        Err(Forbidden::WriteDenied { user: user.id() })
    }
}

fn delete_package(_permission: &WritePermission, package: &Package) -> Result<(), DeleteError> {
    // No check here. Holding a WritePermission is the check.
}
```

Shape rules:
- The token has a private field and no public constructor other than the check. `pub struct Token;` with no fields can be built by anyone as `Token`; the `_private: ()` field closes that door.
- One-shot operations take the token by value (`permit: RebootPermit`) so it is consumed and cannot be reused. Repeatable operations borrow it.
- Never derive `Clone`, `Default`, or `Deserialize` on a token. Each is a way to obtain one without the check.
- Name the token after what it proves. A right that is borrowed for repeated use ends in `Permission` (`WritePermission`, `AdminPermission`); a one-shot approval consumed by the operation ends in `Permit` (`RebootPermit`, `TransactionPermit`); a token that proves a state uses the state's noun (`AuthenticatedUser`, `ExclusiveLock`, `MaintenanceMode`).

**When NOT to apply:** the check and the gated operation sit in the same function with a single call site. The token then names a guarantee the code already has by construction. Introduce it when a second call site appears.

**Rationale:** "Did we remember to check?" is a question asked at every call site during every review. "Where did this token come from?" has exactly one answer, and the compiler checks it.

### 21. Sealed Traits: Public to Call, Private to Implement (MEDIUM)

When a public trait has invariants the crate controls, or describes a fixed set of the crate's own types, stop downstream crates from implementing it by giving it a private supertrait. Callers can still use the trait; only the owning crate can add implementations, so adding a method is not a breaking change.

```rust
// Bad - any crate can implement PackageBackend, so adding a method breaks them all,
// and every method must defend against implementations that break the contract
pub trait PackageBackend {
    fn install(&self, package: &PackageName) -> Result<(), InstallError>;
}

// Good - callable everywhere, implementable only here
mod private {
    pub trait Sealed {}
}

pub trait PackageBackend: private::Sealed {
    fn install(&self, package: &PackageName) -> Result<(), InstallError>;
}

pub struct DnfBackend;

impl private::Sealed for DnfBackend {}

impl PackageBackend for DnfBackend {
    fn install(&self, package: &PackageName) -> Result<(), InstallError> { /* ... */ }
}
// Downstream: `impl PackageBackend for MyBackend` fails - `private::Sealed` is not nameable there.
```

**When NOT to apply:** the trait is a port that adapters in other crates, or mocks in `tests/`, are expected to implement (rust-hexagonal-architecture ports). Sealing a port defeats its purpose. Seal traits over a closed set of the crate's own types, never extension points.

**Rationale:** An open trait is a contract with every crate that ever implements it. A sealed trait is a contract only with the crate that owns it, so it can grow without a major version.

### 22. Extension Traits: Add Methods to Types You Do Not Own (MEDIUM)

When domain behavior belongs conceptually on a type from another crate, define a trait holding that behavior and implement it for the foreign type. Callers get method syntax wherever the trait is imported; the foreign type stays untouched.

```rust
// Bad - free functions scattered beside their call sites
fn is_security_update(package: &libdnf5::Package) -> bool { /* ... */ }
fn upgrade_target(package: &libdnf5::Package) -> Option<PackageVersion> { /* ... */ }

// Good - one extension trait, one concern, method syntax
pub trait PackageExt {
    fn is_security_update(&self) -> bool;
    fn upgrade_target(&self) -> Option<PackageVersion>;
}

impl PackageExt for libdnf5::Package {
    fn is_security_update(&self) -> bool {
        self.advisories().any(|advisory| advisory.kind() == AdvisoryKind::Security)
    }

    fn upgrade_target(&self) -> Option<PackageVersion> { /* ... */ }
}

// Call site
use crate::package::PackageExt;

if package.is_security_update() { /* ... */ }
```

Shape rules:
- Name the trait `<Type>Ext` and place it in the module that owns the domain concern, not beside the foreign type's import.
- One extension trait per concern. Single responsibility applies to traits: do not let one `Ext` trait accumulate unrelated methods.
- When the foreign type needs an invariant enforced, not just methods added, wrap it in a newtype (Idiom 1) instead. An extension trait cannot restrict construction.

**Rationale:** The orphan rule forbids inherent `impl` blocks on foreign types. An extension trait is the sanctioned way to give a foreign type domain vocabulary without wrapping every value.

### 23. Give an Exclusive Resource to One Task (HIGH)

In async code, when several tasks use one resource whose operations must not interleave (a package manager that must never run two transactions at once, a serial device, a write-ahead log), give the resource to exactly one task and send it commands over a channel. Do not share it as `Arc<Mutex<Resource>>` across every caller.

```rust
// Bad - every caller locks; "one transaction at a time" holds only if every caller
// keeps the guard across every .await, and nothing enforces that
let manager = Arc::new(Mutex::new(PackageManager::new()));
// handler:   manager.lock().await.install(&package).await;
// worker:    manager.lock().await.upgrade().await;
// scheduler: manager.lock().await.refresh_metadata().await;

// Good - one owner, one queue, commands as data
const PACKAGE_COMMAND_QUEUE_DEPTH: usize = 32;

enum PackageCommand {
    Install { package: PackageName, reply: oneshot::Sender<Result<(), InstallError>> },
    Upgrade { reply: oneshot::Sender<Result<UpgradeReport, UpgradeError>> },
}

fn spawn_package_manager(mut manager: PackageManager) -> mpsc::Sender<PackageCommand> {
    let (command_sender, mut command_receiver) = mpsc::channel(PACKAGE_COMMAND_QUEUE_DEPTH);

    tokio::spawn(async move {
        while let Some(command) = command_receiver.recv().await {
            match command {
                PackageCommand::Install { package, reply } => {
                    let outcome = manager.install(&package).await;
                    // the requester may have stopped waiting; there is nowhere else to report
                    let _ = reply.send(outcome);
                }
                PackageCommand::Upgrade { reply } => {
                    let outcome = manager.upgrade().await;
                    let _ = reply.send(outcome);
                }
            }
        }
    });

    command_sender
}
```

```text
HTTP handler ──┐
worker ────────┼── mpsc channel ──> package-manager task (sole owner, one command at a time)
scheduler ─────┘
```

Shape rules:
- The command enum is the resource's public API. The `PackageManager` value never leaves the task.
- Each command carries a `oneshot::Sender` for its reply. The caller awaits the reply, so ordering and back-pressure come from the channel, not from a lock.
- Use a bounded channel; the bound is the queue-depth policy and is a named constant (rust-code-style Rule 5).
- Serialization is the point. Never spawn several owner tasks for the same resource.
- When the resource's operations form a typestate sequence (Idiom 17), the task owns whatever creates the first state (the library handle or a factory) and runs the whole sequence to completion inside one command. Typestate values never cross the channel.

**When NOT to apply:**
- The shared state is read-mostly, or its critical sections are synchronous and never hold across `.await`. `Arc<RwLock<_>>` or `Arc<Mutex<_>>` is simpler and correct there.
- There is a single caller. No sharing problem exists.

**Rationale:** A mutex guards memory, not a protocol. "Never two transactions concurrently" is a protocol invariant, and one owning task enforces it structurally: there is exactly one place operations can run, and it runs them one at a time.

### 24. Borrow From the Input in Parsers (MEDIUM)

When a function parses or slices a large input and the result is used only while the input is alive, let the output type borrow from the input instead of allocating owned copies.

```rust
// Bad - two String allocations per line of a multi-megabyte metadata file
struct ParsedPackage {
    name: String,
    version: String,
}

// Good - views into the buffer already in memory; no allocation
struct ParsedPackage<'input> {
    name: &'input str,
    version: &'input str,
}

fn parse_line(line: &str) -> Result<ParsedPackage<'_>, ParseError> {
    let (name, rest) = line.split_once(' ').ok_or(ParseError::MissingVersion)?;
    let (version, _architecture) = rest.split_once(' ').ok_or(ParseError::MissingArchitecture)?;
    Ok(ParsedPackage { name, version })
}
```

```text
"nginx 1.28.0 x86_64"     one buffer
 ^^^^^ ^^^^^^
 name  version            two &str into it, zero copies
```

Scope: parsers and boundary code only (repository metadata, protocol frames, log lines, serialization). Domain models stay owned (`String`, `Vec<T>`). A domain type with a lifetime parameter infects every struct, port trait, and async task that holds it. Parse borrowed at the boundary, then build the owned domain value once the data is known valid (Idiom 2).

**When NOT to apply:**
- The parsed value outlives the input: stored in a repository, sent to another task, returned through a port.
- The input is small or parsed once. The allocation is not worth a lifetime parameter.
- The type must be `'static`: spawned into a Tokio task, or stored in a `Box<dyn Trait>` without a lifetime.

**Rationale:** Copying out of a buffer you already hold is pure overhead on hot parsing paths. Everywhere else owned data is simpler, and the lifetime parameter costs more in API complexity than the allocation it saves.

## Anti-Patterns to Avoid

1. **Primitive obsession**: Using raw String, i32, etc. for domain concepts instead of newtypes
2. **Public inner fields**: Exposing the wrapped value directly, bypassing validation
3. **Duplicated validation**: Having multiple code paths that validate the same invariants
4. **Validation everywhere**: Checking validity in business logic instead of at construction
5. **Missing trait implementations**: Forcing users to wrap your newtypes due to missing derives
6. **Unconsidered Deref**: Implementing Deref without considering the expanded public interface
7. **Bypassed constructors**: Using struct literal syntax to create instances without validation
8. **Introducing a new error crate**: Adding `thiserror` or `anyhow` as a *new* dependency instead of implementing `Error` manually — matching a project that already depends on them is fine
9. **Dynamic error types in libraries**: Using `Box<dyn Error>` in public APIs instead of structured enums
10. **Umbrella error enums**: Creating module-wide errors where most variants are impossible for most functions
11. **String-based errors**: Using `String` or `&str` as error types instead of structured enums
12. **Downcasting errors**: Relying on `downcast_ref` to handle errors programmatically
13. **Positional argument soup**: Constructors or functions with more than 3-4 positional parameters instead of config structs
14. **Boolean sequencing flags**: `initialized: bool` / `resolved: bool` fields re-checked in every method instead of typestate (Idiom 17)
15. **Flag soup**: several `bool`/`Option` fields whose combinations are mostly meaningless instead of one enum with per-variant data (Idiom 18)
16. **Trailing cleanup**: `release()` / `unlock()` / `rollback()` as the last statement of a function instead of in `Drop` (Idiom 19)
17. **Discarded guard**: `let _ = lock.acquire()?;`, which drops the guard on the same line and releases immediately
18. **Check-and-hope**: `if user.can_write()` at some call sites instead of a token the operation requires (Idiom 20)
19. **Forgeable token**: a capability type with a public constructor, or deriving `Clone`, `Default`, or `Deserialize`
20. **Sealed port**: sealing a trait that adapters or test mocks must implement (Idiom 21)
21. **Kitchen-sink extension trait**: one `Ext` trait accumulating unrelated methods on a foreign type (Idiom 22)
22. **Mutex as protocol**: `Arc<Mutex<Resource>>` shared across tasks to enforce "one operation at a time" instead of a single owning task (Idiom 23)
23. **Lifetimes in domain models**: borrowed `&'a str` fields in types that cross ports, tasks, or storage (Idiom 24)

## Guidelines

### Newtype Design
- Wrap primitive types that have semantic meaning in your domain
- Keep inner fields private to enforce validation
- Use tuple structs for simple wrappers: `struct UserId(Uuid);`
- Use named fields when additional clarity is needed
- Use config structs when constructors exceed 3-4 parameters

### Validation Strategy
- Validate once at construction, trust the type afterward
- Single canonical constructor for all creation paths
- Consider unchecked constructors for trusted data sources
- Preserve invariants in all mutable operations

### Trait Implementation
- Implement Debug, Clone, PartialEq, Eq as baseline
- Add Hash if used in collections
- Add Ord if ordering is meaningful
- Implement Display for user-facing output
- Use AsRef for borrowing, be cautious with Deref
- Implement From/TryFrom for conversions

### Error Handling
- Implement `std::error::Error` manually by default; use `thiserror`/`anyhow` only when the project already depends on them
- Design error types as enums capturing all possible failure states
- Scope errors to specific operations, not entire modules
- Implement `From` for composing errors and enabling the `?` operator
- Include relevant context (paths, IDs, values) in error variants
- Implement `source()` to preserve error chains
- Libraries must return structured errors; applications can use `Box<dyn Error>` internally

### Type-Level State
- Ordered steps fixed at compile time: typestate with consuming transitions (Idiom 17)
- Mutually exclusive runtime states: one enum, data on the variant (Idiom 18)
- Independent fields all known up front: config struct (Idiom 10), not a typestate builder

### Resources and Ownership
- Anything acquired is released in `Drop`; bind guards to a named variable, never `let _`
- A check that gates an operation returns a private-constructor token the operation requires
- One exclusive resource with many async callers: one owning task and a command channel

### Trait Surface
- Seal traits over the crate's own closed set of types; never seal ports
- Extend foreign types with one `<Type>Ext` trait per concern; wrap in a newtype when an invariant is needed

### Borrowing
- Borrow from the input in parsers and boundary code; domain models own their data
