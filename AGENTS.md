# Adaptive Textbook Helper - AI Agent Guide

**Version:** 2.0.0  
**Last Updated:** 2026-03-03  
**Status:** Current

---

## Project Overview

The **Adaptive Textbook Helper** is a research-grade Python CLI tool and HTTP service that transforms PDFs into structured knowledge substrates for interaction-driven SQL learning. It treats textbooks not as static content, but as **versioned substrates** that can be re-assembled into adaptive instructional artifacts based on learner traces.

### Core Philosophy

1. **Four-Pack Separation**: Domain-independent architecture through Document, Domain, Trace, and Policy packs
2. **Retrieval-First Generation**: All LLM outputs are grounded in retrieved chunks with full provenance
3. **Complete Observability**: Every action is logged for debugging, replay, and evaluation
4. **Reproducibility**: Deterministic processing with content-addressed artifacts

---

## Technology Stack

- **Language**: Python 3.10+
- **Build System**: setuptools (pyproject.toml)
- **CLI Framework**: Typer >= 0.12
- **Data Validation**: Pydantic v2 >= 2.6
- **PDF Processing**: PyMuPDF >= 1.23
- **Embeddings**: Hash-based 24-dim (deterministic)

### Optional Dependencies

| Feature | Package | Install |
|---------|---------|---------|
| OCR | `ocrmypdf>=16.0` | `pip install -e '.[ocr]'` |
| HTTP Server | `fastapi>=0.110` | `pip install -e '.[server]'` |
| Testing | `pytest>=8.0` | `pip install -e '.[test]'` |

### System Dependencies (OCR)

- `tesseract` - OCR engine
- `ghostscript` - PDF processing

macOS: `brew install tesseract ghostscript`  
Ubuntu: `sudo apt-get install tesseract-ocr ghostscript`

---

## The Four Packs

### Document Pack

**Purpose:** Transform PDFs into content-addressed, retrievable artifacts.

**Key Files:**
- `extract.py` - PDF extraction and OCR
- `clean.py` - Text normalization
- `chunker.py` - Deterministic word-window chunking
- `embedding.py` - Hash-based 24-dim embeddings

**Output Structure:**
```
document-pack/
├── raw/{docId}/source.pdf          # SHA256-addressed
├── derived/{docId}/pages/{n}.txt   # Per-page extraction
└── index/{docId}/
    ├── chunks.jsonl                # Chunk content
    └── embeddings.jsonl            # Hash vectors
```

**Key Requirements:**
- Content-addressed IDs (SHA256)
- Deterministic chunking (same input + config → same chunks)
- Page-level citations preserved
- Quality scores logged per page

### Domain Pack

**Purpose:** Structure content as inspectable, editable knowledge graphs.

**Key Files:**
- `concept_mapper.py` - Map chunks to concepts
- `prereq_validator.py` - Prerequisite DAG validation
- `markdown_generator.py` - Generate concept markdown

**Output Structure:**
```
domain-pack/
├── concepts/
│   ├── concept-map.json            # Concept nodes
│   └── {concept-id}.md             # Concept content
└── prerequisites/
    └── prereq-dag.json             # DAG edges
```

**Key Requirements:**
- Canonical concept IDs (e.g., `sql.select.basic`)
- Explicit prerequisite edges (not flat coverage)
- Versioned DAG changes
- Evidence pointers for every node/edge

### Trace Pack

**Purpose:** Capture complete interaction history for debugging and evaluation.

**Key Files:**
- `event_logger.py` - xAPI/Caliper event logging
- `metric_engines.py` - HDI, CSI, APS, RQS calculators
- `telemetry.py` - OpenTelemetry integration

**Output Structure:**
```
trace-pack/
├── events/                         # Event schemas
├── derived/                        # Metric calculators
└── manifests/                      # Run manifests
```

**Key Requirements:**
- xAPI/Caliper/PROV-aligned schemas
- OpenTelemetry correlation IDs
- Non-negotiable fields in every event

### Policy Pack

**Purpose:** Control escalation and adaptive support delivery.

**Key Files:**
- `policy_engine.py` - Escalation decision logic
- `bandit_learner.py` - Multi-armed bandit implementation
- `threshold_manager.py` - Threshold configuration

**Output Structure:**
```
policy-pack/
├── profiles/                       # Escalation profiles
├── thresholds/                     # Ladder configuration
└── bandit/                         # Bandit parameters
```

**Key Requirements:**
- Four profiles: fast, slow, explanation-first, adaptive
- Explicit reward functions
- Safety constraints (prereq override)
- Logged propensities for off-policy evaluation

---

## Project Structure

```
.
├── pyproject.toml              # Package configuration
├── README.md                   # User-facing documentation
├── AGENTS.md                   # This file
├── docs/
│   ├── PROJECT_BLUEPRINT.md    # Architectural vision
│   ├── ARCHITECTURE.md         # System architecture
│   ├── OUTPUT_SPEC.md          # Output formats
│   ├── EVENT_LOGGING_SPEC.md   # Event taxonomy
│   └── PROVENANCE_ARCHITECTURE.md  # PROV-DM spec
├── src/algl_pdf_helper/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                  # CLI entry point
│   ├── server.py               # FastAPI server
│   │
│   ├── Document Pack
│   │   ├── extract.py
│   │   ├── clean.py
│   │   ├── chunker.py
│   │   └── embedding.py
│   │
│   ├── Domain Pack
│   │   ├── concept_mapper.py
│   │   ├── prereq_validator.py
│   │   └── markdown_generator.py
│   │
│   ├── Trace Pack
│   │   ├── event_logger.py
│   │   ├── metric_engines.py
│   │   └── telemetry.py
│   │
│   ├── Policy Pack
│   │   ├── policy_engine.py
│   │   ├── bandit_learner.py
│   │   └── threshold_manager.py
│   │
│   ├── Shared
│   │   ├── models.py           # Pydantic models
│   │   ├── validators.py       # Validation logic
│   │   ├── quality_gates.py    # Quality checks
│   │   └── provenance.py       # PROV tracking
│   │
│   └── Export
│       ├── export_sqladapt.py
│       └── educational_pipeline.py
│
└── tests/
    ├── test_chunker.py
    ├── test_embedding_parity.py
    ├── test_concept_mapper.py
    ├── test_event_logging.py
    ├── test_provenance.py
    └── test_integration_ci.py
```

---

## Module Responsibilities

### Document Pack Modules

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `extract.py` | PDF extraction | `extract_pages_fitz()`, `check_extraction_quality()` |
| `clean.py` | Text normalization | `remove_headers()`, `fix_ocr_errors()` |
| `chunker.py` | Word-window chunking | `chunk_text()`, `generate_chunk_id()` |
| `embedding.py` | Hash embeddings | `build_hash_embedding()`, `l2_normalize()` |

### Domain Pack Modules

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `concept_mapper.py` | Concept mapping | `load_concepts()`, `map_chunks_to_concepts()` |
| `prereq_validator.py` | DAG validation | `validate_dag()`, `detect_cycles()` |
| `markdown_generator.py` | Markdown output | `generate_concept_md()`, `create_readme()` |

### Trace Pack Modules

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `event_logger.py` | Event logging | `log_event()`, `validate_event()` |
| `metric_engines.py` | Metric calculation | `calculate_hdi()`, `calculate_csi()` |
| `telemetry.py` | OpenTelemetry | `start_span()`, `set_attribute()` |

### Policy Pack Modules

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `policy_engine.py` | Escalation logic | `should_escalate()`, `get_current_level()` |
| `bandit_learner.py` | Bandit algorithm | `select_arm()`, `update_rewards()` |
| `threshold_manager.py` | Threshold config | `load_thresholds()`, `apply_profile()` |

---

## Code Organization

### Data Models (Pydantic)

```python
# Document Pack
class PdfSourceDoc(BaseModel):
    doc_id: str  # SHA256 or alias
    filename: str
    page_count: int
    source_hash: str

class PdfIndexChunk(BaseModel):
    chunk_id: str  # {docId}:p{page}:c{index}
    doc_id: str
    page: int
    text: str
    embedding: list[float]

# Domain Pack
class ConceptNode(BaseModel):
    id: str
    canonical_name: str  # sql.select.basic
    title: str
    definition: str
    prerequisites: list[str]
    teaches: list[str]
    evidence: ConceptEvidence

class PrereqEdge(BaseModel):
    from_: str = Field(alias="from")
    to: str
    type: str = "prerequisite"
    confidence: float
    validated: bool

# Trace Pack
class AttemptSubmittedEvent(BaseModel):
    event_type: Literal["attempt_submitted"]
    timestamp: datetime
    trace_id: UUID
    payload: AttemptPayload

class HDIMetric(BaseModel):
    learner_id: str
    window_start: datetime
    hint_requests: int
    attempts: int
    hdi_score: float

# Policy Pack
class EscalationLadder(BaseModel):
    levels: list[EscalationLevel]
    safety_overrides: list[SafetyOverride]
    profiles: dict[str, ProfileConfig]

class BanditConfig(BaseModel):
    arms: list[str]
    reward_function: str
    update_schedule: str
```

---

## Build and Development Commands

### Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with all dependencies
pip install -e '.[server,ocr,test]'

# Install dev tools
pip install ruff mypy
```

### Makefile Targets

```bash
make help              # Show available targets
make install           # Install package
make test              # Run all tests
make test-ci           # Run CI tests
make lint              # Run ruff, mypy
make format            # Format with ruff
make clean             # Clean generated files
```

### CLI Usage

```bash
# Document Pack
algl-pdf index ./my.pdf --out ./output --use-aliases
algl-pdf check-quality ./my.pdf --detailed

# Domain Pack
algl-pdf suggest-mapping ./book.pdf --output ./concepts.yaml
algl-pdf review-mapping ./book.pdf --output ./review.json

# Trace Pack (conceptual)
algl-pdf validate-events ./events.jsonl
algl-pdf compute-metrics ./events/ --output ./metrics/

# Policy Pack (conceptual)
algl-pdf validate-policy ./escalation-ladder.yaml
algl-pdf replay ./logs/ --policy slow-escalator
```

---

## Code Style Guidelines

### General

- Use `from __future__ import annotations` for forward references
- Type hints required for all function signatures
- Pydantic v2 models for all data structures
- Docstrings for public functions (Google style preferred)

### Event Logging

```python
# Always include correlation fields
def log_attempt_submitted(
    learner_id: str,
    problem_id: str,
    code: str,
) -> None:
    event = {
        "event_type": "attempt_submitted",
        "timestamp": datetime.utcnow().isoformat(),
        "trace_id": generate_trace_id(),
        "run_id": get_current_run_id(),
        "policy_id": get_current_policy_id(),
        "code_version": get_git_commit(),
        "config_hash": get_config_hash(),
        "payload": {
            "learner_id": hash_learner_id(learner_id),
            "problem_id": problem_id,
            "code": code,
        }
    }
    logger.info(json.dumps(event))
```

### Provenance Tracking

```python
# Track artifact provenance
def create_chunk(
    page_text: str,
    page_num: int,
    chunk_index: int,
) -> PdfIndexChunk:
    chunk = PdfIndexChunk(
        chunk_id=f"{doc_id}:p{page_num}:c{chunk_index}",
        text=extract_chunk_text(page_text, chunk_index),
        embedding=compute_embedding(page_text),
        provenance={
            "extraction_method": "pymupdf",
            "source_page": page_num,
            "generation_activity": get_current_activity_id(),
        }
    )
    log_artifact_emitted(chunk)
    return chunk
```

### Error Handling

```python
# Use specific exceptions with cleanup
def process_pdf(pdf_path: Path) -> DocumentPack:
    temp_dir = tempfile.mkdtemp(prefix="algl_pdf_")
    try:
        # Process PDF
        return DocumentPack(...)
    except OCRFailedError as e:
        logger.error(f"OCR failed: {e}")
        raise
    finally:
        # Always cleanup
        if temp_dir.startswith(tempfile.gettempdir() + "/algl_pdf_"):
            shutil.rmtree(temp_dir)
```

---

## Testing Strategy

### Test Categories

| Test File | Purpose | Pack |
|-----------|---------|------|
| `test_chunker.py` | Chunking determinism | Document |
| `test_embedding_parity.py` | Embedding consistency | Document |
| `test_concept_mapper.py` | Concept mapping | Domain |
| `test_prereq_dag.py` | DAG validation | Domain |
| `test_event_logging.py` | Event schema validation | Trace |
| `test_metric_engines.py` | HDI/CSI calculation | Trace |
| `test_provenance.py` | PROV completeness | All |
| `test_integration_ci.py` | Golden fixture | All |

### Running Tests

```bash
# All tests
pytest

# Specific pack
pytest tests/test_concept*.py

# With coverage
pytest --cov=src/algl_pdf_helper

# CI mode
make test-ci
```

### Golden Fixture Testing

```bash
# Update baseline
make update-baselines

# Check for regressions
algl-pdf detect-regressions ./baseline ./current
```

---

## Output Format Specification

### Schema Versions

| Schema | Version | Status |
|--------|---------|--------|
| `textbook-static-v2` | 2.0.0 | Draft |
| `concept-manifest-v1` | 1.0.0 | Stable |
| `prereq-dag-v1` | 1.0.0 | Draft |
| `event-log-v1` | 1.0.0 | Draft |

### Document ID Formats

```python
# Content-addressed (default)
doc_id = f"doc-{sha256(pdf_bytes)[:12]}"

# Stable alias (with --use-aliases)
doc_id = "sql-textbook"  # From filename mapping

# Chunk ID pattern
chunk_id = f"{doc_id}:p{page}:c{index}"
```

---

## Security Considerations

### Data Handling

- Temp files use `tempfile.mkdtemp(prefix="algl_pdf_")`
- Cleanup only removes files matching `algl_pdf_*` pattern
- Learner IDs are pseudonymized (SHA256 hashed)
- No persistent storage of uploaded PDFs

### Event Logging

- Never log raw learner identifiers
- Hash sensitive fields: `learner_id_pseudonymous`
- Log code versions and config hashes for audit
- Include trace IDs for correlation without exposing identity

---

## Documentation Maintenance

### When to Update

| Change | Documents to Update |
|--------|---------------------|
| New pack added | PROJECT_BLUEPRINT.md, ARCHITECTURE.md |
| Schema changes | OUTPUT_SPEC.md, Migration guide |
| New event types | EVENT_LOGGING_SPEC.md |
| New CLI commands | README.md, AGENTS.md |
| Architecture changes | All core docs |

### Version Alignment

Keep these versions aligned:
- `PROJECT_BLUEPRINT.md` - Vision version
- `ARCHITECTURE.md` - Architecture version
- `OUTPUT_SPEC.md` - Schema version
- `README.md` / `AGENTS.md` - Project version

---

## Resources

### Documentation

- [Project Blueprint](docs/PROJECT_BLUEPRINT.md) - Vision and research foundation
- [Architecture](docs/ARCHITECTURE.md) - Five-phase pipeline
- [Output Spec](docs/OUTPUT_SPEC.md) - Four-pack formats
- [Event Logging](docs/EVENT_LOGGING_SPEC.md) - Event taxonomy
- [Provenance](docs/PROVENANCE_ARCHITECTURE.md) - PROV-DM spec

### External References

- xAPI Specification: https://xapi.com/
- Caliper Specification: https://www.imsglobal.org/caliper
- PROV-DM Specification: https://www.w3.org/TR/prov-dm/
- OpenTelemetry: https://opentelemetry.io/

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

*This document is maintained as part of the Adaptive Textbook Helper project.*
