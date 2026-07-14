from __future__ import annotations

import json
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

        reviewer = (
            ROOT / "skills" / "spring-engineering-review" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Keep this skill read-only", reviewer)
        self.assertIn(
            "hand implementation to `spring-application-developer` before editing",
            reviewer,
        )
        self.assertNotIn(
            "Keep review requests read-only unless the user explicitly asks for implementation",
            reviewer,
        )

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
        self.assertIn("Apply `references/greenfield-baseline-policy.json`", self.playbook)
        self.assertIn("spring-initializr-defaults/1", self.playbook)
        self.assertIn("sole selection algorithm", self.playbook)
        self.assertIn("compact user summary by default", self.playbook)
        self.assertIn("save a metadata snapshot or provenance artifact only when", self.playbook)
        self.assertIn("Do not infer a vendor LTS policy", self.playbook)
        sources = (
            self.root / "references" / "official-sources.md"
        ).read_text(encoding="utf-8")
        self.assertIn("https://start.spring.io/metadata/client", sources)

        policy = json.loads(
            (self.root / "references" / "greenfield-baseline-policy.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            policy["metadata"]["accept"],
            "application/vnd.initializr.v2.3+json",
        )
        self.assertEqual(
            policy["metadata"]["selection_algorithm"],
            "spring-initializr-defaults/1",
        )
        self.assertIn("highest-ga", policy["spring_boot"]["omitted"])
        self.assertIn("highest-ga", policy["spring_boot"]["version_line"])
        self.assertTrue(policy["constraints"]["do_not_infer_vendor_lts"])
        self.assertEqual(
            policy["metadata_backed_fields"]["project_type"],
            "user-choice-or-metadata-default-project-format",
        )
        self.assertIn("metadata_sha256", policy["provenance_required"])
        self.assertEqual(
            policy["user_summary_rules"]["metadata_sha256"],
            "first-12-lowercase-hex",
        )
        self.assertEqual(
            policy["user_summary_rules"]["retrieved_at_utc"],
            "RFC3339-UTC-seconds-with-Z",
        )
        self.assertIn("generation_parameters", policy["provenance_required"])
        self.assertLess(set(policy["user_summary_required"]), set(policy["provenance_required"]))
        self.assertEqual(
            policy["user_summary_rules"]["saved_artifact"],
            "never-create-without-an-explicit-user-request",
        )
        self.assertEqual(
            policy["metadata"]["saved_snapshot"],
            "user-requested-artifact-or-isolated-evaluation-evidence",
        )

        for source in (
            "https://docs.spring.io/spring-data/jpa/reference/",
            "https://docs.spring.io/spring-data/relational/reference/jdbc.html",
            "https://jdbc.postgresql.org/documentation/",
            "https://documentation.red-gate.com/flyway/reference",
            "https://maven.apache.org/tools/wrapper/",
            "https://docs.gradle.org/current/userguide/gradle_wrapper.html",
            "https://docs.spring.io/initializr/docs/current/reference/html/",
            "https://docs.spring.io/initializr/docs/current/api/io/spring/initializr/web/controller/ProjectMetadataController.html",
        ):
            self.assertIn(source, sources)

    def test_unpinned_greenfield_behavior_requires_implementation_not_refusal(self) -> None:
        cases = json.loads((ROOT / "evals" / "behavior-cases.json").read_text(encoding="utf-8"))
        case = next(
            item for item in cases if item["id"] == "developer-greenfield-unpinned-version"
        )
        self.assertEqual(case["artifact_mode"], "repository-fixture")
        self.assertTrue(any("continue implementation" in item for item in case["must"]))
        self.assertTrue(any("Initializr metadata algorithm" in item for item in case["must"]))
        self.assertTrue(any("compact user summary" in item for item in case["must"]))
        self.assertTrue(any("metadata hash" in item for item in case["must"]))
        self.assertIn(
            "Stop solely because the prompt does not pin an exact version",
            case["must_not"],
        )


if __name__ == "__main__":
    unittest.main()
