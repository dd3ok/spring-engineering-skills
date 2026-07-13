from __future__ import annotations

import argparse
import http.client
import math
import re
import subprocess
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit


ROOT = Path(__file__).resolve().parents[1]
UPGRADE_SCRIPTS = ROOT / "skills" / "spring-upgrade-planner" / "scripts"
sys.path.insert(0, str(UPGRADE_SCRIPTS))

from cloud_policy import POLICY_PATH, load_policy  # noqa: E402
from check_links import PinnedHTTPSConnection, resolved_addresses  # noqa: E402


MAX_BODY_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 5
MAX_ADDRESSES = 4
APPROVED_HOST = "spring.io"
OFFICIAL_ROW = re.compile(
    r"(?P<row>(?P<train>\d{4}\.\d{1,4}\.x) aka [A-Za-z][A-Za-z0-9-]* "
    r"\d{1,4}\.\d{1,4}\.x(?:, \d{1,4}\.\d{1,4}\.x)*"
    r"(?: \(Starting with \d{4}\.\d{1,4}\.\d{1,4}\))?)"
)


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def normalized_page_text(payload: bytes) -> str:
    parser = TextExtractor()
    parser.feed(payload.decode("utf-8"))
    return " ".join(" ".join(parser.parts).split())


def fetch_official_page(url: str, timeout: float = 15.0) -> bytes:
    current = url
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    deadline = time.monotonic() + timeout
    for _ in range(MAX_REDIRECTS + 1):
        parsed = urlsplit(current)
        if (
            parsed.scheme != "https"
            or parsed.hostname != APPROVED_HOST
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in {None, 443}
        ):
            raise ValueError("Spring Cloud policy fetch left the approved HTTPS publisher")
        host, port, addresses = resolved_addresses(current)
        if time.monotonic() >= deadline:
            raise TimeoutError("Spring Cloud policy fetch exceeded its total network deadline")
        last_error: Exception | None = None
        for address in addresses[:MAX_ADDRESSES]:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Spring Cloud policy fetch exceeded its total network deadline")
            connection = PinnedHTTPSConnection(host, port, address, remaining)
            try:
                target = parsed.path or "/"
                if parsed.query:
                    target += "?" + parsed.query
                connection.request("GET", target, headers={"User-Agent": "spring-engineering-skills-policy-check/1.0"})
                response = connection.getresponse()
                status = response.status
                location = response.getheader("Location")
                content_type = response.getheader("Content-Type", "")
                payload = response.read(MAX_BODY_BYTES + 1)
            except (OSError, http.client.HTTPException) as error:
                last_error = error
                continue
            finally:
                connection.close()
            if status in {301, 302, 303, 307, 308}:
                if not location:
                    raise ValueError("Spring Cloud policy redirect has no Location")
                current = urljoin(current, location)
                break
            if status != 200:
                raise ValueError(f"Spring Cloud policy source returned HTTP {status}")
            if "text/html" not in content_type.lower():
                raise ValueError("Spring Cloud policy source is not HTML")
            if len(payload) > MAX_BODY_BYTES:
                raise ValueError("Spring Cloud policy source exceeds the response limit")
            return payload
        else:
            if last_error is not None:
                raise last_error
            raise OSError("Spring Cloud policy source could not be reached")
    raise ValueError("Spring Cloud policy source redirected too many times")


def marker_errors(policy: dict[str, object], page_text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", page_text).strip()
    rows = policy.get("rows", [])
    if not isinstance(rows, list):
        return ["Spring Cloud policy rows are invalid"]
    expected = {
        f"{row.get('train')}.x": row.get("source_text")
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("train"), str)
    }
    if not expected or not all(isinstance(marker, str) and marker for marker in expected.values()):
        return ["Spring Cloud policy source text is invalid"]
    observed = {match.group("train"): match.group("row") for match in OFFICIAL_ROW.finditer(normalized)}
    return [
        f"Spring Cloud official table row changed or disappeared: {marker}"
        for train, marker in expected.items()
        if observed.get(train) != marker
    ]


def fetch_with_deadline(url: str, timeout: float) -> bytes:
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be a positive finite number")
    command = (sys.executable, str(Path(__file__).resolve()), "--fetch-only", url, "--timeout", str(timeout))
    try:
        # This is the authoritative end-to-end deadline. Keep it equal to the caller's budget so
        # process startup, DNS, redirects, headers, and body reads cannot extend the wall clock.
        completed = subprocess.run(command, capture_output=True, check=False, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        raise TimeoutError("Spring Cloud policy fetch exceeded its wall-clock deadline") from error
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise OSError(detail or "Spring Cloud policy fetch worker failed")
    if len(completed.stdout) > MAX_BODY_BYTES:
        raise ValueError("Spring Cloud policy fetch worker exceeded the response limit")
    return completed.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Spring Cloud policy and optionally check official-table drift.")
    parser.add_argument("--policy", type=Path, default=POLICY_PATH)
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--fetch-only", metavar="URL", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.fetch_only is not None:
        try:
            sys.stdout.buffer.write(fetch_official_page(args.fetch_only, args.timeout))
        except (OSError, UnicodeError, ValueError, http.client.HTTPException) as error:
            print(error, file=sys.stderr)
            return 1
        return 0
    policy, errors = load_policy(args.policy)
    if args.online and not errors:
        try:
            page_text = normalized_page_text(fetch_with_deadline(str(policy["source_locator"]), args.timeout))
        except (OSError, UnicodeError, ValueError, http.client.HTTPException) as error:
            errors.append(f"Spring Cloud official table check is inconclusive: {error}")
        else:
            errors.extend(marker_errors(policy, page_text))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Spring Cloud compatibility policy is valid" + (" and matches official markers." if args.online else "."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
