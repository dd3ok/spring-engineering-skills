from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import capture_behavior_artifact  # noqa: E402


class CaptureBehaviorArtifactTests(unittest.TestCase):
    def test_manifest_records_added_changed_and_deleted_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / "fixture"
            workspace = root / "workspace"
            fixture.mkdir()
            (fixture / "changed.txt").write_text("before", encoding="utf-8")
            (fixture / "deleted.txt").write_text("deleted", encoding="utf-8")
            shutil.copytree(fixture, workspace, dirs_exist_ok=True)
            (workspace / "changed.txt").write_text("after", encoding="utf-8")
            (workspace / "deleted.txt").unlink()
            (workspace / "added.txt").write_text("added", encoding="utf-8")

            manifest = capture_behavior_artifact.build_manifest(
                "implementation-case", fixture, workspace
            )

        self.assertEqual(
            manifest["changed_paths"],
            ["added.txt", "changed.txt", "deleted.txt"],
        )
        self.assertRegex(str(manifest["workspace_diff_sha256"]), r"^[a-f0-9]{64}$")
        changes = {change["path"]: change for change in manifest["changes"]}
        self.assertIsNone(changes["added.txt"]["before_sha256"])
        self.assertIsNone(changes["deleted.txt"]["after_sha256"])

    def test_identical_trees_have_a_stable_empty_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / "fixture"
            workspace = root / "workspace"
            fixture.mkdir()
            workspace.mkdir()
            first = capture_behavior_artifact.build_manifest("empty-case", fixture, workspace)
            second = capture_behavior_artifact.build_manifest("empty-case", fixture, workspace)
        self.assertEqual(first, second)
        self.assertEqual(first["changed_paths"], [])

    def test_top_level_git_metadata_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / "fixture"
            workspace = root / "workspace"
            fixture.mkdir()
            workspace.mkdir()
            (workspace / ".git").write_text("gitdir: elsewhere", encoding="utf-8")
            manifest = capture_behavior_artifact.build_manifest("git-case", fixture, workspace)
        self.assertEqual(manifest["changed_paths"], [])

    def test_same_directory_and_invalid_case_id_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "different directories"):
                capture_behavior_artifact.build_manifest("valid-case", root, root)
            other = root / "other"
            other.mkdir()
            with self.assertRaisesRegex(ValueError, "case_id"):
                capture_behavior_artifact.build_manifest("Invalid Case", root, other)

    def test_manifest_output_must_stay_outside_evaluated_trees(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / "fixture"
            workspace = root / "workspace"
            fixture.mkdir()
            workspace.mkdir()
            with self.assertRaisesRegex(ValueError, "outside the workspace"):
                capture_behavior_artifact.validate_output_path(
                    workspace / "manifest.json", fixture, workspace
                )
            capture_behavior_artifact.validate_output_path(
                root / "manifest.json", fixture, workspace
            )

    def test_linked_fixture_content_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / "fixture"
            workspace = root / "workspace"
            fixture.mkdir()
            workspace.mkdir()
            target = root / "target.txt"
            target.write_text("target", encoding="utf-8")
            try:
                (fixture / "linked.txt").symlink_to(target)
            except OSError as error:
                self.skipTest(f"symbolic links are unavailable: {error}")
            with self.assertRaisesRegex(ValueError, "linked path"):
                capture_behavior_artifact.build_manifest("linked-case", fixture, workspace)


if __name__ == "__main__":
    unittest.main()
