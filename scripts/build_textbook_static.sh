#!/bin/bash
# =============================================================================
# build_textbook_static.sh
# Canonical batch command: index both raw PDFs and export a merged
# textbook-static corpus that the adaptive app can consume directly.
#
# Output layout (under OUTPUT_DIR):
#   textbook-manifest.json   — schema-v1 manifest with both sourceDocIds
#   concept-map.json         — merged concept map, namespaced by docId
#   chunks-metadata.json     — chunk counts per docId
#   concepts/<docId>/*.md    — per-concept markdown files
#
# Usage:
#   ./scripts/build_textbook_static.sh [OUTPUT_DIR]
#
# Environment:
#   OUTPUT_DIR  (arg or env)  destination for the export;
#               defaults to ./output/textbook-static
#   OLLAMA_HOST               Ollama URL (default: http://localhost:11434)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
OUTPUT_DIR="${1:-${OUTPUT_DIR:-./output/textbook-static}}"
INDEX_DIR="${OUTPUT_DIR}/index"   # intermediate per-PDF index trees
MURACH_PDF="raw_pdf/murachs-mysql-3rd-edition.pdf"
RAMI_PDF="raw_pdf/dbms-ramakrishnan-3rd-edition.pdf"

# Activate virtualenv if present
if [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

PYTHON="${PYTHON:-python}"

echo "============================================================"
echo " build_textbook_static — dual-PDF textbook-static export"
echo "============================================================"
echo " Repo root : $REPO_ROOT"
echo " Output dir: $OUTPUT_DIR"
echo " Index dir : $INDEX_DIR"
echo "------------------------------------------------------------"

# ---------------------------------------------------------------------------
# Guard: confirm both PDFs exist
# ---------------------------------------------------------------------------
missing=0
for pdf in "$MURACH_PDF" "$RAMI_PDF"; do
    if [ ! -f "$pdf" ]; then
        echo "❌  Missing PDF: $pdf"
        missing=1
    fi
done
if [ "$missing" -ne 0 ]; then
    echo ""
    echo "Place both PDFs in raw_pdf/ and re-run."
    exit 1
fi

mkdir -p "$OUTPUT_DIR" "$INDEX_DIR"

# ---------------------------------------------------------------------------
# Helper: index one PDF
# ---------------------------------------------------------------------------
index_pdf() {
    local pdf_path="$1"
    local doc_label="$2"
    local idx_dir="$INDEX_DIR/$doc_label"

    echo ""
    echo "──────────────────────────────────────────────────────────"
    echo " INDEXING: $(basename "$pdf_path")"
    echo " → $idx_dir"
    echo "──────────────────────────────────────────────────────────"

    $PYTHON -m algl_pdf_helper index \
        "$pdf_path" \
        --output-dir "$idx_dir" \
        --use-aliases \
        --strip-headers

    echo " ✅ Indexed: $(basename "$pdf_path")"
}

# ---------------------------------------------------------------------------
# Helper: export one indexed PDF into the shared output dir (merge=True)
# ---------------------------------------------------------------------------
export_pdf() {
    local idx_dir="$1"
    local doc_label="$2"

    echo ""
    echo "──────────────────────────────────────────────────────────"
    echo " EXPORTING: $doc_label"
    echo " from $idx_dir → $OUTPUT_DIR"
    echo "──────────────────────────────────────────────────────────"

    $PYTHON -m algl_pdf_helper export \
        "$idx_dir" \
        --output-dir "$OUTPUT_DIR" \
        --merge

    echo " ✅ Exported: $doc_label"
}

# ---------------------------------------------------------------------------
# Phase 1 — Index both PDFs
# ---------------------------------------------------------------------------
echo ""
echo "=== Phase 1: Indexing PDFs ==="
index_pdf "$MURACH_PDF"  "murach"
index_pdf "$RAMI_PDF"    "ramakrishnan"

# ---------------------------------------------------------------------------
# Phase 2 — Export both into shared output (second export merges with first)
# ---------------------------------------------------------------------------
echo ""
echo "=== Phase 2: Exporting to textbook-static ==="
export_pdf "$INDEX_DIR/murach"       "murachs-mysql-3rd-edition"
export_pdf "$INDEX_DIR/ramakrishnan" "dbms-ramakrishnan-3rd-edition"

# ---------------------------------------------------------------------------
# Phase 3 — Validate handoff integrity
# ---------------------------------------------------------------------------
echo ""
echo "=== Phase 3: Validating handoff integrity ==="
$PYTHON -m algl_pdf_helper validate-handoff "$OUTPUT_DIR" && VALID=1 || VALID=0

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "============================================================"
echo " BUILD COMPLETE"
echo "============================================================"
echo " Output: $OUTPUT_DIR"
echo ""

if [ -f "$OUTPUT_DIR/concept-map.json" ]; then
    doc_ids=$($PYTHON -c "
import json, sys
data = json.load(open('$OUTPUT_DIR/concept-map.json'))
ids = data.get('sourceDocIds', [])
print('  sourceDocIds (' + str(len(ids)) + '):')
for d in ids:
    concepts = [k for k in data.get('concepts', {}) if k.startswith(d + '/')]
    print('    ' + d + '  →  ' + str(len(concepts)) + ' concepts')
" 2>/dev/null)
    echo "$doc_ids"
fi

echo ""
if [ -f "$OUTPUT_DIR/textbook-manifest.json" ]; then
    echo " ✅ textbook-manifest.json"
fi
if [ -f "$OUTPUT_DIR/concept-map.json" ]; then
    echo " ✅ concept-map.json"
fi
if [ -f "$OUTPUT_DIR/chunks-metadata.json" ]; then
    echo " ✅ chunks-metadata.json"
fi

echo ""
if [ "$VALID" -eq 1 ]; then
    echo " ✅ Handoff integrity: VALID — ready for adaptive app sync"
else
    echo " ⚠️  Handoff integrity check reported issues — review output above"
    exit 2
fi
echo "============================================================"
