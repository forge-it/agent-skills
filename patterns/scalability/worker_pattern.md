---
name: scalable-worker-pattern
description: >-
  Use when building a SaaS backend that has long-running, computationally heavy,
  or externally blocking work — connectivity probes, notification delivery,
  backup orchestration, data processing — that must not block the HTTP request
  thread. Use when the system must scale the execution layer horizontally
  independent of the API layer. Use when two or more of these symptoms appear:
  API latency spikes during background work; the API and the background tasks
  cannot be scaled independently; a message broker is already in the stack but
  tasks are dispatched inline; the domain types for task dispatch are duplicated
  between the API binary and a would-be worker binary; or there is no typed
  boundary between what is published and what is consumed.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.3"
---

# Scalable Worker Pattern

## Purpose

**In one line:** split the synchronous API from an asynchronous, broker-backed
worker so the system scales horizontally without a later refactor.

Every SaaS product eventually needs background work — connectivity probes,
notification delivery, data processing, orchestration. The naive shortcut is to
run that work inline on the request thread or in a fire-and-forget `tokio::spawn`
inside the API binary. Both work until they don't. When the load grows or the
work grows heavier, the refactor is multi-week: extract a worker binary, design a
broker topology, define a typed message contract, introduce a shared crate,
migrate state, reconcile deployments. **This is not premature optimization — it
is the cost of not designing for scale at the start.** The right time to separate
the API from the worker is before the first background task is written, not after
the tenth is causing latency incidents.

**The core principle (separation of concerns / single responsibility):** the API
owns synchronous request handling — validate, persist, enqueue, respond. The
worker owns asynchronous task execution — consume, lease, execute, report,
settle. The broker decouples them. Neither binary knows how the other is deployed
or scaled.

> **This is worth repeating because it is the one invariant everything else
> follows from:** API = synchronous request handling; worker = asynchronous heavy
> or long work; broker = the decoupling seam. Keep those three responsibilities
> in three different processes.

## Architecture Diagram

```
  ┌──────────────────────────────────────────────────────────────────────┐
  │  API (ironbox-core)                                                   │
  │                                                                        │
  │  ┌──────────────────┐    ┌─────────────────────────────────────────┐  │
  │  │  HTTP handler    │    │  application/task/service.rs             │  │
  │  │  (request path)  │───▶│  enqueue():                             │  │
  │  │                  │    │    1. persist task row (Queued)          │  │
  │  └──────────────────┘    │    2. publish via TaskPublisher port     │  │
  │                          └───────────────────┬─────────────────────┘  │
  │                                              │  domain values only    │
  │                          ┌───────────────────▼─────────────────────┐  │
  │                          │  infrastructure/messaging/rabbitmq/      │  │
  │                          │  LapinTaskPublisher                      │  │
  │                          │    builds TaskEnvelope (contracts DTO)   │  │
  │                          │    publishes to ironbox.tasks exchange   │  │
  │                          │    awaits publisher confirm              │  │
  │                          └───────────────────┬─────────────────────┘  │
  └──────────────────────────────────────────────│────────────────────────┘
                                                 │
                           ┌─────────────────────▼──────────────────────┐
                           │  RabbitMQ broker                            │
                           │                                              │
                           │  exchange: ironbox.tasks  (durable, direct) │
                           │    routing key: "connectivity_check"  ──────┼──┐
                           │    routing key: "connectivity_notification" ┼──┤
                           │    routing key: "noop"                 ──────┼──┤
                           │                                              │  │
                           │  queue: ironbox_tasks.connectivity_check ◀──┘  │
                           │  queue: ironbox_tasks.connectivity_notification◀┘
                           │  queue: ironbox_tasks.noop ◀──────────────────┘
                           └───────────────────┬──────────────────────────┘
                                               │
  ┌────────────────────────────────────────────▼────────────────────────────┐
  │  Worker (ironbox-worker)                                                  │
  │                                                                            │
  │  main.rs ──────────────────────────────────────────────────────────────── │
  │   1. load WorkerConfig                                                     │
  │   2. connect gRPC channel to core (WorkerControl service)                 │
  │   3. register_task_handlers(&mut registry, ...)                           │
  │   4. connect RabbitMqConsumer (declares queues from registry)              │
  │   5. run TaskRuntime (consume → lease → execute → report → settle)        │
  │                                                                            │
  │  ┌────────────────────────────────────────────────────────────────────┐   │
  │  │  application/task/runtime.rs  TaskRuntime                          │   │
  │  │   semaphore-bounded concurrency; JoinSet of Attempt tasks          │   │
  │  │   on shutdown: drain in-flight, then nack survivors                │   │
  │  └──────────────────┬─────────────────────────────────────────────────┘   │
  │                     │  per delivery                                         │
  │  ┌──────────────────▼─────────────────────────────────────────────────┐   │
  │  │  application/task/attempt.rs  Attempt                              │   │
  │  │   1. acquire_lease (fencing token from core)                       │   │
  │  │   2. report_started                                                │   │
  │  │   3. handler.execute(ctx)  ──────────────────────────────────────┐ │   │
  │  │   4. race handler vs. heartbeat supervisor vs. shutdown abort     │ │   │
  │  │   5. report_completed / report_failed                             │ │   │
  │  │   6. ack / nack the broker delivery (exactly once)                │ │   │
  │  └───────────────────────────────────────────────────────────────────┘ │   │
  │                                                                         │   │
  │  ┌──────────────────────────────────────────────────────────────────┐  │   │
  │  │  application/connectivity/handler.rs  ConnectivityCheckHandler   │◀─┘   │
  │  │  application/notification/handler.rs  ConnectivityNotificationH  │      │
  │  │   Each holds its own concept control-plane port (gRPC adapter).   │      │
  │  └──────────────────────────────────────────────────────────────────┘      │
  └─────────────────────────────────────────────────────────────────────────────┘
                         │ gRPC WorkerControl back-channel
                         ▼
  ┌──────────────────────────────────────────────────────┐
  │  core: application/task/service.rs  TaskService      │
  │   acquire_lease / report_started / heartbeat /       │
  │   report_completed / report_failed                   │
  └──────────────────────────────────────────────────────┘
```

The shared `ironbox-task-contracts` workspace crate is the **only code the API
and worker binaries share for the dispatch boundary**. Domain crates (`ironbox-
connectors-runtime`) may also be shared where appropriate. Neither binary imports
the other's application or infrastructure layer.

When the worker must execute heavy mechanics the API also owns (in ironbox:
backup/restore connector execution), those mechanics live in **consumer-free
library crates** shared by both binaries — the library never depends on the API
crate, the contracts crate, or any consumer. Each binary assembles the
library's adapters in its own composition seam. The direction (`api → library`,
`worker → library`, never `library → consumer`) is enforced by the manifest
dependency gate in `rust-architecture-test-setup`, so it cannot silently
invert.

## The Shared Contract Crate — the Queue Boundary

The contract crate (`crates/ironbox-task-contracts/`) is a **pure wire-types
crate**: no business logic, no database drivers, no runtime wiring. It defines:

- `TaskEnvelope` — the JSON-serialized broker message body. Both the publisher
  (core's `LapinTaskPublisher`) and the consumer (the worker's `RabbitMqConsumer`)
  decode the same struct. A `schema_version` field is stamped by the publisher
  and checked by the worker before the handler is invoked — a mismatched version
  fails the task terminally instead of silently discarding or misinterpreting it.

- Exchange and queue topology constants — `TASK_EXCHANGE` (the durable direct
  exchange), `TASK_QUEUE_PREFIX`, and `task_queue_name(task_type)` (the locked
  per-task-type naming convention `ironbox_tasks.<task_type>`). Both binaries
  reference the same names; a rename is a compile error, not a silent mismatch.

- `ActiveLease` — the fencing identity (`task_id` + `lease_token`) the worker
  carries between the lease-acquire and the terminal lifecycle report.

- The generated gRPC stubs for the `WorkerControl` service (the back-channel
  from worker to core). Core acts as the gRPC server; the worker is the client.

**Why a separate crate matters.** The publisher and consumer must agree on the
exact message shape. Inlining the `TaskEnvelope` definition in either binary
means the other must duplicate it, and a field rename in one binary will silently
break the system at runtime. Extracting the shared types into a crate that both
binaries declare as a dependency makes the agreement a compiler guarantee.

## Topology: One Exchange, Per-Task-Type Queues

The publisher targets the exchange and a routing key (the task type string) —
it never names a queue. Each worker declares and binds only the durable queues
for the task types it handles (`consumer_queues` in
`infrastructure/bootstrap/task.rs` derives the topology from the handler
registry). A worker that does not yet handle a task type will never consume (and
terminally fail) a message of that type. A task type published to an exchange
with no bound queue triggers a `basic.return` (the publisher uses `mandatory:
true`), surfacing as `TaskPublishError::Unroutable` — a dispatch is never
silently dropped.

## The Worker Is Its Own Hexagonal Application

The worker is not a library, a plugin, or a stripped-down version of the API. It
is a fully independent deployable with:

- its own `Cargo.toml` and binary entry point (`main.rs`),
- its own hexagonal layers (`application/` and `infrastructure/`),
- its own composition root (the handler registration in
  `infrastructure/bootstrap/task.rs` and the wiring in `main.rs`),
- its own bootstrap (config loading, adapter construction, eager connections), and
- its own runtime loop (`TaskRuntime`) consuming the queue.

This is the [composition root pattern](../project_structure/composition_pattern.md),
the [bootstrap pattern](../lifecycle/bootstrap_pattern.md), and the
[runtime worker supervision pattern](../lifecycle/runtime_pattern.md) applied to
a second binary. The `TaskRuntime`'s consume loop is the runtime-worker: it
drives the application layer (the handlers) from an inbound infrastructure adapter
(the AMQP consumer), exactly as an HTTP server drives the application layer from
an HTTP adapter — the direction of invocation is the same; the transport differs.

### Composition root

`main.rs` is the worker's composition root. It:

1. loads `WorkerConfig` (env-based, fail-fast),
2. constructs the outbound adapters (SMTP notifier, gRPC channel),
3. builds the generic lifecycle control-plane adapter (`GrpcLifecycleControlPlane`),
4. calls `register_task_handlers`, which wires each task-type handler to its own
   concept-specific gRPC adapter over the shared channel,
5. connects the `RabbitMqConsumer` using the queue topology derived from the
   registry,
6. installs the shutdown signal runner, and
7. runs `TaskRuntime`.

Adding a new task type is a single `registry.register(...)` line in
`register_task_handlers` — the generic runtime, the consumer, and `main.rs` are
never touched. This is the open-closed property of the composition root.

### Application layer inside the worker

The worker's `application/` layer mirrors the structure of the API's
`application/` layer:

- `application/task/` holds the **generic execution machinery** — `TaskRuntime`,
  `Attempt`, `TaskRegistry`, the `TaskConsumer` / `DeliveryHandle` /
  `ControlPlane` / `TaskHandler` ports, and the noop reference handler. It names
  no task-type concepts. Adding a task type never widens this machinery.

- Each task type is its **own concept** under `application/` — for example,
  `application/connectivity/` holds `ConnectivityCheckHandler` (which implements
  `TaskHandler`), `ConnectivityControlPlane` (the handler's concept port), and the
  decoded payload model. The handler holds an `Arc<dyn ConnectivityControlPlane>`,
  injected at construction; it never reaches into the generic `ControlPlane`.

This is single responsibility applied inward: the runtime machinery drives any
handler; each handler is responsible for one task type; the two layers are
kept separate.

## Idempotency, Retries, and At-Least-Once Delivery

AMQP delivers at-least-once. A task delivery may be requeued and redelivered
if the worker crashes, loses the connection, or hits a transient control-plane
failure. The system handles this at two levels:

**Lease fencing (core-side idempotency).** Before executing a task, the worker
calls `acquire_lease`. Core issues a fencing token (`lease_token`) and
transitions the task row from `Queued` to `Leased`. Every subsequent lifecycle
call (`report_started`, `heartbeat`, `report_completed`, `report_failed`) must
present the same `task_id` + `lease_token` pair. A redelivery of a task that is
already `Leased` (held by another worker or the same worker after a crash)
resolves to `LeaseRejection::LeaseHeld` — the delivery is nacked with requeue
after a `LEASE_HELD_REQUEUE_DELAY` to avoid a hot retry loop. A redelivery of
a task that is already terminal (`Completed` or `Failed`) resolves to
`LeaseRejection::AlreadyTerminal` — the delivery is acked and dropped (the work
is already done; no re-execution).

**Classified delivery actions (worker-side retry policy).** The `Attempt` maps
every control-plane error to exactly one of three delivery actions:

- `AckDrop` — the task is in a state where retrying would be wrong (e.g. the
  task row no longer exists); ack the delivery and move on.
- `NackDrop` — a worker-side bug; nack without requeue so a dead-letter queue
  can catch it.
- `NackRequeue` — a transient infrastructure failure; nack with requeue so the
  broker will redeliver.

**Envelope schema version gate.** The `schema_version` field in `TaskEnvelope`
is checked before the handler is invoked. A version mismatch calls
`report_failed` (terminal) and acks the delivery — the task row reaches `Failed`
with an explanation, not a silently unprocessed state.

**Bounded drain on shutdown.** When the shutdown token cancels, `TaskRuntime`
stops consuming new deliveries and waits for in-flight attempts to finish within
a configured `shutdown_timeout`. If the timeout elapses, an `abort` token is
cancelled, and each still-running attempt nacks its delivery with requeue — the
broker will redeliver them to another worker instance.

## Worked Example (Rust, ironbox)

This example traces the full round trip for a `connectivity_check` task.

### Step 1 — core enqueues

A scheduler in `core` fires, decides a connectivity check is due, and calls
`TaskService::enqueue`. The application service persists the task row and calls
the `TaskPublisher` port:

```rust
// core: application/task/service.rs  (simplified)
async fn enqueue(&self, request: &CreateTaskRequest) -> Result<Task, EnqueueTaskError> {
    let task = self.task_repository.create(request).await?;
    // The port speaks domain types only; the wire DTO is built inside the adapter.
    if let Err(publish_error) = self.task_publisher.publish_task(
        task.id(),
        task.task_type(),
        task.payload(),
    ).await {
        // Fail-fast: delete the row, surface the error — no silent drop.
        let _ = self.task_repository.delete(task.id()).await;
        return Err(EnqueueTaskError::Publish(publish_error));
    }
    Ok(task)
}
```

The `TaskPublisher` port in `core` speaks domain values (`TaskId`, `TaskType`,
`TaskPayload`). The concrete adapter (`LapinTaskPublisher`) builds the
`TaskEnvelope` wire DTO from the contracts crate:

```rust
// core: infrastructure/messaging/rabbitmq/publisher.rs  (simplified)
fn publish_task(&self, task_id: &TaskId, task_type: &TaskType, payload: &TaskPayload)
    -> Pin<Box<dyn Future<Output = Result<(), TaskPublishError>> + Send + '_>>
{
    Box::pin(async move {
        let envelope = TaskEnvelope {
            schema_version: TASK_ENVELOPE_SCHEMA_VERSION,
            task_id: task_id.to_string(),
            task_type: task_type.as_str().to_owned(),
            payload_json: payload.as_str().to_owned(),
        };
        let body = serde_json::to_vec(&envelope)?;
        // mandatory=true: an unroutable message returns BasicReturn, not a silent ack.
        let confirmation = self.channel.basic_publish(
            TASK_EXCHANGE.as_str(),
            task_type.as_str(),
            BasicPublishOptions { mandatory: true, .. },
            &body,
            BasicProperties::default().with_delivery_mode(PERSISTENT_DELIVERY_MODE),
        ).await?.await?;
        match confirmation {
            Confirmation::Ack(None) => Ok(()),
            Confirmation::Ack(Some(_)) => Err(TaskPublishError::Unroutable(task_type.as_str().to_owned())),
            _ => Err(TaskPublishError::Rejected),
        }
    })
}
```

### Step 2 — worker consumes

The `TaskRuntime` in the worker calls `consumer.next()` in a loop bounded by a
semaphore (concurrency cap). Each delivery is spawned as an `Attempt`:

```rust
// worker: application/task/runtime.rs  (simplified)
pub async fn run(mut self, shutdown: CancellationToken) -> Result<(), RuntimeError> {
    let semaphore = Arc::new(Semaphore::new(self.config.concurrency));
    let mut in_flight: JoinSet<()> = JoinSet::new();
    loop {
        let permit = Self::acquire_slot(&semaphore, &mut in_flight, &shutdown).await
            .ok_or_else(|| break)?;
        tokio::select! {
            biased;
            () = shutdown.cancelled() => break,
            next = self.consumer.next() => {
                let Some((envelope, delivery)) = next else { break; };
                self.spawn_attempt(&mut in_flight, envelope, delivery, permit, &abort);
            }
        }
    }
    Self::drain(in_flight, self.config.shutdown_timeout, &abort).await;
    Ok(())
}
```

### Step 3 — attempt execution

`Attempt::execute` runs the five stages: claim → gate → start → supervise →
settle. The handler's `execute` races the heartbeat supervisor and the shutdown
abort token (so the attempt stops promptly on shutdown without blocking the
drain):

```rust
// worker: application/task/attempt.rs  (simplified)
async fn run_supervised(&self, lease: &ActiveLease, handler: Arc<dyn TaskHandler>) -> Settlement {
    let ctx = HandlerContext { payload_json: &self.envelope.payload_json, lease, .. };
    tokio::select! {
        biased;
        result = handler.execute(ctx) => match result {
            Ok(()) => {
                // Handler called its own concept record_* RPC before returning.
                match self.control_plane.report_completed(lease).await {
                    Ok(()) => Settlement::Ack,
                    Err(error) => Self::settlement_for(&error),
                }
            }
            Err(TaskFailure::Terminal(error)) => self.fail_terminally(lease, &error.to_string()).await,
            Err(TaskFailure::Retryable(error)) => Self::settlement_for(&error),
        },
        end = self.supervise(lease) => { /* heartbeat cancelled or failed */ },
        () = self.abort.cancelled() => Settlement::Nack { requeue: true },
    }
}
```

### Step 4 — handler calls its own concept control plane

The `ConnectivityCheckHandler` holds its own `Arc<dyn ConnectivityControlPlane>`,
injected at construction. It calls `fetch_resolved_probe_payload` and
`record_probe_outcome` over that port — never over the generic `ControlPlane`.
The generic runtime machinery is not widened to accommodate concept-specific RPCs:

```rust
// worker: application/connectivity/handler.rs  (simplified)
pub struct ConnectivityCheckHandler {
    control_plane: Arc<dyn ConnectivityControlPlane>,
}

impl TaskHandler for ConnectivityCheckHandler {
    fn task_type(&self) -> &'static str { "connectivity_check" }

    fn execute<'a>(&'a self, ctx: HandlerContext<'a>)
        -> Pin<Box<dyn Future<Output = Result<(), TaskFailure>> + Send + 'a>>
    {
        Box::pin(async move {
            let probe = self.control_plane
                .fetch_resolved_probe_payload(ctx.lease)
                .await?;
            let outcome = run_probe(&probe).await;
            self.control_plane
                .record_probe_outcome(ctx.lease, &outcome)
                .await?;
            Ok(())
        })
    }
}
```

### Step 5 — worker composition root wires it all together

`main.rs` is the one place that names both the ports and the concrete adapters:

```rust
// worker: main.rs  (simplified)
let grpc_channel = grpc::connect(&worker_config.core_grpc_url).await.or_exit("...");
let lifecycle_control_plane =
    GrpcLifecycleControlPlane::new(grpc_channel.clone(), &worker_config.worker_id);
let mut registry = TaskRegistry::new();
register_task_handlers(&mut registry, &grpc_channel, &worker_config.worker_id, notifier);
let consumer = RabbitMqConsumer::connect(
    &worker_config.rabbitmq_url,
    &consumer_queues(&registry),
    worker_config.concurrency,
).await.or_exit("...");
let shutdown = CancellationToken::new();
ShutdownSignalRunner::new(shutdown.clone()).run();
let runtime = TaskRuntime::new(config, consumer, lifecycle_control_plane, registry);
runtime.run(shutdown).await?;
```

## Mapping to Python

The example above is one *implementation* of the invariants below, not the invariants
themselves. Python keeps every one, but the mechanism changes — and the runtime choice
below fixes which arrive free, which are configured, and which you still build.

### Structural mapping

| Concern | Rust (ironbox) | Python |
|---------|----------------|--------|
| Shared dispatch contract | the `ironbox-task-contracts` crate | a `packages/<project>-task-contracts/` **uv workspace member**, declared by both services via `{ workspace = true }` (see [Python conventions](../conventions/python.md), *uv Workspaces — the packaging substrate*) |
| Typed wire envelope | `TaskEnvelope` + serde | a frozen `pydantic.BaseModel` (boundary validation comes free) or a frozen dataclass with an explicit codec — either way it carries `schema_version` |
| Topology constants | `TASK_EXCHANGE`, `task_queue_name()` | module-level `Final[str]` constants and `def task_queue_name(task_type: str) -> str`, in that same contract package |
| Handler port | `Arc<dyn TaskHandler>` | a `TaskHandler` `typing.Protocol` (`task_type` property + `async def execute(...)`); the registry stores instances keyed by task type |
| Concept control-plane port | `Arc<dyn ConnectivityControlPlane>` | one `Protocol` per concept, injected into that handler's constructor — never the generic runtime port |
| Bounded concurrency | `Semaphore` permit per delivery | `await channel.set_qos(prefetch_count=<cap>)` and nothing else: every in-flight attempt holds exactly one unacked delivery, so the prefetch window **is** the concurrency cap. An `asyncio.Semaphore` with the same cap could never suspend (the broker would have to breach the window first), and awaiting one between pulling a delivery and spawning its attempt is exactly where a shutdown cancellation would orphan an unsettled delivery |
| In-flight set | `JoinSet<()>` | a plain `set[asyncio.Task[None]]` filled by `asyncio.create_task`, drained with `asyncio.wait(timeout=...)`, then explicitly cancelled — **not** `asyncio.TaskGroup`, whose `__aexit__` *awaits* its children on normal exit (unbounded) and cancels them all if the iterator raises (no drain at all) |
| Shutdown / abort pair | two `CancellationToken`s | two `asyncio.Event`s — `shutdown_event` stops consuming, `abort_event` tells live attempts to settle now |
| Composition root | `main.rs` | one `composition.py` module: config, outbound adapters, per-concept control planes, registry, consumer, runtime — and nothing else |
| Boundary enforcement | manifest dependency gate | an import-linter forbidden contract (mandatory — see below); the package itself stays pure wire types — no ORM models, no broker client |

### Choosing a runtime: framework or plain broker client

Celery, arq, and dramatiq are **not** the Python equivalents of the Rust building
blocks. Each *bundles* four decisions this pattern keeps apart — broker binding,
message envelope, retry policy, worker runtime — and adopting one inherits all four.
The envelope is the sharpest consequence: Celery's protocol v2 owns the headers and
the `(args, kwargs, embed)` body, dramatiq's `Message` owns its fixed JSON fields, so
**the publisher-stamped `schema_version` gate is not yours at the message level.**
Keep it by publishing exactly one argument — the serialized contract envelope — and
validating `schema_version` in the task function's first statement.

| Invariant | Celery | dramatiq | arq (Redis) | plain `aio-pika` |
|---|---|---|---|---|
| Record before acknowledge | **Violated by default** — tasks are acknowledged *before* execution; must set `task_acks_late = True`, which Celery's own optimizing guide pairs with `worker_prefetch_multiplier = 1` (it defaults to **4**) for long tasks | Free — messages are acknowledged only after successful processing | Free by a different mechanism — "pessimistic execution": a job is not removed from the queue until it succeeds or fails | Yours — `message.ack()` explicitly, after the control plane has recorded the outcome |
| Redelivery after losing a worker mid-task | **Narrower than it sounds** — `task_acks_late` alone *does* redeliver on whole-node loss, a `SIGKILL` of the parent, or a broker disconnect; the documented gap is a task whose **child process** was terminated (by signal or `sys.exit()`), which Celery acknowledges anyway. `task_reject_on_worker_lost` closes that one gap — and Celery's configuration docs warn it **can cause message loops**, so enable it deliberately | **Broker-dependent** — free on RabbitMQ (dramatiq's `requeue` is a no-op there: RabbitMQ itself requeues unacked deliveries when a consumer disconnects); on Redis, unacked message ids are reclaimed only by probabilistic queue maintenance, gated on a 60 s worker-heartbeat timeout *and* a 0.1 % chance per dispatch — so on an idle queue a dead worker's messages can sit unreclaimed indefinitely | Free — a cancelled job is rerun on restart or by another worker | Yours — an unacknowledged delivery is requeued when the consumer or channel drops |
| Bounded drain, survivors requeued | Partial — `TERM` is a warm shutdown that waits for executing tasks and `QUIT` is cold (`REMAP_SIGTERM` makes `TERM` cold), but that is unconditional only while `worker_soft_shutdown_timeout` is unset: since Celery **5.5** a positive value inserts a time-limited *soft shutdown* before the cold one. The requeue half still comes only from the two settings above | Configure — actors are **not** interrupted by default (`ShutdownNotifications(notify_shutdown=False)`); set `notify_shutdown=True` and re-raise `Shutdown` to requeue | Configure — the default `handle_sig` cancels in-flight jobs immediately; a non-zero `job_completion_wait` (default `0`, **arq ≥ 0.25** — absent in 0.24) swaps in `handle_sig_wait_for_completion`, which stops picking up jobs and waits that many seconds first. Do not copy the name `wait_for_job_completion_on_signal_second` from arq's docstrings — it never shipped, and passing it raises `TypeError` | Yours, and exactly as specified — see below |
| Typed envelope, `schema_version` gate, lease fencing | inside the framework's payload only; no fencing | inside the framework's payload only; no fencing | inside the framework's payload only; no fencing | the envelope **is** the message; fencing is still yours to build |
| Exchange + per-task-type queue topology | framework-owned (`task_default_queue` defaults to `'celery'`; `task_queues` / `task_routes`) | framework-owned (`queue_name`, default `"default"`) | framework-owned Redis queue names | yours |

**What forces a plain broker client**: the envelope being the message, ownership of the
exchange and per-task-type queues, per-delivery *classified settlement*. If day 1 needs
those, use `aio-pika` and port the structure above; take dramatiq only when "late acks
plus retries" is the ceiling, Celery only when it alone provides a required integration.

**On the publishing side**, `aio-pika` defaults `Exchange.publish` to
`mandatory=True` but leaves `on_return_raises=False`, so a returned unroutable
message is **swallowed**. Open the publishing channel with
`publisher_confirms=True, on_return_raises=True`: that turns a return into a
`DeliveryError` and reproduces `TaskPublishError::Unroutable`.

### What no Python framework gives you: the lease/fencing control plane

Task frameworks give retries. **Retries are not fencing.** Celery's `task_id`,
dramatiq's `message_id`, and arq's `_job_id` identify a *message*; none serializes
two concurrent executions against a persisted state machine. Under at-least-once
delivery a redelivered task must resolve to *already leased* or *already terminal*, and
that decision lives in the API's application service, reached over your own
back-channel: a `TaskControlPlane` `Protocol` in the worker's `application/task/`, an
`httpx.AsyncClient`- or `grpc.aio`-backed adapter in `infrastructure/`, and an
`acquire_lease` returning `LeaseGranted | LeaseHeld | AlreadyTerminal` for the attempt
to match on. Where a lease is not warranted (short, cheap, single-writer work), use the
explicit idempotency key the *Non-idempotent task handlers* anti-pattern sanctions: in
the envelope, behind a uniqueness constraint.

### Holding the "worker owns no persistence" boundary

**In a Python monorepo the API's ORM models are one `import` away and nothing fails at
runtime** — a uv workspace installs every member into one shared `.venv`, so the worker
can `import api` with no declaration and `uv sync` stays silent (see [Python
conventions](../conventions/python.md), *uv Workspaces*, caveat 3). The substitute for
Rust's manifest gate is a forbidden-import contract, and it is **not optional**:

```toml
[tool.importlinter]
root_packages = ["api", "worker"]   # plural: the contract spans two distributions
include_external_packages = true    # required: it names external libraries
[[tool.importlinter.contracts]]
name = "Worker owns no persistence and never imports the API"
type = "forbidden"
source_modules = ["worker"]
forbidden_modules = ["api", "sqlalchemy", "alembic", "asyncpg", "psycopg", "aiosqlite"]
```

Set it up with `python-import-linter-setup` and run `lint-imports` in CI. Without
`include_external_packages` the drivers are not in the graph at all, and dropping one
from the list lets `import asyncpg` pass a green `lint-imports`.

### Bounded drain on shutdown, in asyncio

```python
# worker/application/task/runtime.py  (simplified)
class TaskRuntime:
    async def run(self) -> None:
        self.in_flight: set[asyncio.Task[None]] = set()   # strong references until done
        consume_task = asyncio.create_task(self.consume())
        shutdown_signalled = asyncio.create_task(self.shutdown_event.wait())
        # Wait for SIGTERM (its handler only sets shutdown_event) or for the consumer to
        # fail on its own. An `is_set()` test inside the consume loop is not enough:
        # `__anext__` parks on an empty prefetch buffer, so on an idle queue the loop body
        # never runs again. Shutdown has to interrupt the iterator, not just raise a flag.
        await asyncio.wait(
            {consume_task, shutdown_signalled}, return_when=asyncio.FIRST_COMPLETED
        )
        shutdown_signalled.cancel()
        # Stop accepting: cancelling the consumer unblocks `__anext__`, which closes the
        # iterator, which nacks its prefetched-but-unstarted deliveries with requeue.
        consume_task.cancel()
        await asyncio.gather(consume_task, return_exceptions=True)
        await self.drain()          # attempts are separate tasks and are still running

    async def consume(self) -> None:
        # Nothing between the pull and `create_task` awaits, so cancelling this task
        # can never orphan a delivery that was already pulled from the iterator.
        async with self.queue.iterator() as deliveries:
            async for delivery in deliveries:
                attempt_task = asyncio.create_task(self.run_attempt(delivery))
                self.in_flight.add(attempt_task)
                attempt_task.add_done_callback(self.in_flight.discard)

    async def drain(self) -> None:
        still_running = set(self.in_flight)
        if still_running:
            _finished, still_running = await asyncio.wait(
                still_running, timeout=self.shutdown_timeout_seconds
            )
        if still_running:
            self.abort_event.set()      # each live attempt settles now: nack, requeue
            _finished, still_running = await asyncio.wait(
                still_running, timeout=self.abort_grace_seconds
            )
        for straggler in still_running:  # explicit — nothing above cancels anything
            straggler.cancel()           # unsettled; the broker requeues on disconnect
        await asyncio.gather(*still_running, return_exceptions=True)
```

Three rules make that structure correct, and all three are load-bearing:

1. **`run_attempt` must never raise.** It owns the settlement; an escaping exception
   leaves its delivery unsettled until the connection drops, and a plain task set has
   no sibling to notice. Catch everything and convert it into one settlement.
2. **Settle exactly once, and only after the control plane recorded the outcome.**
   `message.ack()` / `reject(requeue=False)` / `nack(requeue=True)` map one-to-one
   onto `AckDrop` / `NackDrop` / `NackRequeue`. Never `async with message.process()`:
   it settles for you, and that settlement is the decision the attempt must own.
3. **Terminate the iterator before the drain, and before the channel.** Both its
   `__aexit__` and its cancellation path nack the buffered (prefetched, never started)
   deliveries with `requeue=True` — explicit and immediate. Closing the channel first
   loses nothing (RabbitMQ requeues unacked deliveries when the channel or connection
   drops), but it makes that requeue implicit, waiting on the broker to reclaim them.

## Quick Reference — Invariants

- **API = synchronous request handling; worker = asynchronous task execution;
  broker = the decoupling seam.** These three responsibilities live in three
  separate processes.
- **The shared contract package is the only code shared across the API/worker
  boundary** for dispatch (a workspace crate in Rust, a uv workspace member in
  Python). It is a pure wire-types package: no business logic, no database
  drivers, no runtime wiring.
- **TaskEnvelope carries a schema_version** stamped by the publisher and
  validated by the worker before dispatch. A version mismatch fails the task
  terminally — never silently discards or misinterprets.
- **Exchange + routing key, never queue name, on the publish side.** The
  publisher targets the exchange and the task type; queues are declared by the
  worker. `mandatory: true` makes an unroutable message a visible error.
- **One durable queue per task type.** The worker declares and binds only the
  queues for the task types it handles. A worker that does not know a task type
  never processes it.
- **Lease fencing makes every handler idempotent under at-least-once delivery.**
  A redelivered task that is already leased or terminal is settled without
  re-execution.
- **Classified delivery actions.** Every control-plane error maps to exactly one
  of ack-drop, nack-drop, or nack-requeue — the policy is explicit, not
  accidental.
- **Bounded drain on shutdown.** In-flight attempts finish within
  `shutdown_timeout`; survivors nack with requeue. Never kill mid-work.
- **Each task type is its own concept inside the worker's application layer.**
  The generic runtime machinery (`application/task/`) names no task-type RPCs
  and is never widened when a new task type is added.
- **The worker has its own composition root, bootstrap, and runtime.** It is a
  full hexagonal application, not a library or a plugin.
- **Adding a task type is one registration line in the composition root.** The
  generic runtime, the consumer adapter, and the entry point (`main.rs` in the
  Rust example) are never touched.
- **Vocabulary is binding: a *heartbeat* is control-plane liveness only** (a
  periodic "I am alive" that extends the lease; its failure is a stale lease).
  **A *progress report* is data-plane advancement** (cumulative counters, phase
  transitions; its failure is a stall). Never name a progress signal a
  heartbeat — a hung subprocess keeps heartbeats healthy while the work is
  dead, and conflating the words hides exactly that failure mode. Fix the
  vocabulary on day 1; renaming a misnamed `*Heartbeat` port later ripples
  through traits, implementors, and wire DTOs.
- **The control plane is authoritative for outcomes; record before
  acknowledge.** The worker reports its fenced result, the control plane
  persists the outcome, and only then does the worker ack the broker delivery.
  Acking first loses durable authority over a completed delivery.
- **The worker owns no persistence** — no dependency on the API package, no
  direct database driver. Enforce it with a dependency gate the build runs: the
  manifest dependency gate in Rust (`rust-architecture-test-setup`), a
  forbidden-import contract in Python (`python-import-linter-setup`), so the
  boundary survives every future contributor.
- **A system task is not a user-facing job.** The task is execution-control
  mechanics — lease, attempt, retry, broker delivery. A *job* is the
  user-visible execution and progress history the API exposes. Keep them as
  separate types with separate lifecycles: work may be queued, deferred, and
  retried for admission reasons with no job to show a user at all. Whether one
  job spans the whole task or each admitted attempt gets its own is a decision
  per operation kind — make it deliberately, once. Conflating the two puts
  scheduling noise in the user's history and costs a schema migration to undo.
- **No secret material on the dispatch path.** The broker message, the durable
  task row, the log line, and the worker's parent environment carry the task's
  non-secret identity and payload — never credentials or key material. Those are
  resolved and handed over only through the authenticated control-plane channel
  (see the [worker fleet pattern](worker_fleet_pattern.md) for what
  authenticates it), to a worker already holding a live lease, and are never
  persisted with the task. Prefer a `0600` credential file over a child
  process's environment, and use a per-child environment variable only where a
  tool offers no file mechanism. A broker is not a secret store, and on Linux
  `/proc/<pid>/cmdline` is world-readable by default, so argv is not private
  either.

## Anti-Patterns to Avoid

- **Doing long or blocking work in the request thread.** The HTTP handler blocks
  while the work runs; API latency degrades under load; the two layers cannot be
  scaled independently; the refactor to extract a worker is a multi-week project.
  Enqueue a task and return the task identifier to the caller immediately.

- **An untyped or informally typed queue.** Publishing a bare JSON blob with no
  schema version, no shared type, and no compiler enforcement between the producer
  and consumer means a field rename silently breaks the consumer at runtime. Use
  a shared contract package (a crate in Rust) with a typed envelope and a schema
  version.

- **Inline fire-and-forget spawning inside the API process** — `tokio::spawn` in
  Rust, a bare `asyncio.create_task` or FastAPI `BackgroundTasks` in Python: no
  handle, no queue, no broker. This is the most common way the three-process split
  collapses back into one. The task is lost on a crash or a restart. It cannot be
  retried, observed, or distributed to another instance.

- **Non-idempotent task handlers.** AMQP is at-least-once. A handler that does
  not check whether its work is already done will duplicate side effects on every
  redelivery. Use lease fencing (core-side) or explicit idempotency keys (inside
  the handler) to make re-execution a no-op.

- **Shared database ownership between the API and the worker.** The worker that
  writes its own task state directly into the API's database couples the two
  deployables at the schema level. The worker owns no persistence; it reads from
  and reports back to the API over the defined back-channel (gRPC in ironbox).

- **Concept-specific RPCs inside the generic runtime.** If `TaskRuntime` or
  `Attempt` imports `ConnectivityControlPlane`, adding a second task type forces
  a runtime change. The generic runtime stays concept-free; each handler holds
  its own concept port.

- **Skipping the contract package (a crate in Rust) for "just one task type."**
  The constraint that makes it necessary — the API and worker are separately
  deployed containers that can version-skew — is present from the first task type.
  It is cheap to create (`rust-workspace-setup`, or the uv workspace member in
  [Python conventions](../conventions/python.md)) and expensive to retrofit.

## Relationship to Other Patterns and Skills

- **[composition root pattern](../project_structure/composition_pattern.md)** —
  the worker has its own composition root; `main.rs` is where ports are wired to
  concrete adapters, task handlers are registered, and the queue topology is
  derived. The same pattern, applied to a second binary.

- **[bootstrap pattern](../lifecycle/bootstrap_pattern.md)** — the worker's
  config loading, adapter construction, and eager gRPC channel connect are
  bootstrap: side-effecting startup work that runs before the runtime loop begins.

- **[runtime worker supervision pattern](../lifecycle/runtime_pattern.md)** —
  `TaskRuntime` is the worker's runtime loop: it is the inbound-adapter-driven
  equivalent of the interval/event runners described in that pattern. The shutdown
  token, drain, and abort semantics are identical.

- **`rust-hexagonal-architecture`** — the worker is a hexagonal application. Its
  `application/task/` ports (`TaskConsumer`, `ControlPlane`, `TaskHandler`) are
  the inbound and outbound ports; the RabbitMQ consumer and gRPC adapters are the
  infrastructure implementations. The dependency rule is identical to the API.

- **`rust-workspace-setup`** — the shared contract crate lives in the workspace's
  `crates/` directory, declared as a path dependency by both the API and the
  worker `Cargo.toml` files. The workspace enforces a single version of every
  shared type across all workspace members.

- **`python-ddd`, `python-import-linter-setup`, and [Python
  conventions](../conventions/python.md)** — the Python delegates for the mapping
  above: the worker's own layering, the forbidden-import contract that replaces
  Rust's manifest dependency gate, and the uv workspace packaging that delivers the
  shared contract package to both services.

- **[worker fleet pattern](worker_fleet_pattern.md)** — once this pattern's
  API/worker/broker split exists, the fleet pattern fixes the next two day-1
  decisions: the deployment topology (homogeneous fleet, replica-count-only
  scaling) and worker identity (self-enrollment with the control plane as
  certificate authority).

- **[observability posture](../decisions/observability_posture_pattern.md)** —
  the durable task rows this pattern mandates (leases, attempts, outcomes) are
  the Stage-1 operational-evidence surface: runbook queries first, exported
  metrics later, with zero application change.
