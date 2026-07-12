# Test Gap Playbook

## Risk-to-test mapping

- Domain invariants and pure transformations: framework-free unit/property tests.
- MVC/WebFlux binding, validation, security filters, serialization: the matching web slice plus focused security assertions.
- JPA/JDBC/R2DBC mapping, queries, constraints, isolation: data slice against the production database engine/version where semantics matter.
- Boot wiring, configuration, transactions across components: focused integration or module tests.
- HTTP/event/schema compatibility: consumer/provider contract and backward/forward compatibility tests.
- Retries, duplicates, ordering, timeouts, partial failure: deterministic failure injection and idempotency assertions.
- Database/config/framework migrations: rehearsal from a production-shaped snapshot or generated representative dataset, including rollback constraints.
- Capacity and latency SLOs: controlled load tests with saturation and tail-latency measurements.

## Anti-pattern checks

- Tests that assert implementation calls but not observable behavior.
- Full-context tests used for logic that needs no Spring container.
- H2 used as proof of vendor-specific SQL, locking, isolation, or migration behavior.
- Random sleeps for asynchronous assertions.
- Shared mutable fixtures, implicit test order, external network dependence, and unpinned container images.
- Coverage gates with no mutation, branch, contract, or failure-mode evidence for critical logic.

## Framework boundary caveats

- A `@SpringBootTest` using a real server such as `RANDOM_PORT` handles server work in a different transaction from the test thread; do not assume test rollback undoes server-side database changes.
- Test-managed transactions do not cover every propagation mode, and preemptive timeout mechanisms can run assertions outside the transaction-owning thread.
- Flush JPA/Hibernate state before assertions when database constraints or generated SQL are the behavior under test; otherwise a test can pass before the database reports the failure.
- Test-managed `@Transactional` supports only a subset of production transaction attributes; do not assume isolation, timeout, read-only, or exception rollback rules are reproduced.
- MockMvc verifies MVC behavior without a running server; it is not proof of container, socket, proxy, or real-client behavior.
- Testcontainers' JUnit 5 extension documents parallel execution as unsupported; design shared-container lifecycle and CI concurrency explicitly.

## Backlog item

Record risk, behavior, proposed test level, fixture, dependency fidelity, failure injection, assertion, CI stage, estimated runtime, flakiness control, and owner.
