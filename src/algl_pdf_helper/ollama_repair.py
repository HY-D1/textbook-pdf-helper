"""
Ollama-based Structured Repair Pass for Weak/Missing L3 Content.

This module provides a structured repair mechanism for instructional units where L3
content is weak or missing. It uses local Ollama (Qwen 3.5 9B recommended) with
strict JSON schema validation for reliable, parseable outputs.

Usage:
    from algl_pdf_helper.ollama_repair import OllamaRepair, StructuredL3Repair
    
    repair = OllamaRepair(model="qwen3.5:9b")
    if repair.available:
        result = repair.repair_l3_content_structured(
            concept_id="joins",
            weak_content={"definition": "Weak...", "why_it_matters": ""},
            source_evidence="Textbook content..."
        )
        if result.repair_accepted:
            use_repaired_content(result.repaired_content)
        else:
            use_original_with_fallback(result.original_content, result.error)
"""

from __future__ import annotations

import hashlib
import json
import logging
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from pydantic import BaseModel, Field, ValidationError
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False
    # Fallback for when pydantic is not available
    class BaseModel:
        pass
    class Field:
        def __init__(self, *args, **kwargs):
            pass
    class ValidationError(Exception):
        pass

from algl_pdf_helper.instructional_models import InstructionalUnit


logger = logging.getLogger(__name__)

# Prompt version for cache invalidation - bump when prompt changes
REPAIR_PROMPT_VERSION = "v3.0.0-structured"

# RECOMMENDED REPAIR MODEL for Week 1: qwen3.5:9b
# This is the primary model users should have locally via Ollama
RECOMMENDED_REPAIR_MODEL = "qwen3.5:9b"

# Preferred models for RTX 4080 optimization (in order of preference)
PREFERRED_MODELS = [
    "qwen3.5:9b",           # RECOMMENDED for Week 1
    "qwen3.5:27b",
    "qwen3.5:9b-q8_0",
    "qwen3.5:27b-q4_K_M",
    "qwen3-coder:30b",
    "glm-4.7-flash:latest",
    "qwen2.5:3b",           # Fallback for testing
]

# Model-specific configurations
MODEL_CONFIGS: dict[str, dict[str, Any]] = {
    "qwen3.5:9b": {
        "context_window": 8192,
        "temperature": 0.1,  # Low temp for consistent structured output
        "top_p": 0.90,
        "top_k": 20,
        "num_predict": 800,
        "description": "RECOMMENDED: Fast 9B model, excellent for structured repair",
    },
    "qwen3.5:27b": {
        "context_window": 4096,
        "temperature": 0.1,
        "top_p": 0.90,
        "top_k": 20,
        "num_predict": 800,
        "description": "Large 27B model, higher quality but slower",
    },
    "qwen3.5:9b-q8_0": {
        "context_window": 8192,
        "temperature": 0.1,
        "top_p": 0.90,
        "top_k": 20,
        "num_predict": 800,
        "description": "9B model with 8-bit quantization",
    },
    "qwen3.5:27b-q4_K_M": {
        "context_window": 4096,
        "temperature": 0.1,
        "top_p": 0.90,
        "top_k": 20,
        "num_predict": 800,
        "description": "27B model with 4-bit quantization",
    },
    "qwen3-coder:30b": {
        "context_window": 4096,
        "temperature": 0.1,
        "top_p": 0.85,
        "top_k": 20,
        "num_predict": 800,
        "description": "Code-specialized 30B model for SQL generation",
    },
    "glm-4.7-flash:latest": {
        "context_window": 8192,
        "temperature": 0.1,
        "top_p": 0.90,
        "top_k": 20,
        "num_predict": 800,
        "description": "Fast GLM model for quick repairs",
    },
    "qwen2.5:3b": {
        "context_window": 4096,
        "temperature": 0.2,
        "top_p": 0.90,
        "top_k": 40,
        "num_predict": 600,
        "description": "Small, fast model for testing (fallback)",
    },
}

# Default config for unknown models
DEFAULT_MODEL_CONFIG = {
    "context_window": 4096,
    "temperature": 0.1,
    "top_p": 0.90,
    "top_k": 20,
    "num_predict": 800,
    "description": "Default configuration",
}


def get_model_config(model_name: str) -> dict[str, Any]:
    """Get configuration for specific model, falling back to default."""
    # Try exact match first
    if model_name in MODEL_CONFIGS:
        return MODEL_CONFIGS[model_name]
    
    # Try partial match
    for key in MODEL_CONFIGS:
        if key in model_name or model_name.startswith(key.split(":")[0]):
            return MODEL_CONFIGS[key]
    
    return DEFAULT_MODEL_CONFIG


# =============================================================================
# STRUCTURED REPAIR SCHEMA (Pydantic)
# =============================================================================

if HAS_PYDANTIC:
    class ExampleRepair(BaseModel):
        """Schema for example repair suggestions."""
        original_example: str = Field(
            default="",
            description="The original example text if present"
        )
        repaired_example: str = Field(
            default="",
            description="Improved or corrected example"
        )
        example_valid: bool = Field(
            default=True,
            description="Whether the example is valid SQL"
        )
        suggested_fix: str = Field(
            default="",
            description="Suggested fix if example is invalid"
        )
    
    class StructuredL3Repair(BaseModel):
        """
        Strict schema for L3 content repair output.
        
        This schema defines the exact structure that the repair LLM must return.
        All fields are validated - if the response doesn't match this schema,
        the repair is rejected and fallback content is used.
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
    # Fallback when pydantic is not available
    class StructuredL3Repair:
        pass
    class ExampleRepair:
        pass


@dataclass
class RepairResult:
    """
    Result of structured repair attempt.
    
    Always provides safe fallback content even if repair fails.
    """
    repair_accepted: bool
    original_content: dict[str, Any]
    repaired_content: dict[str, Any] | None = None
    structured_repair: StructuredL3Repair | None = None
    error: str | None = None
    validation_errors: list[str] = None
    model_used: str = ""
    repair_metadata: dict[str, Any] = None
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []
        if self.repair_metadata is None:
            self.repair_metadata = {}
    
    def get_content_to_use(self) -> dict[str, Any]:
        """Get the content that should be used (repaired or original)."""
        if self.repair_accepted and self.repaired_content:
            return self.repaired_content
        return self.original_content
    
    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "repair_accepted": self.repair_accepted,
            "original_content": self.original_content,
            "repaired_content": self.repaired_content,
            "error": self.error,
            "validation_errors": self.validation_errors,
            "model_used": self.model_used,
            "repair_metadata": self.repair_metadata,
        }


# =============================================================================
# REPAIR CACHE (unchanged from original)
# =============================================================================

class RepairCache:
    """Cache for Ollama-repaired units."""
    
    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or Path.home() / ".cache" / "algl_pdf_helper" / "repairs"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.hits = 0
        self.misses = 0
        self._logger = logging.getLogger(__name__)
    
    def _get_cache_key(
        self, concept_id: str, stage: str, model: str, evidence_hash: str, prompt_version: str
    ) -> str:
        key_data = f"{concept_id}:{stage}:{model}:{evidence_hash}:{prompt_version}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]
    
    def get_cached_repair(
        self, concept_id: str, stage: str, model: str, evidence_hash: str, prompt_version: str
    ) -> dict[str, Any] | None:
        cache_key = self._get_cache_key(concept_id, stage, model, evidence_hash, prompt_version)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, encoding="utf-8") as f:
                    cached = json.load(f)
                self.hits += 1
                return cached
            except (json.JSONDecodeError, IOError):
                try:
                    cache_file.unlink()
                except OSError:
                    pass
        
        self.misses += 1
        return None
    
    def cache_repair(
        self, concept_id: str, stage: str, model: str, evidence_hash: str,
        prompt_version: str, repaired_content: dict[str, Any]
    ) -> Path:
        cache_key = self._get_cache_key(concept_id, stage, model, evidence_hash, prompt_version)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        cache_entry = {
            "_cache_metadata": {
                "concept_id": concept_id,
                "stage": stage,
                "model": model,
                "prompt_version": prompt_version,
            },
            **repaired_content,
        }
        
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_entry, f, indent=2)
            return cache_file
        except IOError:
            return cache_file


# =============================================================================
# OLLAMA REPAIR CLASS
# =============================================================================

class OllamaRepairError(Exception):
    """Base exception for Ollama repair errors."""
    pass


class OllamaRepair:
    """
    Structured repair for weak L3 content using local Ollama.
    
    Uses Qwen 3.5 9B (recommended) with strict JSON schema validation
    for reliable, parseable outputs.
    
    Example:
        >>> repair = OllamaRepair(model="qwen3.5:9b")
        >>> if repair.available:
        ...     result = repair.repair_l3_content_structured(...)
        ...     if result.repair_accepted:
        ...         content = result.get_content_to_use()
    """
    
    DEFAULT_HOST = "http://localhost:11434"
    DEFAULT_MODEL = RECOMMENDED_REPAIR_MODEL
    DEFAULT_TIMEOUT = 120
    
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        host: str = DEFAULT_HOST,
        timeout: int = DEFAULT_TIMEOUT,
        cache: RepairCache | None = None,
        auto_fallback: bool = True,
        skip_preflight: bool = False,
    ):
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.cache = cache
        self.auto_fallback = auto_fallback
        self._available: bool | None = None
        
        # Check availability and resolve model (unless skip_preflight)
        if not skip_preflight and self.available:
            self.model = self._resolve_model(model)
        else:
            self.model = model
    
    @property
    def available(self) -> bool:
        """Check if Ollama is running."""
        if self._available is None:
            self._available = self._check_availability()
        return self._available
    
    @staticmethod
    def run_preflight_check(model: str = DEFAULT_MODEL) -> tuple[bool, str]:
        """
        Static preflight check to avoid creating instance when unavailable.
        
        Args:
            model: Model name to check (not used, for compatibility)
            
        Returns:
            Tuple of (available, message)
        """
        try:
            host = "http://localhost:11434"
            req = urllib.request.Request(
                f"{host}/api/tags",
                method="GET",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status == 200:
                    return True, "Ollama available"
                return False, f"Ollama returned status {response.status}"
        except Exception as e:
            return False, f"Ollama not reachable: {e}"
    
    def _check_availability(self) -> bool:
        """Check if Ollama server is reachable."""
        try:
            req = urllib.request.Request(
                f"{self.host}/api/tags",
                method="GET",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=3) as response:
                return response.status == 200
        except Exception:
            return False
    
    def _resolve_model(self, requested_model: str) -> str:
        """Resolve model name, falling back to available models if needed."""
        available_models = self._list_available_models()
        
        if requested_model in available_models:
            return requested_model
        
        if not self.auto_fallback:
            return requested_model
        
        # Try preferred models in order
        for fallback in PREFERRED_MODELS:
            if fallback in available_models:
                logger.warning(f"Model '{requested_model}' not found, using '{fallback}'")
                return fallback
        
        # Last resort: first available
        if available_models:
            return available_models[0]
        
        return requested_model
    
    def _list_available_models(self) -> list[str]:
        """List available Ollama models."""
        try:
            req = urllib.request.Request(
                f"{self.host}/api/tags",
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
    
    def repair_l3_content_structured(
        self,
        concept_id: str,
        weak_content: dict[str, Any],
        source_evidence: str,
    ) -> RepairResult:
        """
        Repair L3 content with structured schema validation.
        
        This is the RECOMMENDED method for Week 1. It uses strict JSON schema
        validation to ensure reliable, parseable outputs.
        
        Args:
            concept_id: The concept identifier
            weak_content: Dictionary with weak/missing content fields
            source_evidence: Source text from textbook
            
        Returns:
            RepairResult with validated content or safe fallback
        """
        # Create result with original content as fallback
        original_content = {
            "concept_id": concept_id,
            **weak_content,
        }
        
        if not self.available:
            return RepairResult(
                repair_accepted=False,
                original_content=original_content,
                error="Ollama not available",
                model_used=self.model,
            )
        
        if not HAS_PYDANTIC:
            return RepairResult(
                repair_accepted=False,
                original_content=original_content,
                error="Pydantic not available for structured validation",
                model_used=self.model,
            )
        
        # Check cache
        evidence_hash = hashlib.sha256(source_evidence.encode()).hexdigest()[:16]
        if self.cache:
            cached = self.cache.get_cached_repair(
                concept_id, "L3", self.model, evidence_hash, REPAIR_PROMPT_VERSION
            )
            if cached:
                return RepairResult(
                    repair_accepted=True,
                    original_content=original_content,
                    repaired_content=cached,
                    model_used=self.model,
                    repair_metadata={"from_cache": True},
                )
        
        # Build and send structured repair request
        prompt = self._build_structured_prompt(concept_id, weak_content, source_evidence)
        
        try:
            response_text = self._call_ollama_structured(prompt)
            
            # Parse and validate against schema
            structured_repair = self._parse_structured_response(response_text)
            
            if structured_repair is None:
                return RepairResult(
                    repair_accepted=False,
                    original_content=original_content,
                    error="Failed to parse structured response",
                    model_used=self.model,
                )
            
            # Convert to content dict
            repaired_content = self._structured_to_content(structured_repair, concept_id)
            
            # Cache successful repair
            if self.cache:
                self.cache.cache_repair(
                    concept_id, "L3", self.model, evidence_hash,
                    REPAIR_PROMPT_VERSION, repaired_content
                )
            
            return RepairResult(
                repair_accepted=True,
                original_content=original_content,
                repaired_content=repaired_content,
                structured_repair=structured_repair,
                model_used=self.model,
                repair_metadata={
                    "confidence": structured_repair.confidence_score,
                    "uses_only_source": structured_repair.uses_only_source_evidence,
                    "review_flags": structured_repair.review_flags,
                },
            )
            
        except Exception as e:
            logger.warning(f"Structured repair failed for {concept_id}: {e}")
            return RepairResult(
                repair_accepted=False,
                original_content=original_content,
                error=str(e),
                model_used=self.model,
            )
    
    def _build_structured_prompt(
        self,
        concept_id: str,
        weak_content: dict[str, Any],
        evidence: str,
    ) -> str:
        """Build prompt that enforces structured JSON output."""
        config = get_model_config(self.model)
        max_evidence = config.get("context_window", 4096) - 1500
        
        if len(evidence) > max_evidence:
            evidence = evidence[:max_evidence] + "..."
        
        current_definition = weak_content.get("definition", "MISSING")
        current_why = weak_content.get("why_it_maters", "MISSING")
        
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
{evidence}

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
    
    def _call_ollama_structured(self, prompt: str) -> str:
        """Call Ollama with JSON format enforcement."""
        config = get_model_config(self.model)
        
        data = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",  # ENFORCE JSON OUTPUT
            "options": {
                "temperature": config.get("temperature", 0.1),
                "num_predict": config.get("num_predict", 800),
                "top_p": config.get("top_p", 0.9),
                "top_k": config.get("top_k", 20),
                "num_ctx": config.get("context_window", 4096),
            }
        }).encode("utf-8")
        
        req = urllib.request.Request(
            f"{self.host}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result.get("response", "")
        except socket.timeout:
            raise OllamaRepairError(f"Timeout calling Ollama model '{self.model}'")
        except Exception as e:
            raise OllamaRepairError(f"Ollama API error: {e}")
    
    def _parse_structured_response(self, response_text: str) -> StructuredL3Repair | None:
        """Parse and validate response against StructuredL3Repair schema."""
        if not HAS_PYDANTIC:
            return None
        
        try:
            # Try direct JSON parse first
            response_text = response_text.strip()
            
            # Handle markdown code blocks (defensive)
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                if end > start:
                    response_text = response_text[start:end].strip()
            elif response_text.startswith("```"):
                start = response_text.find("\n") + 1
                end = response_text.rfind("```")
                if end > start:
                    response_text = response_text[start:end].strip()
            
            # Parse JSON
            data = json.loads(response_text)
            
            # Validate against schema
            repair = StructuredL3Repair(**data)
            
            # Additional validation
            if repair.confidence_score < 0.3:
                logger.warning(f"Low confidence repair: {repair.confidence_score}")
            
            return repair
            
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in repair response: {e}")
            return None
        except ValidationError as e:
            logger.warning(f"Schema validation failed: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error parsing repair: {e}")
            return None
    
    def _structured_to_content(
        self, repair: StructuredL3Repair, concept_id: str
    ) -> dict[str, Any]:
        """Convert StructuredL3Repair to content dictionary."""
        content = {
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
    
    def assess_content_quality(
        self,
        content: dict[str, Any],
        source_blocks: list[Any] | None = None,
    ) -> float:
        """
        Assess the quality of L3 content using heuristics.
        
        This method provides a fast local quality assessment without calling Ollama.
        It uses heuristics based on content length, presence of key fields, etc.
        
        Args:
            content: Content dictionary to assess
            source_blocks: Optional source blocks for comparison (not used in heuristic mode)
            
        Returns:
            Quality score between 0.0 and 1.0
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
    
    # Legacy method for backwards compatibility
    def repair_l3_content(
        self,
        concept_id: str,
        weak_content: dict[str, Any],
        source_evidence: str,
    ) -> dict[str, Any] | None:
        """
        Legacy repair method. Use repair_l3_content_structured() instead.
        
        This method calls the structured repair and returns the repaired content
        dict for backwards compatibility.
        """
        result = self.repair_l3_content_structured(concept_id, weak_content, source_evidence)
        if result.repair_accepted:
            return result.repaired_content
        return None


def create_ollama_repair_if_enabled(
    enabled: bool = True,
    model: str = RECOMMENDED_REPAIR_MODEL,
    host: str = "http://localhost:11434",
    auto_fallback: bool = True,
) -> tuple[OllamaRepair | None, dict[str, Any]]:
    """
    Factory function to create OllamaRepair if enabled.
    
    Returns:
        Tuple of (repair_instance, status_dict)
    """
    if not enabled:
        return None, {"enabled": False, "available": False, "reason": "disabled", "disabled_reason": "disabled", "model": None}
    
    repair = OllamaRepair(model=model, host=host)
    
    if not repair.available:
        return None, {
            "enabled": True,
            "available": False,
            "reason": "ollama_not_running",
            "disabled_reason": "ollama_not_running",
            "model": None,
            "model_requested": model,
        }
    
    return repair, {
        "enabled": True,
        "available": True,
        "model": repair.model,
        "recommended_model": RECOMMENDED_REPAIR_MODEL,
        "disabled_reason": None,
    }


# =============================================================================
# SELECTIVE REPAIR PASS (for backwards compatibility)
# =============================================================================

@dataclass
class SelectiveRepairResult:
    """
    Result wrapper for selective repair pass.
    
    Provides the interface expected by unit_generator.py:
    - .repaired: bool indicating if repair was applied
    - .get_unit(): returns the (repaired or original) unit
    - .reason: string explaining the repair decision
    """
    unit: Any
    repaired: bool = False
    reason: str = ""
    error: str | None = None
    
    def get_unit(self) -> Any:
        """Get the unit (repaired or original)."""
        return self.unit


class SelectiveRepairPass:
    """
    Selective repair pass for automatic weak content detection.
    
    This class provides a wrapper around OllamaRepair for automatic
    detection and repair of weak L3 content.
    
    Example:
        >>> repair = OllamaRepair(model="qwen3.5:9b")
        >>> selective = SelectiveRepairPass(repair, repair_threshold=0.6)
        >>> result = selective.repair_if_needed(unit, source_blocks)
    """
    
    def __init__(
        self,
        ollama_repair: OllamaRepair,
        repair_threshold: float = 0.6,
    ):
        """
        Initialize selective repair pass.
        
        Args:
            ollama_repair: OllamaRepair instance
            repair_threshold: Quality threshold below which to trigger repair
        """
        self.ollama_repair = ollama_repair
        self.repair_threshold = repair_threshold
        self._logger = logging.getLogger(__name__)
    
    def repair_if_needed(
        self,
        unit: Any,
        source_blocks: list[Any],
        **kwargs,  # Accept extra params for backward compatibility (e.g., concept_id)
    ) -> SelectiveRepairResult:
        """
        Repair unit if quality is below threshold.
        
        Args:
            unit: InstructionalUnit to potentially repair
            source_blocks: Source content blocks for evidence
            **kwargs: Additional keyword arguments (ignored, for compatibility)
            
        Returns:
            SelectiveRepairResult with .repaired, .get_unit(), .reason attributes
        """
        # Handle case where ollama is not available
        if not self.ollama_repair or not self.ollama_repair.available:
            return SelectiveRepairResult(
                unit=unit,
                repaired=False,
                reason="ollama_not_available",
            )
        
        # Check if unit needs repair
        content = getattr(unit, 'content', {})
        if not isinstance(content, dict):
            return SelectiveRepairResult(
                unit=unit,
                repaired=False,
                reason="invalid_content",
            )
        
        # Assess quality
        try:
            quality = self.ollama_repair.assess_content_quality(content, source_blocks)
        except Exception as e:
            self._logger.debug(f"Quality assessment failed: {e}")
            quality = 0.5  # Default to middle quality on error
        
        if quality >= self.repair_threshold:
            return SelectiveRepairResult(
                unit=unit,
                repaired=False,
                reason="no_repair_needed",
            )
        
        # Attempt repair
        concept_id = getattr(unit, 'concept_id', 'unknown')
        weak_content = {
            "definition": content.get("definition", ""),
            "why_it_matters": content.get("why_it_matters", ""),
            "explanation": content.get("explanation", ""),
        }
        
        source_evidence = "\n\n".join(
            getattr(b, 'text_content', str(b)) for b in source_blocks
        )
        
        try:
            result = self.ollama_repair.repair_l3_content_structured(
                concept_id=concept_id,
                weak_content=weak_content,
                source_evidence=source_evidence,
            )
            
            if result.repair_accepted and result.repaired_content:
                # Update unit content
                new_content = dict(content)
                new_content.update({
                    k: v for k, v in result.repaired_content.items()
                    if k not in ('_cache_metadata',)
                })
                
                # Update metadata
                if "_metadata" not in new_content:
                    new_content["_metadata"] = {}
                new_content["_metadata"].update({
                    "_repaired_by_ollama": True,
                    "_repair_model": result.model_used,
                    "content_quality": "repaired",
                })
                
                # Create updated unit
                from dataclasses import replace
                repaired_unit = replace(unit, content=new_content)
                
                return SelectiveRepairResult(
                    unit=repaired_unit,
                    repaired=True,
                    reason=f"repair_applied (confidence: {result.repair_metadata.get('confidence', 'unknown')})",
                )
            else:
                # Repair attempted but not accepted
                return SelectiveRepairResult(
                    unit=unit,
                    repaired=False,
                    reason=f"repair_rejected: {result.error or 'validation_failed'}",
                    error=result.error,
                )
        
        except Exception as e:
            self._logger.warning(f"Repair failed for {concept_id}: {e}")
            return SelectiveRepairResult(
                unit=unit,
                repaired=False,
                reason="repair_exception",
                error=str(e),
            )
    
    def assess_quality(
        self,
        content: dict[str, Any],
        source_blocks: list[Any],
    ) -> float:
        """Assess content quality."""
        if not self.ollama_repair:
            return 0.5
        try:
            return self.ollama_repair.assess_content_quality(content, source_blocks)
        except Exception as e:
            self._logger.debug(f"Quality assessment failed: {e}")
            return 0.5
