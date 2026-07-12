# Spring Transaction and Data Review Rules

Load for transaction, concurrency, JDBC, R2DBC, Spring Data JDBC, JPA, or Hibernate review.

## Transactions, Concurrency, and Idempotency

- Account for Spring rollback defaults: unchecked exceptions and `Error` roll back by default; checked exceptions need explicit rollback rules unless the project has changed rollback semantics. On Spring Framework 6.2+, evaluate `@EnableTransactionManagement(rollbackOn = ALL_EXCEPTIONS)` for consistent behavior, particularly for Kotlin, and verify intentional commit-on-exception cases before adopting it.
- Verify that a rollback-triggering exception escapes the advised call or that code explicitly marks the transaction rollback-only. Catching and swallowing an exception does not trigger automatic rollback.
- Verify that transactional calls cross an initialized Spring proxy. In default proxy mode, self-invocation, constructor or `@PostConstruct` calls, and calls on unmanaged objects do not receive transactional interception; test rollback on the real call path.
- Match the transaction manager and method return type to the programming model. Imperative transactions are thread-bound and do not propagate to newly started threads; reactive transactions require a `ReactiveTransactionManager` and the same Reactor context and reactive pipeline.
- Review propagation, isolation, timeout, `readOnly`, transaction-manager selection, rollback rules, and transaction-bound events as behavior, not decorative annotations.
- Avoid `REQUIRES_NEW` in loops or hot paths. It retains the outer transaction's resources while acquiring an independent connection and can exhaust or deadlock the pool; when it is unavoidable, size the pool above concurrent outer transactions by at least one connection and test the actual nesting and concurrency.
- Use optimistic locking with `@Version` for aggregate updates where lost updates are possible.
- Use pessimistic locks only for short critical sections and only when deadlock and retry behavior are handled explicitly.
- Require an idempotency key for externally retried commands and persist request state or result under a unique constraint.
- Do not keep database transactions open across HTTP calls, Kafka sends that may block, long computation, or slow I/O.

## Data Access

- Prefer JPA when aggregate mapping, identity, unit-of-work semantics, and ORM lifecycle behavior fit the domain.
- Prefer `JdbcClient` or `JdbcTemplate` for SQL-heavy, bulk, reporting, or simple explicit data-access paths.
- Use jOOQ when type-safe SQL and schema-driven code generation matter, subject to Java-version and license constraints.
- Use R2DBC only for reactive database access in a fully reactive path.
- Keep Spring Data repository interfaces narrow. Use derived queries for simple predicates and explicit `@Query` or custom repository code when intent, performance, or query shape would otherwise be hidden.
- Enable Spring Data auditing deliberately. Verify who supplies auditor identity, how timestamps are set, and whether audit metadata is part of the domain contract.
- Use exactly one schema-management mechanism in production, preferably Flyway or Liquibase.
- Do not rely on Hibernate `ddl-auto` or `import.sql` for production schema evolution.
- For production schema changes, review expand/contract compatibility across rolling deployments: additive columns/tables first, dual-read/write if needed, backfill separately, then remove old fields only after all versions are drained.
- Avoid long blocking DDL on hot tables unless the database engine, lock behavior, timeout, and rollback plan are verified.
- Treat data backfills as batch or operational jobs with idempotency, restartability, metrics, and throttling.

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
