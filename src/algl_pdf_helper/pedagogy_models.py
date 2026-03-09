"""
Pedagogy Models for Textbook Structure Preservation.

This module defines data models for capturing and preserving the pedagogical
structure of textbooks including:
- Chapter organization and topic hierarchies
- Exercises with solutions and concept mappings
- SQL examples with provenance and paired-page tracking
- Learning path categorization (developer, admin, design)

These models complement the concept-based instructional units by preserving
the original textbook's pedagogical sequencing and structure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Path Type Enumeration
# =============================================================================

class LearningPathType(str, Enum):
    """
    Learning path categories for SQL textbook content.
    
    Murach and similar textbooks often organize content into tracks
    for different reader goals and roles.
    """
    DEVELOPER = "developer"      # Core query skills, application development
    ADMIN = "admin"              # DBA tasks, security, backup, maintenance
    DESIGN = "design"            # Normalization, ERD, schema design
    GENERAL = "general"          # Content applicable to all paths


# =============================================================================
# Chapter Structure Models
# =============================================================================

@dataclass
class TopicInfo:
    """
    A topic within a chapter - represents a cohesive learning unit.
    
    Topics are more granular than chapters and often map directly
    to specific concepts or small groups of related concepts.
    """
    topic_id: str                          # Unique identifier (e.g., "ch3-select-basics")
    title: str                             # Topic title
    concept_ids: list[str] = field(default_factory=list)  # Mapped concept IDs
    example_refs: list[str] = field(default_factory=list)  # Example IDs in this topic
    page_range: tuple[int, int] = field(default_factory=lambda: (0, 0))  # Start, end pages
    subsection_ids: list[str] = field(default_factory=list)  # Subsection identifiers (e.g., ["3.1", "3.2"])
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "topic_id": self.topic_id,
            "title": self.title,
            "concept_ids": self.concept_ids,
            "example_refs": self.example_refs,
            "page_range": list(self.page_range),
            "subsection_ids": self.subsection_ids,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TopicInfo:
        """Create from dictionary."""
        page_range = data.get("page_range", [0, 0])
        if isinstance(page_range, list) and len(page_range) == 2:
            page_range = tuple(page_range)
        else:
            page_range = (0, 0)
        
        return cls(
            topic_id=data["topic_id"],
            title=data["title"],
            concept_ids=data.get("concept_ids", []),
            example_refs=data.get("example_refs", []),
            page_range=page_range,
            subsection_ids=data.get("subsection_ids", []),
        )


@dataclass
class ChapterSummary:
    """Summary content at the end of a chapter."""
    key_points: list[str] = field(default_factory=list)
    terms: list[dict[str, str]] = field(default_factory=list)  # [{"term": "...", "definition": "..."}]
    skills_checklist: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "key_points": self.key_points,
            "terms": self.terms,
            "skills_checklist": self.skills_checklist,
        }


@dataclass
class ChapterInfo:
    """
    Complete information about a textbook chapter.
    
    Captures the pedagogical organization including topics, exercises,
    page ranges, and learning path categorization.
    """
    chapter_number: int
    chapter_title: str
    topics: list[TopicInfo] = field(default_factory=list)
    exercises: list[str] = field(default_factory=list)  # Exercise IDs
    page_range: tuple[int, int] = field(default_factory=lambda: (0, 0))
    path_type: str = "general"  # "developer", "admin", "design", "general"
    summary: ChapterSummary | None = None
    objectives: list[str] = field(default_factory=list)  # Learning objectives
    prerequisites: list[str] = field(default_factory=list)  # Prerequisite chapter numbers
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "chapter_number": self.chapter_number,
            "chapter_title": self.chapter_title,
            "topics": [t.to_dict() for t in self.topics],
            "exercises": self.exercises,
            "page_range": list(self.page_range),
            "path_type": self.path_type,
            "summary": self.summary.to_dict() if self.summary else None,
            "objectives": self.objectives,
            "prerequisites": self.prerequisites,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChapterInfo:
        """Create from dictionary."""
        page_range = data.get("page_range", [0, 0])
        if isinstance(page_range, list) and len(page_range) == 2:
            page_range = tuple(page_range)
        else:
            page_range = (0, 0)
        
        summary_data = data.get("summary")
        summary = ChapterSummary(**summary_data) if summary_data else None
        
        return cls(
            chapter_number=data["chapter_number"],
            chapter_title=data["chapter_title"],
            topics=[TopicInfo.from_dict(t) for t in data.get("topics", [])],
            exercises=data.get("exercises", []),
            page_range=page_range,
            path_type=data.get("path_type", "general"),
            summary=summary,
            objectives=data.get("objectives", []),
            prerequisites=data.get("prerequisites", []),
        )
    
    @property
    def page_count(self) -> int:
        """Calculate the number of pages in this chapter."""
        start, end = self.page_range
        if start > 0 and end >= start:
            return end - start + 1
        return 0
    
    def get_concept_ids(self) -> set[str]:
        """Get all concept IDs covered in this chapter."""
        concepts = set()
        for topic in self.topics:
            concepts.update(topic.concept_ids)
        return concepts


# =============================================================================
# Exercise Models
# =============================================================================

@dataclass
class ExerciseInfo:
    """
    An end-of-chapter exercise with full metadata.
    
    Exercises are practice problems that appear at the end of chapters,
    distinct from the examples that appear within the instructional text.
    """
    exercise_id: str                       # Unique ID (e.g., "murach-ch3-ex1")
    chapter_number: int
    exercise_number: int                   # Sequential within chapter
    problem_text: str                      # The exercise problem statement
    solution_text: str | None = None       # Solution/explanation (if available)
    concepts_tested: list[str] = field(default_factory=list)  # Concept IDs tested
    difficulty: str = "beginner"           # "beginner", "intermediate", "advanced"
    exercise_type: str = "coding"          # "coding", "conceptual", "debugging"
    page_number: int | None = None         # Page where exercise appears
    hints: list[str] = field(default_factory=list)  # Progressive hints
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "exercise_id": self.exercise_id,
            "chapter": self.chapter_number,
            "exercise_number": self.exercise_number,
            "problem": self.problem_text,
            "solution": self.solution_text,
            "concepts": self.concepts_tested,
            "difficulty": self.difficulty,
            "exercise_type": self.exercise_type,
            "page": self.page_number,
            "hints": self.hints,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExerciseInfo:
        """Create from dictionary."""
        return cls(
            exercise_id=data["exercise_id"],
            chapter_number=data.get("chapter", 0),
            exercise_number=data.get("exercise_number", 0),
            problem_text=data.get("problem", ""),
            solution_text=data.get("solution"),
            concepts_tested=data.get("concepts", []),
            difficulty=data.get("difficulty", "beginner"),
            exercise_type=data.get("exercise_type", "coding"),
            page_number=data.get("page"),
            hints=data.get("hints", []),
        )


# =============================================================================
# Example Models
# =============================================================================

@dataclass
class ExampleInfo:
    """
    An SQL example from the textbook with full provenance.
    
    Examples are the illustrative SQL code that appears within the
    instructional text, distinct from end-of-chapter exercises.
    
    Tracks paired-page format (common in Murach books) where syntax
    appears on one page and explanation on the facing page.
    """
    example_id: str                        # Unique ID (e.g., "murach-ch3-ex1")
    chapter_number: int
    page_number: int                       # Primary page location
    sql_code: str                          # The SQL code
    explanation: str                       # Explanation of what it does
    concept_ids: list[str] = field(default_factory=list)  # Related concepts
    paired_with: str | None = None         # Reference to facing-page explanation
    is_paired_format: bool = False         # True if part of paired-page layout
    example_type: str = "syntax"           # "syntax", "application", "variation"
    schema_context: str | None = None      # Database schema used
    expected_output: str | None = None     # Description of expected results
    line_numbers: tuple[int, int] | None = None  # Line range in source
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "example_id": self.example_id,
            "chapter": self.chapter_number,
            "page": self.page_number,
            "sql": self.sql_code,
            "explanation": self.explanation,
            "concepts": self.concept_ids,
            "paired_with": self.paired_with,
            "is_paired_format": self.is_paired_format,
            "example_type": self.example_type,
        }
        if self.schema_context:
            result["schema"] = self.schema_context
        if self.expected_output:
            result["expected_output"] = self.expected_output
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExampleInfo:
        """Create from dictionary."""
        return cls(
            example_id=data["example_id"],
            chapter_number=data.get("chapter", 0),
            page_number=data.get("page", 0),
            sql_code=data.get("sql", ""),
            explanation=data.get("explanation", ""),
            concept_ids=data.get("concepts", []),
            paired_with=data.get("paired_with"),
            is_paired_format=data.get("is_paired_format", False),
            example_type=data.get("example_type", "syntax"),
            schema_context=data.get("schema"),
            expected_output=data.get("expected_output"),
        )


# =============================================================================
# Pydantic Models for Export
# =============================================================================

class ChapterGraphEntry(BaseModel):
    """
    Pydantic model for chapter_graph.json entries.
    
    Represents a chapter in the export format suitable for
    consumption by adaptive learning systems.
    """
    
    chapter_number: int = Field(..., ge=1, description="Chapter number (1-indexed)")
    title: str = Field(..., min_length=1, description="Chapter title")
    page_range: list[int] = Field(..., min_length=2, max_length=2, description="[start, end] pages")
    topics: list[dict[str, Any]] = Field(default_factory=list, description="Topics within chapter")
    exercises: list[str] = Field(default_factory=list, description="Exercise IDs")
    path_type: str = Field(default="general", description="Learning path: developer, admin, design")
    objectives: list[str] = Field(default_factory=list, description="Learning objectives")
    
    @field_validator("path_type")
    @classmethod
    def validate_path_type(cls, v: str) -> str:
        """Ensure path_type is valid."""
        valid = {"developer", "admin", "design", "general"}
        if v not in valid:
            raise ValueError(f"path_type must be one of {valid}")
        return v


class ExerciseBankEntry(BaseModel):
    """
    Pydantic model for exercise_bank.jsonl entries.
    
    Each line in the JSONL file is one ExerciseBankEntry.
    """
    
    exercise_id: str = Field(..., min_length=1, description="Unique exercise identifier")
    chapter: int = Field(..., ge=1, description="Chapter number")
    exercise_number: int = Field(..., ge=1, description="Sequential within chapter")
    problem: str = Field(..., min_length=5, description="Exercise problem statement")
    solution: str | None = Field(default=None, description="Solution text if available")
    concepts: list[str] = Field(default_factory=list, description="Concept IDs tested")
    difficulty: str = Field(default="beginner", description="Difficulty level")
    exercise_type: str = Field(default="coding", description="Type of exercise")
    page: int | None = Field(default=None, ge=1, description="Page number")
    
    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: str) -> str:
        """Ensure difficulty is valid."""
        valid = {"beginner", "intermediate", "advanced"}
        if v not in valid:
            return "beginner"  # Default fallback
        return v


class ExampleBankEntry(BaseModel):
    """
    Pydantic model for example_bank.jsonl entries.
    
    Each line in the JSONL file is one ExampleBankEntry.
    """
    
    example_id: str = Field(..., min_length=1, description="Unique example identifier")
    chapter: int = Field(..., ge=1, description="Chapter number")
    page: int = Field(..., ge=1, description="Page number")
    sql: str = Field(..., min_length=5, description="SQL code")
    explanation: str = Field(..., min_length=10, description="Explanation of the SQL")
    concepts: list[str] = Field(default_factory=list, description="Related concept IDs")
    paired_with: str | None = Field(default=None, description="Reference to paired explanation")
    is_paired_format: bool = Field(default=False, description="Part of paired-page layout")
    example_type: str = Field(default="syntax", description="Type of example")
    schema_used: str | None = Field(default=None, description="Database schema context")


# =============================================================================
# Navigation Index Model
# =============================================================================

class NavigationIndex(BaseModel):
    """
    Navigation structure for accessing content by different organizations.
    
    Provides:
    - by_concept: Concept-centric organization (existing)
    - by_chapter: Chapter-sequential organization (new)
    - by_path: Learning path filtering (developer, admin, design)
    """
    
    by_concept: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Concept ID → {chapter, topics, units, exercises}"
    )
    by_chapter: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Chapter number → {title, topics, concepts, exercises}"
    )
    by_path: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Path type → list of concept IDs"
    )
    
    def add_concept_mapping(
        self,
        concept_id: str,
        chapter_number: int | None,
        topic_ids: list[str],
        exercise_ids: list[str],
    ) -> None:
        """Add a concept's location information to the index."""
        self.by_concept[concept_id] = {
            "chapter": chapter_number,
            "topics": topic_ids,
            "exercises": exercise_ids,
        }
    
    def add_chapter_mapping(
        self,
        chapter_number: int,
        title: str,
        topic_ids: list[str],
        concept_ids: list[str],
        exercise_ids: list[str],
    ) -> None:
        """Add a chapter's content information to the index."""
        self.by_chapter[str(chapter_number)] = {
            "title": title,
            "topics": topic_ids,
            "concepts": concept_ids,
            "exercises": exercise_ids,
        }
    
    def add_path_concept(self, path_type: str, concept_id: str) -> None:
        """Add a concept to a learning path."""
        if path_type not in self.by_path:
            self.by_path[path_type] = []
        if concept_id not in self.by_path[path_type]:
            self.by_path[path_type].append(concept_id)


# =============================================================================
# Pedagogy Manifest
# =============================================================================

class PedagogyManifest(BaseModel):
    """
    Complete manifest of textbook pedagogy structure.
    
    Contains all chapter, exercise, and example metadata in a
    single structure for easy access and validation.
    """
    
    version: str = Field(default="1.0.0", description="Schema version")
    source_doc_id: str = Field(..., description="Source document identifier")
    generated_at: str = Field(..., description="ISO 8601 timestamp")
    
    # Summary statistics
    total_chapters: int = Field(default=0, ge=0)
    total_exercises: int = Field(default=0, ge=0)
    total_examples: int = Field(default=0, ge=0)
    
    # Path distribution
    developer_path_concepts: list[str] = Field(default_factory=list)
    admin_path_concepts: list[str] = Field(default_factory=list)
    design_path_concepts: list[str] = Field(default_factory=list)
    
    # Paired-page format detection
    paired_page_format_detected: bool = Field(default=False)
    paired_examples_count: int = Field(default=0, ge=0)
    
    # Navigation index
    navigation: NavigationIndex = Field(default_factory=NavigationIndex)
    
    def get_summary(self) -> dict[str, Any]:
        """Generate a summary of the pedagogy structure."""
        return {
            "total_chapters": self.total_chapters,
            "total_exercises": self.total_exercises,
            "total_examples": self.total_examples,
            "paired_page_format": self.paired_page_format_detected,
            "paths": {
                "developer": len(self.developer_path_concepts),
                "admin": len(self.admin_path_concepts),
                "design": len(self.design_path_concepts),
            },
            "navigation": {
                "concepts_indexed": len(self.navigation.by_concept),
                "chapters_indexed": len(self.navigation.by_chapter),
                "paths_indexed": len(self.navigation.by_path),
            },
        }


# =============================================================================
# Utility Functions
# =============================================================================

def detect_paired_page_format(examples: list[ExampleInfo], threshold: float = 0.3) -> bool:
    """
    Detect if textbook uses paired-page format.
    
    Paired-page format (common in Murach books) has:
    - Syntax/code on one page
    - Explanation on facing page
    
    Args:
        examples: List of extracted examples
        threshold: Minimum ratio of paired examples to consider it paired-page
        
    Returns:
        True if paired-page format detected
    """
    if not examples:
        return False
    
    paired_count = sum(1 for e in examples if e.is_paired_format)
    ratio = paired_count / len(examples)
    
    return ratio >= threshold


def estimate_progressive_structure(chapters: list[ChapterInfo]) -> dict[str, Any]:
    """
    Analyze the progressive/difficulty structure of chapters.
    
    Returns statistics about how difficulty progresses through chapters.
    """
    if not chapters:
        return {}
    
    sorted_chapters = sorted(chapters, key=lambda c: c.chapter_number)
    
    # Analyze topic density
    topic_counts = [len(c.topics) for c in sorted_chapters]
    avg_topics = sum(topic_counts) / len(topic_counts) if topic_counts else 0
    
    # Analyze exercise density
    exercise_counts = [len(c.exercises) for c in sorted_chapters]
    avg_exercises = sum(exercise_counts) / len(exercise_counts) if exercise_counts else 0
    
    return {
        "total_chapters": len(chapters),
        "topic_density": {
            "average_per_chapter": avg_topics,
            "max": max(topic_counts) if topic_counts else 0,
            "min": min(topic_counts) if topic_counts else 0,
        },
        "exercise_density": {
            "average_per_chapter": avg_exercises,
            "max": max(exercise_counts) if exercise_counts else 0,
            "min": min(exercise_counts) if exercise_counts else 0,
        },
        "path_distribution": {
            "developer": len([c for c in chapters if c.path_type == "developer"]),
            "admin": len([c for c in chapters if c.path_type == "admin"]),
            "design": len([c for c in chapters if c.path_type == "design"]),
            "general": len([c for c in chapters if c.path_type == "general"]),
        },
    }


def infer_path_type(chapter_title: str, topics: list[str]) -> str:
    """
    Infer the learning path type from chapter/topic content.
    
    Args:
        chapter_title: The chapter title
        topics: List of topic titles
        
    Returns:
        Path type: "developer", "admin", "design", or "general"
    """
    title_lower = chapter_title.lower()
    topics_text = " ".join(t.lower() for t in topics)
    
    # Admin indicators
    admin_keywords = [
        "security", "backup", "restore", "maintenance", "administration",
        "dba", "privilege", "grant", "revoke", "user management",
        "performance", "optimization", "indexing", "transaction log",
    ]
    if any(kw in title_lower or kw in topics_text for kw in admin_keywords):
        return "admin"
    
    # Design indicators
    design_keywords = [
        "design", "normalization", "erd", "entity-relationship", "schema",
        "database design", "data modeling", "relational model",
        "constraint", "foreign key", "primary key design",
    ]
    if any(kw in title_lower or kw in topics_text for kw in design_keywords):
        return "design"
    
    # Developer indicators (default for most SQL content)
    developer_keywords = [
        "query", "select", "join", "subquery", "function", "procedure",
        "trigger", "view", "application", "development", "programming",
    ]
    if any(kw in title_lower or kw in topics_text for kw in developer_keywords):
        return "developer"
    
    return "general"


def generate_exercise_id(doc_id: str, chapter: int, exercise_num: int) -> str:
    """Generate a standard exercise ID."""
    return f"{doc_id}-ch{chapter}-ex{exercise_num}"


def generate_example_id(doc_id: str, chapter: int, example_num: int) -> str:
    """Generate a standard example ID."""
    return f"{doc_id}-ch{chapter}-ex{example_num}"


def is_likely_exercise_section(text: str) -> bool:
    """
    Check if text appears to be an exercise section header.
    
    Args:
        text: Text to check
        
    Returns:
        True if likely an exercise section
    """
    import re
    exercise_patterns = [
        r'^\s*exercises?\s*$',
        r'^\s*practice\s+exercises?\s*$',
        r'^\s*end\s+of\s+chapter\s+exercises?\s*$',
        r'^\s*review\s+questions?\s*$',
        r'^\s*programming\s+exercises?\s*$',
    ]
    text_lower = text.lower().strip()
    return any(re.match(p, text_lower) for p in exercise_patterns)


def is_likely_example(text: str, context: str = "") -> bool:
    """
    Check if text appears to be an SQL example with explanation.
    
    Args:
        text: The text content
        context: Surrounding context
        
    Returns:
        True if likely an example
    """
    import re
    
    # SQL code indicator
    sql_pattern = re.search(
        r'\b(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\s+.+?FROM\s+\w+',
        text,
        re.IGNORECASE | re.DOTALL
    )
    
    if not sql_pattern:
        return False
    
    # Example indicators in context
    example_indicators = [
        r'example\s*\d*[:.]?\s*$',
        r'for\s+example',
        r'illustrates?\s+',
        r'figure\s*\d+',
        r'listing\s*\d+',
    ]
    
    combined = (context + " " + text[:200]).lower()
    has_indicator = any(re.search(p, combined) for p in example_indicators)
    
    return has_indicator or sql_pattern
