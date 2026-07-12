from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_links  # noqa: E402


class CheckLinksTests(unittest.TestCase):
    def test_extracts_and_deduplicates_external_urls(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.md"
            path.write_text(
                "[one](https://example.com/a) https://example.com/a\n[two](local.md)\n",
                encoding="utf-8",
            )
            external, internal = check_links.extract_targets(path)
        self.assertEqual(external, {"https://example.com/a"})
        self.assertEqual(internal, {"local.md"})

    def test_markdown_url_preserves_balanced_parentheses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.md"
            path.write_text("[nested](https://example.com/a_(b))\n", encoding="utf-8")
            external, _ = check_links.extract_targets(path)
        self.assertEqual(external, {"https://example.com/a_(b)"})

    @patch("check_links.open_external", return_value=(200, "https://example.com/final"))
    def test_external_redirect_is_reported(self, _: object) -> None:
        result = check_links.check_external_link("https://example.com/start", timeout=1, retries=0)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.detail, "https://example.com/final")

    @patch("check_links.open_external", return_value=(200, "http://example.com/final"))
    def test_https_downgrade_fails(self, _: object) -> None:
        result = check_links.check_external_link("https://example.com/start", timeout=1, retries=0)
        self.assertEqual(result.status, "failed")

    @patch("check_links.open_external", side_effect=check_links.HTTPError("https://example.com", 404, "", {}, None))
    def test_404_fails(self, _: object) -> None:
        result = check_links.check_external_link("https://example.com", timeout=1, retries=0)
        self.assertEqual(result.status, "failed")

    @patch("check_links.open_external", side_effect=check_links.http.client.BadStatusLine("NOT-HTTP"))
    def test_malformed_http_response_is_inconclusive(self, _: object) -> None:
        result = check_links.check_external_link("https://example.com", timeout=1, retries=0)
        self.assertEqual(result.status, "inconclusive")

    def test_private_destination_is_blocked(self) -> None:
        result = check_links.check_external_link("http://127.0.0.1/internal", timeout=1, retries=0)
        self.assertEqual(result.status, "failed")
        self.assertIn("non-global", result.detail)

    @patch("check_links.resolved_addresses", return_value=("example.com", 443, ("203.0.113.10",)))
    @patch("check_links.PinnedHTTPSConnection")
    def test_connection_is_pinned_to_the_validated_address(self, connection_type: Mock, _: Mock) -> None:
        response = Mock(status=200)
        response.getheader.return_value = None
        connection_type.return_value.getresponse.return_value = response
        self.assertEqual(check_links.open_external("https://example.com/docs", 1), (200, "https://example.com/docs"))
        connection_type.assert_called_once_with("example.com", 443, "203.0.113.10", 1)

    def test_skill_runtime_path_is_resolved_from_skill_root(self) -> None:
        skill = ROOT / "skills" / "spring-evidence-collector" / "SKILL.md"
        _, internal = check_links.extract_targets(skill)
        self.assertIn("references/evidence-contract.md", internal)
        results = check_links.check_internal_links([skill])
        self.assertFalse([result for result in results if result.status == "failed"])


if __name__ == "__main__":
    unittest.main()
