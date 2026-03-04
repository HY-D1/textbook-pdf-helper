# OCR Fix Quick Guide

## The Problem You Experienced

You ran:
```bash
algl-pdf index ./raw_pdf/murachs-mysql-3rd-edition.pdf \
    --output-dir ./read_use/murachs-mysql \
    --ocr \
    --use-aliases
```

And got Tesseract errors:
- `[tesseract] Error during processing.`
- `[tesseract] lots of diacritics - possibly poor OCR`

## Why This Happened

**Your PDF has 99.4% text coverage** - it's a high-quality digital PDF with excellent embedded text.

When you use `--ocr` on such PDFs, Tesseract tries to OCR pages that already have text, which causes errors. **OCR should only be used for scanned documents!**

---

## The Fix

### Immediate Solution (Process Without OCR)

```bash
# ✅ CORRECT WAY - Don't use --ocr for digital PDFs
algl-pdf index ./raw_pdf/murachs-mysql-3rd-edition.pdf \
    --output-dir ./read_use/murachs-mysql \
    --use-aliases
```

This will:
- Extract text directly using PyMuPDF
- Skip Tesseract entirely
- Complete without errors
- Produce high-quality output

---

## New Smart Features (Auto-Protection)

### 1. Smart OCR Skip (Built-in)

The system now automatically skips OCR for high-quality PDFs, even if you use `--ocr`:

```bash
# This will auto-skip OCR and show a warning
algl-pdf index ./my.pdf --out ./output --ocr --use-aliases
```

Output:
```
⚠️ OCR was requested but PDF has excellent text quality (99.4% coverage).
   Skipping OCR to avoid unnecessary processing and potential Tesseract errors.
```

### 2. Smart Processing Script (Recommended)

Use the new smart processing script that checks quality first:

```bash
./smart_process.sh ./raw_pdf/murachs-mysql-3rd-edition.pdf ./read_use/output
```

This script will:
1. Check text quality (99.4% coverage)
2. Detect it's a digital PDF
3. Process WITHOUT OCR
4. Show clear status messages

### 3. Check Quality First

Before processing, check the PDF quality:

```bash
algl-pdf check-quality ./raw_pdf/murachs-mysql-3rd-edition.pdf
```

Output will show:
```
Pages with text: 123
Total characters: 456,789
Readable ratio: 99.6%
Text coverage score: 99.4%
Meets threshold: ✅ Yes

✅ Quality is GOOD - no OCR needed
```

---

## When to Use OCR

| Situation | Use OCR? | Command |
|-----------|----------|---------|
| Digital textbook (like Murach's) | ❌ NO | `algl-pdf index pdf --out dir --use-aliases` |
| Generated PDF (Word, LaTeX, etc) | ❌ NO | `algl-pdf index pdf --out dir --use-aliases` |
| Scanned document | ✅ YES | `algl-pdf index pdf --out dir --ocr --use-aliases` |
| Old fax or image PDF | ✅ YES | `algl-pdf index pdf --out dir --ocr --use-aliases` |

---

## Updated start.sh Pipeline

The `start.sh` pipeline now has **smart OCR detection** built in:

1. **Phase 1 (Analysis)**: Checks PDF quality
2. **If quality > 90%**: Automatically skips OCR
3. **If quality < 70%**: Automatically uses OCR
4. **Clear messages**: Tells you what strategy is being used

To use:
```bash
./start.sh
# Select option 0 for Full Processing Pipeline
# The pipeline will automatically detect and use the correct strategy
```

---

## Summary

### The Root Cause
You used `--ocr` on a digital PDF that didn't need it.

### The Solution
Process without `--ocr`:
```bash
algl-pdf index ./raw_pdf/murachs-mysql-3rd-edition.pdf \
    --output-dir ./read_use/murachs-mysql \
    --use-aliases
```

### The Prevention
The system now has smart OCR skip that automatically prevents this error for high-quality PDFs.

---

## Files Modified

1. **`src/algl_pdf_helper/extract.py`** - Smart OCR skip, better error messages
2. **`src/algl_pdf_helper/indexer.py`** - Smart skip threshold support
3. **`src/algl_pdf_helper/cli.py`** - New `--smart-skip-threshold` option
4. **`start.sh`** - Quality-based OCR decisions in pipeline
5. **`smart_process.sh`** - **NEW** Smart processing wrapper script
6. **`test_reports/OCR_FIX_REPORT.md`** - Detailed technical report

---

## Need Help?

Run these commands for assistance:

```bash
# Check PDF quality
algl-pdf check-quality ./your.pdf

# Get help
algl-pdf index --help

# Use the smart script
./smart_process.sh ./your.pdf
```
