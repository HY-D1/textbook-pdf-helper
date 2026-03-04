# Adaptive Textbook Helper

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Schema: v2](https://img.shields.io/badge/schema-v2.0.0-green.svg)](docs/OUTPUT_SPEC.md)

> **Transform static PDFs into dynamic, inspectable knowledge substrates for interaction-driven SQL learning.**

This project treats textbooks not as static sequences of chapters, but as **versioned content substrates** that can be re-assembled into adaptive instructional artifacts—micro-hints, worked examples, explanations, and reflective notes—based on learner traces and support needs.

## 🎯 What It Does

The Adaptive Textbook Helper addresses the **"assistance dilemma"** in tutoring systems: when to provide hints versus when to escalate to deeper explanations. It combines:

- **📄 Document Pack:** PDF → clean chunks with hash embeddings
- **🗺️ Domain Pack:** Concept maps with prerequisite DAGs
- **📊 Trace Pack:** Complete event logging (xAPI/Caliper aligned)
- **⚙️ Policy Pack:** Adaptive escalation rules and bandit policies

### The Four Packs

| Pack | Purpose | Key Output |
|------|---------|------------|
| **Document** | PDF extraction and chunking | `chunks.json` with page-level citations |
| **Domain** | Knowledge graph construction | `concept-map.json` + `prereq-dag.json` |
| **Trace** | Interaction logging | HDI, CSI, APS, RQS metrics |
| **Policy** | Escalation control | `escalation-ladder.yaml` |

---

## 🚀 Quick Start

### Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with all features
pip install -e '.[server,ocr,test]'

# Install system OCR dependencies (macOS)
brew install tesseract ghostscript

# Install system OCR dependencies (Ubuntu)
sudo apt-get install tesseract-ocr ghostscript
```

### Process Your First PDF

```bash
# Basic processing
algl-pdf index ./SQL_Textbook.pdf --out ./output --use-aliases

# With OCR for scanned PDFs
algl-pdf index ./scanned_book.pdf --out ./output --ocr --use-aliases

# Generate all four packs
algl-pdf index ./textbook.pdf --out ./output \
  --use-aliases \
  --with-domain-pack \
  --with-policy-pack
```

### Export to SQL-Adapt

```bash
# Export processed PDF
algl-pdf export ./output/sql-textbook

# Full educational pipeline with LLM
algl-pdf export-edu ./textbook.pdf \
  --output-dir ./output \
  --llm-provider kimi
```

### Interactive Processing

```bash
# Menu-driven interface
./start.sh
```

Features:
- 📄 Process single or all PDFs
- 🔄 Re-process existing PDFs
- 📋 List PDFs with status
- 📤 Export to SQL-Adapt
- ⚙️ Configure OCR, chunk size, aliases

---

## 📁 Output Structure

```
output/
├── document-pack/              # Document artifacts
│   ├── raw/
│   │   └── sql-textbook/
│   │       └── source.pdf
│   ├── derived/
│   │   └── sql-textbook/
│   │       └── pages/
│   └── index/
│       └── sql-textbook/
│           ├── chunks.jsonl
│           └── index.faiss
│
├── domain-pack/                # Knowledge graph
│   ├── concepts/
│   │   ├── concept-map.json
│   │   └── select-basic.md
│   └── prerequisites/
│       └── prereq-dag.json
│
├── trace-pack/                 # Event infrastructure
│   ├── events/
│   │   └── attempt_submitted.schema.json
│   └── derived/
│       ├── hdi-calculator.json
│       └── csi-calculator.json
│
├── policy-pack/                # Escalation rules
│   ├── profiles/
│   │   ├── fast-escalator.json
│   │   └── slow-escalator.json
│   └── thresholds/
│       └── escalation-ladder.yaml
│
└── textbook-static/            # SQL-Adapt export
    ├── textbook-manifest.json
    ├── concept-map.json
    ├── prereq-dag.json
    └── concepts/
        └── sql-textbook/
            └── select-basic.md
```

---

## 🔧 CLI Commands

### Document Pack

```bash
# Check PDF extraction quality
algl-pdf check-quality ./my.pdf --detailed

# Run preflight analysis
algl-pdf preflight ./my.pdf

# Extract text with specific strategy
algl-pdf extract ./my.pdf --strategy ocrmypdf
```

### Domain Pack

```bash
# Auto-generate concept mapping draft
algl-pdf suggest-mapping ./textbook.pdf --output ./concepts.yaml

# Create review package for human validation
algl-pdf review-mapping ./textbook.pdf --output ./review-package.json

# Extract document structure
algl-pdf extract-structure ./textbook.pdf
```

### Trace Pack

```bash
# Evaluate processing quality
algl-pdf evaluate ./output --threshold 0.75

# Detect regressions
algl-pdf detect-regressions ./baseline ./current
```

### Policy Pack

```bash
# Validate escalation ladder
algl-pdf validate-policy ./escalation-ladder.yaml

# Run counterfactual replay
algl-pdf replay ./logs/session.json --policy slow-escalator
```

### Server Mode

```bash
# Start HTTP server
algl-pdf serve --host 127.0.0.1 --port 7345

# Endpoint: POST /v1/index (multipart form with pdf file)
# Returns: { document, manifest, chunks, conceptMap }
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

## 📖 Documentation

| Document | Purpose |
|----------|---------|
| **[Project Blueprint](docs/PROJECT_BLUEPRINT.md)** | Vision, research foundation, four-pack architecture |
| **[Architecture](docs/ARCHITECTURE.md)** | Five-phase pipeline, component reference |
| **[Output Spec](docs/OUTPUT_SPEC.md)** | JSON schemas, four-pack formats |
| **[Event Logging](docs/EVENT_LOGGING_SPEC.md)** | xAPI/Caliper event taxonomy |
| **[Provenance](docs/PROVENANCE_ARCHITECTURE.md)** | PROV-DM reproducibility |
| **[AI Agent Guide](AGENTS.md)** | Development guidelines |

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

```typescript
// Load concept map with prerequisites
const conceptMap = await fetch('/textbook-static/concept-map.json').then(r => r.json());
const prereqDAG = await fetch('/textbook-static/prereq-dag.json').then(r => r.json());

// Check prerequisites before showing hint
function checkPrerequisites(conceptId: string): string[] {
  const dag = prereqDAG;
  return dag.edges
    .filter(e => e.to === conceptId)
    .map(e => e.from);
}

// Log interaction event
function logEvent(event: AttemptSubmittedEvent) {
  event.trace_id = generateUUID();
  event.code_version = 'git:abc123';
  sendToTelemetry(event);
}
```

---

## 📜 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

This project integrates with:
- **SQL-Adapt** - Adaptive SQL learning platform
- **Cybernetic Sabotage** - Game-based SQL practice
- **SQLBeyond Official** - Official SQL curriculum
- **HintWise** - Intelligent hint system
- **SQL-Engage Dataset** - Error taxonomy backbone

---

*The Adaptive Textbook Helper: Making every PDF a substrate for personalized, research-grounded learning.*
