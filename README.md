# Adaptive Textbook Helper

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Transform static PDFs into dynamic, inspectable knowledge substrates for interaction-driven SQL learning.**

This project treats textbooks not as static sequences of chapters, but as **versioned content substrates** that can be re-assembled into adaptive instructional artifacts—micro-hints, worked examples, explanations, and reflective notes—based on learner traces and support needs.

---

## 🚀 Quick Start

### Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with unit library support (required for most commands)
pip install -e '.[unit]'

# Or install with specific extras
pip install -e '.[unit,validation,ocr]'
```

Available extras:
- `unit` - Unit library pipeline (process, validate, inspect commands)
- `validation` - Enhanced validation tools
- `ocr` - OCR support for scanned PDFs (requires tesseract)
- `dev` - Development dependencies (pytest, etc.)

---

## 📚 Workflows

This tool supports two distinct output workflows:

### Workflow 1: Unit Library (Pedagogical Content)

Generate instructional units with L1-L4 hint levels, explanations, and worked examples.

```bash
# Process PDF into unit library
algl-pdf process ./textbook.pdf --output-dir ./output

# Validate output
algl-pdf validate ./output/

# Inspect a specific concept
algl-pdf inspect ./output/ --concept select-basic
```

**Output files:**
- `instructional_units.jsonl` - Generated instructional units (L1-L4)
- `source_spans.jsonl` - Evidence grounding spans
- `concept_graph.json` - Prerequisite relationships
- `quality_report.json` - Content quality analysis
- `export_manifest.json` - Provenance and statistics

### Workflow 2: Adaptive App Handoff (Textbook-Static Export)

Export PDF content for consumption by the adaptive web application.

```bash
# Step 1: Index the PDF
algl-pdf index ./textbook.pdf \
  --output-dir ./index_output \
  --concepts-config ./concepts.yaml

# Step 2: Export to textbook-static format
algl-pdf export ./index_output --output-dir ./textbook_static
```

**Output files:**
- `concept-map.json` - Concept index with namespaced IDs (`docId/conceptId`)
- `textbook-manifest.json` - Textbook manifest (schema v1)
- `chunks-metadata.json` - Chunk metadata per document
- `concepts/{docId}/{conceptId}.md` - Individual concept markdown files

---

## 🔧 CLI Commands

### Unit Library Commands

| Command | Description | Example |
|---------|-------------|---------|
| `process` | Process PDF into unit library | `algl-pdf process ./book.pdf -o ./out` |
| `validate` | Validate an existing unit library | `algl-pdf validate ./output/` |
| `inspect` | Inspect units for a specific concept | `algl-pdf inspect ./out/ -c select-basic` |
| `filter` | Re-run export filters on existing library | `algl-pdf filter ./out/ --level strict` |
| `diagnose` | Analyze unit library for content gaps | `algl-pdf diagnose ./output/` |
| `export-legacy` | Convert old concept-map.json to new format | `algl-pdf export-legacy ./old.json -o ./new/` |

### Textbook-Static Commands

| Command | Description | Example |
|---------|-------------|---------|
| `index` | Build PDF index to textbook-static format | `algl-pdf index ./book.pdf -o ./out` |
| `export` | Export indexed PDF to SQL-Adapt format | `algl-pdf export ./index_out -o ./export_out` |

### Process Command Options

```bash
algl-pdf process ./textbook.pdf \
  --output-dir ./output \
  --filter-level strict \
  --export-mode student_ready \
  --llm-provider kimi \
  --llm-model kimi-k2-5 \
  --use-ollama-repair \
  --ollama-model qwen3.5:9b-q8_0 \
  --skip-reinforcement \
  --skip-misconceptions \
  --min-quality-score 0.8
```

Available options:
- `--output-dir, -o` - Output directory for the unit library (required)
- `--filter-level` - Export filter level: `strict` (production-ready), `production` (validated), `development` (all content)
- `--export-mode` - Export mode: `prototype` (allows placeholders) or `student_ready` (strict, blocks weak content)
- `--llm-provider` - LLM provider: `kimi`, `openai`, or `ollama`
- `--llm-model` - LLM model to use (default: `kimi-k2-5`)
- `--use-ollama-repair/--no-ollama-repair` - Use Ollama to repair weak L3 content (default: enabled)
- `--ollama-model` - Ollama model for repair (default: `qwen3.5:9b-q8_0`)
- `--skip-reinforcement` - Skip generating reinforcement items
- `--skip-misconceptions` - Skip generating misconception units
- `--validate-sql/--no-validate-sql` - Validate SQL examples (default: enabled)
- `--min-quality-score` - Minimum quality score threshold (0.0-1.0, default: 0.8)

### Index Command Options

```bash
algl-pdf index ./textbook.pdf \
  --output-dir ./output \
  --concepts-config ./concepts.yaml \
  --chunk-words 180 \
  --overlap-words 30
```

Available options:
- `--output-dir, -o` - Output directory (required)
- `--concepts-config` - Path to concepts.yaml config file
- `--chunk-words` - Words per chunk (default: 180)
- `--overlap-words` - Overlapping words between chunks (default: 30)
- `--use-aliases` - Use stable doc aliases instead of SHA256 doc IDs
- `--ocr` - Force OCR for scanned PDFs

### Document Processing Commands

```bash
# Check PDF extraction quality
algl-pdf check-quality ./my.pdf --detailed

# Run preflight analysis
algl-pdf preflight ./my.pdf

# Extract text with specific strategy
algl-pdf extract ./my.pdf --strategy ocrmypdf
```

### Auto-Mapping Commands

```bash
# Auto-generate concept mapping draft
algl-pdf suggest-mapping ./textbook.pdf --output ./concepts.yaml

# Create review package for human validation
algl-pdf review-mapping ./textbook.pdf --output ./review-package.json

# Extract document structure
algl-pdf extract-structure ./textbook.pdf
```

### CI/Quality Gate Commands

```bash
# Evaluate processing quality
algl-pdf evaluate ./output --threshold 0.75

# Detect regressions
algl-pdf detect-regressions ./baseline ./current
```

### Server Mode

```bash
# Start HTTP server
algl-pdf serve --host 127.0.0.1 --port 7345

# Endpoint: POST /v1/index (multipart form with pdf file)
# Returns: { document, manifest, chunks, conceptMap }
```

---

## 📁 Output Files

### Unit Library Output

The `process` command produces a unit library with these files:

- `concept_ontology.json` - Canonical SQL concept definitions
- `concept_graph.json` - Prerequisite graph for mapped concepts
- `source_spans.jsonl` - Evidence grounding spans
- `instructional_units.jsonl` - Generated instructional units
- `misconception_bank.jsonl` - Error-linked remediation
- `reinforcement_bank.jsonl` - Spaced repetition items
- `quality_report.json` - Content quality analysis
- `export_manifest.json` - Provenance and statistics

### Textbook-Static Output

The `index` + `export` commands produce output for the adaptive app:

- `concept-map.json` - Concept index with namespaced IDs (`docId/conceptId`)
- `textbook-manifest.json` - Textbook manifest (schema v1)
- `chunks-metadata.json` - Chunk metadata per document
- `concepts/{docId}/{conceptId}.md` - Individual concept markdown files

---

## 🧪 CI-Tested Example

This exact command runs in CI on every commit:

```bash
algl-pdf process tests/fixtures/golden_chapter.pdf \
  --output-dir ./test_output \
  --filter-level strict
```

---

## 🧠 Adaptive Escalation

The system implements four escalation profiles:

| Profile | Strategy | Use Case |
|---------|----------|----------|
| **Fast Escalator** | Lower thresholds; prioritize time-to-clarity | Time-constrained learners |
| **Slow Escalator** | Higher thresholds; enforce productive struggle | Deep learning focus |
| **Explanation-First** | Bypass ladder for prerequisite violations | Known knowledge gaps |
| **Adaptive Bandit** | Learn optimal per-learner | General population |

### Escalation Ladder

```
Hint Level 1 (Nudge)
    ↓ (after 3 errors or 3 min)
Hint Level 2 (Directed Hint)
    ↓ (after 5 errors or 5 min)
Explanation
    ↓ (after 7 errors or 10 min)
Worked Example
```

Safety overrides:
- Repeated prerequisite failure → jump to explanation
- Learner explicit request → escalate one level

---

## 📊 Derived Metrics

The system computes four key metrics from interaction traces:

| Metric | Description | Use Case |
|--------|-------------|----------|
| **HDI** (Hint Dependency) | Help-seeking behavior patterns | Detect hint over-reliance |
| **CSI** (Cognitive Strain) | Interaction-based load proxy | Detect cognitive overload |
| **APS** (Affective Proxy) | Predicted affective state | Detect frustration/boredom |
| **RQS** (Reflection Quality) | Self-explanation quality | Assess note-taking depth |

---

## 🔬 Research Foundation

This project is grounded in established learning science:

- **Assistance Dilemma** (Koedinger et al.): Balancing help and productive struggle
- **Retrieval-Augmented Generation** (RAG): Grounded, traceable LLM outputs
- **Cognitive Load Theory** (Sweller): Managing intrinsic/extraneous load
- **Productive Failure** (Kapur): Initial struggle benefits learning
- **Self-Explanation** (Chi): Constructive engagement improves understanding
- **Retrieval Practice** (Roediger & Karpicke): Testing improves retention

---

## 📂 Repository Structure

```
.
├── README.md              # This file
├── pyproject.toml         # Package configuration
├── Makefile              # Build automation
├── src/                  # Source code (algl_pdf_helper package)
├── tests/                # Test suite
├── scripts/              # Utility scripts
├── schemas/              # JSON schemas
├── data/                 # Static data files
├── raw_pdf/              # Input PDF storage
└── docs/                 # Documentation
```

See [docs/REPO_LAYOUT.md](docs/REPO_LAYOUT.md) for detailed repository layout.

Manual utility scripts are in `scripts/manual/` (not part of main CLI).

## 📖 Documentation

| Document | Purpose |
|----------|---------|
| **[Usage Guide](docs/USAGE.md)** | Comprehensive CLI usage with examples |
| **[Project Blueprint](docs/PROJECT_BLUEPRINT.md)** | Vision, research foundation, four-pack architecture |
| **[Architecture](docs/ARCHITECTURE.md)** | Five-phase pipeline, component reference |
| **[Repository Layout](docs/REPO_LAYOUT.md)** | Canonical repo structure and organization |
| **[Quality Improvements Summary](docs/QUALITY_IMPROVEMENTS_SUMMARY.md)** | Recent quality enhancements and improvements |
| **[Week 1 Pipeline Contract](docs/pipeline_contract_week1_v15.md)** | Locked production pipeline (v1.5): default/fallback/repair paths |
| **[Fallback Decision Rules](docs/fallback_decision_rules_week1.md)** | Success/failure triggers for OCR and LLM repair |

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run CI-specific tests
make test-ci

# Run integration tests
make test-integration

# Update baselines
make update-baselines

# Run evaluation
make evaluate
```

---

## 🤝 Integration

### SQL-Adapt Integration

The textbook-static export produces files consumable by the adaptive web application:

```typescript
// Load concept map
const conceptMap = await fetch('/textbook-static/concept-map.json').then(r => r.json());

// Load individual concept content
const conceptContent = await fetch(`/textbook-static/concepts/${docId}/${conceptId}.md`).then(r => r.text());

// Check prerequisites before showing hint (from concept-graph.json in unit library)
function checkPrerequisites(conceptId: string): string[] {
  const concept = conceptMap.concepts[conceptId];
  return concept?.relatedConcepts || [];
}

// Log interaction event
function logEvent(event: AttemptSubmittedEvent) {
  event.trace_id = generateUUID();
  event.code_version = 'git:abc123';
  sendToTelemetry(event);
}
```

**Note:** The `prereq-dag.json` file referenced in earlier documentation has been replaced by the `concept-graph.json` file in the unit library workflow, or `relatedConcepts` within the `concept-map.json` entries in the textbook-static workflow.

---

## 📜 License

MIT License - see [LICENSE](LICENSE) file for details.

---

*The Adaptive Textbook Helper: Making every PDF a substrate for personalized, research-grounded learning.*
