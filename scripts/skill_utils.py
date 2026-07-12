from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / "skills"
NAME_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
RUNTIME_PATH_PATTERN = re.compile(r"`((?:references|scripts|assets)/[^`]+)`")
MIN_PYTHON = (3, 12)


def require_supported_python(version=None) -> None:
    actual = version or sys.version_info
    if tuple(actual[:2]) < MIN_PYTHON:
        raise RuntimeError("Python 3.12 or newer is required for junction-safe skill tooling")


require_supported_python()


def is_link_or_junction(path: Path) -> bool:
    try:
        return path.is_symlink() or bool(getattr(path, "is_junction", lambda: False)())
    except OSError:
        return True


def resolves_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=True).relative_to(root.resolve(strict=True))
        return True
    except (OSError, ValueError):
        return False


def skill_directories() -> tuple[Path, ...]:
    if not SKILLS_ROOT.is_dir():
        return ()
    return tuple(sorted(path for path in SKILLS_ROOT.iterdir() if path.is_dir() and (path / "SKILL.md").is_file()))


def parse_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    try:
        label = path.relative_to(ROOT)
    except ValueError:
        label = path
    if not text.startswith("---\n"):
        raise ValueError(f"{label} must start with YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError(f"{label} frontmatter is not closed")
    result: dict[str, str] = {}
    lines = text[4:end].splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line or line[:1].isspace() or ":" not in line:
            raise ValueError(f"unsupported frontmatter line in {label}: {line}")
        key, value = line.split(":", 1)
        key = key.strip()
        if key in result:
            raise ValueError(f"duplicate frontmatter key in {label}: {key}")
        value = value.strip()
        if value in {">", ">-", "|", "|-"}:
            block: list[str] = []
            index += 1
            while index < len(lines) and (not lines[index] or lines[index][:1].isspace()):
                block.append(lines[index].strip())
                index += 1
            result[key] = "\n".join(block) if value.startswith("|") else " ".join(item for item in block if item)
            continue
        result[key] = value.strip("'\"")
        index += 1
    return result, text[end + len("\n---\n") :].lstrip("\r\n")


def skill_name(skill_dir: Path) -> str:
    frontmatter, _ = parse_frontmatter(skill_dir / "SKILL.md")
    return frontmatter.get("name", "")


def runtime_paths(skill_dir: Path) -> tuple[Path, ...]:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    root = skill_dir.resolve()
    result: list[Path] = []
    for value in sorted(set(RUNTIME_PATH_PATTERN.findall(text))):
        relative = Path(value)
        resolved = (skill_dir / relative).resolve()
        try:
            resolved.relative_to(root)
        except ValueError as error:
            raise ValueError(f"runtime path escapes skill root: {skill_dir.name}/{value}") from error
        if not resolved.is_file():
            raise ValueError(f"missing runtime path: {skill_dir.name}/{value}")
        result.append(relative)
    return tuple(result)
