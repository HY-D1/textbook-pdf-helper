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
    from algl_pdf_helper.ollama_repair import OllamaRepair
    
    repair = OllamaRepair(model="qwen2.5:3b")
    if repair.available:
        repaired_content = repair.repair_l3_content(
            concept_id="joins",
            weak_content={"definition": "Weak definition...", "why_it_matters": ""},
            source_evidence="Source text from textbook..."
        )
"""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any


logger = logging.getLogger(__name__)


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
    
    def __init__(
        self,
        model: str = "qwen2.5:3b",
        host: str = "http://localhost:11434",
        timeout: int = 30,
    ):
        """
        Initialize OllamaRepair with model and host configuration.
        
        Args:
            model: The Ollama model name to use for repairs
            host: The Ollama API host URL
            timeout: Request timeout in seconds
        """
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.available = self._check_availability()
        
        if self.available:
            logger.info(f"OllamaRepair initialized with model: {model}")
        else:
            logger.warning(f"Ollama not available at {host} - repair pass will be skipped")
    
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
        
        prompt = self._build_repair_prompt(concept_id, weak_content, source_evidence)
        
        try:
            response = self._call_ollama(prompt)
            if response:
                parsed = self._parse_repair_response(response)
                if parsed:
                    parsed["_repaired_by_ollama"] = True
                    parsed["_repair_model"] = self.model
                    logger.info(f"Successfully repaired L3 content for {concept_id}")
                    return parsed
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
        # Truncate evidence to avoid token limits
        max_evidence_chars = 2000
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
            urllib.error.URLError: If connection fails
            json.JSONDecodeError: If response parsing fails
        """
        data = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,  # Low temperature for consistency
                "num_predict": 500,  # Limit response length
                "top_p": 0.9,
                "top_k": 40,
            }
        }).encode("utf-8")
        
        req = urllib.request.Request(
            f"{self.host}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("response", "")
    
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
) -> OllamaRepair | None:
    """
    Create OllamaRepair instance if enabled and available.
    
    This is a convenience factory function that handles the common case
    of creating a repair instance conditionally.
    
    Args:
        enabled: Whether repair is enabled in configuration
        model: Ollama model to use
        host: Ollama API host
    
    Returns:
        OllamaRepair instance if enabled and available, None otherwise
    
    Example:
        >>> repair = create_ollama_repair_if_enabled(
        ...     enabled=config.use_ollama_repair,
        ...     model=config.ollama_model
        ... )
    """
    if not enabled:
        logger.info("Ollama repair disabled by configuration")
        return None
    
    repair = OllamaRepair(model=model, host=host)
    if repair.available:
        return repair
    
    logger.warning("Ollama repair enabled but server not available")
    return None
