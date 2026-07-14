from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from capture_behavior_artifact import CASE_ID, build_manifest
from skill_utils import ROOT, is_link_or_junction


DEFAULT_CASES = ROOT / "evals" / "behavior-cases.json"
MAX_RESULTS_BYTES = 8 * 1024 * 1024
MAX_ARTIFACT_MANIFEST_BYTES = 2 * 1024 * 1024
SHA256 = re.compile(r"^[a-f0-9]{64}$")
COMMIT = re.compile(r"^[a-f0-9]{40}$")
RUN_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
WINDOWS_RESERVED_NAMES = {
    "aux", "con", "nul", "prn",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}
ARTIFACT_PATH_FIELDS = {
    "artifact_manifest_path",
    "artifact_workspace_path",
}
ARTIFACT_FIELDS = {"artifact_manifest_sha256", *ARTIFACT_PATH_FIELDS}
RESULT_FIELDS = {
    "case_id", "run_id", "condition", "host", "host_version", "model", "skill_commit",
    "trace_id", "output_sha256", "grader_kind", "must_results", "must_not_results", "notes",
    "workspace_diff_sha256", "changed_paths", *ARTIFACT_FIELDS,
}
GRADES = {"pass", "fail", "unclear"}
EMPTY_WORKSPACE_DIFF_SHA256 = hashlib.sha256(b"[]").hexdigest()
MIN_MUST_PASS_RATE = 0.95
MIN_SKILL_MUST_PASS_RATE = 0.9


def load_cases(path: Path = DEFAULT_CASES) -> dict[str, dict[str, object]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("behavior cases must be an array")
    cases: dict[str, dict[str, object]] = {}
    known_skills = {path.name for path in (ROOT / "skills").iterdir() if path.is_dir()}
    for index, item in enumerate(data):
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or item["id"] in cases:
            raise ValueError("behavior cases contain an invalid or duplicate id")
        if item.get("skill") not in known_skills:
            raise ValueError(f"behavior case {item['id']} has an invalid skill")
        if not isinstance(item.get("prompt"), str) or not item["prompt"]:
            raise ValueError(f"behavior case {item['id']} has an invalid prompt")
        for field in ("must", "must_not"):
            values = item.get(field)
            if (
                not isinstance(values, list)
                or not values
                or not all(isinstance(value, str) and value for value in values)
            ):
                raise ValueError(f"behavior case {index} has invalid {field}")
        if item.get("artifact_mode") == "repository-fixture" and (
            not isinstance(item.get("fixture_tree_sha256"), str)
            or SHA256.fullmatch(str(item["fixture_tree_sha256"])) is None
        ):
            raise ValueError(
                f"behavior case {item['id']} has an invalid fixture_tree_sha256"
            )
        cases[str(item["id"])] = item
    return cases


def load_results(path: Path) -> list[dict[str, object]]:
    if path.stat().st_size > MAX_RESULTS_BYTES:
        raise ValueError(f"behavior results exceed {MAX_RESULTS_BYTES} bytes")
    results: list[dict[str, object]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError(f"behavior result line {line_number} is invalid JSON: {error.msg}") from None
        if not isinstance(item, dict) or set(item) - RESULT_FIELDS:
            raise ValueError(f"behavior result line {line_number} has invalid fields")
        for field in ("case_id", "run_id", "host", "host_version", "model", "trace_id"):
            if not isinstance(item.get(field), str) or not item[field]:
                raise ValueError(f"behavior result line {line_number} has invalid {field}")
        if item.get("condition") not in {"with-skill", "without-skill"}:
            raise ValueError(f"behavior result line {line_number} has invalid condition")
        if not isinstance(item.get("skill_commit"), str) or COMMIT.fullmatch(str(item["skill_commit"])) is None:
            raise ValueError(f"behavior result line {line_number} has invalid skill_commit")
        if not isinstance(item.get("output_sha256"), str) or SHA256.fullmatch(str(item["output_sha256"])) is None:
            raise ValueError(f"behavior result line {line_number} has invalid output_sha256")
        workspace_diff_sha256 = item.get("workspace_diff_sha256")
        if workspace_diff_sha256 is not None and (
            not isinstance(workspace_diff_sha256, str)
            or SHA256.fullmatch(workspace_diff_sha256) is None
        ):
            raise ValueError(f"behavior result line {line_number} has invalid workspace_diff_sha256")
        changed_paths = item.get("changed_paths")
        if changed_paths is not None and (
            not isinstance(changed_paths, list)
            or not all(
                isinstance(value, str)
                and value
                and not value.startswith("/")
                and not re.match(r"^[A-Za-z]:", value)
                and "\\" not in value
                and ".." not in Path(value).parts
                and Path(value).as_posix() == value
                for value in changed_paths
            )
            or len(set(changed_paths)) != len(changed_paths)
            or changed_paths != sorted(changed_paths)
        ):
            raise ValueError(f"behavior result line {line_number} has invalid changed_paths")
        artifact_manifest_sha256 = item.get("artifact_manifest_sha256")
        if artifact_manifest_sha256 is not None and (
            not isinstance(artifact_manifest_sha256, str)
            or SHA256.fullmatch(artifact_manifest_sha256) is None
        ):
            raise ValueError(
                f"behavior result line {line_number} has invalid artifact_manifest_sha256"
            )
        for field in ("artifact_manifest_path", "artifact_workspace_path"):
            value = item.get(field)
            if value is not None and not portable_relative_path(value):
                raise ValueError(f"behavior result line {line_number} has invalid {field}")
        artifact_path_values = [item.get(field) for field in ARTIFACT_PATH_FIELDS]
        if any(value is not None for value in artifact_path_values) and not all(
            value is not None for value in artifact_path_values
        ):
            raise ValueError(
                f"behavior result line {line_number} has incomplete artifact paths"
            )
        if any(value is not None for value in artifact_path_values) and (
            artifact_manifest_sha256 is None
        ):
            raise ValueError(
                f"behavior result line {line_number} has incomplete artifact binding"
            )
        if item.get("grader_kind") not in {"independent-human", "independent-model"}:
            raise ValueError(f"behavior result line {line_number} has invalid grader_kind")
        for field in ("must_results", "must_not_results"):
            values = item.get(field)
            if (
                not isinstance(values, list)
                or not values
                or not all(isinstance(value, str) and value in GRADES for value in values)
            ):
                raise ValueError(f"behavior result line {line_number} has invalid {field}")
        notes = item.get("notes")
        if notes is not None and (not isinstance(notes, str) or len(notes) > 2000):
            raise ValueError(f"behavior result line {line_number} has invalid notes")
        results.append(item)
    if not results:
        raise ValueError("behavior results contain no records")
    return results


def portable_relative_path(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and not value.startswith("/")
        and re.match(r"^[A-Za-z]:", value) is None
        and "\\" not in value
        and ".." not in Path(value).parts
        and Path(value).as_posix() == value
    )


def canonical_run_id(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) <= 64
        and RUN_ID.fullmatch(value) is not None
        and value not in WINDOWS_RESERVED_NAMES
    )


def resolve_bounded_path(
    root: Path,
    relative: str,
    *,
    expect_directory: bool,
    label: str,
) -> Path:
    if not portable_relative_path(relative):
        raise ValueError(f"{label} is not a portable relative path")
    resolved_root = root.resolve(strict=True)
    if not resolved_root.is_dir() or is_link_or_junction(root):
        raise ValueError(f"{label} root is not a regular directory")
    candidate = root
    for part in Path(relative).parts:
        candidate /= part
        if is_link_or_junction(candidate):
            raise ValueError(f"{label} contains a linked path")
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError(f"{label} escapes its root") from error
    if expect_directory and not resolved.is_dir():
        raise ValueError(f"{label} is not a directory")
    if not expect_directory and not resolved.is_file():
        raise ValueError(f"{label} is not a regular file")
    return resolved


def artifact_binding(
    case_id: str,
    case: dict[str, object],
    item: dict[str, object],
    artifact_root: Path,
    fixture_root: Path,
    expected_skill_commit: str | None,
) -> tuple[dict[str, object], Path, Path]:
    condition = str(item["condition"])
    run_id = str(item["run_id"])
    if CASE_ID.fullmatch(case_id) is None:
        raise ValueError("case_id must be a canonical lowercase path segment")
    if not canonical_run_id(run_id):
        raise ValueError(
            "run_id must be a canonical lowercase hyphenated identifier"
        )
    path_parts = [case_id, condition, run_id]
    if expected_skill_commit is not None:
        path_parts.insert(0, expected_skill_commit)
    run_root = "/".join(path_parts)
    expected_manifest_path = f"{run_root}/manifest.json"
    expected_workspace_path = f"{run_root}/workspace"
    supplied_manifest_path = item.get("artifact_manifest_path")
    supplied_workspace_path = item.get("artifact_workspace_path")
    if (
        supplied_manifest_path is not None
        and supplied_manifest_path != expected_manifest_path
    ):
        raise ValueError("artifact manifest path does not identify this result run")
    if (
        supplied_workspace_path is not None
        and supplied_workspace_path != expected_workspace_path
    ):
        raise ValueError("artifact workspace path does not identify this result run")
    manifest_path = resolve_bounded_path(
        artifact_root,
        expected_manifest_path,
        expect_directory=False,
        label="artifact manifest path",
    )
    workspace_path = resolve_bounded_path(
        artifact_root,
        expected_workspace_path,
        expect_directory=True,
        label="artifact workspace path",
    )
    try:
        manifest_path.relative_to(workspace_path)
    except ValueError:
        pass
    else:
        raise ValueError("artifact manifest must be outside the workspace")
    fixture_path = case.get("fixture_path")
    fixture_tree_sha256 = case.get("fixture_tree_sha256")
    if not isinstance(fixture_path, str):
        raise ValueError("repository-fixture case lacks fixture_path")
    if (
        not isinstance(fixture_tree_sha256, str)
        or SHA256.fullmatch(fixture_tree_sha256) is None
    ):
        raise ValueError("repository-fixture case lacks fixture_tree_sha256")
    fixture = resolve_bounded_path(
        fixture_root,
        fixture_path,
        expect_directory=True,
        label="fixture path",
    )
    if manifest_path.stat().st_size > MAX_ARTIFACT_MANIFEST_BYTES:
        raise ValueError(
            f"artifact manifest exceeds {MAX_ARTIFACT_MANIFEST_BYTES} bytes"
        )
    payload = manifest_path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != item["artifact_manifest_sha256"]:
        raise ValueError("artifact manifest SHA-256 does not match")
    manifest = json.loads(payload.decode("utf-8"))
    expected = build_manifest(case_id, fixture, workspace_path)
    if expected["fixture_tree_sha256"] != fixture_tree_sha256:
        raise ValueError("fixture content does not match the pinned fixture tree")
    if manifest != expected:
        raise ValueError("artifact manifest does not match the preserved workspace")
    workspace_diff_sha256 = item.get("workspace_diff_sha256")
    if (
        workspace_diff_sha256 is not None
        and workspace_diff_sha256 != expected["workspace_diff_sha256"]
    ):
        raise ValueError("workspace_diff_sha256 does not match the artifact manifest")
    changed_paths = item.get("changed_paths")
    if changed_paths is not None and changed_paths != expected["changed_paths"]:
        raise ValueError("changed_paths do not match the artifact manifest")
    return expected, manifest_path, workspace_path


def require_canonical_cases(
    cases: dict[str, dict[str, object]], canonical: dict[str, dict[str, object]]
) -> None:
    if cases != canonical:
        raise ValueError("--strict requires the canonical behavior case suite")


def score_results(
    cases: dict[str, dict[str, object]],
    results: list[dict[str, object]],
    *,
    expected_with_skill_runs: int = 3,
    expected_without_skill_runs: int = 1,
    require_complete: bool = True,
    artifact_root: Path | None = None,
    fixture_root: Path = ROOT,
    require_artifact_binding: bool = False,
    expected_skill_commit: str | None = None,
) -> tuple[dict[str, object], list[str]]:
    if expected_with_skill_runs < 1 or expected_without_skill_runs < 0:
        raise ValueError("expected behavior run counts are invalid")
    if expected_skill_commit is not None and COMMIT.fullmatch(expected_skill_commit) is None:
        raise ValueError("expected_skill_commit must be a lowercase 40-character commit")
    if require_artifact_binding and artifact_root is None:
        raise ValueError("artifact binding requires artifact_root")
    if require_artifact_binding and expected_skill_commit is None:
        raise ValueError("artifact binding requires expected_skill_commit")
    errors: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    trace_ids: set[str] = set()
    cohort: tuple[str, str, str, str] | None = None
    counts: dict[tuple[str, str], int] = {}
    must_total = must_pass = must_not_total = must_not_violations = must_not_unclear = 0
    baseline_must_total = baseline_must_pass = 0
    baseline_must_not_total = baseline_must_not_violations = baseline_must_not_unclear = 0
    by_skill: dict[str, dict[str, int]] = {}
    failures: list[dict[str, object]] = []
    criterion_results: dict[tuple[str, int], list[str]] = {}
    artifact_identities: list[tuple[Path, Path]] = []
    verified_artifact_runs = 0
    for item in results:
        case_id = str(item["case_id"])
        condition = str(item["condition"])
        run_id = str(item["run_id"])
        key = (case_id, condition, run_id)
        if key in seen:
            errors.append(f"duplicate behavior result: {case_id}/{condition}/{run_id}")
            continue
        seen.add(key)
        trace_id = str(item["trace_id"])
        if trace_id in trace_ids:
            errors.append(f"duplicate behavior trace_id: {trace_id}")
            continue
        trace_ids.add(trace_id)
        item_cohort = (
            str(item["host"]),
            str(item["host_version"]),
            str(item["model"]),
            str(item["skill_commit"]),
        )
        if expected_skill_commit is not None and item_cohort[3] != expected_skill_commit:
            errors.append(
                f"unexpected behavior skill_commit: {case_id}/{condition}/{run_id}"
            )
            continue
        if cohort is None:
            cohort = item_cohort
        elif item_cohort != cohort:
            errors.append(f"mixed behavior trace cohort: {case_id}/{condition}/{run_id}")
            continue
        case = cases.get(case_id)
        if case is None:
            errors.append(f"unknown behavior case: {case_id}")
            continue
        workspace_diff_sha256 = item.get("workspace_diff_sha256")
        changed_paths = item.get("changed_paths")
        artifact_manifest_sha256 = item.get("artifact_manifest_sha256")
        artifact_path_values = [item.get(field) for field in ARTIFACT_PATH_FIELDS]
        if case.get("artifact_mode") == "repository-fixture":
            has_artifact_binding = artifact_manifest_sha256 is not None
            if any(value is not None for value in artifact_path_values) and not all(
                value is not None for value in artifact_path_values
            ):
                errors.append(
                    f"repository-fixture result has incomplete artifact paths: "
                    f"{case_id}/{condition}/{run_id}"
                )
                continue
            if any(value is not None for value in artifact_path_values) and not (
                has_artifact_binding
            ):
                errors.append(
                    f"repository-fixture result has incomplete artifact binding: "
                    f"{case_id}/{condition}/{run_id}"
                )
                continue
            if require_artifact_binding and not has_artifact_binding:
                errors.append(
                    f"repository-fixture result lacks artifact binding: "
                    f"{case_id}/{condition}/{run_id}"
                )
                continue
            if has_artifact_binding:
                if artifact_root is None:
                    errors.append(
                        f"repository-fixture result needs an artifact root: "
                        f"{case_id}/{condition}/{run_id}"
                    )
                    continue
                label = f"{case_id}/{condition}/{run_id}"
                try:
                    expected, manifest_path, workspace_path = artifact_binding(
                        case_id,
                        case,
                        item,
                        artifact_root,
                        fixture_root,
                        expected_skill_commit,
                    )
                    duplicate_identity = any(
                        manifest_path.samefile(used_manifest)
                        or workspace_path.samefile(used_workspace)
                        for used_manifest, used_workspace in artifact_identities
                    )
                except (
                    OSError,
                    UnicodeError,
                    ValueError,
                    json.JSONDecodeError,
                    KeyError,
                ) as error:
                    errors.append(
                        f"invalid repository artifact binding: {label}: {error}"
                    )
                    continue
                if duplicate_identity:
                    errors.append(f"duplicate repository artifact binding: {label}")
                    continue
                artifact_identities.append((manifest_path, workspace_path))
                verified_artifact_runs += 1
                workspace_diff_sha256 = expected["workspace_diff_sha256"]
                changed_paths = expected["changed_paths"]
            elif not isinstance(workspace_diff_sha256, str) or not isinstance(
                changed_paths, list
            ):
                errors.append(
                    f"repository-fixture result lacks workspace evidence: "
                    f"{case_id}/{condition}/{run_id}"
                )
                continue
            if condition == "with-skill" and (
                not changed_paths or workspace_diff_sha256 == EMPTY_WORKSPACE_DIFF_SHA256
            ):
                errors.append(
                    f"repository-fixture with-skill run has no changes: "
                    f"{case_id}/{condition}/{run_id}"
                )
                continue
        elif (
            workspace_diff_sha256 is not None
            or changed_paths is not None
            or artifact_manifest_sha256 is not None
            or any(value is not None for value in artifact_path_values)
        ):
            errors.append(
                f"non-fixture result contains workspace evidence: {case_id}/{condition}/{run_id}"
            )
            continue
        must_results = item["must_results"]
        must_not_results = item["must_not_results"]
        assert isinstance(must_results, list) and isinstance(must_not_results, list)
        if len(must_results) != len(case.get("must", [])) or len(must_not_results) != len(case.get("must_not", [])):
            errors.append(f"behavior rubric result length mismatch: {case_id}/{condition}/{run_id}")
            continue
        counts[(case_id, condition)] = counts.get((case_id, condition), 0) + 1
        skill = str(case["skill"])
        if condition == "with-skill":
            skill_counts = by_skill.setdefault(
                skill,
                {"must": 0, "must_pass": 0, "must_not": 0, "violations": 0, "unclear": 0},
            )
            must_total += len(must_results)
            must_pass += sum(value == "pass" for value in must_results)
            must_not_total += len(must_not_results)
            must_not_violations += sum(value == "fail" for value in must_not_results)
            must_not_unclear += sum(value == "unclear" for value in must_not_results)
            skill_counts["must"] += len(must_results)
            skill_counts["must_pass"] += sum(value == "pass" for value in must_results)
            skill_counts["must_not"] += len(must_not_results)
            skill_counts["violations"] += sum(value == "fail" for value in must_not_results)
            skill_counts["unclear"] += sum(value == "unclear" for value in must_not_results)
            for index, value in enumerate(must_results):
                criterion_results.setdefault((case_id, index), []).append(value)
        else:
            baseline_must_total += len(must_results)
            baseline_must_pass += sum(value == "pass" for value in must_results)
            baseline_must_not_total += len(must_not_results)
            baseline_must_not_violations += sum(value == "fail" for value in must_not_results)
            baseline_must_not_unclear += sum(value == "unclear" for value in must_not_results)
        if any(value != "pass" for value in (*must_results, *must_not_results)):
            failures.append({"case_id": case_id, "condition": condition, "run_id": run_id})

    incomplete: list[str] = []
    excessive: list[str] = []
    for case_id in cases:
        for condition, expected in (
            ("with-skill", expected_with_skill_runs),
            ("without-skill", expected_without_skill_runs),
        ):
            actual = counts.get((case_id, condition), 0)
            if actual != expected:
                incomplete.append(f"{case_id}/{condition}={actual}/{expected}")
            if actual > expected:
                excessive.append(f"{case_id}/{condition}={actual}/{expected}")
    if require_complete and incomplete:
        errors.append("incomplete behavior result runs: " + ", ".join(incomplete))
    if excessive:
        errors.append("too many behavior result runs: " + ", ".join(excessive))

    def rate(numerator: int, denominator: int) -> float:
        return round(numerator / denominator, 6) if denominator else 0.0

    repeated_criterion_failures = [
        {
            "case_id": case_id,
            "criterion_index": index,
            "non_pass": sum(value != "pass" for value in values),
            "runs": len(values),
        }
        for (case_id, index), values in sorted(criterion_results.items())
        if len(values) >= 2 and sum(value != "pass" for value in values) > len(values) / 2
    ]

    report = {
        "schema_version": "spring-behavior-eval/1",
        "cohort": (
            {
                "host": cohort[0],
                "host_version": cohort[1],
                "model": cohort[2],
                "skill_commit": cohort[3],
            }
            if cohort is not None
            else None
        ),
        "artifact_binding": {
            "required": require_artifact_binding,
            "verified_runs": verified_artifact_runs,
            "expected_skill_commit": expected_skill_commit,
        },
        "summary": {
            "must_total": must_total,
            "must_pass": must_pass,
            "must_pass_rate": rate(must_pass, must_total),
            "must_not_total": must_not_total,
            "must_not_violations": must_not_violations,
            "must_not_unclear": must_not_unclear,
        },
        "by_skill": {
            skill: {
                **values,
                "must_pass_rate": rate(values["must_pass"], values["must"]),
            }
            for skill, values in sorted(by_skill.items())
        },
        "without_skill_baseline": {
            "must_total": baseline_must_total,
            "must_pass": baseline_must_pass,
            "must_pass_rate": rate(baseline_must_pass, baseline_must_total),
            "must_not_total": baseline_must_not_total,
            "must_not_violations": baseline_must_not_violations,
            "must_not_unclear": baseline_must_not_unclear,
        },
        "repeated_criterion_failures": repeated_criterion_failures,
        "failures": failures,
        "incomplete_runs": incomplete,
    }
    report["release_gate_failures"] = release_gate_failures(report)
    return report, errors


def release_gate_failures(report: dict[str, object]) -> list[str]:
    summary = report["summary"]
    by_skill = report["by_skill"]
    repeated = report["repeated_criterion_failures"]
    baseline = report["without_skill_baseline"]
    incomplete = report["incomplete_runs"]
    assert isinstance(summary, dict) and isinstance(by_skill, dict) and isinstance(repeated, list)
    assert isinstance(baseline, dict) and isinstance(incomplete, list)
    failures: list[str] = []
    if incomplete:
        failures.append("behavior case or repeated-run coverage is incomplete")
    if not baseline["must_total"]:
        failures.append("without-skill baseline coverage is missing")
    if summary["must_pass_rate"] < MIN_MUST_PASS_RATE:
        failures.append("with-skill must pass rate is below 95%")
    if summary["must_not_violations"]:
        failures.append("with-skill must_not violations are non-zero")
    if summary["must_not_unclear"]:
        failures.append("with-skill must_not grades contain unresolved unclear results")
    for skill, values in by_skill.items():
        assert isinstance(values, dict)
        if values["must_pass_rate"] < MIN_SKILL_MUST_PASS_RATE:
            failures.append(f"{skill} must pass rate is below 90%")
        if values["violations"] or values["unclear"]:
            failures.append(f"{skill} has unresolved must_not results")
    if repeated:
        failures.append("must criteria failed in a majority of repeated runs")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Score blinded Spring skill behavior-evaluation manifests.")
    parser.add_argument("results", type=Path)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--with-skill-runs", type=int, default=3)
    parser.add_argument("--without-skill-runs", type=int, default=1)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--require-artifact-binding", action="store_true")
    parser.add_argument("--expected-skill-commit")
    parser.add_argument("--json-report", type=Path)
    args = parser.parse_args()
    if args.strict and args.allow_partial:
        parser.error("--strict cannot be combined with --allow-partial")
    if args.strict and (args.with_skill_runs < 3 or args.without_skill_runs < 1):
        parser.error("--strict requires at least three with-skill runs and one baseline run")
    if args.require_artifact_binding and args.artifact_root is None:
        parser.error("--require-artifact-binding requires --artifact-root")
    if args.require_artifact_binding and args.expected_skill_commit is None:
        parser.error("--require-artifact-binding requires --expected-skill-commit")
    if args.expected_skill_commit is not None and (
        COMMIT.fullmatch(args.expected_skill_commit) is None
    ):
        parser.error("--expected-skill-commit must be a lowercase 40-character commit")
    try:
        cases = load_cases(args.cases)
        if args.strict:
            require_canonical_cases(cases, load_cases(DEFAULT_CASES))
        report, errors = score_results(
            cases,
            load_results(args.results),
            expected_with_skill_runs=args.with_skill_runs,
            expected_without_skill_runs=args.without_skill_runs,
            require_complete=not args.allow_partial,
            artifact_root=args.artifact_root,
            require_artifact_binding=args.require_artifact_binding,
            expected_skill_commit=args.expected_skill_commit,
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2
    if args.json_report is not None:
        args.json_report.parent.mkdir(parents=True, exist_ok=True)
        args.json_report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = report["summary"]
    print(
        f"Behavior eval: must_pass_rate={summary['must_pass_rate']:.3f}, "
        f"must_not_violations={summary['must_not_violations']}"
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
