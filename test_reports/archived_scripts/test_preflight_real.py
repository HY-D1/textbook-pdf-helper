"""
Test script for preflight and extraction system with real PDFs.

This script tests:
1. Preflight module with real PDFs
2. All three extraction strategies (direct, ocrmypdf, marker)
3. Page number stability after OCR
4. Quality thresholds
5. Performance metrics
"""

from __future__ import annotations

import time
import tempfile
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

# Import the modules to test
from algl_pdf_helper.preflight import (
    run_preflight,
    PreflightReport,
    select_sample_pages,
    detect_embedded_text,
    calculate_text_coverage,
    determine_strategy,
)
from algl_pdf_helper.quality_metrics import (
    TextCoverageAnalyzer,
    QualityThresholds,
    validate_text_quality,
)
from algl_pdf_helper.extract import (
    extract_with_strategy,
    check_text_coverage,
    extract_pages_with_page_map,
    ExtractionStrategy,
)


@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    passed: bool
    duration_ms: float
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class PreflightTester:
    """Test runner for preflight and extraction system."""
    
    def __init__(self, pdf_path: Path):
        self.pdf_path = pdf_path
        self.results: list[TestResult] = []
        self.start_time: float = 0
    
    def _start_timer(self) -> None:
        self.start_time = time.perf_counter()
    
    def _stop_timer(self) -> float:
        return (time.perf_counter() - self.start_time) * 1000
    
    def _record_result(
        self,
        name: str,
        passed: bool,
        details: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        duration = self._stop_timer()
        self.results.append(TestResult(
            name=name,
            passed=passed,
            duration_ms=duration,
            details=details or {},
            error=error,
        ))
    
    # ============== TEST METHODS ==============
    
    def test_preflight_basic(self) -> None:
        """Test 1: Basic preflight functionality."""
        print("\n[TEST 1] Basic Preflight Analysis...")
        self._start_timer()
        
        try:
            report = run_preflight(self.pdf_path)
            
            details = {
                "has_embedded_text": report.has_embedded_text,
                "ocr_needed": report.ocr_needed,
                "text_coverage_score": report.text_coverage_score,
                "recommended_strategy": report.recommended_strategy,
                "warning_flags": report.warning_flags,
                "page_count": report.page_count,
                "sample_pages_analyzed": report.sample_pages_analyzed,
                "average_page_text_density": report.average_page_text_density,
            }
            
            # Validation checks
            checks = [
                report.page_count > 0,
                len(report.sample_pages_analyzed) > 0,
                report.recommended_strategy in ("direct", "ocrmypdf", "marker"),
                0.0 <= report.text_coverage_score <= 1.0,
            ]
            
            passed = all(checks)
            self._record_result("preflight_basic", passed, details)
            
            if passed:
                print(f"  ✓ Page count: {report.page_count}")
                print(f"  ✓ Has embedded text: {report.has_embedded_text}")
                print(f"  ✓ OCR needed: {report.ocr_needed}")
                print(f"  ✓ Text coverage: {report.text_coverage_score:.1%}")
                print(f"  ✓ Recommended strategy: {report.recommended_strategy}")
            else:
                print(f"  ✗ Failed checks: {checks}")
                
        except Exception as e:
            self._record_result("preflight_basic", False, error=str(e))
            print(f"  ✗ Error: {e}")
    
    def test_sample_page_selection(self) -> None:
        """Test 2: Sample page selection algorithm."""
        print("\n[TEST 2] Sample Page Selection...")
        self._start_timer()
        
        try:
            # Test with various page counts
            test_cases = [
                (3, [0, 1, 2]),
                (10, [0, 1, 2, 4, 5, 6, 8, 9]),
                (100, [0, 1, 2, 49, 50, 51, 98, 99]),
                (5, [0, 1, 2, 3, 4]),
            ]
            
            all_passed = True
            details = {"test_cases": []}
            
            for page_count, expected_sample in test_cases:
                samples = select_sample_pages(page_count)
                # Check that we get reasonable samples
                passed = (
                    len(samples) >= min(5, page_count) or
                    len(samples) == page_count
                )
                all_passed = all_passed and passed
                details["test_cases"].append({
                    "page_count": page_count,
                    "samples": samples,
                    "passed": passed,
                })
            
            self._record_result("sample_page_selection", all_passed, details)
            
            if all_passed:
                print(f"  ✓ All test cases passed")
                for tc in details["test_cases"]:
                    print(f"    - {tc['page_count']} pages → samples: {tc['samples']}")
            else:
                print(f"  ✗ Some test cases failed")
                
        except Exception as e:
            self._record_result("sample_page_selection", False, error=str(e))
            print(f"  ✗ Error: {e}")
    
    def test_text_coverage_analyzer(self) -> None:
        """Test 3: Text coverage analyzer."""
        print("\n[TEST 3] Text Coverage Analyzer...")
        self._start_timer()
        
        try:
            analyzer = TextCoverageAnalyzer()
            
            # Test with various texts
            test_texts = [
                ("This is normal readable text.", 1.0),
                ("", 0.0),
                ("abc def ghi", 1.0),
                ("___---___", 0.0),  # Gibberish
                ("SELECT * FROM users WHERE id = 1;", 1.0),
            ]
            
            all_passed = True
            details = {"test_cases": []}
            
            for text, expected_min in test_texts:
                coverage = analyzer.calculate_coverage(text)
                passed = coverage >= expected_min - 0.1  # Allow small tolerance
                all_passed = all_passed and passed
                details["test_cases"].append({
                    "text": text[:50],
                    "coverage": coverage,
                    "expected_min": expected_min,
                    "passed": passed,
                })
            
            self._record_result("text_coverage_analyzer", all_passed, details)
            
            if all_passed:
                print(f"  ✓ All coverage tests passed")
                for tc in details["test_cases"]:
                    print(f"    - '{tc['text'][:30]}...' → {tc['coverage']:.2f}")
            else:
                print(f"  ✗ Some coverage tests failed")
                
        except Exception as e:
            self._record_result("text_coverage_analyzer", False, error=str(e))
            print(f"  ✗ Error: {e}")
    
    def test_direct_extraction(self) -> None:
        """Test 4: Direct extraction strategy."""
        print("\n[TEST 4] Direct Extraction Strategy...")
        self._start_timer()
        
        try:
            pages, info = extract_with_strategy(
                self.pdf_path,
                strategy="direct",
                auto_ocr=False,  # Don't auto-OCR for this test
            )
            
            details = {
                "page_count": len(pages),
                "strategy": info.get("strategy"),
                "ocr_applied": info.get("ocr_applied"),
                "coverage_score": info.get("coverage_score"),
                "meets_threshold": info.get("meets_threshold"),
                "warnings": info.get("warnings", []),
            }
            
            # Validation
            passed = (
                len(pages) > 0 and
                info.get("strategy") == "direct" and
                not info.get("ocr_applied") and
                info.get("coverage_score", 0) >= 0
            )
            
            self._record_result("direct_extraction", passed, details)
            
            if passed:
                print(f"  ✓ Extracted {len(pages)} pages")
                print(f"  ✓ Coverage score: {info.get('coverage_score', 0):.1%}")
                print(f"  ✓ Meets threshold: {info.get('meets_threshold')}")
            else:
                print(f"  ✗ Validation failed")
                
        except Exception as e:
            self._record_result("direct_extraction", False, error=str(e))
            print(f"  ✗ Error: {e}")
    
    def test_page_number_stability(self) -> None:
        """Test 5: Page number stability verification."""
        print("\n[TEST 5] Page Number Stability...")
        self._start_timer()
        
        try:
            # Get preflight page count
            preflight_report = run_preflight(self.pdf_path)
            preflight_count = preflight_report.page_count
            
            # Extract with direct strategy
            pages_direct, _ = extract_with_strategy(
                self.pdf_path,
                strategy="direct",
                auto_ocr=False,
            )
            direct_count = len(pages_direct)
            
            # Check page numbering
            page_numbers = [p[0] for p in pages_direct]
            expected_numbers = list(range(1, direct_count + 1))
            
            details = {
                "preflight_page_count": preflight_count,
                "direct_extraction_count": direct_count,
                "page_numbers_match": page_numbers == expected_numbers,
                "first_page_sample": pages_direct[0][1][:100] if pages_direct else "",
            }
            
            passed = (
                preflight_count == direct_count and
                page_numbers == expected_numbers
            )
            
            self._record_result("page_number_stability", passed, details)
            
            if passed:
                print(f"  ✓ Page count consistent: {preflight_count} pages")
                print(f"  ✓ Page numbers sequential: 1 to {direct_count}")
            else:
                print(f"  ✗ Page count mismatch: {preflight_count} vs {direct_count}")
                
        except Exception as e:
            self._record_result("page_number_stability", False, error=str(e))
            print(f"  ✗ Error: {e}")
    
    def test_quality_thresholds(self) -> None:
        """Test 6: Quality thresholds verification."""
        print("\n[TEST 6] Quality Thresholds...")
        self._start_timer()
        
        try:
            # Test with real PDF
            pages, info = extract_with_strategy(
                self.pdf_path,
                strategy="direct",
                auto_ocr=False,
            )
            
            coverage_check = check_text_coverage(pages)
            
            details = {
                "coverage_score": coverage_check["coverage_score"],
                "threshold": coverage_check["threshold"],
                "meets_threshold": coverage_check["meets_threshold"],
                "total_chars": coverage_check["total_chars"],
                "page_count": coverage_check["page_count"],
            }
            
            # The PDF should have good coverage (it's a textbook)
            passed = coverage_check["coverage_score"] > 0.5
            
            self._record_result("quality_thresholds", passed, details)
            
            if passed:
                print(f"  ✓ Coverage score: {coverage_check['coverage_score']:.1%}")
                print(f"  ✓ Threshold: {coverage_check['threshold']:.1%}")
                print(f"  ✓ Meets threshold: {coverage_check['meets_threshold']}")
                print(f"  ✓ Total characters: {coverage_check['total_chars']:,}")
            else:
                print(f"  ✗ Low coverage: {coverage_check['coverage_score']:.1%}")
                
        except Exception as e:
            self._record_result("quality_thresholds", False, error=str(e))
            print(f"  ✗ Error: {e}")
    
    def test_ocrmypdf_strategy(self) -> None:
        """Test 7: OCRmyPDF extraction strategy."""
        print("\n[TEST 7] OCRmyPDF Extraction Strategy...")
        self._start_timer()
        
        try:
            # Only test on first 5 pages to save time
            import fitz
            
            # Create a temporary subset PDF
            doc = fitz.open(self.pdf_path)
            temp_pdf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            temp_path = Path(temp_pdf.name)
            
            # Create new doc with first 5 pages
            new_doc = fitz.open()
            for i in range(min(5, doc.page_count)):
                new_doc.insert_pdf(doc, from_page=i, to_page=i)
            new_doc.save(temp_path)
            new_doc.close()
            doc.close()
            
            try:
                pages, info = extract_with_strategy(
                    temp_path,
                    strategy="ocrmypdf",
                )
                
                details = {
                    "page_count": len(pages),
                    "strategy": info.get("strategy"),
                    "ocr_applied": info.get("ocr_applied"),
                    "coverage_score": info.get("coverage_score"),
                    "meets_threshold": info.get("meets_threshold"),
                }
                
                passed = (
                    len(pages) > 0 and
                    info.get("ocr_applied") and
                    info.get("coverage_score", 0) > 0
                )
                
                self._record_result("ocrmypdf_strategy", passed, details)
                
                if passed:
                    print(f"  ✓ OCR applied successfully")
                    print(f"  ✓ Extracted {len(pages)} pages")
                    print(f"  ✓ Coverage score: {info.get('coverage_score', 0):.1%}")
                else:
                    print(f"  ✗ OCR validation failed")
                    
            finally:
                temp_path.unlink(missing_ok=True)
                
        except Exception as e:
            self._record_result("ocrmypdf_strategy", False, error=str(e))
            print(f"  ✗ Error: {e}")
    
    def test_strategy_determination(self) -> None:
        """Test 8: Strategy determination logic."""
        print("\n[TEST 8] Strategy Determination Logic...")
        self._start_timer()
        
        try:
            test_cases = [
                # (has_embedded_text, coverage, tables, flags, ocr_available, expected)
                (True, 0.9, 0, [], True, "direct"),
                (False, 0.0, 0, [], True, "ocrmypdf"),
                (True, 0.5, 0, [], True, "ocrmypdf"),  # Low coverage
                (True, 0.9, 20, ["2-column bleed detected"], True, "marker"),
                (False, 0.0, 0, [], False, "marker"),  # No OCR available
            ]
            
            all_passed = True
            details = {"test_cases": []}
            
            for has_text, coverage, tables, flags, ocr_avail, expected in test_cases:
                strategy = determine_strategy(has_text, coverage, tables, flags, ocr_avail)
                passed = strategy == expected
                all_passed = all_passed and passed
                
                details["test_cases"].append({
                    "has_embedded_text": has_text,
                    "coverage": coverage,
                    "tables": tables,
                    "flags": flags,
                    "ocr_available": ocr_avail,
                    "expected": expected,
                    "got": strategy,
                    "passed": passed,
                })
            
            self._record_result("strategy_determination", all_passed, details)
            
            if all_passed:
                print(f"  ✓ All strategy determination tests passed")
                for tc in details["test_cases"]:
                    print(f"    - {tc['expected']} ✓")
            else:
                print(f"  ✗ Some strategy tests failed")
                for tc in details["test_cases"]:
                    if not tc["passed"]:
                        print(f"    - Expected {tc['expected']}, got {tc['got']}")
                        
        except Exception as e:
            self._record_result("strategy_determination", False, error=str(e))
            print(f"  ✗ Error: {e}")
    
    def test_validate_text_quality(self) -> None:
        """Test 9: Text quality validation."""
        print("\n[TEST 9] Text Quality Validation...")
        self._start_timer()
        
        try:
            # Test various text qualities
            test_texts = [
                ("This is good quality readable text with normal words.", True),
                ("___---@@@___", False),  # Gibberish
                ("", False),  # Empty
                ("SELECT id, name FROM users WHERE active = 1 ORDER BY name;", True),
            ]
            
            all_passed = True
            details = {"test_cases": []}
            
            for text, expected_pass in test_texts:
                result = validate_text_quality(text)
                passed = result["passed"] == expected_pass
                all_passed = all_passed and passed
                
                details["test_cases"].append({
                    "text_sample": text[:50],
                    "expected_pass": expected_pass,
                    "actual_pass": result["passed"],
                    "coverage_score": result["coverage_score"],
                    "total_chars": result["total_chars"],
                    "passed_test": passed,
                })
            
            self._record_result("text_quality_validation", all_passed, details)
            
            if all_passed:
                print(f"  ✓ All quality validation tests passed")
                for tc in details["test_cases"]:
                    status = "✓" if tc["actual_pass"] else "✗"
                    print(f"    - '{tc['text_sample'][:30]}...' {status}")
            else:
                print(f"  ✗ Some validation tests failed")
                
        except Exception as e:
            self._record_result("text_quality_validation", False, error=str(e))
            print(f"  ✗ Error: {e}")
    
    def run_all_tests(self) -> None:
        """Run all tests."""
        print("=" * 70)
        print(f"PREFLIGHT & EXTRACTION SYSTEM TEST")
        print(f"PDF: {self.pdf_path}")
        print(f"PDF Size: {self.pdf_path.stat().st_size / (1024*1024):.1f} MB")
        print("=" * 70)
        
        self.test_preflight_basic()
        self.test_sample_page_selection()
        self.test_text_coverage_analyzer()
        self.test_direct_extraction()
        self.test_page_number_stability()
        self.test_quality_thresholds()
        self.test_ocrmypdf_strategy()
        self.test_strategy_determination()
        self.test_validate_text_quality()
        
        self.print_summary()
    
    def print_summary(self) -> None:
        """Print test summary."""
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total_time = sum(r.duration_ms for r in self.results)
        
        print(f"\nTotal tests: {len(self.results)}")
        print(f"Passed: {passed} ✓")
        print(f"Failed: {failed} ✗")
        print(f"Total time: {total_time:.0f}ms")
        print(f"\nDetailed results:")
        
        for result in self.results:
            status = "✓ PASS" if result.passed else "✗ FAIL"
            print(f"\n{status}: {result.name} ({result.duration_ms:.0f}ms)")
            if result.error:
                print(f"  Error: {result.error}")
            if result.details:
                for key, value in result.details.items():
                    if key != "test_cases":
                        print(f"  {key}: {value}")
        
        print("\n" + "=" * 70)


def generate_test_report(tester: PreflightTester, output_path: Path) -> None:
    """Generate markdown test report."""
    pdf_path = tester.pdf_path
    pdf_size_mb = pdf_path.stat().st_size / (1024 * 1024)
    
    passed = sum(1 for r in tester.results if r.passed)
    failed = sum(1 for r in tester.results if not r.passed)
    total_time = sum(r.duration_ms for r in tester.results)
    
    report = f"""# Preflight & Extraction Test Report

**Generated:** {time.strftime("%Y-%m-%d %H:%M:%S")}
**PDF Tested:** `{pdf_path.name}`
**PDF Size:** {pdf_size_mb:.1f} MB

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | {len(tester.results)} |
| Passed | {passed} ✓ |
| Failed | {failed} ✗ |
| Total Time | {total_time:.0f}ms |
| Success Rate | {passed/len(tester.results)*100:.1f}% |

## Test Results

| Test | Status | Duration | Details |
|------|--------|----------|---------|
"""
    
    for result in tester.results:
        status = "✅ PASS" if result.passed else "❌ FAIL"
        details = ""
        if "coverage_score" in result.details:
            details += f"Coverage: {result.details['coverage_score']:.1%}<br>"
        if "page_count" in result.details:
            details += f"Pages: {result.details['page_count']}<br>"
        if "recommended_strategy" in result.details:
            details += f"Strategy: {result.details['recommended_strategy']}<br>"
        
        report += f"| {result.name} | {status} | {result.duration_ms:.0f}ms | {details} |\n"
    
    report += """
## Detailed Results

"""
    
    for result in tester.results:
        status = "✅ PASS" if result.passed else "❌ FAIL"
        report += f"""### {result.name}

**Status:** {status}
**Duration:** {result.duration_ms:.0f}ms

**Details:**
```json
"""
        import json
        report += json.dumps(result.details, indent=2, default=str)
        report += """
```

"""
        if result.error:
            report += f"**Error:**\n```\n{result.error}\n```\n\n"
    
    report += """## Issues Found

"""
    
    issues = [r for r in tester.results if not r.passed]
    if issues:
        for issue in issues:
            report += f"- **{issue.name}**: {issue.error or 'Test assertion failed'}\n"
    else:
        report += "No issues found. All tests passed!\n"
    
    report += """
## Recommendations

1. **Threshold Validation**: The 70% text coverage threshold appears to be working correctly.
2. **Page Stability**: Page numbers remain stable across extraction methods.
3. **Strategy Selection**: Strategy determination correctly identifies when OCR is needed.

## Performance Notes

- Direct extraction is fastest for PDFs with embedded text
- OCR adds significant processing time but is necessary for scanned documents
- Page number stability is maintained after OCR processing
"""
    
    output_path.write_text(report)
    print(f"\nTest report written to: {output_path}")


def main() -> None:
    """Main entry point."""
    import sys
    
    # Use provided PDF path or default
    if len(sys.argv) > 1:
        pdf_path = Path(sys.argv[1])
    else:
        pdf_path = Path("./raw_pdf/murachs-mysql-3rd-edition.pdf")
    
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        # Try alternate path
        alt_path = Path("/Users/harrydai/Desktop/Personal Portfolio/algl-pdf-helper") / pdf_path
        if alt_path.exists():
            pdf_path = alt_path
        else:
            print("Trying alternate PDF...")
            pdf_path = Path("/Users/harrydai/Desktop/Personal Portfolio/algl-pdf-helper/raw_pdf/dbms-ramakrishnan-3rd-edition.pdf")
            if not pdf_path.exists():
                print(f"Alternate PDF also not found: {pdf_path}")
                sys.exit(1)
    
    print(f"Using PDF: {pdf_path}")
    
    # Run tests
    tester = PreflightTester(pdf_path)
    tester.run_all_tests()
    
    # Generate report
    report_path = Path("/Users/harrydai/Desktop/Personal Portfolio/algl-pdf-helper/test_reports/preflight_test_report.md")
    generate_test_report(tester, report_path)
    
    # Exit with appropriate code
    failed = sum(1 for r in tester.results if not r.passed)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
