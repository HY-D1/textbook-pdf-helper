"""
Content Diagnostics Tool for Instructional Unit Library.

This module provides diagnostic capabilities to analyze instructional unit libraries
and identify content gaps, quality issues, and coverage problems before export.

Usage:
    from algl_pdf_helper.content_diagnostics import ContentDiagnostics, DiagnosticReport
    
    diagnostics = ContentDiagnostics()
    report = diagnostics.analyze_library(library_path)
    print(report.summary())
    print(report.format_report())
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CoverageStats:
    """Statistics for concept coverage."""
    total_concepts: int = 0
    with_l1: int = 0
    with_l2: int = 0
    with_l3: int = 0
    with_l4: int = 0
    with_reinforcement: int = 0
    
    @property
    def l3_coverage_pct(self) -> float:
        """Percentage of concepts with L3."""
        return (self.with_l3 / self.total_concepts * 100) if self.total_concepts > 0 else 0.0
    
    @property
    def complete_coverage_pct(self) -> float:
        """Percentage of concepts with all stages."""
        complete = min(self.with_l1, self.with_l2, self.with_l3, self.with_l4, self.with_reinforcement)
        return (complete / self.total_concepts * 100) if self.total_concepts > 0 else 0.0


@dataclass
class QualityIssues:
    """Quality issues found in the library."""
    l2_using_default: list[str] = field(default_factory=list)
    l3_heading_like_why: list[str] = field(default_factory=list)
    unresolved_practice_links: list[str] = field(default_factory=list)
    missing_evidence_spans: list[str] = field(default_factory=list)
    generic_definitions: list[str] = field(default_factory=list)
    
    @property
    def total_issues(self) -> int:
        """Total number of quality issues."""
        return (
            len(self.l2_using_default) +
            len(self.l3_heading_like_why) +
            len(self.unresolved_practice_links) +
            len(self.missing_evidence_spans) +
            len(self.generic_definitions)
        )


@dataclass
class DiagnosticReport:
    """Complete diagnostic report for an instructional unit library."""
    library_path: Path
    total_units: int = 0
    coverage: CoverageStats = field(default_factory=CoverageStats)
    issues: QualityIssues = field(default_factory=QualityIssues)
    missing_l3_concepts: list[str] = field(default_factory=list)
    concept_ids: set[str] = field(default_factory=set)
    
    def summary(self) -> str:
        """Generate a human-readable summary of the diagnostic report."""
        lines = [
            "=" * 60,
            "CONTENT DIAGNOSTICS REPORT",
            "=" * 60,
            f"Library: {self.library_path}",
            f"Total Units: {self.total_units}",
            f"Unique Concepts: {len(self.concept_ids)}",
            "",
            "COVERAGE:",
            f"  L1 (Hints):              {self.coverage.with_l1}/{self.coverage.total_concepts}",
            f"  L2 (Hint+Example):       {self.coverage.with_l2}/{self.coverage.total_concepts}",
            f"  L3 (Explanation):        {self.coverage.with_l3}/{self.coverage.total_concepts} ({self.coverage.l3_coverage_pct:.1f}%)",
            f"  L4 (Reflective):         {self.coverage.with_l4}/{self.coverage.total_concepts}",
            f"  Reinforcement:           {self.coverage.with_reinforcement}/{self.coverage.total_concepts}",
            f"  Complete (all stages):   {self.coverage.complete_coverage_pct:.1f}%",
            "",
            "QUALITY ISSUES:",
            f"  L2 using default examples:     {len(self.issues.l2_using_default)}",
            f"  L3 heading-like why_it_matters: {len(self.issues.l3_heading_like_why)}",
            f"  Unresolved practice links:     {len(self.issues.unresolved_practice_links)}",
            f"  Missing evidence spans:        {len(self.issues.missing_evidence_spans)}",
            f"  Generic definitions:           {len(self.issues.generic_definitions)}",
            f"  TOTAL ISSUES:                  {self.issues.total_issues}",
            "",
        ]
        
        if self.missing_l3_concepts:
            lines.extend([
                "MISSING L3 EXPLANATIONS:",
                f"  {len(self.missing_l3_concepts)} concepts lack L3:",
            ])
            for concept in sorted(self.missing_l3_concepts)[:10]:
                lines.append(f"    - {concept}")
            if len(self.missing_l3_concepts) > 10:
                lines.append(f"    ... and {len(self.missing_l3_concepts) - 10} more")
            lines.append("")
        
        lines.extend([
            "=" * 60,
            "STUDENT-READY ASSESSMENT:",
            self._assess_student_ready(),
            "=" * 60,
        ])
        
        return "\n".join(lines)
    
    def _assess_student_ready(self) -> str:
        """Assess if the library is student-ready."""
        issues = []
        
        if self.coverage.l3_coverage_pct < 80:
            issues.append(f"  ❌ L3 coverage too low ({self.coverage.l3_coverage_pct:.1f}%, need 80%+)")
        else:
            issues.append(f"  ✅ L3 coverage adequate ({self.coverage.l3_coverage_pct:.1f}%)")
        
        if len(self.issues.l2_using_default) > 10:
            issues.append(f"  ❌ Too many L2 defaults ({len(self.issues.l2_using_default)}, want <10)")
        else:
            issues.append(f"  ✅ L2 defaults acceptable ({len(self.issues.l2_using_default)})")
        
        if len(self.issues.unresolved_practice_links) > 5:
            issues.append(f"  ❌ Too many unresolved practice links ({len(self.issues.unresolved_practice_links)})")
        else:
            issues.append(f"  ✅ Practice links acceptable ({len(self.issues.unresolved_practice_links)})")
        
        if self.issues.total_issues > 20:
            issues.append(f"  ❌ Too many quality issues ({self.issues.total_issues}, want <20)")
        else:
            issues.append(f"  ✅ Quality issues acceptable ({self.issues.total_issues})")
        
        if all(line.startswith("  ✅") for line in issues):
            issues.append("\n  🎉 Library appears STUDENT-READY!")
        else:
            issues.append("\n  ⚠️  Library needs improvement before student-ready export.")
        
        return "\n".join(issues)
    
    def format_report(self) -> str:
        """Generate a detailed formatted report."""
        lines = [self.summary(), ""]
        
        if self.issues.l2_using_default:
            lines.extend([
                "-" * 60,
                "L2 UNITS USING DEFAULT EXAMPLES:",
                "-" * 60,
            ])
            for concept in sorted(self.issues.l2_using_default):
                lines.append(f"  - {concept}")
            lines.append("")
        
        if self.issues.l3_heading_like_why:
            lines.extend([
                "-" * 60,
                "L3 UNITS WITH HEADING-LIKE why_it_matters:",
                "-" * 60,
            ])
            for concept in sorted(self.issues.l3_heading_like_why):
                lines.append(f"  - {concept}")
            lines.append("")
        
        if self.issues.unresolved_practice_links:
            lines.extend([
                "-" * 60,
                "UNRESOLVED PRACTICE LINKS:",
                "-" * 60,
            ])
            for concept in sorted(self.issues.unresolved_practice_links):
                lines.append(f"  - {concept}")
            lines.append("")
        
        return "\n".join(lines)


class ContentDiagnostics:
    """Diagnostic tool for analyzing instructional content quality."""
    
    def __init__(self):
        """Initialize the diagnostics tool."""
        self.heading_patterns = [
            r'^how\s+to\s+',
            r'^chapter\s+\d+',
            r'^section\s+\d+',
            r'^unit\s+\d+',
        ]
    
    def analyze_library(self, library_path: Path | str) -> DiagnosticReport:
        """
        Analyze an instructional unit library and generate a diagnostic report.
        
        Args:
            library_path: Path to the unit library file or directory
            
        Returns:
            DiagnosticReport with findings
        """
        library_path = Path(library_path)
        
        # Handle both file and directory paths
        if library_path.is_dir():
            units_file = library_path / "instructional_units.jsonl"
            if not units_file.exists():
                raise FileNotFoundError(f"No instructional_units.jsonl found in {library_path}")
            library_path = units_file
        
        # Load units
        units = self._load_units(library_path)
        
        # Initialize report
        report = DiagnosticReport(library_path=library_path)
        report.total_units = len(units)
        
        # Track coverage per concept
        concept_stages: dict[str, set[str]] = {}
        
        for unit in units:
            concept_id = unit.get("concept_id", "unknown")
            stage = unit.get("target_stage", "unknown")
            
            report.concept_ids.add(concept_id)
            
            if concept_id not in concept_stages:
                concept_stages[concept_id] = set()
            concept_stages[concept_id].add(stage)
            
            # Check for issues
            self._analyze_unit(unit, report)
        
        # Calculate coverage stats
        report.coverage.total_concepts = len(report.concept_ids)
        report.coverage.with_l1 = sum(1 for s in concept_stages.values() if "L1_hint" in s)
        report.coverage.with_l2 = sum(1 for s in concept_stages.values() if "L2_hint_plus_example" in s)
        report.coverage.with_l3 = sum(1 for s in concept_stages.values() if "L3_explanation" in s)
        report.coverage.with_l4 = sum(1 for s in concept_stages.values() if "L4_reflective_note" in s)
        report.coverage.with_reinforcement = sum(1 for s in concept_stages.values() if "reinforcement" in s)
        
        # Find concepts missing L3
        report.missing_l3_concepts = [
            cid for cid in report.concept_ids
            if "L3_explanation" not in concept_stages.get(cid, set())
        ]
        
        return report
    
    def _load_units(self, path: Path) -> list[dict]:
        """Load units from JSONL file."""
        units = []
        
        # Try JSONL first
        if path.suffix == '.jsonl' or path.name == 'instructional_units.jsonl':
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        units.append(json.loads(line))
        else:
            # Try JSON
            with open(path) as f:
                data = json.load(f)
                if isinstance(data, list):
                    units = data
                elif isinstance(data, dict) and "instructional_units" in data:
                    units = data["instructional_units"]
        
        return units
    
    def _analyze_unit(self, unit: dict, report: DiagnosticReport) -> None:
        """Analyze a single unit for quality issues."""
        concept_id = unit.get("concept_id", "unknown")
        stage = unit.get("target_stage", "unknown")
        content = unit.get("content", {}) or {}
        
        if not isinstance(content, dict):
            return
        
        # Check L2 default examples
        if stage == "L2_hint_plus_example":
            metadata = content.get("_metadata", {})
            if content.get("_used_default_example") or metadata.get("content_source") == "default":
                report.issues.l2_using_default.append(concept_id)
            elif content.get("example_metadata"):
                ex_meta = content["example_metadata"]
                if isinstance(ex_meta, dict) and ex_meta.get("source_type") == "default":
                    report.issues.l2_using_default.append(concept_id)
        
        # Check L3 issues
        if stage == "L3_explanation":
            why_it_matters = content.get("why_it_matters", "")
            
            # Check for heading-like why_it_matters
            if self._is_heading_like(why_it_matters):
                report.issues.l3_heading_like_why.append(concept_id)
            
            # Check for generic definitions
            definition = content.get("definition", "")
            if self._is_generic_definition(definition):
                report.issues.generic_definitions.append(concept_id)
        
        # Check for unresolved practice links
        practice_links = content.get("practice_links", [])
        if practice_links:
            has_unresolved = False
            for link in practice_links:
                if isinstance(link, dict):
                    if link.get("needs_resolution"):
                        has_unresolved = True
                        break
                    problem_ids = link.get("problem_ids", [])
                    if any(pid.startswith("unresolved-") for pid in problem_ids):
                        has_unresolved = True
                        break
            if has_unresolved:
                report.issues.unresolved_practice_links.append(concept_id)
        
        # Check for missing evidence spans
        evidence_spans = unit.get("evidence_spans", [])
        if len(evidence_spans) < 2:
            # Curated content is exempt
            metadata = content.get("_metadata", {})
            if metadata.get("content_source") != "curated":
                report.issues.missing_evidence_spans.append(concept_id)
    
    def _is_heading_like(self, text: str) -> bool:
        """Check if text looks like a heading."""
        if not text:
            return False
        
        text_lower = text.strip().lower()
        
        for pattern in self.heading_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        # Check for title case (all words capitalized)
        words = text.strip().split()
        if len(words) > 1 and len(words) < 10:
            content_words = [w for w in words if w.isalpha()]
            if content_words and all(w[0].isupper() for w in content_words):
                small_words = ['a', 'an', 'the', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'is']
                if not any(w.lower() in small_words for w in words):
                    return True
        
        return False
    
    def _is_generic_definition(self, definition: str) -> bool:
        """Check if definition is generic/placeholder."""
        if not definition:
            return True
        
        generic_patterns = [
            r'is an important sql concept',
            r'is a crucial sql concept',
            r'is an essential sql concept',
            r'is a fundamental sql concept',
        ]
        
        definition_lower = definition.lower()
        for pattern in generic_patterns:
            if re.search(pattern, definition_lower):
                return True
        
        return False


def main():
    """CLI entry point for running diagnostics."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python content_diagnostics.py <library_path>")
        print("\nAnalyzes instructional unit library for content gaps and quality issues.")
        sys.exit(1)
    
    library_path = Path(sys.argv[1])
    
    if not library_path.exists():
        print(f"Error: Path not found: {library_path}")
        sys.exit(1)
    
    diagnostics = ContentDiagnostics()
    report = diagnostics.analyze_library(library_path)
    
    print(report.format_report())
    
    # Exit with error code if not student-ready
    summary = report.summary()
    if "❌" in summary:
        sys.exit(1)


if __name__ == "__main__":
    main()
