#!/usr/bin/env python3
"""
HTTP/HTTPS endpoint healthcheck.

Usage:
    python healthcheck.py endpoints.txt
    python healthcheck.py endpoints.txt --timeout 5

Format of the file:
    https://patient.b2b.kompa.com.br/health
    https://api.exemplo.com/status
    api2.exemplo.com/health
"""

from __future__ import annotations

import argparse
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import List, Optional


# ANSI escape codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"


@dataclass
class CheckResult:
    url: str
    domain: str
    endpoint_type: str
    ip: str
    ok: bool
    status_label: str
    http_code: Optional[int]
    content_type: Optional[str]
    title: Optional[str]
    elapsed_ms: int
    request_time_ms: int
    download_size: int
    error: Optional[str] = None


def supports_ansi() -> bool:
    return sys.stdout.isatty()


USE_COLOR = supports_ansi()


def colorize(text: str, color: str) -> str:
    if not USE_COLOR:
        return text
    return f"{color}{text}{RESET}"


def bold(text: str) -> str:
    if not USE_COLOR:
        return text
    return f"{BOLD}{text}{RESET}"


def dim(text: str) -> str:
    if not USE_COLOR:
        return text
    return f"{DIM}{text}{RESET}"


def normalize_url(raw_url: str) -> str:
    raw_url = raw_url.strip()
    if not raw_url:
        return raw_url

    parsed = urllib.parse.urlparse(raw_url)
    if not parsed.scheme:
        raw_url = f"https://{raw_url}"

    return raw_url


def extract_domain(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    return parsed.hostname or parsed.netloc or url


def load_endpoints(file_path: str) -> List[str]:
    endpoints: List[str] = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            value = line.strip()
            if not value or value.startswith("#"):
                continue
            endpoints.append(value)

    return endpoints


def extract_endpoint_type(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.strip("/")

    if not path:
        return "root"

    parts = path.split("/")
    return parts[-1] if parts[-1] else parts[-2] if len(parts) > 1 else "root"


def extract_title(html_bytes: bytes) -> Optional[str]:
    try:
        snippet = html_bytes[:5000].decode("utf-8", errors="ignore")
        match = re.search(
            r"<title[^>]*>(.*?)</title>", snippet, re.IGNORECASE | re.DOTALL
        )
        if match:
            return " ".join(match.group(1).split()).strip()
    except Exception:
        pass
    return None


def perform_check(url: str, timeout: float) -> CheckResult:
    normalized_url = normalize_url(url)
    domain = extract_domain(normalized_url)
    endpoint_type = extract_endpoint_type(normalized_url)

    try:
        ip = socket.gethostbyname(domain)
    except Exception:
        ip = "-"

    request = urllib.request.Request(
        normalized_url,
        headers={
            "User-Agent": "HealthCheckUtility/1.0",
            "Accept": "*/*",
        },
        method="GET",
    )

    start_total = time.perf_counter()

    try:
        # Server response time
        start_request = time.perf_counter()
        with urllib.request.urlopen(request, timeout=timeout) as response:
            request_time_ms = int((time.perf_counter() - start_request) * 1000)

            http_code = response.getcode()
            content_type = response.headers.get("Content-Type", "-")

            # Reads the complete body for TIME to reflect the actual download
            body = response.read()
            download_size = len(body)

            title = None
            if content_type and "text/html" in content_type.lower():
                title = extract_title(body)

        # Total time of the operation, including download
        elapsed_ms = int((time.perf_counter() - start_total) * 1000)

        ok = 200 <= http_code < 400

        return CheckResult(
            url=normalized_url,
            domain=domain,
            endpoint_type=endpoint_type,
            ip=ip,
            ok=ok,
            status_label="OK" if ok else "FAIL",
            http_code=http_code,
            content_type=content_type,
            title=title,
            elapsed_ms=elapsed_ms,
            request_time_ms=request_time_ms,
            download_size=download_size,
            error=None if ok else f"HTTP {http_code}",
        )

    except urllib.error.HTTPError as exc:
        elapsed_ms = int((time.perf_counter() - start_total) * 1000)

        return CheckResult(
            url=normalized_url,
            domain=domain,
            endpoint_type=endpoint_type,
            ip=ip,
            ok=False,
            status_label="FAIL",
            http_code=exc.code,
            content_type=exc.headers.get("Content-Type", "-") if exc.headers else "-",
            title=None,
            elapsed_ms=elapsed_ms,
            request_time_ms=elapsed_ms,
            download_size=0,
            error=f"HTTPError: {exc.reason}",
        )

    except urllib.error.URLError as exc:
        elapsed_ms = int((time.perf_counter() - start_total) * 1000)

        return CheckResult(
            url=normalized_url,
            domain=domain,
            endpoint_type=endpoint_type,
            ip=ip,
            ok=False,
            status_label="FAIL",
            http_code=None,
            content_type="-",
            title=None,
            elapsed_ms=elapsed_ms,
            request_time_ms=elapsed_ms,
            download_size=0,
            error=f"URLError: {exc.reason}",
        )

    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - start_total) * 1000)

        return CheckResult(
            url=normalized_url,
            domain=domain,
            endpoint_type=endpoint_type,
            ip=ip,
            ok=False,
            status_label="FAIL",
            http_code=None,
            content_type="-",
            title=None,
            elapsed_ms=elapsed_ms,
            request_time_ms=elapsed_ms,
            download_size=0,
            error=f"{type(exc).__name__}: {exc}",
        )


def print_banner() -> None:
    print()
    print(bold(colorize("API HEALTHCHECK", CYAN)))
    print(dim("HTTP/HTTPS endpoint availability check"))
    print()


def print_header() -> None:
    header = (
        f"{'TYPE':<12} "
        f"{'STATUS':<8} "
        f"{'HTTP':<6} "
        f"{'DOMAIN':<40} "
        f"{'IP':<15} "
        f"{'CONTENT-TYPE':<20} "
        f"{'SIZE':>8} "
        f"{'REQ(ms)':>8} "
        f"{'TIME(ms)':>9} "
        f"{'TITLE':<25}"
    )

    print(bold(header))
    print(dim("-" * len(header)))


def format_http_code(code: Optional[int]) -> str:
    return str(code) if code is not None else "-"


def format_size(size: int) -> str:
    if size < 1024:
        return f"{size}B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f}KB"
    return f"{size / (1024 * 1024):.1f}MB"


def format_result_line(result: CheckResult) -> str:
    line = (
        f"{result.endpoint_type:<12} "
        f"{result.status_label:<8} "
        f"{format_http_code(result.http_code):<6} "
        f"{result.domain:<40.40} "
        f"{result.ip:<15} "
        f"{(result.content_type or '-')[:20]:<20} "
        f"{format_size(result.download_size):>8} "
        f"{str(result.request_time_ms):>8} "
        f"{str(result.elapsed_ms):>9} "
        f"{(result.title or '-')[:25]:<25}"
    )

    return colorize(line, GREEN if result.ok else RED)


def print_summary(results: List[CheckResult]) -> None:
    total = len(results)
    ok_count = sum(1 for item in results if item.ok)
    fail_count = total - ok_count

    avg_req = int(sum(item.request_time_ms for item in results) / total) if total else 0
    avg_total = int(sum(item.elapsed_ms for item in results) / total) if total else 0

    print()
    print(bold("Resumo"))
    print(dim("-" * 30))
    print(f"Total        : {total}")
    print(
        colorize(f"Success      : {ok_count}", GREEN)
        if ok_count
        else f"Success      : {ok_count}"
    )
    print(
        colorize(f"Failure      : {fail_count}", RED)
        if fail_count
        else f"Failure      : {fail_count}"
    )
    print(f"REQ average  : {avg_req}ms")
    print(f"TIME average : {avg_total}ms")
    print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Performs a health check on a list of HTTP/HTTPS endpoints."
    )
    parser.add_argument(
        "file",
        help="Text file containing one URL per line.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Timeout per request in seconds. Default: 5.0",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        endpoints = load_endpoints(args.file)
    except FileNotFoundError:
        print(colorize(f"File not found: {args.file}", RED), file=sys.stderr)
        return 1
    except Exception as exc:
        print(colorize(f"Error reading file: {exc}", RED), file=sys.stderr)
        return 1

    if not endpoints:
        print(colorize("No valid endpoints were found in the file.", YELLOW))
        return 1

    print_banner()
    print_header()

    results: List[CheckResult] = []

    # Displays each result as soon as the request finishes.
    for endpoint in endpoints:
        result = perform_check(endpoint, timeout=args.timeout)
        results.append(result)
        print(format_result_line(result), flush=True)

    print_summary(results)

    return 0 if all(item.ok for item in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
