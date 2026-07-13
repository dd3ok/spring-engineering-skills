# Upgrade Playbook

The portable interchange format is `spring-upgrade-plan/2`. Version 2 replaces v1 because exact Spring Cloud and controlled-capture provenance fields are now required; migrate v1 artifacts explicitly rather than relabeling them.

The JSON Schema selected by `SKILL.md` defines the portable interchange shape. The bundled semantic validator remains authoritative for provenance, applicability, snapshot, and cross-field invariants.

## Order of work

1. Stabilize on the latest patch of the current supported line where practical.
2. Update the JDK and build tool only in an order supported by both current and target frameworks.
3. Remove unnecessary overrides of versions managed by the Spring Boot BOM.
4. Apply one framework feature-line transition per stage when the risk warrants it.
5. Compile, run focused tests, run integration/contract tests, and observe a production-like canary at every boundary.

For a Boot major transition, preserve the official landing lines in the hop chain: enter Boot 3 through a pinned latest 2.7.x and then a pinned latest 3.0.x; enter Boot 4 through a pinned latest 3.5.x and then a pinned latest 4.0.x. Continue through later feature lines only after reviewing every skipped release note. Resolve every `latest-*.x-from-pinned-source` placeholder to an exact version before `ready` status.

For a Boot 4 transition, turn repository evidence into four bounded work groups: main/test starter and direct-dependency inventory; applicable baseline, removed-feature, container, and Jackson 3 changes; test-infrastructure changes; and compile, focused-test, integration/contract, and canary verification. Do not add Undertow, Pulsar, Batch, native-image, Kotlin, or other technology-specific work unless the evidence pack shows that surface is used or the target baseline directly requires it.

Bind every migration-guide or release-notes snapshot to the exact hop it supports. A Boot 4.0 migration guide cannot substantiate a 2.7 → 3.0 transition or later 4.0 → 4.1 release changes. Aggregate skipped notes only in a content-addressed snapshot whose ledger applicability matches that hop.

Record `spring_cloud_usage` separately from `spring_cloud` so unknown, used, and confirmed non-use cannot collapse into one null. Resolve current evidence and select the exact target train service release, or mark target non-use only with a content-addressed `platform.usage` fact. For Boot 4.1 with the 2025.1 train, require service release 2025.1.2 or newer. Bind the compatibility snapshot to both exact Boot and Cloud versions; when official tables need reconciliation, attach the selected train's release notes under its separate train-bound scope.

Record exact target Java and Maven-or-Gradle versions. Every ready source declares its subject and subject version; JDK migration and build-tool sources must match those target selections and versioned locators. A general Java support roadmap is supplemental lifecycle evidence under a separate scope and cannot satisfy the target-JDK migration source gate.

A SHA-256 establishes the identity of a local copy, not its origin. Ready plans keep the exact `spring-evidence/1` input at `input.evidence_snapshot_path`, record `input.evidence_captured_at`, and reject evidence captures or imported reports older than 180 days. The validator caps the evidence file at 64 MiB, then checks its byte hash, semantic contract, canonical fact IDs, and current Boot/Cloud bindings. Official sources require a controlled-capture manifest with the final allowlisted locator, UTC capture time, capture identity, and response hash; their hashes are streamed rather than loaded wholly into memory. The validator checks manifest consistency and allowlists; trust still depends on the stated controlled capture process.

## Required checks

- Boot-managed dependencies and explicit overrides.
- Spring Cloud release-train compatibility with the Boot line.
- Jakarta namespace, servlet/container, validation, persistence, and security changes.
- Configuration-property removals or renames; use the properties migrator only temporarily and remove it after migration.
- Database drivers, Hibernate/JPA behavior, schema migration tools, serialization, and wire compatibility.
- Observability changes: metric names/tags, tracing propagation, health/readiness, logging, and agent compatibility.
- Test framework and mocking changes, AOT/native-image constraints, container base image, and platform architecture.

## Automation boundary

OpenRewrite or IDE migrations can accelerate mechanical edits, but recipes are code transformations that require review, compilation, tests, and behavior verification. Pin the plugin, recipe artifact, and recipe ID to reviewed versions; record the recipe license; run Maven `rewrite:dryRun` or Gradle `rewriteDryRun` before any separately approved apply. Never present a successful recipe run as proof of a successful upgrade.

## Rollback

Use expand/contract for schemas and protocols. Avoid rollback plans that require downgrading data already written in a new format. State the last reversible stage and the operational signal that triggers rollback.
