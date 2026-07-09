# Spring Migration Review Rules

Use this file for Spring Boot, Spring Framework, Spring Security, Spring Data, Spring Cloud, Java, Kotlin, Jakarta, dependency, build, or runtime major upgrades.

## Source and Compatibility

- Identify current and target versions for Spring Boot, Spring Framework, Spring Security, Spring Data, Spring Cloud, Java, Kotlin, Gradle/Maven, container runtime, and native-image tooling.
- Verify the target line against official migration guides, release notes, system requirements, support matrix, Spring Cloud compatibility table, and Spring Initializr or dependency-generation support.
- Do not approve dependency overrides that bypass the Spring Boot BOM without compatibility evidence.
- Treat exact requirements such as Java, Kotlin, GraalVM, Servlet, Jakarta, Jackson, Hibernate, and server support as target-version facts that must be checked against official sources before being stated firmly.

## Upgrade Path

- Move to the latest patch of the current minor or major line first.
- Remove deprecated APIs, configuration properties, starters, and modules before the major jump when official guidance recommends doing so.
- Separate mechanical namespace/package migration from behavior changes.
- Keep build-tool, plugin, container image, and native-image changes in the migration plan; do not treat them as afterthoughts.

## Runtime Behavior

- Review configuration binding changes, path matching, security defaults, serialization changes, observability changes, actuator exposure, data initialization, schema migration, and HTTP client behavior.
- For Jakarta migrations, check all `javax`/`jakarta` imports, generated code, servlet filters, validation, persistence, JAXB/XML, test fixtures, and third-party libraries.
- For Spring Cloud, verify the target release train and the supported Spring Boot range before approving the upgrade.
- For Spring Security upgrades, check endpoint authorization defaults, method security, CSRF behavior, resource-server configuration, and password/storage migration notes.

## Rollout

- Require rollback plan, canary or staged rollout, compatibility tests, database expand/contract migration, API compatibility checks, and production telemetry comparison.
- Keep irreversible data migrations separate from application binary rollout unless the rollback story is explicit and tested.
- Require dependency and CVE review after the version bump, not only before it.

## Immediate Anti-Patterns

- Major upgrade plan that skips the official migration guide.
- Version claims copied from memory instead of checked against the target line.
- Spring Cloud release train upgraded independently from Spring Boot compatibility.
- Jakarta migration that checks only application source and ignores generated code, tests, filters, validation, persistence, XML, or third-party libraries.
