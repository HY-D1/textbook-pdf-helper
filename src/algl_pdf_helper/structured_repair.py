"""
Provider-Neutral Structured Repair Layer for LLM Content Repair.

This module provides a unified interface for structured LLM-based content repair
that works with multiple providers (Ollama, Claude Local, OpenAI-compatible).

Usage:
    from algl_pdf_helper.structured_repair import (
        StructuredRepairClient,
        OllamaRepairBackend,
        ClaudeLocalRepairBackend,
        RepairResult,
    )

    # Create provider-specific backend
    backend = OllamaRepairBackend(model="qwen3.5:9b-q8_0")
    # or
    backend = ClaudeLocalRepairBackend(
        base_url="http://localhost:8080",
        model="claude-sonnet-4-6"
    )

    # Use unified interface
    client = StructuredRepairClient(backend)
    result = client.repair_l3_content(
        concept_id="joins",
        weak_content={...},
        source_evidence="..."
    )

    if result.success:
        use_repaired_content(result.content)
    else:
        log_repair_failure(result.failure_reason, result.raw_response)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import socket
import time
import traceback
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Literal

try:
    from pydantic import BaseModel, Field, ValidationError
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False
    BaseModel = object
    Field = lambda **kwargs: None
    ValidationError = Exception


logger = logging.getLogger(__name__)


# =============================================================================
# REPAIR OUTCOME ENUMS
# =============================================================================

class RepairOutcome(str, Enum):
    """Explicit outcomes for repair attempts."""
    SUCCESS = "repair_succeeded"
    INVALID_JSON = "repair_invalid_json"
    EMPTY_RESPONSE = "repair_empty_response"
    VALIDATION_FAILED = "repair_validation_failed"
    TIMEOUT = "repair_timeout"
    CONNECTION_ERROR = "repair_connection_error"
    HTTP_ERROR = "repair_http_error"
    MODEL_UNAVAILABLE = "repair_model_unavailable"
    DISABLED = "repair_disabled"
    SKIPPED_NO_CANDIDATE = "repair_skipped_no_candidate"
    PARSE_ERROR = "repair_parse_error"
    PROVIDER_ERROR = "repair_provider_error"


# =============================================================================
# STRUCTURED REPAIR SCHEMA
# =============================================================================

if HAS_PYDANTIC:
    class ExampleRepair(BaseModel):
        """Schema for example repair suggestions."""
        original_example: str = Field(default="", description="The original example text if present")
        repaired_example: str = Field(default="", description="Improved or corrected example")
        example_valid: bool = Field(default=True, description="Whether the example is valid SQL")
        suggested_fix: str = Field(default="", description="Suggested fix if example is invalid")

    class StructuredL3Repair(BaseModel):
        """
        Strict schema for L3 content repair output.

        This schema defines the exact structure that the repair LLM must return.
        All fields are validated - if the response doesn't match this schema,
        the repair is rejected with specific validation errors.
        """
        definition: str = Field(
            ...,
            min_length=20,
            max_length=500,
            description="Clear 1-2 sentence definition of the concept"
        )
        why_it_matters: str = Field(
            ...,
            min_length=20,
            max_length=500,
            description="Why students should care about this concept (1-2 sentences)"
        )
        explanation: str = Field(
            default="",
            max_length=2000,
            description="Detailed explanation using source evidence (2-3 sentences)"
        )
        concept_page_suggestions: list[str] = Field(
            default_factory=list,
            description="Suggested page numbers where this concept appears"
        )
        example_repairs: list[ExampleRepair] = Field(
            default_factory=list,
            description="Suggested repairs for weak or broken examples"
        )
        repair_reasons: list[str] = Field(
            default_factory=list,
            description="List of specific issues that were repaired"
        )
        review_flags: list[str] = Field(
            default_factory=list,
            description="Warnings or items needing human review"
        )
        confidence_score: float = Field(
            default=0.5,
            ge=0.0,
            le=1.0,
            description="Confidence in this repair (0.0-1.0)"
        )
        uses_only_source_evidence: bool = Field(
            default=True,
            description="Whether repair uses only provided source evidence"
        )
else:
    class StructuredL3Repair:
        pass
    class ExampleRepair:
        pass


# =============================================================================
# REPAIR RESULT
# =============================================================================

@dataclass
class RepairResult:
    """
    Result of structured repair attempt with detailed failure information.

    Always provides safe fallback content even if repair fails.
    """
    success: bool
    outcome: RepairOutcome
    original_content: dict[str, Any]
    repaired_content: dict[str, Any] | None = None
    structured_repair: StructuredL3Repair | None = None
    error_message: str | None = None
    validation_errors: list[str] = field(default_factory=list)
    model_used: str = ""
    provider: str = ""
    duration_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    # Debug info for failures
    raw_response_excerpt: str | None = None
    parse_error_details: str | None = None
    prompt_hash: str | None = None

    def get_content_to_use(self) -> dict[str, Any]:
        """Get the content that should be used (repaired or original)."""
        if self.success and self.repaired_content:
            return self.repaired_content
        return self.original_content

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "success": self.success,
            "outcome": self.outcome.value,
            "original_content": self.original_content,
            "repaired_content": self.repaired_content,
            "error_message": self.error_message,
            "validation_errors": self.validation_errors,
            "model_used": self.model_used,
            "provider": self.provider,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
            "raw_response_excerpt": self.raw_response_excerpt,
            "parse_error_details": self.parse_error_details,
        }


# =============================================================================
# FAILURE DEBUG ARTIFACT
# =============================================================================

@dataclass
class RepairFailureRecord:
    """Record of a repair failure for debug artifact."""
    timestamp: str
    provider: str
    model: str
    endpoint: str
    request_mode: str
    phase: str
    concept_id: str
    unit_id: str | None
    prompt_hash: str
    raw_response_excerpt: str
    error_type: str
    error_details: str
    outcome: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "provider": self.provider,
            "model": self.model,
            "endpoint": self.endpoint,
            "request_mode": self.request_mode,
            "phase": self.phase,
            "concept_id": self.concept_id,
            "unit_id": self.unit_id,
            "prompt_hash": self.prompt_hash,
            "raw_response_excerpt": self.raw_response_excerpt[:2000] if self.raw_response_excerpt else None,
            "error_type": self.error_type,
            "error_details": self.error_details,
            "outcome": self.outcome,
        }


class RepairFailureLogger:
    """Logger for repair failures to debug artifact."""

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir
        self.failures: list[RepairFailureRecord] = []

    def set_output_dir(self, output_dir: Path) -> None:
        """Set output directory for failure logs."""
        self.output_dir = output_dir

    def log_failure(self, record: RepairFailureRecord) -> None:
        """Log a failure record."""
        self.failures.append(record)
        # Also write immediately if output dir is set
        if self.output_dir:
            self._append_failure(record)

    def _append_failure(self, record: RepairFailureRecord) -> None:
        """Append single failure to JSONL file."""
        if not self.output_dir:
            return

        failure_file = self.output_dir / "structured_repair_failures.jsonl"
        try:
            with open(failure_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Failed to write failure record: {e}")

    def write_summary(self) -> Path | None:
        """Write full failure summary to JSONL file."""
        if not self.output_dir or not self.failures:
            return None

        failure_file = self.output_dir / "structured_repair_failures.jsonl"
        try:
            with open(failure_file, "w", encoding="utf-8") as f:
                for record in self.failures:
                    f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
            return failure_file
        except Exception as e:
            logger.warning(f"Failed to write failure summary: {e}")
            return None


# Global failure logger instance
_failure_logger = RepairFailureLogger()


def get_failure_logger(output_dir: Path | None = None) -> RepairFailureLogger:
    """Get the global failure logger instance."""
    if output_dir:
        _failure_logger.set_output_dir(output_dir)
    return _failure_logger


# =============================================================================
# TOLERANT JSON PARSING
# =============================================================================

class TolerantJsonParser:
    """
    Tolerant JSON parser for extracting structured data from LLM responses.

    Handles various response formats including:
    - Clean JSON
    - Markdown fenced code blocks
    - Commentary + JSON
    - Multiple JSON objects (extracts first)
    - Truncated responses
    """

    MAX_RESPONSE_LENGTH = 10000  # Truncate very long responses

    @classmethod
    def parse(cls, response_text: str) -> tuple[dict[str, Any] | None, str | None]:
        """
        Attempt to parse JSON from response with multiple fallback strategies.

        Returns:
            Tuple of (parsed_data, error_message)
            - If successful: (data_dict, None)
            - If failed: (None, error_description)
        """
        if not response_text or not response_text.strip():
            return None, "Empty response"

        original_text = response_text
        response_text = response_text.strip()

        # Strategy 1: Direct JSON parse
        try:
            return json.loads(response_text), None
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract from markdown fenced code blocks
        try:
            extracted = cls._extract_from_markdown(response_text)
            if extracted:
                return json.loads(extracted), None
        except json.JSONDecodeError:
            pass

        # Strategy 3: Extract first JSON-like object
        try:
            extracted = cls._extract_first_json_object(response_text)
            if extracted:
                return json.loads(extracted), None
        except json.JSONDecodeError:
            pass

        # Strategy 4: Try to fix common JSON issues
        try:
            fixed = cls._fix_common_issues(response_text)
            if fixed:
                return json.loads(fixed), None
        except json.JSONDecodeError:
            pass

        # All strategies failed
        error_msg = cls._diagnose_failure(original_text)
        return None, error_msg

    @classmethod
    def _extract_from_markdown(cls, text: str) -> str | None:
        """Extract JSON from markdown code blocks."""
        # Try ```json ... ```
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Try ``` ... ``` (without language specifier)
        match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            return match.group(1).strip()

        return None

    @classmethod
    def _extract_first_json_object(cls, text: str) -> str | None:
        """Extract the first JSON object from text."""
        # Look for { ... } with balanced braces
        depth = 0
        start = -1

        for i, char in enumerate(text):
            if char == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0 and start != -1:
                    return text[start:i+1]

        return None

    @classmethod
    def _fix_common_issues(cls, text: str) -> str | None:
        """Fix common JSON formatting issues."""
        # Try extracting just the object part if there's commentary
        lines = text.split('\n')
        json_lines = []
        in_json = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('{'):
                in_json = True
            if in_json:
                json_lines.append(line)
            if stripped.endswith('}') and in_json:
                break

        if json_lines:
            return '\n'.join(json_lines)

        return None

    @classmethod
    def _diagnose_failure(cls, text: str) -> str:
        """Diagnose why JSON parsing failed."""
        if not text.strip():
            return "Empty response"

        text = text.strip()

        if text.startswith('<') or text.startswith('{'):
            # Might be HTML or already JSON that failed validation
            if '<html' in text.lower() or '<!doctype' in text.lower():
                return "Response appears to be HTML, not JSON"

        # Check for common patterns
        if '```' in text:
            return "Markdown fences present but content not valid JSON"

        if text.startswith('{') and text.count('{') != text.count('}'):
            return "Unbalanced braces - JSON may be truncated"

        if '"' in text and not text.startswith('{'):
            return "Response contains quotes but not valid JSON object"

        # Truncation check
        if len(text) > 100 and text[:50].count('{') > text[-50:].count('}'):
            return "Response appears truncated (more opening braces than closing)"

        return f"Unable to parse JSON (response length: {len(text)} chars)"

    @classmethod
    def get_excerpt(cls, text: str, max_length: int = 500) -> str:
        """Get a safe excerpt of the response for logging."""
        if not text:
            return ""
        text = text.strip()
        if len(text) <= max_length:
            return text
        return text[:max_length] + "... [truncated]"


# =============================================================================
# REPAIR BACKEND INTERFACE
# =============================================================================

class RepairBackend(ABC):
    """Abstract base class for repair backends (Ollama, Claude Local, etc.)."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name."""
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """Return the model name."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the backend is available."""
        pass

    @abstractmethod
    def generate_structured_repair(
        self,
        concept_id: str,
        weak_content: dict[str, Any],
        source_evidence: str,
        timeout: int = 120,
    ) -> RepairResult:
        """
        Generate a structured repair.

        Args:
            concept_id: The concept identifier
            weak_content: Dictionary with weak/missing content fields
            source_evidence: Source text from textbook
            timeout: Request timeout in seconds

        Returns:
            RepairResult with success/failure details
        """
        pass


# =============================================================================
# OLLAMA BACKEND
# =============================================================================

class OllamaRepairBackend(RepairBackend):
    """Ollama-specific repair backend implementation."""

    DEFAULT_HOST = "http://localhost:11434"
    DEFAULT_MODEL = "qwen3.5:9b-q8_0"

    # Model-specific configurations
    MODEL_CONFIGS: dict[str, dict[str, Any]] = {
        "qwen3.5:9b": {
            "context_window": 8192,
            "temperature": 0.1,
            "top_p": 0.90,
            "top_k": 20,
            "num_predict": 800,
        },
        "qwen3.5:27b": {
            "context_window": 4096,
            "temperature": 0.1,
            "top_p": 0.90,
            "top_k": 20,
            "num_predict": 800,
        },
        "qwen3.5:9b-q8_0": {
            "context_window": 8192,
            "temperature": 0.1,
            "top_p": 0.90,
            "top_k": 20,
            "num_predict": 800,
        },
        "qwen3.5:27b-q4_K_M": {
            "context_window": 4096,
            "temperature": 0.1,
            "top_p": 0.90,
            "top_k": 20,
            "num_predict": 800,
        },
    }

    DEFAULT_CONFIG = {
        "context_window": 4096,
        "temperature": 0.1,
        "top_p": 0.90,
        "top_k": 20,
        "num_predict": 800,
    }

    def __init__(
        self,
        model: str | None = None,
        host: str | None = None,
        request_mode: Literal["auto", "generate", "chat"] = "auto",
    ):
        self._host = (host or os.getenv("OLLAMA_HOST", self.DEFAULT_HOST)).rstrip("/")
        self._requested_model = model or os.getenv("OLLAMA_MODEL", self.DEFAULT_MODEL)
        self._resolved_model: str | None = None
        self._request_mode = request_mode
        self._available: bool | None = None

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        if self._resolved_model is None and self.is_available():
            self._resolved_model = self._resolve_model(self._requested_model)
        return self._resolved_model or self._requested_model

    @property
    def endpoint(self) -> str:
        return f"{self._host}/api/generate"

    def is_available(self) -> bool:
        if self._available is None:
            self._available = self._check_availability()
        return self._available

    def _check_availability(self) -> bool:
        """Check if Ollama server is reachable."""
        try:
            req = urllib.request.Request(
                f"{self._host}/api/tags",
                method="GET",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=3) as response:
                return response.status == 200
        except Exception:
            return False

    def _list_available_models(self) -> list[str]:
        """List available Ollama models."""
        try:
            req = urllib.request.Request(
                f"{self._host}/api/tags",
                method="GET",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            pass
        return []

    def _resolve_model(self, requested: str) -> str:
        """Resolve model name, falling back to available models."""
        available = self._list_available_models()

        if requested in available:
            return requested

        # Try partial match
        for avail in available:
            if requested in avail or avail.startswith(requested.split(":")[0]):
                logger.warning(f"Model '{requested}' not found, using '{avail}'")
                return avail

        # Return requested anyway - will fail with clear error later
        return requested

    def _get_model_config(self, model_name: str) -> dict[str, Any]:
        """Get configuration for specific model."""
        # Try exact match
        if model_name in self.MODEL_CONFIGS:
            return self.MODEL_CONFIGS[model_name]

        # Try partial match
        for key, config in self.MODEL_CONFIGS.items():
            if key in model_name or model_name.startswith(key.split(":")[0]):
                return config

        return self.DEFAULT_CONFIG

    def _build_prompt(
        self,
        concept_id: str,
        weak_content: dict[str, Any],
        source_evidence: str,
    ) -> str:
        """Build prompt that enforces structured JSON output."""
        config = self._get_model_config(self.model)
        max_evidence = config.get("context_window", 4096) - 1500

        if len(source_evidence) > max_evidence:
            source_evidence = source_evidence[:max_evidence] + "..."

        current_definition = weak_content.get("definition", "MISSING")
        current_why = weak_content.get("why_it_matters", "MISSING")

        # Include the schema in the prompt for strict compliance
        schema_example = {
            "definition": "A JOIN clause combines rows from two or more tables based on a related column between them.",
            "why_it_matters": "JOINs are essential for querying normalized databases where data is spread across multiple tables to reduce redundancy.",
            "explanation": "When tables are normalized, related data is stored separately. JOINs allow you to reconstruct this relationships in your queries.",
            "concept_page_suggestions": ["45", "46"],
            "example_repairs": [
                {
                    "original_example": "SELECT * FROM a, b",
                    "repaired_example": "SELECT * FROM customers JOIN orders ON customers.id = orders.customer_id",
                    "example_valid": True,
                    "suggested_fix": ""
                }
            ],
            "repair_reasons": ["definition_too_short", "missing_examples"],
            "review_flags": ["verify_sql_syntax"],
            "confidence_score": 0.85,
            "uses_only_source_evidence": True,
        }

        return f"""You are an expert SQL educator. Repair weak content using ONLY the provided source evidence.

CONCEPT: {concept_id}

SOURCE EVIDENCE (use ONLY this information):
{source_evidence}

CURRENT WEAK CONTENT:
- Definition: {current_definition}
- Why it matters: {current_why}

STRICT OUTPUT REQUIREMENTS:
You MUST return a valid JSON object matching this exact schema:

{json.dumps(schema_example, indent=2)}

FIELD REQUIREMENTS:
- definition: 20-500 chars, clear and educational (REQUIRED)
- why_it_matters: 20-500 chars, student-focused (REQUIRED)
- explanation: max 2000 chars, detailed with evidence (optional)
- concept_page_suggestions: array of page number strings (optional)
- example_repairs: array of example repair objects (optional)
- repair_reasons: array of strings explaining what was fixed (optional)
- review_flags: array of warning strings for human review (optional)
- confidence_score: number 0.0-1.0 (default: 0.5)
- uses_only_source_evidence: boolean (default: true)

RULES:
1. Use ONLY source evidence - do not invent facts
2. Write for beginner-to-intermediate SQL students
3. Use plain English, avoid unnecessary jargon
4. Return ONLY valid JSON, no markdown, no extra text
5. All string values must be properly escaped

Generate the repair JSON now:"""

    def _call_ollama(self, prompt: str, timeout: int) -> tuple[str | None, RepairOutcome | None, str | None]:
        """Call Ollama API and return response or error."""
        config = self._get_model_config(self.model)

        data = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": config.get("temperature", 0.1),
                "num_predict": config.get("num_predict", 800),
                "top_p": config.get("top_p", 0.9),
                "top_k": config.get("top_k", 20),
                "num_ctx": config.get("context_window", 4096),
            }
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self._host}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                # Check response field first, then thinking field (for qwen3.5 models)
                response_text = result.get("response", "")
                if not response_text:
                    response_text = result.get("thinking", "")
                return response_text, None, None
        except socket.timeout:
            return None, RepairOutcome.TIMEOUT, f"Timeout calling Ollama after {timeout}s"
        except urllib.error.HTTPError as e:
            return None, RepairOutcome.HTTP_ERROR, f"HTTP {e.code}: {e.reason}"
        except urllib.error.URLError as e:
            return None, RepairOutcome.CONNECTION_ERROR, f"Connection error: {e.reason}"
        except Exception as e:
            return None, RepairOutcome.PROVIDER_ERROR, f"Ollama API error: {e}"

    def generate_structured_repair(
        self,
        concept_id: str,
        weak_content: dict[str, Any],
        source_evidence: str,
        timeout: int = 120,
    ) -> RepairResult:
        """Generate structured repair using Ollama."""
        original_content = {"concept_id": concept_id, **weak_content}
        prompt_hash = hashlib.sha256(source_evidence.encode()).hexdigest()[:16]
        start_time = time.time()

        if not self.is_available():
            return RepairResult(
                success=False,
                outcome=RepairOutcome.MODEL_UNAVAILABLE,
                original_content=original_content,
                error_message="Ollama not available",
                model_used=self.model,
                provider=self.provider_name,
                prompt_hash=prompt_hash,
            )

        if not HAS_PYDANTIC:
            return RepairResult(
                success=False,
                outcome=RepairOutcome.DISABLED,
                original_content=original_content,
                error_message="Pydantic not available for structured validation",
                model_used=self.model,
                provider=self.provider_name,
                prompt_hash=prompt_hash,
            )

        # Build and send request
        prompt = self._build_prompt(concept_id, weak_content, source_evidence)

        raw_response, error_outcome, error_message = self._call_ollama(prompt, timeout)
        duration = time.time() - start_time

        if error_outcome:
            return RepairResult(
                success=False,
                outcome=error_outcome,
                original_content=original_content,
                error_message=error_message,
                model_used=self.model,
                provider=self.provider_name,
                duration_seconds=duration,
                prompt_hash=prompt_hash,
            )

        if not raw_response:
            return RepairResult(
                success=False,
                outcome=RepairOutcome.EMPTY_RESPONSE,
                original_content=original_content,
                error_message="Empty response from Ollama",
                model_used=self.model,
                provider=self.provider_name,
                duration_seconds=duration,
                prompt_hash=prompt_hash,
            )

        # Parse with tolerant parser
        parsed_data, parse_error = TolerantJsonParser.parse(raw_response)

        if parse_error:
            return RepairResult(
                success=False,
                outcome=RepairOutcome.INVALID_JSON,
                original_content=original_content,
                error_message=f"JSON parse error: {parse_error}",
                model_used=self.model,
                provider=self.provider_name,
                duration_seconds=duration,
                raw_response_excerpt=TolerantJsonParser.get_excerpt(raw_response),
                parse_error_details=parse_error,
                prompt_hash=prompt_hash,
            )

        # Validate against schema
        try:
            structured_repair = StructuredL3Repair(**parsed_data)
        except ValidationError as e:
            validation_errors = []
            if hasattr(e, 'errors'):
                for err in e.errors():
                    loc = ".".join(str(x) for x in err.get("loc", []))
                    msg = err.get("msg", "")
                    validation_errors.append(f"{loc}: {msg}")
            else:
                validation_errors = [str(e)]

            return RepairResult(
                success=False,
                outcome=RepairOutcome.VALIDATION_FAILED,
                original_content=original_content,
                error_message=f"Schema validation failed: {e}",
                validation_errors=validation_errors,
                model_used=self.model,
                provider=self.provider_name,
                duration_seconds=duration,
                raw_response_excerpt=TolerantJsonParser.get_excerpt(raw_response),
                prompt_hash=prompt_hash,
            )

        # Convert to content dict
        repaired_content = self._structured_to_content(structured_repair, concept_id)

        return RepairResult(
            success=True,
            outcome=RepairOutcome.SUCCESS,
            original_content=original_content,
            repaired_content=repaired_content,
            structured_repair=structured_repair,
            model_used=self.model,
            provider=self.provider_name,
            duration_seconds=duration,
            metadata={
                "confidence": structured_repair.confidence_score,
                "uses_only_source": structured_repair.uses_only_source_evidence,
                "review_flags": structured_repair.review_flags,
            },
            prompt_hash=prompt_hash,
        )

    def _structured_to_content(
        self, repair: StructuredL3Repair, concept_id: str
    ) -> dict[str, Any]:
        """Convert StructuredL3Repair to content dictionary."""
        content: dict[str, Any] = {
            "concept_id": concept_id,
            "definition": repair.definition,
            "why_it_matters": repair.why_it_matters,
            "explanation": repair.explanation,
            "_repaired_by_ollama": True,
            "_repair_model": self.model,
            "_repair_confidence": repair.confidence_score,
            "_uses_only_source": repair.uses_only_source_evidence,
        }

        # Add example repairs if present
        if repair.example_repairs:
            content["example_repairs"] = [
                {
                    "original": ex.original_example,
                    "repaired": ex.repaired_example,
                    "valid": ex.example_valid,
                    "fix": ex.suggested_fix,
                }
                for ex in repair.example_repairs
            ]

        # Add metadata
        if repair.repair_reasons:
            content["_repair_reasons"] = repair.repair_reasons
        if repair.review_flags:
            content["_review_flags"] = repair.review_flags
        if repair.concept_page_suggestions:
            content["_page_suggestions"] = repair.concept_page_suggestions

        return content


# =============================================================================
# CLAUDE LOCAL BACKEND (OpenAI-compatible)
# =============================================================================

class ClaudeLocalRepairBackend(RepairBackend):
    """
    Claude Local repair backend using OpenAI-compatible API.

    Assumes local Claude Code API is OpenAI-compatible, with:
    - CLAUDE_LOCAL_BASE_URL (default: http://localhost:8080)
    - CLAUDE_LOCAL_API_KEY (optional)
    - CLAUDE_LOCAL_MODEL (default: claude-sonnet-4-6)
    """

    DEFAULT_BASE_URL = "http://localhost:8080"
    DEFAULT_MODEL = "claude-sonnet-4-6"

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ):
        self._base_url = (base_url or os.getenv("CLAUDE_LOCAL_BASE_URL", self.DEFAULT_BASE_URL)).rstrip("/")
        self._api_key = api_key or os.getenv("CLAUDE_LOCAL_API_KEY", "")
        self._model = model or os.getenv("CLAUDE_LOCAL_MODEL", self.DEFAULT_MODEL)
        self._available: bool | None = None

    @property
    def provider_name(self) -> str:
        return "claude_local"

    @property
    def model(self) -> str:
        return self._model

    @property
    def endpoint(self) -> str:
        return f"{self._base_url}/v1/chat/completions"

    def is_available(self) -> bool:
        if self._available is None:
            self._available = self._check_availability()
        return self._available

    def _check_availability(self) -> bool:
        """Check if Claude local endpoint is reachable."""
        try:
            # Try to hit the models endpoint or a simple health check
            req = urllib.request.Request(
                f"{self._base_url}/v1/models",
                method="GET",
                headers={"Content-Type": "application/json"},
            )
            if self._api_key:
                req.add_header("Authorization", f"Bearer {self._api_key}")

            with urllib.request.urlopen(req, timeout=3) as response:
                return response.status == 200
        except Exception:
            # Also try a simple connection check
            try:
                import urllib.parse
                parsed = urllib.parse.urlparse(self._base_url)
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((parsed.hostname, parsed.port or 8080))
                sock.close()
                return result == 0
            except Exception:
                return False

    def _build_messages(
        self,
        concept_id: str,
        weak_content: dict[str, Any],
        source_evidence: str,
    ) -> list[dict[str, str]]:
        """Build chat messages for Claude."""
        current_definition = weak_content.get("definition", "MISSING")
        current_why = weak_content.get("why_it_matters", "MISSING")

        schema_example = {
            "definition": "A JOIN clause combines rows from two or more tables based on a related column between them.",
            "why_it_matters": "JOINs are essential for querying normalized databases where data is spread across multiple tables to reduce redundancy.",
            "explanation": "When tables are normalized, related data is stored separately. JOINs allow you to reconstruct this relationships in your queries.",
            "concept_page_suggestions": ["45", "46"],
            "example_repairs": [
                {
                    "original_example": "SELECT * FROM a, b",
                    "repaired_example": "SELECT * FROM customers JOIN orders ON customers.id = orders.customer_id",
                    "example_valid": True,
                    "suggested_fix": ""
                }
            ],
            "repair_reasons": ["definition_too_short", "missing_examples"],
            "review_flags": ["verify_sql_syntax"],
            "confidence_score": 0.85,
            "uses_only_source_evidence": True,
        }

        system_message = """You are an expert SQL educator. Your task is to repair weak or missing educational content using ONLY the provided source evidence.

You MUST return a valid JSON object matching the specified schema. Do not include any other text, markdown formatting, or commentary outside the JSON."""

        user_message = f"""Repair the following weak content for concept: {concept_id}

SOURCE EVIDENCE (use ONLY this information):
{source_evidence[:4000]}  # Truncate to reasonable length

CURRENT WEAK CONTENT:
- Definition: {current_definition}
- Why it matters: {current_why}

REQUIRED JSON SCHEMA:
{json.dumps(schema_example, indent=2)}

FIELD REQUIREMENTS:
- definition: 20-500 chars, clear and educational (REQUIRED)
- why_it_matters: 20-500 chars, student-focused (REQUIRED)
- explanation: max 2000 chars, detailed with evidence (optional)
- concept_page_suggestions: array of page number strings (optional)
- example_repairs: array of example repair objects (optional)
- repair_reasons: array of strings explaining what was fixed (optional)
- review_flags: array of warning strings for human review (optional)
- confidence_score: number 0.0-1.0 (default: 0.5)
- uses_only_source_evidence: boolean (default: true)

RULES:
1. Use ONLY source evidence - do not invent facts
2. Write for beginner-to-intermediate SQL students
3. Use plain English, avoid unnecessary jargon
4. Return ONLY valid JSON, no markdown, no extra text
5. All string values must be properly escaped

Generate the repair JSON now:"""

        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]

    def _call_claude(self, messages: list[dict[str, str]], timeout: int) -> tuple[str | None, RepairOutcome | None, str | None]:
        """Call Claude local API and return response or error."""
        data = json.dumps({
            "model": self._model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 1000,
            "response_format": {"type": "json_object"},
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self._base_url}/v1/chat/completions",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        if self._api_key:
            req.add_header("Authorization", f"Bearer {self._api_key}")

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                # Extract content from response
                choices = result.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    return message.get("content", ""), None, None
                return None, RepairOutcome.EMPTY_RESPONSE, "No choices in response"
        except socket.timeout:
            return None, RepairOutcome.TIMEOUT, f"Timeout calling Claude local after {timeout}s"
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if hasattr(e, 'read') else ""
            return None, RepairOutcome.HTTP_ERROR, f"HTTP {e.code}: {e.reason} - {error_body[:200]}"
        except urllib.error.URLError as e:
            return None, RepairOutcome.CONNECTION_ERROR, f"Connection error: {e.reason}"
        except Exception as e:
            return None, RepairOutcome.PROVIDER_ERROR, f"Claude local API error: {e}"

    def generate_structured_repair(
        self,
        concept_id: str,
        weak_content: dict[str, Any],
        source_evidence: str,
        timeout: int = 120,
    ) -> RepairResult:
        """Generate structured repair using Claude Local."""
        original_content = {"concept_id": concept_id, **weak_content}
        prompt_hash = hashlib.sha256(source_evidence.encode()).hexdigest()[:16]
        start_time = time.time()

        if not self.is_available():
            return RepairResult(
                success=False,
                outcome=RepairOutcome.MODEL_UNAVAILABLE,
                original_content=original_content,
                error_message=f"Claude local not available at {self._base_url}",
                model_used=self._model,
                provider=self.provider_name,
                prompt_hash=prompt_hash,
            )

        if not HAS_PYDANTIC:
            return RepairResult(
                success=False,
                outcome=RepairOutcome.DISABLED,
                original_content=original_content,
                error_message="Pydantic not available for structured validation",
                model_used=self._model,
                provider=self.provider_name,
                prompt_hash=prompt_hash,
            )

        # Build and send request
        messages = self._build_messages(concept_id, weak_content, source_evidence)

        raw_response, error_outcome, error_message = self._call_claude(messages, timeout)
        duration = time.time() - start_time

        if error_outcome:
            return RepairResult(
                success=False,
                outcome=error_outcome,
                original_content=original_content,
                error_message=error_message,
                model_used=self._model,
                provider=self.provider_name,
                duration_seconds=duration,
                prompt_hash=prompt_hash,
            )

        if not raw_response:
            return RepairResult(
                success=False,
                outcome=RepairOutcome.EMPTY_RESPONSE,
                original_content=original_content,
                error_message="Empty response from Claude local",
                model_used=self._model,
                provider=self.provider_name,
                duration_seconds=duration,
                prompt_hash=prompt_hash,
            )

        # Parse with tolerant parser
        parsed_data, parse_error = TolerantJsonParser.parse(raw_response)

        if parse_error:
            return RepairResult(
                success=False,
                outcome=RepairOutcome.INVALID_JSON,
                original_content=original_content,
                error_message=f"JSON parse error: {parse_error}",
                model_used=self._model,
                provider=self.provider_name,
                duration_seconds=duration,
                raw_response_excerpt=TolerantJsonParser.get_excerpt(raw_response),
                parse_error_details=parse_error,
                prompt_hash=prompt_hash,
            )

        # Validate against schema
        try:
            structured_repair = StructuredL3Repair(**parsed_data)
        except ValidationError as e:
            validation_errors = []
            if hasattr(e, 'errors'):
                for err in e.errors():
                    loc = ".".join(str(x) for x in err.get("loc", []))
                    msg = err.get("msg", "")
                    validation_errors.append(f"{loc}: {msg}")
            else:
                validation_errors = [str(e)]

            return RepairResult(
                success=False,
                outcome=RepairOutcome.VALIDATION_FAILED,
                original_content=original_content,
                error_message=f"Schema validation failed: {e}",
                validation_errors=validation_errors,
                model_used=self._model,
                provider=self.provider_name,
                duration_seconds=duration,
                raw_response_excerpt=TolerantJsonParser.get_excerpt(raw_response),
                prompt_hash=prompt_hash,
            )

        # Convert to content dict
        repaired_content = self._structured_to_content(structured_repair, concept_id)

        return RepairResult(
            success=True,
            outcome=RepairOutcome.SUCCESS,
            original_content=original_content,
            repaired_content=repaired_content,
            structured_repair=structured_repair,
            model_used=self._model,
            provider=self.provider_name,
            duration_seconds=duration,
            metadata={
                "confidence": structured_repair.confidence_score,
                "uses_only_source": structured_repair.uses_only_source_evidence,
                "review_flags": structured_repair.review_flags,
            },
            prompt_hash=prompt_hash,
        )

    def _structured_to_content(
        self, repair: StructuredL3Repair, concept_id: str
    ) -> dict[str, Any]:
        """Convert StructuredL3Repair to content dictionary."""
        content: dict[str, Any] = {
            "concept_id": concept_id,
            "definition": repair.definition,
            "why_it_matters": repair.why_it_matters,
            "explanation": repair.explanation,
            "_repaired_by_claude_local": True,
            "_repair_model": self._model,
            "_repair_confidence": repair.confidence_score,
            "_uses_only_source": repair.uses_only_source_evidence,
        }

        # Add example repairs if present
        if repair.example_repairs:
            content["example_repairs"] = [
                {
                    "original": ex.original_example,
                    "repaired": ex.repaired_example,
                    "valid": ex.example_valid,
                    "fix": ex.suggested_fix,
                }
                for ex in repair.example_repairs
            ]

        # Add metadata
        if repair.repair_reasons:
            content["_repair_reasons"] = repair.repair_reasons
        if repair.review_flags:
            content["_review_flags"] = repair.review_flags
        if repair.concept_page_suggestions:
            content["_page_suggestions"] = repair.concept_page_suggestions

        return content


# =============================================================================
# UNIFIED CLIENT
# =============================================================================

class StructuredRepairClient:
    """
    Unified client for structured repair across all providers.

    This is the main entry point for the pipeline - it provides a
    provider-agnostic interface that routes to the appropriate backend.
    """

    def __init__(self, backend: RepairBackend):
        self.backend = backend
        self._failure_logger = get_failure_logger()

    @property
    def provider(self) -> str:
        return self.backend.provider_name

    @property
    def model(self) -> str:
        return self.backend.model

    def is_available(self) -> bool:
        return self.backend.is_available()

    def repair_l3_content(
        self,
        concept_id: str,
        weak_content: dict[str, Any],
        source_evidence: str,
        unit_id: str | None = None,
        timeout: int = 120,
    ) -> RepairResult:
        """
        Repair L3 content using the configured backend.

        This is the main method called by the pipeline. It delegates to
        the backend and handles failure logging.
        """
        result = self.backend.generate_structured_repair(
            concept_id=concept_id,
            weak_content=weak_content,
            source_evidence=source_evidence,
            timeout=timeout,
        )

        # Log failures for debugging
        if not result.success:
            failure_record = RepairFailureRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                provider=result.provider,
                model=result.model_used,
                endpoint=getattr(self.backend, 'endpoint', 'unknown'),
                request_mode=getattr(self.backend, '_request_mode', 'default'),
                phase="L3_repair",
                concept_id=concept_id,
                unit_id=unit_id,
                prompt_hash=result.prompt_hash or "",
                raw_response_excerpt=result.raw_response_excerpt or "",
                error_type=result.outcome.value,
                error_details=result.error_message or "",
                outcome=result.outcome.value,
            )
            self._failure_logger.log_failure(failure_record)

        return result

    def assess_content_quality(
        self,
        content: dict[str, Any],
        source_blocks: list[Any] | None = None,
    ) -> float:
        """
        Assess the quality of L3 content using heuristics.

        This method provides a fast local quality assessment without calling LLM.
        """
        if not isinstance(content, dict):
            return 0.0

        scores = []

        # Check definition quality
        definition = content.get("definition", "")
        if len(definition) >= 100:
            scores.append(1.0)
        elif len(definition) >= 50:
            scores.append(0.7)
        elif len(definition) >= 20:
            scores.append(0.4)
        else:
            scores.append(0.1)

        # Check why_it_matters quality
        why = content.get("why_it_matters", "")
        if len(why) >= 80:
            scores.append(1.0)
        elif len(why) >= 40:
            scores.append(0.7)
        elif len(why) >= 20:
            scores.append(0.4)
        else:
            scores.append(0.1)

        # Check explanation quality
        explanation = content.get("explanation", "")
        if len(explanation) >= 200:
            scores.append(1.0)
        elif len(explanation) >= 100:
            scores.append(0.7)
        elif len(explanation) >= 50:
            scores.append(0.4)
        else:
            scores.append(0.2)

        # Check for SQL examples
        has_example = bool(content.get("example") or content.get("example_repairs"))
        scores.append(1.0 if has_example else 0.5)

        # Calculate average
        return sum(scores) / len(scores) if scores else 0.5


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_repair_backend(
    provider: Literal["ollama", "claude_local", "grounded"],
    model: str | None = None,
    **kwargs,
) -> RepairBackend | None:
    """
    Factory function to create appropriate repair backend.

    Args:
        provider: Provider name (ollama, claude_local, grounded)
        model: Specific model name (provider-specific default if None)
        **kwargs: Additional provider-specific options

    Returns:
        RepairBackend instance or None if grounded/disabled
    """
    if provider == "grounded":
        return None

    if provider == "ollama":
        return OllamaRepairBackend(
            model=model or os.getenv("OLLAMA_MODEL", "qwen3.5:9b-q8_0"),
            host=kwargs.get("host", os.getenv("OLLAMA_HOST")),
            request_mode=kwargs.get("request_mode", "auto"),
        )

    if provider == "claude_local":
        return ClaudeLocalRepairBackend(
            base_url=kwargs.get("base_url", os.getenv("CLAUDE_LOCAL_BASE_URL")),
            api_key=kwargs.get("api_key", os.getenv("CLAUDE_LOCAL_API_KEY")),
            model=model or os.getenv("CLAUDE_LOCAL_MODEL"),
        )

    raise ValueError(f"Unknown repair provider: {provider}")


def create_repair_client(
    provider: Literal["ollama", "claude_local", "grounded"],
    model: str | None = None,
    output_dir: Path | None = None,
    **kwargs,
) -> StructuredRepairClient | None:
    """
    Factory function to create a fully configured repair client.

    Args:
        provider: Provider name (ollama, claude_local, grounded)
        model: Specific model name (provider-specific default if None)
        output_dir: Output directory for failure logs
        **kwargs: Additional provider-specific options

    Returns:
        StructuredRepairClient instance or None if grounded/disabled
    """
    backend = create_repair_backend(provider, model, **kwargs)
    if backend is None:
        return None

    if output_dir:
        get_failure_logger(output_dir)

    return StructuredRepairClient(backend)
