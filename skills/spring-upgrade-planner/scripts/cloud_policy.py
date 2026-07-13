from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path


POLICY_PATH = Path(__file__).resolve().parents[1] / "references" / "spring-cloud-compatibility-policy.json"
POLICY_FIELDS = {"schema_version", "checked_on", "max_age_days", "source_locator", "rows"}
ROW_FIELDS = {"train", "source_text", "boot_lines"}
BOOT_LINE_FIELDS = {"line", "min_service_release"}
TRAIN = re.compile(r"^\d{4}\.\d{1,4}$")
BOOT_LINE = re.compile(r"^\d{1,4}\.\d{1,4}$")
CLOUD_VERSION = re.compile(r"^\d{4}\.\d{1,4}\.\d{1,4}(?:\.\d{1,4})?$")
BOOT_VERSION = re.compile(r"^\d{1,4}\.\d{1,4}\.\d{1,4}$")
SOURCE_LOCATOR = "https://spring.io/projects/spring-cloud/"
SOURCE_ROW = re.compile(
    r"^(?P<train>\d{4}\.\d{1,4})\.x aka [A-Za-z][A-Za-z0-9-]* "
    r"(?P<boot_lines>\d{1,4}\.\d{1,4}\.x(?:, \d{1,4}\.\d{1,4}\.x)*)"
    r"(?: \(Starting with (?P<minimum>\d{4}\.\d{1,4}\.\d{1,4})\))?$"
)


def version_key(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.split("."))


def validate_policy(data: object, *, today: date | None = None) -> list[str]:
    errors: list[str] = []
    current_date = today or date.today()
    if not isinstance(data, dict) or set(data) != POLICY_FIELDS:
        return ["Spring Cloud policy must contain the exact top-level fields"]
    if data.get("schema_version") != "spring-cloud-compatibility-policy/1":
        errors.append("Spring Cloud policy schema_version is invalid")
    checked_on = data.get("checked_on")
    max_age_days = data.get("max_age_days")
    if (
        not isinstance(checked_on, str)
        or isinstance(max_age_days, bool)
        or not isinstance(max_age_days, int)
        or not 1 <= max_age_days <= 365
    ):
        errors.append("Spring Cloud policy review date or max_age_days is invalid")
    else:
        try:
            checked_date = date.fromisoformat(checked_on)
        except ValueError:
            errors.append("Spring Cloud policy checked_on is invalid")
        else:
            age = (current_date - checked_date).days
            if age < 0:
                errors.append("Spring Cloud policy checked_on is in the future")
            elif age > max_age_days:
                errors.append("Spring Cloud policy is stale")
    if data.get("source_locator") != SOURCE_LOCATOR:
        errors.append("Spring Cloud policy source_locator is not the approved official table")
    rows = data.get("rows")
    if not isinstance(rows, list) or not rows:
        errors.append("Spring Cloud policy rows must be non-empty")
        return errors
    seen_trains: set[str] = set()
    seen_boot_lines: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != ROW_FIELDS:
            errors.append(f"Spring Cloud policy row {index} has invalid fields")
            continue
        train = row.get("train")
        if not isinstance(train, str) or TRAIN.fullmatch(train) is None or train in seen_trains:
            errors.append(f"Spring Cloud policy row {index} has an invalid or duplicate train")
            continue
        seen_trains.add(train)
        source_text = row.get("source_text")
        source_match = SOURCE_ROW.fullmatch(source_text) if isinstance(source_text, str) else None
        if source_match is None or source_match.group("train") != train:
            errors.append(f"Spring Cloud policy row {train} has invalid official source text")
            source_boot_lines: list[str] = []
            source_minimum = None
        else:
            source_boot_lines = [value.removesuffix(".x") for value in source_match.group("boot_lines").split(", ")]
            source_minimum = source_match.group("minimum")
        boot_lines = row.get("boot_lines")
        if not isinstance(boot_lines, list) or not boot_lines:
            errors.append(f"Spring Cloud policy mapping {train} has no Boot lines")
            continue
        local_lines: set[str] = set()
        declared_lines: list[str] = []
        declared_minimums: list[str] = []
        for line_index, item in enumerate(boot_lines):
            if not isinstance(item, dict) or set(item) != BOOT_LINE_FIELDS:
                errors.append(f"Spring Cloud policy {train} Boot line {line_index} has invalid fields")
                continue
            line = item.get("line")
            minimum = item.get("min_service_release")
            if (
                not isinstance(line, str)
                or BOOT_LINE.fullmatch(line) is None
                or line in local_lines
                or line in seen_boot_lines
            ):
                errors.append(f"Spring Cloud policy {train} has an invalid or duplicate Boot line")
                continue
            local_lines.add(line)
            seen_boot_lines.add(line)
            declared_lines.append(line)
            if (
                not isinstance(minimum, str)
                or CLOUD_VERSION.fullmatch(minimum) is None
                or not minimum.startswith(f"{train}.")
            ):
                errors.append(f"Spring Cloud policy {train}/{line} has an invalid minimum service release")
            else:
                declared_minimums.append(minimum)
        if declared_lines != source_boot_lines:
            errors.append(f"Spring Cloud policy row {train} Boot-line order does not match official source text")
        if len(declared_minimums) == len(declared_lines):
            base_minimum = f"{train}.0"
            expected = [base_minimum] * len(declared_lines)
            if source_minimum is not None and expected:
                expected[-1] = source_minimum
            if declared_minimums != expected:
                errors.append(f"Spring Cloud policy row {train} minimums do not match their official Boot lines")
    return errors


def load_policy(path: Path = POLICY_PATH, *, today: date | None = None) -> tuple[dict[str, object], list[str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return {}, [f"cannot read Spring Cloud policy: {error}"]
    errors = validate_policy(data, today=today)
    return (data if isinstance(data, dict) else {}), errors


def compatibility_error(policy: dict[str, object], boot_version: str, cloud_version: str) -> str | None:
    if BOOT_VERSION.fullmatch(boot_version) is None or CLOUD_VERSION.fullmatch(cloud_version) is None:
        return "Spring Boot or Spring Cloud target version is invalid"
    boot_line = ".".join(boot_version.split(".")[:2])
    for row in policy.get("rows", []):
        if not isinstance(row, dict):
            continue
        train = row.get("train")
        for item in row.get("boot_lines", []):
            if not isinstance(item, dict) or item.get("line") != boot_line:
                continue
            minimum = item.get("min_service_release")
            if not isinstance(train, str) or not isinstance(minimum, str):
                break
            if not cloud_version.startswith(f"{train}.") or version_key(cloud_version) < version_key(minimum):
                return f"Spring Boot {boot_line}.x requires Spring Cloud {minimum} or newer within the {train} train"
            return None
    return f"Spring Boot {boot_line}.x has no reviewed Spring Cloud compatibility mapping"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the reviewed Spring Cloud compatibility policy.")
    parser.add_argument("--policy", type=Path, default=POLICY_PATH)
    args = parser.parse_args()
    _, errors = load_policy(args.policy)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Spring Cloud compatibility policy is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
