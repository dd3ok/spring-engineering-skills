# Official Documentation Source Map

Use this map to start source checks. Prefer the latest official docs for the target version, and switch to versioned docs when reviewing an older application.

## Spring Boot

- System requirements: https://docs.spring.io/spring-boot/system-requirements.html
- Upgrading Spring Boot: https://docs.spring.io/spring-boot/upgrading.html
- Spring Boot 4.0 migration guide: https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide
- Spring Boot 4.0 release notes: https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Release-Notes
- Build systems and dependency management: https://docs.spring.io/spring-boot/reference/using/build-systems.html
- Externalized configuration: https://docs.spring.io/spring-boot/reference/features/external-config.html
- JSON and Jackson migration: https://docs.spring.io/spring-boot/reference/features/json.html
- Jackson 3 support in Spring: https://spring.io/blog/2025/10/07/introducing-jackson-3-support-in-spring
- Task execution, scheduling, and virtual threads: https://docs.spring.io/spring-boot/reference/features/task-execution-and-scheduling.html
- Servlet web applications: https://docs.spring.io/spring-boot/reference/web/servlet.html
- Reactive web applications: https://docs.spring.io/spring-boot/reference/web/reactive.html
- Graceful shutdown: https://docs.spring.io/spring-boot/reference/web/graceful-shutdown.html
- REST clients and HTTP client settings: https://docs.spring.io/spring-boot/reference/io/rest-client.html
- HTTP client SSRF filter API: https://docs.spring.io/spring-boot/4.1.0/api/java/org/springframework/boot/http/client/InetAddressFilter.html
- SQL databases: https://docs.spring.io/spring-boot/reference/data/sql.html
- Kafka support: https://docs.spring.io/spring-boot/reference/messaging/kafka.html
- Caching: https://docs.spring.io/spring-boot/reference/io/caching.html
- gRPC: https://docs.spring.io/spring-boot/reference/io/grpc.html
- SSL bundles: https://docs.spring.io/spring-boot/reference/features/ssl.html
- Testcontainers: https://docs.spring.io/spring-boot/reference/testing/testcontainers.html
- Actuator endpoints: https://docs.spring.io/spring-boot/reference/actuator/endpoints.html
- Observability: https://docs.spring.io/spring-boot/reference/actuator/observability.html
- Metrics: https://docs.spring.io/spring-boot/reference/actuator/metrics.html
- Tracing: https://docs.spring.io/spring-boot/reference/actuator/tracing.html
- Native images: https://docs.spring.io/spring-boot/reference/packaging/native-image/introducing-graalvm-native-images.html
- Spring Boot project page and release notes entry point: https://spring.io/projects/spring-boot

## Spring Framework

- Transaction rollback rules: https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/rolling-back.html
- `@Transactional` usage: https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html
- Programmatic transactions: https://docs.spring.io/spring-framework/reference/data-access/transaction/programmatic.html
- RFC 9457 error responses for MVC: https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-ann-rest-exceptions.html
- RFC 9457 error responses for WebFlux: https://docs.spring.io/spring-framework/reference/web/webflux/ann-rest-exceptions.html
- WebFlux overview and performance tradeoffs: https://docs.spring.io/spring-framework/reference/web/webflux/new-framework.html
- WebClient: https://docs.spring.io/spring-framework/reference/web/webflux-webclient.html
- REST clients: https://docs.spring.io/spring-framework/reference/integration/rest-clients.html
- Resilience features: https://docs.spring.io/spring-framework/reference/core/resilience.html

## Spring Cloud

- Spring Cloud project and Spring Boot compatibility table: https://spring.io/projects/spring-cloud
- Supported versions wiki: https://github.com/spring-cloud/spring-cloud-release/wiki/Supported-Versions

## Spring Security

- Security reference index: https://docs.spring.io/spring-security/reference/index.html
- Spring Security migration guide: https://docs.spring.io/spring-security/reference/migration/index.html
- Deny-by-default guidance in anonymous authentication: https://docs.spring.io/spring-security/reference/servlet/authentication/anonymous.html
- HTTP request authorization: https://docs.spring.io/spring-security/reference/servlet/authorization/authorize-http-requests.html
- Method security: https://docs.spring.io/spring-security/reference/servlet/authorization/method-security.html
- CSRF: https://docs.spring.io/spring-security/reference/servlet/exploits/csrf.html
- OAuth2 resource server: https://docs.spring.io/spring-security/reference/servlet/oauth2/resource-server/index.html
- Password storage: https://docs.spring.io/spring-security/reference/features/authentication/password-storage.html

## Data Access

- Spring Data JPA reference: https://docs.spring.io/spring-data/jpa/reference/index.html
- Spring Data JPA projections: https://docs.spring.io/spring-data/jpa/reference/repositories/projections.html
- Spring Data JPA query methods and entity graphs: https://docs.spring.io/spring-data/jpa/reference/jpa/query-methods.html
- Hibernate ORM user guide: https://docs.hibernate.org/orm/current/userguide/html_single/
- jOOQ manual: https://www.jooq.org/doc/latest/manual/

## Messaging, Reactor, and Redis

- Spring Kafka transactions: https://docs.spring.io/spring-kafka/reference/kafka/transactions.html
- Spring Kafka filtering and idempotent receiver pattern: https://docs.spring.io/spring-kafka/reference/kafka/receiving-messages/filtering.html
- Reactor schedulers: https://projectreactor.io/docs/core/release/reference/coreFeatures/schedulers.html
- Spring Data Redis drivers and connection thread-safety: https://docs.spring.io/spring-data/redis/reference/redis/drivers.html
- Spring Data Redis cache TTL/TTI: https://docs.spring.io/spring-data/redis/reference/redis/redis-cache.html
- Spring Data Redis template and serialization: https://docs.spring.io/spring-data/redis/reference/redis/template.html
- Redis distributed locks: https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/
- Redis stampede/thundering herd guidance: https://redis.io/blog/how-to-tame-the-thundering-herd-problem/

## Distributed Systems Background

- AWS Builders' Library: https://aws.amazon.com/builders-library/
- The Tail at Scale: https://research.google/pubs/the-tail-at-scale/
- Martin Kleppmann on Redis distributed locking and fencing: https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html

## Routing Hints

- For version upgrades, start with Spring Boot system requirements, release notes, Spring Cloud compatibility, and migration guides.
- For WebFlux questions, check Spring Boot reactive web docs, Spring Framework WebFlux docs, and Reactor schedulers.
- For API error contracts, check Spring Framework RFC 9457 pages and the RFC itself.
- For Kafka plus database atomicity, check Spring Kafka transactions and idempotent receiver docs, then review outbox alternatives.
- For Redis locks, check both Redis official docs and the fencing-token critique before making correctness claims.
- For security reviews, check Spring Security authorization, CSRF, OAuth2 resource server, and method-security docs.
