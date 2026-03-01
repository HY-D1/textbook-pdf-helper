"""
JSON Schema and SQL Validators for Pedagogical Content.

This module provides validation functions to ensure:
- Generated content matches expected JSON schema
- SQL snippets are syntactically valid
- Practice schemas are from the approved list
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

# Import our models
from .pedagogical_models import (
    PedagogicalConcept,
    SQLExample,
    Mistake,
    ValidationError as ModelValidationError,
)

# Import practice schemas from prompts
from .prompts import PRACTICE_SCHEMAS


# =============================================================================
# DATA CLASSES FOR VALIDATION RESULTS
# =============================================================================

@dataclass
class SQLValidationResult:
    """Result of SQL validation."""
    is_valid: bool
    sql_type: str = "unknown"  # SELECT, INSERT, UPDATE, DELETE, etc.
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    def add_issue(self, issue: str) -> None:
        """Add an issue and mark as invalid."""
        self.issues.append(issue)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        """Add a warning (doesn't affect validity)."""
        self.warnings.append(warning)


@dataclass
class ValidationResult:
    """Result of concept JSON validation."""
    is_valid: bool
    errors: list[ModelValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sql_validation_results: dict[str, SQLValidationResult] = field(default_factory=dict)
    
    def add_error(self, field: str, error: str, value: str = "") -> None:
        """Add a validation error."""
        self.errors.append(ModelValidationError(
            field=field,
            error=error,
            value=value[:100] if value else ""  # Truncate long values
        ))
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        """Add a validation warning."""
        self.warnings.append(warning)
    
    def add_sql_result(self, field: str, result: SQLValidationResult) -> None:
        """Add SQL validation result for a field."""
        self.sql_validation_results[field] = result
        if not result.is_valid:
            self.is_valid = False


# =============================================================================
# ALLOWED SCHEMAS
# =============================================================================

# Valid practice schema names
ALLOWED_SCHEMAS: set[str] = set(PRACTICE_SCHEMAS.keys()) if PRACTICE_SCHEMAS else {
    "users", "orders", "products", "employees", "departments", "categories"
}

# Valid SQL keywords for basic validation
VALID_SQL_KEYWORDS = [
    "SELECT", "FROM", "WHERE", "INSERT", "UPDATE", "DELETE", "CREATE",
    "ALTER", "DROP", "JOIN", "INNER", "LEFT", "RIGHT", "OUTER", "FULL",
    "ON", "GROUP", "BY", "ORDER", "HAVING", "LIMIT", "OFFSET",
    "AND", "OR", "NOT", "NULL", "IS", "IN", "EXISTS", "BETWEEN",
    "LIKE", "AS", "DISTINCT", "ALL", "UNION", "INTERSECT", "EXCEPT",
    "WITH", "CASE", "WHEN", "THEN", "ELSE", "END", "VALUES", "SET",
    "INTO", "TABLE", "INDEX", "VIEW", "TRIGGER", "FUNCTION", "PROCEDURE"
]


# =============================================================================
# SQL VALIDATION FUNCTIONS
# =============================================================================

def validate_sql_snippet(sql: str, allow_partial: bool = False) -> SQLValidationResult:
    """
    Validate a SQL snippet for basic syntax correctness.
    
    Args:
        sql: The SQL query to validate
        allow_partial: If True, allows incomplete statements (for educational examples)
        
    Returns:
        SQLValidationResult with validity status and any issues
    """
    result = SQLValidationResult(is_valid=True)
    
    if not sql or not sql.strip():
        result.add_issue("SQL query is empty")
        return result
    
    sql_clean = sql.strip()
    sql_upper = sql_clean.upper()
    
    # Check for basic SQL injection patterns (safety check)
    dangerous_patterns = [
        r";\s*DROP\s+",
        r";\s*DELETE\s+FROM\s+\w+\s*;?\s*$",  # DELETE without WHERE
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, sql_clean, re.IGNORECASE):
            result.add_warning(f"Potentially dangerous pattern detected: {pattern}")
    
    # Check statement type
    if sql_upper.startswith("SELECT"):
        result.sql_type = "SELECT"
    elif sql_upper.startswith("INSERT"):
        result.sql_type = "INSERT"
    elif sql_upper.startswith("UPDATE"):
        result.sql_type = "UPDATE"
    elif sql_upper.startswith("DELETE"):
        result.sql_type = "DELETE"
    elif sql_upper.startswith("CREATE"):
        result.sql_type = "CREATE"
    elif sql_upper.startswith("ALTER"):
        result.sql_type = "ALTER"
    elif sql_upper.startswith("DROP"):
        result.sql_type = "DROP"
    elif sql_upper.startswith("WITH"):
        result.sql_type = "CTE"
    else:
        result.add_issue(f"Unknown or unsupported SQL statement type: {sql_clean[:50]}")
        return result
    
    # Basic syntax checks
    if not allow_partial:
        # Must end with semicolon
        if not sql_clean.endswith(";"):
            result.add_issue("SQL statement must end with a semicolon (;)")
    
    # Check for balanced parentheses
    open_parens = sql_clean.count("(")
    close_parens = sql_clean.count(")")
    if open_parens != close_parens:
        result.add_issue(f"Unbalanced parentheses: {open_parens} open, {close_parens} close")
    
    # Check for common syntax errors
    syntax_errors = [
        (r"\bFROM\s+FROM\b", "Duplicate FROM clause"),
        (r"\bWHERE\s+WHERE\b", "Duplicate WHERE clause"),
        (r"\bSELECT\s+SELECT\b", "Duplicate SELECT clause"),
        (r"\*\*", "Invalid ** operator"),
        (r"==", "Use single = for equality, not =="),
    ]
    
    for pattern, message in syntax_errors:
        if re.search(pattern, sql_clean, re.IGNORECASE):
            result.add_issue(message)
    
    # Type-specific validation
    if result.sql_type == "SELECT":
        _validate_select(sql_clean, result)
    elif result.sql_type == "INSERT":
        _validate_insert(sql_clean, result)
    elif result.sql_type == "UPDATE":
        _validate_update(sql_clean, result)
    elif result.sql_type == "DELETE":
        _validate_delete(sql_clean, result)
    
    return result


def _validate_select(sql: str, result: SQLValidationResult) -> None:
    """Validate SELECT-specific syntax."""
    sql_upper = sql.upper()
    
    # Check for required clauses
    if "FROM" not in sql_upper:
        result.add_issue("SELECT statement missing FROM clause")
    
    # Check for common mistakes
    if re.search(r"\bWHERE\b.*\bGROUP\b.*\bHAVING\b", sql_upper):
        # This is valid, just checking order
        pass
    
    # Check for SELECT * without caution
    if re.search(r"SELECT\s+\*", sql_upper) and "FROM" in sql_upper:
        result.add_warning("Using SELECT * can be inefficient; consider specifying columns")


def _validate_insert(sql: str, result: SQLValidationResult) -> None:
    """Validate INSERT-specific syntax."""
    sql_upper = sql.upper()
    
    if "INTO" not in sql_upper:
        result.add_issue("INSERT statement missing INTO clause")
    
    if "VALUES" not in sql_upper and "SELECT" not in sql_upper:
        result.add_issue("INSERT statement missing VALUES or SELECT clause")


def _validate_update(sql: str, result: SQLValidationResult) -> None:
    """Validate UPDATE-specific syntax."""
    sql_upper = sql.upper()
    
    if "SET" not in sql_upper:
        result.add_issue("UPDATE statement missing SET clause")
    
    # Warning for UPDATE without WHERE (but not an error - might be intentional)
    if "WHERE" not in sql_upper:
        result.add_warning("UPDATE without WHERE will modify all rows")


def _validate_delete(sql: str, result: SQLValidationResult) -> None:
    """Validate DELETE-specific syntax."""
    sql_upper = sql.upper()
    
    # Warning for DELETE without WHERE
    if "WHERE" not in sql_upper:
        result.add_warning("DELETE without WHERE will remove all rows")


# =============================================================================
# SCHEMA VALIDATION
# =============================================================================

def validate_practice_schema(schema_name: str) -> bool:
    """
    Validate that a schema name is in the allowed list.
    
    Args:
        schema_name: Name of the schema to validate
        
    Returns:
        True if schema is allowed, False otherwise
    """
    if not schema_name:
        return False
    return schema_name.lower() in ALLOWED_SCHEMAS


def get_allowed_schemas() -> list[str]:
    """Get list of allowed schema names."""
    return sorted(list(ALLOWED_SCHEMAS))


# =============================================================================
# CONCEPT JSON VALIDATION
# =============================================================================

def validate_concept_json(data: dict[str, Any]) -> ValidationResult:
    """
    Validate a concept dictionary against the PedagogicalConcept schema.
    
    Args:
        data: Dictionary containing concept data
        
    Returns:
        ValidationResult with validity status and any errors
    """
    result = ValidationResult(is_valid=True)
    
    # First, validate against Pydantic model
    try:
        concept = PedagogicalConcept.model_validate(data)
    except ValidationError as e:
        result.is_valid = False
        for error in e.errors():
            field = ".".join(str(x) for x in error["loc"])
            result.add_error(field, error["msg"], str(error.get("input", "")))
        return result
    
    # Additional custom validations
    
    # Validate all SQL examples
    for i, example in enumerate(concept.examples):
        sql_result = validate_sql_snippet(example.query)
        result.add_sql_result(f"examples[{i}].query", sql_result)
        
        # Validate schema used
        if not validate_practice_schema(example.schema_used):
            result.add_error(
                f"examples[{i}].schema_used",
                f"Unknown schema '{example.schema_used}'. Allowed: {', '.join(sorted(ALLOWED_SCHEMAS))}",
                example.schema_used
            )
    
    # Validate all mistake corrections
    for i, mistake in enumerate(concept.common_mistakes):
        # Validate incorrect SQL (allow partial since it's intentionally wrong)
        incorrect_result = validate_sql_snippet(mistake.incorrect_sql, allow_partial=True)
        result.add_sql_result(f"common_mistakes[{i}].incorrect_sql", incorrect_result)
        
        # Validate correct SQL (must be fully valid)
        correct_result = validate_sql_snippet(mistake.correct_sql)
        result.add_sql_result(f"common_mistakes[{i}].correct_sql", correct_result)
    
    # Validate practice references
    for i, ref in enumerate(concept.practice_references):
        if ref.problem_id and not re.match(r"^[a-zA-Z0-9_-]+$", ref.problem_id):
            result.add_error(
                f"practice_references[{i}].problem_id",
                "Problem ID must contain only alphanumeric characters, underscores, and hyphens",
                ref.problem_id
            )
    
    # Check for minimum content requirements
    if len(concept.definition) < 100:
        result.add_warning("Definition is quite short (recommended: 150-250 words)")
    
    if len(concept.key_points) < 2:
        result.add_warning("Consider adding more key_points (recommended: 3-7)")
    
    if len(concept.examples) < 1:
        result.add_error("concepts.examples", "At least one example is required")
    
    if len(concept.common_mistakes) < 1:
        result.add_warning("Consider adding common_mistakes to help students")
    
    return result


# =============================================================================
# BATCH VALIDATION
# =============================================================================

def validate_concepts_batch(concepts: list[dict[str, Any]]) -> dict[str, ValidationResult]:
    """
    Validate multiple concepts at once.
    
    Args:
        concepts: List of concept dictionaries
        
    Returns:
        Dictionary mapping concept_id to ValidationResult
    """
    results = {}
    for concept_data in concepts:
        concept_id = concept_data.get("concept_id", f"unknown_{len(results)}")
        results[concept_id] = validate_concept_json(concept_data)
    return results


def get_validation_summary(results: dict[str, ValidationResult]) -> dict[str, Any]:
    """
    Get a summary of validation results.
    
    Args:
        results: Dictionary of validation results
        
    Returns:
        Summary statistics
    """
    total = len(results)
    valid = sum(1 for r in results.values() if r.is_valid)
    
    all_errors = []
    for concept_id, result in results.items():
        for error in result.errors:
            all_errors.append({
                "concept_id": concept_id,
                "field": error.field,
                "error": error.error
            })
    
    return {
        "total_concepts": total,
        "valid_concepts": valid,
        "invalid_concepts": total - valid,
        "success_rate": valid / total if total > 0 else 0.0,
        "total_errors": len(all_errors),
        "errors": all_errors[:10]  # First 10 errors only
    }


# =============================================================================
# JSON PARSING HELPERS
# =============================================================================

def safe_parse_json(text: str) -> tuple[bool, dict[str, Any] | None, str]:
    """
    Safely parse JSON from text, handling common LLM output issues.
    
    Args:
        text: Text that should contain JSON
        
    Returns:
        Tuple of (success, parsed_data, error_message)
    """
    if not text or not text.strip():
        return False, None, "Empty text provided"
    
    text = text.strip()
    
    # Try to extract JSON from markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        text = json_match.group(1)
    
    # Try to find JSON object directly
    if text.startswith("{") and text.endswith("}"):
        try:
            data = json.loads(text)
            return True, data, ""
        except json.JSONDecodeError as e:
            return False, None, f"JSON parse error: {e}"
    
    # Try to extract JSON object from text
    json_pattern = r'\{[\s\S]*\}'
    match = re.search(json_pattern, text)
    if match:
        try:
            data = json.loads(match.group(0))
            return True, data, ""
        except json.JSONDecodeError as e:
            return False, None, f"JSON parse error: {e}"
    
    return False, None, "No JSON object found in text"


def extract_json_from_llm_output(text: str) -> dict[str, Any] | None:
    """
    Extract and parse JSON from LLM output text.
    
    Handles various formats that LLMs might produce.
    
    Args:
        text: Raw LLM output text
        
    Returns:
        Parsed dictionary or None if parsing failed
    """
    success, data, _ = safe_parse_json(text)
    return data if success else None
