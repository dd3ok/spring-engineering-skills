# Messaging and Integration Review Rules

Use this file only when RabbitMQ/AMQP, Pulsar, Spring Integration, Spring Cloud Stream, JMS, or complex message-flow design is in scope. Use `kafka-rules.md` when Kafka is also in scope.

## Shared Messaging Rules

- Identify broker, producer, consumer, serialization, schema/versioning, delivery guarantees, ordering keys, retry path, dead-letter path, and idempotency boundary.
- Do not accept "exactly once" claims for external side effects without a transactionally coordinated sink or idempotent consumer.
- Review backpressure, consumer concurrency, partition or queue assignment, replay behavior, and poison-message handling together.
- Require explicit timeouts, retry budgets, jitter, observability, and operational procedures for stuck consumers or growing queues.
- Review transport encryption, peer verification, client authentication, resource-level authorization, secret storage, rotation, revocation, and reconnect/reload behavior for every producer, consumer, broker, proxy, and administrative path.

## RabbitMQ and AMQP

- Review exchange, queue, binding, routing key, quorum/classic queue choice, durability, TTL, dead-letter exchange, and parking-lot strategy.
- Verify listener container concurrency, prefetch, acknowledgement mode, requeue policy, transactions, and redelivery classification.
- Use publisher confirms to establish broker acceptance. When unroutable messages must be detected, enable mandatory publishing and handle returned messages; returns do not replace confirms. Treat `RabbitTemplate` send success alone as insufficient durability evidence.
- Require TLS with peer verification across untrusted paths and use a production identity other than the default `guest` account. Scope each identity to the required virtual host and minimum configure/write/read permissions; treat management tags as UI/API access controls, not messaging-resource permissions.
- Verify credential or certificate rotation and revocation through client reconnects because permission changes may be cached per connection or channel.

## Pulsar and Stream Abstractions

- For Pulsar, review subscription type, ack timeout, negative ack/redelivery, retention, schema compatibility, ordering keys, and backlog growth.
- Verify the Spring Pulsar, Pulsar client, broker, and Spring Boot compatibility lines. For Boot 4 migrations, check the removal of reactive Pulsar client dependency management and auto-configuration before approving an existing plan.
- For Spring Cloud Stream, verify binder-specific semantics. Do not assume Kafka, RabbitMQ, and Pulsar binders provide identical partitioning, retry, DLQ, or transaction behavior.
- Pulsar security is not on by default: require TLS plus authentication and authorization unless a documented trusted-network boundary provides equivalent containment. Verify client-to-proxy, proxy-to-broker, broker-to-broker, and administrative paths independently.
- Grant roles at the minimum tenant, namespace, and topic scope; minimize superusers and tenant admins. For tokens or certificates, review expiry, rotation, revocation, trust stores, proxy credential forwarding, and broker re-authentication of the original client identity.
- When deployed, review broker-to-BookKeeper/storage and metadata-store transport and identities, plus Functions/IO worker and connector credentials, authorization, secret injection, and rotation as separate trust boundaries.

## Spring Integration

- Model integration flows as explicit message boundaries: channels, gateways, service activators, filters, transformers, aggregators, splitters, pollers, and error channels.
- Review poller rate, transaction advice, error channel routing, wire taps, message store durability, correlation/release strategies, and timeout behavior.
- Keep integration flows testable with clear endpoint contracts. Avoid anonymous flows that hide side effects and retry behavior.
