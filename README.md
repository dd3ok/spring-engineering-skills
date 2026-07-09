# Spring Best Practice Skill

[한국어 README](README.ko.md)

A portable Agent Skill that gives Codex, Claude Code, Antigravity, and other Agent Skills clients a findings-first Spring Boot reviewer.

Use it when you want an AI coding agent to review Spring or Spring Boot architecture, production readiness, dependency choices, migrations, security, data access, messaging, batch jobs, Spring AI usage, HTTP clients, API protocols, and rollout risk.

## When To Use

Good fits:

- Reviewing a Spring Boot service before production release
- Reviewing Spring architecture, module boundaries, configuration, or dependency choices
- Checking security, observability, transaction, HTTP client, cache, messaging, scheduling, batch, or data-access risks
- Reviewing Spring AI, RAG, ChatClient, vector store, tool-calling, or model-provider failure modes
- Planning a major upgrade involving Spring Boot, Spring Framework, Spring Security, Spring Data, Spring Cloud, Java, Kotlin, Jakarta, Maven, or Gradle
- Challenging an architecture proposal, migration plan, or production-readiness claim

Poor fits:

- Basic Spring explanations, such as how `@Transactional` works
- Generic Java help without a Spring review surface
- Broad best-practice summaries without code, dependencies, design, or operating assumptions to review

## How It Reviews

The skill starts with `SKILL.md`, then loads focused reference files only when the request needs them. Reviews should lead with concrete findings, severity, evidence, and affected files or components before broader recommendations.

Default review shape:

```markdown
## Findings
## Verdict
## Evidence
## Recommendations
## Tests
## Operations
## Open Questions
```

Missing inputs should become conservative assumptions, not invented facts. Recent or version-specific claims should be checked against official Spring documentation.

## Review Coverage

| Review surface | Reference |
| --- | --- |
| Core Spring/Spring Boot architecture, production readiness, security, observability, transactions | `references/review-rules.md` |
| Major version upgrades and dependency compatibility | `references/migration-rules.md` |
| HTTP clients, service-to-service deadlines, retries, pools, SSRF | `references/http-client-rules.md` |
| Redis cache, locks, topology, sessions, rate limiting, streams, pub/sub | `references/redis-rules.md` |
| Scheduling, `@Scheduled`, Quartz, async executors, overlap, virtual-thread scheduling | `references/scheduling-rules.md` |
| Spring AI, LLM/RAG, ChatClient, vector stores, tool calling, MCP, evaluations | `references/spring-ai-rules.md` |
| Spring Batch jobs, restartability, partitioning, chunk processing | `references/spring-batch-rules.md` |
| RabbitMQ/AMQP, Pulsar, Spring Integration, Spring Cloud Stream, JMS | `references/messaging-rules.md` |
| GraphQL, gRPC, Authorization Server, Session, HATEOAS, SOAP/Web Services, LDAP | `references/api-protocol-rules.md` |
| jOOQ, NoSQL, Spring Data REST, data-access strategy beyond core JPA/JDBC/R2DBC | `references/data-access-rules.md` |
| Official source links for version-specific claims | `references/official-docs.md` |
| Packaging and runtime compatibility | `references/vendor-compatibility.md` |

## Quick Start

Codex/OpenAI:

```text
$spring-best-practice-skill review this Spring Boot service for production readiness.
```

Claude Code:

```text
/spring-best-practice-skill review the Redis cache and lock design in this project.
```

The skill is explicit-first. In Codex, `agents/openai.yaml` sets `policy.allow_implicit_invocation: false`, so ordinary Spring prompts should not automatically load this review workflow.

## Install

### Codex/OpenAI

For repo-scoped use:

```text
<repo>/.agents/skills/spring-best-practice-skill/
```

For user-scoped use:

```text
$HOME/.agents/skills/spring-best-practice-skill/
```

Codex usually detects skill changes automatically. Restart Codex if the skill does not appear.

### Claude Code

Install as one of:

```text
~/.claude/skills/spring-best-practice-skill/
<repo>/.claude/skills/spring-best-practice-skill/
```

The shared `SKILL.md` stays portable and does not include Claude-only frontmatter. If you need a Claude-specific manual-only package, generate and validate it:

```powershell
python scripts/build_claude_package.py
python scripts/validate_claude_package.py
```

Publish the generated `dist/claude/` artifact for Claude-specific distribution.

### Antigravity

Prefer a project-scoped install while validating behavior:

```text
<project-root>/.agents/skills/spring-best-practice-skill/
```

Antigravity and Antigravity CLI skill discovery can differ by runtime. Validate the exact install path and invocation behavior before documenting aliases or global locations.

## Package Layout

```text
spring-best-practice-skill/
|-- SKILL.md
|-- README.md
|-- README.ko.md
|-- agents/
|   `-- openai.yaml
|-- scripts/
|   |-- build_claude_package.py
|   `-- validate_claude_package.py
`-- references/
    |-- api-protocol-rules.md
    |-- data-access-rules.md
    |-- http-client-rules.md
    |-- messaging-rules.md
    |-- migration-rules.md
    |-- official-docs.md
    |-- redis-rules.md
    |-- review-rules.md
    |-- scheduling-rules.md
    |-- spring-ai-rules.md
    |-- spring-batch-rules.md
    `-- vendor-compatibility.md
```

`dist/claude/` is generated release output. Do not hand-edit it.

## More Examples

Architecture review:

```text
$spring-best-practice-skill review this migration plan from Spring Boot 3.5 to 4.x. Focus on dependency compatibility, Jakarta changes, security behavior, and rollout risk.
```

Spring AI review:

```text
$spring-best-practice-skill review this Spring AI RAG design. Check retrieval boundaries, tool calling safety, evaluation coverage, and model-provider failure modes.
```

HTTP client review:

```text
$spring-best-practice-skill review our RestClient/WebClient timeout, retry, and SSRF posture.
```

## Validate

Run the Codex skill structural validator:

```powershell
python "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" .
```

Expected:

```text
Skill is valid!
```

Run repository maintenance checks:

```powershell
git diff --check
```

Build and validate the Claude package only when preparing a Claude release artifact:

```powershell
python scripts/build_claude_package.py
python scripts/validate_claude_package.py
```

Expected:

```text
Claude package is valid!
```

Do not run Codex `quick_validate.py` against `dist/claude/`; that generated package intentionally contains Claude-specific frontmatter.

## Release Checklist

- Keep `SKILL.md` frontmatter portable.
- Keep the skill description narrow enough to avoid accidental Spring-question activation.
- Confirm `agents/openai.yaml` still has `policy.allow_implicit_invocation: false`.
- Run `quick_validate.py`.
- Run `git diff --check`.
- Regenerate and validate `dist/claude/` only for Claude-specific releases.
- Smoke-test explicit invocation in each target runtime before publishing usage claims.
- Check `references/vendor-compatibility.md` before changing activation policy, install paths, or vendor-specific metadata.

## References

- [OpenAI Codex Agent Skills](https://developers.openai.com/codex/skills)
- [Claude Code skills documentation](https://code.claude.com/docs/en/skills)
- [Anthropic Agent Skills overview](https://console.anthropic.com/docs/en/agents-and-tools/agent-skills/overview)
- [Google Antigravity skills authoring codelab](https://codelabs.developers.google.com/getting-started-google-antigravity)
- [Google Antigravity CLI skills codelab](https://codelabs.developers.google.com/antigravity/how-to-create-agent-skills-for-antigravity-cli)
