# Implementation Playbook

## Existing-Project Change

1. Inspect repository instructions, worktree status, build descriptors, source sets, configuration profiles, migrations, and the tests nearest the change.
2. Reproduce or statically locate the failing path. Convert the request into an observable before/after condition.
3. Trace the complete Spring boundary involved: bean creation, proxy/AOP interception, validation, transaction ownership, serialization, persistence, security, messaging, scheduling, or outbound I/O.
4. Prefer a local correction over a new abstraction. Preserve package structure, public APIs, configuration keys, database contracts, and operational defaults unless the acceptance criteria require change.
5. Add a regression test that fails for the original trigger. Use the narrowest test level that still exercises the relevant framework behavior.
6. Check callers and adjacent failure paths for compatibility, concurrency, transaction, security, and observability effects.

## Greenfield Application

1. Establish the exact Spring Boot, Java/Kotlin, build-tool, packaging, database, protocol, and deployment requirements. Ask only for choices that materially change the result.
2. Verify the requested version line and system requirements before generating files. Apply `references/greenfield-baseline-policy.json` to every unpinned field: use the current Spring Initializr default stable GA, its default supported Java, and its default project type unless the user selected that field. Do not infer a vendor LTS policy. Record the UTC retrieval time, metadata SHA-256, exact selected versions and build type, generated wrapper version, and which fields came from the user. Ask or stop only when an explicit target is incompatible or pre-release, or when a non-default choice would materially change the requested design.
3. Start with one application entry point, a conventional package root, minimal configuration, and only dependencies required by the first executable behavior.
4. Define external contracts and failure behavior before infrastructure detail. Keep secrets external and provide safe local placeholders without real values.
5. Add a small smoke or slice test plus focused domain tests. Do not add speculative brokers, caches, service discovery, native images, or deployment platforms.

## Cross-Cutting Implementation Baseline

Apply only the rows touched by the request or repository evidence.

- **Structure:** keep one conventional application root and prefer feature-oriented packages once the domain has multiple use cases. Keep domain decisions separate from framework and transport adapters.
- **Dependencies:** use the Spring Boot BOM and minimal starters. Avoid ad hoc managed-version overrides; record why every new dependency is needed.
- **API:** use explicit request/response contracts, boundary validation, stable status and Problem Details behavior, and authorization at the object or tenant boundary.
- **Data:** use versioned Flyway or Liquibase migrations for production schema changes, production-equivalent database semantics in integration tests, and expand/contract steps for rolling compatibility.
- **Integrations:** set bounded connect/read/response deadlines, retry only safe operations with backoff, and design idempotency, ordering, acknowledgement, poison-message, and recovery behavior where applicable.
- **Security:** default to least privilege, externalize secrets, constrain outbound destinations, and avoid logging credentials, tokens, personal data, or full payloads.
- **Operations:** expose only necessary management endpoints; add health, metrics, traces, and structured diagnostic context proportionate to the service and secure their access.
- **Delivery:** preserve wrapper and toolchain constraints. Add reproducibility, SBOM, container, or provenance controls when the deployment contract requires them rather than as decorative files.

## Spring Correctness Checks

- Ensure dependency injection and proxy boundaries are real. Self-invocation does not trigger proxy-based transactions, caching, retries, security, or async behavior.
- Keep transaction ownership explicit; avoid remote calls or unbounded work inside database transactions unless the consistency contract requires it.
- Validate at trust boundaries and preserve authorization at the object or tenant boundary, not only at authentication.
- Distinguish blocking MVC code from reactive execution. Do not move blocking work onto an event loop or label wrappers as non-blocking without evidence.
- Treat database constraints, migrations, broker delivery, retries, idempotency, clocks, and concurrency as observable contracts when the change touches them.
- Preserve useful failure context and observability without logging credentials, tokens, personal data, or full payloads.

## Verification Ladder

1. Review syntax, imports, configuration binding, migration ordering, and the final diff.
2. Run the narrow regression test when allowed.
3. Run the affected module or source-set checks when allowed.
4. Run integration tests against the real dependency semantics, including Testcontainers when already adopted or justified, when allowed.
5. Run the broader repository suite or package step only when proportionate to the change and permitted by the task.
6. Separate passed, failed, skipped, and unrun checks. A code review or compile-shaped inspection is not an executed test.

Stop on a failure that invalidates later checks. Diagnose the failure before broadening scope or changing unrelated code.
