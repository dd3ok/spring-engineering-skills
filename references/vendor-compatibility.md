# Vendor Compatibility Notes

Use this file only when maintaining or packaging the skill itself. Do not load it for normal Spring Boot reviews.

## Portable Base Contract

- Keep the shared `SKILL.md` as the portable source of truth.
- Keep YAML frontmatter minimal: `name` and `description` only unless all target vendors accept the field.
- Keep detailed review rules in `references/` and route to them from `SKILL.md`.
- Keep explicit trigger tokens in both frontmatter `description` and the `Activation Policy` section.
- Do not add vendor-specific control fields to the shared `SKILL.md` if they fail another vendor's validator.
- Keep `SKILL.md` under 500 lines and keep references one level deep from `SKILL.md`.
- Keep `description` under 1024 characters for the open Agent Skills contract and under Claude Code's 1536-character skill-listing cap.

## Explicit Trigger Policy

Supported explicit trigger tokens:

- `$spring-boot-best-practice-skill`
- `/spring-boot-best-practice-skill`
- `spring bp`

Codex/OpenAI:

- Use the shared `SKILL.md`.
- Keep `agents/openai.yaml` with `policy.allow_implicit_invocation: false` for hard explicit-only behavior.
- Keep the default prompt aligned with one supported trigger token.

Claude:

- Claude supports `disable-model-invocation: true` for user-invoked-only skills.
- Do not add `disable-model-invocation` to the shared `SKILL.md`; Codex validation rejects unknown top-level frontmatter fields.
- Claude Code direct invocation uses the skill directory name, for example `/spring-boot-best-practice-skill`; frontmatter `name` is mostly display metadata.
- If publishing a Claude-only package that must be hard manual-only, generate a Claude-specific copy of `SKILL.md` with `disable-model-invocation: true` and document the slash command.
- If the `spring bp` alias must keep working in Claude Code, do not use `disable-model-invocation`; rely on the strict description plus `Activation Policy` guard.
- Install as `~/.claude/skills/<skill-name>/SKILL.md`, `.claude/skills/<skill-name>/SKILL.md`, or a plugin skill.

Antigravity:

- Antigravity routes primarily from `SKILL.md` frontmatter metadata, especially the description.
- Keep the description narrow and explicit-triggered.
- Keep detailed behavior out of frontmatter and in routed Markdown sections or reference files.
- Install project-scoped skills under `<project-root>/.agents/skills/<skill-name>/SKILL.md`.
- Install global Antigravity skills under `~/.gemini/config/skills/<skill-name>/SKILL.md`.
- Validate runtime behavior with Antigravity. Do not use Gemini CLI as a substitute for Antigravity trigger testing.
- No documented Antigravity frontmatter field equivalent to Claude Code's `disable-model-invocation` was found in the official codelabs; treat explicit-only as description plus body guard unless a platform-specific control becomes available.

## Official Vendor References

- OpenAI Codex Agent Skills: https://developers.openai.com/codex/skills
- Claude Code skills: https://docs.anthropic.com/en/docs/claude-code/skills
- Anthropic Agent Skills overview: https://console.anthropic.com/docs/en/agents-and-tools/agent-skills/overview
- Anthropic Skills API guide: https://console.anthropic.com/docs/en/build-with-claude/skills-guide
- Google Antigravity authoring codelab: https://codelabs.developers.google.com/getting-started-with-antigravity-skills
- Google Antigravity CLI codelab: https://codelabs.developers.google.com/antigravity/how-to-create-agent-skills-for-antigravity-cli
