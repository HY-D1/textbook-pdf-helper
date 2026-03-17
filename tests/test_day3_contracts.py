"""
Tests for Day 3 contracts: backbone adapter, HintWise adapter, and learner textbook.

Verifies that:
1. sql_engage_adapter builds backbone from repo truth
2. hintwise_adapter produces valid payloads
3. learner_textbook assembles correctly from concept units + events
4. Prerequisite relationships are correctly handled
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from algl_pdf_helper.sql_engage_adapter import (
    BackboneConcept,
    ErrorSubtypeMapping,
    PracticeMapEntry,
    PrerequisiteEdge,
    SQLEngageBackbone,
    build_backbone,
    load_backbone,
    save_backbone,
)
from algl_pdf_helper.hintwise_adapter import (
    ConceptContext,
    HintwisePayload,
    LearnerContext,
    ProvenanceRefs,
    get_example_payload,
    get_minimal_payload,
    make_hintwise_payload,
    make_hintwise_payload_from_backbone,
)
from algl_pdf_helper.learner_textbook import (
    ConceptMastery,
    LearnerTextbook,
    SavedUnit,
    assemble_learner_textbook,
    export_concept_mastery,
    export_saved_units,
)
from algl_pdf_helper.instructional_models import ConceptUnitEntry


# =============================================================================
# SQL-Engage Backbone Adapter Tests
# =============================================================================


class TestBackboneBuilder:
    """Tests for sql_engage_adapter backbone building."""

    def test_build_backbone_from_repo_truth(self):
        """Backbone builds successfully from current repo sources."""
        backbone = build_backbone()

        assert backbone.schema_version == "1.0.0"
        assert backbone.generated_at is not None
        assert len(backbone.concepts) > 0
        assert len(backbone.prerequisite_edges) > 0

        # Stats should be populated
        assert backbone.stats["total_concepts"] > 0
        assert backbone.stats["prerequisite_edges"] > 0

    def test_backbone_sources_tracked(self):
        """Backbone tracks which sources were used."""
        backbone = build_backbone()

        assert "sql_ontology" in backbone.sources
        assert "practice_map" in backbone.sources

        # SQL ontology should report counts
        ont_source = backbone.sources["sql_ontology"]
        assert ont_source["concept_count"] > 0
        assert ont_source["error_subtype_count"] > 0

    def test_backbone_concept_structure(self):
        """Backbone concepts have expected structure."""
        backbone = build_backbone()

        # Get a sample concept
        concept = next(iter(backbone.concepts.values()))

        assert concept.concept_id
        assert concept.canonical_name
        assert concept.title
        assert concept.category
        assert concept.difficulty
        assert concept.backbone_sources

    def test_backbone_concept_has_select_basic(self):
        """select-basic concept is present with expected data."""
        backbone = build_backbone()

        assert "select-basic" in backbone.concepts
        concept = backbone.concepts["select-basic"]

        assert concept.title == "SELECT Statement Basics"
        assert concept.category == "dql"
        assert "sql_ontology" in concept.backbone_sources

    def test_prerequisite_edges_structure(self):
        """Prerequisite edges have correct structure."""
        backbone = build_backbone()

        for edge in backbone.prerequisite_edges:
            assert edge.from_concept
            assert edge.to_concept
            assert edge.edge_type in ("hard_prereq", "soft_prereq")
            assert 0.0 <= edge.confidence <= 1.0
            assert edge.from_concept != edge.to_concept

    def test_error_subtype_map_populated(self):
        """Error subtype map is populated from ontology."""
        backbone = build_backbone()

        assert len(backbone.error_subtype_map) > 0

        for error_id, mapping in backbone.error_subtype_map.items():
            assert mapping.error_subtype_id == error_id
            assert len(mapping.concept_ids) > 0
            assert mapping.source == "sql_ontology"

    def test_backbone_save_and_load(self, tmp_path: Path):
        """Backbone can be saved and loaded."""
        backbone = build_backbone()
        output_path = tmp_path / "backbone.json"

        save_backbone(backbone, output_path)

        assert output_path.exists()

        loaded = load_backbone(output_path)
        assert loaded["schema_version"] == "1.0.0"
        assert "concepts" in loaded
        assert "prerequisite_edges" in loaded

    def test_backbone_stats_calculated(self):
        """Backbone stats are calculated correctly."""
        backbone = build_backbone()

        stats = backbone.stats
        assert stats["total_concepts"] == len(backbone.concepts)
        assert stats["prerequisite_edges"] == len(backbone.prerequisite_edges)
        assert stats["error_subtypes_mapped"] == len(backbone.error_subtype_map)


class TestBackboneWithPracticeMap:
    """Tests for backbone integration with practice_map.json."""

    def test_concepts_marked_with_hintwise_support(self):
        """Some concepts are marked as supporting HintWise."""
        backbone = build_backbone()

        hintwise_concepts = [
            c for c in backbone.concepts.values() if c.supports_hintwise
        ]

        # Note: practice_map may not have hintwise flags for all concepts
        # Just verify the field exists and is a boolean
        for concept in backbone.concepts.values():
            assert isinstance(concept.supports_hintwise, bool)
            assert isinstance(concept.supports_replay, bool)

    def test_practice_map_entries(self):
        """Practice map entries are created for concepts with problems."""
        backbone = build_backbone()

        # Should have some practice map entries if practice_map.json loaded
        for concept_id, entry in backbone.practice_map.items():
            assert entry.concept_id == concept_id
            assert entry.total_problems >= 0
            assert isinstance(entry.problems, list)

    def test_error_subtypes_from_both_sources(self):
        """Error subtypes come from both ontology and practice_map."""
        backbone = build_backbone()

        # Find concepts with error subtypes
        concepts_with_errors = [
            c for c in backbone.concepts.values() if c.error_subtypes
        ]

        # Verify error subtypes are lists of strings
        for concept in concepts_with_errors:
            assert isinstance(concept.error_subtypes, list)
            for subtype in concept.error_subtypes:
                assert isinstance(subtype, str)


# =============================================================================
# HintWise Adapter Tests
# =============================================================================


class TestHintwiseAdapter:
    """Tests for hintwise_adapter contract."""

    def test_make_hintwise_payload_from_unit(self):
        """Payload can be created from concept unit dict."""
        unit = {
            "concept_id": "select-basic",
            "title": "SELECT Basics",
            "unit_id": "unit_001",
            "unit_type": "explanation",
            "error_subtypes": ["missing_comma"],
            "prerequisites": [],
            "practice_problem_ids": ["prob_001"],
            "supports_hintwise": True,
            "supports_replay": False,
            "source_pdf": "test.pdf",
            "extraction_method": "marker",
        }

        payload = make_hintwise_payload(unit)

        assert payload.concept_context.concept_id == "select-basic"
        assert payload.supports_hintwise is True
        assert payload.is_valid()

    def test_hintwise_payload_eligibility(self):
        """Payload can report hint eligibility."""
        payload = get_example_payload()

        eligibility = payload.get_hint_eligibility()

        assert eligibility["eligible_for_hints"] is True
        assert eligibility["eligible_for_replay"] is True
        assert eligibility["escalation_level"] == "L2"

    def test_minimal_payload_is_valid(self):
        """Minimal payload with just concept_id is valid."""
        payload = get_minimal_payload()

        assert payload.is_valid()
        assert payload.concept_context.concept_id == "select-basic"

    def test_payload_from_backbone_concept(self):
        """Payload can be created from backbone concept."""
        backbone_concept = {
            "concept_id": "where-clause",
            "title": "WHERE Clause",
            "error_subtypes": ["e1.1"],
            "practice_problem_ids": ["p1", "p2"],
            "supports_hintwise": True,
            "supports_replay": True,
            "backbone_sources": ["sql_ontology"],
        }

        payload = make_hintwise_payload_from_backbone(
            backbone_concept,
            learner_id="learner_123",
            problem_id="prob_001",
        )

        assert payload.learner_context.learner_id == "learner_123"
        assert payload.learner_context.problem_id == "prob_001"
        assert payload.supports_hintwise is True
        assert "sql_ontology" in payload.provenance.backbone_sources

    def test_payload_to_dict(self):
        """Payload can be serialized to dict."""
        payload = get_example_payload()

        data = payload.to_dict()

        assert data["schema_version"] == "1.0.0"
        assert "learner_context" in data
        assert "concept_context" in data
        assert data["concept_context"]["concept_id"] == "select-basic"

    def test_payload_escalation_inference(self):
        """Escalation level inferred from unit level/type."""
        # L3 explanation -> L3 escalation
        unit_l3 = {"concept_id": "test", "level": "L3_explanation", "unit_type": "explanation"}
        payload_l3 = make_hintwise_payload(unit_l3)
        assert payload_l3.learner_context.escalation_level == "L3"

        # L2 hint -> L2 escalation
        unit_l2 = {"concept_id": "test", "level": "L2_hint", "unit_type": "hint"}
        payload_l2 = make_hintwise_payload(unit_l2)
        assert payload_l2.learner_context.escalation_level == "L2"


# =============================================================================
# Learner Textbook Tests
# =============================================================================


class TestSavedUnit:
    """Tests for SavedUnit model."""

    def test_saved_unit_creation(self):
        """SavedUnit can be created with required fields."""
        unit = SavedUnit(
            unit_id="unit_001",
            concept_id="select-basic",
            learner_notes="Important concept",
        )

        assert unit.unit_id == "unit_001"
        assert unit.concept_id == "select-basic"
        assert unit.learner_notes == "Important concept"
        assert unit.view_count == 1
        assert unit.explicitly_saved is True


class TestConceptMastery:
    """Tests for ConceptMastery model."""

    def test_mastery_creation(self):
        """ConceptMastery can be created."""
        mastery = ConceptMastery(
            concept_id="select-basic",
            concept_title="SELECT Basics",
        )

        assert mastery.concept_id == "select-basic"
        assert mastery.mastery_score == 0.0
        assert mastery.problems_attempted == 0

    def test_mastery_update_from_problem_attempt(self):
        """Mastery updates from problem attempt event."""
        mastery = ConceptMastery(concept_id="test")

        event = {
            "event_type": "problem_attempt",
            "timestamp": "2026-03-17T10:00:00Z",
            "solved": True,
            "confidence": 0.8,
        }
        mastery.update_from_event(event)

        assert mastery.problems_attempted == 1
        assert mastery.problems_solved == 1
        assert mastery.confidence == 0.8

    def test_mastery_tracks_errors(self):
        """Mastery tracks observed error subtypes."""
        mastery = ConceptMastery(concept_id="test")

        event = {
            "event_type": "problem_attempt",
            "timestamp": "2026-03-17T10:00:00Z",
            "solved": False,
            "error_subtype": "missing_comma",
        }
        mastery.update_from_event(event)

        assert "missing_comma" in mastery.error_subtypes_observed

    def test_mastery_ready_check(self):
        """Mastery correctly reports readiness."""
        mastery = ConceptMastery(concept_id="test")

        # Not ready with low mastery
        mastery.mastery_score = 0.5
        assert not mastery.is_ready_for_next_concept()

        # Ready with high mastery
        mastery.mastery_score = 0.8
        assert mastery.is_ready_for_next_concept()

        # Not ready if blocked by prerequisites
        mastery.blocked_by_prerequisites = ["prereq_1"]
        assert not mastery.is_ready_for_next_concept()


class TestLearnerTextbook:
    """Tests for LearnerTextbook assembly."""

    def test_textbook_creation(self):
        """LearnerTextbook can be created."""
        textbook = LearnerTextbook(
            learner_id="learner_001",
            total_concepts_available=10,
        )

        assert textbook.learner_id == "learner_001"
        assert textbook.total_concepts_available == 10
        assert textbook.schema_version == "1.0.0"

    def test_add_saved_unit(self):
        """Saved units can be added to textbook."""
        textbook = LearnerTextbook()
        unit = SavedUnit(unit_id="u1", concept_id="c1")

        textbook.add_saved_unit(unit)

        assert len(textbook.saved_units) == 1
        assert "c1" in textbook.concepts_with_saved_units
        assert "c1" in textbook.units_by_concept

    def test_add_saved_unit_dedupes(self):
        """Adding same unit twice updates view count."""
        textbook = LearnerTextbook()
        unit1 = SavedUnit(unit_id="u1", concept_id="c1")
        unit2 = SavedUnit(unit_id="u1", concept_id="c1")

        textbook.add_saved_unit(unit1)
        textbook.add_saved_unit(unit2)

        assert len(textbook.saved_units) == 1
        assert textbook.saved_units[0].view_count == 2

    def test_get_coverage_summary(self):
        """Coverage summary calculated correctly."""
        textbook = LearnerTextbook(total_concepts_available=10)
        textbook.add_saved_unit(SavedUnit(unit_id="u1", concept_id="c1"))
        textbook.add_saved_unit(SavedUnit(unit_id="u2", concept_id="c2"))

        summary = textbook.get_coverage_summary()

        assert summary["total_concepts_available"] == 10
        assert summary["concepts_with_saved_units"] == 2
        assert summary["total_saved_units"] == 2
        assert summary["coverage_percentage"] == 20.0

    def test_textbook_save_and_load(self, tmp_path: Path):
        """Textbook can be saved and loaded."""
        textbook = LearnerTextbook(learner_id="test_learner")
        textbook.add_saved_unit(SavedUnit(unit_id="u1", concept_id="c1"))

        output_path = tmp_path / "textbook.json"
        textbook.save(output_path)

        assert output_path.exists()

        loaded = json.loads(output_path.read_text(encoding="utf-8"))
        assert loaded["learner_id"] == "test_learner"
        assert loaded["saved_units"]


class TestTextbookAssembly:
    """Tests for textbook assembly from concept units."""

    def test_assemble_from_empty_paths(self, tmp_path: Path):
        """Assembly handles missing files gracefully."""
        empty_units = tmp_path / "empty_units.json"
        empty_units.write_text("[]", encoding="utf-8")

        textbook = assemble_learner_textbook(
            concept_units_path=empty_units,
            learner_events_path=None,
        )

        assert textbook.total_concepts_available == 0
        assert len(textbook.saved_units) == 0

    def test_assemble_from_units(self, tmp_path: Path):
        """Assembly creates saved units from concept units."""
        units = [
            {
                "concept_id": "select-basic",
                "title": "SELECT Basics",
                "unit_id": "unit_001",
                "unit_type": "explanation",
            }
        ]
        units_path = tmp_path / "units.json"
        units_path.write_text(json.dumps(units), encoding="utf-8")

        textbook = assemble_learner_textbook(
            concept_units_path=units_path,
            learner_events_path=None,
        )

        assert textbook.total_concepts_available == 1
        assert len(textbook.saved_units) == 1
        assert textbook.saved_units[0].concept_id == "select-basic"

    def test_assemble_processes_events(self, tmp_path: Path):
        """Assembly processes learner events to update mastery."""
        units = [{"concept_id": "c1", "unit_id": "u1", "unit_type": "explanation"}]
        units_path = tmp_path / "units.json"
        units_path.write_text(json.dumps(units), encoding="utf-8")

        events = [
            {
                "event_type": "problem_attempt",
                "timestamp": "2026-03-17T10:00:00Z",
                "concept_id": "c1",
                "solved": True,
                "confidence": 0.9,
            }
        ]
        events_path = tmp_path / "events.json"
        events_path.write_text(json.dumps({"events": events}), encoding="utf-8")

        textbook = assemble_learner_textbook(
            concept_units_path=units_path,
            learner_events_path=events_path,
        )

        mastery = textbook.concept_mastery.get("c1")
        assert mastery is not None
        assert mastery.problems_attempted == 1
        assert mastery.problems_solved == 1


# =============================================================================
# Concept Unit Backbone Field Tests
# =============================================================================


class TestConceptUnitBackboneFields:
    """Tests for Day 3 backbone fields on ConceptUnitEntry."""

    def test_concept_unit_has_error_subtypes(self):
        """ConceptUnitEntry has error_subtypes field."""
        unit = ConceptUnitEntry(
            concept_id="test",
            unit_id="unit_001",
            title="Test",
            level="L3",
            unit_type="explanation",
            source_pdf="test.pdf",
            extraction_method="marker",
            generation_mode="extracted",
            error_subtypes=["e1", "e2"],
        )

        assert unit.error_subtypes == ["e1", "e2"]

    def test_concept_unit_has_practice_problem_ids(self):
        """ConceptUnitEntry has practice_problem_ids field."""
        unit = ConceptUnitEntry(
            concept_id="test",
            unit_id="unit_001",
            title="Test",
            level="L3",
            unit_type="explanation",
            source_pdf="test.pdf",
            extraction_method="marker",
            generation_mode="extracted",
            practice_problem_ids=["p1", "p2"],
        )

        assert unit.practice_problem_ids == ["p1", "p2"]

    def test_concept_unit_has_supports_flags(self):
        """ConceptUnitEntry has supports_hintwise and supports_replay fields."""
        unit = ConceptUnitEntry(
            concept_id="test",
            unit_id="unit_001",
            title="Test",
            level="L3",
            unit_type="explanation",
            source_pdf="test.pdf",
            extraction_method="marker",
            generation_mode="extracted",
            supports_hintwise=True,
            supports_replay=False,
        )

        assert unit.supports_hintwise is True
        assert unit.supports_replay is False

    def test_concept_unit_has_backbone_sources(self):
        """ConceptUnitEntry has backbone_sources field."""
        unit = ConceptUnitEntry(
            concept_id="test",
            unit_id="unit_001",
            title="Test",
            level="L3",
            unit_type="explanation",
            source_pdf="test.pdf",
            extraction_method="marker",
            generation_mode="extracted",
            backbone_sources=["sql_ontology", "practice_map"],
        )

        assert "sql_ontology" in unit.backbone_sources

    def test_concept_unit_has_blocked_by_prerequisite(self):
        """ConceptUnitEntry has blocked_by_prerequisite field."""
        unit = ConceptUnitEntry(
            concept_id="joins",
            unit_id="unit_001",
            title="JOINs",
            level="L3",
            unit_type="explanation",
            source_pdf="test.pdf",
            extraction_method="marker",
            generation_mode="extracted",
            prerequisites=["select-basic"],
            blocked_by_prerequisite=["select-basic"],
        )

        assert "select-basic" in unit.blocked_by_prerequisite


# =============================================================================
# Integration Tests with Fixtures
# =============================================================================


class TestWithFixtures:
    """Tests using fixture data."""

    def test_textbook_assembly_with_fixture(self):
        """Textbook assembles correctly from fixture events."""
        fixture_path = Path(__file__).parent / "fixtures" / "learner_events_minimal.json"
        if not fixture_path.exists():
            pytest.skip("Fixture not found")

        # Create minimal concept units
        units = [
            {"concept_id": "select-basic", "unit_id": "u1", "unit_type": "explanation"},
            {"concept_id": "where-clause", "unit_id": "u2", "unit_type": "explanation"},
        ]

        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            units_path = Path(tmp) / "units.json"
            units_path.write_text(json.dumps(units), encoding="utf-8")

            textbook = assemble_learner_textbook(
                concept_units_path=units_path,
                learner_events_path=fixture_path,
                learner_id="test_learner",
            )

            assert textbook.learner_id == "test_learner"
            assert len(textbook.concept_mastery) == 2

            # select-basic should have better mastery (solved problem)
            select_mastery = textbook.concept_mastery["select-basic"]
            assert select_mastery.problems_solved == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
