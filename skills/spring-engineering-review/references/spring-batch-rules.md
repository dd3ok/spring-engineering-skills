# Spring Batch Review Rules

Use this file only when Spring Batch, scheduled bulk processing, chunk-oriented jobs, restartability, partitioning, or large data movement is in scope.

## Job and Step Design

- Identify jobs, steps, readers, processors, writers, chunk sizes, transaction managers, JobRepository storage, and launch mechanism.
- Require stable job parameters and clear rules for whether a new run creates a new JobInstance or restarts an existing one.
- Design every step for restartability or explicitly document why restart is disabled and how operators recover.
- Keep `JobRepository` state for restartable production jobs in durable infrastructure with backup and recovery behavior matched to the job contract.
- Keep batch jobs out of request/response paths. Use explicit launch, scheduling, or orchestration with concurrency control.

## Spring Batch 6 Infrastructure

- On Batch 6+, identify the actual `JobRepository` and transaction infrastructure. Do not mistake the default `ResourcelessJobRepository` from `@EnableBatchProcessing` or `DefaultBatchConfiguration` for durable metadata storage.
- Treat the resourceless repository as suitable only for bounded one-shot work that does not require restart metadata, shared execution context, concurrent execution, partition metadata, or operational history. Do not require a database repository for every non-restartable single-process job.
- When restart, concurrency, partitioning, or operational inspection is required, verify an explicitly configured store-specific repository such as JDBC or MongoDB and its matching transaction manager, backup, and recovery behavior.
- For a Batch 6 migration, review repository configuration, metadata schema changes, execution-context serialization, Jackson 3 effects, immutable domain-model changes, and moved or removed APIs against the exact migration guide.

## Correctness and Idempotency

- Make readers restart-safe and writers idempotent. Check checkpoint state, item identity, duplicate handling, and partial-write behavior.
- Review skip/retry limits, retryable exception classification, poison-record capture, and compensation for side effects outside the transaction.
- Verify transaction boundaries around chunk processing, database writes, message sends, file writes, and remote calls.
- For remote calls inside chunks, require deadlines, bounded retries, idempotency, and rate limits that cannot stall a transaction or overload the dependency.
- Avoid mixing schema migration, data backfill, and business processing in one opaque job.

## Scale and Operations

- Size chunks, pages, fetch size, thread pools, partitions, and database pools together. Validate with production-like volume.
- For partitioned or parallel jobs, review key ranges, ordering needs, shared resource contention, and duplicate partition execution.
- Expose job metrics, step metrics, read/write/skip counts, duration, lag, restart count, and failure reason.
- Provide operator runbooks for start, stop, abandon, restart, parameter correction, and backfill.

## Testing

- Add tests for restart after mid-chunk failure, duplicate input, writer retry, skip limits, empty input, large input, and operator restart.
- Prefer Testcontainers or real infrastructure for database, file store, queue, and remote-system integration paths.
