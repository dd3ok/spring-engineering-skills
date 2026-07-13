from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

from skill_utils import NAME_PATTERN, ROOT, SKILLS_ROOT, is_link_or_junction, parse_frontmatter, resolves_within, skill_directories
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
INLINE_CODE_PATTERN = re.compile(r"`([^`\r\n]+)`")
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]*\]\((<[^>]+>|[^)\s]+)(?:\s+['\"][^'\"]*['\"])?\)")
COMMAND_RESOURCE_PATTERN = re.compile(
    r"(?<![\w])((?:(?:\.\./)+|\.?/)?(?:references|scripts|assets)/[^\s`\"'<>]+)"
)
UNSAFE_LINK_RESOURCE_PATTERN = re.compile(r"^(?:(?:\.\./)+|/)(?:references|scripts|assets)/")
RUNTIME_DIRECTORIES = ("references", "scripts", "assets")


def validate_vendor_neutral(root, errors: list[str]) -> None:
    for relative in FORBIDDEN_VENDOR_PATHS:
        if (root / relative).exists():
            errors.append(f"vendor-specific path is not allowed: {relative}")


def _has_exact_case(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    current = root
    for part in relative.parts:
        try:
            names = {child.name for child in current.iterdir()}
        except OSError:
            return False
        if part not in names:
            return False
        current /= part
    return True


def _resource_tokens(text: str) -> tuple[set[str], set[str]]:
    inline = INLINE_CODE_PATTERN.findall(text)
    links = [target[1:-1] if target.startswith("<") and target.endswith(">") else target for target in MARKDOWN_LINK_PATTERN.findall(text)]
    rooted: set[str] = set()
    for link in links:
        clean = unquote(link.split("#", 1)[0])
        normalized = clean[2:] if clean.startswith("./") else clean
        resource_markers = tuple(f"{directory}/" for directory in RUNTIME_DIRECTORIES)
        if normalized.startswith(resource_markers) or UNSAFE_LINK_RESOURCE_PATTERN.match(clean):
            rooted.add(normalized)
    for value in inline:
        for match in COMMAND_RESOURCE_PATTERN.finditer(value):
            clean = unquote(match.group(1).split("#", 1)[0].rstrip(".,;:"))
            rooted.add(clean[2:] if clean.startswith("./") else clean)
    bare = {
        value.strip()
        for value in inline
        if value.strip() and "/" not in value and "\\" not in value and not value.startswith(("http:", "https:", "mailto:", "#"))
    }
    return rooted, bare


def validate_resource_references(skill_dir, errors: list[str]) -> None:
    skill_root = skill_dir.resolve()
    runtime_files = {
        path.name
        for directory_name in RUNTIME_DIRECTORIES
        if (skill_dir / directory_name).is_dir()
        for path in (skill_dir / directory_name).rglob("*")
        if path.is_file()
    }
    documents = [skill_dir / "SKILL.md"]
    references = skill_dir / "references"
    if references.is_dir():
        documents.extend(sorted(references.rglob("*.md")))

    for document in documents:
        text = document.read_text(encoding="utf-8")
        rooted, bare = _resource_tokens(text)
        label = document.relative_to(skill_dir).as_posix()
        for token in sorted(bare & runtime_files):
            errors.append(f"runtime resource must use a skill-root-relative path: {skill_dir.name}/{label}: {token}")
        for token in sorted(rooted):
            candidate = skill_dir / Path(token)
            try:
                resolved = candidate.resolve(strict=True)
                resolved.relative_to(skill_root)
            except (OSError, ValueError):
                errors.append(f"invalid runtime resource path: {skill_dir.name}/{label}: {token}")
                continue
            if not resolved.is_file() or is_link_or_junction(candidate) or not _has_exact_case(candidate, skill_dir):
                errors.append(f"invalid runtime resource path: {skill_dir.name}/{label}: {token}")

    declared, _ = _resource_tokens((skill_dir / "SKILL.md").read_text(encoding="utf-8"))
    declared = {path for path in declared if path.startswith("references/")}
    actual = {
        path.relative_to(skill_dir).as_posix()
        for path in references.rglob("*")
        if references.is_dir() and path.is_file()
    }
    for orphan in sorted(actual - declared):
        errors.append(f"reference must be linked directly from SKILL.md: {skill_dir.name}/{orphan}")


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
    for directory_name in RUNTIME_DIRECTORIES:
        directory = skill_dir / directory_name
        if directory.is_dir():
            if is_link_or_junction(directory) or not resolves_within(directory, skill_dir):
                errors.append(f"runtime directory cannot be linked or outside skill root: {directory.relative_to(ROOT)}")
                continue
            for path in directory.rglob("*"):
                if is_link_or_junction(path) or not resolves_within(path, skill_dir):
                    errors.append(f"skill runtime path cannot be linked or outside skill root: {path.relative_to(ROOT)}")
    for reference in sorted((skill_dir / "references").rglob("*.md")):
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
