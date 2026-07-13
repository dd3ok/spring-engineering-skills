from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath

from skill_utils import ROOT, is_link_or_junction, resolves_within, skill_directories
from validate_source_policy import has_exact_case


CASES_PATH = ROOT / "evals" / "behavior-cases.json"
FIXTURES_ROOT = ROOT / "evals" / "fixtures"
ARTIFACT_MODES = {"none", "synthetic-inline", "repository-fixture"}
MIN_KOREAN_CASES = 2
HANGUL_PATTERN = re.compile(r"[\uac00-\ud7a3]")
WINDOWS_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:")
MIN_KOREAN_PROMPT_SYLLABLES = 8
KOREAN_RESPONSE_CRITERION = "한국어로 응답"


def repository_fixture_errors(case_id: object, fixture_path: object) -> list[str]:
    label = str(case_id)
    if not isinstance(fixture_path, str) or not fixture_path:
        return [f"{label} repository-fixture requires fixture_path"]
    portable = PurePosixPath(fixture_path)
    if (
        portable.is_absolute()
        or WINDOWS_DRIVE_PATTERN.match(fixture_path)
        or "\\" in fixture_path
        or ".." in portable.parts
        or portable.as_posix() != fixture_path
        or portable.parts[:2] != ("evals", "fixtures")
    ):
        return [f"{label} has an invalid fixture_path"]
    candidate = ROOT / Path(*portable.parts)
    if (
        not candidate.is_dir()
        or not resolves_within(candidate, FIXTURES_ROOT)
        or not has_exact_case(candidate, ROOT)
        or is_link_or_junction(candidate)
    ):
        return [f"{label} has an invalid fixture_path"]
    try:
        entries = tuple(candidate.rglob("*"))
    except OSError:
        return [f"{label} fixture could not be inspected"]
    if not any(entry.is_file() for entry in entries):
        return [f"{label} fixture must contain at least one file"]
    if any(is_link_or_junction(entry) for entry in entries):
        return [f"{label} fixture contains a linked path"]
    return []


def validate_cases() -> list[str]:
    errors: list[str] = []
    data = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return ["behavior-cases.json must contain an array"]
    skills = {path.name for path in skill_directories()}
    seen: set[str] = set()
    covered: set[str] = set()
    korean_cases = 0
    for index, case in enumerate(data):
        if not isinstance(case, dict):
            errors.append(f"case {index} must be an object")
            continue
        case_id = case.get("id")
        skill = case.get("skill")
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            errors.append(f"case {index} has an invalid or duplicate id")
        else:
            seen.add(case_id)
        if skill not in skills:
            errors.append(f"{case_id or index} has an unknown skill")
        else:
            covered.add(str(skill))
        prompt = case.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            errors.append(f"{case_id or index} prompt must be non-empty")
        response_language = case.get("response_language")
        if response_language is not None and response_language != "ko":
            errors.append(f"{case_id or index} has an unsupported response_language")
        hangul_syllables = HANGUL_PATTERN.findall(prompt) if isinstance(prompt, str) else []
        if response_language == "ko":
            if len(hangul_syllables) < MIN_KOREAN_PROMPT_SYLLABLES:
                errors.append(f"{case_id or index} response_language ko requires a substantive Korean prompt")
            else:
                korean_cases += 1
        elif len(hangul_syllables) >= MIN_KOREAN_PROMPT_SYLLABLES:
            errors.append(f"{case_id or index} substantive Korean prompt must require response_language ko")
        artifact_mode = case.get("artifact_mode")
        if artifact_mode not in ARTIFACT_MODES:
            errors.append(f"{case_id or index} has an invalid artifact_mode")
        if artifact_mode == "repository-fixture":
            errors.extend(repository_fixture_errors(case_id or index, case.get("fixture_path")))
        elif "fixture_path" in case:
            errors.append(f"{case_id or index} fixture_path requires repository-fixture mode")
        for field in ("must", "must_not"):
            values = case.get(field)
            if not isinstance(values, list) or not values or not all(isinstance(value, str) and value for value in values):
                errors.append(f"{case_id or index} {field} must be non-empty strings")
        if (
            response_language == "ko"
            and isinstance(case.get("must"), list)
            and KOREAN_RESPONSE_CRITERION not in case["must"]
        ):
            errors.append(f"{case_id or index} must require a Korean response")
        if isinstance(case.get("must"), list) and isinstance(case.get("must_not"), list):
            must_items = {value for value in case["must"] if isinstance(value, str)}
            must_not_items = {value for value in case["must_not"] if isinstance(value, str)}
            overlap = must_items & must_not_items
            if overlap:
                errors.append(f"{case_id or index} contradicts itself: {', '.join(sorted(overlap))}")
    missing = skills - covered
    if missing:
        errors.append("skills without behavior cases: " + ", ".join(sorted(missing)))
    if korean_cases < MIN_KOREAN_CASES:
        errors.append(f"behavior cases require at least {MIN_KOREAN_CASES} Korean prompts")
    return errors


def main() -> int:
    errors = validate_cases()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Behavior evaluation contract is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
