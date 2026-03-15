# Week 1 Production Pipeline Contract v1.5

**Status:** LOCKED  
**Version:** 1.5.0  
**Effective:** 2026-03-15  
**Expiration:** 2026-03-29 (2 week fixed demo scope)  
**Last Updated:** 2026-03-15

---

## Executive Summary

This document locks the Week 1 production pipeline contract for the ALGL PDF Helper. It defines **one explicit default path**, **one explicit fallback path**, **one explicit repair path**, and **one fixed demo scope** for the next 2 weeks.

**Key Principle:** Whole-book processing is **NOT** required for the Week 1 demo. We process **one chapter/page range per textbook**, not full books.

---

## The Three Pipeline Paths

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRODUCTION PIPELINE v1.5                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐                                            │
│  │  INPUT PDF      │                                            │
│  │  (single slice) │                                            │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────────────┐    ┌─────────────────────────────┐ │
│  │  1. DEFAULT PATH        │    │  SUCCESS TRIGGERS           │ │
│  │  Deterministic          │◄───┤  • Coverage ≥ 70%           │ │
│  │  Extraction (PyMuPDF)   │    │  • Readable text ratio ≥70% │ │
│  │  • fitz direct          │    │  • No gibberish patterns    │ │
│  │  • No external API      │    │  • Clean structure          │ │
│  │  • Quality validation   │    │                             │ │
│  └────────┬────────────────┘    └─────────────────────────────┘ │
│           │                                                      │
│           │ FAILURE                                              │
│           ▼                                                      │
│  ┌─────────────────────────┐    ┌─────────────────────────────┐ │
│  │  2. FALLBACK PATH       │    │  FAILURE TRIGGERS           │ │
│  │  GLM OCR Layout         │◄───┤  • Coverage < 70%           │ │
│  │  • GLM-4V OCR API       │    │  • Low readable ratio       │ │
│  │  • Per-page/slice only  │    │  • Gibberish detected       │ │
│  │  • NOT whole-book       │    │  • Encrypted/corrupted      │ │
│  │  • For failed slices    │    │                             │ │
│  └────────┬────────────────┘    └─────────────────────────────┘ │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────────────┐                                    │
│  │  EXTRACTED CONTENT      │                                    │
│  │  (good or fallback)     │                                    │
│  └────────┬────────────────┘                                    │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────────────┐    ┌─────────────────────────────┐ │
│  │  3. REPAIR PATH         │    │  TRIGGER CONDITIONS         │ │
│  │  Local Qwen 9B Repair   │◄───┤  • L3 quality < 0.6         │ │
│  │  • qwen3.5:9b-q8_0      │    │  • Missing L3 content       │ │
│  │  • Ollama localhost     │    │  • Weak concept coverage    │ │
│  │  • NO external LLM      │    │  • Flagged weak units       │ │
│  │  • Per flagged concept  │    │                             │ │
│  └────────┬────────────────┘    └─────────────────────────────┘ │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────────────┐                                    │
│  │  STUDENT_READY EXPORT   │                                    │
│  │  (validated units)      │                                    │
│  └─────────────────────────┘                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Path 1: Default Path (Deterministic Extraction First)

### Method
- **Tool:** PyMuPDF (fitz)
- **Strategy:** Direct text extraction
- **Quality Check:** 70% text coverage threshold
- **External API:** None

### Success Criteria
```yaml
coverage_score: ">= 0.70"
readable_ratio: ">= 0.70"
gibberish_ratio: "<= 0.30"
min_extracted_chars: ">= 500"
```

### When This Path is Used
- Always attempted first for every PDF slice
- No preconditions or prerequisites
- Zero external dependencies required

### Expected Outcome
- Clean text extraction from digital PDFs
- Direct text available from embedded fonts
- No OCR processing needed

---

## Path 2: Fallback Path (GLM OCR Layout)

### Method
- **Tool:** GLM-4V OCR API (not OCRmyPDF)
- **Granularity:** Per-page or per-slice (NOT whole-book)
- **Trigger:** Quality failure on default path
- **External API:** Yes (GLM)

### Failure Triggers (Default Path → Fallback)
| Trigger | Threshold | Description |
|---------|-----------|-------------|
| Low coverage | `< 0.70` | Text coverage below 70% |
| Poor readability | `< 0.70` | Readable character ratio too low |
| High gibberish | `> 0.30` | Too many OCR artifacts detected |
| No embedded text | `0` | Scanned PDF with no text layer |
| Corrupted page | N/A | Page extraction error |

### Granularity Rule
```yaml
# CORRECT: Per-page or per-slice fallback
slice_1: "use deterministic (success)"
slice_2: "use GLM OCR (failed default)"
slice_3: "use deterministic (success)"

# INCORRECT: Whole-book fallback
whole_book: "DO NOT process entire book with GLM OCR"
```

### When This Path is Used
- Only for specific pages/slices that fail deterministic extraction
- Never applied to entire books in Week 1 demo scope
- Only triggered by quality validation failure

---

## Path 3: Repair Path (Local Qwen 9B Only)

### Method
- **Tool:** Ollama with Qwen 9B
- **Model:** `qwen3.5:9b-q8_0` (primary) or `qwen2.5:3b` (fallback)
- **Host:** `http://localhost:11434`
- **External API:** None (local only)

### Trigger Conditions
| Condition | Threshold | Description |
|-----------|-----------|-------------|
| Weak L3 content | `< 0.6` | Content quality score below 0.6 |
| Missing L3 | `absent` | No L3 content generated |
| Low concept coverage | `< 80%` | Less than 80% of concepts have L3 |
| Fallback units | `> 10%` | Too many units using fallback content |

### Repair Scope
- Only runs on **flagged weak concepts**
- NOT run on all units (selective repair)
- Bases repairs on **source evidence** from extraction
- Does not hallucinate outside textbook content

### External LLM Policy
```yaml
# EXPLICITLY PROHIBITED for repair:
kimi_api: false
openai_api: false
anthropic_api: false
remote_llm: false

# EXPLICITLY ALLOWED for repair:
ollama_local: true
qwen_9b: true
```

---

## Fixed Demo Scope (2 Weeks)

### Whole-Book Processing Policy

**WHOLE-BOOK PROCESSING = NOT REQUIRED FOR DEMO**

We process **one chapter/page range per textbook**, not full books.

### Textbook Slices

#### Textbook 1: Murach's MySQL (3rd Edition)
```yaml
slice:
  type: "chapter"
  value: "3"
  pages: "60-80 estimated"
  
concepts:
  count: 8
  ids:
    - select-basic
    - where-clause
    - order-by
    - alias
    - distinct
    - comparison-operators
    - pattern-matching
    - null-handling

export_mode: "student_ready"
```

#### Textbook 2: Ramakrishnan - Database Management Systems
```yaml
slice:
  type: "chapter"
  value: "2"
  pages: "40-60 estimated"
  
concepts:
  count: 10
  ids:
    - relational-model
    - schema-instance
    - key-constraints
    - foreign-key
    - sql-overview
    - create-table
    - insert-statement
    - select-basic
    - where-clause
    - join-concept

export_mode: "student_ready"
```

### Concept Target Range
- **Minimum:** 8 concepts per slice
- **Maximum:** 12 concepts per slice
- **Rationale:** Focused, high-quality extraction over broad coverage

---

## Configuration Reference

### Scope Config File
```yaml
file: "data/demo_scope_week1_v15.yaml"
status: locked
version: "1.5.0"
```

### Fallback Decision Rules
```yaml
file: "docs/fallback_decision_rules_week1.md"
contents: "Detailed trigger conditions and routing logic"
```

### CLI Commands

**Murach Chapter 3:**
```bash
algl-pdf process raw_pdf/murachs-mysql-3rd-edition.pdf \
  --output-dir ./outputs/week1-v15/murach-ch3 \
  --chapter-range 3 \
  --export-mode student_ready \
  --filter-level production \
  --use-ollama-repair \
  --ollama-model qwen3.5:9b-q8_0
```

**Ramakrishnan Chapter 2:**
```bash
algl-pdf process raw_pdf/ramakrishnan-dbms-3rd-edition.pdf \
  --output-dir ./outputs/week1-v15/ramakrishnan-ch2 \
  --chapter-range 2 \
  --export-mode student_ready \
  --filter-level production \
  --use-ollama-repair \
  --ollama-model qwen3.5:9b-q8_0
```

---

## Compliance Checklist

- [x] Default path documented: deterministic extraction first
- [x] Fallback path documented: GLM OCR only for failed slices/pages
- [x] Repair path documented: local Qwen 9B only
- [x] Demo scope documented: one chapter/page range per textbook
- [x] Whole-book processing explicitly marked as NOT required
- [x] Murach slice defined: Chapter 3, 8 concepts
- [x] Ramakrishnan slice defined: Chapter 2, 10 concepts
- [x] Export mode locked: `student_ready`
- [x] Fallback policy documented
- [x] 2-week fixed scope with expiration date

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-03-15 | Initial Week 1 scope (Murach Ch 3-4 only) |
| 1.5.0 | 2026-03-15 | Added Ramakrishnan, locked 3-path pipeline, added GLM OCR fallback |

---

## Related Documents

- **Scope Config:** `data/demo_scope_week1_v15.yaml`
- **Fallback Rules:** `docs/fallback_decision_rules_week1.md`
- **Previous Scope:** `data/demo_scope_week1.yaml` (v1.0)
- **Ollama Repair Guide:** `docs/OLLAMA_REPAIR_GUIDE.md`
