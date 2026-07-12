# Spring Kafka Review Rules

Load when Kafka producer, consumer, transaction, ordering, retry, or delivery semantics are in scope.

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

## Kafka Security

- Review client, broker-to-broker, controller, and administrative traffic paths separately. Require authenticated, encrypted connections for every untrusted network path; do not infer that securing the client listener also secures inter-broker or controller traffic.
- Verify TLS trust, hostname verification, certificate lifecycle, and protocol/cipher policy. Do not disable endpoint identification or certificate verification as a production workaround.
- Match the SASL mechanism to the threat model. Use SASL/PLAIN only over TLS; for SCRAM, Kerberos, OAuth, or custom callbacks, verify server-side validation, principal mapping, expiry, rotation, and failure behavior.
- Enforce least-privilege ACLs for topics, consumer groups, transactional IDs, clusters, and administrative operations. Keep `allow.everyone.if.no.acl.found` disabled unless unrestricted fallback is an explicit, reviewed policy.
- Minimize and tightly control `super.users` membership because it bypasses authorizer checks. Separately grant broker and controller principals only their required ACLs. In KRaft, verify authorization of forwarded administrative requests and require a custom principal builder crossing the broker-controller boundary to implement `KafkaPrincipalSerde`.
- Keep credentials, JAAS content, tokens, and private keys outside source and rendered findings. Verify secret injection, rotation, revocation, and client/broker reload or reconnect behavior without exposing secret values.
