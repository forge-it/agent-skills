---
name: deployment-check-pattern
description: >-
  Use when a project has a local-prod deploy (a `local-deploy-*` recipe family)
  and a test whose subject is the deployed topology itself has nowhere
  principled to live — or when any of these symptoms appear: a fleet-identity
  or deploy-smoke check landed as a stray test root with no category, no
  recipe, and helpers parked in the shared `tests/common/`; an `#[ignore]`d
  test whose subject is the deployed topology sits in `e2e` and boots the whole
  Docker test stack it has no use for; a `just local-deploy-up` stack that
  nothing ever verifies, so a broken image or an unapplied migration is found
  by hand; a Python deployment check under `tests/` that boots the shared stack
  through the root `conftest.py`'s autouse session fixtures; a shell script
  under `tools/` doing SQL and `docker` calls that no gate ever compiles; or a
  second deployment check about to redden `just test-all` for everyone.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.1"
---

# Deployment Check Pattern

## Purpose

Every test category a project already has answers a question about *code*: does
this function compute the right value, does this adapter translate correctly,
does this source tree have the right shape. A deployment check answers one about
the *deployment*: did the built image boot, did the migrations apply, did two
replicas of one image acquire two distinct identities.

**In one line:** when the subject under test is the project's own deployed
topology rather than the project's code, the test belongs in a fifth category
that the canonical gate cannot reach, is invoked by a named recipe whose comment
states the precondition, and never shares a line of setup with the harness-owned
test stack.

> **Core principle (separation of concerns / single responsibility):** the
> canonical gate has one job — prove the code is correct against infrastructure
> the harness builds from nothing. A deployment check has one job — read
> infrastructure an operator already provisioned. Mix them and you get a gate
> that is red whenever nobody has a stack up, or a check that silently never
> runs. Each category owns one lifetime of one kind of infrastructure.

## When to Apply

Apply this pattern when **the repository has a local-prod deploy** — the
`local-deploy-*` recipe family from `justfile-setup` exists (`local-deploy-up`,
`local-deploy-down`, `local-<component>-deploy-up/down`). That is the whole
condition: *not* conditional on the worker pattern, on having a fleet, or on
having more than one component. The category is created with its first member,
never pre-emptively:

- **First member, single service.** A deploy smoke check: the built image
  booted, the migrations applied, and the health endpoint answers — read from
  the stack `just local-deploy-up` left running. Every project with a local-prod
  deploy can write this one.
- **Second member, only when the worker pattern is adopted.** A fleet-identity
  check: two replicas of one image hold **distinct platform-derived names**; the
  **registration table** holds exactly one **runtime-created row per name**; the
  **active fingerprints** differ between the two rows; each row's **enabled**
  flag is set; and **no operator step created either row**. Those are the only
  concepts this check may name — see
  [worker fleet pattern](../scalability/worker_fleet_pattern.md) for the
  vocabulary, and do not reach for readiness or lifecycle concepts it does not
  define.

**When NOT to use:** a project with no local-prod deploy; a test needing a real
external server as a fixture (integration — below); a test needing only a real
database, a broker, or a spawned binary.

---

## Membership Is Decided by Subject, Never by Ownership

One sentence decides every case, and an agent applies it verbatim:

> **Is the project's own deployed topology the subject under test, or is
> external infrastructure merely scaffolding for exercising our code?**

Subject → deployment. Scaffolding → integration.

**The counterexample that makes the line sharp.** A test that can only run
against a real vendor server — a hosting control panel, a payment sandbox, a
storage appliance — needs infrastructure the harness cannot manufacture, and it
carries an `#[ignore]` for exactly that reason. It is *still integration*: its
subject is the adapter that talks to the vendor, the vendor's server is
scaffolding, and nothing about our deployment is under test. Invert the same
test — assert that *our* service, as deployed, reached the vendor at boot and
recorded the result — and the subject becomes our deployed topology, so it
becomes a deployment check.

Three obligations follow as consequences, not as independent membership tests:
it never runs in the canonical gate, because its precondition is normally
absent; it is invoked by a named recipe whose comment states that precondition;
and it lives in the deployment root with **child support only** — never in the
cross-category `tests/common/`, because a deployment helper has exactly one
consumer by construction.

**Closing mnemonic, not the criterion.** Read the table as a consequence; never
reach for it first, since ownership alone misplaces the vendor test.

| Who owns the infrastructure | Categories |
|---|---|
| nobody | unit, structure |
| the harness | integration, end-to-end |
| the operator | deployment |

---

## Rust Shape on a Workspace: a Dev-Only `deployment-checks` Crate

On a workspace the deployment category is **its own crate**, not a fifth test
target inside a component: a workspace member with an empty library, a
dev-dependency on the component it inspects, and its tests in its own `tests/`.

```text
Cargo.toml                    # [workspace] members = [..., "deployment-checks"]
<component>/tests/            # unit.rs, integration.rs, e2e.rs, structure.rs, and
                              # common/ — the harness-owned stack bring-up
deployment-checks/
├── Cargo.toml                # below
├── src/lib.rs                # empty — the crate exists to host tests/
└── tests/
    ├── structure.rs          # this member's own gate — the coverage rule requires one
    ├── deployment.rs         # entry point; mounts NOTHING from any tests/common/
    └── deployment/
        ├── deploy_smoke.rs   # tests only
        ├── deploy_smoke/
        │   ├── support.rs    # facade: declarations only
        │   └── support/      # constants.rs (keys, queries) + helpers.rs
        └── fleet_identity.rs # only when the worker pattern is adopted
```

```toml
# deployment-checks/Cargo.toml
[package]
name        = "deployment-checks"
version     = "0.1.0"
edition     = "2024"
publish     = false
description = "Deployment checks: read the local-prod deploy the operator started. Hosts tests only."

[dev-dependencies]
<component>           = { path = "../<component>" }                   # the component it inspects
<project>-conventions = { path = "../crates/<project>-conventions" }  # its structure gate

[lints]
workspace = true
```

Nothing in `[dependencies]`, and two dev-dependencies rather than one, because
**the checks crate owes a `tests/structure.rs` gate like every other member**:
`rust-conventions-crate-setup`'s coverage rule requires a gate from every
member, including one whose only job is to host tests, so without the file
`<component>-check` goes red the day the crate lands. Verified: adding the gate
leaves both isolation claims below intact. Its gate runs the universal rules
against this crate's own tree, which is one more reason those rules must
allowlist categories rather than deny them (below). `[lints] workspace = true`
keeps the crate under the workspace clippy table, without which the
"compiled, so drift breaks the build" claim below is weaker than stated. The
crate sits at the repository root beside the binaries it inspects, not under
`crates/`, because `rust-workspace-setup` reserves `crates/` for libraries two
or more members depend on and nothing depends on this one; if the workspace
prefixes its member names (`my-project-core`), prefix this one the same way and
use that name after `-p` in the recipes. The entry point declares
`mod deployment { mod deploy_smoke; }` and is named `deployment.rs` in **both**
shapes, so one conventions rule matches either.

### Unreachable by both gates, yet still compiled

| Command | Reaches the `deployment` target? | Verified output |
|---|---|---|
| `cargo test -p <component>` | **no** | builds and runs only that member's own targets; the checks crate is never built |
| `cargo test --workspace --test structure` | **no** | runs every member's `structure` target — the checks crate's included — and no other target, because `--test structure` selects by target name |
| `cargo clippy --all-targets --all-features -- -D warnings` | **compiles it** | `Checking deployment-checks v0.1.0` |
| `cargo test --workspace` | **YES — the hazard** | the checks run against whatever is on the machine; the exit code is the check's verdict, not a property of the command |

The first two rows are why **no `#[ignore]` is needed as the exclusion mechanism
in this shape**: `just test-all` runs one `cargo test -p <component>` per
component and `<component>-check` runs `cargo test --workspace --test
structure`; neither selects the `deployment` target. The third row is why the
crate is not dead weight — a planted unused variable in a check failed the
build with `error: unused variable` → `error: could not compile
'deployment-checks' (test "deployment")`, exit 101, so Rust-level drift breaks
the build on every quality-gate run even though nothing runs the checks.
**This holds because the workspace root is a virtual manifest with no
`default-members`.** Verified: with `default-members = ["core"]` added to the
root manifest, the same planted error passed clippy with exit 0 and the crate
was never checked. A workspace that sets `default-members` must list the checks
crate there, or drift goes unnoticed.

**State the hazard out loud, because it is one word away.** A bare `cargo test
--workspace` in any recipe *does* run the checks, against whatever happens to be
on the machine. Recipes never use it: dropping `-p <component>` or
`--test structure` silently enrols the category into the gate.

### Single-crate fallback

A project with one crate and no workspace has no place for a sibling member.
There the category is a **fifth `[[test]]` target** beside `unit`,
`integration`, `e2e`, and `structure`: `tests/deployment.rs` plus
`tests/deployment/`, same child-support layout as above. Here `cargo test -p
<component>` builds and runs every target, so the exclusion mechanism is
`#[ignore]` — and the **reason literal is required**, because a bare `#[ignore]`
tells the next reader nothing about the missing precondition.

```rust
// tests/deployment/deploy_smoke.rs — inside mod health_endpoint { … }
#[test]
#[ignore = "requires the local-prod deploy stack: just local-deploy-up"]
fn should_answer_after_migrations_applied() { /* ... */ }
```

Verified, in that order: `cargo test --test deployment` → `0 passed; 0 failed;
1 ignored`, with the per-test line `... ignored, requires the local-prod deploy
stack: just local-deploy-up` — the runner prints the literal, which is half of
why the literal is mandatory. Adding `-- --ignored --nocapture
--test-threads=1` → `1 passed; 0 failed; 0 ignored`, with the check's own output
on the terminal. And a target with **no** ignored tests under `-- --ignored` is
not an error: `cargo test --test unit -- --ignored` printed `0 measured;
1 filtered out` and exited **0**, so the recipe cannot detect an empty category
by exit code — the same blindness Python has, below.

**One hazard specific to this shape:** a crate-wide `cargo test -- --ignored`
sweep runs the deployment target along with every other ignored test (verified:
it ran the check and exited 0) — one more reason to prefer the crate shape.

**Escape hatch, for the day CI gains a prod-like stack.** Do not delete the
attribute; make it conditional, so the checks run where the stack exists and
stay ignored everywhere else:

```rust
#[cfg_attr(not(feature = "ci"), ignore = "requires the local-prod deploy stack: just local-deploy-up")]
```

Declare the feature in the crate manifest — `[features] ci = []` — or
`--features ci` is rejected as unknown and the attribute stays unconditional.

---

## Carve-Out From `rust-testing` Section 17

Section 17 requires every test to own its resources: a UUIDv7 suffix on every
created name, port `0` for every server, no fixed shared paths, explicit
teardown, `#[serial]` only as a last resort. **Deployment checks are exempt, and
the exemption is the point of the category.** The deployment the operator
provisioned has fixed container names, fixed host ports from the project's port
registry, and one shared database — that is what "deployed" means, and a check
that insisted on owning its resources would be provisioning, not observing.

So, in this category and nowhere else: fixed container names and fixed host
ports are correct (read from the port registry, never retyped); the shared
local-prod database is the right one to query; nothing is created, so nothing is
torn down; and **the checks run serially**, because they observe one shared
deployment and their output would otherwise interleave — the recipe passes
`--test-threads=1`, and `#[serial]` is the equivalent where a recipe cannot.
Everything else in `rust-testing` still binds: files contain only tests
(Section 16), helpers live in `support/` (Section 15), and there is no `mod.rs`.

---

## Mapping to Python

The Rust shape is one implementation of the invariants, not the invariants.
Python keeps every one, but two mechanisms differ enough to change the layout.

### The category is a sibling root, outside `tests/`

```text
pyproject.toml                  # testpaths = ["tests"]
tests/
├── conftest.py                 # session-scoped autouse: the shared stack
└── unit/  integration/  api/  architecture/
deployment_checks/              # sibling root — NOT under tests/
├── conftest.py                 # its own fixtures; no shared stack
└── test_deploy_smoke.py
```

Where `python-ddd`'s layout applies, the suite lives at `src/tests/` and
`testpaths = ["src/tests"]`; the sibling root then sits beside `src/`, still
outside the tree the root `conftest.py` governs. The rule is positional —
outside whichever `tests/` the project has — not a fixed path.

**Why not `tests/deployment/`?** Because a `conftest.py` under `tests/` cannot
opt out of the root `conftest.py`. Verified: with a session-scoped
`autouse=True` fixture in `tests/conftest.py` and a child `conftest.py` in
`tests/deployment_inside/`, `uv run pytest -n 0 -s -m deployment
tests/deployment_inside` printed `ROOT-CONFTEST-AUTOUSE-FIRED: booting the
shared test stack` before the test body — even though only the subdirectory was
named on the command line. The sibling root does not: the same command against
`deployment_checks` printed no root-conftest line at all.

The one apparent escape — redefining each root autouse fixture **by name** in
the child `conftest.py` — does suppress the root fixture (verified) and is
rejected anyway: it couples the child to every fixture name in the root, and
the next rename or addition boots the shared stack again, silently. A sibling
root has nothing to keep in sync. `testpaths` then keeps it out of the default
run with no marker work: verified, with `testpaths = ["tests"]`, `uv run pytest
-n 0 --collect-only -q` collected `2 tests`, none from `deployment_checks/`,
while naming the root explicitly collected `1 test`.

**If the project has no `testpaths`, adding one is part of adopting this
pattern.** Nothing else in the library sets it, and without it a bare
`uv run pytest` — what `just dev-<component>-test` runs — collects from the
rootdir and picks the sibling root up. Verified: removing `testpaths` turned
the same `--collect-only` run from `2 tests collected` into
`5 tests collected`, `deployment_checks/` included — the exact failure the
category exists to prevent.

### The `deployment` marker is a label, never the exclusion mechanism

Register it, so the intent is legible and `--strict-markers` accepts it:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-n auto"
markers = ["deployment: reads an operator-provisioned deployment"]
```

**Never rely on an `addopts` `-m "not deployment"` to keep the checks out**, for
one verified reason: a command-line `-m` **replaces** the `addopts` `-m` rather
than combining with it. With `addopts = '-n auto -m "not deployment"'`,
`uv run pytest -n 0 -q -m deployment tests` reported `1 passed, 1 deselected` —
the deployment test ran, where combining would have selected nothing, and there
is no warning. Directory separation excludes the category; the marker only says
what a test is.

### The recipe, and why each flag is there

```just
# [python] Read the running local-prod deploy and report its state.
# Precondition: `just local-service-deploy-up` completed and the stack is healthy.
local-service-deploy-check:
  cd service && uv run pytest -n 0 -s -m deployment deployment_checks
```

- **`-n 0`** turns `pytest-xdist` off, because the project's `addopts` carries
  `-n auto`. Two verified reasons. xdist **hides the deselected count**: one
  selection reported `1 passed, 1 deselected in 0.01s` under `-n 0` and
  `1 passed in 7.90s` under `-n auto`, so the operator loses the number saying
  the filter did something. And xdist **swallows `-s`**: the check's own output
  appeared under `-n 0 -s` and not at all under `-n auto -s`.
- **`-s`** because a deployment check's output *is* the result the operator
  reads — replica names, fingerprints, the health response. It is the
  counterpart of `--nocapture` on the Rust side.
- **`-m deployment`** selects within the named root; `deployment_checks`
  restricts collection to it. Both, not either.

**Create the recipe together with the first member**, not before. Verified:
pytest exits **5** both when the selection is legitimately empty (`-m
deployment` against a root with no members → `1 deselected`, exit 5) and when
the marker is misspelled (`-m deploymnet` against a root that *does* have
members → `1 deselected`, exit 5). The two are indistinguishable by exit code
and by summary line, so a recipe written ahead of its first member looks exactly
like one whose marker has a typo — and the first real member never reveals the
difference, because it turns the same command green.
`--strict-markers` does not close this: verified, it rejects an unregistered
marker **applied to a test** (exit 2) but accepts the same typo inside the `-m`
expression (still `1 deselected`, exit 5). A missing directory exits **4**, the
one mistake the exit code does distinguish.

### Category correspondence

| Rust root | Python root | Subject |
|---|---|---|
| `tests/unit/` | `tests/unit/` | pure logic, no infrastructure |
| `tests/integration/` | `tests/integration/` | one adapter or service against real infrastructure |
| `tests/e2e/` | `tests/api/` | a full flow across process boundaries |
| `tests/structure.rs` | `tests/architecture/` | the shape of the source tree |
| `deployment-checks/` (or `tests/deployment.rs`) | `deployment_checks/` | the deployed topology |

**A mapping, not a mirror.** Do not rename either tree for symmetry; each name
is the one its own ecosystem's tooling already uses.

---

## The Recipe Family

The recipe belongs to the **local-prod deploy** family, beside the recipes that
create the precondition it reads:

```just
# [rust] Read the running local-prod deploy and report its state.
# Precondition: `just local-core-deploy-up` completed and core is healthy.
local-core-deploy-check:
  cargo test -p deployment-checks --test deployment deploy_smoke -- --nocapture --test-threads=1
```

**The name filter is not optional.** One checks crate serves every
`local-<component>-deploy-check` recipe, so **every recipe carries a filter**
naming its own module. Verified: the unfiltered `cargo test -p deployment-checks
-- --nocapture --test-threads=1` ran `deploy_smoke` *and* `fleet_identity`, and
the fleet member fails on a correct single-service stack because its
precondition is a worker deploy scaled to two replicas. The filter selects every
test under `mod deployment { mod deploy_smoke { … } }` (verified with
`fleet_identity`: that module's test ran and the runner reported `1 filtered
out`). On the single-crate fallback the last line is instead `cargo test --test
deployment deploy_smoke -- --ignored --nocapture --test-threads=1`. The rules
around it are absolute:

- **Name it `local-<component>-deploy-check`**, beside
  `local-<component>-deploy-up/down` — not `<component>-check`, which is the
  CI-invoked quality gate and stays lint, format, type-check, structure test.
- **It lives in `just/deploy.just`** once the root justfile has been split by
  responsibility: with the deploy family whose precondition it reads.
- **`test-all` never calls it**, being one `dev-<component>-test` per component
  and the single recipe CI calls for the suite; and **CI never invokes it**,
  because CI invokes only `just` recipes and this one is in no job's list. If CI
  ever provisions a prod-like stack, add the job deliberately and switch to the
  `cfg_attr` form above.
- **The recipe comment states the precondition** as a command the operator can
  run. Where the procedure is longer, the recipe is one step of a guideline
  document and the comment points at it.

---

## The Day-1 Conventions Rule Is the Mount Rule

A project adopting this pattern ships **one** conventions rule with the category
itself, and it is not the `#[ignore]` rule. It is the mount rule, because that
failure is the silent one: an entry point that mounts the shared `tests/common/`
module still compiles, still passes, and boots the entire harness-owned Docker
stack — on a machine already running the local-prod stack the check exists to
read. Nothing turns red; the check merely becomes slow, wrong, and coupled to
infrastructure it must not know about.

The rule is `deployment_entry_point_mounts_nothing_from_common()`, in the
conventions crate's testing module. Following
[Rust conventions](../conventions/rust.md), the constructor is **zero-knob** —
`#[must_use] fn() -> Rule`, no path list, no allowlist, no severity flag — and
its policy values are private module constants. It flags any
`#[path = "common/…"]` attribute and any bare `mod common;` in
`tests/deployment.rs` (single-crate shape); and any `#[path]` in
`deployment-checks/tests/deployment.rs` whose target escapes the crate's own
`tests/` directory — the live vector is a relative mount such as
`#[path = "../../<component>/tests/common/infra.rs"]` — plus any
`use <component>::tests::common…` import (crate shape). It ships with
`should_flag` and `should_pass` fixture trees, each writing a throwaway tree
into a uniquely-suffixed directory and asserting on `violations()`, one
`should_pass` per rule-owned exemption.

**The `#[ignore]`-with-reason-literal rule ships later**, with the first member
of the single-crate shape — not day 1. Its failure is loud: a member written
without the attribute reddens `just test-all` in one CI run, so the review that
would write the gate catches it. Ordering the two rules by how quietly they fail
is the whole reason the mount rule goes first; in the crate shape the second is
never needed, because no gate reaches the crate.

**Category-enumerating rules are allowlists, never denylists.** A rule phrased
as "`mocks.rs` may not appear under `integration` or `e2e`" stops covering the
tree the moment a fifth category exists. Phrase it as **"`mocks.rs` exists only
under `tests/unit/**/support/`"** and the new category is covered the day it is
created. Audit every rule that names categories by hand; each is a denylist
waiting to go quiet.

---

## Precondition Ignore vs Ratchet Ignore

Two uses of `#[ignore]` look identical in source and mean opposite things, and
conflating them is what makes projects ban the attribute outright. A
**precondition ignore** names an external precondition the harness cannot create
(`#[ignore = "requires the local-prod deploy stack: just local-deploy-up"]`):
fixing code will never make it runnable, only provisioning the precondition
will, so it is permanent by design, carries no owner and no date because there
is nothing to come back to, and its reason literal is the operator's
instruction. A **ratchet ignore** hides a test that fails or is unimplemented
(`#[ignore = "pending the retry policy"]`): a debt marker, which must carry an
owner and a date, is expected to disappear, and makes the suite lie about its
coverage for every day it survives. The library's "no `#[ignore]`" checks
elsewhere target **ratchets**; the deployment category is the one legitimate
home of precondition ignores — and in the crate shape it needs none at all.

---

## Worked Example (ironbox)

The reference codebase created the category for a single member and recorded it
as an ADR. Worker-fleet work produced a check that stack ownership could not
accommodate: it asserts that two Worker replicas of one image hold independent
identities, reading `worker_registrations` in the *local-deploy* database that
`just local-deploy-up` plus `just local-worker-deploy-up <replicas>` left
running — not the test-stack database. The harness could not manufacture a
scaled Worker deployment, so the infrastructure's lifetime belonged to the
operator and the test was a reader of it.

It first landed as `core/tests/deployment_fleet_identity.rs`: a fifth root with
no category, no document, and a helper parked in `core/tests/common/` though it
served one consumer — replacing `tools/scripts/worker-fleet-identity-check.sh`,
a shell script no gate had ever compiled. Its recipe,
`worker-fleet-identity-check replicas="2"`, broke the naming rule as well as
the placement one: it sat outside the deploy family, and it drove a fifth
`[[test]]` target inside the component crate with `-- --ignored --nocapture`,
making `#[ignore]` load-bearing (the `--nocapture` was the one deliberate part:
the check reports a live fleet's state). `core/tests/integration.rs` and
`core/tests/e2e.rs` both `#[path]`-mount `common/infra.rs`, whose `#[ctor]`
boots a fifteen-container stack merely by loading the binary — the structural
reason the category is a separate target rather than an `#[ignore]`d corner of
`e2e`. On a workspace, prefer the crate.

---

## Quick Reference — Invariants

- **Membership is decided by subject, never by ownership** — a real vendor
  server used as a fixture stays in integration. **The category exists only
  where a local-prod deploy exists**, created with its first member and its
  recipe together, never pre-emptively.
- **On a workspace it is a dev-only `deployment-checks` crate** with its own
  `tests/structure.rs` gate. Its `deployment` target is unreachable by
  `cargo test -p <component>` and `cargo test --workspace --test structure`, and
  compiled by `cargo clippy --all-targets --all-features -- -D warnings` while
  the root sets no `default-members` (or lists the crate). No recipe runs a bare
  `cargo test --workspace`; every recipe carries a name filter.
- **In Python it is a sibling root outside `tests/`**, kept out of `testpaths`
  (added if absent), because a child `conftest.py` cannot opt out of the root's
  autouse fixtures. The `deployment` marker is a registered label, never the
  exclusion mechanism; the recipe passes **`-n 0 -s`**.
- **Deployment checks are exempt from every-test-owns-its-resources**
  (`rust-testing` Section 17) and run serially. In the single-crate fallback
  each carries `#[ignore = "<reason naming the missing precondition>"]`.
- **The recipe is `local-<component>-deploy-check`**, in the deploy family:
  never in `<component>-check`, never in `test-all`, never invoked by CI.
- **The deployment entry point mounts nothing from `tests/common/`** — the
  day-1 conventions rule — and category-enumerating rules are allowlists.

---

## Anti-Patterns to Avoid

- **A stray test root** — a fifth file under `tests/` with no category, no
  recipe, no document. Nothing tells the next reader which stack it wants.
- **Folding the check into `e2e` behind an `#[ignore]`.** End-to-end promises a
  harness-owned stack, any `-- --ignored` sweep fires the check at whatever
  stack is up, and the e2e entry point boots a stack the check has no use for.
- **Deployment helpers in `tests/common/`**, which is for helpers shared by two
  or more categories; a deployment helper has one consumer.
- **A bare `#[ignore]` with no reason literal**, or **`#[ignore]` as the
  exclusion mechanism when a workspace crate would do** — `just test-all` is
  then one forgotten attribute away from red.
- **An unfiltered recipe against a shared checks crate**, which runs every
  member's check — the fleet check included — against a single-service stack.
- **`required-features` on the test target**, or `harness = false`. The first
  converts a compile error into a silent absence; the second loses `#[ignore]`,
  the name filter, and `--nocapture` semantics.
- **A Python check under `tests/`, excluded by `addopts = '-m "not deployment"'`
  and run under xdist** — three mistakes that each fail silently: the root
  `conftest.py` boots the shared stack, a command-line `-m` replaces the
  `addopts` one, and xdist hides the deselected count and swallows `-s`.
- **Reading a green gate as evidence the deployment is healthy** — nothing in
  the canonical gate ever runs these checks — or **leaving the job to a shell
  script under `tools/`**, whose untyped SQL and `docker` strings no gate
  compiles.

---

## Relationship to Other Patterns and Skills

- **[parallel test isolation](parallel_test_isolation_pattern.md)** — the
  harness-owned side of the boundary: exactly what this category must not
  inherit.
- **[worker fleet pattern](../scalability/worker_fleet_pattern.md)** — supplies
  the second member and the only vocabulary it may use.
- **[Rust conventions](../conventions/rust.md)** — how the mount rule is
  written: zero-knob constructor, private constants, `should_flag` /
  `should_pass` trees.
- **`rust-conventions-crate-setup`** — its coverage rule is why the checks crate
  carries a `tests/structure.rs` gate and a dev-dependency on the conventions
  crate.
- **`rust-testing`** — owns the four existing categories (Sections 8, 9, 12),
  the support discipline this one reuses (Section 15), and the isolation rules
  it is carved out of (Section 17).
- **`python-testing`** — owns the `conftest.py` layering the sibling root
  follows internally; `deployment_checks/` is a sibling of `tests/`, not a
  fourth entry in it.
- **`justfile-setup`** — owns the recipe taxonomy: the `local-*-deploy-up/down`
  family the recipe joins, and `just/deploy.just` as its home.
- **`ci-setup`** — CI invokes only `just` recipes, so staying out of
  `<component>-check` and `test-all` keeps the recipe out of CI.
- **`greenfield-project-setup`** — the local-prod deploy comes from phase 5, the
  worker from phase 7 (opt-in); the category is a phase-8 decision, recorded
  with its first member.
