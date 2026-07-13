from __future__ import annotations

import sys
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import score_behavior_results  # noqa: E402


class ScoreBehaviorResultsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cases = {
            "case": {
                "id": "case",
                "skill": "spring-engineering-review",
                "must": ["one", "two"],
                "must_not": ["unsafe"],
            }
        }

    def result(self, run_id: str, condition: str, must=None, must_not=None) -> dict[str, object]:
        return {
            "case_id": "case",
            "run_id": run_id,
            "condition": condition,
            "host": "codex",
            "host_version": "2026.7",
            "model": "gpt-5",
            "skill_commit": "a" * 40,
            "trace_id": f"trace-{condition}-{run_id}",
            "output_sha256": "b" * 64,
            "grader_kind": "independent-human",
            "must_results": must or ["pass", "pass"],
            "must_not_results": must_not or ["pass"],
        }

    def test_complete_passing_manifest_scores(self) -> None:
        results = [self.result(f"with-{index}", "with-skill") for index in range(3)]
        results.append(self.result("without-1", "without-skill"))
        report, errors = score_behavior_results.score_results(self.cases, results)
        self.assertEqual(errors, [])
        self.assertEqual(report["summary"]["must_pass_rate"], 1.0)
        self.assertEqual(report["summary"]["must_not_violations"], 0)

    def test_violation_and_incomplete_runs_are_reported(self) -> None:
        results = [self.result("with-1", "with-skill", must=["pass", "unclear"], must_not=["fail"])]
        report, errors = score_behavior_results.score_results(self.cases, results)
        self.assertTrue(any("incomplete behavior result runs" in error for error in errors))
        self.assertEqual(report["summary"]["must_not_violations"], 1)
        self.assertEqual(len(report["failures"]), 1)

    def test_duplicate_and_rubric_length_mismatch_are_rejected(self) -> None:
        duplicate = self.result("with-1", "with-skill")
        malformed = self.result("with-2", "with-skill", must=["pass"])
        _, errors = score_behavior_results.score_results(
            self.cases, [duplicate, duplicate.copy(), malformed], require_complete=False
        )
        self.assertTrue(any("duplicate behavior result" in error for error in errors))
        self.assertTrue(any("rubric result length mismatch" in error for error in errors))

    def test_without_skill_baseline_does_not_lower_release_score(self) -> None:
        results = [self.result(f"with-{index}", "with-skill") for index in range(3)]
        results.append(
            self.result("without-1", "without-skill", must=["fail", "fail"], must_not=["fail"])
        )
        report, errors = score_behavior_results.score_results(self.cases, results)
        self.assertEqual(errors, [])
        self.assertEqual(report["summary"]["must_pass_rate"], 1.0)
        self.assertEqual(report["summary"]["must_not_violations"], 0)
        self.assertEqual(report["without_skill_baseline"]["must_pass_rate"], 0.0)
        self.assertEqual(report["without_skill_baseline"]["must_not_violations"], 1)
        self.assertEqual(report["release_gate_failures"], [])

    def test_repeated_must_failure_and_unclear_safety_block_release(self) -> None:
        results = [
            self.result("with-1", "with-skill", must=["fail", "pass"]),
            self.result("with-2", "with-skill", must=["unclear", "pass"]),
            self.result("with-3", "with-skill", must_not=["unclear"]),
            self.result("without-1", "without-skill"),
        ]
        report, errors = score_behavior_results.score_results(self.cases, results)
        self.assertEqual(errors, [])
        self.assertEqual(len(report["repeated_criterion_failures"]), 1)
        failures = report["release_gate_failures"]
        self.assertTrue(any("majority" in failure for failure in failures))
        self.assertTrue(any("must_not" in failure for failure in failures))

    def test_per_skill_floor_is_enforced_even_when_global_rate_passes(self) -> None:
        report = {
            "summary": {
                "must_pass_rate": 0.95,
                "must_not_violations": 0,
                "must_not_unclear": 0,
            },
            "by_skill": {
                "spring-engineering-review": {
                    "must_pass_rate": 0.89,
                    "violations": 0,
                    "unclear": 0,
                }
            },
            "without_skill_baseline": {"must_total": 1},
            "repeated_criterion_failures": [],
            "incomplete_runs": [],
        }
        failures = score_behavior_results.release_gate_failures(report)
        self.assertTrue(any("below 90%" in failure for failure in failures))

    def test_duplicate_trace_and_mixed_cohort_are_rejected(self) -> None:
        first = self.result("with-1", "with-skill")
        duplicate_trace = self.result("with-2", "with-skill")
        duplicate_trace["trace_id"] = first["trace_id"]
        mixed = self.result("with-3", "with-skill")
        mixed["model"] = "another-model"
        _, errors = score_behavior_results.score_results(
            self.cases, [first, duplicate_trace, mixed], require_complete=False
        )
        self.assertTrue(any("duplicate behavior trace_id" in error for error in errors))
        self.assertTrue(any("mixed behavior trace cohort" in error for error in errors))

    def test_partial_mode_still_rejects_excess_runs(self) -> None:
        results = [self.result(f"with-{index}", "with-skill") for index in range(4)]
        _, errors = score_behavior_results.score_results(
            self.cases, results, require_complete=False
        )
        self.assertTrue(any("too many behavior result runs" in error for error in errors))

    def test_non_string_grade_is_rejected_without_type_error(self) -> None:
        record = self.result("with-1", "with-skill")
        record["must_results"] = [{}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.jsonl"
            path.write_text(json.dumps(record) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid must_results"):
                score_behavior_results.load_results(path)

    def test_strict_release_rejects_custom_case_suite(self) -> None:
        with self.assertRaisesRegex(ValueError, "canonical behavior case suite"):
            score_behavior_results.require_canonical_cases(self.cases, {})
        score_behavior_results.require_canonical_cases(self.cases, dict(self.cases))


if __name__ == "__main__":
    unittest.main()
