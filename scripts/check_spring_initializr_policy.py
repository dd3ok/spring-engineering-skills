from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import math
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

from check_links import PinnedHTTPSConnection, resolved_addresses


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = (
    ROOT
    / "skills"
    / "spring-application-developer"
    / "references"
    / "greenfield-baseline-policy.json"
)
EXPECTED_ACCEPT = "application/vnd.initializr.v2.3+json"
APPROVED_HOST = "start.spring.io"
APPROVED_PATH = "/metadata/client"
MAX_BODY_BYTES = 1024 * 1024
MAX_ADDRESSES = 4
COMMIT = re.compile(r"^[a-f0-9]{40}$")
CAPABILITIES = (
    "bootVersion",
    "javaVersion",
    "type",
    "language",
    "packaging",
    "configurationFileFormat",
)


def locator_error(url: object) -> str | None:
    if not isinstance(url, str) or not url:
        return "Initializr metadata source is missing"
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError:
        return "Initializr metadata source must be the approved HTTPS endpoint"
    if (
        parsed.scheme != "https"
        or parsed.hostname != APPROVED_HOST
        or parsed.path != APPROVED_PATH
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 443}
    ):
        return "Initializr metadata source must be the approved HTTPS endpoint"
    return None


def load_contract(path: Path = POLICY_PATH) -> tuple[str | None, str | None, list[str]]:
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return None, None, [f"Initializr policy could not be loaded: {error}"]
    if not isinstance(policy, dict) or not isinstance(policy.get("metadata"), dict):
        return None, None, ["Initializr policy metadata contract is missing"]
    metadata = policy["metadata"]
    source = metadata.get("source")
    accept = metadata.get("accept")
    errors: list[str] = []
    source_error = locator_error(source)
    if source_error:
        errors.append(source_error)
    if accept != EXPECTED_ACCEPT:
        errors.append("Initializr metadata Accept contract is not v2.3")
    return (
        source if isinstance(source, str) else None,
        accept if isinstance(accept, str) else None,
        errors,
    )


def content_type_error(content_type: str, accept: str = EXPECTED_ACCEPT) -> str | None:
    actual = content_type.split(";", 1)[0].strip().lower()
    if actual != accept.lower():
        return f"Initializr metadata Content-Type changed: {content_type or '<missing>'}"
    return None


def metadata_errors(payload: bytes) -> list[str]:
    try:
        metadata = json.loads(payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        return [f"Initializr metadata is not valid UTF-8 JSON: {error}"]
    if not isinstance(metadata, dict):
        return ["Initializr metadata root is not an object"]
    errors: list[str] = []
    for name in CAPABILITIES:
        capability = metadata.get(name)
        if not isinstance(capability, dict):
            errors.append(f"Initializr metadata capability is missing: {name}")
            continue
        default = capability.get("default")
        values = capability.get("values")
        if not isinstance(default, str) or not default:
            errors.append(f"Initializr metadata default is invalid: {name}")
            continue
        if not isinstance(values, list) or not values:
            errors.append(f"Initializr metadata values are invalid: {name}")
            continue
        advertised = {
            value.get("id")
            for value in values
            if isinstance(value, dict) and isinstance(value.get("id"), str)
        }
        if default not in advertised:
            errors.append(f"Initializr metadata default is not advertised: {name}={default}")
            continue
        if name == "type":
            selected = next(
                (value for value in values if isinstance(value, dict) and value.get("id") == default),
                None,
            )
            tags = selected.get("tags") if isinstance(selected, dict) else None
            if not isinstance(tags, dict):
                errors.append("Initializr default project type tags are missing or invalid")
            else:
                if not isinstance(tags.get("build"), str) or not tags["build"]:
                    errors.append("Initializr default project type has no build tag")
                if tags.get("format") != "project":
                    errors.append("Initializr default project type is not a project format")
            for project_type in values:
                if not isinstance(project_type, dict) or project_type.get("id") == default:
                    continue
                project_tags = project_type.get("tags")
                if not isinstance(project_tags, dict) or project_tags.get("format") != "project":
                    continue
                build = project_tags.get("build")
                if not isinstance(build, str) or not build:
                    errors.append(
                        "Initializr project type has no build tag: "
                        f"{project_type.get('id', '<missing-id>')}"
                    )
    return errors


def fetch_official_metadata(url: str, accept: str, timeout: float) -> bytes:
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be a positive finite number")
    source_error = locator_error(url)
    if source_error:
        raise ValueError(source_error)
    deadline = time.monotonic() + timeout
    host, port, addresses = resolved_addresses(url)
    last_error: Exception | None = None
    for address in addresses[:MAX_ADDRESSES]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Initializr metadata fetch exceeded its total network deadline")
        connection = PinnedHTTPSConnection(host, port, address, remaining)
        try:
            connection.request(
                "GET",
                APPROVED_PATH,
                headers={
                    "Accept": accept,
                    "User-Agent": "spring-engineering-skills-initializr-check/1.0",
                },
            )
            response = connection.getresponse()
            status = response.status
            content_type = response.getheader("Content-Type", "")
            payload = response.read(MAX_BODY_BYTES + 1)
        except (OSError, http.client.HTTPException) as error:
            last_error = error
            continue
        finally:
            connection.close()
        if status != 200:
            raise ValueError(f"Initializr metadata source returned HTTP {status}")
        type_error = content_type_error(content_type, accept)
        if type_error:
            raise ValueError(type_error)
        if len(payload) > MAX_BODY_BYTES:
            raise ValueError("Initializr metadata source exceeds the response limit")
        return payload
    if last_error is not None:
        raise last_error
    raise OSError("Initializr metadata source could not be reached")


def fetch_with_deadline(url: str, accept: str, timeout: float) -> bytes:
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be a positive finite number")
    command = (
        sys.executable,
        str(Path(__file__).resolve()),
        "--fetch-only",
        url,
        "--accept",
        accept,
        "--timeout",
        str(timeout),
    )
    try:
        completed = subprocess.run(command, capture_output=True, check=False, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        raise TimeoutError("Initializr metadata fetch exceeded its wall-clock deadline") from error
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise OSError(detail or "Initializr metadata fetch worker failed")
    if len(completed.stdout) > MAX_BODY_BYTES:
        raise ValueError("Initializr metadata fetch worker exceeded the response limit")
    return completed.stdout


def save_evaluation_source(payload: bytes, artifact_root: Path, skill_commit: str) -> Path:
    if COMMIT.fullmatch(skill_commit) is None:
        raise ValueError("skill_commit must be a lowercase 40-character commit")
    digest = hashlib.sha256(payload).hexdigest()
    destination = (
        artifact_root / skill_commit / "sources" / "initializr" / f"{digest}.json"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if not destination.is_file() or destination.read_bytes() != payload:
            raise ValueError("Initializr evaluation source path contains different bytes")
        return destination
    destination.write_bytes(payload)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the local Initializr contract and optionally check live metadata semantics."
    )
    parser.add_argument("--policy", type=Path, default=POLICY_PATH)
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument(
        "--save-evaluation-source",
        type=Path,
        metavar="ARTIFACT_ROOT",
        help="Save validated live bytes under a content-addressed evaluation-only path.",
    )
    parser.add_argument("--skill-commit")
    parser.add_argument("--fetch-only", metavar="URL", help=argparse.SUPPRESS)
    parser.add_argument("--accept", default=EXPECTED_ACCEPT, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.save_evaluation_source is not None and not args.online:
        parser.error("--save-evaluation-source requires --online")
    if args.save_evaluation_source is not None and (
        not isinstance(args.skill_commit, str) or COMMIT.fullmatch(args.skill_commit) is None
    ):
        parser.error("--save-evaluation-source requires --skill-commit with 40 lowercase hex characters")
    if args.skill_commit is not None and args.save_evaluation_source is None:
        parser.error("--skill-commit requires --save-evaluation-source")
    if args.fetch_only is not None:
        try:
            sys.stdout.buffer.write(
                fetch_official_metadata(args.fetch_only, args.accept, args.timeout)
            )
        except (OSError, UnicodeError, ValueError, http.client.HTTPException) as error:
            print(error, file=sys.stderr)
            return 1
        return 0

    source, accept, errors = load_contract(args.policy)
    saved_source: Path | None = None
    if args.online and not errors and source is not None and accept is not None:
        try:
            payload = fetch_with_deadline(source, accept, args.timeout)
        except (OSError, UnicodeError, ValueError, http.client.HTTPException) as error:
            errors.append(f"Initializr metadata check is inconclusive: {error}")
        else:
            errors.extend(metadata_errors(payload))
            if not errors and args.save_evaluation_source is not None:
                try:
                    saved_source = save_evaluation_source(
                        payload,
                        args.save_evaluation_source,
                        args.skill_commit,
                    )
                except (OSError, ValueError) as error:
                    errors.append(f"Initializr evaluation source could not be saved: {error}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(
        "Spring Initializr metadata contract is valid"
        + (" and matches live semantics." if args.online else ".")
    )
    if saved_source is not None:
        print(f"Initializr evaluation source: {saved_source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
