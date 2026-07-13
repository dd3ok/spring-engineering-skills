from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

from skill_utils import is_link_or_junction


SCHEMA_VERSION = "spring-behavior-artifact/1"
CASE_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
MAX_FILES = 5_000
MAX_TOTAL_BYTES = 64 * 1024 * 1024
CHUNK_BYTES = 1024 * 1024


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def tree_files(root: Path) -> dict[str, str]:
    try:
        resolved_root = root.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"artifact root does not exist: {root}") from error
    if not resolved_root.is_dir() or is_link_or_junction(root):
        raise ValueError(f"artifact root is not a regular directory: {root}")
    files: dict[str, str] = {}
    total_bytes = 0
    try:
        for current, directories, filenames in os.walk(resolved_root, followlinks=False):
            current_path = Path(current)
            relative_directory = current_path.relative_to(resolved_root)
            directories.sort()
            filenames.sort()
            if not relative_directory.parts and ".git" in directories:
                directories.remove(".git")
            for directory in directories:
                candidate = current_path / directory
                if is_link_or_junction(candidate):
                    relative = candidate.relative_to(resolved_root).as_posix()
                    raise ValueError(f"artifact tree contains a linked path: {relative}")
            for filename in filenames:
                if not relative_directory.parts and filename == ".git":
                    continue
                entry = current_path / filename
                relative = entry.relative_to(resolved_root)
                if is_link_or_junction(entry):
                    raise ValueError(
                        f"artifact tree contains a linked path: {relative.as_posix()}"
                    )
                if not entry.is_file():
                    raise ValueError(
                        f"artifact tree contains a non-regular file: {relative.as_posix()}"
                    )
                if len(files) >= MAX_FILES:
                    raise ValueError(f"artifact tree exceeds {MAX_FILES} files")
                total_bytes += entry.stat().st_size
                if total_bytes > MAX_TOTAL_BYTES:
                    raise ValueError(f"artifact tree exceeds {MAX_TOTAL_BYTES} bytes")
                files[relative.as_posix()] = file_digest(entry)
    except OSError as error:
        raise ValueError(f"artifact tree could not be inspected: {root}") from error
    return files


def build_manifest(case_id: str, fixture: Path, workspace: Path) -> dict[str, object]:
    if CASE_ID.fullmatch(case_id) is None:
        raise ValueError("case_id is invalid")
    try:
        if fixture.resolve(strict=True) == workspace.resolve(strict=True):
            raise ValueError("fixture and workspace must be different directories")
    except OSError as error:
        raise ValueError("fixture and workspace must exist") from error
    before = tree_files(fixture)
    after = tree_files(workspace)
    changes: list[dict[str, str | None]] = []
    for path in sorted(set(before) | set(after)):
        before_sha256 = before.get(path)
        after_sha256 = after.get(path)
        if before_sha256 == after_sha256:
            continue
        changes.append(
            {
                "path": path,
                "before_sha256": before_sha256,
                "after_sha256": after_sha256,
            }
        )
    canonical = json.dumps(
        changes,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return {
        "schema_version": SCHEMA_VERSION,
        "case_id": case_id,
        "workspace_diff_sha256": hashlib.sha256(canonical).hexdigest(),
        "changed_paths": [change["path"] for change in changes],
        "changes": changes,
    }


def validate_output_path(output: Path, fixture: Path, workspace: Path) -> None:
    resolved_output = output.resolve()
    for label, root in (("fixture", fixture), ("workspace", workspace)):
        try:
            resolved_output.relative_to(root.resolve(strict=True))
        except ValueError:
            continue
        except OSError as error:
            raise ValueError(f"{label} root does not exist") from error
        raise ValueError(f"output must be outside the {label} tree")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture a content-addressed diff manifest for a behavior repository fixture."
    )
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.output is not None:
            validate_output_path(args.output, args.fixture, args.workspace)
        manifest = build_manifest(args.case_id, args.fixture, args.workspace)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"ERROR: {error}")
        return 1
    payload = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    if args.output is None:
        print(payload, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
