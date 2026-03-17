# Fallback Decision Rules - Week 1 v1.5

**Status:** LOCKED  
**Version:** 1.5.0  
**Scope:** Week 1 Production Pipeline  
**Last Updated:** 2026-03-15

---

## Overview

This document defines the **explicit fallback decision rules** for the Week 1 production pipeline. It specifies exactly when to trigger OCR/layout fallback and LLM repair, with clear success/failure triggers and routing logic.

```
┌────────────────────────────────────────────────────────────────┐
│              FALLBACK DECISION MATRIX v1.5                      │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│   EXTRACTION QUALITY           ┌──────────────┐                │
│   ┌──────────────────┐         │   ROUTING    │                │
│   │ Coverage ≥ 70%?  │────────►│ Deterministic│                │
│   └────────┬─────────┘  YES    │    Path      │                │
│            │ NO                 └──────────────┘                │
│            ▼                                                    │
│   ┌──────────────────┐         ┌──────────────┐                │
│   │ GLM OCR per-page │────────►│   Fallback   │                │
│   │ (sliced scope)   │         │    Path      │                │
│   └──────────────────┘         └──────────────┘                │
│                                                                 │
│   ┌────────────────────────────────────────────────────┐       │
│   │ POST-PROCESSING QUALITY                            │       │
│   ├────────────────────────────────────────────────────┤       │
│   │ L3 Score ≥ 0.6? ──YES──► Export as-is              │       │
│   │ L3 Score < 0.6? ──NO───► Local Qwen 9B Repair      │       │
│   └────────────────────────────────────────────────────┘       │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## Part 1: Extraction Fallback Rules (Deterministic → GLM OCR)

### Decision Tree

```
┌─────────────────┐
│  Extract Page   │
│  with PyMuPDF   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────────────────┐
│ Calculate       │     │ SUCCESS: Use deterministic  │
│ Coverage Score  │────►│ extraction result           │
└────────┬────────┘ YES └─────────────────────────────┘
         │
         │ NO (< 0.70)
         ▼
┌─────────────────┐     ┌─────────────────────────────┐
│ Run Secondary   │     │ SUCCESS: Use GLM OCR result │
│ Checks (below)  │────►│ for this page only          │
└────────┬────────┘ YES └─────────────────────────────┘
         │
         │ NO (checks fail)
         ▼
┌─────────────────────────────┐
│ FAILURE: Mark page as       │
│ unprocessable, log error    │
└─────────────────────────────┘
```

### Success Triggers (Stay on Default Path)

| Trigger | Condition | Threshold | Action |
|---------|-----------|-----------|--------|
| Coverage threshold | Text coverage score | `≥ 0.70` | ✅ Use deterministic extraction |
| Readable ratio | Readable chars / total | `≥ 0.70` | ✅ Use deterministic extraction |
| Minimum content | Total extracted chars | `≥ 500` | ✅ Use deterministic extraction |
| Clean structure | No column bleed detected | N/A | ✅ Use deterministic extraction |

### Failure Triggers (Switch to Fallback Path)

| Trigger | Condition | Threshold | Action |
|---------|-----------|-----------|--------|
| Low coverage | Text coverage score | `< 0.70` | 🔄 Trigger GLM OCR for this page |
| Poor readability | Readable ratio | `< 0.70` | 🔄 Trigger GLM OCR for this page |
| High gibberish | Gibberish pattern ratio | `> 0.30` | 🔄 Trigger GLM OCR for this page |
| No embedded text | Extracted chars | `< 100` | 🔄 Trigger GLM OCR for this page |
| Encrypted content | Password protected | N/A | 🛑 FAIL (cannot process) |
| Corrupted page | Extraction error | N/A | 🔄 Trigger GLM OCR or skip |

### Granularity Rule (CRITICAL)

**Per-Page/Slice Only - NOT Whole-Book**

```python
# CORRECT: Granular fallback
def process_document(pdf_path, slices):
    for slice in slices:
        result = extract_deterministic(slice)
        if result.quality < 0.70:
            result = extract_glm_ocr(slice)  # Only this slice
        yield result

# INCORRECT: Whole-book fallback  
def process_document(pdf_path, slices):
    if any(s.quality < 0.70 for s in slices):
        return extract_glm_ocr_entire_book(pdf_path)  # DO NOT DO THIS
```

### Fallback Routing Logic

```yaml
routing:
  condition: "deterministic_quality < 0.70"
  action: "route_to_glm_ocr"
  scope: "per_page_or_slice"
  
  # NEVER these actions:
  never:
    - "rerun_entire_book_with_ocr"
    - "switch_all_pages_to_ocr"
    - "use_ocr_as_primary_method"
  
  # ALWAYS these actions:
  always:
    - "attempt_deterministic_first"
    - "evaluate_quality_per_page"
    - "fallback_only_failed_pages"
```

---

## Part 2: Repair Fallback Rules (Weak Content → Qwen 9B)

### Decision Tree

```
┌─────────────────┐
│ Generate L3     │
│ Content         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────────────────┐
│ Assess Quality  │     │ SUCCESS: Export unit        │
│ Score           │────►│ as student_ready            │
└────────┬────────┘ YES └─────────────────────────────┘
         │
         │ NO (< 0.6)
         ▼
┌─────────────────┐     ┌─────────────────────────────┐
│ Source Evidence │     │ SUCCESS: Use repaired       │
│ Available?      │────►│ content, mark as repaired   │
└────────┬────────┘ YES └─────────────────────────────┘
         │
         │ NO
         ▼
┌─────────────────────────────┐
│ FAILURE: Mark as fallback   │
│ unit, may be filtered out   │
└─────────────────────────────┘
```

### Success Triggers (No Repair Needed)

| Trigger | Condition | Threshold | Action |
|---------|-----------|-----------|--------|
| L3 quality good | Quality score | `≥ 0.6` | ✅ Export as-is |
| Definition present | Definition length | `≥ 100 chars` | ✅ Export as-is |
| Examples present | Real (non-synthetic) examples | `≥ 1` | ✅ Export as-is |
| Source grounded | Evidence blocks available | `≥ 2` | ✅ Export as-is |

### Failure Triggers (Trigger Qwen 9B Repair)

| Trigger | Condition | Threshold | Action |
|---------|-----------|-----------|--------|
| Low L3 quality | Quality score | `< 0.6` | 🔄 Trigger Qwen 9B repair |
| Missing definition | Definition length | `< 50 chars` | 🔄 Trigger Qwen 9B repair |
| Missing why_it_matters | Why it matters length | `< 50 chars` | 🔄 Trigger Qwen 9B repair |
| No real examples | All examples synthetic | `100%` | 🔄 Trigger Qwen 9B repair |
| Generic definition | Contains generic phrase | detected | 🔄 Trigger Qwen 9B repair |

### Repair Model Policy

```yaml
repair_model:
  primary: "qwen3.5:9b-q8_0"
  fallback: "qwen2.5:3b"
  host: "http://localhost:11434"
  external_api: false
  
  explicitly_prohibited:
    - "kimi-k2-5"
    - "gpt-4"
    - "claude-3"
    - "any_remote_llm"
  
  explicitly_allowed:
    - "qwen3.5:9b-q8_0"
    - "qwen3.5:27b-q4_K_M"
    - "qwen2.5:3b"
    - "any_ollama_local"
```

### Repair Scope Rules

```yaml
repair_scope:
  type: "selective"
  
  run_repair_for:
    - "flagged_weak_concepts"
    - "units_with_quality < 0.6"
    - "units_with_missing_l3"
  
  do_not_run_repair_for:
    - "all_units_by_default"
    - "units_already_passing_quality"
    - "units_without_source_evidence"
  
  max_repair_attempts: 3
```

---

## Part 3: Decision Tables

### Table 1: Extraction Strategy Decision

| Condition | Value | Deterministic | GLM OCR | Action |
|-----------|-------|:-------------:|:-------:|--------|
| Text coverage | ≥ 70% | ✅ | ❌ | Use deterministic |
| Text coverage | < 70% | ❌ | ✅ | Use GLM OCR for this page |
| Embedded text | Yes + good quality | ✅ | ❌ | Use deterministic |
| Embedded text | No (scanned) | ❌ | ✅ | Use GLM OCR for this page |
| Encrypted | Yes | ❌ | ❌ | FAIL - cannot process |

### Table 2: Repair Trigger Decision

| Condition | Value | No Repair | Qwen 9B | Action |
|-----------|-------|:---------:|:-------:|--------|
| L3 quality score | ≥ 0.6 | ✅ | ❌ | Export as-is |
| L3 quality score | < 0.6 | ❌ | ✅ | Trigger repair |
| Evidence available | Yes + low quality | ❌ | ✅ | Trigger repair |
| Evidence available | No + low quality | ❌ | ❌ | Mark as fallback unit |
| Definition is generic | Yes | ❌ | ✅ | Trigger repair |

### Table 3: Model Selection Decision

| Scenario | Model | External API | Allowed |
|----------|-------|:------------:|:-------:|
| Initial extraction | PyMuPDF | No | ✅ Yes |
| Fallback OCR | GLM-4V | Yes | ✅ Yes (fallback only) |
| Content repair | Qwen 9B (local) | No | ✅ Yes |
| Content repair | Kimi/ChatGPT | Yes | ❌ No |

---

## Part 4: Threshold Reference

### Quality Thresholds

```yaml
thresholds:
  extraction:
    min_text_coverage: 0.70
    min_readable_ratio: 0.70
    max_gibberish_ratio: 0.30
    min_extracted_chars: 500
    
  repair:
    min_l3_quality: 0.60
    min_definition_length: 50
    min_why_it_matters_length: 50
    max_fallback_ratio: 0.10
    
  export:
    min_student_ready_quality: 0.80
    min_concept_coverage: 0.80
```

### Quality Score Formula (L3)

```python
def calculate_l3_quality(content, evidence_blocks):
    score = 0.0
    
    # Definition quality (0-0.4)
    definition = content.get("definition", "")
    if len(definition) > 100:
        score += 0.3
    elif len(definition) > 50:
        score += 0.1
    
    # Why it matters (0-0.2)
    why = content.get("why_it_matters", "")
    if len(why) > 50:
        score += 0.2
    
    # Examples (0-0.3)
    examples = content.get("examples", [])
    real_examples = sum(1 for ex in examples if not ex.get("is_synthetic", True))
    score += min(real_examples * 0.15, 0.3)
    
    # Evidence (0-0.1)
    if len(evidence_blocks) > 5:
        score += 0.1
    elif len(evidence_blocks) > 2:
        score += 0.05
    
    # Penalties
    generic_phrases = [
        "is an important SQL concept",
        "is a crucial SQL concept",
    ]
    for phrase in generic_phrases:
        if phrase in definition.lower():
            score -= 0.2
    
    return max(0.0, min(1.0, score))
```

---

## Part 5: Failure Handling

### Extraction Failure Scenarios

| Scenario | Action | Log Level |
|----------|--------|-----------|
| Single page fails | Try GLM OCR for that page | WARNING |
| GLM OCR also fails | Mark page as unprocessable | ERROR |
| All pages fail | FAIL the document | CRITICAL |
| Encrypted PDF | FAIL immediately | ERROR |
| Corrupted PDF | FAIL with details | ERROR |

### Repair Failure Scenarios

| Scenario | Action | Log Level |
|----------|--------|-----------|
| Ollama not available | Skip repair, continue without | WARNING |
| Model not found | Try fallback model | WARNING |
| Repair timeout | Skip repair, mark as fallback | ERROR |
| Repair validation fails | Retry (up to 3 times) | WARNING |
| All retries fail | Mark as fallback unit | ERROR |

---

## Part 6: Compliance Verification

### Checklist for Pipeline Implementation

- [ ] Deterministic extraction attempted first for every page
- [ ] Quality validation runs after extraction
- [ ] GLM OCR triggered only for pages with quality < 0.70
- [ ] GLM OCR never applied to entire book
- [ ] L3 quality assessment runs on all units
- [ ] Qwen 9B repair triggered only for units with quality < 0.60
- [ ] No external LLM (Kimi/OpenAI) used for repair
- [ ] Repair only runs when source evidence is available
- [ ] Fallback units tracked and reported
- [ ] All thresholds match this document

### Example Log Output

```
[INFO] Processing page 1-50 (deterministic extraction)
[INFO] Coverage: 0.85 - PASS (using deterministic)
[INFO] Processing page 51-100 (deterministic extraction)
[WARN] Coverage: 0.45 - FAIL (triggering GLM OCR)
[INFO] Page 51-100: GLM OCR applied
[INFO] Coverage after OCR: 0.88 - PASS
[INFO] Generated 8 units, assessing quality...
[WARN] Unit 'joins-001' L3 quality: 0.45 (< 0.60)
[INFO] Repairing 'joins-001' with Qwen 9B...
[INFO] Repair successful, new quality: 0.72
[INFO] Export: 8 units (1 repaired) - student_ready mode
```

---

## Related Documents

- **Pipeline Contract:** `docs/pipeline_contract_week1_v15.md`
- **Scope Config:** `data/demo_scope_week1_v15.yaml`
- **Ollama Repair Guide:** `docs/OLLAMA_REPAIR_GUIDE.md`
- **Quality Metrics:** `src/algl_pdf_helper/quality_metrics.py`
