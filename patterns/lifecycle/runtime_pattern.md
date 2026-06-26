---
name: runtime-workers-pattern
description: >-
  Use when a backend runs long-lived background workers — schedulers, periodic
  sweepers, queue/event listeners — and needs them spawned, supervised, and
  stopped cleanly: translating OS signals into cancellation, racing every worker
  loop against a shutdown signal so it exits promptly, and draining in-flight
  work under a timeout before the process exits. Language-agnostic; Rust example
  included.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.1"
---

# Runtime Worker Supervision (Runner) Pattern

## Purpose

**Runtime** is the phase where a service's long-lived background workers run and
then stop cleanly: periodic schedulers, sweepers/garbage collectors, and
queue/event listeners. This pattern gives them a uniform spawn-and-supervise
shape so the process starts every worker the same way and shuts every worker
down gracefully.

**In one line:** runtime answers *how do background workers run and stop
cleanly?* — one supervisor spawns them under a single shutdown signal and drains
them, bounded, on the way out.

Conceptually this is **structured concurrency**: one owner spawns, holds, and
awaits its children, so no background task outlives the process unsupervised.
The shutdown signal is the same idea as Go's `context.Context` cancellation —
nothing downstream ever sees the OS; it only ever sees the cancel signal.

It is the third phase in the process lifecycle, after the
[composition root](../project_structure/composition_pattern.md) constructs the
graph and [bootstrap](bootstrap_pattern.md) prepares the world:
**compose → bootstrap → run + drain → exit.**

> **Core principle (separation of concerns / single responsibility):** three
> roles, three owners. The **worker** owns *what to do* (domain/application
> logic). The **runner** owns *when and how often* to do it and how to spawn it
> (infrastructure). The **supervisor** owns the shutdown signal and the
> collected task handles (lifecycle). A worker never knows about timers,
> threads, or OS signals; that is the runner's job.

## When to Apply

Apply when the service has **work not driven by an inbound request**:

- **Periodic work** — a scheduler that fires due jobs, a sweeper that reclaims
  stale locks/leases or prunes old rows on an interval.
- **Continuous work** — a listener consuming a broker queue or a database
  `LISTEN`/pub-sub channel, running for the life of the process.
- **Any spawned task that must survive until — and stop at — shutdown.**

And when graceful shutdown matters: the process should finish (or cleanly
abandon) in-flight work on SIGTERM rather than being killed mid-operation
(important under Kubernetes / systemd, which signal then wait then `KILL`).

**When NOT to use:** a pure request/response service with no background work, or
a short-lived batch job that runs once and exits. Don't spawn a supervisor with
nothing to supervise.

## The Three Roles

### 1. Worker — *what to do* (domain / application)

A plain object with a unit of work — typically a `tick()` for periodic workers,
or a handler for event-driven ones. It is **runtime-agnostic**: no timers, no
spawn, no signals, no transport types. This keeps the worker unit-testable
without a runtime and lets the application layer stay free of infrastructure (a
runner is an infrastructure adapter *driving* an application service — the same
inversion as the rest of a hexagonal app).

### 2. Runner — *when/how* (infrastructure)

A thin infrastructure adapter that turns a worker into a managed background
task. Each runner follows the **same shape**:

- `new(worker)` — wrap the worker (and hold its tick interval as a constant).
- `run(&mut supervisor)` — clone the shutdown signal, spawn the loop, and
  register the handle with the supervisor. No return value; the call site is a
  single statement.

The loop body is the canonical **"race cancel against work"**:

- check the shutdown signal *and* the next work trigger in one `select`,
- with cancellation **checked first** (biased) so shutdown always wins promptly,
- and **never** sleep/await a trigger without also racing the signal — a bare
  `sleep(interval)` would block the drain for a full interval.

### 3. Supervisor — *lifecycle* (the handle/signal owner)

One object owns the shared shutdown signal and the `Vec` of task handles. It is
passed `&mut` to every `runner.run(...)`, so:

- handing out the signal (`shutdown()`) and registering handles (`push()`) is
  uniform across all runners, and
- after the foreground server exits, the supervisor **drains** — awaits all
  handles under a timeout, logging and moving on if the window elapses (never
  hang forever waiting on a stuck worker).

A small fourth piece, the **signal→cancel adapter**, sits at the edge: it waits
for the first SIGTERM/SIGINT and cancels the signal. That is the *only* place
that touches the OS.

## Worked Example (Rust, tokio)

**Supervisor** — owns the cancellation token and the handles; bounded drain:

```rust
const RUNTIME_DRAIN_TIMEOUT: Duration = Duration::from_secs(30);

pub struct RuntimeHandlesManager {
    shutdown: CancellationToken,
    handles: Vec<JoinHandle<()>>,
}

impl RuntimeHandlesManager {
    pub const fn new(shutdown: CancellationToken) -> Self {
        Self { shutdown, handles: Vec::new() }
    }

    /// A cheap clone of the shared signal for the next runner.
    pub fn shutdown(&self) -> CancellationToken { self.shutdown.clone() }

    /// Register one background-task handle.
    pub fn push(&mut self, handle: JoinHandle<()>) { self.handles.push(handle); }

    /// Await every handle under the timeout; log and exit if it elapses.
    pub async fn drain(self) {
        let drain = futures_util::future::join_all(self.handles);
        if tokio::time::timeout(RUNTIME_DRAIN_TIMEOUT, drain).await.is_ok() {
            tracing::info!("all runtime workers drained cleanly");
        } else {
            tracing::warn!("runtime drain timeout elapsed; some workers may not have finished");
        }
    }
}
```

**Signal → cancel adapter** — the only code that sees the OS:

```rust
pub struct ShutdownSignalRunner { shutdown: CancellationToken }

impl ShutdownSignalRunner {
    pub fn run(self) -> JoinHandle<()> {
        tokio::spawn(async move {
            let mut sigterm = signal(SignalKind::terminate()).expect("install SIGTERM listener");
            tokio::select! {
                _ = tokio::signal::ctrl_c() => tracing::info!("SIGINT received; shutting down"),
                _ = sigterm.recv()          => tracing::info!("SIGTERM received; shutting down"),
            }
            self.shutdown.cancel();   // <-- OS signal becomes one neutral cancel
        })
    }
}
```

**Interval runner** — the canonical shape every periodic runner repeats:

```rust
const SWEEPER_INTERVAL: Duration = Duration::from_secs(3600);

pub struct JobSweeperRunner { sweeper: JobSweeper }

impl JobSweeperRunner {
    pub const fn new(sweeper: JobSweeper) -> Self { Self { sweeper } }

    pub fn run(self, supervisor: &mut RuntimeHandlesManager) {
        let shutdown = supervisor.shutdown();            // 1. take the signal
        supervisor.push(tokio::spawn(async move {        // 3. register the handle
            loop {
                tokio::select! {
                    biased;                               // cancel checked first...
                    () = shutdown.cancelled() => break,   // ...so shutdown wins promptly
                    () = tokio::time::sleep(SWEEPER_INTERVAL) => {}
                }
                self.sweeper.tick().await;                // 2. the worker does the work
            }
        }));
    }
}
```

**Event-driven runner** — same skeleton, but the trigger is an event source, and
two extra rules apply: check the signal *inside* any backoff sleep (so shutdown
isn't blocked for a full backoff window), and decode leniently (a bad message is
logged and skipped, never tears down the loop):

```rust
pub fn run(mut self, supervisor: &mut RuntimeHandlesManager) {
    let shutdown = supervisor.shutdown();
    supervisor.push(tokio::spawn(async move {
        let mut attempt: u32 = 0;
        loop {
            tokio::select! {
                biased;
                () = shutdown.cancelled() => break,
                result = self.listener.try_recv() => match result {
                    Ok(Some(message)) => { attempt = 0; self.handle(message); }   // lenient inside
                    Ok(None)          => { attempt = 0; self.on_reconnect(); }     // resync after a gap
                    Err(error) => {
                        attempt = attempt.saturating_add(1);
                        let delay = Self::backoff(attempt);   // bounded exponential, pure & testable
                        tokio::select! {                      // <-- still cancellable during backoff
                            biased;
                            () = shutdown.cancelled() => break,
                            () = tokio::time::sleep(delay) => {}
                        }
                    }
                }
            }
        }
    }));
}
```

**The entry point** creates the signal, installs the adapter, builds the
supervisor, runs each worker, then drains after the foreground server exits:

```rust
let shutdown = CancellationToken::new();
ShutdownSignalRunner::new(shutdown.clone()).run();             // OS signal -> token
let mut supervisor = RuntimeHandlesManager::new(shutdown.clone());

SchedulerRunner::new(services.scheduler.clone()).run(&mut supervisor);
JobSweeperRunner::new(services.job_sweeper.clone()).run(&mut supervisor);
ConnectivityListenerRunner::new(listener, hub).run(&mut supervisor);
// ...every other runner, each one statement...

server.run(shutdown).await;   // foreground HTTP/gRPC blocks until the token cancels
supervisor.drain().await;     // then wait for the workers, bounded
```

## Mapping to Other Backend Languages

The roles are language-agnostic; only the concurrency primitives change.

| Role / mechanism | Rust (tokio) | Go | Python (asyncio) |
|---|---|---|---|
| Shutdown signal | `CancellationToken` | `context.Context` (`WithCancel`) | `asyncio.Event` / task cancellation |
| Signal → cancel | `ShutdownSignalRunner` → `cancel()` | `signal.NotifyContext(ctx, SIGINT, SIGTERM)` | `loop.add_signal_handler(SIGTERM, …)` |
| Spawn a worker | `tokio::spawn` | `go func()` | `asyncio.create_task` |
| Supervisor / handle set | `RuntimeHandlesManager` (`Vec<JoinHandle>`) | `errgroup.Group` / `sync.WaitGroup` | `asyncio.TaskGroup` / `anyio` task group |
| Race cancel vs. work | `select! { cancelled, sleep }` | `select { <-ctx.Done(); <-ticker.C }` | `await asyncio.wait({tick, stop}, FIRST_COMPLETED)` |
| Bounded drain | `timeout(DRAIN, join_all(handles))` | `WaitGroup.Wait()` raced with a timer | `asyncio.wait_for(gather(*tasks), timeout)` |

In Python a FastAPI `lifespan` is the natural supervisor home: on startup create
the worker tasks (after composition + bootstrap), `yield` to serve, then on
shutdown set the stop event and `await asyncio.wait_for(gather(*tasks), drain)`.
A Go service passes one `signal.NotifyContext` to every goroutine and uses an
`errgroup` to wait them out. The skeleton is identical: one signal in, every
loop races it, one owner waits them all out under a cap.

## Quick Reference — Invariants

- **One shutdown signal, owned by the supervisor**, cloned to every worker. The
  app never reads the OS — only the signal.
- **Exactly one place translates OS signals into the cancel signal.**
- **Every worker loop races the signal against its work**, with cancel checked
  first — and never sleeps/awaits a trigger without also racing the signal.
- **Check the signal inside long sleeps/backoffs too**, not just at loop top.
- **The supervisor collects every spawned handle** — no orphan `spawn`/`go`
  with no owner.
- **Drain is bounded**: await all workers under a timeout, then log and exit;
  never hang on a stuck worker.
- **Worker (what) is separate from runner (when/how).** The worker is
  runtime-agnostic and unit-testable without a runtime.
- **Event loops are resilient**: lenient decode (skip bad input), reconnect with
  bounded backoff, resync after a gap.

## Anti-Patterns to Avoid

- **Fire-and-forget spawning.** `tokio::spawn` / `go func()` with no handle and
  no owner — shutdown can't wait for it, so it's killed mid-work.
- **Bare `sleep(interval)` not raced against the signal.** The worker ignores
  shutdown until its (possibly hour-long) timer fires, blocking the drain.
- **OS signals reaching into business logic.** Handle the signal once at the
  edge and turn it into the neutral cancel signal; don't scatter signal handling.
- **Workers that know about the runtime.** A scheduler that imports the timer
  library or spawns its own task can't be tested without one and leaks
  infrastructure into the application layer.
- **Unbounded drain.** `await`ing all workers with no timeout lets one stuck
  worker hang the whole shutdown.
- **A fragile event loop.** One malformed message or one dropped connection
  tears down the listener for the rest of the process. Decode leniently;
  reconnect with bounded backoff.

## Relationship to Other Skills

- **[composition root pattern](../project_structure/composition_pattern.md)** —
  builds the workers (schedulers/sweepers) this phase runs; its runtime
  projection is where `runner.run(&mut supervisor)` calls live.
- **[bootstrap pattern](bootstrap_pattern.md)** — the prior lifecycle phase; a
  worker may be handed an eagerly-prepared resource (e.g. a live listener
  connection) that bootstrap established fail-fast.
- **`rust-hexagonal-architecture` / `python-ddd`** — a runner is an
  infrastructure adapter that *drives* an application service on a schedule,
  the dual of an inbound adapter that drives one on request.
- **`general-logging`** — log shutdown received, each worker's exit, and the
  drain outcome (clean vs. timed out) so graceful shutdown is observable.
