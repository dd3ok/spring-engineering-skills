# Redis and Cache Review Rules

Use this file only when Redis, Spring Data Redis, Redis-backed cache/session, Redis locks, Redis streams/pubsub, Redis rate limiting, Redis metadata stores, Lettuce, Jedis, Sentinel, Cluster, or managed Redis topology is in scope.

## Decision Surface

- Classify Redis use first: cache, session store, lock or lease, rate-limit counter, deduplication key, metadata store, queue, stream, pub/sub channel, or primary data store.
- Identify the correctness boundary. Redis may reduce duplicate work, latency, or load; it must not become the only guard for money, inventory, entitlement, or once-only external side effects unless the design has fencing, idempotency, or a stronger transactional invariant.
- Define freshness, eviction, persistence, failover, and recovery expectations before approving Redis for anything beyond cache-aside.

## Cache and Data Design

- Specify TTL or TTI, key prefixes, serializers, null-value caching, cache statistics, and clear/eviction strategy per cache.
- Do not accept Redis cache defaults blindly: default entries can have no expiration, null values can be cached, values can use JDK serialization, and cache clearing can use `KEYS` unless a scan strategy is configured.
- Avoid Java native serialization for untrusted data. Prefer explicit JSON, binary, or schema-based serialization with versioning rules.
- For time-to-idle behavior, verify Redis server command support and make sure every access path uses commands that preserve the intended idle-expiration semantics.
- Review cache stampede, hot keys, large values, key cardinality, compression, memory growth, maxmemory policy, and stale-data tolerance.
- For two-level caching, define local-vs-Redis invalidation order, propagation delay, and behavior after partial invalidation failure.

## Locks, Leases, and Coordination

- Use Redis locks for best-effort single-flight work, duplicate scheduled-job reduction, or low-stakes coordination. For correctness-critical mutation, require a database constraint, optimistic or pessimistic lock, fencing token, idempotency record, outbox, or consensus-backed coordinator.
- If implementing a Redis lock directly, acquire with a single atomic `SET key owner NX PX ttl`-style operation and release only when the stored owner value still matches. Do not use separate `SETNX` plus `EXPIRE`, and do not release with unconditional `DEL`.
- Size lock TTL against worst-case work time, network timeout, GC pause, and downstream latency. If renewal is used, set a maximum renewal window and observable failure path.
- Treat expired-lock release, lock ownership mismatch, or lock timeout as a possible integrity signal, not just a warning.
- Use random backoff under contention and expose metrics for lock wait time, acquire failure, renewal failure, expired release, and protected-operation duration.
- Do not assume Redis master-replica failover preserves mutual exclusion. If Redlock or a similar algorithm is used, verify independent masters, majority acquisition, bounded clock drift assumptions, client-side timeouts, and behavior when work exceeds the remaining validity window.
- Prefer a maintained library or Spring Integration `RedisLockRegistry` over a handwritten lock when the semantics match. Still review TTL, renewal, failure, and unlock-after-expiry behavior.

## Spring Session and Integration

- For Spring Session backed by Redis, review TTL, cookie flags, serializer, session fixation protection, concurrent session rules, WebSocket/WebSession behavior, failover, and cross-region assumptions.
- For Spring Integration Redis stores, queues, streams, or metadata stores, review serializer choice, acknowledgement, retry/error channel behavior, atomicity limits, and cluster compatibility.
- Do not hide workflow durability requirements inside Redis pub/sub. Use streams, a broker, outbox, or durable queue when replay, acknowledgement, and operator recovery matter.

## Topology and Client Behavior

- Verify topology explicitly: standalone, Sentinel, Cluster, managed Redis, cross-AZ, cross-region, persistence, backup/restore, failover time, and client routing behavior.
- Check Lettuce versus Jedis capability differences, especially reactive support, cluster behavior, pooling, native connection sharing, pub/sub, pipelining, transactions, and unsupported command behavior.
- Treat `RedisTemplate` as thread-safe after configuration, but do not assume low-level `RedisConnection` instances are generally thread-safe; check connector-specific behavior before sharing native connections.
- Configure command timeout, connect timeout, SSL/TLS, authentication/ACLs, pool or multiplexing strategy, retry policy, and client metrics deliberately.
- For Redis Cluster, review key tags for multi-key operations and avoid assuming Lua, transactions, or WATCH-style atomicity works across slots.

## Testing and Operations

- Use Testcontainers or real infrastructure for cache, lock, stream, Sentinel, Cluster, and failover paths when behavior matters.
- Test crashed lock holder, slow holder, expired lock, duplicate request, Redis restart, failover, network timeout, cache miss, stale cache, large keyspace clear, and high-contention lock acquisition.
- Monitor command latency, errors, reconnects, pool saturation, memory, evictions, keyspace growth, hot keys, replication lag, stream lag, and lock contention.

## Immediate Anti-Patterns

- Redis lock used as the only correctness boundary for financial, inventory, entitlement, or externally visible once-only effects.
- Handwritten lock using `SETNX` then `EXPIRE`, or unconditional `DEL` on release.
- Cache without TTL, key prefix, serializer choice, or invalidation path.
- Large cache clear using `KEYS` in a production-sized keyspace.
- Pub/sub used where replay, acknowledgement, or durable recovery is required.
- Redis Cluster adopted without reviewing multi-key, scripting, transaction, and key-slot constraints.
