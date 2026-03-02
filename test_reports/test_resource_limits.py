#!/usr/bin/env python3
"""
Test resource limits and edge cases.
"""

from __future__ import annotations

import gc
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import fitz
from algl_pdf_helper.indexer import build_index
from algl_pdf_helper.models import IndexBuildOptions


def create_edge_case_pdf(output_path: Path, case_type: str):
    """Create PDFs with edge case characteristics."""
    doc = fitz.open()
    
    if case_type == "empty_pages":
        # PDF with mostly empty pages
        for i in range(50):
            page = doc.new_page()
            if i % 5 == 0:
                page.insert_text((50, 50), f"Page {i+1} has content", fontsize=12)
    
    elif case_type == "very_long_lines":
        # PDF with very long lines (no spaces)
        for i in range(10):
            page = doc.new_page()
            long_text = "A" * 10000
            page.insert_text((50, 50), long_text[:5000], fontsize=10)
    
    elif case_type == "special_chars":
        # PDF with special Unicode characters
        for i in range(10):
            page = doc.new_page()
            text = f"Page {i+1}\n" + "特殊字符 🎉 émojis \u0000\u0001\u0002 tabs\t\t\t newlines\n\n\n"
            page.insert_text((50, 50), text, fontsize=12)
    
    elif case_type == "single_huge_page":
        # One page with massive content
        page = doc.new_page()
        text = "Word " * 100000  # 100k words
        page.insert_text((50, 50), text[:500000], fontsize=10)  # Limit to fit
    
    elif case_type == "many_small_pages":
        # Many pages with minimal content
        for i in range(1000):
            page = doc.new_page()
            page.insert_text((50, 50), f"P{i+1}", fontsize=12)
    
    elif case_type == "images_only":
        # Pages with no text (images only simulation)
        for i in range(20):
            doc.new_page()  # Empty pages
    
    else:
        # Default
        for i in range(10):
            page = doc.new_page()
            page.insert_text((50, 50), f"Page {i+1} content", fontsize=12)
    
    doc.save(output_path)
    doc.close()
    return output_path


def test_edge_case(case_type: str, output_base: Path) -> dict:
    """Test a specific edge case."""
    print(f"\n{'='*60}")
    print(f"Testing: {case_type}")
    print(f"{'='*60}")
    
    pdf_path = output_base / f"edge_case_{case_type}.pdf"
    if not pdf_path.exists():
        create_edge_case_pdf(pdf_path, case_type)
    
    output_dir = output_base / f"output_{case_type}"
    output_dir.mkdir(exist_ok=True)
    
    gc.collect()
    tracemalloc.start()
    start = time.perf_counter()
    
    result = {
        "case_type": case_type,
        "success": False,
        "duration": 0.0,
        "peak_memory_mb": 0.0,
        "chunks": 0,
        "error": None,
    }
    
    try:
        doc = build_index(
            input_path=pdf_path,
            out_dir=output_dir,
            options=IndexBuildOptions(),
            extract_assets=False,
        )
        
        result["success"] = True
        result["chunks"] = len(doc.chunks)
        
    except Exception as e:
        result["error"] = str(e)
        print(f"  Error: {e}")
    
    result["duration"] = time.perf_counter() - start
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    result["peak_memory_mb"] = peak / 1024 / 1024
    
    print(f"  Success: {result['success']}")
    print(f"  Time: {result['duration']:.3f}s")
    print(f"  Memory: {result['peak_memory_mb']:.2f} MB")
    print(f"  Chunks: {result['chunks']}")
    
    return result


def test_parameter_combinations(output_base: Path) -> list[dict]:
    """Test various parameter combinations."""
    print(f"\n{'='*60}")
    print("PARAMETER COMBINATION TESTS")
    print(f"{'='*60}")
    
    # Create standard test PDF
    pdf_path = output_base / "param_test.pdf"
    if not pdf_path.exists():
        create_edge_case_pdf(pdf_path, "default")
    
    results = []
    
    # Test extreme parameters
    test_cases = [
        {"chunkWords": 20, "overlapWords": 0, "name": "min_chunk_no_overlap"},
        {"chunkWords": 20, "overlapWords": 19, "name": "min_chunk_max_overlap"},
        {"chunkWords": 2000, "overlapWords": 0, "name": "max_chunk_no_overlap"},
        {"chunkWords": 2000, "overlapWords": 1000, "name": "max_chunk_large_overlap"},
        {"chunkWords": 180, "overlapWords": 0, "name": "default_chunk_no_overlap"},
        {"chunkWords": 180, "overlapWords": 179, "name": "default_chunk_max_overlap"},
    ]
    
    for case in test_cases:
        print(f"\nTesting: {case['name']}")
        print(f"  chunkWords={case['chunkWords']}, overlapWords={case['overlapWords']}")
        
        output_dir = output_base / f"param_{case['name']}"
        output_dir.mkdir(exist_ok=True)
        
        gc.collect()
        tracemalloc.start()
        start = time.perf_counter()
        
        result = {
            "name": case["name"],
            "params": case,
            "success": False,
            "duration": 0.0,
            "peak_memory_mb": 0.0,
            "chunks": 0,
            "error": None,
        }
        
        try:
            options = IndexBuildOptions(
                chunkWords=case["chunkWords"],
                overlapWords=case["overlapWords"],
            )
            doc = build_index(
                input_path=pdf_path,
                out_dir=output_dir,
                options=options,
                extract_assets=False,
            )
            result["success"] = True
            result["chunks"] = len(doc.chunks)
        except Exception as e:
            result["error"] = str(e)
            print(f"  Error: {e}")
        
        result["duration"] = time.perf_counter() - start
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        result["peak_memory_mb"] = peak / 1024 / 1024
        
        print(f"  Success: {result['success']}, Time: {result['duration']:.3f}s, Chunks: {result['chunks']}")
        results.append(result)
    
    return results


def main():
    """Run resource limit tests."""
    print("="*70)
    print("Resource Limits & Edge Cases Testing")
    print("="*70)
    
    output_base = Path(__file__).parent / "resource_limit_tests"
    output_base.mkdir(exist_ok=True)
    
    # Test edge cases
    edge_cases = [
        "empty_pages",
        "very_long_lines",
        "special_chars",
        "many_small_pages",
        "images_only",
    ]
    
    edge_results = []
    for case in edge_cases:
        result = test_edge_case(case, output_base)
        edge_results.append(result)
    
    # Test parameter combinations
    param_results = test_parameter_combinations(output_base)
    
    # Generate summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    print("\n## Edge Cases\n")
    print("| Case | Success | Time (s) | Memory (MB) | Chunks | Error |")
    print("|------|---------|----------|-------------|--------|-------|")
    for r in edge_results:
        error_short = (r['error'][:25] + "...") if r['error'] and len(r['error']) > 25 else (r['error'] or "")
        print(f"| {r['case_type']:20} | {'✓' if r['success'] else '✗':7} | {r['duration']:8.3f} | {r['peak_memory_mb']:11.2f} | {r['chunks']:6} | {error_short:25} |")
    
    print("\n## Parameter Combinations\n")
    print("| Test | chunkWords | overlapWords | Success | Time (s) | Chunks |")
    print("|------|------------|--------------|---------|----------|--------|")
    for r in param_results:
        params = r['params']
        print(f"| {r['name']:25} | {params['chunkWords']:10} | {params['overlapWords']:12} | {'✓' if r['success'] else '✗':7} | {r['duration']:8.3f} | {r['chunks']:6} |")
    
    # Save report
    report_path = output_base / "resource_limits_report.md"
    with open(report_path, "w") as f:
        f.write("# Resource Limits & Edge Cases Test Report\n\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Edge Cases\n\n")
        f.write("| Case | Success | Time (s) | Memory (MB) | Chunks | Error |\n")
        f.write("|------|---------|----------|-------------|--------|-------|\n")
        for r in edge_results:
            error_short = (r['error'][:30] + "...") if r['error'] and len(r['error']) > 30 else (r['error'] or "")
            f.write(f"| {r['case_type']} | {'Yes' if r['success'] else 'No'} | {r['duration']:.3f} | {r['peak_memory_mb']:.2f} | {r['chunks']} | {error_short} |\n")
        
        f.write("\n## Parameter Combinations\n\n")
        f.write("| Test | chunkWords | overlapWords | Success | Time (s) | Chunks |\n")
        f.write("|------|------------|--------------|---------|----------|--------|\n")
        for r in param_results:
            params = r['params']
            f.write(f"| {r['name']} | {params['chunkWords']} | {params['overlapWords']} | {'Yes' if r['success'] else 'No'} | {r['duration']:.3f} | {r['chunks']} |\n")
    
    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()
