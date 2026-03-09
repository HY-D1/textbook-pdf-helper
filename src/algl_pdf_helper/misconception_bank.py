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
    
    # =========================================================================
    # NULL Handling Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="null_in_arithmetic_v1",
        error_subtype_id="null_arithmetic_error",
        concept_id="null-handling",
        pattern_name="NULL in Arithmetic Operations",
        learner_symptom="Unexpected NULL results in calculations",
        likely_prereq_failure="select-basic",
        sql_pattern=r"SELECT\s+.*\w+\s*\+\s*\w+.*FROM",
        remediation_order=2,
        example_bad_sql="SELECT salary + bonus AS total FROM employees; -- Returns NULL if bonus is NULL",
        example_good_sql="SELECT COALESCE(salary, 0) + COALESCE(bonus, 0) AS total FROM employees;",
        common_error_messages=[
            "NULL result in expression",
        ],
        related_patterns=["incorrect_null_comparison_v1"],
    ),
    
    MisconceptionPattern(
        pattern_id="null_in_aggregate_v1",
        error_subtype_id="null_aggregate_ignored",
        concept_id="null-handling",
        pattern_name="Not Understanding NULL is Ignored by Aggregates",
        learner_symptom="Confusion about COUNT(*) vs COUNT(column) with NULLs",
        likely_prereq_failure="aggregate-functions",
        sql_pattern=r"COUNT\s*\(\s*\w+\s*\)",
        remediation_order=2,
        example_bad_sql="SELECT COUNT(manager_id) FROM employees; -- Excludes rows where manager_id is NULL",
        example_good_sql="SELECT COUNT(*) FROM employees; -- Counts all rows",
        common_error_messages=[
            "unexpected count result",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # Pattern Matching (LIKE) Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="like_wildcard_confusion_v1",
        error_subtype_id="like_wildcard_misuse",
        concept_id="pattern-matching",
        pattern_name="LIKE Wildcard Confusion (% vs _)",
        learner_symptom="Pattern matches too many or too few rows",
        likely_prereq_failure="where-clause",
        sql_pattern=r"LIKE\s+'[^%_]*'",
        remediation_order=2,
        example_bad_sql="SELECT * FROM products WHERE name LIKE 'Apple'; -- Exact match, not pattern",
        example_good_sql="SELECT * FROM products WHERE name LIKE 'Apple%'; -- Pattern match",
        common_error_messages=[
            "no rows returned",
        ],
        related_patterns=["like_no_quotes_v1"],
    ),
    
    MisconceptionPattern(
        pattern_id="like_no_quotes_v1",
        error_subtype_id="like_pattern_syntax",
        concept_id="pattern-matching",
        pattern_name="LIKE Pattern Without Quotes",
        learner_symptom="Column does not exist error when using LIKE",
        likely_prereq_failure="where-clause",
        sql_pattern=r"LIKE\s+[a-zA-Z_][a-zA-Z0-9_]*\s*(?:AND|OR|;|$)",
        remediation_order=1,
        example_bad_sql="SELECT * FROM products WHERE name LIKE Apple%;",
        example_good_sql="SELECT * FROM products WHERE name LIKE 'Apple%';",
        common_error_messages=[
            "column 'apple%' does not exist",
            "invalid identifier",
        ],
        related_patterns=["like_wildcard_confusion_v1"],
    ),
    
    # =========================================================================
    # ORDER BY Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="order_by_column_position_v1",
        error_subtype_id="order_by_position_out_of_range",
        concept_id="order-by",
        pattern_name="ORDER BY Column Position Out of Range",
        learner_symptom="ORDER BY position is out of range of selected columns",
        likely_prereq_failure="select-basic",
        sql_pattern=r"ORDER\s+BY\s+\d+",
        remediation_order=2,
        example_bad_sql="SELECT name, salary FROM employees ORDER BY 5; -- Only 2 columns selected",
        example_good_sql="SELECT name, salary FROM employees ORDER BY 2;",
        common_error_messages=[
            "ORDER BY position is out of range",
            "ORDER BY position 5 is not in select list",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="order_by_before_where_v1",
        error_subtype_id="order_by_clause_order",
        concept_id="order-by",
        pattern_name="ORDER BY Before WHERE",
        learner_symptom="Syntax error near ORDER BY",
        likely_prereq_failure="select-basic",
        sql_pattern=r"SELECT.*ORDER\s+BY.*WHERE",
        remediation_order=1,
        example_bad_sql="SELECT * FROM employees ORDER BY salary WHERE dept_id = 1;",
        example_good_sql="SELECT * FROM employees WHERE dept_id = 1 ORDER BY salary;",
        common_error_messages=[
            "syntax error at or near 'WHERE'",
            "syntax error at or near 'ORDER'",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # LIMIT/OFFSET Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="limit_negative_value_v1",
        error_subtype_id="limit_negative_value",
        concept_id="limit-offset",
        pattern_name="Negative LIMIT or OFFSET Value",
        learner_symptom="LIMIT must not be negative error",
        likely_prereq_failure="select-basic",
        sql_pattern=r"LIMIT\s+-\d+|OFFSET\s+-\d+",
        remediation_order=1,
        example_bad_sql="SELECT * FROM employees LIMIT -10;",
        example_good_sql="SELECT * FROM employees LIMIT 10;",
        common_error_messages=[
            "LIMIT must not be negative",
            "OFFSET must not be negative",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="limit_without_order_by_v1",
        error_subtype_id="limit_without_order_by",
        concept_id="limit-offset",
        pattern_name="LIMIT Without ORDER BY",
        learner_symptom="Indeterminate results when paginating",
        likely_prereq_failure="order-by",
        sql_pattern=r"SELECT.*FROM.*LIMIT\s+\d+(?!.*ORDER\s+BY)",
        remediation_order=2,
        example_bad_sql="SELECT * FROM employees LIMIT 10 OFFSET 20;",
        example_good_sql="SELECT * FROM employees ORDER BY id LIMIT 10 OFFSET 20;",
        common_error_messages=[
            "unpredictable result ordering",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # ALIAS Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="alias_in_where_v1",
        error_subtype_id="alias_reference_in_where",
        concept_id="alias",
        pattern_name="Using Column Alias in WHERE Clause",
        learner_symptom="Column does not exist error for aliased column",
        likely_prereq_failure="select-basic",
        sql_pattern=r"SELECT.*AS\s+\w+.*WHERE.*\w+\s*=",
        remediation_order=2,
        example_bad_sql="SELECT salary * 12 AS annual_salary FROM employees WHERE annual_salary > 50000;",
        example_good_sql="SELECT salary * 12 AS annual_salary FROM employees WHERE salary * 12 > 50000;",
        common_error_messages=[
            "column 'annual_salary' does not exist",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="alias_as_required_v1",
        error_subtype_id="alias_syntax_error",
        concept_id="alias",
        pattern_name="Missing AS in Alias Declaration",
        learner_symptom="Syntax error near identifier",
        likely_prereq_failure="select-basic",
        sql_pattern=r"SELECT\s+\w+\s+\w+\s+FROM",
        remediation_order=1,
        example_bad_sql="SELECT first_name f_name FROM employees;",
        example_good_sql="SELECT first_name AS f_name FROM employees;",
        common_error_messages=[
            "syntax error at or near 'FROM'",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # DISTINCT Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="distinct_multiple_columns_v1",
        error_subtype_id="distinct_scope_misunderstanding",
        concept_id="distinct",
        pattern_name="DISTINCT on Multiple Columns Misunderstanding",
        learner_symptom="Unexpected duplicate values in results",
        likely_prereq_failure="select-basic",
        sql_pattern=r"SELECT\s+DISTINCT\s+\w+\s*,",
        remediation_order=2,
        example_bad_sql="SELECT DISTINCT first_name, DISTINCT last_name FROM employees;",
        example_good_sql="SELECT DISTINCT first_name, last_name FROM employees;",
        common_error_messages=[
            "syntax error at or near 'DISTINCT'",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="distinct_placement_v1",
        error_subtype_id="distinct_placement_error",
        concept_id="distinct",
        pattern_name="DISTINCT After SELECT",
        learner_symptom="Syntax error at or near DISTINCT",
        likely_prereq_failure="select-basic",
        sql_pattern=r"SELECT\s+\w+.*DISTINCT",
        remediation_order=1,
        example_bad_sql="SELECT first_name DISTINCT FROM employees;",
        example_good_sql="SELECT DISTINCT first_name FROM employees;",
        common_error_messages=[
            "syntax error at or near 'DISTINCT'",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # JOIN Type Specific Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="inner_join_null_confusion_v1",
        error_subtype_id="inner_join_excludes_nulls",
        concept_id="inner-join",
        pattern_name="Not Understanding INNER JOIN Excludes Unmatched Rows",
        learner_symptom="Missing rows expected in results",
        likely_prereq_failure="joins-intro",
        sql_pattern=r"INNER\s+JOIN",
        remediation_order=2,
        example_bad_sql="SELECT e.name, d.name FROM employees e INNER JOIN departments d ON e.dept_id = d.dept_id; -- Missing employees without departments",
        example_good_sql="SELECT e.name, d.name FROM employees e LEFT JOIN departments d ON e.dept_id = d.dept_id;",
        common_error_messages=[
            "missing expected rows",
        ],
        related_patterns=["incorrect_join_type_v1"],
    ),
    
    MisconceptionPattern(
        pattern_id="outer_join_direction_confusion_v1",
        error_subtype_id="outer_join_wrong_direction",
        concept_id="outer-join",
        pattern_name="LEFT vs RIGHT JOIN Direction Confusion",
        learner_symptom="Wrong table's unmatched rows are missing",
        likely_prereq_failure="inner-join",
        sql_pattern=r"(LEFT|RIGHT)\s+JOIN",
        remediation_order=2,
        example_bad_sql="SELECT * FROM departments d LEFT JOIN employees e ON d.dept_id = e.dept_id; -- Trying to get all employees including those without departments",
        example_good_sql="SELECT * FROM employees e LEFT JOIN departments d ON e.dept_id = d.dept_id;",
        common_error_messages=[
            "unexpected NULL values",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="self_join_no_alias_v1",
        error_subtype_id="self_join_missing_alias",
        concept_id="self-join",
        pattern_name="Self-Join Without Table Aliases",
        learner_symptom="Not unique table/alias error or ambiguous column",
        likely_prereq_failure="alias",
        sql_pattern=r"FROM\s+\w+\s+JOIN\s+\1",
        remediation_order=1,
        example_bad_sql="SELECT * FROM employees JOIN employees ON employees.manager_id = employees.emp_id;",
        example_good_sql="SELECT e.name, m.name AS manager FROM employees e JOIN employees m ON e.manager_id = m.emp_id;",
        common_error_messages=[
            "Not unique table/alias",
            "ambiguous column",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="cross_join_unintentional_v1",
        error_subtype_id="unintentional_cartesian_product",
        concept_id="cross-join",
        pattern_name="Unintentional CROSS JOIN (Missing ON Clause)",
        learner_symptom="Query returns exponentially more rows than expected",
        likely_prereq_failure="joins-intro",
        sql_pattern=r",\s*\w+\s+(?:WHERE|ORDER|GROUP|LIMIT|$)",
        remediation_order=2,
        example_bad_sql="SELECT * FROM employees, departments WHERE employees.dept_id = departments.dept_id; -- Old syntax without explicit JOIN",
        example_good_sql="SELECT * FROM employees JOIN departments ON employees.dept_id = departments.dept_id;",
        common_error_messages=[
            "query returns too many rows",
        ],
        related_patterns=["missing_join_condition_v1"],
    ),
    
    # =========================================================================
    # CTE (Common Table Expression) Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="cte_undefined_reference_v1",
        error_subtype_id="cte_undefined_reference",
        concept_id="cte",
        pattern_name="CTE Name Not Defined Before Use",
        learner_symptom="relation does not exist error when referencing CTE",
        likely_prereq_failure="subqueries-intro",
        sql_pattern=r"WITH\s+\w+\s+AS",
        remediation_order=1,
        example_bad_sql="SELECT * FROM dept_summary; WITH dept_summary AS (SELECT dept_id, COUNT(*) FROM employees GROUP BY dept_id); -- CTE defined after use",
        example_good_sql="WITH dept_summary AS (SELECT dept_id, COUNT(*) FROM employees GROUP BY dept_id) SELECT * FROM dept_summary;",
        common_error_messages=[
            "relation 'dept_summary' does not exist",
            "cte name is undefined",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="cte_missing_comma_v1",
        error_subtype_id="cte_syntax_error",
        concept_id="cte",
        pattern_name="Missing Comma Between Multiple CTEs",
        learner_symptom="syntax error at or near 'WITH' or unexpected token",
        likely_prereq_failure="cte",
        sql_pattern=r"WITH\s+\w+\s+AS\s*\([^)]+\)\s+\w+\s+AS",
        remediation_order=1,
        example_bad_sql="WITH cte1 AS (SELECT * FROM t1) cte2 AS (SELECT * FROM t2) SELECT * FROM cte1, cte2; -- missing comma",
        example_good_sql="WITH cte1 AS (SELECT * FROM t1), cte2 AS (SELECT * FROM t2) SELECT * FROM cte1, cte2;",
        common_error_messages=[
            "syntax error at or near 'AS'",
            "missing comma",
        ],
        related_patterns=["cte_undefined_reference_v1"],
    ),
    
    MisconceptionPattern(
        pattern_id="cte_recursive_missing_union_v1",
        error_subtype_id="cte_recursive_error",
        concept_id="cte",
        pattern_name="Recursive CTE Missing UNION ALL",
        learner_symptom="Recursive CTE must have anchor and recursive member connected by UNION",
        likely_prereq_failure="cte",
        sql_pattern=r"WITH\s+RECURSIVE\s+\w+\s+AS",
        remediation_order=3,
        example_bad_sql="WITH RECURSIVE nums AS (SELECT 1 AS n) SELECT n+1 FROM nums WHERE n < 5; -- missing UNION",
        example_good_sql="WITH RECURSIVE nums AS (SELECT 1 AS n UNION ALL SELECT n+1 FROM nums WHERE n < 5) SELECT * FROM nums;",
        common_error_messages=[
            "recursive query must have anchor and recursive members",
            "missing UNION in recursive CTE",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # Intersect and Except Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="set_operation_column_mismatch_v1",
        error_subtype_id="set_operation_column_mismatch",
        concept_id="intersect-except",
        pattern_name="Column Count Mismatch in INTERSECT/EXCEPT",
        learner_symptom="Each query in INTERSECT/EXCEPT must have same number of columns",
        likely_prereq_failure="union",
        sql_pattern=r"SELECT.*(INTERSECT|EXCEPT).*SELECT",
        remediation_order=2,
        example_bad_sql="SELECT name FROM employees INTERSECT SELECT name, salary FROM managers; -- column count mismatch",
        example_good_sql="SELECT name, NULL AS salary FROM employees INTERSECT SELECT name, salary FROM managers;",
        common_error_messages=[
            "each query must have the same number of columns",
            "INTERSECT/EXCEPT column count mismatch",
        ],
        related_patterns=["union_column_count_mismatch_v1"],
    ),
    
    MisconceptionPattern(
        pattern_id="intersect_vs_inner_join_confusion_v1",
        error_subtype_id="set_operation_vs_join_confusion",
        concept_id="intersect-except",
        pattern_name="INTERSECT vs INNER JOIN Confusion",
        learner_symptom="Using INTERSECT when JOIN would be more appropriate",
        likely_prereq_failure="inner-join",
        sql_pattern=r"SELECT\s+\w+\s+FROM.*INTERSECT",
        remediation_order=2,
        example_bad_sql="SELECT dept_id FROM employees INTERSECT SELECT id FROM departments; -- loses relationship context",
        example_good_sql="SELECT e.dept_id FROM employees e INNER JOIN departments d ON e.dept_id = d.id; -- preserves row context",
        common_error_messages=[
            "unexpected result format",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="except_vs_not_exists_confusion_v1",
        error_subtype_id="except_vs_not_exists_confusion",
        concept_id="intersect-except",
        pattern_name="EXCEPT vs NOT EXISTS Confusion",
        learner_symptom="Using EXCEPT when NOT EXISTS would be more efficient",
        likely_prereq_failure="exists-operator",
        sql_pattern=r"SELECT.*FROM.*EXCEPT",
        remediation_order=3,
        example_bad_sql="SELECT dept_id FROM departments EXCEPT SELECT dept_id FROM employees; -- set operation approach",
        example_good_sql="SELECT d.dept_id FROM departments d WHERE NOT EXISTS (SELECT 1 FROM employees e WHERE e.dept_id = d.dept_id);",
        common_error_messages=[
            "performance warning",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # Correlated Subquery Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="correlated_subquery_scope_v1",
        error_subtype_id="correlated_subquery_reference_error",
        concept_id="correlated-subquery",
        pattern_name="Correlated Subquery Reference Error",
        learner_symptom="Column does not exist in subquery",
        likely_prereq_failure="subqueries-intro",
        sql_pattern=r"SELECT.*FROM.*WHERE.*\(\s*SELECT.*FROM.*\)",
        remediation_order=3,
        example_bad_sql="SELECT * FROM employees e WHERE salary > (SELECT AVG(salary) FROM employees WHERE dept_id = d.dept_id); -- Wrong table alias reference",
        example_good_sql="SELECT * FROM employees e WHERE salary > (SELECT AVG(salary) FROM employees WHERE dept_id = e.dept_id);",
        common_error_messages=[
            "column 'd.dept_id' does not exist",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="exists_with_columns_v1",
        error_subtype_id="exists_with_select_star",
        concept_id="exists-operator",
        pattern_name="EXISTS with Column Selection",
        learner_symptom="Unnecessary columns in EXISTS subquery (performance issue)",
        likely_prereq_failure="correlated-subquery",
        sql_pattern=r"EXISTS\s*\(\s*SELECT\s+\w+",
        remediation_order=2,
        example_bad_sql="SELECT * FROM departments d WHERE EXISTS (SELECT dept_id FROM employees e WHERE e.dept_id = d.dept_id);",
        example_good_sql="SELECT * FROM departments d WHERE EXISTS (SELECT 1 FROM employees e WHERE e.dept_id = d.dept_id);",
        common_error_messages=[
            "performance warning",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # UNION Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="union_column_count_mismatch_v1",
        error_subtype_id="union_column_count_mismatch",
        concept_id="union",
        pattern_name="UNION Column Count Mismatch",
        learner_symptom="Each UNION query must have the same number of columns",
        likely_prereq_failure="select-basic",
        sql_pattern=r"SELECT.*UNION.*SELECT",
        remediation_order=2,
        example_bad_sql="SELECT name FROM employees UNION SELECT name, salary FROM managers;",
        example_good_sql="SELECT name, NULL AS salary FROM employees UNION SELECT name, salary FROM managers;",
        common_error_messages=[
            "each UNION query must have the same number of columns",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="union_type_confusion_v1",
        error_subtype_id="union_vs_union_all_confusion",
        concept_id="union",
        pattern_name="UNION vs UNION ALL Confusion",
        learner_symptom="Missing duplicate rows that should be preserved",
        likely_prereq_failure="select-basic",
        sql_pattern=r"UNION\s+(?!ALL|DISTINCT)",
        remediation_order=2,
        example_bad_sql="SELECT customer_id FROM orders_2022 UNION SELECT customer_id FROM orders_2023; -- Removes duplicates",
        example_good_sql="SELECT customer_id FROM orders_2022 UNION ALL SELECT customer_id FROM orders_2023;",
        common_error_messages=[
            "missing expected rows",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # DML Errors - INSERT
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="insert_column_value_mismatch_v1",
        error_subtype_id="insert_column_count_mismatch",
        concept_id="insert-statement",
        pattern_name="INSERT Column/Value Count Mismatch",
        learner_symptom="INSERT has more/expressions than target columns",
        likely_prereq_failure="select-basic",
        sql_pattern=r"INSERT\s+INTO\s+\w+\s*\([^)]+\)\s*VALUES\s*\([^)]+\)",
        remediation_order=1,
        example_bad_sql="INSERT INTO employees (name, salary) VALUES ('John', 50000, 'Engineering');",
        example_good_sql="INSERT INTO employees (name, salary, dept) VALUES ('John', 50000, 'Engineering');",
        common_error_messages=[
            "INSERT has more expressions than target columns",
            "INSERT has fewer expressions than target columns",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="insert_missing_column_list_v1",
        error_subtype_id="insert_missing_column_list",
        concept_id="insert-statement",
        pattern_name="INSERT Without Column List",
        learner_symptom="Column count mismatch when table schema changes",
        likely_prereq_failure="select-basic",
        sql_pattern=r"INSERT\s+INTO\s+\w+\s+VALUES",
        remediation_order=2,
        example_bad_sql="INSERT INTO employees VALUES (1, 'John', 50000);",
        example_good_sql="INSERT INTO employees (emp_id, name, salary) VALUES (1, 'John', 50000);",
        common_error_messages=[
            "INSERT has more expressions than target columns",
        ],
        related_patterns=["insert_column_value_mismatch_v1"],
    ),
    
    # =========================================================================
    # MERGE/UPSERT Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="merge_update_delete_conflict_v1",
        error_subtype_id="merge_operation_conflict",
        concept_id="merge-upsert",
        pattern_name="MERGE UPDATE and DELETE on Same Row Conflict",
        learner_symptom="A MERGE statement cannot UPDATE/DELETE the same row more than once",
        likely_prereq_failure="update-statement",
        sql_pattern=r"MERGE\s+INTO.*WHEN\s+MATCHED.*UPDATE.*DELETE",
        remediation_order=3,
        example_bad_sql="MERGE INTO target USING source ON t.id = s.id WHEN MATCHED THEN UPDATE SET val = s.val DELETE WHERE s.status = 'D'; -- conflicts",
        example_good_sql="MERGE INTO target USING source ON t.id = s.id WHEN MATCHED AND s.status != 'D' THEN UPDATE SET val = s.val WHEN MATCHED AND s.status = 'D' THEN DELETE;",
        common_error_messages=[
            "cannot update/delete the same row more than once",
            "MERGE operation conflict",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="merge_missing_source_target_v1",
        error_subtype_id="merge_syntax_error",
        concept_id="merge-upsert",
        pattern_name="MERGE Missing Source or Target Specification",
        learner_symptom="Syntax error in MERGE statement: missing source or target",
        likely_prereq_failure="insert-statement",
        sql_pattern=r"MERGE\s+(?!INTO)",
        remediation_order=1,
        example_bad_sql="MERGE target_table USING source_table ON id = sid; -- missing INTO",
        example_good_sql="MERGE INTO target_table USING source_table ON target_table.id = source_table.sid;",
        common_error_messages=[
            "syntax error at or near 'MERGE'",
            "missing INTO keyword",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="upsert_duplicate_key_v1",
        error_subtype_id="upsert_duplicate_key",
        concept_id="merge-upsert",
        pattern_name="UPSERT Causing Duplicate Key Violation",
        learner_symptom="Duplicate key value violates unique constraint in UPSERT",
        likely_prereq_failure="insert-statement",
        sql_pattern=r"INSERT\s+.*ON\s+(DUPLICATE|CONFLICT)",
        remediation_order=2,
        example_bad_sql="INSERT INTO users (id, name) VALUES (1, 'John') ON DUPLICATE KEY UPDATE name = 'Jane'; -- wrong key assumption",
        example_good_sql="INSERT INTO users (id, name) VALUES (1, 'John') ON DUPLICATE KEY UPDATE name = VALUES(name);",
        common_error_messages=[
            "Duplicate entry for key",
            "unique constraint violation",
        ],
        related_patterns=["duplicate_primary_key_v1"],
    ),
    
    # =========================================================================
    # DML Errors - UPDATE
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="update_set_syntax_v1",
        error_subtype_id="update_set_syntax_error",
        concept_id="update-statement",
        pattern_name="UPDATE SET Syntax Error",
        learner_symptom="Syntax error at or near '='",
        likely_prereq_failure="select-basic",
        sql_pattern=r"UPDATE\s+\w+\s+SET\s+\w+\s*=.*=",
        remediation_order=1,
        example_bad_sql="UPDATE employees SET salary = 50000, bonus = 5000 WHERE id = 1;",
        example_good_sql="UPDATE employees SET salary = 50000, bonus = 5000 WHERE id = 1;",
        common_error_messages=[
            "syntax error at or near '='",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="update_subquery_correlation_v1",
        error_subtype_id="update_subquery_error",
        concept_id="update-statement",
        pattern_name="UPDATE with Subquery Reference",
        learner_symptom="Table being updated is specified in FROM clause",
        likely_prereq_failure="subqueries-intro",
        sql_pattern=r"UPDATE\s+\w+\s+SET.*=\s*\(\s*SELECT",
        remediation_order=3,
        example_bad_sql="UPDATE employees SET salary = (SELECT AVG(salary) FROM employees); -- Attempting to update based on aggregate",
        example_good_sql="UPDATE employees e SET salary = (SELECT AVG(salary) FROM employees WHERE dept_id = e.dept_id);",
        common_error_messages=[
            "cannot update table in subquery",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # DML Errors - DELETE
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="delete_alias_confusion_v1",
        error_subtype_id="delete_alias_syntax",
        concept_id="delete-statement",
        pattern_name="DELETE with Table Alias Confusion",
        learner_symptom="Syntax error with table alias in DELETE",
        likely_prereq_failure="alias",
        sql_pattern=r"DELETE\s+\w+\s+FROM",
        remediation_order=2,
        example_bad_sql="DELETE e FROM employees e WHERE e.status = 'inactive';",
        example_good_sql="DELETE FROM employees WHERE status = 'inactive';",
        common_error_messages=[
            "syntax error at or near 'FROM'",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="delete_without_where_v1",
        error_subtype_id="delete_all_rows_risk",
        concept_id="delete-statement",
        pattern_name="DELETE Without WHERE Clause",
        learner_symptom="All rows deleted from table",
        likely_prereq_failure="where-clause",
        sql_pattern=r"DELETE\s+FROM\s+\w+\s*(?!WHERE)",
        remediation_order=1,
        example_bad_sql="DELETE FROM employees;",
        example_good_sql="DELETE FROM employees WHERE status = 'terminated';",
        common_error_messages=[
            "all rows deleted",
        ],
        related_patterns=["missing_where_clause_v1"],
    ),
    
    # =========================================================================
    # Database Design Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="database_design_missing_pk_v1",
        error_subtype_id="missing_primary_key",
        concept_id="database-design",
        pattern_name="Table Missing Primary Key",
        learner_symptom="Table without primary key can have duplicate rows",
        likely_prereq_failure="create-table",
        sql_pattern=r"CREATE\s+TABLE\s+\w+\s*\([^)]*\)(?!.*PRIMARY\s+KEY)",
        remediation_order=2,
        example_bad_sql="CREATE TABLE audit_log (log_date DATE, message TEXT); -- no primary key",
        example_good_sql="CREATE TABLE audit_log (log_id INT PRIMARY KEY, log_date DATE, message TEXT);",
        common_error_messages=[
            "warning: table lacks primary key",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="database_design_no_normalization_v1",
        error_subtype_id="denormalization_issue",
        concept_id="database-design",
        pattern_name="Denormalized Data Structure",
        learner_symptom="Data redundancy causing update anomalies",
        likely_prereq_failure="normalization",
        sql_pattern=r"CREATE\s+TABLE.*\([^)]*(?:name|title).*\w+_\w+_name",
        remediation_order=3,
        example_bad_sql="CREATE TABLE orders (order_id INT, customer_name VARCHAR(100), customer_address VARCHAR(200), customer_phone VARCHAR(20)); -- redundant customer data",
        example_good_sql="CREATE TABLE orders (order_id INT, customer_id INT, FOREIGN KEY (customer_id) REFERENCES customers(id));",
        common_error_messages=[
            "data redundancy warning",
            "update anomaly risk",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="database_design_missing_fk_v1",
        error_subtype_id="missing_foreign_key",
        concept_id="database-design",
        pattern_name="Missing Foreign Key Constraint",
        learner_symptom="Orphan records possible without FK constraints",
        likely_prereq_failure="foreign-key",
        sql_pattern=r"CREATE\s+TABLE.*\([^)]*\w+_id\s+INT[^)]*\)(?!.*FOREIGN\s+KEY)",
        remediation_order=2,
        example_bad_sql="CREATE TABLE orders (order_id INT, customer_id INT); -- no FK constraint",
        example_good_sql="CREATE TABLE orders (order_id INT, customer_id INT, FOREIGN KEY (customer_id) REFERENCES customers(id));",
        common_error_messages=[
            "referential integrity warning",
        ],
        related_patterns=["database_design_missing_pk_v1"],
    ),
    
    # =========================================================================
    # ERD Basics Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="erd_many_to_many_wrong_v1",
        error_subtype_id="erd_relationship_error",
        concept_id="erd-basics",
        pattern_name="Many-to-Many Relationship Not Resolved",
        learner_symptom="Direct foreign key references in many-to-many relationship",
        likely_prereq_failure="database-design",
        sql_pattern=r"CREATE\s+TABLE.*\([^)]*\w+_id.*\w+_id.*FOREIGN\s+KEY",
        remediation_order=3,
        example_bad_sql="CREATE TABLE students_courses (student_id INT REFERENCES students, course_id INT REFERENCES courses, grade VARCHAR(2)); -- missing junction table concept",
        example_good_sql="CREATE TABLE enrollments (enrollment_id INT PRIMARY KEY, student_id INT REFERENCES students, course_id INT REFERENCES courses, grade VARCHAR(2));",
        common_error_messages=[
            "composite key should be used for junction table",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="erd_wrong_cardinality_v1",
        error_subtype_id="erd_cardinality_error",
        concept_id="erd-basics",
        pattern_name="Wrong Cardinality in Relationship Implementation",
        learner_symptom="One-to-many implemented as one-to-one or vice versa",
        likely_prereq_failure="erd-basics",
        sql_pattern=r"CREATE\s+UNIQUE\s+INDEX.*\w+_id",
        remediation_order=2,
        example_bad_sql="CREATE UNIQUE INDEX idx_emp_dept ON employees(dept_id); -- prevents multiple employees per department",
        example_good_sql="-- Remove UNIQUE for one-to-many: one department has many employees",
        common_error_messages=[
            "cannot insert duplicate key",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # Normalization - First Normal Form (1NF)
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="first_normal_form_multivalue_v1",
        error_subtype_id="first_normal_form_violation",
        concept_id="first-normal-form",
        pattern_name="Multi-Valued Attribute in Single Column",
        learner_symptom="Storing multiple values in one column violates 1NF",
        likely_prereq_failure="database-design",
        sql_pattern=r"CREATE\s+TABLE.*\([^)]*\w+\s+VARCHAR\s*\(\s*\d+\s*\)",
        remediation_order=2,
        example_bad_sql="CREATE TABLE employees (id INT, skills VARCHAR(200)); -- skills = 'SQL,Python,Java' violates 1NF",
        example_good_sql="CREATE TABLE employees (id INT); CREATE TABLE employee_skills (emp_id INT, skill VARCHAR(50));",
        common_error_messages=[
            "multi-valued attribute detected",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="first_normal_form_repeating_groups_v1",
        error_subtype_id="first_normal_form_violation",
        concept_id="first-normal-form",
        pattern_name="Repeating Groups in Table Structure",
        learner_symptom="Multiple similar columns for same attribute type",
        likely_prereq_failure="database-design",
        sql_pattern=r"CREATE\s+TABLE.*\([^)]*phone1.*phone2.*phone3",
        remediation_order=2,
        example_bad_sql="CREATE TABLE contacts (id INT, phone1 VARCHAR(20), phone2 VARCHAR(20), phone3 VARCHAR(20)); -- repeating group",
        example_good_sql="CREATE TABLE contacts (id INT); CREATE TABLE contact_phones (contact_id INT, phone_number VARCHAR(20), phone_type VARCHAR(20));",
        common_error_messages=[
            "repeating groups violate 1NF",
        ],
        related_patterns=["first_normal_form_multivalue_v1"],
    ),
    
    # =========================================================================
    # Normalization - Second Normal Form (2NF)
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="second_normal_form_partial_dependency_v1",
        error_subtype_id="second_normal_form_violation",
        concept_id="second-normal-form",
        pattern_name="Partial Dependency on Composite Key (2NF Violation)",
        learner_symptom="Non-key column depends on only part of composite key",
        likely_prereq_failure="first-normal-form",
        sql_pattern=r"CREATE\s+TABLE.*PRIMARY\s+KEY\s*\([^)]+,[^)]+\)",
        remediation_order=3,
        example_bad_sql="CREATE TABLE enrollment (student_id INT, course_id INT, course_name VARCHAR(100), PRIMARY KEY (student_id, course_id)); -- course_name depends only on course_id",
        example_good_sql="CREATE TABLE enrollments (student_id INT, course_id INT, PRIMARY KEY (student_id, course_id)); CREATE TABLE courses (course_id INT PRIMARY KEY, course_name VARCHAR(100));",
        common_error_messages=[
            "partial dependency detected",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # Normalization - Third Normal Form (3NF)
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="third_normal_form_transitive_dependency_v1",
        error_subtype_id="third_normal_form_violation",
        concept_id="third-normal-form",
        pattern_name="Transitive Dependency Violates 3NF",
        learner_symptom="Non-key column depends on another non-key column",
        likely_prereq_failure="second-normal-form",
        sql_pattern=r"CREATE\s+TABLE.*\w+_name.*\w+_code",
        remediation_order=3,
        example_bad_sql="CREATE TABLE employees (emp_id INT PRIMARY KEY, dept_id INT, dept_name VARCHAR(100), salary DECIMAL); -- dept_name depends on dept_id, not emp_id",
        example_good_sql="CREATE TABLE employees (emp_id INT PRIMARY KEY, dept_id INT, salary DECIMAL); CREATE TABLE departments (dept_id INT PRIMARY KEY, dept_name VARCHAR(100));",
        common_error_messages=[
            "transitive dependency detected",
        ],
        related_patterns=["second_normal_form_partial_dependency_v1"],
    ),
    
    # =========================================================================
    # Normalization - General Concept
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="normalization_over_normalization_v1",
        error_subtype_id="over_normalization",
        concept_id="normalization",
        pattern_name="Over-Normalization Causing Performance Issues",
        learner_symptom="Too many joins required for simple queries",
        likely_prereq_failure="third-normal-form",
        sql_pattern=r"SELECT.*FROM.*JOIN.*JOIN.*JOIN.*JOIN",
        remediation_order=3,
        example_bad_sql="SELECT e.name, d.name, l.city FROM employees e JOIN departments d ON e.dept_id = d.id JOIN locations l ON d.loc_id = l.id JOIN regions r ON l.region_id = r.id; -- excessive normalization",
        example_good_sql="-- Consider denormalizing frequently accessed data into a summary table",
        common_error_messages=[
            "query performance degraded",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="normalization_ignoring_anomalies_v1",
        error_subtype_id="normalization_ignored",
        concept_id="normalization",
        pattern_name="Not Normalizing Leading to Update Anomalies",
        learner_symptom="Data inconsistency from redundant data storage",
        likely_prereq_failure="database-design",
        sql_pattern=r"UPDATE.*SET.*WHERE",
        remediation_order=2,
        example_bad_sql="UPDATE employees SET dept_name = 'Engineering' WHERE dept_id = 5; -- must update all employees in dept",
        example_good_sql="UPDATE departments SET dept_name = 'Engineering' WHERE dept_id = 5; -- update in one place",
        common_error_messages=[
            "inconsistent data after update",
        ],
        related_patterns=["database_design_no_normalization_v1"],
    ),
    
    # =========================================================================
    # DDL Errors - CREATE TABLE
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="create_table_duplicate_column_v1",
        error_subtype_id="create_table_duplicate_column",
        concept_id="create-table",
        pattern_name="CREATE TABLE Duplicate Column Name",
        learner_symptom="Column name already exists in table",
        likely_prereq_failure=None,
        sql_pattern=r"CREATE\s+TABLE.*\(\s*\w+\s+\w+.*\w+\s+\w+",
        remediation_order=1,
        example_bad_sql="CREATE TABLE employees (id INT, name VARCHAR(50), id INT);",
        example_good_sql="CREATE TABLE employees (id INT, name VARCHAR(50), emp_code INT);",
        common_error_messages=[
            "column name 'id' appears more than once",
            "duplicate column name",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="create_table_missing_datatype_v1",
        error_subtype_id="create_table_syntax_error",
        concept_id="create-table",
        pattern_name="CREATE TABLE Missing Data Type",
        learner_symptom="Syntax error at or near column name",
        likely_prereq_failure=None,
        sql_pattern=r"CREATE\s+TABLE.*\([^)]+\w+\s*,",
        remediation_order=1,
        example_bad_sql="CREATE TABLE employees (id, name VARCHAR(50));",
        example_good_sql="CREATE TABLE employees (id INT, name VARCHAR(50));",
        common_error_messages=[
            "syntax error at or near ','",
            "missing data type",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # DDL Errors - ALTER TABLE
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="alter_table_drop_column_v1",
        error_subtype_id="alter_table_drop_column",
        concept_id="alter-table",
        pattern_name="ALTER TABLE DROP COLUMN Syntax",
        learner_symptom="Syntax error near DROP",
        likely_prereq_failure="create-table",
        sql_pattern=r"ALTER\s+TABLE\s+\w+\s+DROP\s+\w+(?!\s+CASCADE|CONSTRAINT|COLUMN)",
        remediation_order=2,
        example_bad_sql="ALTER TABLE employees DROP salary;",
        example_good_sql="ALTER TABLE employees DROP COLUMN salary;",
        common_error_messages=[
            "syntax error at or near 'salary'",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="alter_table_add_column_exists_v1",
        error_subtype_id="alter_table_column_exists",
        concept_id="alter-table",
        pattern_name="ALTER TABLE ADD Column That Already Exists",
        learner_symptom="Column already exists in table",
        likely_prereq_failure="create-table",
        sql_pattern=r"ALTER\s+TABLE.*ADD\s+(?:COLUMN\s+)?\w+",
        remediation_order=2,
        example_bad_sql="ALTER TABLE employees ADD COLUMN salary INT; -- Column already exists",
        example_good_sql="ALTER TABLE employees ADD COLUMN bonus INT;",
        common_error_messages=[
            "column 'salary' of relation 'employees' already exists",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # DDL Errors - DROP TABLE
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="drop_table_if_exists_v1",
        error_subtype_id="drop_table_if_exists",
        concept_id="drop-table",
        pattern_name="DROP TABLE Without IF EXISTS",
        learner_symptom="Table does not exist error",
        likely_prereq_failure="create-table",
        sql_pattern=r"DROP\s+TABLE\s+(?!IF)\s*\w+",
        remediation_order=2,
        example_bad_sql="DROP TABLE employees; -- Table may not exist",
        example_good_sql="DROP TABLE IF EXISTS employees;",
        common_error_messages=[
            "table 'employees' does not exist",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="drop_table_cascade_v1",
        error_subtype_id="drop_table_dependencies",
        concept_id="drop-table",
        pattern_name="DROP TABLE With Dependencies",
        learner_symptom="Cannot drop table with dependent objects",
        likely_prereq_failure="create-table",
        sql_pattern=r"DROP\s+TABLE\s+\w+\s*(?!CASCADE)",
        remediation_order=3,
        example_bad_sql="DROP TABLE departments; -- Has foreign key references from employees",
        example_good_sql="DROP TABLE departments CASCADE;",
        common_error_messages=[
            "cannot drop table 'departments' because other objects depend on it",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # Additional Aggregate Function Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="aggregate_in_select_without_group_by_v1",
        error_subtype_id="aggregate_without_group_by",
        concept_id="aggregate-functions",
        pattern_name="Mixing Aggregates and Columns Without GROUP BY",
        learner_symptom="Column must appear in GROUP BY clause or be used in aggregate",
        likely_prereq_failure="group-by",
        sql_pattern=r"SELECT\s+\w+.*,\s*(COUNT|SUM|AVG|MAX|MIN)\s*\(",
        remediation_order=2,
        example_bad_sql="SELECT dept_id, AVG(salary) FROM employees;",
        example_good_sql="SELECT dept_id, AVG(salary) FROM employees GROUP BY dept_id;",
        common_error_messages=[
            "must appear in the GROUP BY clause",
        ],
        related_patterns=["missing_group_by_v1"],
    ),
    
    MisconceptionPattern(
        pattern_id="aggregate_where_filter_v1",
        error_subtype_id="aggregate_in_where_clause",
        concept_id="aggregate-functions",
        pattern_name="Using Aggregate in WHERE Clause",
        learner_symptom="Aggregate functions not allowed in WHERE",
        likely_prereq_failure="having-clause",
        sql_pattern=r"WHERE\s+.*(COUNT|SUM|AVG|MAX|MIN)\s*\(",
        remediation_order=2,
        example_bad_sql="SELECT dept_id FROM employees WHERE COUNT(*) > 5 GROUP BY dept_id;",
        example_good_sql="SELECT dept_id FROM employees GROUP BY dept_id HAVING COUNT(*) > 5;",
        common_error_messages=[
            "aggregate functions are not allowed in WHERE",
        ],
        related_patterns=["where_having_confusion_v1"],
    ),
    
    # =========================================================================
    # Primary Key Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="duplicate_primary_key_v1",
        error_subtype_id="duplicate_primary_key",
        concept_id="primary-key",
        pattern_name="Duplicate Primary Key Value",
        learner_symptom="Duplicate entry error when inserting or updating row",
        likely_prereq_failure=None,
        sql_pattern=r"INSERT\s+INTO\s+\w+.*VALUES.*\([^)]*\d+",
        remediation_order=2,
        example_bad_sql="INSERT INTO employees (emp_id, name) VALUES (1, 'John'); -- emp_id 1 already exists",
        example_good_sql="INSERT INTO employees (emp_id, name) VALUES (100, 'John'); -- use unique emp_id",
        common_error_messages=[
            "Duplicate entry for key 'PRIMARY'",
            "duplicate key value violates unique constraint",
            "primary key violation",
        ],
        related_patterns=["unique_constraint_violation_v1"],
    ),
    
    MisconceptionPattern(
        pattern_id="primary_key_null_v1",
        error_subtype_id="primary_key_null_violation",
        concept_id="primary-key",
        pattern_name="Primary Key Cannot Be NULL",
        learner_symptom="Column cannot be null error for primary key column",
        likely_prereq_failure="null-handling",
        sql_pattern=r"INSERT\s+INTO\s+\w+\s*\([^)]*\)\s*VALUES\s*\([^)]*NULL",
        remediation_order=1,
        example_bad_sql="INSERT INTO employees (emp_id, name) VALUES (NULL, 'John'); -- PK cannot be NULL",
        example_good_sql="INSERT INTO employees (emp_id, name) VALUES (101, 'John'); -- provide valid PK value",
        common_error_messages=[
            "column cannot be null",
            "violates not-null constraint",
        ],
        related_patterns=["null_constraint_violation_v1"],
    ),
    
    MisconceptionPattern(
        pattern_id="primary_key_auto_increment_confusion_v1",
        error_subtype_id="auto_increment_misuse",
        concept_id="primary-key",
        pattern_name="Confusion About Auto-Increment Primary Keys",
        learner_symptom="Manually specifying values for auto-increment column causing conflicts",
        likely_prereq_failure=None,
        sql_pattern=r"INSERT\s+INTO\s+\w+\s*\(\s*\w+\s*\)\s*VALUES\s*\(\s*\d+",
        remediation_order=2,
        example_bad_sql="INSERT INTO users (user_id, name) VALUES (5, 'Alice'); -- user_id is AUTO_INCREMENT",
        example_good_sql="INSERT INTO users (name) VALUES ('Alice'); -- let auto-increment handle PK",
        common_error_messages=[
            "Duplicate entry for key",
        ],
        related_patterns=["duplicate_primary_key_v1"],
    ),
    
    # =========================================================================
    # Foreign Key Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="foreign_key_violation_insert_v1",
        error_subtype_id="foreign_key_violation",
        concept_id="foreign-key",
        pattern_name="FK Constraint Violation When Inserting Child Row",
        learner_symptom="Cannot add or update a child row: foreign key constraint fails",
        likely_prereq_failure="primary-key",
        sql_pattern=r"INSERT\s+INTO.*VALUES",
        remediation_order=2,
        example_bad_sql="INSERT INTO orders (order_id, customer_id) VALUES (1, 999); -- customer_id 999 doesn't exist in parent table",
        example_good_sql="INSERT INTO orders (order_id, customer_id) VALUES (1, 5); -- valid customer_id referencing existing parent",
        common_error_messages=[
            "Cannot add or update a child row: a foreign key constraint fails",
            "foreign key constraint violation",
            "violates foreign key constraint",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="foreign_key_violation_update_v1",
        error_subtype_id="foreign_key_violation",
        concept_id="foreign-key",
        pattern_name="FK Constraint Violation When Updating Referenced Key",
        learner_symptom="Cannot update parent row because child rows reference it",
        likely_prereq_failure="foreign-key",
        sql_pattern=r"UPDATE\s+\w+\s+SET\s+\w+\s*=",
        remediation_order=3,
        example_bad_sql="UPDATE customers SET customer_id = 999 WHERE customer_id = 5; -- referenced by orders table",
        example_good_sql="UPDATE customers SET name = 'New Name' WHERE customer_id = 5; -- update non-key column instead",
        common_error_messages=[
            "Cannot update parent row: a foreign key constraint fails",
            "foreign key constraint violation on update",
        ],
        related_patterns=["foreign_key_violation_insert_v1"],
    ),
    
    MisconceptionPattern(
        pattern_id="foreign_key_delete_cascade_v1",
        error_subtype_id="foreign_key_delete_violation",
        concept_id="foreign-key",
        pattern_name="Deleting Parent Row Without Handling Children",
        learner_symptom="Cannot delete parent row: foreign key constraint fails",
        likely_prereq_failure="foreign-key",
        sql_pattern=r"DELETE\s+FROM\s+\w+\s*(?!.*WHERE)",
        remediation_order=2,
        example_bad_sql="DELETE FROM departments WHERE dept_id = 1; -- employees still reference this department",
        example_good_sql="DELETE FROM employees WHERE dept_id = 1; DELETE FROM departments WHERE dept_id = 1; -- delete children first",
        common_error_messages=[
            "Cannot delete parent row: a foreign key constraint fails",
            "foreign key constraint violation on delete",
        ],
        related_patterns=["foreign_key_violation_insert_v1"],
    ),
    
    # =========================================================================
    # Constraints Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="foreign_key_violation_v1",
        error_subtype_id="constraint_violation",
        concept_id="constraints",
        pattern_name="Foreign Key Constraint Violation",
        learner_symptom="Foreign key constraint violation error when inserting data",
        likely_prereq_failure="joins-intro",
        sql_pattern=r"INSERT\s+INTO.*VALUES",
        remediation_order=2,
        example_bad_sql="INSERT INTO orders (id, customer_id) VALUES (1, 999);  -- customer_id 999 doesn't exist",
        example_good_sql="INSERT INTO orders (id, customer_id) VALUES (1, 5);  -- valid customer_id",
        common_error_messages=[
            "foreign key constraint violation",
            "violates foreign key constraint",
        ],
        related_patterns=["foreign_key_violation_insert_v1"],
    ),
    
    MisconceptionPattern(
        pattern_id="null_constraint_violation_v1",
        error_subtype_id="null_in_constraint_column",
        concept_id="constraints",
        pattern_name="NOT NULL Constraint Violation",
        learner_symptom="Column cannot be null error during INSERT",
        likely_prereq_failure="null-handling",
        sql_pattern=r"INSERT\s+INTO\s+\w+\s*\([^)]*\)\s*VALUES\s*\([^)]*\)",
        remediation_order=1,
        example_bad_sql="INSERT INTO users (id) VALUES (1);  -- name is NOT NULL",
        example_good_sql="INSERT INTO users (id, name) VALUES (1, 'John');",
        common_error_messages=[
            "column cannot be null",
            "violates not-null constraint",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="unique_constraint_violation_v1",
        error_subtype_id="constraint_violation",
        concept_id="constraints",
        pattern_name="Unique Constraint Violation",
        learner_symptom="Duplicate key value violates unique constraint",
        likely_prereq_failure=None,
        sql_pattern=r"INSERT\s+INTO.*VALUES|UPDATE\s+\w+\s+SET",
        remediation_order=2,
        example_bad_sql="INSERT INTO users (email) VALUES ('john@example.com');  -- email already exists",
        example_good_sql="UPDATE users SET name = 'John Doe' WHERE email = 'john@example.com';",
        common_error_messages=[
            "duplicate key value violates unique constraint",
            "unique constraint violation",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # String Functions Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="string_function_concat_vs_pipe_v1",
        error_subtype_id="string_function_syntax_error",
        concept_id="string-functions",
        pattern_name="Incorrect String Function Usage (CONCAT vs ||)",
        learner_symptom="Syntax error when using string concatenation operator",
        likely_prereq_failure="select-basic",
        sql_pattern=r"SELECT\s+.*\|\|",
        remediation_order=2,
        example_bad_sql="SELECT first_name || ' ' || last_name AS full_name FROM employees; -- || not supported in all databases",
        example_good_sql="SELECT CONCAT(first_name, ' ', last_name) AS full_name FROM employees; -- use CONCAT function",
        common_error_messages=[
            "syntax error at or near '|'",
            "operator does not exist: text || text",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="string_function_concat_missing_comma_v1",
        error_subtype_id="string_function_syntax_error",
        concept_id="string-functions",
        pattern_name="Missing Comma in CONCAT Function",
        learner_symptom="Wrong number of arguments or syntax error in CONCAT",
        likely_prereq_failure="select-basic",
        sql_pattern=r"CONCAT\s*\(\s*\w+\s+\w+",
        remediation_order=1,
        example_bad_sql="SELECT CONCAT(first_name last_name) FROM employees; -- missing comma",
        example_good_sql="SELECT CONCAT(first_name, ' ', last_name) FROM employees;",
        common_error_messages=[
            "wrong number of arguments",
            "syntax error",
        ],
        related_patterns=["string_function_concat_vs_pipe_v1"],
    ),
    
    MisconceptionPattern(
        pattern_id="string_function_case_confusion_v1",
        error_subtype_id="string_function_misuse",
        concept_id="string-functions",
        pattern_name="UPPER vs LOWER Function Confusion",
        learner_symptom="Case-insensitive search not working as expected",
        likely_prereq_failure="where-clause",
        sql_pattern=r"WHERE\s+UPPER\s*\(\s*\w+\s*\)\s*=\s*'[a-z]+",
        remediation_order=2,
        example_bad_sql="SELECT * FROM users WHERE UPPER(name) = 'john'; -- comparing uppercase to lowercase literal",
        example_good_sql="SELECT * FROM users WHERE UPPER(name) = 'JOHN'; -- both sides uppercase",
        common_error_messages=[
            "no rows returned",
            "unexpected empty result",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # Date Functions Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="date_format_mismatch_v1",
        error_subtype_id="date_format_error",
        concept_id="date-functions",
        pattern_name="Date Format Mismatch in Comparison",
        learner_symptom="Date format is not recognized or invalid date value",
        likely_prereq_failure="where-clause",
        sql_pattern=r"WHERE\s+\w+\s*=\s*'\d{2}[/-]\d{2}[/-]\d{2,4}'",
        remediation_order=2,
        example_bad_sql="SELECT * FROM orders WHERE order_date = '01/15/2023'; -- wrong format, use ISO 8601",
        example_good_sql="SELECT * FROM orders WHERE order_date = '2023-01-15'; -- ISO format",
        common_error_messages=[
            "date format is not recognized",
            "invalid date value",
            "date/time field value out of range",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="date_function_string_literal_v1",
        error_subtype_id="date_format_error",
        concept_id="date-functions",
        pattern_name="Date String Without Proper Casting",
        learner_symptom="Operator does not exist when comparing date to string",
        likely_prereq_failure="data-types",
        sql_pattern=r"WHERE\s+\w+\s*[<>=]\s*'\d{4}-\d{2}-\d{2}'",
        remediation_order=2,
        example_bad_sql="SELECT * FROM events WHERE event_date > '2023-01-01'; -- implicit string comparison",
        example_good_sql="SELECT * FROM events WHERE event_date > DATE('2023-01-01'); -- explicit date conversion",
        common_error_messages=[
            "operator does not exist: date > text",
            "invalid input syntax for type date",
        ],
        related_patterns=["date_format_mismatch_v1"],
    ),
    
    MisconceptionPattern(
        pattern_id="date_function_wrong_function_v1",
        error_subtype_id="date_function_misuse",
        concept_id="date-functions",
        pattern_name="Using Wrong Date Function for Task",
        learner_symptom="Unexpected date calculation results",
        likely_prereq_failure="date-functions",
        sql_pattern=r"SELECT\s+.*DAY\s*\(\s*\w+\s*\)",
        remediation_order=2,
        example_bad_sql="SELECT DAY(order_date) FROM orders; -- extracts day number, not day of week",
        example_good_sql="SELECT DAYOFWEEK(order_date) FROM orders; -- get day of week",
        common_error_messages=[
            "unexpected date result",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # Data Types Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="string_number_comparison_v1",
        error_subtype_id="string_number_mismatch",
        concept_id="data-types",
        pattern_name="String vs Number Comparison Mismatch",
        learner_symptom="Unexpected results when comparing string column to number",
        likely_prereq_failure="where-clause",
        sql_pattern=r"WHERE\s+\w+\s*[=<>]\s*'\d+'",
        remediation_order=2,
        example_bad_sql="SELECT * FROM users WHERE age > '50';  -- age is VARCHAR, comparing string to number",
        example_good_sql="SELECT * FROM users WHERE CAST(age AS INT) > 50;",
        common_error_messages=[
            "operator does not exist",
            "invalid input syntax",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="date_format_confusion_v1",
        error_subtype_id="date_format_error",
        concept_id="data-types",
        pattern_name="Date Format Confusion",
        learner_symptom="Date format is not recognized or invalid date value",
        likely_prereq_failure="where-clause",
        sql_pattern=r"WHERE\s+\w+\s*=\s*'\d{2}[/-]\d{2}[/-]\d{2,4}'",
        remediation_order=2,
        example_bad_sql="SELECT * FROM orders WHERE order_date = '01/15/2023';  -- wrong format",
        example_good_sql="SELECT * FROM orders WHERE order_date = '2023-01-15';  -- ISO format",
        common_error_messages=[
            "date format is not recognized",
            "invalid date value",
        ],
        related_patterns=["date_format_mismatch_v1"],
    ),
    
    MisconceptionPattern(
        pattern_id="implicit_type_conversion_v1",
        error_subtype_id="implicit_type_conversion",
        concept_id="data-types",
        pattern_name="Unexpected Implicit Type Conversion",
        learner_symptom="Query returns unexpected results due to type coercion",
        likely_prereq_failure="where-clause",
        sql_pattern=r"SELECT\s+.*\w+\s*\+\s*\w+.*FROM",
        remediation_order=3,
        example_bad_sql="SELECT '10' + 5 FROM dual;  -- Results in 15, not '105'",
        example_good_sql="SELECT CONCAT('10', '5') FROM dual;  -- Results in '105'",
        common_error_messages=[
            "implicit conversion",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # Indexes Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="function_on_indexed_column_v1",
        error_subtype_id="missing_index_optimization",
        concept_id="indexes",
        pattern_name="Function on Indexed Column Prevents Index Usage",
        learner_symptom="Query is slow despite index existing on column",
        likely_prereq_failure="where-clause",
        sql_pattern=r"WHERE\s+(YEAR|MONTH|UPPER|LOWER)\s*\(\s*\w+\s*\)",
        remediation_order=2,
        example_bad_sql="SELECT * FROM orders WHERE YEAR(order_date) = 2023;  -- function prevents index use",
        example_good_sql="SELECT * FROM orders WHERE order_date >= '2023-01-01' AND order_date < '2024-01-01';",
        common_error_messages=[
            "query performance issue",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="leading_wildcard_index_v1",
        error_subtype_id="missing_index_optimization",
        concept_id="indexes",
        pattern_name="Leading Wildcard Prevents Index Usage",
        learner_symptom="LIKE query with leading % is slow even with index",
        likely_prereq_failure="pattern-matching",
        sql_pattern=r"LIKE\s+'%[^']*'",
        remediation_order=2,
        example_bad_sql="SELECT * FROM users WHERE name LIKE '%Smith';  -- leading wildcard",
        example_good_sql="SELECT * FROM users WHERE name LIKE 'Smith%';  -- trailing wildcard uses index",
        common_error_messages=[
            "query performance issue",
        ],
        related_patterns=["like_wildcard_confusion_v1"],
    ),
    
    # =========================================================================
    # Transactions Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="missing_transaction_boundaries_v1",
        error_subtype_id="missing_transaction_boundaries",
        concept_id="transactions",
        pattern_name="Missing Transaction Boundaries",
        learner_symptom="Partial updates occur when errors happen mid-operation",
        likely_prereq_failure=None,
        sql_pattern=r"UPDATE\s+\w+.*;\s*UPDATE\s+\w+",
        remediation_order=2,
        example_bad_sql="UPDATE account SET balance = balance - 100 WHERE id = 1; UPDATE account SET balance = balance + 100 WHERE id = 2;  -- not atomic",
        example_good_sql="BEGIN; UPDATE account SET balance = balance - 100 WHERE id = 1; UPDATE account SET balance = balance + 100 WHERE id = 2; COMMIT;",
        common_error_messages=[
            "inconsistent data state",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="missing_commit_v1",
        error_subtype_id="missing_transaction_boundaries",
        concept_id="transactions",
        pattern_name="Missing COMMIT After Changes",
        learner_symptom="Changes not visible to other sessions after update",
        likely_prereq_failure=None,
        sql_pattern=r"BEGIN.*(?!COMMIT)",
        remediation_order=1,
        example_bad_sql="BEGIN; UPDATE users SET status = 'active' WHERE id = 1;  -- forgot COMMIT",
        example_good_sql="BEGIN; UPDATE users SET status = 'active' WHERE id = 1; COMMIT;",
        common_error_messages=[
            "uncommitted transaction",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # Views Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="view_as_table_insert_v1",
        error_subtype_id="view_table_confusion",
        concept_id="views",
        pattern_name="Trying to Insert Into Non-Updatable View",
        learner_symptom="View is not updatable error when trying to insert",
        likely_prereq_failure="insert-statement",
        sql_pattern=r"INSERT\s+INTO\s+\w+\s+VALUES",
        remediation_order=2,
        example_bad_sql="INSERT INTO high_earners VALUES (...);  -- view with GROUP BY",
        example_good_sql="INSERT INTO employees VALUES (...);  -- insert into base table",
        common_error_messages=[
            "view is not updatable",
            "cannot insert into view",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="view_column_ambiguous_v1",
        error_subtype_id="view_column_reference_error",
        concept_id="views",
        pattern_name="Ambiguous Column Reference in View",
        learner_symptom="Column reference is ambiguous in view query",
        likely_prereq_failure="joins-intro",
        sql_pattern=r"CREATE\s+VIEW.*AS\s+SELECT.*FROM.*JOIN",
        remediation_order=2,
        example_bad_sql="CREATE VIEW emp_dept AS SELECT id, name FROM employees e JOIN departments d ON e.dept_id = d.id;  -- ambiguous id",
        example_good_sql="CREATE VIEW emp_dept AS SELECT e.id AS emp_id, e.name FROM employees e JOIN departments d ON e.dept_id = d.id;",
        common_error_messages=[
            "column reference is ambiguous",
        ],
        related_patterns=["ambiguous_column_reference_v1"],
    ),
    
    # =========================================================================
    # Window Functions Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="window_in_where_v1",
        error_subtype_id="window_function_in_where",
        concept_id="window-functions",
        pattern_name="Window Function in WHERE Clause",
        learner_symptom="Window functions are not allowed in WHERE clause",
        likely_prereq_failure="where-clause",
        sql_pattern=r"WHERE\s+.*(RANK|ROW_NUMBER|DENSE_RANK|LEAD|LAG)\s*\(",
        remediation_order=2,
        example_bad_sql="SELECT * FROM employees WHERE RANK() OVER (ORDER BY salary) <= 10;",
        example_good_sql="WITH ranked AS (SELECT *, RANK() OVER (ORDER BY salary) as r FROM employees) SELECT * FROM ranked WHERE r <= 10;",
        common_error_messages=[
            "window functions are not allowed in WHERE",
            "window function not allowed",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="missing_partition_clause_v1",
        error_subtype_id="missing_partition_clause",
        concept_id="window-functions",
        pattern_name="Missing PARTITION BY When Grouping Needed",
        learner_symptom="Window function ranks entire result set instead of groups",
        likely_prereq_failure="group-by",
        sql_pattern=r"(RANK|ROW_NUMBER|DENSE_RANK)\s*\(\s*\)\s+OVER\s*\(\s*ORDER\s+BY",
        remediation_order=2,
        example_bad_sql="SELECT dept, RANK() OVER (ORDER BY salary) FROM employees;  -- ranks globally",
        example_good_sql="SELECT dept, RANK() OVER (PARTITION BY dept ORDER BY salary) FROM employees;  -- ranks per department",
        common_error_messages=[
            "unexpected ranking results",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="window_function_in_group_by_v1",
        error_subtype_id="window_function_with_group_by",
        concept_id="window-functions",
        pattern_name="Window Function with GROUP BY Confusion",
        learner_symptom="Cannot use window function with GROUP BY",
        likely_prereq_failure="group-by",
        sql_pattern=r"GROUP\s+BY.*(RANK|ROW_NUMBER|SUM|AVG)\s*\(\s*\)\s+OVER",
        remediation_order=3,
        example_bad_sql="SELECT dept, RANK() OVER (ORDER BY AVG(salary)) FROM employees GROUP BY dept;",
        example_good_sql="SELECT dept, AVG(salary) as avg_sal, RANK() OVER (ORDER BY AVG(salary)) FROM employees GROUP BY dept;",
        common_error_messages=[
            "window function not allowed in GROUP BY",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # Isolation Levels Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="dirty_read_risk_v1",
        error_subtype_id="isolation_level_risk",
        concept_id="isolation-levels",
        pattern_name="Dirty Read Risk with Low Isolation",
        learner_symptom="Reading uncommitted data that may be rolled back",
        likely_prereq_failure="transactions",
        sql_pattern=r"SET\s+TRANSACTION\s+ISOLATION\s+LEVEL\s+READ\s+UNCOMMITTED",
        remediation_order=2,
        example_bad_sql="SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED; SELECT * FROM accounts WHERE id = 1;  -- may read dirty data",
        example_good_sql="SET TRANSACTION ISOLATION LEVEL READ COMMITTED; SELECT * FROM accounts WHERE id = 1;  -- only committed data",
        common_error_messages=[
            "dirty read detected",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="lost_update_risk_v1",
        error_subtype_id="isolation_level_risk",
        concept_id="isolation-levels",
        pattern_name="Lost Update Risk",
        learner_symptom="Concurrent updates overwrite each other",
        likely_prereq_failure="transactions",
        sql_pattern=r"BEGIN.*SELECT.*UPDATE",
        remediation_order=3,
        example_bad_sql="BEGIN; SELECT balance FROM accounts WHERE id = 1; -- balance=100 -- (in another session: update to 120) UPDATE accounts SET balance = 110 WHERE id = 1; COMMIT;  -- lost the 120 update",
        example_good_sql="BEGIN; SELECT balance FROM accounts WHERE id = 1 FOR UPDATE; UPDATE accounts SET balance = 110 WHERE id = 1; COMMIT;  -- locks row during read",
        common_error_messages=[
            "lost update",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # Stored Procedures Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="procedure_parameter_confusion_v1",
        error_subtype_id="procedure_parameter_error",
        concept_id="stored-procedures",
        pattern_name="Stored Procedure Parameter Order Confusion",
        learner_symptom="Procedure executed with wrong parameter values",
        likely_prereq_failure=None,
        sql_pattern=r"CALL\s+\w+\s*\([^)]+\)",
        remediation_order=2,
        example_bad_sql="CALL transfer_money(100, 5, 10);  -- which is source, which is target?",
        example_good_sql="CALL transfer_money(amount => 100, from_account => 5, to_account => 10);  -- named parameters",
        common_error_messages=[
            "wrong number of parameters",
            "parameter type mismatch",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="missing_procedure_error_handling_v1",
        error_subtype_id="procedure_error_handling",
        concept_id="stored-procedures",
        pattern_name="Missing Error Handling in Procedure",
        learner_symptom="Procedure fails without proper error handling or rollback",
        likely_prereq_failure="transactions",
        sql_pattern=r"CREATE\s+(?:PROCEDURE|FUNCTION).*BEGIN.*(?!EXCEPTION|CATCH|HANDLER)",
        remediation_order=3,
        example_bad_sql="CREATE PROCEDURE transfer_money(IN amount DECIMAL) BEGIN UPDATE accounts SET balance = balance - amount; UPDATE accounts SET balance = balance + amount; END;  -- no error handling",
        example_good_sql="CREATE PROCEDURE transfer_money(IN amount DECIMAL) BEGIN DECLARE EXIT HANDLER FOR SQLEXCEPTION ROLLBACK; START TRANSACTION; UPDATE accounts SET balance = balance - amount; UPDATE accounts SET balance = balance + amount; COMMIT; END;",
        common_error_messages=[
            "procedure execution failed",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # Triggers Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="trigger_mutating_table_v1",
        error_subtype_id="trigger_mutating_table_error",
        concept_id="triggers",
        pattern_name="Mutating Table Error in Trigger",
        learner_symptom="Table is mutating, trigger may not see it error",
        likely_prereq_failure="constraints",
        sql_pattern=r"CREATE\s+TRIGGER.*SELECT.*FROM.*NEW|OLD",
        remediation_order=3,
        example_bad_sql="CREATE TRIGGER check_total AFTER INSERT ON order_items FOR EACH ROW BEGIN SELECT SUM(quantity) FROM order_items WHERE order_id = NEW.order_id; END;  -- mutating table",
        example_good_sql="CREATE TRIGGER check_total AFTER INSERT ON order_items FOR EACH ROW BEGIN -- Use a separate table or avoid querying the mutating table -- Consider using a view or computed column instead END;",
        common_error_messages=[
            "table is mutating",
            "trigger may not see it",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="trigger_row_statement_confusion_v1",
        error_subtype_id="trigger_timing_error",
        concept_id="triggers",
        pattern_name="Row vs Statement Trigger Confusion",
        learner_symptom="Trigger fires unexpectedly or only once for multiple rows",
        likely_prereq_failure=None,
        sql_pattern=r"CREATE\s+TRIGGER.*FOR\s+EACH\s+STATEMENT",
        remediation_order=2,
        example_bad_sql="CREATE TRIGGER log_changes AFTER UPDATE ON users FOR EACH STATEMENT INSERT INTO audit_log VALUES (NOW(), 'users updated');  -- fires once per statement",
        example_good_sql="CREATE TRIGGER log_changes AFTER UPDATE ON users FOR EACH ROW INSERT INTO audit_log VALUES (NOW(), NEW.id, 'user updated');  -- fires once per row",
        common_error_messages=[
            "trigger fired unexpectedly",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # Subquery in SELECT Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="scalar_subquery_multiple_rows_v1",
        error_subtype_id="scalar_subquery_multiple_rows",
        concept_id="subquery-in-select",
        pattern_name="Scalar Subquery Returns Multiple Rows",
        learner_symptom="Subquery returns more than one row in SELECT clause",
        likely_prereq_failure="subqueries-intro",
        sql_pattern=r"SELECT\s+.*\(\s*SELECT.*FROM",
        remediation_order=2,
        example_bad_sql="SELECT name, (SELECT dept_name FROM departments) FROM employees;  -- multiple rows",
        example_good_sql="SELECT name, (SELECT dept_name FROM departments WHERE id = e.dept_id) FROM employees e;",
        common_error_messages=[
            "subquery returns more than one row",
        ],
        related_patterns=["subquery_multiple_rows_v1"],
    ),
    
    MisconceptionPattern(
        pattern_id="correlated_subquery_no_reference_v1",
        error_subtype_id="correlated_subquery_reference_error",
        concept_id="subquery-in-select",
        pattern_name="Correlated Subquery Missing Outer Reference",
        learner_symptom="Subquery returns same value for all rows",
        likely_prereq_failure="correlated-subquery",
        sql_pattern=r"SELECT\s+.*\(\s*SELECT\s+\w+\s+FROM\s+\w+\s+WHERE",
        remediation_order=2,
        example_bad_sql="SELECT e.name, (SELECT AVG(salary) FROM employees WHERE dept_id = dept_id) FROM employees e;  -- ambiguous dept_id",
        example_good_sql="SELECT e.name, (SELECT AVG(salary) FROM employees WHERE dept_id = e.dept_id) FROM employees e;  -- references outer table",
        common_error_messages=[
            "unexpected same values",
        ],
        related_patterns=[],
    ),
    
    # =========================================================================
    # Subquery in WHERE Errors
    # =========================================================================
    
    MisconceptionPattern(
        pattern_id="in_subquery_null_handling_v1",
        error_subtype_id="in_subquery_null_issue",
        concept_id="subquery-in-where",
        pattern_name="IN Subquery with NULL Values",
        learner_symptom="IN subquery returns unexpected results due to NULL",
        likely_prereq_failure="null-handling",
        sql_pattern=r"WHERE\s+\w+\s+IN\s*\(\s*SELECT",
        remediation_order=3,
        example_bad_sql="SELECT * FROM employees WHERE manager_id IN (SELECT manager_id FROM departments WHERE location IS NULL);  -- NULL in result",
        example_good_sql="SELECT * FROM employees WHERE manager_id IN (SELECT manager_id FROM departments WHERE location IS NULL) OR manager_id IS NULL;",
        common_error_messages=[
            "unexpected exclusion of rows",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="not_in_with_null_v1",
        error_subtype_id="not_in_null_issue",
        concept_id="subquery-in-where",
        pattern_name="NOT IN with NULL Returns No Rows",
        learner_symptom="NOT IN subquery returns empty result unexpectedly",
        likely_prereq_failure="null-handling",
        sql_pattern=r"WHERE\s+\w+\s+NOT\s+IN\s*\(\s*SELECT",
        remediation_order=3,
        example_bad_sql="SELECT * FROM employees WHERE dept_id NOT IN (SELECT dept_id FROM inactive_departments);  -- returns nothing if inactive_departments has NULL",
        example_good_sql="SELECT * FROM employees e WHERE NOT EXISTS (SELECT 1 FROM inactive_departments i WHERE i.dept_id = e.dept_id);  -- use NOT EXISTS instead",
        common_error_messages=[
            "NOT IN returns unexpected empty result",
        ],
        related_patterns=[],
    ),
    
    MisconceptionPattern(
        pattern_id="correlated_subquery_exists_confusion_v1",
        error_subtype_id="exists_subquery_confusion",
        concept_id="subquery-in-where",
        pattern_name="EXISTS vs IN Subquery Confusion",
        learner_symptom="Using IN when EXISTS would be more appropriate",
        likely_prereq_failure="exists-operator",
        sql_pattern=r"WHERE\s+\w+\s+IN\s*\(\s*SELECT\s+1\s+FROM",
        remediation_order=2,
        example_bad_sql="SELECT * FROM departments d WHERE d.id IN (SELECT 1 FROM employees e WHERE e.dept_id = d.dept_id);  -- using IN with constant",
        example_good_sql="SELECT * FROM departments d WHERE EXISTS (SELECT 1 FROM employees e WHERE e.dept_id = d.dept_id);  -- semantically correct",
        common_error_messages=[
            "performance issue",
        ],
        related_patterns=["exists_with_columns_v1"],
    ),
]


# Mapping from error subtype IDs to their primary concept IDs
ERROR_SUBTYPE_TO_CONCEPT: dict[str, str] = {
    # select-basic
    "missing_comma_in_select": "select-basic",
    "extra_comma_in_select": "select-basic",
    
    # where-clause
    "incorrect_null_comparison": "where-clause",
    "missing_where_clause": "where-clause",
    "string_literal_error": "where-clause",
    
    # joins-intro
    "missing_join_condition": "joins-intro",
    "incorrect_join_type": "joins-intro",
    "ambiguous_column_reference": "joins-intro",
    "missing_table_alias": "joins-intro",
    
    # inner-join
    "inner_join_excludes_nulls": "inner-join",
    
    # outer-join
    "outer_join_wrong_direction": "outer-join",
    
    # self-join
    "self_join_missing_alias": "self-join",
    
    # cross-join
    "unintentional_cartesian_product": "cross-join",
    
    # group-by
    "missing_group_by": "group-by",
    
    # having-clause
    "having_without_group_by": "having-clause",
    "where_having_confusion": "having-clause",
    
    # aggregate-functions
    "incorrect_aggregate_function": "aggregate-functions",
    "aggregate_without_group_by": "aggregate-functions",
    "aggregate_in_where_clause": "aggregate-functions",
    
    # subqueries-intro
    "subquery_multiple_rows": "subqueries-intro",
    
    # correlated-subquery
    "correlated_subquery_reference_error": "correlated-subquery",
    
    # exists-operator
    "exists_with_select_star": "exists-operator",
    
    # null-handling
    "null_arithmetic_error": "null-handling",
    "null_aggregate_ignored": "null-handling",
    
    # pattern-matching
    "like_wildcard_misuse": "pattern-matching",
    "like_pattern_syntax": "pattern-matching",
    
    # order-by
    "order_by_position_out_of_range": "order-by",
    "order_by_clause_order": "order-by",
    
    # limit-offset
    "limit_negative_value": "limit-offset",
    "limit_without_order_by": "limit-offset",
    
    # alias
    "alias_reference_in_where": "alias",
    "alias_syntax_error": "alias",
    
    # distinct
    "distinct_scope_misunderstanding": "distinct",
    "distinct_placement_error": "distinct",
    
    # union
    "union_column_count_mismatch": "union",
    "union_vs_union_all_confusion": "union",
    
    # insert-statement
    "insert_column_count_mismatch": "insert-statement",
    "insert_missing_column_list": "insert-statement",
    
    # update-statement
    "update_set_syntax_error": "update-statement",
    "update_subquery_error": "update-statement",
    
    # delete-statement
    "delete_alias_syntax": "delete-statement",
    "delete_all_rows_risk": "delete-statement",
    
    # create-table
    "create_table_duplicate_column": "create-table",
    "create_table_syntax_error": "create-table",
    
    # alter-table
    "alter_table_drop_column": "alter-table",
    "alter_table_column_exists": "alter-table",
    
    # drop-table
    "drop_table_if_exists": "drop-table",
    "drop_table_dependencies": "drop-table",
    
    # constraints
    "constraint_violation": "constraints",
    "null_in_constraint_column": "constraints",
    
    # data-types
    "string_number_mismatch": "data-types",
    "date_format_error": "data-types",
    "implicit_type_conversion": "data-types",
    
    # indexes
    "missing_index_optimization": "indexes",
    
    # transactions
    "missing_transaction_boundaries": "transactions",
    
    # views
    "view_table_confusion": "views",
    "view_column_reference_error": "views",
    
    # window-functions
    "window_function_in_where": "window-functions",
    "missing_partition_clause": "window-functions",
    "window_function_with_group_by": "window-functions",
    
    # isolation-levels
    "isolation_level_risk": "isolation-levels",
    
    # stored-procedures
    "procedure_parameter_error": "stored-procedures",
    "procedure_error_handling": "stored-procedures",
    
    # triggers
    "trigger_mutating_table_error": "triggers",
    "trigger_timing_error": "triggers",
    
    # subquery-in-select
    "scalar_subquery_multiple_rows": "subquery-in-select",
    
    # subquery-in-where
    "in_subquery_null_issue": "subquery-in-where",
    "not_in_null_issue": "subquery-in-where",
    "exists_subquery_confusion": "subquery-in-where",
    
    # primary-key (new)
    "duplicate_primary_key": "primary-key",
    "primary_key_null_violation": "primary-key",
    "auto_increment_misuse": "primary-key",
    
    # foreign-key (new)
    "foreign_key_violation": "foreign-key",
    "foreign_key_delete_violation": "foreign-key",
    
    # string-functions (new)
    "string_function_syntax_error": "string-functions",
    "string_function_misuse": "string-functions",
    
    # date-functions (new)
    "date_function_misuse": "date-functions",
    
    # cte (new)
    "cte_undefined_reference": "cte",
    "cte_syntax_error": "cte",
    "cte_recursive_error": "cte",
    
    # intersect-except (new)
    "set_operation_column_mismatch": "intersect-except",
    "set_operation_vs_join_confusion": "intersect-except",
    "except_vs_not_exists_confusion": "intersect-except",
    
    # merge-upsert (new)
    "merge_operation_conflict": "merge-upsert",
    "merge_syntax_error": "merge-upsert",
    "upsert_duplicate_key": "merge-upsert",
    
    # database-design (new)
    "missing_primary_key": "database-design",
    "denormalization_issue": "database-design",
    "missing_foreign_key": "database-design",
    
    # erd-basics (new)
    "erd_relationship_error": "erd-basics",
    "erd_cardinality_error": "erd-basics",
    
    # first-normal-form (new)
    "first_normal_form_violation": "first-normal-form",
    
    # second-normal-form (new)
    "second_normal_form_violation": "second-normal-form",
    
    # third-normal-form (new)
    "third_normal_form_violation": "third-normal-form",
    
    # normalization (new)
    "over_normalization": "normalization",
    "normalization_ignored": "normalization",
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
