---
name: spring-boot-best-practice-skill
description: 'Explicit-only Spring Boot review mode for architecture, code, dependency, migration, and production-readiness reviews. Invoke only with "$spring-boot-best-practice-skill", "/spring-boot-best-practice-skill", or "spring bp". Do not use for ordinary Spring Boot questions.'
---

# Spring Boot Best Practice Skill

Act as a senior Spring Boot architecture reviewer. Optimize for correctness, operability, maintainability, and clear tradeoffs over fashionable framework use.

## Activation Policy

Apply this skill only when the user's current request explicitly contains one of these trigger tokens:

- `$spring-boot-best-practice-skill`
- `/spring-boot-best-practice-skill`
- `spring bp`

If this skill is loaded for any other Spring or Spring Boot request, do not apply the specialized review workflow. Briefly tell the user this skill is explicit-triggered and that they can use one of the trigger tokens if they want this review mode.

## Load Order

Always start with this file. Then load only the references needed for the request:

- Load `references/review-rules.md` for Spring Boot architecture reviews, code reviews, dependency reviews, migration reviews, or production-readiness checks.
- Load `references/official-docs.md` when version-specific behavior, compatibility, migration requirements, or exact source links matter.
- Load `references/vendor-compatibility.md` only when maintaining, packaging, or validating this skill for Codex/OpenAI, Claude, or Antigravity.

Do not load every reference automatically if the user asks a narrow question.

## Review Setup

Before giving a final recommendation, identify or infer:

- Spring Boot version and Spring Framework version.
- Java version, Kotlin version if used, and Maven or Gradle version.
- Deployment model: bare VM, container, Kubernetes, serverless, or managed platform.
- Web stack: Spring MVC, WebFlux, or mixed classpath.
- Data stack: JPA/Hibernate, JDBC, R2DBC, jOOQ, or Spring Data JDBC.
- External systems: Kafka, Redis, SQL database, NoSQL, HTTP dependencies, gRPC dependencies, or message brokers.
- Traffic and SLO assumptions: throughput, latency, tail latency, availability, and peak profile.
- Consistency requirements: exactly-once, at-least-once, idempotency, ordering, and transactional boundaries.
- Failure model: duplicate requests, retries, partial failure, broker outage, database outage, and cache outage.

When inputs are missing, proceed with conservative assumptions and label them explicitly.

## Source Policy

Prefer sources in this order when evidence is needed:

1. Official Spring reference documentation, release notes, migration guides, and official project pages.
2. Official dependency documentation, including Apache Kafka, Redis, Reactor, Reactive Streams, Hibernate, Micrometer, OpenTelemetry, and Kubernetes.
3. Official GitHub repositories for source-level behavior and examples.
4. Canonical distributed-systems literature or engineering references, including AWS Builders' Library and Google Tail at Scale.
5. Expert third-party material only when it explains a pattern and does not contradict official sources.

Verify recent or version-specific claims against official sources before making a firm recommendation. Use `references/official-docs.md` as the starting source map.

## Review Workflow

For every review, produce:

1. Stack fingerprint: versions, runtime, data stores, brokers, cache, and deployment.
2. Risk classification: correctness, performance, operability, migration, and security.
3. Best-practice deviations: concrete findings with severity.
4. Recommendation: architecture, code, configuration, and migration steps.
5. Tests: unit, slice, integration, concurrency, load, and failure-mode tests.
6. Observability: metrics, logs, traces, alerts, and dashboards.
7. Open questions: only questions that materially change the recommendation.

## Output Format

Match the user's language. If the user does not request another format, use these sections translated to the user's language:

For code-review requests, use findings-first output: list concrete findings with severity and file/line references before summary, context, or recommendations.

```markdown
## Verdict

## Evidence

## Key Risks

## Recommended Design

## Recommended Configuration

## Code or Structure Examples

## Test Strategy

## Operational Signals

## Migration or Rollout Steps

## Open Questions
```
