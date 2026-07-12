# Performance and Capacity Review Rules

Use this file for static performance and capacity design review. Do not interpret runtime metrics, traces, dumps, JFR, profiles, or confirm a bottleneck here; hand those outputs to `spring-performance-investigator`. You may check whether an existing design or tuning proposal names adequate evidence and validation.

## Evidence and Workload Model

- Verify that an existing design or claim identifies Spring Boot, Spring Framework, Java, container, database, driver, client, and infrastructure versions.
- Define the workload: request and message mix, payload and result sizes, read/write ratio, data cardinality, cache state, fan-out, concurrency, arrival pattern, geographic latency, and steady, peak, burst, and failure conditions.
- Define SLOs and resource budgets for latency percentiles, throughput, errors, saturation, memory, CPU, connection use, queue depth, and cost. Do not optimize from averages alone.
- Use aggregatable histograms with SLO-aligned buckets where possible. Do not average client-side percentiles across instances, and report p999 only when the sample count and observation window make it meaningful.
- Require a reproducible baseline and before/after evidence. Treat a microbenchmark, local single-user test, or synthetic happy path as insufficient evidence for end-to-end capacity.

## Capacity, Pools, and Queues

- Build one concurrency model across server threads or event loops, async executors, HTTP clients, database pools, Redis connections, broker consumers, schedulers, and downstream quotas. Include every replica when calculating total connections and concurrency.
- Use measured service time and arrival rate to estimate in-flight work as a steady-state sanity check, not a standalone sizing formula. Validate under production-like bursts and failures, and include retries, fan-out, slow dependencies, and timeout duration because they increase retained concurrency.
- Bound queues and pending-acquire waiters. Define acquisition timeouts, rejection or load-shedding behavior, caller-visible errors, and recovery after saturation.
- Size scarce-resource pools from the downstream capacity and workload, not from server thread count alone. Increasing a pool can move the bottleneck to the database, broker, network, or garbage collector.
- Treat retries as additional offered load. Test retry budgets, backoff, jitter, circuit breaking, and recovery together with pool and queue limits.

## JVM and Container Runtime

- Review container CPU and memory limits together with heap, metaspace, direct buffers, thread stacks, code cache, native libraries, memory-mapped files, and telemetry agents. Leave headroom for non-heap memory and termination handling.
- For Kubernetes, review Deployment surge/unavailable limits and progress deadlines, Pod termination and `preStop`, disruption-budget limitations, HPA metric semantics and resource requests, and topology spread under rollout, drain, autoscaling, and zone failure.
- Require an existing JVM-tuning proposal to correlate GC pause, allocation rate, live-set size, CPU throttling, safepoints, thread states, lock contention, page faults, and out-of-memory events before changing collector or heap flags.
- Require JFR, async-profiler or equivalent production-safe evidence, heap histograms, thread dumps, or allocation evidence instead of speculative tuning, with the exact JDK and flags recorded. Hand artifact interpretation to the investigator.
- For virtual-thread proposals, require evidence that separates carrier pinning from downstream saturation and accounts for the deployed JDK's monitor-pinning behavior.

## Web and HTTP Runtime

- Review connector limits, request queues, keep-alive, header and body limits, multipart limits, compression, serialization, streaming duration, client disconnects, graceful drain, and slow-client behavior.
- For MVC, correlate servlet concurrency with database and downstream pools. For WebFlux, verify event-loop utilization, blocking detection, scheduler hops, backpressure, buffer limits, and cancellation.
- Bound outbound connection pools, pending acquisition, DNS, connect, TLS, write, response, read, redirect, decoder, and total-call time within the end-to-end deadline.
- Measure response size and serialization allocation. Do not enable compression blindly for already-compressed or small payloads; test CPU and bandwidth tradeoffs.

## Relational Data Access

- Require representative SQL and, when performance claims depend on them, execution plans, row estimates, indexes, sort and join strategy, lock waits, temporary storage, network round trips, and returned row counts. Hand runtime plan interpretation to the investigator.
- Prefer bounded pagination and projections. Evaluate keyset pagination for deep or high-churn result sets, and reject unbounded reads, writes, deletes, or ORM graph traversal.
- Measure N+1 queries, JDBC batching, fetch and batch size, persistence-context growth, flush frequency, transaction duration, and connection acquisition time with production-like cardinality.
- Calculate the database connection ceiling across all application replicas, jobs, consumers, administrative traffic, and rollout overlap. Reserve capacity for failover and operations.
- Treat schema changes and backfills as capacity events. Test lock duration, replication lag, log growth, throttling, pause/resume, and rollback independently from application request load.

## Cache, Messaging, and Background Work

- Measure cache hit ratio by use case together with miss cost, stampede behavior, hot keys, value size, invalidation lag, memory growth, eviction, and stale-data tolerance.
- Define negative-cache semantics and TTLs so authorization outcomes, transient failures, or tenant-specific absence cannot be shared incorrectly.
- Size consumer concurrency, partitions or queues, prefetch, batch or chunk size, processing time, database use, and downstream quotas as one flow-control system. Track lag and redelivery amplification.
- Bound async and scheduled work with queue limits, concurrency limits, timeouts, cancellation, and shutdown drain. Virtual threads do not make downstream capacity unbounded.

## Startup and Test Performance

- Profile startup phases and bean initialization before adopting lazy initialization, AOT, native image, CDS, or CRaC. Include first-request latency, warm-up, observability, and operational complexity in the decision.
- Preserve Spring TestContext cache reuse and inspect cache statistics when integration suites are slow. Minimize unnecessary context-key variation, process forks, `@DirtiesContext`, dynamic properties, and per-test bean overrides.

## Verification

- Test warm-up, steady state, expected peak, burst, soak, dependency slowdown, partial outage, retry storm, autoscaling, deployment overlap, and recovery. Use production-like data volume and cardinality.
- Ensure the load generator does not hide coordinated omission or become the bottleneck. Use an open-arrival model when validating an external request rate, and record client-side and server-side latency, offered and completed throughput, errors, saturation, and dropped or rejected work.
- Compare one material change at a time where possible. Preserve raw results, configuration, version information, and acceptance thresholds so regressions can be reproduced.
