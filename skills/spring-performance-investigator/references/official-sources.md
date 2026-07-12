# Official and Canonical Sources

Checked on: 2026-07-12. Vendor documentation is normative for tool/runtime semantics; select the deployed version's documentation. The USE method and coordinated-omission material are advisory diagnostic methods.

- [Oracle `jfr` command](https://docs.oracle.com/en/java/javase/26/docs/specs/man/jfr.html) and [Oracle `jcmd`](https://docs.oracle.com/en/java/javase/26/docs/specs/man/jcmd.html) — Java 26 examples; switch both links to the deployed JDK line.
- [OpenJDK JDK 25](https://openjdk.org/projects/jdk/25/) — JDK 25 feature baseline and release status; use the deployed JDK's diagnostic documentation. Treat LTS duration as a distribution-vendor support policy, not a JVM performance property.
- [Spring Boot observability](https://docs.spring.io/spring-boot/reference/actuator/observability.html) and [metrics](https://docs.spring.io/spring-boot/reference/actuator/metrics.html) — Micrometer integration and runtime instrumentation.
- [Micrometer histograms and percentiles](https://docs.micrometer.io/micrometer/reference/concepts/histogram-quantiles.html) — aggregation and percentile tradeoffs.
- [Micrometer meter filters](https://docs.micrometer.io/micrometer/reference/concepts/meter-filters.html) — cardinality controls and meter limits.
- [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/specs/semconv/) — signal naming, stability, and migration controls.
- [Hibernate ORM releases](https://hibernate.org/orm/releases/) and [current user guide](https://docs.hibernate.org/orm/current/userguide/html_single/) — select the deployed Hibernate series and use its versioned guide; do not infer compatibility from the latest stable series.
- [HikariCP configuration](https://github.com/brettwooldridge/HikariCP#configuration-knobs-baby) — current project guidance; verify settings against the deployed release.
- [Kubernetes resource management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/) — CPU/memory requests, limits, and throttling behavior.
- [Brendan Gregg’s USE method](https://www.brendangregg.com/usemethod.html) — canonical resource utilization, saturation, and error checklist.
- [Google SRE monitoring distributed systems](https://sre.google/sre-book/monitoring-distributed-systems/) — latency, traffic, errors, and saturation signals.
- [The Tail at Scale](https://research.google/pubs/the-tail-at-scale/) — large-scale tail-latency behavior and mitigation research.
- [HdrHistogram coordinated-omission correction](https://hdrhistogram.github.io/HdrHistogram/JavaDoc/org/HdrHistogram/AbstractHistogram.html) — latency measurement distortion and correction.
