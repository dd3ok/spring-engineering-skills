from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from skill_utils import parse_frontmatter  # noqa: E402


class ApplicationDeveloperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = ROOT / "skills" / "spring-application-developer"
        self.frontmatter, _ = parse_frontmatter(self.root / "SKILL.md")
        self.skill = (self.root / "SKILL.md").read_text(encoding="utf-8")
        self.playbook = (self.root / "references" / "implementation-playbook.md").read_text(
            encoding="utf-8"
        )

    def test_description_owns_changes_without_absorbing_peer_outputs(self) -> None:
        description = self.frontmatter["description"]
        for value in (
            "create a Spring Boot application",
            "working repository changes as the primary output",
            "dependencies, or build declarations",
            "spring-evidence/1 or spring-upgrade-plan/2 consumer implementations",
            "review-only findings",
            "exact supported-version verification needed by that implementation",
            "standalone target selection or staged upgrade planning",
            "runtime diagnosis",
        ):
            self.assertIn(value, description)

    def test_workflow_preserves_unrelated_changes_and_verification_truth(self) -> None:
        for value in (
            "Preserve pre-existing and unrelated worktree changes",
            "Run repository-provided verification only when",
            "Do not claim a build, test, migration, or runtime check passed",
            "spring-engineering-review",
            "spring-upgrade-planner",
            "`spring-upgrade-plan/2` consumers",
        ):
            self.assertIn(value, self.skill)

    def test_playbook_pins_proxy_and_verification_boundaries(self) -> None:
        for value in (
            "Self-invocation does not trigger proxy-based transactions",
            "narrowest test level",
            "Verification Ladder",
            "Separate passed, failed, skipped, and unrun checks",
            "Spring Boot BOM and minimal starters",
            "Problem Details",
        ):
            self.assertIn(value, self.playbook)

    def test_compound_request_handoff_is_documented_in_both_languages(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        readme_ko = (ROOT / "README.ko.md").read_text(encoding="utf-8")
        self.assertIn('compound "analyze and fix" request', readme)
        self.assertIn("final output must be repository changes", readme)
        self.assertIn('"분석하고 고쳐줘"', readme_ko)
        self.assertIn("최종 결과가 저장소 변경", readme_ko)

    def test_greenfield_version_verification_does_not_overlap_upgrade_planning(self) -> None:
        planner, _ = parse_frontmatter(ROOT / "skills" / "spring-upgrade-planner" / "SKILL.md")
        self.assertIn("as the primary output", planner["description"])
        self.assertIn("incidental to a requested greenfield implementation", planner["description"])


if __name__ == "__main__":
    unittest.main()
