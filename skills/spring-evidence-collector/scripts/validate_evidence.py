from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any


CERTAINTY = {"resolved", "effective", "declared", "inferred"}
SIGNAL_KINDS = {"config.key", "code.signal", "test.signal", "deployment.signal"}
TOP_LEVEL_FIELDS = {"schema_version", "repository", "collection", "projects", "facts", "conflicts", "gaps", "redaction", "excluded", "deployment_paths"}
FACT_FIELDS = {"id", "project_id", "kind", "name", "value", "certainty", "source", "declaration_role", "scope", "catalog_source"}
SENSITIVE_VALUE = re.compile(r"(?i)(secret|password|passwd|credential|private[_-]?key|access[_-]?token|api[_-]?key)")
MIN_PYTHON = (3, 12)


def require_supported_python(version=None) -> None:
    actual = version or sys.version_info
    if tuple(actual[:2]) < MIN_PYTHON:
        raise RuntimeError("Python 3.12 or newer is required for evidence validation")


require_supported_python()


def canonical_relative_path(value: object, *, allow_dot: bool = False) -> bool:
    if not isinstance(value, str) or not value or "\\" in value or re.match(r"^[A-Za-z]:", value):
        return False
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        return False
    normalized = path.as_posix()
    return normalized == value and (allow_dot or value != ".")


def expected_fact_id(fact: dict[str, Any]) -> str:
    payload = {key: value for key, value in fact.items() if key != "id"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "fact:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate(data: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["evidence must be a JSON object"]
    required = {"schema_version", "repository", "collection", "projects", "facts", "conflicts", "gaps", "redaction"}
    missing = required - set(data)
    if missing:
        errors.append("missing required fields: " + ", ".join(sorted(missing)))
    unknown = set(data) - TOP_LEVEL_FIELDS
    if unknown:
        errors.append("unknown top-level fields: " + ", ".join(sorted(unknown)))
    if data.get("schema_version") != "spring-evidence/1":
        errors.append("unsupported schema_version")
    repository = data.get("repository")
    if not isinstance(repository, dict) or repository.get("root") != ".":
        errors.append("repository.root must be '.'")
    elif set(repository) != {"root"}:
        errors.append("repository contains unknown fields")
    collection = data.get("collection")
    if not isinstance(collection, dict) or collection.get("mode") not in {"static", "imported-resolved"}:
        errors.append("invalid collection mode")
    else:
        if set(collection) != {"collector_version", "mode", "network_used", "build_executed"}:
            errors.append("collection contains unknown fields")
        if not isinstance(collection.get("collector_version"), str) or not collection["collector_version"]:
            errors.append("collector_version is missing")
        if not isinstance(collection.get("network_used"), bool) or not isinstance(collection.get("build_executed"), bool):
            errors.append("collection execution flags must be booleans")
        elif collection.get("mode") == "static" and (collection["network_used"] or collection["build_executed"]):
            errors.append("static evidence cannot use network or execute a build")
    redaction = data.get("redaction")
    if not isinstance(redaction, dict) or redaction.get("configuration_values_omitted") is not True or redaction.get("environment_read") is not False:
        errors.append("redaction contract is missing")
    elif set(redaction) != {"configuration_values_omitted", "environment_read"}:
        errors.append("redaction contains unknown fields")

    projects = data.get("projects")
    project_ids = {"project:."}
    if not isinstance(projects, list):
        errors.append("projects must be an array")
    else:
        for index, project in enumerate(projects):
            if not isinstance(project, dict):
                errors.append(f"projects[{index}] must be an object")
                continue
            if set(project) != {"id", "path", "build_system", "descriptor", "module_ids"}:
                errors.append(f"projects[{index}] contains unknown fields")
            project_id = project.get("id")
            if not isinstance(project_id, str) or not project_id.startswith("project:"):
                errors.append(f"projects[{index}] has invalid id")
            else:
                project_ids.add(project_id)
            if not canonical_relative_path(project.get("path"), allow_dot=True):
                errors.append(f"projects[{index}] has invalid path")
            if not canonical_relative_path(project.get("descriptor")):
                errors.append(f"projects[{index}] has invalid descriptor")
            if project.get("build_system") not in {"maven", "gradle"} or not isinstance(project.get("module_ids"), list) or not all(isinstance(item, str) and item.startswith("project:") and canonical_relative_path(item.removeprefix("project:"), allow_dot=True) for item in project.get("module_ids", [])):
                errors.append(f"projects[{index}] has invalid build metadata")

    facts = data.get("facts")
    ids: set[str] = set()
    if not isinstance(facts, list):
        errors.append("facts must be an array")
        facts = []
    for index, fact in enumerate(facts):
        if not isinstance(fact, dict):
            errors.append(f"facts[{index}] must be an object")
            continue
        required_fact = {"id", "project_id", "kind", "name", "value", "certainty", "source"}
        if required_fact - set(fact):
            errors.append(f"facts[{index}] is missing required fields")
            continue
        if set(fact) - FACT_FIELDS:
            errors.append(f"facts[{index}] contains unknown fields")
        fact_id = fact.get("id")
        if not isinstance(fact_id, str) or fact_id in ids or fact_id != expected_fact_id(fact):
            errors.append(f"facts[{index}] has invalid, stale, or duplicate id")
        ids.add(str(fact_id))
        if fact.get("project_id") not in project_ids:
            errors.append(f"facts[{index}] references an unknown project")
        if fact.get("certainty") not in CERTAINTY:
            errors.append(f"facts[{index}] has invalid certainty")
        if not all(isinstance(fact.get(field), str) and fact.get(field) for field in ("kind", "name", "value")):
            errors.append(f"facts[{index}] has invalid string fields")
        source = fact.get("source")
        if not isinstance(source, dict) or source.get("type") != "file" or not canonical_relative_path(source.get("path")):
            errors.append(f"facts[{index}] must use a canonical relative source path")
        elif set(source) - {"type", "path", "line"}:
            errors.append(f"facts[{index}] source contains unknown fields")
        elif "line" in source and (type(source["line"]) is not int or source["line"] < 1):
            errors.append(f"facts[{index}] has an invalid source line")
        if fact.get("kind") in SIGNAL_KINDS and fact.get("value") != "present":
            errors.append(f"facts[{index}] exposes a value for a key/signal fact")
        if isinstance(fact.get("value"), str) and SENSITIVE_VALUE.search(fact["value"]):
            errors.append(f"facts[{index}] contains a secret-like value")
        for field in ("declaration_role", "scope"):
            if field in fact and (not isinstance(fact[field], str) or not fact[field] or SENSITIVE_VALUE.search(fact[field])):
                errors.append(f"facts[{index}] has invalid {field}")
        if "catalog_source" in fact and (
            not isinstance(fact["catalog_source"], str)
            or not canonical_relative_path(fact["catalog_source"])
            or SENSITIVE_VALUE.search(fact["catalog_source"])
        ):
            errors.append(f"facts[{index}] has invalid catalog_source")

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
        errors.append("facts are not in canonical order")

    conflicts = data.get("conflicts")
    if not isinstance(conflicts, list):
        errors.append("conflicts must be an array")
    else:
        for index, conflict in enumerate(conflicts):
            if not isinstance(conflict, dict) or not isinstance(conflict.get("fact_ids"), list):
                errors.append(f"conflicts[{index}] is invalid")
                continue
            if set(conflict) != {"project_id", "kind", "name", "values", "fact_ids"}:
                errors.append(f"conflicts[{index}] contains unknown fields")
            if not all(isinstance(conflict.get(field), str) and conflict[field] for field in ("project_id", "kind", "name")) or not isinstance(conflict.get("values"), list) or not all(isinstance(value, str) for value in conflict.get("values", [])):
                errors.append(f"conflicts[{index}] has invalid fields")
            if not all(isinstance(value, str) for value in conflict["fact_ids"]):
                errors.append(f"conflicts[{index}] has invalid fact ids")
                continue
            unknown = set(conflict["fact_ids"]) - ids
            if unknown:
                errors.append(f"conflicts[{index}] references unknown facts")
    gaps = data.get("gaps")
    if not isinstance(gaps, list):
        errors.append("gaps must be an array")
    else:
        for index, gap in enumerate(gaps):
            if not isinstance(gap, dict) or not isinstance(gap.get("kind"), str) or not canonical_relative_path(gap.get("path"), allow_dot=True):
                errors.append(f"gaps[{index}] is invalid")
            elif set(gap) != {"kind", "path"}:
                errors.append(f"gaps[{index}] contains unknown fields")
    excluded = data.get("excluded", [])
    if not isinstance(excluded, list) or not all(
        isinstance(item, dict) and set(item) == {"path", "reason"} and canonical_relative_path(item.get("path")) and isinstance(item.get("reason"), str)
        for item in excluded
    ):
        errors.append("excluded entries are invalid")
    deployment_paths = data.get("deployment_paths", [])
    if not isinstance(deployment_paths, list) or not all(canonical_relative_path(item) for item in deployment_paths):
        errors.append("deployment_paths are invalid")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate spring-evidence/1 JSON.")
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    data = json.loads(args.evidence.read_text(encoding="utf-8"))
    errors = validate(data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Evidence is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
