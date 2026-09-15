---
name: configuration-authority-pattern
description: >-
  Use when starting a new backend project, or reviewing one whose settings have
  outgrown the way they are delivered, and any of these symptoms are present: a
  flat environment namespace that has grown past a dozen variables; a
  credential-bearing URL such as `DATABASE_URL=postgres://user:password@host/db`
  sitting in a configuration file or a deployment template; secrets and ordinary
  settings arriving through one shared delivery mechanism; tests that mutate the
  process environment to steer the code under test; a constant that a timing or
  protocol proof depends on exposed as a deployment knob; a library crate or
  package that reads the environment on its own. Produces a day-1 ADR that fixes
  one authority per setting, one typed model per concern, and a secret-delivery
  tier chosen from the project's observable deployment facts — so a small tool
  is never told to run a secret store, and a fleet never ships credentials in
  environment variables.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.1"
---

# Configuration Authority Pattern

## Purpose

**In one line:** every setting has exactly one authority; secrets are a separate
typed input rather than a configuration source; and the *delivery mechanism* for
that secret input is a tier chosen from the project's deployment facts, while
the *consumer contract* is identical at every tier.

Configuration starts as three environment variables and is never revisited. By
the time it is twenty variables carrying a database password, a bind address, a
retry budget, and a cancellation window, nothing can be reviewed or validated as
a whole, and the password has the lifecycle of the port number. The usual
corrections are both wrong: one file for everything gives secrets the backup and
review lifecycle of ordinary policy, and one secret store for everything makes a
store's availability a precondition for knowing which port to bind.

Two facts resolve it:

1. **Settings differ by authority, not by type.** A password, a bind address, a
   retention window, and a protocol timeout are all "configuration" only in the
   sense that all four are values. They differ in who may change them, how
   often, through what review, and with what evidence.
2. **The boundary is universal; the delivery mechanism is not.** Reading one
   complete document, validating it whole, and swapping it atomically is the
   same code whether the file was written by a platform, a Compose secret, or a
   secret-store agent. Only the *producer* changes, and that is a deployment
   concern.

So the day-1 decision is about *authority and the boundary*. The store, if the
project ever needs one, is a later deployment choice the boundary already
accommodates.

> **Core principle (separation of concerns / single responsibility):** each
> setting has one owner, and each module has one job. The configuration boundary
> owns *acquiring and validating*; the composition root owns *wiring*; the
> application owns *behaviour* and never learns where a value came from. A
> module that both reads a source and decides business behaviour is two
> responsibilities wearing one name.

## When to Apply

- A flat environment namespace has grown past a dozen variables, and nobody can
  answer "what does this deployment actually run with?" from one artefact.
- A credential-bearing URL — `DATABASE_URL=postgres://user:password@host/db`,
  an AMQP URL, an S3 URL with an access key — appears in a configuration file, a
  Compose file, a Helm values file, or a checked-in template.
- Secrets and ordinary settings share one delivery mechanism, so rotating a
  password means editing the file that also holds the log level.
- Tests mutate the process environment (`std::env::set_var`,
  `monkeypatch.setenv`) to steer the code under test, which makes them
  order-dependent and hostile to parallel execution.
- A constant that a timing or protocol proof depends on — a termination grace
  period, a frame-size limit, a cancellation window — is exposed as a deployment
  knob, so one deployment can silently invalidate the proof.
- A library crate or package reads the environment. A library has no process; it
  cannot own a process's configuration.
- You are about to write the first deployment manifest, and the question "where
  do the secrets come from?" is about to be answered by accident.

**When NOT to use:** a throwaway script with no deployment and no settings
beyond its command-line arguments. Everything with a process lifetime and a
deployment applies, including a Tier-0 project with no secret at all yet.

## The Five Authority Classes

Every setting the process consumes is classified into exactly one class. A value
must not exist in two classes, and must never fall back from one to another.

| Class | Authority | Examples | Change lifecycle |
| --- | --- | --- | --- |
| **Secret material** | the secret input for the project's delivery tier | passwords, tokens, API keys, enrollment secrets, encryption keys | startup-only until a class-specific rotation protocol exists |
| **Bootstrap configuration** | the process environment or a process argument | configuration-document path, secret-source selector, secret bundle path, platform-created instance identity | process or deployment restart |
| **Deployment policy and tunables** | one versioned structured document per process | bind addresses, endpoints, concurrency, timeouts, retry and retention settings, deployment feature selection | validated at startup; restart unless an explicit reload contract exists |
| **Runtime product policy** | a durable administrative control plane | policy an operator must change without replacing the process | transactional update through an authenticated API and a durable store |
| **Safety and protocol mechanics** | source-code constants, or a shared wire-contract package | termination grace periods, cancellation windows, frame-size and closed-enum limits | code change, contract amendment, and a release |

Three rules keep the table honest:

- A setting does not become **runtime product policy** because changing it
  without a restart would be convenient. It belongs there only when the product
  requires a live, durable, auditable administrative change. This class is
  allowed to be empty, and on most projects it starts empty.
- A **safety constant** is not copied into the configuration document "for
  consistency". A deployment knob must never shadow a value a cross-process
  proof depends on.
- **Tenant data, domain state, test fixtures, and third-party tools' own
  variables are out of scope.** This pattern governs one process's own
  configuration, not everything shaped like a key and a value.

## Typed Models Remain Canonical

Changing the external source must not flatten the internal model. The typed,
concern-specific structures are the runtime source of truth; callers receive
validated types, never a string map and never a source lookup.

```text
external sources (bootstrap inputs, one document, one secret input)
        ▼
source adapters and parsing     ← knows about TOML, files, the environment
        ▼
concern-specific validation     ← one type per concern, one owner each
        ▼
typed AppConfig / WorkerConfig  ← immutable for the process lifetime
        ▼
composition root                ← the only place adapters are constructed
```

Two consequences follow, and both are load-bearing:

- **Libraries never read configuration.** A library crate or package takes its
  settings as constructor parameters; the *consuming process* reads the
  document, validates it, and passes typed values down. A library that reads the
  environment cannot be tested without a process, cannot be used twice in one
  process with different settings, and has claimed an authority that belongs to
  its caller.
- **Source precedence never leaks into consumers.** No application service asks
  "was this from the file or the environment?" The boundary answers once, before
  any service exists.

## Staged Adoption

### Stage 1 — commit 1, every project

This is the universal part. It costs one module — `infrastructure/config/` in
this library's layered layouts, the only module allowed to touch a source —
and no dependencies beyond a parser, and it is the part that is expensive to
retrofit.

1. **One typed model per concern.** `ServerSettings`, `DatabaseSettings`,
   `TaskSettings` — not one `Settings` god-struct, and never a generic map.
2. **One versioned document per process.** TOML by default: hierarchical,
   commentable, and native to both ecosystems (on Python, `tomllib` is in the
   standard library). It carries `schema_version`, and **unknown versions and
   unknown fields fail closed**. Decode the version first, then the body — a v2
   document must be rejected for being v2, not for a field v1 does not know.
3. **The environment is bootstrap only, and enumerated.** Four kinds of value,
   reviewed whenever a fifth is proposed: `<PREFIX>_CONFIGURATION_PATH`,
   `<PREFIX>_SECRET_SOURCE`, `<PREFIX>_SECRET_BUNDLE_PATH`, and platform-created
   instance identity such as a Kubernetes Pod name. The one addition is
   explicit: when `<PREFIX>_SECRET_SOURCE=environment` is selected — development
   and tests only — the secret fixtures named by the secret model are read from
   the environment too, and from nowhere else.
4. **No environment-variable expansion inside the document.** It recreates
   hidden source precedence inside the file that was supposed to end it.
5. **Defaults only where absence is genuinely safe.** A required value stays
   required after every permitted source has been resolved.
6. **A fail-fast loader whose errors name the setting path and its authority
   class, and never a value.** One complete immutable startup generation, or no
   process.
7. **Tests go through an injectable lookup seam and never mutate the process
   environment.** The seam is a trait or a `Mapping`; production passes the real
   environment, tests pass a literal map.
8. **Safety constants stay code-owned** — in the crate or package that owns the
   proof they belong to.
9. **Secrets are a separate typed input in a redacting type.** The endpoint half
   of a connection lives in the document, the credential half in the secret
   input; the URL is assembled in memory when the driver needs it and is never
   serialized, logged, or written back.
10. **The explicit selector is required from the moment the first secret
    exists.** No inference from file existence, no fallback between modes.

#### The document, and the two-pass decode

```toml
schema_version = 1

[server]
bind_address = "0.0.0.0"
port = 8000

[database]
host = "postgres.internal"
port = 5432
database_name = "backend_service"
tls_mode = "verify-full"
```

```rust
// src/infrastructure/config/document.rs
pub const SUPPORTED_SCHEMA_VERSION: u32 = 1;

/// First pass: decode only the schema version, tolerating every other field.
#[derive(Debug, Deserialize)]
struct SchemaVersionEnvelope {
    schema_version: u32,
}

#[derive(Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct DatabaseSettings { /* host, port, database_name, tls_mode */ }

impl ConfigurationDocument {
    pub fn parse(document_text: &str) -> Result<Self, ConfigurationError> {
        let envelope: SchemaVersionEnvelope = toml::from_str(document_text)?;
        if envelope.schema_version != SUPPORTED_SCHEMA_VERSION {
            return Err(/* names `schema_version`, class deployment policy */);
        }
        // Second pass: the whole body, every concern in its own type,
        // every unknown field rejected.
        toml::from_str(document_text).map_err(/* … */)
    }
}
```

Verified with `cargo test` on `cargo 1.95.0`, `serde 1.0.229`, `toml 1.1.6`. The
two failures produce exactly:

```text
configuration error at `<document>` (deployment policy): unknown field `sslmode`,
  expected one of `host`, `port`, `database_name`, `tls_mode`
configuration error at `schema_version` (deployment policy): unsupported schema
  version 2, this build accepts 1
```

Those use `toml::de::Error::message()`. Its full `Display` additionally renders
the line, column, and a caret under the offending key (verified) — prefer it in
the loader, because an operator reading a startup failure wants the line number.

#### The environment seam and the selector

```rust
// src/infrastructure/config/bootstrap.rs
pub trait EnvironmentLookup {
    fn read(&self, variable_name: &str) -> Option<String>;
}

pub struct ProcessEnvironmentLookup;

impl EnvironmentLookup for ProcessEnvironmentLookup {
    fn read(&self, variable_name: &str) -> Option<String> {
        std::env::var(variable_name).ok()
    }
}

impl EnvironmentLookup for BTreeMap<String, String> { /* tests pass a map */ }

/// No `Default`, no inference from file existence, no fallback between variants.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SecretSource { File, Environment }
```

The four bootstrap values are read once, through the seam, into one
`BootstrapInputs` value (configuration path, secret source, optional bundle
path, optional instance identity) that both loaders take. The composition root
sees three calls and nothing else:
`BootstrapInputs::read(&ProcessEnvironmentLookup)`,
`AppConfig::load(&bootstrap)` (which parses the document named by the path), and
`SecretGeneration::load(&bootstrap)` (which reads the selected source). The
loader takes `&impl EnvironmentLookup`, so the test that proves "a missing
selector fails" passes a three-entry `BTreeMap` and never touches the process.
Verified: `BACKEND_SERVICE_SECRET_SOURCE` absent yields `configuration error at
'BACKEND_SERVICE_SECRET_SOURCE' (bootstrap): required, not set`, and the value
`auto` yields `… expected 'file' or 'environment'`.

#### The redacting secret type

```rust
// src/infrastructure/config/secret.rs
pub const REDACTED_PLACEHOLDER: &str = "<redacted:secret>";

/// Minting a fence is restricted to the configuration boundary, so a distant
/// call site cannot construct secret material out of arbitrary bytes.
pub struct SecretMaterialFence(());

impl SecretMaterialFence {
    pub(in crate::infrastructure::config) fn mint() -> Self { Self(()) }
}

pub struct SecretString { value: String }

impl SecretString {
    pub fn new(value: String, _fence: &SecretMaterialFence) -> Self { Self { value } }

    /// The only way to read the material. Never call this from a log, span,
    /// error variant, `Debug`, or `Display` path.
    pub fn expose_secret(&self) -> &str { &self.value }
}

impl Drop for SecretString {
    fn drop(&mut self) { self.value.zeroize(); }   // the `zeroize` crate
}
// Debug, Display, and Serialize each write REDACTED_PLACEHOLDER.
```

Verified with `cargo test`: `format!("{password:?}")` and
`format!("{password}")` produce `<redacted:secret>`,
`serde_json::to_string(password)` produces the JSON string
`"<redacted:secret>"`, and the derived `Debug` of the enclosing struct inherits
it — `SecretGeneration { generation_id: "a3f1", database_username:
"backend_service", database_password: <redacted:secret> }`. Minting a fence from
an integration test fails to compile: `error[E0624]: associated function 'mint'
is private`.

**On the off-the-shelf alternative.** `secrecy 0.10.3` gives `SecretString`,
`expose_secret()`, and zeroize-on-drop, and its `Debug` prints
`SecretBox<str>([REDACTED])` — verified by running it. Two gaps: it implements
no `Display` (`error[E0277]: 'SecretBox<str>' doesn't implement
'std::fmt::Display'`), and its `Serialize` is gated on a `SerializableSecret`
marker that emits the **real** value for types opting in (`secrecy` 0.10.3
`src/lib.rs`, 273–325). If any structured-log frame serializes a struct holding
the secret, write your own type as above.

#### Decomposing a credential-bearing URL

Host, port, database name, and TLS mode come from the document; username and
password from the secret input; the URL exists only in memory.

```rust
// src/infrastructure/config/loader.rs — the two halves meet here and nowhere else.
pub fn connection_url(&self) -> SecretString {
    let url = format!(
        "postgres://{}:{}@{}:{}/{}?sslmode={}",
        self.username, self.password.expose_secret(),
        self.host, self.port, self.database_name, self.tls_mode,
    );
    SecretString::new(url, &SecretMaterialFence::mint())
}
```

The result is itself a `SecretString`, so a `{connection_url:?}` in a `tracing`
span renders `<redacted:secret>` — verified. Where the driver exposes a typed
builder rather than a URL, prefer the builder: percent-encoding, virtual-host
semantics, and TLS identity then each have one explicit typed path instead of
one string that has to be right.

## The Delivery Tiers

Stage 1 says a secret is a separate typed input. It does not say where that
input comes from. **That is a tier, chosen from observable deployment facts and
recorded in the project's ADR.** A wrapper around a system library must not be
told to run a secret store.

| Tier | The project looks like | Delivery | Commits to |
| --- | --- | --- | --- |
| **0** | A process with no secret material at all — a single-binary service, a scheduled job, a CLI with a configuration file | None. The configuration boundary still applies in full | Nothing |
| **1** | Secrets exist, and **the host or the repository produces the secret file**: a systemd credential, a Compose `secrets:` entry with a `file:` source, a file an operator placed on a bare host | That one file, holding the whole bundle document | Nothing beyond what is already installed |
| **2** | Secrets exist, and **the secret is an object in a deployment control plane's API** with its own lifecycle — a Kubernetes `Secret`, a Docker Swarm secret — that the manifest references by name | That object mounted as one file, holding the whole bundle document | The deployment platform you already run |
| **3** | A fleet, a SaaS, audited rotation, or one secret shared across process classes | A secret store with a sidecar agent that renders one complete versioned bundle | A store, and its own operational lifecycle |

**Tier 0 — no secret material.** No secret input, no selector, no bundle path.
The document, the typed models, the fail-fast loader, and the bootstrap
enumeration all still apply — they are what make the project reviewable before
it has secrets. When the first secret appears it gets a home in the secret
boundary, never a line in the configuration document and never a fourteenth
environment variable. Two neighbours of Tier 0 have even less: a **library**
owns no process and reads nothing — it takes its settings as parameters from
whatever process embeds it; a **CLI whose only settings are its arguments** has
no document yet, and the boundary begins with its first file-borne setting.

**Tier 1 — the host or the repository produces the file.** Each mechanism
delivers *one file per declared credential*, so the project declares exactly
**one** credential whose content is the whole bundle document — never one
platform secret per field, which would hand the process a pile of unversioned
fragments with no `schema_version` to check. `<PREFIX>_SECRET_BUNDLE_PATH`
names that one file. One sentence of mechanism each, verified against upstream
documentation:

- **systemd:**
  `LoadCredential=backend-service-secrets:/etc/backend-service/secrets.toml`
  "may be used to load a credential from disk, from an AF_UNIX socket, or
  propagate them from a system credential", and the service reads it from the
  directory named by `$CREDENTIALS_DIRECTORY` (`/run/credentials/<unit name>`
  for a system service, which the documentation asks you not to hardcode), with
  access restricted to the service's user
  ([systemd.io/CREDENTIALS](https://systemd.io/CREDENTIALS/)).
- **Docker Compose:** a top-level `secrets:` entry with a `file:` source —
  `backend_service_secrets: { file: ./secrets.toml }` — referenced by the
  service's own `secrets:` list, is made available at
  `/run/secrets/<secret_name>` inside the container, and "services can only
  access secrets when explicitly granted by a secrets attribute"
  ([Docker Compose secrets](https://docs.docker.com/compose/how-tos/use-secrets/)).
- **A bare host:** a file owned by the service user with mode `0400` (or
  root-owned `0440` with the service's group), written by the operator's
  provisioning step and never by the process; the unit or supervisor runs the
  process as that user.

Environment mode still exists at Tier 1 — for development and tests — and it is
reached only through the explicit `<PREFIX>_SECRET_SOURCE` selector. No store,
no agent, no sidecar.

**Tier 2 — a control-plane secret object.** A Kubernetes `Secret` mounted as a
volume: `volumes: [{name, secret: {secretName}}]` plus a container
`volumeMounts` entry with `readOnly: true` and a `mountPath`, after which each
key of the Secret "appears as a file" under that path
([Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)).
The Secret therefore carries **one key**, `secrets.toml`, whose value is the
whole bundle document. A Docker Swarm secret is the Compose-family equivalent;
a plain Compose `file:` secret is Tier 1, because the repository or the host
produced the file. The application code is unchanged from Tier 1 — only the
manifest differs.

**Tier 3 — a store with a rendering agent.** A secret store renders one
complete, versioned bundle file per process class through a sidecar agent. The
contract accepts any store that can render one complete bundle; what the tier
commits to is the *shape*, not the product:

- One document per process class, carrying at minimum a schema version, a
  monotonic generation identifier, and every field that class needs. Related
  values are never assembled from independently versioned paths.
- Render with missing-key failure enabled, `0400` or `0440` permissions,
  template backup files disabled, onto an empty ephemeral volume.
- **Startup fails closed without freshness proof.** An empty render volume is
  hygiene, not evidence: a restarted container can reuse an ephemeral volume,
  and a newly scaled process can see a bundle rendered for another process's
  startup. The deployment must supply evidence tied to the current startup
  epoch, and the process must not accept work without it. One workable shape,
  for the Tier-3 ADR to adopt or replace: the deployment mints a startup epoch
  value, injects it as the process's platform-created instance identity, and
  has the agent write the same value into the bundle as `rendered_for_epoch`;
  startup rejects a bundle whose epoch differs. This proof exists only at
  Tier 3 — a Tier-1 or Tier-2 file has no producer that could stale-render it.

#### The consumer contract — identical at Tiers 1, 2, and 3

The contract holds at every tier because every tier delivers **one file that
is the whole bundle document**: a TOML document with `schema_version` and the
secret fields, plus a generation identifier where the producer supplies one
(Tier 3). Declaring one platform secret per field would break it.

```text
read one complete candidate file
  → parse the complete document
  → validate the schema version, the generation where present, and every field
  → construct a complete candidate generation
  → atomically swap the in-memory generation

any failure at any step
  → retain the previous validated generation, unchanged
```

Correctness never depends on the producer performing an atomic rename: the
consumer tolerates a truncated, concurrently observed, malformed, stale, or
incomplete file by keeping what it already validated. Startup accepts exactly
one complete document and never combines fragments. Observability reports only
non-secret metadata — active generation identifier, activation time, and a
sanitized reason for a rejected candidate — never a field value, and never the
producer's own health as if it were application health.

**Because the contract is the same, moving up a tier is a deployment change, not
an application change.** That is the point of choosing a tier rather than a
store.

#### Triggers that move a project up a tier

Record these in the ADR alongside the chosen tier, so the next reviewer does not
have to re-derive them.

To Tier 2:

- The deployment gains a control plane that owns secret objects (a Kubernetes
  cluster, a Swarm), so the file no longer comes from the repository or the
  host.
- The same secret must reach more than one process class, and editing a
  repository file per class is how it gets there today.

To Tier 3:

- Credentials must be short-lived or issued dynamically — leases, time-to-live,
  per-process identities — which no platform-native secret object provides.
- Rotation without a redeploy is required.
- Access audit — who read which secret, when — is required.
- An operator-managed store already exists and the project would be the only
  thing outside it.

### Stage 2 — bound to the first production deployment milestone

Not "later, somewhere": the plan that builds the first production deployment
owns all of it.

- **Read-only mounts.** Permissions and ownership prevent the process from
  modifying either the configuration document or the secret bundle.
- **Immutable, revision-named ConfigMaps** (or their equivalent) referenced from
  the pod template, so a change produces a new object name and therefore a
  restart — drift cannot be silent. On Compose, restart the container when its
  image or its document changes.
- **Startup freshness proof** for the secret input, at Tier 3 only (above).
- **Last-known-good on outage.** A running process keeps its last validated
  generation when the producer is unavailable; readiness is not withdrawn merely
  because a refresh failed while the active generation is still usable.
- **Cross-process invariants validated at deployment-assembly time.** One typed
  authority emits every process's document from one canonical input and checks
  the invariants *before* the artefacts exist: paired timeouts that must match,
  a shared secret both processes consume, a heartbeat and the staleness window
  that reads it. A failure must surface at assembly, never as a runtime
  assertion — by then the fleet is already deployed inconsistently.

### Stage 3 — only on demonstrated need

A setting that must change without restarting the process becomes durable
product state behind an authenticated administrative control plane — never a
watched file. It requires validation before commit, transactional persistence,
authorization and audit evidence, a typed read model, explicit propagation
semantics, and a defined behaviour when a process cannot yet observe the new
value. The database is storage, not the public interface; operators do not edit
rows.

Per-class hot reload of secrets is likewise not authorized by the file having
changed. Each class stays startup-only until its own protocol exists:
**prepare** every affected client, **prove** each accepts it, **commit**
that class atomically and route new work to it, record the accepted generation,
then drain the prior one — and only then revoke the old external credential. One
candidate changes exactly one secret class; a candidate that changes two is
rejected.

## Gates

Prose does not hold a boundary. Three gates follow, and one of the rules you
want cannot be written in configuration at all. "Tier" in this section means
the enforcement ladder of [conventions/python](../conventions/python.md) —
config-only, lint plugin, architecture-as-tests — not the secret-delivery tier
above; every gate here applies at every delivery tier.

#### Python — ruff `banned-api` (conventions ladder tier 1)

```toml
# `TID` is already in python-project-setup's `select` list; add only the tables
# below — do not replace `select`.
[tool.ruff.lint.flake8-tidy-imports.banned-api]
"os.environ" = { msg = "Read the process environment only in backend_service.infrastructure.config.bootstrap, through EnvironmentLookup." }
"os.getenv"  = { msg = "Read the process environment only in backend_service.infrastructure.config.bootstrap, through EnvironmentLookup." }

[tool.ruff.lint.per-file-ignores]
"src/backend_service/infrastructure/config/bootstrap.py" = ["TID251"]
# Test support may READ the environment for harness addresses (the isolation
# pattern's admin URL); it may never mutate it — that rule is the tier-3 one.
"src/tests/**" = ["TID251"]
```

Verified with `ruff 0.16.2` (`uv run ruff check`): all three forms fire —
`os.environ["NAME"]` and `os.getenv("NAME")` at the attribute, and
`from os import environ` at the imported name. The exemption was verified in
both directions: with the `per-file-ignores` entry present,
`ruff check --select TID251` reports zero hits in `bootstrap.py`; with the entry
deleted it reports the one at `bootstrap.py:22`, where the configuration
boundary legitimately returns `os.environ`.

#### Python — the rule ruff cannot express (conventions ladder tier 3)

`monkeypatch.setenv` **cannot** be banned by ruff. Verified: a
`"monkeypatch.setenv"` entry in `banned-api` produces no diagnostic, because
`monkeypatch` is a fixture parameter, not a resolvable qualified name. Banning
`"pytest.MonkeyPatch"` instead does fire — but on the *annotation*
(`def test_x(monkeypatch: pytest.MonkeyPatch)`) and on
`pytest.MonkeyPatch.context()`, which bans every legitimate `setattr` use as
well; and an unannotated `def test_x(monkeypatch)` escapes it entirely, verified
to produce `All checks passed!`.

So it belongs at tier 3, in the conventions package described by
[conventions/python](../conventions/python.md). Specify it, do not hand-roll it
here:

- **Name:** `tests_do_not_mutate_the_process_environment()`.
- **Zero-knob**, per that document: no path list, no allowlist, no severity. It
  takes only `package_root(__file__)`.
- **Detection:** over the `ast` of every test module, flag `setenv` or
  `delenv` called on the `monkeypatch` fixture or on a `pytest.MonkeyPatch`
  instance, and any assignment or `del` targeting an `os.environ` subscript.
- **Fixtures:** a `should_flag` tree containing each of those forms, and a
  `should_pass` tree containing a test that injects a literal `dict` into the
  loader — so the rule is proven to fire and proven not to over-fire.

#### Rust — the conventions crate

Specify a rule in the dev-only conventions crate described by
[conventions/rust](../conventions/rust.md), consumed from each member's
`tests/structure.rs`:

```rust
#[test]
fn environment_reads_are_confined_to_the_configuration_boundary() {
    conventions::environment_reads_are_confined_to_the_configuration_boundary()
        .enforce(env!("CARGO_MANIFEST_DIR"));
}
```

Zero-knob, as that pattern requires. Under `src/` it flags every read —
`var`, `var_os`, `vars`, `vars_os`, whether spelled `std::env::…` or
`env::…` — outside the configuration boundary module,
`src/infrastructure/config/`, the same home `python-ddd` and
`rust-hexagonal-architecture` give it. Under `tests/` it flags only mutation —
`set_var` and `remove_var` in either spelling — because test support
legitimately reads harness addresses such as the isolation pattern's admin URL.

**Say plainly what it cannot see.** The scan is syntactic: `use std::env::var as
read_setting;` renames the call and the rule goes quiet, as does a read behind a
macro, a build script, or a dependency. A syntactic rule can only promise a
syntactic exception — the honest framing the Rust conventions document already
uses. The gate closes the accidental path, not the determined one; the
determined one is a review finding, and the reason the boundary is also an ADR.

## Mapping to Python

Everything above holds. The differences are in the tools, not the invariants —
with one honest exception: two checks serde performs for free in Rust must be
written by hand in Python, shown below.

| Concern | Rust | Python |
|---|---|---|
| Document format | the `toml` crate | `tomllib` from the standard library — verified on CPython 3.14.6, the mandatory greenfield floor, so Stage 1 adds no dependency |
| Per-concern type | `#[derive(Deserialize)]` struct with `#[serde(deny_unknown_fields)]` | frozen `@dataclass` per concern, constructed with `**section` |
| Unknown-field rejection | `deny_unknown_fields` | inside a section, the dataclass `__init__` — an unexpected keyword is a `TypeError`; at the top level, and for field *types*, two explicit checks (below): dataclasses validate nothing at runtime |
| Schema-version gate | decode a version-only envelope first | read `document.get("schema_version")` before building any section |
| Environment seam | `trait EnvironmentLookup` | a `Mapping[str, str]` parameter; production passes `os.environ`, tests pass a `dict` |
| Selector | a `#[derive]`-free enum with an explicit parser | a `StrEnum`; `SecretSource(selector)` raises `ValueError` on anything else |
| Redacting type | `SecretString` with `expose_secret()`, `zeroize` on `Drop` | `Secret` with `expose()`, a frozen dataclass whose `__repr__`/`__str__` return a placeholder |
| Static checking | the compiler, plus `cargo clippy` | `basedpyright` in `strict` with `failOnWarnings = true` |

**Inside a section, dataclass construction is the unknown-field check.** A
section builder that calls `DatabaseSettings(**section)` inside a `try` and
re-raises the `TypeError` as a `ConfigurationError` naming the section turns an
`sslmode` key in `[database]` into (verified on CPython 3.14.6):

```text
configuration error at `database` (deployment policy):
DatabaseSettings.__init__() got an unexpected keyword argument 'sslmode'.
Did you mean 'tls_mode'?
```

The wrapper exists for one reason: the `TypeError` names the class, and an
operator needs the *setting path*. The "Did you mean" suffix is CPython's own.

**Two checks serde gives Rust for free must be written by hand in Python**, or
the loader does not fail closed. Verified on the same demo before the checks
existed: an unknown top-level table `[cache]` and an unknown top-level key
`extra_knob` were silently accepted, and `port = "8000"` was accepted with
`server.port == '8000'` — a dataclass performs no runtime type checking, and a
TOML `true` is an `int` to `isinstance`. Both checks are a few lines:

```python
KNOWN_SECTIONS = frozenset({"server", "database"})


def _reject_unknown_top_level_names(document: dict[str, Any]):
    unknown_names = sorted(set(document) - {"schema_version", *KNOWN_SECTIONS})
    if unknown_names:
        raise ConfigurationError(
            unknown_names[0], AuthorityClass.DEPLOYMENT_POLICY, "unknown table or key"
        )


def _reject_wrong_field_types(settings: object, section_name: str):
    if not dataclasses.is_dataclass(settings) or isinstance(settings, type):
        raise ConfigurationError(
            section_name, AuthorityClass.DEPLOYMENT_POLICY, "settings must be a dataclass instance"
        )
    for field in dataclasses.fields(settings):
        expected_type = field.type
        if not isinstance(expected_type, type):
            raise ConfigurationError(
                f"{section_name}.{field.name}",
                AuthorityClass.DEPLOYMENT_POLICY,
                "field annotation must be a plain type",
            )
        value: object = getattr(settings, field.name)
        # TOML booleans are not integers, even though Python's bool subclasses int.
        boolean_where_integer_expected = expected_type is int and isinstance(value, bool)
        if boolean_where_integer_expected or not isinstance(value, expected_type):
            raise ConfigurationError(
                f"{section_name}.{field.name}",
                AuthorityClass.DEPLOYMENT_POLICY,
                f"expected {expected_type.__name__}, got {type(value).__name__}",
            )
```

Verified with `pytest 9.1.1` and clean under basedpyright strict; the three
rejections read:

```text
configuration error at `cache` (deployment policy): unknown table or key
configuration error at `server.port` (deployment policy): expected int, got str
configuration error at `server.port` (deployment policy): expected int, got bool
```

Plain-type annotations (`int`, `str`) are a deliberate constraint of this
loader: a `from __future__ import annotations` import would turn `field.type`
into a string and trip the guard, which is the intended failure.

The redacting type is small:

```python
# src/backend_service/infrastructure/config/secret.py
REDACTED_PLACEHOLDER = "<redacted:secret>"


@dataclass(frozen=True, repr=False)
class Secret:
    """One credential, redacted in every rendering except `expose()`."""

    _material: str

    def expose(self) -> str:
        return self._material

    def __repr__(self) -> str:
        return REDACTED_PLACEHOLDER

    def __str__(self) -> str:
        return REDACTED_PLACEHOLDER
```

Verified with `pytest 9.1.1`: `repr()`, `str()`, and f-string interpolation all
render `<redacted:secret>`, and an enclosing frozen dataclass inherits it —
`SecretGeneration(generation_id='a3f1', database_username='backend_service',
database_password=<redacted:secret>)`. The whole `src` tree, `tomllib` parsing
included, is clean under `uv run basedpyright` with `typeCheckingMode =
"strict"`, `include = ["src"]`, `failOnWarnings = true` (`0 errors, 0 warnings,
0 notes`); the one narrowing that needed help was the section lookup, which ends
in an explicit `cast("dict[str, Any]", section)` at the parse seam.

**Use pydantic's `SecretStr` instead only when pydantic is already a
dependency.** It displays `'**********'` in `repr()` and `str()` and exposes the
value through `get_secret_value()`
([pydantic types](https://pydantic.dev/docs/validation/latest/api/pydantic/types/)).
Adding pydantic to a project for this one type is not worth it; the dataclass
above is fifteen lines.

## Worked Example (ironbox)

**Status: accepted target direction, not implemented.** The reference codebase
still loads most configuration from environment variables at startup. Two ADRs
record the destination; neither claims running code:

- **ADR-R41, configuration sources and authority** — the five authority classes,
  one versioned TOML document per process, the bootstrap enumeration, secrets as
  a parallel input, deployment-assembly validation of cross-process invariants,
  and the inventory-driven migration that removes dual authority rather than
  keeping permanent aliases.
- **ADR-R40, production secret delivery** — the Tier-3 shape: a store with a
  sidecar agent rendering one complete versioned bundle, the read → parse →
  validate → atomic-swap consumer contract, last-known-good on outage, startup
  fail-closed without freshness proof, and single-authority source selection.
  OpenBao is the selected product; the tier does not require it.

The part that was already right, and that both ADRs explicitly preserve, is the
concern split inside the configuration module:

```text
core/src/infrastructure/config/infra_config/
├── auth.rs   ├── connectivity.rs  ├── grpc.rs   ├── platform.rs
├── smtp.rs   ├── storage.rs       ├── task.rs   └── watchdog_budgets.rs
```

Each module parses and validates one concern; `InfraConfig` composes them; the
composition root constructs services from the composed type. Changing the
external source does not touch that shape. What the ADRs change is the
*authority* outside it: a flat environment namespace carrying secrets,
credential-bearing URLs, endpoints, watchdog budgets, retention policy, and
fixed safety mechanics all at once. The redacting secret type is older still —
ADR-R17 §2 specified a fixed-size, zeroize-on-drop,
`Debug`/`Display`/`Serialize`-redacting carrier with one named
`expose_secret()` accessor and a fenced constructor, which is what Stage 1
generalizes.

## Quick Reference — Invariants

- **One authority per setting.** No value exists in two classes; no class falls
  back to another.
- **Secrets are a parallel typed input**, never a section of the configuration
  document and never merged into it.
- **The environment is bootstrap only**, and the list is enumerated: document
  path, secret-source selector, secret bundle path, platform instance identity
  — plus the secret fixtures, only under the explicit `environment` selector.
- **The document is versioned; unknown versions and unknown fields fail
  closed.** Decode the version before the body.
- **The selector is explicit and required** once any secret exists. No inference
  from file existence. No fallback between modes.
- **One consumer contract at every tier:** read one complete file, validate it
  whole, swap atomically, keep the last validated generation on failure.
- **A credential never appears in a URL that is written down.** Endpoint in the
  document, credential in the secret input, URL assembled in memory in a
  redacting type.
- **Errors name the setting path and its class, never a value.**
- **Tests use an injectable lookup seam** and never mutate the process
  environment.
- **Libraries never read configuration.** The consuming process does.
- **Safety constants stay code-owned.** A deployment knob never shadows a proof.
- **The tier is recorded in an ADR, with the triggers that would move it up.**

## Anti-Patterns to Avoid

- **Telling every project to run a secret store.** The named failure mode this
  pattern exists to prevent. A library wrapper records Tier 0 and moves on.
- **Inferring the secret source from file existence.** "If the bundle is there,
  use it; otherwise read the environment" silently degrades production to
  development mode the first time a mount fails.
- **A credential-bearing URL in a file, a template, or a log.** It gives the
  password the review, backup, and rotation lifecycle of a port number.
- **A watched file as the runtime-policy mechanism.** No transaction, no
  authorization, no audit, no propagation semantics, no authority in a
  multi-instance deployment.
- **One platform secret per field.** It hands the process a pile of
  unversioned fragments and no `schema_version`, so the consumer contract
  cannot run; declare one credential whose content is the whole bundle.
- **Permanent compatibility aliases.** "Old name or new name" is two authorities
  wearing one setting. Aliases live inside a bounded migration step and are
  deleted at cutover.
- **Partial activation of a secret bundle.** Combining fields from two
  generations produces a state no generation ever validated.

## Relationship to Other Patterns and Skills

- **[composition pattern](../project_structure/composition_pattern.md)** —
  loading configuration is step 1 of the entry-point sequence; the typed models
  this pattern produces are what the composition root wires.
- **[bootstrap pattern](../lifecycle/bootstrap_pattern.md)** — the fail-fast
  loader *is* the first preflight check.
- **[repo root files](../documentation/repo_root_files_pattern.md)** — its
  env-file convention narrows to bootstrap values plus development secret
  fixtures; deployment policy lives in a committed per-component TOML.
- **`python-project-setup` (skill)** — its CPython 3.14 floor is what makes
  `tomllib` available, so Stage 1 costs no dependency on Python.
- **[conventions/python](../conventions/python.md) and
  [conventions/rust](../conventions/rust.md)** — where the three gates live.
- **[worker fleet pattern](../scalability/worker_fleet_pattern.md)** — the
  shared enrollment secret is Tier-1 material on a single host, Tier-2 once a
  control plane owns it for both process classes, Tier-3 once it must be
  short-lived or audited: the move-up triggers above, in order.
- **[observability posture](observability_posture_pattern.md)** — startup logs
  report effective non-secret settings and their source; secrets only as
  present and valid, by non-secret generation metadata.
- **`rust-design-idioms` (skill)** — the redacting secret type is a newtype
  whose material is unreachable except through one named accessor.
- **`greenfield-project-setup` (skill)** — phase 4 loads configuration before
  composition; phase 8 records the authority classes, the chosen tier, and its
  move-up triggers as a day-1 ADR.
