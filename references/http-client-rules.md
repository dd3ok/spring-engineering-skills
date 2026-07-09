# HTTP Client and Service-to-Service Review Rules

Use this file when `RestClient`, `WebClient`, HTTP Service Clients, Feign/OpenFeign, Reactor Netty, service-to-service calls, SSRF, retries, deadlines, or outbound API reliability is in scope.

## Client Selection

- Prefer `RestClient` for imperative HTTP client code and `WebClient` for reactive pipelines.
- Do not use `WebClient` reactively and then immediately block in controllers or hot paths.
- Prefer Spring HTTP Service Clients for new declarative clients when the target Spring line supports the needed features.
- Treat new OpenFeign usage as a compatibility decision and verify timeouts, retry behavior, circuit breaking, metrics, and migration posture.

## Deadlines and Timeouts

- Define an end-to-end request deadline, then allocate connect, TLS handshake, pool acquisition, write, response, and read timeouts within that budget.
- Do not approve remote calls without explicit timeout behavior and caller-visible failure semantics.
- Bound response body size, decoder memory, redirects, and streaming duration.
- For Spring Boot 4.x HTTP Service Clients, verify group-specific `spring.http.serviceclient.<group>` base URL, timeout, redirect, default header, API versioning, and SSL bundle settings.

## Retries and Resilience

- Retry only idempotent operations or operations protected by an idempotency key.
- Use exponential backoff with jitter, max attempts, retry budget, and retryable exception classification.
- Review circuit breaker, bulkhead, rate limit, and fallback behavior separately from client timeout behavior.
- Do not let retry policies amplify overload on a saturated downstream.

## SSRF and Egress Safety

- For user-influenced URLs or hosts, require host allowlists, scheme allowlists, redirect policy, proxy policy, DNS/private-address filtering, and audit logs.
- Validate behavior after DNS rebinding, redirect to private ranges, IPv6 literals, encoded hostnames, and unusual but valid URL forms.
- Use platform support such as Spring Boot address filtering where available, but do not treat it as a substitute for explicit egress policy.

## Reactor Netty and Pools

- For Reactor Netty-backed clients, check connection pool limits, pending acquire limits, response timeout, TLS, proxy and redirect policy, DNS behavior, decoder limits, metrics, and tracing.
- Size client pools against server concurrency, downstream limits, and retry behavior.
- Verify context propagation and observation instrumentation across reactive and imperative boundaries.

## Operations

- Monitor latency, timeout type, retry count, pool saturation, DNS failures, TLS failures, response size rejection, downstream status codes, and circuit-breaker state.
- Include runbook guidance for downstream outage, partial degradation, retry storms, and configuration rollback.

## Immediate Anti-Patterns

- Remote call with no explicit timeout.
- Retrying non-idempotent mutation without an idempotency key.
- User-supplied URL fetched without SSRF controls.
- Reactive client used only to call `.block()` in a servlet request hot path.
- Client pool and retry settings reviewed independently instead of as one capacity model.
