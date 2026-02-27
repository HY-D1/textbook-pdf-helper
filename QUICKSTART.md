# Quick Start Guide - Generate Educational Outputs

## Three-Layer Concept Mapping System

The outputs integrate with SQL-Engage's three-layer concept mapping:

```
Layer 1: Error Detection (23 subtypes)
    ↓ mappings/error-subtypes.json
Layer 2: Alignment Map (Error → Concept)
    ↓ mappings/alignment-map.json
Layer 3: Concept Registry (Content)
    ↓ concepts/{doc-id}/*.md + mappings/concept-registry.json
```

## Prerequisites

```bash
# 1. Ensure virtual environment is activated
source .venv/bin/activate

# 2. Verify installation
python3 -m algl_pdf_helper --help
```

## Available PDFs

| PDF | Size | Concepts | Status |
|-----|------|----------|--------|
| `raw_pdf/dbms-ramakrishnan-3rd-edition.pdf` | 94MB | 37 | Ready |
| `raw_pdf/murachs-mysql-3rd-edition.pdf` | 19MB | 33 | Ready |

## Method 1: Quick Export (Recommended)

Export a single PDF with educational notes to SQL-Adapt format:

```bash
# Export with default settings (Kimi LLM)
python3 -m algl_pdf_helper export-edu \
    raw_pdf/murachs-mysql-3rd-edition.pdf \
    --output-dir ./output/murach-mysql \
    --llm-provider kimi

# Export with Ollama (local, free)
python3 -m algl_pdf_helper export-edu \
    raw_pdf/murachs-mysql-3rd-edition.pdf \
    --output-dir ./output/murach-mysql \
    --llm-provider ollama \
    --ollama-model qwen2.5:3b

# Export without LLM (fastest, rule-based only)
python3 -m algl_pdf_helper export-edu \
    raw_pdf/murachs-mysql-3rd-edition.pdf \
    --output-dir ./output/murach-mysql \
    --skip-llm
```

## Method 2: Generate Educational Notes Only

Generate just the educational notes without SQL-Adapt export:

```bash
# Generate with OpenAI
python3 -m algl_pdf_helper edu generate \
    raw_pdf/murachs-mysql-3rd-edition.pdf \
    --output-dir ./educational_output \
    --llm-provider openai

# Generate with Kimi
python3 -m algl_pdf_helper edu generate \
    raw_pdf/murachs-mysql-3rd-edition.pdf \
    --output-dir ./educational_output \
    --llm-provider kimi

# Estimate cost only (don't generate)
python3 -m algl_pdf_helper edu generate \
    raw_pdf/murachs-mysql-3rd-edition.pdf \
    --estimate-cost
```

## Method 3: Interactive Menu (start.sh)

```bash
./start.sh
```

Then select from the menu:
- **Option 4**: Process single PDF (with concepts)
- **Option 5**: Process single PDF (full)
- **Option 6**: Process all PDFs in directory

## Method 4: Batch Processing

Process all PDFs in the `raw_pdf/` directory:

```bash
# Using the interactive script
./start.sh
# Select option 6

# Or directly with Python
python3 -c "
from algl_pdf_helper.educational_pipeline import EducationalNoteGenerator
import os

gen = EducationalNoteGenerator(
    output_dir='./output/batch',
    llm_provider='ollama',
    ollama_model='qwen2.5:3b'
)

for pdf in os.listdir('raw_pdf'):
    if pdf.endswith('.pdf'):
        print(f'Processing {pdf}...')
        result = gen.process_pdf(f'raw_pdf/{pdf}')
        print(f'  Status: {result.get(\"status\")}')
"
```

## Output Structure

After processing, you'll have:

```
output/
└── {pdf-name}/
    ├── concept-manifest.json       # Concept mappings
    ├── educational/                # Educational notes
    │   ├── concepts/
    │   │   ├── select-basics.md
    │   │   ├── joins-intro.md
    │   │   └── ...
    │   └── README.md
    ├── sqladapt/                   # SQL-Adapt format
    │   ├── manifest.json
    │   ├── chunks.json
    │   └── index.json
    └── raw/                        # Extracted raw text
        └── pages/
```

## Cost Estimation

Check costs before processing:

```bash
python3 -m algl_pdf_helper edu cost

# Or estimate for specific PDF
python3 -m algl_pdf_helper edu generate \
    raw_pdf/murachs-mysql-3rd-edition.pdf \
    --estimate-cost
```

## Provider Comparison

| Provider | Speed | Cost | Quality | Setup |
|----------|-------|------|---------|-------|
| **Ollama** (local) | Medium | Free | Good | Requires local models |
| **Kimi** | Fast | ~$0.001/page | Excellent | Requires API key |
| **OpenAI** | Fast | ~$0.003/page | Excellent | Requires API key |

## Troubleshooting

### Check dependencies:
```bash
python3 -m algl_pdf_helper edu status
```

### Check extraction quality first:
```bash
python3 -m algl_pdf_helper check-quality raw_pdf/murachs-mysql-3rd-edition.pdf
```

### Common issues:

**"Ollama not available"**
```bash
# Start Ollama first
ollama serve

# Or pull a model
ollama pull qwen2.5:3b
```

**"Marker not installed"**
```bash
pip install marker-pdf
```

**Out of memory with large PDFs**
```bash
# Use PyMuPDF instead of Marker
python3 -m algl_pdf_helper export-edu ... --no-use-marker
```

## Quick Examples

### Example 1: Fast local processing
```bash
python3 -m algl_pdf_helper export-edu \
    raw_pdf/murachs-mysql-3rd-edition.pdf \
    --output-dir ./output/fast \
    --llm-provider ollama \
    --ollama-model qwen2.5:3b \
    --no-use-marker
```

### Example 2: High quality with Kimi
```bash
export KIMI_API_KEY="your-key"
python3 -m algl_pdf_helper export-edu \
    raw_pdf/dbms-ramakrishnan-3rd-edition.pdf \
    --output-dir ./output/high-quality \
    --llm-provider kimi
```

### Example 3: Re-process existing PDF
```bash
# Clean old output first
rm -rf output/murachs-mysql-3rd-edition

# Re-process
python3 -m algl_pdf_helper export-edu \
    raw_pdf/murachs-mysql-3rd-edition.pdf \
    --output-dir ./output/murachs-mysql-3rd-edition \
    --skip-llm
```
