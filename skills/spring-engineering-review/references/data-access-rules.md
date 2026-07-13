# Data Access Strategy Review Rules

Use this file only for jOOQ, Spring Data NoSQL, Spring Data REST, or broad data-access strategy reviews beyond the core JPA/JDBC/R2DBC rules.

Also select the `postgresql` route defined in `SKILL.md` when PostgreSQL-specific MVCC, vacuum, locks, plans, replication, pooling, or schema operations are material.

## Strategy Selection

- Keep baseline JPA, JDBC, and R2DBC selection in the `transaction-data` route defined in `SKILL.md`.
- In this file, focus on deltas: jOOQ for type-safe SQL/schema-driven generation, NoSQL when the store matches the aggregate/query model, and Spring Data REST when repository exposure becomes an API surface.

## jOOQ

- Verify code generation source, migration ordering, generated-source check-in policy, dialect, naming strategy, and regeneration in CI; fail when generated classes drift from the migrated schema.
- Keep jOOQ transaction boundaries aligned with Spring transaction management. Do not mix unmanaged `DSLContext` use with repository transactions casually.
- Review mapping, optimistic locking, batch statements, fetch size, streaming, SQL logging, and N+1-equivalent query loops.
- Check edition and license constraints before recommending commercial-only features.

## Spring Data NoSQL

- For MongoDB, Elasticsearch, Cassandra, Neo4j, and similar stores, review data model, indexes, query patterns, consistency, transactions, paging, schema evolution, and operational limits.
- Verify repository abstractions do not hide expensive queries, unbounded scans, cross-partition access, or eventual consistency.
- For reactive NoSQL drivers, apply the same no-blocking and backpressure rules used for WebFlux.

## Spring Data REST

- Treat repository exposure as public API generation. Review authorization, projections, excerpts, validation, pagination, sorting, event handlers, and accidental entity exposure.
- Prefer explicit controllers when API shape, security, or workflow semantics matter.
