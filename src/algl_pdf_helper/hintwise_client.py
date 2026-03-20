"""
HintWise HTTP Client - Live Integration Layer.

Sends HintwisePayload to a configured HTTP endpoint and returns a normalized
HintwiseResult. All configuration is via environment variables so offline /
local-only operation works without any changes.

Environment variables
---------------------
HINTWISE_BASE_URL   Base URL of the HintWise service, e.g. http://localhost:8080
                    If unset, the client operates in *offline mode* (no HTTP call).
HINTWISE_ENDPOINT   Path appended to base URL (default: /api/hint)
HINTWISE_API_KEY    Bearer token sent as Authorization header (optional)
HINTWISE_TIMEOUT    Request timeout in seconds (default: 10)

Usage
-----
    from algl_pdf_helper.hintwise_client import HintwiseClient, call_hintwise

    result = call_hintwise(payload)
    if result.online:
        print(result.hint_content)
    else:
        print("offline mode – no request sent")
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from algl_pdf_helper.hintwise_adapter import HintwisePayload

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_ENDPOINT = "/api/hint"
_DEFAULT_TIMEOUT = 10


def _get_config() -> dict[str, Any]:
    """Read HintWise config from environment variables."""
    base_url = os.environ.get("HINTWISE_BASE_URL", "").rstrip("/")
    return {
        "base_url": base_url,
        "endpoint": os.environ.get("HINTWISE_ENDPOINT", _DEFAULT_ENDPOINT),
        "api_key": os.environ.get("HINTWISE_API_KEY", ""),
        "timeout": int(os.environ.get("HINTWISE_TIMEOUT", str(_DEFAULT_TIMEOUT))),
        "online": bool(base_url),
    }


# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------


@dataclass
class HintwiseResult:
    """Normalized response from the HintWise endpoint (or offline stub)."""

    # Whether a real HTTP call was made
    online: bool = False

    # Request echo fields
    concept_id: str = ""
    unit_id: str | None = None
    escalation_level: str = "L1"

    # Endpoint response
    status_code: int | None = None
    hint_id: str | None = None
    hint_content: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)

    # Error state (non-empty → call failed)
    error: str | None = None

    # Provenance
    endpoint_url: str | None = None
    requested_at: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)

    def succeeded(self) -> bool:
        """True if the HTTP call returned a 2xx status."""
        return self.online and self.status_code is not None and 200 <= self.status_code < 300

    def to_dict(self) -> dict[str, Any]:
        return {
            "online": self.online,
            "concept_id": self.concept_id,
            "unit_id": self.unit_id,
            "escalation_level": self.escalation_level,
            "status_code": self.status_code,
            "hint_id": self.hint_id,
            "hint_content": self.hint_content,
            "raw_response": self.raw_response,
            "error": self.error,
            "endpoint_url": self.endpoint_url,
            "requested_at": self.requested_at,
            "provenance": self.provenance,
        }


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class HintwiseClient:
    """
    HTTP client for the HintWise hint-selection service.

    When HINTWISE_BASE_URL is not set the client operates offline and
    ``call`` returns a result with ``online=False`` immediately.
    """

    def __init__(
        self,
        base_url: str = "",
        endpoint: str = _DEFAULT_ENDPOINT,
        api_key: str = "",
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.endpoint = endpoint
        self.api_key = api_key
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> "HintwiseClient":
        """Create a client from environment variables."""
        cfg = _get_config()
        return cls(
            base_url=cfg["base_url"],
            endpoint=cfg["endpoint"],
            api_key=cfg["api_key"],
            timeout=cfg["timeout"],
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url)

    def _build_url(self) -> str:
        return self.base_url + self.endpoint

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def call(self, payload: HintwisePayload) -> HintwiseResult:
        """
        Send payload to the configured HintWise endpoint.

        Returns HintwiseResult. If the client is not configured (offline mode)
        the result has ``online=False`` and no HTTP call is made.

        Retries once on connection-level transient failures only
        (OSError / urllib.error.URLError). 4xx/5xx responses are not retried.
        """
        requested_at = datetime.now(timezone.utc).isoformat()
        concept_id = payload.concept_context.concept_id
        unit_id = payload.concept_context.unit_id
        escalation = payload.learner_context.escalation_level
        provenance = {
            "source_pdf": payload.provenance.source_pdf,
            "source_pages": payload.provenance.source_pages,
            "backbone_sources": payload.provenance.backbone_sources,
        }

        if not self.is_configured:
            logger.debug("HintWise offline mode (HINTWISE_BASE_URL not set)")
            return HintwiseResult(
                online=False,
                concept_id=concept_id,
                unit_id=unit_id,
                escalation_level=escalation,
                requested_at=requested_at,
                provenance=provenance,
            )

        url = self._build_url()
        body = json.dumps(payload.to_dict()).encode("utf-8")
        headers = self._build_headers()

        last_error: str | None = None
        for attempt in range(2):  # one retry on transient errors
            try:
                req = urllib.request.Request(url, data=body, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    status_code = resp.status
                    raw_bytes = resp.read()
                    try:
                        raw_response = json.loads(raw_bytes)
                    except json.JSONDecodeError:
                        raw_response = {"raw": raw_bytes.decode("utf-8", errors="replace")}

                    return HintwiseResult(
                        online=True,
                        concept_id=concept_id,
                        unit_id=unit_id,
                        escalation_level=escalation,
                        status_code=status_code,
                        hint_id=raw_response.get("hint_id"),
                        hint_content=raw_response.get("hint_content") or raw_response.get("content"),
                        raw_response=raw_response,
                        endpoint_url=url,
                        requested_at=requested_at,
                        provenance=provenance,
                    )

            except urllib.error.HTTPError as exc:
                # HTTP-level error: read body and return immediately (no retry)
                try:
                    raw_response = json.loads(exc.read())
                except Exception:
                    raw_response = {}
                return HintwiseResult(
                    online=True,
                    concept_id=concept_id,
                    unit_id=unit_id,
                    escalation_level=escalation,
                    status_code=exc.code,
                    raw_response=raw_response,
                    error=f"HTTP {exc.code}: {exc.reason}",
                    endpoint_url=url,
                    requested_at=requested_at,
                    provenance=provenance,
                )

            except (OSError, urllib.error.URLError) as exc:
                last_error = str(exc)
                if attempt == 0:
                    logger.warning("HintWise transient error (will retry): %s", exc)
                else:
                    logger.error("HintWise failed after retry: %s", exc)

        return HintwiseResult(
            online=True,
            concept_id=concept_id,
            unit_id=unit_id,
            escalation_level=escalation,
            error=f"Connection error: {last_error}",
            endpoint_url=url,
            requested_at=requested_at,
            provenance=provenance,
        )


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


def call_hintwise(payload: HintwisePayload) -> HintwiseResult:
    """
    Build a client from environment variables and call the HintWise endpoint.

    This is the main entry point for one-off calls; use ``HintwiseClient``
    directly when you need to share a client across multiple calls.
    """
    client = HintwiseClient.from_env()
    return client.call(payload)
