# Educational Notes Generation Guide

## Overview

This solution provides **ready-to-learn notes** for students by:
1. Using **Marker** for high-quality PDF extraction (fixes OCR artifacts)
2. Using **LLM** (OpenAI) to transform raw text into educational content
3. Outputting **SQL-Adapt compatible format** with student-friendly structure

## Features

### ✅ Guaranteed Working Output
- No exceptions - handles all errors gracefully
- Fallback to PyMuPDF if Marker fails
- Fallback to basic notes if LLM unavailable
- Always produces valid SQL-Adapt format

### 📚 Educational Content Structure
Each concept includes:
- **Definition**: Clear, simple explanation
- **Explanation**: Detailed walkthrough with analogies
- **Key Points**: Essential takeaways
- **Examples**: Code/SQL examples with explanations
- **Common Mistakes**: What students get wrong
- **Practice Questions**: With solutions

### 🎯 SQL-Adapt Compatible

Output follows the **standard SQL-Adapt directory structure**:

```
output_dir/
├── concept-map.json               # MAIN INDEX: Maps concept IDs to metadata & chunks
├── concept-manifest.json          # Internal format (diagnostic)
├── chunks-metadata.json           # PDF chunk metadata
├── concepts/                      # Individual concept markdown files
│   ├── {textbook-name}/           # Subdirectory per textbook
│   │   ├── README.md              # Index of concepts for this textbook
│   │   ├── select-basics.md
│   │   ├── where-clause.md
│   │   └── ...
│   └── {another-textbook}/
│       └── ...
├── {doc_id}-extraction.json       # Raw extraction (diagnostic)
├── {doc_id}-educational-notes.json # Educational notes (diagnostic)
├── {doc_id}-sqladapt.json         # SQL-Adapt format (diagnostic)
└── {doc_id}-study-guide.md        # Combined study guide
```

**concept-map.json (Main Index File):**
```json
{
  "version": "1.0.0",
  "generatedAt": "2026-02-26T04:42:10.237197+00:00",
  "sourceDocIds": ["murachs-mysql-3rd-edition", "dbms-ramakrishnan-3rd-edition"],
  "concepts": {
    "{source}/{concept-id}": {
      "title": "Human-readable title",
      "definition": "One-line definition",
      "difficulty": "beginner|intermediate|advanced",
      "pageNumbers": [94, 95, 96],
      "chunkIds": {
        "definition": ["source:p94:c1", "source:p94:c2"],
        "explanation": ["source:p96:c1"],
        "examples": ["source:p102:c1"],
        "commonMistakes": ["source:p36:c1"]
      },
      "relatedConcepts": ["source/other-concept"],
      "practiceProblemIds": [],
      "sourceDocId": "source"
    }
  }
}
```

**Chunk ID Format:** `{sourceDocId}:p{page}:c{chunkNumber}`

**Concept Markdown Format (concepts/{source}/{id}.md):**
```markdown
# {Concept Title}

## Definition
{Clear, concise definition}

## Explanation
{Detailed explanation with context}

## Examples

### Example 1: {Title}
```sql
-- SQL code example
SELECT * FROM table;
```
{Explanation of example}

## Common Mistakes

### Mistake Title
**Incorrect:**
```sql
-- Wrong code
```

**Correct:**
```sql
-- Fixed code
```

**Why this happens:** {Explanation}
```

## Installation

### 1. Install Marker (for PDF extraction)
```bash
pip install marker-pdf
```

**First run**: Downloads ~3GB of models (automatic)

### 2. Or: Use Kimi (Moonshot AI) ⭐ RECOMMENDED
Kimi is **cheaper** than OpenAI and offers excellent Chinese/English bilingual support:

```bash
# Set API key (get from https://platform.moonshot.cn/)
export KIMI_API_KEY='sk-your-key-here'
```

**Available Models:**

| Model | Cost/1K tokens | Context | Best For |
|-------|----------------|---------|----------|
| `moonshot-v1-8k` | ¥0.012 | 8K | Cheap, fast, simple notes |
| `moonshot-v1-32k` | ¥0.024 | 32K | Medium-length content |
| `moonshot-v1-128k` | ¥0.12 | 128K | Long chapters |
| **`kimi-k2-5`** ⭐ | ¥0.05 | 256K | **Best for education!** |

**Why Kimi K2.5 for Education?**
- 🧠 **1T parameter MoE model** - Better reasoning for complex SQL concepts
- 📚 **256K context** - Process entire chapters at once
- 🌏 **Bilingual** - Perfect for Chinese/English textbooks
- 💰 **Affordable** - ~¥8-12 per PDF (vs ¥33 for OpenAI)

```bash
# Use K2.5 for best quality
export KIMI_MODEL=kimi-k2-5
```

### 3. Or: Install Ollama (for local LLM) 🦙
Instead of using API services (Kimi/OpenAI), you can run LLMs **locally** with Ollama:

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model (recommended for M1 Pro 16GB)
ollama pull llama3.2:3b     # Fast, ~4GB RAM
ollama pull qwen2.5:7b      # Chinese/English, ~8GB RAM
ollama pull mistral:7b      # Balanced, ~8GB RAM
ollama pull phi4            # Reasoning, ~10GB RAM

# Start Ollama server
ollama serve
```

**Benefits of Ollama:**
- ✅ **Free** - No API costs
- ✅ **Private** - Data stays on your machine
- ✅ **Offline** - Works without internet
- ✅ **Fast** - No network latency

**Recommended Models for M1 Pro 16GB:**

| Model | RAM | Speed | Best For |
|-------|-----|-------|----------|
| `llama3.2:3b` | 4GB | ⚡ Fast | Quick drafts, testing |
| `qwen2.5:7b` | 8GB | 🚀 Good | Chinese/English content |
| `mistral:7b` | 8GB | 🚀 Good | General purpose |
| `phi4` | 10GB | 🐢 Slower | Complex reasoning |
| `gemma2:9b` | 10GB | 🐢 Slower | High quality output |

### 4. Verify Installation
```bash
algl-pdf edu status
```

Output:
```
📋 Dependency Status
========================================
✅ Marker (PDF extraction): Available
✅ OpenAI (LLM enhancement): Available
✅ OPENAI_API_KEY: Set
```

## Usage

### Quick Start

```bash
# Generate educational notes from PDF
algl-pdf edu generate path/to/textbook.pdf

# Specify output directory
algl-pdf edu generate textbook.pdf --output-dir ./my-notes

# Without LLM (faster, basic notes)
algl-pdf edu generate textbook.pdf --no-use-llm
```

### Export to SQL-Adapt

```bash
# Direct export to SQL-Adapt with educational format
algl-pdf export-edu textbook.pdf --output-dir /path/to/sql-adapt
```

### Python API

```python
from algl_pdf_helper.educational_pipeline import EducationalNoteGenerator

# Initialize
generator = EducationalNoteGenerator(
    openai_api_key="your-key",  # Optional
    use_marker=True,             # Use best extraction
)

# Process PDF
result = generator.process_pdf(
    pdf_path=Path("textbook.pdf"),
    output_dir=Path("./output"),
)

# Check results
if result["success"]:
    print(f"Generated {result['stats']['concepts_generated']} concepts")
    print(f"Files: {result['outputs']}")
else:
    print(f"Errors: {result['errors']}")
```

## Output Files

For each PDF, generates:

| File | Description |
|------|-------------|
| `{doc-id}-extraction.json` | Raw extracted content |
| `{doc-id}-educational-notes.json` | LLM-enhanced notes |
| `{doc-id}-sqladapt.json` | SQL-Adapt compatible format |
| `{doc-id}-study-guide.md` | Human-readable study guide |

## Comparison: Before vs After

### ❌ Before (Raw Chunks)
```text
and functions How to create triggers and events Section 5 
Database administration Chapter 17 Chapter 18 Chapter 19 
An introduction to database administration How to secure a 
database How to backup and restore a database Appendixes
```

### ✅ After (Educational Notes)
```json
{
  "concept": "Database Administration",
  "definition": "The process of managing and maintaining database systems...",
  "explanation": "Think of a database administrator as a librarian...",
  "key_points": [
    "Security: Controlling who can access data",
    "Backups: Creating copies to prevent data loss",
    "Recovery: Restoring data after failures"
  ],
  "examples": [
    {
      "title": "Creating a backup",
      "code": "BACKUP DATABASE mydb TO DISK = 'backup.bak';",
      "explanation": "This command creates a full backup..."
    }
  ],
  "common_mistakes": [
    {
      "mistake": "Forgetting to test backup restoration",
      "correction": "Regularly test restoring from backups",
      "explanation": "A backup you can't restore is useless..."
    }
  ]
}
```

## How It Works

### Pipeline Architecture

```
PDF Input
    ↓
┌─────────────────┐
│  Marker Extract │ → Clean text, structure preserved
│  (or PyMuPDF)   │   Falls back if Marker fails
└─────────────────┘
    ↓
┌─────────────────┐
│ Structure by    │ → Map to concepts/topics
│ Concepts        │   Uses concepts.yaml if available
└─────────────────┘
    ↓
┌─────────────────┐
│ LLM Enhance     │ → Generate educational content
│ (or Basic)      │   Falls back if no API key
└─────────────────┘
    ↓
┌─────────────────┐
│ SQL-Adapt       │ → Final structured output
│ Format          │   Guaranteed valid format
└─────────────────┘
    ↓
Output Files
```

### Error Handling

Every step has fallbacks:

| Step | Primary | Fallback | Result |
|------|---------|----------|--------|
| PDF Extraction | Marker | PyMuPDF | Always get text |
| Content Structuring | concepts.yaml | Auto-detect | Always have topics |
| Note Generation | LLM (GPT-4) | Template-based | Always have notes |
| Format Output | Full structure | Minimal valid | Always valid JSON |

## Configuration

### Using concepts.yaml

Map PDF pages to educational concepts:

```yaml
concepts:
  select-basics:
    title: "SELECT Statement Basics"
    definition: "Retrieve data from database tables"
    difficulty: beginner
    estimatedReadTime: 15
    pages: [45, 46, 47]  # Pages in PDF
    sections:
      definition: [45]
      examples: [46, 47]
```

### Custom LLM Prompts

Modify `educational_pipeline.py` to customize:

```python
def _llm_enhance_concept(self, title, definition, raw_text):
    prompt = f"""
    YOUR CUSTOM PROMPT HERE
    
    TOPIC: {title}
    TEXT: {raw_text}
    
    Generate educational content...
    """
    # ...
```

### Extraction Method Auto-Detection

The system automatically chooses the best extraction method based on PDF content:

| PDF Type | Method Used | Speed | Quality |
|----------|-------------|-------|---------|
| **Text-based PDF** (embedded text) | PyMuPDF direct | ⚡ Fast (~5s) | Good |
| **Scanned PDF** (no text) | Marker OCR | 🐢 Slow (~5min) | Excellent |
| **Mixed PDF** (some scanned pages) | Marker auto-detect | 🐢 Slow | Excellent |
| **Large PDF** (>50MB) | Marker chunked | 🐢 Slow | Excellent |

**How it works:**
1. First extracts text with PyMuPDF
2. Checks quality (character count, readable ratio)
3. If good text found → uses it directly (fast!)
4. If poor/empty → tries Marker with OCR
5. If Marker fails → uses PyMuPDF fallback

### Memory Management (Prevent OOM)

For large PDFs (>50MB), the system automatically **splits and processes in chunks** to prevent out-of-memory errors while still using high-quality Marker extraction.

#### Auto-Split Feature
When a PDF exceeds `MARKER_MAX_SIZE_MB` (default: 50MB):
1. PDF is split into ~20MB chunks (max 50 pages each)
2. Each chunk processed with Marker
3. Results merged back together
4. Page numbers automatically adjusted

```bash
# Configure the size limit (default: 50MB)
export MARKER_MAX_SIZE_MB=50

# Or disable auto-split and use PyMuPDF fallback
export MARKER_MAX_SIZE_MB=9999  # Effectively disables splitting
```

#### Memory Control Variables
```bash
# Limit parallel workers (default: 1)
export SURYA_MAX_WORKERS=1
export MARKER_MAX_WORKERS=1

# Force CPU instead of MPS/GPU (saves memory)
export TORCH_DEVICE=cpu
```

## Performance

### Time Estimates

| Step | Time | Notes |
|------|------|-------|
| Marker Extraction | 30-60s first run | Downloads models |
| | 5-10s subsequent | Cached models |
| PyMuPDF Extraction | 1-2s | Fallback |
| LLM Enhancement | 2-5s per concept | Depends on concept size |
| Total (100-page PDF) | 3-5 minutes | With LLM |
| | 30 seconds | Without LLM |

### Cost Estimates (OpenAI)

- GPT-4o-mini: ~$0.005 per concept
- 30 concepts: ~$0.15 per PDF
- 100-page textbook: ~$0.50

## Troubleshooting

### "Marker not installed"
```bash
pip install marker-pdf
```

### "First run is slow"
Marker downloads ~3GB of models on first use. Subsequent runs are fast.

### "LLM not available"
Set your OpenAI API key:
```bash
export OPENAI_API_KEY='sk-...'
```

Or use `--no-use-llm` flag for basic notes.

### "Out of memory" / "Killed: 9"

The system now **auto-splits large PDFs** to prevent OOM errors. If you still get memory issues:

**Option 1: Reduce chunk size**
```bash
export MARKER_MAX_SIZE_MB=30  # Smaller chunks (~18MB each)
```

**Option 2: Use PyMuPDF fallback (no Marker)**
```bash
# Disable Marker entirely
algl-pdf export-edu your-textbook.pdf --no-use-marker
```

**Option 3: Manual PDF splitting**
```bash
# Use PDFtk to split manually
pdftk large-textbook.pdf cat 1-100 output part1.pdf
pdftk large-textbook.pdf cat 101-200 output part2.pdf
```

**Option 4: Process on a machine with more RAM**
```bash
# On a 32GB+ RAM machine, increase limits
export MARKER_MAX_SIZE_MB=200
export SURYA_MAX_WORKERS=2
```

## Example Output

See `examples/educational-output/` for sample outputs including:
- `extraction.json` - Raw extraction
- `educational-notes.json` - LLM-enhanced
- `sqladapt.json` - SQL-Adapt format
- `study-guide.md` - Human readable

## Next Steps

1. Install dependencies: `pip install marker-pdf openai`
2. Set API key: `export OPENAI_API_KEY='...'`
3. Test: `algl-pdf edu generate your-textbook.pdf`
4. Export: `algl-pdf export-edu your-textbook.pdf`
