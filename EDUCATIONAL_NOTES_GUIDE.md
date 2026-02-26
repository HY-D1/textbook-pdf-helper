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
Output format matches SQL-Adapt expectations:
```json
{
  "schemaVersion": "educational-concept-v1",
  "sourceDocId": "pdf-name",
  "concepts": {
    "concept-id": {
      "id": "...",
      "title": "...",
      "definition": "...",
      "difficulty": "beginner|intermediate|advanced",
      "estimatedReadTime": 15,
      "pageReferences": [45, 46],
      "sections": {
        "definition": { "text": "...", "chunkIds": [...] },
        "explanation": { "text": "...", "chunkIds": [...] },
        "examples": { "items": [...] },
        "commonMistakes": { "items": [...] },
        "practice": { "questions": [...] }
      }
    }
  }
}
```

## Installation

### 1. Install Marker (for PDF extraction)
```bash
pip install marker-pdf
```

**First run**: Downloads ~3GB of models (automatic)

### 2. Install OpenAI (for LLM enhancement)
```bash
pip install openai
```

Set your API key:
```bash
export OPENAI_API_KEY='sk-your-key-here'
```

### 3. Verify Installation
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

### "Out of memory"
Marker uses ~5GB VRAM with GPU, or ~8GB RAM with CPU. For large PDFs:
```python
# Process in chunks
generator.process_pdf(pdf_path, chunk_size=50)  # pages at a time
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
