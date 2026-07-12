# PostgreSQL Review Rules

Use this file when PostgreSQL behavior or operations are material. Identify the deployed server, driver, pooler, and extension versions and use matching official documentation.

## Transactions and Concurrency

- Review isolation level, transaction duration, `idle_in_transaction_session_timeout`, `statement_timeout`, `lock_timeout`, deadlock retry, and application cancellation together.
- Treat long transactions and long-lived snapshots as vacuum, bloat, replica-lag, and transaction-ID-wraparound risks, not only connection-pool occupancy.
- Inspect explicit and implicit lock acquisition for DDL, foreign keys, hot updates, queue tables, and migrations. Require bounded waits and a retry or abort policy.
- Do not assume read replicas provide read-after-write consistency. Document routing, lag tolerance, and failover behavior.

## Queries, Plans, and Indexes

- Require representative SQL, parameters, data cardinality, and the target PostgreSQL version before approving an execution-plan claim.
- Use `EXPLAIN (ANALYZE, BUFFERS)` only in a safe environment or with an explicitly bounded production procedure; it executes the statement.
- Review row-estimate errors, scan, join and sort strategies, temporary I/O, returned rows, and lock waits. Validate index benefit against write amplification and maintenance cost.
- Use `pg_stat_statements` or equivalent normalized workload evidence for hot-query prioritization, treating query text and retention as sensitive operational data.

## Vacuum, Capacity, and Connections

- Review autovacuum thresholds and scale factors, table churn, dead tuples, freeze age, transaction-ID age, long snapshots, and maintenance capacity for high-write tables.
- Calculate connection demand across replicas, jobs, consumers, administration, failover, and rollout overlap. Align HikariCP and any external pooler with PostgreSQL capacity.
- With PgBouncer or another pooler, verify session versus transaction pooling compatibility with prepared statements, session state, advisory locks, temporary objects, and driver behavior.

## Security and Tenant Isolation

- Require TLS for untrusted network paths and verify the server identity with a trusted CA and hostname validation (for libpq-style clients, `verify-full` semantics). Do not treat encryption without identity verification as protection from an active intermediary.
- Review `pg_hba.conf` as an ordered first-match policy. Reject broad `trust` rules and weak fallback entries; constrain database, role, address, TLS state, and authentication method, then test both intended access and denial cases after reload.
- Prefer `scram-sha-256` for password authentication. Treat PostgreSQL 18's deprecated MD5 password authentication and stored MD5 hashes as a migration risk; inventory client support, change `password_encryption`, rotate stored passwords, then update `pg_hba.conf` with rollback and denial tests.
- For pgJDBC, distinguish `ssl=true` (server-certificate and hostname verification) from `sslmode=require` (encryption without server identity validation). Verify the actual driver version, trust material, and connection properties.
- Use separate login and owner roles where practical, grant least privilege, and review schema `USAGE`, object privileges, ownership, role inheritance, and default privileges for objects created later.
- For `SECURITY DEFINER` functions, pin a safe `search_path` with trusted schemas first and `pg_temp` last, revoke unintended `PUBLIC` execution, and qualify security-sensitive objects.
- Treat row-level security as defense in depth, not a superuser boundary: superusers and roles with `BYPASSRLS` always bypass policies. Table owners normally bypass policies; `FORCE ROW LEVEL SECURITY` can make the owner subject to them. Review permissive-policy OR and restrictive-policy AND composition, separate `USING` visibility from `WITH CHECK` writes, and cover operations such as `TRUNCATE` and `REFERENCES` that RLS does not govern. Test deployed application, owner, migration, and maintenance roles.
- Verify password, certificate, and secret rotation through the JDBC pool and any external pooler, including connection lifetime, reconnect, revocation, and failover behavior without logging credentials.

## Schema Change and Recovery

- Review DDL lock levels, rewrite behavior, concurrent-index constraints, timeouts, replication lag, disk/log growth, and cancellation for every production migration.
- Use expand/contract changes for rolling deployments and run backfills as restartable, throttled jobs with progress and pause controls.
- Test backup restore, point-in-time recovery, replica promotion, connection re-resolution, and application recovery rather than treating replication as backup.
