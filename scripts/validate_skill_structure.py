from __future__ import annotations

import re

from skill_utils import NAME_PATTERN, ROOT, SKILLS_ROOT, is_link_or_junction, parse_frontmatter, resolves_within, runtime_paths, skill_directories
from validate_source_policy import validate_source_policy


FORBIDDEN_VENDOR_PATHS = (
    ".agents",
    ".claude-plugin",
    ".codex-plugin",
    "docs/vendor-compatibility.md",
    "scripts/build_claude_package.py",
    "scripts/build_claude_packages.py",
    "scripts/validate_claude_package.py",
    "scripts/validate_claude_packages.py",
    "tests/test_claude_package.py",
)
RESOURCE_TOKEN_PATTERN = re.compile(r"`([^`\s/\\]+)`")


def validate_vendor_neutral(root, errors: list[str]) -> None:
    for relative in FORBIDDEN_VENDOR_PATHS:
        if (root / relative).exists():
            errors.append(f"vendor-specific path is not allowed: {relative}")


def validate_resource_references(skill_dir, errors: list[str]) -> None:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    runtime_files = {
        path.name
        for directory_name in ("references", "scripts", "assets")
        if (skill_dir / directory_name).is_dir()
        for path in (skill_dir / directory_name).rglob("*")
        if path.is_file()
    }
    for token in RESOURCE_TOKEN_PATTERN.findall(text):
        if "/" not in token and "\\" not in token and token in runtime_files:
            errors.append(f"runtime resource must use a skill-root-relative path: {skill_dir.name}/SKILL.md: {token}")


def validate_skill(skill_dir, errors: list[str]) -> None:
    relative = skill_dir.relative_to(ROOT)
    if is_link_or_junction(skill_dir) or not resolves_within(skill_dir, SKILLS_ROOT):
        errors.append(f"skill directory cannot be linked or outside skills root: {relative}")
        return
    try:
        frontmatter, _ = parse_frontmatter(skill_dir / "SKILL.md")
    except ValueError as error:
        errors.append(str(error))
        return
    if set(frontmatter) != {"name", "description"}:
        errors.append(f"{relative}/SKILL.md frontmatter must contain only name and description")
    name = frontmatter.get("name", "")
    if not 1 <= len(name) <= 64 or NAME_PATTERN.fullmatch(name) is None:
        errors.append(f"invalid skill name: {name or relative.name}")
    if name != skill_dir.name:
        errors.append(f"skill directory/name mismatch: {relative} != {name}")
    description = frontmatter.get("description", "")
    if not 1 <= len(description) <= 1024:
        errors.append(f"description must contain 1 to 1024 characters: {name}")
    if len((skill_dir / "SKILL.md").read_text(encoding="utf-8").splitlines()) >= 500:
        errors.append(f"SKILL.md must stay under 500 lines: {name}")
    validate_resource_references(skill_dir, errors)
    try:
        runtime_paths(skill_dir)
    except ValueError as error:
        errors.append(str(error))
    for directory_name in ("references", "scripts", "assets"):
        directory = skill_dir / directory_name
        if directory.is_dir():
            if is_link_or_junction(directory) or not resolves_within(directory, skill_dir):
                errors.append(f"runtime directory cannot be linked or outside skill root: {directory.relative_to(ROOT)}")
                continue
            for path in directory.rglob("*"):
                if is_link_or_junction(path) or not resolves_within(path, skill_dir):
                    errors.append(f"skill runtime path cannot be linked or outside skill root: {path.relative_to(ROOT)}")
    for reference in sorted((skill_dir / "references").glob("*.md")):
        lines = reference.read_text(encoding="utf-8").splitlines()
        if len(lines) > 100 and "## Contents" not in lines:
            errors.append(f"reference over 100 lines needs Contents: {reference.relative_to(ROOT)}")
    if (skill_dir / "agents").exists():
        errors.append(f"vendor-specific agents metadata is not allowed: {name}")


def validate_structure() -> list[str]:
    errors: list[str] = []
    validate_vendor_neutral(ROOT, errors)
    if (ROOT / "SKILL.md").exists() or (ROOT / "agents").exists() or (ROOT / "references").exists():
        errors.append("suite root must not retain a single-skill SKILL.md, agents/, or references/")
    skills = skill_directories()
    if not skills:
        errors.append("no skills found")
    if SKILLS_ROOT.is_dir():
        for entry in SKILLS_ROOT.iterdir():
            if entry.is_dir() and not (entry / "SKILL.md").is_file():
                errors.append(f"skill directory is missing SKILL.md: {entry.relative_to(ROOT)}")
            elif not entry.is_dir():
                errors.append(f"skills root may contain only skill directories: {entry.relative_to(ROOT)}")
    for skill_dir in skills:
        validate_skill(skill_dir, errors)
    errors.extend(validate_source_policy())
    return errors


def main() -> int:
    errors = validate_structure()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"{len(skill_directories())} vendor-neutral skills are structurally valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
