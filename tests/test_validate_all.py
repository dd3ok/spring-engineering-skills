from __future__ import annotations

import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_all  # noqa: E402


class ValidateAllTests(unittest.TestCase):
    def test_ci_workflow_is_minimal_pinned_and_offline(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "validate.yml").read_text(encoding="utf-8")
        self.assertIn("name: validate", workflow)
        self.assertIn("python scripts/validate_all.py", workflow)
        self.assertIn("python -m ruff check scripts tests skills", workflow)
        self.assertIn("name: windows-smoke", workflow)
        self.assertIn(
            "python -m unittest tests.test_skill_structure tests.test_check_links "
            "tests.test_evidence_collector tests.test_spring_project_lifecycle",
            workflow,
        )
        self.assertIn("tests.test_capture_behavior_artifact", workflow)
        self.assertIn("tests.test_score_behavior_results", workflow)
        self.assertIn("-r .github/requirements-ci.txt", workflow)
        self.assertNotIn("check_links.py --online", workflow)
        self.assertNotIn("matrix:", workflow)
        self.assertNotIn("pull_request_target:", workflow)
        self.assertNotIn("write-all", workflow)
        self.assertIn("permissions:\n  contents: read\n", workflow)
        self.assertIn("timeout-minutes: 10", workflow)
        self.assertIn("timeout-minutes: 5", workflow)
        action_lines = [line.strip() for line in workflow.splitlines() if "uses:" in line]
        self.assertTrue(action_lines)
        for line in action_lines:
            self.assertRegex(line, r"uses: [^@]+@[0-9a-f]{40}(?:\s+#.*)?$")

    def test_online_freshness_is_scheduled_not_pr_required(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "source-freshness.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("schedule:", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("check_spring_cloud_policy.py --online", workflow)
        self.assertIn("check_spring_project_lifecycle.py --online", workflow)
        self.assertIn("check_links.py --online", workflow)
        self.assertIn("--timeout 10 --retries 1 --workers 12", workflow)
        self.assertNotIn("pull_request:", workflow)
        self.assertNotIn("pull_request_target:", workflow)
        self.assertNotIn("write-all", workflow)
        self.assertIn("permissions:\n  contents: read\n", workflow)
        self.assertIn("timeout-minutes: 15", workflow)
        for line in (line.strip() for line in workflow.splitlines() if "uses:" in line):
            self.assertRegex(line, r"uses: [^@]+@[0-9a-f]{40}(?:\s+#.*)?$")

    def test_command_set_covers_every_repository_check(self) -> None:
        commands = validate_all.validation_commands("python-test")
        flattened = [" ".join(command) for _, command in commands]
        for required in (
            "validate_skill_structure.py",
            "validate_source_policy.py",
            "validate_routing_contract.py",
            "validate_behavior_cases.py",
            "check_spring_cloud_policy.py",
            "check_spring_project_lifecycle.py",
            "unittest discover",
            "check_links.py --offline",
        ):
            self.assertTrue(any(required in command for command in flattened), required)
        self.assertTrue(all(command[0] == "python-test" for _, command in commands))

    @patch("validate_all.subprocess.run")
    def test_runner_stops_at_first_failure(self, run: Mock) -> None:
        run.side_effect = [Mock(returncode=0), Mock(returncode=7), Mock(returncode=0)]
        commands = (("one", ("python", "one.py")), ("two", ("python", "two.py")), ("three", ("python", "three.py")))
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            result = validate_all.run(commands, ROOT)
        self.assertEqual(result, 7)
        self.assertEqual(run.call_count, 2)


if __name__ == "__main__":
    unittest.main()
