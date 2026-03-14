#!/bin/bash
# Re-process PDFs with quality fixes - background execution with logging

set -e

cd "/Users/harrydai/Desktop/Personal Portfolio/algl-pdf-helper"
source .venv/bin/activate

LOG_FILE="reprocess_$(date +%Y%m%d_%H%M%S).log"
OUTPUT_DIR="/Users/harrydai/Desktop/Personal Portfolio/adaptive-instructional-artifacts/apps/web/public/textbook-static"

echo "=========================================="
echo "PDF Re-processing with Quality Fixes"
echo "=========================================="
echo "Log file: $LOG_FILE"
echo "Output: $OUTPUT_DIR"
echo ""

# Function to process a single PDF
process_pdf() {
    local pdf_path=$1
    local pdf_name=$(basename "$pdf_path")
    
    echo "==========================================" | tee -a "$LOG_FILE"
    echo "Processing: $pdf_name" | tee -a "$LOG_FILE"
    echo "Started: $(date)" | tee -a "$LOG_FILE"
    echo "==========================================" | tee -a "$LOG_FILE"
    
    python3 -c "
import sys
sys.path.insert(0, 'src')
from algl_pdf_helper.educational_pipeline import EducationalNoteGenerator
from pathlib import Path
import json

pdf_path = Path('$pdf_path')
output_dir = Path('$OUTPUT_DIR')

print(f'Initializing pipeline...', flush=True)
generator = EducationalNoteGenerator(
    llm_provider='ollama',
    ollama_model='qwen2.5-coder:7b',
    use_marker=True,
    min_content_relevance=0.3,
)

print(f'LLM: {generator.llm_status_message}', flush=True)
print(f'Min relevance: {generator.min_content_relevance}', flush=True)
print(f'Processing PDF...', flush=True)

def progress(step, current, total, message=''):
    pct = int((current/total)*100)
    bar = '█' * (pct//5) + '░' * (20 - pct//5)
    print(f'\\r  [{bar}] {pct:3}% {step:12} {message[:50]}', end='', flush=True)

result = generator.process_pdf(
    pdf_path=pdf_path,
    output_dir=output_dir,
    progress_callback=progress,
)

print('\\n', flush=True)

if result['success']:
    print(f'✅ Success!', flush=True)
    stats = result.get('stats', {})
    print(f'  Pages: {stats.get(\"pages_extracted\", \"N/A\")}', flush=True)
    print(f'  Concepts: {stats.get(\"concepts_generated\", \"N/A\")}', flush=True)
    print(f'  Method: {stats.get(\"extraction_method\", \"N/A\")}', flush=True)
    
    validation = result.get('content_validation', {}).get('summary', {})
    if validation:
        print(f'  Validation: {validation.get(\"relevant\", 0)}/{validation.get(\"total\", 0)} relevant', flush=True)
else:
    print(f'❌ Failed: {result.get(\"errors\", [])}', flush=True)

# Save result summary
with open(output_dir / f'{pdf_path.stem}-reprocess-result.json', 'w') as f:
    json.dump(result, f, indent=2, default=str)
" 2>&1 | tee -a "$LOG_FILE"
    
    echo "" | tee -a "$LOG_FILE"
    echo "Completed: $(date)" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
}

# Process both PDFs
process_pdf "raw_pdf/dbms-ramakrishnan-3rd-edition.pdf"
process_pdf "raw_pdf/murachs-mysql-3rd-edition.pdf"

echo "==========================================" | tee -a "$LOG_FILE"
echo "All PDFs processed!" | tee -a "$LOG_FILE"
echo "Completed: $(date)" | tee -a "$LOG_FILE"
echo "Log saved to: $LOG_FILE" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"
