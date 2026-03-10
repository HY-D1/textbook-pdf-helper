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
        student_ready_passed: Whether all units passed student-ready checks
        blocked_by_student_ready: List of unit IDs blocked by student-ready rules
        quality_warnings: List of quality warnings even for passed units
        library_validation: Library-level validation results
    """
    can_export: bool
    blocked_by: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    filtered_units: list[str] = field(default_factory=list)
    passed_units: list[str] = field(default_factory=list)
    student_ready_passed: bool = field(default=True)
    blocked_by_student_ready: list[str] = field(default_factory=list)
    quality_warnings: list[str] = field(default_factory=list)
    library_validation: dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_units(self) -> int:
        """Total number of units processed."""
        return len(self.filtered_units) + len(self.passed_units)
    
    @property
    def pass_rate(self) -> float:
        """Percentage of units that passed."""
        total = self.total_units
        return len(self.passed_units) / total if total > 0 else 0.0
    
    @property
    def student_ready_pass_rate(self) -> float:
        """Percentage of units that passed student-ready checks."""
        total = self.total_units
        passed = total - len(self.blocked_by_student_ready)
        return passed / total if total > 0 else 0.0


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
    - Reference document text ("Golden Reference...", "Reference Manual")
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
    definition_stripped = definition.strip()
    
    # REJECT: Chapter/section patterns with colon or hyphen
    if re.match(r'^Chapter\s+\d+[:\-]', definition, re.IGNORECASE):
        return False, f"Definition appears to be a chapter title: {definition[:50]}"
    
    if re.match(r'^(Chapter|Section|Unit|Module|Lesson|Part)\s+\d+[:\-]', definition, re.IGNORECASE):
        return False, f"Definition appears to be a heading: {definition[:50]}"
    
    # REJECT: Just "Chapter X" or "Section X" without content
    if re.match(r'^(Chapter|Section|Unit|Module|Lesson|Part)\s+\d+[a-z]?$', definition_stripped, re.IGNORECASE):
        return False, f"Definition is just a heading label: {definition[:50]}"
    
    # REJECT: Reference Manual patterns
    if 'reference manual' in definition_lower:
        return False, "Definition contains 'reference manual' - appears to be reference text"
    
    # REJECT: Golden Reference / Reference Document patterns
    if 'golden reference' in definition_lower:
        return False, "Definition contains 'golden reference' - appears to be reference text"
    
    if 'reference document' in definition_lower:
        return False, "Definition contains 'reference document' - appears to be reference text"
    
    # REJECT: "References" or "Bibliography" as standalone
    if re.match(r'^References?$', definition_stripped, re.IGNORECASE):
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
    """Block units with broken SQL like 'SELECT;' (verb-only SQL).
    
    Applies to all stages that contain SQL examples (L2_hint_plus_example, L3_explanation).
    Blocks SQL that contains:
    - "SELECT;", "INSERT;", "UPDATE;", "DELETE;" (verb-only statements)
    - Any SQL statement that is just the verb followed by semicolon
    """
    # Check applicable stages
    applicable_stages = {"L2_hint_plus_example", "L3_explanation"}
    if unit.target_stage not in applicable_stages:
        return True, f"Broken SQL check skipped for {unit.target_stage}"
    
    content = unit.content or {}
    if not isinstance(content, dict):
        return True, "Content is not a dict, cannot check SQL"
    
    # Collect all SQL to check
    sql_statements: list[str] = []
    
    # L2 style: single example_sql field
    if "example_sql" in content:
        sql_statements.append(content["example_sql"])
    
    # L3 style: list of SQLExample objects
    examples = content.get("examples", [])
    if isinstance(examples, list):
        for ex in examples:
            if isinstance(ex, dict):
                sql = ex.get("sql", "") or ex.get("query", "")
                if sql:
                    sql_statements.append(sql)
    
    if not sql_statements:
        return True, "No SQL examples to check"
    
    # Check for broken/verb-only SQL
    # Pattern matches: SELECT; INSERT; UPDATE; DELETE; (with optional whitespace)
    broken_patterns = [
        r"^\s*SELECT\s*;\s*$",
        r"^\s*INSERT\s*;\s*$",
        r"^\s*UPDATE\s*;\s*$",
        r"^\s*DELETE\s*;\s*$",
    ]
    
    for i, sql in enumerate(sql_statements):
        if not sql or not isinstance(sql, str):
            continue
            
        for pattern in broken_patterns:
            if re.match(pattern, sql, re.IGNORECASE):
                return False, f"Broken SQL (verb-only): {sql[:40]}..."
        
        # Check for too-short examples
        if len(sql.strip()) < 25:
            return False, f"SQL example too short to be useful: {sql[:40]}..."
    
    return True, "All SQL examples look valid"


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
# STUDENT-READY CHECK FUNCTIONS (Strict Mode)
# =============================================================================


def _check_fallback_unit(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if unit is a fallback unit (is_fallback=True in metadata).
    
    HARD BLOCK for student-ready mode - fallback units indicate extraction failures.
    """
    content = unit.content or {}
    if not isinstance(content, dict):
        return True, "Content is not a dict, cannot check fallback status"
    
    # Check for fallback flag in content or metadata
    metadata = content.get("_metadata", {})
    is_fallback = content.get("is_fallback", False) or metadata.get("is_fallback", False)
    
    if is_fallback:
        return False, "Unit is a fallback unit (extraction failed)"
    
    return True, "Unit is not a fallback"


def _check_offbook_curated_concept(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if unit has source_mode == 'curated_only_offbook' or offbook_concept=True.
    
    HARD BLOCK for student-ready mode - off-book concepts without source grounding
    should not be exported to students.
    """
    content = unit.content or {}
    if not isinstance(content, dict):
        return True, "Content is not a dict, cannot check source mode"
    
    # Check for source_mode in content or metadata
    metadata = content.get("_metadata", {})
    source_mode = content.get("source_mode", "") or metadata.get("source_mode", "")
    
    if source_mode == "curated_only_offbook":
        return False, "Off-book curated-only concept (no source grounding)"
    
    # Also check for explicit offbook_concept flag
    offbook_concept = content.get("offbook_concept", False) or metadata.get("offbook_concept", False)
    if offbook_concept:
        return False, "Off-book concept not from source textbook"
    
    return True, "Concept from source material"


def _check_placeholder_practice_links_strict(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check for placeholder practice links with needs_resolution=true.
    
    HARD BLOCK for student-ready mode - blocks if ANY practice link has
    needs_resolution=True, indicating unresolved placeholder links.
    """
    # Only check L3 explanation units
    if unit.target_stage != "L3_explanation":
        return True, f"Practice link check skipped for {unit.target_stage}"
    
    content = unit.content or {}
    if not isinstance(content, dict):
        return True, "Content is not a dict, cannot check practice links"
    
    practice_links = content.get("practice_links", [])
    if not practice_links:
        return True, "No practice links present"
    
    # Track placeholder status
    needs_resolution_count = 0
    
    for link in practice_links:
        if isinstance(link, dict):
            needs_resolution = link.get("needs_resolution", False)
        else:
            needs_resolution = getattr(link, "needs_resolution", False)
        
        if needs_resolution:
            needs_resolution_count += 1
    
    if needs_resolution_count > 0:
        return False, f"Practice links with needs_resolution=true ({needs_resolution_count} links)"
    
    return True, "All practice links are resolved"


def _check_default_example_no_source_evidence(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if L2 unit uses default example with no source evidence.
    
    HARD BLOCK for student-ready mode - blocks if L2 unit uses a default/generic
    example AND has no proper source evidence spans.
    """
    # Only check L2 units
    if unit.target_stage != "L2_hint_plus_example":
        return True, f"Default example check skipped for {unit.target_stage}"
    
    content = unit.content or {}
    if not isinstance(content, dict):
        return True, "Content is not a dict, cannot check example"
    
    # Check if using default example
    metadata = content.get("_metadata", {})
    used_default = content.get("_used_default_example", False) or metadata.get("_used_default_example", False)
    
    if not used_default:
        return True, "L2 unit does not use default example"
    
    # Check for source evidence
    if not unit.evidence_spans or len(unit.evidence_spans) < 2:
        return False, "L2 uses default example with insufficient source evidence"
    
    return True, "L2 has default example but has source evidence"


def _check_placeholder_practice_links(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check for placeholder practice links - HARD BLOCK for student-ready.
    
    Blocks units where practice_links contains any with:
    - needs_resolution=True
    - IDs starting with "unresolved-" or "problem-" (placeholder pattern)
    - All problems have is_placeholder=true in metadata
    """
    # Only check L3 explanation units
    if unit.target_stage != "L3_explanation":
        return True, f"Practice link check skipped for {unit.target_stage}"
    
    content = unit.content or {}
    if not isinstance(content, dict):
        return True, "Content is not a dict, cannot check practice links"
    
    practice_links = content.get("practice_links", [])
    if not practice_links:
        return True, "No practice links present"
    
    # Track placeholder status for all links
    total_problem_ids = 0
    placeholder_count = 0
    unresolved_count = 0
    
    # Check for any placeholder links
    for link in practice_links:
        if isinstance(link, dict):
            needs_resolution = link.get("needs_resolution", False)
            problem_ids = link.get("problem_ids", [])
            metadata = link.get("metadata", {})
        else:
            # Handle PracticeLink objects
            needs_resolution = getattr(link, "needs_resolution", False)
            problem_ids = getattr(link, "problem_ids", [])
            metadata = getattr(link, "metadata", {}) or {}
        
        total_problem_ids += len(problem_ids)
        
        # Check if this link needs resolution
        if needs_resolution:
            unresolved_count += len(problem_ids)
        
        # Check metadata for v2.0 format placeholder flag
        problems_meta = metadata.get("problems", []) if isinstance(metadata, dict) else []
        for problem_meta in problems_meta:
            if isinstance(problem_meta, dict) and problem_meta.get("is_placeholder", False):
                placeholder_count += 1
        
        # Check for placeholder problem IDs
        for pid in problem_ids:
            if pid.startswith("unresolved-"):
                unresolved_count += 1
            elif pid.startswith("problem-"):
                placeholder_count += 1
    
    # If all problem IDs are placeholders/unresolved, this is a hard block
    if total_problem_ids > 0 and (placeholder_count + unresolved_count) >= total_problem_ids:
        return False, f"Student-ready export cannot contain placeholder practice links ({placeholder_count} placeholders, {unresolved_count} unresolved)"
    
    if placeholder_count > 0 or unresolved_count > 0:
        return True, f"WARNING: {placeholder_count} placeholder(s) and {unresolved_count} unresolved link(s) found"
    
    return True, "All practice links are resolved"


def _check_default_only_l2_example(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if L2 unit uses default example instead of concept-appropriate SQL.
    
    Blocks L2 units with _used_default_example=True in metadata.
    """
    # Only check L2 units
    if unit.target_stage != "L2_hint_plus_example":
        return True, f"Default example check skipped for {unit.target_stage}"
    
    content = unit.content or {}
    if not isinstance(content, dict):
        return True, "Content is not a dict, cannot check metadata"
    
    # Check for default example flag in content or metadata
    metadata = content.get("_metadata", {})
    used_default = content.get("_used_default_example", False) or metadata.get("_used_default_example", False)
    
    if used_default:
        return False, "L2 unit uses generic default example instead of concept-appropriate SQL"
    
    return True, "L2 unit has concept-appropriate SQL example"


def _check_synthetic_only_l3(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if L3 explanation is purely synthetic without source grounding.
    
    Blocks L3 units with _content_source="synthetic" and no source evidence spans.
    """
    # Only check L3 units
    if unit.target_stage != "L3_explanation":
        return True, f"Synthetic L3 check skipped for {unit.target_stage}"
    
    content = unit.content or {}
    if not isinstance(content, dict):
        return True, "Content is not a dict, cannot check source"
    
    # Check if content is marked as synthetic
    metadata = content.get("_metadata", {})
    content_source = content.get("_content_source", "") or metadata.get("content_source", "")
    
    if content_source == "synthetic":
        # Check for source evidence spans
        if not unit.evidence_spans:
            return False, "L3 explanation is purely synthetic with no source evidence spans"
        # Also check grounding confidence
        if unit.grounding_confidence < 0.3:
            return False, "L3 explanation has low grounding confidence (< 0.3)"
    
    return True, "L3 explanation has source grounding"


# Core concepts that require L3 explanation
CORE_CONCEPTS = {
    "select-basic",
    "where-clause", 
    "joins",
    "join-inner",
    "join-outer",
    "join-left",
    "join-right",
    "join-cross",
    "join-self",
    "group-by",
    "aggregation",
    "order-by",
    "limit-offset",
}


def _check_missing_l3_for_core_concepts(library: UnitLibraryExport) -> list[tuple[str, str]]:
    """Check if core concepts are missing required L3 explanation.
    
    Returns list of (concept_id, message) tuples for blocked concepts.
    """
    violations = []
    
    # Get all concepts that have L3 units
    concepts_with_l3 = set()
    for unit in library.instructional_units:
        if unit.target_stage == "L3_explanation":
            concepts_with_l3.add(unit.concept_id)
    
    # Check which core concepts are missing L3
    for concept_id in CORE_CONCEPTS:
        if concept_id not in concepts_with_l3:
            # Check if this concept exists in the library at all
            has_any_unit = any(u.concept_id == concept_id for u in library.instructional_units)
            if has_any_unit:
                violations.append((
                    concept_id, 
                    f"Core concept '{concept_id}' missing required L3 explanation"
                ))
    
    return violations


def _check_low_quality_score(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if unit quality score is below threshold - SOFT BLOCK.
    
    Warns on units with quality score < 0.7 but allows export with flag.
    """
    # Get quality score from content metadata
    content = unit.content or {}
    if not isinstance(content, dict):
        return True, "Cannot check quality score"
    
    metadata = content.get("_metadata", {})
    quality_score = content.get("_quality_score", 0.0) or metadata.get("quality_score", 0.0)
    
    # Also consider grounding confidence as a quality indicator
    if quality_score == 0.0 and unit.grounding_confidence > 0:
        quality_score = unit.grounding_confidence
    
    if quality_score < 0.7:
        return True, f"WARNING: Unit quality score ({quality_score:.2f}) below recommended threshold (0.7)"
    
    return True, f"Unit quality score acceptable ({quality_score:.2f})"


def _check_weak_curated_fallback(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if curated fallback content is just placeholder text.
    
    Blocks curated content that is just a heading/title (length < 20 chars).
    """
    content = unit.content or {}
    if not isinstance(content, dict):
        return True, "Content is not a dict, cannot check curated fallback"
    
    # Check if this is curated fallback
    metadata = content.get("_metadata", {})
    is_curated = content.get("_used_curated_fallback", False) or metadata.get("content_source") == "curated"
    
    if not is_curated:
        return True, "Not curated fallback content"
    
    # Get the content to check length
    definition = content.get("definition", "")
    if not definition:
        # Try other content fields
        definition = content.get("explanation", "") or content.get("description", "")
    
    if len(definition.strip()) < 20:
        return False, f"Curated fallback content appears to be placeholder text ({len(definition)} chars)"
    
    return True, "Curated fallback content has sufficient length"


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


def _check_empty_why_it_matters(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if why_it_matters field is missing or too short.
    
    Only applies to L3_explanation units. Requires at least 30 characters
    to be considered meaningful instructional content.
    """
    # Skip for non-explanation stages
    if unit.target_stage != "L3_explanation":
        return True, f"why_it_matters check skipped for {unit.target_stage}"
    
    content = unit.content or {}
    if not isinstance(content, dict):
        return True, "Content is not a dict, cannot check why_it_matters"
    
    # Get why_it_matters from various possible field names
    why_it_matters = (
        content.get("why_it_matters", "") or 
        content.get("why_it_matters", "") or
        content.get("importance", "") or
        content.get("relevance", "")
    )
    
    if not why_it_matters or not isinstance(why_it_matters, str):
        return False, "why_it_matters is missing or empty"
    
    why_stripped = why_it_matters.strip()
    if len(why_stripped) < 30:
        return False, f"why_it_matters too short ({len(why_stripped)} chars, min 30)"
    
    return True, f"why_it_matters length acceptable ({len(why_stripped)} chars)"


def _check_heading_like_why_it_matters(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if why_it_matters looks like a heading instead of instructional content.
    
    Rejects content that starts with:
    - "How to..." (procedure heading)
    - "Chapter X..." (chapter title)
    - "Section X..." (section heading)
    - All-caps text (heading)
    - Very short text (title-like)
    
    Only applies to L3_explanation units.
    """
    # Skip for non-explanation stages
    if unit.target_stage != "L3_explanation":
        return True, f"why_it_matters heading check skipped for {unit.target_stage}"
    
    content = unit.content or {}
    if not isinstance(content, dict):
        return True, "Content is not a dict, cannot check why_it_matters"
    
    why_it_matters = (
        content.get("why_it_matters", "") or 
        content.get("importance", "") or
        content.get("relevance", "")
    )
    
    if not why_it_matters or not isinstance(why_it_matters, str):
        return True, "No why_it_matters to check"
    
    why_stripped = why_it_matters.strip()
    why_lower = why_stripped.lower()
    
    # REJECT: Starts with "How to" (procedure heading)
    if re.match(r'^How\s+to\s+', why_stripped, re.IGNORECASE):
        return False, f"why_it_matters is heading-like (starts with 'How to'): {why_stripped[:50]}..."
    
    # REJECT: Chapter/section patterns
    if re.match(r'^(Chapter|Section|Unit|Module|Lesson|Part)\s+\d+', why_stripped, re.IGNORECASE):
        return False, f"why_it_matters is heading-like (chapter/section): {why_stripped[:50]}..."
    
    # REJECT: All-caps (likely a heading)
    if why_stripped.isupper():
        return False, "why_it_matters is all uppercase (heading-like)"
    
    # REJECT: Title case without small words (likely a heading)
    words = why_stripped.split()
    if len(words) > 1 and len(words) < 10:
        content_words = [w for w in words if w.isalpha()]
        if content_words and all(w[0].isupper() for w in content_words):
            small_words = ['a', 'an', 'the', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'is', 'are', 'with', 'by', 'as']
            if not any(w.lower() in small_words for w in words):
                return False, f"why_it_matters appears to be title-case heading: {why_stripped[:50]}..."
    
    # REJECT: Ends with section markers
    if re.search(r'\s+-\s+(Examples|Overview|Summary|Details)$', why_stripped, re.IGNORECASE):
        return False, f"why_it_matters ends with section marker: {why_stripped[:50]}..."
    
    return True, "why_it_matters appears to be instructional content"


def _check_insufficient_evidence_spans(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if unit has sufficient evidence spans for source grounding.
    
    Requires at least 2 evidence spans for strong source grounding.
    Curated content is exempt from this check.
    """
    # Curated content is always considered well-grounded
    content = unit.content or {}
    if isinstance(content, dict):
        metadata = content.get("_metadata", {})
        if metadata.get("content_source") == "curated":
            return True, "Curated content - evidence requirement waived"
    
    evidence_spans = unit.evidence_spans or []
    
    if len(evidence_spans) < 2:
        return False, f"Insufficient evidence spans ({len(evidence_spans)}, need 2+)"
    
    return True, f"Sufficient evidence spans ({len(evidence_spans)})"


def _check_ontology_fallback_definition(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if L3 unit uses ontology fallback definition (not extracted from source).
    
    Blocks L3 units where the definition came from ontology fallback rather than
    being extracted from the textbook source material. This ensures student-facing
    content is grounded in actual textbook content.
    
    Only applies to L3_explanation units.
    """
    # Skip for non-explanation stages
    if unit.target_stage != "L3_explanation":
        return True, f"Ontology fallback check skipped for {unit.target_stage}"
    
    content = unit.content or {}
    if not isinstance(content, dict):
        return True, "Content is not a dict, cannot check definition source"
    
    # Get metadata
    metadata = content.get("_metadata", {})
    
    # Check for definition source markers
    definition_source = metadata.get("definition_source", "")
    content_source = metadata.get("content_source", "")
    
    # Block if definition is from ontology fallback
    if definition_source in ("ontology", "default"):
        return False, f"L3 definition is from {definition_source} fallback, not extracted from source"
    
    # Also check for curated content (which is acceptable)
    if content_source == "curated":
        return True, "Curated content - ontology fallback check waived"
    
    # Check if definition has generic fallback patterns
    definition = _get_unit_definition(unit)
    generic_patterns = [
        r"is an important SQL concept\.?$",
        r"is a crucial SQL concept\.?$",
        r"is an essential SQL concept\.?$",
        r"is a fundamental SQL concept\.?$",
    ]
    
    is_generic = any(
        re.search(pattern, definition, re.IGNORECASE)
        for pattern in generic_patterns
    )
    
    if is_generic:
        # Check if we have real examples to compensate
        examples = _get_unit_examples(unit)
        has_real_examples = any(
            not ex.get("is_synthetic", False) if isinstance(ex, dict) else True
            for ex in examples
        )
        
        if not has_real_examples:
            return False, "L3 has generic ontology fallback definition with no real examples"
    
    return True, "L3 definition appears to be extracted or curated"


def _check_generic_boilerplate(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check for generic boilerplate text that shouldn't be in student content.
    
    Blocks content containing:
    - "Golden Reference Document" or similar test strings
    - Template/example text that wasn't replaced
    """
    content = unit.content or {}
    if not isinstance(content, dict):
        return True, "Content is not a dict, cannot check for boilerplate"
    
    # Collect all text content to check
    text_parts = []
    
    # Check common content fields
    for field in ["definition", "explanation", "description", "why_it_matters", "title"]:
        if field in content and isinstance(content[field], str):
            text_parts.append(content[field])
    
    # Check hint text for L1
    if "hint_text" in content and isinstance(content["hint_text"], str):
        text_parts.append(content["hint_text"])
    
    # Check reflective content for L4
    if "reflective_content" in content and isinstance(content["reflective_content"], str):
        text_parts.append(content["reflective_content"])
    
    all_text = " ".join(text_parts).lower()
    
    # Boilerplate patterns that indicate test/template content
    boilerplate_patterns = [
        ("golden reference document", "Contains 'Golden Reference Document' - test/template content"),
        ("golden reference", "Contains 'Golden Reference' - appears to be test content"),
        ("this is a placeholder", "Contains placeholder text"),
        ("insert content here", "Contains template text 'insert content here'"),
        ("your content here", "Contains template text 'your content here'"),
        ("lorem ipsum", "Contains 'lorem ipsum' placeholder text"),
        ("example content", "Contains 'example content' - may be template text"),
        ("sample text", "Contains 'sample text' - may be template text"),
    ]
    
    for pattern, message in boilerplate_patterns:
        if pattern in all_text:
            return False, message
    
    return True, "No generic boilerplate detected"


# Cache for tracking reflective summaries across concepts (for repeated boilerplate detection)
_reflective_summary_cache: dict[str, list[str]] = {"summaries": [], "concepts": []}


def _check_repeated_boilerplate(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if the same reflective summary is used across multiple concepts.
    
    This indicates copy-paste boilerplate rather than concept-specific content.
    Uses a simple cache to detect duplicates across units.
    """
    content = unit.content or {}
    if not isinstance(content, dict):
        return True, "Content is not a dict, cannot check for repeated boilerplate"
    
    # Only check L4 reflective notes and units with summary content
    reflective_content = ""
    
    if unit.target_stage == "L4_reflective_note":
        reflective_content = content.get("reflective_content", "") or content.get("summary", "")
    elif "summary" in content:
        reflective_content = content.get("summary", "")
    elif "reflective_summary" in content:
        reflective_content = content.get("reflective_summary", "")
    
    if not reflective_content or len(reflective_content) < 20:
        return True, "No reflective content to check"
    
    # Normalize the content for comparison (lowercase, strip whitespace)
    normalized = reflective_content.strip().lower()
    
    # Check if we've seen this exact content before for a different concept
    cache = _reflective_summary_cache
    
    for i, existing in enumerate(cache["summaries"]):
        # If content matches and it's for a different concept
        if existing == normalized and cache["concepts"][i] != unit.concept_id:
            return False, f"Reflective summary appears to be copy-pasted from concept '{cache['concepts'][i]}'"
    
    # Add to cache
    cache["summaries"].append(normalized)
    cache["concepts"].append(unit.concept_id)
    
    return True, "Reflective content appears to be concept-specific"


def _check_wrong_example_for_concept(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check if SQL examples match the concept they are teaching.
    
    Detects mismatches like:
    - SELECT examples for CREATE TABLE concept
    - JOIN examples for WHERE clause concept
    
    Only applies to L2 and L3 stages that contain SQL examples.
    """
    # Check applicable stages
    applicable_stages = {"L2_hint_plus_example", "L3_explanation"}
    if unit.target_stage not in applicable_stages:
        return True, f"Example-concept mismatch check skipped for {unit.target_stage}"
    
    content = unit.content or {}
    if not isinstance(content, dict):
        return True, "Content is not a dict, cannot check examples"
    
    concept_id = unit.concept_id.lower()
    
    # Collect all SQL examples
    sql_statements: list[str] = []
    
    # L2 style
    if "example_sql" in content and isinstance(content["example_sql"], str):
        sql_statements.append(content["example_sql"])
    
    # L3 style
    examples = content.get("examples", [])
    if isinstance(examples, list):
        for ex in examples:
            if isinstance(ex, dict):
                sql = ex.get("sql", "") or ex.get("query", "")
                if sql:
                    sql_statements.append(sql)
    
    if not sql_statements:
        return True, "No SQL examples to check"
    
    # Define concept-SQL verb mappings (concept substring -> required SQL verb)
    concept_verb_mappings = {
        # DDL concepts
        "create-table": ["CREATE TABLE"],
        "create-index": ["CREATE INDEX"],
        "create-view": ["CREATE VIEW"],
        "alter-table": ["ALTER TABLE"],
        "drop-table": ["DROP TABLE"],
        "drop-index": ["DROP INDEX"],
        
        # DML concepts
        "insert": ["INSERT"],
        "update": ["UPDATE"],
        "delete": ["DELETE"],
        "merge": ["MERGE"],
        "upsert": ["UPSERT", "INSERT", "UPDATE"],
        
        # DQL concepts  
        "select": ["SELECT"],
        "where": ["SELECT"],  # WHERE is part of SELECT
        "join": ["SELECT", "JOIN"],
        "inner-join": ["SELECT", "JOIN"],
        "left-join": ["SELECT", "JOIN"],
        "right-join": ["SELECT", "JOIN"],
        "outer-join": ["SELECT", "JOIN"],
        "cross-join": ["SELECT", "JOIN"],
        "self-join": ["SELECT", "JOIN"],
        "group-by": ["SELECT"],
        "order-by": ["SELECT"],
        "having": ["SELECT"],
        "limit": ["SELECT"],
        "offset": ["SELECT"],
        "subquery": ["SELECT"],
        "cte": ["WITH"],
        "common-table-expression": ["WITH"],
        "union": ["SELECT", "UNION"],
        "intersect": ["SELECT", "INTERSECT"],
        "except": ["SELECT", "EXCEPT"],
        
        # Transaction concepts
        "transaction": ["BEGIN", "COMMIT", "ROLLBACK", "START TRANSACTION"],
        "commit": ["COMMIT"],
        "rollback": ["ROLLBACK"],
        
        # Other
        "grant": ["GRANT"],
        "revoke": ["REVOKE"],
    }
    
    # Find matching concept pattern
    required_verbs: list[str] = []
    for concept_pattern, verbs in concept_verb_mappings.items():
        if concept_pattern in concept_id:
            required_verbs = verbs
            break
    
    if not required_verbs:
        # Concept doesn't have a specific verb requirement
        return True, f"No specific SQL verb requirement for concept '{concept_id}'"
    
    # Check each SQL example
    for sql in sql_statements:
        sql_upper = sql.strip().upper()
        
        # Skip if SQL contains any of the required verbs
        if not any(verb in sql_upper for verb in required_verbs):
            # Special case: WHERE clause examples might not have WHERE if they're showing
            # the before/after or common mistakes
            if "where" in concept_id and "SELECT" in sql_upper:
                continue  # SELECT without explicit WHERE might be intentional
            
            return False, f"SQL example doesn't match concept '{concept_id}': {sql[:50]}... (expected {required_verbs})"
    
    return True, f"SQL examples match concept '{concept_id}'"


def _check_placeholder_practice_ids(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check for placeholder practice IDs in student_ready mode.
    
    HARD BLOCK for any ID starting with:
    - "unresolved-"
    - "placeholder"
    
    Also checks for IDs containing "placeholder" substring.
    """
    content = unit.content or {}
    if not isinstance(content, dict):
        return True, "Content is not a dict, cannot check practice IDs"
    
    # Check practice_links
    practice_links = content.get("practice_links", [])
    if practice_links and isinstance(practice_links, list):
        for link in practice_links:
            problem_ids = []
            if isinstance(link, dict):
                problem_ids = link.get("problem_ids", [])
            else:
                problem_ids = getattr(link, "problem_ids", [])
            
            if isinstance(problem_ids, list):
                for pid in problem_ids:
                    if isinstance(pid, str):
                        if pid.startswith("unresolved-"):
                            return False, f"Placeholder practice ID found: {pid}"
                        if pid.startswith("placeholder") or "placeholder" in pid.lower():
                            return False, f"Placeholder practice ID found: {pid}"
    
    # Check for any field that might contain problem/references IDs
    for field in ["problem_ids", "practice_ids", "exercise_ids"]:
        if field in content:
            ids = content[field]
            if isinstance(ids, list):
                for pid in ids:
                    if isinstance(pid, str):
                        if pid.startswith("unresolved-"):
                            return False, f"Placeholder {field} found: {pid}"
                        if pid.startswith("placeholder") or "placeholder" in pid.lower():
                            return False, f"Placeholder {field} found: {pid}"
    
    return True, "No placeholder practice IDs found"


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

# Build STRICT_FILTERS with deduplication (some rules may already exist in HARD_BLOCK_RULES)
_strict_rules_dict = {r.rule_id: r for r in HARD_BLOCK_RULES}
_strict_rules_dict.update({
    "placeholder_practice_ids": ExportRule(
        rule_id="placeholder_practice_ids",
        rule_type=RuleType.HARD_BLOCK,
        description="Practice IDs starting with 'unresolved-' or containing 'placeholder'",
        check_fn=_check_placeholder_practice_ids,
        error_message="Strict export cannot contain placeholder practice IDs"
    ),
    "empty_why_it_matters": ExportRule(
        rule_id="empty_why_it_matters",
        rule_type=RuleType.HARD_BLOCK,
        description="why_it_matters is missing or less than 30 characters",
        check_fn=_check_empty_why_it_matters,
        error_message="Strict export requires meaningful why_it_matters (min 30 chars)"
    ),
    "generic_boilerplate": ExportRule(
        rule_id="generic_boilerplate",
        rule_type=RuleType.HARD_BLOCK,
        description="Content contains generic boilerplate like 'Golden Reference Document'",
        check_fn=_check_generic_boilerplate,
        error_message="Content contains generic boilerplate/template text"
    ),
    "wrong_example_for_concept": ExportRule(
        rule_id="wrong_example_for_concept",
        rule_type=RuleType.HARD_BLOCK,
        description="SQL example doesn't match the concept being taught",
        check_fn=_check_wrong_example_for_concept,
        error_message="SQL example doesn't match concept (e.g., SELECT example for CREATE TABLE)"
    ),
})
STRICT_FILTERS: list[ExportRule] = list(_strict_rules_dict.values())
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
# EXPORT MODE FILTER SETS
# =============================================================================

def _check_placeholder_practice_links_warn(unit: InstructionalUnit) -> tuple[bool, str]:
    """Check for placeholder practice links - WARN only for prototype mode.
    
    Same checks as _check_placeholder_practice_links but always returns True
    to allow export, with appropriate warning messages.
    """
    # Only check L3 explanation units
    if unit.target_stage != "L3_explanation":
        return True, f"Practice link check skipped for {unit.target_stage}"
    
    content = unit.content or {}
    if not isinstance(content, dict):
        return True, "Content is not a dict, cannot check practice links"
    
    practice_links = content.get("practice_links", [])
    if not practice_links:
        return True, "No practice links present"
    
    # Track placeholder status
    total_problem_ids = 0
    placeholder_count = 0
    unresolved_count = 0
    
    for link in practice_links:
        if isinstance(link, dict):
            needs_resolution = link.get("needs_resolution", False)
            problem_ids = link.get("problem_ids", [])
            metadata = link.get("metadata", {})
        else:
            # Handle PracticeLink objects
            needs_resolution = getattr(link, "needs_resolution", False)
            problem_ids = getattr(link, "problem_ids", [])
            metadata = getattr(link, "metadata", {}) or {}
        
        total_problem_ids += len(problem_ids)
        
        if needs_resolution:
            unresolved_count += len(problem_ids)
        
        # Check metadata for v2.0 format
        problems_meta = metadata.get("problems", []) if isinstance(metadata, dict) else []
        for problem_meta in problems_meta:
            if isinstance(problem_meta, dict) and problem_meta.get("is_placeholder", False):
                placeholder_count += 1
        
        for pid in problem_ids:
            if pid.startswith("unresolved-"):
                unresolved_count += 1
            elif pid.startswith("problem-"):
                placeholder_count += 1
    
    # Always return True (allow export) with warning if issues found
    if placeholder_count > 0 or unresolved_count > 0:
        return True, f"WARNING: {placeholder_count} placeholder(s) and {unresolved_count} unresolved link(s) found - replace with real problem IDs"
    
    return True, "All practice links are resolved"


PROTOTYPE_FILTERS: list[ExportRule] = PRODUCTION_FILTERS.copy() + [
    # Override placeholder check to warn only (not block)
    ExportRule(
        rule_id="placeholder_practice_links_warn",
        rule_type=RuleType.WARN,
        description="Practice links contain placeholder IDs (warning only in prototype mode)",
        check_fn=_check_placeholder_practice_links_warn,
        error_message="WARNING: Prototype mode allows placeholder practice links"
    ),
]
"""Prototype filters - current production behavior.

Allows placeholder practice links with warnings but permits export.
This is the default mode for backward compatibility.
"""

STUDENT_READY_FILTERS: list[ExportRule] = HARD_BLOCK_RULES.copy() + [
    # === NEW STRICT RULES FOR STUDENT_READY MODE ===
    
    # 1. Fallback L2 units - any unit with is_fallback=True in metadata
    ExportRule(
        rule_id="fallback_unit",
        rule_type=RuleType.HARD_BLOCK,
        description="Unit is a fallback unit (is_fallback=True in metadata)",
        check_fn=_check_fallback_unit,
        error_message="Student-ready export cannot contain fallback units (extraction failed)"
    ),
    
    # 2. Off-book curated-only concepts - source_mode == "curated_only_offbook"
    ExportRule(
        rule_id="offbook_curated_concept",
        rule_type=RuleType.HARD_BLOCK,
        description="Off-book curated-only concept (source_mode == curated_only_offbook)",
        check_fn=_check_offbook_curated_concept,
        error_message="Student-ready export cannot contain off-book curated-only concepts"
    ),
    
    # 3. Placeholder practice links with needs_resolution=true
    ExportRule(
        rule_id="placeholder_practice_links_strict",
        rule_type=RuleType.HARD_BLOCK,
        description="Practice links with needs_resolution=true",
        check_fn=_check_placeholder_practice_links_strict,
        error_message="Student-ready export cannot contain unresolved practice links (needs_resolution=true)"
    ),
    
    # 4. Heading-like L3 definitions (already covered by heading_like_definition, but explicit here)
    # Note: heading_like_definition in HARD_BLOCK_RULES already handles this
    
    # 5. Default-only examples with no source evidence
    ExportRule(
        rule_id="default_example_no_source_evidence",
        rule_type=RuleType.HARD_BLOCK,
        description="L2 uses default example with no source evidence",
        check_fn=_check_default_example_no_source_evidence,
        error_message="L2 uses default example with insufficient source evidence"
    ),
    
    # 6. Broken SQL examples (already covered by broken_sql_example in HARD_BLOCK_RULES)
    # Note: broken_sql_example in HARD_BLOCK_RULES already handles this
    
    # === EXISTING STUDENT-READY RULES ===
    
    # Hard block: Practice links contain placeholders (unresolved-*, problem-*)
    # This rule blocks if ANY placeholder practice links are found
    ExportRule(
        rule_id="placeholder_practice_links",
        rule_type=RuleType.HARD_BLOCK,
        description="Practice links contain placeholder IDs (unresolved-*, problem-*) or is_placeholder=true",
        check_fn=_check_placeholder_practice_links,
        error_message="Student-ready export cannot contain placeholder practice links"
    ),
    # Hard block: Placeholder practice IDs anywhere
    ExportRule(
        rule_id="placeholder_practice_ids",
        rule_type=RuleType.HARD_BLOCK,
        description="Practice IDs starting with 'unresolved-' or containing 'placeholder'",
        check_fn=_check_placeholder_practice_ids,
        error_message="Student-ready export cannot contain placeholder practice IDs"
    ),
    # Block L2 units using default examples
    ExportRule(
        rule_id="default_only_l2_example",
        rule_type=RuleType.HARD_BLOCK,
        description="L2 unit uses generic default example instead of concept-appropriate SQL",
        check_fn=_check_default_only_l2_example,
        error_message="L2 unit uses generic default example instead of concept-appropriate SQL"
    ),
    # Block purely synthetic L3 without source grounding
    ExportRule(
        rule_id="synthetic_only_l3",
        rule_type=RuleType.HARD_BLOCK,
        description="L3 explanation is purely synthetic with no source evidence",
        check_fn=_check_synthetic_only_l3,
        error_message="L3 explanation must be grounded in source text, not purely synthetic"
    ),
    # Block weak curated fallback (placeholder text)
    ExportRule(
        rule_id="weak_curated_fallback",
        rule_type=RuleType.HARD_BLOCK,
        description="Curated fallback content appears to be placeholder text",
        check_fn=_check_weak_curated_fallback,
        error_message="Curated fallback content appears to be placeholder text"
    ),
    # Block empty or too-short why_it_matters
    ExportRule(
        rule_id="empty_why_it_matters",
        rule_type=RuleType.HARD_BLOCK,
        description="why_it_matters is missing or less than 30 characters",
        check_fn=_check_empty_why_it_matters,
        error_message="Student-ready export requires meaningful why_it_matters (min 30 chars)"
    ),
    # Block generic boilerplate content
    ExportRule(
        rule_id="generic_boilerplate",
        rule_type=RuleType.HARD_BLOCK,
        description="Content contains generic boilerplate like 'Golden Reference Document'",
        check_fn=_check_generic_boilerplate,
        error_message="Content contains generic boilerplate/template text"
    ),
    # Block repeated boilerplate across concepts
    ExportRule(
        rule_id="repeated_boilerplate",
        rule_type=RuleType.HARD_BLOCK,
        description="Same reflective summary used across multiple concepts (copy-paste)",
        check_fn=_check_repeated_boilerplate,
        error_message="Reflective content appears to be copy-pasted from another concept"
    ),
    # Block wrong example type for concept
    ExportRule(
        rule_id="wrong_example_for_concept",
        rule_type=RuleType.HARD_BLOCK,
        description="SQL example doesn't match the concept being taught",
        check_fn=_check_wrong_example_for_concept,
        error_message="SQL example doesn't match concept (e.g., SELECT example for CREATE TABLE)"
    ),
    # Add critical soft blocks as hard blocks
    ExportRule(
        rule_id="missing_learning_objectives",
        rule_type=RuleType.HARD_BLOCK,
        description="No learning objectives defined",
        check_fn=_check_missing_learning_objectives,
        error_message="Missing learning objectives - required for student-ready export"
    ),
    ExportRule(
        rule_id="example_not_validated",
        rule_type=RuleType.HARD_BLOCK,
        description="SQL examples not execution-tested",
        check_fn=_check_example_not_validated,
        error_message="SQL examples must be validated before student-ready export"
    ),
    # Quality score check as SOFT_BLOCK (warn but allow)
    ExportRule(
        rule_id="low_quality_score",
        rule_type=RuleType.SOFT_BLOCK,
        description="Unit quality score below 0.7",
        check_fn=_check_low_quality_score,
        error_message="Unit quality below threshold for student-ready export"
    ),
    # Block heading-like why_it_matters (not instructional content)
    ExportRule(
        rule_id="heading_like_why_it_matters",
        rule_type=RuleType.HARD_BLOCK,
        description="why_it_matters looks like a heading ('How to...', 'Chapter X', etc.)",
        check_fn=_check_heading_like_why_it_matters,
        error_message="why_it_matters appears to be a heading, not instructional content"
    ),
    # Block L3 with ontology fallback definitions (not extracted from source)
    ExportRule(
        rule_id="ontology_fallback_definition",
        rule_type=RuleType.HARD_BLOCK,
        description="L3 definition is from ontology fallback, not extracted",
        check_fn=_check_ontology_fallback_definition,
        error_message="L3 definition is ontology fallback, not grounded in textbook source"
    ),
    # Block units with too few evidence spans (weak grounding)
    ExportRule(
        rule_id="insufficient_evidence_spans",
        rule_type=RuleType.HARD_BLOCK,
        description="Unit has fewer than 2 evidence spans (weak source grounding)",
        check_fn=_check_insufficient_evidence_spans,
        error_message="Unit has insufficient source evidence (need 2+ spans)"
    ),
]
"""Student-ready filters - strict mode for production learner content.

Blocks:
- Fallback units (is_fallback=True)
- Off-book curated-only concepts (source_mode == curated_only_offbook)
- Placeholder practice links with needs_resolution=true
- Default-only examples without source evidence
- Placeholder practice links (unresolved-*, problem-*)
- L2 units using default examples
- Purely synthetic L3 without source grounding
- Weak curated fallback (placeholder text)
- Missing learning objectives
- Unvalidated SQL examples
- Low quality scores (warning)

Use this mode when exporting content for actual student consumption.
"""


# =============================================================================
# EXPORT FILTER ENGINE
# =============================================================================

class ExportFilterEngine:
    """
    Engine for filtering instructional content before export.
    
    Applies a set of rules to each unit in a library, tracking which units
    pass, which are blocked, and collecting warnings for soft-blocked content.
    
    Supports two export modes:
    - "prototype": Allows placeholder content with warnings (default, backward compatible)
    - "student_ready": Strict mode, blocks all weak/problematic content
    
    Example:
        >>> engine = ExportFilterEngine(PRODUCTION_FILTERS)
        >>> result = engine.filter_unit_library(library)
        >>> print(f"Pass rate: {result.pass_rate:.1%}")
        >>> exportable = engine.get_exportable_subset(library)
        
        >>> # Student-ready mode
        >>> engine = ExportFilterEngine(export_mode="student_ready")
        >>> result = engine.filter_unit_library(library)
        >>> print(f"Student-ready passed: {result.student_ready_passed}")
    """
    
    def __init__(
        self, 
        rules: list[ExportRule] | None = None,
        export_mode: str | None = None,
    ):
        """
        Initialize the filter engine.
        
        Args:
            rules: List of ExportRule to apply. If None, uses filters based on export_mode.
            export_mode: Export mode - "prototype" or "student_ready". If provided and 
                        rules is None, loads the appropriate filter set.
        """
        self.export_mode = export_mode or "prototype"
        
        if rules is not None:
            self.rules = rules
        elif self.export_mode == "student_ready":
            self.rules = STUDENT_READY_FILTERS
        elif self.export_mode == "prototype":
            self.rules = PROTOTYPE_FILTERS
        else:
            self.rules = PRODUCTION_FILTERS
        
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
        quality_warnings: list[str] = []
        filtered_units: list[str] = []
        passed_units: list[str] = []
        student_ready_blocked: list[str] = []
        library_validation: dict[str, Any] = {}
        
        for unit in library.instructional_units:
            unit_result = self._filter_single_unit(unit)
            
            if unit_result.can_export:
                passed_units.append(unit.unit_id)
                # Still collect warnings
                warnings.extend(unit_result.warnings)
                # Track quality warnings separately
                quality_warnings.extend([w for w in unit_result.warnings if "quality" in w.lower()])
            else:
                filtered_units.append(unit.unit_id)
                blocked_by.extend(unit_result.hard_block_reasons)
                # Track student-ready specific blocks
                if self.export_mode == "student_ready":
                    student_ready_blocked.append(unit.unit_id)
        
        # Check for missing L3 for core concepts (student_ready mode only)
        if self.export_mode == "student_ready":
            missing_l3_violations = _check_missing_l3_for_core_concepts(library)
            for concept_id, message in missing_l3_violations:
                blocked_by.append(f"missing_l3_core_concept: {message}")
                # Mark all units for this concept as blocked
                for unit in library.instructional_units:
                    if unit.concept_id == concept_id and unit.unit_id in passed_units:
                        passed_units.remove(unit.unit_id)
                        student_ready_blocked.append(unit.unit_id)
                        if unit.unit_id not in filtered_units:
                            filtered_units.append(unit.unit_id)
        
        # Run library-level validation for student_ready mode
        if self.export_mode == "student_ready":
            library_validation = self._validate_library_level(library)
            # If library-level validation fails, mark student_ready as failed
            if not library_validation.get("valid", True):
                student_ready_blocked.extend(passed_units)
        
        # Deduplicate
        blocked_by = list(set(blocked_by))
        warnings = list(set(warnings))
        
        can_export = len(passed_units) > 0
        student_ready_passed = len(student_ready_blocked) == 0
        
        return FilterResult(
            can_export=can_export,
            blocked_by=blocked_by,
            warnings=warnings,
            filtered_units=filtered_units,
            passed_units=passed_units,
            student_ready_passed=student_ready_passed,
            blocked_by_student_ready=student_ready_blocked,
            quality_warnings=quality_warnings,
            library_validation=library_validation,
        )
    
    def _validate_library_level(self, library: UnitLibraryExport) -> dict[str, Any]:
        """
        Run library-level validation checks for student_ready mode.
        
        Checks:
        - L2 coverage: at least 80% of concepts have L2 units
        - L3 coverage: at least 80% of concepts have L3 units
        - Fallback ratio: less than 10% of units are fallback
        - Off-book concepts: no off-book curated-only concepts
        
        Returns:
            Dictionary with validation results
        """
        units = library.instructional_units
        if not units:
            return {"valid": False, "reason": "No units in library"}
        
        # Collect statistics
        all_concepts: set[str] = set()
        concepts_with_l2: set[str] = set()
        concepts_with_l3: set[str] = set()
        fallback_count = 0
        offbook_concepts: list[str] = []
        
        for unit in units:
            all_concepts.add(unit.concept_id)
            
            # Check L2/L3 coverage
            if unit.target_stage == "L2_hint_plus_example":
                concepts_with_l2.add(unit.concept_id)
            elif unit.target_stage == "L3_explanation":
                concepts_with_l3.add(unit.concept_id)
            
            # Check for fallback units
            content = unit.content or {}
            if isinstance(content, dict):
                metadata = content.get("_metadata", {})
                is_fallback = content.get("is_fallback", False) or metadata.get("is_fallback", False)
                if is_fallback:
                    fallback_count += 1
                
                # Check for off-book curated-only
                source_mode = content.get("source_mode", "") or metadata.get("source_mode", "")
                if source_mode == "curated_only_offbook":
                    if unit.concept_id not in offbook_concepts:
                        offbook_concepts.append(unit.concept_id)
        
        total_concepts = len(all_concepts)
        if total_concepts == 0:
            return {"valid": False, "reason": "No concepts found in library"}
        
        # Calculate metrics
        l2_coverage = len(concepts_with_l2) / total_concepts if total_concepts > 0 else 0.0
        l3_coverage = len(concepts_with_l3) / total_concepts if total_concepts > 0 else 0.0
        fallback_ratio = fallback_count / len(units) if units else 0.0
        
        # Validate against thresholds
        validation_errors: list[str] = []
        
        if l2_coverage < 0.8:
            validation_errors.append(
                f"L2 coverage too low: {len(concepts_with_l2)}/{total_concepts} concepts "
                f"({l2_coverage:.1%}, min 80%)"
            )
        
        if l3_coverage < 0.8:
            validation_errors.append(
                f"L3 coverage too low: {len(concepts_with_l3)}/{total_concepts} concepts "
                f"({l3_coverage:.1%}, min 80%)"
            )
        
        if fallback_ratio > 0.1:
            validation_errors.append(
                f"Fallback ratio too high: {fallback_count}/{len(units)} units "
                f"({fallback_ratio:.1%}, max 10%)"
            )
        
        if offbook_concepts:
            validation_errors.append(
                f"Off-book curated-only concepts present: {', '.join(offbook_concepts[:5])}"
                + (f" and {len(offbook_concepts) - 5} more" if len(offbook_concepts) > 5 else "")
            )
        
        return {
            "valid": len(validation_errors) == 0,
            "l2_coverage": {
                "count": len(concepts_with_l2),
                "total": total_concepts,
                "ratio": l2_coverage,
            },
            "l3_coverage": {
                "count": len(concepts_with_l3),
                "total": total_concepts,
                "ratio": l3_coverage,
            },
            "fallback_ratio": {
                "count": fallback_count,
                "total": len(units),
                "ratio": fallback_ratio,
            },
            "offbook_concepts": offbook_concepts,
            "errors": validation_errors,
        }
    
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
    
    def should_block_unit(self, unit: InstructionalUnit) -> tuple[bool, list[str]]:
        """
        Determine if a unit should be blocked from export.
        
        This method provides a clear API for checking if content should be
        blocked, returning both the block decision and the reasons.
        
        Args:
            unit: The InstructionalUnit to check
            
        Returns:
            Tuple of (should_block, list_of_reasons)
            - should_block: True if the unit should be blocked
            - list_of_reasons: List of reasons why it was blocked (empty if not blocked)
        """
        result = self._filter_single_unit(unit)
        
        # Unit should be blocked if it has any hard block reasons
        should_block = len(result.hard_block_reasons) > 0
        
        return should_block, result.hard_block_reasons
    
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
        
        # Show export mode
        print(f"\n🎯 Export Mode: {self.export_mode.upper()}")
        if self.export_mode == "student_ready":
            print("   (Strict mode - blocks placeholder and weak content)")
        elif self.export_mode == "prototype":
            print("   (Prototype mode - allows placeholders with warnings)")
        
        print(f"\n📊 Summary:")
        print(f"   Total Units: {result.total_units}")
        print(f"   Passed: {len(result.passed_units)} ✅")
        print(f"   Filtered: {len(result.filtered_units)} ❌")
        print(f"   Pass Rate: {result.pass_rate:.1%}")
        
        # Show student-ready specific summary
        if self.export_mode == "student_ready":
            print(f"\n📚 Student-Ready Summary:")
            print(f"   Student-Ready Passed: {'✅ YES' if result.student_ready_passed else '❌ NO'}")
            print(f"   Blocked for Student-Ready: {len(result.blocked_by_student_ready)} units")
            if result.blocked_by_student_ready:
                print(f"   Student-Ready Pass Rate: {result.student_ready_pass_rate:.1%}")
            
            # Show library-level validation results
            if result.library_validation:
                print(f"\n📚 Library-Level Validation:")
                l2_cov = result.library_validation.get("l2_coverage", {})
                l3_cov = result.library_validation.get("l3_coverage", {})
                fallback = result.library_validation.get("fallback_ratio", {})
                offbook = result.library_validation.get("offbook_concepts", [])
                
                print(f"   L2 Coverage: {l2_cov.get('count', 0)}/{l2_cov.get('total', 0)} concepts ({l2_cov.get('ratio', 0):.1%})")
                print(f"   L3 Coverage: {l3_cov.get('count', 0)}/{l3_cov.get('total', 0)} concepts ({l3_cov.get('ratio', 0):.1%})")
                print(f"   Fallback Ratio: {fallback.get('count', 0)}/{fallback.get('total', 0)} units ({fallback.get('ratio', 0):.1%})")
                if offbook:
                    print(f"   Off-book Concepts: {len(offbook)} found")
                
                if not result.library_validation.get("valid", True):
                    print(f"\n   ❌ Library Validation FAILED:")
                    for error in result.library_validation.get("errors", []):
                        print(f"      • {error}")
                else:
                    print(f"\n   ✅ Library Validation PASSED")
        
        if result.can_export:
            print(f"\n   ✅ Can export: YES")
        else:
            print(f"\n   ❌ Can export: NO (no units passed)")
        
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
        
        # Show student-ready specific blocked reasons
        if self.export_mode == "student_ready" and result.blocked_by_student_ready:
            print(f"\n🚫 Blocked for Student-Ready Export ({len(result.blocked_by_student_ready)}):")
            student_ready_rejected = [
                (uid, reasons) for uid, reasons in rejected 
                if uid in result.blocked_by_student_ready
            ][:10]
            for unit_id, reasons in student_ready_rejected:
                print(f"   - {unit_id}:")
                for reason in reasons[:2]:
                    # Highlight student-ready specific rules
                    is_student_rule = any(
                        sr in reason.lower() 
                        for sr in ["placeholder", "default", "synthetic", "curated", "fallback", "offbook"]
                    )
                    prefix = "   🎯" if is_student_rule else "      •"
                    print(f"{prefix} {reason}")
            if len(result.blocked_by_student_ready) > 10:
                print(f"   ... and {len(result.blocked_by_student_ready) - 10} more")
        
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
    "PROTOTYPE_FILTERS",
    "STUDENT_READY_FILTERS",
    
    # Core concepts list
    "CORE_CONCEPTS",
    
    # Main engine
    "ExportFilterEngine",
    
    # Utility functions
    "create_custom_filter_set",
    "quick_filter_check",
    "should_export",
    
    # Student-ready check functions (for advanced use)
    "_check_placeholder_practice_links",
    "_check_placeholder_practice_ids",
    "_check_default_only_l2_example",
    "_check_synthetic_only_l3",
    "_check_weak_curated_fallback",
    "_check_empty_why_it_matters",
    "_check_generic_boilerplate",
    "_check_repeated_boilerplate",
    "_check_wrong_example_for_concept",
    "_check_missing_l3_for_core_concepts",
    "_check_low_quality_score",
    "_check_fallback_unit",
    "_check_offbook_curated_concept",
    "_check_placeholder_practice_links_strict",
    "_check_default_example_no_source_evidence",
]
