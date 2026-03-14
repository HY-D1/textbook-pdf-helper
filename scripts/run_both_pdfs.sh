#!/bin/bash
# Process both PDFs with educational note generation

set -e

cd "/Users/harrydai/Desktop/Personal Portfolio/algl-pdf-helper"
source .venv/bin/activate

OUTPUT_DIR="./output/both-pdfs"
mkdir -p "$OUTPUT_DIR"

echo "=========================================="
echo "Processing BOTH PDFs"
echo "=========================================="
echo "Output: $OUTPUT_DIR"
echo "LLM: Ollama (qwen2.5-coder:7b)"
echo ""

# Temporarily move concepts.yaml (Ramakrishnan mappings) so auto-detect works
if [ -f "concepts.yaml" ]; then
    mv concepts.yaml concepts.yaml.bak
    RESTORE_NEEDED=1
fi

# Function to process a single PDF
process_pdf() {
    local pdf_path=$1
    local pdf_name=$(basename "$pdf_path")
    local doc_name="${pdf_name%.pdf}"
    
    echo "=========================================="
    echo "Processing: $pdf_name"
    echo "Started: $(date)"
    echo "=========================================="
    
    python3 -c "
import sys
sys.path.insert(0, 'src')
from algl_pdf_helper.educational_pipeline import EducationalNoteGenerator
from pathlib import Path
import json

pdf_path = Path('$pdf_path')
output_dir = Path('$OUTPUT_DIR')

generator = EducationalNoteGenerator(
    llm_provider='ollama',
    ollama_model='qwen2.5-coder:7b',
    use_marker=False,  # Use PyMuPDF for speed
    min_content_relevance=0.3,
)

print(f'LLM: {generator.llm_status_message}')
print(f'Processing...')

def progress(step, current, total, message=''):
    pct = int((current/total)*100) if total > 0 else 0
    bar = '█' * (pct//5) + '░' * (20 - pct//5)
    print(f'\\r  [{bar}] {pct:3}% {step:15} {message[:45]}', end='', flush=True)

result = generator.process_pdf(
    pdf_path=pdf_path,
    output_dir=output_dir,
    progress_callback=progress,
)

print('\\n')

if result['success']:
    print(f'✅ Success!')
    stats = result.get('stats', {})
    print(f'  Pages: {stats.get(\"pages_extracted\", \"N/A\")}')
    print(f'  Concepts: {stats.get(\"concepts_generated\", \"N/A\")}')
    print(f'  Method: {stats.get(\"extraction_method\", \"N/A\")}')
    print(f'  LLM Enhanced: {stats.get(\"llm_enhanced\", False)}')
    
    validation = result.get('content_validation', {}).get('summary', {})
    if validation:
        print(f'  Relevant: {validation.get(\"relevant\", 0)}/{validation.get(\"total\", 0)}')
else:
    print(f'❌ Failed: {result.get(\"errors\", [])}')

# Save result summary
with open(output_dir / f'{pdf_path.stem}-result.json', 'w') as f:
    json.dump(result, f, indent=2, default=str)
" 2>&1
    
    echo ""
    echo "Completed: $(date)"
    echo ""
}

# Process Murach's MySQL (smaller, faster)
process_pdf "raw_pdf/murachs-mysql-3rd-edition.pdf"

# Process DBMS Ramakrishnan (larger)
process_pdf "raw_pdf/dbms-ramakrishnan-3rd-edition.pdf"

# Restore concepts.yaml if needed
if [ -n "$RESTORE_NEEDED" ]; then
    mv concepts.yaml.bak concepts.yaml
    echo "Restored concepts.yaml"
fi

echo "=========================================="
echo "All PDFs processed!"
echo "Completed: $(date)"
echo "Output: $OUTPUT_DIR"
echo "=========================================="
