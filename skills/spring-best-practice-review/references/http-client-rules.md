# HTTP Client and Service-to-Service Review Rules

Use this file when `RestClient`, `WebClient`, HTTP Service Clients, Feign/OpenFeign, Reactor Netty, service-to-service calls, SSRF, retries, deadlines, or outbound API reliability is in scope.

## Client Selection

- Prefer `RestClient` for imperative HTTP client code and `WebClient` for reactive pipelines.
- On Spring Framework 7+, treat `RestTemplate` as deprecated and review a staged `RestClient` migration; for older lines, verify behavior against the deployed version.
- Do not use `WebClient` reactively and then immediately block in controllers or hot paths.
- Prefer Spring HTTP Service Clients for new declarative clients when the target Spring line supports the needed features.
- Treat Spring Cloud OpenFeign as feature-complete. Prefer Spring HTTP Service Clients for new work; retain or add OpenFeign only for a documented compatibility or feature dependency, with timeouts, retry behavior, circuit breaking, metrics, and migration posture reviewed.

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
- On Spring Boot 4.1, explicitly configure `InetAddressFilter` through HTTP client settings for blocking and reactive clients where address filtering is required; verify equivalent behavior against versioned documentation on any other line. Retain host and scheme allowlists, redirect controls, DNS-rebinding tests, proxy policy, and network egress controls; the classpath alone does not enable SSRF protection.

## Reactor Netty and Pools

- For Reactor Netty-backed clients, check connection pool limits, pending acquire limits, response timeout, TLS, proxy and redirect policy, DNS behavior, decoder limits, metrics, and tracing.
- Size client pools against server concurrency, downstream limits, and retry behavior.
- Verify context propagation and observation instrumentation across reactive and imperative boundaries.

## Operations

- Monitor latency, timeout type, retry count, pool saturation, DNS failures, TLS failures, response size rejection, downstream status codes, and circuit-breaker state.
- Include runbook guidance for downstream outage, partial degradation, retry storms, and configuration rollback.
