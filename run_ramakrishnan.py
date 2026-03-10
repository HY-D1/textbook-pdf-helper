#!/usr/bin/env python3
"""Run Ramakrishnan PDF processing pipeline with detailed logging."""
from __future__ import annotations

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from algl_pdf_helper.instructional_pipeline import process_pdf_to_unit_library, PipelineConfig

def main():
    pdf_path = Path("raw_pdf/dbms-ramakrishnan-3rd-edition.pdf")
    output_dir = Path("outputs/ramakrishnan")
    
    print(f"[{time.strftime('%H:%M:%S')}] Starting pipeline")
    print(f"  PDF: {pdf_path}")
    print(f"  Output: {output_dir}")
    print(f"  Pages: ~1,098")
    
    config = PipelineConfig(
        pdf_path=pdf_path,
        output_dir=output_dir,
        filter_level="production",
        export_mode="prototype",
        skip_reinforcement=True,
        skip_misconceptions=True,
        use_ollama_repair=False,
    )
    
    start_time = time.time()
    
    try:
        result = process_pdf_to_unit_library(config=config)
        
        elapsed = time.time() - start_time
        print(f"\n[{time.strftime('%H:%M:%S')}] Pipeline completed successfully!")
        print(f"  Time taken: {elapsed/60:.1f} minutes")
        print(f"  Units generated: {len(result.units) if hasattr(result, 'units') else 'N/A'}")
        
        # List output files
        if output_dir.exists():
            print("\n  Output files:")
            for f in sorted(output_dir.iterdir()):
                size_kb = f.stat().st_size / 1024
                print(f"    {f.name}: {size_kb:.1f} KB")
        
        return 0
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n[{time.strftime('%H:%M:%S')}] Pipeline failed!")
        print(f"  Time elapsed: {elapsed/60:.1f} minutes")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
