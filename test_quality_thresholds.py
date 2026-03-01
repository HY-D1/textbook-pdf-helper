"""
Test quality thresholds with various text quality levels.
"""

from __future__ import annotations

from pathlib import Path

from algl_pdf_helper.quality_metrics import (
    TextCoverageAnalyzer,
    QualityThresholds,
    validate_text_quality,
)
from algl_pdf_helper.preflight import run_preflight
from algl_pdf_helper.extract import check_text_coverage


def test_quality_thresholds() -> dict:
    """Test quality thresholds with various text samples."""
    print("\n[Testing Quality Thresholds]")
    
    analyzer = TextCoverageAnalyzer()
    
    # Test cases: (description, text, expected_pass)
    test_cases = [
        # Good quality text
        (
            "Normal readable text",
            "This is a normal sentence with readable words and punctuation.",
            True
        ),
        # SQL code
        (
            "SQL code",
            "SELECT id, name FROM users WHERE active = 1 ORDER BY name ASC;",
            True
        ),
        # Empty text
        (
            "Empty text",
            "",
            False
        ),
        # Whitespace only
        (
            "Whitespace only",
            "   \n\t   ",
            False
        ),
        # Gibberish patterns
        (
            "Repeated dashes",
            "___---___===___",
            False
        ),
        # Mixed content (should still pass)
        (
            "Mixed content",
            "Hello world! 123 Some text here... More text follows.",
            True
        ),
        # Text with some noise
        (
            "Text with noise",
            "Hello world! ___ This is still readable text despite some noise.",
            True  # Should pass if coverage is still above threshold
        ),
        # Very short text
        (
            "Too short",
            "Hi",
            False  # Below MIN_PAGE_CHARS
        ),
        # Normal paragraph
        (
            "Normal paragraph",
            """SQL (Structured Query Language) is a domain-specific language used in programming 
            and designed for managing data held in a relational database management system. 
            It is particularly useful in handling structured data where there are relations 
            between different data entities.""",
            True
        ),
    ]
    
    results = []
    all_passed = True
    
    print(f"\n  Testing {len(test_cases)} text quality scenarios:")
    print(f"  Threshold: {QualityThresholds.MIN_TEXT_COVERAGE:.0%} coverage, "
          f"{QualityThresholds.MIN_PAGE_CHARS} min chars")
    
    for description, text, expected_pass in test_cases:
        result = validate_text_quality(text)
        actual_pass = result["passed"]
        test_passed = actual_pass == expected_pass
        
        all_passed = all_passed and test_passed
        
        results.append({
            "description": description,
            "expected": expected_pass,
            "actual": actual_pass,
            "coverage": result["coverage_score"],
            "chars": result["total_chars"],
            "passed": test_passed,
        })
        
        status = "✓" if test_passed else "✗"
        print(f"    {status} {description}: {result['coverage_score']:.1%} coverage, "
              f"{result['total_chars']} chars -> {'PASS' if actual_pass else 'FAIL'}")
    
    return {
        "all_passed": all_passed,
        "test_count": len(test_cases),
        "passed_count": sum(1 for r in results if r["passed"]),
        "results": results,
    }


def test_pdf_quality_detection(pdf_path: Path) -> dict:
    """Test quality detection on real PDF."""
    print(f"\n[Testing PDF Quality Detection: {pdf_path.name}]")
    
    # Run preflight
    report = run_preflight(pdf_path)
    
    print(f"  Preflight results:")
    print(f"    Page count: {report.page_count}")
    print(f"    Has embedded text: {report.has_embedded_text}")
    print(f"    Text coverage: {report.text_coverage_score:.1%}")
    print(f"    OCR needed: {report.ocr_needed}")
    print(f"    Recommended strategy: {report.recommended_strategy}")
    
    # Direct extraction and check coverage
    from algl_pdf_helper.extract import extract_with_strategy
    pages, info = extract_with_strategy(pdf_path, strategy="direct", auto_ocr=False)
    
    coverage_check = check_text_coverage(pages)
    
    print(f"\n  Extraction results:")
    print(f"    Pages extracted: {len(pages)}")
    print(f"    Total characters: {coverage_check['total_chars']:,}")
    print(f"    Coverage score: {coverage_check['coverage_score']:.1%}")
    print(f"    Meets threshold: {coverage_check['meets_threshold']}")
    
    # Validate consistency
    # Note: Preflight samples pages, so coverage may differ from full extraction
    
    result = {
        "pdf_name": pdf_path.name,
        "preflight": {
            "page_count": report.page_count,
            "has_embedded_text": report.has_embedded_text,
            "text_coverage": report.text_coverage_score,
            "ocr_needed": report.ocr_needed,
            "strategy": report.recommended_strategy,
        },
        "extraction": {
            "page_count": len(pages),
            "total_chars": coverage_check["total_chars"],
            "coverage_score": coverage_check["coverage_score"],
            "meets_threshold": coverage_check["meets_threshold"],
        },
    }
    
    # For a textbook PDF, we expect:
    # - Has embedded text: True
    # - Coverage > 70%
    # - Strategy: direct (if coverage is good)
    
    expected_embedded = True
    expected_coverage_good = coverage_check["coverage_score"] >= 0.7
    
    passed = (
        report.has_embedded_text == expected_embedded and
        expected_coverage_good
    )
    
    result["passed"] = passed
    result["expected"] = {
        "embedded_text": expected_embedded,
        "good_coverage": expected_coverage_good,
    }
    
    status = "✓ PASSED" if passed else "✗ FAILED"
    print(f"\n  Overall: {status}")
    
    return result


def main():
    """Run all quality threshold tests."""
    print("=" * 70)
    print("QUALITY THRESHOLD TESTS")
    print("=" * 70)
    
    # Test 1: Text quality thresholds
    text_results = test_quality_thresholds()
    
    # Test 2: PDF quality detection (using available PDFs)
    pdf_results = []
    
    pdf_files = [
        Path("/Users/harrydai/Desktop/Personal Portfolio/algl-pdf-helper/raw_pdf/murachs-mysql-3rd-edition.pdf"),
        Path("/Users/harrydai/Desktop/Personal Portfolio/algl-pdf-helper/raw_pdf/dbms-ramakrishnan-3rd-edition.pdf"),
    ]
    
    for pdf_path in pdf_files:
        if pdf_path.exists():
            pdf_result = test_pdf_quality_detection(pdf_path)
            pdf_results.append(pdf_result)
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    print(f"\nText Quality Tests: {text_results['passed_count']}/{text_results['test_count']} passed")
    print(f"PDF Quality Tests: {sum(1 for r in pdf_results if r.get('passed'))}/{len(pdf_results)} passed")
    
    all_passed = text_results["all_passed"] and all(r.get("passed") for r in pdf_results)
    
    print(f"\nOverall: {'ALL TESTS PASSED ✓' if all_passed else 'SOME TESTS FAILED ✗'}")
    
    # Save report
    import json
    report = {
        "text_quality_tests": text_results,
        "pdf_quality_tests": pdf_results,
        "all_passed": all_passed,
    }
    
    output_path = Path("/Users/harrydai/Desktop/Personal Portfolio/algl-pdf-helper/test_reports/quality_threshold_results.json")
    output_path.write_text(json.dumps(report, indent=2, default=str))
    print(f"\nResults saved to: {output_path}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
