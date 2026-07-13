from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import urljoin, urlsplit, urlunsplit

from check_spring_cloud_policy import fetch_with_deadline
from skill_utils import ROOT, is_link_or_junction
from validate_source_policy import has_exact_case


CATALOG_PATH = ROOT / "evals" / "spring-project-lifecycle.json"
TOP_LEVEL_FIELDS = {
    "schema_version",
    "source_locator",
    "reviewed_on",
    "review_every_days",
    "attic_marker",
    "claims",
}
CLAIM_FIELDS = {"id", "project_name", "project_locator", "status", "consumers"}
CONSUMER_FIELDS = {"path", "marker"}
VALID_STATUSES = {"active", "attic"}
ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
WINDOWS_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:")
APPROVED_PROJECT_HOSTS = {"spring.io", "github.com"}


def canonical_project_locator(locator: str, base_url: str | None = None) -> str:
    parsed = urlsplit(urljoin(base_url, locator) if base_url is not None else locator)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in APPROVED_PROJECT_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in {None, 443}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("project locator must use an approved canonical HTTPS URL")
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit(("https", str(parsed.hostname), path, "", ""))


class ProjectLinkParser(HTMLParser):
    def __init__(self, source_locator: str, attic_marker: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source_locator = source_locator
        self.attic_marker = attic_marker
        self.attic_boundaries = 0
        self.heading_parts: list[str] | None = None
        self.div_contexts: list[str | None] = []
        self.article_contexts: list[str | None] = []
        self.anchor_href: str | None = None
        self.anchor_parts: list[str] | None = None
        self.anchor_heading_parts: list[str] | None = None
        self.anchor_name: str | None = None
        self.anchor_context: str | None = None
        self.entries: list[tuple[str, str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "div":
            parent = self.div_contexts[-1] if self.div_contexts else None
            if {"list", "columns", "is-multiline"} <= classes:
                context = "active"
            elif {"list-2", "columns", "is-multiline"} <= classes:
                context = "attic"
            else:
                context = parent
            self.div_contexts.append(context)
        elif tag == "article":
            list_context = self.div_contexts[-1] if self.div_contexts else None
            if list_context == "active" and {"column", "is-4"} <= classes:
                context = "active"
            elif list_context == "attic" and {"column", "is-3"} <= classes:
                context = "attic"
            else:
                context = None
            self.article_contexts.append(context)
        elif tag == "h2" and {
            "has-big-border-dark-top",
            "is-size-4",
            "has-text-weight-bold",
        } <= classes:
            self.heading_parts = []
        elif tag == "a" and self.article_contexts:
            context = self.article_contexts[-1]
            is_project_link = (context == "active" and {"box", "item"} <= classes) or (
                context == "attic" and "is-link" in classes
            )
            if not is_project_link:
                return
            self.anchor_href = dict(attrs).get("href")
            self.anchor_parts = []
            self.anchor_name = None
            self.anchor_context = context
        elif tag == "h1" and self.anchor_parts is not None:
            self.anchor_heading_parts = []

    def handle_data(self, data: str) -> None:
        if self.heading_parts is not None:
            self.heading_parts.append(data)
        if self.anchor_parts is not None:
            self.anchor_parts.append(data)
        if self.anchor_heading_parts is not None:
            self.anchor_heading_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h2" and self.heading_parts is not None:
            heading = " ".join(" ".join(self.heading_parts).split())
            if heading == self.attic_marker:
                self.attic_boundaries += 1
            self.heading_parts = None
        elif tag == "h1" and self.anchor_heading_parts is not None:
            self.anchor_name = " ".join(" ".join(self.anchor_heading_parts).split())
            self.anchor_heading_parts = None
        elif tag == "a" and self.anchor_parts is not None:
            name = self.anchor_name or " ".join(" ".join(self.anchor_parts).split())
            href = self.anchor_href
            if name and isinstance(href, str):
                try:
                    locator = canonical_project_locator(href, self.source_locator)
                except ValueError:
                    pass
                else:
                    if self.anchor_context is not None:
                        self.entries.append((name, locator, self.anchor_context))
            self.anchor_href = None
            self.anchor_parts = None
            self.anchor_heading_parts = None
            self.anchor_name = None
            self.anchor_context = None
        elif tag == "article" and self.article_contexts:
            self.article_contexts.pop()
        elif tag == "div" and self.div_contexts:
            self.div_contexts.pop()


def marker_has_status(marker: str, status: str) -> bool:
    return re.search(
        rf"(?<![A-Za-z]){re.escape(status)}(?![A-Za-z])",
        marker,
        flags=re.IGNORECASE,
    ) is not None


def catalog_errors(
    catalog: object,
    root: Path = ROOT,
    *,
    today: date | None = None,
) -> list[str]:
    if (
        not isinstance(catalog, dict)
        or set(catalog) != TOP_LEVEL_FIELDS
        or catalog.get("schema_version") != "spring-project-lifecycle/1"
    ):
        return ["Spring project lifecycle catalog has invalid top-level fields"]

    errors: list[str] = []
    if catalog.get("source_locator") != "https://spring.io/projects/":
        errors.append("Spring project lifecycle catalog has an invalid source locator")
    attic_marker = catalog.get("attic_marker")
    if not isinstance(attic_marker, str) or not attic_marker.strip():
        errors.append("Spring project lifecycle catalog has an invalid Attic marker")

    cadence = catalog.get("review_every_days")
    if isinstance(cadence, bool) or not isinstance(cadence, int) or cadence <= 0:
        errors.append("Spring project lifecycle catalog has an invalid review cadence")
    reviewed_on = catalog.get("reviewed_on")
    try:
        reviewed_date = date.fromisoformat(reviewed_on) if isinstance(reviewed_on, str) else None
    except ValueError:
        reviewed_date = None
    if reviewed_date is None:
        errors.append("Spring project lifecycle catalog has an invalid reviewed_on date")
    else:
        age = ((today or datetime.now(UTC).date()) - reviewed_date).days
        if age < 0:
            errors.append("Spring project lifecycle catalog is future-dated")
        elif isinstance(cadence, int) and cadence > 0 and age > cadence:
            errors.append(f"Spring project lifecycle catalog is stale ({age} days > {cadence})")

    claims = catalog.get("claims")
    if not isinstance(claims, list) or not claims:
        return [*errors, "Spring project lifecycle claims must be non-empty"]

    seen_ids: set[str] = set()
    seen_projects: set[str] = set()
    seen_statuses: set[str] = set()
    seen_consumers: set[tuple[str, str]] = set()
    repository_root = root.resolve()
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict) or set(claim) != CLAIM_FIELDS:
            errors.append(f"Spring project lifecycle claim {index} has invalid fields")
            continue
        claim_id = claim.get("id")
        if (
            not isinstance(claim_id, str)
            or ID_PATTERN.fullmatch(claim_id) is None
            or claim_id in seen_ids
        ):
            errors.append(f"Spring project lifecycle claim {index} has an invalid or duplicate id")
            continue
        seen_ids.add(claim_id)
        project_name = claim.get("project_name")
        if (
            not isinstance(project_name, str)
            or not project_name.strip()
            or project_name in seen_projects
        ):
            errors.append(f"Spring project lifecycle claim {claim_id} has an invalid or duplicate project")
        else:
            seen_projects.add(project_name)
        project_locator = claim.get("project_locator")
        try:
            canonical_locator = (
                canonical_project_locator(project_locator)
                if isinstance(project_locator, str)
                else None
            )
        except ValueError:
            canonical_locator = None
        if canonical_locator is None or canonical_locator != project_locator:
            errors.append(f"Spring project lifecycle claim {claim_id} has an invalid project locator")
        status = claim.get("status")
        if not isinstance(status, str) or status not in VALID_STATUSES:
            errors.append(f"Spring project lifecycle claim {claim_id} has an invalid status")
        else:
            seen_statuses.add(status)
        consumers = claim.get("consumers")
        if not isinstance(consumers, list) or not consumers:
            errors.append(f"Spring project lifecycle claim {claim_id} has no consumers")
            continue
        for consumer_index, consumer in enumerate(consumers):
            label = f"Spring project lifecycle claim {claim_id} consumer {consumer_index}"
            if not isinstance(consumer, dict) or set(consumer) != CONSUMER_FIELDS:
                errors.append(f"{label} has invalid fields")
                continue
            path_value = consumer.get("path")
            marker = consumer.get("marker")
            if not isinstance(path_value, str) or not path_value:
                errors.append(f"{label} has an invalid path")
                continue
            if not isinstance(marker, str) or not marker:
                errors.append(f"{label} has an invalid marker")
                continue
            if isinstance(project_name, str) and project_name not in marker:
                errors.append(f"{label} marker is not bound to its project name")
            if isinstance(status, str) and not marker_has_status(marker, status):
                errors.append(f"{label} marker is not bound to its lifecycle status")
            identity = (path_value, marker)
            if identity in seen_consumers:
                errors.append(f"{label} is duplicated")
                continue
            seen_consumers.add(identity)
            portable = PurePosixPath(path_value)
            candidate = root / Path(*portable.parts)
            if (
                portable.is_absolute()
                or WINDOWS_DRIVE_PATTERN.match(path_value)
                or "\\" in path_value
                or ".." in portable.parts
                or portable.as_posix() != path_value
            ):
                errors.append(f"{label} has an invalid path")
                continue
            try:
                resolved = candidate.resolve(strict=True)
                resolved.relative_to(repository_root)
            except (OSError, ValueError):
                errors.append(f"{label} has an invalid path")
                continue
            if (
                not candidate.is_file()
                or not has_exact_case(candidate, root)
                or is_link_or_junction(candidate)
            ):
                errors.append(f"{label} has an invalid path")
                continue
            try:
                occurrences = candidate.read_text(encoding="utf-8").count(marker)
            except (OSError, UnicodeError) as error:
                errors.append(f"{label} could not be read: {error}")
                continue
            if occurrences != 1:
                errors.append(f"{label} marker occurs {occurrences} times instead of once")

    if seen_statuses != VALID_STATUSES:
        errors.append("Spring project lifecycle catalog must cover active and Attic claims")
    return errors


def load_catalog(
    path: Path = CATALOG_PATH,
    root: Path = ROOT,
    *,
    today: date | None = None,
) -> tuple[dict[str, object], list[str]]:
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return {}, [f"Spring project lifecycle catalog is invalid: {error}"]
    errors = catalog_errors(catalog, root, today=today)
    return catalog if isinstance(catalog, dict) else {}, errors


def page_errors(catalog: dict[str, object], payload: bytes) -> list[str]:
    source_locator = catalog.get("source_locator")
    attic_marker = catalog.get("attic_marker")
    claims = catalog.get("claims")
    if (
        not isinstance(source_locator, str)
        or not isinstance(attic_marker, str)
        or not isinstance(claims, list)
    ):
        return ["Spring project lifecycle claims are invalid"]
    parser = ProjectLinkParser(source_locator, attic_marker)
    try:
        parser.feed(payload.decode("utf-8"))
        parser.close()
    except UnicodeError as error:
        return [f"Spring projects page is not valid UTF-8: {error}"]
    if parser.attic_boundaries != 1:
        return ["Spring projects page Attic boundary changed or disappeared"]
    errors: list[str] = []
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        project_name = claim.get("project_name")
        project_locator = claim.get("project_locator")
        status = claim.get("status")
        if (
            not isinstance(project_name, str)
            or not isinstance(project_locator, str)
            or status not in VALID_STATUSES
        ):
            continue
        observed = [
            section
            for name, locator, section in parser.entries
            if name == project_name and locator == project_locator
        ]
        if observed != [status]:
            errors.append(
                f"Spring project lifecycle changed: {project_name} expected {status}, "
                f"observed exact project-link sections={observed}"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Spring project lifecycle claims and optionally check official-page drift."
    )
    parser.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()
    catalog, errors = load_catalog(args.catalog)
    if args.online and not errors:
        try:
            payload = fetch_with_deadline(str(catalog["source_locator"]), args.timeout)
        except (OSError, UnicodeError, ValueError) as error:
            detail = str(error).replace("Spring Cloud policy", "Spring project lifecycle")
            errors.append(f"Spring project lifecycle check is inconclusive: {detail}")
        else:
            errors.extend(page_errors(catalog, payload))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Spring project lifecycle catalog is valid" + (" and matches official markers." if args.online else "."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
