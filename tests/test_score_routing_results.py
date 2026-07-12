from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import score_routing_results  # noqa: E402


class ScoreRoutingResultsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cases: list[dict[str, object]] = [
            {
                "id": "semantic-review",
                "prompt": "Review this Spring service",
                "expected_skill": "spring-best-practice-review",
                "activation_channel": "semantic",
            },
            {
                "id": "ordinary-question",
                "prompt": "Explain dependency injection",
                "expected_skill": None,
                "activation_channel": "none",
            },
        ]

    def test_blind_prompt_export_does_not_leak_expectations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "prompts.jsonl"
            score_routing_results.emit_blind_prompts(self.cases, destination)
            records = [json.loads(line) for line in destination.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(set(records[0]), {"case_id", "prompt"})
        self.assertNotIn("expected_skill", records[0])

    def test_perfect_results_score_all_channels_without_false_activation(self) -> None:
        results = [
            {
                "case_id": "semantic-review",
                "selected_skill": "spring-best-practice-review",
                "handoff_skills": ["spring-test-gap-planner"],
            },
            {"case_id": "ordinary-question", "selected_skill": None},
        ]
        report, errors = score_routing_results.score_results(self.cases, results)
        self.assertEqual(errors, [])
        summary = report["summary"]
        self.assertEqual(summary["accuracy"], 1.0)
        self.assertEqual(summary["false_activation_rate"], 0.0)
        self.assertEqual(report["failures"], [])
        self.assertEqual(report["observed_handoffs"][0]["handoff_skills"], ["spring-test-gap-planner"])

    def test_wrong_and_false_activation_routes_are_measured(self) -> None:
        results = [
            {"case_id": "semantic-review", "selected_skill": "spring-test-gap-planner"},
            {"case_id": "ordinary-question", "selected_skill": "spring-best-practice-review"},
        ]
        report, errors = score_routing_results.score_results(self.cases, results)
        self.assertEqual(errors, [])
        summary = report["summary"]
        self.assertEqual(summary["accuracy"], 0.0)
        self.assertEqual(summary["wrong_skill"], 1)
        self.assertEqual(summary["false_activation_rate"], 1.0)
        self.assertEqual(len(report["failures"]), 2)

    def test_duplicate_unknown_and_missing_results_are_rejected(self) -> None:
        results = [
            {"case_id": "semantic-review", "selected_skill": "spring-best-practice-review"},
            {"case_id": "semantic-review", "selected_skill": "spring-best-practice-review"},
            {"case_id": "unknown", "selected_skill": None},
        ]
        _, errors = score_routing_results.score_results(self.cases, results)
        self.assertTrue(any("duplicate routing result" in error for error in errors))
        self.assertTrue(any("unknown routing case" in error for error in errors))
        self.assertTrue(any("missing routing results" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
