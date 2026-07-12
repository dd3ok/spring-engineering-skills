from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any


PRECEDENCE = {"resolved": 4, "effective": 3, "declared": 2, "inferred": 1}
FACT_FIELDS = {"id", "project_id", "kind", "name", "value", "certainty", "source", "declaration_role", "scope", "catalog_source"}
SIGNAL_KINDS = {"config.key", "code.signal", "test.signal", "deployment.signal"}
SENSITIVE_VALUE = re.compile(r"(?i)(secret|password|passwd|credential|private[_-]?key|access[_-]?token|api[_-]?key)")
VERSION = re.compile(r"^\d{1,4}\.\d{1,4}\.\d{1,4}(?:-(?:SNAPSHOT|M\d{1,4}|RC\d{1,4}))?$", re.IGNORECASE)
PRERELEASE = re.compile(r"-(?:SNAPSHOT|M\d+|RC\d+)$", re.IGNORECASE)
MIN_PYTHON = (3, 12)


def require_supported_python(version=None) -> None:
    actual = version or sys.version_info
    if tuple(actual[:2]) < MIN_PYTHON:
        raise RuntimeError("Python 3.12 or newer is required for upgrade planning")


require_supported_python()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_fact_id(fact: dict[str, Any]) -> str:
    payload = {key: value for key, value in fact.items() if key != "id"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "fact:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def valid_relative_path(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value or re.match(r"^[A-Za-z]:", value):
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and path.as_posix() == value


def valid_project_path(value: object) -> bool:
    return value == "." or valid_relative_path(value)


def validate_evidence_input(evidence: object) -> list[str]:
    if not isinstance(evidence, dict):
        return ["evidence must be an object"]
    errors: list[str] = []
    required = {"schema_version", "repository", "collection", "projects", "facts", "conflicts", "gaps", "redaction"}
    if required - set(evidence):
        errors.append("evidence is missing required spring-evidence/1 fields")
    allowed = required | {"excluded", "deployment_paths"}
    if set(evidence) - allowed:
        errors.append("evidence contains unknown top-level fields")
    if evidence.get("schema_version") != "spring-evidence/1":
        errors.append("evidence schema_version must be spring-evidence/1")
    repository = evidence.get("repository")
    if not isinstance(repository, dict) or repository != {"root": "."}:
        errors.append("evidence repository contract is invalid")
    collection = evidence.get("collection")
    if not isinstance(collection, dict) or collection.get("mode") not in {"static", "imported-resolved"}:
        errors.append("evidence collection mode is invalid")
    else:
        if set(collection) != {"collector_version", "mode", "network_used", "build_executed"}:
            errors.append("evidence collection contains unknown fields")
        if not isinstance(collection.get("collector_version"), str) or not collection["collector_version"]:
            errors.append("evidence collector_version is missing")
        if (
            not isinstance(collection.get("network_used"), bool)
            or not isinstance(collection.get("build_executed"), bool)
            or (collection.get("mode") == "static" and (collection["network_used"] or collection["build_executed"]))
        ):
            errors.append("evidence collection execution flags are invalid")
    redaction = evidence.get("redaction")
    if not isinstance(redaction, dict) or redaction != {"configuration_values_omitted": True, "environment_read": False}:
        errors.append("evidence redaction contract is invalid")
    projects = evidence.get("projects")
    project_ids = {"project:."}
    if not isinstance(projects, list):
        errors.append("evidence projects must be an array")
    else:
        for index, project in enumerate(projects):
            if not isinstance(project, dict) or set(project) != {"id", "path", "build_system", "descriptor", "module_ids"}:
                errors.append(f"evidence project {index} is invalid")
                continue
            project_id = project.get("id")
            if not isinstance(project_id, str) or not project_id.startswith("project:"):
                errors.append(f"evidence project {index} has an invalid id")
            else:
                project_ids.add(project_id)
            if not valid_project_path(project.get("path")) or not valid_relative_path(project.get("descriptor")):
                errors.append(f"evidence project {index} has an unsafe path")
            modules = project.get("module_ids")
            if project.get("build_system") not in {"maven", "gradle"} or not isinstance(modules, list) or not all(
                isinstance(item, str) and item.startswith("project:") and valid_project_path(item.removeprefix("project:")) for item in modules
            ):
                errors.append(f"evidence project {index} has invalid build metadata")
    facts = evidence.get("facts")
    if not isinstance(facts, list):
        errors.append("evidence facts must be an array")
        return errors
    ids: set[str] = set()
    for index, fact in enumerate(facts):
        if not isinstance(fact, dict) or set(fact) - FACT_FIELDS or {"id", "project_id", "kind", "name", "value", "certainty", "source"} - set(fact):
            errors.append(f"evidence fact {index} has invalid fields")
            continue
        if fact.get("id") != expected_fact_id(fact) or fact.get("id") in ids:
            errors.append(f"evidence fact {index} has an invalid or duplicate id")
            continue
        ids.add(str(fact["id"]))
        source = fact.get("source")
        if not isinstance(source, dict) or set(source) - {"type", "path", "line"} or source.get("type") != "file" or not valid_relative_path(source.get("path")):
            errors.append(f"evidence fact {index} has an unsafe source path")
        elif "line" in source and (type(source["line"]) is not int or source["line"] < 1):
            errors.append(f"evidence fact {index} has an invalid source line")
        if fact.get("project_id") not in project_ids or fact.get("certainty") not in PRECEDENCE:
            errors.append(f"evidence fact {index} has invalid project or certainty")
        if not all(isinstance(fact.get(field), str) and fact.get(field) for field in ("kind", "name", "value")):
            errors.append(f"evidence fact {index} has invalid string fields")
        if fact.get("kind") in SIGNAL_KINDS and fact.get("value") != "present":
            errors.append(f"evidence fact {index} exposes a signal value")
        for field in ("value", "declaration_role", "scope", "catalog_source"):
            value = fact.get(field)
            if value is not None and (not isinstance(value, str) or not value or SENSITIVE_VALUE.search(value)):
                errors.append(f"evidence fact {index} has invalid {field}")
        if "catalog_source" in fact and not valid_relative_path(fact["catalog_source"]):
            errors.append(f"evidence fact {index} has unsafe catalog_source")
    expected_order = sorted(
        [fact for fact in facts if isinstance(fact, dict)],
        key=lambda item: (
            str(item.get("kind", "")), str(item.get("name", "")),
            str(item.get("source", {}).get("path", "")) if isinstance(item.get("source"), dict) else "",
            item.get("source", {}).get("line", 0) if isinstance(item.get("source"), dict) and type(item.get("source", {}).get("line", 0)) is int else -1,
            str(item.get("value", "")), str(item.get("id", "")),
        ),
    )
    if facts != expected_order:
        errors.append("evidence facts are not in canonical order")
    conflicts = evidence.get("conflicts")
    if not isinstance(conflicts, list) or any(
        not isinstance(item, dict)
        or set(item) != {"project_id", "kind", "name", "values", "fact_ids"}
        or not isinstance(item.get("fact_ids"), list)
        or not all(isinstance(value, str) for value in item.get("fact_ids", []))
        or not all(isinstance(item.get(field), str) and item[field] for field in ("project_id", "kind", "name"))
        or not isinstance(item.get("values"), list)
        or not all(isinstance(value, str) for value in item.get("values", []))
        or set(item["fact_ids"]) - ids
        for item in conflicts or []
    ):
        errors.append("evidence conflicts are invalid")
    gaps = evidence.get("gaps")
    if not isinstance(gaps, list) or any(
        not isinstance(item, dict) or set(item) != {"kind", "path"} or not isinstance(item.get("kind"), str) or not valid_project_path(item.get("path"))
        for item in gaps or []
    ):
        errors.append("evidence gaps are invalid")
    excluded = evidence.get("excluded", [])
    if not isinstance(excluded, list) or any(
        not isinstance(item, dict) or set(item) != {"path", "reason"} or not valid_relative_path(item.get("path")) or not isinstance(item.get("reason"), str)
        for item in excluded
    ):
        errors.append("evidence excluded entries are invalid")
    deployment_paths = evidence.get("deployment_paths", [])
    if not isinstance(deployment_paths, list) or not all(valid_relative_path(item) for item in deployment_paths):
        errors.append("evidence deployment_paths are invalid")
    return errors


def current_boot(evidence: dict[str, Any]) -> tuple[str | None, list[str], str | None]:
    candidates = [
        fact for fact in evidence.get("facts", [])
        if isinstance(fact, dict)
        and fact.get("kind") == "platform.version"
        and fact.get("name") in {"spring-boot", "spring-boot.version"}
        and fact.get("certainty") in PRECEDENCE
        and isinstance(fact.get("value"), str)
        and VERSION.fullmatch(fact["value"])
    ]
    if not candidates:
        return None, [], "a concrete Spring Boot version was not found in evidence"
    rank = max(PRECEDENCE[str(item["certainty"])] for item in candidates)
    strongest = [item for item in candidates if PRECEDENCE[str(item["certainty"])] == rank]
    values = sorted({str(item["value"]) for item in strongest})
    ids = sorted(str(item["id"]) for item in strongest)
    if len(values) != 1:
        return None, ids, "conflicting strongest Spring Boot version facts: " + ", ".join(values)
    return values[0], ids, None


def current_cloud(evidence: dict[str, Any]) -> tuple[str | None, list[str], str]:
    candidates = [
        fact for fact in evidence.get("facts", [])
        if isinstance(fact, dict)
        and fact.get("kind") == "platform.version"
        and fact.get("name") in {"spring-cloud", "spring-cloud.version"}
        and fact.get("certainty") in PRECEDENCE
        and isinstance(fact.get("value"), str)
        and VERSION.fullmatch(fact["value"])
    ]
    if not candidates:
        return None, [], "unknown"
    rank = max(PRECEDENCE[str(item["certainty"])] for item in candidates)
    strongest = [item for item in candidates if PRECEDENCE[str(item["certainty"])] == rank]
    values = sorted({str(item["value"]) for item in strongest})
    ids = sorted(str(item["id"]) for item in strongest)
    if len(values) != 1:
        return None, ids, "unknown"
    return values[0], ids, "used"


def version_tuple(value: str) -> tuple[int, int, int]:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", value)
    if not match:
        raise ValueError(f"invalid exact version: {value}")
    return tuple(int(item) for item in match.groups())


def version_key(value: str) -> tuple[int, int, int, int, int]:
    base = version_tuple(value)
    suffix = value.split("-", 1)[1].upper() if "-" in value else ""
    if not suffix:
        return (*base, 4, 0)
    if suffix.startswith("RC"):
        return (*base, 3, int(suffix[2:] or 0))
    if suffix.startswith("M"):
        return (*base, 2, int(suffix[1:] or 0))
    return (*base, 1, 0)


def bridge_points(current: str | None, target: str) -> list[str]:
    if current is None:
        return []
    current_version = version_tuple(current)
    target_version = version_tuple(target)
    bridges: list[str] = []
    if current_version[0] < 3 <= target_version[0]:
        if not (current_version[0] == 2 and current_version[1] == 7):
            bridges.append("latest-2.7.x-from-pinned-source")
        if target_version[0] > 3 or target_version[1] > 0:
            bridges.append("latest-3.0.x-from-pinned-source")
    if current_version[0] < 4 <= target_version[0]:
        if not (current_version[0] == 3 and current_version[1] == 5):
            bridges.append("latest-3.5.x-from-pinned-source")
        if target_version[0] > 4 or target_version[1] > 0:
            bridges.append("latest-4.0.x-from-pinned-source")
    return bridges


def build(
    evidence_path: Path,
    target: str,
    allow_prerelease: bool,
    source_ids: list[str],
    allow_downgrade: bool = False,
    target_spring_cloud: str | None = None,
    no_spring_cloud: bool = False,
    target_java: str | None = None,
    target_maven: str | None = None,
    target_gradle: str | None = None,
) -> dict[str, Any]:
    if any(not isinstance(value, str) or not value.strip() or not value.startswith("source:") for value in source_ids):
        raise ValueError("source ids must be non-empty and start with source:")
    if not VERSION.fullmatch(target):
        raise ValueError("target must be an exact Spring Boot version such as 4.1.0 or 4.1.0-RC1")
    if target_spring_cloud is not None and not VERSION.fullmatch(target_spring_cloud):
        raise ValueError("target Spring Cloud must be an exact service release such as 2025.1.2")
    if target_spring_cloud is not None and no_spring_cloud:
        raise ValueError("target Spring Cloud version and --no-spring-cloud are mutually exclusive")
    if target_java is not None and re.fullmatch(r"\d{1,4}(?:\.\d{1,4}){0,2}", target_java) is None:
        raise ValueError("target Java must be an exact feature or update version such as 25 or 25.0.1")
    selected_build_tools = [("maven", target_maven), ("gradle", target_gradle)]
    selected_build_tools = [(name, version) for name, version in selected_build_tools if version is not None]
    if len(selected_build_tools) > 1:
        raise ValueError("target Maven and Gradle versions are mutually exclusive")
    if selected_build_tools and not VERSION.fullmatch(str(selected_build_tools[0][1])):
        raise ValueError("target build-tool version must be exact")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence_errors = validate_evidence_input(evidence)
    if evidence_errors:
        raise ValueError("invalid evidence: " + "; ".join(evidence_errors))
    current, evidence_ids, blocker = current_boot(evidence)
    cloud, cloud_evidence_ids, cloud_usage = current_cloud(evidence)
    if current and version_key(target) < version_key(current) and not allow_downgrade:
        raise ValueError("target is lower than the observed current version; use --allow-downgrade explicitly")
    unresolved: list[str] = []
    if blocker:
        unresolved.append(blocker)
    if PRERELEASE.search(target) and not allow_prerelease:
        unresolved.append("prerelease target requires --allow-prerelease")
    if cloud_usage == "unknown":
        unresolved.append("confirm current Spring Cloud non-use or resolve the exact current service release")
    target_cloud_usage = "used" if target_spring_cloud else "not-used" if no_spring_cloud else "unknown"
    if target_cloud_usage == "unknown":
        unresolved.append("select an exact target Spring Cloud service release or confirm target non-use")
    if target_java is None:
        unresolved.append("select an exact target Java version")
    if not selected_build_tools:
        unresolved.append("select the target Maven or Gradle version")
    target_build_tool = selected_build_tools[0][0] if selected_build_tools else None
    target_build_tool_version = selected_build_tools[0][1] if selected_build_tools else None
    unresolved.append("attach pinned-source-copy evidence with a controlled capture manifest and SHA-256")
    bridges = bridge_points(current, target)
    if bridges:
        unresolved.append("resolve required major-upgrade bridge versions from pinned official migration sources")
    status = "blocked" if blocker or (PRERELEASE.search(target) and not allow_prerelease) else "draft"
    gates: list[dict[str, Any]] = [
        {"id": "gate:target-support", "status": "unknown", "rationale": "Confirm target support policy.", "evidence_ids": evidence_ids, "source_ids": sorted(source_ids)},
        {"id": "gate:java-build-tools", "status": "unknown", "rationale": "Confirm target system requirements.", "evidence_ids": [], "source_ids": sorted(source_ids)},
        {"id": "gate:spring-cloud", "status": "unknown", "rationale": "Confirm compatibility or document non-use.", "evidence_ids": [], "source_ids": sorted(source_ids)},
    ]
    if bridges:
        gates.append({"id": "gate:major-bridge", "status": "unknown", "rationale": "Resolve official latest-patch bridge releases.", "evidence_ids": evidence_ids, "source_ids": sorted(source_ids)})
    points = [current or "unknown", *bridges, target]
    hops = [
        {
            "id": f"hop:{index + 1}", "from": source, "to": destination,
            "rationale": "Confirm this transition against every skipped release note and migration guide.",
            "source_ids": sorted(source_ids), "changes": [], "verification": [], "rollback": [],
        }
        for index, (source, destination) in enumerate(zip(points, points[1:]))
    ]
    return {
        "schema_version": "spring-upgrade-plan/2",
        "status": status,
        "input": {"evidence_sha256": sha256(evidence_path), "target": target, "source_snapshot_ids": sorted(source_ids)},
        "current": {
            "spring_boot": current, "spring_cloud": cloud, "spring_cloud_usage": cloud_usage,
            "evidence_ids": evidence_ids, "spring_cloud_evidence_ids": cloud_evidence_ids,
        },
        "target": {
            "spring_boot": target, "spring_cloud": target_spring_cloud,
            "spring_cloud_usage": target_cloud_usage, "java": target_java,
            "build_tool": target_build_tool, "build_tool_version": target_build_tool_version,
            "prerelease_allowed": allow_prerelease,
        },
        "policy": {"allow_downgrade": allow_downgrade},
        "compatibility_gates": gates,
        "hops": hops,
        "automation": [],
        "rollout": {"canary_signals": [], "rollback_trigger": None},
        "unresolved": sorted(unresolved),
        "source_ledger": [
            {
                "id": value, "kind": "unverified-reference", "locator": None, "publisher": None,
                "checked_version": target, "checked_spring_cloud": None, "scope": None,
                "subject": None, "subject_version": None, "applies_from": None, "applies_to": None,
                "snapshot_path": None, "sha256": None,
                "capture": None,
            }
            for value in sorted(set(source_ids))
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a deterministic Spring upgrade-plan draft.")
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--target", required=True, help="Exact target version; latest is intentionally unsupported.")
    parser.add_argument("--allow-prerelease", action="store_true")
    parser.add_argument("--allow-downgrade", action="store_true")
    cloud_group = parser.add_mutually_exclusive_group()
    cloud_group.add_argument("--target-spring-cloud", help="Exact target Spring Cloud service release.")
    cloud_group.add_argument("--no-spring-cloud", action="store_true", help="Confirm Spring Cloud is not used in the target.")
    parser.add_argument("--target-java", help="Exact target Java feature or update version.")
    build_group = parser.add_mutually_exclusive_group()
    build_group.add_argument("--target-maven", help="Exact target Maven version.")
    build_group.add_argument("--target-gradle", help="Exact target Gradle version.")
    parser.add_argument("--source-id", action="append", default=[], help="Unverified source label for a draft; enrich the ledger before ready status.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        plan = build(
            args.evidence, args.target, args.allow_prerelease, args.source_id,
            args.allow_downgrade, args.target_spring_cloud, args.no_spring_cloud,
            args.target_java, args.target_maven, args.target_gradle,
        )
    except (ValueError, json.JSONDecodeError) as error:
        raise SystemExit(str(error)) from error
    rendered = json.dumps(plan, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
