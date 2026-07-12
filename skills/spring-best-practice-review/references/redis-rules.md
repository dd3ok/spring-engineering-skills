# Redis Review Rules

Use this file when Redis is central to cache correctness, topology, locks, rate limiting, streams, pub/sub, sessions, failover, or performance.

## Cache Policy

- Specify TTLs, key prefixes, serializers, cache-null behavior, invalidation ownership, and cache warming deliberately.
- Do not accept Redis cache defaults blindly: default cache entries have no expiration, values use JDK serialization, and cache clearing can use `KEYS` unless configured otherwise.
- Avoid Java native serialization for untrusted data. Prefer JSON or another explicit serialization format with schema/version handling.
- Review cache stampede, hot keys, large values, eviction policy, memory growth, and local-plus-remote cache interaction before high-traffic launch.
- For time-to-idle behavior, verify Redis server command support and consistent access paths.

## Connection and Topology

- Treat a fully configured `RedisTemplate` as thread-safe; do not mutate serializers or other configuration at runtime, and do not assume low-level `RedisConnection` instances are generally thread-safe.
- If Redis is more than a cache-aside store, verify topology and failover explicitly: standalone plus Sentinel, Cluster, managed service behavior, persistence, eviction policy, connection pooling or multiplexing, and client retry behavior.
- Check command timeout, socket timeout, pool limits, multiplexing behavior, reconnect policy, TLS, authentication, ACLs, and client metrics.
- Verify cluster key tags and multi-key operations when Redis Cluster is used.

## Locks and Correctness

- Do not use Redis distributed locks for correctness-critical mutual exclusion unless fencing tokens or a stronger consensus or transactional mechanism protects the resource.
- If Redis locks are accepted for best-effort coordination, verify lock TTL, renewal, owner token release, clock assumptions, operation timeout, crash behavior, and idempotency.
- Do not treat Redlock as a consensus substitute without explicitly accepting its assumptions and failure model.

## Rate Limiting, Sessions, Streams, and Pub/Sub

- For rate limiting, define identity key, window algorithm, burst behavior, clock source, fail-open/fail-closed policy, and cross-region behavior.
- For Spring Session backed by Redis, verify TTL, serialization, cookie flags, concurrent sessions, WebSocket/WebSession behavior, and cross-region failure modes.
- For Redis Streams, review consumer groups, pending entry list handling, acknowledgement, replay, trimming, idempotency, and poison-message handling.
- For pub/sub, treat delivery as ephemeral unless the design explicitly tolerates message loss and subscriber downtime.

## Operations

- Monitor latency, command timeout, reconnects, rejected connections, memory, evictions, key count, hot keys, slow log, replication lag, failover events, and client-side pool saturation.
- Define operational procedures for failover, cache flush, schema/serializer migration, keyspace growth, and stale or poisoned entries.
