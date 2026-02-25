# algl-pdf-helper

Helper project for **ALGL SQL-Adapt** that turns PDFs (including scanned PDFs) into a
`PdfIndexDocument` compatible with the existing client-side retrieval system.

## What it does

1. (Optional) OCR scanned PDFs using `ocrmypdf` + Tesseract.
2. Extract per-page text.
3. Clean/normalize text.
4. Chunk into word windows (default: 180 words, overlap 30).
5. Build lightweight 24-dim hash embeddings per chunk.
6. Emit JSON that matches the app contract:
   - `manifest.json`
   - `chunks.json`
   - `index.json` (full `PdfIndexDocument`)

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[server,ocr,test]'
```

### OCR dependencies (system)

- `tesseract`
- `ghostscript`

macOS (Homebrew):

```bash
brew install tesseract ghostscript
```

## CLI usage

### Build an index from a PDF

```bash
algl-pdf index ./my.pdf --out ./out/pdf-index
```

### Force OCR first (recommended for scanned PDFs)

```bash
algl-pdf index ./scan.pdf --out ./out/pdf-index --ocr
```

### Process a directory of PDFs

```bash
algl-pdf index ./pdfs --out ./out/pdf-index
```

### Generate concept-based learning materials (NEW)

Create a `concepts.yaml` file to define concepts and their page ranges (see `concepts.yaml.example`),
then run:

```bash
algl-pdf index ./SQL_Textbook.pdf --out ./out/pdf-index --use-aliases
```

This generates:

```
out/pdf-index/
├── manifest.json           # Index metadata
├── chunks.json            # Raw chunks with embeddings
├── index.json             # Full document
├── concept-manifest.json  # NEW: Concept metadata and chunk mappings
└── concepts/              # NEW: Readable markdown files
    ├── README.md          # Index of all concepts
    ├── select-basic.md    # Individual concept content
    ├── where-clause.md
    └── ...
```

Concept files include:
- Structured content (definition, examples, common mistakes)
- Page references for source citation
- Difficulty levels and estimated read times
- Links to related concepts

## Server usage (optional)

```bash
algl-pdf serve --host 127.0.0.1 --port 7345
```

Endpoints:

- `POST /v1/index`  (multipart form field: `pdf`)
  - returns `{ document, manifest, chunks }`

## Output format notes

- Schema version: `pdf-index-schema-v2`
- Chunker version: `word-window-180-overlap-30-v1`
- Embedding model ID: `hash-embedding-v1`

Doc IDs:

- Upload-mode doc IDs: `doc-<sha256[:12]>`
- Disk-mode doc IDs (optional): stable aliases (e.g. `sql-textbook`) via `--use-aliases`

