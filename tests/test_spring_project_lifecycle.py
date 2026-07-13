from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_spring_project_lifecycle  # noqa: E402


class SpringProjectLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = json.loads(
            (ROOT / "evals" / "spring-project-lifecycle.json").read_text(encoding="utf-8")
        )

    @staticmethod
    def active_card(
        *,
        name: str = "Spring Web Flow",
        locator: str = "/projects/spring-webflow",
    ) -> str:
        return f"""
            <article class="column is-4">
              <a class="box is-special item" href="{locator}">
                <div><h1 class="is-size-4">{name}</h1></div>
                <p>Project description outside the heading.</p>
              </a>
            </article>
        """

    @staticmethod
    def attic_card(name: str, locator: str) -> str:
        return f"""
            <article class="column is-3"><a class="is-link" href="{locator}">{name}</a></article>
        """

    def page(
        self,
        *,
        active: str | None = None,
        attic: str | None = None,
        include_heading: bool = True,
        before: str = "",
        after: str = "",
    ) -> bytes:
        active_html = (
            self.active_card()
            + self.active_card(name="Spring Shell", locator="/projects/spring-shell")
            if active is None
            else active
        )
        attic_html = (
            self.attic_card(
                "Spring Cloud Contract",
                "https://github.com/spring-cloud/spring-cloud-contract",
            )
            if attic is None
            else attic
        )
        heading = (
            '<h2 class="pb-5 has-big-border-dark-top is-size-4 has-text-weight-bold">'
            "Projects <span>in the Attic</span></h2>"
            if include_heading
            else ""
        )
        return f"""
            {before}
            <div class="container">
              <div class="list columns is-multiline pb-6">{active_html}</div>
              {heading}
              <div class="list-2 columns is-multiline pb-6">{attic_html}</div>
            </div>
            {after}
        """.encode()

    def test_catalog_and_consumer_markers_are_valid(self) -> None:
        self.assertEqual(
            check_spring_project_lifecycle.catalog_errors(
                self.catalog, ROOT, today=date(2026, 7, 13)
            ),
            [],
        )

    def test_official_sections_match_expected_statuses(self) -> None:
        self.assertEqual(
            check_spring_project_lifecycle.page_errors(self.catalog, self.page()), []
        )

    def test_moved_project_reports_lifecycle_drift(self) -> None:
        attic = self.attic_card("Spring Web Flow", "/projects/spring-webflow") + self.attic_card(
            "Spring Cloud Contract",
            "https://github.com/spring-cloud/spring-cloud-contract",
        )
        shell = self.active_card(name="Spring Shell", locator="/projects/spring-shell")
        payload = self.page(active=shell, attic=attic)
        errors = check_spring_project_lifecycle.page_errors(self.catalog, payload)
        self.assertTrue(any("Spring Web Flow expected active" in error for error in errors))

    def test_missing_attic_boundary_is_rejected(self) -> None:
        errors = check_spring_project_lifecycle.page_errors(
            self.catalog, self.page(include_heading=False)
        )
        self.assertEqual(errors, ["Spring projects page Attic boundary changed or disappeared"])

    def test_plain_text_or_wrong_link_cannot_satisfy_a_project_claim(self) -> None:
        shell = self.active_card(name="Spring Shell", locator="/projects/spring-shell")
        payload = self.page(
            active=self.active_card(locator="/unrelated") + shell,
            before="<script>const label = 'Spring Web Flow';</script>",
        )
        errors = check_spring_project_lifecycle.page_errors(self.catalog, payload)
        self.assertTrue(any("Spring Web Flow expected active" in error for error in errors))

    def test_navigation_link_cannot_replace_active_project_card(self) -> None:
        navigation = '<nav><a href="/projects/spring-webflow">Spring Web Flow</a></nav>'
        shell = self.active_card(name="Spring Shell", locator="/projects/spring-shell")
        errors = check_spring_project_lifecycle.page_errors(
            self.catalog, self.page(active=shell, before=navigation)
        )
        self.assertTrue(any("Spring Web Flow expected active" in error for error in errors))

    def test_footer_link_does_not_duplicate_project_status(self) -> None:
        footer = '<footer><a href="/projects/spring-webflow">Spring Web Flow</a></footer>'
        self.assertEqual(
            check_spring_project_lifecycle.page_errors(
                self.catalog, self.page(after=footer)
            ),
            [],
        )

    def test_status_binding_uses_word_boundaries(self) -> None:
        self.assertTrue(check_spring_project_lifecycle.marker_has_status("active project", "active"))
        self.assertFalse(
            check_spring_project_lifecycle.marker_has_status(
                "Spring Web Flow is inactive", "active"
            )
        )

    def test_boolean_cadence_and_windows_absolute_consumer_are_rejected(self) -> None:
        invalid_cadence = deepcopy(self.catalog)
        invalid_cadence["review_every_days"] = True
        self.assertTrue(
            any(
                "invalid review cadence" in error
                for error in check_spring_project_lifecycle.catalog_errors(
                    invalid_cadence, ROOT, today=date(2026, 7, 13)
                )
            )
        )
        invalid_path = deepcopy(self.catalog)
        invalid_path["claims"][0]["consumers"][0]["path"] = (
            "C:/repository/skills/spring-engineering-review/SKILL.md"
        )
        self.assertTrue(
            any(
                "invalid path" in error
                for error in check_spring_project_lifecycle.catalog_errors(
                    invalid_path, ROOT, today=date(2026, 7, 13)
                )
            )
        )


if __name__ == "__main__":
    unittest.main()
