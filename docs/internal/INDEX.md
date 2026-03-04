# Master Documentation Index

**Project:** Adaptive Textbook Helper  
**Version:** 2.0.0  
**Last Updated:** 2026-03-03  
**Status:** Current

---

## Overview

This document serves as the single source of truth for all project documentation. It catalogs every document, its purpose, status, and relationships to other documents.

The Adaptive Textbook Helper transforms static PDFs into dynamic, inspectable knowledge substrates for interaction-driven SQL learning.

---

## Documentation Structure

```
docs/
├── README.md                 # Documentation landing page
├── ARCHITECTURE.md           # System architecture
├── PROJECT_BLUEPRINT.md      # Vision & research foundation
├── api/                      # API & Contract Specifications
│   ├── OUTPUT_SPEC.md
│   ├── EVENT_LOGGING.md
│   └── PROVENANCE.md
├── guides/                   # User Guides
│   ├── QUICKSTART.md
│   ├── OCR_TROUBLESHOOTING.md
│   └── CONTENT_QUALITY.md
├── reference/                # Reference Materials
│   ├── TESTING.md
│   └── OUTPUT_STRUCTURE.md
├── internal/                 # Internal Documentation
│   ├── INDEX.md              # This file
│   └── CHANGELOG.md
└── archive/                  # Historical documentation
```

---

## Quick Navigation

| If you want to... | Read this document |
|-------------------|-------------------|
| Understand the vision | [PROJECT_BLUEPRINT.md](../PROJECT_BLUEPRINT.md) |
| Learn the architecture | [ARCHITECTURE.md](../ARCHITECTURE.md) |
| See output formats | [api/OUTPUT_SPEC.md](../api/OUTPUT_SPEC.md) |
| Understand event logging | [api/EVENT_LOGGING.md](../api/EVENT_LOGGING.md) |
| Understand provenance | [api/PROVENANCE.md](../api/PROVENANCE.md) |
| Get started quickly | [guides/QUICKSTART.md](../guides/QUICKSTART.md) |
| Get project overview | [Root README.md](../../README.md) |
| Develop new features | [AGENTS.md](../../AGENTS.md) |

---

## Core Documentation

### Vision and Blueprint

#### PROJECT_BLUEPRINT.md
- **Path:** `/docs/PROJECT_BLUEPRINT.md`
- **Purpose:** Architectural vision, four-pack separation, research foundation
- **Audience:** Architects, researchers, stakeholders
- **Status:** ✅ Current (v1.0.0)
- **Key Content:**
  - The Four Packs (Document, Domain, Trace, Policy)
  - Artifact specification and content-addressing
  - Escalation ladder and adaptive policies
  - Research foundation (assistance dilemma, RAG, etc.)

### Architecture Documentation

#### ARCHITECTURE.md
- **Path:** `/docs/ARCHITECTURE.md`
- **Purpose:** Complete system architecture with five-phase pipeline
- **Audience:** Developers, architects
- **Status:** ✅ Current (v2.0.0)
- **Key Content:**
  - Five-phase pipeline
  - The Four Packs in detail
  - Component reference
  - Data flow diagrams

---

## API Specifications

### api/OUTPUT_SPEC.md
- **Purpose:** Complete output format specification (textbook-static-v2)
- **Audience:** Integrators, API consumers
- **Status:** ✅ Current (v2.0.0)
- **Key Content:**
  - Four-pack structure schemas
  - Prerequisite DAG specification
  - Event schemas
  - Migration guide

### api/EVENT_LOGGING.md
- **Purpose:** Event taxonomy and logging architecture
- **Audience:** Developers, data scientists
- **Status:** ✅ Current (v1.0.0)
- **Key Content:**
  - xAPI/Caliper alignment
  - Event taxonomy
  - Required correlation fields
  - Storage policies

### api/PROVENANCE.md
- **Purpose:** PROV-DM based provenance tracking
- **Audience:** Developers, researchers
- **Status:** ✅ Current (v1.0.0)
- **Key Content:**
  - PROV-DM model (Entity, Activity, Agent)
  - Provenance graph structure
  - Counterfactual replay architecture

---

## User Guides

### guides/QUICKSTART.md
- **Purpose:** Get up and running quickly
- **Audience:** New users
- **Status:** ✅ Current

### guides/OCR_TROUBLESHOOTING.md
- **Purpose:** OCR issues and solutions
- **Audience:** Users processing scanned PDFs
- **Status:** ✅ Current

### guides/CONTENT_QUALITY.md
- **Purpose:** Content quality guidelines
- **Audience:** Content creators
- **Status:** ✅ Current

---

## Reference Materials

### reference/TESTING.md
- **Purpose:** Testing strategy and CI/CD
- **Audience:** Developers, DevOps
- **Status:** ✅ Current
- **Key Content:**
  - Golden PDF fixture
  - CI test suite
  - Offline metrics
  - Regression detection

### reference/OUTPUT_STRUCTURE.md
- **Purpose:** Three-layer concept mapping explanation
- **Audience:** Integrators
- **Status:** ✅ Current

---

## Internal Documentation

### internal/INDEX.md
- **Purpose:** This file - Master documentation index
- **Status:** ✅ Current

### internal/CHANGELOG.md
- **Purpose:** Change history
- **Status:** ✅ Current

---

## Root-Level Documentation

### README.md (Root)
- **Path:** `/README.md`
- **Purpose:** Project overview, installation, quickstart
- **Audience:** End users, new developers
- **Status:** ✅ Current

### AGENTS.md
- **Path:** `/AGENTS.md`
- **Purpose:** AI Agent development guidelines
- **Audience:** AI agents, core developers
- **Status:** ✅ Current

---

## Documentation Relationships

```
Root README.md
    │
    ├── docs/README.md (Docs landing)
    │       │
    │       ├── PROJECT_BLUEPRINT.md (Vision)
    │       │
    │       ├── ARCHITECTURE.md (Architecture)
    │       │
    │       ├── api/
    │       │   ├── OUTPUT_SPEC.md (Schemas)
    │       │   ├── EVENT_LOGGING.md (Events)
    │       │   └── PROVENANCE.md (Provenance)
    │       │
    │       ├── guides/
    │       │   ├── QUICKSTART.md
    │       │   ├── OCR_TROUBLESHOOTING.md
    │       │   └── CONTENT_QUALITY.md
    │       │
    │       ├── reference/
    │       │   ├── TESTING.md
    │       │   └── OUTPUT_STRUCTURE.md
    │       │
    │       └── internal/
    │           ├── INDEX.md (This file)
    │           └── CHANGELOG.md
    │
    └── AGENTS.md (Dev guide)
```

---

## Documentation Maintenance

### Update Cycle

| Frequency | Action |
|-----------|--------|
| **With each release** | Update version references |
| **On feature changes** | Update relevant docs |
| **On schema changes** | Update api/OUTPUT_SPEC.md |
| **Quarterly** | Full documentation review |

### Version Alignment

| Document | Version | Aligns With |
|----------|---------|-------------|
| PROJECT_BLUEPRINT.md | v1.0.0 | Architecture v2.0 |
| ARCHITECTURE.md | v2.0.0 | Output Spec v2.0 |
| api/OUTPUT_SPEC.md | v2.0.0 | Schema v2 |
| api/EVENT_LOGGING.md | v1.0.0 | Architecture v2.0 |
| api/PROVENANCE.md | v1.0.0 | Architecture v2.0 |

### Change Log

| Date | Change | Files Affected |
|------|--------|----------------|
| 2026-03-03 | Documentation restructure | Reorganized into api/guides/reference/internal |
| 2026-03-03 | Four-pack architecture | PROJECT_BLUEPRINT.md, ARCHITECTURE.md |
| 2026-03-03 | Event logging spec | api/EVENT_LOGGING.md |
| 2026-03-03 | Provenance spec | api/PROVENANCE.md |

---

## Quick Reference by Task

| Task | Primary Doc | Secondary Doc(s) |
|------|-------------|------------------|
| Understand the vision | PROJECT_BLUEPRINT.md | - |
| Learn the architecture | ARCHITECTURE.md | PROJECT_BLUEPRINT.md |
| See API specs | api/OUTPUT_SPEC.md | api/EVENT_LOGGING.md |
| Get started | guides/QUICKSTART.md | Root README.md |
| Fix OCR issues | guides/OCR_TROUBLESHOOTING.md | - |
| Check quality | guides/CONTENT_QUALITY.md | - |
| Set up CI/CD | reference/TESTING.md | - |
| Integrate with SQL-Adapt | api/OUTPUT_SPEC.md | ARCHITECTURE.md |
| Develop features | AGENTS.md | ARCHITECTURE.md |

---

## Four-Pack Quick Reference

### Document Pack
- **Purpose:** PDF → chunks + embeddings
- **Key Docs:** ARCHITECTURE.md Phase 1, api/OUTPUT_SPEC.md
- **Key Files:** `chunks.json`, `index.faiss`

### Domain Pack
- **Purpose:** Concepts + prerequisite DAG
- **Key Docs:** ARCHITECTURE.md Phase 2, api/OUTPUT_SPEC.md
- **Key Files:** `concept-map.json`, `prereq-dag.json`

### Trace Pack
- **Purpose:** Event logging + derived metrics
- **Key Docs:** api/EVENT_LOGGING.md, ARCHITECTURE.md Phase 3
- **Key Files:** Event schemas, HDI/CSI/APS/RQS calculators

### Policy Pack
- **Purpose:** Escalation rules + adaptive policies
- **Key Docs:** PROJECT_BLUEPRINT.md, api/OUTPUT_SPEC.md
- **Key Files:** `profiles/*.json`, `escalation-ladder.yaml`

---

**End of Index**

*This document is maintained as part of the Adaptive Textbook Helper project documentation.*
