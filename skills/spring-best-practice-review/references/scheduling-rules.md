# Scheduling and Async Work Review Rules

Use this file when `@Scheduled`, task execution, async executors, Quartz, overlapping runs, distributed scheduling, virtual-thread schedulers, or scheduled bulk work is in scope.

## Trigger and Ownership

- Identify every scheduler: Spring `@Scheduled`, `TaskScheduler`, `@Async`, Quartz, Kubernetes CronJob, external orchestrator, or message-driven trigger.
- Verify whether the job runs per application instance, per cluster, per tenant, or per partition.
- For multi-instance deployments, require explicit leader election, external coordination, partitioning, or idempotent duplicate-safe work.
- Prefer an external orchestrator or durable job framework when operators need backfills, history, retries, and manual recovery.

## Overlap, Timeouts, and Cancellation

- Prevent unintended overlap with single-flight guards, partition keys, durable job state, Quartz misfire policy, or duplicate-safe idempotency.
- Define max runtime, cancellation behavior, shutdown drain, and what happens when the next trigger fires while a prior run is active.
- Do not rely on in-memory locks for cluster-wide mutual exclusion.
- Keep scheduled work out of request/response transactions.

## Failure and Idempotency

- Make scheduled side effects idempotent or protected by unique constraints and operation state.
- Bound retries with backoff, jitter, retry budget, and poison-item handling.
- Treat remote calls from scheduled jobs like production HTTP clients: deadlines, timeouts, rate limits, and caller-visible failure semantics still apply.
- For backfills, use resumable checkpoints, throttling, metrics, and operator runbooks.

## Threads and Executors

- Verify scheduler pool size for non-virtual-thread scheduling and understand that one default scheduler thread can serialize unrelated jobs.
- If virtual threads are enabled, review `SimpleAsyncTaskScheduler` behavior and remember that pooling properties may not apply.
- Size async executors, database pools, HTTP client pools, and downstream quotas together.
- Do not use virtual threads as a concurrency limiter; use semaphores, bulkheads, resource pools, or queue bounds.

## Operations

- Emit job start, success, failure, duration, skipped-overlap, retry, lag, processed count, and last-success timestamp metrics.
- Provide operator actions for pause, resume, rerun, backfill, abandon, and parameter correction when the workload matters operationally.
- Include scheduled task health in readiness only when the traffic-routing consequence is intentional.
