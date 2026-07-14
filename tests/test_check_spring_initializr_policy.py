from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_spring_initializr_policy as initializr  # noqa: E402


def capability(default: str, *values: str) -> dict[str, object]:
    return {
        "default": default,
        "values": [{"id": value, "name": value} for value in values],
    }


def valid_metadata() -> dict[str, object]:
    metadata = {
        "bootVersion": capability("4.1.0", "4.1.1-SNAPSHOT", "4.1.0"),
        "javaVersion": capability("17", "26", "25", "21", "17"),
        "type": capability("gradle-project", "gradle-project", "maven-project"),
        "language": capability("java", "java", "kotlin"),
        "packaging": capability("jar", "jar", "war"),
        "configurationFileFormat": capability("properties", "properties", "yaml"),
    }
    metadata["type"]["values"][0]["tags"] = {"build": "gradle", "format": "project"}
    return metadata


class CheckSpringInitializrPolicyTests(unittest.TestCase):
    def test_repository_contract_and_representative_metadata_are_valid(self) -> None:
        source, accept, errors = initializr.load_contract()
        self.assertEqual(errors, [])
        self.assertEqual(source, "https://start.spring.io/metadata/client")
        self.assertEqual(accept, initializr.EXPECTED_ACCEPT)
        payload = json.dumps(valid_metadata()).encode("utf-8")
        self.assertEqual(initializr.metadata_errors(payload), [])

    def test_missing_capability_and_unadvertised_default_report_drift(self) -> None:
        metadata = valid_metadata()
        del metadata["language"]
        metadata["bootVersion"]["default"] = "9.9.9"
        errors = initializr.metadata_errors(json.dumps(metadata).encode("utf-8"))
        self.assertTrue(any("capability is missing: language" in error for error in errors))
        self.assertTrue(any("default is not advertised: bootVersion=9.9.9" in error for error in errors))

    def test_default_project_type_requires_build_and_project_tags(self) -> None:
        metadata = valid_metadata()
        metadata["type"]["values"][0]["tags"] = {"format": "library"}
        errors = initializr.metadata_errors(json.dumps(metadata).encode("utf-8"))
        self.assertTrue(any("no build tag" in error for error in errors))
        self.assertTrue(any("not a project format" in error for error in errors))

    def test_invalid_json_and_content_type_are_rejected(self) -> None:
        self.assertTrue(initializr.metadata_errors(b"not-json"))
        self.assertIsNone(
            initializr.content_type_error(initializr.EXPECTED_ACCEPT + ";charset=UTF-8")
        )
        self.assertIn(
            "Content-Type changed",
            initializr.content_type_error("application/json") or "",
        )

    def test_contract_rejects_an_unapproved_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(
                json.dumps(
                    {
                        "metadata": {
                            "source": "https://example.com/metadata/client",
                            "accept": initializr.EXPECTED_ACCEPT,
                        }
                    }
                ),
                encoding="utf-8",
            )
            _, _, errors = initializr.load_contract(path)
        self.assertTrue(any("approved HTTPS endpoint" in error for error in errors))

    def test_fetch_deadline_rejects_nonfinite_values_and_times_out_worker(self) -> None:
        for timeout in (0.0, -1.0, float("inf"), float("nan")):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                initializr.fetch_with_deadline(
                    "https://start.spring.io/metadata/client",
                    initializr.EXPECTED_ACCEPT,
                    timeout,
                )
        with patch.object(
            initializr.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(cmd="worker", timeout=0.01),
        ) as run:
            with self.assertRaises(TimeoutError):
                initializr.fetch_with_deadline(
                    "https://start.spring.io/metadata/client",
                    initializr.EXPECTED_ACCEPT,
                    0.01,
                )
        self.assertEqual(run.call_args.kwargs["timeout"], 0.01)


if __name__ == "__main__":
    unittest.main()
