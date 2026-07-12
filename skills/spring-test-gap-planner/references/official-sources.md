# Official Sources

Checked on: 2026-07-12. These official project documents are normative for the test infrastructure and framework behavior they describe.

Fixed Kafka and Pulsar links below are reviewed examples, not compatibility defaults. Use the deployed broker/client line's matching official documentation for version-specific test semantics.

- [Spring Boot testing](https://docs.spring.io/spring-boot/reference/testing/index.html) and [testing applications](https://docs.spring.io/spring-boot/reference/testing/spring-boot-applications.html) — Boot context and slice-test behavior.
- [Spring Boot test auto-configuration](https://docs.spring.io/spring-boot/appendix/test-auto-configuration/slices.html) — slice contents by annotation.
- [Spring Framework TestContext caching](https://docs.spring.io/spring-framework/reference/testing/testcontext-framework/ctx-management/caching.html) — cache keys, reuse, and invalidation.
- [Spring Framework test-managed transactions](https://docs.spring.io/spring-framework/reference/testing/testcontext-framework/tx.html) — propagation and preemptive-timeout boundaries.
- [Spring Framework MockMvc](https://docs.spring.io/spring-framework/reference/testing/mockmvc.html) — server-side MVC testing scope.
- [Spring Boot Testcontainers](https://docs.spring.io/spring-boot/reference/testing/testcontainers.html) — service connections and lifecycle interaction with cached contexts.
- [Spring Security testing](https://docs.spring.io/spring-security/reference/servlet/test/index.html) — authentication, authorization, CSRF, and MVC support.
- [Spring Cloud Contract](https://docs.spring.io/spring-cloud-contract/reference/) — consumer-driven and producer contract tests.
- [Spring REST Docs](https://docs.spring.io/spring-restdocs/docs/current/reference/htmlsingle/) — documentation driven by verified tests.
- [Testcontainers JUnit 5](https://java.testcontainers.org/test_framework_integration/junit_5/) — container lifecycle and parallel-execution limitation.
- [Apache Kafka 4.3 security](https://kafka.apache.org/43/security/security-overview/) and [ACLs](https://kafka.apache.org/43/security/authorization-and-acls/) — listener authentication, encryption, and resource-authorization test boundaries.
- [RabbitMQ access control](https://www.rabbitmq.com/docs/access-control), [TLS](https://www.rabbitmq.com/docs/ssl), and [confirms/acknowledgements](https://www.rabbitmq.com/docs/confirms) — identity, permission, transport, and delivery-semantics tests.
- [Apache Pulsar 4.1 security](https://pulsar.apache.org/docs/4.1.x/security-overview/) and [authorization](https://pulsar.apache.org/docs/4.1.x/security-authorization/) — default security posture and tenant/namespace/topic permission tests.
- [PostgreSQL client authentication](https://www.postgresql.org/docs/current/auth-pg-hba-conf.html) and [row security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) — ordered access rules, denial cases, and tenant-role isolation tests.
