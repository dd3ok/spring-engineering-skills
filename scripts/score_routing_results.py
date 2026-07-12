from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from skill_utils import ROOT, skill_directories


DEFAULT_CASES = ROOT / "evals" / "routing-cases.json"
MAX_RESULTS_BYTES = 8 * 1024 * 1024
RESULT_FIELDS = {"case_id", "selected_skill", "handoff_skills", "host", "model", "run_id"}


def load_cases(path: Path) -> list[dict[str, object]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("routing cases must be a JSON array")
    cases: list[dict[str, object]] = []
    seen: set[str] = set()
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"routing case {index} must be an object")
        case_id = item.get("id")
        prompt = item.get("prompt")
        expected = item.get("expected_skill")
        channel = item.get("activation_channel")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError(f"routing case {index} has an invalid id")
        if case_id in seen:
            raise ValueError(f"duplicate routing case id: {case_id}")
        if not isinstance(prompt, str) or not prompt:
            raise ValueError(f"routing case {case_id} has an invalid prompt")
        if expected is not None and not isinstance(expected, str):
            raise ValueError(f"routing case {case_id} has an invalid expected_skill")
        if channel not in {"semantic", "explicit-name", "none"}:
            raise ValueError(f"routing case {case_id} has an invalid activation_channel")
        seen.add(case_id)
        cases.append(item)
    return cases


def emit_blind_prompts(cases: list[dict[str, object]], destination: Path | None) -> None:
    lines = [
        json.dumps({"case_id": case["id"], "prompt": case["prompt"]}, ensure_ascii=False)
        for case in cases
    ]
    payload = "\n".join(lines) + "\n"
    if destination is None:
        sys.stdout.write(payload)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(payload, encoding="utf-8", newline="\n")


def load_results(path: Path) -> list[dict[str, object]]:
    if path.stat().st_size > MAX_RESULTS_BYTES:
        raise ValueError(f"routing results exceed {MAX_RESULTS_BYTES} bytes")
    results: list[dict[str, object]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            item = json.loads(raw_line)
        except json.JSONDecodeError as error:
            raise ValueError(f"routing result line {line_number} is invalid JSON: {error.msg}") from None
        if not isinstance(item, dict):
            raise ValueError(f"routing result line {line_number} must be an object")
        unknown = set(item) - RESULT_FIELDS
        if unknown:
            raise ValueError(
                f"routing result line {line_number} has unknown fields: {', '.join(sorted(unknown))}"
            )
        case_id = item.get("case_id")
        selected = item.get("selected_skill")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError(f"routing result line {line_number} has an invalid case_id")
        if selected is not None and (not isinstance(selected, str) or not selected):
            raise ValueError(f"routing result line {line_number} has an invalid selected_skill")
        handoffs = item.get("handoff_skills", [])
        if (
            not isinstance(handoffs, list)
            or not all(isinstance(value, str) and value for value in handoffs)
            or len(set(handoffs)) != len(handoffs)
        ):
            raise ValueError(f"routing result line {line_number} has invalid handoff_skills")
        if selected is None and handoffs:
            raise ValueError(f"routing result line {line_number} cannot hand off without an initial skill")
        for metadata in ("host", "model", "run_id"):
            value = item.get(metadata)
            if value is not None and (not isinstance(value, str) or not value):
                raise ValueError(f"routing result line {line_number} has invalid {metadata}")
        results.append(item)
    if not results:
        raise ValueError("routing results contain no records")
    return results


def rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def score_results(
    cases: list[dict[str, object]],
    results: list[dict[str, object]],
    *,
    require_complete: bool = True,
) -> tuple[dict[str, object], list[str]]:
    errors: list[str] = []
    case_by_id = {str(case["id"]): case for case in cases}
    known_skills = {path.name for path in skill_directories()}
    result_by_id: dict[str, dict[str, object]] = {}
    for item in results:
        case_id = str(item["case_id"])
        if case_id in result_by_id:
            errors.append(f"duplicate routing result: {case_id}")
            continue
        if case_id not in case_by_id:
            errors.append(f"unknown routing case: {case_id}")
            continue
        selected = item.get("selected_skill")
        if isinstance(selected, str) and selected not in known_skills:
            errors.append(f"unknown selected skill for {case_id}: {selected}")
            continue
        handoffs = item.get("handoff_skills", [])
        assert isinstance(handoffs, list)
        unknown_handoffs = sorted(set(handoffs) - known_skills)
        if unknown_handoffs:
            errors.append(f"unknown handoff skills for {case_id}: {', '.join(unknown_handoffs)}")
            continue
        result_by_id[case_id] = item

    missing = sorted(set(case_by_id) - set(result_by_id))
    if require_complete and missing:
        errors.append("missing routing results: " + ", ".join(missing))

    evaluated = 0
    correct = 0
    activation_cases = 0
    missed_activations = 0
    non_activation_cases = 0
    false_activations = 0
    wrong_skill = 0
    failures: list[dict[str, object]] = []
    observed_handoffs: list[dict[str, object]] = []
    channel_counts: dict[str, dict[str, int]] = {
        channel: {"evaluated": 0, "correct": 0}
        for channel in ("semantic", "explicit-name", "none")
    }

    for case in cases:
        case_id = str(case["id"])
        result = result_by_id.get(case_id)
        if result is None:
            continue
        expected = case.get("expected_skill")
        selected = result.get("selected_skill")
        handoffs = result.get("handoff_skills", [])
        assert isinstance(handoffs, list)
        channel = str(case["activation_channel"])
        if handoffs:
            observed_handoffs.append(
                {
                    "case_id": case_id,
                    "initial_skill": selected,
                    "handoff_skills": handoffs,
                }
            )
        evaluated += 1
        channel_counts[channel]["evaluated"] += 1
        if expected is None:
            non_activation_cases += 1
            if selected is not None:
                false_activations += 1
        else:
            activation_cases += 1
            if selected is None:
                missed_activations += 1
            elif selected != expected:
                wrong_skill += 1
        if selected == expected:
            correct += 1
            channel_counts[channel]["correct"] += 1
        else:
            failures.append(
                {
                    "case_id": case_id,
                    "channel": channel,
                    "expected_skill": expected,
                    "selected_skill": selected,
                }
            )

    by_channel: dict[str, dict[str, object]] = {}
    for channel, counts in channel_counts.items():
        by_channel[channel] = {
            **counts,
            "accuracy": rate(counts["correct"], counts["evaluated"]),
        }

    report: dict[str, object] = {
        "schema_version": "spring-routing-eval/1",
        "summary": {
            "evaluated": evaluated,
            "correct": correct,
            "accuracy": rate(correct, evaluated),
            "activation_cases": activation_cases,
            "missed_activations": missed_activations,
            "missed_activation_rate": rate(missed_activations, activation_cases),
            "non_activation_cases": non_activation_cases,
            "false_activations": false_activations,
            "false_activation_rate": rate(false_activations, non_activation_cases),
            "wrong_skill": wrong_skill,
        },
        "by_channel": by_channel,
        "failures": failures,
        "observed_handoffs": observed_handoffs,
        "missing_cases": missing,
    }
    return report, errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Emit blind routing prompts or score observed host routing results."
    )
    parser.add_argument("results", nargs="?", type=Path, help="Observed routing results in JSONL format.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument(
        "--emit-prompts",
        nargs="?",
        const="-",
        metavar="OUTPUT",
        help="Write case_id and prompt only; use '-' or omit OUTPUT for stdout.",
    )
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when any route is incorrect.")
    parser.add_argument("--json-report", type=Path)
    args = parser.parse_args()
    if (args.results is None) == (args.emit_prompts is None):
        parser.error("provide either a results path or --emit-prompts")
    return args


def main() -> int:
    args = parse_args()
    try:
        cases = load_cases(args.cases)
        if args.emit_prompts is not None:
            destination = None if args.emit_prompts == "-" else Path(args.emit_prompts)
            emit_blind_prompts(cases, destination)
            return 0
        results = load_results(args.results)
        report, errors = score_results(cases, results, require_complete=not args.allow_partial)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2
    summary = report["summary"]
    assert isinstance(summary, dict)
    print(
        "Routing eval: "
        f"{summary['correct']}/{summary['evaluated']} correct, "
        f"accuracy={summary['accuracy']:.3f}, "
        f"false_activation_rate={summary['false_activation_rate']:.3f}, "
        f"missed_activation_rate={summary['missed_activation_rate']:.3f}"
    )
    if args.json_report is not None:
        args.json_report.parent.mkdir(parents=True, exist_ok=True)
        args.json_report.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
        )
    failures = report["failures"]
    assert isinstance(failures, list)
    return 1 if args.strict and failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
