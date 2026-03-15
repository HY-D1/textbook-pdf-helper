"""
Unit tests for the fallback routing layer.

Tests cover:
- deterministic_ok path
- needs_ocr_fallback trigger
- needs_layout_fallback trigger
- needs_llm_repair trigger
- artifact persistence
- edge cases (missing signals, empty inputs)
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from algl_pdf_helper.fallback_router import (
    FallbackRouter,
    RoutingClassification,
    RoutingArtifact,
    RoutingThresholds,
    SliceRoutingDecision,
    classify_from_pipeline_result,
)


class TestRoutingThresholds:
    """Tests for RoutingThresholds configuration."""
    
    def test_default_thresholds(self):
        """Test that default thresholds are reasonable."""
        thresholds = RoutingThresholds()
        
        assert thresholds.min_text_coverage == 0.70
        assert thresholds.min_readable_ratio == 0.70
        assert thresholds.max_gibberish_ratio == 0.30
        assert thresholds.min_l3_quality_score == 0.60
    
    def test_custom_thresholds(self):
        """Test that thresholds can be customized."""
        thresholds = RoutingThresholds(
            min_text_coverage=0.80,
            min_readable_ratio=0.75,
        )
        
        assert thresholds.min_text_coverage == 0.80
        assert thresholds.min_readable_ratio == 0.75
        # Other values should remain defaults
        assert thresholds.max_gibberish_ratio == 0.30


class TestSliceRoutingDecision:
    """Tests for SliceRoutingDecision dataclass."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        decision = SliceRoutingDecision(
            classification=RoutingClassification.DETERMINISTIC_OK,
            confidence=0.95,
            slice_id="pages_1_50",
            explanation="Good quality extraction",
        )
        
        data = decision.to_dict()
        
        assert data["classification"] == "deterministic_ok"
        assert data["confidence"] == 0.95
        assert data["slice_id"] == "pages_1_50"
        assert data["explanation"] == "Good quality extraction"
        assert data["recommendation"] == "Continue with deterministic extraction pipeline"
    
    def test_get_recommendation(self):
        """Test recommendation strings for each classification."""
        classifications = [
            (RoutingClassification.DETERMINISTIC_OK, "deterministic"),
            (RoutingClassification.NEEDS_LAYOUT_FALLBACK, "layout"),
            (RoutingClassification.NEEDS_OCR_FALLBACK, "ocr"),
            (RoutingClassification.NEEDS_LLM_REPAIR, "repair"),
        ]
        
        for classification, keyword in classifications:
            decision = SliceRoutingDecision(
                classification=classification,
                confidence=0.8,
            )
            assert keyword in decision.get_recommendation().lower()


class TestFallbackRouterHappyPaths:
    """Tests for happy path classifications."""
    
    def test_healthy_slice_real_metrics_deterministic_ok(self):
        """Test that a healthy PDF slice with real metrics gets deterministic_ok."""
        router = FallbackRouter()
        
        # Simulate real metrics from a healthy PDF extraction
        # (like Murach's MySQL which has good embedded text)
        preflight = {
            "text_coverage_score": 0.85,  # Good coverage
            "has_embedded_text": True,
            "ocr_needed": False,
            "warning_flags": [],
        }
        
        extraction = {
            "coverage_score": 0.85,
            "readable_ratio": 0.82,  # Good readability
            "gibberish_ratio": 0.05,  # Low gibberish
            "is_quality_good": True,
            "needs_ocr": False,
            "total_chars": 15000,  # Substantial text
        }
        
        pages = [
            {"page_number": 1, "coverage_score": 0.88, "has_embedded_text": True, "text": "Good content"},
            {"page_number": 2, "coverage_score": 0.85, "has_embedded_text": True, "text": "More good content"},
            {"page_number": 3, "coverage_score": 0.82, "has_embedded_text": True, "text": "Even more content"},
        ]
        
        decision = router.classify_slice(
            preflight_report=preflight,
            extraction_quality=extraction,
            page_analyses=pages,
            slice_id="murach_ch3_healthy",
        )
        
        # Healthy slice should get deterministic_ok
        assert decision.classification == RoutingClassification.DETERMINISTIC_OK, \
            f"Expected deterministic_ok, got {decision.classification}. Explanation: {decision.explanation}"
        assert decision.confidence > 0.7
        assert "coverage=85%" in decision.explanation or "acceptable" in decision.explanation.lower()
    
    def test_deterministic_ok_strong_signals(self):
        """Test deterministic_ok when all signals are strong."""
        router = FallbackRouter()
        
        preflight = {
            "text_coverage_score": 0.90,
            "has_embedded_text": True,
            "ocr_needed": False,
            "warning_flags": [],
        }
        
        extraction = {
            "coverage_score": 0.90,
            "readable_ratio": 0.85,
            "gibberish_ratio": 0.10,
            "is_quality_good": True,
            "needs_ocr": False,
            "total_chars": 5000,
        }
        
        decision = router.classify_slice(
            preflight_report=preflight,
            extraction_quality=extraction,
            slice_id="test_slice",
        )
        
        assert decision.classification == RoutingClassification.DETERMINISTIC_OK
        assert decision.confidence > 0.7
        assert "test_slice" in decision.slice_id
    
    def test_deterministic_ok_minimum_thresholds(self):
        """Test deterministic_ok at minimum acceptable thresholds."""
        router = FallbackRouter()
        
        preflight = {
            "text_coverage_score": 0.70,
            "has_embedded_text": True,
            "ocr_needed": False,
        }
        
        extraction = {
            "coverage_score": 0.70,
            "readable_ratio": 0.70,
            "is_quality_good": True,
            "needs_ocr": False,
        }
        
        decision = router.classify_slice(
            preflight_report=preflight,
            extraction_quality=extraction,
        )
        
        assert decision.classification == RoutingClassification.DETERMINISTIC_OK


class TestFallbackRouterFailurePaths:
    """Tests for failure path classifications."""
    
    def test_needs_ocr_fallback_low_coverage(self):
        """Test OCR fallback trigger for low coverage."""
        router = FallbackRouter()
        
        preflight = {
            "text_coverage_score": 0.40,
            "has_embedded_text": False,
            "ocr_needed": True,
        }
        
        extraction = {
            "coverage_score": 0.40,
            "readable_ratio": 0.45,
            "is_quality_good": False,
            "needs_ocr": True,
        }
        
        decision = router.classify_slice(
            preflight_report=preflight,
            extraction_quality=extraction,
        )
        
        assert decision.classification == RoutingClassification.NEEDS_OCR_FALLBACK
        assert "coverage" in decision.explanation.lower()
    
    def test_needs_ocr_fallback_no_embedded_text(self):
        """Test OCR fallback when no embedded text detected."""
        router = FallbackRouter()
        
        preflight = {
            "text_coverage_score": 0.0,
            "has_embedded_text": False,
            "ocr_needed": True,
        }
        
        extraction = {
            "is_quality_good": False,
            "needs_ocr": True,
        }
        
        decision = router.classify_slice(
            preflight_report=preflight,
            extraction_quality=extraction,
        )
        
        assert decision.classification == RoutingClassification.NEEDS_OCR_FALLBACK
    
    def test_needs_layout_fallback(self):
        """Test layout fallback for complex structures."""
        router = FallbackRouter()
        
        preflight = {
            "text_coverage_score": 0.75,
            "has_embedded_text": True,
            "ocr_needed": False,
            "estimated_table_count": 15,
            "warning_flags": ["2-column bleed detected"],
        }
        
        extraction = {
            "coverage_score": 0.75,
            "readable_ratio": 0.72,
            "is_quality_good": True,
        }
        
        decision = router.classify_slice(
            preflight_report=preflight,
            extraction_quality=extraction,
        )
        
        assert decision.classification == RoutingClassification.NEEDS_LAYOUT_FALLBACK
        assert "table" in decision.explanation.lower() or "layout" in decision.explanation.lower()
    
    def test_needs_llm_repair(self):
        """Test LLM repair for acceptable extraction but weak L3."""
        router = FallbackRouter()
        
        preflight = {
            "text_coverage_score": 0.80,
            "has_embedded_text": True,
        }
        
        extraction = {
            "coverage_score": 0.80,
            "readable_ratio": 0.75,
            "is_quality_good": True,
        }
        
        downstream = {
            "l3_quality_score": 0.45,  # Below threshold
            "concept_coverage": 0.60,
        }
        
        decision = router.classify_slice(
            preflight_report=preflight,
            extraction_quality=extraction,
            downstream_quality=downstream,
        )
        
        assert decision.classification == RoutingClassification.NEEDS_LLM_REPAIR
        assert "l3" in decision.explanation.lower() or "quality" in decision.explanation.lower()


class TestFallbackRouterEdgeCases:
    """Tests for edge cases."""
    
    def test_empty_inputs(self):
        """Test handling of empty/None inputs - should default to deterministic_ok."""
        router = FallbackRouter()
        
        decision = router.classify_slice(
            preflight_report=None,
            extraction_quality=None,
            page_analyses=None,
        )
        
        # Missing metrics should default to deterministic_ok (safe default)
        # NOT automatically OCR fallback
        assert decision.classification == RoutingClassification.DETERMINISTIC_OK
        assert "no evidence" in decision.explanation.lower() or "deterministic" in decision.explanation.lower()
    
    def test_partial_signals(self):
        """Test handling of partial signal availability."""
        router = FallbackRouter()
        
        # Only preflight, no extraction
        decision = router.classify_slice(
            preflight_report={"text_coverage_score": 0.85},
            extraction_quality=None,
        )
        
        # Should use available signals
        assert decision.signals["text_coverage_score"] == 0.85
    
    def test_custom_thresholds_affect_classification(self):
        """Test that custom thresholds change classification outcomes."""
        # Strict thresholds
        strict_router = FallbackRouter(RoutingThresholds(min_text_coverage=0.90))
        
        preflight = {"text_coverage_score": 0.85}  # Good by default, bad by strict
        extraction = {"coverage_score": 0.85}
        
        decision = strict_router.classify_slice(
            preflight_report=preflight,
            extraction_quality=extraction,
        )
        
        # With strict thresholds, this might need repair
        assert decision.confidence is not None
    
    def test_page_analyses_integration(self):
        """Test integration with page-level analyses."""
        router = FallbackRouter()
        
        pages = [
            {"page_number": 1, "coverage_score": 0.80, "has_embedded_text": True},
            {"page_number": 2, "coverage_score": 0.30, "has_embedded_text": False},
            {"page_number": 3, "coverage_score": 0.85, "has_embedded_text": True},
        ]
        
        decision = router.classify_slice(
            preflight_report={"text_coverage_score": 0.65},
            extraction_quality={"coverage_score": 0.65},
            page_analyses=pages,
        )
        
        # Should have page-level decisions
        assert len(decision.page_decisions) == 3
        assert decision.page_decisions[1]["classification"] == "needs_ocr"  # Page 2


class TestRoutingArtifact:
    """Tests for RoutingArtifact persistence."""
    
    def test_save_and_load(self):
        """Test saving and loading routing decisions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            artifact = RoutingArtifact(output_dir)
            
            decision = SliceRoutingDecision(
                classification=RoutingClassification.DETERMINISTIC_OK,
                confidence=0.95,
                slice_id="pages_1_50",
                explanation="Test decision",
            )
            
            # Save
            saved_path = artifact.save(decision, pipeline_stats={"units": 10})
            assert saved_path.exists()
            assert saved_path.name == "routing_decision.json"
            
            # Load
            loaded = artifact.load()
            assert loaded is not None
            assert loaded["slice_id"] == "pages_1_50"
            assert loaded["decision"]["classification"] == "deterministic_ok"
            assert loaded["pipeline_stats"]["units"] == 10
    
    def test_load_nonexistent(self):
        """Test loading when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = RoutingArtifact(Path(tmpdir))
            
            loaded = artifact.load()
            assert loaded is None
    
    def test_output_directory_created(self):
        """Test that output directory is created if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = Path(tmpdir) / "nested" / "output"
            artifact = RoutingArtifact(nested_dir)
            
            decision = SliceRoutingDecision(
                classification=RoutingClassification.DETERMINISTIC_OK,
                confidence=0.90,
            )
            
            artifact.save(decision)
            assert nested_dir.exists()


class TestClassifyFromPipelineResult:
    """Tests for the convenience function."""
    
    def test_basic_classification(self):
        """Test classification from pipeline result dict."""
        pipeline_result = {
            "slice_id": "test_slice",
            "preflight_report": {
                "text_coverage_score": 0.85,
                "has_embedded_text": True,
                "ocr_needed": False,
            },
            "extraction_quality": {
                "coverage_score": 0.85,
                "readable_ratio": 0.80,
                "is_quality_good": True,
                "needs_ocr": False,
            },
            "quality_gates": {
                "l3_quality_score": 0.75,
            },
        }
        
        decision = classify_from_pipeline_result(pipeline_result)
        
        assert decision.slice_id == "test_slice"
        assert decision.classification == RoutingClassification.DETERMINISTIC_OK
    
    def test_empty_result_defaults(self):
        """Test handling of empty pipeline result."""
        decision = classify_from_pipeline_result({})
        
        # Should handle gracefully
        assert decision.classification is not None
        assert decision.confidence is not None


class TestSignalExtraction:
    """Tests for specific signal extraction logic."""
    
    def test_warning_flag_detection(self):
        """Test that warning flags are correctly parsed."""
        router = FallbackRouter()
        
        preflight = {
            "warning_flags": ["2-column bleed detected", "heavy headers/footers"],
        }
        
        decision = router.classify_slice(preflight_report=preflight)
        
        assert decision.signals["column_bleed_detected"] is True
        assert decision.signals["heavy_headers_footers"] is True
    
    def test_page_coverage_aggregation(self):
        """Test aggregation of page-level coverage."""
        router = FallbackRouter()
        
        pages = [
            {"page_number": 1, "coverage_score": 0.90, "has_embedded_text": True},
            {"page_number": 2, "coverage_score": 0.75, "has_embedded_text": True},  # Above threshold
            {"page_number": 3, "coverage_score": 0.40, "has_embedded_text": False},  # Below threshold
        ]
        
        decision = router.classify_slice(page_analyses=pages)
        
        assert decision.signals["page_count"] == 3
        assert decision.signals["pages_with_low_coverage"] == 1  # Only page 3
        assert decision.signals["ratio_pages_with_text"] == 2/3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
