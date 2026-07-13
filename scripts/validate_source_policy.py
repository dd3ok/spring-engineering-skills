from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from skill_utils import ROOT


URL_PATTERN = re.compile(r"https?://[^\s)>]+")
CHECKED_PATTERN = re.compile(r"(?m)^Checked on: (\d{4}-\d{2}-\d{2})\.")
FIXED_VERSION_PATTERN = re.compile(
    r"/(?:java(?:se)?/)?\d+(?:\.\d+)*(?:/|$)|(?:/|[-_])\d{1,4}\.\d{1,4}(?:\.\d{1,4}|\.x)?(?:[-_/]|$)",
    re.IGNORECASE,
)
PRERELEASE_PATTERN = re.compile(r"(?:SNAPSHOT|(?:^|[-./])(?:M|MILESTONE|RC)\d+|[-./](?:alpha|beta|ea)\d*)", re.IGNORECASE)
LATEST_LABEL_PATTERN = re.compile(r"\b(?:current|latest|stable|ga)\b", re.IGNORECASE)
MAX_REVIEW_AGE_DAYS = 180
REVIEW_CADENCES = {30, 45, 60, 90, 180}
PUBLISHER_POLICY_PATH = ROOT / "evals" / "source-publisher-policy.json"
REVIEW_REGISTER_FIELDS = {"schema_version", "claims"}
REVIEW_CLAIM_FIELDS = {"id", "sources", "consumers", "review_scope", "reviewed_on", "review_every_days"}


def load_publisher_policy(path: Path = PUBLISHER_POLICY_PATH) -> tuple[set[str], set[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    official = data.get("official_publishers") if isinstance(data, dict) else None
    supporting = data.get("supporting_publishers") if isinstance(data, dict) else None
    github = data.get("github_owners") if isinstance(data, dict) else None
    if (
        not isinstance(official, list)
        or not all(isinstance(value, str) and value for value in official)
        or not isinstance(supporting, list)
        or not all(isinstance(value, str) and value for value in supporting)
        or set(official) & set(supporting)
        or not isinstance(github, dict)
        or not all(
            isinstance(owner, str)
            and owner
            and isinstance(classification, str)
            and classification in {"official-project", "supporting-project"}
            for owner, classification in github.items()
        )
    ):
        raise ValueError("source publisher policy is invalid")
    return set(official) | set(supporting), set(github)


def source_files(root: Path = ROOT) -> tuple[Path, ...]:
    return tuple(sorted(root.glob("skills/*/references/*sources.md")))


def has_exact_case(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    current = root
    for part in relative.parts:
        try:
            names = {child.name for child in current.iterdir()}
        except OSError:
            return False
        if part not in names:
            return False
        current /= part
    return True


def validate_source_review_register(root: Path, current_date: date, source_urls: set[str]) -> list[str]:
    path = root / "evals" / "source-review-register.json"
    if not path.is_file():
        return ["source review register is missing"] if root.resolve() == ROOT.resolve() else []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return [f"source review register is invalid: {error}"]
    if not isinstance(data, dict) or set(data) != REVIEW_REGISTER_FIELDS or data.get("schema_version") != "spring-source-review/1":
        return ["source review register has invalid top-level fields"]
    claims = data.get("claims")
    if not isinstance(claims, list) or not claims:
        return ["source review register claims must be non-empty"]
    errors: list[str] = []
    seen_ids: set[str] = set()
    seen_sources: set[str] = set()
    repository_root = root.resolve()
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict) or set(claim) != REVIEW_CLAIM_FIELDS:
            errors.append(f"source review claim {index} has invalid fields")
            continue
        claim_id = claim.get("id")
        if not isinstance(claim_id, str) or not claim_id or claim_id in seen_ids:
            errors.append(f"source review claim {index} has an invalid or duplicate id")
            continue
        seen_ids.add(claim_id)
        sources = claim.get("sources")
        consumers = claim.get("consumers")
        scope = claim.get("review_scope")
        cadence = claim.get("review_every_days")
        if (
            not isinstance(sources, list)
            or not sources
            or not all(isinstance(value, str) and value for value in sources)
            or len(set(sources)) != len(sources)
        ):
            errors.append(f"source review claim {claim_id} has invalid sources")
        else:
            for source in sources:
                if source not in source_urls:
                    errors.append(f"source review claim {claim_id} uses a source outside approved maps: {source}")
                if source in seen_sources:
                    errors.append(f"source review source is assigned to multiple claims: {source}")
                seen_sources.add(source)
        if (
            not isinstance(consumers, list)
            or not consumers
            or not all(isinstance(value, str) and value for value in consumers)
            or len(set(consumers)) != len(consumers)
        ):
            errors.append(f"source review claim {claim_id} has invalid consumers")
        else:
            for consumer in consumers:
                portable = PurePosixPath(consumer)
                candidate = root / Path(*portable.parts)
                try:
                    resolved = candidate.resolve(strict=True)
                    resolved.relative_to(repository_root)
                except (OSError, ValueError):
                    errors.append(f"source review claim {claim_id} has an invalid consumer: {consumer}")
                    continue
                if (
                    portable.is_absolute()
                    or ".." in portable.parts
                    or portable.as_posix() != consumer
                    or not candidate.is_file()
                    or not has_exact_case(candidate, root)
                    or candidate.is_symlink()
                    or bool(getattr(candidate, "is_junction", lambda: False)())
                ):
                    errors.append(f"source review claim {claim_id} has an invalid consumer: {consumer}")
        if (
            not isinstance(scope, list)
            or not scope
            or not all(isinstance(value, str) and value for value in scope)
            or len(set(scope)) != len(scope)
        ):
            errors.append(f"source review claim {claim_id} has an invalid review_scope")
        if not isinstance(cadence, int) or cadence not in REVIEW_CADENCES:
            errors.append(f"source review claim {claim_id} has an invalid cadence")
        reviewed_on = claim.get("reviewed_on")
        if not isinstance(reviewed_on, str):
            errors.append(f"source review claim {claim_id} has an invalid reviewed_on date")
            continue
        try:
            reviewed_date = date.fromisoformat(reviewed_on)
        except ValueError:
            errors.append(f"source review claim {claim_id} has an invalid reviewed_on date")
            continue
        age = (current_date - reviewed_date).days
        if age < 0:
            errors.append(f"source review claim {claim_id} is future-dated")
        elif isinstance(cadence, int) and age > cadence:
            errors.append(f"source review claim {claim_id} is stale ({age} days > {cadence})")
    return errors


def validate_source_policy(
    root: Path = ROOT,
    *,
    today: date | None = None,
    max_age_days: int = MAX_REVIEW_AGE_DAYS,
) -> list[str]:
    errors: list[str] = []
    current_date = today or datetime.now(UTC).date()
    files = source_files(root)
    if not files:
        return ["no official source maps found"]
    try:
        approved_hosts, approved_github_owners = load_publisher_policy()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return [f"invalid source publisher policy: {error}"]

    urls_by_skill: dict[Path, dict[str, list[Path]]] = defaultdict(lambda: defaultdict(list))

    for path in files:
        relative = path.relative_to(root)
        text = path.read_text(encoding="utf-8")
        checked = CHECKED_PATTERN.search(text)
        if checked is None:
            errors.append(f"missing Checked on date: {relative}")
        else:
            try:
                checked_date = date.fromisoformat(checked.group(1))
            except ValueError:
                errors.append(f"invalid Checked on date: {relative}")
            else:
                age = (current_date - checked_date).days
                if age < 0:
                    errors.append(f"Checked on date is in the future: {relative}")
                elif age > max_age_days:
                    errors.append(
                        f"source review is stale ({age} days > {max_age_days}): {relative}"
                    )

        urls = [match.group(0).rstrip(".,;") for match in URL_PATTERN.finditer(text)]
        skill_root = relative.parents[1]
        for url in set(urls):
            urls_by_skill[skill_root][url].append(relative)
            try:
                parsed = urlsplit(url)
                hostname = parsed.hostname
                port = parsed.port
            except ValueError:
                parsed = None
                hostname = None
                port = None
            if (
                parsed is None
                or parsed.scheme != "https"
                or hostname is None
                or parsed.username is not None
                or parsed.password is not None
                or port not in {None, 443}
                or hostname not in approved_hosts | {"github.com"}
            ):
                errors.append(f"source URL uses an unapproved publisher: {relative}: {url}")
            elif hostname == "github.com":
                owner = parsed.path.strip("/").split("/", 1)[0]
                if owner not in approved_github_owners:
                    errors.append(f"GitHub source uses an unapproved owner: {relative}: {url}")
        for url, count in sorted(Counter(urls).items()):
            if count > 1:
                errors.append(f"duplicate URL in {relative}: {url}")

        for line_number, line in enumerate(text.splitlines(), start=1):
            lowered = line.lower()
            line_urls = [match.group(0).rstrip(".,;") for match in URL_PATTERN.finditer(line)]
            if any(PRERELEASE_PATTERN.search(url) for url in line_urls) and "non-ga" not in lowered:
                errors.append(
                    f"prerelease source must be labeled non-GA: {relative}:{line_number}"
                )
            if LATEST_LABEL_PATTERN.search(line) and any(FIXED_VERSION_PATTERN.search(url) for url in line_urls):
                errors.append(
                    f"fixed-version URL cannot be labeled current/latest/stable/GA: {relative}:{line_number}"
                )

    for skill_root, urls in sorted(urls_by_skill.items()):
        for url, locations in sorted(urls.items()):
            if len(locations) > 1:
                joined = ", ".join(str(location) for location in sorted(locations))
                errors.append(f"duplicate URL across source maps in {skill_root}: {url} ({joined})")

    source_urls = {url for urls in urls_by_skill.values() for url in urls}
    errors.extend(validate_source_review_register(root, current_date, source_urls))

    return errors


def main() -> int:
    errors = validate_source_policy()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Approved source publisher policy is valid ({len(source_files())} source maps).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
