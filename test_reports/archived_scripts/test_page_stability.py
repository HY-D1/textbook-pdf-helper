"""
Test page number stability before and after OCR processing.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from algl_pdf_helper.extract import (
    extract_pages_with_page_map,
    ocr_pdf_with_validation,
)


def test_page_stability(pdf_path: Path, max_pages: int = 10) -> dict:
    """Test that page numbers remain stable after OCR.
    
    Args:
        pdf_path: Path to PDF file
        max_pages: Maximum pages to test (for performance)
        
    Returns:
        Test results dictionary
    """
    print(f"\nTesting page stability for: {pdf_path.name}")
    print(f"Testing first {max_pages} pages...")
    
    # Step 1: Extract directly from original PDF
    pages_before, metadata_before = extract_pages_with_page_map(pdf_path)
    print(f"  Original: {len(pages_before)} pages")
    
    # Limit to max_pages for testing
    if len(pages_before) > max_pages:
        pages_before = pages_before[:max_pages]
    
    # Step 2: OCR the PDF (using first max_pages only)
    import fitz
    doc = fitz.open(pdf_path)
    temp_pdf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    temp_path = Path(temp_pdf.name)
    
    new_doc = fitz.open()
    for i in range(min(max_pages, doc.page_count)):
        new_doc.insert_pdf(doc, from_page=i, to_page=i)
    new_doc.save(temp_path)
    new_doc.close()
    doc.close()
    
    try:
        # Step 3: OCR the temp PDF
        ocr_path, validation = ocr_pdf_with_validation(temp_path)
        print(f"  OCR validation: {validation['coverage_score']:.1%} coverage")
        
        # Step 4: Extract from OCR'd PDF
        pages_after, metadata_after = extract_pages_with_page_map(ocr_path)
        print(f"  After OCR: {len(pages_after)} pages")
        
        # Step 5: Compare page numbers
        page_numbers_before = [p[0] for p in pages_before]
        page_numbers_after = [p[0] for p in pages_after]
        
        # Check alignment
        aligned = len(pages_before) == len(pages_after)
        sequential_before = page_numbers_before == list(range(1, len(pages_before) + 1))
        sequential_after = page_numbers_after == list(range(1, len(pages_after) + 1))
        
        # Check content similarity (basic check)
        content_similar = True
        if aligned:
            for i, ((num1, text1), (num2, text2)) in enumerate(zip(pages_before, pages_after)):
                # Text lengths should be roughly similar (within 50%)
                if len(text1) > 0 and len(text2) > 0:
                    ratio = min(len(text1), len(text2)) / max(len(text1), len(text2))
                    if ratio < 0.3:  # Less than 30% similarity in length
                        print(f"    Warning: Page {i+1} text length differs significantly")
                        print(f"      Before: {len(text1)} chars, After: {len(text2)} chars")
                        content_similar = False
                        break
        
        result = {
            "pdf_name": pdf_path.name,
            "pages_before": len(pages_before),
            "pages_after": len(pages_after),
            "pages_aligned": aligned,
            "sequential_before": sequential_before,
            "sequential_after": sequential_after,
            "content_similar": content_similar,
            "page_numbers_before": page_numbers_before,
            "page_numbers_after": page_numbers_after,
            "ocr_coverage": validation["coverage_score"],
            "passed": aligned and sequential_before and sequential_after,
        }
        
        # Cleanup OCR temp file
        from algl_pdf_helper.extract import cleanup_temp_pdf
        cleanup_temp_pdf(ocr_path)
        
        return result
        
    finally:
        temp_path.unlink(missing_ok=True)


def main():
    """Run page stability tests."""
    import json
    
    pdf_files = [
        Path("/Users/harrydai/Desktop/Personal Portfolio/algl-pdf-helper/raw_pdf/murachs-mysql-3rd-edition.pdf"),
        Path("/Users/harrydai/Desktop/Personal Portfolio/algl-pdf-helper/raw_pdf/dbms-ramakrishnan-3rd-edition.pdf"),
    ]
    
    results = []
    
    for pdf_path in pdf_files:
        if pdf_path.exists():
            result = test_page_stability(pdf_path, max_pages=5)
            results.append(result)
            
            print(f"\n  Results:")
            print(f"    Pages aligned: {result['pages_aligned']} ✓" if result['pages_aligned'] else "    Pages aligned: ✗")
            print(f"    Sequential before: {result['sequential_before']} ✓" if result['sequential_before'] else "    Sequential before: ✗")
            print(f"    Sequential after: {result['sequential_after']} ✓" if result['sequential_after'] else "    Sequential after: ✗")
            print(f"    Content similar: {result['content_similar']} ✓" if result['content_similar'] else "    Content similar: ✗")
            print(f"    Overall: {'PASSED ✓' if result['passed'] else 'FAILED ✗'}")
    
    # Summary
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    
    print(f"\n{'='*60}")
    print(f"Page Stability Test Summary: {passed}/{total} passed")
    print(f"{'='*60}")
    
    # Save results
    output_path = Path("/Users/harrydai/Desktop/Personal Portfolio/algl-pdf-helper/test_reports/page_stability_results.json")
    output_path.write_text(json.dumps(results, indent=2, default=str))
    print(f"\nResults saved to: {output_path}")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
