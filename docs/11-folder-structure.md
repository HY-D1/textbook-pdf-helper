# Folder Structure Guide

This project uses a simple folder-based workflow for processing PDFs.

## Directory Layout

```
algl-pdf-helper/
├── raw_pdf/           # Put your PDFs here (input)
│   ├── textbook.pdf
│   └── reference.pdf
├── read_use/          # Processed outputs appear here
│   ├── textbook/      # One folder per PDF
│   │   ├── manifest.json
│   │   ├── chunks.json
│   │   ├── index.json
│   │   ├── concept-manifest.json
│   │   └── concepts/
│   │       ├── README.md
│   │       ├── select-basic.md
│   │       └── ...
│   └── reference/
│       └── ...
└── start.sh           # Interactive processing script
```

## Quick Start

### 1. Add PDFs

Copy your PDF files into the `raw_pdf/` folder:

```bash
cp ~/Downloads/SQL_Textbook.pdf raw_pdf/
```

### 2. Run the Interactive Script

```bash
./start.sh
```

This will show a menu:

```
========================================
ALGL PDF Helper - Main Menu
========================================

Raw PDFs available: 1
Output directory: /Users/.../algl-pdf-helper/read_use

1) 📄 Process Single PDF
2) 📁 Process All PDFs
3) 🔄 Re-process Existing PDF
4) 📋 List Raw PDFs
5) 📂 Open Output Folder
6) ⚙️  Advanced Options
7) 🚪 Exit

Select option [1-7]:
```

### 3. Choose Processing Option

- **Option 1**: Select and process a single PDF
- **Option 2**: Process all PDFs in `raw_pdf/`
- **Option 3**: Re-process a previously processed PDF
- **Option 4**: List all PDFs with their processing status

### 4. Find Your Output

After processing, outputs are organized in `read_use/<pdf-name>/`:

```
read_use/sql-textbook/
├── manifest.json              # Index metadata
├── chunks.json               # Text chunks with embeddings
├── index.json                # Complete index document
├── concept-manifest.json     # Concept mappings (if concepts.yaml exists)
└── concepts/                 # Readable concept files
    ├── README.md             # Index of all concepts
    ├── select-basic.md       # Individual concept content
    ├── where-clause.md
    └── ...
```

## Advanced Usage

### Custom Concepts Configuration

To generate concept-based learning materials, create a `concepts.yaml` in the **same folder as your PDF** or in the project root:

```bash
cp concepts.yaml.example raw_pdf/my-textbook-concepts.yaml
cd raw_pdf
ln -s my-textbook-concepts.yaml concepts.yaml
```

### Batch Processing Without Menu

You can also process directly without the interactive menu:

```bash
# Process single PDF
algl-pdf index raw_pdf/textbook.pdf --out read_use/textbook --use-aliases

# Process with OCR
algl-pdf index raw_pdf/scanned.pdf --out read_use/scanned --ocr --use-aliases

# Process with custom concepts config
algl-pdf index raw_pdf/textbook.pdf --out read_use/textbook --use-aliases --concepts-config raw_pdf/concepts.yaml
```

## Git Ignore

The `.gitignore` is configured to:
- **Ignore** PDF files in `raw_pdf/` (you add these manually)
- **Ignore** all generated outputs in `read_use/`
- **Keep** the folder structure with `.gitkeep` files

This keeps the repository clean while maintaining the expected folder structure.
