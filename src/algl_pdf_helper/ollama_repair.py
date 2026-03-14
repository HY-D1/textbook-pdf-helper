"""
Ollama-based Repair Pass for Weak/Missing L3 Content.

This module provides a repair mechanism for instructional units where L3 content
is weak or missing due to insufficient textbook evidence. It uses a local Ollama
instance to improve content quality based on available source evidence.

The repair pass is designed to:
- Only run for flagged weak concepts (not all units)
- Use local models like qwen2.5:3b (M1 Pro compatible)
- Base repairs on source evidence (avoid hallucination)
- Fall back gracefully if Ollama is unavailable

Usage:
    from algl_pdf_helper.ollama_repair import OllamaRepair, SelectiveRepairPass, RepairCache
    
    repair = OllamaRepair(model="qwen2.5:3b")
    if repair.available:
        repaired_content = repair.repair_l3_content(
            concept_id="joins",
            weak_content={"definition": "Weak definition...", "why_it_matters": ""},
            source_evidence="Textbook content..."
        )
    
    # Or use the selective repair pass for automatic detection
    selective_pass = SelectiveRepairPass(repair)
    repair_result = selective_pass.repair_if_needed(unit, source_blocks)
    
    # Cache management
    cache = RepairCache()
    cache.clear_cache()  # Clear all cached repairs
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from algl_pdf_helper.instructional_models import InstructionalUnit


logger = logging.getLogger(__name__)

# Prompt version for cache invalidation - bump when prompt changes
REPAIR_PROMPT_VERSION = "v2.1.0-rtx4080"

# Preferred models for RTX 4080 optimization (in order of preference)
PREFERRED_MODELS = [
    "qwen3.5:9b-q8_0",
    "qwen3.5:27b-q4_K_M",
    "qwen3-coder:30b",
    "glm-4.7-flash:latest",
]

# Model-specific configurations for RTX 4080 (16GB VRAM)
MODEL_CONFIGS: dict[str, dict[str, Any]] = {
    "qwen3.5:9b-q8_0": {
        "context_window": 8192,
        "temperature": 0.2,
        "top_p": 0.85,
        "top_k": 30,
        "num_predict": 600,
        "description": "Fast, high-quality 9B model with 8-bit quantization",
    },
    "qwen3.5:27b-q4_K_M": {
        "context_window": 4096,
        "temperature": 0.2,
        "top_p": 0.85,
        "top_k": 30,
        "num_predict": 600,
        "description": "Large 27B model with 4-bit quantization",
    },
    "qwen3-coder:30b": {
        "context_window": 4096,
        "temperature": 0.15,
        "top_p": 0.80,
        "top_k": 25,
        "num_predict": 700,
        "description": "Code-specialized 30B model for SQL generation",
    },
    "glm-4.7-flash:latest": {
        "context_window": 8192,
        "temperature": 0.2,
        "top_p": 0.85,
        "top_k": 30,
        "num_predict": 600,
        "description": "Fast GLM model for quick repairs",
    },
    "qwen2.5:3b": {
        "context_window": 4096,
        "temperature": 0.3,
        "top_p": 0.90,
        "top_k": 40,
        "num_predict": 500,
        "description": "Small, fast model for testing (fallback)",
    },
}

# Default config for unknown models
DEFAULT_MODEL_CONFIG = {
    "context_window": 4096,
    "temperature": 0.3,
    "top_p": 0.90,
    "top_k": 40,
    "num_predict": 500,
    "description": "Default configuration",
}


def get_model_config(model_name: str) -> dict[str, Any]:
    """Get configuration for specific model, falling back to default."""
    # Try exact match first
    if model_name in MODEL_CONFIGS:
        return MODEL_CONFIGS[model_name]
    
    # Try partial match (e.g., "qwen3.5:9b" matches "qwen3.5:9b-q8_0")
    for key in MODEL_CONFIGS:
        if key in model_name or model_name.startswith(key.split(":")[0]):
            return MODEL_CONFIGS[key]
    
    return DEFAULT_MODEL_CONFIG


class RepairCache:
    """
    Cache for Ollama-repaired units.
    
    Caches successful repairs to avoid regenerating the same content
    across pipeline runs. Cache keys are based on concept_id, stage,
    model, evidence hash, and prompt version for cache invalidation.
    
    Attributes:
        cache_dir: Directory where cache files are stored
        hits: Number of cache hits (for statistics)
        misses: Number of cache misses (for statistics)
    
    Example:
        >>> cache = RepairCache()
        >>> cached = cache.get_cached_repair("joins", "L3", "qwen2.5:3b", "abc123", "v1.0")
        >>> if cached:
        ...     print("Cache hit!")
        >>> else:
        ...     # Generate repair, then cache it
        ...     cache.cache_repair("joins", "L3", "qwen2.5:3b", "abc123", "v1.0", repaired_content)
    """
    
    def __init__(self, cache_dir: Path | None = None):
        """
        Initialize the repair cache.
        
        Args:
            cache_dir: Directory for cache files (default: ~/.cache/algl_pdf_helper/repairs)
        """
        self.cache_dir = cache_dir or Path.home() / ".cache" / "algl_pdf_helper" / "repairs"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.hits = 0
        self.misses = 0
        self._logger = logging.getLogger(__name__)
    
    def _get_cache_key(
        self,
        concept_id: str,
        stage: str,
        model: str,
        evidence_hash: str,
        prompt_version: str,
    ) -> str:
        """Generate cache key from repair parameters."""
        key_data = f"{concept_id}:{stage}:{model}:{evidence_hash}:{prompt_version}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]
    
    def get_cached_repair(
        self,
        concept_id: str,
        stage: str,
        model: str,
        evidence_hash: str,
        prompt_version: str = REPAIR_PROMPT_VERSION,
    ) -> dict[str, Any] | None:
        """
        Get cached repair if available.
        
        Returns:
            Cached repair content dict, or None if not in cache
        """
        cache_key = self._get_cache_key(concept_id, stage, model, evidence_hash, prompt_version)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, encoding="utf-8") as f:
                    cached = json.load(f)
                self.hits += 1
                self._logger.debug(f"Cache hit for {concept_id}/{stage}: {cache_key}")
                return cached
            except (json.JSONDecodeError, IOError) as e:
                self._logger.warning(f"Failed to read cache file {cache_file}: {e}")
                try:
                    cache_file.unlink()
                except OSError:
                    pass
        
        self.misses += 1
        return None
    
    def cache_repair(
        self,
        concept_id: str,
        stage: str,
        model: str,
        evidence_hash: str,
        prompt_version: str,
        repaired_content: dict[str, Any],
    ) -> Path:
        """Cache a successful repair."""
        cache_key = self._get_cache_key(concept_id, stage, model, evidence_hash, prompt_version)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        cache_entry = {
            "_cache_metadata": {
                "concept_id": concept_id,
                "stage": stage,
                "model": model,
                "prompt_version": prompt_version,
                "cache_key": cache_key,
            },
            **repaired_content,
        }
        
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_entry, f, indent=2)
            self._logger.debug(f"Cached repair for {concept_id}/{stage}: {cache_key}")
            return cache_file
        except IOError as e:
            self._logger.warning(f"Failed to write cache file {cache_file}: {e}")
            return cache_file
    
    def clear_cache(self) -> int:
        """Clear all cached repairs."""
        count = 0
        if self.cache_dir.exists():
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    cache_file.unlink()
                    count += 1
                except OSError as e:
                    self._logger.warning(f"Failed to remove cache file {cache_file}: {e}")
        
        self._logger.info(f"Cleared {count} cached repairs from {self.cache_dir}")
        return count
    
    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        cache_files = list(self.cache_dir.glob("*.json")) if self.cache_dir.exists() else []
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0,
            "cached_files": len(cache_files),
            "cache_dir": str(self.cache_dir),
            "total_size_bytes": total_size,
        }


class OllamaRepairError(Exception):
    """Base exception for Ollama repair errors."""
    pass


class OllamaModelNotFoundError(OllamaRepairError):
    """Raised when the specified model is not found in Ollama."""
    
    def __init__(self, model: str, available: list[str]):
        self.model = model
        self.available = available
        super().__init__(
            f"Model '{model}' not found. Available models: {available}. "
            f"Use --ollama-model to specify a different model."
        )


class OllamaTimeoutError(OllamaRepairError):
    """Raised when Ollama request times out."""
    
    def __init__(self, model: str):
        self.model = model
        super().__init__(
            f"Ollama timeout for model '{model}'. "
            f"Model may be loading or too large for GPU. "
            f"First call after Ollama start may be slow as model loads into VRAM."
        )


class RepairValidator:
    """Validates repairs and handles quality checks."""
    
    @staticmethod
    def validate_repair_output(output: dict[str, Any], concept_id: str) -> tuple[bool, list[str]]:
        """
        Validate the repair output from Ollama.
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check required fields
        required_fields = ["definition"]
        for field in required_fields:
            if field not in output or not output[field]:
                issues.append(f"missing_{field}")
        
        # Check definition quality
        definition = output.get("definition", "")
        if len(definition) < 20:
            issues.append("definition_too_short")
        if definition.isupper():
            issues.append("definition_is_heading")
        
        # Check for generic phrases
        generic_phrases = [
            "is an important SQL concept",
            "is a crucial SQL concept",
            "is an essential SQL concept",
        ]
        for phrase in generic_phrases:
            if phrase in definition.lower():
                issues.append(f"generic_definition_contains_{phrase.replace(' ', '_')}")
        
        # Check hallucination indicators
        hallucination_indicators = [
            "according to the source",
            "the textbook states",
            "as mentioned in",
        ]
        for indicator in hallucination_indicators:
            if indicator in definition.lower():
                issues.append(f"possible_hallucination_{indicator.replace(' ', '_')}")
        
        return len(issues) == 0, issues


class OllamaRepair:
    """
    Repair weak L3 content using local Ollama.
    
    This class provides methods to check Ollama availability and repair
    weak instructional content using local LLM models. It's designed as
    a "repair pass" that only runs when content is flagged as weak,
    not as a primary content generator.
    
    Attributes:
        model: The Ollama model to use (default: "qwen2.5:3b")
        host: The Ollama API host URL (default: "http://localhost:11434")
        available: Whether Ollama server is available and reachable
    
    Example:
        >>> repair = OllamaRepair(model="qwen2.5:3b")
        >>> if repair.available:
        ...     result = repair.repair_l3_content(
        ...         concept_id="joins",
        ...         weak_content={"definition": "Weak..."},
        ...         source_evidence="Textbook content..."
        ...     )
    """
    
    # Class-level state for run-level availability tracking
    _preflight_completed = False
    _preflight_available = False
    _preflight_logged = False
    _available_models: list[str] | None = None
    
    @classmethod
    def run_preflight_check(cls, host: str = "http://localhost:11434", model: str = "qwen2.5:3b") -> tuple[bool, str | None]:
        """
        Run a one-time preflight check for Ollama availability.
        
        This should be called once at the start of the pipeline to check
        Ollama availability. Subsequent instances will use this cached result.
        
        Args:
            host: Ollama API host URL
            model: Model to check availability for
            
        Returns:
            Tuple of (is_available, disabled_reason)
            - is_available: True if Ollama is available
            - disabled_reason: None if available, or reason string (e.g., "ollama_not_running")
        """
        if cls._preflight_completed:
            return cls._preflight_available, None if cls._preflight_available else "ollama_not_running"
        
        cls._preflight_completed = True
        
        # Try to connect to Ollama
        try:
            import urllib.request
            import json
            req = urllib.request.Request(
                f"{host}/api/tags",
                method="GET",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    models = data.get("models", [])
                    cls._available_models = [m.get("name", "") for m in models if m.get("name")]
                    
                    # Check if requested model is available
                    model_available = any(
                        model in m or m.startswith(model.split(":")[0])
                        for m in cls._available_models
                    )
                    
                    if model_available or cls._available_models:
                        cls._preflight_available = True
                        logger.info(f"Ollama repair available with {len(cls._available_models)} models")
                        return True, None
                    else:
                        cls._preflight_available = False
                        if not cls._preflight_logged:
                            logger.warning("Ollama running but no models found - repair disabled")
                            cls._preflight_logged = True
                        return False, "no_models_available"
                        
        except Exception as e:
            cls._preflight_available = False
            if not cls._preflight_logged:
                logger.warning(f"Ollama repair enabled but server not available at {host}")
                cls._preflight_logged = True
            return False, "ollama_not_running"
        
        return False, "unknown_error"
    
    @classmethod
    def reset_preflight(cls) -> None:
        """Reset the preflight check state (for testing)."""
        cls._preflight_completed = False
        cls._preflight_available = False
        cls._preflight_logged = False
        cls._available_models = None
    
    def __init__(
        self,
        model: str = "qwen2.5:3b",
        host: str = "http://localhost:11434",
        timeout: int = 120,
        cache: RepairCache | None = None,
        auto_fallback: bool = True,
        skip_preflight: bool = False,
    ):
        """
        Initialize OllamaRepair with model and host configuration.
        
        Args:
            model: The Ollama model name to use for repairs
            host: The Ollama API host URL
            timeout: Request timeout in seconds (default 120 for large models)
            cache: Optional RepairCache instance for caching repairs
            auto_fallback: Whether to automatically fallback to available models
            skip_preflight: If True, don't run preflight check (use cached result)
        """
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.cache = cache
        self.auto_fallback = auto_fallback
        self._model_loaded = False
        
        # Run preflight if not already done and not skipped
        if not skip_preflight and not OllamaRepair._preflight_completed:
            OllamaRepair.run_preflight_check(self.host, model)
        
        # Use preflight result for availability
        self.available = OllamaRepair._preflight_available
        
        if self.available:
            # Validate model and potentially fallback
            self.model = self._resolve_model(model)
            # Check if model is loaded (warn if not)
            self._check_model_loaded()
        else:
            # Set model but won't be used
            self.model = model
    
    def _resolve_model(self, requested_model: str) -> str:
        """
        Resolve model name, falling back to available models if needed.
        
        Args:
            requested_model: The originally requested model name
            
        Returns:
            The resolved model name (may be different if fallback occurred)
        """
        is_valid, available_models = self._validate_model(requested_model)
        
        if is_valid:
            return requested_model
        
        if not self.auto_fallback:
            raise OllamaModelNotFoundError(requested_model, available_models)
        
        # Try fallback models in order
        models_to_try = [m for m in PREFERRED_MODELS if m != requested_model]
        
        for fallback_model in models_to_try:
            if fallback_model in available_models:
                logger.warning(
                    f"Model '{requested_model}' not found. "
                    f"Auto-fallback to '{fallback_model}'."
                )
                return fallback_model
        
        # Try any available model as last resort
        if available_models:
            fallback = available_models[0]
            logger.warning(
                f"Model '{requested_model}' not found. "
                f"Falling back to first available: '{fallback}'."
            )
            return fallback
        
        # No models available - return original and let it fail later
        logger.error(f"No models available in Ollama. Requested: {requested_model}")
        return requested_model
    
    def _validate_model(self, model_name: str) -> tuple[bool, list[str]]:
        """
        Check if model exists in Ollama, return available models if not.
        
        Args:
            model_name: The model name to validate
            
        Returns:
            Tuple of (is_valid, available_models)
        """
        try:
            available_models = self._list_available_models()
            
            # Check exact match or match without tag
            if model_name in available_models:
                return True, available_models
            
            # Check if model name matches the start of any available model
            # (handles cases like "qwen2.5:3b" matching "qwen2.5:3b-16k")
            for available in available_models:
                if available.startswith(model_name) or model_name.startswith(available.split(":")[0]):
                    return True, available_models
            
            return False, available_models
            
        except Exception as e:
            logger.debug(f"Could not validate model (Ollama may be unavailable): {e}")
            # Return True to let it try - actual error will happen at call time
            return True, []
    
    def _list_available_models(self) -> list[str]:
        """
        List all available models in Ollama.
        
        Returns:
            List of model names available in Ollama
        """
        try:
            req = urllib.request.Request(
                f"{self.host}/api/tags",
                method="GET",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    models = data.get("models", [])
                    model_names = [m.get("name", "") for m in models if m.get("name")]
                    # Cache for later use
                    OllamaRepair._available_models = model_names
                    return model_names
        except Exception as e:
            logger.debug(f"Failed to list models: {e}")
        
        return OllamaRepair._available_models or []
    
    def _check_model_loaded(self) -> bool:
        """
        Check if the current model is already loaded in Ollama.
        
        Returns:
            True if model is loaded, False otherwise
        """
        try:
            req = urllib.request.Request(
                f"{self.host}/api/ps",
                method="GET",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    running_models = data.get("models", [])
                    for m in running_models:
                        if m.get("name") == self.model or m.get("model") == self.model:
                            self._model_loaded = True
                            return True
                    
                    # Model not loaded - warn user
                    if not self._model_loaded:
                        logger.warning(
                            f"Model '{self.model}' is not currently loaded. "
                            f"First call may be slow as model loads into GPU memory."
                        )
                    return False
        except Exception as e:
            logger.debug(f"Could not check loaded models: {e}")
        return False
    

    
    def _check_availability(self) -> bool:
        """
        Check if Ollama server is running and reachable.
        
        Returns:
            True if Ollama is available, False otherwise
        """
        try:
            req = urllib.request.Request(
                f"{self.host}/api/tags",
                method="GET",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
                    # Check if our model is available
                    data = json.loads(response.read().decode())
                    models = data.get("models", [])
                    model_names = [m.get("name", "") for m in models]
                    if self.model in model_names or any(
                        self.model in name for name in model_names
                    ):
                        logger.debug(f"Model {self.model} is available")
                        return True
                    else:
                        logger.warning(
                            f"Model {self.model} not found in Ollama. "
                            f"Available models: {model_names}"
                        )
                        # Still return True as we can try to pull it
                        return True
        except urllib.error.URLError as e:
            logger.debug(f"Ollama availability check failed: {e}")
        except Exception as e:
            logger.debug(f"Unexpected error checking Ollama: {e}")
        return False
    
    def _get_model_config(self) -> dict[str, Any]:
        """
        Get configuration for the current model.
        
        Returns:
            Configuration dictionary with context window, temperature, etc.
        """
        return get_model_config(self.model)
    
    def repair_l3_content(
        self,
        concept_id: str,
        weak_content: dict[str, Any],
        source_evidence: str,
    ) -> dict[str, Any] | None:
        """
        Repair weak L3 content using retrieved evidence.
        
        This method takes weak or missing L3 content and attempts to improve
        it using the local Ollama model, based strictly on the provided
        source evidence.
        
        Args:
            concept_id: The concept identifier (e.g., "joins", "subqueries")
            weak_content: Dictionary containing weak/missing content fields
                Expected keys: "definition", "why_it_matters", "explanation"
            source_evidence: Source text from textbook to base repairs on
        
        Returns:
            Dictionary with repaired content fields, or None if repair failed.
            The returned dict may include a "_repaired_by_ollama" flag set to True.
        
        Example:
            >>> repaired = repair.repair_l3_content(
            ...     concept_id="joins",
            ...     weak_content={
            ...         "definition": "JOIN combines tables.",
            ...         "why_it_matters": "",
            ...     },
            ...     source_evidence="JOIN operations combine rows from tables..."
            ... )
        """
        if not self.available:
            logger.debug(f"Ollama not available, skipping repair for {concept_id}")
            return None
        
        # Check cache first
        if self.cache:
            evidence_hash = hashlib.sha256(source_evidence.encode()).hexdigest()[:16]
            cached = self.cache.get_cached_repair(
                concept_id, "L3", self.model, evidence_hash, REPAIR_PROMPT_VERSION
            )
            if cached:
                logger.debug(f"Using cached repair for {concept_id}")
                return cached
        
        prompt = self._build_repair_prompt(concept_id, weak_content, source_evidence)
        
        try:
            response = self._call_ollama(prompt)
            if response:
                parsed = self._parse_repair_response(response)
                if parsed:
                    # Validate the repair
                    is_valid, issues = RepairValidator.validate_repair_output(parsed, concept_id)
                    if not is_valid:
                        logger.warning(f"Repair validation failed for {concept_id}: {issues}")
                    
                    parsed["_repaired_by_ollama"] = True
                    parsed["_repair_model"] = self.model
                    
                    # Cache the repair
                    if self.cache:
                        self.cache.cache_repair(
                            concept_id, "L3", self.model, evidence_hash,
                            REPAIR_PROMPT_VERSION, parsed
                        )
                    
                    logger.info(f"Successfully repaired L3 content for {concept_id}")
                    return parsed
        except OllamaModelNotFoundError as e:
            logger.error(str(e))
        except OllamaTimeoutError as e:
            logger.error(str(e))
        except Exception as e:
            logger.warning(f"Ollama repair failed for {concept_id}: {e}")
        
        return None
    
    def _build_repair_prompt(
        self,
        concept_id: str,
        weak_content: dict[str, Any],
        evidence: str,
    ) -> str:
        """
        Build prompt for Ollama repair.
        
        Creates a structured prompt that guides the LLM to improve content
        based strictly on the provided source evidence.
        
        Args:
            concept_id: The concept identifier
            weak_content: Dictionary with current weak content
            evidence: Source text evidence from textbook
        
        Returns:
            Formatted prompt string for the LLM
        """
        config = self._get_model_config()
        max_evidence_chars = config.get("context_window", 4096) - 1000  # Reserve space for prompt
        
        # Truncate evidence to avoid token limits
        if len(evidence) > max_evidence_chars:
            evidence = evidence[:max_evidence_chars] + "..."
        
        # Format current content for context
        current_definition = weak_content.get("definition", "MISSING")
        current_why = weak_content.get("why_it_matters", "MISSING")
        
        return f"""You are an expert SQL educator improving a tutorial. Your task is to rewrite weak content to be clear and helpful for students learning SQL.

CONCEPT: {concept_id}

SOURCE EVIDENCE (use ONLY this information):
{evidence}

CURRENT WEAK CONTENT:
- Definition: {current_definition}
- Why it matters: {current_why}

INSTRUCTIONS:
1. Rewrite the definition to be clear, accurate, and educational (1-2 sentences)
2. Explain why students should care about this concept (1-2 sentences)
3. Use ONLY the source evidence provided - do not invent new facts
4. Write for beginner-to-intermediate SQL students
5. Use plain English, avoid unnecessary jargon

OUTPUT FORMAT (JSON only):
{{
  "definition": "Clear 1-2 sentence definition based on source",
  "why_it_matters": "Why students should care, 1-2 sentences",
  "explanation": "Detailed explanation using source evidence (2-3 sentences)"
}}

Return ONLY valid JSON, no markdown code blocks, no extra commentary."""
    
    def _call_ollama(self, prompt: str) -> str:
        """
        Call Ollama API with the given prompt.
        
        Args:
            prompt: The prompt to send to Ollama
        
        Returns:
            The raw response text from Ollama
        
        Raises:
            OllamaModelNotFoundError: If model is not found (404)
            OllamaTimeoutError: If request times out
            urllib.error.URLError: If connection fails
            json.JSONDecodeError: If response parsing fails
        """
        config = self._get_model_config()
        
        data = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": config.get("temperature", 0.3),
                "num_predict": config.get("num_predict", 500),
                "top_p": config.get("top_p", 0.9),
                "top_k": config.get("top_k", 40),
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
        except urllib.error.HTTPError as e:
            if e.code == 404:
                available = self._list_available_models()
                raise OllamaModelNotFoundError(self.model, available) from e
            raise
        except socket.timeout:
            raise OllamaTimeoutError(self.model)
        except urllib.error.URLError as e:
            if "timed out" in str(e).lower():
                raise OllamaTimeoutError(self.model) from e
            raise
    
    def _parse_repair_response(self, response: str) -> dict[str, Any] | None:
        """
        Parse JSON from Ollama response.
        
        Handles various response formats including markdown code blocks.
        
        Args:
            response: Raw response text from Ollama
        
        Returns:
            Parsed dictionary or None if parsing fails
        """
        try:
            # Try to find JSON in the response
            response = response.strip()
            
            # Handle markdown code blocks
            if "```json" in response:
                match = response.find("```json")
                end_match = response.find("```", match + 7)
                if end_match > match:
                    response = response[match + 7:end_match].strip()
            elif "```" in response:
                match = response.find("```")
                end_match = response.find("```", match + 3)
                if end_match > match:
                    response = response[match + 3:end_match].strip()
            
            # Find JSON object if embedded in other text
            json_start = response.find("{")
            json_end = response.rfind("}")
            if json_start >= 0 and json_end > json_start:
                response = response[json_start:json_end + 1]
            
            parsed = json.loads(response)
            
            # Validate required fields
            if "definition" not in parsed:
                logger.warning("Ollama response missing 'definition' field")
                return None
            
            return parsed
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from Ollama response: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error parsing Ollama response: {e}")
            return None
    
    def assess_content_quality(self, content: dict[str, Any], blocks: list) -> float:
        """
        Assess L3 content quality on a 0-1 scale.
        
        This is a heuristic quality assessment that checks:
        - Definition length and quality
        - Presence of real examples vs synthetic
        - Amount of source evidence
        
        Args:
            content: The L3 content dictionary
            blocks: Source content blocks
        
        Returns:
            Quality score between 0.0 and 1.0
        """
        score = 0.0
        
        # Check definition quality
        definition = content.get("definition", "")
        if len(definition) > 100:
            score += 0.3
        if len(definition) > 50:
            score += 0.1
        # Penalize generic definitions
        if "is an important SQL concept" in definition.lower():
            score -= 0.2
        if "is a crucial SQL concept" in definition.lower():
            score -= 0.2
        
        # Check why_it_matters quality
        why_it_matters = content.get("why_it_matters", "")
        if len(why_it_matters) > 50:
            score += 0.2
        
        # Check examples
        examples = content.get("examples", [])
        if examples:
            real_examples = sum(
                1 for ex in examples 
                if not ex.get("is_synthetic", True)
            )
            score += min(real_examples * 0.15, 0.3)
        
        # Check evidence quantity
        if len(blocks) > 5:
            score += 0.2
        elif len(blocks) > 2:
            score += 0.1
        
        # Clamp to 0-1 range
        return max(0.0, min(1.0, score))


def create_ollama_repair_if_enabled(
    enabled: bool = True,
    model: str = "qwen2.5:3b",
    host: str = "http://localhost:11434",
    auto_fallback: bool = True,
    preflight_available: bool | None = None,
) -> tuple[OllamaRepair | None, dict[str, Any]]:
    """
    Create OllamaRepair instance if enabled and available.
    
    This is a convenience factory function that handles the common case
    of creating a repair instance conditionally.
    
    Args:
        enabled: Whether repair is enabled in configuration
        model: Ollama model to use
        host: Ollama API host
        auto_fallback: Whether to automatically fallback to available models
        preflight_available: Optional preflight result to avoid re-checking
    
    Returns:
        Tuple of (repair_instance, status_dict)
        - repair_instance: OllamaRepair if enabled and available, None otherwise
        - status_dict: Dict with keys: enabled, available, disabled_reason, model
    
    Example:
        >>> repair, status = create_ollama_repair_if_enabled(
        ...     enabled=config.use_ollama_repair,
        ...     model=config.ollama_model
        ... )
        >>> if repair:
        ...     print(f"Repair available with model: {status['model']}")
    """
    status = {
        "enabled": enabled,
        "available": False,
        "disabled_reason": None,
        "model": model,
    }
    
    if not enabled:
        status["disabled_reason"] = "user_disabled"
        logger.debug("Ollama repair disabled by configuration")
        return None, status
    
    # Run preflight check if not already done and no result provided
    if preflight_available is None and not OllamaRepair._preflight_completed:
        available, reason = OllamaRepair.run_preflight_check(host, model)
        preflight_available = available
        if not available:
            status["disabled_reason"] = reason or "ollama_not_running"
    
    # If preflight shows unavailable, return None without logging
    if preflight_available is False:
        status["disabled_reason"] = "ollama_not_running"
        return None, status
    
    try:
        repair = OllamaRepair(
            model=model,
            host=host,
            auto_fallback=auto_fallback,
            skip_preflight=True,  # Already done above
        )
        if repair.available:
            status["available"] = True
            status["model"] = repair.model  # May have changed due to fallback
            return repair, status
        else:
            status["disabled_reason"] = "ollama_not_available"
    except OllamaModelNotFoundError as e:
        logger.error(str(e))
        status["disabled_reason"] = f"model_not_found: {e.model}"
    except Exception as e:
        logger.warning(f"Failed to create OllamaRepair: {e}")
        status["disabled_reason"] = f"error: {e}"
    
    return None, status


@dataclass
class RepairResult:
    """
    Result of a repair attempt.
    
    Attributes:
        repaired: Whether the unit was successfully repaired
        reason: Reason for repair or non-repair
        original_unit: The original unit before repair
        repaired_unit: The repaired unit (if repaired=True)
    """
    repaired: bool
    reason: str
    original_unit: InstructionalUnit
    repaired_unit: InstructionalUnit | None = None
    
    def get_unit(self) -> InstructionalUnit:
        """Get the best available unit (repaired or original)."""
        return self.repaired_unit or self.original_unit


class SelectiveRepairPass:
    """
    Selective repair pass for weak instructional units.
    
    This class provides intelligent detection of weak units and applies
    targeted repairs using Ollama when available. It's designed to be
    conservative and evidence-based, only repairing units that meet
    specific quality criteria.
    
    Attributes:
        ollama_repair: OllamaRepair instance for LLM-based repairs
        repair_threshold: Quality score threshold below which to trigger repair
        max_repairs_per_run: Maximum number of units to repair in one pass
    
    Example:
        >>> repair = OllamaRepair(model="qwen2.5:3b")
        >>> selective = SelectiveRepairPass(repair, repair_threshold=0.6)
        >>> result = selective.repair_if_needed(unit, source_blocks)
        >>> if result.repaired:
        ...     print(f"Repaired: {result.reason}")
    """
    
    def __init__(
        self,
        ollama_repair: OllamaRepair,
        repair_threshold: float = 0.6,
        max_repairs_per_run: int = 50,
    ):
        """
        Initialize the selective repair pass.
        
        Args:
            ollama_repair: OllamaRepair instance
            repair_threshold: Quality score threshold (0.0-1.0) for triggering repair
            max_repairs_per_run: Maximum number of repairs to perform in one run
        """
        self.ollama_repair = ollama_repair
        self.repair_threshold = repair_threshold
        self.max_repairs_per_run = max_repairs_per_run
        self._repair_count = 0
    
    def repair_if_needed(
        self,
        unit: InstructionalUnit,
        source_blocks: list[Any],
        concept_id: str | None = None,
    ) -> "RepairResult":
        """
        Check if unit needs repair and apply repair if necessary.
        
        Args:
            unit: The instructional unit to check and potentially repair
            source_blocks: Source content blocks for evidence
            concept_id: Optional concept ID override (defaults to unit.concept_id)
        
        Returns:
            RepairResult with repair status and metadata
        """
        # Check if Ollama is available
        if not self.ollama_repair.available:
            return RepairResult(
                repaired=False,
                reason="ollama_not_available",
                original_unit=unit,
            )
        
        # Check repair limit
        if self._repair_count >= self.max_repairs_per_run:
            logger.debug(f"Max repairs reached ({self.max_repairs_per_run}), skipping")
            return RepairResult(
                repaired=False,
                reason="max_repairs_reached",
                original_unit=unit,
            )
        
        concept_id = concept_id or unit.concept_id
        
        # Check if unit needs repair
        needs_repair, repair_reasons = self._check_needs_repair(unit, source_blocks)
        
        if not needs_repair:
            return RepairResult(
                repaired=False,
                reason="no_repair_needed",
                original_unit=unit,
            )
        
        # Apply appropriate repair based on unit type
        repaired_unit = self._apply_repair(unit, source_blocks, concept_id, repair_reasons)
        
        if repaired_unit:
            self._repair_count += 1
            return RepairResult(
                repaired=True,
                reason="|".join(repair_reasons),
                original_unit=unit,
                repaired_unit=repaired_unit,
            )
        
        return RepairResult(
            repaired=False,
            reason="repair_failed",
            original_unit=unit,
        )
    
    def _check_needs_repair(
        self,
        unit: InstructionalUnit,
        source_blocks: list[Any],
    ) -> tuple[bool, list[str]]:
        """
        Check if a unit needs repair based on quality criteria.
        
        Repair triggers (unit needs repair if ANY are true):
        - Missing L3 content (no L3 unit generated)
        - Low evidence count (< 2 source blocks)
        - Default L2 example used (has metadata flag used_default_example)
        - Placeholder practice links (needs_resolution=True)
        - Low quality score (< repair_threshold)
        - Heading-like definition (starts with "Section" or "Chapter")
        
        Args:
            unit: The instructional unit to check
            source_blocks: Source content blocks
        
        Returns:
            Tuple of (needs_repair, list_of_reasons)
        """
        reasons = []
        content = unit.content
        
        # Check 1: Low evidence count (< 2 source blocks)
        if len(source_blocks) < 2:
            reasons.append("low_evidence_count")
        
        # Check 2: Default L2 example used
        if content.get("used_default_example"):
            reasons.append("default_l2_example")
        
        # Check 3: Placeholder practice links
        practice_links = content.get("practice_links", [])
        for link in practice_links:
            if isinstance(link, dict) and link.get("needs_resolution"):
                reasons.append("placeholder_practice_links")
                break
        
        # Check 4: Low quality score
        quality_score = self._assess_unit_quality(unit, source_blocks)
        if quality_score < self.repair_threshold:
            reasons.append(f"low_quality_score_{quality_score:.2f}")
        
        # Check 5: Heading-like definition
        definition = content.get("definition", "")
        if self._is_heading_like_definition(definition):
            reasons.append("heading_like_definition")
        
        # Check 6: Missing critical L3 content
        if unit.target_stage == "L3_explanation":
            if not content.get("definition") or len(content.get("definition", "")) < 50:
                reasons.append("missing_l3_definition")
            if not content.get("why_it_matters"):
                reasons.append("missing_l3_why_it_matters")
            if not content.get("examples") or len(content.get("examples", [])) < 1:
                reasons.append("missing_l3_examples")
        
        return len(reasons) > 0, reasons
    
    def _assess_unit_quality(
        self,
        unit: InstructionalUnit,
        source_blocks: list[Any],
    ) -> float:
        """
        Assess unit quality on a 0-1 scale.
        
        Args:
            unit: The instructional unit to assess
            source_blocks: Source content blocks
        
        Returns:
            Quality score between 0.0 and 1.0
        """
        score = 0.0
        content = unit.content
        
        # Definition quality
        definition = content.get("definition", "")
        if len(definition) > 100:
            score += 0.3
        elif len(definition) > 50:
            score += 0.15
        
        # Why it matters quality
        why_it_matters = content.get("why_it_matters", "")
        if len(why_it_matters) > 50:
            score += 0.2
        
        # Examples quality
        examples = content.get("examples", [])
        if examples:
            real_examples = sum(
                1 for ex in examples 
                if not ex.get("is_synthetic", True)
            )
            score += min(real_examples * 0.15, 0.3)
        
        # Evidence quantity
        if len(source_blocks) > 5:
            score += 0.2
        elif len(source_blocks) > 2:
            score += 0.1
        
        # Check for generic/placeholder content
        generic_phrases = [
            "is an important SQL concept",
            "is a crucial SQL concept",
            "is an essential SQL concept",
            "is a fundamental SQL concept",
        ]
        for phrase in generic_phrases:
            if phrase in definition.lower():
                score -= 0.3
                break
        
        return max(0.0, min(1.0, score))
    
    def _is_heading_like_definition(self, text: str) -> bool:
        """
        Check if definition looks like a heading rather than content.
        
        Args:
            text: The definition text to check
        
        Returns:
            True if the text looks like a heading
        """
        if not text:
            return True
        
        text_stripped = text.strip()
        text_lower = text.lower()
        
        # Check for chapter/section patterns
        heading_patterns = [
            r'^Chapter\s+\d+',
            r'^Section\s+\d+',
            r'^Unit\s+\d+',
            r'^Module\s+\d+',
            r'^Lesson\s+\d+',
            r'^Part\s+\d+',
        ]
        for pattern in heading_patterns:
            if re.match(pattern, text_stripped, re.IGNORECASE):
                return True
        
        # All-caps is likely a heading
        if text_stripped.isupper():
            return True
        
        # Very short text
        if len(text_stripped) < 40:
            return True
        
        return False
    
    def _apply_repair(
        self,
        unit: InstructionalUnit,
        source_blocks: list[Any],
        concept_id: str,
        repair_reasons: list[str],
    ) -> InstructionalUnit | None:
        """
        Apply appropriate repair based on unit type and issues.
        
        Args:
            unit: The unit to repair
            source_blocks: Source content blocks for evidence
            concept_id: The concept ID
            repair_reasons: List of reasons why repair is needed
        
        Returns:
            Repaired unit or None if repair failed
        """
        # Build source evidence string
        source_evidence = self._build_source_evidence(source_blocks)
        
        if not source_evidence:
            logger.warning(f"No source evidence available for {concept_id}, skipping repair")
            return None
        
        # Apply repair based on unit stage
        if unit.target_stage == "L3_explanation":
            return self._repair_l3_unit(unit, source_evidence, concept_id, repair_reasons)
        elif unit.target_stage == "L2_hint_plus_example":
            return self._repair_l2_unit(unit, source_evidence, concept_id, repair_reasons)
        else:
            # For other stages, just mark as needing review
            return self._mark_for_review(unit, repair_reasons)
    
    def _build_source_evidence(self, source_blocks: list[Any]) -> str:
        """
        Build source evidence string from content blocks.
        
        Args:
            source_blocks: List of content blocks
        
        Returns:
            Combined source evidence text
        """
        evidence_parts = []
        for block in source_blocks:
            if hasattr(block, 'text_content') and block.text_content:
                evidence_parts.append(block.text_content)
            elif isinstance(block, dict) and block.get('text_content'):
                evidence_parts.append(block['text_content'])
        
        return "\n\n".join(evidence_parts)
    
    def _repair_l3_unit(
        self,
        unit: InstructionalUnit,
        source_evidence: str,
        concept_id: str,
        repair_reasons: list[str],
    ) -> InstructionalUnit | None:
        """
        Repair an L3 explanation unit.
        
        Args:
            unit: The L3 unit to repair
            source_evidence: Source evidence text
            concept_id: The concept ID
            repair_reasons: List of repair reasons
        
        Returns:
            Repaired unit or None if repair failed
        """
        content = unit.content
        
        # Build weak content dict
        weak_content = {
            "definition": content.get("definition", ""),
            "why_it_matters": content.get("why_it_matters", ""),
            "explanation": content.get("definition", ""),  # Use definition as base explanation
        }
        
        # Call Ollama for repair
        repaired_content = self.ollama_repair.repair_l3_content(
            concept_id=concept_id,
            weak_content=weak_content,
            source_evidence=source_evidence,
        )
        
        if not repaired_content:
            logger.warning(f"Ollama repair failed for {concept_id}")
            return self._mark_for_review(unit, repair_reasons + ["ollama_repair_failed"])
        
        # Create repaired unit
        new_content = dict(content)
        new_content["definition"] = repaired_content.get("definition", content.get("definition", ""))
        new_content["why_it_matters"] = repaired_content.get("why_it_matters", content.get("why_it_matters", ""))
        
        # Add repair metadata
        if "_metadata" not in new_content:
            new_content["_metadata"] = {}
        new_content["_metadata"].update({
            "_repaired_by_ollama": True,
            "_repair_model": self.ollama_repair.model,
            "_repair_reason": "|".join(repair_reasons),
            "_repair_timestamp": self._get_timestamp(),
        })
        
        # Create new unit with repaired content
        repaired_unit = unit.model_copy(update={"content": new_content})
        
        logger.info(f"Successfully repaired L3 unit for {concept_id}")
        return repaired_unit
    
    def _repair_l2_unit(
        self,
        unit: InstructionalUnit,
        source_evidence: str,
        concept_id: str,
        repair_reasons: list[str],
    ) -> InstructionalUnit | None:
        """
        Repair an L2 hint+example unit by generating concept-appropriate SQL.
        
        Args:
            unit: The L2 unit to repair
            source_evidence: Source evidence text
            concept_id: The concept ID
            repair_reasons: List of repair reasons
        
        Returns:
            Repaired unit or None if repair failed
        """
        content = unit.content
        
        # Build L2 repair prompt
        prompt = self._build_l2_repair_prompt(concept_id, source_evidence)
        
        try:
            response = self.ollama_repair._call_ollama(prompt)
            if response:
                parsed = self.ollama_repair._parse_repair_response(response)
                if parsed and "example_sql" in parsed:
                    # Create repaired unit
                    new_content = dict(content)
                    new_content["example_sql"] = parsed["example_sql"]
                    if "example_explanation" in parsed:
                        new_content["example_explanation"] = parsed["example_explanation"]
                    
                    # Add repair metadata
                    if "_metadata" not in new_content:
                        new_content["_metadata"] = {}
                    new_content["_metadata"].update({
                        "_repaired_by_ollama": True,
                        "_repair_model": self.ollama_repair.model,
                        "_repair_reason": "|".join(repair_reasons),
                        "_repair_timestamp": self._get_timestamp(),
                    })
                    
                    repaired_unit = unit.model_copy(update={"content": new_content})
                    logger.info(f"Successfully repaired L2 unit for {concept_id}")
                    return repaired_unit
        except Exception as e:
            logger.warning(f"L2 repair failed for {concept_id}: {e}")
        
        return self._mark_for_review(unit, repair_reasons + ["l2_repair_failed"])
    
    def _build_l2_repair_prompt(self, concept_id: str, source_evidence: str) -> str:
        """
        Build repair prompt for L2 content (concept-appropriate SQL example).
        
        Args:
            concept_id: The concept identifier
            source_evidence: Source evidence text
        
        Returns:
            Formatted prompt string
        """
        config = self.ollama_repair._get_model_config()
        max_evidence_chars = config.get("context_window", 4096) - 1000
        
        # Truncate evidence to avoid token limits
        if len(source_evidence) > max_evidence_chars:
            source_evidence = source_evidence[:max_evidence_chars] + "..."
        
        return f"""You are an expert SQL educator creating a worked example for students learning SQL.

CONCEPT: {concept_id}

SOURCE EVIDENCE (use ONLY this information):
{source_evidence}

TASK:
Generate a concept-appropriate SQL example that demonstrates {concept_id}.

INSTRUCTIONS:
1. Create a valid SQL query that clearly demonstrates the concept
2. Base the example ONLY on the source evidence provided
3. Use standard SQL syntax that works in SQLite
4. Include a brief explanation of what the SQL does
5. Do not invent table names or columns not supported by the source or standard SQL patterns

OUTPUT FORMAT (JSON only):
{{
  "example_sql": "SELECT ...;",
  "example_explanation": "This query demonstrates {concept_id} by..."
}}

Return ONLY valid JSON, no markdown code blocks, no extra commentary."""
    
    def _mark_for_review(
        self,
        unit: InstructionalUnit,
        repair_reasons: list[str],
    ) -> InstructionalUnit:
        """
        Mark a unit as needing review without applying repairs.
        
        Args:
            unit: The unit to mark
            repair_reasons: List of reasons why review is needed
        
        Returns:
            Unit with review flags added
        """
        new_content = dict(unit.content)
        
        if "_metadata" not in new_content:
            new_content["_metadata"] = {}
        
        new_content["_metadata"].update({
            "review_needed": True,
            "review_reason": "|".join(repair_reasons),
            "_repair_attempted": True,
            "_repair_timestamp": self._get_timestamp(),
        })
        
        return unit.model_copy(update={"content": new_content})
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Main classes
    "OllamaRepair",
    "SelectiveRepairPass",
    "RepairResult",
    "RepairCache",
    "RepairValidator",
    # Factory function
    "create_ollama_repair_if_enabled",
    # Constants
    "REPAIR_PROMPT_VERSION",
    "PREFERRED_MODELS",
    "MODEL_CONFIGS",
    "DEFAULT_MODEL_CONFIG",
    # Exceptions
    "OllamaRepairError",
    "OllamaModelNotFoundError",
    "OllamaTimeoutError",
    # Functions
    "get_model_config",
]
