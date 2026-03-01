# PDF to Learnable Notes - Improvement Plan

## Current Problems

1. **OCR Artifacts**: Text has garbled characters (`con1ponents`, `syste111`)
2. **No Structure**: Table of contents mixed with actual content
3. **No Pedagogical Value**: Raw text chunks aren't educational
4. **Missing Context**: Explanations separated from examples

## Recommended Solution: Marker + LLM Pipeline

### Step 1: Better PDF Extraction (Marker)

**Marker** (`marker-pdf`) is a state-of-the-art PDF converter that:
- Converts PDF to structured Markdown/JSON
- Preserves document structure (sections, headers, lists)
- Handles tables, equations, code blocks
- Removes headers/footers automatically
- Supports LLM-enhanced extraction

**Installation:**
```bash
pip install marker-pdf
```

**Basic Usage:**
```bash
# Convert to markdown with structure
marker_single input.pdf --output_dir ./output --output_format markdown

# Get structured JSON with blocks
marker_single input.pdf --output_dir ./output --output_format json

# Use LLM for highest accuracy
marker_single input.pdf --output_dir ./output --use_llm
```

### Step 2: Generate Educational Notes (LLM)

Use an LLM to transform extracted text into pedagogical content:

```python
# Pseudo-code for educational note generation

def generate_educational_notes(section_text, concept_name):
    prompt = f"""
    Transform this textbook section into structured learning material.
    
    CONCEPT: {concept_name}
    
    TEXT:
    {section_text}
    
    OUTPUT FORMAT (JSON):
    {{
      "concept": "Concept name",
      "definition": "Clear 1-2 sentence definition",
      "explanation": "Detailed explanation in simple terms",
      "key_points": ["Point 1", "Point 2", "Point 3"],
      "examples": [
        {{
          "title": "Example title",
          "code": "SQL/code example",
          "explanation": "Step-by-step walkthrough"
        }}
      ],
      "common_mistakes": [
        {{
          "mistake": "What students do wrong",
          "correction": "How to fix it",
          "explanation": "Why it's wrong"
        }}
      ],
      "practice_questions": [
        {{
          "question": "Practice question",
          "hint": "Optional hint",
          "solution": "Detailed solution"
        }}
      ],
      "related_concepts": ["concept1", "concept2"]
    }}
    
    Rules:
    - Make content self-contained (student can learn without textbook)
    - Include concrete SQL examples for database concepts
    - Anticipate student confusion points
    - Write in a conversational, encouraging tone
    """
    
    return llm_generate(prompt)
```

### Step 3: New Output Format

```json
{
  "schemaVersion": "educational-notes-v1",
  "concept": "SELECT Statement",
  "source": {
    "pdf": "murachs-mysql-3rd-edition",
    "pages": [45, 46, 47],
    "section": "Chapter 3: How to retrieve data"
  },
  "difficulty": "beginner",
  "estimatedTime": 15,
  "learningObjectives": [
    "Retrieve all columns from a table",
    "Retrieve specific columns",
    "Use column aliases"
  ],
  "content": {
    "definition": "The SELECT statement retrieves data from database tables...",
    "explanation": "Detailed explanation with analogies...",
    "keyPoints": ["Point 1", "Point 2"],
    "examples": [...],
    "commonMistakes": [...],
    "practiceQuestions": [...]
  },
  "prerequisites": ["database-basics"],
  "nextConcepts": ["where-clause", "order-by"]
}
```

## Implementation Options

### Option A: Integrate Marker into Current Pipeline

Replace PyMuPDF extraction with Marker in `extract.py`:

```python
# New extract_with_marker.py
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict

def extract_text_with_marker(pdf_path):
    converter = PdfConverter(artifact_dict=create_model_dict())
    rendered = converter(str(pdf_path))
    
    # Returns structured content with sections
    return rendered.markdown, rendered.metadata
```

**Pros:**
- Best text extraction quality
- Preserves document structure
- Handles complex layouts

**Cons:**
- Requires GPU for best performance (CPU works but slower)
- Adds ~3GB of model dependencies
- First run downloads models

### Option B: Post-Process Current Chunks with LLM

Keep current extraction but use LLM to clean and structure:

```python
# clean_chunks_with_llm.py
def clean_chunk(chunk_text):
    prompt = """
    Clean and structure this extracted textbook text.
    
    Input: Raw OCR text with artifacts
    Output: Clean, readable educational text
    
    Fix:
    - OCR errors (con1ponents → components)
    - Formatting issues
    - Remove page numbers/headers
    - Preserve code examples
    """
    return llm_clean(prompt, chunk_text)
```

**Pros:**
- Works with current pipeline
- No new dependencies
- Can fix existing outputs

**Cons:**
- Still limited by poor input quality
- LLM costs for cleaning
- Doesn't solve structure problem

### Option C: Hybrid Approach (Recommended)

1. Use Marker for initial extraction (best quality)
2. Use LLM to generate educational notes (pedagogical value)
3. Store both raw and generated content

```
Pipeline:
PDF → Marker → Structured Markdown → LLM → Educational Notes → Output
```

## Quick Start: Test Marker

```bash
# Install
pip install marker-pdf

# Test on first 5 pages
marker_single murachs-mysql-3rd-edition.pdf \
  --page_range "0-5" \
  --output_dir ./test_marker \
  --output_format markdown

# View result
cat ./test_marker/murachs-mysql-3rd-edition.md
```

## Next Steps

1. **Evaluate Marker**: Test on sample pages from both PDFs
2. **Compare Quality**: Side-by-side with current PyMuPDF output
3. **Design Note Format**: Define educational content schema
4. **Implement LLM Pipeline**: Generate learnable notes
5. **Update Export**: Modify SQL-Adapt export for new format

## Resources

- **Marker GitHub**: https://github.com/datalab-to/marker
- **PaddleOCR**: https://github.com/PaddlePaddle/PaddleOCR (alternative)
- **AI-University Paper**: Shows complete educational pipeline using LLMs
