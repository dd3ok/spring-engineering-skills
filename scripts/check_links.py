from __future__ import annotations

import argparse
import http.client
import ipaddress
import json
import re
import socket
import ssl
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlsplit


ROOT = Path(__file__).resolve().parents[1]
BARE_URL = re.compile(r"https?://[^\s<`]+")
RUNTIME_PATH = re.compile(r"`((?:references|scripts|assets)/[^`]+)`")
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
INCONCLUSIVE_STATUS = {401, 403, 429}


@dataclass(frozen=True)
class LinkResult:
    status: str
    target: str
    detail: str = ""


def resolved_addresses(url: str, allow_private: bool = False) -> tuple[str, int, tuple[str, ...]]:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("only absolute HTTP(S) URLs are supported")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as error:
        raise ValueError("URL has an invalid port") from error
    addresses = {
        item[4][0]
        for item in socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
    }
    if not addresses:
        raise ValueError("host did not resolve")
    blocked = sorted(address for address in addresses if not ipaddress.ip_address(address.split("%", 1)[0]).is_global)
    if blocked:
        if not allow_private:
            raise ValueError("private, local, reserved, or non-global address blocked: " + ", ".join(blocked))
    return parsed.hostname, port, tuple(sorted(addresses))


class PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host: str, port: int, address: str, timeout: float) -> None:
        super().__init__(host, port, timeout=timeout)
        self.address = address

    def connect(self) -> None:
        self.sock = socket.create_connection((self.address, self.port), self.timeout, self.source_address)


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, port: int, address: str, timeout: float) -> None:
        super().__init__(host, port, timeout=timeout, context=ssl.create_default_context())
        self.address = address

    def connect(self) -> None:
        raw = socket.create_connection((self.address, self.port), self.timeout, self.source_address)
        self.sock = self._context.wrap_socket(raw, server_hostname=self.host)


def markdown_files() -> list[Path]:
    files = list(sorted(ROOT.glob("README*.md")))
    files.extend(sorted((ROOT / "docs").glob("**/*.md")))
    files.extend(sorted((ROOT / "evals").glob("**/*.md")))
    files.extend(sorted((ROOT / "skills").glob("*/SKILL.md")))
    files.extend(sorted((ROOT / "skills").glob("*/references/**/*.md")))
    return [path for path in files if path.is_file()]


def normalize_markdown_target(raw: str) -> str:
    target = raw.strip()
    if target.startswith("<") and ">" in target:
        return target[1 : target.index(">")]
    return target.split(maxsplit=1)[0]


def markdown_link_targets(text: str) -> list[tuple[str, int, int]]:
    targets: list[tuple[str, int, int]] = []
    position = 0
    while True:
        marker = text.find("](", position)
        if marker == -1:
            break
        start = marker + 2
        index = start
        depth = 1
        while index < len(text):
            character = text[index]
            if character == "\\":
                index += 2
                continue
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0:
                    targets.append((text[start:index], start, index))
                    index += 1
                    break
            index += 1
        position = max(index, start + 1)
    return targets


def normalize_bare_url(raw: str) -> str:
    target = raw.rstrip(".,;")
    while target.endswith(")") and target.count(")") > target.count("("):
        target = target[:-1]
    return target


def extract_targets(path: Path) -> tuple[set[str], set[str]]:
    text = path.read_text(encoding="utf-8")
    markdown_targets = markdown_link_targets(text)
    markdown_spans = [(start, end) for _, start, end in markdown_targets]
    external = {
        normalize_bare_url(match.group(0))
        for match in BARE_URL.finditer(text)
        if not any(start <= match.start() < end for start, end in markdown_spans)
    }
    internal: set[str] = set()
    for raw_target, _, _ in markdown_targets:
        target = normalize_markdown_target(raw_target)
        if target.startswith(("http://", "https://")):
            external.add(target.rstrip(".,;"))
        elif target and not target.startswith(("#", "mailto:")):
            internal.add(target)
    if path.name == "SKILL.md" and path.parent.parent == ROOT / "skills":
        internal.update(match.group(1) for match in RUNTIME_PATH.finditer(text))
    return external, internal


def has_exact_case(path: Path) -> bool:
    try:
        relative = path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return False
    current = ROOT.resolve()
    for part in relative.parts:
        names = {child.name for child in current.iterdir()}
        if part not in names:
            return False
        current /= part
    return True


def check_internal_links(files: list[Path]) -> list[LinkResult]:
    results: list[LinkResult] = []
    for source in files:
        _, targets = extract_targets(source)
        for target in sorted(targets):
            clean = unquote(target.split("#", 1)[0])
            base = source.parent
            resolved = (base / clean).resolve()
            label = f"{source.relative_to(ROOT)} -> {target}"
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                results.append(LinkResult("failed", label, "path escapes the repository"))
                continue
            if not resolved.exists():
                results.append(LinkResult("failed", label, "target does not exist"))
            elif not has_exact_case(resolved):
                results.append(LinkResult("failed", label, "path case does not match the filesystem"))
            else:
                results.append(LinkResult("ok", label))
    return results


def open_external(url: str, timeout: float, allow_private: bool = False) -> tuple[int, str]:
    current = url
    for _ in range(10):
        parsed = urlsplit(current)
        host, port, addresses = resolved_addresses(current, allow_private)
        last_error: Exception | None = None
        for address in addresses:
            connection_type = PinnedHTTPSConnection if parsed.scheme == "https" else PinnedHTTPConnection
            connection = connection_type(host, port, address, timeout)
            try:
                target = parsed.path or "/"
                if parsed.query:
                    target += "?" + parsed.query
                connection.request("GET", target, headers={"User-Agent": "spring-engineering-skills-link-check/1.0", "Range": "bytes=0-0"})
                response = connection.getresponse()
                response.read(1)
                location = response.getheader("Location")
                status = response.status
            except (OSError, http.client.HTTPException) as error:
                last_error = error
                continue
            finally:
                connection.close()
            if status in {301, 302, 303, 307, 308} and location:
                current = urljoin(current, location)
                break
            return status, current
        else:
            if last_error is not None:
                raise last_error
            raise OSError("no resolved address could be reached")
    raise ValueError("too many redirects")


def check_external_link(url: str, timeout: float, retries: int, allow_private: bool = False) -> LinkResult:
    last_detail = ""
    for attempt in range(retries + 1):
        try:
            status, final_url = open_external(url, timeout, allow_private)
            if urlsplit(url).scheme == "https" and urlsplit(final_url).scheme == "http":
                return LinkResult("failed", url, f"redirected to insecure URL: {final_url}")
            if status in INCONCLUSIVE_STATUS:
                return LinkResult("inconclusive", url, f"HTTP {status}: {final_url}")
            if status >= 400:
                return LinkResult("failed", url, f"HTTP {status}: {final_url}")
            return LinkResult("ok", url, final_url if final_url != url else "")
        except HTTPError as error:
            last_detail = f"HTTP {error.code}: {error.geturl()}"
            if error.code in INCONCLUSIVE_STATUS and error.code not in RETRYABLE_STATUS:
                return LinkResult("inconclusive", url, last_detail)
            if error.code not in RETRYABLE_STATUS or attempt == retries:
                status = "inconclusive" if error.code in INCONCLUSIVE_STATUS else "failed"
                return LinkResult(status, url, last_detail)
        except ValueError as error:
            return LinkResult("failed", url, str(error))
        except (TimeoutError, URLError, OSError, http.client.HTTPException) as error:
            last_detail = f"{type(error).__name__}: {error}"
            if attempt == retries:
                return LinkResult("inconclusive", url, last_detail)
        time.sleep(0.25 * (2**attempt))
    return LinkResult("inconclusive", url, last_detail)


def external_urls(files: list[Path]) -> list[str]:
    urls: set[str] = set()
    for path in files:
        external, _ = extract_targets(path)
        urls.update(external)
    return sorted(urls)


def check_external_links(
    urls: list[str], timeout: float, retries: int, workers: int, allow_private: bool = False
) -> list[LinkResult]:
    results: list[LinkResult] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(check_external_link, url, timeout, retries, allow_private): url for url in urls
        }
        for future in as_completed(futures):
            results.append(future.result())
    return sorted(results, key=lambda result: result.target)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check internal and optional external Markdown links.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true", help="Check internal links only (default).")
    mode.add_argument("--online", action="store_true", help="Also check external URLs.")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--allow-private",
        action="store_true",
        help="Allow localhost, private, and non-global destinations during online checks.",
    )
    parser.add_argument("--json-report", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    files = markdown_files()
    results = check_internal_links(files)
    if args.online:
        results.extend(
            check_external_links(external_urls(files), args.timeout, args.retries, args.workers, args.allow_private)
        )

    counts = {status: sum(result.status == status for result in results) for status in ("ok", "inconclusive", "failed")}
    for result in results:
        if result.status != "ok":
            print(f"{result.status.upper()}: {result.target}: {result.detail}", file=sys.stderr)
    print(f"Links: {counts['ok']} ok, {counts['inconclusive']} inconclusive, {counts['failed']} failed")

    if args.json_report:
        args.json_report.parent.mkdir(parents=True, exist_ok=True)
        args.json_report.write_text(
            json.dumps({"counts": counts, "results": [asdict(result) for result in results]}, indent=2) + "\n",
            encoding="utf-8",
        )
    if counts["failed"]:
        return 1
    if counts["inconclusive"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
