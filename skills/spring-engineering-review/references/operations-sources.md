# JVM, Operations, and Background Sources

Checked on: 2026-07-12. Use this map for discovery, then cite the exact versioned page used. Re-check current pages and label non-GA sources.

## JVM, Performance, and Testing

- Spring Framework TestContext caching: https://docs.spring.io/spring-framework/reference/testing/testcontext-framework/ctx-management/caching.html
- OpenJDK JDK 25 release and feature list: https://openjdk.org/projects/jdk/25/
- Oracle JDK 25 migration guide: https://docs.oracle.com/en/java/javase/25/migrate/
- Oracle Java SE support roadmap and Oracle LTS policy: https://www.oracle.com/java/technologies/java-se-support-roadmap.html
- Oracle JDK 24 significant changes and JEP 491 summary: https://docs.oracle.com/en/java/javase/24/migrate/significant-changes-jdk-24.html
- JEP 491, Synchronize Virtual Threads without Pinning: https://openjdk.org/jeps/491
- Oracle Java 26 virtual threads guide: https://docs.oracle.com/en/java/javase/26/core/virtual-threads.html
- Oracle Java 21 virtual threads guide: https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html
- Spring Boot AOT on the JVM: https://docs.spring.io/spring-boot/reference/packaging/aot.html
- Spring Framework AOT restrictions: https://docs.spring.io/spring-framework/reference/core/aot.html
- Spring Boot native images: https://docs.spring.io/spring-boot/reference/packaging/native-image/introducing-graalvm-native-images.html
- Spring Boot native application testing: https://docs.spring.io/spring-boot/how-to/native-image/testing-native-applications.html
- Spring Framework Kotlin requirements: https://docs.spring.io/spring-framework/reference/languages/kotlin/requirements.html
- Kotlin all-open and `kotlin-spring` compiler plugins: https://kotlinlang.org/docs/all-open-plugin.html
- Kotlin no-arg and `kotlin-jpa` compiler plugins: https://kotlinlang.org/docs/no-arg-plugin.html
- Spring Data coroutine repositories: https://docs.spring.io/spring-data/commons/reference/kotlin/coroutines.html

Treat feature availability and GA status as JDK-line facts. Treat LTS designation, patch availability, and support duration as distribution-vendor policy; verify the deployed vendor before making lifecycle claims.
- Oracle Java 26 Flight Recorder guide: https://docs.oracle.com/en/java/javase/26/jfapi/flight-recorder.html
- async-profiler official repository: https://github.com/async-profiler/async-profiler
- Micrometer histograms and percentiles: https://docs.micrometer.io/micrometer/reference/concepts/histogram-quantiles.html
- OpenTelemetry semantic conventions: https://opentelemetry.io/docs/specs/semconv/
- HikariCP official repository and configuration reference: https://github.com/brettwooldridge/HikariCP
- HikariCP pool sizing guidance: https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing
- Kubernetes container resource management: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/
- Kubernetes Deployments and rolling updates: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
- Kubernetes Pod lifecycle and termination: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/
- Kubernetes Pod disruptions and disruption budgets: https://kubernetes.io/docs/concepts/workloads/pods/disruptions/
- Kubernetes horizontal Pod autoscaling: https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/
- Kubernetes topology spread constraints: https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/
- Kubernetes container image lifecycle and digests: https://kubernetes.io/docs/concepts/containers/images/
- Kubernetes Pod Security Standards: https://kubernetes.io/docs/concepts/security/pod-security-standards/
- Kubernetes Secrets good practices: https://kubernetes.io/docs/concepts/security/secrets-good-practices/
- Spring Boot Kubernetes probes and main-port availability groups: https://docs.spring.io/spring-boot/reference/actuator/endpoints.html#actuator.endpoints.kubernetes-probes
- k6 open and closed workload models: https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/open-vs-closed/

## Background References

- AWS Builders' Library: https://aws.amazon.com/builders-library/
- The Tail at Scale: https://research.google/pubs/the-tail-at-scale/
- Kubernetes liveness, readiness, and startup probes: https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/
