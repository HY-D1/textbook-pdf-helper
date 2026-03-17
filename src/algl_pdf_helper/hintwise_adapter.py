"""
HintWise Adapter - Contract Layer for Hint System Integration.

This module defines an explicit adapter contract between helper outputs and
a future HintWise-style consumer. It transforms current helper repo truth into
a payload that a hint system could consume.

IMPORTANT: This is a contract layer only. It does NOT call a live HintWise service.
All payloads are generated from local data only.

Usage:
    from hintwise_adapter import make_hintwise_payload, HintwisePayload

    # From a concept unit (or backbone concept)
    payload = make_hintwise_payload(unit_data)
    print(payload.to_dict())
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


# =============================================================================
# HintWise Payload Models
# =============================================================================

@dataclass
class LearnerContext:
    """Learner/problem context reference."""

    learner_id: str | None = None
    session_id: str | None = None
    problem_id: str | None = None
    # Escalation level of the current interaction
    escalation_level: str = "L1"  # L1, L2, L3, L4
    # Previous hints shown in this session
    previous_hint_ids: list[str] = field(default_factory=list)
    # Current error state if any
    current_error_subtype: str | None = None


@dataclass
class ConceptContext:
    """Concept-related context for hint selection."""

    concept_id: str = ""
    concept_title: str = ""
    unit_id: str | None = None
    # Candidate units that could be shown
    candidate_unit_ids: list[str] = field(default_factory=list)
    # Type of unit: explanation, hint, misconception, example
    unit_type: str = "explanation"
    # Error subtypes associated with this concept
    error_subtypes: list[str] = field(default_factory=list)
    # Prerequisites for this concept
    prerequisites: list[str] = field(default_factory=list)
    # Practice problems linked to this concept
    practice_problem_ids: list[str] = field(default_factory=list)


@dataclass
class ProvenanceRefs:
    """Evidence/provenance references for audit trail."""

    # Source of the unit content
    source_pdf: str | None = None
    source_pages: list[int] = field(default_factory=list)
    extraction_method: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    # Backbone data sources
    backbone_sources: list[str] = field(default_factory=list)


@dataclass
class HintwisePayload:
    """
    Complete HintWise adapter payload.

    This is the contract between the PDF helper and a hint system.
    It contains everything needed for the hint system to select
    and deliver appropriate guidance to the learner.
    """

    # Schema version for contract evolution
    schema_version: str = "1.0.0"

    # Core context
    learner_context: LearnerContext = field(default_factory=LearnerContext)
    concept_context: ConceptContext = field(default_factory=ConceptContext)

    # Feature flags from backbone
    supports_hintwise: bool = False
    supports_replay: bool = False

    # Provenance for transparency
    provenance: ProvenanceRefs = field(default_factory=ProvenanceRefs)

    # Metadata
    generated_at: str | None = None
    generation_source: str = "pdf_helper_local"

    def to_dict(self) -> dict[str, Any]:
        """Convert payload to dictionary for serialization."""
        return asdict(self)

    def is_valid(self) -> bool:
        """Check if payload has minimum required fields."""
        return bool(self.concept_context.concept_id)

    def get_hint_eligibility(self) -> dict[str, Any]:
        """
        Return hint eligibility assessment.

        This helps the hint system decide what types of hints can be shown.
        """
        return {
            "eligible_for_hints": self.supports_hintwise,
            "eligible_for_replay": self.supports_replay,
            "escalation_level": self.learner_context.escalation_level,
            "has_prerequisites": len(self.concept_context.prerequisites) > 0,
            "has_practice_problems": len(self.concept_context.practice_problem_ids) > 0,
            "has_error_subtypes": len(self.concept_context.error_subtypes) > 0,
        }


# =============================================================================
# Payload Builders
# =============================================================================


def make_hintwise_payload(
    unit_or_concept: dict[str, Any],
    learner_context: dict[str, Any] | None = None,
) -> HintwisePayload:
    """
    Create a HintWise payload from a concept unit or backbone concept.

    Args:
        unit_or_concept: Dictionary containing concept/unit data
        learner_context: Optional learner context override

    Returns:
        HintwisePayload ready for hint system consumption
    """
    # Determine if this is a concept unit or backbone concept
    is_backbone = "backbone_sources" in unit_or_concept

    # Extract concept context
    concept_ctx = ConceptContext(
        concept_id=unit_or_concept.get("concept_id", ""),
        concept_title=unit_or_concept.get("title", unit_or_concept.get("concept_title", "")),
        unit_id=unit_or_concept.get("unit_id"),
        unit_type=unit_or_concept.get("unit_type", "explanation"),
        error_subtypes=unit_or_concept.get("error_subtypes", []),
        prerequisites=unit_or_concept.get("prerequisites", []),
        practice_problem_ids=unit_or_concept.get("practice_problem_ids", []),
    )

    # Extract learner context
    if learner_context:
        learner_ctx = LearnerContext(**learner_context)
    else:
        learner_ctx = LearnerContext(
            escalation_level=_infer_escalation_level(unit_or_concept),
        )

    # Extract provenance
    if is_backbone:
        provenance = ProvenanceRefs(
            backbone_sources=unit_or_concept.get("backbone_sources", []),
        )
    else:
        provenance = ProvenanceRefs(
            source_pdf=unit_or_concept.get("source_pdf"),
            source_pages=unit_or_concept.get("source_pages", []),
            extraction_method=unit_or_concept.get("extraction_method"),
            llm_provider=unit_or_concept.get("llm_provider"),
            llm_model=unit_or_concept.get("llm_model"),
            backbone_sources=unit_or_concept.get("backbone_sources", []),
        )

    return HintwisePayload(
        learner_context=learner_ctx,
        concept_context=concept_ctx,
        supports_hintwise=unit_or_concept.get("supports_hintwise", False),
        supports_replay=unit_or_concept.get("supports_replay", False),
        provenance=provenance,
        generation_source="pdf_helper_local",
    )


def make_hintwise_payload_from_backbone(
    backbone_concept: dict[str, Any],
    learner_id: str | None = None,
    problem_id: str | None = None,
) -> HintwisePayload:
    """
    Create a HintWise payload from a backbone concept entry.

    Args:
        backbone_concept: Backbone concept dictionary
        learner_id: Optional learner identifier
        problem_id: Optional problem identifier

    Returns:
        HintwisePayload
    """
    return HintwisePayload(
        learner_context=LearnerContext(
            learner_id=learner_id,
            problem_id=problem_id,
            escalation_level="L1",
        ),
        concept_context=ConceptContext(
            concept_id=backbone_concept.get("concept_id", ""),
            concept_title=backbone_concept.get("title", ""),
            unit_type="explanation",
            error_subtypes=backbone_concept.get("error_subtypes", []),
            practice_problem_ids=backbone_concept.get("practice_problem_ids", []),
        ),
        supports_hintwise=backbone_concept.get("supports_hintwise", False),
        supports_replay=backbone_concept.get("supports_replay", False),
        provenance=ProvenanceRefs(
            backbone_sources=backbone_concept.get("backbone_sources", []),
        ),
        generation_source="pdf_helper_backbone",
    )


def _infer_escalation_level(unit_data: dict[str, Any]) -> str:
    """Infer escalation level from unit type/level."""
    level = unit_data.get("level", "")
    unit_type = unit_data.get("unit_type", "")

    if "L1" in level or unit_type == "escalation":
        return "L1"
    elif "L2" in level or unit_type == "hint":
        return "L2"
    elif "L3" in level or unit_type == "explanation":
        return "L3"
    elif "L4" in level or unit_type == "misconception":
        return "L4"

    return "L1"  # Default


# =============================================================================
# Example Payloads for Documentation/Testing
# =============================================================================


def get_example_payload() -> HintwisePayload:
    """Return an example payload for documentation and testing."""
    return HintwisePayload(
        learner_context=LearnerContext(
            learner_id="learner_123",
            session_id="session_456",
            problem_id="select-basic-01",
            escalation_level="L2",
            previous_hint_ids=["hint_001"],
            current_error_subtype="missing_comma_in_select",
        ),
        concept_context=ConceptContext(
            concept_id="select-basic",
            concept_title="SELECT Statement Basics",
            unit_id="unit_select_basic_001",
            unit_type="hint",
            candidate_unit_ids=["unit_001", "unit_002", "unit_003"],
            error_subtypes=["missing_comma_in_select", "select_star_misuse"],
            prerequisites=[],
            practice_problem_ids=["prob_001", "prob_002", "prob_003"],
        ),
        supports_hintwise=True,
        supports_replay=True,
        provenance=ProvenanceRefs(
            source_pdf="murach_sql_2015.pdf",
            source_pages=[45, 46],
            extraction_method="marker",
            llm_provider="ollama",
            llm_model="qwen3.5:9b-q8_0",
            backbone_sources=["sql_ontology", "practice_map"],
        ),
        generation_source="pdf_helper_example",
    )


def get_minimal_payload() -> HintwisePayload:
    """Return a minimal valid payload."""
    return HintwisePayload(
        concept_context=ConceptContext(concept_id="select-basic"),
    )
