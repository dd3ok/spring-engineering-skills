from __future__ import annotations

import json

from skill_utils import ROOT, skill_directories


CASES_PATH = ROOT / "evals" / "behavior-cases.json"
ARTIFACT_MODES = {"none", "synthetic-inline", "repository-fixture"}


def validate_cases() -> list[str]:
    errors: list[str] = []
    data = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return ["behavior-cases.json must contain an array"]
    skills = {path.name for path in skill_directories()}
    seen: set[str] = set()
    covered: set[str] = set()
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
        if case.get("artifact_mode") not in ARTIFACT_MODES:
            errors.append(f"{case_id or index} has an invalid artifact_mode")
        for field in ("must", "must_not"):
            values = case.get(field)
            if not isinstance(values, list) or not values or not all(isinstance(value, str) and value for value in values):
                errors.append(f"{case_id or index} {field} must be non-empty strings")
        if isinstance(case.get("must"), list) and isinstance(case.get("must_not"), list):
            overlap = set(case["must"]) & set(case["must_not"])
            if overlap:
                errors.append(f"{case_id or index} contradicts itself: {', '.join(sorted(overlap))}")
    missing = skills - covered
    if missing:
        errors.append("skills without behavior cases: " + ", ".join(sorted(missing)))
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
