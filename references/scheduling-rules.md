# Scheduling and Job Coordination Review Rules

Use this file only when `@Scheduled`, `TaskScheduler`, `TaskExecutor`, Quartz, cron, periodic jobs, scheduled bulk work, single-flight tasks, overlap prevention, or distributed job coordination is in scope.

## Mechanism Selection

- Use `@Scheduled` for simple in-process periodic work. Treat it as per-instance behavior: every running application instance may execute the task unless the design adds coordination.
- Use Spring Batch for restartable, stateful, large-volume, chunk-oriented jobs.
- Use Quartz when durable schedules, calendars, persistent triggers, misfire handling, clustering, operator control, or job metadata matter.
- Use an external orchestrator when cross-service dependency graphs, long-running workflows, human approval, backfill planning, or centralized run history matter.

## Task Design

- Define job identity, trigger source, idempotency key, overlap policy, retry budget, timeout, and cancellation behavior before approving a scheduled task.
- For fixed-rate, fixed-delay, and cron schedules, review time zone, daylight-saving behavior, startup delay, long-running execution, and what happens after missed executions.
- Keep transactions short and do not hold database transactions across remote calls, file operations, message sends, or long computation.
- Do not run slow or blocking work on an undersized scheduler. Spring Boot's default non-virtual-thread scheduler has one thread unless configured; virtual-thread scheduling uses a different scheduler and ignores pooling properties.
- Bound concurrency with resource pools, semaphores, or bulkheads. Do not rely on virtual threads to protect a database, broker, or remote API.

## Distributed Coordination

- In a multi-instance deployment, decide explicitly whether each instance should run the task, only one instance should run it, or work should be partitioned.
- For single-instance execution, prefer a database invariant, Quartz clustering, leader election, or a reviewed lock registry. Redis locks can reduce duplicates, but correctness-critical tasks still need fencing, idempotency, or database constraints.
- Prevent overlapping runs for the same logical job unless overlap is explicitly safe. Include behavior for stuck jobs, lock timeout, node crash, and manual unlock.
- Make side effects idempotent: email, webhooks, payments, file writes, message sends, and external API calls need duplicate-suppression or an outbox-style record.

## Quartz

- Verify JobStore choice, DataSource, transaction manager, clustering setting, thread pool, misfire policy, calendars, job durability, and whether jobs are stateful or can run concurrently.
- Do not enable production Quartz schema initialization casually. Standard Quartz initialization scripts can drop existing tables and delete triggers on restart.
- Review whether application-defined jobs should overwrite existing persisted jobs, and how schedule changes are rolled out safely.
- Expose operator procedures for pause, resume, trigger now, abandon, rerun, backfill, and parameter correction.

## Observability and Operations

- Track scheduled task duration, failures, skipped runs, overlapping-run prevention, lock wait, lock timeout, last success, next fire time, and backlog.
- Use actuator `scheduledtasks` and `quartz` endpoints when available, but secure them like other management endpoints.
- Verify graceful shutdown: stop accepting new triggers, drain or cancel in-flight work, stop message listeners in the right order, and record recoverable state.

## Testing

- Test overlap, duplicate trigger, node crash, lock timeout, clock drift or time-zone behavior, long execution, retry exhaustion, manual rerun, and idempotent side effects.
- For Quartz or distributed scheduling, use a real database and multiple application instances in at least one integration or staging test.

## Immediate Anti-Patterns

- `@Scheduled` in a horizontally scaled service with no stated overlap or single-run policy.
- Cron logic that ignores time zone, DST, missed executions, or long-running task behavior.
- Scheduler launching non-idempotent side effects without duplicate suppression.
- Quartz JDBC schema initialization enabled in production without protecting existing triggers.
- Hidden long-running work on the default one-thread scheduler.
