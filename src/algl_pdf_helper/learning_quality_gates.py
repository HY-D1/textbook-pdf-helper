"""
Quality Gates for Learning Utility Validation.

This module provides comprehensive quality validation for instructional units,
focusing on learning utility rather than just format compliance. It validates:

- Content validity (canonical mapping, source evidence, relevance)
- Example quality (SQL executability, semantic correctness, difficulty)
- Instruction quality (explanations, practice items, takeaways)
- Adaptive readiness (prerequisites, error tags, stage variants)
- Export integrity (no placeholders, learner-ready status)

Usage:
    from algl_pdf_helper.learning_quality_gates import (
        LearningQualityGates,
        QualityReport,
        Severity,
    )
    
    gates = LearningQualityGates()
    report = QualityReport().generate_full_report(unit_library)
    
    if report["overall_passed"]:
        print("Library ready for export!")
    else:
        for rec in report["recommendations"]:
            print(f"Fix: {rec}")
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .instructional_models import (
    InstructionalUnit,
    UnitLibraryExport,
    SourceSpan,
)
from .sql_ontology import ConceptOntology
from .validators import validate_sql_snippet


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class Severity(Enum):
    """Severity levels for quality check failures."""
    
    BLOCKING = "blocking"  # Cannot export - must fix
    WARNING = "warning"    # Can export with notes
    INFO = "info"          # Suggestion for improvement


# Target stage variants for adaptive readiness
TARGET_STAGES = {"L1_hint", "L2_hint_plus_example", "L3_explanation", "L4_reflective_note", "reinforcement"}

# Placeholder patterns to detect
PLACEHOLDER_PATTERNS = [
    r"see\s+textbook",
    r"content\s+could\s+not\s+be\s+extracted",
    r"\[placeholder\s*\]",
    r"\[to\s+be\s+added\s*\]",
    r"\[tbd\s*\]",
    r"\[todo\s*\]",
    r"not\s+available",
    r"coming\s+soon",
]

# Admin/config concept patterns (not teaching-relevant)
ADMIN_CONCEPT_PATTERNS = [
    r"^(preface|introduction|foreword|appendix)",
    r"^(setup|installation|configuration)",
    r"^(about|copyright|acknowledgment)",
    r"^sql\.(history|overview)$",
]

# Heading fragment patterns (titles that look like section headers)
HEADING_FRAGMENT_PATTERNS = [
    r"^\d+\.\d+\s+",  # Section numbers like "3.2 "
    r"^chapter\s+\d+",  # "Chapter 5"
    r"^section\s+\d+",  # "Section 2"
    r"^part\s+[ivx]+",  # "Part IV"
]

# Placeholder content patterns (test data, boilerplate)
PLACEHOLDER_CONTENT_PATTERNS = [
    r"golden\s+reference\s+document",
    r"test\s+string",
    r"lorem\s+ipsum",
    r"sample\s+content",
    r"placeholder\s+text",
    r"your\s+text\s+here",
    r"insert\s+content\s+here",
    r"example\s+text",
]

# Generic "why it matters" patterns (filler content)
GENERIC_WHY_PATTERNS = [
    r"this\s+is\s+important\s+because",
    r"understanding\s+this\s+concept\s+is\s+crucial",
    r"this\s+is\s+a\s+fundamental\s+concept",
    r"it\s+is\s+essential\s+to\s+understand",
    r"this\s+helps\s+you\s+learn\s+sql",
    r"mastering\s+this\s+will\s+help\s+you",
    r"this\s+concept\s+is\s+widely\s+used",
    r"you\s+will\s+use\s+this\s+feature\s+often",
]

# Broken SQL patterns that should fail validation
BROKEN_SQL_PATTERNS = [
    r"^\s*SELECT\s*;?\s*$",  # Just "SELECT" or "SELECT;"
    r"^\s*FROM\s*;?\s*$",    # Just "FROM"
    r"^\s*WHERE\s*;?\s*$",   # Just "WHERE"
    r"^\s*INSERT\s*;?\s*$",  # Just "INSERT"
    r"^\s*UPDATE\s*;?\s*$",  # Just "UPDATE"
    r"^\s*DELETE\s*;?\s*$",  # Just "DELETE"
    r"^\s*JOIN\s*;?\s*$",    # Just "JOIN"
    r"^\s*GROUP\s+BY\s*;?\s*$",  # Just "GROUP BY"
    r"^\s*ORDER\s+BY\s*;?\s*$",  # Just "ORDER BY"
    r"^\s*SELECT\s+\*\s*$",  # "SELECT *" without FROM
]

# Minimum lengths for substantive content
MIN_DEFINITION_LENGTH = 50
MIN_WHY_IT_MATTERS_LENGTH = 40
MIN_EXAMPLE_EXPLANATION_LENGTH = 30


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class QualityCheck:
    """
    Result of a single quality check.
    
    Attributes:
        check_name: Identifier for this check
        passed: Whether the check passed
        score: Quality score 0-1
        message: Human-readable explanation
        severity: BLOCKING, WARNING, or INFO
    """
    
    check_name: str
    passed: bool
    score: float
    message: str
    severity: Severity = Severity.INFO
    
    def __post_init__(self):
        """Validate score is in valid range."""
        self.score = max(0.0, min(1.0, self.score))


@dataclass
class QualityGateResult:
    """
    Aggregated result for a quality gate (collection of related checks).
    
    Attributes:
        passed: True if all blocking checks passed
        gate_name: Name of this gate category
        score: Average score across all checks (0-1)
        checks: List of individual QualityCheck results
        errors: List of error messages (blocking failures)
        warnings: List of warning messages
    """
    
    passed: bool
    gate_name: str
    score: float
    checks: list[QualityCheck] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate score is in valid range."""
        self.score = max(0.0, min(1.0, self.score))


# =============================================================================
# LEARNING QUALITY GATES CLASS
# =============================================================================

class LearningQualityGates:
    """
    Comprehensive quality validation for instructional units.
    
    Validates content for learning utility, not just format compliance.
    Provides methods for all gate categories with detailed scoring.
    
    Example:
        >>> gates = LearningQualityGates()
        >>> check = gates.validate_source_evidence(unit)
        >>> if not check.passed:
        ...     print(f"Issue: {check.message}")
    """
    
    def __init__(self, ontology: ConceptOntology | None = None):
        """
        Initialize the quality gates.
        
        Args:
            ontology: Optional ConceptOntology instance. If not provided,
                     a new one will be created.
        """
        self.ontology = ontology or ConceptOntology()
        self._error_subtype_cache: set[str] | None = None
        self._boilerplate_cache: set[str] = set()  # Track repeated boilerplate
    
    # =====================================================================
    # CONTENT QUALITY HELPER METHODS
    # =====================================================================
    
    def _is_valid_sql_example(self, sql: str) -> bool:
        """
        Check if SQL is valid (not just "SELECT;" etc.).
        
        Args:
            sql: The SQL string to validate
            
        Returns:
            True if SQL appears valid and complete, False otherwise
        """
        if not sql or not sql.strip():
            return False
        
        sql_stripped = sql.strip()
        sql_upper = sql_stripped.upper()
        
        # Check for broken SQL patterns
        for pattern in BROKEN_SQL_PATTERNS:
            if re.search(pattern, sql_upper):
                return False
        
        # Check for placeholder patterns
        for pattern in PLACEHOLDER_PATTERNS:
            if re.search(pattern, sql, re.IGNORECASE):
                return False
        
        # Must have at least one complete clause with identifiers
        # A valid SQL should have keywords AND table/column references
        has_keywords = any(kw in sql_upper for kw in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP'])
        
        # Check for identifiers (not just keywords and punctuation)
        # Remove SQL keywords and punctuation, check if anything substantive remains
        sql_clean = re.sub(r'[;,()\'"]', ' ', sql_upper)
        sql_keywords = ['SELECT', 'FROM', 'WHERE', 'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET', 
                       'DELETE', 'JOIN', 'ON', 'GROUP', 'BY', 'ORDER', 'HAVING', 'LIMIT', 'OFFSET',
                       'CREATE', 'TABLE', 'ALTER', 'DROP', 'ADD', 'AND', 'OR', 'NOT', 'NULL',
                       'IS', 'AS', 'DISTINCT', 'INNER', 'LEFT', 'RIGHT', 'OUTER', 'FULL',
                       'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'EXISTS', 'UNION', 'ALL']
        
        words = [w for w in sql_clean.split() if w and w not in sql_keywords]
        # At least 1 non-keyword identifier (e.g., table name) or wildcard (*) with table
        has_identifiers = len(words) >= 1
        # Also check for minimal structure: SELECT ... FROM ...
        has_basic_structure = 'SELECT' in sql_upper and 'FROM' in sql_upper
        
        return has_keywords and has_identifiers and has_basic_structure
    
    def _is_heading_like(self, text: str) -> tuple[bool, str]:
        """
        Detect if text looks like a chapter/section heading.
        
        Args:
            text: The text to check
            
        Returns:
            Tuple of (is_heading, reason)
        """
        if not text or not text.strip():
            return False, ""
        
        text_stripped = text.strip()
        text_lower = text_stripped.lower()
        
        # Chapter/Section/Part patterns
        heading_patterns = [
            (r"^(Chapter|Section|Part|Unit|Module|Lesson)\s+\d+", "chapter/section title"),
            (r"^\d+\.\d+\s+", "numbered section"),
            (r"^(How to|Working with|Understanding|Introduction to|Overview of)", "instructional heading"),
            (r"^(In this chapter|Learning objectives|Summary|Exercises|Review|Quiz)", "section marker"),
            (r"^[A-Z][a-z]+ing\s+[A-Z]", "gerund phrase heading"),  # "Creating Tables"
            (r"^Reference\s+(Document|Manual|Guide)", "reference marker"),
            (r"^Golden\s+Reference", "reference marker"),
            (r"^Table of Contents", "TOC marker"),
        ]
        
        for pattern, reason in heading_patterns:
            if re.search(pattern, text_stripped, re.IGNORECASE):
                return True, reason
        
        # All uppercase (likely a heading)
        if text_stripped.isupper() and len(text_stripped) > 5:
            return True, "all uppercase"
        
        # Title case without small words (likely a heading)
        words = text_stripped.split()
        if 2 <= len(words) < 10:
            small_words = ['a', 'an', 'the', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'is', 'are', 'with', 'by']
            content_words = [w for w in words if w.isalpha()]
            if content_words:
                capitalized = sum(1 for w in content_words if w[0].isupper())
                if capitalized / len(content_words) > 0.8 and not any(w.lower() in small_words for w in words):
                    return True, "title case without sentence structure"
        
        # Ends with colon (often a heading)
        if text_stripped.endswith(':'):
            return True, "ends with colon"
        
        return False, ""
    
    def _is_placeholder_content(self, content: str) -> tuple[bool, str]:
        """
        Detect placeholder or test content.
        
        Args:
            content: The content to check
            
        Returns:
            Tuple of (is_placeholder, reason)
        """
        if not content or not content.strip():
            return False, ""
        
        content_lower = content.lower()
        
        # Check for placeholder patterns
        for pattern in PLACEHOLDER_CONTENT_PATTERNS:
            if re.search(pattern, content_lower):
                return True, "placeholder content pattern"
        
        # Check for test data indicators
        test_indicators = ['test_', '_test', 'sample_', 'example_', 'dummy']
        for indicator in test_indicators:
            if indicator in content_lower:
                return True, "test data indicator"
        
        return False, ""
    
    def _is_generic_why_it_matters(self, text: str) -> tuple[bool, str]:
        """
        Detect generic filler content in why_it_matters.
        
        Args:
            text: The text to check
            
        Returns:
            Tuple of (is_generic, reason)
        """
        if not text or not text.strip():
            return True, "empty content"
        
        text_stripped = text.strip()
        text_lower = text_stripped.lower()
        
        # Check length
        if len(text_stripped) < MIN_WHY_IT_MATTERS_LENGTH:
            return True, f"too short ({len(text_stripped)} chars, min {MIN_WHY_IT_MATTERS_LENGTH})"
        
        # Check for generic patterns
        for pattern in GENERIC_WHY_PATTERNS:
            if re.search(pattern, text_lower):
                return True, "generic filler pattern"
        
        # Check for vague statements
        vague_phrases = [
            'it is important',
            'this is useful',
            'you need to know',
            'this helps',
            'good to know',
        ]
        for phrase in vague_phrases:
            if phrase in text_lower and len(text_stripped) < 80:
                return True, "vague statement"
        
        return False, ""
    
    def _check_example_appropriateness(self, sql: str, concept_id: str) -> tuple[bool, str]:
        """
        Check if example SQL is appropriate for the concept being taught.
        
        Args:
            sql: The SQL example
            concept_id: The concept ID
            
        Returns:
            Tuple of (is_appropriate, reason)
        """
        if not sql or not sql.strip():
            return False, "empty SQL"
        
        sql_upper = sql.upper()
        
        # Concept-appropriate keyword mappings
        concept_requirements = {
            "select-basic": (["SELECT", "FROM"], "needs SELECT and FROM"),
            "where-clause": (["WHERE"], "should demonstrate WHERE clause"),
            "null-handling": (["NULL", "IS"], "should demonstrate NULL handling"),
            "pattern-matching": (["LIKE"], "should use LIKE operator"),
            "order-by": (["ORDER", "BY"], "should demonstrate ORDER BY"),
            "limit-offset": (["LIMIT"], "should demonstrate LIMIT/OFFSET"),
            "alias": (["AS"], "should demonstrate AS alias"),
            "distinct": (["DISTINCT"], "should use DISTINCT"),
            "inner-join": (["JOIN", "ON"], "should demonstrate JOIN"),
            "outer-join": (["LEFT", "JOIN"], "should demonstrate LEFT/RIGHT JOIN"),
            "self-join": (["JOIN"], "should demonstrate self-join"),
            "aggregate-functions": (["COUNT", "SUM", "AVG", "MIN", "MAX"], "should use aggregate function"),
            "group-by": (["GROUP", "BY"], "should demonstrate GROUP BY"),
            "having-clause": (["HAVING", "GROUP"], "should demonstrate HAVING with GROUP BY"),
            "subqueries-intro": (["SELECT"], "should contain nested SELECT"),
            "correlated-subquery": (["EXISTS"], "should demonstrate EXISTS or correlation"),
            "union": (["UNION"], "should demonstrate UNION"),
            "insert-statement": (["INSERT", "INTO"], "should demonstrate INSERT"),
            "update-statement": (["UPDATE", "SET"], "should demonstrate UPDATE"),
            "delete-statement": (["DELETE", "FROM"], "should demonstrate DELETE"),
            "create-table": (["CREATE", "TABLE"], "should demonstrate CREATE TABLE"),
            "alter-table": (["ALTER", "TABLE"], "should demonstrate ALTER TABLE"),
            "constraints": (["PRIMARY", "FOREIGN", "UNIQUE", "CHECK"], "should demonstrate constraints"),
        }
        
        requirements = concept_requirements.get(concept_id)
        if requirements:
            required_keywords, reason = requirements
            has_any_keyword = any(kw in sql_upper for kw in required_keywords)
            if not has_any_keyword:
                return False, f"Example inappropriate for {concept_id}: {reason}"
        
        return True, ""
    
    def _is_using_default_example(self, sql: str, concept_id: str) -> bool:
        """
        Check if the example appears to be a default/generic example.
        
        Args:
            sql: The SQL example
            concept_id: The concept ID
            
        Returns:
            True if appears to be default example, False otherwise
        """
        if not sql or not sql.strip():
            return True  # Empty is treated as default
        
        sql_upper = sql.upper()
        
        # Common default example patterns
        default_patterns = [
            "SELECT * FROM table",
            "SELECT * FROM users",
            "SELECT * FROM customers",
            "SELECT column FROM table",
        ]
        
        # Normalize SQL for comparison (remove extra whitespace)
        normalized = ' '.join(sql_upper.split())
        
        for pattern in default_patterns:
            if pattern.upper() in normalized:
                return True
        
        # Check for generic table/column names without specificity
        generic_tables = ['TABLE1', 'TABLE2', 'T1', 'T2', 'A', 'B', 'X', 'Y']
        generic_columns = ['COL1', 'COL2', 'C1', 'C2', 'COLUMN1', 'COLUMN2']
        
        has_generic_table = any(f' FROM {t}' in sql_upper or f' JOIN {t}' in sql_upper 
                               for t in generic_tables)
        has_generic_column = any(c in sql_upper for c in generic_columns)
        
        if has_generic_table and has_generic_column:
            return True
        
        return False
    
    def _detect_boilerplate_across_units(self, units: list[InstructionalUnit]) -> dict[str, list[str]]:
        """
        Detect repeated boilerplate content across multiple units.
        
        Args:
            units: List of instructional units
            
        Returns:
            Dictionary mapping boilerplate text to list of concept_ids
        """
        content_occurrences: dict[str, list[str]] = {}
        
        for unit in units:
            content = unit.content or {}
            if not isinstance(content, dict):
                continue
            
            concept_id = unit.concept_id
            
            # Check fields that might have boilerplate
            fields_to_check = ['why_it_matters', 'definition', 'example_explanation', 'hint_text']
            
            for field in fields_to_check:
                text = content.get(field, '')
                if text and len(text) > 20:
                    # Normalize for comparison
                    normalized = text.lower().strip()
                    if normalized not in content_occurrences:
                        content_occurrences[normalized] = []
                    content_occurrences[normalized].append(f"{concept_id}.{field}")
        
        # Find content that appears in 3+ different concepts
        boilerplate = {text: occurrences for text, occurrences in content_occurrences.items() 
                      if len(occurrences) >= 3}
        
        return boilerplate
    
    # =========================================================================
    # CONTENT VALIDITY GATES
    # =========================================================================
    
    def validate_canonical_mapping(
        self,
        unit: InstructionalUnit,
    ) -> QualityCheck:
        """
        Validate that the unit's concept ID exists in the canonical ontology.
        
        Checks:
        - Concept ID exists in ontology
        - Not an admin/reference-only concept
        
        Args:
            unit: The instructional unit to validate
            
        Returns:
            QualityCheck with validation results
        """
        concept_id = unit.concept_id
        
        # Check if concept exists
        if not self.ontology.validate_concept_id(concept_id):
            return QualityCheck(
                check_name="canonical_mapping",
                passed=False,
                score=0.0,
                message=f"Concept '{concept_id}' not found in canonical ontology",
                severity=Severity.BLOCKING,
            )
        
        # Check if it's an admin/reference concept
        concept = self.ontology.get_concept(concept_id)
        if concept and not concept.get("is_core_learning_node", True):
            # Check if it matches admin patterns
            for pattern in ADMIN_CONCEPT_PATTERNS:
                if re.search(pattern, concept_id, re.IGNORECASE):
                    return QualityCheck(
                        check_name="canonical_mapping",
                        passed=False,
                        score=0.5,
                        message=f"Concept '{concept_id}' appears to be admin/reference-only",
                        severity=Severity.WARNING,
                    )
        
        return QualityCheck(
            check_name="canonical_mapping",
            passed=True,
            score=1.0,
            message=f"Concept '{concept_id}' valid in ontology",
            severity=Severity.INFO,
        )
    
    def validate_source_evidence(
        self,
        unit: InstructionalUnit,
        source_blocks: dict[str, Any] | None = None,
    ) -> QualityCheck:
        """
        Validate that the unit has proper source evidence.
        
        Checks:
        - Has at least one evidence span
        - Spans point to actual source blocks
        - Not just placeholder references
        
        Args:
            unit: The instructional unit to validate
            source_blocks: Optional dict mapping block_ids to actual content
            
        Returns:
            QualityCheck with validation results
        """
        evidence_spans = unit.evidence_spans
        
        # Check if any evidence spans exist
        if not evidence_spans:
            return QualityCheck(
                check_name="source_evidence",
                passed=False,
                score=0.0,
                message="No evidence spans provided - content is not grounded",
                severity=Severity.BLOCKING,
            )
        
        # Check for placeholder-only spans
        placeholder_count = 0
        valid_spans = 0
        
        for span in evidence_spans:
            text = span.text_content if isinstance(span, SourceSpan) else str(span)
            is_placeholder = any(
                re.search(pattern, text, re.IGNORECASE)
                for pattern in PLACEHOLDER_PATTERNS
            )
            if is_placeholder:
                placeholder_count += 1
            else:
                valid_spans += 1
        
        # Calculate score based on valid vs placeholder spans
        total_spans = len(evidence_spans)
        score = valid_spans / total_spans if total_spans > 0 else 0.0
        
        # Check if spans point to actual blocks (if source_blocks provided)
        if source_blocks:
            for span in evidence_spans:
                block_id = span.span_id if isinstance(span, SourceSpan) else str(span)
                if block_id not in source_blocks:
                    return QualityCheck(
                        check_name="source_evidence",
                        passed=False,
                        score=score * 0.5,
                        message=f"Evidence span references unknown block: {block_id}",
                        severity=Severity.BLOCKING,
                    )
        
        if placeholder_count == total_spans:
            return QualityCheck(
                check_name="source_evidence",
                passed=False,
                score=0.0,
                message="All evidence spans are placeholders - no actual source content",
                severity=Severity.BLOCKING,
            )
        
        if placeholder_count > 0:
            return QualityCheck(
                check_name="source_evidence",
                passed=True,
                score=score,
                message=f"{placeholder_count}/{total_spans} evidence spans are placeholders",
                severity=Severity.WARNING,
            )
        
        return QualityCheck(
            check_name="source_evidence",
            passed=True,
            score=1.0,
            message=f"All {total_spans} evidence spans are valid source references",
            severity=Severity.INFO,
        )
    
    def validate_content_relevance(self, unit: InstructionalUnit) -> QualityCheck:
        """
        Validate that unit content is teaching-relevant.
        
        Checks:
        - Title is not too long (< 10 words)
        - Title doesn't look like a heading fragment
        - Content is teaching-relevant (not admin/config)
        
        Args:
            unit: The instructional unit to validate
            
        Returns:
            QualityCheck with validation results
        """
        content = unit.content or {}
        title = content.get("title", "") if isinstance(content, dict) else ""
        
        if not title:
            # Try to get title from unit_id if content title missing
            title = unit.unit_id.replace("_", " ").replace("-", " ")
        
        # Check title word count
        word_count = len(title.split())
        if word_count >= 10:
            return QualityCheck(
                check_name="content_relevance",
                passed=False,
                score=0.5,
                message=f"Title too long ({word_count} words, max 9): '{title[:50]}...'",
                severity=Severity.WARNING,
            )
        
        # Check if title looks like a heading fragment
        for pattern in HEADING_FRAGMENT_PATTERNS:
            if re.search(pattern, title, re.IGNORECASE):
                return QualityCheck(
                    check_name="content_relevance",
                    passed=False,
                    score=0.6,
                    message=f"Title appears to be a heading fragment: '{title[:50]}'",
                    severity=Severity.WARNING,
                )
        
        # Check if content is teaching-relevant
        # Look for admin/config patterns in content
        content_str = str(content).lower()
        admin_indicators = [
            "copyright", "all rights reserved", "isbn",
            "published by", "printed in", "dedicated to",
            "acknowledgment", "preface", "foreword",
        ]
        
        admin_matches = sum(1 for indicator in admin_indicators if indicator in content_str)
        if admin_matches >= 2:
            return QualityCheck(
                check_name="content_relevance",
                passed=False,
                score=0.3,
                message="Content appears to be admin/config material, not teaching content",
                severity=Severity.BLOCKING,
            )
        
        # Calculate score based on title quality
        score = 1.0
        if word_count > 7:
            score = 0.8
        elif admin_matches > 0:
            score = 0.7
        
        return QualityCheck(
            check_name="content_relevance",
            passed=True,
            score=score,
            message=f"Content appears teaching-relevant ({word_count} words in title)",
            severity=Severity.INFO,
        )
    
    # =========================================================================
    # EXAMPLE QUALITY GATES
    # =========================================================================
    
    def validate_sql_executable(
        self,
        example_sql: str,
        schema: dict[str, Any] | None = None,
    ) -> QualityCheck:
        """
        Validate that example SQL is syntactically correct and executable.
        
        Checks:
        - SQL parses correctly
        - Executes without errors (if schema provided for validation)
        - Uses allowed practice schemas
        
        Args:
            example_sql: The SQL query to validate
            schema: Optional schema definition for execution testing
            
        Returns:
            QualityCheck with validation results
        """
        if not example_sql or not example_sql.strip():
            return QualityCheck(
                check_name="sql_executable",
                passed=False,
                score=0.0,
                message="SQL is empty or whitespace only",
                severity=Severity.BLOCKING,
            )
        
        sql = example_sql.strip()
        
        # Check for placeholder patterns
        for pattern in PLACEHOLDER_PATTERNS:
            if re.search(pattern, sql, re.IGNORECASE):
                return QualityCheck(
                    check_name="sql_executable",
                    passed=False,
                    score=0.0,
                    message="SQL appears to be a placeholder",
                    severity=Severity.BLOCKING,
                )
        
        # Use existing validator for basic syntax
        validation = validate_sql_snippet(sql)
        
        if not validation.is_valid:
            issues_str = "; ".join(validation.issues[:3])
            return QualityCheck(
                check_name="sql_executable",
                passed=False,
                score=0.3,
                message=f"SQL syntax error: {issues_str}",
                severity=Severity.BLOCKING,
            )
        
        # Try to execute against provided schema (in-memory SQLite)
        if schema:
            try:
                conn = sqlite3.connect(":memory:")
                cursor = conn.cursor()
                
                # Create schema tables
                for table_name, table_def in schema.items():
                    if isinstance(table_def, dict) and "columns" in table_def:
                        cols = table_def["columns"]
                        if cols and isinstance(cols[0], tuple):
                            col_defs = ", ".join(f"{c[0]} {c[1]}" for c in cols)
                        else:
                            col_defs = ", ".join(f"{c} TEXT" for c in cols)
                        cursor.execute(f"CREATE TABLE {table_name} ({col_defs});")
                
                # Try to execute the SQL
                cursor.execute(sql)
                conn.close()
                
            except sqlite3.Error as e:
                return QualityCheck(
                    check_name="sql_executable",
                    passed=False,
                    score=0.5,
                    message=f"SQL execution error: {str(e)[:100]}",
                    severity=Severity.WARNING,
                )
        
        score = 1.0
        if validation.warnings:
            score = 0.9
        
        return QualityCheck(
            check_name="sql_executable",
            passed=True,
            score=score,
            message=f"SQL is valid ({validation.sql_type})" + (f" with {len(validation.warnings)} warnings" if validation.warnings else ""),
            severity=Severity.INFO,
        )
    
    def validate_sql_semantic(
        self,
        example_sql: str,
        concept_id: str,
        schema: dict[str, Any] | None = None,
    ) -> QualityCheck:
        """
        Validate that example SQL semantically aligns with the concept being taught.
        
        Checks:
        - Aligns to concept being taught (uses relevant keywords)
        - No semantically wrong joins
        - Proper use of concept features
        
        Args:
            example_sql: The SQL query to validate
            concept_id: The concept ID this example should demonstrate
            schema: Optional schema for additional validation
            
        Returns:
            QualityCheck with validation results
        """
        if not example_sql or not example_sql.strip():
            return QualityCheck(
                check_name="sql_semantic",
                passed=False,
                score=0.0,
                message="Cannot validate semantic alignment of empty SQL",
                severity=Severity.BLOCKING,
            )
        
        sql_upper = example_sql.upper()
        
        # Concept keyword mappings for semantic validation
        concept_keywords = {
            "select-basic": ["SELECT", "FROM"],
            "where-clause": ["WHERE"],
            "null-handling": ["NULL", "IS"],
            "pattern-matching": ["LIKE"],
            "order-by": ["ORDER", "BY"],
            "limit-offset": ["LIMIT", "OFFSET"],
            "alias": ["AS"],
            "distinct": ["DISTINCT"],
            "inner-join": ["JOIN", "ON"],
            "outer-join": ["LEFT", "RIGHT", "OUTER", "FULL"],
            "self-join": ["JOIN", "ON"],
            "aggregate-functions": ["COUNT", "SUM", "AVG", "MIN", "MAX"],
            "group-by": ["GROUP", "BY"],
            "having-clause": ["HAVING"],
            "subqueries-intro": ["SELECT", "FROM"],
            "correlated-subquery": ["EXISTS", "SELECT", "FROM"],
            "union": ["UNION"],
            "insert-statement": ["INSERT", "INTO"],
            "update-statement": ["UPDATE", "SET"],
            "delete-statement": ["DELETE", "FROM"],
            "create-table": ["CREATE", "TABLE"],
            "alter-table": ["ALTER", "TABLE"],
            "constraints": ["PRIMARY", "FOREIGN", "KEY", "UNIQUE", "CHECK"],
        }
        
        # Check if SQL uses relevant keywords for the concept
        required_keywords = concept_keywords.get(concept_id, [])
        if required_keywords:
            keyword_matches = sum(1 for kw in required_keywords if kw in sql_upper)
            keyword_score = keyword_matches / len(required_keywords)
            
            if keyword_score < 0.5:
                return QualityCheck(
                    check_name="sql_semantic",
                    passed=False,
                    score=0.4,
                    message=f"SQL may not demonstrate '{concept_id}' - missing typical keywords",
                    severity=Severity.WARNING,
                )
        
        # Check for wrong join types
        if concept_id == "inner-join" and ("LEFT" in sql_upper or "RIGHT" in sql_upper):
            return QualityCheck(
                check_name="sql_semantic",
                passed=False,
                score=0.5,
                message="Example for INNER JOIN uses LEFT/RIGHT JOIN",
                severity=Severity.WARNING,
            )
        
        # Check for HAVING without GROUP BY
        if concept_id == "having-clause" and "GROUP" not in sql_upper:
            return QualityCheck(
                check_name="sql_semantic",
                passed=False,
                score=0.4,
                message="HAVING clause example missing GROUP BY",
                severity=Severity.WARNING,
            )
        
        return QualityCheck(
            check_name="sql_semantic",
            passed=True,
            score=1.0,
            message=f"SQL appears semantically aligned with '{concept_id}'",
            severity=Severity.INFO,
        )
    
    def validate_example_difficulty(
        self,
        examples: list[dict[str, Any]],
        target_difficulty: str,
    ) -> QualityCheck:
        """
        Validate that examples match the target difficulty level.
        
        Checks:
        - Examples match target difficulty
        - Progression from simple to complex
        
        Args:
            examples: List of example objects with difficulty info
            target_difficulty: Expected difficulty level
            
        Returns:
            QualityCheck with validation results
        """
        if not examples:
            return QualityCheck(
                check_name="example_difficulty",
                passed=False,
                score=0.0,
                message="No examples to validate",
                severity=Severity.WARNING,
            )
        
        valid_difficulties = {"beginner", "intermediate", "advanced"}
        if target_difficulty not in valid_difficulties:
            return QualityCheck(
                check_name="example_difficulty",
                passed=False,
                score=0.5,
                message=f"Invalid target difficulty: '{target_difficulty}'",
                severity=Severity.WARNING,
            )
        
        # Count matching vs non-matching examples
        matching = 0
        difficulties = []
        
        for ex in examples:
            ex_diff = ex.get("difficulty", target_difficulty) if isinstance(ex, dict) else target_difficulty
            difficulties.append(ex_diff)
            if ex_diff == target_difficulty:
                matching += 1
        
        # Check progression (should go from simpler to more complex)
        has_progression = False
        if len(difficulties) >= 2:
            diff_order = {"beginner": 0, "intermediate": 1, "advanced": 2}
            values = [diff_order.get(d, 1) for d in difficulties]
            # Check if mostly increasing or stable
            increases = sum(1 for i in range(len(values) - 1) if values[i+1] >= values[i])
            has_progression = increases >= len(values) - 2  # Allow one out-of-order
        
        score = matching / len(examples)
        if has_progression:
            score = min(1.0, score + 0.1)
        
        if matching == 0:
            return QualityCheck(
                check_name="example_difficulty",
                passed=False,
                score=score,
                message=f"No examples match target difficulty '{target_difficulty}'",
                severity=Severity.WARNING,
            )
        
        if not has_progression and len(examples) > 2:
            return QualityCheck(
                check_name="example_difficulty",
                passed=True,
                score=score,
                message=f"{matching}/{len(examples)} match difficulty, but no clear progression",
                severity=Severity.INFO,
            )
        
        return QualityCheck(
            check_name="example_difficulty",
            passed=True,
            score=score,
            message=f"{matching}/{len(examples)} examples match difficulty '{target_difficulty}'",
            severity=Severity.INFO,
        )
    
    # =========================================================================
    # INSTRUCTION QUALITY GATES
    # =========================================================================
    
    def validate_explanation_quality(self, unit: InstructionalUnit) -> QualityCheck:
        """
        Validate the quality of explanations in the unit (stage-aware).
        
        Different stages have different explanation requirements:
        - L1_hint: hint_text, syntax_cue, when_to_use
        - L2_hint_plus_example: hint_text, example_sql, example_explanation
        - L3_explanation: definition, why_it_matters, common_mistakes
        - L4_reflective_note: key_concept_summary, reflection_prompts, transfer_questions
        - reinforcement: recall_prompt, quick_check_question, quick_check_answer
        
        Args:
            unit: The instructional unit to validate
            
        Returns:
            QualityCheck with validation results
        """
        content = unit.content or {}
        if not isinstance(content, dict):
            return QualityCheck(
                check_name="explanation_quality",
                passed=False,
                score=0.5,
                message="Content format not supported for explanation validation",
                severity=Severity.WARNING,
            )
        
        target_stage = unit.target_stage
        score = 1.0
        issues = []
        checks = []
        min_score = 0.6
        
        if target_stage == "L1_hint":
            # L1: Check hint quality, syntax cue, when_to_use
            checks = [
                ("hint_text", content.get("hint_text", "")),
                ("syntax_cue", content.get("syntax_cue", "")),
            ]
            min_score = 0.6
            # Optional: when_to_use gives bonus
            if content.get("when_to_use"):
                score = min(1.0, score + 0.1)
                
        elif target_stage == "L2_hint_plus_example":
            # L2: Check hint + example + pitfall
            checks = [
                ("hint_text", content.get("hint_text", "")),
                ("example_sql", content.get("example_sql", "")),
                ("example_explanation", content.get("example_explanation", "")),
            ]
            min_score = 0.6
            
            # NEW: Validate example_sql is valid SQL
            example_sql = content.get("example_sql", "")
            if example_sql:
                if not self._is_valid_sql_example(example_sql):
                    score -= 0.4
                    issues.append("example_sql is invalid or incomplete (e.g., 'SELECT;')")
                else:
                    # NEW: Check example is appropriate for concept
                    is_appropriate, reason = self._check_example_appropriateness(example_sql, unit.concept_id)
                    if not is_appropriate:
                        score -= 0.2
                        issues.append(f"example not appropriate for concept: {reason}")
                
                # NEW: Check for default example usage
                if self._is_using_default_example(example_sql, unit.concept_id):
                    score -= 0.15
                    issues.append("appears to use default/generic example")
            
            # Optional: common_pitfall gives bonus
            if content.get("common_pitfall"):
                score = min(1.0, score + 0.1)
                
        elif target_stage == "L3_explanation":
            # L3: Full explanation criteria
            checks = [
                ("definition", content.get("definition", "")),
                ("why_it_matters", content.get("why_it_matters", "")),
            ]
            min_score = 0.7
            
            # NEW: Check definition doesn't look like heading
            definition = content.get("definition", "")
            if definition:
                is_heading, reason = self._is_heading_like(definition)
                if is_heading:
                    score -= 0.5
                    issues.append(f"definition appears to be heading ({reason})")
                
                # NEW: Check for placeholder content
                is_placeholder, placeholder_reason = self._is_placeholder_content(definition)
                if is_placeholder:
                    score -= 0.4
                    issues.append(f"definition contains placeholder content ({placeholder_reason})")
                
                # Check definition length
                if len(definition.strip()) < MIN_DEFINITION_LENGTH:
                    score -= 0.2
                    issues.append(f"definition too short ({len(definition)} chars, min {MIN_DEFINITION_LENGTH})")
            
            # NEW: Check why_it_matters is substantive
            why_it_matters = content.get("why_it_matters", "")
            if why_it_matters:
                is_generic, generic_reason = self._is_generic_why_it_matters(why_it_matters)
                if is_generic:
                    score -= 0.3
                    issues.append(f"why_it_matters appears generic ({generic_reason})")
            
            # NEW: Verify at least one example has valid SQL
            examples = content.get("examples", [])
            if examples:
                has_valid_sql = False
                for ex in examples:
                    ex_sql = ex.get("sql", "") if isinstance(ex, dict) else str(ex)
                    if self._is_valid_sql_example(ex_sql):
                        has_valid_sql = True
                        break
                if not has_valid_sql:
                    score -= 0.2
                    issues.append("no examples with valid SQL found")
            
            # Check for misconceptions/common mistakes
            common_mistakes = content.get("common_mistakes", [])
            if not common_mistakes and "mistakes" in content:
                common_mistakes = content.get("mistakes", [])
            
            if not common_mistakes:
                score -= 0.3
                issues.append("no misconceptions documented")
            else:
                # Check for repair explanations in mistakes
                has_repair = False
                for mistake in common_mistakes:
                    if isinstance(mistake, dict):
                        if mistake.get("fix_sql") or mistake.get("repair"):
                            has_repair = True
                            break
                
                if not has_repair:
                    score -= 0.2
                    issues.append("misconceptions missing repair explanations")
                
        elif target_stage == "L4_reflective_note":
            # L4: Check summary + reflection + transfer
            checks = [
                ("key_concept_summary", content.get("key_concept_summary", "")),
            ]
            min_score = 0.6
            
            # reflection_prompts and transfer_questions are lists
            reflection_prompts = content.get("reflection_prompts", [])
            transfer_questions = content.get("transfer_questions", [])
            
            if not reflection_prompts:
                score -= 0.2
                issues.append("no reflection prompts")
            if not transfer_questions:
                score -= 0.2
                issues.append("no transfer questions")
                
        elif target_stage == "reinforcement":
            # Reinforcement: Check recall + quick check
            checks = [
                ("recall_prompt", content.get("recall_prompt", "")),
                ("quick_check_question", content.get("quick_check_question", "")),
                ("quick_check_answer", content.get("quick_check_answer", "")),
            ]
            min_score = 0.6
        else:
            # Unknown stage - use L3 as default with warning
            checks = [
                ("definition", content.get("definition", "")),
                ("why_it_matters", content.get("why_it_matters", "")),
            ]
            min_score = 0.7
            issues.append(f"unknown target_stage: {target_stage}")
        
        # Validate the required fields for this stage
        for field_name, field_value in checks:
            if isinstance(field_value, str):
                if not field_value or len(field_value.strip()) < 10:
                    score -= 0.3
                    issues.append(f"missing or insufficient '{field_name}'")
            elif isinstance(field_value, list):
                if not field_value:
                    score -= 0.3
                    issues.append(f"missing '{field_name}'")
            elif not field_value:
                score -= 0.3
                issues.append(f"missing '{field_name}'")
        
        if score < min_score:
            return QualityCheck(
                check_name="explanation_quality",
                passed=False,
                score=max(0.0, score),
                message=f"Explanation quality issues: {', '.join(issues)}" if issues else "insufficient explanation content",
                severity=Severity.WARNING,
            )
        
        return QualityCheck(
            check_name="explanation_quality",
            passed=True,
            score=max(0.0, score),
            message=f"Explanation quality meets standards for {target_stage}" + (f" ({len(common_mistakes)} misconceptions)" if target_stage == "L3_explanation" and 'common_mistakes' in locals() and common_mistakes else ""),
            severity=Severity.INFO,
        )
    
    def validate_definition_not_heading(self, unit: InstructionalUnit) -> QualityCheck:
        """
        Validate that L3 definition is not a heading or section title.
        
        Blocks definitions that look like:
        - Chapter titles ("Chapter 1: Introduction")
        - Section headings ("How to create tables", "Working with dates")
        - Gerund phrases ("Creating Tables", "Understanding Joins")
        - TOC entries ("3.2 Join Operations")
        
        This is critical for student_ready export mode where headings
        are not acceptable as learner-ready definitions.
        
        Args:
            unit: The instructional unit to validate
            
        Returns:
            QualityCheck with validation results
        """
        # Only relevant for L3 units with definitions
        if unit.target_stage != "L3_explanation":
            return QualityCheck(
                check_name="definition_not_heading",
                passed=True,
                score=1.0,
                message="Heading check only applies to L3 units",
                severity=Severity.INFO,
            )
        
        content = unit.content or {}
        if not isinstance(content, dict):
            return QualityCheck(
                check_name="definition_not_heading",
                passed=False,
                score=0.5,
                message="Content format not supported for heading validation",
                severity=Severity.WARNING,
            )
        
        definition = content.get("definition", "")
        if not definition:
            return QualityCheck(
                check_name="definition_not_heading",
                passed=False,
                score=0.0,
                message="No definition found to check",
                severity=Severity.WARNING,
            )
        
        definition_stripped = definition.strip()
        definition_lower = definition_stripped.lower()
        
        # Heading patterns that indicate section/chapter titles
        heading_patterns = [
            (r"^(How to|Working with|Understanding|Introduction to|Overview of)", "instructional heading"),
            (r"^(Chapter|Section|Part|Unit|Module|Lesson)\s+\d+", "chapter/section title"),
            (r"^\d+\.\d+\s+", "numbered section"),
            (r"^(In this chapter|Learning objectives|Summary|Exercises|Review|Quiz)", "section marker"),
            (r"^[A-Z][a-z]+ing\s+[a-z\s]+$", "gerund phrase heading"),
            (r"^Reference\s+(Document|Manual|Guide)", "reference marker"),
            (r"^Golden\s+Reference", "reference marker"),
            (r"^Table of Contents", "TOC marker"),
        ]
        
        for pattern, pattern_name in heading_patterns:
            if re.search(pattern, definition_stripped, re.IGNORECASE):
                return QualityCheck(
                    check_name="definition_not_heading",
                    passed=False,
                    score=0.0,
                    message=f"Definition appears to be a {pattern_name}: '{definition_stripped[:50]}...'",
                    severity=Severity.BLOCKING,
                )
        
        # Check for all-caps (likely a heading)
        if definition_stripped.isupper():
            return QualityCheck(
                check_name="definition_not_heading",
                passed=False,
                score=0.0,
                message="Definition is all uppercase - appears to be a heading",
                severity=Severity.BLOCKING,
            )
        
        # Check for title case without small words (likely a heading, not a sentence)
        words = definition_stripped.split()
        if len(words) < 10:
            small_words = ['a', 'an', 'the', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'is', 'are', 'with', 'by']
            content_words = [w for w in words if w.isalpha()]
            if content_words:
                capitalized = sum(1 for w in content_words if w[0].isupper())
                if capitalized / len(content_words) > 0.7 and not any(w.lower() in small_words for w in words):
                    return QualityCheck(
                        check_name="definition_not_heading",
                        passed=False,
                        score=0.2,
                        message=f"Definition appears to be title-case heading without sentence structure: '{definition_stripped[:50]}...'",
                        severity=Severity.WARNING,
                    )
        
        # Check for section endings like " - Overview" or ": Summary"
        section_endings = (' - Overview', ' - Summary', ' - Details', ' - Examples',
                          ': Overview', ': Summary', ': Details', ': Examples')
        if any(definition_stripped.endswith(ending) for ending in section_endings):
            return QualityCheck(
                check_name="definition_not_heading",
                passed=False,
                score=0.0,
                message=f"Definition appears to be a section heading: '{definition_stripped[:50]}...'",
                severity=Severity.BLOCKING,
            )
        
        return QualityCheck(
            check_name="definition_not_heading",
            passed=True,
            score=1.0,
            message="Definition does not appear to be a heading",
            severity=Severity.INFO,
        )
    
    def validate_practice_included(self, unit: InstructionalUnit) -> QualityCheck:
        """
        Validate that practice items are included (stage-aware).
        
        Different stages have different practice requirements:
        - L1_hint: Practice optional
        - L2_hint_plus_example: Example required, formal practice optional
        - L3_explanation: Practice required
        - L4_reflective_note: Transfer questions count as practice
        - reinforcement: Quick check required
        
        Args:
            unit: The instructional unit to validate
            
        Returns:
            QualityCheck with validation results
        """
        content = unit.content or {}
        if not isinstance(content, dict):
            return QualityCheck(
                check_name="practice_included",
                passed=False,
                score=0.5,
                message="Content format not supported for practice validation",
                severity=Severity.WARNING,
            )
        
        target_stage = unit.target_stage
        practice_links = content.get("practice_links", [])
        practice_items = content.get("practice_items", [])
        quick_check = content.get("quick_check_question", "")
        
        if target_stage == "L1_hint":
            # Practice optional for L1 - hint itself is the practice
            return QualityCheck(
                check_name="practice_included",
                passed=True,
                score=1.0,
                message="Practice optional for L1 hint units",
                severity=Severity.INFO,
            )
            
        elif target_stage == "L2_hint_plus_example":
            # Example required, formal practice optional
            has_example = bool(content.get("example_sql"))
            if has_example:
                return QualityCheck(
                    check_name="practice_included",
                    passed=True,
                    score=0.9,
                    message="Example SQL present (formal practice optional for L2)",
                    severity=Severity.INFO,
                )
            else:
                return QualityCheck(
                    check_name="practice_included",
                    passed=False,
                    score=0.4,
                    message="L2 units should have an example SQL",
                    severity=Severity.WARNING,
                )
                
        elif target_stage == "L3_explanation":
            # Practice required for L3
            total_practice = len(practice_links) + len(practice_items) + (1 if quick_check else 0)
            
            if total_practice == 0:
                return QualityCheck(
                    check_name="practice_included",
                    passed=False,
                    score=0.0,
                    message="No practice items included (required for L3)",
                    severity=Severity.WARNING,
                )
            
            # Check practice alignment (basic check)
            practice_content = str(practice_links) + str(practice_items) + str(quick_check)
            concept_keywords = unit.concept_id.replace("-", " ").lower().split()
            
            alignment_score = sum(1 for kw in concept_keywords if kw in practice_content.lower())
            score = min(1.0, 0.5 + (alignment_score / max(1, len(concept_keywords))) * 0.5)
            
            return QualityCheck(
                check_name="practice_included",
                passed=True,
                score=score,
                message=f"Found {total_practice} practice item(s)" + (", concept alignment unclear" if score < 0.7 else ""),
                severity=Severity.INFO,
            )
            
        elif target_stage == "L4_reflective_note":
            # Transfer questions count as practice
            transfer_questions = content.get("transfer_questions", [])
            reflection_prompts = content.get("reflection_prompts", [])
            
            has_transfer = bool(transfer_questions)
            
            if has_transfer:
                return QualityCheck(
                    check_name="practice_included",
                    passed=True,
                    score=0.9,
                    message=f"Transfer questions present ({len(transfer_questions)} items)",
                    severity=Severity.INFO,
                )
            elif reflection_prompts:
                return QualityCheck(
                    check_name="practice_included",
                    passed=True,
                    score=0.7,
                    message="Reflection prompts present (transfer questions recommended)",
                    severity=Severity.INFO,
                )
            else:
                return QualityCheck(
                    check_name="practice_included",
                    passed=False,
                    score=0.3,
                    message="L4 units should have transfer questions or reflection prompts",
                    severity=Severity.WARNING,
                )
                
        elif target_stage == "reinforcement":
            # Quick check required
            has_check = bool(content.get("quick_check_question"))
            
            if has_check:
                return QualityCheck(
                    check_name="practice_included",
                    passed=True,
                    score=1.0,
                    message="Quick check question present",
                    severity=Severity.INFO,
                )
            else:
                return QualityCheck(
                    check_name="practice_included",
                    passed=False,
                    score=0.0,
                    message="Reinforcement units require a quick check question",
                    severity=Severity.WARNING,
                )
        else:
            # Unknown stage - default to checking for any practice
            total_practice = len(practice_links) + len(practice_items) + (1 if quick_check else 0)
            
            if total_practice == 0:
                return QualityCheck(
                    check_name="practice_included",
                    passed=False,
                    score=0.0,
                    message="No practice items included",
                    severity=Severity.WARNING,
                )
            
            return QualityCheck(
                check_name="practice_included",
                passed=True,
                score=0.7,
                message=f"Found {total_practice} practice item(s)",
                severity=Severity.INFO,
            )
    
    def validate_practice_links_real(
        self, 
        unit: InstructionalUnit,
        strict_mode: bool = False,
    ) -> QualityCheck:
        """
        Check that practice links point to real problems, not placeholders.
        
        Validates:
        - Practice links use real problem IDs (not 'problem-*' or 'unresolved-*')
        - No placeholder practice links in production content
        - Links have proper metadata when available
        - Supports v2.0 format with is_placeholder flag, real_problem_id, etc.
        
        Args:
            unit: The instructional unit to validate
            strict_mode: If True, treat placeholders as BLOCKING (student_ready mode).
                        If False, treat as WARNING (prototype mode).
            
        Returns:
            QualityCheck with validation results
        """
        content = unit.content or {}
        if not isinstance(content, dict):
            return QualityCheck(
                check_name="practice_links_real",
                passed=True,
                score=1.0,
                message="Content format not supported for practice link validation",
                severity=Severity.INFO,
            )
        
        # Only relevant for units with practice links
        practice_links = content.get("practice_links", [])
        if not practice_links:
            return QualityCheck(
                check_name="practice_links_real",
                passed=True,
                score=1.0,
                message="No practice links to validate",
                severity=Severity.INFO,
            )
        
        # Count placeholder patterns
        placeholder_count = 0
        unresolved_count = 0
        v2_placeholder_count = 0  # v2.0 format with is_placeholder=true
        total_links = 0
        
        for link in practice_links:
            if isinstance(link, dict):
                problem_ids = link.get("problem_ids", [])
                needs_resolution = link.get("needs_resolution", False)
                metadata = link.get("metadata", {})
            else:
                # Handle PracticeLink objects
                problem_ids = getattr(link, "problem_ids", [])
                needs_resolution = getattr(link, "needs_resolution", False)
                metadata = getattr(link, "metadata", {}) or {}
            
            for pid in problem_ids:
                total_links += 1
                if pid.startswith("unresolved-"):
                    unresolved_count += 1
                    placeholder_count += 1
                elif pid.startswith("problem-"):
                    placeholder_count += 1
                elif needs_resolution:
                    placeholder_count += 1
            
            # Check v2.0 format metadata for is_placeholder flag
            if isinstance(metadata, dict):
                problems_meta = metadata.get("problems", [])
                for problem_meta in problems_meta:
                    if isinstance(problem_meta, dict):
                        if problem_meta.get("is_placeholder", False):
                            v2_placeholder_count += 1
                        # Also check for v2.0 real_problem_id presence
                        if not problem_meta.get("real_problem_id"):
                            # No real_problem_id means it's likely a placeholder
                            pass
        
        if total_links == 0:
            return QualityCheck(
                check_name="practice_links_real",
                passed=True,
                score=1.0,
                message="No problem IDs found in practice links",
                severity=Severity.INFO,
            )
        
        # Calculate score based on real vs placeholder links
        real_count = total_links - placeholder_count - v2_placeholder_count
        score = max(0.0, real_count / total_links) if total_links > 0 else 0.0
        
        # Determine severity based on strict_mode
        severity = Severity.BLOCKING if strict_mode else Severity.WARNING
        
        # Check if ALL links are placeholders (most severe case)
        if (placeholder_count + v2_placeholder_count) >= total_links:
            return QualityCheck(
                check_name="practice_links_real",
                passed=False,
                score=0.0,
                message=f"All {total_links} practice links are placeholders - replace with real problem IDs",
                severity=severity,
            )
        
        # Check for unresolved links
        if unresolved_count > 0:
            return QualityCheck(
                check_name="practice_links_real",
                passed=not strict_mode,  # Fail in strict mode, pass with warning otherwise
                score=score,
                message=f"{unresolved_count} unresolved practice links found - integration with practice system needed",
                severity=severity,
            )
        
        # Check for any placeholders
        if placeholder_count > 0 or v2_placeholder_count > 0:
            total_placeholders = placeholder_count + v2_placeholder_count
            return QualityCheck(
                check_name="practice_links_real",
                passed=not strict_mode,  # Fail in strict mode, pass with warning otherwise
                score=score,
                message=f"{total_placeholders}/{total_links} practice links are placeholders - {real_count} are real",
                severity=severity,
            )
        
        return QualityCheck(
            check_name="practice_links_real",
            passed=True,
            score=1.0,
            message=f"All {total_links} practice links point to real problem IDs",
            severity=Severity.INFO,
        )
    
    def validate_practice_links_strict(self, unit: InstructionalUnit) -> QualityCheck:
        """
        Strict validation for student-ready exports.
        
        Blocks if any placeholder practice links are found.
        
        Args:
            unit: The instructional unit to validate
            
        Returns:
            QualityCheck with BLOCKING severity if placeholders found
        """
        return self.validate_practice_links_real(unit, strict_mode=True)
    
    def validate_takeaway_present(self, unit: InstructionalUnit) -> QualityCheck:
        """
        Validate that a concise takeaway is present (stage-aware).
        
        Different stages have different takeaway requirements:
        - L1_hint: hint_text can serve as takeaway
        - L2_hint_plus_example: hint or pitfall can count
        - L3_explanation: explicit takeaway or summary required
        - L4_reflective_note: key_concept_summary required
        - reinforcement: quick_check can satisfy minimal summary
        
        Args:
            unit: The instructional unit to validate
            
        Returns:
            QualityCheck with validation results
        """
        content = unit.content or {}
        if not isinstance(content, dict):
            return QualityCheck(
                check_name="takeaway_present",
                passed=False,
                score=0.5,
                message="Content format not supported for takeaway validation",
                severity=Severity.WARNING,
            )
        
        target_stage = unit.target_stage
        takeaway = None
        takeaway_field = None
        
        if target_stage == "L1_hint":
            # Hint text can serve as takeaway
            if content.get("hint_text"):
                takeaway = content["hint_text"]
                takeaway_field = "hint_text"
            elif content.get("syntax_cue"):
                takeaway = content["syntax_cue"]
                takeaway_field = "syntax_cue"
                
        elif target_stage == "L2_hint_plus_example":
            # Hint or pitfall can count
            if content.get("hint_text"):
                takeaway = content["hint_text"]
                takeaway_field = "hint_text"
            elif content.get("common_pitfall"):
                takeaway = content["common_pitfall"]
                takeaway_field = "common_pitfall"
            elif content.get("key_takeaway"):
                takeaway = content["key_takeaway"]
                takeaway_field = "key_takeaway"
                
        elif target_stage == "L3_explanation":
            # Explicit takeaway or summary required
            for field_name in ["key_takeaway", "takeaway", "summary", "one_sentence_summary"]:
                if content.get(field_name):
                    takeaway = content[field_name]
                    takeaway_field = field_name
                    break
                    
        elif target_stage == "L4_reflective_note":
            # key_concept_summary required
            if content.get("key_concept_summary"):
                takeaway = content["key_concept_summary"]
                takeaway_field = "key_concept_summary"
            elif content.get("summary"):
                takeaway = content["summary"]
                takeaway_field = "summary"
                
        elif target_stage == "reinforcement":
            # Quick check can satisfy minimal summary
            if content.get("quick_check_question"):
                takeaway = content["quick_check_question"]
                takeaway_field = "quick_check_question"
            elif content.get("recall_prompt"):
                takeaway = content["recall_prompt"]
                takeaway_field = "recall_prompt"
        else:
            # Unknown stage - try all standard fields
            for field_name in ["takeaway", "key_takeaway", "summary", "key_concept_summary", "one_sentence_summary"]:
                if content.get(field_name):
                    takeaway = content[field_name]
                    takeaway_field = field_name
                    break
        
        if not takeaway:
            return QualityCheck(
                check_name="takeaway_present",
                passed=False,
                score=0.0,
                message=f"No takeaway found for {target_stage} unit",
                severity=Severity.WARNING,
            )
        
        takeaway_str = str(takeaway).strip()
        
        # Check if it's one sentence (roughly) - but be lenient for certain fields
        sentence_count = takeaway_str.count(".") + takeaway_str.count("!") + takeaway_str.count("?")
        
        # L1 and reinforcement can have multi-sentence takeaways
        if target_stage in ("L1_hint", "reinforcement"):
            return QualityCheck(
                check_name="takeaway_present",
                passed=True,
                score=1.0,
                message=f"Takeaway present via {takeaway_field} ({len(takeaway_str)} chars)",
                severity=Severity.INFO,
            )
        
        if sentence_count > 2:
            return QualityCheck(
                check_name="takeaway_present",
                passed=True,
                score=0.7,
                message=f"Takeaway appears to be {sentence_count} sentences (recommend: 1 concise sentence)",
                severity=Severity.INFO,
            )
        
        return QualityCheck(
            check_name="takeaway_present",
            passed=True,
            score=1.0,
            message=f"Concise takeaway present via {takeaway_field} ({len(takeaway_str)} chars)",
            severity=Severity.INFO,
        )
    
    # =========================================================================
    # ADAPTIVE READINESS GATES
    # =========================================================================
    
    def validate_prerequisite_tags(self, unit: InstructionalUnit) -> QualityCheck:
        """
        Validate prerequisite tags.
        
        Checks:
        - Prerequisites are listed (for non-root concepts)
        - Prerequisites exist in ontology
        - Root concepts (no prerequisites in ontology) can have empty prerequisites
        
        Args:
            unit: The instructional unit to validate
            
        Returns:
            QualityCheck with validation results
        """
        prereqs = unit.prerequisites or []
        
        # Check if this is a root concept in the ontology (has no prerequisites)
        ontology_prereqs = self.ontology.get_prerequisites(unit.concept_id)
        is_root_concept = not ontology_prereqs
        
        if not prereqs:
            # Root concepts are allowed to have empty prerequisites
            if is_root_concept:
                return QualityCheck(
                    check_name="prerequisite_tags",
                    passed=True,
                    score=1.0,
                    message=f"Root concept '{unit.concept_id}' - no prerequisites expected",
                    severity=Severity.INFO,
                )
            # Non-root concepts should have prerequisites
            return QualityCheck(
                check_name="prerequisite_tags",
                passed=False,
                score=0.3,
                message="No prerequisites listed",
                severity=Severity.WARNING,
            )
        
        # Check if all prerequisites exist in ontology
        invalid_prereqs = []
        for prereq in prereqs:
            if not self.ontology.validate_concept_id(prereq):
                invalid_prereqs.append(prereq)
        
        if invalid_prereqs:
            return QualityCheck(
                check_name="prerequisite_tags",
                passed=False,
                score=0.5,
                message=f"Invalid prerequisites not in ontology: {', '.join(invalid_prereqs[:3])}",
                severity=Severity.WARNING,
            )
        
        return QualityCheck(
            check_name="prerequisite_tags",
            passed=True,
            score=1.0,
            message=f"All {len(prereqs)} prerequisites valid in ontology",
            severity=Severity.INFO,
        )
    
    def validate_error_subtype_tags(self, unit: InstructionalUnit) -> QualityCheck:
        """
        Validate error subtype tags.
        
        Checks:
        - Error subtypes are listed (optional but recommended)
        - Subtypes map to SQL-Engage errors
        
        Args:
            unit: The instructional unit to validate
            
        Returns:
            QualityCheck with validation results
        """
        error_subtypes = unit.error_subtypes or []
        
        if not error_subtypes:
            # Error subtypes are optional, so this is just info
            return QualityCheck(
                check_name="error_subtype_tags",
                passed=True,
                score=0.7,
                message="No error subtypes tagged (optional, but recommended for misconception units)",
                severity=Severity.INFO,
            )
        
        # Cache valid error subtypes
        if self._error_subtype_cache is None:
            self._error_subtype_cache = set(self.ontology.list_all_error_subtypes())
        
        # Validate each subtype
        invalid_subtypes = []
        valid_subtypes = []
        
        for subtype in error_subtypes:
            if subtype in self._error_subtype_cache:
                valid_subtypes.append(subtype)
            else:
                # Check if it's a valid pattern (E1.1, E2.3, etc.)
                if not re.match(r"^E\d+\.\d+$", subtype):
                    invalid_subtypes.append(subtype)
        
        if invalid_subtypes:
            score = len(valid_subtypes) / len(error_subtypes)
            return QualityCheck(
                check_name="error_subtype_tags",
                passed=False,
                score=score,
                message=f"Unknown error subtypes: {', '.join(invalid_subtypes[:3])}",
                severity=Severity.WARNING,
            )
        
        return QualityCheck(
            check_name="error_subtype_tags",
            passed=True,
            score=1.0,
            message=f"All {len(error_subtypes)} error subtypes valid",
            severity=Severity.INFO,
        )
    
    def validate_stage_variants(
        self,
        unit_library: UnitLibraryExport,
    ) -> QualityCheck:
        """
        Validate that all 5 stage variants are present.
        
        Checks:
        - All 5 stage variants present (L1-L4 + reinforcement)
        - Variants cover the same concepts
        
        Args:
            unit_library: The complete unit library export
            
        Returns:
            QualityCheck with validation results
        """
        units = unit_library.instructional_units
        
        if not units:
            return QualityCheck(
                check_name="stage_variants",
                passed=False,
                score=0.0,
                message="No units in library",
                severity=Severity.BLOCKING,
            )
        
        # Group units by concept
        concept_stages: dict[str, set[str]] = {}
        for unit in units:
            cid = unit.concept_id
            if cid not in concept_stages:
                concept_stages[cid] = set()
            concept_stages[cid].add(unit.target_stage)
        
        # Check coverage
        incomplete_concepts = []
        complete_count = 0
        
        for concept_id, stages in concept_stages.items():
            missing = TARGET_STAGES - stages
            if missing:
                incomplete_concepts.append((concept_id, missing))
            else:
                complete_count += 1
        
        total_concepts = len(concept_stages)
        score = complete_count / total_concepts if total_concepts > 0 else 0.0
        
        if incomplete_concepts:
            sample = incomplete_concepts[:3]
            sample_str = "; ".join(f"{c}: missing {', '.join(m)}" for c, m in sample)
            return QualityCheck(
                check_name="stage_variants",
                passed=False,
                score=score,
                message=f"{len(incomplete_concepts)} concepts missing variants: {sample_str}",
                severity=Severity.WARNING,
            )
        
        return QualityCheck(
            check_name="stage_variants",
            passed=True,
            score=1.0,
            message=f"All {total_concepts} concepts have all 5 stage variants",
            severity=Severity.INFO,
        )
    
    def validate_reinforcement_present(
        self,
        unit_library: UnitLibraryExport,
    ) -> QualityCheck:
        """
        Validate that reinforcement items exist for concepts.
        
        Checks:
        - Reinforcement items exist for concept
        
        Args:
            unit_library: The complete unit library export
            
        Returns:
            QualityCheck with validation results
        """
        reinforcement_items = unit_library.reinforcement_bank
        units = unit_library.instructional_units
        
        if not units:
            return QualityCheck(
                check_name="reinforcement_present",
                passed=False,
                score=0.0,
                message="No units in library",
                severity=Severity.WARNING,
            )
        
        # Get concepts with units
        concepts_with_units = set(u.concept_id for u in units)
        
        # Get concepts with reinforcement
        concepts_with_reinforcement = set()
        if reinforcement_items:
            concepts_with_reinforcement = set(r.concept_id for r in reinforcement_items)
        
        # Check coverage
        missing_reinforcement = concepts_with_units - concepts_with_reinforcement
        
        if missing_reinforcement:
            score = 1.0 - (len(missing_reinforcement) / len(concepts_with_units))
            sample = list(missing_reinforcement)[:5]
            return QualityCheck(
                check_name="reinforcement_present",
                passed=False,
                score=score,
                message=f"{len(missing_reinforcement)} concepts missing reinforcement: {', '.join(sample)}",
                severity=Severity.WARNING,
            )
        
        return QualityCheck(
            check_name="reinforcement_present",
            passed=True,
            score=1.0,
            message=f"All {len(concepts_with_units)} concepts have reinforcement items",
            severity=Severity.INFO,
        )
    
    def validate_l3_for_core_concepts(
        self,
        unit_library: UnitLibraryExport,
    ) -> QualityCheck:
        """
        Validate that L3 (explanation) units exist for core concepts.
        
        Core concepts (non-admin, non-reference) should have L3 explanations
        for comprehensive learning coverage.
        
        Args:
            unit_library: The complete unit library export
            
        Returns:
            QualityCheck with validation results
        """
        units = unit_library.instructional_units
        
        if not units:
            return QualityCheck(
                check_name="l3_for_core_concepts",
                passed=False,
                score=0.0,
                message="No units in library",
                severity=Severity.WARNING,
            )
        
        # Group units by concept and collect stages
        concept_stages: dict[str, set[str]] = {}
        concept_units: dict[str, list[InstructionalUnit]] = {}
        
        for unit in units:
            cid = unit.concept_id
            if cid not in concept_stages:
                concept_stages[cid] = set()
                concept_units[cid] = []
            concept_stages[cid].add(unit.target_stage)
            concept_units[cid].append(unit)
        
        # Find core concepts (non-admin)
        core_concepts = []
        admin_concepts = []
        
        for concept_id in concept_stages:
            is_admin = any(
                re.search(pattern, concept_id, re.IGNORECASE)
                for pattern in ADMIN_CONCEPT_PATTERNS
            )
            if is_admin:
                admin_concepts.append(concept_id)
            else:
                core_concepts.append(concept_id)
        
        # Check which core concepts are missing L3
        missing_l3 = []
        for concept_id in core_concepts:
            if "L3_explanation" not in concept_stages.get(concept_id, set()):
                missing_l3.append(concept_id)
        
        if missing_l3:
            score = 1.0 - (len(missing_l3) / max(1, len(core_concepts)))
            sample = missing_l3[:5]
            return QualityCheck(
                check_name="l3_for_core_concepts",
                passed=False,
                score=score,
                message=f"{len(missing_l3)} core concepts missing L3 explanations: {', '.join(sample)}",
                severity=Severity.WARNING,
            )
        
        return QualityCheck(
            check_name="l3_for_core_concepts",
            passed=True,
            score=1.0,
            message=f"All {len(core_concepts)} core concepts have L3 explanations",
            severity=Severity.INFO,
        )
    
    def validate_boilerplate_content(
        self,
        unit_library: UnitLibraryExport,
    ) -> QualityCheck:
        """
        Validate that content doesn't have excessive boilerplate across units.
        
        Checks:
        - Same why_it_matters text repeated across multiple concepts
        - Identical definitions across concepts
        - Repeated example_explanation text
        
        Args:
            unit_library: The complete unit library export
            
        Returns:
            QualityCheck with validation results
        """
        units = unit_library.instructional_units
        
        if not units:
            return QualityCheck(
                check_name="boilerplate_detection",
                passed=True,
                score=1.0,
                message="No units to check",
                severity=Severity.INFO,
            )
        
        # Detect boilerplate
        boilerplate = self._detect_boilerplate_across_units(units)
        
        if boilerplate:
            total_instances = sum(len(instances) for instances in boilerplate.values())
            # Sample for message
            sample_text = list(boilerplate.keys())[0][:50] if boilerplate else ""
            sample_count = len(list(boilerplate.values())[0]) if boilerplate else 0
            
            return QualityCheck(
                check_name="boilerplate_detection",
                passed=False,
                score=0.6,
                message=f"Detected {len(boilerplate)} boilerplate texts repeated across {total_instances} instances (e.g., {sample_count} uses of '{sample_text}...')",
                severity=Severity.WARNING,
            )
        
        return QualityCheck(
            check_name="boilerplate_detection",
            passed=True,
            score=1.0,
            message="No excessive boilerplate detected",
            severity=Severity.INFO,
        )
    
    # =========================================================================
    # EXPORT INTEGRITY GATES
    # =========================================================================
    
    def validate_no_placeholders(self, unit: InstructionalUnit) -> QualityCheck:
        """
        Validate that no placeholder content exists (stage-aware).
        
        Checks:
        - No "see textbook" or "content could not be extracted"
        - No empty required fields (stage-dependent)
        - No placeholder examples
        - No test data or boilerplate content
        
        Different stages have different required fields:
        - L1_hint: requires hint_text
        - L2_hint_plus_example: requires hint_text
        - L3_explanation: requires definition
        - L4_reflective_note: requires key_concept_summary
        - reinforcement: requires recall_prompt or quick_check_question
        
        Args:
            unit: The instructional unit to validate
            
        Returns:
            QualityCheck with validation results
        """
        content = unit.content or {}
        content_str = str(content)
        target_stage = unit.target_stage
        
        placeholder_count = 0
        placeholder_types = []
        
        # Check standard placeholder patterns
        for pattern in PLACEHOLDER_PATTERNS:
            matches = re.findall(pattern, content_str, re.IGNORECASE)
            if matches:
                placeholder_count += len(matches)
                placeholder_types.append(pattern[:30])
        
        # NEW: Check for test/placeholder content patterns
        is_placeholder, placeholder_reason = self._is_placeholder_content(content_str)
        if is_placeholder:
            placeholder_count += 1
            placeholder_types.append(f"placeholder content ({placeholder_reason})")
        
        # Stage-aware check for empty required fields
        if isinstance(content, dict):
            if target_stage == "L3_explanation":
                # L3 requires definition
                definition = content.get("definition", "")
                if not definition or len(definition.strip()) < 20:
                    placeholder_count += 1
                    placeholder_types.append("empty/missing definition")
                elif len(definition.strip()) < MIN_DEFINITION_LENGTH:
                    placeholder_count += 0.5
                    placeholder_types.append("short definition")
                    
            elif target_stage == "L1_hint":
                # L1 requires hint_text
                hint = content.get("hint_text", "")
                if not hint or len(hint.strip()) < 10:
                    placeholder_count += 1
                    placeholder_types.append("empty/missing hint")
                    
            elif target_stage == "L2_hint_plus_example":
                # L2 requires hint_text
                hint = content.get("hint_text", "")
                if not hint or len(hint.strip()) < 10:
                    placeholder_count += 1
                    placeholder_types.append("empty/missing hint")
                # Also check for example if present but empty or broken
                example = content.get("example_sql", "")
                if example:
                    if len(example.strip()) < 5:
                        placeholder_count += 1
                        placeholder_types.append("empty example_sql")
                    elif not self._is_valid_sql_example(example):
                        placeholder_count += 1
                        placeholder_types.append("invalid/broken SQL in example")
                        
            elif target_stage == "L4_reflective_note":
                # L4 requires key_concept_summary
                summary = content.get("key_concept_summary", "")
                if not summary or len(summary.strip()) < 10:
                    placeholder_count += 1
                    placeholder_types.append("empty/missing key_concept_summary")
                    
            elif target_stage == "reinforcement":
                # Reinforcement requires recall or quick check
                recall = content.get("recall_prompt", "")
                check = content.get("quick_check_question", "")
                if (not recall or len(recall.strip()) < 10) and (not check or len(check.strip()) < 10):
                    placeholder_count += 1
                    placeholder_types.append("empty/missing recall or quick check")
            else:
                # Unknown stage - check definition as default
                definition = content.get("definition", "")
                if not definition or len(definition.strip()) < 10:
                    placeholder_count += 1
                    placeholder_types.append("empty/missing definition")
        
        if placeholder_count > 0:
            score = max(0.0, 1.0 - (placeholder_count * 0.2))
            return QualityCheck(
                check_name="no_placeholders",
                passed=False,
                score=score,
                message=f"Found {placeholder_count} placeholder(s): {', '.join(placeholder_types[:3])}",
                severity=Severity.BLOCKING,
            )
        
        return QualityCheck(
            check_name="no_placeholders",
            passed=True,
            score=1.0,
            message="No placeholder content detected",
            severity=Severity.INFO,
        )
    
    def validate_no_broken_sql(self, unit: InstructionalUnit) -> QualityCheck:
        """
        Validate that no broken SQL exists in the unit.
        
        Checks:
        - example_sql is valid (not "SELECT;" etc.)
        - Any SQL in examples is valid
        - No incomplete SQL statements
        
        Args:
            unit: The instructional unit to validate
            
        Returns:
            QualityCheck with validation results
        """
        content = unit.content or {}
        if not isinstance(content, dict):
            return QualityCheck(
                check_name="no_broken_sql",
                passed=True,
                score=1.0,
                message="Content format not supported for SQL validation",
                severity=Severity.INFO,
            )
        
        broken_sql_found = []
        
        # Check example_sql
        example_sql = content.get("example_sql", "")
        if example_sql and not self._is_valid_sql_example(example_sql):
            broken_sql_found.append("example_sql")
        
        # Check examples list
        examples = content.get("examples", [])
        for i, ex in enumerate(examples):
            if isinstance(ex, dict):
                ex_sql = ex.get("sql", "")
            else:
                ex_sql = str(ex)
            if ex_sql and not self._is_valid_sql_example(ex_sql):
                broken_sql_found.append(f"examples[{i}]")
        
        # Check common_mistakes for fix_sql
        mistakes = content.get("common_mistakes", [])
        for i, mistake in enumerate(mistakes):
            if isinstance(mistake, dict):
                fix_sql = mistake.get("fix_sql", "")
                if fix_sql and not self._is_valid_sql_example(fix_sql):
                    broken_sql_found.append(f"common_mistakes[{i}].fix_sql")
        
        if broken_sql_found:
            return QualityCheck(
                check_name="no_broken_sql",
                passed=False,
                score=0.0,
                message=f"Broken SQL found in: {', '.join(broken_sql_found[:3])}",
                severity=Severity.BLOCKING,
            )
        
        return QualityCheck(
            check_name="no_broken_sql",
            passed=True,
            score=1.0,
            message="No broken SQL detected",
            severity=Severity.INFO,
        )
    
    def validate_learner_ready(self, unit: InstructionalUnit) -> QualityCheck:
        """
        Validate that unit is ready for learner-facing export.
        
        Checks:
        - All blocking checks passed
        - Ready for learner-facing export
        
        Args:
            unit: The instructional unit to validate
            
        Returns:
            QualityCheck with validation results
        """
        # Run all unit-level checks
        checks = [
            self.validate_canonical_mapping(unit),
            self.validate_source_evidence(unit),
            self.validate_content_relevance(unit),
            self.validate_no_placeholders(unit),
        ]
        
        # Check for any blocking failures
        blocking_failures = [c for c in checks if not c.passed and c.severity == Severity.BLOCKING]
        
        if blocking_failures:
            failure_names = [c.check_name for c in blocking_failures]
            score = sum(c.score for c in checks) / len(checks)
            return QualityCheck(
                check_name="learner_ready",
                passed=False,
                score=score,
                message=f"Blocking issues: {', '.join(failure_names)}",
                severity=Severity.BLOCKING,
            )
        
        # Count warnings
        warnings = [c for c in checks if c.severity == Severity.WARNING]
        score = sum(c.score for c in checks) / len(checks)
        
        return QualityCheck(
            check_name="learner_ready",
            passed=True,
            score=score,
            message=f"Ready for export with {len(warnings)} warning(s)" if warnings else "Ready for learner export",
            severity=Severity.INFO,
        )


# =============================================================================
# LIBRARY-LEVEL VALIDATION
# =============================================================================

def validate_library(
    unit_library: UnitLibraryExport,
    min_l2_coverage: float = 0.8,
    min_l3_coverage: float = 0.8,
    max_fallback_ratio: float = 0.1,
    strict_mode: bool = True,
) -> dict[str, Any]:
    """
    Validate an entire unit library for student-ready deployment.
    
    This function performs library-level checks that cannot be determined
    by examining individual units alone, such as coverage statistics and
    ratios across the entire library.
    
    Args:
        unit_library: The complete unit library to validate
        min_l2_coverage: Minimum ratio of concepts that must have L2 units (default 0.8)
        min_l3_coverage: Minimum ratio of concepts that must have L3 units (default 0.8)
        max_fallback_ratio: Maximum ratio of units that can be fallback (default 0.1)
        strict_mode: If True, validation fails on any off-book curated concepts
        
    Returns:
        Dictionary with validation results:
        - valid: True if library is deployable
        - l2_coverage: {count, total, ratio, passed}
        - l3_coverage: {count, total, ratio, passed}
        - fallback_ratio: {count, total, ratio, passed}
        - offbook_concepts: {list, passed}
        - overall_status: "DEPLOYABLE" or "NOT DEPLOYABLE"
        - reasons: List of reasons if not deployable
    """
    units = unit_library.instructional_units
    
    if not units:
        return {
            "valid": False,
            "overall_status": "NOT DEPLOYABLE",
            "reasons": ["No units in library"],
            "l2_coverage": {"count": 0, "total": 0, "ratio": 0.0, "passed": False},
            "l3_coverage": {"count": 0, "total": 0, "ratio": 0.0, "passed": False},
            "fallback_ratio": {"count": 0, "total": 0, "ratio": 0.0, "passed": False},
            "offbook_concepts": {"list": [], "passed": False},
        }
    
    # Collect statistics
    all_concepts: set[str] = set()
    concepts_with_l2: set[str] = set()
    concepts_with_l3: set[str] = set()
    
    # Run individual checks
    l2_result = _check_l2_coverage(unit_library)
    l3_result = _check_l3_coverage(unit_library)
    fallback_result = _check_fallback_ratio(unit_library)
    offbook_result = _check_offbook_concepts(unit_library, strict_mode)
    
    # Build reasons list if not valid
    reasons: list[str] = []
    
    if not l2_result["passed"]:
        reasons.append(
            f"L2 coverage insufficient: {l2_result['count']}/{l2_result['total']} "
            f"concepts ({l2_result['ratio']:.1%}, min {min_l2_coverage:.0%})"
        )
    
    if not l3_result["passed"]:
        reasons.append(
            f"L3 coverage insufficient: {l3_result['count']}/{l3_result['total']} "
            f"concepts ({l3_result['ratio']:.1%}, min {min_l3_coverage:.0%})"
        )
    
    if not fallback_result["passed"]:
        reasons.append(
            f"Fallback ratio too high: {fallback_result['count']}/{fallback_result['total']} "
            f"units ({fallback_result['ratio']:.1%}, max {max_fallback_ratio:.0%})"
        )
    
    if not offbook_result["passed"]:
        concepts_str = ", ".join(offbook_result['list'][:5])
        if len(offbook_result['list']) > 5:
            concepts_str += f" and {len(offbook_result['list']) - 5} more"
        reasons.append(f"Off-book curated-only concepts present: {concepts_str}")
    
    valid = l2_result["passed"] and l3_result["passed"] and fallback_result["passed"] and offbook_result["passed"]
    
    return {
        "valid": valid,
        "overall_status": "DEPLOYABLE" if valid else "NOT DEPLOYABLE",
        "reasons": reasons,
        "l2_coverage": l2_result,
        "l3_coverage": l3_result,
        "fallback_ratio": fallback_result,
        "offbook_concepts": offbook_result,
    }


def _check_l2_coverage(
    unit_library: UnitLibraryExport,
    min_coverage: float = 0.8,
) -> dict[str, Any]:
    """
    Check if at least 80% of concepts have L2 (hint+example) units.
    
    Args:
        unit_library: The unit library to check
        min_coverage: Minimum required coverage ratio (default 0.8)
        
    Returns:
        Dictionary with count, total, ratio, and passed status
    """
    units = unit_library.instructional_units
    
    # Get all unique concepts
    all_concepts: set[str] = set()
    concepts_with_l2: set[str] = set()
    
    for unit in units:
        all_concepts.add(unit.concept_id)
        if unit.target_stage == "L2_hint_plus_example":
            concepts_with_l2.add(unit.concept_id)
    
    total = len(all_concepts)
    count = len(concepts_with_l2)
    ratio = count / total if total > 0 else 0.0
    
    return {
        "count": count,
        "total": total,
        "ratio": ratio,
        "passed": ratio >= min_coverage,
    }


def _check_l3_coverage(
    unit_library: UnitLibraryExport,
    min_coverage: float = 0.8,
) -> dict[str, Any]:
    """
    Check if at least 80% of concepts have L3 (explanation) units.
    
    Args:
        unit_library: The unit library to check
        min_coverage: Minimum required coverage ratio (default 0.8)
        
    Returns:
        Dictionary with count, total, ratio, and passed status
    """
    units = unit_library.instructional_units
    
    # Get all unique concepts
    all_concepts: set[str] = set()
    concepts_with_l3: set[str] = set()
    
    for unit in units:
        all_concepts.add(unit.concept_id)
        if unit.target_stage == "L3_explanation":
            concepts_with_l3.add(unit.concept_id)
    
    total = len(all_concepts)
    count = len(concepts_with_l3)
    ratio = count / total if total > 0 else 0.0
    
    return {
        "count": count,
        "total": total,
        "ratio": ratio,
        "passed": ratio >= min_coverage,
    }


def _check_fallback_ratio(
    unit_library: UnitLibraryExport,
    max_ratio: float = 0.1,
) -> dict[str, Any]:
    """
    Check if less than 10% of units are fallback units.
    
    Fallback units indicate extraction failures and should be limited
    in student-ready exports.
    
    Args:
        unit_library: The unit library to check
        max_ratio: Maximum allowed fallback ratio (default 0.1)
        
    Returns:
        Dictionary with count, total, ratio, and passed status
    """
    units = unit_library.instructional_units
    
    fallback_count = 0
    for unit in units:
        content = unit.content or {}
        if isinstance(content, dict):
            metadata = content.get("_metadata", {})
            is_fallback = content.get("is_fallback", False) or metadata.get("is_fallback", False)
            if is_fallback:
                fallback_count += 1
    
    total = len(units)
    ratio = fallback_count / total if total > 0 else 0.0
    
    return {
        "count": fallback_count,
        "total": total,
        "ratio": ratio,
        "passed": ratio <= max_ratio,
    }


def _check_offbook_concepts(
    unit_library: UnitLibraryExport,
    strict_mode: bool = True,
) -> dict[str, Any]:
    """
    Check for off-book curated-only concepts.
    
    Off-book concepts (source_mode == "curated_only_offbook") have no
    source grounding from the textbook and should not be in student-ready
    exports unless explicitly allowed.
    
    Args:
        unit_library: The unit library to check
        strict_mode: If True, any off-book concept fails validation
        
    Returns:
        Dictionary with list of off-book concepts and passed status
    """
    units = unit_library.instructional_units
    
    offbook_concepts: list[str] = []
    seen_concepts: set[str] = set()
    
    for unit in units:
        content = unit.content or {}
        if isinstance(content, dict):
            metadata = content.get("_metadata", {})
            source_mode = content.get("source_mode", "") or metadata.get("source_mode", "")
            
            if source_mode == "curated_only_offbook":
                if unit.concept_id not in seen_concepts:
                    offbook_concepts.append(unit.concept_id)
                    seen_concepts.add(unit.concept_id)
    
    return {
        "list": offbook_concepts,
        "passed": len(offbook_concepts) == 0 if strict_mode else True,
    }


# =============================================================================
# QUALITY REPORT CLASS
# =============================================================================

class QualityReport:
    """
    Generate comprehensive quality reports for unit libraries.
    
    Aggregates all quality gates across all units and produces
    actionable recommendations for fixes.
    
    Example:
        >>> report = QualityReport()
        >>> result = report.generate_full_report(unit_library)
        >>> print(f"Pass rate: {result['summary']['overall_pass_rate']:.1%}")
    """
    
    def __init__(self, gates: LearningQualityGates | None = None):
        """
        Initialize the quality report generator.
        
        Args:
            gates: Optional LearningQualityGates instance
        """
        self.gates = gates or LearningQualityGates()
    
    def generate_full_report(
        self,
        unit_library: UnitLibraryExport,
    ) -> dict[str, Any]:
        """
        Run all gates on all units and generate comprehensive report.
        
        Args:
            unit_library: The complete unit library export
            
        Returns:
            Comprehensive report dictionary with:
            - Overall pass rate
            - Pass rate by gate type
            - Failed units list
            - Recommendations for fixes
        """
        units = unit_library.instructional_units
        
        if not units:
            return {
                "summary": {
                    "total_units": 0,
                    "passed_units": 0,
                    "failed_units": 0,
                    "overall_pass_rate": 0.0,
                    "overall_passed": False,
                },
                "gate_results": {},
                "failed_units": [],
                "recommendations": ["No units to validate"],
            }
        
        # Run checks on all units
        unit_results: list[dict[str, Any]] = []
        gate_scores: dict[str, list[float]] = {
            "content_validity": [],
            "example_quality": [],
            "instruction_quality": [],
            "adaptive_readiness": [],
            "export_integrity": [],
        }
        
        for unit in units:
            unit_result = self._check_unit(unit)
            unit_results.append(unit_result)
            
            # Aggregate scores by gate category
            for check in unit_result.get("checks", []):
                category = self._categorize_check(check["check_name"])
                if category:
                    gate_scores[category].append(check["score"])
        
        # Run library-level checks
        library_checks = self._check_library(unit_library)
        
        # Calculate statistics
        total_units = len(units)
        passed_units = sum(1 for r in unit_results if r["passed"])
        failed_units = total_units - passed_units
        pass_rate = passed_units / total_units if total_units > 0 else 0.0
        
        # Calculate gate pass rates
        gate_pass_rates = {}
        for category, scores in gate_scores.items():
            if scores:
                gate_pass_rates[category] = {
                    "average_score": sum(scores) / len(scores),
                    "pass_rate": sum(1 for s in scores if s >= 0.7) / len(scores),
                    "total_checks": len(scores),
                }
        
        # Identify failed units
        failed_unit_details = [
            {
                "unit_id": r["unit_id"],
                "concept_id": r["concept_id"],
                "failed_checks": r["failed_checks"],
                "score": r["score"],
            }
            for r in unit_results
            if not r["passed"]
        ]
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            unit_results, library_checks, gate_pass_rates
        )
        
        return {
            "summary": {
                "total_units": total_units,
                "passed_units": passed_units,
                "failed_units": failed_units,
                "overall_pass_rate": round(pass_rate, 3),
                "overall_passed": pass_rate >= 0.9,
                "library_checks": {
                    name: check.passed 
                    for name, check in library_checks.items()
                },
            },
            "gate_pass_rates": gate_pass_rates,
            "failed_units": failed_unit_details,
            "recommendations": recommendations,
        }
    
    def _check_unit(self, unit: InstructionalUnit) -> dict[str, Any]:
        """Run all checks on a single unit."""
        checks = [
            self.gates.validate_canonical_mapping(unit),
            self.gates.validate_source_evidence(unit),
            self.gates.validate_content_relevance(unit),
            self.gates.validate_explanation_quality(unit),
            self.gates.validate_definition_not_heading(unit),
            self.gates.validate_practice_included(unit),
            self.gates.validate_practice_links_real(unit),
            self.gates.validate_takeaway_present(unit),
            self.gates.validate_prerequisite_tags(unit),
            self.gates.validate_error_subtype_tags(unit),
            self.gates.validate_no_placeholders(unit),
            self.gates.validate_no_broken_sql(unit),
            self.gates.validate_learner_ready(unit),
        ]
        
        failed_checks = [
            {"name": c.check_name, "message": c.message, "severity": c.severity.value}
            for c in checks
            if not c.passed
        ]
        
        blocking_failures = [c for c in checks if not c.passed and c.severity == Severity.BLOCKING]
        
        score = sum(c.score for c in checks) / len(checks) if checks else 0.0
        
        return {
            "unit_id": unit.unit_id,
            "concept_id": unit.concept_id,
            "passed": len(blocking_failures) == 0,
            "score": round(score, 3),
            "checks": [{"check_name": c.check_name, "score": c.score, "passed": c.passed} for c in checks],
            "failed_checks": failed_checks,
        }
    
    def _check_library(
        self,
        unit_library: UnitLibraryExport,
    ) -> dict[str, QualityCheck]:
        """Run library-level checks."""
        # Import here to avoid circular import
        from .learning_quality_gates import (
            _check_l2_coverage,
            _check_l3_coverage,
            _check_fallback_ratio,
            _check_offbook_concepts,
        )
        
        checks = {
            "stage_variants": self.gates.validate_stage_variants(unit_library),
            "reinforcement_present": self.gates.validate_reinforcement_present(unit_library),
            "l3_for_core_concepts": self.gates.validate_l3_for_core_concepts(unit_library),
            "boilerplate_detection": self.gates.validate_boilerplate_content(unit_library),
        }
        
        # Add new library-level checks
        l2_coverage = _check_l2_coverage(unit_library)
        l3_coverage = _check_l3_coverage(unit_library)
        fallback_ratio = _check_fallback_ratio(unit_library)
        offbook_concepts = _check_offbook_concepts(unit_library)
        
        # Convert results to QualityCheck format
        checks["l2_coverage"] = QualityCheck(
            check_name="l2_coverage",
            passed=l2_coverage["passed"],
            score=l2_coverage["ratio"],
            message=f"L2 coverage: {l2_coverage['count']}/{l2_coverage['total']} concepts ({l2_coverage['ratio']:.1%})",
            severity=Severity.WARNING if not l2_coverage["passed"] else Severity.INFO,
        )
        
        checks["l3_coverage"] = QualityCheck(
            check_name="l3_coverage",
            passed=l3_coverage["passed"],
            score=l3_coverage["ratio"],
            message=f"L3 coverage: {l3_coverage['count']}/{l3_coverage['total']} concepts ({l3_coverage['ratio']:.1%})",
            severity=Severity.WARNING if not l3_coverage["passed"] else Severity.INFO,
        )
        
        checks["fallback_ratio"] = QualityCheck(
            check_name="fallback_ratio",
            passed=fallback_ratio["passed"],
            score=1.0 - fallback_ratio["ratio"],  # Higher score = less fallback
            message=f"Fallback ratio: {fallback_ratio['count']}/{fallback_ratio['total']} units ({fallback_ratio['ratio']:.1%})",
            severity=Severity.WARNING if not fallback_ratio["passed"] else Severity.INFO,
        )
        
        checks["offbook_concepts"] = QualityCheck(
            check_name="offbook_concepts",
            passed=offbook_concepts["passed"],
            score=1.0 if offbook_concepts["passed"] else 0.0,
            message=f"Off-book concepts: {len(offbook_concepts['list'])}" if offbook_concepts["list"] else "No off-book concepts",
            severity=Severity.WARNING if not offbook_concepts["passed"] else Severity.INFO,
        )
        
        return checks
    
    def _categorize_check(self, check_name: str) -> str | None:
        """Categorize a check by type."""
        content_validity = {
            "canonical_mapping", "source_evidence", "content_relevance", "definition_not_heading",
            "l3_for_core_concepts", "boilerplate_detection",
        }
        example_quality = {
            "sql_executable", "sql_semantic", "example_difficulty", "no_broken_sql",
        }
        instruction_quality = {
            "explanation_quality", "practice_included", "takeaway_present",
        }
        adaptive_readiness = {
            "prerequisite_tags", "error_subtype_tags", "stage_variants", "reinforcement_present",
        }
        export_integrity = {
            "no_placeholders", "learner_ready", "practice_links_real",
        }
        
        if check_name in content_validity:
            return "content_validity"
        elif check_name in example_quality:
            return "example_quality"
        elif check_name in instruction_quality:
            return "instruction_quality"
        elif check_name in adaptive_readiness:
            return "adaptive_readiness"
        elif check_name in export_integrity:
            return "export_integrity"
        return None
    
    def _generate_recommendations(
        self,
        unit_results: list[dict[str, Any]],
        library_checks: dict[str, QualityCheck],
        gate_pass_rates: dict[str, Any],
    ) -> list[str]:
        """Generate actionable recommendations based on failures."""
        recommendations = []
        
        # Count failure types
        failure_counts: dict[str, int] = {}
        for result in unit_results:
            for check in result.get("failed_checks", []):
                name = check["name"]
                failure_counts[name] = failure_counts.get(name, 0) + 1
        
        # Sort by frequency
        sorted_failures = sorted(failure_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Generate recommendations for top issues
        for check_name, count in sorted_failures[:5]:
            if check_name == "source_evidence":
                recommendations.append(
                    f"[{count} units] Add source evidence spans to ground content in textbook"
                )
            elif check_name == "canonical_mapping":
                recommendations.append(
                    f"[{count} units] Map units to valid canonical concept IDs from sql_ontology"
                )
            elif check_name == "no_placeholders":
                recommendations.append(
                    f"[{count} units] Replace placeholder text with actual content"
                )
            elif check_name == "no_broken_sql":
                recommendations.append(
                    f"[{count} units] Fix broken SQL examples (e.g., 'SELECT;', incomplete statements)"
                )
            elif check_name == "explanation_quality":
                recommendations.append(
                    f"[{count} units] Add 'why it matters' and common misconceptions to explanations"
                )
            elif check_name == "definition_not_heading":
                recommendations.append(
                    f"[{count} units] Replace heading-like definitions with actual concept explanations"
                )
            elif check_name == "takeaway_present":
                recommendations.append(
                    f"[{count} units] Add concise one-sentence takeaways to units"
                )
            elif check_name == "practice_included":
                recommendations.append(
                    f"[{count} units] Include practice items aligned to concepts"
                )
            elif check_name == "practice_links_real":
                recommendations.append(
                    f"[{count} units] Replace placeholder practice IDs with real problem IDs from practice system"
                )
            elif check_name == "prerequisite_tags":
                recommendations.append(
                    f"[{count} units] Add prerequisite concept tags for adaptive pathing"
                )
        
        # Library-level recommendations
        if "stage_variants" in library_checks and not library_checks["stage_variants"].passed:
            recommendations.append(
                "[Library] Generate all 5 stage variants (L1-L4 + reinforcement) for each concept"
            )
        
        if "reinforcement_present" in library_checks and not library_checks["reinforcement_present"].passed:
            recommendations.append(
                "[Library] Create reinforcement items (recall prompts, quick checks) for concepts"
            )
        
        if "l3_for_core_concepts" in library_checks and not library_checks["l3_for_core_concepts"].passed:
            recommendations.append(
                "[Library] Generate L3 explanation units for all core concepts"
            )
        
        if "boilerplate_detection" in library_checks and not library_checks["boilerplate_detection"].passed:
            recommendations.append(
                "[Library] Review and replace repeated boilerplate content across units"
            )
        
        # Gate-level recommendations
        for gate_name, stats in gate_pass_rates.items():
            if stats["average_score"] < 0.7:
                recommendations.append(
                    f"[Gate: {gate_name}] Average score {stats['average_score']:.1%} - review category standards"
                )
        
        if not recommendations:
            recommendations.append("No issues found - library ready for export!")
        
        return recommendations


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def validate_unit_library(
    unit_library: UnitLibraryExport,
    min_pass_rate: float = 0.9,
    strict_mode: bool = False,
) -> tuple[bool, dict[str, Any]]:
    """
    Quick validation function for unit libraries with teaching quality metrics.
    
    Args:
        unit_library: The unit library to validate
        min_pass_rate: Minimum required pass rate (default 90%)
        strict_mode: If True, validation fails on broken SQL, excessive defaults, 
                    or heading-like content (default False)
        
    Returns:
        Tuple of (passed, report_dict) where report_dict includes:
        - summary: Overall pass rate and status
        - issue_counts: Count of each issue type
        - problematic_concepts: Dict mapping issue types to list of concept_ids
        - quality_score: Overall teaching content quality score (0-1)
        - strict_failures: List of strict-mode failures (if strict_mode=True)
    """
    gates = LearningQualityGates()
    report = QualityReport(gates).generate_full_report(unit_library)
    
    units = unit_library.instructional_units
    
    # Collect detailed issue information
    issue_counts: dict[str, int] = {}
    problematic_concepts: dict[str, list[str]] = {}
    strict_failures: list[dict[str, Any]] = []
    
    # Track specific issues
    broken_sql_units = []
    default_example_units = []
    heading_definition_units = []
    missing_l3_concepts = []
    
    for unit in units:
        concept_id = unit.concept_id
        content = unit.content or {}
        
        # Check for broken SQL
        if isinstance(content, dict):
            example_sql = content.get("example_sql", "")
            if example_sql and not gates._is_valid_sql_example(example_sql):
                broken_sql_units.append({
                    "concept_id": concept_id,
                    "unit_id": unit.unit_id,
                    "issue": "broken_sql",
                    "sql": example_sql[:100],
                })
            
            # Check for default example overuse
            if example_sql and gates._is_using_default_example(example_sql, concept_id):
                default_example_units.append({
                    "concept_id": concept_id,
                    "unit_id": unit.unit_id,
                    "issue": "default_example",
                })
            
            # Check for heading-like definitions (L3 only)
            if unit.target_stage == "L3_explanation":
                definition = content.get("definition", "")
                if definition:
                    is_heading, reason = gates._is_heading_like(definition)
                    if is_heading:
                        heading_definition_units.append({
                            "concept_id": concept_id,
                            "unit_id": unit.unit_id,
                            "issue": "heading_definition",
                            "reason": reason,
                        })
    
    # Calculate issue counts
    issue_counts["broken_sql"] = len(broken_sql_units)
    issue_counts["default_examples"] = len(default_example_units)
    issue_counts["heading_definitions"] = len(heading_definition_units)
    
    # Build problematic concepts dict
    if broken_sql_units:
        problematic_concepts["broken_sql"] = [u["concept_id"] for u in broken_sql_units]
    if default_example_units:
        problematic_concepts["default_examples"] = [u["concept_id"] for u in default_example_units]
    if heading_definition_units:
        problematic_concepts["heading_definitions"] = [u["concept_id"] for u in heading_definition_units]
    
    # Check for missing L3 for core concepts
    l3_check = gates.validate_l3_for_core_concepts(unit_library)
    if not l3_check.passed:
        # Extract concept list from message
        issue_counts["missing_l3"] = l3_check.message.count(",") + 1 if ":" in l3_check.message else 0
        # Parse missing L3 concepts from message
        if "missing L3 explanations:" in l3_check.message:
            concepts_str = l3_check.message.split("missing L3 explanations:")[1]
            missing_l3_concepts = [c.strip() for c in concepts_str.split(",")]
            problematic_concepts["missing_l3"] = missing_l3_concepts
    else:
        issue_counts["missing_l3"] = 0
    
    # Calculate teaching quality score (0-1)
    # Based on: valid SQL, appropriate examples, substantive definitions, no boilerplate
    total_units = len(units) if units else 1
    l2_units = [u for u in units if u.target_stage == "L2_hint_plus_example"]
    l3_units = [u for u in units if u.target_stage == "L3_explanation"]
    
    # SQL quality score
    l2_with_sql = len(l2_units)
    sql_quality_score = 1.0
    if l2_with_sql > 0:
        sql_quality_score = 1.0 - (len(broken_sql_units) / l2_with_sql)
    
    # Default example score
    default_example_score = 1.0
    if l2_with_sql > 0:
        default_example_score = 1.0 - (len(default_example_units) / l2_with_sql)
    
    # Definition quality score
    definition_quality_score = 1.0
    if l3_units:
        definition_quality_score = 1.0 - (len(heading_definition_units) / len(l3_units))
    
    # L3 coverage score
    core_concepts = len(set(u.concept_id for u in units)) - len(problematic_concepts.get("missing_l3", []))
    l3_coverage_score = 1.0
    if core_concepts > 0:
        l3_coverage_score = 1.0 - (issue_counts.get("missing_l3", 0) / core_concepts)
    
    # Overall teaching quality score (weighted average)
    teaching_quality_score = (
        sql_quality_score * 0.3 +
        default_example_score * 0.2 +
        definition_quality_score * 0.25 +
        l3_coverage_score * 0.25
    )
    
    # Strict mode checks
    if strict_mode:
        # Fail on any broken SQL
        if broken_sql_units:
            strict_failures.extend(broken_sql_units)
        
        # Fail if >50% of L2 units use defaults
        if l2_with_sql > 0 and len(default_example_units) / l2_with_sql > 0.5:
            strict_failures.append({
                "concept_id": "LIBRARY",
                "issue": "excessive_default_examples",
                "details": f"{len(default_example_units)}/{l2_with_sql} L2 units use default examples (>50%)",
            })
        
        # Fail on any heading-like definitions
        if heading_definition_units:
            strict_failures.extend(heading_definition_units)
    
    # Update report with enhanced information
    enhanced_report = {
        **report,
        "issue_counts": issue_counts,
        "problematic_concepts": problematic_concepts,
        "teaching_quality_score": round(teaching_quality_score, 3),
        "quality_breakdown": {
            "sql_validity": round(sql_quality_score, 3),
            "example_originality": round(default_example_score, 3),
            "definition_quality": round(definition_quality_score, 3),
            "l3_coverage": round(l3_coverage_score, 3),
        },
        "strict_failures": strict_failures if strict_mode else None,
        "detailed_failures": {
            "broken_sql": broken_sql_units,
            "default_examples": default_example_units,
            "heading_definitions": heading_definition_units,
        },
    }
    
    # Determine if passed
    base_passed = report["summary"]["overall_pass_rate"] >= min_pass_rate
    if strict_mode:
        passed = base_passed and len(strict_failures) == 0
    else:
        passed = base_passed
    
    return passed, enhanced_report


def format_report_markdown(report: dict[str, Any]) -> str:
    """
    Format a quality report as markdown.
    
    Args:
        report: Report dictionary from QualityReport.generate_full_report()
        
    Returns:
        Markdown-formatted report string
    """
    summary = report["summary"]
    
    lines = [
        "# Content Quality Report",
        "",
        "## Summary",
        "",
        f"- **Total Units:** {summary['total_units']}",
        f"- **Passed:** {summary['passed_units']} ✅",
        f"- **Failed:** {summary['failed_units']} ❌",
        f"- **Pass Rate:** {summary['overall_pass_rate']:.1%}",
        f"- **Overall Passed:** {'Yes ✅' if summary['overall_passed'] else 'No ❌'}",
    ]
    
    # Add teaching quality score if available
    if "teaching_quality_score" in report:
        tqs = report["teaching_quality_score"]
        tqs_emoji = "✅" if tqs >= 0.8 else "⚠️" if tqs >= 0.6 else "❌"
        lines.append(f"- **Teaching Quality Score:** {tqs:.1%} {tqs_emoji}")
    
    lines.extend(["", "## Gate Pass Rates", ""])
    
    for gate_name, stats in report.get("gate_pass_rates", {}).items():
        lines.append(f"- **{gate_name}:** {stats['average_score']:.1%} avg score ({stats['pass_rate']:.1%} pass rate)")
    
    # Add quality breakdown if available
    if "quality_breakdown" in report:
        lines.extend(["", "## Teaching Quality Breakdown", ""])
        qb = report["quality_breakdown"]
        for metric, score in qb.items():
            emoji = "✅" if score >= 0.8 else "⚠️" if score >= 0.6 else "❌"
            lines.append(f"- **{metric.replace('_', ' ').title()}:** {score:.1%} {emoji}")
    
    # Add issue counts if available
    if "issue_counts" in report and report["issue_counts"]:
        lines.extend(["", "## Issue Counts", ""])
        for issue_type, count in report["issue_counts"].items():
            if count > 0:
                lines.append(f"- **{issue_type.replace('_', ' ').title()}:** {count}")
    
    # Add problematic concepts if available
    if "problematic_concepts" in report and report["problematic_concepts"]:
        lines.extend(["", "## Problematic Concepts", ""])
        for issue_type, concepts in report["problematic_concepts"].items():
            if concepts:
                lines.append(f"- **{issue_type.replace('_', ' ').title()}:** {', '.join(concepts[:5])}")
                if len(concepts) > 5:
                    lines.append(f"  - *...and {len(concepts) - 5} more*")
    
    lines.extend([
        "",
        "## Recommendations",
        "",
    ])
    
    for rec in report.get("recommendations", []):
        lines.append(f"- {rec}")
    
    if report.get("failed_units"):
        lines.extend([
            "",
            "## Failed Units",
            "",
        ])
        for unit in report["failed_units"][:10]:
            lines.append(f"- **{unit['unit_id']}** (score: {unit['score']:.2f})")
            for fc in unit.get("failed_checks", [])[:3]:
                lines.append(f"  - {fc['name']}: {fc['message']}")
    
    # Add strict failures if in strict mode
    if report.get("strict_failures"):
        lines.extend([
            "",
            "## Strict Mode Failures",
            "",
        ])
        for failure in report["strict_failures"][:10]:
            lines.append(f"- **{failure.get('concept_id', 'Unknown')}:** {failure.get('issue', 'Unknown issue')}")
    
    return "\n".join(lines)
