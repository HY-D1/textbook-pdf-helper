"""
Pydantic Data Models for Instructional Unit Graph.

This module defines the data models for the "grounded instructional unit graph" 
architecture, transforming PDF content into adaptive, traceable teaching artifacts.

The models support:
- Atomic instructional units with precise source grounding
- Concept prerequisite DAGs for adaptive learning paths
- Error-linked misconception remediation
- Spaced repetition reinforcement items
- Complete export manifest for SQL-Adapt integration
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Canonical Content Schemas
# =============================================================================


class SQLExample(BaseModel):
    """
    Canonical schema for SQL examples.
    
    Used consistently across the instructional unit pipeline to ensure
    field name compatibility between generators and exporters.
    """
    
    title: str = Field(
        ..., 
        min_length=1, 
        max_length=200,
        description="Descriptive title of the example"
    )
    scenario: str = Field(
        ..., 
        min_length=10, 
        max_length=500,
        description="Real-world context/description of the scenario"
    )
    sql: str = Field(
        ..., 
        min_length=5, 
        max_length=2000,
        description="The SQL query (canonical field name)"
    )
    explanation: str = Field(
        ..., 
        min_length=20, 
        max_length=1000,
        description="Detailed explanation of how the SQL works"
    )
    expected_output: str | None = Field(
        default=None,
        max_length=500,
        description="Description of expected query output"
    )
    difficulty: str = Field(
        default="beginner",
        description="Difficulty level: beginner, intermediate, advanced"
    )
    schema_used: str = Field(
        default="practice",
        max_length=100,
        description="Name of the schema used (e.g., 'practice', 'users')"
    )
    is_validated: bool = Field(
        default=False,
        description="Whether this example has been validated"
    )
    
    @field_validator("sql")
    @classmethod
    def validate_sql_ends_with_semicolon(cls, v: str) -> str:
        """Ensure SQL query ends with a semicolon."""
        v = v.strip()
        if v and not v.endswith(";"):
            v += ";"
        return v


class PracticeLink(BaseModel):
    """
    Canonical schema for practice problem links.
    
    Maps concepts to related practice problems with difficulty tracking.
    """
    
    concept_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="The concept this link belongs to"
    )
    problem_ids: list[str] = Field(
        default_factory=list,
        description="List of practice problem IDs"
    )
    difficulty_range: tuple[str, str] | None = Field(
        default=None,
        description="(min_difficulty, max_difficulty) tuple"
    )
    
    def add_problem(self, problem_id: str) -> None:
        """Add a problem ID if not already present."""
        if problem_id not in self.problem_ids:
            self.problem_ids.append(problem_id)


class MisconceptionExample(BaseModel):
    """
    Canonical schema for misconception examples.
    
    Documents common mistakes students make with explanations and fixes.
    """
    
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Descriptive name of the error"
    )
    error_sql: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="The incorrect SQL that demonstrates the mistake"
    )
    error_message: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Realistic error message the student would see"
    )
    why_it_happens: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Conceptual explanation of why students make this error"
    )
    fix_sql: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="The corrected SQL that fixes the mistake"
    )
    key_takeaway: str = Field(
        ...,
        min_length=5,
        max_length=300,
        description="One-sentence reminder to avoid this mistake"
    )

# =============================================================================
# L3 Content Model (using canonical schemas)
# =============================================================================


class L3Content(BaseModel):
    """
    Content for L3 full explanation stage - comprehensive.
    
    Uses canonical schema types to ensure consistency between
    generator and exporter field names.
    """
    
    definition: str = Field(
        ...,
        max_length=1000,
        description="What this concept is"
    )
    why_it_matters: str = Field(
        ...,
        max_length=500,
        description="Real-world relevance"
    )
    examples: list[SQLExample] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="SQL examples using canonical schema"
    )
    contrast_example: SQLExample | None = Field(
        default=None,
        description="What NOT to do example (as SQLExample)"
    )
    common_mistakes: list[MisconceptionExample] = Field(
        default_factory=list,
        max_length=5,
        description="Mistakes with fixes using canonical schema"
    )
    practice_links: list[PracticeLink] = Field(
        default_factory=list,
        description="Links to practice problems using canonical schema"
    )
    
    def get_example_by_difficulty(self, difficulty: str) -> SQLExample | None:
        """Get first example matching the specified difficulty."""
        for ex in self.examples:
            if ex.difficulty == difficulty:
                return ex
        return None
    
    def add_practice_link(self, concept_id: str, problem_id: str) -> None:
        """Add a practice problem link for a concept."""
        for link in self.practice_links:
            if link.concept_id == concept_id:
                link.add_problem(problem_id)
                return
        # Create new link if not found
        self.practice_links.append(
            PracticeLink(
                concept_id=concept_id,
                problem_ids=[problem_id]
            )
        )


# =============================================================================
# Version Constants
# =============================================================================

INSTRUCTIONAL_EXPORT_VERSION = "2.0.0"
INSTRUCTIONAL_SCHEMA_ID = "instructional-unit-graph-v2"

# =============================================================================
# Enums (as Literal types for Pydantic compatibility)
# =============================================================================

UnitType = Literal[
    "hint",
    "explanation",
    "worked_example",
    "contrast_example",
    "reflection",
    "practice",
    "prerequisite_repair",
    "misconception_repair",
]

TargetStage = Literal[
    "L1_hint",
    "L2_hint_plus_example",
    "L3_explanation",
    "L4_reflective_note",
    "reinforcement",
]

DifficultyLevel = Literal["beginner", "intermediate", "advanced"]

BlockType = Literal[
    "heading",
    "prose",
    "code",
    "figure",
    "table",
    "exercise",
    "summary",
    "admin",
]

CoverageStatus = Literal["complete", "partial", "missing"]

EdgeType = Literal["hard_prereq", "soft_prereq", "repair_suggestion"]

RemediationLevel = Literal["hint_level", "explanation_level"]

ReinforcementType = Literal[
    "recall_prompt",
    "sql_completion",
    "misconception_discrimination",
    "query_choice",
]


# =============================================================================
# Source Grounding Models
# =============================================================================


class SourceSpan(BaseModel):
    """
    A specific text span within a source document for evidence tracking.
    
    Provides exact character-level grounding for extracted content,
    enabling precise citation and verification of instructional materials.
    """
    
    span_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Unique identifier for this source span",
    )
    doc_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Document identifier (e.g., 'sql-textbook-v1')",
    )
    page_number: int = Field(
        ...,
        ge=1,
        description="Page number where span appears (1-indexed)",
    )
    char_start: int = Field(
        ...,
        ge=0,
        description="Character start position (0-indexed, relative to page)",
    )
    char_end: int = Field(
        ...,
        ge=0,
        description="Character end position (exclusive)",
    )
    block_type: BlockType = Field(
        ...,
        description="Type of content block this span represents",
    )
    text_content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The actual text content of this span",
    )
    extraction_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for extraction quality (0-1)",
    )
    
    @field_validator("char_end")
    @classmethod
    def validate_char_end_greater_than_start(cls, v: int, info) -> int:
        """Ensure char_end is greater than char_start."""
        char_start = info.data.get("char_start")
        if char_start is not None and v <= char_start:
            raise ValueError("char_end must be greater than char_start")
        return v
    
    def to_citation(self) -> str:
        """Generate a human-readable citation string."""
        return f"{self.doc_id}, p.{self.page_number} [{self.char_start}:{self.char_end}]"


# =============================================================================
# Core Instructional Unit Model
# =============================================================================


class InstructionalUnit(BaseModel):
    """
    The core atomic teaching object in the instructional unit graph.
    
    Represents a single, self-contained piece of instructional content
    with full provenance tracking, prerequisite awareness, and difficulty
    classification. Designed for adaptive delivery based on learner state.
    """
    
    unit_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Unique identifier for this instructional unit",
    )
    concept_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Canonical concept reference (e.g., 'select-basic', 'join-inner')",
    )
    unit_type: UnitType = Field(
        ...,
        description="Type of instructional content",
    )
    target_stage: TargetStage = Field(
        ...,
        description="Escalation stage this unit is designed for",
    )
    content: dict[str, Any] = Field(
        default_factory=dict,
        description="The actual teaching content (structure varies by unit_type)",
    )
    error_subtypes: list[str] = Field(
        default_factory=list,
        description="SQL-Engage error subtype IDs this unit addresses",
    )
    prerequisites: list[str] = Field(
        default_factory=list,
        description="Concept IDs that must be mastered before this unit",
    )
    difficulty: DifficultyLevel = Field(
        default="beginner",
        description="Difficulty level of this unit",
    )
    evidence_spans: list[SourceSpan] = Field(
        default_factory=list,
        description="Exact source spans grounding this unit's content",
    )
    source_pages: list[int] = Field(
        default_factory=list,
        description="Page numbers in source document (1-indexed)",
    )
    grounding_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall confidence in content grounding (0-1)",
    )
    estimated_read_time: int = Field(
        default=60,
        ge=1,
        le=3600,
        description="Estimated time to read/absorb in seconds",
    )
    blocked_if_prereq_missing: bool = Field(
        default=True,
        description="Whether to block this unit if prerequisites are unmet",
    )
    
    @field_validator("source_pages")
    @classmethod
    def validate_source_pages_positive(cls, v: list[int]) -> list[int]:
        """Ensure all source pages are positive integers."""
        for page in v:
            if page < 1:
                raise ValueError("All source_pages must be >= 1")
        return v
    
    @field_validator("error_subtypes")
    @classmethod
    def validate_error_subtypes_format(cls, v: list[str]) -> list[str]:
        """Ensure error subtype IDs follow expected format."""
        for subtype in v:
            if len(subtype) < 2:
                raise ValueError(f"Error subtype ID too short: {subtype}")
        return v
    
    def get_primary_source_page(self) -> int | None:
        """Get the primary (first) source page, if available."""
        return self.source_pages[0] if self.source_pages else None
    
    def has_grounding(self) -> bool:
        """Check if this unit has source grounding evidence."""
        return len(self.evidence_spans) > 0 and self.grounding_confidence > 0
    
    def to_summary(self) -> dict[str, Any]:
        """Generate a summary dictionary for quick reference."""
        return {
            "unit_id": self.unit_id,
            "concept_id": self.concept_id,
            "unit_type": self.unit_type,
            "target_stage": self.target_stage,
            "difficulty": self.difficulty,
            "pages": self.source_pages,
            "read_time_sec": self.estimated_read_time,
        }


# =============================================================================
# Concept Graph Models
# =============================================================================


class ConceptNode(BaseModel):
    """
    A node in the concept graph representing a canonical learning objective.
    
    Connects to instructional units and maintains prerequisite relationships
    for building adaptive learning paths.
    """
    
    concept_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Canonical concept identifier (e.g., 'select-basic')",
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Human-readable title of the concept",
    )
    definition: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Clear, concise definition of the concept",
    )
    difficulty: DifficultyLevel = Field(
        default="beginner",
        description="Overall difficulty level of this concept",
    )
    prerequisites: list[str] = Field(
        default_factory=list,
        description="Direct prerequisite concept IDs (edges in the DAG)",
    )
    downstream_concepts: list[str] = Field(
        default_factory=list,
        description="Concepts that depend on this one (reverse edges)",
    )
    repair_first_prereq: str | None = Field(
        default=None,
        max_length=100,
        description="Primary prerequisite to repair if learner struggles",
    )
    unit_ids: list[str] = Field(
        default_factory=list,
        description="References to instructional units for this concept",
    )
    coverage_status: CoverageStatus = Field(
        default="missing",
        description="Coverage status from source materials",
    )
    
    def get_coverage_score(self) -> float:
        """Calculate a coverage score based on status."""
        scores = {"complete": 1.0, "partial": 0.5, "missing": 0.0}
        return scores.get(self.coverage_status, 0.0)
    
    def is_ready(self, mastered_concepts: set[str]) -> bool:
        """Check if this concept is ready to learn given mastered concepts."""
        return all(prereq in mastered_concepts for prereq in self.prerequisites)


class PrerequisiteEdge(BaseModel):
    """
    An edge in the concept prerequisite DAG.
    
    Represents a directed relationship between concepts, indicating
    learning dependencies and repair pathways.
    """
    
    from_concept: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Source concept ID (prerequisite)",
    )
    to_concept: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Target concept ID (dependent)",
    )
    edge_type: EdgeType = Field(
        ...,
        description="Type of prerequisite relationship",
    )
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence in this prerequisite relationship (0-1)",
    )
    
    @field_validator("from_concept")
    @classmethod
    def validate_different_concepts(cls, v: str, info) -> str:
        """Ensure from and to concepts are different."""
        to_concept = info.data.get("to_concept")
        if to_concept is not None and v == to_concept:
            raise ValueError("from_concept and to_concept must be different")
        return v


# =============================================================================
# Misconception Remediation Models
# =============================================================================


class MisconceptionUnit(BaseModel):
    """
    A remediation unit linked to specific SQL-Engage error subtypes.
    
    Provides targeted intervention for known misconceptions, with
    structured content for hint-level and explanation-level repair.
    """
    
    misconception_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Unique identifier for this misconception",
    )
    error_subtype_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="SQL-Engage error subtype ID (e.g., 'E1.1', 'E2.3')",
    )
    concept_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Concept ID where this misconception occurs",
    )
    symptom_description: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Description of observable error symptoms",
    )
    likely_prereq_failure: str | None = Field(
        default=None,
        max_length=100,
        description="Most likely prerequisite concept causing the error",
    )
    remediation_order: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Order in remediation sequence (1 = first)",
    )
    remediation_level: RemediationLevel = Field(
        ...,
        description="Level of remediation (hint vs explanation)",
    )
    repair_content: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured repair content (prompts, explanations, examples)",
    )
    
    def to_repair_strategy(self) -> dict[str, Any]:
        """Generate a repair strategy dictionary for adaptive systems."""
        return {
            "misconception_id": self.misconception_id,
            "error_subtype": self.error_subtype_id,
            "level": self.remediation_level,
            "order": self.remediation_order,
            "prereq_to_repair": self.likely_prereq_failure,
        }


# =============================================================================
# Reinforcement (Spaced Repetition) Models
# =============================================================================


class ReinforcementItem(BaseModel):
    """
    A spaced repetition item for concept reinforcement.
    
    Supports various item types including recall prompts, SQL completions,
    misconception discrimination, and query choice questions.
    """
    
    item_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Unique identifier for this reinforcement item",
    )
    concept_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Concept ID this item reinforces",
    )
    item_type: ReinforcementType = Field(
        ...,
        description="Type of reinforcement item",
    )
    prompt: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="The question or prompt presented to the learner",
    )
    expected_answer: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Expected answer or solution",
    )
    estimated_time_seconds: int = Field(
        default=30,
        ge=5,
        le=600,
        description="Estimated time to complete in seconds",
    )
    
    @field_validator("prompt")
    @classmethod
    def validate_prompt_not_empty(cls, v: str) -> str:
        """Ensure prompt is not just whitespace."""
        if not v.strip():
            raise ValueError("Prompt cannot be empty or whitespace only")
        return v


# =============================================================================
# Export Container Models
# =============================================================================


class UnitLibraryExport(BaseModel):
    """
    Top-level export container for the complete instructional unit library.
    
    This is the primary output format for the PDF → grounded instructional
    unit graph pipeline. Contains all concepts, units, misconceptions,
    reinforcement items, and metadata for SQL-Adapt integration.
    """
    
    export_version: str = Field(
        default=INSTRUCTIONAL_EXPORT_VERSION,
        description="Version of the export format",
    )
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp of export generation",
    )
    source_pdf_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Identifier of the source PDF document",
    )
    concept_ontology: dict[str, Any] = Field(
        default_factory=dict,
        description="Ontology metadata for concepts (taxonomy, versions)",
    )
    concept_graph: dict[str, Any] = Field(
        default_factory=dict,
        description="Serialized concept graph with nodes and edges",
    )
    instructional_units: list[InstructionalUnit] = Field(
        default_factory=list,
        description="All instructional units in the library",
    )
    misconception_bank: list[MisconceptionUnit] = Field(
        default_factory=list,
        description="All misconception remediation units",
    )
    reinforcement_bank: list[ReinforcementItem] = Field(
        default_factory=list,
        description="All spaced repetition reinforcement items",
    )
    quality_report: dict[str, Any] = Field(
        default_factory=dict,
        description="Quality metrics and validation results",
    )
    export_manifest: dict[str, Any] = Field(
        default_factory=dict,
        description="Provenance and export metadata",
    )
    
    @field_validator("export_version")
    @classmethod
    def validate_export_version(cls, v: str) -> str:
        """Ensure export version matches expected format."""
        if v != INSTRUCTIONAL_EXPORT_VERSION:
            raise ValueError(f"export_version must be '{INSTRUCTIONAL_EXPORT_VERSION}'")
        return v
    
    def get_units_for_concept(self, concept_id: str) -> list[InstructionalUnit]:
        """Get all instructional units for a specific concept."""
        return [u for u in self.instructional_units if u.concept_id == concept_id]
    
    def get_misconceptions_for_error(self, error_subtype: str) -> list[MisconceptionUnit]:
        """Get all misconception units for a specific error subtype."""
        return [m for m in self.misconception_bank if m.error_subtype_id == error_subtype]
    
    def get_reinforcement_for_concept(self, concept_id: str) -> list[ReinforcementItem]:
        """Get all reinforcement items for a specific concept."""
        return [r for r in self.reinforcement_bank if r.concept_id == concept_id]
    
    def get_concept_ids(self) -> set[str]:
        """Get all unique concept IDs in the export."""
        ids = set()
        nodes = self.concept_graph.get("nodes", [])
        if nodes:
            ids.update(node.get("concept_id") for node in nodes if node.get("concept_id"))
        # Also collect from units
        ids.update(u.concept_id for u in self.instructional_units)
        return ids
    
    def validate_graph_integrity(self) -> list[str]:
        """
        Validate the integrity of the concept graph.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Get all concept IDs
        all_concept_ids = self.get_concept_ids()
        
        # Validate unit references
        for unit in self.instructional_units:
            if unit.concept_id not in all_concept_ids:
                errors.append(f"Unit {unit.unit_id} references unknown concept: {unit.concept_id}")
            for prereq in unit.prerequisites:
                if prereq not in all_concept_ids:
                    errors.append(f"Unit {unit.unit_id} references unknown prerequisite: {prereq}")
        
        # Validate misconception references
        for misc in self.misconception_bank:
            if misc.concept_id not in all_concept_ids:
                errors.append(f"Misconception {misc.misconception_id} references unknown concept: {misc.concept_id}")
            if misc.likely_prereq_failure and misc.likely_prereq_failure not in all_concept_ids:
                errors.append(
                    f"Misconception {misc.misconception_id} references unknown prereq: {misc.likely_prereq_failure}"
                )
        
        # Validate reinforcement references
        for item in self.reinforcement_bank:
            if item.concept_id not in all_concept_ids:
                errors.append(f"Reinforcement {item.item_id} references unknown concept: {item.concept_id}")
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if the export passes all validation checks."""
        return len(self.validate_graph_integrity()) == 0
    
    def to_json(self) -> str:
        """Serialize the entire export to JSON string."""
        return self.model_dump_json(indent=2)
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize the entire export to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UnitLibraryExport":
        """Create a UnitLibraryExport from a dictionary."""
        return cls(**data)


# =============================================================================
# JSON Schema Export Functions
# =============================================================================


def get_instructional_unit_schema() -> dict[str, Any]:
    """Get the JSON schema for InstructionalUnit."""
    return InstructionalUnit.model_json_schema()


def get_source_span_schema() -> dict[str, Any]:
    """Get the JSON schema for SourceSpan."""
    return SourceSpan.model_json_schema()


def get_concept_node_schema() -> dict[str, Any]:
    """Get the JSON schema for ConceptNode."""
    return ConceptNode.model_json_schema()


def get_prerequisite_edge_schema() -> dict[str, Any]:
    """Get the JSON schema for PrerequisiteEdge."""
    return PrerequisiteEdge.model_json_schema()


def get_misconception_unit_schema() -> dict[str, Any]:
    """Get the JSON schema for MisconceptionUnit."""
    return MisconceptionUnit.model_json_schema()


def get_reinforcement_item_schema() -> dict[str, Any]:
    """Get the JSON schema for ReinforcementItem."""
    return ReinforcementItem.model_json_schema()


def get_unit_library_export_schema() -> dict[str, Any]:
    """Get the JSON schema for UnitLibraryExport."""
    return UnitLibraryExport.model_json_schema()


def get_all_schemas() -> dict[str, dict[str, Any]]:
    """Get all schemas as a dictionary for LLM prompting."""
    return {
        "InstructionalUnit": get_instructional_unit_schema(),
        "SourceSpan": get_source_span_schema(),
        "ConceptNode": get_concept_node_schema(),
        "PrerequisiteEdge": get_prerequisite_edge_schema(),
        "MisconceptionUnit": get_misconception_unit_schema(),
        "ReinforcementItem": get_reinforcement_item_schema(),
        "UnitLibraryExport": get_unit_library_export_schema(),
    }
