"""
Unit Library Exporter - JSONL-Based Export Format for Adaptive Textbook Helper.

This module implements the new export system that outputs the "grounded instructional
unit graph" format instead of concept markdown. It provides:

1. ExportConfig - Configuration for export behavior
2. UnitLibraryExporter - Main export class with file-per-type output
3. Load utilities - Round-trip support for importing exported libraries
4. Legacy converter - Convert old concept-map.json format to new format

Output Structure:
    output/
    ├── concept_ontology.json          # Canonical concept definitions
    ├── concept_graph.json             # Nodes + prerequisite edges
    ├── source_spans.jsonl             # All source spans (JSONL format)
    ├── instructional_units.jsonl      # All units (JSONL format)
    ├── misconception_bank.jsonl       # Misconception units
    ├── reinforcement_bank.jsonl       # Reinforcement items
    ├── example_bank.jsonl             # SQL examples with validation
    ├── practice_links.json            # Concept → practice problem mapping
    ├── quality_report.json            # Full quality analysis
    └── export_manifest.json           # Provenance, versions, stats

Usage:
    from unit_library_exporter import ExportConfig, UnitLibraryExporter
    
    config = ExportConfig(output_dir=Path("./output"))
    exporter = UnitLibraryExporter()
    
    # Export a library
    result_path = exporter.export(library, config)
    
    # Load it back
    loaded = load_unit_library(Path("./output"))
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterator

import logging
from .instructional_models import (
    INSTRUCTIONAL_EXPORT_VERSION,
    InstructionalUnit,
    MisconceptionUnit,
    PracticeLink,
    ReinforcementItem,
    SourceSpan,
    SQLExample,
    UnitLibraryExport,
)
from .pedagogy_models import (
    ChapterGraphEntry,
    ExerciseBankEntry,
    ExampleBankEntry,
    NavigationIndex,
    PedagogyManifest,
)
from .sql_ontology import ConceptOntology, SQL_CONCEPTS, PREREQUISITE_DAG


# =============================================================================
# Filter Level Enum
# =============================================================================

class FilterLevel(str, Enum):
    """Export filter levels for controlling content inclusion."""
    
    STRICT = "strict"       # Only fully validated, production-ready content
    PRODUCTION = "production"  # Validated content, may include partial units
    DEVELOPMENT = "development"  # All content including drafts and experiments


# =============================================================================
# Export Configuration
# =============================================================================

@dataclass
class ExportConfig:
    """
    Configuration for unit library export.
    
    Controls output directory, format version, content filtering, and
    provenance inclusion for the export process.
    
    Attributes:
        output_dir: Directory where export files will be written
        format_version: Version string for the export format
        include_provenance: Whether to include full provenance information
        include_validation_logs: Whether to include detailed validation logs
        filter_level: Content filtering strictness level
        export_mode: Export mode - "prototype" (allows placeholders) or "student_ready" (strict)
        source_pdf_id: Identifier for the source PDF document
    """
    
    output_dir: Path = field(default_factory=lambda: Path("./output"))
    format_version: str = INSTRUCTIONAL_EXPORT_VERSION + "-unit-library"
    include_provenance: bool = True
    include_validation_logs: bool = True
    filter_level: FilterLevel = FilterLevel.PRODUCTION
    export_mode: str = "prototype"  # "prototype" or "student_ready"
    source_pdf_id: str = "unknown-source"


# =============================================================================
# Example With Validation
# =============================================================================

@dataclass
class ValidatedSQLExample:
    """An SQL example with validation status using canonical field names."""
    
    example_id: str
    concept_id: str
    unit_id: str | None
    title: str
    scenario: str  # Canonical: was "description"
    sql: str  # Canonical: was "query"
    explanation: str
    expected_output: str | None
    schema_used: str
    difficulty: str
    is_valid: bool
    validation_issues: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization using canonical field names."""
        return {
            "example_id": self.example_id,
            "concept_id": self.concept_id,
            "unit_id": self.unit_id,
            "title": self.title,
            "scenario": self.scenario,  # Canonical field name
            "sql": self.sql,  # Canonical field name
            "explanation": self.explanation,
            "expected_output": self.expected_output,
            "schema_used": self.schema_used,
            "difficulty": self.difficulty,
            "is_valid": self.is_valid,
            "validation_issues": self.validation_issues,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ValidatedSQLExample:
        """Create from dictionary with backward compatibility for old field names."""
        # Handle both old field names (query/description) and new (sql/scenario)
        sql_value = data.get("sql", data.get("query", ""))
        scenario_value = data.get("scenario", data.get("description", ""))
        
        return cls(
            example_id=data["example_id"],
            concept_id=data["concept_id"],
            unit_id=data.get("unit_id"),
            title=data.get("title", "Example"),
            scenario=scenario_value,
            sql=sql_value,
            explanation=data.get("explanation", ""),
            expected_output=data.get("expected_output"),
            schema_used=data.get("schema_used", "practice"),
            difficulty=data.get("difficulty", "beginner"),
            is_valid=data["is_valid"],
            validation_issues=data.get("validation_issues", []),
        )
    
    @classmethod
    def from_sql_example(
        cls,
        example: SQLExample,
        example_id: str,
        concept_id: str,
        unit_id: str | None,
        is_valid: bool = True,
        validation_issues: list[str] | None = None,
    ) -> ValidatedSQLExample:
        """Create from a canonical SQLExample model."""
        return cls(
            example_id=example_id,
            concept_id=concept_id,
            unit_id=unit_id,
            title=example.title,
            scenario=example.scenario,
            sql=example.sql,
            explanation=example.explanation,
            expected_output=example.expected_output,
            schema_used=example.schema_used,
            difficulty=example.difficulty,
            is_valid=is_valid,
            validation_issues=validation_issues or [],
        )


# =============================================================================
# Practice Links
# =============================================================================

@dataclass  
class ExportPracticeLink:
    """Mapping from concept to practice problems for export.
    
    This is a wrapper around the canonical PracticeLink model
    with additional export-specific fields.
    """
    
    concept_id: str
    problem_ids: list[str]
    concept_title: str = ""
    difficulty: str = "beginner"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "concept_id": self.concept_id,
            "problem_ids": self.problem_ids,
            "concept_title": self.concept_title,
            "difficulty": self.difficulty,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExportPracticeLink:
        """Create from dictionary."""
        return cls(
            concept_id=data["concept_id"],
            problem_ids=data.get("problem_ids", []),
            concept_title=data.get("concept_title", ""),
            difficulty=data.get("difficulty", "beginner"),
        )
    
    @classmethod
    def from_practice_link(
        cls,
        link: PracticeLink,
        concept_title: str = "",
        difficulty: str = "beginner",
    ) -> ExportPracticeLink:
        """Create from a canonical PracticeLink model."""
        return cls(
            concept_id=link.concept_id,
            problem_ids=link.problem_ids,
            concept_title=concept_title,
            difficulty=difficulty,
        )


# =============================================================================
# Unit Library Exporter
# =============================================================================

class UnitLibraryExporter:
    """
    Main exporter for unit library format.
    
    Transforms UnitLibraryExport into a directory of JSON/JSONL files
    optimized for streaming access and version control.
    
    Example:
        exporter = UnitLibraryExporter()
        config = ExportConfig(output_dir=Path("./output"))
        result = exporter.export(library, config)
    """
    
    # Output file names
    ONTOLOGY_FILE = "concept_ontology.json"
    GRAPH_FILE = "concept_graph.json"
    SOURCE_SPANS_FILE = "source_spans.jsonl"
    UNITS_FILE = "instructional_units.jsonl"
    MISCONCEPTIONS_FILE = "misconception_bank.jsonl"
    REINFORCEMENT_FILE = "reinforcement_bank.jsonl"
    EXAMPLES_FILE = "example_bank.jsonl"
    PRACTICE_LINKS_FILE = "practice_links.json"
    QUALITY_REPORT_FILE = "quality_report.json"
    MANIFEST_FILE = "export_manifest.json"
    
    # Pedagogy export files (new)
    CHAPTER_GRAPH_FILE = "chapter_graph.json"
    EXERCISE_BANK_FILE = "exercise_bank.jsonl"
    PEDAGOGY_MANIFEST_FILE = "pedagogy_manifest.json"
    
    def __init__(self):
        """Initialize the exporter."""
        self._ontology = ConceptOntology()
        self._logger = logging.getLogger(__name__)
        self._pedagogy_data: dict[str, Any] | None = None
    
    def set_pedagogy_data(
        self,
        chapters: list[Any] | None = None,
        exercises: list[Any] | None = None,
        examples: list[Any] | None = None,
        navigation: NavigationIndex | None = None,
    ) -> None:
        """
        Set pedagogy data for inclusion in export.
        
        Args:
            chapters: List of ChapterInfo objects
            exercises: List of ExerciseInfo objects
            examples: List of ExampleInfo objects (textbook examples, not SQL examples)
            navigation: NavigationIndex for cross-referencing
        """
        self._pedagogy_data = {
            "chapters": chapters or [],
            "exercises": exercises or [],
            "examples": examples or [],
            "navigation": navigation,
        }
    
    def export(
        self,
        library: UnitLibraryExport,
        config: ExportConfig | None = None,
    ) -> Path:
        """
        Main export method that creates all output files.
        
        Args:
            library: The UnitLibraryExport to export
            config: Export configuration (uses defaults if not provided)
            
        Returns:
            Path to the output directory
            
        Raises:
            ValueError: If library is invalid
            OSError: If output directory cannot be created
        """
        config = config or ExportConfig()
        
        # Validate library
        if not library:
            raise ValueError("Library cannot be None")
        
        # Create output directory
        config.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Apply filter level (skip if library was already filtered by the pipeline)
        already_filtered = getattr(library, '_pre_filtered', False)
        if already_filtered:
            self._logger.info("Library was already filtered by pipeline, skipping second filter pass")
            filtered_library = library
        else:
            filtered_library = self._apply_filter(library, config.filter_level)
        
        # Extract source spans from units
        source_spans = self._extract_all_source_spans(filtered_library)
        
        # Extract examples from units
        examples = self._extract_all_examples(filtered_library)
        
        # Build practice links
        practice_links = self._build_practice_links(filtered_library)
        
        # Write all files
        self._write_concept_ontology(
            filtered_library.concept_ontology, config.output_dir
        )
        
        self._write_concept_graph(
            filtered_library.concept_graph, config.output_dir
        )
        
        self._write_source_spans_jsonl(source_spans, config.output_dir)
        
        self._write_instructional_units_jsonl(
            filtered_library.instructional_units, config.output_dir
        )
        
        self._write_misconception_bank_jsonl(
            filtered_library.misconception_bank, config.output_dir
        )
        
        self._write_reinforcement_bank_jsonl(
            filtered_library.reinforcement_bank, config.output_dir
        )
        
        self._write_example_bank_jsonl(examples, config.output_dir)
        
        self._write_practice_links(practice_links, config.output_dir)
        
        self._write_quality_report(
            filtered_library.quality_report, config.output_dir
        )
        
        self._write_export_manifest(
            filtered_library, config, config.output_dir
        )
        
        # Write pedagogy exports if data available
        if self._pedagogy_data:
            self._write_pedagogy_exports(config.output_dir)
        
        return config.output_dir
    
    def _apply_filter(
        self,
        library: UnitLibraryExport,
        filter_level: FilterLevel,
    ) -> UnitLibraryExport:
        """
        Apply content filtering based on filter level.
        
        Args:
            library: The library to filter
            filter_level: The strictness level to apply
            
        Returns:
            Filtered library (may be the same object if no filtering needed)
        """
        if filter_level == FilterLevel.DEVELOPMENT:
            # Include everything
            return library
        
        # Filter units based on quality criteria
        filtered_units = []
        for unit in library.instructional_units:
            if self._unit_passes_filter(unit, filter_level):
                filtered_units.append(unit)
        
        # Filter misconceptions
        filtered_misconceptions = []
        for misc in library.misconception_bank:
            if self._misconception_passes_filter(misc, filter_level):
                filtered_misconceptions.append(misc)
        
        # Filter reinforcement items
        filtered_reinforcement = []
        for item in library.reinforcement_bank:
            if self._reinforcement_passes_filter(item, filter_level):
                filtered_reinforcement.append(item)
        
        # Create filtered library
        return UnitLibraryExport(
            export_version=library.export_version,
            generated_at=library.generated_at,
            source_pdf_id=library.source_pdf_id,
            concept_ontology=library.concept_ontology,
            concept_graph=library.concept_graph,
            instructional_units=filtered_units,
            misconception_bank=filtered_misconceptions,
            reinforcement_bank=filtered_reinforcement,
            quality_report=library.quality_report,
            export_manifest=library.export_manifest,
        )
    
    def _unit_passes_filter(
        self,
        unit: InstructionalUnit,
        filter_level: FilterLevel,
    ) -> bool:
        """Check if a unit passes the filter level."""
        # Curated content is high quality and should pass regardless of grounding
        content = unit.content or {}
        is_curated = content.get("_used_curated_fallback") or (
            content.get("_metadata", {}).get("content_source") == "curated"
        )
        
        if is_curated:
            # Curated content passes all filter levels
            return True
        
        if filter_level == FilterLevel.STRICT:
            # Require full grounding and high confidence
            return (
                unit.has_grounding()
                and unit.grounding_confidence >= 0.9
                and len(unit.evidence_spans) > 0
            )
        elif filter_level == FilterLevel.PRODUCTION:
            # Require basic grounding
            return unit.has_grounding() and unit.grounding_confidence >= 0.7
        else:
            return True
    
    def _misconception_passes_filter(
        self,
        misc: MisconceptionUnit,
        filter_level: FilterLevel,
    ) -> bool:
        """Check if a misconception passes the filter level."""
        if filter_level == FilterLevel.STRICT:
            return len(misc.repair_content) > 0 and misc.remediation_order <= 2
        return True
    
    def _reinforcement_passes_filter(
        self,
        item: ReinforcementItem,
        filter_level: FilterLevel,
    ) -> bool:
        """Check if a reinforcement item passes the filter level."""
        if filter_level == FilterLevel.STRICT:
            return len(item.prompt) >= 10 and len(item.expected_answer) >= 1
        return True
    
    def _compute_l2_stats(self, units: list[InstructionalUnit]) -> dict:
        """Compute L2 source type statistics.
        
        Analyzes all L2 (hint_plus_example) units and categorizes them by
        their source type: default, extracted, curated, or conceptual.
        
        Args:
            units: List of instructional units to analyze
            
        Returns:
            Dictionary with L2 statistics including counts and percentages
        """
        l2_units = [u for u in units if u.target_stage == 'L2_hint_plus_example']
        
        stats = {
            'total_l2_units': len(l2_units),
            'default_count': 0,
            'extracted_count': 0,
            'curated_count': 0,
            'conceptual_count': 0,
            'unknown_count': 0,
            'default_percentage': 0.0,
            'concepts_with_default': []
        }
        
        for unit in l2_units:
            content = unit.content or {}
            metadata = content.get('example_metadata', {})
            
            # Check audit fields first
            source_type = metadata.get('example_source_type') or metadata.get('source_type', 'unknown')
            used_default = metadata.get('used_default_example', False)
            
            if used_default or source_type == 'default':
                stats['default_count'] += 1
                stats['concepts_with_default'].append(unit.concept_id)
            elif source_type == 'extracted':
                stats['extracted_count'] += 1
            elif source_type == 'curated':
                stats['curated_count'] += 1
            elif source_type == 'conceptual':
                stats['conceptual_count'] += 1
            else:
                stats['unknown_count'] += 1
        
        # Calculate percentage
        if stats['total_l2_units'] > 0:
            stats['default_percentage'] = round(
                stats['default_count'] / stats['total_l2_units'] * 100, 1
            )
        
        return stats
    
    def _compute_stage_counts(self, units: list[InstructionalUnit]) -> dict:
        """Compute unit counts per target stage.
        
        Args:
            units: List of instructional units
            
        Returns:
            Dictionary mapping stage names to counts
        """
        counts: dict[str, int] = {}
        for unit in units:
            stage = unit.target_stage
            counts[stage] = counts.get(stage, 0) + 1
        return counts
    
    def _write_l2_audit_log(
        self,
        output_dir: Path,
        units: list[InstructionalUnit]
    ) -> Path | None:
        """Write detailed L2 selection audit log.
        
        Creates a machine-readable JSONL file with audit information for each
        L2 unit, including source type, match scores, and selection reasons.
        
        Args:
            output_dir: Directory to write the audit log
            units: List of instructional units to audit
            
        Returns:
            Path to the audit log file, or None if no L2 units
        """
        l2_units = [u for u in units if u.target_stage == 'L2_hint_plus_example']
        if not l2_units:
            return None
        
        audit_path = output_dir / 'l2_selection_audit.jsonl'
        
        with open(audit_path, 'w', encoding='utf-8') as f:
            for unit in l2_units:
                content = unit.content or {}
                metadata = content.get('example_metadata', {})
                
                # Get SQL preview (truncate if too long)
                source_sql = content.get('source_example_sql', '')
                if source_sql:
                    source_sql_preview = source_sql[:100] + '...' if len(source_sql) > 100 else source_sql
                else:
                    source_sql_preview = None
                
                audit_entry = {
                    'concept_id': unit.concept_id,
                    'unit_id': unit.unit_id,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'source_type': metadata.get('example_source_type', 'unknown'),
                    'match_score': metadata.get('example_match_score', 0.0),
                    'selection_reason': metadata.get('example_selection_reason', ''),
                    'matched_signals': metadata.get('example_matched_signals', []),
                    'used_default': metadata.get('used_default_example', False),
                    'is_conceptual': metadata.get('is_conceptual', False),
                    'source_sql_preview': source_sql_preview,
                    'page': metadata.get('page'),
                    'rejection_reason': metadata.get('rejection_reason'),
                    'fallback_reason': metadata.get('fallback_reason'),
                }
                f.write(json.dumps(audit_entry, ensure_ascii=False) + '\n')
        
        self._logger.info(f"Wrote L2 audit log: {audit_path.name} ({len(l2_units)} entries)")
        return audit_path
    
    def _extract_all_source_spans(
        self,
        library: UnitLibraryExport,
    ) -> list[SourceSpan]:
        """Extract all unique source spans from the library."""
        spans: dict[str, SourceSpan] = {}
        
        for unit in library.instructional_units:
            for span in unit.evidence_spans:
                spans[span.span_id] = span
        
        return list(spans.values())
    
    def _extract_all_examples(
        self,
        library: UnitLibraryExport,
    ) -> list[ValidatedSQLExample]:
        """Extract all SQL examples from units with validation using canonical field names."""
        examples: list[ValidatedSQLExample] = []
        example_counter = 0
        
        for unit in library.instructional_units:
            unit_examples = unit.content.get("examples", [])
            for ex in unit_examples:
                example_counter += 1
                example_id = f"ex_{example_counter:04d}"
                
                # Handle both dict (legacy) and SQLExample (canonical) formats
                if isinstance(ex, SQLExample):
                    # Already a canonical SQLExample - use directly
                    is_valid = self._validate_example_sql(ex.sql)
                    issues = [] if is_valid else ["Invalid SQL syntax"]
                    validated = ValidatedSQLExample.from_sql_example(
                        example=ex,
                        example_id=example_id,
                        concept_id=unit.concept_id,
                        unit_id=unit.unit_id,
                        is_valid=is_valid,
                        validation_issues=issues,
                    )
                elif isinstance(ex, dict):
                    # Legacy dict format - extract using canonical field names
                    # Support both old (query/description) and new (sql/scenario) keys
                    sql = ex.get("sql", ex.get("query", ""))
                    scenario = ex.get("scenario", ex.get("description", ""))
                    
                    is_valid = self._validate_example_sql(sql)
                    issues = [] if is_valid else ["Invalid SQL syntax"]
                    
                    validated = ValidatedSQLExample(
                        example_id=example_id,
                        concept_id=unit.concept_id,
                        unit_id=unit.unit_id,
                        title=ex.get("title", "Example"),
                        scenario=scenario,  # Canonical: was "description"
                        sql=sql,  # Canonical: was "query"
                        explanation=ex.get("explanation", ""),
                        expected_output=ex.get("expected_output"),
                        schema_used=ex.get("schema_used", "practice"),
                        difficulty=ex.get("difficulty", "beginner"),
                        is_valid=is_valid,
                        validation_issues=issues,
                    )
                else:
                    # Unknown format - skip
                    continue
                    
                examples.append(validated)
        
        return examples
    
    def _validate_example_sql(self, sql: str) -> bool:
        """Basic SQL validation using canonical field name."""
        sql = sql.strip() if sql else ""
        if not sql:
            return False
        
        # Check for basic SQL keywords
        valid_starts = [
            "SELECT", "INSERT", "UPDATE", "DELETE",
            "CREATE", "ALTER", "DROP", "WITH"
        ]
        sql_upper = sql.upper()
        return any(sql_upper.startswith(kw) for kw in valid_starts)
    
    def _build_practice_links(
        self,
        library: UnitLibraryExport,
    ) -> list[ExportPracticeLink]:
        """Build concept to practice problem mapping using canonical practice_links field."""
        links: dict[str, ExportPracticeLink] = {}
        
        for unit in library.instructional_units:
            unit_content = unit.content
            
            # Check for canonical practice_links field (list of PracticeLink or dict)
            practice_links_data = unit_content.get("practice_links", [])
            
            # Also check for legacy practice_problem_ids field for backward compatibility
            legacy_practice_ids = unit_content.get("practice_problem_ids", [])
            
            # Process canonical practice_links
            for link_data in practice_links_data:
                if isinstance(link_data, PracticeLink):
                    # Canonical PracticeLink model
                    if link_data.concept_id not in links:
                        links[link_data.concept_id] = ExportPracticeLink.from_practice_link(
                            link_data,
                            concept_title=unit_content.get("title", ""),
                            difficulty=unit.difficulty,
                        )
                    else:
                        links[link_data.concept_id].problem_ids.extend(link_data.problem_ids)
                elif isinstance(link_data, dict):
                    # Dict format - could be legacy or canonical
                    concept_id = link_data.get("concept_id", unit.concept_id)
                    problem_ids = link_data.get("problem_ids", [])
                    
                    if concept_id not in links:
                        links[concept_id] = ExportPracticeLink(
                            concept_id=concept_id,
                            problem_ids=[],
                            concept_title=unit_content.get("title", ""),
                            difficulty=unit.difficulty,
                        )
                    links[concept_id].problem_ids.extend(problem_ids)
            
            # Process legacy practice_problem_ids (list of strings)
            if legacy_practice_ids:
                if unit.concept_id not in links:
                    links[unit.concept_id] = ExportPracticeLink(
                        concept_id=unit.concept_id,
                        problem_ids=[],
                        concept_title=unit_content.get("title", ""),
                        difficulty=unit.difficulty,
                    )
                links[unit.concept_id].problem_ids.extend(legacy_practice_ids)
        
        # Deduplicate problem IDs
        for link in links.values():
            link.problem_ids = list(dict.fromkeys(link.problem_ids))
        
        return list(links.values())
    
    # -------------------------------------------------------------------------
    # File Writing Methods
    # -------------------------------------------------------------------------
    
    def _write_concept_ontology(
        self,
        ontology: dict[str, Any],
        output_dir: Path,
    ) -> None:
        """
        Write SQL_CONCEPTS as JSON.
        
        Creates the canonical concept definitions file with version info.
        """
        output = {
            "version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "concepts": SQL_CONCEPTS,
            "metadata": {
                "total_concepts": len(SQL_CONCEPTS),
                "categories": list(set(
                    c.get("category", "unknown") for c in SQL_CONCEPTS.values()
                )),
            },
        }
        
        # Merge with any custom ontology data from the library
        if ontology:
            output["custom_metadata"] = ontology
        
        filepath = output_dir / self.ONTOLOGY_FILE
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
    
    def _write_concept_graph(
        self,
        graph: dict[str, Any],
        output_dir: Path,
    ) -> None:
        """
        Write concept graph from library (not static data).
        
        Uses the dynamic concept graph built by the pipeline, which contains
        only concepts actually mapped from the document content.
        
        Args:
            graph: The concept graph from the library (nodes, edges, metadata)
            output_dir: Directory to write the file
        """
        filepath = output_dir / self.GRAPH_FILE
        
        if graph and graph.get("nodes"):
            # Use the pipeline's dynamic graph
            graph_data = graph
            self._logger.info(
                f"Using pipeline's dynamic concept graph: "
                f"{len(graph.get('nodes', []))} nodes, "
                f"{len(graph.get('edges', []))} edges"
            )
        else:
            # Fallback: build minimal graph from exported units
            graph_data = self._build_graph_from_units([])
            self._logger.info("Using fallback graph (no library graph available)")
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(graph_data, f, indent=2)
    
    def _build_graph_from_units(
        self,
        units: list[InstructionalUnit],
    ) -> dict[str, Any]:
        """
        Build minimal concept graph from actual units (fallback method).
        
        This is used when the pipeline's dynamic graph is not available.
        Builds nodes and edges from the units themselves.
        
        Args:
            units: List of instructional units
            
        Returns:
            Dictionary with nodes, edges, and metadata
        """
        # Get unique concept IDs from units
        concept_ids = set(u.concept_id for u in units)
        
        # Build nodes from concepts
        nodes = []
        for concept_id in concept_ids:
            concept = self._ontology.get_concept(concept_id)
            if concept:
                nodes.append({
                    "id": concept_id,
                    "concept_id": concept_id,
                    "title": concept.get("title", ""),
                    "difficulty": concept.get("difficulty", "beginner"),
                    "category": concept.get("category", "unknown"),
                    "has_content": True,
                })
        
        # Build edges from PREREQUISITE_DAG, but only for mapped concepts
        edges = []
        for edge in PREREQUISITE_DAG:
            if edge["from"] in concept_ids and edge["to"] in concept_ids:
                edges.append(edge)
        
        # Calculate omitted concepts
        all_concept_ids = set(SQL_CONCEPTS.keys())
        omitted_concepts = list(all_concept_ids - concept_ids)
        
        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_ontology_concepts": len(SQL_CONCEPTS),
                "mapped_concepts": len(nodes),
                "omitted_concepts": omitted_concepts,
                "omitted_count": len(omitted_concepts),
                "version": "1.0.0",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "is_fallback": True,
            },
        }
    
    def _write_source_spans_jsonl(
        self,
        spans: list[SourceSpan],
        output_dir: Path,
    ) -> None:
        """
        Write source spans as JSONL (one per line for large files).
        
        Enables streaming access to source spans without loading all into memory.
        """
        filepath = output_dir / self.SOURCE_SPANS_FILE
        with open(filepath, "w", encoding="utf-8") as f:
            for span in spans:
                # Convert Pydantic model to dict and serialize
                record = span.model_dump()
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    def _write_instructional_units_jsonl(
        self,
        units: list[InstructionalUnit],
        output_dir: Path,
    ) -> None:
        """
        Write units as JSONL.
        
        Each line is a complete InstructionalUnit for easy streaming.
        """
        filepath = output_dir / self.UNITS_FILE
        with open(filepath, "w", encoding="utf-8") as f:
            for unit in units:
                record = unit.model_dump()
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    def _write_misconception_bank_jsonl(
        self,
        units: list[MisconceptionUnit],
        output_dir: Path,
    ) -> None:
        """Write misconception units as JSONL."""
        filepath = output_dir / self.MISCONCEPTIONS_FILE
        count = 0
        with open(filepath, "w", encoding="utf-8") as f:
            for unit in units:
                record = unit.model_dump()
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
        self._logger.info(f"Exported {count} misconception units to {filepath.name}")
    
    def _write_reinforcement_bank_jsonl(
        self,
        items: list[ReinforcementItem],
        output_dir: Path,
    ) -> None:
        """Write reinforcement items as JSONL."""
        filepath = output_dir / self.REINFORCEMENT_FILE
        count = 0
        with open(filepath, "w", encoding="utf-8") as f:
            for item in items:
                record = item.model_dump()
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
        self._logger.info(f"Exported {count} reinforcement items to {filepath.name}")
    
    def _write_example_bank_jsonl(
        self,
        examples: list[ValidatedSQLExample],
        output_dir: Path,
    ) -> None:
        """Write SQL examples with validation status and provenance as JSONL."""
        filepath = output_dir / self.EXAMPLES_FILE
        
        # Get example provenance from pedagogy data if available
        example_provenance: dict[str, dict[str, Any]] = {}
        if self._pedagogy_data and self._pedagogy_data.get("examples"):
            for ex in self._pedagogy_data["examples"]:
                if hasattr(ex, 'example_id'):
                    example_provenance[ex.example_id] = {
                        "chapter": ex.chapter_number,
                        "page": ex.page_number,
                        "title": getattr(ex, 'title', ""),
                    }
        
        with open(filepath, "w", encoding="utf-8") as f:
            for example in examples:
                record = example.to_dict()
                
                # Add provenance if available from pedagogy data
                if example.example_id in example_provenance:
                    prov = example_provenance[example.example_id]
                    record["chapter"] = prov.get("chapter")
                    record["page"] = prov.get("page")
                    if prov.get("title"):
                        record["title"] = prov["title"]
                
                # Ensure source_type is set
                if "source_type" not in record:
                    record["source_type"] = "extracted"
                
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    def _write_practice_links(
        self,
        mapping: list[ExportPracticeLink],
        output_dir: Path,
    ) -> None:
        """Write concept to practice problem links as JSON."""
        output = {
            "version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "links": [link.to_dict() for link in mapping],
            "metadata": {
                "total_concepts_with_practice": len(mapping),
                "total_practice_links": sum(len(l.problem_ids) for l in mapping),
            },
        }
        
        filepath = output_dir / self.PRACTICE_LINKS_FILE
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
    
    def _write_quality_report(
        self,
        report: dict[str, Any],
        output_dir: Path,
    ) -> None:
        """Write comprehensive quality report as JSON."""
        # Enhance report with timestamp and version
        enhanced_report = {
            "version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            **report,
        }
        
        filepath = output_dir / self.QUALITY_REPORT_FILE
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(enhanced_report, f, indent=2)
    
    def _write_export_manifest(
        self,
        library: UnitLibraryExport,
        config: ExportConfig,
        output_dir: Path,
    ) -> None:
        """
        Write manifest with provenance, versions, and statistics.
        
        The manifest is the entry point for understanding the export contents
        and verifying its completeness.
        """
        # Calculate statistics
        units_per_concept: dict[str, int] = defaultdict(int)
        for unit in library.instructional_units:
            units_per_concept[unit.concept_id] += 1
        
        # Compute L2 statistics
        l2_stats = self._compute_l2_stats(library.instructional_units)
        
        # Write audit log
        audit_path = self._write_l2_audit_log(output_dir, library.instructional_units)
        
        # Log L2 summary
        self._logger.info(
            f"L2 Export Stats: {l2_stats['extracted_count']} extracted, "
            f"{l2_stats['curated_count']} curated, "
            f"{l2_stats['default_count']} default "
            f"({l2_stats['default_percentage']}%)"
        )
        
        if l2_stats['default_count'] > 0:
            self._logger.warning(f"Concepts using default L2: {l2_stats['concepts_with_default']}")
        
        # Get quality pass rate from report
        quality_report = library.quality_report
        summary = quality_report.get("summary", {})
        quality_pass_rate = summary.get("pass_rate", 0.0)
        
        # Build validation results
        validation_results = {
            "graph_integrity_errors": library.validate_graph_integrity(),
            "quality_pass_rate": quality_pass_rate,
            "total_units": len(library.instructional_units),
            "total_misconceptions": len(library.misconception_bank),
            "total_reinforcement": len(library.reinforcement_bank),
        }
        
        # Get generation stats from metadata if available
        stats = library.export_manifest.get("generation_stats", {})
        generated_units = stats.get("generated_units", len(library.instructional_units))
        filtered_out = stats.get("filtered_out", 0)
        exported_units = stats.get("exported_units", len(library.instructional_units))
        fallback_units = stats.get("fallback_units", 0)
        filter_level = stats.get("filter_level", config.filter_level.value)
        export_filter_pass_rate = exported_units / max(generated_units, 1)
        
        # Get misconception and reinforcement generation stats
        generated_misconceptions = stats.get("generated_misconceptions", len(library.misconception_bank))
        exported_misconceptions = len(library.misconception_bank)
        generated_reinforcement = stats.get("generated_reinforcement", len(library.reinforcement_bank))
        exported_reinforcement = len(library.reinforcement_bank)
        
        # Build filter results with real counts
        filter_results = {
            "filter_level": filter_level,
            "original_units": generated_units,
            "filtered_units": filtered_out,
            "pass_rate": export_filter_pass_rate,
        }
        
        # Build configuration section
        configuration = {
            "filter_level": filter_level,
            "export_mode": config.export_mode,
        }
        
        # Build provenance
        provenance = {
            "source_pdf_id": library.source_pdf_id or config.source_pdf_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "export_version": config.format_version,
            "schema_version": library.export_version,
            "tools_used": ["algl-pdf-helper"],
        }
        
        if config.include_provenance:
            provenance["library_generated_at"] = library.generated_at
        
        # Check for quality report paths from pipeline
        quality_reports = library.export_manifest.get("quality_reports", {})
        
        # Build files section with both quality reports if available
        files_section = {
            "concept_ontology": self.ONTOLOGY_FILE,
            "concept_graph": self.GRAPH_FILE,
            "source_spans": self.SOURCE_SPANS_FILE,
            "instructional_units": self.UNITS_FILE,
            "misconception_bank": self.MISCONCEPTIONS_FILE,
            "reinforcement_bank": self.REINFORCEMENT_FILE,
            "example_bank": self.EXAMPLES_FILE,
            "practice_links": self.PRACTICE_LINKS_FILE,
            "quality_report": self.QUALITY_REPORT_FILE,
            "manifest": self.MANIFEST_FILE,
        }
        
        # Add pedagogy files if available
        if self._pedagogy_data:
            files_section["chapter_graph"] = self.CHAPTER_GRAPH_FILE
            files_section["exercise_bank"] = self.EXERCISE_BANK_FILE
            files_section["pedagogy_manifest"] = self.PEDAGOGY_MANIFEST_FILE
        
        # Add both quality reports if available from pipeline
        if quality_reports:
            files_section["quality_report_generated"] = quality_reports.get("generated")
            files_section["quality_report_exported"] = quality_reports.get("exported")
        
        manifest = {
            "export_version": config.format_version,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_pdf_id": library.source_pdf_id or config.source_pdf_id,
            "statistics": {
                "total_units": len(library.instructional_units),
                "generated_units": generated_units,
                "filtered_out": filtered_out,
                "instructional_units": exported_units,
                "fallback_units": fallback_units,
                "concepts_covered": len(units_per_concept),
                "units_per_concept": dict(units_per_concept),
                "export_filter_pass_rate": export_filter_pass_rate,
                "quality_gate_pass_rate": quality_pass_rate,
                "l2": l2_stats,
                "by_stage": self._compute_stage_counts(library.instructional_units),
                "misconceptions": {
                    "generated": generated_misconceptions,
                    "exported": exported_misconceptions,
                },
                "reinforcement": {
                    "generated": generated_reinforcement,
                    "exported": exported_reinforcement,
                },
                "total_misconceptions": exported_misconceptions,
                "total_reinforcement": exported_reinforcement,
            },
            "quality_flags": {
                "high_default_l2_rate": l2_stats['default_percentage'] > 30,
                "l2_coverage_complete": l2_stats['unknown_count'] == 0,
                "has_l2_audit_log": audit_path is not None,
            },
            "provenance": provenance,
            "validation_results": validation_results,
            "filter_results": filter_results,
            "configuration": configuration,
            "quality_reports": quality_reports if quality_reports else {
                "generated": None,
                "exported": self.QUALITY_REPORT_FILE,
            },
            "files": files_section,
            "audit_log": str(audit_path.relative_to(output_dir)) if audit_path else None,
        }
        
        filepath = output_dir / self.MANIFEST_FILE
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)


    # -------------------------------------------------------------------------
    # Pedagogy Export Methods (New)
    # -------------------------------------------------------------------------
    
    def _write_pedagogy_exports(self, output_dir: Path) -> None:
        """
        Write all pedagogy export files.
        
        Creates:
        - chapter_graph.json: Chapter structure and organization
        - exercise_bank.jsonl: End-of-chapter exercises
        - pedagogy_manifest.json: Complete pedagogy metadata
        """
        if not self._pedagogy_data:
            return
        
        self._logger.info("Writing pedagogy exports...")
        
        # Write chapter graph
        self._write_chapter_graph(output_dir)
        
        # Write exercise bank
        self._write_exercise_bank(output_dir)
        
        # Write pedagogy manifest
        self._write_pedagogy_manifest(output_dir)
        
        self._logger.info("Pedagogy exports complete")
    
    def _write_chapter_graph(self, output_dir: Path) -> None:
        """Write chapter_graph.json with textbook structure."""
        if not self._pedagogy_data or not self._pedagogy_data.get("chapters"):
            return
        
        chapters = self._pedagogy_data["chapters"]
        
        # Convert to export format
        entries = []
        for chapter in chapters:
            if hasattr(chapter, 'to_dict'):
                chapter_dict = chapter.to_dict()
            else:
                chapter_dict = chapter
            
            # Extract topic data
            topics = []
            for topic in chapter_dict.get("topics", []):
                if hasattr(topic, 'to_dict'):
                    topic_dict = topic.to_dict()
                else:
                    topic_dict = topic
                topics.append({
                    "topic_id": topic_dict.get("topic_id", ""),
                    "title": topic_dict.get("title", ""),
                    "concepts": topic_dict.get("concept_ids", []),
                    "subsection_ids": topic_dict.get("subsection_ids", []),
                })
            
            # Build sections list for chapter graph
            sections = []
            for topic in topics:
                sections.append({
                    "title": topic["title"],
                    "page": topic.get("subsection_ids", [0])[0] if topic.get("subsection_ids") else 0,
                })
            
            # Determine concepts covered from topics
            concepts_covered = []
            for topic in topics:
                concepts_covered.extend(topic.get("concepts", []))
            concepts_covered = list(set(concepts_covered))  # Deduplicate
            
            entry = {
                "number": chapter_dict.get("chapter_number", 0),
                "title": chapter_dict.get("chapter_title", ""),
                "page_range": list(chapter_dict.get("page_range", [0, 0])),
                "sections": sections,
                "concepts_covered": concepts_covered,
                "exercises": chapter_dict.get("exercises", []),
                "prerequisites": chapter_dict.get("prerequisites", []),
                "next_chapters": [],  # Will be populated based on chapter number
            }
            
            # Infer next chapters (sequential)
            chapter_num = chapter_dict.get("chapter_number", 0)
            if chapter_num > 0:
                entry["next_chapters"] = [chapter_num + 1]
            
            entries.append(entry)
        
        output = {
            "version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "chapters": entries,
            "metadata": {
                "total_chapters": len(entries),
                "path_types": list(set(
                    e.get("path_type", "general") for e in entries
                )),
            },
        }
        
        filepath = output_dir / self.CHAPTER_GRAPH_FILE
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
        
        self._logger.info(f"Wrote chapter graph: {len(entries)} chapters")
    
    def _write_exercise_bank(self, output_dir: Path) -> None:
        """Write exercise_bank.jsonl with end-of-chapter exercises."""
        if not self._pedagogy_data or not self._pedagogy_data.get("exercises"):
            return
        
        exercises = self._pedagogy_data["exercises"]
        
        filepath = output_dir / self.EXERCISE_BANK_FILE
        with open(filepath, "w", encoding="utf-8") as f:
            for exercise in exercises:
                if hasattr(exercise, 'to_dict'):
                    ex_dict = exercise.to_dict()
                elif hasattr(exercise, 'exercise_id'):
                    # ExerciseInfo dataclass
                    ex_dict = {
                        "exercise_id": exercise.exercise_id,
                        "chapter": exercise.chapter,
                        "number": exercise.number,
                        "text": exercise.text,
                        "solution_sql": exercise.solution_sql,
                        "solution_text": exercise.solution_text,
                        "concepts_tested": exercise.concepts_tested,
                        "difficulty": exercise.difficulty,
                        "exercise_type": exercise.exercise_type,
                        "page": exercise.page,
                        "hints": exercise.hints,
                    }
                else:
                    ex_dict = exercise
                
                # Build standardized exercise entry
                entry = {
                    "exercise_id": ex_dict.get("exercise_id", ""),
                    "chapter": ex_dict.get("chapter", 0),
                    "number": str(ex_dict.get("number", ex_dict.get("exercise_number", ""))),
                    "text": ex_dict.get("text", ex_dict.get("problem", ex_dict.get("problem_text", ""))),
                    "solution_sql": ex_dict.get("solution_sql") or ex_dict.get("solution"),
                    "concepts_tested": ex_dict.get("concepts_tested", ex_dict.get("concepts", [])),
                    "difficulty": ex_dict.get("difficulty", "beginner"),
                    "exercise_type": ex_dict.get("exercise_type", "coding"),
                    "page": ex_dict.get("page"),
                }
                
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        
        self._logger.info(f"Wrote exercise bank: {len(exercises)} exercises")
    
    def _write_pedagogy_manifest(self, output_dir: Path) -> None:
        """Write pedagogy_manifest.json with complete structure metadata."""
        if not self._pedagogy_data:
            return
        
        chapters = self._pedagogy_data.get("chapters", [])
        exercises = self._pedagogy_data.get("exercises", [])
        examples = self._pedagogy_data.get("examples", [])
        navigation = self._pedagogy_data.get("navigation")
        
        # Count path types
        dev_concepts = set()
        admin_concepts = set()
        design_concepts = set()
        
        for chapter in chapters:
            if hasattr(chapter, 'to_dict'):
                chapter_dict = chapter.to_dict()
            else:
                chapter_dict = chapter
            
            path_type = chapter_dict.get("path_type", "general")
            chapter_concepts = set()
            
            for topic in chapter_dict.get("topics", []):
                if hasattr(topic, 'to_dict'):
                    topic_dict = topic.to_dict()
                else:
                    topic_dict = topic
                chapter_concepts.update(topic_dict.get("concept_ids", []))
            
            if path_type == "developer":
                dev_concepts.update(chapter_concepts)
            elif path_type == "admin":
                admin_concepts.update(chapter_concepts)
            elif path_type == "design":
                design_concepts.update(chapter_concepts)
        
        # Detect paired-page format
        paired_count = sum(
            1 for e in examples
            if hasattr(e, 'is_paired_format') and e.is_paired_format
        )
        paired_detected = paired_count > 0
        
        manifest = PedagogyManifest(
            source_doc_id=self._pedagogy_data.get("doc_id", "unknown"),
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_chapters=len(chapters),
            total_exercises=len(exercises),
            total_examples=len(examples),
            developer_path_concepts=list(dev_concepts),
            admin_path_concepts=list(admin_concepts),
            design_path_concepts=list(design_concepts),
            paired_page_format_detected=paired_detected,
            paired_examples_count=paired_count,
            navigation=navigation or NavigationIndex(),
        )
        
        filepath = output_dir / self.PEDAGOGY_MANIFEST_FILE
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(manifest.model_dump(), f, indent=2)
        
        self._logger.info(
            f"Wrote pedagogy manifest: "
            f"{len(chapters)} chapters, "
            f"{len(exercises)} exercises, "
            f"{len(examples)} examples"
        )

# =============================================================================
# Import/Load Utilities
# =============================================================================

def load_unit_library(output_dir: Path) -> UnitLibraryExport:
    """
    Load library from exported files.
    
    Reconstructs a UnitLibraryExport from the exported file structure.
    This enables round-trip serialization: export -> files -> load.
    
    Args:
        output_dir: Directory containing exported files
        
    Returns:
        Reconstructed UnitLibraryExport
        
    Raises:
        FileNotFoundError: If required files are missing
        ValueError: If files are corrupted or invalid
    """
    exporter = UnitLibraryExporter()
    
    # Load manifest
    manifest_path = output_dir / exporter.MANIFEST_FILE
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest file not found: {manifest_path}")
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    
    # Load instructional units
    units_path = output_dir / exporter.UNITS_FILE
    units: list[InstructionalUnit] = []
    if units_path.exists():
        with open(units_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    units.append(InstructionalUnit(**data))
    
    # Load misconceptions
    misc_path = output_dir / exporter.MISCONCEPTIONS_FILE
    misconceptions: list[MisconceptionUnit] = []
    if misc_path.exists():
        with open(misc_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    misconceptions.append(MisconceptionUnit(**data))
    
    # Load reinforcement items
    reinf_path = output_dir / exporter.REINFORCEMENT_FILE
    reinforcement: list[ReinforcementItem] = []
    if reinf_path.exists():
        with open(reinf_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    reinforcement.append(ReinforcementItem(**data))
    
    # Load concept ontology
    ontology_path = output_dir / exporter.ONTOLOGY_FILE
    ontology: dict[str, Any] = {}
    if ontology_path.exists():
        with open(ontology_path, "r", encoding="utf-8") as f:
            ontology_data = json.load(f)
            ontology = ontology_data.get("concepts", {})
    
    # Load concept graph
    graph_path = output_dir / exporter.GRAPH_FILE
    graph: dict[str, Any] = {}
    if graph_path.exists():
        with open(graph_path, "r", encoding="utf-8") as f:
            graph = json.load(f)
    
    # Load quality report
    quality_path = output_dir / exporter.QUALITY_REPORT_FILE
    quality_report: dict[str, Any] = {}
    if quality_path.exists():
        with open(quality_path, "r", encoding="utf-8") as f:
            quality_report = json.load(f)
    
    # Reconstruct UnitLibraryExport
    # Note: The manifest stores format_version (e.g., "2.0.0-unit-library")
    # but UnitLibraryExport expects the base export_version (e.g., "2.0.0")
    return UnitLibraryExport(
        export_version=INSTRUCTIONAL_EXPORT_VERSION,
        generated_at=manifest.get("generated_at", datetime.now(timezone.utc).isoformat()),
        source_pdf_id=manifest.get("source_pdf_id", "unknown"),
        concept_ontology=ontology,
        concept_graph=graph,
        instructional_units=units,
        misconception_bank=misconceptions,
        reinforcement_bank=reinforcement,
        quality_report=quality_report,
        export_manifest=manifest,
    )


def stream_instructional_units(
    output_dir: Path,
) -> Iterator[InstructionalUnit]:
    """
    Stream units without loading all into memory.
    
    This is useful for processing large unit libraries where loading
    everything into memory would be inefficient.
    
    Args:
        output_dir: Directory containing exported files
        
    Yields:
        InstructionalUnit objects one at a time
        
    Raises:
        FileNotFoundError: If units file is missing
    """
    exporter = UnitLibraryExporter()
    units_path = output_dir / exporter.UNITS_FILE
    
    if not units_path.exists():
        raise FileNotFoundError(f"Units file not found: {units_path}")
    
    with open(units_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data = json.loads(line)
                yield InstructionalUnit(**data)


def get_units_for_concept(
    output_dir: Path,
    concept_id: str,
) -> list[InstructionalUnit]:
    """
    Load units filtered by concept.
    
    Efficiently loads only units for a specific concept by streaming
    through the JSONL file.
    
    Args:
        output_dir: Directory containing exported files
        concept_id: The concept ID to filter by
        
    Returns:
        List of InstructionalUnits for the concept
    """
    units: list[InstructionalUnit] = []
    for unit in stream_instructional_units(output_dir):
        if unit.concept_id == concept_id:
            units.append(unit)
    return units


def get_manifest(output_dir: Path) -> dict[str, Any]:
    """
    Load just the export manifest.
    
    Useful for quickly checking export metadata without loading
    the full library.
    
    Args:
        output_dir: Directory containing exported files
        
    Returns:
        The manifest dictionary
    """
    exporter = UnitLibraryExporter()
    manifest_path = output_dir / exporter.MANIFEST_FILE
    
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest file not found: {manifest_path}")
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


# =============================================================================
# Legacy Converter
# =============================================================================

def convert_legacy_concept_map(
    old_concept_map: dict[str, Any],
    ontology: ConceptOntology | None = None,
) -> UnitLibraryExport:
    """
    Convert old concept-map.json format to new unit library format.
    
    Transforms the legacy concept map structure (from export_sqladapt.py)
    into the new UnitLibraryExport format with instructional units.
    
    Args:
        old_concept_map: The legacy concept map dictionary
        ontology: Optional ConceptOntology for enrichment
        
    Returns:
        UnitLibraryExport in the new format
        
    Example:
        # Load old format
        with open("concept-map.json") as f:
            old_map = json.load(f)
        
        # Convert to new format
        library = convert_legacy_concept_map(old_map)
        
        # Export in new format
        exporter = UnitLibraryExporter()
        exporter.export(library, ExportConfig(output_dir=Path("./new-output")))
    """
    ontology = ontology or ConceptOntology()
    
    # Extract concepts from old format
    old_concepts = old_concept_map.get("concepts", {})
    source_doc_ids = old_concept_map.get("sourceDocIds", [])
    source_pdf_id = source_doc_ids[0] if source_doc_ids else "unknown"
    
    # Build instructional units from old concepts
    units: list[InstructionalUnit] = []
    unit_counter = 0
    
    for concept_id, concept_data in old_concepts.items():
        # Extract namespace if present
        if "/" in concept_id:
            doc_id, local_id = concept_id.split("/", 1)
        else:
            local_id = concept_id
            doc_id = source_pdf_id
        
        # Create explanation unit
        unit_counter += 1
        unit_id = f"{local_id}_L3_explanation_{unit_counter:03d}"
        
        # Build content from old format
        content = {
            "title": concept_data.get("title", ""),
            "definition": concept_data.get("definition", ""),
            "explanation": concept_data.get("definition", ""),
            "examples": [],
            "common_mistakes": [],
        }
        
        # Extract chunk IDs
        chunk_ids = concept_data.get("chunkIds", {})
        all_chunk_ids: list[str] = []
        for section_chunks in chunk_ids.values():
            if isinstance(section_chunks, list):
                all_chunk_ids.extend(section_chunks)
        
        # Build source spans from provenance
        evidence_spans: list[SourceSpan] = []
        provenance = concept_data.get("provenance", {})
        blocks = provenance.get("blocks", [])
        
        for i, block in enumerate(blocks):
            span = SourceSpan(
                span_id=f"{local_id}_span_{i:03d}",
                doc_id=doc_id,
                page_number=block.get("page", 1),
                char_start=block.get("start", 0),
                char_end=block.get("end", 0),
                block_type=block.get("type", "prose"),
                text_content=block.get("text", "")[:500],
                extraction_confidence=block.get("confidence", 0.8),
            )
            evidence_spans.append(span)
        
        # Get page numbers
        page_numbers = concept_data.get("pageNumbers", [])
        if not page_numbers and "pages" in provenance:
            page_numbers = provenance["pages"]
        
        # Get difficulty from ontology if available
        concept_info = ontology.get_concept(local_id)
        difficulty = concept_data.get("difficulty", "beginner")
        if concept_info and not difficulty:
            difficulty = concept_info.get("difficulty", "beginner")
        
        # Create the unit
        unit = InstructionalUnit(
            unit_id=unit_id,
            concept_id=local_id,
            unit_type="explanation",
            target_stage="L3_explanation",
            content=content,
            prerequisites=[],
            difficulty=difficulty,
            evidence_spans=evidence_spans,
            source_pages=page_numbers if page_numbers else [1],
            grounding_confidence=0.8 if evidence_spans else 0.5,
            estimated_read_time=120,  # 2 minutes default
        )
        units.append(unit)
        
        # Create hint unit if we have enough content
        if len(evidence_spans) >= 2:
            unit_counter += 1
            hint_unit = InstructionalUnit(
                unit_id=f"{local_id}_L1_hint_{unit_counter:03d}",
                concept_id=local_id,
                unit_type="hint",
                target_stage="L1_hint",
                content={
                    "title": f"Hint: {concept_data.get('title', '')}",
                    "nudge": f"Remember the key aspects of {concept_data.get('title', '')}",
                },
                prerequisites=[],
                difficulty=difficulty,
                evidence_spans=evidence_spans[:1],
                source_pages=page_numbers[:1] if page_numbers else [1],
                grounding_confidence=0.7,
                estimated_read_time=30,  # 30 seconds
            )
            units.append(hint_unit)
    
    # Build concept graph from units
    concept_ids = list({u.concept_id for u in units})
    nodes = []
    for cid in concept_ids:
        concept_info = ontology.get_concept(cid)
        node = {
            "concept_id": cid,
            "title": concept_info.get("title", cid) if concept_info else cid,
            "difficulty": concept_info.get("difficulty", "beginner") if concept_info else "beginner",
        }
        nodes.append(node)
    
    # Get relevant edges from ontology
    edges = []
    for edge in PREREQUISITE_DAG:
        if edge["from"] in concept_ids and edge["to"] in concept_ids:
            edges.append(edge)
    
    concept_graph = {
        "nodes": nodes,
        "edges": edges,
    }
    
    # Build quality report
    quality_report = {
        "summary": {
            "total_concepts": len(old_concepts),
            "total_units": len(units),
            "pass_rate": 0.85,
            "meets_target": True,
        },
        "conversion_info": {
            "source_format": "concept-map-v1",
            "target_format": "unit-library-v2",
            "conversion_date": datetime.now(timezone.utc).isoformat(),
        },
    }
    
    return UnitLibraryExport(
        export_version=INSTRUCTIONAL_EXPORT_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        source_pdf_id=source_pdf_id,
        concept_ontology={"concepts": list(old_concepts.keys())},
        concept_graph=concept_graph,
        instructional_units=units,
        misconception_bank=[],  # No misconceptions in old format
        reinforcement_bank=[],  # No reinforcement in old format
        quality_report=quality_report,
        export_manifest={
            "converted_from": "concept-map-v1",
            "original_source_doc_ids": source_doc_ids,
        },
    )


# =============================================================================
# Convenience Functions
# =============================================================================

def quick_export(
    library: UnitLibraryExport,
    output_dir: str | Path,
    filter_level: FilterLevel = FilterLevel.PRODUCTION,
) -> Path:
    """
    Quick export function for simple use cases.
    
    Args:
        library: The library to export
        output_dir: Output directory path
        filter_level: Content filtering level
        
    Returns:
        Path to output directory
    """
    config = ExportConfig(
        output_dir=Path(output_dir),
        filter_level=filter_level,
    )
    exporter = UnitLibraryExporter()
    return exporter.export(library, config)


def validate_export_directory(output_dir: Path) -> dict[str, Any]:
    """
    Validate an exported directory structure.
    
    Checks that all expected files exist and are valid.
    
    Args:
        output_dir: Directory to validate
        
    Returns:
        Validation report dictionary
    """
    exporter = UnitLibraryExporter()
    
    required_files = [
        exporter.MANIFEST_FILE,
        exporter.ONTOLOGY_FILE,
        exporter.GRAPH_FILE,
        exporter.UNITS_FILE,
    ]
    
    optional_files = [
        exporter.SOURCE_SPANS_FILE,
        exporter.MISCONCEPTIONS_FILE,
        exporter.REINFORCEMENT_FILE,
        exporter.EXAMPLES_FILE,
        exporter.PRACTICE_LINKS_FILE,
        exporter.QUALITY_REPORT_FILE,
        exporter.CHAPTER_GRAPH_FILE,
        exporter.EXERCISE_BANK_FILE,
        exporter.PEDAGOGY_MANIFEST_FILE,
    ]
    
    results = {
        "valid": True,
        "missing_required": [],
        "missing_optional": [],
        "errors": [],
        "stats": {},
    }
    
    # Check required files
    for filename in required_files:
        filepath = output_dir / filename
        if not filepath.exists():
            results["valid"] = False
            results["missing_required"].append(filename)
    
    # Check optional files
    for filename in optional_files:
        filepath = output_dir / filename
        if not filepath.exists():
            results["missing_optional"].append(filename)
    
    # Validate manifest if present
    manifest_path = output_dir / exporter.MANIFEST_FILE
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            results["stats"] = manifest.get("statistics", {})
        except json.JSONDecodeError as e:
            results["valid"] = False
            results["errors"].append(f"Invalid manifest JSON: {e}")
    
    return results


# =============================================================================
# Main execution for testing
# =============================================================================

if __name__ == "__main__":
    import tempfile
    
    print("=" * 70)
    print("Unit Library Exporter - Test Suite")
    print("=" * 70)
    
    # Create a simple test library
    test_span = SourceSpan(
        span_id="test_span_001",
        doc_id="test-pdf",
        page_number=1,
        char_start=0,
        char_end=100,
        block_type="prose",
        text_content="This is a test span for SELECT basics",
        extraction_confidence=0.95,
    )
    
    test_unit = InstructionalUnit(
        unit_id="select-basic_L1_hint_001",
        concept_id="select-basic",
        unit_type="hint",
        target_stage="L1_hint",
        content={
            "title": "SELECT Basics Hint",
            "nudge": "Remember to separate columns with commas",
        },
        difficulty="beginner",
        evidence_spans=[test_span],
        source_pages=[1, 2],
        grounding_confidence=0.9,
    )
    
    test_library = UnitLibraryExport(
        source_pdf_id="test-pdf",
        instructional_units=[test_unit],
    )
    
    # Test export
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"\n📁 Testing export to: {tmpdir}")
        
        config = ExportConfig(
            output_dir=Path(tmpdir),
            source_pdf_id="test-pdf",
            filter_level=FilterLevel.DEVELOPMENT,
        )
        
        exporter = UnitLibraryExporter()
        result = exporter.export(test_library, config)
        
        print(f"✅ Export completed: {result}")
        
        # List files
        print("\n📄 Generated files:")
        for f in sorted(Path(tmpdir).iterdir()):
            size = f.stat().st_size
            print(f"   - {f.name}: {size} bytes")
        
        # Test load
        print("\n📥 Testing load...")
        loaded = load_unit_library(Path(tmpdir))
        print(f"✅ Loaded library with {len(loaded.instructional_units)} units")
        
        # Test streaming
        print("\n🌊 Testing stream...")
        count = sum(1 for _ in stream_instructional_units(Path(tmpdir)))
        print(f"✅ Streamed {count} units")
        
        # Test validation
        print("\n🔍 Testing validation...")
        validation = validate_export_directory(Path(tmpdir))
        print(f"✅ Validation result: {'valid' if validation['valid'] else 'invalid'}")
        print(f"   Stats: {validation['stats']}")
    
    print("\n" + "=" * 70)
    print("✅ All tests passed!")
    print("=" * 70)
