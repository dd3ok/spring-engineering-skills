from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UPGRADE_SCRIPTS = ROOT / "skills" / "spring-upgrade-planner" / "scripts"
sys.path.insert(0, str(UPGRADE_SCRIPTS))

import cloud_policy  # noqa: E402


class SpringCloudPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = json.loads(cloud_policy.POLICY_PATH.read_text(encoding="utf-8"))
        self.today = date(2026, 7, 13)

    def test_repository_policy_is_valid(self) -> None:
        self.assertEqual(cloud_policy.validate_policy(self.policy, today=self.today), [])

    def test_current_compatibility_mapping(self) -> None:
        self.assertIsNone(cloud_policy.compatibility_error(self.policy, "4.0.5", "2025.1.0"))
        self.assertIsNone(cloud_policy.compatibility_error(self.policy, "4.1.0", "2025.1.2"))
        self.assertIn("2025.1.2", cloud_policy.compatibility_error(self.policy, "4.1.0", "2025.1.1") or "")
        self.assertIn("no reviewed", cloud_policy.compatibility_error(self.policy, "4.2.0", "2025.1.2") or "")

    def test_stale_future_and_malformed_policies_are_rejected(self) -> None:
        for checked_on in ("2025-01-01", "2027-01-01", "invalid"):
            with self.subTest(checked_on=checked_on):
                policy = copy.deepcopy(self.policy)
                policy["checked_on"] = checked_on
                self.assertTrue(cloud_policy.validate_policy(policy, today=self.today))

    def test_duplicate_boot_line_and_wrong_train_minimum_are_rejected(self) -> None:
        duplicate = copy.deepcopy(self.policy)
        duplicate["rows"].append(copy.deepcopy(duplicate["rows"][0]))
        duplicate["rows"][1]["train"] = "2026.0"
        self.assertTrue(any("duplicate Boot line" in error for error in cloud_policy.validate_policy(duplicate, today=self.today)))

        wrong_minimum = copy.deepcopy(self.policy)
        wrong_minimum["rows"][0]["boot_lines"][0]["min_service_release"] = "2025.0.9"
        self.assertTrue(any("minimum service release" in error for error in cloud_policy.validate_policy(wrong_minimum, today=self.today)))

    def test_source_text_is_semantically_bound_to_enforced_minimums(self) -> None:
        lowered = copy.deepcopy(self.policy)
        lowered["rows"][0]["boot_lines"][1]["min_service_release"] = "2025.1.0"
        self.assertTrue(any("minimums" in error for error in cloud_policy.validate_policy(lowered, today=self.today)))

        vague = copy.deepcopy(self.policy)
        vague["rows"][0]["source_text"] = "Spring Cloud"
        self.assertTrue(any("source text" in error for error in cloud_policy.validate_policy(vague, today=self.today)))

        swapped = copy.deepcopy(self.policy)
        swapped["rows"][0]["boot_lines"][0]["min_service_release"] = "2025.1.2"
        swapped["rows"][0]["boot_lines"][1]["min_service_release"] = "2025.1.0"
        self.assertTrue(any("official Boot lines" in error for error in cloud_policy.validate_policy(swapped, today=self.today)))

    def test_boolean_max_age_is_rejected(self) -> None:
        malformed = copy.deepcopy(self.policy)
        malformed["max_age_days"] = True
        self.assertTrue(cloud_policy.validate_policy(malformed, today=self.today))

    def test_invalid_json_is_reported_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text("{", encoding="utf-8")
            _, errors = cloud_policy.load_policy(path, today=self.today)
        self.assertTrue(any("cannot read" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
