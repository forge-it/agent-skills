---
name: rust-design-idioms
description: Rust-specific design idioms including Newtype pattern, type-safe domain modeling, and parse-don't-validate approach
license: MIT
metadata:
  author: cristian.ciortea@proton.me
  version: "0.0.1"
---

# Design Idioms Skill

Version: 0.0.1

## Purpose

This skill provides guidelines for applying Rust-specific design idioms. It focuses on patterns that leverage Rust's type system to create safer, more expressive code. These idioms help eliminate runtime errors by encoding invariants in the type system.

## When to Apply

Apply these guidelines when:
- Modeling domain concepts with specific validation rules
- Preventing invalid states at compile time
- Working with primitive types that have semantic meaning
- Designing APIs that are hard to misuse

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

## Anti-Patterns to Avoid

1. **Primitive obsession**: Using raw String, i32, etc. for domain concepts instead of newtypes
2. **Public inner fields**: Exposing the wrapped value directly, bypassing validation
3. **Duplicated validation**: Having multiple code paths that validate the same invariants
4. **Validation everywhere**: Checking validity in business logic instead of at construction
5. **Missing trait implementations**: Forcing users to wrap your newtypes due to missing derives
6. **Unconsidered Deref**: Implementing Deref without considering the expanded public interface
7. **Bypassed constructors**: Using struct literal syntax to create instances without validation

## Guidelines

### Newtype Design
- Wrap primitive types that have semantic meaning in your domain
- Keep inner fields private to enforce validation
- Use tuple structs for simple wrappers: `struct UserId(Uuid);`
- Use named fields when additional clarity is needed

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
- Create dedicated error types for validation failures
- Include the invalid value in error messages
- Use thiserror for ergonomic error definitions
