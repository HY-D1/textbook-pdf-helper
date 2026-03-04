# Adaptive Textbook Helper - Project Blueprint

**Version:** 1.0.0  
**Status:** Draft  
**Last Updated:** 2026-03-03  

---

## Executive Summary

The **Adaptive Textbook Helper** transforms static course textbooks into dynamic, inspectable knowledge substrates that power interaction-driven SQL learning. It treats textbooks not as static sequences of chapters, but as **versioned content substrates** that can be re-assembled into adaptive instructional artifacts based on learner traces and support needs.

### Core Innovation

This project addresses the **"assistance dilemma"** in tutoring systems: balancing productive struggle with timely support. The system uses learner interaction traces to decide when to stay at hint level versus when to escalate into deeper reflective instructional units (explanations, worked examples, summaries, "My Notes").

### Target Integration

Designed to plug into the existing ecosystem:
- **Cybernetic Sabotage** - Game-based SQL learning
- **SQLBeyond Official** - Official SQL learning platform
- **HintWise** - Intelligent hint system
- **SQL-Engage Dataset** - Error/concept/feedback backbone

---

## Guiding Principles

### 1. Retrieval-First Generation

Generation quality and verifiability improve when answers are grounded in retrieved passages. All LLM generation stays **retrieval-first and traceable** (RAG paradigm).

### 2. Domain Independence Through Separation

The architecture separates concerns into four orthogonal "packs":

| Pack | Responsibility | Examples |
|------|---------------|----------|
| **Domain Pack** | Concept vocabulary, prerequisite DAG, error taxonomy | `sql.where.basic`, prerequisite edges, error subtypes |
| **Document Pack** | PDF extraction outputs, chunk index, page-level citations | Chunks with embeddings, page references |
| **Trace Pack** | Interaction events and derived features | Attempt events, hint requests, escalation decisions |
| **Policy Pack** | Escalation rules and learned policy parameters | Bandit arms, threshold configurations |

### 3. Complete Reproducibility

Every aspect of the system is designed for **publishable evaluation**:
- Complete event logging for debugging
- Counterfactual replay capabilities
- Versioned artifacts with content addressing
- Deterministic processing pipelines

---

## System Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ADAPTIVE TEXTBOOK HELPER PIPELINE                         │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
    │   RAW PDF        │────▶│  PHASE 1         │────▶│  PHASE 2         │
    │   Textbook       │     │  Document Pack   │     │  Knowledge       │
    │                  │     │  Extraction      │     │  Substrate       │
    └──────────────────┘     └──────────────────┘     └────────┬─────────┘
                                                               │
    ┌──────────────────┐     ┌──────────────────┐              │
    │   ADAPTIVE       │◀────│  PHASE 3         │◀─────────────┘
    │   OUTPUT         │     │  Domain Pack     │
    │   (SQL-Adapt)    │     │  Concept Mapping │
    └──────────────────┘     └────────┬─────────┘
                                      │
    ┌──────────────────┐              │
    │   LEARNER        │──────────────┘
    │   INTERACTIONS   │     Trace Pack + Policy Pack
    └──────────────────┘
```

---

## The Four Packs

### Document Pack (PDF → Usable Knowledge)

Transforms raw PDFs (including scanned) into structured, auditable artifacts:

```
document-pack/
├── raw/
│   └── {doc_alias}/
│       └── source.pdf                    # Immutable original
├── derived/
│   └── {doc_alias}/
│       ├── ocr.pdf                       # OCR output (if applied)
│       ├── pages/
│       │   └── {page}.txt                # Per-page extraction
│       └── layout.json                   # Headings, blocks, tables
└── index/
    └── {doc_alias}/
        ├── chunks.jsonl                  # Chunked content
        └── index.*                       # Vector/semantic index
```

**Key Requirements:**
- Content-addressed artifacts (SHA256-based IDs)
- Per-page extraction with confidence scores
- Page-level citations preserved throughout
- Deterministic chunking (same input + config → same chunks)

### Domain Pack (Knowledge Organization)

Structures educational content as a traversable knowledge graph:

```
domain-pack/
├── concepts/
│   └── concept-map.json                  # Concept nodes and metadata
├── prerequisites/
│   └── prereq-dag.json                   # Directed edges: prereq → concept
├── errors/
│   └── error-taxonomy.json               # Error subtypes → concepts
└── rubrics/
    └── assessment-rubrics.json           # Evaluation criteria
```

**Key Requirements:**
- Canonical concept IDs (e.g., `sql.where.basic`, `sql.groupby.agg`)
- Prerequisite DAG explicitly modeled (not flat coverage)
- Versioned and auditable (DAG changes affect mastery propagation)
- Evidence pointers to chunks/pages for every node/edge

### Trace Pack (Interaction Logging)

Captures complete learner interaction history:

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

**Key Requirements:**
- xAPI/Caliper/PROV-aligned event schemas
- Correlation IDs across all components (OpenTelemetry)
- Non-negotiable fields: `trace_id`, `run_id`, `policy_id`, `code_version`

### Policy Pack (Adaptive Orchestration)

Controls escalation and support delivery:

```
policy-pack/
├── profiles/
│   ├── fast-escalator.json               # Lower thresholds
│   ├── slow-escalator.json               # Higher thresholds
│   ├── explanation-first.json            # Bypass ladder
│   └── adaptive-bandit.json              # Learned policy
├── thresholds/
│   └── escalation-ladder.yaml            # Formal trigger definitions
└── bandit/
    └── arm-configs.json                  # Multi-armed bandit parameters
```

**Escalation Profiles:**

| Profile | Strategy | Use Case |
|---------|----------|----------|
| **Fast Escalator** | Lower thresholds; prioritize time-to-clarity | Learners with time constraints |
| **Slow Escalator** | Higher thresholds; enforce productive struggle | Learners needing deeper engagement |
| **Adaptive Bandit** | Dynamic thresholds based on recovery patterns | General population optimization |
| **Explanation-First** | Bypass ladder for prerequisite violations | Known knowledge gaps |

---

## Artifact Specification

### Content-Addressed IDs

All artifacts use content-based addressing for reproducibility:

```python
# Document ID
doc_id = sha256(source_pdf_bytes)[:16]
# or: stable alias + version (e.g., "sql-textbook@v1.2.0")

# Chunk ID
chunk_id = f"{doc_id}:p{page}:c{index}"
# Example: "sql-textbook:p45:c1"

# Run ID
run_id = sha256(config_json + code_version + timestamp)
```

### Required Metadata per Artifact

Every generated artifact must include:

```json
{
  "artifactType": "concept-map|chunk-index|event-log|...",
  "artifactId": "sha256-hash",
  "createdAt": "2024-01-15T10:30:00Z",
  "provenance": {
    "codeVersion": "git:abc123",
    "configHash": "sha256:def456",
    "inputArtifacts": ["artifact-id-1", "artifact-id-2"],
    "runId": "run-xyz789"
  }
}
```

---

## Event Logging Architecture

### Event Taxonomy

Structured event families with strict schemas:

#### Interaction Events

| Event | Trigger | Required Fields |
|-------|---------|-----------------|
| `attempt_submitted` | Learner submits solution | `problem_id`, `code`, `timestamp` |
| `attempt_result` | Auto-grading complete | `correct`, `error_subtype`, `concept_ids` |
| `error_classified` | Error mapped to taxonomy | `error_subtype`, `mapped_concepts` |
| `hint_requested` | Learner asks for hint | `hint_level`, `trigger_reason` |
| `hint_shown` | Hint displayed | `content_id`, `source_chunk_ids` |
| `escalation_decision` | Support level changed | `trigger`, `thresholds`, `profile_id` |
| `explanation_generated` | LLM produces explanation | `prompt_template_id`, `retrieved_chunks` |
| `explanation_shown` | Explanation displayed | `provenance`, `citation_links` |
| `note_saved` | Learner saves note | `note_type`, `content_hash` |
| `problem_completed` | Problem finished | `time_spent`, `hint_count`, `escalation_count` |

#### Pipeline Events

| Event | Trigger | Context |
|-------|---------|---------|
| `pdf_ingest_started` | PDF processing begins | `doc_id`, `ocr_required` |
| `page_text_extracted` | Single page processed | `page`, `quality_score`, `flags` |
| `chunk_created` | Chunk generated | `chunk_id`, `boundaries`, `token_count` |
| `concept_link_suggested` | AI suggests mapping | `concept_id`, `chunk_id`, `confidence` |
| `concept_link_confirmed` | Human validates mapping | `confirmed_by`, `validation_method` |

### Correlation Fields (Non-Negotiable)

Every log entry must include:

```json
{
  "trace_id": "uuid-for-distributed-trace",
  "span_id": "uuid-for-operation-span",
  "run_id": "pipeline-run-identifier",
  "experiment_id": "evaluation-run-identifier",
  "policy_id": "policy-version-identifier",
  "learner_id_pseudonymous": "hashed-learner-id",
  "session_id": "learning-session-uuid",
  "problem_id": "problem-identifier",
  "attempt_id": "attempt-sequence-number",
  "doc_id": "source-document",
  "chunk_ids": ["relevant-chunks"],
  "concept_ids": ["relevant-concepts"],
  "code_version": "git:abc123",
  "config_hash": "sha256:config",
  "data_hash": "sha256:input-data",
  "llm_model_id": "model-identifier",
  "prompt_template_id": "template-version",
  "temperature": 0.7,
  "max_tokens": 2048
}
```

---

## Reproducibility Stack

### 1. Versioned Pipelines

```yaml
# pipeline-lock.yaml
version: "1.0.0"
code:
  repository: "https://github.com/algl/pdf-helper"
  commit: "abc123def456"
  dirty: false
environment:
  python: "3.10.12"
  dependencies_hash: "sha256:xyz789"
  container_image: "ghcr.io/algl/pdf-helper:v1.0.0"
config:
  chunk_size: 150
  overlap: 30
  embedding_model: "hash-embedding-v1"
  ocr_engine: "tesseract-v5.3.0"
data:
  inputs:
    - path: "raw/sql-textbook/source.pdf"
      hash: "sha256:book123"
  outputs:
    - path: "index/sql-textbook/chunks.jsonl"
      hash: "sha256:chunks456"
```

### 2. Environment Capture

Container-based reproduction:

```dockerfile
FROM python:3.10-slim
COPY requirements.lock .
RUN pip install -r requirements.lock
COPY . .
RUN pip install -e .
ENTRYPOINT ["algl-pdf"]
```

### 3. Experiment Tracking

```
experiments/
├── {experiment_id}/
│   ├── manifest.json           # Config, versions, seeds
│   ├── events/                 # Raw interaction logs
│   ├── metrics/                # Computed metrics
│   ├── artifacts/              # Generated content
│   └── provenance/             # PROV-DM graph
```

### 4. Counterfactual Replay

The system supports replaying learner traces against different policies:

```python
# Replay invariants
- Learner actions remain fixed
- Only system decisions vary
- Compute comparable metrics

# Replay outputs
- explanations_shown_total
- avg_escalation_depth
- simulated_HDI, simulated_CSI
- concept_coverage_score
```

---

## Derived Metrics

### Hint Dependency Index (HDI)

Measures help-seeking behavior patterns.

```
HDI = (hint_requests / attempts) × (time_with_hints / total_time)
```

### Cognitive Strain Index (CSI)

Interaction-based proxy for cognitive load.

```
CSI = α(backspaces) + β(deletions) + γ(pause_time) + δ(error_rate)
```

**Note:** CSI is an interaction-based indicator, not a direct cognitive measurement.

### Affective Proxy Score (APS)

Predicts affective states from UI interactions.

```
APS = f(click_pattern, dwell_time, rapid_switching, repeated_errors)
```

Validated against observable outcomes (quitting, rapid switching).

### Reflection Quality Score (RQS)

Assesses quality of learner-generated notes.

```
RQS = g(note_length, concept_references, self_explanation_depth, edit_frequency)
```

Aligned with ICAP framework (constructive engagement).

---

## Integration with SQL-Adapt

### Data Flow

```
┌──────────────────────┐         ┌──────────────────────┐
│  Adaptive Textbook   │         │   SQL-Adapt Web      │
│  Helper              │         │   Application        │
│                      │         │                      │
│  ┌────────────────┐  │         │  ┌────────────────┐  │
│  │ Document Pack  │──┼────────▶│  │ RAG Retrieval  │  │
│  └────────────────┘  │         │  └────────────────┘  │
│  ┌────────────────┐  │         │  ┌────────────────┐  │
│  │ Domain Pack    │──┼────────▶│  │ Concept Graph  │  │
│  └────────────────┘  │         │  └────────────────┘  │
│  ┌────────────────┐  │         │  ┌────────────────┐  │
│  │ Trace Pack     │◀─┼────────│  │ Event Logger   │  │
│  └────────────────┘  │         │  └────────────────┘  │
│  ┌────────────────┐  │         │  ┌────────────────┐  │
│  │ Policy Pack    │◀─┼────────│  │ Policy Engine  │  │
│  └────────────────┘  │         │  └────────────────┘  │
└──────────────────────┘         └──────────────────────┘
```

### Export Format

The Document Pack exports to SQL-Adapt as:

```
textbook-static/
├── textbook-manifest.json      # Metadata and versions
├── concept-map.json            # Web app concept index
├── chunks.json                 # Embeddings for retrieval
├── prereq-dag.json             # Prerequisite relationships
└── concepts/                   # Readable content
    └── {docId}/
        └── {concept-id}.md
```

---

## Implementation Checklist

### Working Prototype Deliverables

- [ ] **Document Pack Pipeline**
  - PDF → OCR → pages → chunks → index
  - Deterministic build with hash-based IDs
  - Export to SQL-Adapt retrieval contract

- [ ] **Domain Pack Structure**
  - Concept vocabulary with canonical IDs
  - Prerequisite DAG with version control
  - Error taxonomy mappings

- [ ] **Trace Pack Infrastructure**
  - xAPI/Caliper-aligned event schemas
  - OpenTelemetry correlation
  - HDI/CSI/APS/RQS computation

- [ ] **Policy Pack Engine**
  - Static profiles + adaptive bandit
  - Explicit reward functions
  - Safety constraints (prereq override)

### Experimental Evidence Deliverables

- [ ] **Evaluation Protocol**
  - Pre-registered baselines and metrics
  - Exclusion rules and datasets

- [ ] **Replay Study Results**
  - Counterfactual outcomes for 3+ policies
  - Doubly robust estimators

- [ ] **Learning Consolidation**
  - Delayed micro-check outcomes
  - Spacing and retrieval practice metrics

- [ ] **Self-Explanation Analysis**
  - RQS distributions
  - Correlation with learning outcomes

---

## Risk Controls

| Risk | Mitigation |
|------|------------|
| **PDF Extraction Brittleness** | Log OCR coverage; fallback behaviors; quality gates |
| **Concept Map Drift** | Version DAG changes; audit trail for edits |
| **Policy Evaluation Validity** | Log propensities; use doubly robust estimators |
| **Affect/Cognitive Proxies** | Treat as interaction indicators; validate against outcomes |

---

## Research Foundation

This design is grounded in established learning science:

- **Assistance Dilemma** (Koedinger et al.): Balancing help and struggle
- **Cognitive Load Theory** (Sweller): Managing intrinsic/extraneous load
- **Productive Failure** (Kapur): Initial struggle benefits
- **Self-Explanation** (Chi): Constructive engagement improves learning
- **Retrieval Practice** (Roediger & Karpicke): Testing improves retention
- **Distributed Practice** (Cepeda et al.): Spacing improves learning

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0.0 | 2026-03-03 | Initial blueprint document |

---

*This document defines the architectural vision for the Adaptive Textbook Helper project.*
