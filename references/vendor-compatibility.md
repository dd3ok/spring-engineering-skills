# Vendor Compatibility Notes

Use this file only when maintaining or packaging the skill itself. Do not load it for normal Spring or Spring Boot reviews.

## Portable Base Contract

- Keep the shared `SKILL.md` as the portable source of truth.
- Keep YAML frontmatter minimal: `name` and `description` only unless all target vendors accept the field.
- Keep detailed review rules in `references/` and route to them from `SKILL.md`.
- Keep activation tokens in frontmatter `description`; keep vendor-specific loader behavior in `Activation Policy` and this file.
- Do not add vendor-specific control fields to the shared `SKILL.md` if they fail another vendor's validator.
- Do not check generated vendor packages into the portable source package. Generate them as release artifacts from the shared source.
- Keep `SKILL.md` under 500 lines and keep references one level deep from `SKILL.md`.
- Keep `description` under 1024 characters for the open Agent Skills contract and under Claude Code's 1536-character skill-listing cap.

## Explicit Trigger Policy

Shared activation tokens accepted by the skill body after it has been loaded:

- `$spring-best-practice-skill`
- `/spring-best-practice-skill`
- `spring bp`

Do not document all three as guaranteed loader triggers for every vendor.

Codex/OpenAI:

- Use the shared `SKILL.md`.
- Keep `agents/openai.yaml` with `policy.allow_implicit_invocation: false` for hard explicit-only behavior.
- Treat `$spring-best-practice-skill` or `/skills` selection as the documented explicit invocation path.
- Do not rely on `/spring-best-practice-skill` or `spring bp` as Codex loader triggers unless the specific runtime has been validated.
- Keep the default prompt aligned with `$spring-best-practice-skill`.
- Codex scans `.agents/skills` from the current working directory up to the repository root, plus `$HOME/.agents/skills` for user skills. It detects newly installed skills automatically, but restart Codex if a new skill does not appear.
- For reusable distribution beyond local or repo-scoped authoring, prefer packaging the skill as a Codex plugin.

Claude:

- Claude supports `disable-model-invocation: true` for user-invoked-only skills.
- Do not add `disable-model-invocation` to the shared `SKILL.md`; Claude-only fields are not part of the portable/OpenAI skill contract and should live in vendor-specific copies unless validated.
- Generate the Claude-only package with `python scripts/build_claude_package.py`, then validate it with `python scripts/validate_claude_package.py`. Treat `dist/claude/` as generated release output. Do not hand-edit `dist/claude/SKILL.md`; regenerate it from the shared source.
- Do not validate `dist/claude` with Codex `quick_validate.py`; that validator correctly rejects Claude-only frontmatter.
- Claude Code direct invocation uses the skill directory name, for example `/spring-best-practice-skill`; frontmatter `name` is mostly display metadata.
- If publishing a Claude-only package that must be hard manual-only, generate a Claude-specific copy of `SKILL.md` with `disable-model-invocation: true` and document the slash command.
- If the `spring bp` alias must keep working in Claude Code, do not use `disable-model-invocation`; rely on the strict description plus `Activation Policy` guard and validate runtime routing.
- Install as `~/.claude/skills/<skill-name>/SKILL.md`, `.claude/skills/<skill-name>/SKILL.md`, or a plugin skill.

Antigravity:

- Antigravity uses `SKILL.md` frontmatter metadata, especially the description, for discovery.
- Keep the description narrow and explicit-triggered.
- Keep detailed behavior out of frontmatter and in routed Markdown sections or reference files.
- Install project-scoped skills under `<project-root>/.agents/skills/<skill-name>/`; this is the safest cross-vendor repo layout.
- Official Antigravity codelabs describe global product scope as `~/.gemini/config/skills/`.
- Antigravity CLI examples also discover project skills from `.agents/skills/`.
- Prefer project-scoped `.agents/skills` for cross-vendor repos; use a global path only after validating the specific Antigravity runtime.
- Validate runtime behavior with Antigravity. Do not use Gemini CLI as a substitute for Antigravity trigger testing.
- No documented Antigravity frontmatter field equivalent to Claude Code's `disable-model-invocation` was found in the official codelabs; treat explicit-only as description plus body guard unless a platform-specific control becomes available.

## Official Vendor References

- OpenAI Codex Agent Skills: https://developers.openai.com/codex/skills
- Claude Code skills: https://docs.anthropic.com/en/docs/claude-code/skills
- Anthropic Agent Skills overview: https://console.anthropic.com/docs/en/agents-and-tools/agent-skills/overview
- Anthropic Skills API guide: https://console.anthropic.com/docs/en/build-with-claude/skills-guide
- Google Antigravity authoring codelab: https://codelabs.developers.google.com/getting-started-with-antigravity-skills
- Google Antigravity CLI codelab: https://codelabs.developers.google.com/antigravity/how-to-create-agent-skills-for-antigravity-cli
