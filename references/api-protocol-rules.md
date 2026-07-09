# API and Protocol Review Rules

Use this file only when GraphQL, gRPC, Spring Authorization Server, Spring Session, HATEOAS, SOAP/Web Services, LDAP, or protocol-specific API behavior is in scope.

## GraphQL

- Review schema ownership, resolver boundaries, authorization per field/resolver, error shape, pagination, nullability, and versioning strategy.
- Prevent N+1 with DataLoader, projections, fetch joins, or query-specific data access. Test query count for important operations.
- Bound query depth, complexity, execution time, request size, introspection exposure, subscriptions, and file uploads.
- Treat GraphQL as an API surface with the same audit, rate-limit, authentication, and observability requirements as REST.

## Authorization Server and OAuth/OIDC

- Note that Spring Authorization Server 1.5.x is the last standalone generation and new work moves into Spring Security 7+. Verify the target line before recommending new development.
- Review registered clients, grant types, redirect URI exactness, PKCE, client authentication, token format, key rotation, consent, logout, introspection, revocation, and multi-tenant issuer behavior.
- Do not build an authorization server unless the team has identity-provider operational ownership. Prefer managed IdP when customization is not a core requirement.

## gRPC

- Review protobuf evolution rules, deadlines, retry policy, health service, reflection exposure, authentication, authorization, and TLS/mTLS.
- Verify Spring gRPC client/server starter availability against the target Boot line, generated-stub lifecycle, test coverage, shutdown/drain behavior, and observability.

## Session, HATEOAS, SOAP, and LDAP

- For Spring Session, verify repository choice, TTL, cookie flags, session fixation protection, serialization format, concurrent session rules, WebSocket/WebSession behavior, and cross-region failure modes.
- For HATEOAS, use it only when hypermedia navigation is a real API contract. Do not add links as decoration around CRUD JSON.
- For SOAP/Web Services, review contract-first WSDL/XSD compatibility, WS-Security, XML parser hardening, timeouts, retries, and schema evolution.
- For LDAP, review bind strategy, connection pooling, TLS, search base/filter escaping, group mapping, paging, referral handling, and least-privilege service accounts.

## Immediate Anti-Patterns

- GraphQL endpoint with no query complexity/depth limits.
- Authorization server built casually for login when a managed IdP would satisfy requirements.
- gRPC service without deadlines, protobuf compatibility rules, authentication/authorization, or TLS/mTLS review.
- Distributed session store without TTL, serialization, and failover review.
- LDAP search filters built from unescaped user input.
