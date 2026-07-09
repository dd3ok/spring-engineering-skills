# Spring Review Rules

Use these rules for Spring and Spring Boot architecture reviews, code reviews, migration reviews, and production-readiness checks.

## Contents

- Version and Dependency Management
- Configuration, Secrets, and Runtime State
- MVC, WebFlux, and Threads
- API and HTTP Clients
- Security
- Validation, Serialization, and External Side Effects
- Transactions, Concurrency, and Idempotency
- Data Access
- Spring Data JDBC and Relational
- JPA and Hibernate
- Kafka and Messaging
- Redis and Caching
- Scheduling and Async Work
- Architecture and Modular Boundaries
- High Traffic and Distributed Systems
- Observability and Operations
- TLS and Certificates
- Testing
- Immediate Anti-Patterns

## Spring Portfolio Scope

- Treat Spring Boot, Spring Framework, Spring Security, Spring Data, Spring Cloud, Micrometer, and Reactor as the default review surface.
- Treat workload-specific Spring projects as conditional and load focused references using `SKILL.md` routing when the stack, dependency list, or user request mentions them.
- Treat Spring Shell as CLI-specific and version-gated. Do not recommend Projects in the Attic for new designs except legacy migration or replacement planning.
- Prefer active Spring projects and Spring Initializr-supported starters for new applications, then verify module-specific docs before approving unusual stack choices.

## Version and Dependency Management

- Use Spring Boot BOM-managed dependency versions by default.
- For new applications, prefer Spring Initializr and a minimal starter set over hand-assembling Spring dependencies.
- Treat auto-configuration as the default, but verify selected starters match the runtime model before approving them.
- Do not override Spring Framework, Spring Data, Reactor, Kafka, Hibernate, Micrometer, Spring Security, or Spring Cloud versions without verified compatibility evidence.
- Match the Spring Cloud release train to the Spring Boot minor line. Check the Spring Cloud compatibility table for the exact supported range.
- Before a major upgrade, first move to the latest patch version of the current major/minor line and remove deprecated APIs and properties.
- For major upgrades, load `references/migration-rules.md`; state exact Java, Kotlin, GraalVM, Jakarta, Servlet, Jackson, server, and build-tool requirements only after checking the target line's official sources.
- For version and security checks, start with official release highlights, generation compatibility/support pages, and Spring security advisories before relying on blog posts or transitive dependency scanners alone.
- Treat native-image, AOT, CRaC, and checkpoint/restore guidance as deployment-specific. Do not recommend them unless startup time, memory footprint, packaging, or platform requirements justify the tradeoff.
- Treat externalized configuration as production behavior. Review property-source precedence, profile activation/groups, `spring.config.import`, config trees for mounted secrets, and fail-fast `@ConfigurationProperties` validation.
- For Kotlin Spring applications, verify Spring Boot/Kotlin compatibility, compiler plugin use such as `kotlin-spring` and no-arg where needed, nullability boundaries, and Java interoperability.

## Configuration, Secrets, and Runtime State

- Treat configuration as part of the release contract: review property-source precedence, profile groups, config imports, config-tree mounts, placeholders, and fail-fast validation.
- For Spring Cloud Config, review backend choice, label/version strategy, profile merge order, access controls, encryption keys, key rotation, health checks, refresh boundaries, and failure behavior when the config server is unavailable.
- For Vault or secret managers, review authentication method, token/lease renewal, secret rotation, revocation, fail-fast behavior, TLS, audit logs, and whether dynamic credentials outlive connection pools.
- Secure actuator `env` and `configprops` exposure and avoid logging secrets through startup reports, error messages, traces, or debug dumps.

## MVC, WebFlux, and Threads

- Default to Spring MVC for blocking CRUD APIs, JPA/Hibernate, JDBC, traditional servlet filters, and simple request/response services.
- Choose WebFlux only when the runtime path is genuinely non-blocking end to end, or when streaming, backpressure, or high-concurrency I/O workloads justify it.
- If both `spring-boot-starter-web` and `spring-boot-starter-webflux` are present, treat MVC as the default runtime unless the application explicitly configures a reactive application type.
- Never block Reactor event-loop threads. Isolate unavoidable blocking calls with `Schedulers.boundedElastic()` and test with BlockHound where appropriate.
- Do not present WebFlux as a performance fix for blocking database calls.
- Treat virtual threads as an option for blocking I/O throughput, not a substitute for non-blocking design and not a lower-latency guarantee. Verify Java version and `spring.threads.virtual.enabled` behavior before recommending them.
- For virtual threads, check pinning risk from long `synchronized`, native, or foreign-function calls; do not pool virtual threads to limit concurrency. Use resource pools, semaphores, or explicit bulkheads instead.
- For WebFlux/Reactor, review backpressure, `publishOn`/`subscribeOn` placement, context propagation, and `ThreadLocal` bridging before accepting mixed reactive/imperative code.

## API and HTTP Clients

- Load `references/http-client-rules.md` when outbound HTTP correctness, deadlines, retries, SSRF, client pools, declarative clients, or service-to-service reliability are central to the request.
- Prefer explicit API versioning through path, header, query parameter, or media type strategies.
- Prefer RFC 9457 Problem Details for API error responses.
- Avoid suffix-pattern content negotiation.
- Define stable error codes, correlation IDs, and idempotency-key behavior in API contracts.
- For outbound HTTP, use baseline smoke checks only: client choice matches the app model, hot paths do not block reactive clients, every remote call has timeout/deadline behavior, user-influenced URLs have SSRF controls, and retries are bounded by idempotency or compensation.

## Security

- Prefer deny-by-default authorization: explicitly permit public endpoints and protect everything else.
- Verify actuator endpoint exposure, authentication, authorization, network reachability, and sensitive endpoint access.
- Do not assume method-level authorization is active just because Spring Security is on the classpath. Check for explicit method-security enablement when service-layer authorization matters.
- Keep CSRF enabled for browser/session-backed state-changing flows. Disable it only for stateless APIs or protocols where it is incompatible, and document why.
- For OAuth2 resource servers, verify issuer/JWKS/introspection configuration, token audience/issuer validation, clock skew handling, and multi-tenant token validation if applicable.
- For browser clients, review CORS origins, credentialed requests, cookie `Secure`/`HttpOnly`/`SameSite` settings, session fixation protection, and logout behavior.
- For passwords, tokens, and reset flows, verify adaptive password hashing, token expiry and rotation, auditability, and absence of secrets in logs or traces.
- For file upload/download paths, require size limits, type validation, path traversal controls, safe content disposition, storage isolation, and malware or content scanning where risk justifies it.
- Avoid leaking authorization failure details in API responses. Prefer logs, audit events, and correlation IDs for diagnosis.

## Validation, Serialization, and External Side Effects

- Validate request DTOs, message payloads, and command objects at the boundary. For service method validation, verify type-level `@Validated` is present where inline method constraints are expected.
- Validate `@ConfigurationProperties` so missing endpoints, credentials, pool sizes, limits, and feature flags fail at startup instead of failing under traffic.
- Review JSON/XML serialization boundaries: unknown fields, enum evolution, date/time formats, numeric precision, polymorphic deserialization, backward compatibility, and PII in logs or traces.
- For email, SMS, webhooks, push notifications, file writes, and other external side effects, require explicit timeouts, retry budgets, idempotency or duplicate suppression, auditability, and outbox-style recovery when side effects are coupled to database changes.
- Use JTA/XA only when all enlisted resources, transaction managers, recovery logs, and operational procedures are explicitly supported. Prefer outbox, idempotent consumers, or compensation for service-to-service consistency.

## Transactions, Concurrency, and Idempotency

- Keep transactions short and local to one consistency boundary.
- Account for Spring rollback defaults: unchecked exceptions and `Error` roll back by default; checked exceptions need explicit rollback rules unless the project has changed rollback semantics.
- Avoid `REQUIRES_NEW` in loops or hot paths unless the connection pool is sized for nested transactions.
- Use optimistic locking with `@Version` for aggregate updates where lost updates are possible.
- Use pessimistic locks only for short critical sections and only when deadlock and retry behavior are handled explicitly.
- Require an idempotency key for externally retried commands and persist request state or result under a unique constraint.
- Do not keep database transactions open across HTTP calls, Kafka sends that may block, long computation, or slow I/O.

## Data Access

- Prefer JPA when aggregate persistence, identity/lifecycle management, and object mapping fit the domain model.
- Use `JdbcClient` or `JdbcTemplate` for SQL-heavy, bulk, reporting, or precise query paths.
- Use jOOQ when type-safe SQL and schema-driven code generation matter, subject to Java-version and license constraints.
- Use R2DBC only for reactive database access in a fully reactive path.
- Keep Spring Data repository interfaces narrow. Use derived queries for simple predicates and explicit `@Query` or custom repository code when intent, performance, or query shape would otherwise be hidden.
- Enable Spring Data auditing deliberately. Verify who supplies auditor identity, how timestamps are set, and whether audit metadata is part of the domain contract.
- Use exactly one schema-management mechanism in production, preferably Flyway or Liquibase.
- Do not rely on Hibernate `ddl-auto` or `import.sql` for production schema evolution.

## Spring Data JDBC and Relational

- Treat Spring Data JDBC as an aggregate-centric repository model, not a lightweight JPA replacement. Verify aggregate roots, ownership, and consistency boundaries explicitly.
- Expect one repository per aggregate root. Avoid repositories for nested entities that are only reachable through an aggregate root.
- Account for Spring Data JDBC save semantics: referenced entities in an existing aggregate may be deleted and recreated. Review write amplification, triggers, foreign keys, audit tables, and optimistic-lock behavior before using it on large aggregates.
- Do not assume JPA behavior such as lazy loading, dirty checking, first-level cache identity semantics, or entity graphs when reviewing Spring Data JDBC.
- For high-read aggregate paths, check whether Single Query Loading applies, whether its constraints are met, and whether fallback loading creates excessive SQL statements.
- Use Spring Data Commons repository, mapping, auditing, and entity-state rules as shared assumptions across Spring Data modules, then check module-specific behavior before making performance or consistency claims.

## JPA and Hibernate

- Make associations lazy by default unless a specific eager association is justified and tested.
- Use DTO projections, fetch joins, `@EntityGraph`, batch fetching, or query-specific fetch plans to solve N+1.
- Test SQL statement counts for important read paths.
- For write-heavy paths, verify JDBC batch size, ordered inserts/updates where applicable, flush mode, persistence-context growth, and Hibernate statistics before approving performance claims.
- Avoid Open Session in View for production APIs unless lazy rendering is deliberately accepted.
- Treat second-level cache as an optimization with explicit consistency semantics, not as a correctness mechanism.
- Account for stale persistence-context state after bulk updates and deletes.

## Kafka and Messaging

- Partition by business key when ordering per key matters.
- Use idempotent producers and appropriate `acks` and retry settings for durability.
- Disable consumer auto-commit for business-critical processing unless the risk is explicitly accepted.
- Use `read_committed` only when consuming transactional records and when the latency and visibility tradeoff is acceptable.
- Design retry topics, dead-letter topics, and poison-message handling explicitly.
- For Spring Kafka non-blocking retries, verify they are not combined with container transactions, and document topic naming, backoff precision, fatal-exception classification, and DLT processing strategy.
- For database plus Kafka atomicity, prefer transactional outbox or a consciously documented alternative. Require idempotent consumers.
- Do not claim Kafka exactly-once semantics make external database writes, HTTP calls, emails, or other side effects exactly once.
- If using Spring Kafka transactions, verify `transaction-id-prefix` uniqueness per application instance, size transactional producer caches for concurrency, and set producer `maxAge` below broker `transactional.id.expiration.ms` when idle producers can expire.
- For Spring Kafka consumers, review listener container ack mode, `enable.auto.commit`, concurrency versus partition count, partition assignment strategy, batch-vs-record listener tradeoffs, deserialization failure handling, rebalance behavior, and `max.poll.interval.ms` together.

## Redis and Caching

- Load `references/redis-rules.md` when Redis is central to cache design, session storage, locks, rate limiting, streams, pub/sub, or topology.
- Use Redis cache for shared, short-lived, invalidatable data. Use local Caffeine for hot per-instance cache when appropriate.
- In baseline review, flag missing TTL/key-prefix/serializer/null-cache policy, large `KEYS` clears, correctness-critical Redis locks without fencing or idempotency, and unreviewed topology/failover assumptions.

## Scheduling and Async Work

- Load `references/scheduling-rules.md` when `@Scheduled`, Quartz, task execution, async executors, overlapping runs, virtual-thread schedulers, or distributed scheduling are central to the request.
- In baseline review, flag scheduled work without overlap control, idempotency, timeout, retry/backoff, cancellation, observability, and multi-instance behavior.

## Architecture and Modular Boundaries

- For large modular monoliths, check whether package boundaries, domain events, and dependency direction are explicit enough to test. Consider Spring Modulith when module verification, module-level integration tests, generated module documentation, or event publication/outbox support would reduce architecture drift.
- Do not introduce Spring Modulith just to add framework surface area. Use it when the application already has meaningful domain modules or when module-boundary regression tests are a concrete need.
- For public REST APIs, prefer test-generated documentation such as Spring REST Docs when API examples, headers, fields, and error contracts must stay synchronized with tests.

## High Traffic and Distributed Systems

- Use circuit breakers, bulkheads, rate limiters, and load shedding where dependencies can fail or saturate.
- On Spring Framework 7+, consider `@Retryable` and `@ConcurrencyLimit` for simple method-level resilience, but do not treat them as a replacement for end-to-end circuit breaking, deadlines, idempotency, and backpressure.
- If Spring Cloud Circuit Breaker or Resilience4J is used, verify blocking versus reactive starter choice, timeout and bulkhead semantics, fallback behavior, property precedence, and exported metrics.
- Track p95, p99, and p999 latency, not just averages.
- Size pools explicitly: HTTP client, server threads, database pool, Kafka consumer concurrency, Redis connections, and Reactor schedulers.
- Ensure Kubernetes readiness reflects the ability to serve traffic, liveness reflects recoverability, and startup probes cover slow initialization without masking real deadlocks.
- Do not include shared external systems such as databases, Web APIs, or Redis in liveness checks. Include external checks in readiness only when the traffic-routing consequence is understood.
- Check graceful shutdown behavior for web requests, message consumers, scheduled jobs, and in-flight database work, including drain windows and listener/container stop ordering.

## Observability and Operations

- Add actuator endpoints, metrics, tracing, structured logs, and correlation IDs.
- Secure management endpoints and limit exposed actuator endpoints.
- Export Micrometer and OpenTelemetry signals using platform conventions.
- Define observation conventions and context propagation across HTTP, messaging, scheduler, async, and reactive boundaries. Avoid duplicate auto-instrumentation.
- Define SLO dashboards and alerts for latency, errors, saturation, and queue lag.
- Watch metric cardinality, especially labels derived from user input, URLs, tenant IDs, error messages, or exception details.
- Verify that handled exceptions are visible in logs/metrics/traces when they affect user-visible behavior.

## TLS and Certificates

- Use Spring Boot SSL bundles where they reduce duplicated trust-store configuration across clients and servers.
- Never disable certificate validation outside explicitly scoped local tests.

## Testing

- Use Spring Boot slice tests for web, repository/data, serialization, and other framework slices; test service logic with unit tests or narrow Spring integration tests when Spring infrastructure is part of the behavior.
- Prefer Spring's test support, including TestContext, MockMvc, WebTestClient, and Spring Boot test slices, over ad hoc integration harnesses.
- Use Testcontainers for integration tests with real databases, Redis, Kafka, and dependent infrastructure.
- Use `@ServiceConnection` when supported to reduce brittle property wiring.
- Use embedded Kafka carefully. Avoid mixing global embedded brokers with per-test brokers.
- Include failure-mode tests for duplicate requests, retry after timeout, broker outage, database deadlock, lock timeout, cache miss, stale cache, scheduler overlap, expired lock release, consumer replay, authorization denial, and graceful shutdown.

## Immediate Anti-Patterns

Flag these immediately:

- WebFlux with JPA or JDBC used as if the whole stack were non-blocking.
- Kafka exactly-once claims while writing to an external database or API without idempotency or a transactionally coordinated sink.
- Redis lock used as a correctness boundary without fencing.
- Horizontally scaled `@Scheduled` work with no stated overlap, partitioning, or single-run policy.
- Broad `@Transactional` methods that include HTTP calls, Kafka sends, or slow I/O.
- Email, webhook, payment, or file side effects emitted inside database transactions without idempotency or recovery design.
- Unbounded retries or retries without jitter.
- Missing timeout settings for HTTP, database, Redis, Kafka, or gRPC clients.
- Spring Projects in the Attic proposed for a new design without a migration or compatibility reason.
- Eager JPA associations by default.
- N+1 hidden behind repository methods.
- Flyway or Liquibase mixed with Hibernate production DDL generation.
- Actuator endpoints exposed without security.
- No readiness and liveness separation.
- Dependency versions overridden outside the Spring Boot BOM without compatibility evidence.
- Public endpoints added outside a deny-by-default security posture.
