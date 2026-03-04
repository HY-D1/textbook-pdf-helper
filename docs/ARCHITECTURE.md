# ALGL PDF Helper - System Architecture

**Version:** 2.0.0  
**Last Updated:** 2026-03-03  
**Status:** Current

---

## Table of Contents

1. [Overview](#overview)
2. [The Four Packs](#the-four-packs)
3. [Pipeline Phases](#pipeline-phases)
4. [Data Flow](#data-flow)
5. [Component Reference](#component-reference)
6. [Event Logging](#event-logging)
7. [Provenance and Reproducibility](#provenance-and-reproducibility)
8. [Output Generation](#output-generation)

---

## Overview

The **Adaptive Textbook Helper** is a research-grade pipeline that transforms raw PDFs into structured, auditable knowledge substrates for interaction-driven SQL learning. It treats textbooks not as static sequences of chapters, but as **versioned content substrates** that can be re-assembled into adaptive instructional artifacts based on learner traces.

### Core Innovation

The system addresses the **"assistance dilemma"** in tutoring systems: when to provide hints vs. when to escalate to deeper explanations. This is operationalized through:

- **Retrieval-first generation** (RAG paradigm)
- **Complete event logging** for debugging and counterfactual replay
- **Four-pack separation** for domain independence
- **Deterministic, reproducible processing**

### Pipeline Phases

| Phase | Name | Input | Output | Key Components |
|-------|------|-------|--------|----------------|
| 1 | Document Pack Creation | Raw PDF | Clean chunks with embeddings | PyMuPDF, OCRmyPDF, Chunker |
| 2 | Domain Pack Construction | Chunks | Concept map + prerequisite DAG | Concept Mapper, Prerequisite Validator |
| 3 | Trace Pack Foundation | Domain Pack | Event schemas, metric calculators | Event Logger, Metric Engines |
| 4 | Policy Pack Integration | All Packs | Escalation rules, bandit configs | Policy Engine, Bandit Learner |
| 5 | Export & Integration | All Packs | SQL-Adapt compatible output | Exporter, Validation |

---

## The Four Packs

### Document Pack

Transforms raw PDFs into content-addressed, retrievable artifacts:

```
document-pack/
├── raw/
│   └── {doc_alias}/
│       └── source.pdf                    # Immutable original (SHA256)
├── derived/
│   └── {doc_alias}/
│       ├── ocr.pdf                       # OCR output (if applied)
│       ├── pages/{page}.txt              # Per-page extraction with quality scores
│       └── layout.json                   # Structure metadata
└── index/
    └── {doc_alias}/
        ├── chunks.jsonl                  # Deterministic chunks
        ├── embeddings.jsonl              # Hash-based 24-dim vectors
        └── index.faiss                   # Semantic retrieval index
```

**Key Requirements:**
- Content-addressed IDs (SHA256-based)
- Deterministic chunking (same input + config → same chunks)
- Page-level citations preserved throughout
- Extraction quality scores logged

### Domain Pack

Structures content as an inspectable, editable knowledge graph:

```
domain-pack/
├── concepts/
│   ├── concept-map.json                  # Concept nodes with metadata
│   └── concept-definitions.yaml          # Human-curated definitions
├── prerequisites/
│   └── prereq-dag.json                   # Directed edges: prereq → concept
├── errors/
│   └── error-taxonomy.json               # Error subtypes → concepts
└── rubrics/
    └── assessment-rubrics.json           # Evaluation criteria
```

**Concept Node Schema:**

```json
{
  "id": "select-basic",
  "canonical_name": "sql.select.basic",
  "title": "SELECT Statement Basics",
  "definition": "Retrieves data from one or more tables",
  "difficulty": "beginner",
  "estimatedReadTime": 5,
  "pageReferences": [45, 46],
  "chunkIds": ["sql-textbook:p45:c1", "sql-textbook:p45:c2"],
  "relatedConcepts": ["where-clause", "order-by"],
  "prerequisites": [],
  "teaches": ["sql.dql.basic"],
  "evidence": {
    "sourceChunks": ["sql-textbook:p45:c1"],
    "validatedBy": "human-reviewer-001",
    "validationDate": "2024-01-15T09:10:00Z"
  }
}
```

**Prerequisite DAG:**

```json
{
  "edges": [
    {
      "from": "select-basic",
      "to": "where-clause",
      "type": "prerequisite",
      "confidence": 1.0,
      "validated": true
    }
  ],
  "version": "1.0.0",
  "lastModified": "2024-01-15T09:10:00Z",
  "modifiedBy": "human-reviewer-001"
}
```

**Key Requirements:**
- Canonical concept IDs (e.g., `sql.where.basic`)
- Explicit prerequisite edges (not flat coverage)
- Versioned and auditable (DAG changes affect mastery propagation)
- Evidence pointers to chunks/pages for every node

### Trace Pack

Captures complete interaction history for debugging and evaluation:

```
trace-pack/
├── events/
│   └── {session_id}.jsonl                # xAPI/Caliper-aligned events
├── derived/
│   ├── hdi/                              # Hint Dependency Index
│   ├── csi/                              # Cognitive Strain Index
│   ├── aps/                              # Affective Proxy Score
│   └── rqs/                              # Reflection Quality Score
└── manifests/
    └── {run_id}.json                     # Run configuration and hashes
```

**Key Metrics:**

| Metric | Definition | Formula |
|--------|------------|---------|
| **HDI** (Hint Dependency) | Help-seeking behavior | `(hints/attempts) × (time_with_hints/total_time)` |
| **CSI** (Cognitive Strain) | Interaction-based load proxy | `α(backspaces) + β(deletions) + γ(pause_time) + δ(error_rate)` |
| **APS** (Affective Proxy) | Predicted affective state | `f(click_pattern, dwell_time, rapid_switching)` |
| **RQS** (Reflection Quality) | Self-explanation quality | `g(note_length, concept_refs, self_explanation_depth)` |

**Key Requirements:**
- xAPI/Caliper/PROV-aligned event schemas
- OpenTelemetry correlation IDs
- Non-negotiable fields: `trace_id`, `run_id`, `policy_id`, `code_version`

### Policy Pack

Controls escalation and adaptive support delivery:

```
policy-pack/
├── profiles/
│   ├── fast-escalator.json               # Lower thresholds
│   ├── slow-escalator.json               # Higher thresholds
│   ├── explanation-first.json            # Bypass ladder for prereq violations
│   └── adaptive-bandit.json              # Learned policy parameters
├── thresholds/
│   └── escalation-ladder.yaml            # Formal trigger definitions
└── bandit/
    ├── arm-configs.json                  # Multi-armed bandit setup
    └── reward-function.json              # Computable from logs
```

**Escalation Profiles:**

| Profile | Strategy | Threshold Example |
|---------|----------|-------------------|
| **Fast Escalator** | Prioritize time-to-clarity | Escalate after 2 errors |
| **Slow Escalator** | Enforce productive struggle | Escalate after 5 errors |
| **Explanation-First** | Bypass for prereq violations | Immediate explanation |
| **Adaptive Bandit** | Learn optimal per-learner | Dynamic based on recovery |

**Escalation Triggers:**

```yaml
escalation_ladder:
  levels:
    - name: hint
      max_errors: 3
      max_time_ms: 300000
    - name: explanation  
      max_errors: 5
      max_time_ms: 600000
    - name: worked_example
      max_errors: 7
      max_time_ms: 900000
  
  safety_overrides:
    - trigger: prereq_violation_detected
      action: immediate_explanation
    - trigger: learner_explicit_request
      action: escalate_one_level
```

---

## Pipeline Phases

### Phase 1: Document Pack Creation

```
┌────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 1: DOCUMENT PACK CREATION                          │
│                       Input: Raw PDF → Output: Chunks                       │
└────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────┐
    │   Raw PDF File  │
    │  (source.pdf)   │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────────────────────────────────────────┐
    │  STEP 1: Quality Check & OCR Decision               │
    │  ├─ PyMuPDF extracts embedded text                  │
    │  ├─ Check coverage score (>70% = good)              │
    │  ├─ Smart OCR Skip: Skip if >90% coverage           │
    │  └─ Log: extraction_method, quality_score, flags    │
    └────────┬────────────────────────────────────────────┘
             │
    ┌────────┴────────────────────────────────────────────┐
    │  STEP 2: Page Text Extraction                       │
    │  ├─ Extract per-page text                           │
    │  ├─ Preserve page boundaries                        │
    │  ├─ Log per-page: char_count, quality_score         │
    │  └─ Emit: page_text_extracted event                 │
    └────────┬────────────────────────────────────────────┘
             │
             ▼
    ┌─────────────────────────────────────────────────────┐
    │  STEP 3: Text Cleaning                              │
    │  ├─ Fix OCR errors ("Arz" → "Are")                  │
    │  ├─ Remove headers/footers                          │
    │  ├─ Fix 2-column layout                             │
    │  └─ Normalize whitespace                            │
    └────────┬────────────────────────────────────────────┘
             │
             ▼
    ┌─────────────────────────────────────────────────────┐
    │  STEP 4: Deterministic Chunking                     │
    │  ├─ Word window: 150 words, 30 overlap              │
    │  ├─ Preserve sentence boundaries                    │
    │  ├─ Chunk ID: {docId}:p{page}:c{index}              │
    │  └─ Emit: chunk_created event                       │
    └────────┬────────────────────────────────────────────┘
             │
             ▼
    ┌─────────────────────────────────────────────────────┐
    │  STEP 5: Hash Embedding                             │
    │  ├─ 24-dimensional hash-based vectors               │
    │  ├─ Deterministic (same text → same embedding)      │
    │  ├─ L2 normalized                                   │
    │  └─ Model ID: hash-embedding-v1                     │
    └────────┬────────────────────────────────────────────┘
             │
             ▼
    ┌─────────────────────────────────────────────────────┐
    │  OUTPUT: Document Pack                              │
    │  ├─ raw/{docId}/source.pdf                          │
    │  ├─ derived/{docId}/pages/{page}.txt                │
    │  ├─ index/{docId}/chunks.jsonl                      │
    │  └─ index/{docId}/index.faiss                       │
    └─────────────────────────────────────────────────────┘
```

**CLI Commands:**
```bash
# Check extraction quality
algl-pdf check-quality ./my.pdf --detailed

# Run preflight analysis
algl-pdf preflight ./my.pdf

# Process with logging
algl-pdf index ./my.pdf --out ./document-pack --log-level debug
```

### Phase 2: Domain Pack Construction

```
┌────────────────────────────────────────────────────────────────────────────┐
│                  PHASE 2: DOMAIN PACK CONSTRUCTION                          │
│                   Input: Chunks → Output: Concept DAG                       │
└────────────────────────────────────────────────────────────────────────────┘

    Chunks (from Document Pack)
           │
           ▼
    ┌──────────────────────────────────────────────────────────┐
    │              CONCEPT MAPPING PIPELINE                     │
    └──────────────────────────────────────────────────────────┘
           │
           ├──▶ Layer 1: Manual Mapping (concepts.yaml)
           │     ├─ Human-curated concept definitions
           │     ├─ Page ranges per concept section
           │     └─ Evidence: page → chunk mapping
           │
           ├──▶ Layer 2: Auto-Suggestion
           │     ├─ Keyword matching
           │     ├─ Semantic similarity
           │     └─ Confidence scoring
           │
           └──▶ Layer 3: Human Validation
                 ├─ Review suggested links
                 ├─ Confirm or reject
                 └─ Log: concept_link_confirmed event
           │
           ▼
    ┌──────────────────────────────────────────────────────────┐
    │           PREREQUISITE DAG CONSTRUCTION                   │
    └──────────────────────────────────────────────────────────┘
           │
           ├──▶ Auto-Suggest Edges
           │     ├─ Heuristic: chapter order
           │     ├─ Keyword overlap analysis
           │     └─ Weak supervision signals
           │
           ├──▶ Human Review
           │     ├─ Validate edges
           │     ├─ Add missing edges
           │     └─ Log: prereq_edge_added event
           │
           └──▶ Version & Lock
                 ├─ DAG version: 1.0.0
                 ├─ Modified by: reviewer-id
                 └─ Immutable past versions
           │
           ▼
    ┌─────────────────────────────────────────────────────┐
    │  OUTPUT: Domain Pack                                │
    │  ├─ concepts/concept-map.json                       │
    │  ├─ prerequisites/prereq-dag.json                   │
    │  └─ concepts/{concept-id}.md                        │
    └─────────────────────────────────────────────────────┘
```

**Content Validation:**
```
Score = (SQL_keywords × 0.3) + (concept_match × 0.5) - (non_SQL_penalty × 0.2)

Filter out:
- JDBC/Java content
- HTTP protocol docs
- Chapter introductions
```

### Phase 3: Trace Pack Foundation

```
┌────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 3: TRACE PACK FOUNDATION                           │
│                Input: Domain Pack → Output: Event Infrastructure            │
└────────────────────────────────────────────────────────────────────────────┘

    Domain Pack + Document Pack
           │
           ▼
    ┌──────────────────────────────────────────────────────────┐
    │              EVENT SCHEMA GENERATION                      │
    │  ├─ xAPI-aligned event types                              │
    │  ├─ Caliper-compatible envelopes                          │
    │  └─ PROV-DM provenance tracking                           │
    └──────────────────────────────────────────────────────────┘
           │
           ▼
    ┌──────────────────────────────────────────────────────────┐
    │              METRIC CALCULATOR SETUP                      │
    │  ├─ HDI: Hint Dependency Index                            │
    │  ├─ CSI: Cognitive Strain Index                           │
    │  ├─ APS: Affective Proxy Score                            │
    │  └─ RQS: Reflection Quality Score                         │
    └──────────────────────────────────────────────────────────┘
           │
           ▼
    ┌──────────────────────────────────────────────────────────┐
    │              CORRELATION INFRASTRUCTURE                   │
    │  ├─ OpenTelemetry trace context                           │
    │  ├─ Span IDs for operations                               │
    │  └─ Cross-service correlation                             │
    └──────────────────────────────────────────────────────────┘
           │
           ▼
    ┌─────────────────────────────────────────────────────┐
    │  OUTPUT: Trace Pack                                 │
    │  ├─ events/ (schema definitions)                    │
    │  ├─ derived/ (metric calculators)                   │
    │  └─ manifests/ (run configuration)                  │
    └─────────────────────────────────────────────────────┘
```

### Phase 4: Policy Pack Integration

```
┌────────────────────────────────────────────────────────────────────────────┐
│                   PHASE 4: POLICY PACK INTEGRATION                          │
│              Input: All Packs → Output: Escalation Rules                    │
└────────────────────────────────────────────────────────────────────────────┘

    All Packs
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│              POLICY PROFILE DEFINITION                    │
│  ├─ Fast Escalator: Lower thresholds                      │
│  ├─ Slow Escalator: Higher thresholds                     │
│  ├─ Explanation-First: Prereq violation override          │
│  └─ Adaptive Bandit: Learned per-learner                  │
└──────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│              MULTI-ARMED BANDIT SETUP                     │
│  ├─ Define arms (profiles)                                │
│  ├─ Define reward function                                │
│  │   └─ Reward = learning_gain - hint_dependency_cost     │
│  ├─ Update schedule                                       │
│  └─ Safety constraints                                    │
└──────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│              ESCALATION LADDER CONFIG                     │
│  ├─ Level definitions (hint → explanation → example)      │
│  ├─ Thresholds per level                                  │
│  ├─ Safety overrides                                      │
│  └─ Trigger logging                                       │
└──────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────┐
│  OUTPUT: Policy Pack                                │
│  ├─ profiles/*.json                                 │
│  ├─ thresholds/escalation-ladder.yaml               │
│  └─ bandit/*.json                                   │
└─────────────────────────────────────────────────────┘
```

### Phase 5: Export & Integration

```
┌────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 5: EXPORT & INTEGRATION                            │
│               Input: All Packs → Output: SQL-Adapt Format                   │
└────────────────────────────────────────────────────────────────────────────┘

    All Packs
       │
       ├──▶┌──────────────────────────┐
       │   │  SQL-Adapt Export        │
       │   │  (export_sqladapt.py)    │
       │   │  ├─ textbook-manifest    │
       │   │  ├─ concept-map.json     │
       │   │  ├─ prereq-dag.json      │
       │   │  └─ chunks.json          │
       │   └──────────┬───────────────┘
       │              │
       │              ▼
       │        textbook-static/
       │
       ├──▶┌──────────────────────────┐
       │   │  Markdown Generation     │
       │   │  (markdown_generator.py) │
       │   │  ├─ concepts/*.md        │
       │   │  └─ README.md            │
       │   └──────────┬───────────────┘
       │              │
       │              ▼
       │        concepts/{docId}/*.md
       │
       └──▶┌──────────────────────────┐
           │  Validation              │
           │  ├─ JSON Schema check    │
           │  ├─ Provenance complete  │
           │  └─ Quality gates        │
           └──────────┬───────────────┘
                      │
                      ▼
            ┌─────────────────┐
            │ SQL-Adapt App   │
            │  • RAG retrieval│
            │  • Concept graph│
            │  • Event logger │
            └─────────────────┘
```

---

## Data Flow

### Complete System Flow

```
RAW PDF
  │
  │  ┌────────────────────────────────────────────────────────────────────┐
  ├──┤ DOCUMENT PACK (Phase 1)                                           │
  │  │ ├─ OCR (conditional)                                              │
  │  │ ├─ Page extraction                                                │
  │  │ ├─ Text cleaning                                                  │
  │  │ ├─ Chunking (150 words, 30 overlap)                               │
  │  │ └─ Hash embedding (24-dim)                                        │
  │  └────────────────────────────────────────────────────────────────────┘
  │                                    │
  │                                    ▼
  │                          Document Pack Artifacts
  │                          ├─ raw/source.pdf
  │                          ├─ derived/pages/*.txt
  │                          └─ index/chunks.jsonl
  │                                    │
  │  ┌────────────────────────────────────────────────────────────────────┐
  ├──┤ DOMAIN PACK (Phase 2)                                             │
  │  │ ├─ Concept mapping (concepts.yaml)                                │
  │  │ ├─ Prerequisite DAG construction                                  │
  │  │ └─ Evidence validation                                            │
  │  └────────────────────────────────────────────────────────────────────┘
  │                                    │
  │                                    ▼
  │                          Domain Pack Artifacts
  │                          ├─ concepts/concept-map.json
  │                          └─ prerequisites/prereq-dag.json
  │                                    │
  │  ┌────────────────────────────────────────────────────────────────────┐
  ├──┤ TRACE PACK (Phase 3)                                              │
  │  │ ├─ Event schema (xAPI/Caliper/PROV)                               │
  │  │ ├─ Metric calculators (HDI/CSI/APS/RQS)                           │
  │  │ └─ Correlation infrastructure                                     │
  │  └────────────────────────────────────────────────────────────────────┘
  │                                    │
  │                                    ▼
  │                          Trace Pack Infrastructure
  │                          ├─ events/*.jsonl
  │                          └─ derived/
  │                                    │
  │  ┌────────────────────────────────────────────────────────────────────┐
  ├──┤ POLICY PACK (Phase 4)                                             │
  │  │ ├─ Profile definitions                                            │
  │  │ ├─ Bandit configuration                                           │
  │  │ └─ Escalation ladder                                              │
  │  └────────────────────────────────────────────────────────────────────┘
  │                                    │
  │                                    ▼
  │                          Policy Pack Artifacts
  │                          ├─ profiles/*.json
  │                          └─ thresholds/*.yaml
  │                                    │
  │  ┌────────────────────────────────────────────────────────────────────┐
  └──┤ EXPORT & INTEGRATION (Phase 5)                                    │
     │ ├─ SQL-Adapt format export                                        │
     │ ├─ Markdown generation                                            │
     │ └─ Validation                                                     │
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
| `extract.py` | PDF text extraction | `extract_pages_fitz()`, quality detection |
| `clean.py` | Text normalization | Header/footer removal, OCR error fix |
| `chunker.py` | Word-window chunking | `chunk_text()`, deterministic IDs |
| `embedding.py` | Hash embeddings | `build_hash_embedding()`, L2 normalize |
| `concept_mapper.py` | Concept mapping | Load YAML, map chunks to concepts |
| `markdown_generator.py` | Markdown output | Generate concept files |
| `export_sqladapt.py` | SQL-Adapt export | Export with prerequisite DAG |
| `provenance.py` | PROV tracking | Entity/Activity/Agent logging |

### Data Models

| Model | Location | Purpose |
|-------|----------|---------|
| `PdfSourceDoc` | `models.py` | Source document metadata |
| `PdfIndexChunk` | `models.py` | Individual text chunk |
| `ConceptManifest` | `models.py` | Concept mappings |
| `PrereqDAG` | `models.py` | Prerequisite graph |
| `EscalationLadder` | `models.py` | Policy configuration |

### Configuration Files

| File | Purpose |
|------|---------|
| `concepts.yaml` | Concept definitions |
| `prereq-dag.yaml` | Prerequisite edges |
| `escalation-ladder.yaml` | Policy thresholds |
| `bandit-config.yaml` | Bandit parameters |

---

## Event Logging

### Event Taxonomy

| Category | Events | Standard |
|----------|--------|----------|
| Interaction | `attempt_submitted`, `hint_shown`, `escalation_decision` | xAPI |
| Pipeline | `chunk_created`, `index_built` | Custom |
| Retrieval | `retrieval_query`, `retrieval_results` | Custom |
| Generation | `explanation_generated`, `note_saved` | Custom |
| Reproducibility | `run_manifest_written`, `artifact_emitted` | PROV |

### Required Correlation Fields

```json
{
  "trace_id": "uuid",
  "run_id": "pipeline-run-id",
  "experiment_id": "eval-run-id",
  "policy_id": "policy-version",
  "learner_id_pseudonymous": "hashed-id",
  "session_id": "session-uuid",
  "code_version": "git:abc123",
  "config_hash": "sha256:xyz"
}
```

See [EVENT_LOGGING_SPEC.md](EVENT_LOGGING_SPEC.md) for complete specification.

---

## Provenance and Reproducibility

### PROV-DM Model

Every artifact tracks:
- **Entity**: The artifact itself
- **Activity**: How it was created
- **Agent**: Who/what created it

### Content-Addressed IDs

```python
# Document
doc_id = sha256(source_pdf)[:16]

# Chunk
chunk_id = f"{doc_id}:p{page}:c{index}"

# Run
run_id = sha256(config + code_version + timestamp)
```

### Run Manifest

```json
{
  "run_id": "run-123",
  "code": {
    "repository": "https://github.com/algl/pdf-helper",
    "commit": "abc123",
    "dirty": false
  },
  "environment": {
    "python": "3.10.12",
    "container": "ghcr.io/algl/pdf-helper:v1.0.0"
  },
  "inputs": [{"path": "source.pdf", "hash": "sha256:..."}],
  "outputs": [{"path": "chunks.jsonl", "hash": "sha256:..."}]
}
```

See [PROVENANCE_ARCHITECTURE.md](PROVENANCE_ARCHITECTURE.md) for complete specification.

---

## Output Generation

### File Structure

```
textbook-static/
├── textbook-manifest.json          # Schema, versions, metadata
├── concept-map.json                # Web app concept index
├── prereq-dag.json                 # Prerequisite relationships
├── chunks.json                     # Embeddings for retrieval
├── concept-manifest.json           # Internal concept metadata
└── concepts/
    ├── README.md                   # Auto-generated index
    └── {docId}/
        ├── README.md               # Doc-specific index
        └── {concept-id}.md         # Individual concept files
```

### Schema Versions

| Schema | Version | Status |
|--------|---------|--------|
| `textbook-static-v1` | 1.0.0 | Stable |
| `concept-manifest-v1` | 1.0.0 | Stable |
| `prereq-dag-v1` | 1.0.0 | Draft |
| `event-log-v1` | 1.0.0 | Draft |

### Integration with SQL-Adapt

```
algl-pdf-helper/output/                    SQL-Adapt/
    │                                            │
    ▼                                            ▼
┌──────────────────┐                    ┌──────────────────────────┐
│ concept-map.json │ ─────────────────▶ │ apps/web/public/         │
│ prereq-dag.json  │    Copied via      │   textbook-static/       │
└──────────────────┘    export script    └──────────────────────────┘
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2024 | Basic PDF → chunks pipeline |
| v2.0 | 2025 | Educational pipeline with Ollama |
| v3.0 | Feb 2026 | LLM integration with Kimi |
| v3.1 | Mar 2026 | Documentation consolidation |
| v4.0 | Mar 2026 | **Four-pack architecture** (this version) |

---

*This document consolidates architecture documentation for the Adaptive Textbook Helper.*
