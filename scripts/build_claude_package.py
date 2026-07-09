from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist" / "claude"


def build_skill_md() -> str:
    source = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    if not source.startswith("---\n"):
        raise SystemExit("SKILL.md must start with YAML frontmatter")

    marker = "\n---"
    end = source.find(marker, 4)
    if end == -1:
        raise SystemExit("SKILL.md frontmatter is not closed")

    frontmatter = source[4:end].strip().splitlines()
    body = source[end + len(marker) :].lstrip("\r\n")

    rendered: list[str] = []
    inserted = False
    for line in frontmatter:
        if line.startswith("disable-model-invocation:"):
            continue
        rendered.append(line)
        if line.startswith("description:") and not inserted:
            rendered.append("disable-model-invocation: true")
            inserted = True

    if not inserted:
        rendered.append("disable-model-invocation: true")

    return "---\n" + "\n".join(rendered) + "\n---\n\n" + body


def ensure_safe_output() -> None:
    out = OUT.resolve()
    root = ROOT.resolve()
    if root not in out.parents:
        raise SystemExit(f"Refusing to write outside skill root: {out}")


def main() -> None:
    ensure_safe_output()
    if OUT.exists():
        shutil.rmtree(OUT)

    OUT.mkdir(parents=True)
    (OUT / "SKILL.md").write_text(build_skill_md(), encoding="utf-8", newline="\n")
    shutil.copytree(ROOT / "references", OUT / "references")
    print(f"Claude package written to {OUT}")


if __name__ == "__main__":
    main()
