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


if __name__ == "__main__":
    unittest.main()
