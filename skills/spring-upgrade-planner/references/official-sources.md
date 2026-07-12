# Official Sources

Checked on: 2026-07-12. Treat official target-version requirements and migration notes as normative; re-check current release and support claims.

- [Spring Boot upgrading guide](https://docs.spring.io/spring-boot/upgrading.html) — review every skipped release and remove the temporary properties migrator after use.
- [Spring Boot build systems](https://docs.spring.io/spring-boot/reference/using/build-systems.html) — managed BOM and dependency override guidance.
- [Spring Boot system requirements](https://docs.spring.io/spring-boot/system-requirements.html) — current JDK and build-tool baselines; use the target line's versioned page for historical targets.
- [Spring support policy](https://spring.io/support-policy) — project support timelines and policy.
- [Spring Initializr reference](https://docs.spring.io/initializr/docs/current/reference/html/) — metadata capabilities; metadata availability alone does not prove long-term support.
- [Spring Boot 4.0 migration guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide) — required bridge and migration guidance for Boot 4.
- [Spring Boot 4.1 release notes](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.1-Release-Notes) — target-line changes after the Boot 4.0 bridge.
- [Spring Cloud project page](https://spring.io/projects/spring-cloud/) — primary current release-train and Spring Boot compatibility table, including service-release qualifications.
- [Spring Cloud supported versions](https://github.com/spring-cloud/spring-cloud-release/wiki/Supported-Versions) — component matrix and support detail; it can lag the project page. When official sources disagree, verify the newer project table and the selected train's release notes before deciding the gate.
- [Spring Cloud 2025.1 release notes](https://github.com/spring-cloud/spring-cloud-release/wiki/Spring-Cloud-2025.1-Release-Notes) — train-bound example for reconciling compatibility details; substitute the selected target train.
- [Spring project release highlights](https://spring.io/projects/release-highlights) and [project catalog](https://spring.io/projects/) — discovery; confirm details in each project’s release notes.
- [OpenRewrite Spring recipes](https://docs.openrewrite.org/recipes/java/spring) — transformation recipes and applicability.
- [OpenRewrite Maven dry run](https://docs.openrewrite.org/reference/rewrite-maven-plugin) and [Gradle plugin configuration](https://docs.openrewrite.org/reference/gradle-plugin-configuration) — reviewable dry-run workflow.
- [Spring Boot managed coordinates](https://docs.spring.io/spring-boot/appendix/dependency-versions/coordinates.html) — target-line managed dependency inventory.
- [Maven POM reference](https://maven.apache.org/pom.html) and [Gradle dependency reports](https://docs.gradle.org/current/userguide/viewing_debugging_dependencies.html) — effective dependency evidence.
- [Maven 3.9.11 release notes](https://maven.apache.org/docs/3.9.11/release-notes.html) and [Gradle 9.1.0 release notes](https://docs.gradle.org/9.1.0/release-notes.html) — version-bound examples; substitute the exact selected build-tool release.
- [OpenJDK JDK 25](https://openjdk.org/projects/jdk/25/) — JDK 25 feature inventory and release status; select the actual target JDK line.
- [Oracle JDK 25 migration guide](https://docs.oracle.com/en/java/javase/25/migrate/) — Oracle JDK migration changes; review every intervening target line.
- [Oracle Java SE Support Roadmap](https://www.oracle.com/java/technologies/java-se-support-roadmap.html) — Oracle's LTS designation and support timeline. Confirm the selected distribution vendor's separate support policy before making lifecycle claims.
- [Hibernate ORM releases](https://hibernate.org/orm/releases/) — select the supported target series and its compatibility line.
- [Hibernate ORM mutable current migration guide](https://docs.hibernate.org/orm/current/migration-guide/) — discovery only; pin the target series and never use this redirect as evidence for an earlier crossed boundary.
- [Hibernate ORM 7.4 migration guide](https://docs.hibernate.org/orm/7.4/migration-guide/), [7.2 migration guide](https://docs.hibernate.org/orm/7.2/migration-guide/), and [6.x-to-7.0 major guide](https://docs.hibernate.org/orm/7.0/migration-guide/) — examples of versioned hop evidence. Review every intervening series actually crossed.
