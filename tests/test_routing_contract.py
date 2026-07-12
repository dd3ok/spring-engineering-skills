from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_routing_contract  # noqa: E402


class RoutingContractTests(unittest.TestCase):
    def test_repository_contract_is_valid(self) -> None:
        self.assertEqual(validate_routing_contract.validate_contract(), [])

    def validate_modified_cases(self, mutate: Callable[[list[dict[str, object]]], None]) -> list[str]:
        cases = json.loads(validate_routing_contract.CASES_PATH.read_text(encoding="utf-8"))
        mutate(cases)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text(json.dumps(cases), encoding="utf-8")
            original = validate_routing_contract.CASES_PATH
            validate_routing_contract.CASES_PATH = path
            try:
                return validate_routing_contract.validate_contract()
            finally:
                validate_routing_contract.CASES_PATH = original

    def test_unrelated_prompt_fails_route_signal_contract(self) -> None:
        errors = self.validate_modified_cases(
            lambda cases: cases[0].update(prompt="unrelated request")
        )
        self.assertTrue(any("prompt lacks route signals" in error for error in errors))

    def test_none_case_rejects_named_skill(self) -> None:
        errors = self.validate_modified_cases(
            lambda cases: cases[-1].update(
                prompt="Use spring-modulith-auditor to explain transactions"
            )
        )
        self.assertTrue(any("must not name a skill" in error for error in errors))

    def test_missing_negative_coverage_is_rejected(self) -> None:
        errors = self.validate_modified_cases(
            lambda cases: [case.update(forbidden_skills=[]) for case in cases]
        )
        self.assertTrue(any("without negative/non-overlap" in error for error in errors))

    def test_expected_reference_must_be_routed_by_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill = Path(directory)
            (skill / "SKILL.md").write_text("# Sample\n", encoding="utf-8")
            self.assertFalse(validate_routing_contract.reference_is_routed(skill, "references/rules.md"))
            (skill / "SKILL.md").write_text(
                "Load `references/rules.md` for this workflow.\n", encoding="utf-8"
            )
            self.assertTrue(validate_routing_contract.reference_is_routed(skill, "references/rules.md"))

    def test_case_cannot_expect_and_forbid_the_same_reference(self) -> None:
        errors = self.validate_modified_cases(
            lambda cases: cases[0].update(
                forbidden_refs=[cases[0]["expected_refs"][0]]
            )
        )
        self.assertTrue(any("expects and forbids references" in error for error in errors))

    def test_dedicated_skill_case_must_partition_conditional_references(self) -> None:
        def remove_forbidden(cases: list[dict[str, object]]) -> None:
            case = next(item for item in cases if item["id"] == "static-evidence")
            case["forbidden_refs"] = []

        errors = self.validate_modified_cases(remove_forbidden)
        self.assertTrue(any("exactly partition dedicated-skill references" in error for error in errors))

    def test_conditional_reference_requires_positive_route_coverage(self) -> None:
        def remove_schema_route(cases: list[dict[str, object]]) -> None:
            cases[:] = [case for case in cases if case["id"] != "upgrade-plan-schema-consumer"]

        errors = self.validate_modified_cases(remove_schema_route)
        self.assertTrue(any("references without positive route coverage" in error for error in errors))

    def test_review_source_map_swap_violates_machine_readable_policy(self) -> None:
        def swap(cases: list[dict[str, object]]) -> None:
            case = next(item for item in cases if item["id"] == "versioned-postgresql-review-loads-data-sources")
            case["expected_refs"] = [
                "references/core-review-rules.md",
                "references/postgresql-rules.md",
                "references/messaging-sources.md",
            ]
            case["forbidden_refs"] = ["references/data-sources.md"]

        errors = self.validate_modified_cases(swap)
        self.assertTrue(any("review routing policy" in error for error in errors))

    def test_review_policy_covers_every_direct_skill_reference(self) -> None:
        root = ROOT / "skills" / "spring-best-practice-review"
        skill_refs = set(re.findall(r"`(references/[^`]+)`", (root / "SKILL.md").read_text(encoding="utf-8")))
        always, routes = validate_routing_contract.load_review_policy()
        policy_refs = set(always)
        for refs in routes.values():
            policy_refs.update(refs)
        self.assertEqual(skill_refs, policy_refs)

    def test_every_review_policy_route_has_case_coverage(self) -> None:
        cases = validate_routing_contract.load_cases()
        covered = {
            route
            for case in cases
            if case.get("expected_skill") == "spring-best-practice-review"
            for route in case.get("review_routes", [])
        }
        _, routes = validate_routing_contract.load_review_policy()
        self.assertEqual(set(routes), covered)

    def test_review_skill_route_rows_match_policy(self) -> None:
        self.assertEqual(validate_routing_contract.validate_contract(), [])

    def test_upgrade_handoff_names_the_target_skill(self) -> None:
        skill = (ROOT / "skills" / "spring-upgrade-planner" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("recommend `spring-evidence-collector` by exact name", skill)
        self.assertIn("do not assume collection has run", skill)


if __name__ == "__main__":
    unittest.main()
