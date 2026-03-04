"""
Structured Pydantic Models for Pedagogical Content Generation.

This module defines strict schemas for LLM outputs to ensure:
- Type safety and validation
- Consistent structure across all generated content
- Clear contracts for downstream processing
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# SQL EXAMPLE MODELS
# =============================================================================

class SQLExample(BaseModel):
    """
    A validated SQL example with explanation.
    
    All SQL examples must include a description, the actual query,
    an explanation of how it works, and the schema used.
    """
    description: str = Field(
        ...,  # Required field
        min_length=10,
        max_length=500,
        description="Brief description of what this example demonstrates"
    )
    query: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="The SQL query (must end with semicolon)"
    )
    explanation: str = Field(
        ...,
        min_length=20,
        max_length=1000,
        description="Detailed explanation of how the query works"
    )
    schema_used: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the practice schema used (e.g., 'users', 'orders')"
    )
    difficulty: Literal["beginner", "intermediate", "advanced"] = Field(
        default="beginner",
        description="Difficulty level of this example"
    )
    
    @field_validator("query")
    @classmethod
    def validate_sql_ends_with_semicolon(cls, v: str) -> str:
        """Ensure SQL query ends with a semicolon."""
        v = v.strip()
        if not v.endswith(";"):
            v += ";"
        return v
    
    @field_validator("query")
    @classmethod
    def validate_sql_starts_with_keyword(cls, v: str) -> str:
        """Ensure SQL query starts with a valid keyword."""
        v_stripped = v.strip().upper()
        valid_starts = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "WITH"]
        if not any(v_stripped.startswith(kw) for kw in valid_starts):
            raise ValueError(f"SQL query must start with one of: {', '.join(valid_starts)}")
        return v


# =============================================================================
# COMMON MISTAKE MODELS
# =============================================================================

class Mistake(BaseModel):
    """
    A documented common mistake with correction.
    
    Captures the error type, incorrect SQL, correct SQL, and explanation
    to help students learn from typical errors.
    """
    error_type: str = Field(
        ...,
        min_length=5,
        max_length=200,
        description="Type of error (e.g., 'Missing WHERE clause')"
    )
    incorrect_sql: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="The incorrect SQL that causes the error"
    )
    correct_sql: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="The corrected SQL that works properly"
    )
    explanation: str = Field(
        ...,
        min_length=20,
        max_length=1000,
        description="Explanation of why the error occurs and how to avoid it"
    )
    error_message: str = Field(
        default="",
        max_length=500,
        description="Typical error message the student would see"
    )
    key_takeaway: str = Field(
        default="",
        max_length=300,
        description="One-sentence takeaway to remember"
    )
    
    @field_validator("correct_sql")
    @classmethod
    def validate_correct_sql_ends_with_semicolon(cls, v: str) -> str:
        """Ensure correct SQL ends with a semicolon."""
        v = v.strip()
        if not v.endswith(";"):
            v += ";"
        return v


# =============================================================================
# PRACTICE REFERENCE MODELS
# =============================================================================

class PracticeReference(BaseModel):
    """
    Reference to a practice problem or exercise.
    """
    problem_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Unique identifier for the practice problem"
    )
    title: str = Field(
        default="",
        max_length=200,
        description="Human-readable title of the practice problem"
    )
    difficulty: Literal["beginner", "intermediate", "advanced"] = Field(
        default="beginner",
        description="Difficulty level of this practice problem"
    )
    concept_alignment: str = Field(
        default="",
        max_length=300,
        description="How this problem aligns with the concept being taught"
    )


# =============================================================================
# MAIN PEDAGOGICAL CONCEPT MODEL
# =============================================================================

class PedagogicalConcept(BaseModel):
    """
    Complete pedagogical concept with all educational content.
    
    This is the top-level model that represents a single SQL concept
    with all its educational materials properly structured.
    """
    
    # Core identification
    concept_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Unique identifier for this concept"
    )
    title: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Human-readable title of the concept"
    )
    difficulty: Literal["beginner", "intermediate", "advanced"] = Field(
        default="beginner",
        description="Overall difficulty level of this concept"
    )
    
    # Core content
    definition: str = Field(
        ...,
        min_length=50,
        max_length=1000,
        description="Clear, concise definition of the concept (150-250 words recommended)"
    )
    key_points: list[str] = Field(
        default_factory=list,
        min_length=1,
        max_length=10,
        description="Key learning points (3-7 points recommended)"
    )
    
    # SQL Examples (must have at least 1)
    examples: list[SQLExample] = Field(
        default_factory=list,
        min_length=1,
        max_length=5,
        description="SQL examples demonstrating this concept (1-3 recommended)"
    )
    
    # Common mistakes (must have at least 1)
    common_mistakes: list[Mistake] = Field(
        default_factory=list,
        min_length=1,
        max_length=5,
        description="Common mistakes students make (2-3 recommended)"
    )
    
    # Practice references
    practice_references: list[PracticeReference] = Field(
        default_factory=list,
        max_length=10,
        description="References to related practice problems"
    )
    
    # Metadata
    estimated_time_minutes: int = Field(
        default=15,
        ge=5,
        le=120,
        description="Estimated time to learn this concept in minutes"
    )
    prerequisites: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="List of prerequisite concept IDs"
    )
    tags: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Tags for categorization (e.g., 'sql', 'query', 'join')"
    )
    
    @field_validator("key_points")
    @classmethod
    def validate_key_points_not_empty(cls, v: list[str]) -> list[str]:
        """Ensure key points are not empty strings."""
        if not v:
            return v
        for point in v:
            if len(point.strip()) < 5:
                raise ValueError("Each key point must be at least 5 characters")
        return v
    
    @field_validator("tags")
    @classmethod
    def validate_tags_lowercase(cls, v: list[str]) -> list[str]:
        """Normalize tags to lowercase."""
        return [tag.lower().strip() for tag in v if tag.strip()]


# =============================================================================
# GENERATION RESULT MODELS
# =============================================================================

class ValidationError(BaseModel):
    """A single validation error with context."""
    field: str = Field(..., description="Field that failed validation")
    error: str = Field(..., description="Error message")
    value: str = Field(default="", description="The invalid value (truncated)")


class GenerationResult(BaseModel):
    """
    Result of a pedagogical content generation attempt.
    
    Includes the generated content (if successful) and any validation errors.
    """
    success: bool = Field(..., description="Whether generation succeeded")
    concept: PedagogicalConcept | None = Field(
        default=None,
        description="The generated concept (if successful)"
    )
    validation_errors: list[ValidationError] = Field(
        default_factory=list,
        description="List of validation errors (if any)"
    )
    attempts: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of generation attempts made"
    )
    model_used: str = Field(
        default="",
        description="Name of the model used for generation"
    )
    generation_time_seconds: float = Field(
        default=0.0,
        ge=0,
        description="Time taken to generate in seconds"
    )


# =============================================================================
# QUALITY GATE MODELS
# =============================================================================

class QualityCheckResult(BaseModel):
    """Result of a single quality check."""
    check_name: str = Field(..., description="Name of the quality check")
    passed: bool = Field(..., description="Whether the check passed")
    score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Quality score for this check (0-1)"
    )
    message: str = Field(
        default="",
        description="Human-readable message about the check result"
    )


class QualityGateResult(BaseModel):
    """
    Result of quality gate checks for a concept.
    
    Aggregates all quality checks and provides overall pass/fail status.
    """
    concept_id: str = Field(..., description="Concept that was checked")
    overall_passed: bool = Field(..., description="Whether all required checks passed")
    checks: list[QualityCheckResult] = Field(
        default_factory=list,
        description="Individual check results"
    )
    total_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall quality score (0-1)"
    )
    
    def get_failed_checks(self) -> list[QualityCheckResult]:
        """Get list of failed checks."""
        return [c for c in self.checks if not c.passed]
    
    def get_passed_checks(self) -> list[QualityCheckResult]:
        """Get list of passed checks."""
        return [c for c in self.checks if c.passed]


# =============================================================================
# JSON SCHEMA EXPORT
# =============================================================================

def get_pedagogical_concept_schema() -> dict:
    """
    Get the JSON schema for PedagogicalConcept.
    
    This can be included in LLM prompts to enforce structured output.
    """
    return PedagogicalConcept.model_json_schema()


def get_sql_example_schema() -> dict:
    """Get the JSON schema for SQLExample."""
    return SQLExample.model_json_schema()


def get_mistake_schema() -> dict:
    """Get the JSON schema for Mistake."""
    return Mistake.model_json_schema()
