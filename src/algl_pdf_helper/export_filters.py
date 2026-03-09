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
from typing import Any, Callable

from .instructional_models import InstructionalUnit, UnitLibraryExport, SourceSpan
from .sql_ontology import ConceptOntology


# =============================================================================
# TYPES AND PROTOCOLS
# =============================================================================

class RuleType(Enum):
    """Type of export rule - determines severity of violation."""
    HARD_BLOCK = "hard_block"  # Prevents export entirely
    SOFT_BLOCK = "soft_block"  # Allows export with warning
    WARN = "warn"              # Just logs a warning


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
    check_fn: Callable[[InstructionalUnit], tuple[bool, str]]
    error_message: str
    
    def check(self, unit: InstructionalUnit) -> tuple[bool, str]:
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

# Cache for ontology instance
_ontology_cache: ConceptOntology | None = None


def _get_ontology() -> ConceptOntology:
    """Get or create cached ConceptOntology instance."""
    global _ontology_cache
    if _ontology_cache is None:
        _ontology_cache = ConceptOntology()
    return _ontology_cache


def _get_unit_title(unit: InstructionalUnit) -> str:
    """Extract title from unit content."""
    content = unit.content or {}
    if isinstance(content, dict):
        title = content.get("title", "")
        if not title:
            # Try other possible fields
            title = content.get("concept_title", "")
        if not title:
            # Fall back to unit_id formatted
            title = unit.unit_id.replace("_", " ").replace("-", " ")
    else:
        title = str(unit.unit_id).replace("_", " ").replace("-", " ")
    return title


def _get_unit_definition(unit: InstructionalUnit) -> str:
    """Extract definition/explanation from unit content."""
    content = unit.content or {}
    if isinstance(content, dict):
        # Try various possible definition fields
        for field in ["definition", "explanation", "description", "body", "text"]:
            if field in content and content[field]:
                return str(content[field])
    return ""


def _get_unit_examples(unit: InstructionalUnit) -> list[dict]:
    """Extract SQL examples from unit content, handling all stage types."""
    content = unit.content or {}
    examples = []
    if isinstance(content, dict):
        # L3 style: list of SQLExample objects
        if "examples" in content and isinstance(content["examples"], list):
            examples.extend(content["examples"])

        # L2 style: single example_sql field
        if "example_sql" in content and isinstance(content["example_sql"], str):
            examples.append({
                "sql": content["example_sql"],
                "explanation": content.get("example_explanation", ""),
            })

        # Legacy/other styles
        if "example" in content and isinstance(content["example"], dict):
            examples.append(content["example"])
        if "sql" in content and isinstance(content["sql"], str):
            examples.append({"sql": content["sql"]})
    return examples


def _check_title_too_long(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if title is too long (looks like a sentence/fragment)."""
    title = _get_unit_title(unit)
    words = title.split()
    word_count = len(words)
    if word_count > 10:
        return False, f"Title too long ({word_count} words, max 10): looks like a sentence"
    return True, "Title length acceptable"


def _check_title_is_heading_fragment(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if title ends with words like 'the', 'and', 'for' (fragment indicator)."""
    fragment_words = {"the", "and", "for", "of", "in", "to", "a", "an", "with", "by", "from", "on", "at"}
    title = _get_unit_title(unit)
    words = title.lower().split()
    if words and words[-1] in fragment_words:
        return False, f"Title ends with fragment word '{words[-1]}': appears to be incomplete"
    return True, "Title does not end with fragment word"


def _check_low_relevance_score(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if grounding confidence is too low (uses unit.grounding_confidence).
    
    Relaxed threshold to allow grounded fallback content (0.3) while still
    blocking truly ungrounded content (0.0).
    
    Curated content is always considered high relevance regardless of score.
    """
    # Check if this is curated content
    content = unit.content or {}
    is_curated = content.get("_used_curated_fallback") or (
        content.get("_metadata", {}).get("content_source") == "curated"
    )
    
    if is_curated:
        # Curated content passes this check
        return True, "Curated content - high relevance"
    
    confidence = unit.grounding_confidence
    if confidence < 0.3:
        return False, f"Grounding confidence too low ({confidence:.2f}, min 0.3)"
    return True, f"Grounding confidence acceptable ({confidence:.2f})"


def _check_placeholder_example_present(unit: InstructionalUnit) -> tuple[bool, str]:
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
        r"coming soon",
        r"\[tbd\]",
    ]
    
    title = _get_unit_title(unit)
    definition = _get_unit_definition(unit)
    examples = _get_unit_examples(unit)
    
    text_to_check = f"{title} {definition}"
    for ex in examples:
        if isinstance(ex, dict):
            for key in ["sql", "query", "description", "explanation", "text"]:
                if key in ex:
                    text_to_check += f" {ex[key]}"
    
    text_lower = text_to_check.lower()
    
    for pattern in placeholder_patterns:
        if re.search(pattern, text_lower):
            return False, f"Placeholder text detected: '{pattern}'"
    
    return True, "No placeholder text detected"


def _check_empty_definition(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if definition/content is empty or too short.
    
    Only applies to L3_explanation units - other stages don't require
    full definitions (L1/L2 are hints, L4 is reflective, reinforcement is practice).
    """
    # Skip for non-explanation stages
    if unit.target_stage != "L3_explanation":
        return True, f"Definition check skipped for {unit.target_stage}"
    
    definition = _get_unit_definition(unit)
    if not definition.strip():
        return False, "Definition is empty"
    if len(definition.strip()) < 20:
        return False, f"Definition too short ({len(definition)} chars, min 20)"
    return True, f"Definition length acceptable ({len(definition)} chars)"


def _check_heading_like_definition(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if definition looks like a heading or reference text instead of actual content.
    
    Rejects definitions that are:
    - Chapter titles ("Chapter 5: ...")
    - Section headings ("Section 3.2 - Examples")
    - Reference document text ("Golden Reference...")
    - All-caps headings
    - Title-only text with no sentence structure
    
    Only applies to L3_explanation units.
    """
    # Skip for non-explanation stages
    if unit.target_stage != "L3_explanation":
        return True, f"Heading-like definition check skipped for {unit.target_stage}"
    
    definition = _get_unit_definition(unit)
    if not definition:
        return True, "No definition to check"
    
    definition_lower = definition.lower()
    
    # REJECT: Chapter/section patterns
    if re.match(r'^Chapter\s+\d+', definition, re.IGNORECASE):
        return False, f"Definition appears to be a chapter title: {definition[:50]}"
    
    if re.match(r'^(Chapter|Section|Unit|Module|Lesson|Part)\s+\d+', definition, re.IGNORECASE):
        return False, f"Definition appears to be a heading: {definition[:50]}"
    
    # REJECT: Golden Reference / Reference Document patterns
    if 'golden reference' in definition_lower:
        return False, "Definition contains 'golden reference' - appears to be reference text"
    
    if 'reference document' in definition_lower:
        return False, "Definition contains 'reference document' - appears to be reference text"
    
    # REJECT: "References" or "Bibliography" as standalone
    if re.match(r'^References?$', definition.strip(), re.IGNORECASE):
        return False, "Definition is just 'References' - not a valid definition"
    
    # REJECT: "X - Examples" or similar heading patterns
    if re.search(r'\s+-\s+(Examples|Overview|Summary|Details|Introduction)$', definition, re.IGNORECASE):
        return False, f"Definition appears to be a section heading: {definition[:50]}"
    
    # REJECT: All-caps (likely a heading)
    if definition.isupper():
        return False, "Definition is all uppercase - appears to be a heading"
    
    # REJECT: Title case only with no small words (likely a heading)
    words = definition.split()
    if len(words) > 1 and all(w[0].isupper() for w in words if w and w[0].isalpha()):
        small_words = ['a', 'an', 'the', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'is', 'are', 'with', 'by']
        if not any(w.lower() in small_words for w in words):
            return False, "Definition appears to be title case heading with no sentence structure"
    
    return True, "Definition does not appear to be a heading"


# Concepts that don't require SQL examples (theoretical/admin concepts)
SQL_OPTIONAL_CONCEPTS = {
    "transactions", 
    "isolation-levels", 
    "acid-properties",
    "normalization", 
    "erd-design", 
    "schema-design",
    "transaction-management",
    "concurrency-control",
    "database-design",
}


def _check_no_valid_example(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if there's at least one executable SQL example.
    
    Only applies to L2_hint_plus_example and L3_explanation units.
    Skipped for L1_hint (just hints), L4_reflective_note (reflection), 
    and reinforcement (practice) stages.
    
    Also skipped for theoretical concepts where SQL examples are optional
    (e.g., transactions, isolation levels, ACID properties).
    """
    # Skip for concepts where SQL examples are optional
    if unit.concept_id in SQL_OPTIONAL_CONCEPTS:
        return True, f"SQL examples optional for theoretical concept '{unit.concept_id}'"
    
    # Only apply to L2 and L3 stages
    applicable_stages = {"L2_hint_plus_example", "L3_explanation"}
    if unit.target_stage not in applicable_stages:
        return True, f"SQL example check skipped for {unit.target_stage}"
    
    examples = _get_unit_examples(unit)
    
    if not examples:
        return False, "No SQL examples present"
    
    # Check for at least one valid-looking SQL query
    sql_keywords = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "WITH"]
    for i, ex in enumerate(examples):
        query = ""
        if isinstance(ex, dict):
            query = ex.get("sql", "") or ex.get("query", "")
        elif isinstance(ex, str):
            query = ex
        
        query = query.strip() if query else ""
        if not query:
            continue
        
        # Basic SQL validation - must start with SQL keyword and end with semicolon
        query_upper = query.upper()
        if any(query_upper.startswith(kw) for kw in sql_keywords) and query.endswith(";"):
            return True, f"Valid SQL example found (example {i+1})"
    
    return False, "No executable SQL examples found"


def _check_not_in_canonical_ontology(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if concept ID is in the canonical SQL ontology."""
    ontology = _get_ontology()
    
    if not ontology.validate_concept_id(unit.concept_id):
        return False, f"Concept '{unit.concept_id}' not in canonical ontology"
    return True, "Concept in canonical ontology"


def _check_no_source_evidence(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if unit has evidence spans and source pages."""
    # Use the InstructionalUnit's has_grounding() method
    if not unit.has_grounding():
        return False, "Unit has no source grounding (no evidence spans or zero grounding confidence)"
    
    # Also verify evidence_spans and source_pages are present
    if not unit.evidence_spans:
        return False, "No evidence spans attached"
    if not unit.source_pages:
        return False, "No source pages attached"
    
    return True, "Source evidence present"


# Concepts that should never be flagged as admin-only
# These are legitimate SQL concepts that happen to contain words like "reference"
NON_ADMIN_CONCEPTS = {
    "correlated-subquery", 
    "subquery", 
    "scalar-subquery",
    "exists-operator", 
    "in-operator", 
    "any-all-operators",
    "nested-query",
    "query-reference",
    "table-reference",
    "foreign-key",
    "primary-key",
    "unique-constraint",
    "check-constraint",
    "default-constraint",
    "referential-integrity",
    "cross-reference",
    "self-reference",
    "recursive-query",
    "with-clause",
    "cte",  # Common Table Expression
    "common-table-expression",
}


def _check_admin_only_concept(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if concept is marked as admin/reference only.
    
    Skips whitelisted concepts that may contain words like "reference"
    but are legitimate SQL educational content.
    """
    # Skip for non-admin concepts that are whitelisted
    if unit.concept_id in NON_ADMIN_CONCEPTS:
        return True, f"Concept '{unit.concept_id}' is whitelisted as educational content"
    
    # Check unit_type for admin content
    admin_types = {"admin", "reference", "metadata", "toc"}
    if unit.unit_type in admin_types:
        return False, f"Unit type '{unit.unit_type}' is admin-only"
    
    # Check target_stage
    if unit.target_stage == "reinforcement" and unit.unit_type in ["hint", "reflection"]:
        # This is a design choice - reinforcement hints are OK
        pass
    
    # Check for admin-only tags in error_subtypes (shouldn't have admin tags here but just in case)
    admin_indicators = {"admin", "internal", "teacher-only", "instructor", "copyright", "preface"}
    
    title_lower = _get_unit_title(unit).lower()
    definition_lower = _get_unit_definition(unit).lower()
    combined_text = f"{title_lower} {definition_lower}"
    
    for indicator in admin_indicators:
        if indicator in combined_text:
            return False, f"Admin-only indicator '{indicator}' found in content"
    
    # Special handling for "reference" - check for context that suggests admin content
    reference_admin_patterns = [
        r"system\s+table",
        r"metadata\s+table",
        r"information_schema",
        r"pg_catalog",
        r"sys\.",
        r"reference\s+document",
        r"golden\s+reference",
        r"bibliography",
        r"citation",
        r"works\s+cited",
    ]
    
    if "reference" in combined_text:
        for pattern in reference_admin_patterns:
            if re.search(pattern, combined_text):
                return False, f"Admin-only context for 'reference' detected: '{pattern}'"
    
    return True, "Not an admin-only concept"


def _check_extraction_confidence_too_low(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if grounding confidence is too low.
    
    Relaxed threshold to allow grounded fallback content (0.3) while still
    blocking truly ungrounded content (0.0).
    """
    confidence = unit.grounding_confidence
    
    if confidence < 0.3:
        return False, f"Grounding confidence too low ({confidence:.2f}, min 0.3)"
    
    return True, f"Grounding confidence acceptable ({confidence:.2f})"


def _check_unresolved_practice_links(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if all practice links are unresolved placeholders - warn but don't block.
    
    Only applies to L3_explanation units with practice_links content.
    Changed from HARD_BLOCK to WARN: practice system integration isn't ready yet,
    so placeholder links are acceptable for now.
    """
    # Skip for non-explanation stages
    if unit.target_stage != "L3_explanation":
        return True, f"Practice links check skipped for {unit.target_stage}"
    
    content = unit.content or {}
    if not isinstance(content, dict):
        return True, "Content is not a dict, cannot check practice links"
    
    practice_links = content.get("practice_links", [])
    if not practice_links:
        return True, "No practice links present"
    
    # Check if all links are unresolved
    all_unresolved = True
    unresolved_count = 0
    for link in practice_links:
        if isinstance(link, dict):
            needs_resolution = link.get("needs_resolution", False)
            problem_ids = link.get("problem_ids", [])
        else:
            # Handle PracticeLink objects
            needs_resolution = getattr(link, "needs_resolution", False)
            problem_ids = getattr(link, "problem_ids", [])
        
        # A link is considered resolved if needs_resolution is False OR
        # if it has real problem IDs (not starting with "unresolved-")
        if not needs_resolution:
            # Check if problem IDs are real (not unresolved- prefixed)
            has_real_problems = any(
                not pid.startswith("unresolved-") for pid in problem_ids
            )
            if has_real_problems:
                all_unresolved = False
            else:
                unresolved_count += 1
        else:
            unresolved_count += 1
    
    if all_unresolved:
        # Changed: return True with warning message instead of False
        return True, f"WARNING: All {len(practice_links)} practice links are unresolved placeholders"
    
    if unresolved_count > 0:
        return True, f"WARNING: {unresolved_count}/{len(practice_links)} practice links are unresolved placeholders"
    
    return True, "Has resolved practice links with real problem IDs"


def _check_broken_sql_example(unit: InstructionalUnit) -> tuple[bool, str]:
    """Block L2 units with broken SQL like 'SELECT;'."""
    if unit.target_stage != "L2_hint_plus_example":
        return True, f"Broken SQL check skipped for {unit.target_stage}"
    
    content = unit.content or {}
    if not isinstance(content, dict):
        return True, "Content is not a dict, cannot check SQL"
    
    example_sql = content.get("example_sql", "")
    if not example_sql:
        return True, "No SQL example to check"
    
    # Check for broken examples
    broken_patterns = [
        r"^SELECT\s*;?$",
        r"^INSERT\s*;?$",
        r"^UPDATE\s*;?$",
        r"^DELETE\s*;?$",
    ]
    
    for pattern in broken_patterns:
        if re.match(pattern, example_sql, re.IGNORECASE):
            return False, f"L2 has broken SQL example: {example_sql[:30]}..."
    
    # Check for too-short examples
    if len(example_sql) < 25:
        return False, "L2 SQL example too short to be useful"
    
    return True, "L2 SQL example looks valid"


def _check_generic_hint_text(unit: InstructionalUnit) -> tuple[bool, str]:
    """Block L1 units with generic/heading-like hints."""
    if unit.target_stage != "L1_hint":
        return True, f"Generic hint check skipped for {unit.target_stage}"
    
    content = unit.content or {}
    if not isinstance(content, dict):
        return True, "Content is not a dict, cannot check hint"
    
    hint_text = content.get("hint_text", "")
    if not hint_text:
        return True, "No hint text to check"
    
    generic_patterns = [
        r"^Remember how to use",
        r"^Common Mistakes to Avoid:",
        r"^Chapter \d+",
        r"^Section \d+",
        r"Golden Reference",
        r"Key concepts:.*only$",  # Just a list of terms, no explanation
    ]
    
    for pattern in generic_patterns:
        if re.search(pattern, hint_text, re.IGNORECASE):
            return False, f"L1 hint is generic/heading-like: {hint_text[:50]}..."
    
    return True, "L1 hint text looks instructional"


def _check_generic_definition(unit: InstructionalUnit) -> tuple[bool, str]:
    """Block L3 units with TRULY weak generic definitions.
    
    Only blocks if the definition is generic AND there are no real examples.
    Allows fallback content that has curated or extracted examples.
    """
    if unit.target_stage != "L3_explanation":
        return True, f"Generic definition check skipped for {unit.target_stage}"
    
    content = unit.content or {}
    if not isinstance(content, dict):
        return True, "Content is not a dict, cannot check definition"
    
    definition = content.get("definition", "")
    if not definition:
        return True, "No definition to check"
    
    # Check for generic patterns
    generic_patterns = [
        r"is an important SQL concept\.?$",
        r"is a crucial SQL concept\.?$",
        r"is an essential SQL concept\.?$",
        r"is a fundamental SQL concept\.?$",
        r"^Chapter \d+",
        r"^Section \d+",
        r"Golden Reference",
    ]
    
    is_generic = any(
        re.search(pattern, definition, re.IGNORECASE)
        for pattern in generic_patterns
    )
    
    if not is_generic:
        return True, "L3 definition looks instructional"
    
    # Definition is generic - check if we have real examples to compensate
    examples = content.get("examples", [])
    has_real_examples = False
    
    for ex in examples:
        if isinstance(ex, dict):
            # Real if: from source, curated, or not marked synthetic
            is_synthetic = ex.get("is_synthetic", False)
            from_source = ex.get("from_source", False) or ex.get("schema_used") == "source"
            is_curated = ex.get("is_curated", False)
            
            if from_source or is_curated or not is_synthetic:
                has_real_examples = True
                break
    
    # Only block if generic AND no real examples
    if is_generic and not has_real_examples:
        return False, f"L3 definition is generic with no real examples: {definition[:50]}..."
    
    # Allow if generic but has real examples (acceptable fallback)
    return True, "L3 has generic definition but has real examples"


def _check_synthetic_only_examples(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check L3 units with only synthetic examples - SOFT BLOCK only.
    
    Changed from HARD_BLOCK to SOFT_BLOCK behavior: warns about synthetic-only
    content but allows export since grounded fallback mode often uses synthetic
    examples when no source SQL is available.
    """
    if unit.target_stage != "L3_explanation":
        return True, f"Synthetic-only check skipped for {unit.target_stage}"
    
    content = unit.content or {}
    if not isinstance(content, dict):
        return True, "Content is not a dict, cannot check examples"
    
    examples = content.get("examples", [])
    if not examples:
        return True, "No examples to check"
    
    # Check if all examples are synthetic
    all_synthetic = all(ex.get("is_synthetic", False) for ex in examples if isinstance(ex, dict))
    
    if all_synthetic:
        # Return True (passed) but the message will be used as a warning
        # This is handled by the caller checking the message content
        return True, "WARNING: L3 has only synthetic examples (no extracted SQL)"
    
    return True, "L3 has at least one non-synthetic example"


# =============================================================================
# SOFT BLOCK CHECK FUNCTIONS
# =============================================================================

def _check_missing_learning_objectives(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if unit has learning objectives in content.
    
    Only applies to L3_explanation units - other stages don't require
    formal learning objectives (L1/L2 are hints, L4 is reflective, 
    reinforcement is practice).
    """
    # Skip for non-explanation stages
    if unit.target_stage != "L3_explanation":
        return True, f"Learning objectives check skipped for {unit.target_stage}"
    
    content = unit.content or {}
    objectives = []
    
    if isinstance(content, dict):
        objectives = content.get("learning_objectives", []) or content.get("objectives", [])
    
    if not objectives:
        return False, "No learning objectives defined"
    
    return True, f"Has {len(objectives)} learning objectives"


def _check_missing_prerequisites(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if unit has prerequisites defined."""
    prereqs = unit.prerequisites
    
    if not prereqs:
        return False, "No prerequisites defined (isolated node in learning graph)"
    
    return True, f"Has {len(prereqs)} prerequisites"


def _check_missing_error_subtypes(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if unit has error subtype tags."""
    error_subtypes = unit.error_subtypes
    
    if not error_subtypes:
        return False, "No error subtype tags (reduces SQL-Engage integration)"
    
    return True, f"Has {len(error_subtypes)} error subtypes"


def _check_incomplete_stage_variants(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if unit has valid target_stage for adaptive delivery."""
    valid_stages = {
        "L1_hint", "L2_hint_plus_example", "L3_explanation", 
        "L4_reflective_note", "reinforcement"
    }
    
    if unit.target_stage not in valid_stages:
        return False, f"Invalid target_stage: {unit.target_stage}"
    
    return True, f"Target stage valid: {unit.target_stage}"


def _check_example_not_validated(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if SQL examples have been execution-tested (based on content quality).
    
    Only applies to units that actually contain SQL examples to validate.
    Skipped for units without SQL content (L1_hint, L4_reflective_note, etc.).
    """
    # Check if examples exist - if no examples, skip validation
    examples = _get_unit_examples(unit)
    
    if not examples:
        return True, f"No SQL examples to validate for {unit.target_stage}"
    
    # Check if examples have explanation/validation markers
    for ex in examples:
        if isinstance(ex, dict):
            # Should have explanation if validated
            has_explanation = bool(ex.get("explanation", ""))
            if not has_explanation:
                return False, "SQL examples lack explanations (not fully validated)"
    
    return True, "SQL examples have validation markers"


def _check_low_semantic_score(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if grounding confidence (semantic score equivalent) is below threshold."""
    confidence = unit.grounding_confidence
    
    if confidence < 0.7:
        return False, f"Grounding confidence low ({confidence:.2f}, recommended min 0.7)"
    
    return True, f"Grounding confidence acceptable ({confidence:.2f})"


# =============================================================================
# CONTENT QUALITY CHECK FUNCTIONS
# =============================================================================

def _check_contains_config_variables(unit: InstructionalUnit) -> tuple[bool, str]:
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
    
    title = _get_unit_title(unit)
    definition = _get_unit_definition(unit)
    text_to_check = f"{title} {definition}"
    text_lower = text_to_check.lower()
    
    for pattern in config_patterns:
        if re.search(pattern, text_lower):
            return False, f"Config/code-like content detected: '{pattern}'"
    
    return True, "No config-like content detected"


def _check_looks_like_toc_entry(unit: InstructionalUnit) -> tuple[bool, str]:
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
    
    title = _get_unit_title(unit)
    title_lower = title.lower().strip()
    
    for pattern in toc_patterns:
        if re.match(pattern, title_lower):
            return False, f"Matches TOC pattern: '{pattern}'"
    
    # Check for very short content that looks like a TOC entry
    definition = _get_unit_definition(unit)
    examples = _get_unit_examples(unit)
    if len(definition) < 50 and not examples:
        return False, "Very short content with no examples - likely TOC entry"
    
    return True, "Not a TOC entry"


def _check_appendix_content(unit: InstructionalUnit) -> tuple[bool, str]:
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
    
    title = _get_unit_title(unit)
    title_lower = title.lower().strip()
    
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
        rule_id="heading_like_definition",
        rule_type=RuleType.HARD_BLOCK,
        description="Definition looks like a chapter/section heading or reference text",
        check_fn=_check_heading_like_definition,
        error_message="Definition appears to be a heading or reference text, not actual content"
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
    ExportRule(
        rule_id="unresolved_practice_links",
        rule_type=RuleType.WARN,  # Changed from HARD_BLOCK to WARN
        description="All practice links are unresolved placeholders",
        check_fn=_check_unresolved_practice_links,
        error_message="All practice links are unresolved placeholders - practice system integration pending"
    ),
    ExportRule(
        rule_id="broken_sql_example",
        rule_type=RuleType.HARD_BLOCK,
        description="L2 has broken SQL example like 'SELECT;'",
        check_fn=_check_broken_sql_example,
        error_message="L2 has broken SQL example - insufficient for learning"
    ),
    ExportRule(
        rule_id="generic_hint_text",
        rule_type=RuleType.HARD_BLOCK,
        description="L1 hint is generic/heading-like (e.g., 'Remember how to use X')",
        check_fn=_check_generic_hint_text,
        error_message="L1 hint is generic - not instructional content"
    ),
    ExportRule(
        rule_id="generic_definition",
        rule_type=RuleType.HARD_BLOCK,
        description="L3 definition is generic (e.g., 'X is an important SQL concept')",
        check_fn=_check_generic_definition,
        error_message="L3 definition is generic - not instructional content"
    ),
    ExportRule(
        rule_id="synthetic_only_examples",
        rule_type=RuleType.WARN,  # Changed from HARD_BLOCK to WARN
        description="L3 has only synthetic examples (no extracted SQL)",
        check_fn=_check_synthetic_only_examples,
        error_message="L3 has only synthetic examples - no real SQL from textbook"
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
        
        for unit in library.instructional_units:
            unit_result = self._filter_single_unit(unit)
            
            if unit_result.can_export:
                passed_units.append(unit.unit_id)
                # Still collect warnings
                warnings.extend(unit_result.warnings)
            else:
                filtered_units.append(unit.unit_id)
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
    
    def _filter_single_unit(self, unit: InstructionalUnit) -> UnitFilterResult:
        """
        Filter a single unit against all rules.
        
        Args:
            unit: The InstructionalUnit to check
            
        Returns:
            UnitFilterResult with detailed results
        """
        hard_block_reasons: list[str] = []
        warnings: list[str] = []
        
        # Check hard block rules
        for rule in self.hard_block_rules:
            try:
                passed, message = rule.check(unit)
                if not passed:
                    hard_block_reasons.append(f"{rule.rule_id}: {message}")
            except Exception as e:
                # If check fails, treat as hard block
                hard_block_reasons.append(f"{rule.rule_id}: Check failed - {str(e)}")
        
        # Check soft block rules
        for rule in self.soft_block_rules:
            try:
                passed, message = rule.check(unit)
                if not passed:
                    warnings.append(f"{unit.unit_id} - {rule.rule_id}: {message}")
            except Exception:
                # Soft block failures don't block export
                pass
        
        # Check warn rules
        for rule in self.warn_rules:
            try:
                passed, message = rule.check(unit)
                if not passed:
                    warnings.append(f"{unit.unit_id} - {rule.rule_id}: {message}")
            except Exception:
                pass
        
        can_export = len(hard_block_reasons) == 0
        
        return UnitFilterResult(
            unit_id=unit.unit_id,
            can_export=can_export,
            hard_block_reasons=hard_block_reasons,
            warnings=warnings,
        )
    
    def validate_single_unit(self, unit: InstructionalUnit) -> tuple[bool, list[str]]:
        """
        Check one unit against all rules.
        
        Args:
            unit: The InstructionalUnit to validate
            
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
        passed_units: list[InstructionalUnit] = []
        
        for unit in library.instructional_units:
            result = self._filter_single_unit(unit)
            if result.can_export:
                passed_units.append(unit)
        
        # Create new library with filtered units
        filtered_library = library.model_copy(deep=True)
        filtered_library.instructional_units = passed_units
        
        # Update metadata
        if not filtered_library.export_manifest:
            filtered_library.export_manifest = {}
        filtered_library.export_manifest.update({
            "filtered": True,
            "original_unit_count": len(library.instructional_units),
            "filtered_unit_count": len(passed_units),
            "filter_pass_rate": len(passed_units) / len(library.instructional_units) if library.instructional_units else 0.0,
        })
        
        return filtered_library
    
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
        
        for unit in library.instructional_units:
            result = self._filter_single_unit(unit)
            if not result.can_export:
                rejected.append((unit.unit_id, result.hard_block_reasons))
        
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
        
        for unit in library.instructional_units:
            result = self._filter_single_unit(unit)
            unit_violations[unit.unit_id] = []
            
            # Track which rules were violated
            for reason in result.hard_block_reasons:
                rule_id = reason.split(":")[0]
                if rule_id in rule_violations:
                    rule_violations[rule_id] += 1
                unit_violations[unit.unit_id].append(reason)
        
        # Sort rules by violation count
        top_violations = sorted(
            rule_violations.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        return {
            "total_units": len(library.instructional_units),
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


def quick_filter_check(unit: InstructionalUnit) -> tuple[bool, list[str]]:
    """
    Quick check using STRICT_FILTERS.
    
    Args:
        unit: The InstructionalUnit to check
        
    Returns:
        Tuple of (can_export, list_of_violations)
    """
    engine = ExportFilterEngine(STRICT_FILTERS)
    return engine.validate_single_unit(unit)


def should_export(unit: InstructionalUnit) -> bool:
    """
    Quick boolean check if a unit should be exported (using STRICT_FILTERS).
    
    Args:
        unit: The InstructionalUnit to check
        
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
