from __future__ import annotations

import sys
import tempfile
import unittest
import json
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_source_policy  # noqa: E402


class SourcePolicyTests(unittest.TestCase):
    def write_source(self, root: Path, body: str) -> None:
        path = root / "skills" / "sample" / "references" / "official-sources.md"
        path.parent.mkdir(parents=True)
        path.write_text(body, encoding="utf-8")

    def validate(self, body: str) -> list[str]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_source(root, body)
            return validate_source_policy.validate_source_policy(
                root, today=date(2026, 7, 12), max_age_days=180
            )

    def test_valid_stable_sources_pass(self) -> None:
        self.assertEqual(
            self.validate(
                "# Official Sources\n\nChecked on: 2026-07-12. Re-check versions.\n\n"
                "- Stable docs: https://docs.spring.io/reference/\n"
            ),
            [],
        )

    def test_duplicate_url_is_rejected(self) -> None:
        errors = self.validate(
            "# Official Sources\n\nChecked on: 2026-07-12. Re-check versions.\n\n"
            "- One: https://docs.spring.io/reference/\n"
            "- Two: https://docs.spring.io/reference/\n"
        )
        self.assertTrue(any("duplicate URL" in error for error in errors))

    def test_duplicate_url_across_source_maps_in_one_skill_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            references = root / "skills" / "sample" / "references"
            references.mkdir(parents=True)
            body = (
                "# Official Sources\n\nChecked on: 2026-07-12. Re-check versions.\n\n"
                "- Stable docs: https://docs.spring.io/reference/\n"
            )
            (references / "core-sources.md").write_text(body, encoding="utf-8")
            (references / "data-sources.md").write_text(body, encoding="utf-8")
            errors = validate_source_policy.validate_source_policy(
                root, today=date(2026, 7, 12), max_age_days=180
            )
        self.assertTrue(any("duplicate URL across source maps" in error for error in errors))

    def test_same_url_in_different_portable_skills_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            body = (
                "# Official Sources\n\nChecked on: 2026-07-12. Re-check versions.\n\n"
                "- Stable docs: https://docs.spring.io/reference/\n"
            )
            for skill in ("one", "two"):
                references = root / "skills" / skill / "references"
                references.mkdir(parents=True)
                (references / "official-sources.md").write_text(body, encoding="utf-8")
            errors = validate_source_policy.validate_source_policy(
                root, today=date(2026, 7, 12), max_age_days=180
            )
        self.assertEqual(errors, [])

    def test_stale_review_is_rejected(self) -> None:
        errors = self.validate(
            "# Official Sources\n\nChecked on: 2025-01-01. Re-check versions.\n\n"
            "- Stable docs: https://docs.spring.io/reference/\n"
        )
        self.assertTrue(any("source review is stale" in error for error in errors))

    def test_unlabeled_snapshot_is_rejected(self) -> None:
        errors = self.validate(
            "# Official Sources\n\nChecked on: 2026-07-12. Re-check versions.\n\n"
            "- Docs: https://docs.spring.io/2.0.0-SNAPSHOT/reference/\n"
        )
        self.assertTrue(any("prerelease source" in error for error in errors))

    def test_unlabeled_release_candidate_is_rejected(self) -> None:
        for suffix in ("RC1", "M1", "MILESTONE1", "alpha1", "beta1", "EA"):
            with self.subTest(suffix=suffix):
                errors = self.validate(
                    "# Official Sources\n\nChecked on: 2026-07-12. Re-check versions.\n\n"
                    f"- Docs: https://docs.spring.io/4.1.0-{suffix}/reference/\n"
                )
                self.assertTrue(any("prerelease source" in error for error in errors))

    def test_fixed_version_cannot_be_called_current(self) -> None:
        errors = self.validate(
            "# Official Sources\n\nChecked on: 2026-07-12. Re-check versions.\n\n"
            "- Current guide: https://docs.spring.io/7.0/reference/\n"
        )
        self.assertTrue(any("fixed-version URL" in error for error in errors))

    def test_fixed_version_cannot_be_called_latest_or_stable(self) -> None:
        for label in ("Latest", "Stable", "GA"):
            with self.subTest(label=label):
                errors = self.validate(
                    "# Official Sources\n\nChecked on: 2026-07-12. Re-check versions.\n\n"
                    f"- {label} guide: https://docs.spring.io/7.0/reference/\n"
                )
                self.assertTrue(any("fixed-version URL" in error for error in errors))

    def test_vendor_fixed_version_url_shapes_cannot_be_called_current(self) -> None:
        for url in (
            "https://pulsar.apache.org/docs/4.1.x/security-overview/",
            "https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.1-Release-Notes",
            "https://github.com/spring-cloud/spring-cloud-release/wiki/Spring-Cloud-2025.1-Release-Notes",
        ):
            with self.subTest(url=url):
                errors = self.validate(
                    "# Official Sources\n\nChecked on: 2026-07-12. Re-check versions.\n\n"
                    f"- Current stable guide: {url}\n"
                )
                self.assertTrue(any("fixed-version URL" in error for error in errors))

    def test_unapproved_publisher_and_github_owner_are_rejected(self) -> None:
        for url in (
            "https://evil.example/fabricated",
            "https://github.com/not-spring/forged-guide",
        ):
            with self.subTest(url=url):
                errors = self.validate(
                    "# Official Sources\n\nChecked on: 2026-07-12. Re-check versions.\n\n"
                    f"- Fabricated: {url}\n"
                )
                self.assertTrue(any("unapproved" in error for error in errors))

    def test_repository_source_review_register_is_valid(self) -> None:
        source_urls = {
            match.group(0).rstrip(".,;")
            for path in validate_source_policy.source_files(ROOT)
            for match in validate_source_policy.URL_PATTERN.finditer(path.read_text(encoding="utf-8"))
        }
        self.assertEqual(
            validate_source_policy.validate_source_review_register(ROOT, date(2026, 7, 14), source_urls),
            [],
        )

    def test_source_review_register_rejects_stale_claim_and_missing_consumer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            register = root / "evals" / "source-review-register.json"
            register.parent.mkdir(parents=True)
            register.write_text(
                json.dumps(
                    {
                        "schema_version": "spring-source-review/1",
                        "claims": [
                            {
                                "id": "claim",
                                "sources": ["https://docs.spring.io/reference/"],
                                "consumers": ["missing.md"],
                                "review_scope": ["policy"],
                                "reviewed_on": "2026-01-01",
                                "review_every_days": 30,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            errors = validate_source_policy.validate_source_review_register(
                root, date(2026, 7, 13), {"https://docs.spring.io/reference/"}
            )
        self.assertTrue(any("invalid consumer" in error for error in errors))
        self.assertTrue(any("stale" in error for error in errors))

    def test_source_review_register_requires_unique_scope_and_regular_file_consumer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "consumer-dir").mkdir()
            register = root / "evals" / "source-review-register.json"
            register.parent.mkdir(parents=True)
            register.write_text(
                json.dumps(
                    {
                        "schema_version": "spring-source-review/1",
                        "claims": [
                            {
                                "id": "claim",
                                "sources": ["https://docs.spring.io/reference/"],
                                "consumers": ["consumer-dir"],
                                "review_scope": ["policy", "policy"],
                                "reviewed_on": "2026-07-12",
                                "review_every_days": 30,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            errors = validate_source_policy.validate_source_review_register(
                root, date(2026, 7, 13), {"https://docs.spring.io/reference/"}
            )
        self.assertTrue(any("invalid consumer" in error for error in errors))
        self.assertTrue(any("invalid review_scope" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
