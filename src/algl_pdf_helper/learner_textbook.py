"""
Learner Textbook - Personal Textbook Assembly from Concept Units.

This module provides models and assembly logic for creating learner-specific
textbook views from exported concept units and learner interaction events.

Features:
- LearnerTextbook: Personal view with saved units and notes
- SavedUnit: A unit saved by the learner for review
- ConceptMastery: Mastery tracking for each concept
- Assembly from concept units + synthetic learner events

Usage:
    from learner_textbook import assemble_learner_textbook, LearnerTextbook

    textbook = assemble_learner_textbook(
        concept_units_path=Path("outputs/concept_units.json"),
        learner_events_path=Path("tests/fixtures/learner_events.json"),
    )
    textbook.save(Path("outputs/learner_textbook.json"))
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class SavedUnit:
    """A unit saved by the learner for later review."""

    unit_id: str
    concept_id: str
    saved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    # User notes attached to this saved unit
    learner_notes: str = ""
    # How many times the learner has viewed this unit
    view_count: int = 1
    # Last viewed timestamp
    last_viewed_at: str | None = None
    # Source of the unit
    source_type: str = "explanation"  # explanation, hint, misconception, example
    # Whether this was explicitly saved or auto-saved
    explicitly_saved: bool = True


@dataclass
class ConceptMastery:
    """Mastery tracking for a single concept."""

    concept_id: str
    concept_title: str = ""
    # Mastery level: 0.0 to 1.0
    mastery_score: float = 0.0
    # Confidence in the mastery score
    confidence: float = 0.0
    # Evidence sources for this mastery score
    evidence_sources: list[str] = field(default_factory=list)
    # Practice problem performance
    problems_attempted: int = 0
    problems_solved: int = 0
    # Error patterns observed
    error_subtypes_observed: list[str] = field(default_factory=list)
    # Prerequisites that need work
    blocked_by_prerequisites: list[str] = field(default_factory=list)
    # Last interaction timestamp
    last_interaction_at: str | None = None
    # Recommended next units
    recommended_unit_ids: list[str] = field(default_factory=list)

    def update_from_event(self, event: dict[str, Any]) -> None:
        """Update mastery based on a learner event."""
        event_type = event.get("event_type", "")

        if event_type == "problem_attempt":
            self.problems_attempted += 1
            if event.get("solved", False):
                self.problems_solved += 1
            if "error_subtype" in event:
                self.error_subtypes_observed.append(event["error_subtype"])
            if "confidence" in event:
                # Weighted average update
                old_weight = self.problems_attempted - 1
                new_confidence = event["confidence"]
                if old_weight > 0:
                    self.confidence = (self.confidence * old_weight + new_confidence) / self.problems_attempted
                else:
                    self.confidence = new_confidence

        elif event_type == "unit_completed":
            # Increase mastery slightly for completing educational content
            completion_boost = event.get("completion_score", 0.1)
            self.mastery_score = min(1.0, self.mastery_score + completion_boost)
            if "unit_id" in event and event["unit_id"] not in self.recommended_unit_ids:
                self.evidence_sources.append(f"completed:{event['unit_id']}")

        self.last_interaction_at = event.get("timestamp")

    def is_ready_for_next_concept(self) -> bool:
        """Check if learner is ready to move to next concept."""
        return self.mastery_score >= 0.7 and not self.blocked_by_prerequisites


@dataclass
class LearnerTextbook:
    """
    Personal learner textbook assembled from concept units.

    Contains saved units, concept mastery tracking, and notes.
    """

    # Schema version
    schema_version: str = "1.0.0"
    # Learner identifier
    learner_id: str = "anonymous"
    # When this textbook was assembled
    assembled_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Source data references
    source_concept_units_path: str | None = None
    source_learner_events_path: str | None = None

    # Core content
    saved_units: list[SavedUnit] = field(default_factory=list)
    concept_mastery: dict[str, ConceptMastery] = field(default_factory=dict)

    # Organization
    # Units grouped by concept for navigation
    units_by_concept: dict[str, list[str]] = field(default_factory=dict)
    # Learning path order (prerequisite-aware)
    recommended_concept_order: list[str] = field(default_factory=list)

    # Coverage tracking
    total_concepts_available: int = 0
    concepts_with_saved_units: set[str] = field(default_factory=set)

    # Metadata
    assembly_stats: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert sets to lists for JSON serialization
        data["concepts_with_saved_units"] = list(self.concepts_with_saved_units)
        return data

    def save(self, output_path: Path) -> None:
        """Save textbook to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    def add_saved_unit(self, unit: SavedUnit) -> None:
        """Add a saved unit, deduplicating by unit_id."""
        # Check if already exists
        existing = next((u for u in self.saved_units if u.unit_id == unit.unit_id), None)
        if existing:
            # Update view count and timestamp
            existing.view_count += 1
            existing.last_viewed_at = unit.saved_at
            if unit.learner_notes:
                existing.learner_notes = unit.learner_notes
        else:
            self.saved_units.append(unit)
            self.concepts_with_saved_units.add(unit.concept_id)

        # Update units_by_concept
        if unit.concept_id not in self.units_by_concept:
            self.units_by_concept[unit.concept_id] = []
        if unit.unit_id not in self.units_by_concept[unit.concept_id]:
            self.units_by_concept[unit.concept_id].append(unit.unit_id)

    def get_mastery(self, concept_id: str) -> ConceptMastery:
        """Get or create mastery record for a concept."""
        if concept_id not in self.concept_mastery:
            self.concept_mastery[concept_id] = ConceptMastery(concept_id=concept_id)
        return self.concept_mastery[concept_id]

    def get_coverage_summary(self) -> dict[str, Any]:
        """Return coverage summary for this learner."""
        mastered_concepts = [
            c for c in self.concept_mastery.values()
            if c.mastery_score >= 0.7
        ]
        return {
            "total_concepts_available": self.total_concepts_available,
            "concepts_with_saved_units": len(self.concepts_with_saved_units),
            "concepts_mastered": len(mastered_concepts),
            "total_saved_units": len(self.saved_units),
            "coverage_percentage": (
                len(self.concepts_with_saved_units) / self.total_concepts_available * 100
                if self.total_concepts_available > 0 else 0
            ),
        }


# =============================================================================
# Assembly Functions
# =============================================================================


def _load_concept_units(path: Path) -> list[dict[str, Any]]:
    """Load concept units from JSON file."""
    if not path.exists():
        return []

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # Handle both list and dict formats
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        return data.get("units", [])
    return []


def _load_learner_events(path: Path) -> list[dict[str, Any]]:
    """Load learner events from JSON file."""
    if not path.exists():
        return []

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # Handle both list and dict formats
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        return data.get("events", [])
    return []


def _build_prerequisite_order(
    concept_ids: list[str],
    prerequisite_edges: list[tuple[str, str]],
) -> list[str]:
    """
    Build prerequisite-aware concept ordering.

    Returns concepts in learning order (prerequisites first).
    """
    # Build adjacency list
    prereq_graph: dict[str, set[str]] = {cid: set() for cid in concept_ids}
    for from_c, to_c in prerequisite_edges:
        if to_c in prereq_graph:
            prereq_graph[to_c].add(from_c)

    # Simple topological sort
    visited: set[str] = set()
    order: list[str] = []

    def visit(cid: str) -> None:
        if cid in visited or cid not in prereq_graph:
            return
        visited.add(cid)
        for prereq in prereq_graph[cid]:
            visit(prereq)
        order.append(cid)

    for cid in concept_ids:
        visit(cid)

    return order


def assemble_learner_textbook(
    concept_units_path: Path,
    learner_events_path: Path | None = None,
    learner_id: str = "anonymous",
    prerequisite_edges: list[tuple[str, str]] | None = None,
) -> LearnerTextbook:
    """
    Assemble a learner textbook from concept units and learner events.

    Args:
        concept_units_path: Path to concept_units.json
        learner_events_path: Optional path to learner events JSON
        learner_id: Learner identifier
        prerequisite_edges: Optional list of (from, to) prerequisite tuples

    Returns:
        Assembled LearnerTextbook
    """
    # Load source data
    concept_units = _load_concept_units(concept_units_path)
    learner_events = _load_learner_events(learner_events_path) if learner_events_path else []

    # Initialize textbook
    textbook = LearnerTextbook(
        learner_id=learner_id,
        source_concept_units_path=str(concept_units_path),
        source_learner_events_path=str(learner_events_path) if learner_events_path else None,
        total_concepts_available=len(concept_units),
    )

    # Index units by concept
    concept_ids: list[str] = []
    for unit in concept_units:
        concept_id = unit.get("concept_id", "unknown")
        concept_ids.append(concept_id)
        unit_id = unit.get("unit_id", f"unit_{concept_id}")

        # Create saved unit from concept unit (treat as implicitly saved)
        saved_unit = SavedUnit(
            unit_id=unit_id,
            concept_id=concept_id,
            source_type=unit.get("unit_type", "explanation"),
            explicitly_saved=False,  # Auto-populated from textbook
        )
        textbook.add_saved_unit(saved_unit)

        # Initialize mastery record
        mastery = textbook.get_mastery(concept_id)
        mastery.concept_title = unit.get("title", concept_id)

    # Process learner events to update mastery
    for event in learner_events:
        concept_id = event.get("concept_id")
        if not concept_id:
            continue

        mastery = textbook.get_mastery(concept_id)
        mastery.update_from_event(event)

    # Build recommended order if prerequisites provided
    if prerequisite_edges:
        textbook.recommended_concept_order = _build_prerequisite_order(
            list(set(concept_ids)),
            prerequisite_edges,
        )

    # Calculate blocked-by-prerequisite status
    for concept_id, mastery in textbook.concept_mastery.items():
        if prerequisite_edges:
            for from_c, to_c in prerequisite_edges:
                if to_c == concept_id:
                    prereq_mastery = textbook.concept_mastery.get(from_c)
                    if prereq_mastery and prereq_mastery.mastery_score < 0.5:
                        mastery.blocked_by_prerequisites.append(from_c)

    # Set assembly stats
    textbook.assembly_stats = {
        "total_units": len(concept_units),
        "total_events_processed": len(learner_events),
        "unique_concepts": len(set(concept_ids)),
        "mastery_records_created": len(textbook.concept_mastery),
    }

    return textbook


def load_learner_textbook(path: Path) -> dict[str, Any]:
    """Load a previously saved learner textbook."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# =============================================================================
# Export Functions
# =============================================================================


def export_saved_units(textbook: LearnerTextbook, output_path: Path) -> None:
    """Export just the saved units to JSON."""
    data = {
        "schema_version": "1.0.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "learner_id": textbook.learner_id,
        "saved_units": [asdict(u) for u in textbook.saved_units],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def export_concept_mastery(textbook: LearnerTextbook, output_path: Path) -> None:
    """Export just the concept mastery records to JSON."""
    data = {
        "schema_version": "1.0.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "learner_id": textbook.learner_id,
        "mastery_records": {k: asdict(v) for k, v in textbook.concept_mastery.items()},
        "summary": textbook.get_coverage_summary(),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
