# Spring Migration Review Rules

Use this file only to evaluate an existing Spring, Java/Kotlin, Jakarta, dependency, build, or runtime migration proposal or implementation. Do not select a target or synthesize missing stages; hand that output to `spring-upgrade-planner`.

## Source and Compatibility

- Verify that the proposal identifies current and target versions for Spring Boot, Spring Framework, Spring Security, Spring Data, Spring Cloud, Java, Kotlin, Gradle/Maven, container runtime, and native-image tooling.
- Verify the target line against official migration guides, release notes, system requirements, support matrix, Spring Cloud compatibility table, and Spring Initializr or dependency-generation support.
- Do not approve dependency overrides that bypass the Spring Boot BOM without compatibility evidence.
- Treat exact requirements such as Java, Kotlin, GraalVM, Servlet, Jakarta, Jackson, Hibernate, and server support as target-version facts that must be checked against official sources before being stated firmly.
- For Java upgrades, distinguish LTS policy from feature availability and review every intervening JDK migration guide, removed API, security-default, runtime, and tooling change; include Java 25 when it is a supported target line.
- For Hibernate major upgrades, require the target major's migration guide in addition to Spring Boot dependency management and Spring Framework release notes.

## Upgrade Path

- Check whether the proposal first moves to the latest appropriate patch of the current line.
- Verify that it removes deprecated APIs, properties, starters, and modules before the major jump when official guidance recommends doing so.
- Verify that it separates mechanical namespace or package migration from behavior changes.
- Confirm that it includes build-tool, plugin, container-image, and native-image changes rather than treating them as afterthoughts.

## Runtime Behavior

- Review configuration binding changes, path matching, security defaults, serialization changes, observability changes, actuator exposure, data initialization, schema migration, and HTTP client behavior.
- For Jakarta migrations, check all `javax`/`jakarta` imports, generated code, servlet filters, validation, persistence, JAXB/XML, test fixtures, and third-party libraries.
- For Spring Cloud, verify the target release train and the supported Spring Boot range before approving the upgrade.
- For Spring Security upgrades, check endpoint authorization defaults, method security, CSRF behavior, resource-server configuration, and password/storage migration notes.
- For Spring Security 7+, check Authorization Server integration, SPA CSRF configuration, MFA-related changes, DSL removals, and module moves against the target line.

## Rollout

- Verify that the proposal includes rollback, canary or staged rollout, compatibility tests, database expand/contract migration, API compatibility checks, and production telemetry comparison.
- Reject coupling irreversible data migrations to application binary rollout unless the rollback story is explicit and tested.
- Verify that dependency and CVE review occurs after the version bump, not only before it.
