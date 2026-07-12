# Spring Architecture and Operations Review Rules

Load for broad/full reviews and for architecture, distributed-systems, observability, operations, or testing concerns.

## Spring Portfolio Scope

- Treat Spring Boot, Spring Framework, Spring Security, Spring Data, Spring Cloud, Micrometer, and Reactor as the default review surface.
- Treat workload-specific Spring projects as conditional and load focused references using `SKILL.md` routing when the stack, dependency list, or user request mentions them.
- Treat Spring Shell as CLI-specific and version-gated. Do not recommend Projects in the Attic for new designs except legacy migration or replacement planning.
- Prefer active Spring projects and Spring Initializr-supported starters for new applications, then verify module-specific docs before approving unusual stack choices.

## Version and Dependency Management

- For new applications, prefer Spring Initializr and a minimal starter set over hand-assembling Spring dependencies.
- Treat auto-configuration as the default, but verify selected starters match the runtime model before approving them.
- Match the Spring Cloud release train to the Spring Boot minor line. Check the Spring Cloud compatibility table for the exact supported range.
- Before a major upgrade, first move to the latest patch version of the current major/minor line and remove deprecated APIs and properties.
- For Spring Boot major upgrades, load `references/migration-rules.md` and verify the target line against the official migration guide, release notes, system requirements, Spring Cloud compatibility table, and dependency generation support before making version-specific claims.
- For version and security checks, start with official release highlights, generation compatibility/support pages, and Spring security advisories before relying on blog posts or transitive dependency scanners alone.
- Treat native-image, AOT, CRaC, and checkpoint/restore guidance as deployment-specific. Do not recommend them unless startup time, memory footprint, packaging, or platform requirements justify the tradeoff. When they are in scope, review reflection/resource/proxy hints, dynamic class loading, serialization, generated clients, observability agents, TLS/cert loading, startup initialization, native integration tests, and post-restore reinitialization of sockets, pools, schedulers, locks, clocks, credentials, random seeds, and external connections.
- For Kotlin applications, review nullability boundaries, validation on constructor properties, all-open/no-arg plugin needs for proxies/JPA, coroutine transaction behavior, blocking calls inside suspend/reactive paths, and Jackson/Kotlin module configuration.
- Treat externalized configuration as production behavior. Review property-source precedence, profile activation/groups, `spring.config.import`, config trees for mounted secrets, and fail-fast `@ConfigurationProperties` validation.

## Redis and Caching

- Load `references/redis-rules.md` when Redis is central to correctness, topology, locks, rate limiting, streams, pub/sub, sessions, or failover behavior.
- Use Redis cache for shared, short-lived, invalidatable data. Use local Caffeine for hot per-instance cache when appropriate.
- In baseline review, flag missing TTL/serializer/key-prefix/invalidation policy, Java native serialization, large `KEYS`-based clears, correctness-critical Redis locks without fencing/idempotency, and unreviewed topology/failover assumptions.

## Scheduling and Async Work

- Load `references/scheduling-rules.md` when `@Scheduled`, Quartz, task execution, async executors, overlapping runs, virtual-thread schedulers, or distributed scheduling are central to the request.
- In baseline review, flag scheduled work without overlap control, idempotency, timeout, retry/backoff, cancellation, observability, and multi-instance behavior.

## Architecture and Modular Boundaries

Use this section for a static boundary screen. Use `spring-modulith-auditor` for an explicit dependency graph, Modulith verification semantics, event-registry behavior, and module-test audit.

- For large modular monoliths, check whether package boundaries, domain events, and dependency direction are explicit enough to test. Consider Spring Modulith when module verification, module-level integration tests, generated module documentation, or event publication/outbox support would reduce architecture drift.
- Do not introduce Spring Modulith just to add framework surface area. Use it when the application already has meaningful domain modules or when module-boundary regression tests are a concrete need.
- For public REST APIs, prefer test-generated documentation such as Spring REST Docs when API examples, headers, fields, and error contracts must stay synchronized with tests.

## High Traffic and Distributed Systems

- Load `references/performance-rules.md` when throughput, latency, capacity, pools, queues, JVM/container tuning, profiling, startup, or load testing is central to the request.
- Use circuit breakers, bulkheads, rate limiters, and load shedding where dependencies can fail or saturate.
- On Spring Framework 7+, consider `@Retryable` and `@ConcurrencyLimit` for simple method-level resilience only after verifying `@EnableResilientMethods` or equivalent infrastructure is active. Account for proxy-invoked method semantics, self-invocation, retry classification, total attempts, backoff, and idempotency. `@Retryable` adapts supported reactive return types; do not assume identical reactive-pipeline behavior for concurrency limiting without verification. Do not treat these annotations as replacements for end-to-end circuit breaking, deadlines, idempotency, and backpressure.
- If Spring Cloud Circuit Breaker or Resilience4J is used, verify blocking versus reactive starter choice, timeout and bulkhead semantics, fallback behavior, property precedence, and exported metrics.
- Track SLO-relevant tail latency, not just averages. Require sufficient samples before reporting extreme percentiles such as p999, and prefer aggregatable histograms over averaging per-instance client-side percentiles.
- Size pools explicitly: HTTP client, server threads, database pool, Kafka consumer concurrency, Redis connections, and Reactor schedulers.
- Ensure Kubernetes readiness reflects the ability to serve traffic, liveness reflects recoverability, and startup probes cover slow initialization without masking real deadlocks.
- Do not include shared external systems such as databases, Web APIs, or Redis in liveness checks. Include external checks in readiness only when the traffic-routing consequence is understood.
- Check graceful shutdown behavior for web requests, message consumers, scheduled jobs, and in-flight database work, including drain windows and listener/container stop ordering.

## Observability and Operations

- Add actuator endpoints, metrics, tracing, structured logs, and correlation IDs.
- Secure management endpoints and limit exposed actuator endpoints.
- Export Micrometer and OpenTelemetry signals using platform conventions.
- Define observation conventions and context propagation across HTTP, messaging, scheduler, async, and reactive boundaries. Avoid duplicate auto-instrumentation.
- Pin the OpenTelemetry semantic-convention and instrumentation transition in use; prevent duplicate legacy/stable attributes and budget high-cardinality HTTP, database, messaging, and tenant dimensions.
- Define SLO dashboards and alerts for latency, errors, saturation, and queue lag.
- Watch metric cardinality, especially labels derived from user input, URLs, tenant IDs, error messages, or exception details.
- Verify that handled exceptions are visible in logs/metrics/traces when they affect user-visible behavior.

## Testing

Use this section to check whether the reviewed change has adequate verification. Use `spring-test-gap-planner` for the risk-ranked backlog, fixtures, CI placement, runtime, and flakiness design.

- Use Spring Boot test slices for web, data, JSON, GraphQL, and similar infrastructure boundaries; prefer plain unit tests or narrow integration tests for service-layer logic unless Spring infrastructure is part of the behavior under test.
- Prefer Spring's test support, including TestContext, MockMvc, WebTestClient, and Spring Boot test slices, over ad hoc integration harnesses.
- Use Testcontainers for integration tests with real databases, Redis, Kafka, and dependent infrastructure.
- Use `@ServiceConnection` when supported to reduce brittle property wiring.
- Use embedded Kafka carefully. Avoid mixing global embedded brokers with per-test brokers.
- Preserve Spring TestContext cache reuse: review excessive context-key variation, process forking, `@DirtiesContext`, dynamic properties, and bean overrides when integration suites are slow. Measure cache statistics before increasing parallelism or replacing tests.
- Include failure-mode tests for duplicate requests, retry after timeout, broker outage, database deadlock, lock timeout, cache miss, stale cache, consumer replay, authorization denial, and graceful shutdown.
