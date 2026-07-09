from __future__ import annotations

import re

from build_claude_package import ROOT, build_skill_md, ensure_simple_frontmatter

PACKAGE = ROOT / "dist" / "claude"
MAX_PORTABLE_DESCRIPTION_CHARS = 1024


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise SystemExit("dist/claude/SKILL.md must start with YAML frontmatter")

    end = text.find("\n---", 4)
    if end == -1:
        raise SystemExit("dist/claude/SKILL.md frontmatter is not closed")

    lines = text[4:end].strip().splitlines()
    ensure_simple_frontmatter(lines, "dist/claude/SKILL.md")

    result: dict[str, str] = {}
    for line in lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip("'\"")
    description = result.get("description", "")
    if len(description) > MAX_PORTABLE_DESCRIPTION_CHARS:
        raise SystemExit(
            f"description must stay under {MAX_PORTABLE_DESCRIPTION_CHARS} characters for portable skill metadata"
        )
    return result


def main() -> None:
    skill = PACKAGE / "SKILL.md"
    refs = PACKAGE / "references"
    if not skill.exists():
        raise SystemExit("Missing dist/claude/SKILL.md; run scripts/build_claude_package.py")
    if not refs.is_dir():
        raise SystemExit("Missing dist/claude/references; run scripts/build_claude_package.py")

    text = skill.read_text(encoding="utf-8")
    expected = build_skill_md()
    if text != expected:
        raise SystemExit("dist/claude/SKILL.md is stale; run scripts/build_claude_package.py")

    frontmatter = parse_frontmatter(text)
    for key in ("name", "description"):
        if not frontmatter.get(key):
            raise SystemExit(f"Missing required frontmatter key: {key}")
    if frontmatter.get("disable-model-invocation") != "true":
        raise SystemExit("Claude package must set disable-model-invocation: true")

    missing: list[str] = []
    for match in sorted(set(re.findall(r"`(references/[^`]+\.md)`", text))):
        if not (PACKAGE / match).exists():
            missing.append(match)
    if missing:
        raise SystemExit("Missing referenced files: " + ", ".join(missing))

    source_refs = sorted(path.relative_to(ROOT / "references") for path in (ROOT / "references").glob("*.md"))
    package_refs = sorted(path.relative_to(refs) for path in refs.glob("*.md"))
    if source_refs != package_refs:
        raise SystemExit("dist/claude/references file set is stale; run scripts/build_claude_package.py")

    stale_refs = [
        str(path)
        for path in source_refs
        if (ROOT / "references" / path).read_bytes() != (refs / path).read_bytes()
    ]
    if stale_refs:
        raise SystemExit("dist/claude/references content is stale: " + ", ".join(stale_refs))

    print("Claude package is valid!")


if __name__ == "__main__":
    main()
