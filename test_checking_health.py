from __future__ import annotations

import importlib.util
import io
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.error import URLError

import pytest


# Ajuste este caminho se o nome/local do script mudar.
TARGET_FILE = Path(__file__).resolve().parent / "Código colado.py"


@pytest.fixture(scope="module")
def healthcheck_module():
    """
    Carrega o script dinamicamente, já que o nome do arquivo contém espaço/acento
    e não é importável como módulo Python convencional.
    """
    if not TARGET_FILE.exists():
        pytest.fail(f"Arquivo alvo não encontrado: {TARGET_FILE}")

    spec = importlib.util.spec_from_file_location("healthcheck_module", TARGET_FILE)
    if spec is None or spec.loader is None:
        pytest.fail("Não foi possível criar spec para o módulo alvo.")

    module = importlib.util.module_from_spec(spec)
    sys.modules["healthcheck_module"] = module
    spec.loader.exec_module(module)
    return module


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


def test_normalize_url_adds_https_when_missing(healthcheck_module):
    assert healthcheck_module.normalize_url("google.com/health") == "https://google.com/health"


def test_normalize_url_keeps_scheme(healthcheck_module):
    assert healthcheck_module.normalize_url("http://google.com/health") == "http://google.com/health"


def test_extract_domain(healthcheck_module):
    assert (
        healthcheck_module.extract_domain("https://patient.b2b.kompa.com.br/healthcheck")
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
def test_extract_endpoint_type(healthcheck_module, url, expected):
    assert healthcheck_module.extract_endpoint_type(url) == expected


def test_extract_title_from_html(healthcheck_module):
    html = b"<html><head><title> Portal de Saude </title></head><body></body></html>"
    assert healthcheck_module.extract_title(html) == "Portal de Saude"


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
def test_format_size(healthcheck_module, size, expected):
    assert healthcheck_module.format_size(size) == expected


def test_perform_check_success_html(monkeypatch, healthcheck_module):
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

    monkeypatch.setattr(healthcheck_module.socket, "gethostbyname", fake_gethostbyname)
    monkeypatch.setattr(healthcheck_module.urllib.request, "urlopen", fake_urlopen)

    result = healthcheck_module.perform_check("google.com.br/healthcheck/status", timeout=3.0)

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


def test_perform_check_urlerror(monkeypatch, healthcheck_module):
    def fake_gethostbyname(domain):
        return "10.0.0.1"

    def fake_urlopen(request, timeout):
        raise URLError("temporary failure in name resolution")

    monkeypatch.setattr(healthcheck_module.socket, "gethostbyname", fake_gethostbyname)
    monkeypatch.setattr(healthcheck_module.urllib.request, "urlopen", fake_urlopen)

    result = healthcheck_module.perform_check("https://api.example.com/health", timeout=2.0)

    assert result.ok is False
    assert result.status_label == "FAIL"
    assert result.http_code is None
    assert result.content_type == "-"
    assert result.title is None
    assert result.download_size == 0
    assert "URLError" in result.error
    assert result.endpoint_type == "health"


def test_format_result_line_contains_expected_columns(monkeypatch, healthcheck_module):
    monkeypatch.setattr(healthcheck_module, "USE_COLOR", False)

    result = healthcheck_module.CheckResult(
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

    line = healthcheck_module.format_result_line(result)

    assert "healthcheck" in line
    assert "OK" in line
    assert "200" in line
    assert "patient.b2b.kompa.com.br" in line
    assert "203.0.113.10" in line
    assert "application/json" in line
    assert "512B" in line
    assert "23" in line
    assert "41" in line


def test_main_returns_zero_when_all_checks_pass(monkeypatch, tmp_path, capsys, healthcheck_module):
    endpoints_file = tmp_path / "endpoints.txt"
    endpoints_file.write_text("https://google.com.br/healthcheck\n", encoding="utf-8")

    def fake_parse_args():
        return SimpleNamespace(file=str(endpoints_file), timeout=5.0)

    fake_result = healthcheck_module.CheckResult(
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

    monkeypatch.setattr(healthcheck_module, "parse_args", fake_parse_args)
    monkeypatch.setattr(healthcheck_module, "perform_check", lambda url, timeout: fake_result)
    monkeypatch.setattr(healthcheck_module, "USE_COLOR", False)

    exit_code = healthcheck_module.main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "API HEALTHCHECK" in captured.out
    assert "DOMAIN" in captured.out
    assert "healthcheck" in captured.out
    assert "google.com.br" in captured.out
    assert "Success" in captured.out


def test_main_returns_one_when_file_has_no_valid_endpoints(monkeypatch, tmp_path, capsys, healthcheck_module):
    endpoints_file = tmp_path / "empty_endpoints.txt"
    endpoints_file.write_text("\n# comment only\n\n", encoding="utf-8")

    def fake_parse_args():
        return SimpleNamespace(file=str(endpoints_file), timeout=5.0)

    monkeypatch.setattr(healthcheck_module, "parse_args", fake_parse_args)
    monkeypatch.setattr(healthcheck_module, "USE_COLOR", False)

    exit_code = healthcheck_module.main()
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "No valid endpoints were found in the file." in captured.out
