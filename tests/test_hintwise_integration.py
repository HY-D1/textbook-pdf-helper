"""
Integration tests for the HintWise integration service layer
(hintwise_service.py) and the mocked end-to-end roundtrip.

All tests are offline and deterministic — no real HTTP calls are made.
"""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from algl_pdf_helper.hintwise_adapter import (
    get_example_payload,
    get_minimal_payload,
    make_hintwise_payload,
)
from algl_pdf_helper.hintwise_client import HintwiseClient, HintwiseResult
from algl_pdf_helper.hintwise_service import (
    DEFAULT_RESULTS_FILENAME,
    HintwiseService,
    _build_record,
    load_results,
    request_hint,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_response(status: int, body: dict) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.read.return_value = json.dumps(body).encode("utf-8")
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _online_client(base_url: str = "http://hintwise.test") -> HintwiseClient:
    return HintwiseClient(base_url=base_url, endpoint="/api/hint", timeout=5)


def _offline_client() -> HintwiseClient:
    return HintwiseClient(base_url="")


_EXAMPLE_UNIT: dict = {
    "concept_id": "select-basic",
    "title": "SELECT Statement Basics",
    "unit_id": "unit_select_001",
    "unit_type": "explanation",
    "supports_hintwise": True,
    "supports_replay": True,
    "source_pdf": "murach_sql_2015.pdf",
    "source_pages": [45, 46],
    "extraction_method": "marker",
    "llm_provider": "ollama",
    "llm_model": "qwen3.5:9b-q8_0",
    # No backbone_sources — treated as a unit from concept_units.json,
    # so make_hintwise_payload captures source_pdf/source_pages.
    "error_subtypes": ["missing_comma_in_select"],
    "prerequisites": [],
    "practice_problem_ids": ["prob_001"],
}

# Backbone variant for tests that need backbone_sources populated
_BACKBONE_UNIT: dict = {
    **_EXAMPLE_UNIT,
    "backbone_sources": ["sql_ontology"],
}


# ---------------------------------------------------------------------------
# _build_record
# ---------------------------------------------------------------------------


class TestBuildRecord:
    def test_record_has_required_keys(self):
        payload = make_hintwise_payload(_EXAMPLE_UNIT)
        result = HintwiseResult(
            online=False,
            concept_id="select-basic",
            requested_at="2026-01-01T00:00:00+00:00",
        )
        record = _build_record(result, payload)

        assert "schema_version" in record
        assert "recorded_at" in record
        assert "request" in record
        assert "response" in record
        assert "provenance" in record
        assert "requested_at" in record

    def test_record_request_fields(self):
        payload = make_hintwise_payload(
            _EXAMPLE_UNIT,
            learner_context={"escalation_level": "L2", "learner_id": "u42"},
        )
        result = HintwiseResult(
            online=False,
            concept_id="select-basic",
            requested_at="2026-01-01T00:00:00+00:00",
        )
        record = _build_record(result, payload)

        req = record["request"]
        assert req["concept_id"] == "select-basic"
        assert req["unit_id"] == "unit_select_001"
        assert req["escalation_level"] == "L2"
        assert req["learner_id"] == "u42"

    def test_record_response_fields(self):
        payload = make_hintwise_payload(_EXAMPLE_UNIT)
        result = HintwiseResult(
            online=True,
            concept_id="select-basic",
            status_code=200,
            hint_id="h_123",
            hint_content="Use aliases for clarity.",
            endpoint_url="http://hw/api/hint",
            requested_at="2026-01-01T00:00:00+00:00",
        )
        record = _build_record(result, payload)

        resp = record["response"]
        assert resp["online"] is True
        assert resp["status_code"] == 200
        assert resp["hint_id"] == "h_123"
        assert resp["hint_content"] == "Use aliases for clarity."

    def test_record_provenance_from_result(self):
        payload = make_hintwise_payload(_EXAMPLE_UNIT)
        result = HintwiseResult(
            online=False,
            concept_id="select-basic",
            requested_at="2026-01-01T00:00:00+00:00",
            provenance={
                "source_pdf": "murach_sql_2015.pdf",
                "source_pages": [45, 46],
                "backbone_sources": [],
            },
        )
        record = _build_record(result, payload)

        prov = record["provenance"]
        assert prov["source_pdf"] == "murach_sql_2015.pdf"
        assert prov["source_pages"] == [45, 46]


# ---------------------------------------------------------------------------
# HintwiseService - offline
# ---------------------------------------------------------------------------


class TestHintwiseServiceOffline:
    def test_request_offline_no_save(self):
        svc = HintwiseService(client=_offline_client(), output_path=None)
        result = svc.request(_EXAMPLE_UNIT)

        assert result.online is False
        assert result.concept_id == "select-basic"

    def test_request_offline_no_file_created(self, tmp_path: Path):
        out = tmp_path / "results.jsonl"
        svc = HintwiseService(client=_offline_client(), output_path=out)
        # save=False so file is not created
        svc.request(_EXAMPLE_UNIT, save=False)

        assert not out.exists()

    def test_request_offline_saves_record(self, tmp_path: Path):
        out = tmp_path / DEFAULT_RESULTS_FILENAME
        svc = HintwiseService(client=_offline_client(), output_path=out)
        svc.request(_EXAMPLE_UNIT, save=True)

        assert out.exists()
        records = load_results(out)
        assert len(records) == 1
        assert records[0]["request"]["concept_id"] == "select-basic"
        assert records[0]["response"]["online"] is False

    def test_multiple_requests_append_lines(self, tmp_path: Path):
        out = tmp_path / DEFAULT_RESULTS_FILENAME
        svc = HintwiseService(client=_offline_client(), output_path=out)
        svc.request(_EXAMPLE_UNIT)
        svc.request({**_EXAMPLE_UNIT, "concept_id": "where-clause"})

        records = load_results(out)
        assert len(records) == 2
        concept_ids = {r["request"]["concept_id"] for r in records}
        assert concept_ids == {"select-basic", "where-clause"}


# ---------------------------------------------------------------------------
# HintwiseService - mocked online call
# ---------------------------------------------------------------------------


class TestHintwiseServiceOnline:
    def test_successful_call_result(self):
        client = _online_client()
        svc = HintwiseService(client=client)
        mock_resp = _make_mock_response(200, {"hint_id": "h42", "hint_content": "tip"})

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = svc.request(_EXAMPLE_UNIT)

        assert result.succeeded()
        assert result.hint_id == "h42"
        assert result.hint_content == "tip"

    def test_successful_call_saves_record(self, tmp_path: Path):
        out = tmp_path / DEFAULT_RESULTS_FILENAME
        client = _online_client()
        svc = HintwiseService(client=client, output_path=out)
        mock_resp = _make_mock_response(200, {"hint_id": "h77", "hint_content": "hello"})

        with patch("urllib.request.urlopen", return_value=mock_resp):
            svc.request(_EXAMPLE_UNIT)

        records = load_results(out)
        assert len(records) == 1
        assert records[0]["response"]["hint_id"] == "h77"
        assert records[0]["response"]["hint_content"] == "hello"

    def test_error_result_saved(self, tmp_path: Path):
        out = tmp_path / DEFAULT_RESULTS_FILENAME
        client = _online_client()
        svc = HintwiseService(client=client, output_path=out)

        with patch("urllib.request.urlopen", side_effect=OSError("refused")):
            result = svc.request(_EXAMPLE_UNIT)

        assert result.error is not None
        records = load_results(out)
        assert records[0]["response"]["error"] is not None

    def test_learner_context_threaded_into_record(self, tmp_path: Path):
        out = tmp_path / DEFAULT_RESULTS_FILENAME
        client = _online_client()
        svc = HintwiseService(client=client, output_path=out)
        mock_resp = _make_mock_response(200, {})

        with patch("urllib.request.urlopen", return_value=mock_resp):
            svc.request(
                _EXAMPLE_UNIT,
                learner_context={"learner_id": "lrn_99", "problem_id": "p11", "escalation_level": "L3"},
            )

        records = load_results(out)
        req = records[0]["request"]
        assert req["learner_id"] == "lrn_99"
        assert req["problem_id"] == "p11"
        assert req["escalation_level"] == "L3"


# ---------------------------------------------------------------------------
# request_hint (stateless helper)
# ---------------------------------------------------------------------------


class TestRequestHint:
    def test_offline_no_save(self, monkeypatch):
        monkeypatch.delenv("HINTWISE_BASE_URL", raising=False)
        result = request_hint(_EXAMPLE_UNIT)
        assert result.online is False

    def test_offline_saves_to_path(self, tmp_path: Path, monkeypatch):
        monkeypatch.delenv("HINTWISE_BASE_URL", raising=False)
        out = tmp_path / "results.jsonl"
        request_hint(_EXAMPLE_UNIT, output_path=out)
        assert out.exists()
        records = load_results(out)
        assert len(records) == 1

    def test_online_mocked(self, monkeypatch):
        monkeypatch.setenv("HINTWISE_BASE_URL", "http://hw.test")
        mock_resp = _make_mock_response(200, {"hint_id": "h_stateless"})

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = request_hint(_EXAMPLE_UNIT)

        assert result.succeeded()
        assert result.hint_id == "h_stateless"


# ---------------------------------------------------------------------------
# load_results
# ---------------------------------------------------------------------------


class TestLoadResults:
    def test_load_empty_file(self, tmp_path: Path):
        f = tmp_path / "empty.jsonl"
        f.write_text("", encoding="utf-8")
        assert load_results(f) == []

    def test_load_missing_file(self, tmp_path: Path):
        assert load_results(tmp_path / "nonexistent.jsonl") == []

    def test_load_single_record(self, tmp_path: Path):
        f = tmp_path / "results.jsonl"
        f.write_text(json.dumps({"concept_id": "x"}) + "\n", encoding="utf-8")
        records = load_results(f)
        assert len(records) == 1
        assert records[0]["concept_id"] == "x"

    def test_load_multiple_records(self, tmp_path: Path):
        f = tmp_path / "results.jsonl"
        lines = [json.dumps({"n": i}) for i in range(5)]
        f.write_text("\n".join(lines) + "\n", encoding="utf-8")
        records = load_results(f)
        assert len(records) == 5

    def test_skips_malformed_line(self, tmp_path: Path):
        f = tmp_path / "results.jsonl"
        f.write_text(
            json.dumps({"ok": True}) + "\n" + "NOT JSON\n" + json.dumps({"ok": True}) + "\n",
            encoding="utf-8",
        )
        records = load_results(f)
        assert len(records) == 2  # malformed line skipped silently


# ---------------------------------------------------------------------------
# Full mocked end-to-end roundtrip
# ---------------------------------------------------------------------------


class TestMockedEndToEnd:
    """
    Simulates the complete path:
    concept_unit → payload → HTTP POST → normalized result → JSONL artifact
    """

    def test_end_to_end_roundtrip(self, tmp_path: Path):
        out = tmp_path / "hintwise-results.jsonl"
        client = HintwiseClient(
            base_url="http://hintwise-stub.test",
            endpoint="/api/hint",
            api_key="test-key",
            timeout=5,
        )
        svc = HintwiseService(client=client, output_path=out)

        response_body = {
            "hint_id": "stub_hint_001",
            "hint_content": "Remember: SELECT lists columns separated by commas.",
        }
        mock_resp = _make_mock_response(200, response_body)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = svc.request(
                _EXAMPLE_UNIT,
                learner_context={
                    "learner_id": "learner_e2e",
                    "problem_id": "select-prob-01",
                    "escalation_level": "L2",
                },
            )

        # Result assertions
        assert result.succeeded()
        assert result.hint_id == "stub_hint_001"
        assert "SELECT" in result.hint_content

        # Artifact assertions
        assert out.exists()
        records = load_results(out)
        assert len(records) == 1

        rec = records[0]
        assert rec["schema_version"] == "1.0.0"
        assert rec["request"]["concept_id"] == "select-basic"
        assert rec["request"]["learner_id"] == "learner_e2e"
        assert rec["request"]["escalation_level"] == "L2"
        assert rec["response"]["hint_id"] == "stub_hint_001"
        # _EXAMPLE_UNIT has no backbone_sources, so source_pdf is captured in provenance
        assert rec["provenance"]["source_pdf"] == "murach_sql_2015.pdf"
        assert 45 in rec["provenance"]["source_pages"]
