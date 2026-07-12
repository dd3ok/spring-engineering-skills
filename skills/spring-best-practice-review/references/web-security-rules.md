# Spring Web and Security Review Rules

Load for core MVC, WebFlux, API, HTTP-client, Spring Security, TLS, or certificate review.

## MVC, WebFlux, and Threads

- Default to Spring MVC for blocking CRUD APIs, JPA/Hibernate, JDBC, traditional servlet filters, and simple request/response services.
- Choose WebFlux only when the runtime path is genuinely non-blocking end to end, or when streaming, backpressure, or high-concurrency I/O workloads justify it.
- If both `spring-boot-starter-web` and `spring-boot-starter-webflux` are present, treat MVC as the default runtime unless the application explicitly configures a reactive application type.
- Never block Reactor event-loop threads. Isolate unavoidable blocking calls with `Schedulers.boundedElastic()` and test with BlockHound where appropriate.
- Do not present WebFlux as a performance fix for blocking database calls.
- Treat virtual threads as an option for blocking I/O throughput, not a substitute for non-blocking design and not a lower-latency guarantee. Verify Java version and `spring.threads.virtual.enabled` behavior before recommending them.
- For virtual threads on Java 21 through 23, check frequent long-lived pinning from blocking inside `synchronized`, native, or foreign-function calls. On Java 24+, account for JEP 491 removing monitor-based pinning and investigate only evidence-backed residual pinning such as native or FFM callbacks and VM or class-initialization frames reported by JFR. Do not pool virtual threads to limit concurrency; use resource pools, semaphores, queue bounds, or explicit bulkheads.
- Review carrier-thread assumptions, executor selection, cancellation, downstream concurrency limits, and `ThreadLocal` values used as expensive mutable caches before enabling virtual threads. Ordinary request or transaction context in `ThreadLocal` is not by itself a defect. Verify behavior with JFR and production-like load instead of assuming a throughput gain.
- For WebFlux/Reactor, review backpressure, `publishOn`/`subscribeOn` placement, context propagation, and `ThreadLocal` bridging before accepting mixed reactive/imperative code.

## API and HTTP Clients

- Load `references/http-client-rules.md` when outbound HTTP correctness, deadlines, retries, SSRF, client pools, declarative clients, or service-to-service reliability are central to the request.
- Prefer explicit API versioning through path, header, query parameter, or media type strategies.
- Prefer RFC 9457 Problem Details for API error responses.
- Avoid suffix-pattern content negotiation.
- Define stable error codes, correlation IDs, and idempotency-key behavior in API contracts.
- Prefer `RestClient` for imperative HTTP client code and `WebClient` for reactive pipelines. Do not use `WebClient` reactively and then immediately block in controllers or hot paths.
- For new declarative HTTP clients, prefer Spring HTTP Service Clients where appropriate. Treat new OpenFeign usage as a compatibility decision and verify timeouts, retries, circuit breaking, and migration posture.
- In baseline review, flag remote calls without explicit timeout behavior, unbounded retries, user-influenced URLs without SSRF controls, missing idempotency for retryable mutations, and unreviewed client pool/decoder/TLS/redirect/proxy behavior.

## Security

Use this section to review code and configuration controls. Use `spring-security-threat-modeler` for system-wide trust boundaries, data flows, abuse paths, and residual risk.

- Prefer deny-by-default authorization: explicitly permit public endpoints and protect everything else.
- Verify actuator endpoint exposure, authentication, authorization, network reachability, and sensitive endpoint access.
- Do not assume method-level authorization is active just because Spring Security is on the classpath. Check for explicit method-security enablement when service-layer authorization matters.
- Keep CSRF protection for browser flows whenever credentials can be attached automatically, including cookies and HTTP Basic authentication. Consider disabling it only for non-browser clients or credential transport that a browser cannot attach automatically, and document and test that assumption; statelessness alone is not sufficient evidence.
- For OAuth2 resource servers, verify issuer/JWKS/introspection configuration, token audience/issuer validation, clock skew handling, and multi-tenant token validation if applicable.
- Review CORS as an explicit allowlist, not a wildcard convenience setting.
- For browser flows, verify cookie `Secure`, `HttpOnly`, `SameSite`, session fixation protection, logout behavior, HSTS, and security header policy.
- Verify password storage uses current adaptive hashing guidance and no reversible or legacy hashes remain.
- For file uploads, review content type validation, extension handling, size limits, malware scanning boundary, storage permissions, and path traversal controls.
- Avoid leaking authorization failure details in API responses. Prefer logs, audit events, and correlation IDs for diagnosis.
- Review trusted proxy and forwarded-header configuration, host validation, request/header/body limits, HTTP firewall behavior, and redirect targets at the actual ingress topology.
- Verify secrets and personal data are redacted from logs, traces, metrics, error responses, actuator `/env` and `/configprops`, heap dumps, and support bundles. Treat actuator `show-values` and custom sanitization as security-sensitive configuration.
- Include dependency provenance, supported release lines, Spring security advisories, SBOM generation, and reachable-vulnerability triage in release reviews; do not equate a scanner finding or absence of one with exploitability proof.

## TLS and Certificates

- Use Spring Boot SSL bundles where they reduce duplicated trust-store configuration across clients and servers.
- Never disable certificate validation outside explicitly scoped local tests.
