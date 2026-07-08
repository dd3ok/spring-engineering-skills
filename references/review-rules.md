# Spring Boot Review Rules

Use these rules for Spring Boot architecture reviews, code reviews, migration reviews, and production-readiness checks.

## Contents

- Version and Dependency Management
- MVC, WebFlux, and Threads
- API and HTTP Clients
- Security
- Transactions, Concurrency, and Idempotency
- Data Access
- Spring Data JDBC and Relational
- JPA and Hibernate
- Kafka and Messaging
- Redis and Caching
- Architecture and Modular Boundaries
- High Traffic and Distributed Systems
- Observability and Operations
- gRPC, TLS, and Protocol-Specific Concerns
- Testing
- Immediate Anti-Patterns

## Version and Dependency Management

- Use Spring Boot BOM-managed dependency versions by default.
- For new applications, prefer Spring Initializr and a minimal starter set over hand-assembling Spring dependencies.
- Treat auto-configuration as the default, but verify selected starters match the runtime model before approving them.
- Do not override Spring Framework, Spring Data, Reactor, Kafka, Hibernate, Micrometer, Spring Security, or Spring Cloud versions without verified compatibility evidence.
- Match the Spring Cloud release train to the Spring Boot minor line. Check the Spring Cloud compatibility table for the exact supported range.
- Before a major upgrade, first move to the latest patch version of the current major/minor line and remove deprecated APIs and properties.
- For Spring Boot 4.x migrations, start from the latest 3.5.x line, review the Boot 4 migration guide and release notes, and verify Java 17+, Kotlin 2.2+, GraalVM 25+, Maven/Gradle requirements, Jakarta EE 11, Servlet 6.1, Spring Framework 7.x, Jackson 3, modularized starters/modules, and removed features such as Undertow support.
- For version and security checks, start with official release highlights, generation compatibility/support pages, and Spring security advisories before relying on blog posts or transitive dependency scanners alone.
- Treat native-image, AOT, CRaC, and checkpoint/restore guidance as deployment-specific. Do not recommend them unless startup time, memory footprint, packaging, or platform requirements justify the tradeoff.

## MVC, WebFlux, and Threads

- Default to Spring MVC for blocking CRUD APIs, JPA/Hibernate, JDBC, traditional servlet filters, and simple request/response services.
- Choose WebFlux only when the runtime path is genuinely non-blocking end to end, or when streaming, backpressure, or high-concurrency I/O workloads justify it.
- If both `spring-boot-starter-web` and `spring-boot-starter-webflux` are present, treat MVC as the default runtime unless the application explicitly configures a reactive application type.
- Never block Reactor event-loop threads. Isolate unavoidable blocking calls with `Schedulers.boundedElastic()` and test with BlockHound where appropriate.
- Do not present WebFlux as a performance fix for blocking database calls.
- Treat virtual threads as an option for blocking workloads, not a substitute for non-blocking design. Verify Java version and `spring.threads.virtual.enabled` behavior before recommending them.

## API and HTTP Clients

- Prefer explicit API versioning through path, header, query parameter, or media type strategies.
- Prefer RFC 9457 Problem Details for API error responses.
- Avoid suffix-pattern content negotiation.
- Define stable error codes, correlation IDs, and idempotency-key behavior in API contracts.
- Prefer `RestClient` for imperative HTTP client code and `WebClient` for reactive pipelines. Do not use `WebClient` reactively and then immediately block in controllers or hot paths.
- Require explicit connect and read timeouts for every remote call. For modern Boot applications, check whether global `spring.http.clients.*` settings or per-client builders are appropriate.
- For Spring Boot 4.x HTTP Service Clients, verify group-specific `spring.http.serviceclient.<group>` base URL, timeout, redirect, default header, API versioning, and SSL bundle settings.
- For outbound calls influenced by user-controlled URLs or hosts, review SSRF controls such as host allowlists, redirect behavior, proxy behavior, DNS/private-address handling, and Spring Boot `InetAddressFilter` support where applicable.
- Bound retries and use exponential backoff with jitter. Retry only when idempotency or compensating logic exists.

## Security

- Prefer deny-by-default authorization: explicitly permit public endpoints and protect everything else.
- Verify actuator endpoint exposure, authentication, authorization, network reachability, and sensitive endpoint access.
- Do not assume method-level authorization is active just because Spring Security is on the classpath. Check for explicit method-security enablement when service-layer authorization matters.
- Keep CSRF enabled for browser/session-backed state-changing flows. Disable it only for stateless APIs or protocols where it is incompatible, and document why.
- For OAuth2 resource servers, verify issuer/JWKS/introspection configuration, token audience/issuer validation, clock skew handling, and multi-tenant token validation if applicable.
- Avoid leaking authorization failure details in API responses. Prefer logs, audit events, and correlation IDs for diagnosis.

## Transactions, Concurrency, and Idempotency

- Keep transactions short and local to one consistency boundary.
- Account for Spring rollback defaults: unchecked exceptions and `Error` roll back by default; checked exceptions need explicit rollback rules unless the project has changed rollback semantics.
- Avoid `REQUIRES_NEW` in loops or hot paths unless the connection pool is sized for nested transactions.
- Use optimistic locking with `@Version` for aggregate updates where lost updates are possible.
- Use pessimistic locks only for short critical sections and only when deadlock and retry behavior are handled explicitly.
- Require an idempotency key for externally retried commands and persist request state or result under a unique constraint.
- Do not keep database transactions open across HTTP calls, Kafka sends that may block, long computation, or slow I/O.

## Data Access

- Use JPA for aggregate persistence and object mapping.
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

## Redis and Caching

- Use Redis cache for shared, short-lived, invalidatable data. Use local Caffeine for hot per-instance cache when appropriate.
- Specify TTLs, key prefixes, serializers, and cache-null behavior deliberately.
- Do not accept Redis cache defaults blindly: default cache entries have no expiration, values use JDK serialization, and cache clearing can use `KEYS` unless configured otherwise.
- Avoid Java native serialization for untrusted data. Prefer JSON or another explicit serialization format.
- Treat `RedisTemplate` as thread-safe, but do not assume low-level `RedisConnection` instances are generally thread-safe.
- Do not use Redis distributed locks for correctness-critical mutual exclusion unless fencing tokens or a stronger consensus or transactional mechanism protects the resource.
- Review cache stampede, hot keys, large values, eviction policy, and memory growth before high-traffic launch.
- For time-to-idle behavior, verify Redis server command support and consistent access paths.

## Architecture and Modular Boundaries

- For large modular monoliths, check whether package boundaries, domain events, and dependency direction are explicit enough to test. Consider Spring Modulith when module verification, module-level integration tests, generated module documentation, or event publication/outbox support would reduce architecture drift.
- Do not introduce Spring Modulith just to add framework surface area. Use it when the application already has meaningful domain modules or when module-boundary regression tests are a concrete need.
- For public REST APIs, prefer test-generated documentation such as Spring REST Docs when API examples, headers, fields, and error contracts must stay synchronized with tests.

## High Traffic and Distributed Systems

- Use circuit breakers, bulkheads, rate limiters, and load shedding where dependencies can fail or saturate.
- On Spring Framework 7+, consider `@Retryable` and `@ConcurrencyLimit` for simple method-level resilience, but do not treat them as a replacement for end-to-end circuit breaking, deadlines, idempotency, and backpressure.
- Track p95, p99, and p999 latency, not just averages.
- Size pools explicitly: HTTP client, server threads, database pool, Kafka consumer concurrency, Redis connections, and Reactor schedulers.
- Ensure Kubernetes readiness reflects the ability to serve traffic and liveness reflects recoverability.
- Check graceful shutdown behavior for web requests, message consumers, scheduled jobs, and in-flight database work.

## Observability and Operations

- Add actuator endpoints, metrics, tracing, structured logs, and correlation IDs.
- Secure management endpoints and limit exposed actuator endpoints.
- Export Micrometer and OpenTelemetry signals using platform conventions.
- Define SLO dashboards and alerts for latency, errors, saturation, and queue lag.
- Watch metric cardinality, especially labels derived from user input, URLs, tenant IDs, error messages, or exception details.
- Verify that handled exceptions are visible in logs/metrics/traces when they affect user-visible behavior.

## gRPC, TLS, and Protocol-Specific Concerns

- For gRPC services, review protobuf evolution rules, deadlines, retry policy, health service, reflection exposure, authentication, authorization, and TLS/mTLS.
- Use Spring Boot SSL bundles where they reduce duplicated trust-store configuration across clients and servers.
- Never disable certificate validation outside explicitly scoped local tests.

## Testing

- Use slice tests for controller, repository, and service isolation.
- Prefer Spring's test support, including TestContext, MockMvc, WebTestClient, and Spring Boot test slices, over ad hoc integration harnesses.
- Use Testcontainers for integration tests with real databases, Redis, Kafka, and dependent infrastructure.
- Use `@ServiceConnection` when supported to reduce brittle property wiring.
- Use embedded Kafka carefully. Avoid mixing global embedded brokers with per-test brokers.
- Include failure-mode tests for duplicate requests, retry after timeout, broker outage, database deadlock, lock timeout, cache miss, stale cache, consumer replay, authorization denial, and graceful shutdown.

## Immediate Anti-Patterns

Flag these immediately:

- WebFlux with JPA or JDBC used as if the whole stack were non-blocking.
- Kafka exactly-once claims while writing to an external database or API without idempotency or a transactionally coordinated sink.
- Redis lock used as a correctness boundary without fencing.
- Broad `@Transactional` methods that include HTTP calls, Kafka sends, or slow I/O.
- Unbounded retries or retries without jitter.
- Missing timeout settings for HTTP, database, Redis, Kafka, or gRPC clients.
- Eager JPA associations by default.
- N+1 hidden behind repository methods.
- Flyway or Liquibase mixed with Hibernate production DDL generation.
- Actuator endpoints exposed without security.
- No readiness and liveness separation.
- Dependency versions overridden outside the Spring Boot BOM without compatibility evidence.
- Public endpoints added outside a deny-by-default security posture.
