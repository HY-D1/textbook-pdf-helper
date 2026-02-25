# ALGL PDF Helper - AI Agent Guide

## Project Overview

`algl-pdf-helper` is a Python CLI tool and optional HTTP service that processes PDFs (including scanned documents) and converts them into a structured `PdfIndexDocument` format compatible with the ALGL SQL-Adapt project's client-side retrieval system.

The pipeline performs:
1. **Automatic quality detection** - Checks if text extraction is readable
2. **Auto-OCR fallback** - Retries with OCR if quality is poor (scanned PDFs)
3. Per-page text extraction using PyMuPDF
4. Text cleaning and normalization
5. Word-window chunking (default: 180 words, 30-word overlap)
6. Lightweight 24-dimensional hash-based embeddings per chunk
7. Output of JSON artifacts (`manifest.json`, `chunks.json`, `index.json`)
8. Concept-based learning material generation from `concepts.yaml` config

## Technology Stack

- **Language**: Python 3.10+
- **Build System**: setuptools (configured in `pyproject.toml`)
- **Core Dependencies**:
  - `pydantic>=2.6` - Data validation and serialization
  - `typer>=0.12` - CLI framework
  - `pymupdf>=1.23` - PDF text extraction (PyMuPDF)
  - `pyyaml>=6.0` - YAML parsing for concept configuration
- **Optional Dependencies**:
  - `ocrmypdf>=16.0` - OCR capability (install with `pip install -e '.[ocr]'`)
  - `fastapi>=0.110`, `uvicorn[standard]>=0.27`, `python-multipart>=0.0.9` - HTTP server (install with `pip install -e '.[server]'`)
  - `pytest>=8.0` - Testing (install with `pip install -e '.[test]'`)
- **External System Dependencies** (for OCR):
  - `tesseract` - OCR engine
  - `ghostscript` - PDF processing
  - macOS install: `brew install tesseract ghostscript`

## Project Structure

```
.
├── pyproject.toml           # Package configuration and dependencies
├── README.md                # Human-readable documentation
├── LICENSE                  # MIT License
├── .gitignore              # Git ignore patterns
├── concepts.yaml.example   # Example concept configuration
├── src/
│   └── algl_pdf_helper/    # Main package
│       ├── __init__.py     # Package version
│       ├── models.py       # Pydantic data models (includes Concept models)
│       ├── cli.py          # CLI entry point (Typer)
│       ├── server.py       # FastAPI HTTP server
│       ├── extract.py      # PDF extraction and OCR logic
│       ├── clean.py        # Text normalization and header/footer stripping
│       ├── chunker.py      # Word-window chunking algorithm
│       ├── embedding.py    # Hash-based embedding generation
│       ├── indexer.py      # Main indexing orchestrator
│       ├── concept_mapper.py    # NEW: Maps chunks to concepts from YAML config
│       └── markdown_generator.py # NEW: Generates readable markdown per concept
└── tests/
    ├── conftest.py         # pytest configuration (adds src to path)
    ├── test_chunker.py     # Tests for chunking logic
    ├── test_embedding_parity.py  # Tests for embedding determinism
    ├── test_concept_mapper.py    # Tests for concept mapping
    ├── test_markdown_generator.py # Tests for markdown generation
    └── test_quality_check.py      # Tests for text quality detection
```

## Code Organization

### Module Responsibilities

| Module | Purpose |
|--------|---------|
| `models.py` | Pydantic models: `PdfSourceDoc`, `PdfIndexChunk`, `PdfIndexDocument`, `PdfIndexManifest`, `IndexBuildOptions`, `ConceptInfo`, `ConceptManifest`, `ConceptSection` |
| `extract.py` | PDF text extraction via PyMuPDF, SHA256 hashing, OCR handling via ocrmypdf, quality detection, temp file cleanup |
| `clean.py` | Text normalization (whitespace, null bytes), heuristic header/footer removal |
| `chunker.py` | Sliding word-window chunker with configurable overlap; chunk IDs: `{docId}:p{page}:c{chunkIndex}` |
| `embedding.py` | Tokenization, hash-based vectorization, L2 normalization; produces deterministic embeddings |
| `indexer.py` | Main orchestrator: discovers PDFs, coordinates pipeline, generates unique index ID, writes JSON outputs, triggers concept generation |
| `concept_mapper.py` | Reads `concepts.yaml`, maps page ranges to chunk IDs, builds `ConceptManifest` |
| `markdown_generator.py` | Generates readable `.md` files per concept from chunks, creates concept library README |
| `cli.py` | Typer CLI with `index` and `serve` commands |
| `server.py` | FastAPI server with `POST /v1/index` endpoint for PDF upload |

### Key Data Flow

```
Input PDF(s)
    ↓
extract.py: PyMuPDF text extraction
    ↓
Quality Check: Is text readable?
    ├─ NO → Auto-OCR retry
    └─ YES → Continue
    ↓
clean.py: normalize text → strip headers/footers
    ↓
chunker.py: word-window chunking
    ↓
embedding.py: hash embedding per chunk
    ↓
indexer.py: assemble → write manifest.json, chunks.json, index.json
    ↓
(concepts.yaml exists?)
    ↓ YES
concept_mapper.py: map chunks to concepts
    ↓
markdown_generator.py: write concept-manifest.json + concepts/*.md
```

## Build and Development Commands

### Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with all optional dependencies
pip install -e '.[server,ocr,test]'
```

### CLI Usage

```bash
# Build index from single PDF
algl-pdf index ./my.pdf --out ./out/pdf-index

# Force OCR (recommended for scanned PDFs)
algl-pdf index ./scan.pdf --out ./out/pdf-index --ocr

# Process directory of PDFs
algl-pdf index ./pdfs --out ./out/pdf-index

# Use stable doc aliases instead of SHA-based IDs
algl-pdf index ./my.pdf --out ./out/pdf-index --use-aliases

# Specify concept config explicitly
algl-pdf index ./my.pdf --out ./out/pdf-index --concepts-config ./my-concepts.yaml

# Check extraction quality without processing
algl-pdf check-quality ./my.pdf
```

### Server Usage

```bash
# Start HTTP server
algl-pdf serve --host 127.0.0.1 --port 7345

# Endpoint: POST /v1/index (multipart form with pdf file)
# Returns: { document, manifest, chunks }
```

### Testing

```bash
# Run all tests
pytest

# pytest configuration is in pyproject.toml:
# - Quiet mode (-q)
# - Test directory: tests/
```

## Code Style Guidelines

- Use `from __future__ import annotations` in all modules for forward references
- Type hints are required for function signatures
- Pydantic v2 models for all data structures
- Docstrings for public functions (Google style not strictly enforced but preferred)
- Error handling: use specific exceptions with descriptive messages
- Temp file cleanup in `finally` blocks to ensure resources are freed

## Testing Strategy

- **Framework**: pytest
- **Test Location**: `tests/` directory
- **Configuration**: `pyproject.toml` (quiet mode, testpaths = ["tests"])
- **Path Setup**: `conftest.py` adds `src/` to `sys.path` for imports
- **Current Tests**:
  - `test_chunker.py`: Verifies chunk ID format and word overlap between chunks
  - `test_embedding_parity.py`: Verifies deterministic embedding output matches reference vector
  - `test_concept_mapper.py`: Tests concept config loading, manifest building, chunk mapping
  - `test_markdown_generator.py`: Tests markdown generation, page links, README generation
  - `test_quality_check.py`: Tests text quality detection, gibberish pattern detection
- **Import Pattern**: `from algl_pdf_helper.module import function`

## Output Format Specification

### Schema Version
- `pdf-index-schema-v2`
- `chunkerVersion`: `word-window-180-overlap-30-v1`
- `embeddingModelId`: `hash-embedding-v1`

### Doc ID Formats
- Upload mode (default): `doc-<sha256[:12]>`
- Disk mode (with `--use-aliases`): stable aliases like `sql-textbook`

### Generated Files

#### Core Index Files
- `manifest.json` - Index metadata without chunks
- `chunks.json` - Array of chunks with embeddings
- `index.json` - Full `PdfIndexDocument` including all chunks

#### Concept Learning Files (NEW)
- `concept-manifest.json` - Concept metadata with chunk mappings
- `concepts/*.md` - Individual concept content files
- `concepts/README.md` - Index of all concepts

### Concept Manifest Schema

```json
{
  "schemaVersion": "concept-manifest-v1",
  "sourceDocId": "sql-textbook",
  "createdAt": "2024-01-01T00:00:00Z",
  "conceptCount": 5,
  "concepts": {
    "select-basic": {
      "id": "select-basic",
      "title": "SELECT Statement Basics",
      "definition": "Retrieves data from one or more tables",
      "difficulty": "beginner",
      "estimatedReadTime": 5,
      "pageReferences": [45, 46],
      "sections": {
        "definition": {
          "chunkIds": ["sql-textbook:p45:c1"],
          "pageNumbers": [45]
        },
        "examples": {
          "chunkIds": ["sql-textbook:p45:c2", "sql-textbook:p46:c1"],
          "pageNumbers": [45, 46]
        }
      },
      "relatedConcepts": ["where-clause"],
      "tags": ["sql", "query"]
    }
  }
}
```

## Concepts Configuration (`concepts.yaml`)

The `concepts.yaml` file defines how PDF pages map to learning concepts:

```yaml
concepts:
  select-basic:
    title: "SELECT Statement Basics"
    definition: "Retrieves data from one or more tables"
    difficulty: beginner  # beginner, intermediate, advanced
    estimatedReadTime: 5  # minutes
    sections:
      definition: [45]        # Page 45 contains definition
      examples: [45, 46]      # Pages 45-46 have examples
      commonMistakes: [47]    # Page 47 discusses mistakes
    relatedConcepts: [where-clause, order-by]
    tags: [sql, query, dql]

  where-clause:
    title: "WHERE Clause"
    definition: "Filters rows based on conditions"
    difficulty: beginner
    sections:
      definition: [50]
      examples: [50, 51]
```

**Auto-discovery**: The indexer automatically looks for `concepts.yaml` in:
1. Same directory as input PDF file
2. Input directory (if input is a directory)
3. Parent of input directory
4. Current working directory

## Security Considerations

- Temp files are created with `tempfile.mkdtemp()` with prefix `algl_pdf_`
- Cleanup only removes files in directories matching the `algl_pdf_*` pattern
- File uploads in server mode are written to temp directories and cleaned up in `finally` blocks
- No persistent storage of uploaded PDFs
- OCR processing uses safe defaults: deskew and rotate pages enabled

## Development Notes

- The embedding algorithm is deterministic and must remain backward-compatible (see `test_embedding_parity.py`)
- Chunk overlap must be smaller than chunk size (validated in `IndexBuildOptions.validate_pair()`)
- OCR is automatically triggered when extracted text is less than 800 characters (`min_total_chars`)
- Default aliases map `SQL_Course_Textbook.pdf` → `sql-textbook`
- Concept generation is optional and gracefully degrades if config is missing or invalid
