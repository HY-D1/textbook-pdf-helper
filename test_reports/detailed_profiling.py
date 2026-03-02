#!/usr/bin/env python3
"""
Detailed profiling of PDF processing pipeline.
Uses cProfile for detailed function-level profiling.
"""

from __future__ import annotations

import cProfile
import io
import pstats
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from algl_pdf_helper.indexer import build_index
from algl_pdf_helper.models import IndexBuildOptions


def profile_build_index(pdf_path: Path, output_dir: Path, sort_by: str = "cumulative"):
    """Profile the build_index function."""
    print(f"\n{'='*60}")
    print(f"Profiling: build_index")
    print(f"PDF: {pdf_path}")
    print(f"Sort by: {sort_by}")
    print(f"{'='*60}\n")
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    start = time.perf_counter()
    
    try:
        result = build_index(
            input_path=pdf_path,
            out_dir=output_dir,
            options=IndexBuildOptions(),
            extract_assets=False,
        )
        elapsed = time.perf_counter() - start
        print(f"Completed in {elapsed:.2f}s")
        print(f"Generated {len(result.chunks)} chunks")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        profiler.disable()
    
    # Print stats
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats(sort_by)
    ps.print_stats(50)  # Top 50 functions
    print(s.getvalue())
    
    return profiler


def profile_with_different_sorts(pdf_path: Path, output_base: Path):
    """Profile with different sort options."""
    sorts = ["cumulative", "time", "calls"]
    
    for sort in sorts:
        output_dir = output_base / f"profile_{sort}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        profile_build_index(pdf_path, output_dir, sort_by=sort)
        print("\n" + "="*60)
        input("Press Enter to continue to next profile...")


def main():
    """Run detailed profiling."""
    print("="*70)
    print("Detailed Profiling Suite")
    print("="*70)
    
    # Use the smaller PDF for faster profiling
    pdf_path = Path(__file__).parent.parent / "raw_pdf" / "dbms-ramakrishnan-3rd-edition.pdf"
    
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        return
    
    output_base = Path(__file__).parent / "profiling_output"
    output_base.mkdir(exist_ok=True)
    
    # Profile with cumulative time (most useful for finding bottlenecks)
    profile_build_index(pdf_path, output_base / "profile_run", sort_by="cumulative")


if __name__ == "__main__":
    main()
