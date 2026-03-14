"""
Multi-Pass Generation Pipeline for Pedagogical Content.

This module implements a robust generation pipeline that:
1. Generates content using small, fast models (qwen2.5:3b)
2. Validates JSON structure
3. Validates SQL snippets
4. Regenerates only broken fields if needed
5. Falls back gracefully on errors

Optimized for 8GB M1 Mac with conservative memory usage.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Callable

from .pedagogical_models import (
    PedagogicalConcept,
    GenerationResult,
    SQLExample,
    Mistake,
)
from .validators import (
    validate_concept_json,
    validate_sql_snippet,
    extract_json_from_llm_output,
    safe_parse_json,
)
from .prompts import (
    build_strict_pedagogical_prompt,
    build_strict_sql_example_prompt,
    build_strict_mistakes_prompt,
    PRACTICE_SCHEMAS,
)


# =============================================================================
# MODEL CONFIGURATION FOR 8GB M1 MAC
# =============================================================================

# Recommended models for 8GB M1 Mac
M1_8GB_MODELS = {
    "qwen2.5:3b": {
        "description": "Fast, lightweight, good for education",
        "ram_gb": 3,
        "recommended": True,
    },
    "qwen2.5:3b-instruct": {
        "description": "Fast, lightweight, instruct-tuned",
        "ram_gb": 3,
        "recommended": True,
    },
    "qwen:1.8b": {
        "description": "Very fast, minimal RAM usage",
        "ram_gb": 2,
        "recommended": True,
    },
    "qwen2.5-coder:3b": {
        "description": "Optimized for code generation",
        "ram_gb": 3,
        "recommended": True,
    },
    "llama3.2:3b": {
        "description": "Fast, efficient",
        "ram_gb": 3,
        "recommended": True,
    },
    "gemma2:2b": {
        "description": "Very lightweight",
        "ram_gb": 2,
        "recommended": True,
    },
    "phi4-mini:3.8b": {
        "description": "Microsoft Phi-4 mini, good quality",
        "ram_gb": 3,
        "recommended": True,
    },
}

# 7B models require more memory - use with caution
OPTIONAL_7B_MODELS = {
    "qwen2.5:7b": {
        "description": "Better quality, requires more RAM",
        "ram_gb": 7,
        "recommended": False,
        "warning": "May cause memory pressure on 8GB M1 Mac. Close other applications.",
    },
    "qwen2.5-coder:7b": {
        "description": "Best for code, requires more RAM",
        "ram_gb": 7,
        "recommended": False,
        "warning": "May cause memory pressure on 8GB M1 Mac. Close other applications.",
    },
    "mistral:7b": {
        "description": "Balanced quality/speed, requires more RAM",
        "ram_gb": 7,
        "recommended": False,
        "warning": "May cause memory pressure on 8GB M1 Mac.",
    },
}

ALL_MODELS = {**M1_8GB_MODELS, **OPTIONAL_7B_MODELS}


def get_system_memory_gb() -> int:
    """
    Get system memory in GB (conservative estimate).
    
    Returns:
        Estimated system memory in GB (minimum 8)
    """
    try:
        import subprocess
        result = subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            bytes_mem = int(result.stdout.strip())
            gb_mem = bytes_mem // (1024 ** 3)
            return max(8, gb_mem)  # Minimum 8GB assumption
    except Exception:
        pass
    return 8  # Default assumption


def check_model_compatibility(model_name: str) -> tuple[bool, str]:
    """
    Check if a model is compatible with the current system.
    
    Args:
        model_name: Name of the model to check
        
    Returns:
        Tuple of (is_compatible, warning_message)
    """
    model_config = ALL_MODELS.get(model_name)
    if not model_config:
        return True, f"Unknown model '{model_name}'. Compatibility unknown."
    
    system_memory = get_system_memory_gb()
    required_memory = model_config.get("ram_gb", 8)
    
    if required_memory > system_memory:
        return False, f"Model '{model_name}' requires {required_memory}GB RAM but system has {system_memory}GB."
    
    if not model_config.get("recommended", False):
        warning = model_config.get("warning", f"Model '{model_name}' is not recommended for {system_memory}GB systems.")
        return True, warning
    
    return True, ""


def get_recommended_model() -> str:
    """Get the recommended model for the current system."""
    system_memory = get_system_memory_gb()
    
    # For 8GB systems, prefer 3B models
    if system_memory <= 8:
        return "qwen3.5:9b-q8_0"  # Default recommendation for RTX 4080
    
    # For 16GB+ systems, can use 7B models
    return "qwen2.5-coder:7b"


# =============================================================================
# MULTI-PASS GENERATOR
# =============================================================================

class MultiPassGenerator:
    """
    Multi-pass generator with validation and regeneration capabilities.
    
    This generator:
    1. Generates content using specified or default model
    2. Validates JSON structure against schema
    3. Validates SQL snippets
    4. Regenerates only broken fields if needed
    5. Falls back to default content on persistent failures
    
    Attributes:
        ollama_host: URL of Ollama server
        model: Model name to use
        max_attempts: Maximum regeneration attempts
        temperature: LLM temperature (0.0-1.0)
        timeout: Request timeout in seconds
    """
    
    DEFAULT_TIMEOUT = 180  # 3 minutes for small models
    DEFAULT_TEMPERATURE = 0.3  # Lower for more consistent output
    MAX_ATTEMPTS = 3
    
    def __init__(
        self,
        ollama_host: str | None = None,
        model: str | None = None,
        max_attempts: int = MAX_ATTEMPTS,
        temperature: float = DEFAULT_TEMPERATURE,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        """
        Initialize the multi-pass generator.
        
        Args:
            ollama_host: Ollama server URL (default: http://localhost:11434)
            model: Model to use (default: auto-detect based on memory)
            max_attempts: Maximum generation attempts (default: 3)
            temperature: LLM temperature (default: 0.3)
            timeout: Request timeout in seconds (default: 180)
        """
        self.ollama_host = ollama_host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = model or get_recommended_model()
        self.max_attempts = max(1, min(max_attempts, 5))  # Clamp between 1-5
        self.temperature = max(0.0, min(temperature, 1.0))
        self.timeout = timeout
        
        # Check model compatibility
        is_compatible, warning = check_model_compatibility(self.model)
        if not is_compatible:
            print(f"⚠️  {warning}")
            print(f"   Falling back to recommended model: {get_recommended_model()}")
            self.model = get_recommended_model()
        elif warning:
            print(f"⚠️  {warning}")
    
    def _ollama_chat(self, messages: list[dict], temperature: float | None = None) -> str:
        """
        Send chat request to Ollama.
        
        Args:
            messages: List of message dicts with "role" and "content"
            temperature: Optional override for temperature
            
        Returns:
            Generated text content
            
        Raises:
            urllib.error.URLError: If connection fails
            TimeoutError: If request times out
        """
        temp = temperature if temperature is not None else self.temperature
        
        data = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temp,
                "num_predict": 4000,  # Reasonable limit for concept generation
            },
        }
        
        req = urllib.request.Request(
            f"{self.ollama_host}/api/chat",
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
            content = result.get("message", {}).get("content", "")
            if not content:
                raise ValueError("Empty response from Ollama")
            return content
    
    def generate_with_validation(
        self,
        concept_id: str,
        concept_title: str,
        raw_text: str,
        difficulty: str = "beginner",
        progress_callback: Callable[[str], None] | None = None,
    ) -> GenerationResult:
        """
        Generate pedagogical content with multi-pass validation.
        
        Args:
            concept_id: Unique identifier for the concept
            concept_title: Human-readable title
            raw_text: Raw textbook content to base generation on
            difficulty: Difficulty level (beginner/intermediate/advanced)
            progress_callback: Optional callback for progress updates
            
        Returns:
            GenerationResult with success status and generated concept
        """
        start_time = time.time()
        
        def _progress(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)
        
        _progress(f"Generating content for: {concept_title}")
        
        # Build the prompt
        prompt = build_strict_pedagogical_prompt(
            concept_id=concept_id,
            concept_title=concept_title,
            difficulty=difficulty,
            raw_text=raw_text,
        )
        
        # Attempt generation with validation
        for attempt in range(1, self.max_attempts + 1):
            _progress(f"Attempt {attempt}/{self.max_attempts}...")
            
            try:
                # Generate content
                response = self._ollama_chat([
                    {"role": "user", "content": prompt}
                ])
                
                # Parse JSON
                success, parsed_data, error_msg = safe_parse_json(response)
                
                if not success or not parsed_data:
                    _progress(f"JSON parse failed: {error_msg}")
                    if attempt < self.max_attempts:
                        # Retry with higher temperature for variety
                        prompt += f"\n\nPREVIOUS ATTEMPT FAILED: {error_msg}\nPlease ensure valid JSON only."
                        continue
                    else:
                        # All attempts failed, return error result
                        elapsed = time.time() - start_time
                        return GenerationResult(
                            success=False,
                            concept=None,
                            validation_errors=[{
                                "field": "json_parse",
                                "error": error_msg,
                                "value": response[:200]
                            }],
                            attempts=attempt,
                            model_used=self.model,
                            generation_time_seconds=elapsed,
                        )
                
                # Validate against schema
                validation_result = validate_concept_json(parsed_data)
                
                if validation_result.is_valid:
                    # Success! Return the validated concept
                    elapsed = time.time() - start_time
                    concept = PedagogicalConcept.model_validate(parsed_data)
                    _progress("Validation passed!")
                    return GenerationResult(
                        success=True,
                        concept=concept,
                        validation_errors=[],
                        attempts=attempt,
                        model_used=self.model,
                        generation_time_seconds=elapsed,
                    )
                
                # Validation failed - try to fix specific fields
                _progress(f"Validation failed with {len(validation_result.errors)} errors")
                
                if attempt < self.max_attempts:
                    # Add validation feedback to prompt for next attempt
                    error_feedback = "\n".join([
                        f"- {e.field}: {e.error}" for e in validation_result.errors[:5]
                    ])
                    prompt += f"\n\nVALIDATION ERRORS TO FIX:\n{error_feedback}\n\nPlease regenerate with these fixes."
                    continue
                else:
                    # Max attempts reached - try to use partial data
                    elapsed = time.time() - start_time
                    
                    # Try to fix common issues and create a valid concept
                    fixed_concept = self._attempt_fixes(parsed_data, validation_result)
                    if fixed_concept:
                        _progress("Applied fixes to create valid concept")
                        return GenerationResult(
                            success=True,
                            concept=fixed_concept,
                            validation_errors=validation_result.errors,
                            attempts=attempt,
                            model_used=self.model,
                            generation_time_seconds=elapsed,
                        )
                    
                    return GenerationResult(
                        success=False,
                        concept=None,
                        validation_errors=validation_result.errors,
                        attempts=attempt,
                        model_used=self.model,
                        generation_time_seconds=elapsed,
                    )
                    
            except urllib.error.URLError as e:
                _progress(f"Connection error: {e}")
                elapsed = time.time() - start_time
                return GenerationResult(
                    success=False,
                    concept=None,
                    validation_errors=[{
                        "field": "connection",
                        "error": f"Cannot connect to Ollama: {e}",
                        "value": ""
                    }],
                    attempts=attempt,
                    model_used=self.model,
                    generation_time_seconds=elapsed,
                )
            except TimeoutError:
                _progress("Request timed out")
                elapsed = time.time() - start_time
                return GenerationResult(
                    success=False,
                    concept=None,
                    validation_errors=[{
                        "field": "timeout",
                        "error": f"Request timed out after {self.timeout}s",
                        "value": ""
                    }],
                    attempts=attempt,
                    model_used=self.model,
                    generation_time_seconds=elapsed,
                )
            except Exception as e:
                _progress(f"Unexpected error: {e}")
                if attempt == self.max_attempts:
                    elapsed = time.time() - start_time
                    return GenerationResult(
                        success=False,
                        concept=None,
                        validation_errors=[{
                            "field": "generation",
                            "error": str(e),
                            "value": ""
                        }],
                        attempts=attempt,
                        model_used=self.model,
                        generation_time_seconds=elapsed,
                    )
        
        # Should not reach here, but just in case
        elapsed = time.time() - start_time
        return GenerationResult(
            success=False,
            concept=None,
            validation_errors=[{
                "field": "unknown",
                "error": "Max attempts reached without success",
                "value": ""
            }],
            attempts=self.max_attempts,
            model_used=self.model,
            generation_time_seconds=elapsed,
        )
    
    def _attempt_fixes(
        self,
        data: dict[str, Any],
        validation_result: Any,
    ) -> PedagogicalConcept | None:
        """
        Attempt to fix common issues in the data.
        
        Args:
            data: Parsed JSON data
            validation_result: Validation result with errors
            
        Returns:
            Fixed PedagogicalConcept or None if unfixable
        """
        try:
            # Ensure required fields exist
            if "concept_id" not in data or not data["concept_id"]:
                data["concept_id"] = "unknown-concept"
            
            if "title" not in data or not data["title"]:
                data["title"] = "Untitled Concept"
            
            if "definition" not in data or not data["definition"]:
                data["definition"] = "Definition not available."
            
            # Ensure lists exist
            if "key_points" not in data or not isinstance(data["key_points"], list):
                data["key_points"] = ["Key point not available"]
            
            if "examples" not in data or not isinstance(data["examples"], list) or len(data["examples"]) == 0:
                # Create a default example
                data["examples"] = [{
                    "description": "Basic example",
                    "query": "SELECT * FROM users LIMIT 5;",
                    "explanation": "A simple query to demonstrate the concept.",
                    "schema_used": "users",
                    "difficulty": "beginner",
                }]
            
            if "common_mistakes" not in data or not isinstance(data["common_mistakes"], list):
                data["common_mistakes"] = []
            
            # Ensure all SQL ends with semicolon
            for ex in data.get("examples", []):
                if "query" in ex and not ex["query"].strip().endswith(";"):
                    ex["query"] = ex["query"].strip() + ";"
            
            for m in data.get("common_mistakes", []):
                if "correct_sql" in m and not m["correct_sql"].strip().endswith(";"):
                    m["correct_sql"] = m["correct_sql"].strip() + ";"
            
            # Try validation again
            return PedagogicalConcept.model_validate(data)
            
        except Exception:
            return None
    
    def generate_sql_example(
        self,
        concept_title: str,
        scenario: str,
        difficulty: str = "beginner",
    ) -> SQLExample | None:
        """
        Generate a single SQL example with validation.
        
        Args:
            concept_title: Concept being demonstrated
            scenario: Scenario description
            difficulty: Difficulty level
            
        Returns:
            Validated SQLExample or None if generation failed
        """
        prompt = build_strict_sql_example_prompt(
            concept_title=concept_title,
            scenario=scenario,
            difficulty=difficulty,
        )
        
        try:
            response = self._ollama_chat([
                {"role": "user", "content": prompt}
            ])
            
            parsed = extract_json_from_llm_output(response)
            if not parsed:
                return None
            
            # Validate SQL
            if "query" in parsed:
                sql_result = validate_sql_snippet(parsed["query"])
                if not sql_result.is_valid:
                    # Try to fix
                    parsed["query"] = parsed["query"].strip()
                    if not parsed["query"].endswith(";"):
                        parsed["query"] += ";"
            
            return SQLExample.model_validate(parsed)
            
        except Exception:
            return None
    
    def generate_common_mistakes(
        self,
        concept_title: str,
        concept_id: str = "",
        difficulty: str = "beginner",
    ) -> list[Mistake]:
        """
        Generate common mistakes with validation.
        
        Args:
            concept_title: Concept being taught
            concept_id: Optional concept ID
            difficulty: Difficulty level
            
        Returns:
            List of validated Mistake objects
        """
        prompt = build_strict_mistakes_prompt(
            concept_title=concept_title,
            concept_id=concept_id,
            difficulty=difficulty,
        )
        
        try:
            response = self._ollama_chat([
                {"role": "user", "content": prompt}
            ])
            
            parsed = extract_json_from_llm_output(response)
            if not parsed or not isinstance(parsed, list):
                return []
            
            mistakes = []
            for m in parsed:
                try:
                    # Ensure correct_sql ends with semicolon
                    if "correct_sql" in m and not m["correct_sql"].strip().endswith(";"):
                        m["correct_sql"] = m["correct_sql"].strip() + ";"
                    
                    mistake = Mistake.model_validate(m)
                    mistakes.append(mistake)
                except Exception:
                    continue
            
            return mistakes
            
        except Exception:
            return []


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def check_ollama_available(host: str | None = None) -> bool:
    """
    Check if Ollama is available at the given host.
    
    Args:
        host: Ollama host URL (default: http://localhost:11434)
        
    Returns:
        True if Ollama is available
    """
    host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
    
    try:
        req = urllib.request.Request(
            f"{host}/api/tags",
            method="GET",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status == 200
    except Exception:
        return False


def list_available_models(host: str | None = None) -> list[dict]:
    """
    List available Ollama models.
    
    Args:
        host: Ollama host URL
        
    Returns:
        List of model information dictionaries
    """
    host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
    
    try:
        req = urllib.request.Request(
            f"{host}/api/tags",
            method="GET",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("models", [])
    except Exception:
        return []
