from __future__ import annotations

import json
import re
from skill_utils import ROOT, skill_directories


CASES_PATH = ROOT / "evals" / "routing-cases.json"
REVIEW_POLICY_PATH = ROOT / "evals" / "review-routing-policy.json"
ACTIVATION_CHANNELS = {"semantic", "explicit-name", "none"}


def load_cases() -> list[dict[str, object]]:
    data = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("routing-cases.json must contain a JSON array")
    return data


def load_review_policy() -> tuple[set[str], dict[str, set[str]]]:
    data = json.loads(REVIEW_POLICY_PATH.read_text(encoding="utf-8"))
    always = data.get("always") if isinstance(data, dict) else None
    routes = data.get("routes") if isinstance(data, dict) else None
    if not isinstance(always, list) or not all(isinstance(value, str) for value in always):
        raise ValueError("review-routing-policy always must be a string array")
    if not isinstance(routes, dict) or not all(
        isinstance(name, str)
        and isinstance(values, list)
        and all(isinstance(value, str) for value in values)
        for name, values in routes.items()
    ):
        raise ValueError("review-routing-policy routes must map names to string arrays")
    return set(always), {name: set(values) for name, values in routes.items()}


def reference_is_routed(skill_dir, reference: str) -> bool:
    skill_text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    return f"`{reference}`" in skill_text


def validate_contract() -> list[str]:
    errors: list[str] = []
    skill_dirs = {path.name: path for path in skill_directories()}
    skill_names = set(skill_dirs)
    seen_ids: set[str] = set()
    positive_coverage: set[str] = set()
    negative_coverage: set[str] = set()
    review_route_coverage: set[str] = set()
    positive_reference_coverage: dict[str, set[str]] = {name: set() for name in skill_names}
    split_coverage: dict[str, set[str]] = {name: set() for name in (*skill_names, "none")}
    try:
        review_always, review_policy = load_review_policy()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return [f"invalid review routing policy: {error}"]
    review_root = skill_dirs.get("spring-engineering-review")
    if review_root is not None:
        skill_text = (review_root / "SKILL.md").read_text(encoding="utf-8")
        routed_refs = set(re.findall(r"`(references/[^`]+)`", skill_text))
        policy_refs = set(review_always)
        for values in review_policy.values():
            policy_refs.update(values)
        missing_policy = routed_refs - policy_refs
        extra_policy = policy_refs - routed_refs
        if missing_policy:
            errors.append("review references missing from routing policy: " + ", ".join(sorted(missing_policy)))
        if extra_policy:
            errors.append("review routing policy references absent from SKILL.md: " + ", ".join(sorted(extra_policy)))
        route_rows = {
            route: set(re.findall(r"`(references/[^`]+)`", load_cell))
            for route, load_cell in re.findall(
                r"(?m)^\| [^|]+ \| `([a-z0-9-]+)` \| (.+) \|$", skill_text
            )
        }
        expected_rows = {"always", *review_policy}
        if set(route_rows) != expected_rows:
            errors.append("review SKILL route IDs do not match routing policy")
        for route, refs in route_rows.items():
            expected_refs = review_always if route == "always" else review_policy.get(route, set())
            if refs != expected_refs:
                errors.append(f"review SKILL route row does not match routing policy: {route}")

    for item in load_cases():
        if not isinstance(item, dict):
            errors.append("every routing case must be an object")
            continue
        case_id = item.get("id")
        prompt = item.get("prompt")
        expected = item.get("expected_skill")
        channel = item.get("activation_channel")
        signals = item.get("route_signals")
        split = item.get("split")
        intent_family = item.get("intent_family")
        refs = item.get("expected_refs")
        forbidden_refs = item.get("forbidden_refs", [])
        review_routes = item.get("review_routes")
        forbidden = item.get("forbidden_skills")
        if not isinstance(case_id, str) or not case_id:
            errors.append("routing case has an invalid id")
            continue
        if case_id in seen_ids:
            errors.append(f"duplicate case id: {case_id}")
        seen_ids.add(case_id)
        if not isinstance(prompt, str) or not isinstance(channel, str) or channel not in ACTIVATION_CHANNELS:
            errors.append(f"{case_id} has invalid prompt or activation_channel")
            continue
        if expected is not None and (not isinstance(expected, str) or expected not in skill_names):
            errors.append(f"{case_id} has unknown expected_skill: {expected}")
            continue
        if split not in {"train", "validation"} or not isinstance(intent_family, str) or not intent_family:
            errors.append(f"{case_id} has invalid split or intent_family")
            continue
        split_coverage[expected if isinstance(expected, str) else "none"].add(split)
        if not isinstance(signals, list) or not all(isinstance(value, str) and value for value in signals):
            errors.append(f"{case_id} route_signals must be non-empty strings")
            continue
        if expected is not None and not signals:
            errors.append(f"{case_id} needs at least one route signal")
        if not isinstance(refs, list) or not all(isinstance(value, str) for value in refs):
            errors.append(f"{case_id} expected_refs must be a string array")
            continue
        if not isinstance(forbidden_refs, list) or not all(
            isinstance(value, str) for value in forbidden_refs
        ):
            errors.append(f"{case_id} forbidden_refs must be a string array")
            continue
        if not isinstance(forbidden, list) or not all(isinstance(value, str) for value in forbidden):
            errors.append(f"{case_id} forbidden_skills must be a string array")
            continue
        unknown_forbidden = set(forbidden) - skill_names
        if unknown_forbidden:
            errors.append(f"{case_id} has unknown forbidden skills: {', '.join(sorted(unknown_forbidden))}")
        if expected in forbidden:
            errors.append(f"{case_id} expects and forbids the same skill")

        prompt_folded = prompt.casefold()
        missing_signals = [signal for signal in signals if signal.casefold() not in prompt_folded]
        if missing_signals:
            errors.append(f"{case_id} prompt lacks route signals: {', '.join(missing_signals)}")
        if channel == "explicit-name":
            if expected is None or expected not in prompt:
                errors.append(f"{case_id} must contain the expected skill name")
        elif channel == "semantic" and expected is not None and expected in prompt:
            errors.append(f"{case_id} semantic prompt must not name the skill")
        elif channel == "none" and any(name in prompt for name in skill_names):
            errors.append(f"{case_id} must not name a skill")
        if channel == "none" and expected is not None:
            errors.append(f"{case_id} channel none cannot expect a skill")
        if expected is None and refs:
            errors.append(f"{case_id} cannot expect references without a skill")
        if expected is None and forbidden_refs:
            errors.append(f"{case_id} cannot forbid references without a skill")
        overlap = set(refs) & set(forbidden_refs)
        if overlap:
            errors.append(f"{case_id} expects and forbids references: {', '.join(sorted(overlap))}")
        if expected == "spring-engineering-review":
            if not isinstance(review_routes, list) or not review_routes or not all(
                isinstance(value, str) and value for value in review_routes
            ):
                errors.append(f"{case_id} must declare review_routes")
            else:
                review_route_coverage.update(review_routes)
                unknown_routes = set(review_routes) - set(review_policy)
                if unknown_routes:
                    errors.append(f"{case_id} has unknown review routes: {', '.join(sorted(unknown_routes))}")
                else:
                    policy_refs = set(review_always)
                    for route in review_routes:
                        policy_refs.update(review_policy[route])
                    if set(refs) != policy_refs:
                        errors.append(f"{case_id} expected_refs do not match review routing policy")
        else:
            if review_routes is not None:
                errors.append(f"{case_id} declares review_routes for a non-review skill")
            if expected is not None:
                root = skill_dirs[expected]
                routed_refs = set(
                    re.findall(r"`(references/[^`]+)`", (root / "SKILL.md").read_text(encoding="utf-8"))
                )
                if set(refs) | set(forbidden_refs) != routed_refs:
                    errors.append(f"{case_id} does not exactly partition dedicated-skill references")
        if expected is not None:
            positive_coverage.add(expected)
            positive_reference_coverage[expected].update(refs)
            root = skill_dirs[expected]
            for reference in refs:
                if not reference.startswith("references/") or not (root / reference).is_file():
                    errors.append(f"{case_id} uses missing or non-local reference: {reference}")
                elif not reference_is_routed(root, reference):
                    errors.append(f"{case_id} expects a reference not routed by SKILL.md: {reference}")
            for reference in forbidden_refs:
                if not reference.startswith("references/") or not (root / reference).is_file():
                    errors.append(f"{case_id} forbids a missing or non-local reference: {reference}")
                elif not reference_is_routed(root, reference):
                    errors.append(f"{case_id} forbids a reference not routed by SKILL.md: {reference}")
        negative_coverage.update(forbidden)

    missing_positive = skill_names - positive_coverage
    if missing_positive:
        errors.append("skills without positive routing cases: " + ", ".join(sorted(missing_positive)))
    for owner, splits in sorted(split_coverage.items()):
        if splits != {"train", "validation"}:
            errors.append(f"{owner} routing cases must cover train and validation splits")
    missing_negative = skill_names - negative_coverage
    if missing_negative:
        errors.append("skills without negative/non-overlap cases: " + ", ".join(sorted(missing_negative)))
    missing_review_routes = set(review_policy) - review_route_coverage
    if missing_review_routes:
        errors.append("review routes without routing cases: " + ", ".join(sorted(missing_review_routes)))
    for skill_name, root in sorted(skill_dirs.items()):
        direct_refs = set(
            re.findall(r"`(references/[^`]+)`", (root / "SKILL.md").read_text(encoding="utf-8"))
        )
        missing_refs = direct_refs - positive_reference_coverage[skill_name]
        if missing_refs:
            errors.append(
                f"{skill_name} references without positive route coverage: "
                + ", ".join(sorted(missing_refs))
            )

    return errors


def main() -> int:
    errors = validate_contract()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Multi-skill semantic routing contract is valid (specification drift only, not model behavior).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
