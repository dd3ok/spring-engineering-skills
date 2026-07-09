# Spring Best Practice Skill

Explicitly triggered Agent Skill for Spring and Spring Boot review work. It focuses on architecture, production readiness, security, data access, messaging, batch, AI, API design, migration risk, and operational tradeoffs.

This repository is the portable source package. Runtime instructions live in `SKILL.md`; heavier domain rules live in `references/` and are loaded only when the request needs them. Vendor-specific package outputs are generated from this source.

## Activation

Documented loader triggers differ by runtime:

- Codex/OpenAI: `$spring-best-practice-skill` or selecting the skill from `/skills`.
- Claude Code: `/spring-best-practice-skill` when installed under the expected skill directory.
- Antigravity: validate trigger behavior in the specific runtime; prefer project-scoped `.agents/skills/spring-best-practice-skill/`.

After the skill has loaded, `spring bp` may be treated as an in-body local alias only when the target runtime has been validated. Do not document it as a portable loader trigger or cross-runtime command.

Do not rely on ordinary Spring wording to trigger the skill. The package is intentionally explicit-first.

## Vendor Compatibility

Codex/OpenAI:

- Uses the portable `SKILL.md` with `name` and `description` frontmatter.
- Includes `agents/openai.yaml` with `policy.allow_implicit_invocation: false`, so Codex does not select the skill implicitly from general Spring prompts.
- Documented explicit path is `$spring-best-practice-skill` or selecting it from `/skills`.
- Repo-scoped install path is `.agents/skills/spring-best-practice-skill/`; user-scoped install path is `$HOME/.agents/skills/spring-best-practice-skill/`.

Claude Code:

- Direct invocation is based on the skill directory name, so the expected command is `/spring-best-practice-skill`.
- The shared `SKILL.md` intentionally does not include Claude-only `disable-model-invocation: true`.
- If a Claude-only package must block all model-triggered invocation, run `python scripts/build_claude_package.py` and publish the generated `dist/claude/` artifact. In that mode, use `/spring-best-practice-skill` as the explicit command unless a separate Claude command/plugin alias has been implemented and validated.
- Install as `~/.claude/skills/spring-best-practice-skill/`, `.claude/skills/spring-best-practice-skill/`, or as part of a Claude plugin.

Antigravity:

- Uses the same open Agent Skills layout: a folder containing `SKILL.md` plus optional supporting files.
- Preferred project/workspace install path is `<project-root>/.agents/skills/spring-best-practice-skill/`.
- Official Google codelabs describe global product scope at `~/.gemini/config/skills/`; CLI examples also discover project skills from `.agents/skills/`.
- Keep the description narrow and validate trigger behavior in the specific Antigravity runtime before relying on aliases.

See `references/vendor-compatibility.md` for maintenance notes.

## Package Layout

```text
spring-best-practice-skill/
|-- SKILL.md
|-- agents/
|   `-- openai.yaml
|-- scripts/
|   |-- build_claude_package.py
|   `-- validate_claude_package.py
`-- references/
    |-- api-protocol-rules.md
    |-- data-access-rules.md
    |-- http-client-rules.md
    |-- migration-rules.md
    |-- messaging-rules.md
    |-- official-docs.md
    |-- redis-rules.md
    |-- review-rules.md
    |-- scheduling-rules.md
    |-- spring-ai-rules.md
    |-- spring-batch-rules.md
    `-- vendor-compatibility.md
```

`dist/claude/` is generated release output, not part of the portable source layout.

## Scope

The baseline review rules cover core Spring and Spring Boot work: configuration, dependency boundaries, HTTP clients and timeouts, security, validation, serialization, observability, transactions, Redis/Kafka usage, scheduling, virtual threads, migrations, and production rollout risks.

Focused references add deeper routing for:

- Spring AI, LLM/RAG, vector stores, tool calling, MCP, and evaluations.
- Spring Batch jobs, chunk processing, restartability, partitioning, and scheduling.
- Redis cache/session/lock design, streams/pubsub, topology, Sentinel/Cluster, and client behavior.
- `@Scheduled`, TaskScheduler/TaskExecutor, Quartz, cron, overlap prevention, and distributed job coordination.
- Messaging with Kafka-adjacent Spring patterns, RabbitMQ/AMQP, Pulsar, Spring Integration, Spring Cloud Stream, and JMS.
- API/protocol concerns such as GraphQL, gRPC, Gateway, WebSocket/RSocket, Authorization Server, Session, HATEOAS, SOAP/Web Services, and LDAP.
- Data-access strategy beyond core JPA/JDBC/R2DBC, including jOOQ, NoSQL, and Spring Data REST.
- HTTP client, service-to-service reliability, deadline, retry, pool, and SSRF reviews.
- Major Spring, Java, Kotlin, dependency, Jakarta, build, and runtime migrations.

## Validation

Run the structural validator from the Codex skill creator:

```powershell
python "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" .
```

Expected: `Skill is valid!`

Suggested maintenance checks:

```powershell
git diff --check
```

Build and validate the Claude manual-only package when preparing a Claude release artifact. Do not run the Codex `quick_validate.py` against `dist/claude`; that generated package intentionally contains Claude-only `disable-model-invocation: true` frontmatter.

```powershell
python scripts/build_claude_package.py
python scripts/validate_claude_package.py
```

Expected: `Claude package is valid!`

Routing smoke tests before release:

- Codex/OpenAI should trigger: `$spring-best-practice-skill review this Spring Boot service for production readiness`
- Codex/OpenAI should trigger: selecting the skill from `/skills`, then asking for a Spring Boot production-readiness review.
- Claude Code should trigger: `/spring-best-practice-skill review Redis cache and lock design`
- `spring bp` should be accepted only as a validated local alias after the skill is loaded, not assumed to be a portable loader trigger.
- Ordinary Spring prompts such as `Explain @Transactional in Spring` or `How do I create a Spring Boot controller?` should not trigger/load the skill; if a runtime loads it anyway, the skill should decline the specialized workflow.
- Spring AI, RAG, ChatClient, tool calling, or vector store requests should route to `references/spring-ai-rules.md`.
- jOOQ, NoSQL, Spring Data REST, or broad data-access strategy requests should route to `references/data-access-rules.md`.
- GraphQL, gRPC, Gateway, WebSocket/RSocket, Authorization Server, Session, HATEOAS, SOAP, or LDAP requests should route to `references/api-protocol-rules.md`.
- RabbitMQ/AMQP, Pulsar, Spring Integration, Spring Cloud Stream, JMS, or complex message-flow requests should route to `references/messaging-rules.md`.
- Redis cache/session/lock/topology request should route to `references/redis-rules.md`.
- Scheduled job, Quartz, overlap, async executor, or virtual-thread scheduler requests should route to `references/scheduling-rules.md`.
- Batch restartability request should route to `references/spring-batch-rules.md`.
- HTTP client timeout/SSRF request should route to `references/http-client-rules.md`.
- Major version upgrade request should route to `references/migration-rules.md`.

Before release, also search for stale trigger aliases and vendor-only fields so the shared `SKILL.md` stays portable.

## Official References

- [OpenAI Codex Agent Skills](https://developers.openai.com/codex/skills)
- [OpenAI Codex customization guide](https://developers.openai.com/codex/concepts/customization)
- [Claude Code skills documentation](https://code.claude.com/docs/en/skills)
- [Google Antigravity skills authoring codelab](https://codelabs.developers.google.com/getting-started-with-antigravity-skills)
- [Google Antigravity CLI skills codelab](https://codelabs.developers.google.com/antigravity/how-to-create-agent-skills-for-antigravity-cli)
