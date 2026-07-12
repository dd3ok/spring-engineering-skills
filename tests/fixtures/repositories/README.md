# Golden repository fixtures

These repositories are fixed parser-regression snapshots, not templates or recommendations to use the recorded dependency versions. They intentionally cover three common build shapes without executing Maven or Gradle:

- Spring Boot 3 Maven reactor with Java;
- Spring Boot 3 Gradle Groovy multi-project with Java;
- Spring Boot 4 Gradle Kotlin DSL multi-project with Kotlin.

Update a fixture version only when the parser contract being tested changes. Product-version recommendations must still be verified against current official support and compatibility documentation.

The Boot 4 fixture shape follows the official [Spring Boot system requirements](https://docs.spring.io/spring-boot/system-requirements.html), [Kotlin support](https://docs.spring.io/spring-boot/reference/features/kotlin.html), and [Gradle multi-project build](https://docs.gradle.org/current/userguide/multi_project_builds.html) guidance. Its pinned versions are regression inputs, not a claim that they remain the latest releases.
