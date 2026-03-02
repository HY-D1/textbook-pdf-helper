#!/usr/bin/env python3
"""
Benchmark real large PDFs from the project.
"""

from __future__ import annotations

import gc
import sys
import time
import tracemalloc
from dataclasses import dataclass, field
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import fitz
from algl_pdf_helper.indexer import build_index
from algl_pdf_helper.models import IndexBuildOptions


@dataclass
class RealPdfBenchmark:
    """Benchmark result for a real PDF."""
    name: str
    path: Path
    size_mb: float
    page_count: int
    processing_time: float
    peak_memory_mb: float
    chunk_count: int
    errors: list[str] = field(default_factory=list)


def get_pdf_info(pdf_path: Path) -> dict:
    """Get PDF metadata."""
    doc = fitz.open(pdf_path)
    info = {
        "page_count": doc.page_count,
        "metadata": doc.metadata,
    }
    doc.close()
    return info


def benchmark_pdf(pdf_path: Path, output_base: Path) -> RealPdfBenchmark:
    """Benchmark a single PDF."""
    name = pdf_path.stem
    size_mb = pdf_path.stat().st_size / 1024 / 1024
    
    print(f"\n{'='*60}")
    print(f"Benchmarking: {name}")
    print(f"Size: {size_mb:.2f} MB")
    print(f"{'='*60}")
    
    # Get PDF info
    info = get_pdf_info(pdf_path)
    page_count = info["page_count"]
    print(f"Pages: {page_count}")
    
    # Prepare output
    output_dir = output_base / f"benchmark_{name}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Clear memory
    gc.collect()
    
    # Benchmark
    options = IndexBuildOptions(
        chunkWords=180,
        overlapWords=30,
        embeddingDim=24,
    )
    
    errors = []
    chunk_count = 0
    
    tracemalloc.start()
    start_time = time.perf_counter()
    
    try:
        result = build_index(
            input_path=pdf_path,
            out_dir=output_dir,
            options=options,
            extract_assets=False,  # Skip asset extraction for speed
        )
        chunk_count = len(result.chunks)
    except Exception as e:
        errors.append(str(e))
        import traceback
        errors.append(traceback.format_exc())
    
    elapsed = time.perf_counter() - start_time
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    peak_mb = peak / 1024 / 1024
    
    benchmark = RealPdfBenchmark(
        name=name,
        path=pdf_path,
        size_mb=size_mb,
        page_count=page_count,
        processing_time=elapsed,
        peak_memory_mb=peak_mb,
        chunk_count=chunk_count,
        errors=errors,
    )
    
    print(f"\nResults:")
    print(f"  Time: {elapsed:.2f}s")
    print(f"  Peak memory: {peak_mb:.2f} MB")
    print(f"  Chunks: {chunk_count}")
    print(f"  Pages/sec: {page_count/elapsed:.2f}")
    print(f"  Chunks/sec: {chunk_count/elapsed:.2f}")
    print(f"  MB/sec: {size_mb/elapsed:.2f}")
    
    if errors:
        print(f"  Errors: {len(errors)}")
        for e in errors[:3]:
            print(f"    - {e[:100]}")
    
    return benchmark


def main():
    """Run benchmarks on real PDFs."""
    print("="*70)
    print("Real PDF Benchmarks")
    print("="*70)
    
    # PDF paths
    pdf_dir = Path(__file__).parent.parent / "raw_pdf"
    pdfs = [
        pdf_dir / "murachs-mysql-3rd-edition.pdf",
        pdf_dir / "dbms-ramakrishnan-3rd-edition.pdf",
    ]
    
    # Output directory
    output_base = Path(__file__).parent / "real_pdf_benchmarks"
    output_base.mkdir(exist_ok=True)
    
    results: list[RealPdfBenchmark] = []
    
    for pdf_path in pdfs:
        if not pdf_path.exists():
            print(f"\nPDF not found: {pdf_path}")
            continue
        
        benchmark = benchmark_pdf(pdf_path, output_base)
        results.append(benchmark)
    
    # Generate summary report
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    print("\n| PDF | Size (MB) | Pages | Time (s) | Memory (MB) | Chunks | Pages/s |")
    print("|-----|-----------|-------|----------|-------------|--------|---------|")
    
    for r in results:
        pages_per_sec = r.page_count / r.processing_time if r.processing_time > 0 else 0
        print(
            f"| {r.name[:30]:30} | {r.size_mb:9.2f} | {r.page_count:5} | "
            f"{r.processing_time:8.2f} | {r.peak_memory_mb:11.2f} | "
            f"{r.chunk_count:6} | {pages_per_sec:7.2f} |"
        )
    
    # Save detailed report
    report_path = output_base / "benchmark_report.md"
    with open(report_path, "w") as f:
        f.write("# Real PDF Benchmark Results\n\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Summary Table\n\n")
        f.write("| PDF | Size (MB) | Pages | Time (s) | Memory (MB) | Chunks | Pages/s | MB/s |\n")
        f.write("|-----|-----------|-------|----------|-------------|--------|---------|------|\n")
        
        for r in results:
            pages_per_sec = r.page_count / r.processing_time if r.processing_time > 0 else 0
            mb_per_sec = r.size_mb / r.processing_time if r.processing_time > 0 else 0
            f.write(
                f"| {r.name} | {r.size_mb:.2f} | {r.page_count} | "
                f"{r.processing_time:.2f} | {r.peak_memory_mb:.2f} | "
                f"{r.chunk_count} | {pages_per_sec:.2f} | {mb_per_sec:.2f} |\n"
            )
        
        f.write("\n## Detailed Results\n\n")
        for r in results:
            f.write(f"### {r.name}\n\n")
            f.write(f"- **Path**: {r.path}\n")
            f.write(f"- **Size**: {r.size_mb:.2f} MB\n")
            f.write(f"- **Pages**: {r.page_count}\n")
            f.write(f"- **Processing Time**: {r.processing_time:.2f} seconds\n")
            f.write(f"- **Peak Memory**: {r.peak_memory_mb:.2f} MB\n")
            f.write(f"- **Chunks Generated**: {r.chunk_count}\n")
            f.write(f"- **Pages/second**: {r.page_count/r.processing_time:.2f}\n")
            f.write(f"- **Chunks/second**: {r.chunk_count/r.processing_time:.2f}\n")
            f.write(f"- **MB/second**: {r.size_mb/r.processing_time:.2f}\n")
            if r.errors:
                f.write(f"- **Errors**: {len(r.errors)}\n")
            f.write("\n")
    
    print(f"\nDetailed report saved to: {report_path}")


if __name__ == "__main__":
    main()
