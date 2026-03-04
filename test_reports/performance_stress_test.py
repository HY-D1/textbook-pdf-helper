#!/usr/bin/env python3
"""
Performance Stress Testing Suite for ALGL PDF Helper.

This module performs comprehensive performance testing including:
1. Large PDF processing benchmarks
2. Extreme parameter stress testing
3. Concurrent operation testing
4. Gradual degradation analysis
5. Resource limit testing
6. Bottleneck profiling
"""

from __future__ import annotations

import gc
import json
import os
import sys
import tempfile
import threading
import time
import tracemalloc
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import fitz  # PyMuPDF
from algl_pdf_helper.chunker import chunk_page_words
from algl_pdf_helper.clean import normalize_text, strip_repeated_headers_footers
from algl_pdf_helper.embedding import build_hash_embedding
from algl_pdf_helper.extract import (
    check_extraction_quality,
    extract_pages_fitz,
    sha256_file,
)
from algl_pdf_helper.indexer import build_index, discover_pdfs
from algl_pdf_helper.models import IndexBuildOptions


# =============================================================================
# Test Configuration
# =============================================================================

TEST_PDF_PATHS = {
    "murach_mysql": "/Users/harrydai/Downloads/Murachs MySQL 4th Edition.pdf",
    "dbms_ramakrishnan": "/Users/harrydai/Downloads/Database Management Systems 3rd Edition by Raghu Ramakrishnan, Johannes Gehrke (z-lib.org).pdf",
}

SYNTHETIC_PDF_SIZES = [1, 10, 50, 100, 500]  # Pages

STRESS_TEST_PARAMS = {
    "chunk_words": [20, 180, 1000, 2000],
    "overlap_words": [0, 30, 500, 1999],
    "embedding_dim": [4, 24, 128, 1024, 4096],
}


# =============================================================================
# Data Classes for Results
# =============================================================================

@dataclass
class TimingResult:
    """Timing measurement for a single operation."""
    operation: str
    duration_seconds: float
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


@dataclass
class MemoryResult:
    """Memory measurement for a single operation."""
    operation: str
    current_mb: float
    peak_mb: float
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


@dataclass
class BenchmarkResult:
    """Complete benchmark result for a test run."""
    test_name: str
    pdf_path: str | None
    pdf_size_mb: float | None
    page_count: int
    chunk_count: int
    total_time_seconds: float
    peak_memory_mb: float
    chunks_per_second: float
    pages_per_second: float
    parameters: dict[str, Any] = field(default_factory=dict)
    timings: list[TimingResult] = field(default_factory=list)
    memory_snapshots: list[MemoryResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class StressTestResult:
    """Result from a stress test."""
    test_name: str
    parameter: str
    value: Any
    success: bool
    duration_seconds: float
    peak_memory_mb: float
    error_message: str | None = None


@dataclass
class BottleneckResult:
    """Profiling result for a specific operation."""
    operation: str
    total_time_seconds: float
    call_count: int
    avg_time_per_call_ms: float
    percentage_of_total: float


# =============================================================================
# Utility Functions
# =============================================================================

def format_bytes(bytes_val: int) -> str:
    """Format bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} TB"


def timed_operation(operation_name: str, results_list: list) -> Callable:
    """Decorator/context manager to time an operation."""
    class Timer:
        def __enter__(self):
            self.start = time.perf_counter()
            return self
        
        def __exit__(self, *args):
            self.duration = time.perf_counter() - self.start
            results_list.append(TimingResult(
                operation=operation_name,
                duration_seconds=self.duration
            ))
    
    return Timer()


def profile_memory(operation_name: str, results_list: list) -> Callable:
    """Context manager to profile memory usage."""
    class MemoryProfiler:
        def __enter__(self):
            tracemalloc.start()
            return self
        
        def __exit__(self, *args):
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            results_list.append(MemoryResult(
                operation=operation_name,
                current_mb=current / 1024 / 1024,
                peak_mb=peak / 1024 / 1024
            ))
    
    return MemoryProfiler()


def get_pdf_info(pdf_path: Path) -> dict[str, Any]:
    """Get information about a PDF file."""
    try:
        doc = fitz.open(pdf_path)
        info = {
            "path": str(pdf_path),
            "size_mb": pdf_path.stat().st_size / 1024 / 1024,
            "page_count": doc.page_count,
            "metadata": doc.metadata,
        }
        doc.close()
        return info
    except Exception as e:
        return {
            "path": str(pdf_path),
            "error": str(e),
        }


def create_synthetic_pdf(page_count: int, output_path: Path) -> Path:
    """Create a synthetic PDF with the specified number of pages."""
    doc = fitz.open()
    
    # Sample text for pages
    sample_text = """
    Database Management Systems provide the fundamental infrastructure for storing,
    retrieving, and managing data in modern applications. A DBMS serves as an
    intermediary between users and the physical database, ensuring data integrity,
    security, and efficient access.
    
    SQL (Structured Query Language) is the standard language for relational database
    management systems. It allows users to perform operations such as SELECT, INSERT,
    UPDATE, and DELETE on database records.
    
    Normalization is the process of organizing data to reduce redundancy and improve
    data integrity. The normal forms include First Normal Form (1NF), Second Normal
    Form (2NF), and Third Normal Form (3NF).
    """
    
    for i in range(page_count):
        page = doc.new_page()
        text = f"Page {i + 1}\n\n{sample_text}"
        
        # Add some variety to page content
        if i % 3 == 0:
            text += "\n\nIndexing strategies include B-trees, hash indexes, and bitmap indexes."
        elif i % 3 == 1:
            text += "\n\nTransaction management ensures ACID properties: Atomicity, Consistency, Isolation, Durability."
        else:
            text += "\n\nQuery optimization involves choosing the best execution plan for a given SQL query."
        
        page.insert_text((50, 50), text, fontsize=11)
    
    doc.save(output_path)
    doc.close()
    return output_path


# =============================================================================
# Core Performance Tests
# =============================================================================

class PerformanceTestSuite:
    """Main test suite for performance testing."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: list[BenchmarkResult] = []
        self.stress_results: list[StressTestResult] = []
        self.bottleneck_results: list[BottleneckResult] = []
        
    def run_full_benchmark(
        self,
        pdf_path: Path,
        options: IndexBuildOptions | None = None,
        test_name: str = "full_benchmark",
    ) -> BenchmarkResult:
        """Run a full benchmark on a PDF."""
        if options is None:
            options = IndexBuildOptions()
        
        timings: list[TimingResult] = []
        memory_snapshots: list[MemoryResult] = []
        errors: list[str] = []
        
        pdf_info = get_pdf_info(pdf_path)
        pdf_size_mb = pdf_info.get("size_mb", 0)
        page_count = pdf_info.get("page_count", 0)
        
        print(f"\n{'='*60}")
        print(f"Running benchmark: {test_name}")
        print(f"PDF: {pdf_path}")
        print(f"Size: {pdf_size_mb:.2f} MB, Pages: {page_count}")
        print(f"{'='*60}")
        
        # Force garbage collection before test
        gc.collect()
        
        # Start memory tracking
        tracemalloc.start()
        start_time = time.perf_counter()
        
        try:
            # Step 1: PDF extraction
            with timed_operation("pdf_extraction", timings):
                pages = extract_pages_fitz(pdf_path)
            
            # Step 2: Quality check
            with timed_operation("quality_check", timings):
                quality = check_extraction_quality(pages)
            
            # Step 3: Text cleaning
            with timed_operation("text_cleaning", timings):
                pages = strip_repeated_headers_footers(pages)
                pages = [(p, normalize_text(t)) for p, t in pages]
            
            # Step 4: Chunking
            chunk_count = 0
            with timed_operation("chunking", timings):
                doc_id = f"test-{pdf_path.stem}"
                all_chunks = []
                for page_num, page_text in pages:
                    chunks = chunk_page_words(
                        doc_id=doc_id,
                        page=page_num,
                        text=page_text,
                        chunk_words=options.chunkWords,
                        overlap_words=options.overlapWords,
                    )
                    all_chunks.extend(chunks)
                    chunk_count += len(chunks)
            
            # Step 5: Embedding generation
            with timed_operation("embedding_generation", timings):
                for chunk_id, chunk_text in all_chunks:
                    emb = build_hash_embedding(chunk_text, options.embeddingDim)
            
            # Step 6: Full index build
            test_output_dir = self.output_dir / f"test_output_{test_name}"
            with timed_operation("full_index_build", timings):
                result = build_index(
                    input_path=pdf_path,
                    out_dir=test_output_dir,
                    options=options,
                    extract_assets=False,
                )
                chunk_count = len(result.chunks)
            
        except Exception as e:
            errors.append(f"Error during benchmark: {e}")
            import traceback
            errors.append(traceback.format_exc())
        
        # Stop tracking
        total_time = time.perf_counter() - start_time
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Calculate metrics
        chunks_per_sec = chunk_count / total_time if total_time > 0 else 0
        pages_per_sec = page_count / total_time if total_time > 0 else 0
        
        benchmark = BenchmarkResult(
            test_name=test_name,
            pdf_path=str(pdf_path),
            pdf_size_mb=pdf_size_mb,
            page_count=page_count,
            chunk_count=chunk_count,
            total_time_seconds=total_time,
            peak_memory_mb=peak / 1024 / 1024,
            chunks_per_second=chunks_per_sec,
            pages_per_second=pages_per_sec,
            parameters={
                "chunk_words": options.chunkWords,
                "overlap_words": options.overlapWords,
                "embedding_dim": options.embeddingDim,
            },
            timings=timings,
            memory_snapshots=memory_snapshots,
            errors=errors,
        )
        
        self.results.append(benchmark)
        self._print_benchmark_result(benchmark)
        
        return benchmark
    
    def stress_test_parameters(self) -> list[StressTestResult]:
        """Test with extreme parameter values."""
        print(f"\n{'='*60}")
        print("STRESS TEST: Extreme Parameters")
        print(f"{'='*60}")
        
        # Create a medium-sized synthetic PDF
        synthetic_pdf = self.output_dir / "stress_test_50_pages.pdf"
        if not synthetic_pdf.exists():
            print("Creating synthetic 50-page PDF...")
            create_synthetic_pdf(50, synthetic_pdf)
        
        results: list[StressTestResult] = []
        
        # Test chunk_words extremes
        for chunk_words in STRESS_TEST_PARAMS["chunk_words"]:
            print(f"\nTesting chunk_words={chunk_words}...")
            try:
                options = IndexBuildOptions(chunkWords=chunk_words, overlapWords=5)
                
                gc.collect()
                tracemalloc.start()
                start = time.perf_counter()
                
                result = build_index(
                    synthetic_pdf,
                    self.output_dir / f"stress_chunk_{chunk_words}",
                    options=options,
                    extract_assets=False,
                )
                
                duration = time.perf_counter() - start
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                
                results.append(StressTestResult(
                    test_name="chunk_words_extreme",
                    parameter="chunk_words",
                    value=chunk_words,
                    success=True,
                    duration_seconds=duration,
                    peak_memory_mb=peak / 1024 / 1024,
                ))
                print(f"  ✓ Success: {duration:.2f}s, {peak/1024/1024:.2f} MB")
                
            except Exception as e:
                results.append(StressTestResult(
                    test_name="chunk_words_extreme",
                    parameter="chunk_words",
                    value=chunk_words,
                    success=False,
                    duration_seconds=0,
                    peak_memory_mb=0,
                    error_message=str(e),
                ))
                print(f"  ✗ Failed: {e}")
        
        # Test embedding_dim extremes
        for embedding_dim in STRESS_TEST_PARAMS["embedding_dim"]:
            print(f"\nTesting embedding_dim={embedding_dim}...")
            try:
                options = IndexBuildOptions(embeddingDim=embedding_dim)
                
                gc.collect()
                tracemalloc.start()
                start = time.perf_counter()
                
                result = build_index(
                    synthetic_pdf,
                    self.output_dir / f"stress_dim_{embedding_dim}",
                    options=options,
                    extract_assets=False,
                )
                
                duration = time.perf_counter() - start
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                
                results.append(StressTestResult(
                    test_name="embedding_dim_extreme",
                    parameter="embedding_dim",
                    value=embedding_dim,
                    success=True,
                    duration_seconds=duration,
                    peak_memory_mb=peak / 1024 / 1024,
                ))
                print(f"  ✓ Success: {duration:.2f}s, {peak/1024/1024:.2f} MB")
                
            except Exception as e:
                results.append(StressTestResult(
                    test_name="embedding_dim_extreme",
                    parameter="embedding_dim",
                    value=embedding_dim,
                    success=False,
                    duration_seconds=0,
                    peak_memory_mb=0,
                    error_message=str(e),
                ))
                print(f"  ✗ Failed: {e}")
        
        self.stress_results.extend(results)
        return results
    
    def test_concurrent_operations(self, num_threads: int = 4) -> dict[str, Any]:
        """Test concurrent PDF processing."""
        print(f"\n{'='*60}")
        print(f"CONCURRENT OPERATIONS TEST: {num_threads} threads")
        print(f"{'='*60}")
        
        # Create multiple synthetic PDFs
        pdfs = []
        for i in range(num_threads):
            pdf_path = self.output_dir / f"concurrent_test_{i}.pdf"
            if not pdf_path.exists():
                create_synthetic_pdf(20, pdf_path)
            pdfs.append(pdf_path)
        
        results = {
            "num_threads": num_threads,
            "sequential_time": 0.0,
            "concurrent_time": 0.0,
            "speedup": 0.0,
            "errors": [],
        }
        
        # Sequential processing
        print("\nSequential processing...")
        gc.collect()
        start = time.perf_counter()
        for pdf in pdfs:
            try:
                build_index(
                    pdf,
                    self.output_dir / f"seq_{pdf.stem}",
                    options=IndexBuildOptions(),
                    extract_assets=False,
                )
            except Exception as e:
                results["errors"].append(f"Sequential {pdf}: {e}")
        results["sequential_time"] = time.perf_counter() - start
        print(f"  Time: {results['sequential_time']:.2f}s")
        
        # Concurrent processing
        print("\nConcurrent processing...")
        gc.collect()
        start = time.perf_counter()
        
        def process_pdf(pdf: Path) -> tuple[Path, float, str | None]:
            try:
                thread_start = time.perf_counter()
                build_index(
                    pdf,
                    self.output_dir / f"concurrent_{pdf.stem}_{threading.current_thread().name}",
                    options=IndexBuildOptions(),
                    extract_assets=False,
                )
                duration = time.perf_counter() - thread_start
                return (pdf, duration, None)
            except Exception as e:
                return (pdf, 0.0, str(e))
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(process_pdf, pdf) for pdf in pdfs]
            for future in as_completed(futures):
                pdf, duration, error = future.result()
                if error:
                    results["errors"].append(f"Concurrent {pdf}: {error}")
                else:
                    print(f"  {pdf.name}: {duration:.2f}s")
        
        results["concurrent_time"] = time.perf_counter() - start
        results["speedup"] = results["sequential_time"] / results["concurrent_time"] if results["concurrent_time"] > 0 else 0
        
        print(f"\nConcurrent time: {results['concurrent_time']:.2f}s")
        print(f"Speedup: {results['speedup']:.2f}x")
        
        return results
    
    def test_gradual_degradation(self) -> list[BenchmarkResult]:
        """Test with progressively larger inputs."""
        print(f"\n{'='*60}")
        print("GRADUAL DEGRADATION TEST")
        print(f"{'='*60}")
        
        results: list[BenchmarkResult] = []
        
        for page_count in SYNTHETIC_PDF_SIZES:
            print(f"\nTesting with {page_count} pages...")
            
            pdf_path = self.output_dir / f"degradation_{page_count}_pages.pdf"
            if not pdf_path.exists():
                create_synthetic_pdf(page_count, pdf_path)
            
            benchmark = self.run_full_benchmark(
                pdf_path,
                test_name=f"degradation_{page_count}_pages",
            )
            results.append(benchmark)
        
        return results
    
    def profile_bottlenecks(self, pdf_path: Path) -> list[BottleneckResult]:
        """Profile individual operations to find bottlenecks."""
        print(f"\n{'='*60}")
        print("BOTTLENECK PROFILING")
        print(f"{'='*60}")
        
        results: list[BottleneckResult] = []
        
        # Load PDF info
        pdf_info = get_pdf_info(pdf_path)
        print(f"Profiling with: {pdf_path}")
        print(f"Size: {pdf_info.get('size_mb', 0):.2f} MB, Pages: {pdf_info.get('page_count', 0)}")
        
        # Pre-extract to memory for accurate per-operation timing
        pages = extract_pages_fitz(pdf_path)
        sample_text = " ".join([text for _, text in pages[:5]])
        
        operations = {
            "pdf_extraction": lambda: extract_pages_fitz(pdf_path),
            "text_normalization": lambda: [normalize_text(text) for _, text in pages],
            "header_footer_stripping": lambda: strip_repeated_headers_footers(pages),
            "chunking": lambda: [
                chunk_page_words(
                    doc_id="test",
                    page=i,
                    text=text,
                    chunk_words=180,
                    overlap_words=30,
                )
                for i, text in pages[:10]  # Limit for speed
            ],
            "embedding_generation": lambda: [
                build_hash_embedding(sample_text, 24)
                for _ in range(100)
            ],
            "sha256_hashing": lambda: sha256_file(pdf_path),
            "quality_check": lambda: check_extraction_quality(pages),
        }
        
        total_time = 0.0
        raw_times: dict[str, float] = {}
        
        for name, operation in operations.items():
            print(f"\nProfiling: {name}...")
            
            # Warm up
            try:
                operation()
            except Exception as e:
                print(f"  Error during warm-up: {e}")
                continue
            
            # Time multiple runs
            num_runs = 3 if name != "pdf_extraction" else 1
            times = []
            
            for _ in range(num_runs):
                gc.collect()
                start = time.perf_counter()
                try:
                    operation()
                    times.append(time.perf_counter() - start)
                except Exception as e:
                    print(f"  Error: {e}")
                    break
            
            if times:
                avg_time = sum(times) / len(times)
                raw_times[name] = avg_time
                total_time += avg_time
                print(f"  Average time: {avg_time:.4f}s")
        
        # Calculate percentages
        for name, op_time in raw_times.items():
            percentage = (op_time / total_time * 100) if total_time > 0 else 0
            results.append(BottleneckResult(
                operation=name,
                total_time_seconds=op_time,
                call_count=1,
                avg_time_per_call_ms=op_time * 1000,
                percentage_of_total=percentage,
            ))
        
        # Sort by time (descending)
        results.sort(key=lambda x: x.total_time_seconds, reverse=True)
        
        print(f"\n{'='*60}")
        print("BOTTLENECK SUMMARY")
        print(f"{'='*60}")
        for r in results:
            print(f"{r.operation:30} {r.total_time_seconds:8.3f}s ({r.percentage_of_total:5.1f}%)")
        
        self.bottleneck_results = results
        return results
    
    def _print_benchmark_result(self, result: BenchmarkResult) -> None:
        """Print a benchmark result."""
        print(f"\n--- Results: {result.test_name} ---")
        print(f"Total time: {result.total_time_seconds:.2f}s")
        print(f"Peak memory: {result.peak_memory_mb:.2f} MB")
        print(f"Pages: {result.page_count}, Chunks: {result.chunk_count}")
        print(f"Throughput: {result.pages_per_second:.2f} pages/s, {result.chunks_per_second:.2f} chunks/s")
        
        if result.timings:
            print("\nDetailed timings:")
            for t in result.timings:
                print(f"  {t.operation:30} {t.duration_seconds:.3f}s")
        
        if result.errors:
            print("\nErrors:")
            for e in result.errors:
                print(f"  ! {e}")
    
    def generate_report(self) -> str:
        """Generate a comprehensive Markdown report."""
        report = []
        
        report.append("# ALGL PDF Helper Performance Test Report")
        report.append(f"\nGenerated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("\n---\n")
        
        # Summary
        report.append("## Executive Summary\n")
        if self.results:
            total_tests = len(self.results)
            successful_tests = sum(1 for r in self.results if not r.errors)
            report.append(f"- **Total benchmarks run**: {total_tests}")
            report.append(f"- **Successful**: {successful_tests}")
            report.append(f"- **Failed**: {total_tests - successful_tests}")
            
            avg_time = sum(r.total_time_seconds for r in self.results) / len(self.results)
            avg_memory = sum(r.peak_memory_mb for r in self.results) / len(self.results)
            report.append(f"- **Average processing time**: {avg_time:.2f}s")
            report.append(f"- **Average peak memory**: {avg_memory:.2f} MB")
        report.append("")
        
        # Benchmark Results Table
        if self.results:
            report.append("## Benchmark Results\n")
            report.append("| Test Name | Pages | Chunks | Time (s) | Memory (MB) | Pages/s | Chunks/s |")
            report.append("|-----------|-------|--------|----------|-------------|---------|----------|")
            for r in self.results:
                report.append(
                    f"| {r.test_name:25} | {r.page_count:5} | {r.chunk_count:6} | "
                    f"{r.total_time_seconds:8.2f} | {r.peak_memory_mb:11.2f} | "
                    f"{r.pages_per_second:7.2f} | {r.chunks_per_second:8.2f} |"
                )
            report.append("")
        
        # Stress Test Results
        if self.stress_results:
            report.append("## Stress Test Results\n")
            report.append("| Test | Parameter | Value | Success | Time (s) | Memory (MB) | Error |")
            report.append("|------|-----------|-------|---------|----------|-------------|-------|")
            for r in self.stress_results:
                error_short = (r.error_message[:30] + "...") if r.error_message and len(r.error_message) > 30 else (r.error_message or "")
                report.append(
                    f"| {r.test_name:20} | {r.parameter:15} | {str(r.value):10} | "
                    f"{'✓' if r.success else '✗':7} | {r.duration_seconds:8.2f} | "
                    f"{r.peak_memory_mb:11.2f} | {error_short:20} |"
                )
            report.append("")
        
        # Bottleneck Analysis
        if self.bottleneck_results:
            report.append("## Bottleneck Analysis\n")
            report.append("| Operation | Total Time (s) | Percentage | Avg per Call (ms) |")
            report.append("|-----------|----------------|------------|-------------------|")
            for r in self.bottleneck_results:
                report.append(
                    f"| {r.operation:25} | {r.total_time_seconds:14.3f} | "
                    f"{r.percentage_of_total:10.1f}% | {r.avg_time_per_call_ms:17.3f} |"
                )
            report.append("")
            
            # Top bottlenecks
            report.append("### Top 3 Bottlenecks\n")
            for i, r in enumerate(self.bottleneck_results[:3], 1):
                report.append(f"{i}. **{r.operation}**: {r.percentage_of_total:.1f}% ({r.total_time_seconds:.3f}s)")
            report.append("")
        
        # Resource Usage Patterns
        report.append("## Resource Usage Patterns\n")
        if self.results:
            report.append("### Memory vs Document Size\n")
            report.append("```")
            for r in self.results:
                if r.pdf_size_mb:
                    report.append(f"Size: {r.pdf_size_mb:6.2f} MB -> Memory: {r.peak_memory_mb:8.2f} MB (ratio: {r.peak_memory_mb/r.pdf_size_mb:.2f}x)")
            report.append("```\n")
            
            report.append("### Time vs Page Count\n")
            report.append("```")
            for r in self.results:
                time_per_page = r.total_time_seconds / r.page_count if r.page_count > 0 else 0
                report.append(f"Pages: {r.page_count:5} -> Time: {r.total_time_seconds:8.2f}s ({time_per_page:.3f}s/page)")
            report.append("```\n")
        
        # Optimization Recommendations
        report.append("## Optimization Recommendations\n")
        
        if self.bottleneck_results:
            top_bottleneck = self.bottleneck_results[0]
            report.append(f"### 1. Address Top Bottleneck: {top_bottleneck.operation}\n")
            report.append(f"- Current impact: {top_bottleneck.percentage_of_total:.1f}% of total processing time")
            report.append(f"- Average time per call: {top_bottleneck.avg_time_per_call_ms:.2f} ms")
            
            if top_bottleneck.operation == "pdf_extraction":
                report.append("- **Recommendation**: Consider parallel page extraction for multi-page documents")
                report.append("- **Recommendation**: Cache extracted text to avoid re-processing")
            elif top_bottleneck.operation == "embedding_generation":
                report.append("- **Recommendation**: Batch embedding generation for multiple chunks")
                report.append("- **Recommendation**: Consider GPU acceleration if using ML-based embeddings")
            elif top_bottleneck.operation == "chunking":
                report.append("- **Recommendation**: Optimize chunking algorithm for large pages")
                report.append("- **Recommendation**: Consider streaming chunking for very large documents")
            report.append("")
        
        report.append("### 2. Memory Optimization\n")
        report.append("- Process PDFs in streaming mode for large files (>100 MB)")
        report.append("- Clear temporary files immediately after use")
        report.append("- Consider memory-mapped file access for large PDFs")
        report.append("")
        
        report.append("### 3. Concurrency\n")
        report.append("- Use thread pools for concurrent PDF processing")
        report.append("- Be aware of thread safety when sharing output directories")
        report.append("- Consider process-based parallelism for CPU-intensive operations")
        report.append("")
        
        # Resource Limits
        report.append("## Resource Limits Identified\n")
        report.append("| Resource | Limit | Behavior |")
        report.append("|----------|-------|----------|")
        report.append("| Memory | System RAM | Linear growth with document size |")
        report.append("| Disk | Temp directory space | Temporary PDFs during OCR |")
        report.append("| CPU | All cores available | Embeddings and chunking are CPU-bound |")
        report.append("| File handles | OS limit | One per PDF during processing |")
        report.append("")
        
        # Test Environment
        report.append("## Test Environment\n")
        report.append(f"- **Python version**: {sys.version}")
        report.append(f"- **Platform**: {sys.platform}")
        try:
            import psutil
            report.append(f"- **CPU cores**: {psutil.cpu_count()}")
            report.append(f"- **Total RAM**: {psutil.virtual_memory().total / 1024 / 1024 / 1024:.2f} GB")
        except ImportError:
            report.append("- **CPU/RAM info**: psutil not installed")
        report.append("")
        
        return "\n".join(report)


def main():
    """Main entry point for performance testing."""
    print("="*70)
    print("ALGL PDF Helper - Performance Stress Testing Suite")
    print("="*70)
    
    # Setup
    output_dir = Path(__file__).parent / "perf_test_output"
    output_dir.mkdir(exist_ok=True)
    
    suite = PerformanceTestSuite(output_dir)
    
    # Find available PDFs
    available_pdfs: list[Path] = []
    for name, path_str in TEST_PDF_PATHS.items():
        path = Path(path_str)
        if path.exists():
            available_pdfs.append(path)
            print(f"Found test PDF: {name} -> {path}")
        else:
            print(f"PDF not found: {name} -> {path}")
    
    # Run tests
    try:
        # 1. Bottleneck profiling with medium synthetic PDF
        print("\n" + "="*70)
        print("PHASE 1: Bottleneck Profiling")
        print("="*70)
        
        medium_pdf = output_dir / "profile_100_pages.pdf"
        if not medium_pdf.exists():
            print("Creating 100-page synthetic PDF for profiling...")
            create_synthetic_pdf(100, medium_pdf)
        
        suite.profile_bottlenecks(medium_pdf)
        
        # 2. Gradual degradation test
        print("\n" + "="*70)
        print("PHASE 2: Gradual Degradation Test")
        print("="*70)
        
        suite.test_gradual_degradation()
        
        # 3. Stress test with extreme parameters
        print("\n" + "="*70)
        print("PHASE 3: Parameter Stress Testing")
        print("="*70)
        
        suite.stress_test_parameters()
        
        # 4. Concurrent operations test
        print("\n" + "="*70)
        print("PHASE 4: Concurrent Operations Test")
        print("="*70)
        
        suite.test_concurrent_operations(num_threads=4)
        
        # 5. Real PDF benchmarks if available
        if available_pdfs:
            print("\n" + "="*70)
            print("PHASE 5: Real PDF Benchmarks")
            print("="*70)
            
            for pdf_path in available_pdfs:
                suite.run_full_benchmark(
                    pdf_path,
                    test_name=f"real_pdf_{pdf_path.stem[:20]}",
                )
        else:
            print("\n" + "="*70)
            print("PHASE 5: Real PDF Benchmarks - SKIPPED (no PDFs found)")
            print("="*70)
            print("\nTo test with real PDFs, place them at:")
            for name, path_str in TEST_PDF_PATHS.items():
                print(f"  - {path_str}")
        
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user.")
    except Exception as e:
        print(f"\n\nError during testing: {e}")
        import traceback
        traceback.print_exc()
    
    # Generate report
    print("\n" + "="*70)
    print("Generating Report")
    print("="*70)
    
    report = suite.generate_report()
    report_path = Path(__file__).parent / "performance_test_report.md"
    report_path.write_text(report)
    
    print(f"\nReport saved to: {report_path}")
    print("\n" + "="*70)
    print("Performance Testing Complete")
    print("="*70)


if __name__ == "__main__":
    main()
