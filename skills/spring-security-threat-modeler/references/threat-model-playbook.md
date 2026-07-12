# Threat Model Playbook

## Required surfaces

- HTTP/WebSocket/GraphQL/gRPC endpoints, filters, gateways, and forwarded headers.
- Authentication credentials, session/token lifecycle, logout/revocation, and service identities.
- URL and method authorization, object-level authorization, method security, unmatched/default rules, tenant boundaries, and administrative functions.
- JWT issuer and audience validation, authority mapping, key rotation, and multi-tenant issuer allowlists.
- CSRF, CORS, response headers, cookies, redirects, request size, multipart upload, and error responses.
- SQL/NoSQL/query construction, serialization/deserialization, templates, file paths, and command/process execution.
- Outbound HTTP/DNS/redirect behavior, metadata services, webhooks, and callback URLs.
- Brokers, event schemas, replay/duplicate handling, DLQs, and producer/consumer authorization.
- Secrets/configuration, Actuator/JMX, logs/traces, backups, CI/CD, images, and software supply chain.

## Finding standard

Each finding states asset, actor, boundary/flow, precondition, attack path, observed control, control gap, impact, likelihood rationale, confidence, remediation, verification, treatment state (open, mitigated, accepted, or transferred), and residual risk. Severity follows reachability and impact, not keyword matches.

## Control traps

- `permitAll` or matcher order can expose more than the nearby code suggests.
- Multiple servlet filter chains use first-match semantics; if no chain matches, Spring Security does not protect that request. Verify a deliberate default chain.
- Reactive applications require `SecurityWebFilterChain`, reactive method-security, and reactive CSRF semantics; do not transpose servlet behavior without evidence.
- Authentication does not prove object or tenant authorization.
- Disabling defaults such as CSRF or headers requires an explicit replacement or evidence that the threat is absent.
- Sanitized observability still requires endpoint authorization and network controls.
