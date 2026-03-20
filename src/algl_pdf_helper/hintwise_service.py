"""
HintWise Integration Service Layer.

Bridges helper artifacts (concept units, backbone concepts) with the live
HintWise HTTP endpoint. Handles the full roundtrip:

    concept/unit + learner context
        → HintwisePayload  (via hintwise_adapter)
        → HTTP call        (via hintwise_client)
        → HintwiseResult   (normalized)
        → persisted artifact (hintwise-results.jsonl)

All IO is optional; callers can skip saving if they just want the result.

Usage
-----
    from algl_pdf_helper.hintwise_service import request_hint, HintwiseService

    # Stateless one-shot
    result = request_hint(concept_unit, learner_context={"learner_id": "abc"})

    # Stateful (shared client + output file)
    svc = HintwiseService(output_path=Path("hintwise-results.jsonl"))
    result = svc.request(concept_unit, learner_context={"escalation_level": "L2"})
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from algl_pdf_helper.hintwise_adapter import HintwisePayload, make_hintwise_payload
from algl_pdf_helper.hintwise_client import HintwiseClient, HintwiseResult, call_hintwise

logger = logging.getLogger(__name__)

# Default artifact filename written to output directories
DEFAULT_RESULTS_FILENAME = "hintwise-results.jsonl"


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------


class HintwiseService:
    """
    Stateful HintWise integration service.

    Shares a single HintwiseClient across calls and appends results to an
    output JSONL file if ``output_path`` is provided.
    """

    def __init__(
        self,
        client: HintwiseClient | None = None,
        output_path: Path | None = None,
    ) -> None:
        self.client = client or HintwiseClient.from_env()
        self.output_path = output_path

    def request(
        self,
        unit_or_concept: dict[str, Any],
        learner_context: dict[str, Any] | None = None,
        save: bool = True,
    ) -> HintwiseResult:
        """
        Build a payload, call the endpoint, and optionally save the result.

        Parameters
        ----------
        unit_or_concept:
            Concept unit dict (from concept_units.json) or backbone concept dict.
        learner_context:
            Optional learner/session context overrides (learner_id, problem_id,
            escalation_level, previous_hint_ids, current_error_subtype).
        save:
            If True and ``output_path`` is set, append the result to the JSONL file.

        Returns
        -------
        HintwiseResult
        """
        payload = make_hintwise_payload(unit_or_concept, learner_context=learner_context)
        result = self.client.call(payload)

        if save and self.output_path is not None:
            self._append_result(result, payload)

        return result

    def _append_result(self, result: HintwiseResult, payload: HintwisePayload) -> None:
        """Append one line to the JSONL artifact file."""
        record = _build_record(result, payload)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
        logger.debug("HintWise result saved to %s", self.output_path)


# ---------------------------------------------------------------------------
# Stateless convenience helpers
# ---------------------------------------------------------------------------


def request_hint(
    unit_or_concept: dict[str, Any],
    learner_context: dict[str, Any] | None = None,
    output_path: Path | None = None,
) -> HintwiseResult:
    """
    One-shot helper: build payload → call endpoint → optionally persist result.

    Uses a fresh ``HintwiseClient`` configured from environment variables.
    """
    payload = make_hintwise_payload(unit_or_concept, learner_context=learner_context)
    result = call_hintwise(payload)

    if output_path is not None:
        record = _build_record(result, payload)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

    return result


def load_results(path: Path) -> list[dict[str, Any]]:
    """Load all records from a hintwise-results.jsonl file."""
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("Skipping malformed JSONL line in %s", path)
    return records


# ---------------------------------------------------------------------------
# Record builder (shared by service and stateless helper)
# ---------------------------------------------------------------------------


def _build_record(result: HintwiseResult, payload: HintwisePayload) -> dict[str, Any]:
    """
    Build a persisted record that links the result back to its request context.

    Schema
    ------
    {
        "schema_version": "1.0.0",
        "recorded_at": "<ISO8601>",
        "request": {
            "concept_id": ...,
            "unit_id": ...,
            "escalation_level": ...,
            "learner_id": ...,
            "problem_id": ...,
            "payload_schema_version": ...
        },
        "response": {
            "online": ...,
            "status_code": ...,
            "hint_id": ...,
            "hint_content": ...,
            "error": ...,
            "endpoint_url": ...
        },
        "provenance": {
            "source_pdf": ...,
            "source_pages": [...],
            "backbone_sources": [...]
        },
        "requested_at": ...
    }
    """
    return {
        "schema_version": "1.0.0",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "request": {
            "concept_id": payload.concept_context.concept_id,
            "unit_id": payload.concept_context.unit_id,
            "escalation_level": payload.learner_context.escalation_level,
            "learner_id": payload.learner_context.learner_id,
            "problem_id": payload.learner_context.problem_id,
            "payload_schema_version": payload.schema_version,
        },
        "response": {
            "online": result.online,
            "status_code": result.status_code,
            "hint_id": result.hint_id,
            "hint_content": result.hint_content,
            "error": result.error,
            "endpoint_url": result.endpoint_url,
        },
        "provenance": result.provenance,
        "requested_at": result.requested_at,
    }
