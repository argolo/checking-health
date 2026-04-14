from types import SimpleNamespace
from urllib.error import URLError

import pytest

import checking_health


class FakeResponse:
    def __init__(self, code=200, content_type="text/html; charset=utf-8", body=b""):
        self._code = code
        self.headers = {"Content-Type": content_type}
        self._body = body

    def getcode(self):
        return self._code

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_normalize_url_adds_https_when_missing():
    assert checking_health.normalize_url("google.com/health") == "https://google.com/health"


def test_normalize_url_keeps_existing_scheme():
    assert checking_health.normalize_url("http://google.com/health") == "http://google.com/health"


def test_extract_domain():
    assert (
        checking_health.extract_domain("https://patient.b2b.kompa.com.br/healthcheck")
        == "patient.b2b.kompa.com.br"
    )


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://google.com.br/healthcheck", "healthcheck"),
        ("https://google.com.br/healthcheck/status", "status"),
        ("https://google.com.br/", "root"),
        ("https://google.com.br", "root"),
    ],
)
def test_extract_endpoint_type(url, expected):
    assert checking_health.extract_endpoint_type(url) == expected


def test_extract_title_from_html():
    html = b"<html><head><title> Portal Status </title></head><body></body></html>"
    assert checking_health.extract_title(html) == "Portal Status"


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        (0, "0B"),
        (512, "512B"),
        (1024, "1.0KB"),
        (1536, "1.5KB"),
        (1024 * 1024, "1.0MB"),
    ],
)
def test_format_size(size, expected):
    assert checking_health.format_size(size) == expected


def test_perform_check_success_html(monkeypatch):
    body = b"<html><head><title>Health Status</title></head><body>ok</body></html>"

    def fake_gethostbyname(domain):
        assert domain == "google.com.br"
        return "142.250.0.1"

    def fake_urlopen(request, timeout):
        assert request.full_url == "https://google.com.br/healthcheck/status"
        assert timeout == 3.0
        return FakeResponse(
            code=200,
            content_type="text/html; charset=utf-8",
            body=body,
        )

    monkeypatch.setattr(checking_health.socket, "gethostbyname", fake_gethostbyname)
    monkeypatch.setattr(checking_health.urllib.request, "urlopen", fake_urlopen)

    result = checking_health.perform_check("google.com.br/healthcheck/status", timeout=3.0)

    assert result.ok is True
    assert result.status_label == "OK"
    assert result.http_code == 200
    assert result.domain == "google.com.br"
    assert result.endpoint_type == "status"
    assert result.ip == "142.250.0.1"
    assert result.content_type == "text/html; charset=utf-8"
    assert result.title == "Health Status"
    assert result.download_size == len(body)
    assert result.request_time_ms >= 0
    assert result.elapsed_ms >= result.request_time_ms


def test_perform_check_urlerror(monkeypatch):
    def fake_gethostbyname(domain):
        return "10.0.0.1"

    def fake_urlopen(request, timeout):
        raise URLError("temporary failure in name resolution")

    monkeypatch.setattr(checking_health.socket, "gethostbyname", fake_gethostbyname)
    monkeypatch.setattr(checking_health.urllib.request, "urlopen", fake_urlopen)

    result = checking_health.perform_check("https://api.example.com/health", timeout=2.0)

    assert result.ok is False
    assert result.status_label == "FAIL"
    assert result.http_code is None
    assert result.content_type == "-"
    assert result.title is None
    assert result.download_size == 0
    assert "URLError" in result.error
    assert result.endpoint_type == "health"


def test_format_result_line_contains_expected_columns(monkeypatch):
    monkeypatch.setattr(checking_health, "USE_COLOR", False)

    result = checking_health.CheckResult(
        url="https://patient.b2b.kompa.com.br/healthcheck",
        domain="patient.b2b.kompa.com.br",
        endpoint_type="healthcheck",
        ip="203.0.113.10",
        ok=True,
        status_label="OK",
        http_code=200,
        content_type="application/json",
        title=None,
        elapsed_ms=41,
        request_time_ms=23,
        download_size=512,
        error=None,
    )

    line = checking_health.format_result_line(result)

    assert "healthcheck" in line
    assert "OK" in line
    assert "200" in line
    assert "patient.b2b.kompa.com.br" in line
    assert "203.0.113.10" in line
    assert "application/json" in line
    assert "512B" in line


def test_main_returns_zero_when_all_checks_pass(monkeypatch, tmp_path, capsys):
    endpoints_file = tmp_path / "endpoints.txt"
    endpoints_file.write_text("https://google.com.br/healthcheck\n", encoding="utf-8")

    def fake_parse_args():
        return SimpleNamespace(file=str(endpoints_file), timeout=5.0)

    fake_result = checking_health.CheckResult(
        url="https://google.com.br/healthcheck",
        domain="google.com.br",
        endpoint_type="healthcheck",
        ip="142.250.0.1",
        ok=True,
        status_label="OK",
        http_code=200,
        content_type="text/html",
        title="Google",
        elapsed_ms=30,
        request_time_ms=20,
        download_size=1024,
        error=None,
    )

    monkeypatch.setattr(checking_health, "parse_args", fake_parse_args)
    monkeypatch.setattr(checking_health, "perform_check", lambda url, timeout: fake_result)
    monkeypatch.setattr(checking_health, "USE_COLOR", False)

    exit_code = checking_health.main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "CHECKING HEALTH" in captured.out
    assert "DOMAIN" in captured.out
    assert "healthcheck" in captured.out
    assert "google.com.br" in captured.out
    assert "Success" in captured.out


def test_main_returns_one_when_file_has_no_valid_endpoints(monkeypatch, tmp_path, capsys):
    endpoints_file = tmp_path / "empty_endpoints.txt"
    endpoints_file.write_text("\n# comment only\n\n", encoding="utf-8")

    def fake_parse_args():
        return SimpleNamespace(file=str(endpoints_file), timeout=5.0)

    monkeypatch.setattr(checking_health, "parse_args", fake_parse_args)
    monkeypatch.setattr(checking_health, "USE_COLOR", False)

    exit_code = checking_health.main()
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "No valid endpoints were found in the file." in captured.out
