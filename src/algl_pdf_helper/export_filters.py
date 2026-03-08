"""
Strict Export Filter System for Instructional Content.

This module implements aggressive "do not export" rules to prevent low-quality
content from reaching learners. It provides a configurable rule-based system
for filtering instructional units before export.

Usage:
    from export_filters import ExportFilterEngine, PRODUCTION_FILTERS
    
    engine = ExportFilterEngine(PRODUCTION_FILTERS)
    result = engine.filter_unit_library(library)
    
    if result.can_export:
        export_data = engine.get_exportable_subset(library)
    else:
        rejected = engine.get_rejected_units(library)
        print(f"Blocked {len(rejected)} units")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Protocol

from .pedagogical_models import PedagogicalConcept, SQLExample


# =============================================================================
# TYPES AND PROTOCOLS
# =============================================================================

class RuleType(Enum):
    """Type of export rule - determines severity of violation."""
    HARD_BLOCK = "hard_block"  # Prevents export entirely
    SOFT_BLOCK = "soft_block"  # Allows export with warning
    WARN = "warn"              # Just logs a warning


class InstructionalUnit(Protocol):
    """Protocol for instructional units that can be filtered."""
    
    concept_id: str
    title: str
    definition: str
    examples: list[SQLExample]
    
    # Optional attributes that may be present
    relevance_score: float | None
    semantic_score: float | None
    extraction_confidence: float | None
    learning_objectives: list[str] | None
    prerequisites: list[str] | None
    error_subtypes: list[str] | None
    stage_variants: dict[str, Any] | None
    evidence_spans: list[dict] | None
    source_pages: list[int] | None
    is_admin_only: bool | None
    is_validated: bool | None
    tags: list[str] | None


@dataclass
class UnitLibraryExport:
    """A library of instructional units ready for export."""
    
    units: list[PedagogicalConcept] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def get_unit(self, concept_id: str) -> PedagogicalConcept | None:
        """Get a unit by its concept ID."""
        for unit in self.units:
            if unit.concept_id == concept_id:
                return unit
        return None
    
    def get_unit_ids(self) -> list[str]:
        """Get all unit IDs in the library."""
        return [u.concept_id for u in self.units]


# =============================================================================
# RULE AND RESULT DATA CLASSES
# =============================================================================

@dataclass
class ExportRule:
    """
    A rule for filtering instructional content.
    
    Attributes:
        rule_id: Unique identifier for this rule
        rule_type: HARD_BLOCK, SOFT_BLOCK, or WARN
        description: Human-readable description
        check_fn: Function that takes a unit and returns (passed, message)
        error_message: Default message when rule fails
    """
    rule_id: str
    rule_type: RuleType
    description: str
    check_fn: Callable[[PedagogicalConcept], tuple[bool, str]]
    error_message: str
    
    def check(self, unit: PedagogicalConcept) -> tuple[bool, str]:
        """Run the check function on a unit."""
        return self.check_fn(unit)


@dataclass
class FilterResult:
    """
    Result of running export filters on a unit library.
    
    Attributes:
        can_export: Whether any content can be exported
        blocked_by: List of rule IDs that caused hard blocks
        warnings: List of warning messages from soft blocks
        filtered_units: Unit IDs that were removed (hard blocked)
        passed_units: Unit IDs that passed all hard blocks
    """
    can_export: bool
    blocked_by: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    filtered_units: list[str] = field(default_factory=list)
    passed_units: list[str] = field(default_factory=list)
    
    @property
    def total_units(self) -> int:
        """Total number of units processed."""
        return len(self.filtered_units) + len(self.passed_units)
    
    @property
    def pass_rate(self) -> float:
        """Percentage of units that passed."""
        total = self.total_units
        return len(self.passed_units) / total if total > 0 else 0.0


@dataclass
class UnitFilterResult:
    """Result of filtering a single unit."""
    unit_id: str
    can_export: bool
    hard_block_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# =============================================================================
# PLACEHOLDER CHECK FUNCTIONS
# =============================================================================

def _check_title_too_long(unit: PedagogicalConcept) -> tuple[bool, str]:
    """Check if title is too long (looks like a sentence/fragment)."""
    words = unit.title.split()
    word_count = len(words)
    if word_count > 10:
        return False, f"Title too long ({word_count} words, max 10): looks like a sentence"
    return True, "Title length acceptable"


def _check_title_is_heading_fragment(unit: PedagogicalConcept) -> tuple[bool, str]:
    """Check if title ends with words like 'the', 'and', 'for' (fragment indicator)."""
    fragment_words = {"the", "and", "for", "of", "in", "to", "a", "an", "with", "by", "from", "on", "at"}
    words = unit.title.lower().split()
    if words and words[-1] in fragment_words:
        return False, f"Title ends with fragment word '{words[-1]}': appears to be incomplete"
    return True, "Title does not end with fragment word"


def _check_low_relevance_score(unit: PedagogicalConcept) -> tuple[bool, str]:
    """Check if relevance score is too low (requires unit.relevance_score attribute)."""
    score = getattr(unit, 'relevance_score', None)
    if score is None:
        return True, "No relevance score set"
    if score < 0.6:
        return False, f"Relevance score too low ({score:.2f}, min 0.6)"
    return True, f"Relevance score acceptable ({score:.2f})"


def _check_placeholder_example_present(unit: PedagogicalConcept) -> tuple[bool, str]:
    """Check for placeholder text indicating failed extraction."""
    placeholder_patterns = [
        r"see textbook",
        r"refer to",
        r"content could not be extracted",
        r"extraction failed",
        r"\[placeholder\]",
        r"\[example needed\]",
        r"\[todo\]",
        r"not available",
    ]
    
    text_to_check = f"{unit.title} {unit.definition}"
    for example in unit.examples:
        text_to_check += f" {example.description} {example.query} {example.explanation}"
    
    text_lower = text_to_check.lower()
    
    for pattern in placeholder_patterns:
        if re.search(pattern, text_lower):
            return False, f"Placeholder text detected: '{pattern}'"
    
    return True, "No placeholder text detected"


def _check_empty_definition(unit: PedagogicalConcept) -> tuple[bool, str]:
    """Check if definition is empty or too short."""
    definition = unit.definition or ""
    if not definition.strip():
        return False, "Definition is empty"
    if len(definition.strip()) < 20:
        return False, f"Definition too short ({len(definition)} chars, min 20)"
    return True, f"Definition length acceptable ({len(definition)} chars)"


def _check_no_valid_example(unit: PedagogicalConcept) -> tuple[bool, str]:
    """Check if there's at least one executable SQL example."""
    if not unit.examples:
        return False, "No SQL examples present"
    
    # Check for at least one valid-looking SQL query
    for i, example in enumerate(unit.examples):
        query = example.query.strip() if example.query else ""
        if not query:
            continue
        # Basic SQL validation - must start with SQL keyword and end with semicolon
        sql_keywords = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "WITH"]
        query_upper = query.upper()
        if any(query_upper.startswith(kw) for kw in sql_keywords) and query.endswith(";"):
            return True, f"Valid SQL example found (example {i+1})"
    
    return False, "No executable SQL examples found"


def _check_not_in_canonical_ontology(unit: PedagogicalConcept) -> tuple[bool, str]:
    """Check if concept ID is in the canonical SQL ontology."""
    from .sql_ontology import SQL_CONCEPTS
    
    if unit.concept_id not in SQL_CONCEPTS:
        return False, f"Concept '{unit.concept_id}' not in canonical ontology"
    return True, "Concept in canonical ontology"


def _check_no_source_evidence(unit: PedagogicalConcept) -> tuple[bool, str]:
    """Check if unit has evidence spans and source pages."""
    evidence_spans = getattr(unit, 'evidence_spans', None)
    source_pages = getattr(unit, 'source_pages', None)
    
    has_evidence = evidence_spans is not None and len(evidence_spans) > 0
    has_pages = source_pages is not None and len(source_pages) > 0
    
    if not has_evidence and not has_pages:
        return False, "No source evidence or pages attached"
    if not has_evidence:
        return False, "No evidence spans attached"
    if not has_pages:
        return False, "No source pages attached"
    
    return True, "Source evidence present"


def _check_admin_only_concept(unit: PedagogicalConcept) -> tuple[bool, str]:
    """Check if concept is marked as admin/reference only."""
    is_admin = getattr(unit, 'is_admin_only', None)
    
    if is_admin:
        return False, "Concept marked as admin-only (not for student consumption)"
    
    # Also check tags
    tags = getattr(unit, 'tags', []) or []
    admin_tags = {"admin", "reference", "internal", "teacher-only", "instructor"}
    if any(tag.lower() in admin_tags for tag in tags):
        return False, "Concept has admin-only tag"
    
    return True, "Not an admin-only concept"


def _check_extraction_confidence_too_low(unit: PedagogicalConcept) -> tuple[bool, str]:
    """Check if extraction confidence is too low."""
    confidence = getattr(unit, 'extraction_confidence', None)
    
    if confidence is None:
        return True, "No extraction confidence set"
    
    if confidence < 0.5:
        return False, f"Extraction confidence too low ({confidence:.2f}, min 0.5)"
    
    return True, f"Extraction confidence acceptable ({confidence:.2f})"


# =============================================================================
# SOFT BLOCK CHECK FUNCTIONS
# =============================================================================

def _check_missing_learning_objectives(unit: PedagogicalConcept) -> tuple[bool, str]:
    """Check if unit has learning objectives."""
    objectives = getattr(unit, 'learning_objectives', None)
    
    if objectives is None or len(objectives) == 0:
        return False, "No learning objectives defined"
    
    return True, f"Has {len(objectives)} learning objectives"


def _check_missing_prerequisites(unit: PedagogicalConcept) -> tuple[bool, str]:
    """Check if unit has prerequisites defined."""
    prereqs = getattr(unit, 'prerequisites', None)
    
    if prereqs is None or len(prereqs) == 0:
        return False, "No prerequisites defined (isolated node in learning graph)"
    
    return True, f"Has {len(prereqs)} prerequisites"


def _check_missing_error_subtypes(unit: PedagogicalConcept) -> tuple[bool, str]:
    """Check if unit has error subtype tags."""
    error_subtypes = getattr(unit, 'error_subtypes', None)
    
    if error_subtypes is None or len(error_subtypes) == 0:
        return False, "No error subtype tags (reduces SQL-Engage integration)"
    
    return True, f"Has {len(error_subtypes)} error subtypes"


def _check_incomplete_stage_variants(unit: PedagogicalConcept) -> tuple[bool, str]:
    """Check if unit has complete L1-L4 stage variants."""
    stage_variants = getattr(unit, 'stage_variants', None)
    
    if stage_variants is None:
        return False, "No stage variants defined"
    
    required_stages = ["L1", "L2", "L3", "L4"]
    missing = [s for s in required_stages if s not in stage_variants]
    
    if missing:
        return False, f"Missing stage variants: {', '.join(missing)}"
    
    return True, "All L1-L4 stage variants present"


def _check_example_not_validated(unit: PedagogicalConcept) -> tuple[bool, str]:
    """Check if SQL examples have been execution-tested."""
    is_validated = getattr(unit, 'is_validated', None)
    
    if is_validated is False:
        return False, "SQL examples not validated (not execution-tested)"
    
    return True, "SQL examples validated or validation not tracked"


def _check_low_semantic_score(unit: PedagogicalConcept) -> tuple[bool, str]:
    """Check if semantic score is below threshold."""
    score = getattr(unit, 'semantic_score', None)
    
    if score is None:
        return True, "No semantic score set"
    
    if score < 0.7:
        return False, f"Semantic score low ({score:.2f}, recommended min 0.7)"
    
    return True, f"Semantic score acceptable ({score:.2f})"


# =============================================================================
# CONTENT QUALITY CHECK FUNCTIONS
# =============================================================================

def _check_contains_config_variables(unit: PedagogicalConcept) -> tuple[bool, str]:
    """Check if content looks like configuration code."""
    config_patterns = [
        r"log_output\s*=",
        r"settings\s*[=\{]",
        r"config\s*[=\{]",
        r"DEBUG\s*=",
        r"PORT\s*=",
        r"HOST\s*=",
        r"API_KEY",
        r"password\s*=",
        r"username\s*=",
        r"\.env",
        r"environment variable",
    ]
    
    text_to_check = f"{unit.title} {unit.definition}"
    text_lower = text_to_check.lower()
    
    for pattern in config_patterns:
        if re.search(pattern, text_lower):
            return False, f"Config/code-like content detected: '{pattern}'"
    
    return True, "No config-like content detected"


def _check_looks_like_toc_entry(unit: PedagogicalConcept) -> tuple[bool, str]:
    """Check if content matches table of contents patterns."""
    toc_patterns = [
        r"^chapter\s+\d+",
        r"^section\s+\d+",
        r"^\d+\.\d+\s+",
        r"^appendix\s+[a-z]",
        r"^table of contents",
        r"^contents$",
        r"^index$",
        r"^glossary$",
        r"^references$",
    ]
    
    title_lower = unit.title.lower().strip()
    
    for pattern in toc_patterns:
        if re.match(pattern, title_lower):
            return False, f"Matches TOC pattern: '{pattern}'"
    
    # Check for very short content that looks like a TOC entry
    if len(unit.definition) < 50 and len(unit.examples) == 0:
        return False, "Very short content with no examples - likely TOC entry"
    
    return True, "Not a TOC entry"


def _check_appendix_content(unit: PedagogicalConcept) -> tuple[bool, str]:
    """Check if content is appendix/admin material."""
    appendix_indicators = [
        "appendix",
        "bibliography",
        "acknowledgments",
        "about the author",
        "about this book",
        "preface",
        "foreword",
        "copyright",
        "trademark",
        "disclaimer",
        "license",
        "errata",
        "revision history",
    ]
    
    title_lower = unit.title.lower().strip()
    
    for indicator in appendix_indicators:
        if indicator in title_lower:
            return False, f"Appendix/admin content: '{indicator}'"
    
    return True, "Not appendix/admin content"


# =============================================================================
# PRE-DEFINED RULES
# =============================================================================

# Hard Block Rules - These prevent export entirely
HARD_BLOCK_RULES: list[ExportRule] = [
    ExportRule(
        rule_id="title_too_long",
        rule_type=RuleType.HARD_BLOCK,
        description="Title > 10 words looks like a sentence/fragment",
        check_fn=_check_title_too_long,
        error_message="Title is too long - appears to be a sentence, not a concept title"
    ),
    ExportRule(
        rule_id="title_is_heading_fragment",
        rule_type=RuleType.HARD_BLOCK,
        description="Title ends with fragment words like 'the', 'and', 'for'",
        check_fn=_check_title_is_heading_fragment,
        error_message="Title appears to be an incomplete heading fragment"
    ),
    ExportRule(
        rule_id="low_relevance_score",
        rule_type=RuleType.HARD_BLOCK,
        description="Relevance score < 0.6",
        check_fn=_check_low_relevance_score,
        error_message="Content relevance too low for student consumption"
    ),
    ExportRule(
        rule_id="placeholder_example_present",
        rule_type=RuleType.HARD_BLOCK,
        description="Contains placeholder text indicating failed extraction",
        check_fn=_check_placeholder_example_present,
        error_message="Contains placeholder text - content extraction failed"
    ),
    ExportRule(
        rule_id="empty_definition",
        rule_type=RuleType.HARD_BLOCK,
        description="Definition is empty or < 20 characters",
        check_fn=_check_empty_definition,
        error_message="Definition is missing or too short"
    ),
    ExportRule(
        rule_id="no_valid_example",
        rule_type=RuleType.HARD_BLOCK,
        description="No executable SQL example",
        check_fn=_check_no_valid_example,
        error_message="No valid SQL examples for students to learn from"
    ),
    ExportRule(
        rule_id="not_in_canonical_ontology",
        rule_type=RuleType.HARD_BLOCK,
        description="Concept ID not in sql_ontology",
        check_fn=_check_not_in_canonical_ontology,
        error_message="Concept not in canonical ontology - cannot be placed in learning graph"
    ),
    ExportRule(
        rule_id="no_source_evidence",
        rule_type=RuleType.HARD_BLOCK,
        description="No evidence spans or empty source_pages",
        check_fn=_check_no_source_evidence,
        error_message="No source evidence attached - cannot verify content accuracy"
    ),
    ExportRule(
        rule_id="admin_only_concept",
        rule_type=RuleType.HARD_BLOCK,
        description="Concept marked as admin/reference only",
        check_fn=_check_admin_only_concept,
        error_message="Admin-only content - not for student consumption"
    ),
    ExportRule(
        rule_id="extraction_confidence_too_low",
        rule_type=RuleType.HARD_BLOCK,
        description="Extraction confidence < 0.5",
        check_fn=_check_extraction_confidence_too_low,
        error_message="Extraction confidence too low - content may be inaccurate"
    ),
]

# Soft Block Rules - Can export with warnings
SOFT_BLOCK_RULES: list[ExportRule] = [
    ExportRule(
        rule_id="missing_learning_objectives",
        rule_type=RuleType.SOFT_BLOCK,
        description="No learning objectives defined",
        check_fn=_check_missing_learning_objectives,
        error_message="Missing learning objectives"
    ),
    ExportRule(
        rule_id="missing_prerequisites",
        rule_type=RuleType.SOFT_BLOCK,
        description="Prerequisites list empty",
        check_fn=_check_missing_prerequisites,
        error_message="No prerequisites - may be isolated in learning graph"
    ),
    ExportRule(
        rule_id="missing_error_subtypes",
        rule_type=RuleType.SOFT_BLOCK,
        description="No error subtype tags",
        check_fn=_check_missing_error_subtypes,
        error_message="No error subtypes - reduces SQL-Engage integration"
    ),
    ExportRule(
        rule_id="incomplete_stage_variants",
        rule_type=RuleType.SOFT_BLOCK,
        description="Missing some L1-L4 variants",
        check_fn=_check_incomplete_stage_variants,
        error_message="Incomplete stage variants (L1-L4)"
    ),
    ExportRule(
        rule_id="example_not_validated",
        rule_type=RuleType.SOFT_BLOCK,
        description="SQL examples not execution-tested",
        check_fn=_check_example_not_validated,
        error_message="SQL examples not validated by execution"
    ),
    ExportRule(
        rule_id="low_semantic_score",
        rule_type=RuleType.SOFT_BLOCK,
        description="Semantic score < 0.7",
        check_fn=_check_low_semantic_score,
        error_message="Semantic similarity below recommended threshold"
    ),
]

# Content Quality Rules
CONTENT_QUALITY_RULES: list[ExportRule] = [
    ExportRule(
        rule_id="contains_config_variables",
        rule_type=RuleType.HARD_BLOCK,
        description="Content looks like config/code",
        check_fn=_check_contains_config_variables,
        error_message="Content appears to be configuration, not educational material"
    ),
    ExportRule(
        rule_id="looks_like_toc_entry",
        rule_type=RuleType.HARD_BLOCK,
        description="Content matches TOC patterns",
        check_fn=_check_looks_like_toc_entry,
        error_message="Content appears to be a table of contents entry"
    ),
    ExportRule(
        rule_id="appendix_content",
        rule_type=RuleType.HARD_BLOCK,
        description="Appendix/admin material",
        check_fn=_check_appendix_content,
        error_message="Appendix or administrative content - not instructional"
    ),
]


# =============================================================================
# PRE-CONFIGURED FILTER SETS
# =============================================================================

STRICT_FILTERS: list[ExportRule] = HARD_BLOCK_RULES.copy()
"""Strict filters - all hard blocks. Prevents any questionable content from exporting."""

PRODUCTION_FILTERS: list[ExportRule] = HARD_BLOCK_RULES + [
    # Add critical soft blocks as hard blocks for production
    ExportRule(
        rule_id="missing_learning_objectives",
        rule_type=RuleType.HARD_BLOCK,
        description="No learning objectives defined",
        check_fn=_check_missing_learning_objectives,
        error_message="Missing learning objectives - required for production"
    ),
    ExportRule(
        rule_id="example_not_validated",
        rule_type=RuleType.HARD_BLOCK,
        description="SQL examples not execution-tested",
        check_fn=_check_example_not_validated,
        error_message="SQL examples must be validated before production"
    ),
]
"""Production filters - hard blocks plus critical soft blocks as hard blocks."""

DEVELOPMENT_FILTERS: list[ExportRule] = [
    # Convert hard blocks to warnings for development
    ExportRule(
        rule_id="title_too_long",
        rule_type=RuleType.WARN,
        description="Title > 10 words",
        check_fn=_check_title_too_long,
        error_message="Title is long (warning only in dev)"
    ),
    ExportRule(
        rule_id="low_relevance_score",
        rule_type=RuleType.WARN,
        description="Relevance score < 0.6",
        check_fn=_check_low_relevance_score,
        error_message="Low relevance score (warning only in dev)"
    ),
    ExportRule(
        rule_id="placeholder_example_present",
        rule_type=RuleType.HARD_BLOCK,  # Keep this as hard block even in dev
        description="Contains placeholder text",
        check_fn=_check_placeholder_example_present,
        error_message="Contains placeholder text - cannot export"
    ),
    ExportRule(
        rule_id="empty_definition",
        rule_type=RuleType.HARD_BLOCK,  # Keep this as hard block even in dev
        description="Definition is empty",
        check_fn=_check_empty_definition,
        error_message="Definition is missing - cannot export"
    ),
] + SOFT_BLOCK_RULES
"""Development filters - warnings instead of blocks, but still catches critical issues."""


# =============================================================================
# EXPORT FILTER ENGINE
# =============================================================================

class ExportFilterEngine:
    """
    Engine for filtering instructional content before export.
    
    Applies a set of rules to each unit in a library, tracking which units
    pass, which are blocked, and collecting warnings for soft-blocked content.
    
    Example:
        >>> engine = ExportFilterEngine(PRODUCTION_FILTERS)
        >>> result = engine.filter_unit_library(library)
        >>> print(f"Pass rate: {result.pass_rate:.1%}")
        >>> exportable = engine.get_exportable_subset(library)
    """
    
    def __init__(self, rules: list[ExportRule] | None = None):
        """
        Initialize the filter engine.
        
        Args:
            rules: List of ExportRule to apply. If None, uses PRODUCTION_FILTERS.
        """
        self.rules = rules or PRODUCTION_FILTERS
        self._rule_map: dict[str, ExportRule] = {r.rule_id: r for r in self.rules}
        
        # Categorize rules by type
        self.hard_block_rules = [r for r in self.rules if r.rule_type == RuleType.HARD_BLOCK]
        self.soft_block_rules = [r for r in self.rules if r.rule_type == RuleType.SOFT_BLOCK]
        self.warn_rules = [r for r in self.rules if r.rule_type == RuleType.WARN]
    
    def add_rule(self, rule: ExportRule) -> None:
        """Add a custom rule to the engine."""
        self.rules.append(rule)
        self._rule_map[rule.rule_id] = rule
        
        # Update categorized lists
        if rule.rule_type == RuleType.HARD_BLOCK:
            self.hard_block_rules.append(rule)
        elif rule.rule_type == RuleType.SOFT_BLOCK:
            self.soft_block_rules.append(rule)
        elif rule.rule_type == RuleType.WARN:
            self.warn_rules.append(rule)
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID. Returns True if removed."""
        if rule_id not in self._rule_map:
            return False
        
        rule = self._rule_map.pop(rule_id)
        self.rules.remove(rule)
        
        # Update categorized lists
        if rule in self.hard_block_rules:
            self.hard_block_rules.remove(rule)
        if rule in self.soft_block_rules:
            self.soft_block_rules.remove(rule)
        if rule in self.warn_rules:
            self.warn_rules.remove(rule)
        
        return True
    
    def filter_unit_library(self, library: UnitLibraryExport) -> FilterResult:
        """
        Apply all rules to each unit in the library.
        
        Args:
            library: The UnitLibraryExport to filter
            
        Returns:
            FilterResult with summary of what passed/failed and why
        """
        blocked_by: list[str] = []
        warnings: list[str] = []
        filtered_units: list[str] = []
        passed_units: list[str] = []
        
        for unit in library.units:
            unit_result = self._filter_single_unit(unit)
            
            if unit_result.can_export:
                passed_units.append(unit.concept_id)
                # Still collect warnings
                warnings.extend(unit_result.warnings)
            else:
                filtered_units.append(unit.concept_id)
                blocked_by.extend(unit_result.hard_block_reasons)
        
        # Deduplicate
        blocked_by = list(set(blocked_by))
        warnings = list(set(warnings))
        
        can_export = len(passed_units) > 0
        
        return FilterResult(
            can_export=can_export,
            blocked_by=blocked_by,
            warnings=warnings,
            filtered_units=filtered_units,
            passed_units=passed_units,
        )
    
    def _filter_single_unit(self, unit: PedagogicalConcept) -> UnitFilterResult:
        """
        Filter a single unit against all rules.
        
        Args:
            unit: The PedagogicalConcept to check
            
        Returns:
            UnitFilterResult with detailed results
        """
        hard_block_reasons: list[str] = []
        warnings: list[str] = []
        
        # Check hard block rules
        for rule in self.hard_block_rules:
            passed, message = rule.check(unit)
            if not passed:
                hard_block_reasons.append(f"{rule.rule_id}: {message}")
        
        # Check soft block rules
        for rule in self.soft_block_rules:
            passed, message = rule.check(unit)
            if not passed:
                warnings.append(f"{unit.concept_id} - {rule.rule_id}: {message}")
        
        # Check warn rules
        for rule in self.warn_rules:
            passed, message = rule.check(unit)
            if not passed:
                warnings.append(f"{unit.concept_id} - {rule.rule_id}: {message}")
        
        can_export = len(hard_block_reasons) == 0
        
        return UnitFilterResult(
            unit_id=unit.concept_id,
            can_export=can_export,
            hard_block_reasons=hard_block_reasons,
            warnings=warnings,
        )
    
    def validate_single_unit(self, unit: PedagogicalConcept) -> tuple[bool, list[str]]:
        """
        Check one unit against all rules.
        
        Args:
            unit: The PedagogicalConcept to validate
            
        Returns:
            Tuple of (can_export, list_of_violations)
        """
        result = self._filter_single_unit(unit)
        
        violations = result.hard_block_reasons.copy()
        if result.warnings:
            violations.extend([f"WARN: {w}" for w in result.warnings])
        
        return result.can_export, violations
    
    def get_exportable_subset(self, library: UnitLibraryExport) -> UnitLibraryExport:
        """
        Return only units that pass all hard blocks.
        
        Args:
            library: The UnitLibraryExport to filter
            
        Returns:
            New UnitLibraryExport with only passing units
        """
        passed_units: list[PedagogicalConcept] = []
        
        for unit in library.units:
            result = self._filter_single_unit(unit)
            if result.can_export:
                passed_units.append(unit)
        
        return UnitLibraryExport(
            units=passed_units,
            metadata={
                **library.metadata,
                "filtered": True,
                "original_count": len(library.units),
                "filtered_count": len(passed_units),
            }
        )
    
    def get_rejected_units(
        self, 
        library: UnitLibraryExport
    ) -> list[tuple[str, list[str]]]:
        """
        Return units that were rejected with their reasons.
        
        Args:
            library: The UnitLibraryExport to check
            
        Returns:
            List of (unit_id, reasons) tuples for rejected units
        """
        rejected: list[tuple[str, list[str]]] = []
        
        for unit in library.units:
            result = self._filter_single_unit(unit)
            if not result.can_export:
                rejected.append((unit.concept_id, result.hard_block_reasons))
        
        return rejected
    
    def get_filter_statistics(self, library: UnitLibraryExport) -> dict[str, Any]:
        """
        Get detailed statistics about rule violations.
        
        Args:
            library: The UnitLibraryExport to analyze
            
        Returns:
            Dictionary with violation statistics
        """
        rule_violations: dict[str, int] = {r.rule_id: 0 for r in self.rules}
        unit_violations: dict[str, list[str]] = {}
        
        for unit in library.units:
            result = self._filter_single_unit(unit)
            unit_violations[unit.concept_id] = []
            
            # Track which rules were violated
            for reason in result.hard_block_reasons:
                rule_id = reason.split(":")[0]
                if rule_id in rule_violations:
                    rule_violations[rule_id] += 1
                unit_violations[unit.concept_id].append(reason)
        
        # Sort rules by violation count
        top_violations = sorted(
            rule_violations.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        return {
            "total_units": len(library.units),
            "hard_block_rules": len(self.hard_block_rules),
            "soft_block_rules": len(self.soft_block_rules),
            "warn_rules": len(self.warn_rules),
            "rule_violations": dict(top_violations),
            "top_violations": [
                {"rule": r, "count": c} 
                for r, c in top_violations[:5] 
                if c > 0
            ],
            "units_with_violations": {
                k: v for k, v in unit_violations.items() 
                if v
            },
        }
    
    def print_filter_report(self, library: UnitLibraryExport) -> None:
        """Print a formatted filter report to console."""
        result = self.filter_unit_library(library)
        stats = self.get_filter_statistics(library)
        rejected = self.get_rejected_units(library)
        
        print("\n" + "=" * 70)
        print("EXPORT FILTER REPORT")
        print("=" * 70)
        
        print(f"\n📊 Summary:")
        print(f"   Total Units: {result.total_units}")
        print(f"   Passed: {len(result.passed_units)} ✅")
        print(f"   Filtered: {len(result.filtered_units)} ❌")
        print(f"   Pass Rate: {result.pass_rate:.1%}")
        
        if result.can_export:
            print(f"   ✅ Can export: YES")
        else:
            print(f"   ❌ Can export: NO (no units passed)")
        
        if stats["top_violations"]:
            print(f"\n🔍 Top Rule Violations:")
            for v in stats["top_violations"]:
                print(f"   - {v['rule']}: {v['count']} units")
        
        if rejected:
            print(f"\n❌ Rejected Units ({len(rejected)}):")
            for unit_id, reasons in rejected[:10]:  # Show first 10
                print(f"   - {unit_id}:")
                for reason in reasons[:2]:  # Show first 2 reasons
                    print(f"      • {reason}")
            if len(rejected) > 10:
                print(f"   ... and {len(rejected) - 10} more")
        
        if result.warnings:
            print(f"\n⚠️  Warnings ({len(result.warnings)}):")
            for warning in result.warnings[:5]:  # Show first 5
                print(f"   - {warning}")
            if len(result.warnings) > 5:
                print(f"   ... and {len(result.warnings) - 5} more")
        
        print("\n" + "=" * 70)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def create_custom_filter_set(
    include_hard_blocks: list[str] | None = None,
    include_soft_blocks: list[str] | None = None,
    include_warns: list[str] | None = None,
    custom_rules: list[ExportRule] | None = None,
) -> list[ExportRule]:
    """
    Create a custom filter set by selecting from pre-defined rules.
    
    Args:
        include_hard_blocks: List of hard block rule IDs to include (None = all)
        include_soft_blocks: List of soft block rule IDs to include (None = all)
        include_warns: List of warn rule IDs to include (None = all)
        custom_rules: Additional custom rules to add
        
    Returns:
        List of ExportRule for use with ExportFilterEngine
    """
    rules: list[ExportRule] = []
    
    # Add hard blocks
    hard_block_map = {r.rule_id: r for r in HARD_BLOCK_RULES}
    if include_hard_blocks is None:
        rules.extend(HARD_BLOCK_RULES)
    else:
        for rule_id in include_hard_blocks:
            if rule_id in hard_block_map:
                rules.append(hard_block_map[rule_id])
    
    # Add soft blocks
    soft_block_map = {r.rule_id: r for r in SOFT_BLOCK_RULES}
    if include_soft_blocks is None:
        rules.extend(SOFT_BLOCK_RULES)
    else:
        for rule_id in include_soft_blocks:
            if rule_id in soft_block_map:
                rules.append(soft_block_map[rule_id])
    
    # Add warn rules
    warn_map = {r.rule_id: r for r in CONTENT_QUALITY_RULES}
    if include_warns is None:
        rules.extend(CONTENT_QUALITY_RULES)
    else:
        for rule_id in include_warns:
            if rule_id in warn_map:
                rules.append(warn_map[rule_id])
    
    # Add custom rules
    if custom_rules:
        rules.extend(custom_rules)
    
    return rules


def quick_filter_check(unit: PedagogicalConcept) -> tuple[bool, list[str]]:
    """
    Quick check using STRICT_FILTERS.
    
    Args:
        unit: The PedagogicalConcept to check
        
    Returns:
        Tuple of (can_export, list_of_violations)
    """
    engine = ExportFilterEngine(STRICT_FILTERS)
    return engine.validate_single_unit(unit)


def should_export(unit: PedagogicalConcept) -> bool:
    """
    Quick boolean check if a unit should be exported (using STRICT_FILTERS).
    
    Args:
        unit: The PedagogicalConcept to check
        
    Returns:
        True if unit passes all hard blocks
    """
    can_export, _ = quick_filter_check(unit)
    return can_export


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Enums and dataclasses
    "RuleType",
    "ExportRule",
    "FilterResult",
    "UnitFilterResult",
    "UnitLibraryExport",
    
    # Pre-defined rules
    "HARD_BLOCK_RULES",
    "SOFT_BLOCK_RULES",
    "CONTENT_QUALITY_RULES",
    
    # Pre-configured filter sets
    "STRICT_FILTERS",
    "PRODUCTION_FILTERS",
    "DEVELOPMENT_FILTERS",
    
    # Main engine
    "ExportFilterEngine",
    
    # Utility functions
    "create_custom_filter_set",
    "quick_filter_check",
    "should_export",
]
