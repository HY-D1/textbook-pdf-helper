"""
Tests for pipeline artifact contracts.

Verifies that all required artifacts are created with the correct structure.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from algl_pdf_helper.instructional_models import (
    ConceptUnitEntry,
    ConceptUnitsReport,
    ExtractionReport,
    LLMIntervention,
    LLMInterventionsReport,
)


class TestExtractionReport:
    """Tests for extraction_report.json artifact."""

    def test_extraction_report_required_fields(self):
        """ExtractionReport must have all required fields."""
        report = ExtractionReport(
            source_pdf="test.pdf",
            extraction_method="pymupdf",
            page_count=100,
        )

        data = report.to_dict()
        assert "schema_version" in data
        assert "source_pdf" in data
        assert "extraction_method" in data
        assert "page_count" in data
        assert "chunk_count" in data
        assert "section_count" in data
        assert "use_marker" in data
        assert "use_pymupdf" in data
        assert "ocr_fallback_used" in data
        assert "extraction_timestamp" in data
        assert "repair_applied" in data
        assert "warnings" in data
        assert "errors" in data
        assert "text_coverage_score" in data

    def test_extraction_report_save_and_load(self, tmp_path: Path):
        """ExtractionReport can be saved and loaded."""
        report = ExtractionReport(
            source_pdf="test.pdf",
            extraction_method="marker",
            page_count=50,
            chunk_count=25,
            section_count=10,
            use_marker=True,
            text_coverage_score=0.95,
        )

        output_path = tmp_path / "extraction_report.json"
        report.save(output_path)

        assert output_path.exists()

        loaded = json.loads(output_path.read_text(encoding="utf-8"))
        assert loaded["source_pdf"] == "test.pdf"
        assert loaded["extraction_method"] == "marker"
        assert loaded["page_count"] == 50


class TestLLMInterventionsReport:
    """Tests for llm_interventions.json artifact."""

    def test_llm_interventions_required_fields(self):
        """LLMInterventionsReport must have all required fields."""
        report = LLMInterventionsReport(
            llm_provider="ollama",
            llm_model="qwen3.5:9b",
        )

        data = report.to_dict()
        assert "schema_version" in data
        assert "llm_provider" in data
        assert "llm_model" in data
        assert "ollama_host" in data
        assert "total_interventions" in data
        assert "successful_interventions" in data
        assert "failed_interventions" in data
        assert "interventions" in data
        assert "phase_summary" in data
        assert "generated_at" in data

    def test_add_intervention_updates_stats(self):
        """Adding interventions updates statistics correctly."""
        report = LLMInterventionsReport(
            llm_provider="ollama",
            llm_model="qwen3.5:9b",
        )

        intervention = LLMIntervention(
            intervention_id="int_0001",
            phase="L3_repair",
            target_id="select-basic",
            target_type="concept",
            reason="weak_definition",
            llm_provider="ollama",
            llm_model="qwen3.5:9b",
            outcome="success",
            success=True,
        )

        report.add_intervention(intervention)

        assert report.total_interventions == 1
        assert report.successful_interventions == 1
        assert report.failed_interventions == 0
        assert "L3_repair" in report.phase_summary
        assert report.phase_summary["L3_repair"]["count"] == 1

    def test_llm_intervention_fields(self):
        """LLMIntervention must have all required fields."""
        intervention = LLMIntervention(
            intervention_id="int_0001",
            phase="L3_repair",
            target_id="select-basic",
            target_type="concept",
            reason="weak_definition",
            llm_provider="ollama",
            llm_model="qwen3.5:9b",
            ollama_host="http://localhost:11434",
            outcome="success",
            success=True,
            timestamp="2026-03-17T12:00:00Z",
            duration_seconds=2.5,
            metadata={"confidence": 0.85},
        )

        data = intervention.model_dump()
        assert data["intervention_id"] == "int_0001"
        assert data["phase"] == "L3_repair"
        assert data["target_id"] == "select-basic"
        assert data["llm_provider"] == "ollama"
        assert data["ollama_host"] == "http://localhost:11434"
        assert data["success"] is True


class TestConceptUnitsReport:
    """Tests for concept_units.json artifact."""

    def test_concept_units_required_fields(self):
        """ConceptUnitsReport must have all required fields."""
        report = ConceptUnitsReport(
            source_pdf="test.pdf",
        )

        data = report.to_dict()
        assert "schema_version" in data
        assert "source_pdf" in data
        assert "generated_at" in data
        assert "total_units" in data
        assert "units_by_level" in data
        assert "units" in data

    def test_concept_unit_entry_fields(self):
        """ConceptUnitEntry must have all required fields."""
        entry = ConceptUnitEntry(
            concept_id="select-basic",
            unit_id="unit_001",
            title="SELECT Basics",
            level="L3_explanation",
            unit_type="explanation",
            source_pdf="test.pdf",
            extraction_method="marker",
            generation_mode="extracted",
            confidence=0.85,
        )

        data = entry.model_dump()
        assert data["concept_id"] == "select-basic"
        assert data["unit_id"] == "unit_001"
        assert data["title"] == "SELECT Basics"
        assert data["level"] == "L3_explanation"
        assert data["unit_type"] == "explanation"
        assert data["extraction_method"] == "marker"
        assert data["llm_provider"] is None
        assert data["llm_model"] is None
        assert data["generation_mode"] == "extracted"
        assert data["confidence"] == 0.85
        assert data["quality_flags"] == []
        assert data["has_examples"] is False
        assert data["example_count"] == 0

    def test_add_unit_updates_counts(self):
        """Adding units updates statistics correctly."""
        report = ConceptUnitsReport(source_pdf="test.pdf")

        entry1 = ConceptUnitEntry(
            concept_id="select-basic",
            unit_id="unit_001",
            title="SELECT Basics",
            level="L3_explanation",
            unit_type="explanation",
            source_pdf="test.pdf",
            extraction_method="marker",
            generation_mode="extracted",
            confidence=0.85,
        )
        entry2 = ConceptUnitEntry(
            concept_id="where-clause",
            unit_id="unit_002",
            title="WHERE Clause",
            level="L2_hint_plus_example",
            unit_type="hint",
            source_pdf="test.pdf",
            extraction_method="marker",
            generation_mode="repaired",
            llm_provider="ollama",
            llm_model="qwen3.5:9b",
            confidence=0.90,
        )

        report.add_unit(entry1)
        report.add_unit(entry2)

        assert report.total_units == 2
        assert report.units_by_level.get("L3_explanation") == 1
        assert report.units_by_level.get("L2_hint_plus_example") == 1


class TestArtifactFileStructure:
    """Tests for artifact file structure and content."""

    def test_extraction_report_json_structure(self, tmp_path: Path):
        """extraction_report.json has correct structure when saved."""
        report = ExtractionReport(
            source_pdf="raw_pdf/test.pdf",
            extraction_method="pymupdf",
            page_count=100,
            chunk_count=50,
            section_count=20,
            use_pymupdf=True,
            text_coverage_score=0.92,
            warnings=["Low quality on page 50"],
        )

        output_path = tmp_path / "extraction_report.json"
        report.save(output_path)

        # Verify JSON structure
        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)

        assert data["schema_version"] == "1.0.0"
        assert data["source_pdf"] == "raw_pdf/test.pdf"
        assert data["page_count"] == 100
        assert data["chunk_count"] == 50
        assert data["section_count"] == 20
        assert data["use_pymupdf"] is True
        assert data["text_coverage_score"] == 0.92
        assert len(data["warnings"]) == 1

    def test_llm_interventions_json_structure(self, tmp_path: Path):
        """llm_interventions.json has correct structure when saved."""
        report = LLMInterventionsReport(
            llm_provider="ollama",
            llm_model="qwen3.5:9b-q8_0",
            ollama_host="http://localhost:11434",
        )

        # Add sample interventions
        for i in range(3):
            intervention = LLMIntervention(
                intervention_id=f"int_{i+1:04d}",
                phase="L3_repair" if i < 2 else "boundary_detection",
                target_id=f"concept_{i}",
                target_type="concept",
                reason="weak_content",
                llm_provider="ollama",
                llm_model="qwen3.5:9b-q8_0",
                outcome="success" if i < 2 else "partial",
                success=i < 2,
            )
            report.add_intervention(intervention)

        output_path = tmp_path / "llm_interventions.json"
        report.save(output_path)

        # Verify JSON structure
        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)

        assert data["llm_provider"] == "ollama"
        assert data["llm_model"] == "qwen3.5:9b-q8_0"
        assert data["ollama_host"] == "http://localhost:11434"
        assert data["total_interventions"] == 3
        assert data["successful_interventions"] == 2
        assert data["failed_interventions"] == 1
        assert len(data["interventions"]) == 3
        assert "L3_repair" in data["phase_summary"]
        assert "boundary_detection" in data["phase_summary"]


class TestProcessCommandOptions:
    """Tests for process command options."""

    def test_skip_llm_flag_exists(self):
        """The --skip-llm flag is defined in the CLI."""
        # This is verified by the CLI help test
        # Here we verify the PipelineConfig accepts skip_llm
        from algl_pdf_helper.instructional_pipeline import PipelineConfig

        # Create a minimal config with skip_llm
        # Note: This would fail if the attribute doesn't exist
        import inspect
        sig = inspect.signature(PipelineConfig.__init__)
        assert "skip_llm" in sig.parameters


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
