"""
Fallback Routing Layer for ALGL PDF Helper.

This module provides slice-level routing decisions to determine whether
to stay on deterministic extraction or escalate to layout/OCR fallback
or local LLM repair.

Usage:
    from algl_pdf_helper.fallback_router import FallbackRouter, SliceRoutingDecision
    
    router = FallbackRouter()
    decision = router.classify_slice(
        preflight_report=preflight_report,
        extraction_quality=extraction_quality,
        page_analyses=page_analyses,
    )
    
    if decision.classification == "deterministic_ok":
        # Continue with normal pipeline
    elif decision.classification == "needs_ocr_fallback":
        # Trigger GLM OCR for this slice
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Literal


class RoutingClassification(str, Enum):
    """Classification states for slice routing."""
    DETERMINISTIC_OK = "deterministic_ok"
    NEEDS_LAYOUT_FALLBACK = "needs_layout_fallback"
    NEEDS_OCR_FALLBACK = "needs_ocr_fallback"
    NEEDS_LLM_REPAIR = "needs_llm_repair"


@dataclass
class SliceRoutingDecision:
    """
    Routing decision for a processed slice.
    
    Contains the classification, confidence, and detailed evidence
    for why the decision was made.
    
    Attributes:
        classification: One of deterministic_ok, needs_layout_fallback,
                       needs_ocr_fallback, needs_llm_repair
        confidence: Confidence score 0.0-1.0
        slice_id: Identifier for the slice (e.g., "pages_1_50")
        signals: Dict of signal names to values used in decision
        thresholds: Dict of threshold names to values applied
        explanation: Human-readable explanation
        page_decisions: Optional per-page classification details
    """
    classification: RoutingClassification
    confidence: float
    slice_id: str = "unknown"
    signals: dict[str, Any] = field(default_factory=dict)
    thresholds: dict[str, float] = field(default_factory=dict)
    explanation: str = ""
    page_decisions: list[dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert decision to dictionary for serialization."""
        return {
            "classification": self.classification.value,
            "confidence": round(self.confidence, 3),
            "slice_id": self.slice_id,
            "signals": self.signals,
            "thresholds": self.thresholds,
            "explanation": self.explanation,
            "page_decisions": self.page_decisions,
            "recommendation": self.get_recommendation(),
        }
    
    def get_recommendation(self) -> str:
        """Get action recommendation based on classification."""
        recommendations = {
            RoutingClassification.DETERMINISTIC_OK: 
                "Continue with deterministic extraction pipeline",
            RoutingClassification.NEEDS_LAYOUT_FALLBACK: 
                "Use layout-aware extraction (Marker) for complex structures",
            RoutingClassification.NEEDS_OCR_FALLBACK: 
                "Use GLM OCR for this slice - text quality insufficient",
            RoutingClassification.NEEDS_LLM_REPAIR: 
                "Extraction acceptable but needs local Qwen 9B repair for L3 content",
        }
        return recommendations.get(self.classification, "Unknown")


@dataclass
class RoutingThresholds:
    """Configurable thresholds for routing decisions."""
    # Extraction quality thresholds
    min_text_coverage: float = 0.70
    min_readable_ratio: float = 0.70
    max_gibberish_ratio: float = 0.30
    min_total_chars: int = 500
    
    # Layout/structure thresholds
    max_column_bleed_ratio: float = 0.50
    min_pages_with_embedded_text: float = 0.50
    
    # Downstream quality thresholds
    min_l3_quality_score: float = 0.60
    min_concept_coverage: float = 0.50
    
    # Confidence calculation weights
    coverage_weight: float = 0.40
    readability_weight: float = 0.30
    structure_weight: float = 0.30


class FallbackRouter:
    """
    Router for determining fallback strategy per slice.
    
    Analyzes preflight signals, extraction quality metrics, and downstream
    quality indicators to classify a slice into one of four routing states.
    
    Example:
        >>> router = FallbackRouter()
        >>> decision = router.classify_slice(
        ...     preflight_report={"text_coverage_score": 0.45, "ocr_needed": True},
        ...     extraction_quality={"is_quality_good": False, "readable_ratio": 0.55},
        ...     slice_id="pages_1_50"
        ... )
        >>> print(decision.classification)
        RoutingClassification.NEEDS_OCR_FALLBACK
    """
    
    def __init__(self, thresholds: RoutingThresholds | None = None):
        """
        Initialize the fallback router.
        
        Args:
            thresholds: Optional custom thresholds (uses defaults if None)
        """
        self.thresholds = thresholds or RoutingThresholds()
    
    def classify_slice(
        self,
        preflight_report: dict[str, Any] | None = None,
        extraction_quality: dict[str, Any] | None = None,
        page_analyses: list[dict[str, Any]] | None = None,
        downstream_quality: dict[str, Any] | None = None,
        slice_id: str = "unknown",
    ) -> SliceRoutingDecision:
        """
        Classify a slice based on available signals.
        
        Evaluates signals in order of priority:
        1. Extraction quality (coverage, readability)
        2. Preflight signals (embedded text, column bleed)
        3. Downstream quality (L3 scores, concept coverage)
        
        Args:
            preflight_report: Preflight analysis results
            extraction_quality: Extraction quality metrics
            page_analyses: Per-page analysis details
            downstream_quality: Quality gate results
            slice_id: Identifier for this slice
            
        Returns:
            SliceRoutingDecision with classification and evidence
        """
        preflight = preflight_report or {}
        extraction = extraction_quality or {}
        downstream = downstream_quality or {}
        pages = page_analyses or []
        
        # Collect all signals
        signals = self._extract_signals(preflight, extraction, downstream, pages)
        
        # Determine classification based on priority order
        classification, confidence, explanation = self._determine_classification(signals)
        
        # Build page-level decisions if available
        page_decisions = self._build_page_decisions(pages)
        
        return SliceRoutingDecision(
            classification=classification,
            confidence=confidence,
            slice_id=slice_id,
            signals=signals,
            thresholds=self._thresholds_dict(),
            explanation=explanation,
            page_decisions=page_decisions,
        )
    
    def _extract_signals(
        self,
        preflight: dict[str, Any],
        extraction: dict[str, Any],
        downstream: dict[str, Any],
        pages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Extract and normalize all signals from inputs."""
        signals = {}
        
        # Preflight signals
        signals["text_coverage_score"] = preflight.get("text_coverage_score", 0.0)
        signals["has_embedded_text"] = preflight.get("has_embedded_text", False)
        signals["ocr_needed"] = preflight.get("ocr_needed", False)
        signals["estimated_table_count"] = preflight.get("estimated_table_count", 0)
        signals["average_page_text_density"] = preflight.get("average_page_text_density", 0)
        signals["warning_flags"] = preflight.get("warning_flags", [])
        signals["column_bleed_detected"] = "2-column bleed detected" in signals["warning_flags"]
        signals["heavy_headers_footers"] = "heavy headers/footers" in signals["warning_flags"]
        
        # Extraction quality signals
        signals["total_chars"] = extraction.get("total_chars", 0)
        signals["readable_ratio"] = extraction.get("readable_ratio", 0.0)
        signals["gibberish_ratio"] = extraction.get("gibberish_ratio", 0.0)
        signals["is_quality_good"] = extraction.get("is_quality_good", False)
        signals["needs_ocr"] = extraction.get("needs_ocr", False)
        signals["coverage_score"] = extraction.get("coverage_score", signals["text_coverage_score"])
        
        # Page-level aggregate signals
        if pages:
            signals["page_count"] = len(pages)
            signals["pages_with_low_coverage"] = sum(
                1 for p in pages if p.get("coverage_score", 0) < self.thresholds.min_text_coverage
            )
            signals["pages_with_embedded_text"] = sum(
                1 for p in pages if p.get("has_embedded_text", False)
            )
            signals["ratio_pages_with_text"] = signals["pages_with_embedded_text"] / len(pages)
            signals["repeated_line_ratio"] = self._calculate_repeated_line_ratio(pages)
        else:
            signals["page_count"] = 0
            signals["pages_with_low_coverage"] = 0
            signals["ratio_pages_with_text"] = 0.0
            signals["repeated_line_ratio"] = 0.0
        
        # Downstream quality signals
        signals["l3_quality_score"] = downstream.get("l3_quality_score", 0.0)
        signals["concept_coverage"] = downstream.get("concept_coverage", 0.0)
        signals["has_weak_l3_content"] = signals["l3_quality_score"] < self.thresholds.min_l3_quality_score
        
        return signals
    
    def _determine_classification(
        self, signals: dict[str, Any]
    ) -> tuple[RoutingClassification, float, str]:
        """
        Determine classification based on signals.
        
        Priority order:
        1. needs_ocr_fallback: Very poor extraction quality
        2. needs_layout_fallback: Structural issues with acceptable text
        3. needs_llm_repair: Acceptable extraction but weak downstream
        4. deterministic_ok: Everything looks good
        """
        coverage = signals.get("coverage_score", 0)
        readable = signals.get("readable_ratio", 0)
        gibberish = signals.get("gibberish_ratio", 0)
        has_embedded = signals.get("has_embedded_text", False)
        needs_ocr = signals.get("needs_ocr", False)
        column_bleed = signals.get("column_bleed_detected", False)
        table_count = signals.get("estimated_table_count", 0)
        l3_quality = signals.get("l3_quality_score", 0)
        concept_coverage = signals.get("concept_coverage", 0)
        
        # Priority 1: OCR Fallback - critical extraction failures
        if needs_ocr or coverage < 0.50 or readable < 0.50 or not has_embedded:
            confidence = self._calculate_confidence(signals, "ocr")
            explanation = (
                f"Extraction quality insufficient: coverage={coverage:.1%}, "
                f"readable={readable:.1%}. OCR required."
            )
            return RoutingClassification.NEEDS_OCR_FALLBACK, confidence, explanation
        
        # Priority 2: Layout Fallback - structural issues
        if column_bleed and table_count > 10:
            confidence = self._calculate_confidence(signals, "layout")
            explanation = (
                f"Complex layout detected: {table_count} tables with column bleed. "
                f"Layout-aware extraction recommended."
            )
            return RoutingClassification.NEEDS_LAYOUT_FALLBACK, confidence, explanation
        
        # Priority 3: LLM Repair - extraction ok but downstream weak
        if coverage >= self.thresholds.min_text_coverage and l3_quality > 0 and l3_quality < self.thresholds.min_l3_quality_score:
            confidence = self._calculate_confidence(signals, "repair")
            explanation = (
                f"Extraction acceptable (coverage={coverage:.1%}) but L3 quality low "
                f"({l3_quality:.2f}). Local repair recommended."
            )
            return RoutingClassification.NEEDS_LLM_REPAIR, confidence, explanation
        
        # Priority 4: Deterministic OK
        confidence = self._calculate_confidence(signals, "deterministic")
        explanation = (
            f"Extraction quality good: coverage={coverage:.1%}, "
            f"readable={readable:.1%}. No fallback needed."
        )
        return RoutingClassification.DETERMINISTIC_OK, confidence, explanation
    
    def _calculate_confidence(
        self, signals: dict[str, Any], classification_type: str
    ) -> float:
        """Calculate confidence score for the classification."""
        coverage = signals.get("coverage_score", 0)
        readable = signals.get("readable_ratio", 0)
        gibberish = signals.get("gibberish_ratio", 0)
        
        if classification_type == "deterministic":
            # Higher coverage/readable = higher confidence
            score = (
                coverage * self.thresholds.coverage_weight +
                readable * self.thresholds.readability_weight +
                (1 - gibberish) * self.thresholds.structure_weight
            )
        elif classification_type == "ocr":
            # Lower coverage = higher confidence in OCR need
            score = 1.0 - (coverage * 0.5 + readable * 0.5)
        elif classification_type == "layout":
            score = 0.75  # Moderate confidence for layout issues
        else:  # repair
            score = 0.70  # Moderate confidence for repair need
        
        return round(max(0.0, min(1.0, score)), 3)
    
    def _calculate_repeated_line_ratio(
        self, pages: list[dict[str, Any]]
    ) -> float:
        """
        Calculate ratio of repeated lines (indicator of broken paragraphs).
        
        High repeated line ratio suggests table-of-contents noise or
        broken paragraph structures from poor extraction.
        """
        if not pages:
            return 0.0
        
        from collections import Counter
        
        total_lines = 0
        repeated_lines = 0
        
        for page in pages:
            text = page.get("text", "")
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            total_lines += len(lines)
            
            # Count lines that appear more than once
            line_counts = Counter(lines)
            repeated_lines += sum(1 for count in line_counts.values() if count > 1)
        
        if total_lines == 0:
            return 0.0
        
        return round(repeated_lines / total_lines, 3)
    
    def _build_page_decisions(
        self, pages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Build per-page classification details."""
        decisions = []
        
        for page in pages:
            page_num = page.get("page_number", 0)
            coverage = page.get("coverage_score", 0)
            
            # Classify individual page
            if coverage < 0.50:
                page_class = "needs_ocr"
            elif coverage < self.thresholds.min_text_coverage:
                page_class = "marginal"
            else:
                page_class = "ok"
            
            decisions.append({
                "page_number": page_num,
                "classification": page_class,
                "coverage_score": round(coverage, 3),
                "text_length": page.get("text_length", 0),
            })
        
        return decisions
    
    def _thresholds_dict(self) -> dict[str, float]:
        """Convert thresholds to dictionary."""
        return {
            "min_text_coverage": self.thresholds.min_text_coverage,
            "min_readable_ratio": self.thresholds.min_readable_ratio,
            "max_gibberish_ratio": self.thresholds.max_gibberish_ratio,
            "min_total_chars": self.thresholds.min_total_chars,
            "min_l3_quality_score": self.thresholds.min_l3_quality_score,
        }


class RoutingArtifact:
    """
    Persistent artifact for routing decisions.
    
    Writes routing decisions to JSON for downstream analysis and audit.
    
    Example:
        >>> artifact = RoutingArtifact(output_dir=Path("./output"))
        >>> artifact.save(decision, pipeline_stats={"units": 10})
        >>> decisions = artifact.load_all()
    """
    
    FILENAME = "routing_decision.json"
    
    def __init__(self, output_dir: Path):
        """
        Initialize the routing artifact.
        
        Args:
            output_dir: Directory to write routing_decision.json
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def save(
        self,
        decision: SliceRoutingDecision,
        pipeline_stats: dict[str, Any] | None = None,
    ) -> Path:
        """
        Save routing decision to JSON file.
        
        Args:
            decision: The routing decision to save
            pipeline_stats: Optional additional pipeline statistics
            
        Returns:
            Path to the saved file
        """
        output_path = self.output_dir / self.FILENAME
        
        data = {
            "routing_version": "1.0.0",
            "slice_id": decision.slice_id,
            "decision": decision.to_dict(),
            "pipeline_stats": pipeline_stats or {},
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def load(self) -> dict[str, Any] | None:
        """Load routing decision from JSON file if it exists."""
        output_path = self.output_dir / self.FILENAME
        
        if not output_path.exists():
            return None
        
        with open(output_path, "r", encoding="utf-8") as f:
            return json.load(f)


def classify_from_pipeline_result(
    pipeline_result: dict[str, Any],
    router: FallbackRouter | None = None,
) -> SliceRoutingDecision:
    """
    Convenience function to classify from pipeline result.
    
    Args:
        pipeline_result: Dictionary with pipeline outputs
        router: Optional FallbackRouter instance (creates default if None)
        
    Returns:
        SliceRoutingDecision based on pipeline results
    """
    router = router or FallbackRouter()
    
    # Extract available signals from pipeline result
    preflight = pipeline_result.get("preflight_report", {})
    extraction = pipeline_result.get("extraction_quality", {})
    downstream = pipeline_result.get("quality_gates", {})
    
    return router.classify_slice(
        preflight_report=preflight,
        extraction_quality=extraction,
        downstream_quality=downstream,
        slice_id=pipeline_result.get("slice_id", "unknown"),
    )
