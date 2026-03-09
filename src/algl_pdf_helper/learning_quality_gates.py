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
            for field in ["key_takeaway", "takeaway", "summary", "one_sentence_summary"]:
                if content.get(field):
                    takeaway = content[field]
                    takeaway_field = field
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
            for field in ["takeaway", "key_takeaway", "summary", "key_concept_summary", "one_sentence_summary"]:
                if content.get(field):
                    takeaway = content[field]
                    takeaway_field = field
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
        
        for pattern in PLACEHOLDER_PATTERNS:
            matches = re.findall(pattern, content_str, re.IGNORECASE)
            if matches:
                placeholder_count += len(matches)
                placeholder_types.append(pattern[:30])
        
        # Stage-aware check for empty required fields
        if isinstance(content, dict):
            if target_stage == "L3_explanation":
                # L3 requires definition
                definition = content.get("definition", "")
                if not definition or len(definition.strip()) < 20:
                    placeholder_count += 1
                    placeholder_types.append("empty/missing definition")
                    
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
                    # Also check for example if present but empty
                    example = content.get("example_sql", "")
                    if example and len(example.strip()) < 5:
                        placeholder_count += 1
                        placeholder_types.append("empty example_sql")
                        
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
            self.gates.validate_practice_included(unit),
            self.gates.validate_takeaway_present(unit),
            self.gates.validate_prerequisite_tags(unit),
            self.gates.validate_error_subtype_tags(unit),
            self.gates.validate_no_placeholders(unit),
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
        return {
            "stage_variants": self.gates.validate_stage_variants(unit_library),
            "reinforcement_present": self.gates.validate_reinforcement_present(unit_library),
        }
    
    def _categorize_check(self, check_name: str) -> str | None:
        """Categorize a check by type."""
        content_validity = {
            "canonical_mapping", "source_evidence", "content_relevance",
        }
        example_quality = {
            "sql_executable", "sql_semantic", "example_difficulty",
        }
        instruction_quality = {
            "explanation_quality", "practice_included", "takeaway_present",
        }
        adaptive_readiness = {
            "prerequisite_tags", "error_subtype_tags", "stage_variants", "reinforcement_present",
        }
        export_integrity = {
            "no_placeholders", "learner_ready",
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
            elif check_name == "explanation_quality":
                recommendations.append(
                    f"[{count} units] Add 'why it matters' and common misconceptions to explanations"
                )
            elif check_name == "takeaway_present":
                recommendations.append(
                    f"[{count} units] Add concise one-sentence takeaways to units"
                )
            elif check_name == "practice_included":
                recommendations.append(
                    f"[{count} units] Include practice items aligned to concepts"
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
) -> tuple[bool, dict[str, Any]]:
    """
    Quick validation function for unit libraries.
    
    Args:
        unit_library: The unit library to validate
        min_pass_rate: Minimum required pass rate (default 90%)
        
    Returns:
        Tuple of (passed, report_dict)
    """
    report = QualityReport().generate_full_report(unit_library)
    passed = report["summary"]["overall_pass_rate"] >= min_pass_rate
    return passed, report


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
        "",
        "## Gate Pass Rates",
        "",
    ]
    
    for gate_name, stats in report.get("gate_pass_rates", {}).items():
        lines.append(f"- **{gate_name}:** {stats['average_score']:.1%} avg score ({stats['pass_rate']:.1%} pass rate)")
    
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
    
    return "\n".join(lines)
