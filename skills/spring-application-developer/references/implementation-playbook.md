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
2. Verify the requested version line and system requirements before generating files. Apply `references/greenfield-baseline-policy.json` as the sole selection algorithm (`spring-initializr-defaults/1`) for every unpinned generation field, including its hash-before-parsing rule. Use host-provided metadata bytes only when they are bound to the current run and their hash is verified; otherwise retrieve the approved source with normal certificate and hostname verification. Never use an insecure TLS fallback. If verified retrieval fails, block version-sensitive generation rather than infer a version. Do not infer a vendor LTS policy.
3. Complete the version-resolution checkpoint before the first workspace mutation: send the compact user summary by default, with selected versus defaulted values, source, retrieval time, hash prefix, and any relevant wrapper warning, and repeat the resolved selection in the final handoff. Collect full provenance for the current run, retain it in an evaluation trace when the host provides one, and save a metadata snapshot or provenance artifact only when the user requests it. Ask or stop only when the policy blocks or a non-default choice would materially change the requested design.
4. Start with one application entry point, a conventional package root, minimal configuration, and only dependencies required by the first executable behavior.
5. Define external contracts and failure behavior before infrastructure detail. Keep secrets external and provide safe local placeholders without real values.
6. Add a small smoke or slice test plus focused domain tests. Do not add speculative brokers, caches, service discovery, native images, or deployment platforms.

## Cross-Cutting Implementation Baseline

Apply only the rows touched by the request or repository evidence. A new network service always touches API exposure, an explicit security posture, and a minimum operational health signal; this does not authorize inventing an authentication scheme or broader telemetry requirements.

- **Structure:** keep one conventional application root and prefer feature-oriented packages once the domain has multiple use cases. Keep domain decisions separate from framework and transport adapters.
- **Dependencies:** use the Spring Boot BOM and minimal starters. Avoid ad hoc managed-version overrides; record why every new dependency is needed.
- **API:** use explicit request/response contracts, boundary validation, stable status and Problem Details behavior, and an explicit security posture. Enforce authorization at the object or tenant boundary when authentication and actor requirements are supplied.
- **Data:** use versioned Flyway or Liquibase migrations for production schema changes, production-equivalent database semantics in integration tests, and expand/contract steps for rolling compatibility. Treat authoring those test definitions separately from executing them: a prohibition on build or container execution does not prohibit adding justified Testcontainers configuration or tests; leave those checks unrun and report them.
- **Integrations:** set bounded connect/read/response deadlines, retry only safe operations with backoff, and design idempotency, ordering, acknowledgement, poison-message, and recovery behavior where applicable.
- **Security:** default to least privilege, externalize secrets, constrain outbound destinations, and avoid logging credentials, tokens, personal data, or full payloads. When authentication requirements are absent, do not invent Basic, API-key, session, or OAuth2 behavior; document that external exposure is blocked until the caller and authorization contract are chosen.
- **Operations:** for a new network service, include Actuator health as the minimum operational baseline and expose only health by default. Add metrics, traces, or broader management endpoints only when the service or deployment contract requires them, and secure their access.
- **Delivery:** preserve wrapper and toolchain constraints. Add reproducibility, SBOM, container, or provenance controls when the deployment contract requires them rather than as decorative files.

## Spring Correctness Checks

- Ensure dependency injection and proxy boundaries are real. Self-invocation does not trigger proxy-based transactions, caching, retries, security, or async behavior.
- Keep transaction ownership explicit; avoid remote calls or unbounded work inside database transactions unless the consistency contract requires it.
- Validate at trust boundaries and preserve authorization at the object or tenant boundary, not only at authentication.
- Distinguish blocking MVC code from reactive execution. Do not move blocking work onto an event loop or label wrappers as non-blocking without evidence.
- Treat database constraints, migrations, broker delivery, retries, idempotency, clocks, and concurrency as observable contracts when the change touches them.
- Preserve useful failure context and observability without logging credentials, tokens, personal data, or full payloads.

## Verification Ladder

Do not enter an executable rung when the relevant tool or task is explicitly forbidden. Do not probe availability by launching the prohibited command; record executable checks as unrun and continue only with safe static inspection.

1. Review syntax, imports, configuration binding, migration ordering, and the final diff.
2. Run the narrow regression test when allowed.
3. Run the affected module or source-set checks when allowed.
4. Run integration tests against the real dependency semantics, including Testcontainers when already adopted or justified, when allowed. If execution is forbidden, keep the production-equivalent test definition and report the command as unrun.
5. Run the broader repository suite or package step only when proportionate to the change and permitted by the task.
6. Separate passed, failed, skipped, and unrun checks. A code review or compile-shaped inspection is not an executed test.

Stop on a failure that invalidates later checks. Diagnose the failure before broadening scope or changing unrelated code.
