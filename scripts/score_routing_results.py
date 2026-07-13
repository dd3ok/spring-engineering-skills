from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from skill_utils import ROOT, skill_directories


DEFAULT_CASES = ROOT / "evals" / "routing-cases.json"
MAX_RESULTS_BYTES = 8 * 1024 * 1024
RESULT_FIELDS = {
    "case_id", "selected_skill", "handoff_skills", "host", "host_version", "model", "run_id",
    "skill_commit", "observation_kind", "trace_id",
}
COMMIT = re.compile(r"^[a-f0-9]{40}$")
EXACT_NAME_MIN_ACCURACY = 1.0
VALIDATION_MIN_ACCURACY = 0.9
MAX_FALSE_ACTIVATION_RATE = 0.05
MAX_MISSED_ACTIVATION_RATE = 0.1


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
        split = item.get("split")
        intent_family = item.get("intent_family")
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
        if split is not None and split not in {"train", "validation"}:
            raise ValueError(f"routing case {case_id} has an invalid split")
        if intent_family is not None and (not isinstance(intent_family, str) or not intent_family):
            raise ValueError(f"routing case {case_id} has an invalid intent_family")
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


def require_canonical_cases(
    cases: list[dict[str, object]], canonical: list[dict[str, object]]
) -> None:
    if cases != canonical:
        raise ValueError("--strict requires the canonical routing case suite")


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
        for metadata in ("host", "host_version", "model", "run_id", "trace_id"):
            value = item.get(metadata)
            if value is not None and (not isinstance(value, str) or not value):
                raise ValueError(f"routing result line {line_number} has invalid {metadata}")
        commit = item.get("skill_commit")
        if commit is not None and (not isinstance(commit, str) or COMMIT.fullmatch(commit) is None):
            raise ValueError(f"routing result line {line_number} has invalid skill_commit")
        observation = item.get("observation_kind")
        if observation is not None and observation != "host-activation-trace":
            raise ValueError(f"routing result line {line_number} has invalid observation_kind")
        results.append(item)
    if not results:
        raise ValueError("routing results contain no records")
    return results


def rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def release_gate_failures(report: dict[str, object]) -> list[str]:
    summary = report["summary"]
    by_channel = report["by_channel"]
    by_split = report["by_split"]
    case_results = report["case_results"]
    assert isinstance(summary, dict)
    assert isinstance(by_channel, dict)
    assert isinstance(by_split, dict)
    assert isinstance(case_results, list)
    failures: list[str] = []
    exact_name = by_channel["explicit-name"]
    validation = by_split["validation"]
    assert isinstance(exact_name, dict) and isinstance(validation, dict)
    if not exact_name["evaluated"]:
        failures.append("exact-name coverage is missing")
    elif exact_name["accuracy"] < EXACT_NAME_MIN_ACCURACY:
        failures.append("exact-name accuracy is below 100%")
    if not validation["evaluated"]:
        failures.append("validation split coverage is missing")
    elif validation["accuracy"] < VALIDATION_MIN_ACCURACY:
        failures.append("validation accuracy is below 90%")
    if not summary["activation_cases"]:
        failures.append("activation coverage is missing")
    if not summary["non_activation_cases"]:
        failures.append("non-activation coverage is missing")
    if summary["false_activation_rate"] > MAX_FALSE_ACTIVATION_RATE:
        failures.append("false activation rate exceeds 5%")
    if summary["missed_activation_rate"] > MAX_MISSED_ACTIVATION_RATE:
        failures.append("missed activation rate exceeds 10%")
    failed_cases = [str(item["case_id"]) for item in case_results if not item["passed"]]
    if failed_cases:
        failures.append("case majority failed: " + ", ".join(failed_cases))
    if report["missing_cases"] or report["incomplete_cases"]:
        failures.append("case or repeated-run coverage is incomplete")
    return failures


def score_results(
    cases: list[dict[str, object]],
    results: list[dict[str, object]],
    *,
    require_complete: bool = True,
    expected_runs: int = 1,
    require_trace: bool = False,
    pass_threshold: float = 0.5,
) -> tuple[dict[str, object], list[str]]:
    if expected_runs < 1:
        raise ValueError("expected_runs must be positive")
    if not 0 <= pass_threshold < 1:
        raise ValueError("pass_threshold must be between 0 (inclusive) and 1 (exclusive)")
    errors: list[str] = []
    case_by_id = {str(case["id"]): case for case in cases}
    known_skills = {path.name for path in skill_directories()}
    invalid_expected = {
        case_id
        for case_id, case in case_by_id.items()
        if isinstance(case.get("expected_skill"), str)
        and case["expected_skill"] not in known_skills
    }
    for case_id in sorted(invalid_expected):
        errors.append(f"unknown expected skill for {case_id}: {case_by_id[case_id]['expected_skill']}")
    result_by_key: dict[tuple[str, str], dict[str, object]] = {}
    results_by_case: dict[str, list[dict[str, object]]] = {case_id: [] for case_id in case_by_id}
    trace_ids: set[str] = set()
    trace_cohort: tuple[str, str, str, str] | None = None
    for item in results:
        case_id = str(item["case_id"])
        if case_id not in case_by_id:
            errors.append(f"unknown routing case: {case_id}")
            continue
        raw_run_id = item.get("run_id")
        if expected_runs > 1 and not isinstance(raw_run_id, str):
            errors.append(f"routing result requires run_id for repeated case: {case_id}")
            continue
        run_id = raw_run_id if isinstance(raw_run_id, str) else "single"
        key = (case_id, run_id)
        if key in result_by_key:
            errors.append(f"duplicate routing result: {case_id}/{run_id}")
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
        if require_trace:
            missing_trace = [
                field
                for field in ("host", "host_version", "model", "run_id", "skill_commit", "trace_id")
                if not isinstance(item.get(field), str) or not item.get(field)
            ]
            if item.get("observation_kind") != "host-activation-trace" or missing_trace:
                errors.append(
                    f"routing result lacks host activation trace provenance for {case_id}/{run_id}: "
                    + ", ".join(missing_trace or ["observation_kind"])
                )
                continue
            trace_id = str(item["trace_id"])
            if trace_id in trace_ids:
                errors.append(f"duplicate host activation trace_id: {trace_id}")
                continue
            cohort = (
                str(item["host"]),
                str(item["host_version"]),
                str(item["model"]),
                str(item["skill_commit"]),
            )
            if trace_cohort is None:
                trace_cohort = cohort
            elif cohort != trace_cohort:
                errors.append(f"mixed routing trace cohort for {case_id}/{run_id}")
                continue
            trace_ids.add(trace_id)
        result_by_key[key] = item
        results_by_case[case_id].append(item)

    missing = sorted(case_id for case_id, items in results_by_case.items() if not items)
    if require_complete and missing:
        errors.append("missing routing results: " + ", ".join(missing))
    incomplete: list[str] = []
    for case_id, items in results_by_case.items():
        if items and len(items) != expected_runs:
            incomplete.append(f"{case_id}={len(items)}/{expected_runs}")
    if require_complete and incomplete:
        errors.append("incomplete routing result runs: " + ", ".join(sorted(incomplete)))
    excessive = [case_id for case_id, items in results_by_case.items() if len(items) > expected_runs]
    if excessive:
        errors.append("too many routing result runs: " + ", ".join(sorted(excessive)))

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
    split_counts: dict[str, dict[str, int]] = {
        split: {"evaluated": 0, "correct": 0} for split in ("train", "validation", "unspecified")
    }
    skill_counts: dict[str, dict[str, int]] = {
        skill: {"evaluated": 0, "correct": 0} for skill in sorted(known_skills)
    }
    case_results: list[dict[str, object]] = []

    for case in cases:
        case_id = str(case["id"])
        if case_id in invalid_expected:
            continue
        case_runs = results_by_case.get(case_id, [])
        if not case_runs:
            continue
        expected = case.get("expected_skill")
        channel = str(case["activation_channel"])
        split = str(case.get("split", "unspecified"))
        case_correct = 0
        for result in case_runs:
            selected = result.get("selected_skill")
            handoffs = result.get("handoff_skills", [])
            assert isinstance(handoffs, list)
            if handoffs:
                observed_handoffs.append(
                    {
                        "case_id": case_id,
                        "run_id": result.get("run_id"),
                        "initial_skill": selected,
                        "handoff_skills": handoffs,
                    }
                )
            evaluated += 1
            channel_counts[channel]["evaluated"] += 1
            split_counts[split]["evaluated"] += 1
            if isinstance(expected, str):
                skill_counts[expected]["evaluated"] += 1
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
                case_correct += 1
                channel_counts[channel]["correct"] += 1
                split_counts[split]["correct"] += 1
                if isinstance(expected, str):
                    skill_counts[expected]["correct"] += 1
            else:
                failures.append(
                    {
                        "case_id": case_id,
                        "run_id": result.get("run_id"),
                        "channel": channel,
                        "expected_skill": expected,
                        "selected_skill": selected,
                    }
                )
        case_accuracy = rate(case_correct, len(case_runs))
        case_results.append(
            {
                "case_id": case_id,
                "split": split,
                "runs": len(case_runs),
                "correct": case_correct,
                "accuracy": case_accuracy,
                "passed": case_accuracy > pass_threshold,
            }
        )

    by_channel: dict[str, dict[str, object]] = {}
    for channel, counts in channel_counts.items():
        by_channel[channel] = {
            **counts,
            "accuracy": rate(counts["correct"], counts["evaluated"]),
        }

    by_split = {
        split: {**counts, "accuracy": rate(counts["correct"], counts["evaluated"])}
        for split, counts in split_counts.items()
    }
    by_skill = {
        skill: {**counts, "accuracy": rate(counts["correct"], counts["evaluated"])}
        for skill, counts in skill_counts.items()
        if counts["evaluated"]
    }

    report: dict[str, object] = {
        "schema_version": "spring-routing-eval/2",
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
            "cases_evaluated": len(case_results),
            "cases_passed": sum(bool(item["passed"]) for item in case_results),
        },
        "by_channel": by_channel,
        "by_split": by_split,
        "by_skill": by_skill,
        "case_results": case_results,
        "failures": failures,
        "observed_handoffs": observed_handoffs,
        "missing_cases": missing,
        "incomplete_cases": incomplete,
    }
    report["release_gate_failures"] = release_gate_failures(report)
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
    parser.add_argument("--expected-runs", type=int, default=1)
    parser.add_argument("--pass-threshold", type=float, default=0.5)
    parser.add_argument("--require-trace", action="store_true")
    parser.add_argument(
        "--strict", action="store_true", help="Apply the canonical-suite release gate."
    )
    parser.add_argument("--json-report", type=Path)
    args = parser.parse_args()
    if (args.results is None) == (args.emit_prompts is None):
        parser.error("provide either a results path or --emit-prompts")
    if args.strict and args.allow_partial:
        parser.error("--strict cannot be combined with --allow-partial")
    if args.strict and args.expected_runs < 3:
        parser.error("--strict requires --expected-runs 3 or greater")
    if args.strict and args.pass_threshold != 0.5:
        parser.error("--strict requires the canonical 0.5 case-majority threshold")
    return args


def main() -> int:
    args = parse_args()
    try:
        cases = load_cases(args.cases)
        if args.emit_prompts is not None:
            destination = None if args.emit_prompts == "-" else Path(args.emit_prompts)
            emit_blind_prompts(cases, destination)
            return 0
        if args.strict:
            require_canonical_cases(cases, load_cases(DEFAULT_CASES))
        results = load_results(args.results)
        report, errors = score_results(
            cases,
            results,
            require_complete=not args.allow_partial,
            expected_runs=args.expected_runs,
            require_trace=args.require_trace or args.expected_runs > 1 or args.strict,
            pass_threshold=args.pass_threshold,
        )
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
    gate_failures = report["release_gate_failures"]
    assert isinstance(gate_failures, list)
    if args.strict and gate_failures:
        for failure in gate_failures:
            print(f"RELEASE GATE: {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
