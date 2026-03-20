"""
Unit tests for hintwise_client.py.

All tests are offline and deterministic — no real HTTP calls are made.
Network interactions are intercepted via monkeypatching urllib.request.urlopen.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from algl_pdf_helper.hintwise_adapter import (
    HintwisePayload,
    get_example_payload,
    get_minimal_payload,
)
from algl_pdf_helper.hintwise_client import (
    HintwiseClient,
    HintwiseResult,
    _get_config,
    call_hintwise,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_response(status: int, body: dict) -> MagicMock:
    """Return a mock object that acts like an http.client.HTTPResponse."""
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.read.return_value = json.dumps(body).encode("utf-8")
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _make_client(base_url: str = "http://hintwise.test") -> HintwiseClient:
    return HintwiseClient(base_url=base_url, endpoint="/api/hint", timeout=5)


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


class TestConfig:
    def test_offline_when_no_base_url(self, monkeypatch):
        monkeypatch.delenv("HINTWISE_BASE_URL", raising=False)
        cfg = _get_config()
        assert cfg["online"] is False
        assert cfg["base_url"] == ""

    def test_online_when_base_url_set(self, monkeypatch):
        monkeypatch.setenv("HINTWISE_BASE_URL", "http://localhost:8080")
        cfg = _get_config()
        assert cfg["online"] is True
        assert cfg["base_url"] == "http://localhost:8080"

    def test_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("HINTWISE_API_KEY", "secret-key")
        monkeypatch.setenv("HINTWISE_BASE_URL", "http://x")
        cfg = _get_config()
        assert cfg["api_key"] == "secret-key"

    def test_timeout_default(self, monkeypatch):
        monkeypatch.delenv("HINTWISE_TIMEOUT", raising=False)
        cfg = _get_config()
        assert cfg["timeout"] == 10

    def test_timeout_from_env(self, monkeypatch):
        monkeypatch.setenv("HINTWISE_TIMEOUT", "30")
        cfg = _get_config()
        assert cfg["timeout"] == 30


# ---------------------------------------------------------------------------
# Client construction
# ---------------------------------------------------------------------------


class TestClientConstruction:
    def test_from_env_offline(self, monkeypatch):
        monkeypatch.delenv("HINTWISE_BASE_URL", raising=False)
        client = HintwiseClient.from_env()
        assert not client.is_configured

    def test_from_env_online(self, monkeypatch):
        monkeypatch.setenv("HINTWISE_BASE_URL", "http://hw.example.com")
        client = HintwiseClient.from_env()
        assert client.is_configured
        assert client.base_url == "http://hw.example.com"

    def test_trailing_slash_stripped(self):
        client = HintwiseClient(base_url="http://hw.example.com/")
        assert client.base_url == "http://hw.example.com"

    def test_build_url(self):
        client = HintwiseClient(base_url="http://hw.example.com", endpoint="/api/hint")
        assert client._build_url() == "http://hw.example.com/api/hint"

    def test_headers_without_api_key(self):
        client = HintwiseClient(base_url="http://x", api_key="")
        headers = client._build_headers()
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers

    def test_headers_with_api_key(self):
        client = HintwiseClient(base_url="http://x", api_key="tok123")
        headers = client._build_headers()
        assert headers["Authorization"] == "Bearer tok123"


# ---------------------------------------------------------------------------
# Offline mode
# ---------------------------------------------------------------------------


class TestOfflineMode:
    def test_call_returns_offline_result_when_not_configured(self):
        client = HintwiseClient(base_url="")
        payload = get_minimal_payload()
        result = client.call(payload)

        assert result.online is False
        assert result.status_code is None
        assert result.error is None
        assert result.concept_id == "select-basic"

    def test_offline_result_is_not_succeeded(self):
        client = HintwiseClient(base_url="")
        result = client.call(get_minimal_payload())
        assert not result.succeeded()

    def test_convenience_function_offline(self, monkeypatch):
        monkeypatch.delenv("HINTWISE_BASE_URL", raising=False)
        result = call_hintwise(get_example_payload())
        assert result.online is False


# ---------------------------------------------------------------------------
# Successful HTTP call
# ---------------------------------------------------------------------------


class TestSuccessfulCall:
    def test_200_response_parsed_correctly(self):
        client = _make_client()
        payload = get_example_payload()
        response_body = {
            "hint_id": "hint_abc",
            "hint_content": "Use SELECT * carefully.",
        }
        mock_resp = _make_mock_response(200, response_body)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = client.call(payload)

        assert result.online is True
        assert result.status_code == 200
        assert result.hint_id == "hint_abc"
        assert result.hint_content == "Use SELECT * carefully."
        assert result.error is None
        assert result.succeeded()

    def test_result_echo_fields(self):
        client = _make_client()
        payload = get_example_payload()
        mock_resp = _make_mock_response(200, {"hint_id": "h1"})

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = client.call(payload)

        assert result.concept_id == payload.concept_context.concept_id
        assert result.escalation_level == payload.learner_context.escalation_level
        assert result.endpoint_url == "http://hintwise.test/api/hint"

    def test_provenance_forwarded(self):
        client = _make_client()
        payload = get_example_payload()
        mock_resp = _make_mock_response(200, {})

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = client.call(payload)

        assert result.provenance["source_pdf"] == payload.provenance.source_pdf
        assert result.provenance["source_pages"] == payload.provenance.source_pages

    def test_content_alias_used(self):
        """hint_content falls back to 'content' key if 'hint_content' is absent."""
        client = _make_client()
        payload = get_minimal_payload()
        mock_resp = _make_mock_response(200, {"content": "Hint text here."})

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = client.call(payload)

        assert result.hint_content == "Hint text here."


# ---------------------------------------------------------------------------
# HTTP error responses
# ---------------------------------------------------------------------------


class TestHTTPErrors:
    def _make_http_error(self, code: int, reason: str, body: bytes = b"{}") -> urllib.error.HTTPError:
        return urllib.error.HTTPError(
            url="http://hintwise.test/api/hint",
            code=code,
            msg=reason,
            hdrs=None,  # type: ignore[arg-type]
            fp=BytesIO(body),
        )

    def test_404_returns_error_result(self):
        client = _make_client()
        exc = self._make_http_error(404, "Not Found")

        with patch("urllib.request.urlopen", side_effect=exc):
            result = client.call(get_minimal_payload())

        assert result.online is True
        assert result.status_code == 404
        assert result.error is not None
        assert "404" in result.error
        assert not result.succeeded()

    def test_500_returns_error_result(self):
        client = _make_client()
        exc = self._make_http_error(500, "Internal Server Error")

        with patch("urllib.request.urlopen", side_effect=exc):
            result = client.call(get_minimal_payload())

        assert result.status_code == 500
        assert "500" in result.error

    def test_http_error_body_parsed(self):
        client = _make_client()
        body = json.dumps({"message": "invalid concept"}).encode()
        exc = self._make_http_error(422, "Unprocessable", body)

        with patch("urllib.request.urlopen", side_effect=exc):
            result = client.call(get_minimal_payload())

        assert result.raw_response == {"message": "invalid concept"}


# ---------------------------------------------------------------------------
# Network / connection errors (retry logic)
# ---------------------------------------------------------------------------


class TestConnectionErrors:
    def test_connection_error_returns_error_result(self):
        client = _make_client()

        with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
            result = client.call(get_minimal_payload())

        assert result.online is True
        assert result.error is not None
        assert "Connection error" in result.error
        assert not result.succeeded()

    def test_retry_succeeds_on_second_attempt(self):
        """First call raises OSError, second attempt returns 200."""
        client = _make_client()
        mock_resp = _make_mock_response(200, {"hint_id": "h_retry"})

        call_count = {"n": 0}

        def side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise OSError("temporary failure")
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=side_effect):
            result = client.call(get_minimal_payload())

        assert result.status_code == 200
        assert result.hint_id == "h_retry"
        assert call_count["n"] == 2  # was retried exactly once

    def test_url_error_retried(self):
        client = _make_client()
        url_err = urllib.error.URLError("name resolution failed")

        with patch("urllib.request.urlopen", side_effect=url_err):
            result = client.call(get_minimal_payload())

        assert result.error is not None


# ---------------------------------------------------------------------------
# Request serialization
# ---------------------------------------------------------------------------


class TestRequestSerialization:
    def test_request_body_is_valid_json(self):
        client = _make_client()
        payload = get_example_payload()
        captured_body: list[bytes] = []

        def fake_urlopen(req, timeout=None):
            captured_body.append(req.data)
            return _make_mock_response(200, {})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            client.call(payload)

        assert len(captured_body) == 1
        parsed = json.loads(captured_body[0])
        assert parsed["schema_version"] == "1.0.0"
        assert parsed["concept_context"]["concept_id"] == "select-basic"

    def test_request_uses_post_method(self):
        client = _make_client()
        captured_req: list[urllib.request.Request] = []

        def fake_urlopen(req, timeout=None):
            captured_req.append(req)
            return _make_mock_response(200, {})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            client.call(get_minimal_payload())

        assert captured_req[0].method == "POST"

    def test_request_includes_content_type_header(self):
        client = _make_client()
        captured_req: list[urllib.request.Request] = []

        def fake_urlopen(req, timeout=None):
            captured_req.append(req)
            return _make_mock_response(200, {})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            client.call(get_minimal_payload())

        assert captured_req[0].get_header("Content-type") == "application/json"

    def test_api_key_in_authorization_header(self):
        client = HintwiseClient(base_url="http://x", api_key="tok_test", timeout=5)
        captured_req: list[urllib.request.Request] = []

        def fake_urlopen(req, timeout=None):
            captured_req.append(req)
            return _make_mock_response(200, {})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            client.call(get_minimal_payload())

        assert captured_req[0].get_header("Authorization") == "Bearer tok_test"


# ---------------------------------------------------------------------------
# HintwiseResult model
# ---------------------------------------------------------------------------


class TestHintwiseResult:
    def test_succeeded_true_on_200(self):
        r = HintwiseResult(online=True, status_code=200)
        assert r.succeeded()

    def test_succeeded_false_on_offline(self):
        r = HintwiseResult(online=False, status_code=None)
        assert not r.succeeded()

    def test_succeeded_false_on_500(self):
        r = HintwiseResult(online=True, status_code=500)
        assert not r.succeeded()

    def test_to_dict_structure(self):
        r = HintwiseResult(
            online=True,
            concept_id="select-basic",
            status_code=200,
            hint_id="h1",
            hint_content="Remember to use aliases.",
            requested_at="2026-01-01T00:00:00+00:00",
        )
        d = r.to_dict()
        assert d["online"] is True
        assert d["concept_id"] == "select-basic"
        assert d["hint_id"] == "h1"
        assert d["hint_content"] == "Remember to use aliases."
