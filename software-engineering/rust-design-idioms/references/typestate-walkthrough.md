# Typestate Walkthrough

Companion to Idiom 17 in `../SKILL.md`. Read this when you need to understand *why* the pattern is built the way it is, not just its shape.

## The idea in one line

Encode the current state of an object into its Rust type, so that a method which is only valid in one state exists only on that state's type.

Instead of one runtime object:

```rust
struct PackageManager {
    initialized: bool,
    transaction_resolved: bool,
}
```

model distinct compile-time states:

```text
PackageManager<Uninitialized>
PackageManager<Ready>
PackageManager<TransactionResolved>
```

The generic parameter is the state.

## Why a generic parameter carries the state

Generics are normally used to describe the kind of data a type holds: `Vec<String>`, `Vec<i32>`, `Option<UserId>`. Typestate uses the same mechanism to describe the legal state of the object instead of its content. `PackageManager<Ready>` and `PackageManager<Uninitialized>` are two different types to the compiler, exactly as `Vec<String>` and `Vec<i32>` are, so an `impl` block written for one does not apply to the other.

```rust
struct PackageManager<State> {
    handle: RawHandle,
    _state: std::marker::PhantomData<State>,
}

struct Uninitialized;
struct Ready;
struct TransactionResolved;
```

The marker types contain no data. They exist purely for the compiler.

## What `PhantomData` does

Without it:

```rust
struct PackageManager<State> {
    handle: RawHandle,
}
```

Rust rejects the definition because `State` is declared but never used. `PhantomData<State>` tells the compiler "treat this struct as logically associated with `State`, even though no `State` value is stored". It occupies zero bytes.

```text
runtime memory                    compile-time type

+------------------+              PackageManager<Ready>
| RawHandle        |                             ^^^^^
+------------------+                             compiler-only marker
```

`PackageManager<Ready>` and `PackageManager<Uninitialized>` have identical size and layout. The state costs nothing at runtime; this is why typestate is called a zero-cost abstraction.

## Why transitions take `self`, not `&mut self`

With `&mut self`:

```rust
fn initialize(&mut self)
```

the value keeps its type after the call. It was `PackageManager<Uninitialized>` before and is still `PackageManager<Uninitialized>` after, so nothing has changed for the compiler.

With `self`:

```rust
fn initialize(self) -> PackageManager<Ready>
```

the old value is moved into the method and a value of a new type comes out. The caller's binding for the old state is gone; using it again is a use-after-move compile error. That move is what makes "you cannot use the old state" and "you cannot run this twice" compiler guarantees rather than conventions.

```text
PackageManager<Uninitialized>
        |
        | initialize(self)         old value consumed
        v
PackageManager<Ready>             new value returned
```

## A complete example

```rust
use std::marker::PhantomData;

struct Uninitialized;
struct Ready;
struct Resolved;

struct PackageManager<State> {
    handle: RawHandle,
    _state: PhantomData<State>,
}

impl PackageManager<Uninitialized> {
    fn new(handle: RawHandle) -> Self {
        Self { handle, _state: PhantomData }
    }

    fn initialize(self) -> Result<PackageManager<Ready>, InitializeError> {
        self.handle.initialize()?;
        Ok(PackageManager { handle: self.handle, _state: PhantomData })
    }
}

impl PackageManager<Ready> {
    fn resolve(self) -> Result<PackageManager<Resolved>, ResolveError> {
        self.handle.resolve()?;
        Ok(PackageManager { handle: self.handle, _state: PhantomData })
    }
}

impl PackageManager<Resolved> {
    fn run(self) -> Result<TransactionReport, RunError> {
        self.handle.run()
    }
}

fn upgrade_everything(handle: RawHandle) -> Result<TransactionReport, UpgradeError> {
    let manager = PackageManager::new(handle);
    let ready_manager = manager.initialize()?;
    let resolved_manager = ready_manager.resolve()?;
    let report = resolved_manager.run()?;
    Ok(report)
}
```

What fails to compile, and why:

```rust
let manager = PackageManager::new(handle);
manager.run();
// error: no method named `run` found for struct `PackageManager<Uninitialized>`

let resolved_manager = manager.initialize()?.resolve()?;
resolved_manager.run()?;
resolved_manager.run()?;
// error: use of moved value: `resolved_manager`
```

## Mapping a real workflow

Write the legal sequence as a diagram first, then give each box a marker type and each arrow a consuming method.

```text
PackageManager<Created>
        |
        | load_repositories()
        v
PackageManager<RepositoriesLoaded>
        |
        | resolve_upgrade()
        v
Transaction<Resolved>
        |
        | run()
        v
TransactionReport
```

Two things this buys for a package-manager binding:

- `resolve_upgrade()` cannot be called before repositories are loaded, because `PackageManager<Created>` has no such method.
- `run()` cannot be called twice, because it consumes the `Transaction<Resolved>`.

Neither guarantee needs an `if transaction.already_ran { return Err(...) }` check, because the situation the check would catch cannot be written.

## States that carry data

When a later state has data the earlier states do not, put it in the marker type and store the marker as a real field instead of `PhantomData`:

```rust
struct Resolved {
    plan: TransactionPlan,
}

struct Transaction<State> {
    handle: RawHandle,
    state: State,
}

impl Transaction<Resolved> {
    fn planned_changes(&self) -> &[PlannedChange] {
        &self.state.plan.changes
    }
}
```

`Transaction<Created>` still carries an empty marker; `Transaction<Resolved>` carries the plan. Each state has exactly the fields that make sense for it, which is the same property Idiom 18 gives runtime state enums.

## Typestate or an enum?

| The state is decided by | Use |
|---|---|
| The program's code path, fixed at compile time (initialize, then resolve, then run) | Typestate (Idiom 17) |
| Data that arrives at runtime (the job succeeded or failed) | One enum with per-variant data (Idiom 18) |
| Both: a fixed workflow whose steps each succeed or fail | Typestate for the steps; `Result` for each step's outcome, as in the example above |

Typestate says which operations exist at this point in the program. An enum says what happened. They are not alternatives for the same problem, and one design often uses both.
