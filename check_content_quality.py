#!/usr/bin/env python3
"""Content quality checker for pedagogical concepts."""

import json
import re
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import sys

@dataclass
class QualityReport:
    """Quality check report for a concept."""
    concept_id: str
    passed: bool
    score: int  # 0-100
    issues: List[str]
    warnings: List[str]
    strengths: List[str]

class ContentQualityChecker:
    """Check quality of generated pedagogical content."""
    
    # Valid practice tables
    PRACTICE_TABLES = {'users', 'orders', 'products', 'employees', 'departments', 'categories', 
                       'customers', 'students', 'courses', 'invoices', 'vendors', 'accounts',
                       'line_items', 'terms', 'general_ledger_accounts'}
    
    # Textbook tables that should NOT appear
    TEXTBOOK_TABLES = {'sailors', 'boats', 'reserves', 'ap_invoices', 'ap_vendors', 'ap_parts', 
                       'suppliers', 'invoices_ap', 'vendors_ap', 'parts', 'ap'}
    
    # Required sections
    REQUIRED_SECTIONS = ['definition', 'examples', 'commonMistakes']
    
    # SQL patterns to check for
    SQL_PATTERNS = {
        'select': r'\bSELECT\b',
        'from': r'\bFROM\b',
        'where': r'\bWHERE\b',
        'join': r'\bJOIN\b',
        'group_by': r'\bGROUP\s+BY\b',
        'order_by': r'\bORDER\s+BY\b',
        'aggregate': r'\b(COUNT|SUM|AVG|MAX|MIN)\s*\(',
    }
    
    def __init__(self):
        self.reports: List[QualityReport] = []
    
    def check_concept(self, concept: Dict[str, Any]) -> QualityReport:
        """Run all quality checks on a concept."""
        issues: List[str] = []
        warnings: List[str] = []
        strengths: List[str] = []
        score = 100.0
        
        concept_id = concept.get('id', concept.get('concept_id', 'unknown'))
        
        # Check 1: Schema Alignment
        schema_score = self._check_schema_alignment(concept, issues, warnings, strengths)
        score -= (100 - schema_score) * 0.3
        
        # Check 2: Content Structure
        structure_score = self._check_structure(concept, issues, warnings, strengths)
        score -= (100 - structure_score) * 0.2
        
        # Check 3: Examples Quality
        examples_score = self._check_examples(concept, issues, warnings, strengths)
        score -= (100 - examples_score) * 0.25
        
        # Check 4: Common Mistakes Quality
        mistakes_score = self._check_common_mistakes(concept, issues, warnings, strengths)
        score -= (100 - mistakes_score) * 0.15
        
        # Check 5: Educational Value
        educational_score = self._check_educational_value(concept, issues, warnings, strengths)
        score -= (100 - educational_score) * 0.1
        
        passed = score >= 70 and len([i for i in issues if i.startswith('CRITICAL')]) == 0
        
        return QualityReport(
            concept_id=concept_id,
            passed=passed,
            score=int(max(0, score)),
            issues=issues,
            warnings=warnings,
            strengths=strengths
        )
    
    def _check_schema_alignment(self, concept: Dict, issues: List, warnings: List, strengths: List) -> int:
        """Check that all SQL uses practice schemas."""
        score = 100
        all_sql = []
        
        # Collect all SQL from educational_notes
        notes = concept.get('educational_notes', {})
        
        # Collect SQL from examples in notes
        if isinstance(notes, dict):
            # Handle nested notes structure
            notes_list = notes.get('notes', [notes])
            if not isinstance(notes_list, list):
                notes_list = [notes_list]
            
            for note in notes_list:
                if isinstance(note, dict):
                    # Check examples array
                    examples = note.get('examples', [])
                    if isinstance(examples, list):
                        for ex in examples:
                            if isinstance(ex, dict):
                                all_sql.append(ex.get('sql', '') if 'sql' in ex else ex.get('example', ''))
                    
                    # Check sql_examples
                    sql_examples = note.get('sql_examples', [])
                    if isinstance(sql_examples, list):
                        for ex in sql_examples:
                            if isinstance(ex, dict):
                                all_sql.append(ex.get('example', ''))
                    
                    # Check mistakes
                    mistakes = note.get('mistakes', note.get('common_mistakes', []))
                    if isinstance(mistakes, list):
                        for m in mistakes:
                            if isinstance(m, dict):
                                all_sql.append(m.get('error_sql', ''))
                                all_sql.append(m.get('fix_sql', ''))
                    
                    # Check practice question
                    pq = note.get('practice_question', {})
                    if isinstance(pq, dict):
                        all_sql.append(pq.get('solution', ''))
        
        # Check for textbook tables
        sql_text = ' '.join(all_sql).lower()
        found_textbook = []
        for table in self.TEXTBOOK_TABLES:
            if re.search(rf'\b{table}\b', sql_text):
                found_textbook.append(table)
        
        if found_textbook:
            issues.append(f"CRITICAL: Found textbook tables: {', '.join(found_textbook)}. Must use practice schemas (users, orders, products).")
            score -= 50
        
        # Check for practice tables
        found_practice = []
        for table in self.PRACTICE_TABLES:
            if re.search(rf'\b{table}\b', sql_text):
                found_practice.append(table)
        
        if not found_practice and sql_text.strip():
            warnings.append("No standard practice tables found. Consider using users, orders, products, etc.")
            score -= 10
        elif found_practice:
            strengths.append(f"Uses practice tables: {', '.join(found_practice[:3])}")
        
        return max(0, score)
    
    def _check_structure(self, concept: Dict, issues: List, warnings: List, strengths: List) -> int:
        """Check content structure."""
        score = 100
        
        # Check required sections
        sections = concept.get('sections', {})
        for required in self.REQUIRED_SECTIONS:
            if required not in sections:
                issues.append(f"CRITICAL: Missing required section: {required}")
                score -= 20
        
        # Check title
        if not concept.get('title'):
            issues.append("CRITICAL: Missing concept title")
            score -= 15
        
        # Check definition
        definition = concept.get('definition', '')
        if not definition or definition == 'See textbook for details.':
            warnings.append("Definition is missing or placeholder")
            score -= 10
        
        # Check difficulty
        if not concept.get('difficulty'):
            warnings.append("No difficulty level specified")
            score -= 5
        
        # Check educational_notes
        notes = concept.get('educational_notes', {})
        if not notes:
            issues.append("CRITICAL: Missing educational_notes")
            score -= 25
        
        return max(0, score)
    
    def _check_examples(self, concept: Dict, issues: List, warnings: List, strengths: List) -> int:
        """Check examples quality."""
        score = 100
        
        # Get examples from educational_notes
        notes = concept.get('educational_notes', {})
        examples = []
        
        if isinstance(notes, dict):
            # Handle notes list structure
            notes_list = notes.get('notes', [notes])
            if not isinstance(notes_list, list):
                notes_list = [notes_list]
            
            for note in notes_list:
                if isinstance(note, dict):
                    # Check examples array
                    ex_list = note.get('examples', [])
                    if isinstance(ex_list, list):
                        examples.extend(ex_list)
                    
                    # Check sql_examples
                    sql_ex = note.get('sql_examples', [])
                    if isinstance(sql_ex, list):
                        examples.extend(sql_ex)
        
        if not examples:
            issues.append("CRITICAL: No examples provided")
            return 0
        
        if len(examples) < 2:
            warnings.append("Only 1 example provided, recommend 2-3")
            score -= 10
        
        valid_examples = 0
        for i, ex in enumerate(examples):
            if not isinstance(ex, dict):
                continue
                
            # Check SQL exists
            sql = ex.get('sql') or ex.get('example', '')
            if not sql:
                issues.append(f"Example {i+1}: Missing SQL code")
                score -= 15
            elif 'SELECT' in sql.upper() or 'INSERT' in sql.upper() or 'UPDATE' in sql.upper():
                valid_examples += 1
            
            # Check explanation exists
            if not ex.get('explanation'):
                warnings.append(f"Example {i+1}: Missing explanation")
                score -= 5
        
        if valid_examples >= 2:
            strengths.append(f"Good: {valid_examples} runnable SQL examples provided")
        
        return max(0, score)
    
    def _check_common_mistakes(self, concept: Dict, issues: List, warnings: List, strengths: List) -> int:
        """Check common mistakes quality."""
        score = 100
        mistakes = []
        
        # Get mistakes from educational_notes
        notes = concept.get('educational_notes', {})
        
        if isinstance(notes, dict):
            notes_list = notes.get('notes', [notes])
            if not isinstance(notes_list, list):
                notes_list = [notes_list]
            
            for note in notes_list:
                if isinstance(note, dict):
                    m = note.get('mistakes', note.get('common_mistakes', []))
                    if isinstance(m, list):
                        mistakes.extend(m)
        
        if not mistakes:
            warnings.append("No common mistakes documented")
            score -= 20
            return max(0, score)
        
        for i, m in enumerate(mistakes):
            if not isinstance(m, dict):
                continue
                
            # Check mistake description
            if not m.get('mistake'):
                issues.append(f"Mistake {i+1}: Missing mistake description")
                score -= 10
            
            # Check correction
            if not m.get('correction'):
                warnings.append(f"Mistake {i+1}: Missing correction")
                score -= 5
        
        if len(mistakes) >= 2:
            strengths.append(f"Good: {len(mistakes)} common mistakes documented with corrections")
        
        return max(0, score)
    
    def _check_educational_value(self, concept: Dict, issues: List, warnings: List, strengths: List) -> int:
        """Check educational value."""
        score = 100
        
        # Get notes content
        notes = concept.get('educational_notes', {})
        all_text = ''
        
        if isinstance(notes, dict):
            notes_list = notes.get('notes', [notes])
            if not isinstance(notes_list, list):
                notes_list = [notes_list]
            
            for note in notes_list:
                if isinstance(note, dict):
                    for key, value in note.items():
                        if isinstance(value, str):
                            all_text += value + ' '
                        elif isinstance(value, list) and value and isinstance(value[0], dict):
                            for item in value:
                                if isinstance(item, dict):
                                    for k, v in item.items():
                                        if isinstance(v, str):
                                            all_text += v + ' '
        
        # Check for conceptual explanation length
        if len(all_text) < 200:
            warnings.append("Educational content is brief, consider expanding")
            score -= 10
        
        # Check for "why it matters"
        if 'why' not in all_text.lower() and 'matter' not in all_text.lower() and 'important' not in all_text.lower():
            warnings.append("Consider explaining why this concept matters")
            score -= 5
        
        # Check for real-world context
        has_context = any(
            word in all_text.lower() 
            for word in ['example', 'scenario', 'when you', 'real', 'application', 'use case', 'practical']
        )
        if not has_context:
            warnings.append("Consider adding real-world context")
            score -= 5
        else:
            strengths.append("Good: Real-world context provided")
        
        if score >= 90:
            strengths.append("Good: Strong educational value with clear explanations")
        
        return max(0, score)
    
    def check_file(self, file_path: Path) -> Dict[str, QualityReport]:
        """Check all concepts in a file."""
        reports = {}
        
        try:
            with open(file_path) as f:
                data = json.load(f)
            
            # Handle different structures
            concepts = data.get('concepts', {})
            
            for concept_id, concept_data in concepts.items():
                if isinstance(concept_data, dict):
                    # Add concept_id if missing
                    if 'id' not in concept_data:
                        concept_data['id'] = concept_id
                    
                    report = self.check_concept(concept_data)
                    reports[report.concept_id] = report
                    self.reports.append(report)
        
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
        
        return reports
    
    def check_directory(self, concepts_dir: Path) -> Dict[str, QualityReport]:
        """Check all concept files in a directory."""
        reports = {}
        
        for concept_file in concepts_dir.glob('*.json'):
            file_reports = self.check_file(concept_file)
            reports.update(file_reports)
        
        return reports
    
    def generate_summary_report(self) -> str:
        """Generate summary report."""
        if not self.reports:
            return "No concepts were checked."
        
        lines = [
            "=" * 70,
            "CONTENT QUALITY SUMMARY REPORT",
            "=" * 70,
            "",
            f"Total concepts checked: {len(self.reports)}",
            f"Passed: {sum(1 for r in self.reports if r.passed)}",
            f"Failed: {sum(1 for r in self.reports if not r.passed)}",
            f"Average score: {sum(r.score for r in self.reports) / len(self.reports):.1f}",
            "",
            "-" * 70,
        ]
        
        # Sort by score (lowest first)
        sorted_reports = sorted(self.reports, key=lambda r: r.score)
        
        for report in sorted_reports:
            status = "✓ PASS" if report.passed else "✗ FAIL"
            lines.append(f"\n{status} {report.concept_id}: {report.score}/100")
            
            if report.issues:
                lines.append("  Issues:")
                for issue in report.issues:
                    lines.append(f"    ⚠ {issue}")
            
            if report.warnings:
                lines.append("  Warnings:")
                for warning in report.warnings[:3]:  # Limit warnings shown
                    lines.append(f"    ! {warning}")
            
            if report.strengths:
                lines.append("  Strengths:")
                for strength in report.strengths[:3]:
                    lines.append(f"    ✓ {strength}")
        
        lines.append("")
        lines.append("=" * 70)
        
        return '\n'.join(lines)
    
    def generate_detailed_json_report(self) -> Dict:
        """Generate detailed JSON report."""
        return {
            "summary": {
                "total": len(self.reports),
                "passed": sum(1 for r in self.reports if r.passed),
                "failed": sum(1 for r in self.reports if not r.passed),
                "average_score": sum(r.score for r in self.reports) / len(self.reports) if self.reports else 0
            },
            "concepts": [
                {
                    "concept_id": r.concept_id,
                    "passed": r.passed,
                    "score": r.score,
                    "issues": r.issues,
                    "warnings": r.warnings,
                    "strengths": r.strengths
                }
                for r in self.reports
            ]
        }


def main():
    """Main quality check function."""
    checker = ContentQualityChecker()
    
    # Parse command line arguments
    target_paths = sys.argv[1:] if len(sys.argv) > 1 else []
    
    # Default locations to check
    default_paths = [
        Path("test_output"),
        Path("output/test-3-concepts"),
        Path("output/murach-fixed"),
        Path("output/quality-test"),
    ]
    
    paths_to_check = [Path(p) for p in target_paths] if target_paths else default_paths
    
    checked_any = False
    
    for path in paths_to_check:
        if not path.exists():
            continue
            
        print(f"\nChecking concepts in: {path}")
        checked_any = True
        
        if path.is_dir():
            # Check for educational notes files
            for notes_file in path.glob("*-educational-notes.json"):
                print(f"  Processing: {notes_file}")
                checker.check_file(notes_file)
            
            # Also check any subdirectory
            for subdir in path.iterdir():
                if subdir.is_dir():
                    for notes_file in subdir.glob("*-educational-notes.json"):
                        print(f"  Processing: {notes_file}")
                        checker.check_file(notes_file)
        elif path.suffix == '.json':
            print(f"  Processing: {path}")
            checker.check_file(path)
    
    if not checked_any:
        print("No concept files found in default locations.")
        print("Usage: python check_content_quality.py [path1] [path2] ...")
        print("\nSearched locations:")
        for p in default_paths:
            print(f"  - {p} {'(exists)' if p.exists() else '(not found)'}")
        return
    
    # Print summary report
    print("\n" + checker.generate_summary_report())
    
    # Save detailed JSON report
    if checker.reports:
        json_report = checker.generate_detailed_json_report()
        report_path = Path("content_quality_report.json")
        with open(report_path, 'w') as f:
            json.dump(json_report, f, indent=2)
        print(f"\nDetailed report saved to: {report_path}")


if __name__ == "__main__":
    main()
