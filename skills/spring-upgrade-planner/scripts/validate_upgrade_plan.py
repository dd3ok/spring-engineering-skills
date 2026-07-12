from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from urllib.parse import SplitResult, urlsplit

from build_plan_skeleton import validate_evidence_input


STATUSES = {"ready", "draft", "blocked"}
GATE_STATUSES = {"pass", "fail", "unknown", "not-applicable"}
REQUIRED_GATES = {"gate:target-support", "gate:java-build-tools", "gate:spring-cloud"}
SOURCE_SCOPES = {
    "target-support", "system-requirements", "spring-cloud-compatibility", "migration-guide",
    "release-notes", "managed-dependencies", "rewrite-recipe", "java-migration",
    "maven-reference", "gradle-reference", "spring-upgrade-guide", "build-system-guide",
    "automation-guide", "java-support-policy", "spring-cloud-release-notes",
}
GATE_SCOPE = {
    "gate:target-support": "target-support",
    "gate:java-build-tools": "system-requirements",
    "gate:spring-cloud": "spring-cloud-compatibility",
    "gate:major-bridge": "migration-guide",
}
GATE_PUBLISHERS = {
    "gate:target-support": {"spring"},
    "gate:java-build-tools": {"spring"},
    "gate:spring-cloud": {"spring", "spring-github"},
    "gate:major-bridge": {"spring-github"},
}
PUBLISHER_HOSTS = {
    "spring": {"spring.io", "docs.spring.io"},
    "oracle": {"docs.oracle.com", "www.oracle.com"},
    "maven": {"maven.apache.org"},
    "gradle": {"docs.gradle.org"},
    "openrewrite": {"docs.openrewrite.org"},
    "spring-github": {"github.com"},
    "openjdk": {"openjdk.org"},
}
PUBLISHER_SCOPE_PATH_PATTERNS = {
    ("spring", "spring.io", "target-support"): (re.compile(r"^/support-policy/?$"),),
    ("spring", "spring.io", "spring-cloud-compatibility"): (re.compile(r"^/projects/spring-cloud/?$"),),
    ("spring", "docs.spring.io", "system-requirements"): (
        re.compile(r"^/spring-boot/(?:\d+\.\d+(?:\.\d+)?/)?system-requirements\.html$"),
    ),
    ("spring", "docs.spring.io", "managed-dependencies"): (
        re.compile(r"^/spring-boot/(?:\d+\.\d+(?:\.\d+)?/)?appendix/dependency-versions/coordinates\.html$"),
    ),
    ("spring-github", "github.com", "migration-guide"): (
        re.compile(r"^/spring-projects/spring-boot/wiki/Spring-Boot-\d+\.\d+-Migration-Guide$"),
    ),
    ("spring-github", "github.com", "release-notes"): (
        re.compile(r"^/spring-projects/spring-boot/wiki/Spring-Boot-\d+\.\d+-Release-Notes$"),
    ),
    ("spring-github", "github.com", "spring-cloud-compatibility"): (
        re.compile(r"^/spring-cloud/spring-cloud-release/wiki/Supported-Versions$"),
    ),
    ("spring-github", "github.com", "spring-cloud-release-notes"): (
        re.compile(r"^/spring-cloud/spring-cloud-release/wiki/Spring-Cloud-\d{4}\.\d+-Release-Notes$"),
    ),
    ("openrewrite", "docs.openrewrite.org", "rewrite-recipe"): (
        re.compile(r"^/recipes/java/spring(?:/.*)?$"),
    ),
    ("spring", "docs.spring.io", "spring-upgrade-guide"): (
        re.compile(r"^/spring-boot/(?:\d+\.\d+(?:\.\d+)?/)?upgrading\.html$"),
    ),
    ("spring", "docs.spring.io", "build-system-guide"): (
        re.compile(r"^/spring-boot/(?:\d+\.\d+(?:\.\d+)?/)?reference/using/build-systems\.html$"),
    ),
    ("oracle", "docs.oracle.com", "java-migration"): (
        re.compile(r"^/en/java/javase/\d+/migrate(?:/.*)?$"),
    ),
    ("oracle", "www.oracle.com", "java-support-policy"): (
        re.compile(r"^/java/technologies/java-se-support-roadmap\.html$"),
    ),
    ("openjdk", "openjdk.org", "java-migration"): (re.compile(r"^/projects/jdk/\d+/?$"),),
    ("maven", "maven.apache.org", "maven-reference"): (
        re.compile(r"^/docs/\d+\.\d+\.\d+/release-notes\.html$"),
    ),
    ("gradle", "docs.gradle.org", "gradle-reference"): (
        re.compile(r"^/\d+\.\d+\.\d+/release-notes\.html$"),
    ),
    ("openrewrite", "docs.openrewrite.org", "automation-guide"): (
        re.compile(r"^/reference/(?:rewrite-maven-plugin|gradle-plugin-configuration)$"),
    ),
}
VERSION = re.compile(r"^\d{1,4}\.\d{1,4}\.\d{1,4}(?:-(?:SNAPSHOT|M\d{1,4}|RC\d{1,4}))?$", re.IGNORECASE)
CLOUD_VERSION = re.compile(r"^\d{4}\.\d{1,4}\.\d{1,4}(?:\.\d{1,4})?(?:-(?:SNAPSHOT|M\d{1,4}|RC\d{1,4}))?$", re.IGNORECASE)
JAVA_VERSION = re.compile(r"^\d{1,4}(?:\.\d{1,4}){0,2}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
FACT_ID = re.compile(r"^fact:[a-f0-9]{64}$")
SOURCE_ID = re.compile(r"^source:.+$")
SOURCE_REQUIRED_FIELDS = {
    "id", "kind", "locator", "publisher", "checked_version", "scope",
    "checked_spring_cloud", "subject", "subject_version", "applies_from", "applies_to",
    "snapshot_path", "sha256", "capture",
}
CAPTURE_REQUIRED_FIELDS = {"method", "captured_at", "captured_by", "final_locator", "response_sha256"}
INPUT_FIELDS = {"evidence_sha256", "evidence_captured_at", "evidence_snapshot_path", "target", "source_snapshot_ids"}
CURRENT_FIELDS = {"spring_boot", "spring_cloud", "spring_cloud_usage", "evidence_ids", "spring_cloud_evidence_ids"}
TARGET_FIELDS = {"spring_boot", "spring_cloud", "spring_cloud_usage", "java", "build_tool", "build_tool_version", "prerelease_allowed"}
GATE_FIELDS = {"id", "status", "rationale", "evidence_ids", "source_ids"}
HOP_FIELDS = {"id", "from", "to", "rationale", "source_ids", "changes", "verification", "rollback"}
CAPTURED_AT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
MUTABLE_SOURCE_SCOPES = {
    "target-support", "system-requirements", "spring-cloud-compatibility",
    "managed-dependencies", "rewrite-recipe", "spring-upgrade-guide", "build-system-guide",
    "java-migration", "maven-reference", "gradle-reference",
    "migration-guide", "release-notes", "automation-guide",
    "java-support-policy", "spring-cloud-release-notes",
}
MAX_MUTABLE_CAPTURE_AGE = timedelta(days=180)
SCOPE_SUBJECT = {
    "target-support": "spring-boot",
    "system-requirements": "spring-boot",
    "spring-cloud-compatibility": "spring-cloud",
    "spring-cloud-release-notes": "spring-cloud",
    "migration-guide": "spring-boot",
    "release-notes": "spring-boot",
    "managed-dependencies": "spring-boot",
    "spring-upgrade-guide": "spring-boot",
    "build-system-guide": "spring-boot",
    "rewrite-recipe": "openrewrite",
    "java-migration": "java",
    "java-support-policy": "java",
    "maven-reference": "maven",
    "gradle-reference": "gradle",
    "automation-guide": "openrewrite",
}
MIN_PYTHON = (3, 12)
MAX_EVIDENCE_BYTES = 64 * 1024 * 1024
HASH_CHUNK_BYTES = 1024 * 1024


def require_supported_python(version=None) -> None:
    actual = version or sys.version_info
    if tuple(actual[:2]) < MIN_PYTHON:
        raise RuntimeError("Python 3.12 or newer is required for junction-safe upgrade validation")


require_supported_python()


def nonempty_items(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) and bool(item.strip()) for item in value
    )


def parse_locator(value: object) -> SplitResult | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return None
    if not (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and parsed.username is None
        and parsed.password is None
        and port in {None, 443}
        and not parsed.query
        and not parsed.fragment
    ):
        return None
    return parsed


def valid_locator(value: object) -> bool:
    return parse_locator(value) is not None


def approved_publisher_path(publisher: str, hostname: str, path: str, scope: object) -> bool:
    patterns = PUBLISHER_SCOPE_PATH_PATTERNS.get((publisher, hostname, str(scope)))
    if patterns is None:
        return False
    if "%" in path or "\\" in path or any(segment in {".", ".."} for segment in path.split("/")):
        return False
    return any(pattern.fullmatch(path) is not None for pattern in patterns)


def locator_matches_applicability(path: str, scope: object, applies_to: object) -> bool:
    if not isinstance(scope, str) or scope not in {"migration-guide", "release-notes"} or not isinstance(applies_to, str):
        return True
    match = re.fullmatch(
        r"/spring-projects/spring-boot/wiki/Spring-Boot-(\d+)\.(\d+)-(?:Migration-Guide|Release-Notes)",
        path,
    )
    if match is None:
        return False
    target_line = tuple(int(value) for value in applies_to.split("-", 1)[0].split(".")[:2])
    return (int(match.group(1)), int(match.group(2))) == target_line


def valid_captured_at(value: object) -> bool:
    if not isinstance(value, str) or CAPTURED_AT.fullmatch(value) is None:
        return False
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return False
    return True


def locator_matches_checked_boot_line(path: str, scope: object, checked_version: object) -> bool:
    if not isinstance(scope, str) or scope not in {"system-requirements", "managed-dependencies", "spring-upgrade-guide", "build-system-guide"}:
        return True
    if not isinstance(checked_version, str) or VERSION.fullmatch(checked_version) is None:
        return False
    match = re.match(r"^/spring-boot/(\d+)\.(\d+)(?:\.\d+)?/", path)
    if match is None:
        return False
    checked_line = tuple(int(value) for value in checked_version.split("-", 1)[0].split(".")[:2])
    return (int(match.group(1)), int(match.group(2))) == checked_line


def locator_matches_subject_version(path: str, subject: object, subject_version: object) -> bool:
    if not isinstance(subject, str) or not isinstance(subject_version, str):
        return False
    if subject == "java":
        match = re.search(r"/(?:javase|jdk)/(\d+)(?:/|$)", path)
        return match is not None and int(match.group(1)) == int(subject_version.split(".", 1)[0])
    if subject == "gradle":
        match = re.match(r"^/(\d+\.\d+\.\d+)/release-notes\.html$", path)
        return match is not None and subject_version == match.group(1)
    if subject == "maven":
        match = re.match(r"^/docs/(\d+\.\d+\.\d+)/release-notes\.html$", path)
        return match is not None and subject_version == match.group(1)
    return True


def locator_matches_cloud_train(path: str, scope: object, subject_version: object) -> bool:
    if scope != "spring-cloud-release-notes":
        return True
    if not isinstance(subject_version, str) or CLOUD_VERSION.fullmatch(subject_version) is None:
        return False
    match = re.fullmatch(
        r"/spring-cloud/spring-cloud-release/wiki/Spring-Cloud-(\d{4})\.(\d+)-Release-Notes",
        path,
    )
    if match is None:
        return False
    expected_train = subject_version.split("-", 1)[0].split(".")[:2]
    return [match.group(1), match.group(2)] == expected_train


def valid_capture(
    capture: object,
    locator: object,
    publisher: object,
    scope: object,
    sha256: object,
    *,
    now: datetime | None = None,
) -> bool:
    if not isinstance(capture, dict) or set(capture) != CAPTURE_REQUIRED_FIELDS:
        return False
    final_locator = capture.get("final_locator")
    if (
        capture.get("method") != "controlled-fetch"
        or not isinstance(capture.get("captured_by"), str)
        or not capture["captured_by"].strip()
        or not valid_captured_at(capture.get("captured_at"))
        or capture.get("response_sha256") != sha256
        or parse_locator(final_locator) is None
        or not isinstance(locator, str)
        or not isinstance(publisher, str)
    ):
        return False
    requested = parse_locator(locator)
    final = parse_locator(final_locator)
    if requested is None or final is None:
        return False
    captured_at = datetime.strptime(str(capture["captured_at"]), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    current_time = now or datetime.now(UTC)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=UTC)
    if captured_at > current_time:
        return False
    if isinstance(scope, str) and scope in MUTABLE_SOURCE_SCOPES and current_time - captured_at > MAX_MUTABLE_CAPTURE_AGE:
        return False
    return (
        final.hostname in PUBLISHER_HOSTS.get(publisher, set())
        and approved_publisher_path(publisher, str(final.hostname), final.path, scope)
        and requested.hostname in PUBLISHER_HOSTS.get(publisher, set())
        and approved_publisher_path(publisher, str(requested.hostname), requested.path, scope)
    )


def valid_snapshot_path(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value or re.match(r"^[A-Za-z]:", value):
        return False
    path = PurePosixPath(value)
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{index}" for index in range(1, 10)), *(f"LPT{index}" for index in range(1, 10))}
    return (
        not path.is_absolute()
        and ".." not in path.parts
        and path.as_posix() == value
        and all(
            part
            and part == part.rstrip(". ")
            and re.fullmatch(r"[A-Za-z0-9._-]+", part) is not None
            and part.split(".", 1)[0].upper() not in reserved
            for part in path.parts
        )
    )


def is_link_or_junction(path: Path) -> bool:
    try:
        return path.is_symlink() or bool(getattr(path, "is_junction", lambda: False)())
    except OSError:
        return True


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(HASH_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def load_evidence_snapshot(
    base_dir: Path | None,
    snapshot_path: object,
    expected_sha256: object,
    evidence_captured_at: object,
    *,
    now: datetime,
) -> tuple[dict[str, dict[str, object]], list[str]]:
    errors: list[str] = []
    if base_dir is None:
        return {}, ["ready evidence hash requires a plan base directory"]
    if not valid_snapshot_path(snapshot_path):
        return {}, ["ready plan lacks a safe evidence_snapshot_path"]
    base = base_dir.resolve()
    candidate = base / str(snapshot_path)
    snapshot = candidate.resolve()
    try:
        snapshot.relative_to(base)
    except ValueError:
        return {}, ["ready evidence snapshot escapes plan directory"]
    if is_link_or_junction(candidate) or not snapshot.is_file():
        return {}, ["ready evidence snapshot is missing or linked"]
    try:
        with snapshot.open("rb") as handle:
            payload = handle.read(MAX_EVIDENCE_BYTES + 1)
    except OSError:
        return {}, ["ready evidence snapshot cannot be read"]
    if len(payload) > MAX_EVIDENCE_BYTES:
        return {}, ["ready evidence snapshot exceeds the 64 MiB limit"]
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        errors.append("ready evidence snapshot hash mismatch")
    try:
        evidence = json.loads(payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return {}, [*errors, "ready evidence snapshot is not valid UTF-8 spring-evidence/1 JSON"]
    evidence_errors = validate_evidence_input(evidence)
    if evidence_errors:
        return {}, [*errors, *(f"ready evidence snapshot: {error}" for error in evidence_errors)]
    assert isinstance(evidence, dict) and isinstance(evidence.get("facts"), list)
    collection = evidence.get("collection")
    if isinstance(collection, dict) and collection.get("mode") == "imported-resolved":
        provenance = collection.get("provenance")
        collected_at_value = provenance.get("collected_at") if isinstance(provenance, dict) else None
        try:
            collected_at = datetime.strptime(str(collected_at_value), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
        except ValueError:
            errors.append("ready imported evidence has an invalid collection time")
        else:
            if now - collected_at > MAX_MUTABLE_CAPTURE_AGE:
                errors.append("ready imported evidence is older than 180 days")
            if valid_captured_at(evidence_captured_at):
                captured_at = datetime.strptime(str(evidence_captured_at), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
                if captured_at < collected_at:
                    errors.append("ready evidence capture predates imported report collection")
    fact_index = {
        str(fact["id"]): fact
        for fact in evidence["facts"]
        if isinstance(fact, dict) and isinstance(fact.get("id"), str)
    }
    return fact_index, errors


def evidence_ids(value: object) -> list[str] | None:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and FACT_ID.fullmatch(item) is not None for item in value
    ) or len(set(value)) != len(value):
        return None
    return value


def required_bridge_lines(current: str, target: str) -> set[tuple[int, int]]:
    current_parts = tuple(int(value) for value in current.split("-", 1)[0].split("."))
    target_parts = tuple(int(value) for value in target.split("-", 1)[0].split("."))
    required: set[tuple[int, int]] = set()
    if current_parts[0] < 3 <= target_parts[0]:
        required.update({(2, 7), (3, 0)})
    if current_parts[0] < 4 <= target_parts[0]:
        required.update({(3, 5), (4, 0)})
    return required


def version_key(value: str) -> tuple[int, int, int, int, int, int]:
    base_text, _, suffix = value.partition("-")
    base_parts = [int(item) for item in base_text.split(".")]
    base = tuple((base_parts + [0] * 4)[:4])
    suffix = suffix.upper()
    if not suffix:
        return (*base, 4, 0)
    if suffix.startswith("RC"):
        return (*base, 3, int(suffix[2:] or 0))
    if suffix.startswith("M"):
        return (*base, 2, int(suffix[1:] or 0))
    return (*base, 1, 0)


def validate(plan: object, base_dir: Path | None = None, *, now: datetime | None = None) -> list[str]:
    if not isinstance(plan, dict):
        return ["plan must be a JSON object"]
    errors: list[str] = []
    validation_time = now or datetime.now(UTC)
    if validation_time.tzinfo is None:
        validation_time = validation_time.replace(tzinfo=UTC)
    required = {"schema_version", "status", "input", "current", "target", "policy", "compatibility_gates", "hops", "automation", "rollout", "unresolved", "source_ledger"}
    missing = required - set(plan)
    if missing:
        errors.append("missing required fields: " + ", ".join(sorted(missing)))
    extra = set(plan) - required
    if extra:
        errors.append("unknown top-level fields: " + ", ".join(sorted(extra)))
    if plan.get("schema_version") != "spring-upgrade-plan/2":
        errors.append("unsupported schema_version")
    status = plan.get("status")
    if not isinstance(status, str) or status not in STATUSES:
        errors.append("invalid plan status")

    input_data = plan.get("input")
    input_source_ids = input_data.get("source_snapshot_ids", []) if isinstance(input_data, dict) else []
    input_source_ids_valid = (
        isinstance(input_source_ids, list)
        and all(isinstance(value, str) and SOURCE_ID.fullmatch(value) is not None for value in input_source_ids)
        and len(set(input_source_ids)) == len(input_source_ids)
    )
    evidence_snapshot_path = input_data.get("evidence_snapshot_path") if isinstance(input_data, dict) else None
    evidence_captured_at = input_data.get("evidence_captured_at") if isinstance(input_data, dict) else None
    if (
        not isinstance(input_data, dict)
        or set(input_data) != INPUT_FIELDS
        or not input_source_ids_valid
        or not SHA256.fullmatch(str(input_data.get("evidence_sha256", "")))
        or (evidence_captured_at is not None and not valid_captured_at(evidence_captured_at))
        or (evidence_snapshot_path is not None and not valid_snapshot_path(evidence_snapshot_path))
    ):
        errors.append("input evidence hash, evidence_snapshot_path, or source_snapshot_ids are invalid")
    current = plan.get("current")
    target = plan.get("target")
    current_evidence_ids = evidence_ids(current.get("evidence_ids")) if isinstance(current, dict) else None
    if (
        not isinstance(current, dict)
        or set(current) != CURRENT_FIELDS
        or "spring_boot" not in current
        or current_evidence_ids is None
    ):
        errors.append("current state is invalid")
    current_version = current.get("spring_boot") if isinstance(current, dict) else None
    current_cloud = current.get("spring_cloud") if isinstance(current, dict) else None
    current_cloud_usage = current.get("spring_cloud_usage") if isinstance(current, dict) else None
    if isinstance(current, dict) and (
        "spring_cloud" not in current
        or not isinstance(current_cloud_usage, str)
        or current_cloud_usage not in {"used", "not-used", "unknown"}
        or evidence_ids(current.get("spring_cloud_evidence_ids")) is None
        or (current_cloud is not None and (not isinstance(current_cloud, str) or not CLOUD_VERSION.fullmatch(current_cloud)))
        or (current_cloud_usage == "used" and current_cloud is None)
        or (current_cloud_usage != "used" and current_cloud is not None)
    ):
        errors.append("current Spring Cloud usage/version evidence is invalid")
    if status == "ready" and current_cloud_usage == "unknown":
        errors.append("ready plan must resolve current Spring Cloud use or non-use")
    if (
        status == "ready"
        and isinstance(current_cloud_usage, str)
        and current_cloud_usage in {"used", "not-used"}
        and not nonempty_items(current.get("spring_cloud_evidence_ids") if isinstance(current, dict) else None)
    ):
        errors.append("resolved current Spring Cloud use/non-use requires evidence IDs")
    if status == "ready" and (not isinstance(current_version, str) or not VERSION.fullmatch(current_version)):
        errors.append("ready plan requires an exact current Spring Boot version")
    evidence_fact_index: dict[str, dict[str, object]] = {}
    if status == "ready":
        if not valid_captured_at(evidence_captured_at):
            errors.append("ready plan requires evidence_captured_at")
        else:
            captured_at = datetime.strptime(str(evidence_captured_at), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
            if captured_at > validation_time or validation_time - captured_at > MAX_MUTABLE_CAPTURE_AGE:
                errors.append("ready evidence capture is future-dated or older than 180 days")
        evidence_fact_index, evidence_errors = load_evidence_snapshot(
            base_dir,
            evidence_snapshot_path,
            input_data.get("evidence_sha256") if isinstance(input_data, dict) else None,
            evidence_captured_at,
            now=validation_time,
        )
        errors.extend(evidence_errors)
        if not current_evidence_ids:
            errors.append("ready current Spring Boot version requires evidence IDs")
        else:
            unknown = set(current_evidence_ids) - set(evidence_fact_index)
            if unknown:
                errors.append("current Spring Boot evidence IDs are absent from the evidence snapshot")
            elif not all(
                evidence_fact_index[item].get("kind") == "platform.version"
                and evidence_fact_index[item].get("name") in {"spring-boot", "spring-boot.version"}
                and evidence_fact_index[item].get("value") == current_version
                for item in current_evidence_ids
            ):
                errors.append("current Spring Boot evidence IDs do not bind the selected version")
        cloud_ids = evidence_ids(current.get("spring_cloud_evidence_ids")) if isinstance(current, dict) else None
        if cloud_ids:
            unknown = set(cloud_ids) - set(evidence_fact_index)
            if unknown:
                errors.append("current Spring Cloud evidence IDs are absent from the evidence snapshot")
            elif current_cloud_usage == "used" and not all(
                evidence_fact_index[item].get("kind") == "platform.version"
                and evidence_fact_index[item].get("name") in {"spring-cloud", "spring-cloud.version"}
                and evidence_fact_index[item].get("value") == current_cloud
                for item in cloud_ids
            ):
                errors.append("current Spring Cloud evidence IDs do not bind the selected version")
            elif current_cloud_usage == "not-used" and not all(
                evidence_fact_index[item].get("kind") == "platform.usage"
                and evidence_fact_index[item].get("name") == "spring-cloud"
                and evidence_fact_index[item].get("value") == "not-used"
                and evidence_fact_index[item].get("certainty") in {"effective", "resolved"}
                for item in cloud_ids
            ):
                errors.append("current Spring Cloud evidence IDs do not prove confirmed non-use")
    target_version = target.get("spring_boot") if isinstance(target, dict) else None
    target_cloud = target.get("spring_cloud") if isinstance(target, dict) else None
    target_cloud_usage = target.get("spring_cloud_usage") if isinstance(target, dict) else None
    target_java = target.get("java") if isinstance(target, dict) else None
    target_build_tool = target.get("build_tool") if isinstance(target, dict) else None
    target_build_tool_version = target.get("build_tool_version") if isinstance(target, dict) else None
    if not isinstance(target, dict) or set(target) != TARGET_FIELDS or not isinstance(target.get("prerelease_allowed"), bool) or not isinstance(target_version, str) or not VERSION.fullmatch(target_version):
        errors.append("target must contain an exact Spring Boot version")
    if isinstance(target_version, str) and isinstance(input_data, dict) and input_data.get("target") != target_version:
        errors.append("input.target does not match target.spring_boot")
    if (
        status != "blocked"
        and isinstance(target_version, str)
        and re.search(r"-(?:SNAPSHOT|M\d+|RC\d+)$", target_version, re.IGNORECASE)
        and isinstance(target, dict)
        and target.get("prerelease_allowed") is False
    ):
        errors.append("prerelease target requires prerelease_allowed")
    if isinstance(target, dict) and (
        "spring_cloud" not in target
        or not isinstance(target_cloud_usage, str)
        or target_cloud_usage not in {"used", "not-used", "unknown"}
        or (target_cloud is not None and (not isinstance(target_cloud, str) or not CLOUD_VERSION.fullmatch(target_cloud)))
        or (target_cloud_usage == "used" and target_cloud is None)
        or (target_cloud_usage != "used" and target_cloud is not None)
    ):
        errors.append("target Spring Cloud usage/service release is invalid")
    if status == "ready" and target_cloud_usage == "unknown":
        errors.append("ready plan must select target Spring Cloud or confirm non-use")
    if isinstance(target, dict) and (
        "java" not in target
        or "build_tool" not in target
        or "build_tool_version" not in target
        or (target_java is not None and (not isinstance(target_java, str) or JAVA_VERSION.fullmatch(target_java) is None))
        or not (target_build_tool is None or (isinstance(target_build_tool, str) and target_build_tool in {"maven", "gradle"}))
        or (target_build_tool_version is not None and (not isinstance(target_build_tool_version, str) or VERSION.fullmatch(target_build_tool_version) is None))
        or ((target_build_tool is None) != (target_build_tool_version is None))
    ):
        errors.append("target Java/build-tool selection is invalid")
    if status == "ready" and (target_java is None or target_build_tool is None or target_build_tool_version is None):
        errors.append("ready plan requires exact target Java and build-tool versions")
    if (
        status == "ready"
        and isinstance(target_version, str)
        and target_version.startswith("4.1.")
        and isinstance(target_cloud, str)
    ):
        if not target_cloud.startswith("2025.1.") or version_key(target_cloud) < version_key("2025.1.2"):
            errors.append("Spring Boot 4.1 requires Spring Cloud 2025.1.2 or newer within the 2025.1 train")
    policy = plan.get("policy")
    if not isinstance(policy, dict) or set(policy) != {"allow_downgrade"} or not isinstance(policy.get("allow_downgrade"), bool):
        errors.append("policy.allow_downgrade must be a boolean")
    elif isinstance(current_version, str) and VERSION.fullmatch(current_version) and isinstance(target_version, str) and VERSION.fullmatch(target_version) and version_key(target_version) < version_key(current_version) and not policy["allow_downgrade"]:
        errors.append("target is a downgrade without policy opt-in")

    ledger = plan.get("source_ledger")
    source_ids: set[str] = set()
    source_scopes: dict[str, str] = {}
    source_publishers: dict[str, str] = {}
    source_subject_versions: dict[str, tuple[str, str]] = {}
    source_applicability: dict[str, tuple[str, str]] = {}
    source_locators: set[str] = set()
    source_artifacts: set[tuple[object, object]] = set()
    if not isinstance(ledger, list):
        errors.append("source_ledger must be an array")
        ledger = []
    for index, source in enumerate(ledger):
        if not isinstance(source, dict) or SOURCE_REQUIRED_FIELDS - set(source):
            errors.append(f"source_ledger[{index}] is missing required schema fields")
            continue
        if not isinstance(source, dict) or set(source) != SOURCE_REQUIRED_FIELDS or not isinstance(source.get("id"), str) or SOURCE_ID.fullmatch(source["id"]) is None or source["id"] in source_ids:
            errors.append(f"source_ledger[{index}] has an invalid or duplicate id")
            continue
        source_ids.add(source["id"])
        if status == "ready":
            raw_locator = source.get("locator")
            raw_parsed = parse_locator(raw_locator)
            locator_key = raw_parsed.geturl() if raw_parsed is not None else raw_locator
            artifact_key = (str(source.get("publisher")), str(source.get("sha256")))
            if isinstance(locator_key, str) and locator_key in source_locators:
                errors.append(f"ready source locator is duplicated: {source['id']}")
            if artifact_key in source_artifacts:
                errors.append(f"ready source snapshot identity is duplicated: {source['id']}")
            if isinstance(locator_key, str):
                source_locators.add(locator_key)
            source_artifacts.add(artifact_key)
        scope = source.get("scope")
        if scope is not None and (not isinstance(scope, str) or scope not in SOURCE_SCOPES):
            errors.append(f"source has invalid scope: {source['id']}")
        elif isinstance(scope, str):
            source_scopes[source["id"]] = scope
        if isinstance(source.get("publisher"), str):
            source_publishers[source["id"]] = source["publisher"]
        if isinstance(source.get("subject"), str) and isinstance(source.get("subject_version"), str):
            source_subject_versions[source["id"]] = (source["subject"], source["subject_version"])
        if status == "ready":
            publisher = source.get("publisher")
            locator = source.get("locator")
            if source.get("kind") != "pinned-source-copy" or not isinstance(publisher, str) or publisher not in PUBLISHER_HOSTS or not valid_locator(locator):
                errors.append(f"ready source lacks official publisher metadata: {source['id']}")
            else:
                parsed = parse_locator(locator)
                assert parsed is not None
                if parsed.hostname not in PUBLISHER_HOSTS[str(publisher)]:
                    errors.append(f"ready source publisher/host mismatch: {source['id']}")
                if not approved_publisher_path(str(publisher), str(parsed.hostname), parsed.path, scope):
                    errors.append(f"source is outside approved publisher paths: {source['id']}")
            applies_from = source.get("applies_from")
            applies_to = source.get("applies_to")
            if isinstance(scope, str) and scope in {"migration-guide", "release-notes"}:
                if not isinstance(applies_from, str) or not VERSION.fullmatch(applies_from) or not isinstance(applies_to, str) or not VERSION.fullmatch(applies_to) or source.get("checked_version") != applies_to:
                    errors.append(f"ready migration source lacks exact applicability: {source['id']}")
                else:
                    source_applicability[source["id"]] = (applies_from, applies_to)
                    capture = source.get("capture")
                    final_locator = capture.get("final_locator") if isinstance(capture, dict) else None
                    requested_parsed = parse_locator(locator)
                    final_parsed = parse_locator(final_locator)
                    if (
                        requested_parsed is None
                        or final_parsed is None
                        or not locator_matches_applicability(requested_parsed.path, scope, applies_to)
                        or not locator_matches_applicability(final_parsed.path, scope, applies_to)
                    ):
                        errors.append(f"ready source locator version does not match applicability: {source['id']}")
            elif (
                source.get("checked_version") != target_version
                or not isinstance(scope, str)
                or scope not in SOURCE_SCOPES
                or applies_from is not None
                or applies_to is not None
            ):
                errors.append(f"ready source lacks target version/scope or has unexpected applicability: {source['id']}")
            if isinstance(scope, str) and scope in {"system-requirements", "managed-dependencies", "spring-upgrade-guide", "build-system-guide"}:
                capture = source.get("capture")
                final_locator = capture.get("final_locator") if isinstance(capture, dict) else None
                requested_parsed = parse_locator(locator)
                final_parsed = parse_locator(final_locator)
                if (
                    requested_parsed is None
                    or final_parsed is None
                    or not locator_matches_checked_boot_line(
                        requested_parsed.path, scope, source.get("checked_version")
                    )
                    or not locator_matches_checked_boot_line(
                        final_parsed.path, scope, source.get("checked_version")
                    )
                ):
                    errors.append(f"ready source locator line does not match checked Spring Boot version: {source['id']}")
            checked_cloud = source.get("checked_spring_cloud")
            if scope in {"spring-cloud-compatibility", "spring-cloud-release-notes"}:
                if not isinstance(target_cloud, str) or checked_cloud != target_cloud:
                    errors.append(f"Spring Cloud source is not bound to target service release: {source['id']}")
            elif checked_cloud is not None:
                errors.append(f"non-Cloud source has unexpected checked_spring_cloud: {source['id']}")
            subject = source.get("subject")
            subject_version = source.get("subject_version")
            expected_subject = SCOPE_SUBJECT.get(str(scope))
            expected_subject_version: object = None
            if expected_subject == "spring-boot":
                expected_subject_version = applies_to if scope in {"migration-guide", "release-notes"} else target_version
            elif expected_subject == "spring-cloud":
                expected_subject_version = target_cloud
            elif expected_subject == "java":
                expected_subject_version = target_java
            elif expected_subject == "maven" and target_build_tool == "maven":
                expected_subject_version = target_build_tool_version
            elif expected_subject == "gradle" and target_build_tool == "gradle":
                expected_subject_version = target_build_tool_version
            elif (
                expected_subject == "openrewrite"
                and isinstance(subject_version, str)
                and VERSION.fullmatch(subject_version) is not None
            ):
                expected_subject_version = subject_version
            if (
                expected_subject is None
                or subject != expected_subject
                or not isinstance(subject_version, str)
                or subject_version != expected_subject_version
            ):
                errors.append(f"ready source subject/version is not bound to the plan target: {source['id']}")
            capture = source.get("capture")
            final_locator = capture.get("final_locator") if isinstance(capture, dict) else None
            requested_parsed = parse_locator(locator)
            final_parsed = parse_locator(final_locator)
            if (
                requested_parsed is None
                or final_parsed is None
                or (
                    scope != "java-support-policy"
                    and not locator_matches_subject_version(requested_parsed.path, subject, subject_version)
                )
                or (
                    scope != "java-support-policy"
                    and not locator_matches_subject_version(final_parsed.path, subject, subject_version)
                )
                or not locator_matches_cloud_train(requested_parsed.path, scope, subject_version)
                or not locator_matches_cloud_train(final_parsed.path, scope, subject_version)
            ):
                errors.append(f"ready source locator does not match subject version: {source['id']}")
            if source.get("kind") == "official-snapshot":
                errors.append(f"legacy official-snapshot kind is not provenance-safe: {source['id']}")
            if source.get("kind") != "pinned-source-copy" or not valid_capture(
                source.get("capture"), locator, publisher, scope, source.get("sha256"), now=validation_time
            ):
                errors.append(f"ready source lacks a controlled capture manifest: {source['id']}")
            if not valid_snapshot_path(source.get("snapshot_path")) or not SHA256.fullmatch(str(source.get("sha256", ""))):
                errors.append(f"ready source lacks a safe snapshot path or SHA-256: {source['id']}")
            elif base_dir is None:
                errors.append(f"ready source hash requires a plan base directory: {source['id']}")
            else:
                base = base_dir.resolve()
                candidate = base / str(source["snapshot_path"])
                snapshot = candidate.resolve()
                try:
                    snapshot.relative_to(base)
                except ValueError:
                    errors.append(f"ready source snapshot escapes plan directory: {source['id']}")
                else:
                    if is_link_or_junction(candidate) or not snapshot.is_file():
                        errors.append(f"ready source snapshot is missing or linked: {source['id']}")
                    else:
                        try:
                            digest = file_sha256(snapshot)
                        except OSError:
                            errors.append(f"ready source snapshot cannot be read: {source['id']}")
                        else:
                            if digest != source["sha256"]:
                                errors.append(f"ready source snapshot hash mismatch: {source['id']}")
    if input_source_ids_valid and set(input_source_ids) != source_ids:
        errors.append("input source_snapshot_ids do not match source_ledger")

    gates = plan.get("compatibility_gates")
    gate_ids: set[str] = set()
    if not isinstance(gates, list) or not gates:
        errors.append("compatibility_gates must be a non-empty array")
        gates = []
    for index, gate in enumerate(gates):
        if (
            not isinstance(gate, dict)
            or not isinstance(gate.get("id"), str)
            or not isinstance(gate.get("status"), str)
            or gate.get("status") not in GATE_STATUSES
        ):
            errors.append(f"compatibility_gates[{index}] is invalid")
            continue
        if set(gate) != GATE_FIELDS:
            errors.append(f"compatibility_gates[{index}] has invalid fields")
        if gate["id"] in gate_ids:
            errors.append(f"duplicate compatibility gate: {gate['id']}")
        gate_ids.add(gate["id"])
        referenced = gate.get("source_ids")
        if (
            not isinstance(referenced, list)
            or not all(isinstance(item, str) and SOURCE_ID.fullmatch(item) is not None for item in referenced)
            or len(set(referenced)) != len(referenced)
        ):
            errors.append(f"gate source_ids are invalid: {gate['id']}")
            referenced_ids: list[str] = []
        else:
            referenced_ids = referenced
        if set(referenced_ids) - source_ids:
            errors.append(f"gate references unknown sources: {gate['id']}")
        gate_evidence_ids = evidence_ids(gate.get("evidence_ids"))
        if gate_evidence_ids is None:
            errors.append(f"gate evidence_ids are invalid: {gate['id']}")
        elif status == "ready" and set(gate_evidence_ids) - set(evidence_fact_index):
            errors.append(f"gate references evidence absent from the snapshot: {gate['id']}")
        if status == "ready":
            if gate["id"] in {"gate:target-support", "gate:java-build-tools"} and gate["status"] != "pass":
                errors.append(f"required gate must pass: {gate['id']}")
            elif gate["status"] not in {"pass", "not-applicable"}:
                errors.append(f"ready plan has unresolved gate: {gate['id']}")
            if gate["status"] == "pass" and not referenced_ids:
                errors.append(f"passing gate lacks source_ids: {gate['id']}")
            expected_scope = GATE_SCOPE.get(gate["id"])
            if gate["status"] == "pass" and expected_scope and not any(source_scopes.get(source_id) == expected_scope for source_id in referenced_ids):
                errors.append(f"passing gate lacks a source scoped for {expected_scope}: {gate['id']}")
            allowed_publishers = GATE_PUBLISHERS.get(gate["id"])
            if gate["status"] == "pass" and allowed_publishers and not any(source_publishers.get(source_id) in allowed_publishers for source_id in referenced_ids if source_scopes.get(source_id) == expected_scope):
                errors.append(f"passing gate lacks an allowed publisher: {gate['id']}")
            if gate["status"] == "not-applicable" and (not isinstance(gate.get("rationale"), str) or not gate["rationale"].strip()):
                errors.append(f"not-applicable gate lacks rationale: {gate['id']}")
            if gate["status"] == "not-applicable" and not nonempty_items(gate.get("evidence_ids")):
                errors.append(f"not-applicable gate lacks evidence_ids: {gate['id']}")
            if gate["id"] == "gate:spring-cloud":
                if gate["status"] == "pass" and (target_cloud_usage != "used" or not isinstance(target_cloud, str)):
                    errors.append("passing Spring Cloud gate requires target.spring_cloud")
                if gate["status"] == "not-applicable" and (target_cloud_usage != "not-used" or target_cloud is not None):
                    errors.append("not-applicable Spring Cloud gate requires confirmed target non-use")
                if gate["status"] == "not-applicable" and gate_evidence_ids and not all(
                    evidence_fact_index.get(item, {}).get("kind") == "platform.usage"
                    and evidence_fact_index.get(item, {}).get("name") == "spring-cloud"
                    and evidence_fact_index.get(item, {}).get("value") == "not-used"
                    and evidence_fact_index.get(item, {}).get("certainty") in {"effective", "resolved"}
                    for item in gate_evidence_ids
                ):
                    errors.append("not-applicable Spring Cloud gate lacks resolved non-use evidence")
            if gate["id"] == "gate:java-build-tools" and gate["status"] == "pass":
                required_subjects = {
                    ("spring-boot", str(target_version), "system-requirements"),
                    ("java", str(target_java), "java-migration"),
                    (str(target_build_tool), str(target_build_tool_version), f"{target_build_tool}-reference"),
                }
                referenced_subjects = {
                    (*source_subject_versions[source_id], source_scopes.get(source_id))
                    for source_id in referenced_ids
                    if source_id in source_subject_versions and source_id in source_scopes
                }
                missing_subjects = required_subjects - referenced_subjects
                if missing_subjects:
                    labels = ", ".join(
                        f"{subject}:{version} ({scope})"
                        for subject, version, scope in sorted(missing_subjects)
                    )
                    errors.append(f"Java/build-tool gate lacks subject-bound sources: {labels}")
    missing_gates = REQUIRED_GATES - gate_ids
    if missing_gates:
        errors.append("missing required gates: " + ", ".join(sorted(missing_gates)))
    bridge_lines: set[tuple[int, int]] = set()
    if status == "ready" and isinstance(current_version, str) and VERSION.fullmatch(current_version) and isinstance(target_version, str) and VERSION.fullmatch(target_version):
        bridge_lines = required_bridge_lines(current_version, target_version)
        if bridge_lines and "gate:major-bridge" not in gate_ids:
            errors.append("major upgrade is missing gate:major-bridge")
        elif bridge_lines:
            bridge = next((gate for gate in gates if isinstance(gate, dict) and gate.get("id") == "gate:major-bridge"), None)
            if not isinstance(bridge, dict) or bridge.get("status") != "pass":
                errors.append("major upgrade bridge gate must pass")

    hops = plan.get("hops")
    if not isinstance(hops, list) or not hops:
        errors.append("hops must be a non-empty array")
        hops = []
    for index, hop in enumerate(hops):
        if not isinstance(hop, dict):
            errors.append(f"hops[{index}] must be an object")
            continue
        if set(hop) != HOP_FIELDS:
            errors.append(f"hops[{index}] has invalid fields")
        if not all(isinstance(hop.get(field), str) and hop[field] for field in ("id", "from", "to", "rationale")):
            errors.append(f"hops[{index}] has invalid identity or endpoints")
        referenced = hop.get("source_ids")
        if not isinstance(referenced, list) or not all(isinstance(item, str) and SOURCE_ID.fullmatch(item) is not None for item in referenced) or set(referenced) - source_ids:
            errors.append(f"hops[{index}] has invalid source references")
        if status == "ready":
            if not VERSION.fullmatch(str(hop.get("from", ""))) or not VERSION.fullmatch(str(hop.get("to", ""))):
                errors.append(f"ready hop must use exact versions: {hop.get('id', index)}")
            for field in ("source_ids", "changes", "verification", "rollback"):
                if not nonempty_items(hop.get(field)):
                    errors.append(f"ready plan hop lacks valid {field}: {hop.get('id', index)}")
            applicable = [
                source_id for source_id in referenced
                if source_scopes.get(source_id) in {"migration-guide", "release-notes"}
                and source_applicability.get(source_id) == (hop.get("from"), hop.get("to"))
            ] if isinstance(referenced, list) else []
            if not applicable:
                errors.append(f"ready hop lacks an applicable migration/release source: {hop.get('id', index)}")
            elif not any(source_publishers.get(source_id) in {"spring", "spring-github"} for source_id in applicable):
                errors.append(f"ready hop lacks an official Spring publisher: {hop.get('id', index)}")
    if status == "ready" and hops and all(isinstance(hop, dict) for hop in hops):
        if hops[0].get("from") != current_version or hops[-1].get("to") != target_version:
            errors.append("ready hop chain does not match current and target versions")
        for previous, following in zip(hops, hops[1:]):
            if previous.get("to") != following.get("from"):
                errors.append("ready hop chain is not continuous")
                break
        endpoints = {
            tuple(int(value) for value in str(hop[field]).split("-", 1)[0].split("."))[:2]
            for hop in hops for field in ("from", "to") if VERSION.fullmatch(str(hop.get(field, "")))
        }
        missing_lines = bridge_lines - endpoints
        if missing_lines:
            errors.append("ready hop chain skips required landing lines: " + ", ".join(f"{major}.{minor}.x" for major, minor in sorted(missing_lines)))

    unresolved = plan.get("unresolved")
    if not isinstance(unresolved, list) or not all(isinstance(item, str) and item for item in unresolved):
        errors.append("unresolved must be a string array")
    elif status == "ready" and unresolved:
        errors.append("ready plan cannot contain unresolved items")
    if status == "blocked" and not unresolved:
        errors.append("blocked plan must explain the blocker")
    if not isinstance(plan.get("automation"), list) or not all(isinstance(item, dict) for item in plan.get("automation", [])):
        errors.append("automation must be an array")
    rollout = plan.get("rollout")
    if not isinstance(rollout, dict) or set(rollout) != {"canary_signals", "rollback_trigger"} or not isinstance(rollout.get("canary_signals"), list):
        errors.append("rollout is invalid")
    elif status == "ready" and (not nonempty_items(rollout["canary_signals"]) or not isinstance(rollout.get("rollback_trigger"), str) or not rollout["rollback_trigger"]):
        errors.append("ready plan needs canary signals and a rollback trigger")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate spring-upgrade-plan/2 JSON semantics.")
    parser.add_argument("plan", type=Path)
    args = parser.parse_args()
    try:
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        print(f"ERROR: cannot read valid UTF-8 plan JSON: {error}")
        return 1
    errors = validate(plan, args.plan.parent)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Upgrade plan is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
