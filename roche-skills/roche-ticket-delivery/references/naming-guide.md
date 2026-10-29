# Naming things in Rust

The reference for stage 8's naming designers. A name should say what a thing is to its caller,
and the type system carries part of that load.

- **Names only.** Stage 8 reviews names. Do not propose moving code, adding types, or turning a
  trait into an enum. The design advice below explains why a name is wrong; it is not a task.
- **Cite a rule by its id:** `T4`, `P6`, `C-CONV`. Team rules are `T1`-`T5`, the principles
  `P1`-`P6`, and the API Guidelines items keep their own `C-` ids.
- **When rules disagree:** the repository's gates and `docs/layout.md` first, then the Team
  rules, then the rest of this guide.

## Names you do not propose to change

Skip these, or mark the proposal "needs his word":

- Methods of a trait or of generated code: tonic's `PackageManager` methods
  (`get_operation_status` mirrors `rpc GetOperationStatus`), `fmt` in `Display` impls, wire
  and serde names.
- The proto contract, `libdnf5-adapter` items shared with C++ (`src/ffi.rs`, `src/cpp/`),
  anything an ADR names, anything under `vendor/`.
- JSON log event names and keys (`docs/operations.md`), CLI flags, config keys.
- File names in the vocabulary of `docs/layout.md` and **rust-project-structure**: `model.rs`,
  `port.rs`, `error.rs`, a facade `<concept>.rs`.

## Casing (C-CASE)

- `snake_case`: variables, functions, methods, modules, crate identifiers. Cargo package names
  are kebab-case (`rdnx-core`).
- `UpperCamelCase`: structs, enums, enum variants, traits, type aliases
- `SCREAMING_SNAKE_CASE`: `const` and `static`
- Acronyms and contractions are one word. In CamelCase: `HttpClient`, `Uuid`, `Stdin`, not
  `HTTPClient`, `UUID`, `StdIn`. In snake_case: `is_xid_start`, `parse_http_header`. A
  single-letter word only in final position: `btree_map`, `PI_2`.

The compiler warns on the first three. The acronym rule is from RFC 430, restated as C-CASE.
Clippy's `upper_case_acronyms` catches only the fully capitalised form (`HTTP`), so check mixed
names such as `HTTPClient` yourself.

## Principles

**P1. No single-letter names, with Rust's accepted exceptions.**
Generic type parameters (`T`, `E`, `K`, `V`), lifetimes (`'a`) and the parameter of a one-line
closure (`|entry| entry.len()`, or `|x| x * 2`) are outside the rule. Anything that lives
longer than a line gets a real name. T1 holds the team's form of this rule.

**P2. Don't abbreviate, but follow the ecosystem's shorthand.**
Std's established short words stay allowed: `Vec`, `fmt`, `io`, `Rc`, `ptr`, `from_secs`,
`buf`, `len`, `env`, `args`, and `tx` / `rx` for the two ends of a channel. In rdnx, `id` and
`config` are fine everywhere. `repo` is allowed only when the name copies a spelling that
exists in dnf or libdnf5 (a config key such as `repo_gpgcheck`, a CLI option, a type such as
`RepoSack`); otherwise write `repository`. Shorthand the project invented (`sess_mgr`,
`usr_cnt`) is out.

**P3. Don't put types in names. Shadowing makes this easy.**
You can reuse a name when the value changes type, so you never need `port_str` and `port_num`:

```rust
let port = std::env::var("PORT")?;   // String
let port: u16 = port.parse()?;       // u16
```

Shadow to refine the same value (parse, unwrap, convert). When the value is something else,
use a new name. P3 is about suffixes such as `_str`, `_vec`, `_u16`; T4 overrides it for
bindings of the repository's own types.

**P4. Units: let types carry them.**
For time, use `std::time::Duration` rather than `delay_seconds: u64`. A newtype such as
`struct Meters(f64)` lets the compiler reject mixups. A raw number keeps a unit suffix
(`budget_bytes`, `delay_seconds`): that is the accepted fallback, so do not propose a newtype
in place of it.

**P5. No `I`, `Base`, `Abstract`, or `Trait` decorations.**

- **Name traits for a capability or a concept.** Std uses verbs (`Read`, `Write`, `Clone`,
  `Hash`) or nouns (`Iterator`). Never `ITruck` or `TruckTrait`.
- **The general name goes to the abstraction, the specific name to the implementor:** the
  port `RepositoryMetadataReader`, the adapter `FsRepositoryMetadataReader`.
- **Variants don't repeat the enum's name:** `Truck::Trailer`, not `Truck::TrailerTruck`.

**P6. No `utils.rs`, and stutter has two cases.**

- A `utils.rs` or `helpers.rs` names no concept. Name the module for what its items are about.
- *File names* are a gate. A file under `src/` never repeats its folder
  (`backup/backup_executor.rs`). Never propose a stuttering file name.
- *Item names* in rdnx keep the concept word: `OperationId` in `domain::operation`,
  `RepositoryStoreError` in `application::repository::error`. Callers import the item by name,
  so the module name is not typed twice, and T2 wins. Do not propose `operation::Id` or
  `error::Error`. Propose dropping a repeated word only for an item that callers always use
  through its module path (`io::Error` style), and show that call site.

Clippy's `module_name_repetitions` is in the `restriction` group, so it is off by default, and
this workspace does not enable it.

## From the Rust API Guidelines

- **Getters (C-GETTER):** an accessor has no `get_` prefix: `fn name(&self) -> &str`,
  `first()`, `first_mut()`. Plain `get` is for one obvious thing (`Cell::get`) or a checked
  lookup by key or index (`Vec::get`, `HashMap::get`). A method that goes through a port or
  mirrors an RPC or wire name keeps its verb.
- **Conversions (C-CONV):**
  - `as_`: free, borrowed to borrowed (`as_str`, `as_bytes`). On a `Copy` type it may take
    `self` by value (`fn as_str(self) -> &'static str`); clippy accepts that, so do not
    propose renaming it.
  - `to_`: expensive or allocating; borrowed to owned, or owned to owned for a `Copy` type.
  - `into_`: consumes a non-Copy `self`; cost varies. A single-value wrapper exposes its value
    as `into_inner()`.
  - `mut` sits where it sits in the return type: `as_mut_slice`, not `as_slice_mut`.
- **Constructors (C-CASE):** `new` or `with_more_details`, `from_*` for conversions (or a
  `From` impl), `try_*` for fallible ones.
- **Iterators (C-ITER, C-ITER-TY):** a homogeneous collection has `iter()`, `iter_mut()` and
  `into_iter()`, and the iterator types are named after them: `Iter`, `IterMut`, `IntoIter`. A
  domain-named iterator (`events()`, `keys()`, `chars()`) is fine.
- **Errors (C-WORD-ORDER):** one word order per crate; for parsing, `ParseIntError`, not
  `IntParseError`. rdnx keeps a unique `…Error` name per failure (`RepositoryStoreError`,
  `LookupError`, `SubmitError`).

## Booleans (std practice)

- A predicate method reads as a question: `is_empty()`, `has_terminal()`, `contains(..)`.
- A bool field, parameter or local reads as a true/false statement: `keep_cache`,
  `cache_disabled`, `replace_all`. A bare verb (`stop`, `disable_cache`) reads as an order:
  rename it so it reads as a statement, never by adding `_flag`.
- `_flag` is only for a shared `AtomicBool` that signals a request: `stop_request_flag`.
- A bool argument hides its meaning at the call site (`rename(path, true)`). For a public
  function, note a two-variant enum (`rename(path, Overwrite::Replace)`) as a remark for him,
  not as a rename.

## Team rules

Cristian's rules for rdnx. Where they differ from the rest of this guide, they win.

T1 to T3 have no sanctioned deviation. T4 and T5 are Tier 2 in `rust.md` terms: a deviation with
a one-line `// why:` is not a finding, provided the comment names the constraint
(`// why: mirrors the libdnf5 field`), not the deviation (`// why: named after the Arc`). Flag
a hollow `// why:`.

**T1. No single-letter variable names**, outside P1's exceptions. A formatter in `fmt` is
`formatter`, not `f`; a loop variable is `entry`, not `e`.

**T2. A name says what the thing is for**, so the code explains itself.

- Length: count the CamelCase or snake_case words; `Id`, `Libdnf5` and an acronym count as
  one. Up to four words is normal. Five or six only when no shorter name plus a `///` line says
  the same; propose one only beside the shorter option it beats.
- Test it: read the name at a call site without opening the type. If you cannot say what it
  holds, decides or does, it is vague. Words that rarely pass alone: `Share`, `Data`, `Info`,
  `State`, `Context`, `Handler`, `Manager`, `Item`, `Value`, `Helper`; a bare verb for a flag
  (`stop`); a bare noun beside a sibling (`budget`). This is a prompt to look, not an
  automatic fail.
- Avoid words that read two ways. `Share::Full` and `put_full` read as "the queue is full"
  when they mean "may use the whole budget"; `Headroom::MayUse` cannot be misread.

**T3. Short name, full meaning in the doc line.** Use it when the exact name needs five or more
words, or when a shorter name with its `///` line reads better at the call site than the exact
one: `Headroom` with `/// Headroom kept for lifecycle event lines.` instead of
`LifecycleEventLineHeadroom`. A short name with no doc line completing it is still vague.

**T4. A binding of one of the repository's own types is named the snake_case of that type, the
same way for every sibling.**

- A field always: it is read far from its declaration (`self.queue_budget`), where the type
  is not in sight. `queue_budget: QueueBudget` next to `drain_budget: DrainBudget`, never
  `budget` next to `drain`.
- A parameter or local only when a sibling is in scope: any other value of a related kind
  visible in the same function, such as a second id, including one reached through a field.
  `fn cancel(&self, id: &OperationId)` is fine. `fn attach(&self, operation_id: &OperationId,
  plan_id: &PlanId)` names both. `fn attach(&self, id: &OperationId, plan: &Plan)` whose body
  uses `plan.id` names its parameter `operation_id`.
- Look through `&`, `Option`, `Arc` and `Box`: `queue_ledger: Arc<QueueLedger>`. It does not
  apply to std, tonic or primitive types (`channel`, `receiver`, `request`, `count`).

**T5. Name a type or binding after what it holds, never after how it is held:** `QueueLedger`,
not `QueueShared` for something kept behind an `Arc`. Words to look for: `Shared`, `Locked`,
`Arc`, `Boxed`, `Inner`, `Cell`. A lock guard kept beside its lock is the usual sanctioned
deviation (`// why: guard and Mutex are both in scope` above `let queue_guard = ...`).

## Tests

Follow **rust-testing** §7 and §10. A test module is named after the function or type it tests
(`mod from_config`). A test fn is `should_<behaviour>` or `should_<behaviour>_when_<condition>`.
No `test_` prefix and no `_test` suffix on files or modules; a test file mirrors its source file's
name. T1 to T5 apply to test code too. Flag only the names the change adds or renames.

Sources:
- [Rust API Guidelines, naming](https://rust-lang.github.io/api-guidelines/naming.html)
- [RFC 430, naming conventions](https://rust-lang.github.io/rfcs/0430-finalizing-naming-conventions.html)
- [Clippy lint source: module_name_repetitions (restriction group)](https://github.com/rust-lang/rust-clippy/blob/master/clippy_lints/src/item_name_repetitions.rs)
