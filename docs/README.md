# Adaptive Textbook Helper - Documentation

Welcome to the Adaptive Textbook Helper documentation. This project transforms static PDFs into dynamic, inspectable knowledge substrates for interaction-driven SQL learning.

## 📚 Documentation Structure

```
docs/
├── README.md                 # This file - Documentation landing page
├── ARCHITECTURE.md           # System architecture (5-phase pipeline)
├── PROJECT_BLUEPRINT.md      # Vision, research foundation, four-packs
├── api/                      # API & Contract Specifications
│   ├── OUTPUT_SPEC.md        # Output format specification (v2)
│   ├── EVENT_LOGGING.md      # Event taxonomy & logging
│   └── PROVENANCE.md         # PROV-DM provenance architecture
├── guides/                   # User Guides
│   ├── QUICKSTART.md         # Quick start guide
│   ├── OCR_TROUBLESHOOTING.md # OCR troubleshooting
│   └── CONTENT_QUALITY.md    # Content quality guidelines
├── reference/                # Reference Materials
│   ├── TESTING.md            # Testing & CI/CD (Phase 6)
│   └── OUTPUT_STRUCTURE.md   # Three-layer output structure
├── internal/                 # Internal Documentation
│   ├── INDEX.md              # Master documentation index
│   └── CHANGELOG.md          # Change history
└── archive/                  # Historical documentation
```

## 🚀 Quick Start

New to the project? Start here:

1. **[PROJECT_BLUEPRINT.md](PROJECT_BLUEPRINT.md)** - Understand the vision and research foundation
2. **[ARCHITECTURE.md](ARCHITECTURE.md)** - Learn the five-phase pipeline and four-pack architecture
3. **[guides/QUICKSTART.md](guides/QUICKSTART.md)** - Get up and running quickly

## 📖 Documentation by Role

### For Developers

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture, component reference |
| [api/OUTPUT_SPEC.md](api/OUTPUT_SPEC.md) | Output formats and schemas |
| [api/EVENT_LOGGING.md](api/EVENT_LOGGING.md) | Event logging implementation |
| [api/PROVENANCE.md](api/PROVENANCE.md) | Provenance tracking |
| [reference/TESTING.md](reference/TESTING.md) | Testing strategy and CI/CD |

### For Researchers

| Document | Purpose |
|----------|---------|
| [PROJECT_BLUEPRINT.md](PROJECT_BLUEPRINT.md) | Research foundation, assistance dilemma, metrics |
| [api/EVENT_LOGGING.md](api/EVENT_LOGGING.md) | HDI, CSI, APS, RQS metrics |
| [api/PROVENANCE.md](api/PROVENANCE.md) | Reproducibility, counterfactual replay |

### For Integrators

| Document | Purpose |
|----------|---------|
| [api/OUTPUT_SPEC.md](api/OUTPUT_SPEC.md) | JSON schemas, migration guide |
| [reference/OUTPUT_STRUCTURE.md](reference/OUTPUT_STRUCTURE.md) | Three-layer mapping structure |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Integration patterns |

### For Users

| Document | Purpose |
|----------|---------|
| [guides/QUICKSTART.md](guides/QUICKSTART.md) | Quick start guide |
| [guides/OCR_TROUBLESHOOTING.md](guides/OCR_TROUBLESHOOTING.md) | OCR issues and solutions |
| [guides/CONTENT_QUALITY.md](guides/CONTENT_QUALITY.md) | Content quality guidelines |

## 🏗️ The Four Packs

The architecture is organized around four orthogonal "packs":

| Pack | Purpose | Key Docs |
|------|---------|----------|
| **Document** | PDF → chunks + embeddings | [ARCHITECTURE.md#document-pack](ARCHITECTURE.md) |
| **Domain** | Concepts + prerequisite DAG | [ARCHITECTURE.md#domain-pack](ARCHITECTURE.md) |
| **Trace** | Event logging + metrics | [api/EVENT_LOGGING.md](api/EVENT_LOGGING.md) |
| **Policy** | Escalation rules + bandits | [PROJECT_BLUEPRINT.md#policy-pack](PROJECT_BLUEPRINT.md) |

## 🔗 External References

- [Root README.md](../README.md) - Project overview and installation
- [AGENTS.md](../AGENTS.md) - AI agent development guide
- [SQL-Adapt Integration](api/OUTPUT_SPEC.md#integration-with-sql-adapt)

## 📋 Document Status

| Document | Version | Status | Last Updated |
|----------|---------|--------|--------------|
| PROJECT_BLUEPRINT.md | v1.0.0 | ✅ Current | 2026-03-03 |
| ARCHITECTURE.md | v2.0.0 | ✅ Current | 2026-03-03 |
| api/OUTPUT_SPEC.md | v2.0.0 | ✅ Current | 2026-03-03 |
| api/EVENT_LOGGING.md | v1.0.0 | ✅ Current | 2026-03-03 |
| api/PROVENANCE.md | v1.0.0 | ✅ Current | 2026-03-03 |

---

*For the complete documentation index, see [internal/INDEX.md](internal/INDEX.md).*
