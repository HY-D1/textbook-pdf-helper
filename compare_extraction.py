#!/usr/bin/env python3
"""
Compare PyMuPDF vs Marker extraction quality.

Run this to see the difference in text extraction quality.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from algl_pdf_helper.extract_marker import (
    MARKER_AVAILABLE,
    compare_extraction_methods,
    extract_with_marker,
)


def print_comparison(pdf_path: Path):
    """Print side-by-side comparison."""
    print("=" * 80)
    print(f"EXTRACTION QUALITY COMPARISON")
    print(f"PDF: {pdf_path}")
    print("=" * 80)
    
    # PyMuPDF extraction
    print("\n📄 PYMuPDF (Current Method)")
    print("-" * 80)
    
    import fitz
    doc = fitz.open(str(pdf_path))
    
    # Get pages 23-25 (content pages from Murach's)
    for page_num in [23, 24, 25]:
        if page_num < len(doc):
            page = doc[page_num - 1]  # 0-indexed
            text = page.get_text()[:500]
            print(f"\nPage {page_num}:")
            print(text)
            print()
    
    doc.close()
    
    # Marker extraction
    if MARKER_AVAILABLE:
        print("\n📄 MARKER (New Method)")
        print("-" * 80)
        
        try:
            # Note: This will be slow on first run (downloads models)
            markdown, pages, metadata = extract_with_marker(pdf_path)
            
            print(f"Metadata: {metadata}")
            print(f"\nSample output (first 1500 chars):")
            print(markdown[:1500])
            
        except Exception as e:
            print(f"Error: {e}")
            print("Note: First run downloads ~3GB of models")
    else:
        print("\n❌ MARKER NOT INSTALLED")
        print("Install with: pip install marker-pdf")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("""
PyMuPDF:
- ✅ Fast
- ❌ OCR artifacts (con1ponents, syste111)
- ❌ No structure (TOC mixed with content)
- ❌ Headers/footers included

Marker:
- ✅ Cleaner text
- ✅ Preserves structure (sections, lists)
- ✅ Removes headers/footers
- ❌ Slower (especially first run)
- ❌ Requires ~3GB models

RECOMMENDATION:
Use Marker for one-time processing of textbooks to get
high-quality, structured content suitable for learning.
""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        pdf_path = Path("raw_pdf/murachs-mysql-3rd-edition.pdf")
        if not pdf_path.exists():
            print(f"Usage: python compare_extraction.py <pdf_path>")
            sys.exit(1)
    else:
        pdf_path = Path(sys.argv[1])
    
    print_comparison(pdf_path)
