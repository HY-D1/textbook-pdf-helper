"""
Misconception Bank Generator for Error-Linked Remediation.

This module provides a comprehensive system for transforming common SQL mistakes
into grounded, error-linked remediation units. It maps SQL-Engage error subtypes
to instructional content with prerequisite-aware repair strategies.

Architecture:
- MisconceptionPattern: Defines detectable error patterns with regex matching
- MisconceptionBank: Repository and matcher for misconception patterns
- MisconceptionContentGenerator: Creates grounded remediation content
- ErrorLinkedTagging: Links instructional units to error types

Usage:
    bank = MisconceptionBank.load_default()
    
    # Detect misconceptions in student code
    patterns = bank.detect_in_student_code("SELECT col1 col2 FROM table", "select-basic")
    
    # Get remediation for an error
    remediation = bank.get_remediation_for_error("missing_comma_in_select", "select-basic")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from .instructional_models import (
    InstructionalUnit,
    MisconceptionUnit,
    RemediationLevel,
    SourceSpan,
    TargetStage,
    UnitType,
)


# =============================================================================
# Generation Configuration
# =============================================================================


@dataclass
class GenerationConfig:
    """
    Configuration for content generation.
    
    Controls the verbosity, difficulty, and style of generated
    remediation content.
    """
    
    difficulty: str = "beginner"
    max_examples: int = 2
    include_prevention_hints: bool = True
    include_key_takeaways: bool = True
    source_grounding_required: bool = True
    remediation_style: str = "socratic"  # socratic, direct, exploratory
    
    # Content length limits
    max_symptom_description_chars: int = 300
    max_explanation_chars: int = 800
    max_key_takeaway_chars: int = 200


# =============================================================================
# Misconception Pattern Definition
# =============================================================================


@dataclass
class MisconceptionPattern:
    """
    A detectable pattern representing a common SQL misconception.
    
    Links SQL-Engage error subtypes to instructional content with
    regex-based detection capabilities and prerequisite mapping for
    repair-first remediation strategies.
    
    Attributes:
        pattern_id: Unique identifier for this pattern (e.g., "missing_comma_v1")
        error_subtype_id: SQL-Engage error subtype ID (e.g., "missing_comma_in_select")
        concept_id: Concept where this misconception occurs (e.g., "select-basic")
        pattern_name: Human-readable name for this misconception
        learner_symptom: What the student sees or experiences (error message, behavior)
        likely_prereq_failure: Which prerequisite concept likely failed, if any
        sql_pattern: Regex pattern to detect in student SQL code
        remediation_order: 1=hint-level, 2=explanation-level, higher=advanced
        example_bad_sql: Example of incorrect SQL demonstrating this pattern
        example_good_sql: Corrected version of the example SQL
        common_error_messages: List of typical database error messages
    """
    
    pattern_id: str
    error_subtype_id: str
    concept_id: str
    pattern_name: str
    learner_symptom: str
    likely_prereq_failure: str | None
    sql_pattern: str
    remediation_order: int
    example_bad_sql: str = ""
    example_good_sql: str = ""
    common_error_messages: list[str] = field(default_factory=list)
    related_patterns: list[str] = field(default_factory=list)
    
    def get_compiled_regex(self) -> re.Pattern | None:
        """Compile the SQL pattern regex for matching."""
        try:
            return re.compile(self.sql_pattern, re.IGNORECASE | re.MULTILINE)
        except re.error:
            return None
    
    def matches(self, sql_code: str) -> bool:
        """Check if the given SQL code matches this misconception pattern."""
        pattern = self.get_compiled_regex()
        if pattern is None:
            return False
        return bool(pattern.search(sql_code))
    
    def to_summary(self) -> dict[str, Any]:
        """Generate a summary dictionary for this pattern."""
        return {
            "pattern_id": self.pattern_id,
            "error_subtype_id": self.error_subtype_id,
            "concept_id": self.concept_id,
            "pattern_name": self.pattern_name,
            "remediation_order": self.remediation_order,
            "has_prereq_link": self.likely_prereq_failure is not None,
        }


# =============================================================================
# Common SQL Misconceptions Library
# =============================================================================

# Pre-defined misconception patterns aligned with SQL-Engage error subtypes
# These patterns cover the most common SQL errors students make

COMMON_MISCONCEPTIONS: list[MisconceptionPattern] = [
    # =========================================================================
    # SELECT Syntax Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="missing_comma_select_v1",
        error_subtype_id="missing_comma_in_select",
        concept_id="select-basic",
        pattern_name="Missing Comma in SELECT",
        learner_symptom="Syntax error near column name or unexpected identifier",
        likely_prereq_failure=None,
        sql_pattern=r"SELECT\s+\w+\s+\w+\s+FROM",
        remediation_order=1,
        example_bad_sql="SELECT first_name last_name FROM employees;",
        example_good_sql="SELECT first_name, last_name FROM employees;",
        common_error_messages=[
            "syntax error at or near",
            "missing comma",
            "unexpected identifier",
        ],
        related_patterns=["extra_comma_select_v1"],
    ),
    
    MisconceptionPattern(
        pattern_id="extra_comma_select_v1",
        error_subtype_id="extra_comma_in_select",
        concept_id="select-basic",
        pattern_name="Extra Comma in SELECT",
        learner_symptom="Syntax error near ')' or unexpected end of statement",
        likely_prereq_failure=None,
        sql_pattern=r"SELECT\s+.*,\s*FROM",
        remediation_order=1,
        example_bad_sql="SELECT first_name, last_name, FROM employees;",
        example_good_sql="SELECT first_name, last_name FROM employees;",
        common_error_messages=[
            "syntax error at or near ')'",
            "syntax error at or near 'FROM'",
        ],
        related_patterns=["missing_comma_select_v1"],
    ),
    
    MisconceptionPattern(
        pattern_id="incorrect_null_comparison_v1",
        error_subtype_id="incorrect_null_comparison",
        concept_id="where-clause",
        pattern_name="Using = NULL instead of IS NULL",
        learner_symptom="Query returns no results when checking for NULL values",
        likely_prereq_failure="select-basic",
        sql_pattern=r"=\s*NULL\b",
        remediation_order=2,
        example_bad_sql="SELECT * FROM employees WHERE manager_id = NULL;",
        example_good_sql="SELECT * FROM employees WHERE manager_id IS NULL;",
        common_error_messages=[
            "operator does not exist",
            "unknown operator",
        ],
        related_patterns=["incorrect_null_comparison_v2"],
    ),
    
    MisconceptionPattern(
        pattern_id="incorrect_null_comparison_v2",
        error_subtype_id="incorrect_null_comparison",
        concept_id="where-clause",
        pattern_name="Using != NULL instead of IS NOT NULL",
        learner_symptom="Query returns no results when excluding NULL values",
        likely_prereq_failure="select-basic",
        sql_pattern=r"(!=|<>)\s*NULL\b",
        remediation_order=2,
        example_bad_sql="SELECT * FROM employees WHERE manager_id != NULL;",
        example_good_sql="SELECT * FROM employees WHERE manager_id IS NOT NULL;",
        common_error_messages=[
            "operator does not exist",
            "unknown operator",
        ],
        related_patterns=["incorrect_null_comparison_v1"],
    ),
    
    # =========================================================================
    # JOIN Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="missing_join_condition_v1",
        error_subtype_id="missing_join_condition",
        concept_id="joins-intro",
        pattern_name="Missing JOIN Condition (Cartesian Product)",
        learner_symptom="Query returns too many rows (Cartesian product) or missing ON clause error",
        likely_prereq_failure=None,
        sql_pattern=r"JOIN\s+\w+\s+(?!ON\b)",
        remediation_order=2,
        example_bad_sql="SELECT * FROM employees JOIN departments;",
        example_good_sql="SELECT * FROM employees JOIN departments ON employees.dept_id = departments.dept_id;",
        common_error_messages=[
            "JOIN expression must have an ON clause",
            "syntax error at end of input",
        ],
        related_patterns=["ambiguous_column_reference_v1"],
    ),
    
    MisconceptionPattern(
        pattern_id="incorrect_join_type_v1",
        error_subtype_id="incorrect_join_type",
        concept_id="joins-intro",
        pattern_name="Wrong JOIN Type Selected",
        learner_symptom="Missing expected rows or including unwanted NULLs in results",
        likely_prereq_failure="inner-join",
        sql_pattern=r"(INNER|LEFT|RIGHT|FULL)\s+JOIN",
        remediation_order=3,
        example_bad_sql="SELECT * FROM employees INNER JOIN departments ON employees.dept_id = departments.dept_id; -- Missing employees without departments",
        example_good_sql="SELECT * FROM employees LEFT JOIN departments ON employees.dept_id = departments.dept_id;",
        common_error_messages=[
            "unexpected NULL values",
            "missing expected rows",
        ],
        related_patterns=["missing_join_condition_v1"],
    ),
    
    MisconceptionPattern(
        pattern_id="ambiguous_column_reference_v1",
        error_subtype_id="ambiguous_column_reference",
        concept_id="joins-intro",
        pattern_name="Ambiguous Column Reference",
        learner_symptom="Column reference is ambiguous error",
        likely_prereq_failure="alias",
        sql_pattern=r"SELECT\s+.*\b(id|name|code|status)\b.*FROM\s+\w+\s*,\s*\w+",
        remediation_order=2,
        example_bad_sql="SELECT id, name FROM employees, departments;",
        example_good_sql="SELECT employees.id, employees.name FROM employees, departments;",
        common_error_messages=[
            "column reference is ambiguous",
            "ambiguous column",
        ],
        related_patterns=["missing_table_alias_v1"],
    ),
    
    MisconceptionPattern(
        pattern_id="missing_table_alias_v1",
        error_subtype_id="ambiguous_column_reference",
        concept_id="joins-intro",
        pattern_name="Missing Table Alias",
        learner_symptom="Difficult to read queries or ambiguous column errors",
        likely_prereq_failure="alias",
        sql_pattern=r"SELECT\s+\w+\.\w+.*FROM\s+\w+\s+\w+\s*,",
        remediation_order=1,
        example_bad_sql="SELECT e.name, d.name FROM employees e, departments d WHERE e.dept_id = d.dept_id;",
        example_good_sql="SELECT e.name AS employee_name, d.name AS dept_name FROM employees e JOIN departments d ON e.dept_id = d.dept_id;",
        common_error_messages=[
            "column reference is ambiguous",
        ],
        related_patterns=["ambiguous_column_reference_v1"],
    ),
    
    # =========================================================================
    # GROUP BY and Aggregation Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="missing_group_by_v1",
        error_subtype_id="missing_group_by",
        concept_id="group-by",
        pattern_name="Missing GROUP BY with Aggregates",
        learner_symptom="Column must appear in GROUP BY clause error",
        likely_prereq_failure="aggregate-functions",
        sql_pattern=r"SELECT\s+\w+.*,(?!.*GROUP\s+BY).*\b(COUNT|SUM|AVG|MAX|MIN)\s*\(",
        remediation_order=2,
        example_bad_sql="SELECT dept_id, COUNT(*) FROM employees;",
        example_good_sql="SELECT dept_id, COUNT(*) FROM employees GROUP BY dept_id;",
        common_error_messages=[
            "must appear in the GROUP BY clause",
            "column must appear in the GROUP BY clause",
        ],
        related_patterns=["where_having_confusion_v1"],
    ),
    
    MisconceptionPattern(
        pattern_id="having_without_group_by_v1",
        error_subtype_id="having_without_group_by",
        concept_id="having-clause",
        pattern_name="HAVING without GROUP BY",
        learner_symptom="HAVING clause without GROUP BY error or confusing results",
        likely_prereq_failure="aggregate-functions",
        sql_pattern=r"HAVING\b(?!.*GROUP\s+BY)",
        remediation_order=2,
        example_bad_sql="SELECT * FROM employees HAVING COUNT(*) > 5;",
        example_good_sql="SELECT dept_id, COUNT(*) FROM employees GROUP BY dept_id HAVING COUNT(*) > 5;",
        common_error_messages=[
            "HAVING clause without GROUP BY",
        ],
        related_patterns=["missing_group_by_v1", "where_having_confusion_v1"],
    ),
    
    MisconceptionPattern(
        pattern_id="where_having_confusion_v1",
        error_subtype_id="where_having_confusion",
        concept_id="having-clause",
        pattern_name="WHERE vs HAVING Misuse",
        learner_symptom="Aggregate functions not allowed in WHERE clause error",
        likely_prereq_failure="where-clause",
        sql_pattern=r"WHERE\s+.*\b(COUNT|SUM|AVG|MAX|MIN)\s*\(",
        remediation_order=2,
        example_bad_sql="SELECT dept_id, AVG(salary) FROM employees WHERE AVG(salary) > 50000 GROUP BY dept_id;",
        example_good_sql="SELECT dept_id, AVG(salary) FROM employees GROUP BY dept_id HAVING AVG(salary) > 50000;",
        common_error_messages=[
            "aggregate functions are not allowed in WHERE",
            "cannot use aggregate function in WHERE clause",
        ],
        related_patterns=["having_without_group_by_v1"],
    ),
    
    MisconceptionPattern(
        pattern_id="incorrect_aggregate_function_v1",
        error_subtype_id="incorrect_aggregate_function",
        concept_id="aggregate-functions",
        pattern_name="Wrong Aggregate Function",
        learner_symptom="Results don't match expected calculations",
        likely_prereq_failure="aggregate-functions",
        sql_pattern=r"(COUNT|SUM|AVG|MAX|MIN)\s*\(",
        remediation_order=2,
        example_bad_sql="SELECT COUNT(salary) FROM employees; -- Should be SUM for total payroll",
        example_good_sql="SELECT SUM(salary) FROM employees;",
        common_error_messages=[
            "incorrect result",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # Subquery Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="subquery_multiple_rows_v1",
        error_subtype_id="subquery_multiple_rows",
        concept_id="subqueries-intro",
        pattern_name="Subquery Returns Multiple Rows",
        learner_symptom="Subquery returns more than one row error",
        likely_prereq_failure="where-clause",
        sql_pattern=r"=\s*\(\s*SELECT",
        remediation_order=2,
        example_bad_sql="SELECT * FROM employees WHERE dept_id = (SELECT dept_id FROM departments WHERE location = 'NYC');",
        example_good_sql="SELECT * FROM employees WHERE dept_id IN (SELECT dept_id FROM departments WHERE location = 'NYC');",
        common_error_messages=[
            "subquery returns more than one row",
            "more than one row returned by a subquery",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # Additional Common Patterns
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="missing_where_clause_v1",
        error_subtype_id="missing_where_clause",
        concept_id="where-clause",
        pattern_name="Missing WHERE Clause",
        learner_symptom="All rows affected instead of specific rows (data loss risk)",
        likely_prereq_failure="where-clause",
        sql_pattern=r"UPDATE\s+\w+\s+SET(?!.*WHERE)|DELETE\s+FROM\s+\w+\s*(?!.*WHERE)",
        remediation_order=1,
        example_bad_sql="UPDATE employees SET salary = 50000; -- Updates ALL employees!",
        example_good_sql="UPDATE employees SET salary = 50000 WHERE dept_id = 1;",
        common_error_messages=[
            "all rows affected",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="string_literal_quotes_v1",
        error_subtype_id="string_literal_error",
        concept_id="where-clause",
        pattern_name="Missing Quotes on String Literals",
        learner_symptom="Column does not exist or invalid identifier error",
        likely_prereq_failure="select-basic",
        sql_pattern=r"WHERE\s+\w+\s*=\s*[a-zA-Z_]+[a-zA-Z0-9_]*\s*(?:AND|OR|;|$)",
        remediation_order=1,
        example_bad_sql="SELECT * FROM employees WHERE name = Smith;",
        example_good_sql="SELECT * FROM employees WHERE name = 'Smith';",
        common_error_messages=[
            "column does not exist",
            "invalid identifier",
        ],
        related_patterns=[],
    ),
]


# Mapping from error subtype IDs to their primary concept IDs
ERROR_SUBTYPE_TO_CONCEPT: dict[str, str] = {
    "missing_comma_in_select": "select-basic",
    "extra_comma_in_select": "select-basic",
    "incorrect_null_comparison": "where-clause",
    "missing_join_condition": "joins-intro",
    "incorrect_join_type": "joins-intro",
    "missing_group_by": "group-by",
    "having_without_group_by": "having-clause",
    "where_having_confusion": "having-clause",
    "incorrect_aggregate_function": "aggregate-functions",
    "ambiguous_column_reference": "joins-intro",
    "missing_table_alias": "joins-intro",
    "subquery_multiple_rows": "subqueries-intro",
    "missing_where_clause": "where-clause",
    "string_literal_error": "where-clause",
}


# =============================================================================
# Misconception Bank
# =============================================================================


class MisconceptionBank:
    """
    Repository for misconception patterns with detection and retrieval capabilities.
    
    The MisconceptionBank manages a collection of misconception patterns,
    provides SQL code analysis to detect likely misconceptions, and generates
    appropriate remediation units based on error subtypes.
    
    Example:
        bank = MisconceptionBank.load_default()
        
        # Detect patterns in student code
        patterns = bank.detect_in_student_code(
            "SELECT col1 col2 FROM table",
            concept_id="select-basic"
        )
        
        # Get remediation content
        remediation = bank.get_remediation_for_error(
            "missing_comma_in_select",
            "select-basic"
        )
    """
    
    def __init__(self, patterns: list[MisconceptionPattern] | None = None):
        """
        Initialize the misconception bank.
        
        Args:
            patterns: Optional list of patterns. If None, starts empty.
        """
        self._patterns: list[MisconceptionPattern] = patterns or []
        self._pattern_index: dict[str, MisconceptionPattern] = {}
        self._error_subtype_index: dict[str, list[MisconceptionPattern]] = {}
        self._concept_index: dict[str, list[MisconceptionPattern]] = {}
        
        if patterns:
            self._rebuild_indexes()
    
    def _rebuild_indexes(self) -> None:
        """Rebuild internal indexes for fast lookups."""
        self._pattern_index = {}
        self._error_subtype_index = {}
        self._concept_index = {}
        
        for pattern in self._patterns:
            # Index by pattern_id
            self._pattern_index[pattern.pattern_id] = pattern
            
            # Index by error_subtype_id
            if pattern.error_subtype_id not in self._error_subtype_index:
                self._error_subtype_index[pattern.error_subtype_id] = []
            self._error_subtype_index[pattern.error_subtype_id].append(pattern)
            
            # Index by concept_id
            if pattern.concept_id not in self._concept_index:
                self._concept_index[pattern.concept_id] = []
            self._concept_index[pattern.concept_id].append(pattern)
    
    @classmethod
    def load_default(cls) -> MisconceptionBank:
        """Load the bank with default common misconception patterns."""
        return cls(patterns=COMMON_MISCONCEPTIONS.copy())
    
    def add_pattern(self, pattern: MisconceptionPattern) -> None:
        """Add a new pattern to the bank."""
        self._patterns.append(pattern)
        self._rebuild_indexes()
    
    def get_pattern(self, pattern_id: str) -> MisconceptionPattern | None:
        """Get a pattern by its ID."""
        return self._pattern_index.get(pattern_id)
    
    def get_patterns_for_error_subtype(self, error_subtype: str) -> list[MisconceptionPattern]:
        """Get all patterns for a specific error subtype."""
        return self._error_subtype_index.get(error_subtype, [])
    
    def get_patterns_for_concept(self, concept_id: str) -> list[MisconceptionPattern]:
        """Get all patterns related to a concept."""
        return self._concept_index.get(concept_id, [])
    
    def detect_in_student_code(
        self,
        student_sql: str,
        concept_id: str | None = None
    ) -> list[MisconceptionPattern]:
        """
        Detect likely misconceptions in student SQL code.
        
        Args:
            student_sql: The SQL code submitted by the student
            concept_id: Optional concept ID to limit search scope
            
        Returns:
            List of matching misconception patterns, ordered by remediation_order
        """
        matches: list[MisconceptionPattern] = []
        
        # Determine which patterns to check
        if concept_id:
            patterns_to_check = self.get_patterns_for_concept(concept_id)
        else:
            patterns_to_check = self._patterns
        
        # Check each pattern
        for pattern in patterns_to_check:
            if pattern.matches(student_sql):
                matches.append(pattern)
        
        # Sort by remediation order (lower = more basic)
        matches.sort(key=lambda p: p.remediation_order)
        
        return matches
    
    def generate_for_concept(
        self,
        concept_id: str,
        source_blocks: list[dict[str, Any]],
        error_subtypes: list[str],
        config: GenerationConfig | None = None
    ) -> list[MisconceptionUnit]:
        """
        Generate misconception units for a concept.
        
        Matches error subtypes to patterns and creates grounded remediation
        content based on source material.
        
        Args:
            concept_id: The concept to generate units for
            source_blocks: Source content blocks for grounding
            error_subtypes: List of error subtype IDs to generate units for
            config: Optional generation configuration
            
        Returns:
            List of generated misconception units
        """
        config = config or GenerationConfig()
        units: list[MisconceptionUnit] = []
        
        for error_subtype in error_subtypes:
            # Find matching patterns
            patterns = self.get_patterns_for_error_subtype(error_subtype)
            
            for pattern in patterns:
                # Skip if pattern is for a different concept
                if pattern.concept_id != concept_id:
                    continue
                
                # Generate remediation content
                content_generator = MisconceptionContentGenerator()
                repair_content = content_generator.generate_repair_content(
                    pattern, source_blocks, config
                )
                
                # Create the misconception unit
                unit = MisconceptionUnit(
                    misconception_id=f"{pattern.pattern_id}_unit",
                    error_subtype_id=error_subtype,
                    concept_id=concept_id,
                    symptom_description=repair_content.get(
                        "symptom_description", pattern.learner_symptom
                    ),
                    likely_prereq_failure=pattern.likely_prereq_failure,
                    remediation_order=pattern.remediation_order,
                    remediation_level=self._get_remediation_level(pattern.remediation_order),
                    repair_content=repair_content,
                )
                units.append(unit)
        
        # Sort by remediation order
        units.sort(key=lambda u: u.remediation_order)
        
        return units
    
    def get_remediation_for_error(
        self,
        error_subtype: str,
        concept_id: str,
        config: GenerationConfig | None = None
    ) -> MisconceptionUnit | None:
        """
        Get the appropriate remediation unit for an error.
        
        Returns the first (lowest remediation_order) matching unit,
        or None if no pattern exists for this error/concept combination.
        
        Args:
            error_subtype: The SQL-Engage error subtype ID
            concept_id: The concept where the error occurred
            config: Optional generation configuration
            
        Returns:
            A MisconceptionUnit or None
        """
        patterns = self.get_patterns_for_error_subtype(error_subtype)
        
        # Filter to matching concept and sort by order
        matching = [p for p in patterns if p.concept_id == concept_id]
        if not matching:
            return None
        
        matching.sort(key=lambda p: p.remediation_order)
        pattern = matching[0]
        
        # Generate content (without source blocks for simplicity)
        config = config or GenerationConfig()
        content_generator = MisconceptionContentGenerator()
        repair_content = content_generator.generate_repair_content(
            pattern, [], config
        )
        
        return MisconceptionUnit(
            misconception_id=f"{pattern.pattern_id}_remediation",
            error_subtype_id=error_subtype,
            concept_id=concept_id,
            symptom_description=repair_content.get(
                "symptom_description", pattern.learner_symptom
            ),
            likely_prereq_failure=pattern.likely_prereq_failure,
            remediation_order=pattern.remediation_order,
            remediation_level=self._get_remediation_level(pattern.remediation_order),
            repair_content=repair_content,
        )
    
    def _get_remediation_level(self, order: int) -> RemediationLevel:
        """Map remediation order to level."""
        return "hint_level" if order == 1 else "explanation_level"
    
    def list_all_patterns(self) -> list[dict[str, Any]]:
        """Get a summary of all patterns in the bank."""
        return [p.to_summary() for p in self._patterns]
    
    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about the misconception bank."""
        return {
            "total_patterns": len(self._patterns),
            "unique_error_subtypes": len(self._error_subtype_index),
            "concepts_covered": list(self._concept_index.keys()),
            "error_subtypes_covered": list(self._error_subtype_index.keys()),
            "avg_remediation_order": sum(p.remediation_order for p in self._patterns) / max(len(self._patterns), 1),
            "patterns_with_prereq": sum(1 for p in self._patterns if p.likely_prereq_failure),
        }


# =============================================================================
# Misconception Content Generator
# =============================================================================


class MisconceptionContentGenerator:
    """
    Generates grounded remediation content for misconception patterns.
    
    Creates structured repair content including symptom descriptions,
    explanations, examples, and prevention hints. Content can be
    grounded in source material when available.
    """
    
    def generate_repair_content(
        self,
        pattern: MisconceptionPattern,
        source_blocks: list[dict[str, Any]],
        config: GenerationConfig
    ) -> dict[str, Any]:
        """
        Generate comprehensive repair content for a misconception.
        
        Creates a structured dictionary with all components needed for
        effective remediation, optionally grounded in source material.
        
        Args:
            pattern: The misconception pattern to generate content for
            source_blocks: Source content blocks for grounding
            config: Generation configuration
            
        Returns:
            Dictionary with repair content components:
            - symptom_description: What the student sees/does
            - why_it_happens: Explanation of the root cause
            - repair_explanation: How to fix the error
            - fix_example: Bad vs good SQL comparison
            - key_takeaway: One-sentence summary
            - prevention_hint: How to avoid in future
        """
        # Generate symptom description
        symptom = self._generate_symptom_description(pattern, config)
        
        # Generate why it happens
        why = self._generate_why_it_happens(pattern, source_blocks, config)
        
        # Generate repair explanation
        repair = self._generate_repair_explanation(pattern, config)
        
        # Generate fix example
        fix_example = self._generate_fix_example(pattern)
        
        # Generate key takeaway
        takeaway = self._generate_key_takeaway(pattern, config)
        
        # Generate prevention hint
        prevention = self._generate_prevention_hint(pattern) if config.include_prevention_hints else ""
        
        content: dict[str, Any] = {
            "symptom_description": symptom,
            "why_it_happens": why,
            "repair_explanation": repair,
            "fix_example": fix_example,
            "key_takeaway": takeaway,
        }
        
        if prevention:
            content["prevention_hint"] = prevention
        
        # Add source grounding if available
        if source_blocks and config.source_grounding_required:
            content["source_grounding"] = self._extract_source_grounding(
                pattern, source_blocks
            )
        
        return content
    
    def _generate_symptom_description(
        self,
        pattern: MisconceptionPattern,
        config: GenerationConfig
    ) -> str:
        """Generate symptom description based on pattern."""
        base_symptom = pattern.learner_symptom
        
        if pattern.remediation_order == 1:
            return f"You see an error: {base_symptom}. This is a common syntax issue."
        else:
            return f"You encounter: {base_symptom}. This suggests a conceptual misunderstanding."
    
    def _generate_why_it_happens(
        self,
        pattern: MisconceptionPattern,
        source_blocks: list[dict[str, Any]],
        config: GenerationConfig
    ) -> str:
        """Generate explanation of why the error happens."""
        explanations: dict[str, str] = {
            "missing_comma_select_v1": (
                "In SQL, columns in the SELECT list must be separated by commas. "
                "Without a comma, the database interprets the second column name "
                "as an alias for the first column, causing a syntax error."
            ),
            "extra_comma_select_v1": (
                "In SQL, the SELECT list cannot end with a comma. The last column "
                "before FROM should not have a trailing comma, unlike some programming "
                "languages that allow trailing commas."
            ),
            "incorrect_null_comparison_v1": (
                "NULL represents unknown values in SQL. Because NULL is not a value "
                "but rather the absence of a value, you cannot use standard comparison "
                "operators like = or !=. Instead, use IS NULL or IS NOT NULL."
            ),
            "missing_join_condition_v1": (
                "JOIN operations require an ON clause to specify how tables relate. "
                "Without this condition, the database performs a Cartesian product, "
                "returning every combination of rows from both tables."
            ),
            "missing_group_by_v1": (
                "When using aggregate functions (COUNT, SUM, AVG, etc.) alongside "
                "non-aggregated columns, SQL requires a GROUP BY clause listing all "
                "non-aggregated columns to know how to group the data."
            ),
            "where_having_confusion_v1": (
                "WHERE filters individual rows before aggregation, while HAVING filters "
                "groups after aggregation. Aggregate functions can only be used in HAVING, "
                "not WHERE, because WHERE runs before the aggregation is computed."
            ),
            "subquery_multiple_rows_v1": (
                "The = operator expects exactly one value. When a subquery might return "
                "multiple rows, use IN instead of =, or ensure the subquery returns "
                "only one row with LIMIT 1 or proper filtering."
            ),
        }
        
        return explanations.get(
            pattern.pattern_id,
            f"This error occurs due to a misunderstanding of SQL syntax or semantics. "
            f"Review the {pattern.concept_id} concept for correct usage patterns."
        )[:config.max_explanation_chars]
    
    def _generate_repair_explanation(
        self,
        pattern: MisconceptionPattern,
        config: GenerationConfig
    ) -> str:
        """Generate step-by-step repair instructions."""
        repairs: dict[str, str] = {
            "missing_comma_select_v1": (
                "Add a comma between each column in your SELECT list. "
                "Look at your column list and ensure there's a comma after every column "
                "except the last one before FROM."
            ),
            "extra_comma_select_v1": (
                "Remove the trailing comma before the FROM keyword. "
                "The last column in your SELECT list should not be followed by a comma."
            ),
            "incorrect_null_comparison_v1": (
                "Replace = NULL with IS NULL, and != NULL with IS NOT NULL. "
                "Remember: NULL comparisons always use IS or IS NOT, never = or !=."
            ),
            "missing_join_condition_v1": (
                "Add an ON clause to your JOIN specifying how the tables connect. "
                "Format: JOIN table2 ON table1.column = table2.column"
            ),
            "missing_group_by_v1": (
                "Add a GROUP BY clause after your WHERE clause (if any) and before "
                "ORDER BY. Include all non-aggregated columns from your SELECT list."
            ),
            "where_having_confusion_v1": (
                "Move conditions with aggregate functions from WHERE to a new HAVING clause "
                "that comes after GROUP BY. Keep non-aggregate conditions in WHERE."
            ),
            "subquery_multiple_rows_v1": (
                "Change = to IN if the subquery can return multiple values, "
                "or add LIMIT 1 to the subquery if you only want one result."
            ),
        }
        
        return repairs.get(
            pattern.pattern_id,
            f"Review the syntax for {pattern.concept_id} and correct your query accordingly."
        )[:config.max_explanation_chars]
    
    def _generate_fix_example(self, pattern: MisconceptionPattern) -> dict[str, str]:
        """Generate bad vs good SQL example."""
        return {
            "bad_sql": pattern.example_bad_sql or f"-- Incorrect {pattern.pattern_name}",
            "good_sql": pattern.example_good_sql or f"-- Correct {pattern.pattern_name}",
            "explanation": f"The corrected version fixes the {pattern.pattern_name.lower()} issue."
        }
    
    def _generate_key_takeaway(
        self,
        pattern: MisconceptionPattern,
        config: GenerationConfig
    ) -> str:
        """Generate a one-sentence key takeaway."""
        takeaways: dict[str, str] = {
            "missing_comma_select_v1": "Always separate SELECT columns with commas, but don't add one after the last column.",
            "extra_comma_select_v1": "No trailing commas allowed in SQL SELECT lists.",
            "incorrect_null_comparison_v1": "Use IS NULL and IS NOT NULL, never = NULL or != NULL.",
            "missing_join_condition_v1": "Every JOIN needs an ON clause to specify the relationship.",
            "missing_group_by_v1": "GROUP BY is required when mixing aggregates with regular columns.",
            "where_having_confusion_v1": "WHERE filters rows; HAVING filters groups. Use HAVING for aggregate conditions.",
            "subquery_multiple_rows_v1": "Use IN for subqueries that might return multiple rows; use = only for single values.",
        }
        
        return takeaways.get(
            pattern.pattern_id,
            f"Master the correct syntax for {pattern.concept_id} to avoid this error."
        )[:config.max_key_takeaway_chars]
    
    def _generate_prevention_hint(self, pattern: MisconceptionPattern) -> str:
        """Generate a prevention hint for future queries."""
        hints: dict[str, str] = {
            "missing_comma_select_v1": "Before submitting, count your columns and commas - you should have n-1 commas for n columns.",
            "extra_comma_select_v1": "Scan your query for 'FROM' and check there's no comma right before it.",
            "incorrect_null_comparison_v1": "Search your query for '= NULL' and replace with 'IS NULL'.",
            "missing_join_condition_v1": "Always write 'JOIN table ON' together - never write JOIN without ON.",
            "missing_group_by_v1": "If you see aggregate functions, check that all non-aggregate columns are in GROUP BY.",
            "where_having_confusion_v1": "If your condition uses COUNT, SUM, AVG, etc., it belongs in HAVING, not WHERE.",
            "subquery_multiple_rows_v1": "Before using = with a subquery, ask: 'Can this subquery return more than one row?'",
        }
        
        return hints.get(pattern.pattern_id, "Review the concept documentation before attempting similar queries.")
    
    def _extract_source_grounding(
        self,
        pattern: MisconceptionPattern,
        source_blocks: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Extract relevant source spans for content grounding."""
        # Simple keyword-based matching
        relevant_spans: list[SourceSpan] = []
        
        keywords = pattern.pattern_name.lower().split()
        
        for block in source_blocks:
            text = block.get("text", "").lower()
            # Check if any keyword appears in the block
            if any(kw in text for kw in keywords):
                span = SourceSpan(
                    span_id=block.get("span_id", f"span_{len(relevant_spans)}"),
                    doc_id=block.get("doc_id", "unknown"),
                    page_number=block.get("page_number", 1),
                    char_start=block.get("char_start", 0),
                    char_end=block.get("char_end", len(text)),
                    block_type=block.get("block_type", "prose"),
                    text_content=block.get("text", "")[:500],  # Truncate for summary
                    extraction_confidence=block.get("confidence", 0.8),
                )
                relevant_spans.append(span)
        
        return {
            "relevant_spans": [span.span_id for span in relevant_spans[:3]],
            "span_count": len(relevant_spans),
            "primary_source": relevant_spans[0].to_citation() if relevant_spans else None,
        }


# =============================================================================
# Error-Linked Tagging
# =============================================================================


class ErrorLinkedTagging:
    """
    Links instructional units to error subtypes with confidence scoring.
    
    Provides functionality to tag units with error information and
    determine escalation paths for remediation sequences.
    """
    
    # Standard escalation path for remediation
    DEFAULT_ESCALATION_PATH = ["hint", "explanation", "practice", "prereq_repair"]
    
    # Concept-specific escalation overrides
    # All concept IDs verified against sql_ontology.py canonical definitions
    CONCEPT_ESCALATION_PATHS: dict[str, list[str]] = {
        "select-basic": ["hint", "explanation", "practice"],
        "joins-intro": ["hint", "explanation", "contrast_example", "practice", "prereq_repair"],
        "group-by": ["hint", "explanation", "worked_example", "practice", "prereq_repair"],
        "subqueries-intro": ["hint", "explanation", "practice", "prereq_repair"],
    }
    
    @classmethod
    def tag_unit_with_error_subtype(
        cls,
        unit: InstructionalUnit,
        error_subtype: str,
        confidence: float
    ) -> InstructionalUnit:
        """
        Tag an instructional unit with an error subtype.
        
        Adds the error subtype to the unit's error_subtypes list
        if not already present, and updates unit metadata.
        
        Args:
            unit: The instructional unit to tag
            error_subtype: The SQL-Engage error subtype ID
            confidence: Confidence score (0-1) for this tagging
            
        Returns:
            The updated instructional unit
        """
        # Add error subtype if not already present
        if error_subtype not in unit.error_subtypes:
            unit.error_subtypes.append(error_subtype)
        
        # Update content with error link metadata
        if "error_links" not in unit.content:
            unit.content["error_links"] = {}
        
        unit.content["error_links"][error_subtype] = {
            "confidence": confidence,
            "tagged_at": "auto",  # In production, use actual timestamp
        }
        
        return unit
    
    @classmethod
    def get_escalation_path(cls, error_subtype: str, concept_id: str) -> list[str]:
        """
        Get the escalation path for an error subtype.
        
        Returns a sequence of remediation stages from least to most intensive:
        hint → explanation → practice → prereq repair
        
        Args:
            error_subtype: The error subtype ID
            concept_id: The concept where the error occurred
            
        Returns:
            List of remediation stage names in order
        """
        # Get concept-specific path or default
        path = cls.CONCEPT_ESCALATION_PATHS.get(concept_id, cls.DEFAULT_ESCALATION_PATH)
        
        # Some error types may need modified paths
        if error_subtype in ["missing_where_clause"]:
            # Data loss risk - escalate faster
            return ["explanation", "practice", "prereq_repair"]
        
        if error_subtype in ["incorrect_null_comparison"]:
            # Fundamental concept - always include prerequisite repair
            if "prereq_repair" not in path:
                path = path + ["prereq_repair"]
        
        return path
    
    @classmethod
    def get_next_remediation_stage(
        cls,
        current_stage: str,
        error_subtype: str,
        concept_id: str
    ) -> str | None:
        """
        Get the next stage in the escalation path.
        
        Args:
            current_stage: Current remediation stage
            error_subtype: The error subtype being addressed
            concept_id: The concept where the error occurred
            
        Returns:
            Next stage name or None if at end of path
        """
        path = cls.get_escalation_path(error_subtype, concept_id)
        
        try:
            current_index = path.index(current_stage)
            if current_index < len(path) - 1:
                return path[current_index + 1]
        except ValueError:
            # Current stage not in path, return first stage
            return path[0] if path else None
        
        return None
    
    @classmethod
    def should_escalate(
        cls,
        error_subtype: str,
        concept_id: str,
        attempt_count: int,
        max_attempts_per_stage: int = 2
    ) -> bool:
        """
        Determine if remediation should escalate to next stage.
        
        Args:
            error_subtype: The error subtype being addressed
            concept_id: The concept where the error occurred
            attempt_count: Number of attempts at current stage
            max_attempts_per_stage: Max attempts before escalating
            
        Returns:
            True if should escalate, False otherwise
        """
        path = cls.get_escalation_path(error_subtype, concept_id)
        
        # Always escalate if exceeded max attempts
        if attempt_count >= max_attempts_per_stage * len(path):
            return True
        
        # Check if at end of path
        current_stage_index = (attempt_count - 1) // max_attempts_per_stage
        return current_stage_index >= len(path) - 1 and attempt_count % max_attempts_per_stage == 0
    
    @classmethod
    def get_unit_type_for_stage(cls, stage: str) -> UnitType:
        """Map escalation stage to unit type."""
        stage_to_type: dict[str, UnitType] = {
            "hint": "hint",
            "explanation": "explanation",
            "practice": "practice",
            "prereq_repair": "prerequisite_repair",
            "contrast_example": "contrast_example",
            "worked_example": "worked_example",
        }
        return stage_to_type.get(stage, "explanation")
    
    @classmethod
    def get_target_stage_for_level(cls, level: RemediationLevel) -> TargetStage:
        """Map remediation level to target stage."""
        return "L1_hint" if level == "hint_level" else "L3_explanation"


# =============================================================================
# Convenience Functions
# =============================================================================

def create_misconception_bank(patterns: list[MisconceptionPattern] | None = None) -> MisconceptionBank:
    """Create a new misconception bank with optional custom patterns."""
    if patterns is None:
        return MisconceptionBank.load_default()
    return MisconceptionBank(patterns=patterns)


def detect_misconceptions(
    sql_code: str,
    concept_id: str | None = None
) -> list[MisconceptionPattern]:
    """
    Convenience function to detect misconceptions in SQL code.
    
    Uses the default misconception bank.
    """
    bank = MisconceptionBank.load_default()
    return bank.detect_in_student_code(sql_code, concept_id)


def get_remediation(
    error_subtype: str,
    concept_id: str
) -> MisconceptionUnit | None:
    """
    Convenience function to get remediation for an error.
    
    Uses the default misconception bank.
    """
    bank = MisconceptionBank.load_default()
    return bank.get_remediation_for_error(error_subtype, concept_id)


# =============================================================================
# Module Export
# =============================================================================

__all__ = [
    # Dataclasses
    "MisconceptionPattern",
    "GenerationConfig",
    
    # Constants
    "COMMON_MISCONCEPTIONS",
    "ERROR_SUBTYPE_TO_CONCEPT",
    
    # Classes
    "MisconceptionBank",
    "MisconceptionContentGenerator",
    "ErrorLinkedTagging",
    
    # Convenience functions
    "create_misconception_bank",
    "detect_misconceptions",
    "get_remediation",
]
