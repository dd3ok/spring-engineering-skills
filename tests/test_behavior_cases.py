from __future__ import annotations

import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_behavior_cases  # noqa: E402


class BehaviorCaseTests(unittest.TestCase):
    def test_behavior_case_contract_is_valid(self) -> None:
        self.assertEqual(validate_behavior_cases.validate_cases(), [])

    def test_contradictory_rubric_is_rejected(self) -> None:
        cases = json.loads(validate_behavior_cases.CASES_PATH.read_text(encoding="utf-8"))
        cases[0]["must_not"].append(cases[0]["must"][0])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text(json.dumps(cases), encoding="utf-8")
            with patch.object(validate_behavior_cases, "CASES_PATH", path):
                errors = validate_behavior_cases.validate_cases()
        self.assertTrue(any("contradicts itself" in error for error in errors))

    def test_repository_fixture_cases_bind_existing_safe_directories(self) -> None:
        cases = json.loads(validate_behavior_cases.CASES_PATH.read_text(encoding="utf-8"))
        repository_cases = [
            case for case in cases if case.get("artifact_mode") == "repository-fixture"
        ]
        self.assertEqual(
            {case["id"] for case in repository_cases},
            {
                "korean-existing-application-fix",
                "developer-greenfield-unpinned-version",
            },
        )
        for case in repository_cases:
            self.assertEqual(
                validate_behavior_cases.repository_fixture_errors(
                    case["id"],
                    case.get("fixture_path"),
                    case.get("fixture_tree_sha256"),
                ),
                [],
            )

    def test_repository_fixture_rejects_missing_or_escaping_paths(self) -> None:
        self.assertTrue(
            any(
                "requires fixture_path" in error
                for error in validate_behavior_cases.repository_fixture_errors(
                    "case", None, None
                )
            )
        )
        self.assertTrue(
            any(
                "invalid fixture_path" in error
                for error in validate_behavior_cases.repository_fixture_errors(
                    "case", "evals/fixtures/../behavior-cases.json", "a" * 64
                )
            )
        )

    def test_non_repository_case_cannot_declare_a_fixture(self) -> None:
        cases = json.loads(validate_behavior_cases.CASES_PATH.read_text(encoding="utf-8"))
        cases[0]["fixture_path"] = "evals/fixtures/developer-greenfield-unpinned-version"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text(json.dumps(cases), encoding="utf-8")
            with patch.object(validate_behavior_cases, "CASES_PATH", path):
                errors = validate_behavior_cases.validate_cases()
        self.assertTrue(any("fixture fields require repository-fixture mode" in error for error in errors))

    def test_repository_fixture_hash_must_match_the_fixture_content(self) -> None:
        cases = json.loads(validate_behavior_cases.CASES_PATH.read_text(encoding="utf-8"))
        repository_case = next(
            case for case in cases if case.get("artifact_mode") == "repository-fixture"
        )
        repository_case["fixture_tree_sha256"] = "f" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text(json.dumps(cases), encoding="utf-8")
            with patch.object(validate_behavior_cases, "CASES_PATH", path):
                errors = validate_behavior_cases.validate_cases()
        self.assertTrue(any("does not match fixture content" in error for error in errors))

    def test_unhashable_rubric_items_return_validation_errors(self) -> None:
        cases = json.loads(validate_behavior_cases.CASES_PATH.read_text(encoding="utf-8"))
        cases[0]["must"] = [["nested"]]
        cases[0]["must_not"] = [{"unexpected": "object"}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text(json.dumps(cases), encoding="utf-8")
            with patch.object(validate_behavior_cases, "CASES_PATH", path):
                errors = validate_behavior_cases.validate_cases()
        self.assertTrue(any("must must be non-empty strings" in error for error in errors))
        self.assertTrue(any("must_not must be non-empty strings" in error for error in errors))

    def test_korean_behavior_coverage_is_required(self) -> None:
        cases = json.loads(validate_behavior_cases.CASES_PATH.read_text(encoding="utf-8"))
        cases = [
            case
            for case in cases
            if case.get("response_language") != "ko"
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text(json.dumps(cases), encoding="utf-8")
            with patch.object(validate_behavior_cases, "CASES_PATH", path):
                errors = validate_behavior_cases.validate_cases()
        self.assertIn("behavior cases require at least 2 Korean prompts", errors)

    def test_unlabeled_mixed_language_prompt_is_not_forced_to_korean(self) -> None:
        cases = json.loads(validate_behavior_cases.CASES_PATH.read_text(encoding="utf-8"))
        cases[0]["prompt"] = "Explain the field 이름 without changing output language"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text(json.dumps(cases), encoding="utf-8")
            with patch.object(validate_behavior_cases, "CASES_PATH", path):
                errors = validate_behavior_cases.validate_cases()
        self.assertEqual(errors, [])

    def test_substantive_korean_prompt_requires_language_declaration(self) -> None:
        cases = json.loads(validate_behavior_cases.CASES_PATH.read_text(encoding="utf-8"))
        cases[0]["prompt"] = "운영 환경에서 수집한 근거 없이 병목을 확정하지 마세요"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text(json.dumps(cases), encoding="utf-8")
            with patch.object(validate_behavior_cases, "CASES_PATH", path):
                errors = validate_behavior_cases.validate_cases()
        self.assertTrue(any("substantive Korean prompt must require" in error for error in errors))

    def test_korean_response_language_requires_rubric(self) -> None:
        cases = json.loads(validate_behavior_cases.CASES_PATH.read_text(encoding="utf-8"))
        korean = next(case for case in cases if case.get("response_language") == "ko")
        korean["must"].remove(validate_behavior_cases.KOREAN_RESPONSE_CRITERION)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text(json.dumps(cases), encoding="utf-8")
            with patch.object(validate_behavior_cases, "CASES_PATH", path):
                errors = validate_behavior_cases.validate_cases()
        self.assertTrue(any("must require a Korean response" in error for error in errors))

    def test_invalid_korean_rubric_type_returns_an_error(self) -> None:
        cases = json.loads(validate_behavior_cases.CASES_PATH.read_text(encoding="utf-8"))
        korean = next(case for case in cases if case.get("response_language") == "ko")
        korean["must"] = None
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text(json.dumps(cases), encoding="utf-8")
            with patch.object(validate_behavior_cases, "CASES_PATH", path):
                errors = validate_behavior_cases.validate_cases()
        self.assertTrue(any("must must be non-empty strings" in error for error in errors))

    def test_korean_coverage_rejects_token_only_localization(self) -> None:
        cases = json.loads(validate_behavior_cases.CASES_PATH.read_text(encoding="utf-8"))
        korean = next(case for case in cases if case.get("response_language") == "ko")
        korean["prompt"] = "Diagnose this latency 병목"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text(json.dumps(cases), encoding="utf-8")
            with patch.object(validate_behavior_cases, "CASES_PATH", path):
                errors = validate_behavior_cases.validate_cases()
        self.assertTrue(any("requires a substantive Korean prompt" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
