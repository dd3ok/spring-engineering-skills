# Spring Best Practice Skill

Explicit-triggered Agent Skill for Spring and Spring Boot review work. It focuses on architecture, production readiness, security, data access, messaging, batch, AI, API design, migration risk, and operational tradeoffs.

This repository is the distribution package. Runtime instructions live in `SKILL.md`; heavier domain rules live in `references/` and are loaded only when the request needs them.

## Activation

Use one of these explicit activation paths:

- `$spring-best-practice-skill`
- `/spring-best-practice-skill`
- `spring bp`, after the target runtime has been validated to route that alias

Do not rely on ordinary Spring wording to trigger the skill. The package is intentionally explicit-first.

## Vendor Compatibility

Codex/OpenAI:

- Uses the portable `SKILL.md` with `name` and `description` frontmatter.
- Includes `agents/openai.yaml` with `policy.allow_implicit_invocation: false`, so Codex does not select the skill implicitly from general Spring prompts.
- Guaranteed explicit path is `$spring-best-practice-skill` or selecting it from `/skills`.
- Repo-scoped install path is `.agents/skills/spring-best-practice-skill/`; user-scoped install path is `$HOME/.agents/skills/spring-best-practice-skill/`.

Claude Code:

- Direct invocation is based on the skill directory name, so the expected command is `/spring-best-practice-skill`.
- The shared `SKILL.md` intentionally does not include Claude-only `disable-model-invocation: true`.
- If a Claude-only package must block all model-triggered invocation, create a Claude-specific copy with `disable-model-invocation: true`.
- Install as `~/.claude/skills/spring-best-practice-skill/`, `.claude/skills/spring-best-practice-skill/`, or as part of a Claude plugin.

Antigravity:

- Uses the same open Agent Skills layout: a folder containing `SKILL.md` plus optional supporting files.
- Preferred project/workspace install path is `<project-root>/.agents/skills/spring-best-practice-skill/`.
- Official Google codelabs describe global product scope at `~/.gemini/config/skills/`. They also note that Antigravity may see `~/.agents/skills/`, while Antigravity CLI may require copying global skills to `~/.gemini/antigravity-cli/skills/`.
- Keep the description narrow and validate trigger behavior in the specific Antigravity runtime before relying on aliases.

See `references/vendor-compatibility.md` for maintenance notes.

## Package Layout

```text
spring-best-practice-skill/
|-- SKILL.md
|-- agents/
|   `-- openai.yaml
`-- references/
    |-- api-protocol-rules.md
    |-- data-access-rules.md
    |-- messaging-rules.md
    |-- official-docs.md
    |-- review-rules.md
    |-- spring-ai-rules.md
    |-- spring-batch-rules.md
    `-- vendor-compatibility.md
```

## Scope

The baseline review rules cover core Spring and Spring Boot work: configuration, dependency boundaries, HTTP clients and timeouts, security, observability, transactions, Redis/Kafka usage, virtual threads, migrations, and production rollout risks.

Focused references add deeper routing for:

- Spring AI, LLM/RAG, vector stores, tool calling, MCP, and evaluations.
- Spring Batch jobs, chunk processing, restartability, partitioning, and scheduling.
- Messaging with Kafka-adjacent Spring patterns, RabbitMQ/AMQP, Pulsar, Spring Integration, Spring Cloud Stream, and JMS.
- API/protocol concerns such as GraphQL, gRPC, Authorization Server, Session, HATEOAS, SOAP/Web Services, and LDAP.
- Data-access strategy beyond core JPA/JDBC/R2DBC, including jOOQ, NoSQL, and Spring Data REST.

## Validation

Run the structural validator from the Codex skill creator:

```powershell
python "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" .
```

Suggested maintenance checks:

```powershell
git diff --check
```

Before release, also search for stale trigger aliases and vendor-only fields so the shared `SKILL.md` stays portable.

## Official References

- [OpenAI Codex Agent Skills](https://developers.openai.com/codex/skills)
- [OpenAI Codex customization guide](https://developers.openai.com/codex/concepts/customization)
- [Claude Code skills documentation](https://code.claude.com/docs/en/skills)
- [Google Antigravity skills authoring codelab](https://codelabs.developers.google.com/getting-started-with-antigravity-skills)
- [Google Antigravity CLI skills codelab](https://codelabs.developers.google.com/antigravity/how-to-create-agent-skills-for-antigravity-cli)
