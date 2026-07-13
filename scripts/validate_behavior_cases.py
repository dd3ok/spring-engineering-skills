from __future__ import annotations

import json
import re

from skill_utils import ROOT, skill_directories


CASES_PATH = ROOT / "evals" / "behavior-cases.json"
ARTIFACT_MODES = {"none", "synthetic-inline", "repository-fixture"}
MIN_KOREAN_CASES = 2
HANGUL_PATTERN = re.compile(r"[\uac00-\ud7a3]")
MIN_KOREAN_PROMPT_SYLLABLES = 8
KOREAN_RESPONSE_CRITERION = "한국어로 응답"


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
        if case.get("artifact_mode") not in ARTIFACT_MODES:
            errors.append(f"{case_id or index} has an invalid artifact_mode")
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
