# Messaging and Integration Review Rules

Use this file only when RabbitMQ/AMQP, Pulsar, Spring Integration, Spring Cloud Stream, JMS, or complex message-flow design is in scope. Use `review-rules.md` for core Kafka checks first.

## Shared Messaging Rules

- Identify broker, producer, consumer, serialization, schema/versioning, delivery guarantees, ordering keys, retry path, dead-letter path, and idempotency boundary.
- Do not accept "exactly once" claims for external side effects without a transactionally coordinated sink or idempotent consumer.
- Review backpressure, consumer concurrency, partition or queue assignment, replay behavior, and poison-message handling together.
- Require explicit timeouts, retry budgets, jitter, observability, and operational procedures for stuck consumers or growing queues.

## RabbitMQ and AMQP

- Review exchange, queue, binding, routing key, quorum/classic queue choice, durability, TTL, dead-letter exchange, and parking-lot strategy.
- Verify listener container concurrency, prefetch, acknowledgement mode, requeue policy, transactions, and redelivery classification.
- Use publisher confirms and returns where message loss matters. Treat `RabbitTemplate` send success as insufficient durability evidence unless confirms are handled.

## Pulsar and Stream Abstractions

- For Pulsar, review subscription type, ack timeout, negative ack/redelivery, retention, schema compatibility, ordering keys, and backlog growth.
- For Spring Cloud Stream, verify binder-specific semantics. Do not assume Kafka, RabbitMQ, and Pulsar binders provide identical partitioning, retry, DLQ, or transaction behavior.

## Spring Integration

- Model integration flows as explicit message boundaries: channels, gateways, service activators, filters, transformers, aggregators, splitters, pollers, and error channels.
- Review poller rate, transaction advice, error channel routing, wire taps, message store durability, correlation/release strategies, and timeout behavior.
- Keep integration flows testable with clear endpoint contracts. Avoid anonymous flows that hide side effects and retry behavior.

## Immediate Anti-Patterns

- Requeue-on-failure loops without backoff or poison-message escape.
- Unbounded listener concurrency that can overwhelm the database or downstream APIs.
- Binder abstraction used to hide broker-specific delivery, ordering, and transaction semantics.
- Integration flow with no explicit error channel, timeout, or observability for external adapters.
