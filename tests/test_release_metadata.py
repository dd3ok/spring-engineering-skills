from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReleaseMetadataTests(unittest.TestCase):
    def test_version_is_consistent_across_release_documents(self) -> None:
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        self.assertIn(f"**{version} (public beta)**", (ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertIn(f"**{version}(public beta)**", (ROOT / "README.ko.md").read_text(encoding="utf-8"))
        self.assertIn(f"| Suite release | `{version}` (public beta) |", (ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertIn(f"| 스킬 모음 릴리스 | `{version}` (public beta) |", (ROOT / "README.ko.md").read_text(encoding="utf-8"))
        self.assertRegex(
            (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"),
            rf"(?m)^## {re.escape(version)} - \d{{4}}-\d{{2}}-\d{{2}}$",
        )
        collector = (
            ROOT / "skills" / "spring-evidence-collector" / "scripts" / "collect_evidence.py"
        ).read_text(encoding="utf-8")
        self.assertIn(f'"collector_version": "{version}"', collector)

    def test_apache_license_is_present_and_linked(self) -> None:
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("Apache License", license_text)
        self.assertIn("Version 2.0, January 2004", license_text)
        self.assertIn("END OF TERMS AND CONDITIONS", license_text)
        self.assertIn("[Apache License 2.0](LICENSE)", (ROOT / "README.md").read_text(encoding="utf-8"))
        for skill in (ROOT / "skills").iterdir():
            if skill.is_dir():
                self.assertEqual((skill / "LICENSE").read_text(encoding="utf-8"), license_text)
        self.assertIn("`SKILL.md`, `LICENSE`, `references/`", (ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertIn("`SKILL.md`, `LICENSE`, `references/`", (ROOT / "README.ko.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
