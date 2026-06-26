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
  version: "0.0.1"
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

## Quick Reference — Invariants

- **API = synchronous request handling; worker = asynchronous task execution;
  broker = the decoupling seam.** These three responsibilities live in three
  separate processes.
- **The shared contract crate is the only code shared across the API/worker
  boundary** for dispatch. It is a pure wire-types crate: no business logic, no
  database drivers, no runtime wiring.
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
  generic runtime, the consumer adapter, and `main.rs` are never touched.

## Anti-Patterns to Avoid

- **Doing long or blocking work in the request thread.** The HTTP handler blocks
  while the work runs; API latency degrades under load; the two layers cannot be
  scaled independently; the refactor to extract a worker is a multi-week project.
  Enqueue a task and return the task identifier to the caller immediately.

- **An untyped or informally typed queue.** Publishing a bare JSON blob with no
  schema version, no shared type, and no compiler enforcement between the producer
  and consumer means a field rename silently breaks the consumer at runtime. Use
  a shared contract crate with a typed envelope and a schema version.

- **Inline fire-and-forget spawning inside the API binary** (`tokio::spawn` with
  no handle, no queue, no broker). The task is lost on a crash or a restart. It
  cannot be retried, observed, or distributed to another instance.

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

- **Skipping the contract crate for "just one task type."** The constraint that
  makes the contract crate necessary — the API and worker are separately deployed
  containers that can version-skew — is present from the first task type. The
  crate is cheap to create (see `rust-workspace-setup`) and expensive to retrofit.

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
