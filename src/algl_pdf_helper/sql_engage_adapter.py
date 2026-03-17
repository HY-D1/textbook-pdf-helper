"""
SQL-Engage Backbone Adapter - Normalized Learning Backbone from Repo Truth.

This module builds a normalized backbone view from the repo's existing sources:
- sql_ontology.py (concepts, prerequisites, error subtypes)
- data/practice_map.json (practice problem mappings)

The backbone provides a unified interface for adaptive learning systems,
exposing concept relationships, error mappings, and practice problems.

Usage:
    from sql_engage_adapter import build_backbone, save_backbone

    backbone = build_backbone()
    path = save_backbone(backbone, Path("outputs/sql_engage_backbone.json"))
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .sql_ontology import ConceptOntology, PREREQUISITE_DAG, ERROR_SUBTYPE_TO_CONCEPT_MAPPING


# =============================================================================
# Backbone Data Classes
# =============================================================================

@dataclass
class BackboneConcept:
    """A concept in the SQL-Engage backbone."""

    concept_id: str
    canonical_name: str
    title: str
    category: str
    difficulty: str
    is_core_learning_node: bool
    learning_objectives: list[str] = field(default_factory=list)
    description: str = ""
    # Backbone alignment fields (populated from practice_map if available)
    error_subtypes: list[str] = field(default_factory=list)
    practice_problem_ids: list[str] = field(default_factory=list)
    supports_hintwise: bool = False
    supports_replay: bool = False
    # Source tracking
    backbone_sources: list[str] = field(default_factory=list)


@dataclass
class PrerequisiteEdge:
    """A prerequisite relationship between concepts."""

    from_concept: str
    to_concept: str
    edge_type: str = "requires"
    confidence: float = 0.8


@dataclass
class ErrorSubtypeMapping:
    """Mapping from error subtype to concept."""

    error_subtype_id: str
    concept_ids: list[str]
    description: str = ""
    severity: str = "medium"
    source: str = "sql_ontology"


@dataclass
class PracticeMapEntry:
    """Practice problem mapping for a concept."""

    concept_id: str
    problems: list[dict[str, Any]] = field(default_factory=list)
    total_problems: int = 0
    difficulty_range: dict[str, Any] = field(default_factory=dict)
    source: str = "practice_map"


@dataclass
class SQLEngageBackbone:
    """Complete SQL-Engage backbone structure."""

    schema_version: str = "1.0.0"
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sources: dict[str, Any] = field(default_factory=dict)
    # Core backbone data
    concepts: dict[str, BackboneConcept] = field(default_factory=dict)
    prerequisite_edges: list[PrerequisiteEdge] = field(default_factory=list)
    error_subtype_map: dict[str, ErrorSubtypeMapping] = field(default_factory=dict)
    practice_map: dict[str, PracticeMapEntry] = field(default_factory=dict)
    # Metadata
    stats: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert backbone to dictionary for JSON serialization."""
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "sources": self.sources,
            "concepts": {k: asdict(v) for k, v in self.concepts.items()},
            "prerequisite_edges": [asdict(e) for e in self.prerequisite_edges],
            "error_subtype_map": {k: asdict(v) for k, v in self.error_subtype_map.items()},
            "practice_map": {k: asdict(v) for k, v in self.practice_map.items()},
            "stats": self.stats,
        }

    def save(self, output_path: Path) -> None:
        """Save backbone to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


# =============================================================================
# Backbone Builder
# =============================================================================


def _load_practice_map(practice_map_path: Path | None = None) -> dict[str, Any]:
    """Load practice map from JSON file."""
    if practice_map_path is None:
        # Try to find practice_map.json relative to this file
        practice_map_path = Path(__file__).parent.parent.parent / "data" / "practice_map.json"

    if not practice_map_path.exists():
        return {}

    with open(practice_map_path, encoding="utf-8") as f:
        return json.load(f)


def _build_concepts(ontology: ConceptOntology, practice_map: dict[str, Any]) -> dict[str, BackboneConcept]:
    """Build backbone concepts from ontology and practice map."""
    concepts: dict[str, BackboneConcept] = {}
    practice_concepts = practice_map.get("concepts", {})

    for concept_id in ontology.list_all_concepts():
        concept_data = ontology.get_concept(concept_id)
        if not concept_data:
            continue

        sources = ["sql_ontology"]

        # Get practice map data for this concept if available
        pm_data = practice_concepts.get(concept_id, {})
        problems = pm_data.get("problems", [])

        # Extract error subtypes from practice problems
        error_subtypes: set[str] = set()
        problem_ids: list[str] = []
        supports_hintwise = False
        supports_replay = False

        if problems:
            sources.append("practice_map")
            for problem in problems:
                problem_ids.append(problem.get("problem_id", ""))
                error_subtypes.update(problem.get("error_subtypes", []))
                if problem.get("supports_hintwise"):
                    supports_hintwise = True
                if problem.get("supports_replay"):
                    supports_replay = True

        # Also check ontology error mappings
        for error_subtype, mapped_concepts in ERROR_SUBTYPE_TO_CONCEPT_MAPPING.items():
            if concept_id in mapped_concepts:
                error_subtypes.add(error_subtype)
                if "sql_ontology" not in sources:
                    sources.append("sql_ontology")

        concepts[concept_id] = BackboneConcept(
            concept_id=concept_id,
            canonical_name=concept_data.get("canonical_name", concept_id),
            title=concept_data.get("title", concept_id),
            category=concept_data.get("category", "unknown"),
            difficulty=concept_data.get("difficulty", "beginner"),
            is_core_learning_node=concept_data.get("is_core_learning_node", False),
            learning_objectives=concept_data.get("learning_objectives", []),
            description=concept_data.get("description", ""),
            error_subtypes=sorted(list(error_subtypes)),
            practice_problem_ids=problem_ids,
            supports_hintwise=supports_hintwise,
            supports_replay=supports_replay,
            backbone_sources=sources,
        )

    return concepts


def _build_prerequisite_edges(ontology: ConceptOntology) -> list[PrerequisiteEdge]:
    """Build prerequisite edges from ontology DAG.

    PREREQUISITE_DAG is a list of dicts: {"from": f, "to": t, "type": typ}
    """
    edges: list[PrerequisiteEdge] = []

    for edge_dict in PREREQUISITE_DAG:
        if isinstance(edge_dict, dict):
            from_concept = edge_dict.get("from")
            to_concept = edge_dict.get("to")
            edge_type = edge_dict.get("type", "hard_prereq")
        elif isinstance(edge_dict, (list, tuple)) and len(edge_dict) >= 2:
            # Handle tuple format if present
            from_concept = edge_dict[0]
            to_concept = edge_dict[1]
            edge_type = edge_dict[2] if len(edge_dict) > 2 else "hard_prereq"
        else:
            continue

        if from_concept and to_concept:
            edges.append(
                PrerequisiteEdge(
                    from_concept=from_concept,
                    to_concept=to_concept,
                    edge_type=edge_type,
                    confidence=0.9,  # High confidence for ontology-defined edges
                )
            )

    return edges


def _build_error_subtype_map(ontology: ConceptOntology) -> dict[str, ErrorSubtypeMapping]:
    """Build error subtype mappings from ontology."""
    error_map: dict[str, ErrorSubtypeMapping] = {}

    for error_subtype, concept_ids in ERROR_SUBTYPE_TO_CONCEPT_MAPPING.items():
        error_map[error_subtype] = ErrorSubtypeMapping(
            error_subtype_id=error_subtype,
            concept_ids=concept_ids,
            source="sql_ontology",
        )

    return error_map


def _build_practice_map(practice_map_data: dict[str, Any]) -> dict[str, PracticeMapEntry]:
    """Build practice map entries from practice_map.json data."""
    entries: dict[str, PracticeMapEntry] = {}
    concepts = practice_map_data.get("concepts", {})

    for concept_id, data in concepts.items():
        problems = data.get("problems", [])
        if not problems:
            continue

        # Calculate difficulty range
        difficulties = [p.get("difficulty", "medium") for p in problems]
        difficulty_order = {"beginner": 1, "easy": 2, "medium": 3, "hard": 4, "advanced": 5}
        numeric_diffs = [difficulty_order.get(d, 3) for d in difficulties]

        entries[concept_id] = PracticeMapEntry(
            concept_id=concept_id,
            problems=problems,
            total_problems=len(problems),
            difficulty_range={
                "min": min(difficulties) if difficulties else "medium",
                "max": max(difficulties) if difficulties else "medium",
                "numeric_min": min(numeric_diffs) if numeric_diffs else 3,
                "numeric_max": max(numeric_diffs) if numeric_diffs else 3,
            },
            source="practice_map",
        )

    return entries


def build_backbone(
    practice_map_path: Path | None = None,
    external_csv_path: Path | None = None,
) -> SQLEngageBackbone:
    """
    Build the SQL-Engage backbone from current repo truth.

    Args:
        practice_map_path: Optional path to practice_map.json
        external_csv_path: Optional path to external SQL-Engage CSV data

    Returns:
        SQLEngageBackbone with normalized view of learning structure
    """
    ontology = ConceptOntology()
    practice_map_data = _load_practice_map(practice_map_path)

    # Track sources used
    sources = {
        "sql_ontology": {
            "concept_count": len(ontology.list_all_concepts()),
            "error_subtype_count": len(ontology.list_all_error_subtypes()),
            "prerequisite_edge_count": len(PREREQUISITE_DAG),
        },
        "practice_map": {
            "path": str(practice_map_path) if practice_map_path else "data/practice_map.json",
            "concept_count": len(practice_map_data.get("concepts", {})),
            "present": bool(practice_map_data),
        },
    }

    # Note if external CSV was provided (but we don't require it)
    if external_csv_path:
        sources["external_csv"] = {
            "path": str(external_csv_path),
            "present": external_csv_path.exists(),
            "loaded": False,  # Not implemented in default path
            "note": "External CSV support reserved for future extension",
        }

    # Build backbone components
    concepts = _build_concepts(ontology, practice_map_data)
    edges = _build_prerequisite_edges(ontology)
    error_map = _build_error_subtype_map(ontology)
    practice_entries = _build_practice_map(practice_map_data)

    # Calculate stats
    stats = {
        "total_concepts": len(concepts),
        "core_learning_nodes": sum(1 for c in concepts.values() if c.is_core_learning_node),
        "prerequisite_edges": len(edges),
        "error_subtypes_mapped": len(error_map),
        "concepts_with_practice_problems": len(practice_entries),
        "concepts_with_hintwise_support": sum(1 for c in concepts.values() if c.supports_hintwise),
        "concepts_with_replay_support": sum(1 for c in concepts.values() if c.supports_replay),
    }

    return SQLEngageBackbone(
        sources=sources,
        concepts=concepts,
        prerequisite_edges=edges,
        error_subtype_map=error_map,
        practice_map=practice_entries,
        stats=stats,
    )


def save_backbone(backbone: SQLEngageBackbone, output_path: Path) -> Path:
    """
    Save backbone to JSON file.

    Args:
        backbone: SQLEngageBackbone to save
        output_path: Path to write JSON file

    Returns:
        Path to saved file
    """
    backbone.save(output_path)
    return output_path


def load_backbone(path: Path) -> dict[str, Any]:
    """
    Load a previously saved backbone from JSON.

    Args:
        path: Path to backbone JSON file

    Returns:
        Backbone as dictionary
    """
    with open(path, encoding="utf-8") as f:
        return json.load(f)
