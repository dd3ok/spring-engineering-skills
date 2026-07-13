from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_spring_cloud_policy  # noqa: E402


class CheckSpringCloudPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = json.loads(
            (ROOT / "skills" / "spring-upgrade-planner" / "references" / "spring-cloud-compatibility-policy.json").read_text(
                encoding="utf-8"
            )
        )

    def test_markers_match_normalized_official_text(self) -> None:
        text = "Release Train 2025.1.x aka Oakwood 4.0.x,   4.1.x (Starting with 2025.1.2)"
        self.assertEqual(check_spring_cloud_policy.marker_errors(self.policy, text), [])

    def test_missing_marker_reports_drift(self) -> None:
        errors = check_spring_cloud_policy.marker_errors(self.policy, "2025.1.x aka Oakwood 4.0.x, 4.1.x")
        self.assertTrue(any("Starting with 2025.1.2" in error for error in errors))

    def test_truncated_row_reports_drift(self) -> None:
        text = "2025.1.x aka Oakwood 4.0.x, 4.1.x"
        self.assertTrue(check_spring_cloud_policy.marker_errors(self.policy, text))

    def test_fetch_deadline_rejects_nonfinite_values_and_times_out_worker(self) -> None:
        for timeout in (0.0, -1.0, float("inf"), float("nan")):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                check_spring_cloud_policy.fetch_with_deadline("https://spring.io/projects/spring-cloud/", timeout)
        with patch.object(
            check_spring_cloud_policy.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(cmd="worker", timeout=0.01),
        ) as run:
            with self.assertRaises(TimeoutError):
                check_spring_cloud_policy.fetch_with_deadline("https://spring.io/projects/spring-cloud/", 0.01)
        self.assertEqual(run.call_args.kwargs["timeout"], 0.01)

    def test_html_text_is_bounded_and_normalized(self) -> None:
        payload = b"<html><body><p>2025.1.x</p><p>4.0.x, 4.1.x</p></body></html>"
        self.assertEqual(check_spring_cloud_policy.normalized_page_text(payload), "2025.1.x 4.0.x, 4.1.x")


if __name__ == "__main__":
    unittest.main()
