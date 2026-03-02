# ALGL PDF Helper - System Architecture

**Version:** 1.0.0  
**Last Updated:** 2026-03-01  
**Status:** Current

---

## Table of Contents

1. [Overview](#overview)
2. [High-Level Flow](#high-level-flow)
3. [Pipeline Phases](#pipeline-phases)
4. [Data Flow](#data-flow)
5. [Component Reference](#component-reference)
6. [Quality Metrics](#quality-metrics)
7. [Output Generation](#output-generation)

---

## Overview

The ALGL PDF Helper uses a multi-phase pipeline to transform raw PDFs into structured educational content compatible with the SQL-Adapt learning platform.

### Pipeline Phases

| Phase | Name | Input | Output | Key Components |
|-------|------|-------|--------|----------------|
| 1 | PDF Extraction & OCR | Raw PDF | Clean text pages | PyMuPDF, OCRmyPDF, TextCleaner |
| 2 | Chunking & Embedding | Clean pages | Text chunks with embeddings | Chunker, Embedding |
| 3 | Concept Mapping | Chunks | Structured concepts | Concept Mapper, Content Validator |
| 4 | Content Generation | Validated concepts | Educational notes | LLM Integration, SQL Validator |
| 5 | Export & Integration | Educational notes | SQL-Adapt format | Markdown Generator, Exporter |

---

## High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PDF PROCESSING PIPELINE                              │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
    │  RAW PDF     │────▶│  PHASE 1     │────▶│  PHASE 2     │
    │  Textbooks   │     │  PDF Extract │     │  Knowledge   │
    │              │     │  & Clean     │     │  Extract     │
    └──────────────┘     └──────────────┘     └──────┬───────┘
                                                      │
    ┌──────────────┐     ┌──────────────┐            │
    │  ADAPTIVE    │◀────│  PHASE 3     │◀───────────┘
    │  OUTPUT      │     │  LLM Enhance │
    │  (SQL-Adapt) │     │  & Validate  │
    └──────────────┘     └──────────────┘
```

---

## Pipeline Phases

### Phase 1: PDF Extraction & OCR

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           PHASE 1: PDF EXTRACTION                           │
│                      Input: Raw PDF → Output: Clean Text                    │
└────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────┐
    │   Raw PDF File  │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────────────────────────────────────────┐
    │  STEP 1: Quality Check                              │
    │  ├─ PyMuPDF extracts embedded text                  │
    │  ├─ Check character count (>800 = good)             │
    │  └─ Detect if OCR needed (scanned PDF)              │
    └────────┬────────────────────────────────────────────┘
             │
    ┌────────┴────────────────────────────────────────────┐
    │  Quality Result                                     │
    │  ├─ ✅ GOOD (2.4M chars) → Use PyMuPDF directly     │
    │  └─ ❌ POOR → Try OCR                               │
    └────────┬────────────────────────────────────────────┘
             │
             ▼
    ┌─────────────────────────────────────────────────────┐
    │  STEP 2: Text Cleaning (TextCleaner class)          │
    │  ├─ Fix OCR errors ("Arz" → "An")                   │
    │  ├─ Remove headers ("160 Section 1...")             │
    │  ├─ Remove footers (page numbers)                   │
    │  ├─ Fix 2-column layout (remove duplicates)         │
    │  └─ Clean SQL blocks (remove narrative text)        │
    └────────┬────────────────────────────────────────────┘
             │
             ▼
    ┌─────────────────────────────────────────────────────┐
    │  OUTPUT: Clean Page Objects                         │
    │  [{                                                  │
    │    "page_number": 45,                               │
    │    "text": "SELECT * FROM users...",               │
    │    "sections": [...]                                │
    │  }]                                                 │
    └─────────────────────────────────────────────────────┘
```

**Key Components:**
- `extract.py`: PyMuPDF extraction, quality detection, OCR handling
- `clean.py`: Text normalization, header/footer removal
- **Output**: Array of page objects with clean text

**CLI Commands:**
```bash
# Check extraction quality
algl-pdf check-quality ./my.pdf

# Run preflight analysis
algl-pdf preflight ./my.pdf

# Extract text with strategy
algl-pdf extract ./my.pdf --strategy direct
```

---

### Phase 2: Chunking & Embedding

```
┌────────────────────────────────────────────────────────────────────────────┐
│              PHASE 2: PROCESSING & CHUNKING                      │
└────────────────────────────────────────────────────────────────────────────┘

Raw Text (from Phase 1)
      │
      ▼
┌──────────────────────────┐
│  Text Normalization      │
│  • Fix encoding issues   │
│  • Standardize whitespace│
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Word Window Chunking    │
│  (chunker.py)            │
│  • 180 words per chunk   │
│  • 30 word overlap       │
│  • Preserve page info    │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Hash Embedding          │
│  (embedding.py)          │
│  • 24-dim vectors        │
│  • Local, deterministic  │
│  • No external API       │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Chunk Objects           │
│  {                       │
│    chunkId: "doc:p1:c1"  │
│    page: 1,              │
│    text: "...",          │
│    embedding: [0.1, ...] │
│  }                       │
└──────────────────────────┘
```

**Key Components:**
- `chunker.py`: Word window chunking (default: 180 words, 30 overlap)
- `embedding.py`: Hash-based 24-dimensional embeddings
- **Output**: Chunks with unique IDs following pattern `{docId}:p{page}:c{index}`

**Chunk ID Format:**
- Pattern: `{docId}:p{page}:c{index}`
- Example: `sql-textbook:p45:c1` (Document "sql-textbook", page 45, chunk 1)

---

### Phase 3: Concept Mapping

```
┌────────────────────────────────────────────────────────────────────────────┐
│       PHASE 3: CONCEPT MAPPING & VALIDATION                      │
└────────────────────────────────────────────────────────────────────────────┘

Chunks (from Phase 2)
      │
      ▼
┌──────────────────────────────────────────────────────────┐
│              CONCEPT MAPPING SYSTEM                       │
│  (concept_mapper.py)                                     │
│  Multi-layer approach:                                   │
└──────────────────────────────────────────────────────────┘
      │
      ├── Layer 1: Manual Mapping (concepts.yaml)
      │   • Define concepts and page ranges
      │   • Human-curated mappings
      │
      ├── Layer 2: Semantic Matching
      │   • Match chunks to concepts
      │   • Content validation
      │
      └── Layer 3: AI-Assisted (Kimi/Ollama)
          • Extract relevant passages
          • Validate relevance
          ▼
┌──────────────────────────┐
│  Content Validation      │
│  (ContentValidator)      │
│  • SQL keyword detection │
│  • Non-SQL filtering     │
│  • Relevance scoring     │
└──────────┬───────────────┘
           │
           ▼
     [CONCEPT OBJECTS]
           │
           ▼
    ┌──────────────────┐
    │ concept-manifest │
    │ .json            │
    └──────────────────┘
```

**Content Validation Algorithm:**
```
Score = (SQL_keywords × 0.3) + (concept_match × 0.5) - (non_SQL_penalty × 0.2)

Filter out:
- JDBC/Java content
- HTTP protocol docs
- Chapter introductions
```

**Key Components:**
- `concept_mapper.py`: Maps chunks to concepts from YAML config
- `concepts.yaml`: Concept definitions with page ranges
- **Output**: Validated concept objects with relevance scores

---

### Phase 4: Content Generation

```
┌────────────────────────────────────────────────────────────────────────────┐
│           PHASE 4: PEDAGOGICAL CONTENT GENERATION                │
└────────────────────────────────────────────────────────────────────────────┘

Concept Objects (from Phase 3)
      │
      ▼
┌──────────────────────────┐
│  Schema Alignment        │
│  (EducationalNoteGenerator)
│                          │
│  Textbook → Practice     │
│  ┌────────────────────┐  │
│  │ Sailors  → users   │  │
│  │ Boats    → products│  │
│  │ Reserves → orders  │  │
│  │ Staff    → employees│ │
│  └────────────────────┘  │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  LLM Content Generation  │
│  • Definition            │
│  • Detailed explanation  │
│  • 2-3 SQL examples      │
│  • Common mistakes       │
│  • Practice questions    │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  SQL Validation          │
│  (SQLValidator)          │
│                          │
│  Checks:                 │
│  • has_SELECT            │
│  • has_FROM              │
│  • has_semicolon         │
│                          │
│  Auto-fixes:             │
│  • Add missing clauses   │
│  • Capitalize keywords   │
└──────────┬───────────────┘
           │
           ▼
     [EDUCATIONAL NOTES]
```

**Key Components:**
- `educational_pipeline.py`: Orchestrates content generation
- `SQLValidator`: Syntax checking and auto-fix
- **Output**: Validated educational notes with SQL examples

**LLM Integration:**
```bash
# Generate with Kimi (recommended)
algl-pdf export-edu ./book.pdf --llm-provider kimi

# Generate with Ollama (local)
algl-pdf export-edu ./book.pdf --llm-provider ollama --ollama-model qwen2.5:7b

# Skip LLM for faster processing
algl-pdf export-edu ./book.pdf --skip-llm
```

---

### Phase 5: Export & Integration

```
┌────────────────────────────────────────────────────────────────────────────┐
│                  PHASE 5: OUTPUT GENERATION                      │
└────────────────────────────────────────────────────────────────────────────┘

Educational Notes (from Phase 4)
      │
      ├──▶┌──────────────────────────┐
      │   │  Markdown Generator      │
      │   │  (markdown_generator.py) │
      │   │  • Format as .md         │
      │   │  • Add syntax highlighting│
      │   └──────────┬───────────────┘
      │              │
      │              ▼
      │        concepts/{doc_id}/*.md
      │
      ├──▶┌──────────────────────────┐
      │   │  Index Files             │
      │   │  (export_sqladapt.py)    │
      │   └──────────┬───────────────┘
      │              │
      │              ▼
      │    concept-map.json
      │
      └──▶┌──────────────────────────┐
          │  SQL-Adapt Export        │
          └──────────┬───────────────┘
                     │
                     ▼
              ┌──────────────┐
              │ SQL-Adapt    │
              │ Web App      │
              └──────────────┘
```

**Generated Files:**

```
textbook-static/
├── textbook-manifest.json       # Main manifest (metadata, versions)
├── concept-map.json             # Web app concept index
├── chunks.json                  # All chunks with embeddings
├── concept-manifest.json        # Internal concept metadata
├── assets/
│   ├── asset-manifest.json
│   ├── images/{docId}/          # Extracted images
│   └── tables/{docId}/          # Extracted tables
└── concepts/
    ├── README.md                # Auto-generated concept index
    └── {docId}/
        ├── {concept-id}.md      # Individual concept content
        └── README.md            # Doc-specific concept index
```

**Key Components:**
- `markdown_generator.py`: Markdown file generation
- `export_sqladapt.py`: SQL-Adapt compatible export
- **Output**: SQL-Adapt ready files

**Export Commands:**
```bash
# Export processed PDF to SQL-Adapt
algl-pdf export ./read_use/sql-textbook

# Full educational export with LLM
algl-pdf export-edu ./book.pdf --output-dir ./output --llm-provider kimi
```

---

## Data Flow

### Complete Pipeline Flow

```
RAW PDF
  │
  │  ┌────────────────────────────────────────────────────────────────────┐
  ├──┤ PDF PROCESSING (Phase 1)                                          │
  │  │ ├─ PyMuPDF extraction                                             │
  │  │ ├─ OCR error correction (TextCleaner)                             │
  │  │ ├─ Header/footer removal                                          │
  │  │ └─ 2-column layout fix                                            │
  │  └────────────────────────────────────────────────────────────────────┘
  │                                    │
  │                                    ▼
  │                          Clean Page Objects
  │                                    │
  │  ┌────────────────────────────────────────────────────────────────────┐
  ├──┤ CHUNKING & EMBEDDING (Phase 2)                                    │
  │  │ ├─ Word window chunking (180 words, 30 overlap)                   │
  │  │ └─ Hash embedding (24-dim)                                        │
  │  └────────────────────────────────────────────────────────────────────┘
  │                                    │
  │                                    ▼
  │                          Text Chunks with Embeddings
  │                                    │
  │  ┌────────────────────────────────────────────────────────────────────┐
  ├──┤ CONCEPT MAPPING (Phase 3)                                         │
  │  │ ├─ Load concepts.yaml                                             │
  │  │ ├─ Map pages to concepts                                          │
  │  │ ├─ Content validation (relevance scoring)                         │
  │  │ └─ Filter non-SQL content                                         │
  │  └────────────────────────────────────────────────────────────────────┘
  │                                    │
  │                                    ▼
  │                          Validated Concepts
  │                                    │
  │  ┌────────────────────────────────────────────────────────────────────┐
  ├──┤ CONTENT GENERATION (Phase 4)                                      │
  │  │ ├─ Schema alignment                                               │
  │  │ ├─ LLM enhancement (Kimi/Ollama)                                  │
  │  │ └─ SQL validation                                                 │
  │  └────────────────────────────────────────────────────────────────────┘
  │                                    │
  │                                    ▼
  │                          Educational Notes
  │                                    │
  │  ┌────────────────────────────────────────────────────────────────────┐
  └──┤ EXPORT & INTEGRATION (Phase 5)                                    │
     │ ├─ Create .md files for each concept                               │
     │ ├─ Generate concept-map.json (index)                               │
     │ └─ Export to SQL-Adapt format                                      │
     └────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
                          ┌───────────────────────────────┐
                          │   SQL-ADAPT OUTPUT            │
                          │   (Ready for Web App)         │
                          └───────────────────────────────┘
```

---

## Component Reference

### Core Modules

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `extract.py` | PDF text extraction | `extract_pages_fitz()`, `check_extraction_quality()` |
| `clean.py` | Text normalization | Header/footer removal, whitespace normalization |
| `chunker.py` | Word-window chunking | `chunk_text()`, overlap management |
| `embedding.py` | Hash embeddings | `build_hash_embedding()`, L2 normalization |
| `concept_mapper.py` | Concept mapping | `load_concepts_config()`, map chunks to concepts |
| `markdown_generator.py` | Markdown output | Generate concept files, README |
| `export_sqladapt.py` | SQL-Adapt export | Merge and export to web app format |

### Data Models

| Model | Location | Purpose |
|-------|----------|---------|
| `PdfSourceDoc` | `models.py` | Source document metadata |
| `PdfIndexChunk` | `models.py` | Individual text chunk |
| `PdfIndexDocument` | `models.py` | Complete index with all chunks |
| `PdfIndexManifest` | `models.py` | Index metadata without chunks |
| `ConceptManifest` | `models.py` | Concept mappings and metadata |
| `IndexBuildOptions` | `models.py` | Build configuration |

### Configuration Files

| File | Purpose |
|------|---------|
| `concepts.yaml` | Concept-to-page mappings |
| `pyproject.toml` | Package configuration |

---

## Quality Metrics

### By Phase

| Phase | Quality Metric | Target |
|-------|----------------|--------|
| Phase 1 | OCR accuracy | >95% |
| Phase 2 | Embedding consistency | Deterministic |
| Phase 3 | Relevance score | >0.7 |
| Phase 4 | SQL validity | 100% |
| Phase 5 | File structure validity | Valid JSON |

### Evaluation Commands

```bash
# Evaluate processing quality
algl-pdf evaluate ./output --threshold 0.75

# Detect regressions
algl-pdf detect-regressions ./baseline ./current

# Run CI tests
make test-ci
```

### Quality Checkpoints

```
Checkpoint 1: After Phase 1 (PDF Extraction)
├─ ✓ Text extracted successfully
├─ ✓ OCR errors corrected
├─ ✓ Headers/footers removed
└─ ❌ Check: No garbled text, no page numbers

Checkpoint 2: After Phase 2 (Chunking)
├─ ✓ Chunks generated
├─ ✓ Embeddings computed
└─ ❌ Check: Chunk IDs follow format

Checkpoint 3: After Phase 3 (Concept Mapping)
├─ ✓ Concepts mapped correctly
├─ ✓ Relevance score > 0.3
└─ ❌ Check: No JDBC content in SQL concepts

Checkpoint 4: After Phase 4 (Content Generation)
├─ ✓ Definition exists and is clear
├─ ✓ Examples include valid SQL
└─ ❌ Check: SQL syntax validated

Checkpoint 5: Final Output
├─ ✓ All .md files generated
├─ ✓ concept-map.json valid
└─ ❌ Check: Files load in web app
```

---

## Output Generation

### File Structure

```
textbook-static/
├── textbook-manifest.json       # Schema: textbook-static-v1
├── concept-map.json             # Web app consumable index
├── chunks.json                  # All chunks with embeddings
├── concept-manifest.json        # Internal metadata
└── concepts/
    ├── README.md                # Auto-generated index
    └── {docId}/
        ├── README.md            # Doc-specific index
        └── {concept-id}.md      # Individual concept files
```

### Schema Versions

| Schema | Version | Status |
|--------|---------|--------|
| `textbook-static-v1` | 1.0.0 | Stable |
| `concept-manifest-v1` | 1.0.0 | Stable |

### Integration with SQL-Adapt

```
algl-pdf-helper/output/                    SQL-Adapt/
    │                                            │
    ▼                                            ▼
┌──────────────────┐                    ┌──────────────────────────┐
│ concept-map.json │ ─────────────────▶ │ apps/web/public/         │
│                  │    Copied via      │   textbook-static/       │
│                  │    export script   │   concept-map.json       │
└──────────────────┘                    └──────────────────────────┘
                                              │
┌──────────────────┐                          ▼
│ concepts/*.md    │ ─────────────────▶ ┌──────────────────────────┐
│                  │                    │ textbook-static/         │
│                  │                    │   concepts/*.md          │
└──────────────────┘                    └──────────────────────────┘
                                               │
                                               ▼
                                        ┌──────────────────────────┐
                                        │  Web App Integration     │
                                        │  • RAG retrieval         │
                                        │  • Concept browsing      │
                                        │  • Learning interface    │
                                        └──────────────────────────┘
```

---

## Performance Characteristics

| Stage | Time per Concept | Bottleneck |
|-------|------------------|------------|
| PDF Extraction | ~0.1s | I/O (disk read) |
| Text Cleaning | ~0.05s | Regex processing |
| Content Validation | ~0.01s | In-memory calculation |
| LLM Enhancement | ~60-120s | LLM inference |
| SQL Validation | ~0.01s | Regex parsing |
| File Generation | ~0.01s | Disk write |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2024 | Basic PDF → chunks pipeline |
| v2.0 | 2025 | Educational pipeline with Ollama |
| v3.0 | Feb 2026 | LLM integration with Kimi |
| v3.1 | Mar 2026 | Documentation consolidation |

---

*This document consolidates content from previous architecture documentation.*
