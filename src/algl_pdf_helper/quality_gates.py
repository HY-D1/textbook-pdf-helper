"""
Quality Gates for Pedagogical Content.

This module provides configurable quality checks to ensure generated content
meets educational standards before being used by students.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .pedagogical_models import (
    PedagogicalConcept,
    QualityGateResult,
    QualityCheckResult,
)
from .validators import validate_sql_snippet, validate_practice_schema


# =============================================================================
# QUALITY GATE CONFIGURATION
# =============================================================================

@dataclass
class QualityGateConfig:
    """
    Configuration for quality gate checks.
    
    All thresholds are configurable to allow customization for different
    educational contexts.
    """
    # Content presence checks
    require_definition: bool = True
    min_definition_length: int = 100
    max_definition_length: int = 1000
    
    # Key points checks
    min_key_points: int = 2
    max_key_points: int = 10
    min_key_point_length: int = 10
    
    # Examples checks
    min_examples: int = 1
    max_examples: int = 5
    require_valid_sql: bool = True
    require_allowed_schemas: bool = True
    
    # Mistakes checks
    min_mistakes: int = 1
    max_mistakes: int = 5
    require_correct_sql_in_mistakes: bool = True
    
    # Practice references (optional)
    min_practice_references: int = 0  # 0 = optional
    
    # Metadata checks
    require_difficulty: bool = True
    require_time_estimate: bool = True
    min_time_minutes: int = 5
    max_time_minutes: int = 120
    
    # Overall quality
    min_overall_score: float = 0.7  # 70% to pass


# =============================================================================
# QUALITY GATE CLASS
# =============================================================================

class QualityGate:
    """
    Quality gate for validating pedagogical content.
    
    Provides configurable checks to ensure content meets educational standards:
    - Definition present and appropriate length
    - Sufficient key points
    - Valid SQL examples
    - Common mistakes documented
    - Practice schemas enforced
    
    Example:
        >>> gate = QualityGate()  # Default config
        >>> result = gate.check(concept)
        >>> if result.overall_passed:
        ...     print("Content approved!")
        ... else:
        ...     for check in result.get_failed_checks():
        ...         print(f"Failed: {check.check_name}")
    """
    
    def __init__(self, config: QualityGateConfig | None = None):
        """
        Initialize the quality gate.
        
        Args:
            config: Quality gate configuration (default: QualityGateConfig())
        """
        self.config = config or QualityGateConfig()
        
        # Register all checks
        self._checks: list[tuple[str, Callable[[PedagogicalConcept], QualityCheckResult]]] = [
            ("definition_present", self._check_definition_present),
            ("definition_length", self._check_definition_length),
            ("key_points_count", self._check_key_points_count),
            ("key_points_quality", self._check_key_points_quality),
            ("examples_count", self._check_examples_count),
            ("examples_sql_valid", self._check_examples_sql_valid),
            ("examples_schemas_allowed", self._check_examples_schemas_allowed),
            ("mistakes_count", self._check_mistakes_count),
            ("mistakes_sql_valid", self._check_mistakes_sql_valid),
            ("practice_references", self._check_practice_references),
            ("difficulty_set", self._check_difficulty_set),
            ("time_estimate", self._check_time_estimate),
        ]
    
    def check(self, concept: PedagogicalConcept) -> QualityGateResult:
        """
        Run all quality checks on a concept.
        
        Args:
            concept: The pedagogical concept to check
            
        Returns:
            QualityGateResult with all check results and overall status
        """
        results = []
        total_score = 0.0
        
        for check_name, check_func in self._checks:
            result = check_func(concept)
            results.append(result)
            total_score += result.score
        
        # Calculate overall score
        avg_score = total_score / len(results) if results else 0.0
        
        # Determine overall pass/fail
        # Must pass all required checks AND meet minimum overall score
        required_checks = [
            "definition_present",
            "examples_count",
            "examples_sql_valid",
            "mistakes_count",
        ]
        
        required_passed = all(
            r.passed for r in results if r.check_name in required_checks
        )
        score_passed = avg_score >= self.config.min_overall_score
        
        overall_passed = required_passed and score_passed
        
        return QualityGateResult(
            concept_id=concept.concept_id,
            overall_passed=overall_passed,
            checks=results,
            total_score=round(avg_score, 2),
        )
    
    def check_batch(
        self,
        concepts: list[PedagogicalConcept]
    ) -> dict[str, QualityGateResult]:
        """
        Check multiple concepts.
        
        Args:
            concepts: List of concepts to check
            
        Returns:
            Dictionary mapping concept_id to QualityGateResult
        """
        return {c.concept_id: self.check(c) for c in concepts}
    
    def get_pass_rate(self, results: dict[str, QualityGateResult]) -> float:
        """
        Calculate the pass rate for a batch of results.
        
        Args:
            results: Dictionary of QualityGateResults
            
        Returns:
            Pass rate as a float (0.0-1.0)
        """
        if not results:
            return 0.0
        passed = sum(1 for r in results.values() if r.overall_passed)
        return passed / len(results)
    
    # -------------------------------------------------------------------------
    # Individual Check Methods
    # -------------------------------------------------------------------------
    
    def _check_definition_present(self, concept: PedagogicalConcept) -> QualityCheckResult:
        """Check if definition is present and not empty."""
        if not self.config.require_definition:
            return QualityCheckResult(
                check_name="definition_present",
                passed=True,
                score=1.0,
                message="Definition check skipped (not required)",
            )
        
        has_definition = bool(concept.definition and len(concept.definition.strip()) > 0)
        
        return QualityCheckResult(
            check_name="definition_present",
            passed=has_definition,
            score=1.0 if has_definition else 0.0,
            message="Definition is present" if has_definition else "Definition is missing",
        )
    
    def _check_definition_length(self, concept: PedagogicalConcept) -> QualityCheckResult:
        """Check if definition is appropriate length."""
        length = len(concept.definition) if concept.definition else 0
        
        if length < self.config.min_definition_length:
            return QualityCheckResult(
                check_name="definition_length",
                passed=False,
                score=length / self.config.min_definition_length,
                message=f"Definition too short ({length} chars, min: {self.config.min_definition_length})",
            )
        
        if length > self.config.max_definition_length:
            return QualityCheckResult(
                check_name="definition_length",
                passed=False,
                score=0.5,  # Partial credit
                message=f"Definition too long ({length} chars, max: {self.config.max_definition_length})",
            )
        
        # Calculate score based on ideal range (150-250 words ~ 1000-1500 chars)
        ideal_min = 150
        ideal_max = 1000
        if ideal_min <= length <= ideal_max:
            score = 1.0
        elif length < ideal_min:
            score = 0.7 + (0.3 * (length / ideal_min))
        else:
            score = 0.8
        
        return QualityCheckResult(
            check_name="definition_length",
            passed=True,
            score=round(score, 2),
            message=f"Definition length good ({length} chars)",
        )
    
    def _check_key_points_count(self, concept: PedagogicalConcept) -> QualityCheckResult:
        """Check if there are sufficient key points."""
        count = len(concept.key_points)
        
        if count < self.config.min_key_points:
            return QualityCheckResult(
                check_name="key_points_count",
                passed=False,
                score=count / self.config.min_key_points,
                message=f"Too few key points ({count}, min: {self.config.min_key_points})",
            )
        
        if count > self.config.max_key_points:
            return QualityCheckResult(
                check_name="key_points_count",
                passed=False,
                score=0.5,
                message=f"Too many key points ({count}, max: {self.config.max_key_points})",
            )
        
        # Score based on ideal range (3-7)
        if 3 <= count <= 7:
            score = 1.0
        else:
            score = 0.8
        
        return QualityCheckResult(
            check_name="key_points_count",
            passed=True,
            score=round(score, 2),
            message=f"Key points count good ({count})",
        )
    
    def _check_key_points_quality(self, concept: PedagogicalConcept) -> QualityCheckResult:
        """Check quality of key points."""
        if not concept.key_points:
            return QualityCheckResult(
                check_name="key_points_quality",
                passed=False,
                score=0.0,
                message="No key points to check",
            )
        
        good_points = 0
        short_points = 0
        
        for point in concept.key_points:
            if len(point.strip()) >= self.config.min_key_point_length:
                good_points += 1
            else:
                short_points += 1
        
        total = len(concept.key_points)
        score = good_points / total if total > 0 else 0.0
        
        return QualityCheckResult(
            check_name="key_points_quality",
            passed=score >= 0.7,  # At least 70% good
            score=round(score, 2),
            message=f"{good_points}/{total} key points are detailed enough",
        )
    
    def _check_examples_count(self, concept: PedagogicalConcept) -> QualityCheckResult:
        """Check if there are sufficient examples."""
        count = len(concept.examples)
        
        if count < self.config.min_examples:
            return QualityCheckResult(
                check_name="examples_count",
                passed=False,
                score=count / self.config.min_examples if self.config.min_examples > 0 else 0.0,
                message=f"Too few examples ({count}, min: {self.config.min_examples})",
            )
        
        if count > self.config.max_examples:
            return QualityCheckResult(
                check_name="examples_count",
                passed=False,
                score=0.5,
                message=f"Too many examples ({count}, max: {self.config.max_examples})",
            )
        
        # Ideal is 2-3 examples
        if 1 <= count <= 3:
            score = 1.0
        else:
            score = 0.9
        
        return QualityCheckResult(
            check_name="examples_count",
            passed=True,
            score=round(score, 2),
            message=f"Examples count good ({count})",
        )
    
    def _check_examples_sql_valid(self, concept: PedagogicalConcept) -> QualityCheckResult:
        """Check if all example SQL is valid."""
        if not self.config.require_valid_sql:
            return QualityCheckResult(
                check_name="examples_sql_valid",
                passed=True,
                score=1.0,
                message="SQL validation skipped",
            )
        
        if not concept.examples:
            return QualityCheckResult(
                check_name="examples_sql_valid",
                passed=False,
                score=0.0,
                message="No examples to validate",
            )
        
        valid_count = 0
        issues = []
        
        for i, example in enumerate(concept.examples):
            result = validate_sql_snippet(example.query)
            if result.is_valid:
                valid_count += 1
            else:
                issues.append(f"Example {i+1}: {', '.join(result.issues[:2])}")
        
        total = len(concept.examples)
        score = valid_count / total if total > 0 else 0.0
        
        return QualityCheckResult(
            check_name="examples_sql_valid",
            passed=score == 1.0,
            score=round(score, 2),
            message=f"{valid_count}/{total} examples have valid SQL" if not issues else f"Issues: {'; '.join(issues[:3])}",
        )
    
    def _check_examples_schemas_allowed(self, concept: PedagogicalConcept) -> QualityCheckResult:
        """Check if all examples use allowed schemas."""
        if not self.config.require_allowed_schemas:
            return QualityCheckResult(
                check_name="examples_schemas_allowed",
                passed=True,
                score=1.0,
                message="Schema validation skipped",
            )
        
        if not concept.examples:
            return QualityCheckResult(
                check_name="examples_schemas_allowed",
                passed=False,
                score=0.0,
                message="No examples to validate",
            )
        
        valid_count = 0
        issues = []
        
        for i, example in enumerate(concept.examples):
            if validate_practice_schema(example.schema_used):
                valid_count += 1
            else:
                issues.append(f"Example {i+1}: '{example.schema_used}' not in allowed schemas")
        
        total = len(concept.examples)
        score = valid_count / total if total > 0 else 0.0
        
        return QualityCheckResult(
            check_name="examples_schemas_allowed",
            passed=score == 1.0,
            score=round(score, 2),
            message=f"{valid_count}/{total} examples use allowed schemas" if not issues else f"Issues: {'; '.join(issues[:3])}",
        )
    
    def _check_mistakes_count(self, concept: PedagogicalConcept) -> QualityCheckResult:
        """Check if there are sufficient common mistakes."""
        count = len(concept.common_mistakes)
        
        if count < self.config.min_mistakes:
            return QualityCheckResult(
                check_name="mistakes_count",
                passed=False,
                score=count / self.config.min_mistakes if self.config.min_mistakes > 0 else 0.0,
                message=f"Too few mistakes ({count}, min: {self.config.min_mistakes})",
            )
        
        if count > self.config.max_mistakes:
            return QualityCheckResult(
                check_name="mistakes_count",
                passed=False,
                score=0.5,
                message=f"Too many mistakes ({count}, max: {self.config.max_mistakes})",
            )
        
        # Ideal is 2-3 mistakes
        if 2 <= count <= 3:
            score = 1.0
        else:
            score = 0.9
        
        return QualityCheckResult(
            check_name="mistakes_count",
            passed=True,
            score=round(score, 2),
            message=f"Mistakes count good ({count})",
        )
    
    def _check_mistakes_sql_valid(self, concept: PedagogicalConcept) -> QualityCheckResult:
        """Check if mistake corrections have valid SQL."""
        if not self.config.require_correct_sql_in_mistakes:
            return QualityCheckResult(
                check_name="mistakes_sql_valid",
                passed=True,
                score=1.0,
                message="SQL validation skipped",
            )
        
        if not concept.common_mistakes:
            return QualityCheckResult(
                check_name="mistakes_sql_valid",
                passed=False,
                score=0.0,
                message="No mistakes to validate",
            )
        
        valid_count = 0
        issues = []
        
        for i, mistake in enumerate(concept.common_mistakes):
            result = validate_sql_snippet(mistake.correct_sql)
            if result.is_valid:
                valid_count += 1
            else:
                issues.append(f"Mistake {i+1}: {', '.join(result.issues[:2])}")
        
        total = len(concept.common_mistakes)
        score = valid_count / total if total > 0 else 0.0
        
        return QualityCheckResult(
            check_name="mistakes_sql_valid",
            passed=score == 1.0,
            score=round(score, 2),
            message=f"{valid_count}/{total} mistake corrections have valid SQL" if not issues else f"Issues: {'; '.join(issues[:3])}",
        )
    
    def _check_practice_references(self, concept: PedagogicalConcept) -> QualityCheckResult:
        """Check practice references if required."""
        if self.config.min_practice_references == 0:
            return QualityCheckResult(
                check_name="practice_references",
                passed=True,
                score=1.0,
                message="Practice references not required",
            )
        
        count = len(concept.practice_references)
        
        if count < self.config.min_practice_references:
            return QualityCheckResult(
                check_name="practice_references",
                passed=False,
                score=count / self.config.min_practice_references,
                message=f"Too few practice references ({count}, min: {self.config.min_practice_references})",
            )
        
        return QualityCheckResult(
            check_name="practice_references",
            passed=True,
            score=1.0,
            message=f"Practice references count good ({count})",
        )
    
    def _check_difficulty_set(self, concept: PedagogicalConcept) -> QualityCheckResult:
        """Check if difficulty is set and valid."""
        if not self.config.require_difficulty:
            return QualityCheckResult(
                check_name="difficulty_set",
                passed=True,
                score=1.0,
                message="Difficulty check skipped",
            )
        
        valid_difficulties = ["beginner", "intermediate", "advanced"]
        is_valid = concept.difficulty in valid_difficulties
        
        return QualityCheckResult(
            check_name="difficulty_set",
            passed=is_valid,
            score=1.0 if is_valid else 0.0,
            message=f"Difficulty is '{concept.difficulty}'" if is_valid else f"Invalid difficulty: '{concept.difficulty}'",
        )
    
    def _check_time_estimate(self, concept: PedagogicalConcept) -> QualityCheckResult:
        """Check if time estimate is reasonable."""
        if not self.config.require_time_estimate:
            return QualityCheckResult(
                check_name="time_estimate",
                passed=True,
                score=1.0,
                message="Time estimate check skipped",
            )
        
        time = concept.estimated_time_minutes
        
        if time < self.config.min_time_minutes:
            return QualityCheckResult(
                check_name="time_estimate",
                passed=False,
                score=time / self.config.min_time_minutes,
                message=f"Time estimate too low ({time} min, min: {self.config.min_time_minutes})",
            )
        
        if time > self.config.max_time_minutes:
            return QualityCheckResult(
                check_name="time_estimate",
                passed=False,
                score=0.5,
                message=f"Time estimate too high ({time} min, max: {self.config.max_time_minutes})",
            )
        
        return QualityCheckResult(
            check_name="time_estimate",
            passed=True,
            score=1.0,
            message=f"Time estimate good ({time} min)",
        )


# =============================================================================
# BATCH QUALITY REPORTING
# =============================================================================

def generate_quality_report(
    results: dict[str, QualityGateResult],
    config: QualityGateConfig | None = None,
) -> dict[str, Any]:
    """
    Generate a comprehensive quality report for multiple concepts.
    
    Args:
        results: Dictionary of QualityGateResults
        config: Quality gate configuration used
        
    Returns:
        Dictionary with summary statistics and details
    """
    total = len(results)
    passed = sum(1 for r in results.values() if r.overall_passed)
    failed = total - passed
    pass_rate = passed / total if total > 0 else 0.0
    
    # Aggregate scores
    total_scores = [r.total_score for r in results.values()]
    avg_score = sum(total_scores) / len(total_scores) if total_scores else 0.0
    
    # Collect failures by check type
    failures_by_check: dict[str, int] = {}
    for result in results.values():
        for check in result.get_failed_checks():
            failures_by_check[check.check_name] = failures_by_check.get(check.check_name, 0) + 1
    
    # Sort by most common failures
    top_failures = sorted(failures_by_check.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "summary": {
            "total_concepts": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(pass_rate, 2),
            "average_score": round(avg_score, 2),
            "target_pass_rate": 0.9,  # 90% target
            "meets_target": pass_rate >= 0.9,
        },
        "configuration": {
            "min_examples": config.min_examples if config else 1,
            "min_mistakes": config.min_mistakes if config else 1,
            "require_valid_sql": config.require_valid_sql if config else True,
            "min_overall_score": config.min_overall_score if config else 0.7,
        },
        "top_failures": [
            {"check": name, "count": count, "percentage": round(count / total * 100, 1)}
            for name, count in top_failures
        ],
        "failed_concepts": [
            {
                "concept_id": concept_id,
                "score": result.total_score,
                "failed_checks": [c.check_name for c in result.get_failed_checks()]
            }
            for concept_id, result in results.items()
            if not result.overall_passed
        ],
    }


def print_quality_report(report: dict[str, Any]) -> None:
    """
    Print a formatted quality report to console.
    
    Args:
        report: Quality report from generate_quality_report()
    """
    summary = report["summary"]
    
    print("\n" + "=" * 60)
    print("QUALITY GATE REPORT")
    print("=" * 60)
    
    print(f"\n📊 Summary:")
    print(f"   Total Concepts: {summary['total_concepts']}")
    print(f"   Passed: {summary['passed']} ✅")
    print(f"   Failed: {summary['failed']} ❌")
    print(f"   Pass Rate: {summary['pass_rate']*100:.1f}%")
    print(f"   Average Score: {summary['average_score']:.2f}")
    
    target = summary['target_pass_rate'] * 100
    if summary['meets_target']:
        print(f"   ✅ Meets target ({target:.0f}%)")
    else:
        print(f"   ❌ Below target ({target:.0f}%)")
    
    if report["top_failures"]:
        print(f"\n🔍 Top Issues:")
        for failure in report["top_failures"]:
            print(f"   - {failure['check']}: {failure['count']} ({failure['percentage']}%)")
    
    if report["failed_concepts"]:
        print(f"\n❌ Failed Concepts ({len(report['failed_concepts'])}):")
        for fc in report["failed_concepts"][:10]:  # Show first 10
            print(f"   - {fc['concept_id']}: score={fc['score']:.2f}")
        if len(report["failed_concepts"]) > 10:
            print(f"   ... and {len(report['failed_concepts']) - 10} more")
    
    print("\n" + "=" * 60)
