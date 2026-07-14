from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest import mock


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

    def bind_repository_artifact(
        self,
        root: Path,
        record: dict[str, object],
    ) -> tuple[dict[str, dict[str, object]], Path, Path, Path]:
        fixture_root = root / "fixtures"
        fixture = fixture_root / "case"
        fixture.mkdir(parents=True)
        (fixture / "original.txt").write_text("original", encoding="utf-8")
        artifact_root = root / "artifacts"
        run_root = (
            artifact_root
            / str(record["case_id"])
            / str(record["condition"])
            / str(record["run_id"])
        )
        workspace = run_root / "workspace"
        shutil.copytree(fixture, workspace)
        if record["condition"] == "with-skill":
            (workspace / "changed.txt").write_text("changed", encoding="utf-8")
        manifest = score_behavior_results.build_manifest("case", fixture, workspace)
        payload = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode()
        manifest_path = run_root / "manifest.json"
        manifest_path.write_bytes(payload)
        record.update(
            {
                "workspace_diff_sha256": manifest["workspace_diff_sha256"],
                "changed_paths": manifest["changed_paths"],
                "artifact_manifest_path": manifest_path.relative_to(artifact_root).as_posix(),
                "artifact_manifest_sha256": hashlib.sha256(payload).hexdigest(),
                "artifact_workspace_path": workspace.relative_to(artifact_root).as_posix(),
            }
        )
        cases = {
            "case": {
                **self.cases["case"],
                "artifact_mode": "repository-fixture",
                "fixture_path": "case",
            }
        }
        return cases, artifact_root, fixture_root, workspace

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

    def test_repository_fixture_requires_non_empty_with_skill_workspace_evidence(self) -> None:
        cases = {
            "case": {
                **self.cases["case"],
                "artifact_mode": "repository-fixture",
            }
        }
        missing = self.result("with-1", "with-skill")
        _, errors = score_behavior_results.score_results(
            cases, [missing], require_complete=False
        )
        self.assertTrue(any("lacks workspace evidence" in error for error in errors))

        empty = self.result("with-2", "with-skill")
        empty["workspace_diff_sha256"] = score_behavior_results.EMPTY_WORKSPACE_DIFF_SHA256
        empty["changed_paths"] = []
        _, errors = score_behavior_results.score_results(cases, [empty], require_complete=False)
        self.assertTrue(any("has no changes" in error for error in errors))

    def test_repository_fixture_accepts_bound_changes_and_empty_baseline(self) -> None:
        cases = {
            "case": {
                **self.cases["case"],
                "artifact_mode": "repository-fixture",
            }
        }
        with_skill = self.result("with-1", "with-skill")
        with_skill["workspace_diff_sha256"] = "c" * 64
        with_skill["changed_paths"] = ["src/main/java/example/Application.java"]
        baseline = self.result("without-1", "without-skill")
        baseline["workspace_diff_sha256"] = "d" * 64
        baseline["changed_paths"] = []
        _, errors = score_behavior_results.score_results(
            cases,
            [with_skill, baseline],
            expected_with_skill_runs=1,
            expected_without_skill_runs=1,
        )
        self.assertEqual(errors, [])

    def test_strict_repository_artifact_binding_recomputes_preserved_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = self.result("with-1", "with-skill")
            cases, artifact_root, fixture_root, _ = self.bind_repository_artifact(
                root, record
            )
            _, errors = score_behavior_results.score_results(
                cases,
                [record],
                expected_with_skill_runs=1,
                expected_without_skill_runs=0,
                artifact_root=artifact_root,
                fixture_root=fixture_root,
                require_artifact_binding=True,
            )
        self.assertEqual(errors, [])

    def test_strict_repository_artifact_binding_rejects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = self.result("with-1", "with-skill")
            cases, artifact_root, fixture_root, workspace = self.bind_repository_artifact(
                root, record
            )
            (workspace / "changed.txt").write_text("tampered", encoding="utf-8")
            _, errors = score_behavior_results.score_results(
                cases,
                [record],
                expected_with_skill_runs=1,
                expected_without_skill_runs=0,
                artifact_root=artifact_root,
                fixture_root=fixture_root,
                require_artifact_binding=True,
            )
        self.assertTrue(any("preserved workspace" in error for error in errors))

    def test_strict_repository_artifact_binding_rejects_wrong_manifest_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = self.result("with-1", "with-skill")
            cases, artifact_root, fixture_root, _ = self.bind_repository_artifact(
                root, record
            )
            record["artifact_manifest_sha256"] = "f" * 64
            _, errors = score_behavior_results.score_results(
                cases,
                [record],
                expected_with_skill_runs=1,
                expected_without_skill_runs=0,
                artifact_root=artifact_root,
                fixture_root=fixture_root,
                require_artifact_binding=True,
            )
        self.assertTrue(any("manifest SHA-256" in error for error in errors))

    def test_repository_artifact_binding_must_identify_its_result_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = self.result("with-1", "with-skill")
            cases, artifact_root, fixture_root, _ = self.bind_repository_artifact(
                root, record
            )
            record["artifact_workspace_path"] = (
                "case/with-skill/different-run/workspace"
            )
            _, errors = score_behavior_results.score_results(
                cases,
                [record],
                expected_with_skill_runs=1,
                expected_without_skill_runs=0,
                artifact_root=artifact_root,
                fixture_root=fixture_root,
                require_artifact_binding=True,
            )
        self.assertTrue(any("does not identify this result run" in error for error in errors))

    def test_strict_repository_fixture_requires_artifact_binding(self) -> None:
        cases = {
            "case": {
                **self.cases["case"],
                "artifact_mode": "repository-fixture",
            }
        }
        record = self.result("with-1", "with-skill")
        record["workspace_diff_sha256"] = "c" * 64
        record["changed_paths"] = ["changed.txt"]
        _, errors = score_behavior_results.score_results(
            cases,
            [record],
            require_complete=False,
            require_artifact_binding=True,
        )
        self.assertTrue(any("lacks artifact binding" in error for error in errors))

    def test_direct_scoring_rejects_incomplete_artifact_binding(self) -> None:
        cases = {
            "case": {
                **self.cases["case"],
                "artifact_mode": "repository-fixture",
            }
        }
        record = self.result("with-1", "with-skill")
        record.update(
            {
                "workspace_diff_sha256": "c" * 64,
                "changed_paths": ["changed.txt"],
                "artifact_manifest_path": "run/manifest.json",
            }
        )
        _, errors = score_behavior_results.score_results(
            cases,
            [record],
            require_complete=False,
        )
        self.assertTrue(any("incomplete artifact binding" in error for error in errors))

    def test_non_fixture_result_rejects_workspace_evidence(self) -> None:
        record = self.result("with-1", "with-skill")
        record["workspace_diff_sha256"] = "c" * 64
        record["changed_paths"] = ["src/main/java/example/Application.java"]
        _, errors = score_behavior_results.score_results(
            self.cases, [record], require_complete=False
        )
        self.assertTrue(any("non-fixture result" in error for error in errors))

    def test_workspace_evidence_paths_are_portable_strings(self) -> None:
        record = self.result("with-1", "with-skill")
        record["workspace_diff_sha256"] = "c" * 64
        record["changed_paths"] = [["nested"]]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.jsonl"
            path.write_text(json.dumps(record) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid changed_paths"):
                score_behavior_results.load_results(path)

    def test_artifact_binding_paths_are_portable_and_complete(self) -> None:
        record = self.result("with-1", "with-skill")
        record.update(
            {
                "artifact_manifest_path": "../manifest.json",
                "artifact_manifest_sha256": "c" * 64,
                "artifact_workspace_path": "run/workspace",
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.jsonl"
            path.write_text(json.dumps(record) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid artifact_manifest_path"):
                score_behavior_results.load_results(path)

        record["artifact_manifest_path"] = "run/manifest.json"
        record.pop("artifact_workspace_path")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.jsonl"
            path.write_text(json.dumps(record) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "incomplete artifact binding"):
                score_behavior_results.load_results(path)

    def test_strict_release_rejects_custom_case_suite(self) -> None:
        with self.assertRaisesRegex(ValueError, "canonical behavior case suite"):
            score_behavior_results.require_canonical_cases(self.cases, {})
        score_behavior_results.require_canonical_cases(self.cases, dict(self.cases))

    def test_strict_cli_requires_artifact_root(self) -> None:
        with redirect_stderr(StringIO()), mock.patch.object(
            sys,
            "argv",
            ["score_behavior_results.py", "results.jsonl", "--strict"],
        ), self.assertRaises(SystemExit):
            score_behavior_results.main()


if __name__ == "__main__":
    unittest.main()
