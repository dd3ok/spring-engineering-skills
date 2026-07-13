from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import score_routing_results  # noqa: E402


class ScoreRoutingResultsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cases: list[dict[str, object]] = [
            {
                "id": "semantic-review",
                "prompt": "Review this Spring service",
                "expected_skill": "spring-engineering-review",
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
                "selected_skill": "spring-engineering-review",
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
            {"case_id": "ordinary-question", "selected_skill": "spring-engineering-review"},
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
            {"case_id": "semantic-review", "selected_skill": "spring-engineering-review"},
            {"case_id": "semantic-review", "selected_skill": "spring-engineering-review"},
            {"case_id": "unknown", "selected_skill": None},
        ]
        _, errors = score_routing_results.score_results(self.cases, results)
        self.assertTrue(any("duplicate routing result" in error for error in errors))
        self.assertTrue(any("unknown routing case" in error for error in errors))
        self.assertTrue(any("missing routing results" in error for error in errors))

    def test_repeated_runs_are_scored_by_case_threshold(self) -> None:
        results = [
            {
                "case_id": "semantic-review",
                "run_id": f"run-{index}",
                "selected_skill": "spring-engineering-review" if index < 3 else None,
            }
            for index in range(1, 4)
        ]
        results.extend(
            {"case_id": "ordinary-question", "run_id": f"run-{index}", "selected_skill": None}
            for index in range(1, 4)
        )
        report, errors = score_routing_results.score_results(
            self.cases, results, expected_runs=3
        )
        self.assertEqual(errors, [])
        semantic = next(item for item in report["case_results"] if item["case_id"] == "semantic-review")
        self.assertAlmostEqual(semantic["accuracy"], 2 / 3, places=6)
        self.assertTrue(semantic["passed"])
        self.assertEqual(report["summary"]["cases_passed"], 2)

    def test_repeated_runs_require_unique_run_ids_and_complete_counts(self) -> None:
        results = [
            {"case_id": "semantic-review", "run_id": "same", "selected_skill": "spring-engineering-review"},
            {"case_id": "semantic-review", "run_id": "same", "selected_skill": "spring-engineering-review"},
        ]
        _, errors = score_routing_results.score_results(self.cases, results, expected_runs=3)
        self.assertTrue(any("duplicate routing result" in error for error in errors))
        self.assertTrue(any("incomplete routing result runs" in error for error in errors))

    def test_trace_provenance_is_required_for_release_evaluation(self) -> None:
        self.cases = [self.cases[0]]
        self.cases[0]["split"] = "validation"
        incomplete = [{"case_id": "semantic-review", "run_id": "run-1", "selected_skill": "spring-engineering-review"}]
        _, errors = score_routing_results.score_results(
            self.cases, incomplete, require_trace=True
        )
        self.assertTrue(any("activation trace provenance" in error for error in errors))

        traced = [
            {
                "case_id": "semantic-review",
                "run_id": "run-1",
                "selected_skill": "spring-engineering-review",
                "host": "codex-desktop",
                "host_version": "2026.7",
                "model": "gpt-5",
                "skill_commit": "a" * 40,
                "observation_kind": "host-activation-trace",
                "trace_id": "trace-1",
            }
        ]
        report, errors = score_routing_results.score_results(self.cases, traced, require_trace=True)
        self.assertEqual(errors, [])
        self.assertEqual(report["by_split"]["validation"]["accuracy"], 1.0)

    def test_release_gate_enforces_published_aggregate_thresholds(self) -> None:
        cases = [
            {
                "id": "named",
                "prompt": "Use spring-engineering-review",
                "expected_skill": "spring-engineering-review",
                "activation_channel": "explicit-name",
                "split": "validation",
            },
            {
                "id": "negative",
                "prompt": "Explain DI",
                "expected_skill": None,
                "activation_channel": "none",
                "split": "validation",
            },
        ]
        results = [
            {"case_id": "named", "selected_skill": None},
            {"case_id": "negative", "selected_skill": "spring-engineering-review"},
        ]
        report, errors = score_routing_results.score_results(cases, results)
        self.assertEqual(errors, [])
        failures = report["release_gate_failures"]
        self.assertTrue(any("exact-name" in failure for failure in failures))
        self.assertTrue(any("validation" in failure for failure in failures))
        self.assertTrue(any("false activation" in failure for failure in failures))
        self.assertTrue(any("missed activation" in failure for failure in failures))

    def test_release_gate_passes_perfect_observations(self) -> None:
        cases = [
            {**self.cases[0], "activation_channel": "explicit-name", "split": "validation"},
            {**self.cases[1], "split": "validation"},
        ]
        results = [
            {"case_id": "semantic-review", "selected_skill": "spring-engineering-review"},
            {"case_id": "ordinary-question", "selected_skill": None},
        ]
        report, errors = score_routing_results.score_results(cases, results)
        self.assertEqual(errors, [])
        self.assertEqual(report["release_gate_failures"], [])

    def test_release_gate_rejects_missing_required_case_families(self) -> None:
        report, errors = score_routing_results.score_results(
            [self.cases[0]],
            [{"case_id": "semantic-review", "selected_skill": "spring-engineering-review"}],
        )
        self.assertEqual(errors, [])
        failures = report["release_gate_failures"]
        self.assertTrue(any("exact-name coverage" in failure for failure in failures))
        self.assertTrue(any("validation split coverage" in failure for failure in failures))
        self.assertTrue(any("non-activation coverage" in failure for failure in failures))

    def test_trace_ids_must_be_unique_and_cohort_must_match(self) -> None:
        cases = [self.cases[0]]
        base = {
            "case_id": "semantic-review",
            "selected_skill": "spring-engineering-review",
            "host": "codex",
            "host_version": "2026.7",
            "model": "gpt-5",
            "skill_commit": "a" * 40,
            "observation_kind": "host-activation-trace",
            "trace_id": "same-trace",
        }
        first = {**base, "run_id": "run-1"}
        duplicate = {**base, "run_id": "run-2"}
        mixed = {**base, "run_id": "run-3", "trace_id": "trace-3", "model": "other"}
        _, errors = score_routing_results.score_results(
            cases,
            [first, duplicate, mixed],
            require_complete=False,
            expected_runs=3,
            require_trace=True,
        )
        self.assertTrue(any("duplicate host activation trace_id" in error for error in errors))
        self.assertTrue(any("mixed routing trace cohort" in error for error in errors))

    def test_unknown_expected_skill_is_rejected_without_crashing(self) -> None:
        cases = [{**self.cases[0], "expected_skill": "not-installed"}]
        _, errors = score_routing_results.score_results(
            cases, [{"case_id": "semantic-review", "selected_skill": None}]
        )
        self.assertTrue(any("unknown expected skill" in error for error in errors))

    def test_strict_cli_requires_repeated_complete_evaluation(self) -> None:
        with redirect_stderr(StringIO()), mock.patch.object(
            sys, "argv", ["score_routing_results.py", "results.jsonl", "--strict"]
        ), self.assertRaises(SystemExit):
            score_routing_results.parse_args()

    def test_strict_release_rejects_custom_case_suite(self) -> None:
        with self.assertRaisesRegex(ValueError, "canonical routing case suite"):
            score_routing_results.require_canonical_cases(self.cases, self.cases[:1])
        score_routing_results.require_canonical_cases(self.cases, list(self.cases))
        with redirect_stderr(StringIO()), mock.patch.object(
            sys,
            "argv",
            [
                "score_routing_results.py",
                "results.jsonl",
                "--strict",
                "--expected-runs",
                "3",
                "--allow-partial",
            ],
        ), self.assertRaises(SystemExit):
            score_routing_results.parse_args()

    def test_published_route_label_smoke_summary_matches_records(self) -> None:
        observation = json.loads(
            (ROOT / "evals" / "route-label-smoke-2026-07-12.json").read_text(encoding="utf-8")
        )
        initial = [item for item in observation["results"] if item["id"].startswith("route-")]
        post_description = [
            item for item in observation["results"] if item["id"].startswith("post-description-")
        ]
        summary = observation["summary"]
        self.assertEqual(summary["initial_evaluated"], len(initial))
        self.assertEqual(summary["initial_matching_labels"], sum(
            item["expected"] == item["observed"] for item in initial
        ))
        self.assertEqual(summary["single_skill"], sum(len(item["expected"]) == 1 for item in initial))
        self.assertEqual(summary["non_activation"], sum(not item["expected"] for item in initial))
        self.assertEqual(summary["compound_handoff"], sum(len(item["expected"]) > 1 for item in initial))
        self.assertEqual(summary["post_description_checks"], len(post_description))
        self.assertEqual(summary["post_description_matching_labels"], sum(
            item["expected"] == item["observed"] for item in post_description
        ))
        self.assertEqual(summary["total_evaluated"], len(observation["results"]))
        self.assertEqual(summary["total_matching_labels"], sum(
            item["expected"] == item["observed"] for item in observation["results"]
        ))


if __name__ == "__main__":
    unittest.main()
