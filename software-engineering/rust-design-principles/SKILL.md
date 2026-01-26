---
name: rust-design-principles
description: Rust software design principles including SOLID, KISS, and design pattern usage guidelines
license: MIT
metadata:
  author: cristian.ciortea@proton.me
  version: "0.0.1"
---

# Design Principles Skill

Version: 0.0.1

## Purpose

This skill provides guidelines for applying software design principles. It focuses on SOLID principles, KISS (Keep It Simple, Stupid), and appropriate use of design patterns.

## When to Apply

Apply these guidelines when:
- Designing new features or modules
- Refactoring existing code
- Reviewing code architecture
- Making design decisions

## Core Principles

### 1. SOLID Principles (CRITICAL)

Apply SOLID principles in backend code:

#### Single Responsibility Principle
Each module/component does one thing well.

```rust
// Bad - class does too many things
struct UserManager {
    fn create_user(&self, data: UserData) -> User { /* ... */ }
    fn send_welcome_email(&self, user: &User) { /* ... */ }
    fn generate_report(&self, users: &[User]) -> Report { /* ... */ }
}

// Good - separated responsibilities
struct UserRepository {
    fn create(&self, data: UserData) -> User { /* ... */ }
}

struct EmailService {
    fn send_welcome(&self, user: &User) { /* ... */ }
}

struct ReportGenerator {
    fn generate_user_report(&self, users: &[User]) -> Report { /* ... */ }
}
```

#### Open/Closed Principle
Open for extension, closed for modification.

```rust
// Bad - modifying existing code for new behavior
fn calculate_discount(customer_type: &str, amount: f64) -> f64 {
    match customer_type {
        "regular" => amount * 0.1,
        "premium" => amount * 0.2,
        "vip" => amount * 0.3,  // Added later, modifying existing function
        _ => 0.0,
    }
}

// Good - extend through new implementations
trait DiscountStrategy {
    fn calculate(&self, amount: f64) -> f64;
}

struct RegularDiscount;
impl DiscountStrategy for RegularDiscount {
    fn calculate(&self, amount: f64) -> f64 { amount * 0.1 }
}

struct PremiumDiscount;
impl DiscountStrategy for PremiumDiscount {
    fn calculate(&self, amount: f64) -> f64 { amount * 0.2 }
}

// New discount types can be added without modifying existing code
struct VipDiscount;
impl DiscountStrategy for VipDiscount {
    fn calculate(&self, amount: f64) -> f64 { amount * 0.3 }
}
```

#### Liskov Substitution Principle
Subtypes must be substitutable for their base types.

```rust
// Bad - subtype violates base type contract
trait Bird {
    fn fly(&self);
}

struct Penguin;
impl Bird for Penguin {
    fn fly(&self) {
        panic!("Penguins can't fly!"); // Violates LSP
    }
}

// Good - proper abstraction
trait Bird {
    fn move_around(&self);
}

trait FlyingBird: Bird {
    fn fly(&self);
}

struct Sparrow;
impl Bird for Sparrow {
    fn move_around(&self) { self.fly(); }
}
impl FlyingBird for Sparrow {
    fn fly(&self) { /* ... */ }
}

struct Penguin;
impl Bird for Penguin {
    fn move_around(&self) { /* waddle */ }
}
```

#### Interface Segregation Principle
Prefer small, specific interfaces over large ones.

```rust
// Bad - fat interface
trait Worker {
    fn work(&self);
    fn eat(&self);
    fn sleep(&self);
    fn attend_meeting(&self);
    fn write_report(&self);
}

// Good - segregated interfaces
trait Workable {
    fn work(&self);
}

trait Feedable {
    fn eat(&self);
}

trait Reportable {
    fn write_report(&self);
}

// Implementations only implement what they need
struct Robot;
impl Workable for Robot {
    fn work(&self) { /* ... */ }
}

struct Employee;
impl Workable for Employee {
    fn work(&self) { /* ... */ }
}
impl Feedable for Employee {
    fn eat(&self) { /* ... */ }
}
impl Reportable for Employee {
    fn write_report(&self) { /* ... */ }
}
```

#### Dependency Inversion Principle
Depend on abstractions, not concretions.

```rust
// Bad - depending on concrete implementation
struct OrderService {
    repository: PostgresOrderRepository, // Concrete dependency
}

// Good - depending on abstraction
trait OrderRepository {
    fn save(&self, order: &Order) -> Result<(), Error>;
    fn find_by_id(&self, id: OrderId) -> Result<Order, Error>;
}

struct OrderService<R: OrderRepository> {
    repository: R, // Abstract dependency
}

impl<R: OrderRepository> OrderService<R> {
    fn new(repository: R) -> Self {
        Self { repository }
    }
}
```

### 2. KISS - Keep It Simple, Stupid (CRITICAL)

Keep implementations simple. Avoid over-engineering. Choose the straightforward solution unless complexity is truly justified.

```rust
// Bad - over-engineered
trait ValidationStrategy {
    fn validate(&self, value: &str) -> bool;
}
struct EmailValidationStrategy;
impl ValidationStrategy for EmailValidationStrategy {
    fn validate(&self, value: &str) -> bool { value.contains('@') }
}
struct ValidationContext {
    strategy: Box<dyn ValidationStrategy>,
}

// Good - simple and direct
fn is_valid_email(value: &str) -> bool {
    value.contains('@')
}
```

### 3. Design Patterns - Use Judiciously (CRITICAL)

Use design patterns only when they solve a real problem. Never introduce patterns preemptively or for theoretical benefits.

```rust
// Bad - pattern for pattern's sake
// Using Factory pattern for a simple object with no variants
trait UserFactory {
    fn create(&self) -> User;
}
struct DefaultUserFactory;
impl UserFactory for DefaultUserFactory {
    fn create(&self) -> User { User::default() }
}

// Good - use pattern when it solves a real problem
// Factory pattern when you have multiple implementations
trait NotificationSender {
    fn send(&self, message: &str) -> Result<(), Error>;
}

struct EmailSender;
struct SmsSender;
struct PushSender;

fn create_sender(channel: NotificationChannel) -> Box<dyn NotificationSender> {
    match channel {
        NotificationChannel::Email => Box::new(EmailSender),
        NotificationChannel::Sms => Box::new(SmsSender),
        NotificationChannel::Push => Box::new(PushSender),
    }
}
```

## Anti-Patterns to Avoid

1. **God classes**: Classes that do too many things (violates SRP)
2. **Premature abstraction**: Creating interfaces before they're needed
3. **Pattern obsession**: Using patterns where simple code would suffice
4. **Deep inheritance**: Preferring inheritance over composition
5. **Leaky abstractions**: Exposing implementation details through interfaces
6. **Speculative generality**: Building for hypothetical future requirements

## Guidelines

### SOLID Application
- Single Responsibility: One reason to change per module
- Open/Closed: Extend behavior without modifying existing code
- Liskov Substitution: Subtypes must honor base type contracts
- Interface Segregation: Many specific interfaces over one general
- Dependency Inversion: Depend on abstractions, inject dependencies

### Simplicity First
- Choose the simplest solution that works
- Add complexity only when justified by real requirements
- Avoid over-engineering and speculative features
- Prefer composition over inheritance

### Pattern Usage
- Only use patterns to solve real, present problems
- Never introduce patterns preemptively
- Understand the problem before choosing a pattern
- Simple code is better than pattern-heavy code

### Decision Making
- Ask "Do I need this complexity now?"
- Consider the cost of abstraction vs the benefit
- Prefer concrete implementations until patterns prove necessary
- Refactor to patterns when duplication or change patterns emerge
