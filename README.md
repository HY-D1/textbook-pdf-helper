# Adaptive Textbook Helper

A CLI tool that transforms SQL textbooks from PDFs into structured instructional units (L1-L4 hints, explanations, worked examples) for adaptive learning systems, using local Ollama LLMs and grounded extraction pipelines.

## Demo

```bash
# Process a PDF with Ollama repair (default)
python -m algl_pdf_helper process raw_pdf/sample.pdf --output-dir outputs/demo

# Skip LLM for fast extraction-only run
python -m algl_pdf_helper process raw_pdf/sample.pdf --output-dir outputs/demo --skip-llm

# Replay synthetic traces under different policies
python -m algl_pdf_helper replay tests/fixtures/traces --output-dir outputs/replay
```

## Features

### Implemented (v1.0)

- **PDF Processing Pipeline**: Extracts text, chunks, maps concepts, generates instructional units
- **Ollama-First Defaults**: Local LLM repair for weak L3 content (default: `qwen3.5:9b-q8_0`)
- **Canonical Artifacts**: `extraction_report.json`, `llm_interventions.json`, `concept_units.json`, `quality_report.json`
- **Educational Commands**: `edu status`, `edu generate`, `edu cost`
- **Replay System**: Replay learner traces under 3 escalation policies (fast/slow/adaptive)
- **SQL-Engage Backbone**: 50 SQL concepts, 59 prerequisite edges, 29 error subtypes
- **HintWise Adapter**: Contract for hint eligibility payloads
- **Learner Textbook Assembly**: Personal textbooks from concept units + learner events

### Planned (v2.0)

- Live HintWise HTTP integration
- Real learner trace ingestion (not synthetic)
- Online bandit policy adaptation
- Marker PDF extraction backend
- Full adaptive web app UI

## Architecture

The pipeline follows a 5-phase flow:

1. **Extraction** (pymupdf → text pages)
2. **Cleaning** (normalize, strip headers)
3. **Chunking** (word-based chunks with overlap)
4. **Concept Mapping** (SQL ontology → chunks)
5. **Unit Generation** (L1-L4 instructional units with Ollama repair)

Data flows: `PDF → chunks → concepts → units → artifacts`. The replay layer simulates policy decisions on learner traces without live integration.

```mermaid
graph LR
    A[PDF Input] --> B[Extraction]
    B --> C[Chunking]
    C --> D[Concept Mapping]
    D --> E[Unit Generation]
    E --> F[Artifacts]
    F --> G[Replay System]
    G --> H[Policy Comparison]
```

## Setup

### Prerequisites

- Python 3.10+
- Ollama server running locally (default: `http://localhost:11434`)
- Recommended model: `qwen3.5:9b-q8_0`

### Quick Start

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install with unit library support
pip install -e '.[unit]'

# Verify Ollama is available
python -m algl_pdf_helper edu status

# Process a PDF
python -m algl_pdf_helper process raw_pdf/sample.pdf --output-dir ./output
```

### Run Tests

```bash
# Core contract tests (fast)
pytest tests/test_artifact_contracts.py tests/test_day3_contracts.py tests/test_replay_system.py -q

# Full suite (includes integration tests that may timeout without Ollama)
pytest -q
```

### Configuration

| Environment Variable | Purpose | Default |
|---------------------|---------|---------|
| `OLLAMA_HOST` | Ollama server URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama model name | `qwen3.5:9b-q8_0` |
| `ALGL_LLM_PROVIDER` | Override default provider | `ollama` |

## API Reference

### CLI Commands

| Command | Description |
|---------|-------------|
| `process` | Process PDF into unit library with artifacts |
| `edu` | Educational note generation (`status`, `generate`, `cost`) |
| `replay` | Replay traces under policies for comparison |
| `index` | Build PDF index to textbook-static format |
| `validate` | Validate an existing unit library |
| `inspect` | Inspect units for a specific concept |
| `cache` | Manage Ollama repair cache |

### Key Options for `process`

| Option | Description |
|--------|-------------|
| `--output-dir, -o` | Output directory (required) |
| `--skip-llm` | Skip all LLM-based processing |
| `--llm-provider` | LLM provider: `ollama` (default), `grounded`, `kimi`, `openai` |
| `--ollama-model` | Ollama model for repair |
| `--use-ollama-repair` | Enable Ollama repair for weak L3 content (default: on) |
| `--filter-level` | `strict`, `production` (default), or `development` |
| `--export-mode` | `prototype` (default) or `student_ready` |

## Data Model / Schema

### Core Artifacts (process command)

- `extraction_report.json` - Extraction method, page counts, quality metrics
- `llm_interventions.json` - LLM repair calls, success/failure tracking
- `concept_units.json` - Generated units with provenance metadata
- `quality_report.json` - Content quality analysis, pass/fail status

### Replay Artifacts

- `replay_summary.json` / `replay_summary.csv` - Run metadata, policy metrics
- `per_learner_metrics.csv` - Per-learner HDI, CSI, APS scores
- `policy_comparison.csv` - Cross-policy comparison statistics

### Backbone Files

- `sql_engage_backbone.json` - 50 SQL concepts, prerequisite edges, practice map
- `learner_textbook.json` - Personal textbook with saved units and mastery

See [docs/schema-reference.md](docs/schema-reference.md) for detailed field documentation.

## Trade-offs & Design Decisions

**Chose:** Ollama as default LLM provider with local-first operation.
**Gave up:** Cloud LLM convenience and higher throughput.
**Why:** Enables air-gapped operation, reduces API costs, and keeps learner data local by default.

**Chose:** Synthetic trace fixtures for replay testing.
**Gave up:** Real learner data coverage.
**Why:** No live adaptive system is in production; fixtures provide deterministic policy comparison without data privacy concerns.

**Chose:** Separate backbone adapter over direct integration.
**Gave up:** Tight coupling with SQL-Engage service.
**Why:** The PDF helper operates as a standalone pipeline; explicit adapter contracts allow future HTTP integration without refactoring.

## Limitations

1. **Integration Tests Timeout**: `test_process_command_creates_units` and `test_end_to_end_pipeline` may timeout in CI without Ollama running locally with the expected model.

2. **OCR Fallback**: GLM-OCR integration attempts Ollama vision but may fail with 500 errors if models are not loaded.

3. **Unit Generation on Weak Slices**: Test PDF slices with minimal SQL content may produce 0 instructional units (expected behavior).

4. **No Live Bandit**: The replay system computes metrics deterministically; online policy adaptation is not implemented.

5. **Synthetic Data Only**: All learner traces in fixtures are synthetic; no real learner data is included.

See [docs/final-verification.md](docs/final-verification.md) for current test status.

## Next Steps

- [ ] Add HTTP client for live HintWise integration
- [ ] Implement real learner trace ingestion endpoint
- [ ] Add online bandit update loop for policy learning
- [ ] Expand SQL concept ontology beyond 50 core concepts
- [ ] Add production monitoring for Ollama repair success rates

---

*For detailed pipeline documentation, see [docs/ollama-pipeline.md](docs/ollama-pipeline.md) and [docs/replay-evaluation.md](docs/replay-evaluation.md).*
