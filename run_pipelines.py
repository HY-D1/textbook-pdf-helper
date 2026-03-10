#!/usr/bin/env python3
"""
Run full pipeline on both textbooks.
This script runs outside the timeout-limited shell.
"""
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from algl_pdf_helper.instructional_pipeline import (
    PipelineConfig, 
    InstructionalPipeline,
    process_pdf_to_unit_library
)

def process_textbook(pdf_name, output_name):
    """Process a single textbook."""
    pdf_path = Path(f"raw_pdf/{pdf_name}")
    output_dir = Path(f"outputs/{output_name}")
    
    log_file = Path(f"pipeline_{output_name}.log")
    
    def log(msg):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {msg}"
        print(line)
        with open(log_file, "a") as f:
            f.write(line + "\n")
    
    log(f"=" * 60)
    log(f"Processing: {pdf_name}")
    log(f"Output: {output_dir}")
    log(f"Pages: Checking...")
    
    try:
        import fitz
        doc = fitz.open(pdf_path)
        page_count = doc.page_count
        doc.close()
        log(f"Pages: {page_count}")
    except Exception as e:
        log(f"Error checking pages: {e}")
        page_count = "unknown"
    
    log(f"Starting pipeline...")
    start_time = time.time()
    
    try:
        config = PipelineConfig(
            pdf_path=pdf_path,
            output_dir=output_dir,
            doc_id=f"doc_{output_name}_{int(start_time)}",
            llm_provider="none",  # Don't use LLM for faster processing
            filter_level="production",
            export_mode="prototype",
            skip_reinforcement=True,
            skip_misconceptions=True,
            use_ollama_repair=False,
            validate_sql=False,
        )
        
        pipeline = InstructionalPipeline(config)
        result = pipeline.run()
        
        elapsed = time.time() - start_time
        log(f"Pipeline completed in {elapsed:.1f}s")
        log(f"Success: {result.success}")
        log(f"Stages completed: {len(result.stages_completed)}")
        log(f"Statistics: {result.statistics}")
        
        # Check output
        if output_dir.exists():
            files = list(output_dir.rglob("*"))
            log(f"Output files created: {len(files)}")
            for f in files[:10]:  # Show first 10 files
                log(f"  - {f.relative_to(output_dir)}")
        else:
            log("WARNING: Output directory not created!")
            
    except Exception as e:
        elapsed = time.time() - start_time
        log(f"ERROR after {elapsed:.1f}s: {e}")
        import traceback
        log(traceback.format_exc())
    
    log(f"=" * 60)
    log("")

if __name__ == "__main__":
    # Process both textbooks
    textbooks = [
        ("dbms-ramakrishnan-3rd-edition.pdf", "ramakrishnan"),
        ("murachs-mysql-3rd-edition.pdf", "murach"),
    ]
    
    for pdf_name, output_name in textbooks:
        process_textbook(pdf_name, output_name)
    
    print("\nAll pipelines completed!")
