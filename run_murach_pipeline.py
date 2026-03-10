#!/usr/bin/env python3
"""Run the Murach MySQL PDF through the ALGL PDF Helper pipeline."""
from __future__ import annotations

import time
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from algl_pdf_helper.instructional_pipeline import process_pdf_to_unit_library, PipelineConfig

def main():
    # Record start time
    start_time = time.time()
    
    # Open log file for writing
    log_file = open("murach_pipeline.log", "w", buffering=1)
    
    def log(msg):
        print(msg)
        log_file.write(msg + "\n")
        log_file.flush()
    
    log(f"Starting pipeline at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Processing: raw_pdf/murachs-mysql-3rd-edition.pdf")
    log(f"Output: outputs/murach")
    log(f"Settings:")
    log(f"  - filter_level: production")
    log(f"  - skip_reinforcement: False")
    log(f"  - skip_misconceptions: False")
    log(f"  - use_ollama_repair: False")
    log("")
    
    # Create config
    config = PipelineConfig(
        pdf_path=Path("raw_pdf/murachs-mysql-3rd-edition.pdf"),
        output_dir=Path("outputs/murach"),
        filter_level="production",
        skip_reinforcement=False,
        skip_misconceptions=False,
        use_ollama_repair=False
    )
    
    try:
        result = process_pdf_to_unit_library(config)
        
        elapsed = time.time() - start_time
        log(f"\n=== Pipeline Complete ===")
        log(f"Time taken: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        log(f"Success: {result.success}")
        if result.success:
            log(f"Statistics: {result.statistics}")
        log_file.close()
        return 0
        
    except Exception as e:
        elapsed = time.time() - start_time
        log(f"\n=== Pipeline Failed ===")
        log(f"Error: {e}")
        import traceback
        traceback.print_exc(file=log_file)
        log_file.flush()
        log(f"Time taken: {elapsed:.1f} seconds")
        log_file.close()
        return 1

if __name__ == "__main__":
    sys.exit(main())
