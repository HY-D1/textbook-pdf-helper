# Master Documentation Index

**Project:** ALGL PDF Helper  
**Version:** 0.1.0  
**Last Updated:** 2026-03-01  
**Status:** Consolidated

---

## Overview

This document serves as the single source of truth for all project documentation. It catalogs every document, its purpose, status, and relationships to other documents.

---

## Root-Level Documentation

### Primary Entry Points

#### README.md
- **Path:** `/README.md`
- **Purpose:** Main project documentation - installation, usage, features
- **Audience:** End users, new developers
- **Status:** ✅ Current
- **Last Verified:** 2026-03-01
- **Key Sections:**
  - What it does (pipeline overview)
  - Installation instructions
  - CLI usage examples
  - Concept generation
  - Interactive processing with start.sh
  - Server usage
  - Output format notes

#### AGENTS.md
- **Path:** `/AGENTS.md`
- **Purpose:** AI Agent development guidelines and project architecture
- **Audience:** AI agents, core developers
- **Status:** ✅ Current
- **Last Verified:** 2026-03-01
- **Key Sections:**
  - Project overview
  - Technology stack
  - Project structure
  - Module responsibilities
  - Data flow diagrams
  - Build and development commands
  - Code style guidelines
  - Testing strategy
  - Output format specification
  - Concepts configuration

#### CONTENT_QUALITY_RECOMMENDATIONS.md
- **Path:** `/CONTENT_QUALITY_RECOMMENDATIONS.md`
- **Purpose:** Content quality analysis and improvement recommendations
- **Audience:** Content creators, quality assurance
- **Status:** ✅ Current
- **Last Verified:** 2026-03-01
- **Key Content:**
  - Quality metrics (186 concepts analyzed)
  - Critical issues identification
  - P0-P3 prioritized recommendations
  - Quality checklist for new concepts

#### LICENSE
- **Path:** `/LICENSE`
- **Purpose:** MIT License
- **Status:** ✅ Current
- **Last Verified:** 2026-03-01

---

## docs/ Directory

### Core Documentation

#### DOCUMENTATION_INDEX.md (This File)
- **Path:** `/docs/DOCUMENTATION_INDEX.md`
- **Purpose:** Master index of all documentation
- **Audience:** All
- **Status:** ✅ Current (updated 2026-03-01)

### Architecture Documentation

#### ARCHITECTURE.md
- **Path:** `/docs/ARCHITECTURE.md`
- **Purpose:** Complete system architecture and pipeline documentation (consolidated)
- **Audience:** Developers, architects
- **Status:** ✅ Current
- **Last Verified:** 2026-03-01
- **Key Content:**
  - 5-phase pipeline overview
  - Detailed phase breakdowns
  - Data flow diagrams
  - Component reference
  - Quality metrics
  - Output generation
- **Replaces:**
  - `03-pipeline-architecture.md` (archived)
  - `PIPELINE_DIAGRAM.md` (archived)

### Output Documentation

#### OUTPUT_SPEC.md
- **Path:** `/docs/OUTPUT_SPEC.md`
- **Purpose:** Complete output format specification (textbook-static-v1)
- **Audience:** Integrators, API consumers
- **Status:** ✅ Current
- **Last Verified:** 2026-03-01
- **Key Content:**
  - Schema versioning
  - Environment configuration
  - Folder structure
  - JSON schema definitions
  - Markdown frontmatter schema
  - Chunk ID format
  - Migration guide

#### 12-output-structure.md
- **Path:** `/docs/12-output-structure.md`
- **Purpose:** Three-layer concept mapping output structure
- **Audience:** Integrators, SQL-Adapt developers
- **Status:** ✅ Current
- **Last Verified:** 2026-03-01
- **Key Content:**
  - Three-layer mapping explanation
  - Generated output structure
  - Key output files explained
  - Concept determination flow
  - SQL-Adapt integration code examples

### Testing Documentation

#### PHASE6_INTEGRATION_GATES.md
- **Path:** `/docs/PHASE6_INTEGRATION_GATES.md`
- **Purpose:** Phase 6 testing, CI/CD, and regression detection
- **Audience:** Developers, DevOps
- **Status:** ✅ Current
- **Last Verified:** 2026-03-01
- **Key Content:**
  - Golden PDF fixture
  - CI test suite
  - Offline metrics (CoverageMetric, RetrievalSanityMetric, QualityScore)
  - Regression detection
  - Evaluation CLI commands
  - Baseline storage

---

## docs/archive/ Directory

### Archived Documentation

The following documents have been archived as part of documentation consolidation (2026-03-01):

#### 03-pipeline-architecture.md
- **Reason:** Content merged into ARCHITECTURE.md
- **Status:** 📦 Archived
- **Historical Value:** Detailed phase-by-phase documentation

#### PIPELINE_DIAGRAM.md
- **Reason:** Content merged into ARCHITECTURE.md
- **Status:** 📦 Archived
- **Historical Value:** Visual pipeline diagrams

---

## Documentation Relationships

```
README.md (Entry Point)
    ├── AGENTS.md (Development Guide)
    ├── docs/
    │   ├── ARCHITECTURE.md (Consolidated Architecture)
    │   ├── OUTPUT_SPEC.md (Output Format)
    │   ├── 12-output-structure.md (Integration)
    │   └── PHASE6_INTEGRATION_GATES.md (Testing)
    └── CONTENT_QUALITY_RECOMMENDATIONS.md
```

---

## Documentation Maintenance

### Update Cycle

- **Quarterly Review:** Check all "Current" docs for accuracy
- **With Each Release:** Update version references, archive outdated content
- **On-Demand:** Update when features change

### Change Log

| Date | Change | Files Affected |
|------|--------|----------------|
| 2026-03-01 | Documentation consolidation | ARCHITECTURE.md created, 03-pipeline-architecture.md and PIPELINE_DIAGRAM.md archived |

---

## Quick Reference

### By Task

| Task | Primary Doc | Secondary Doc(s) |
|------|-------------|------------------|
| Install the tool | README.md | - |
| Process a PDF | README.md | AGENTS.md |
| Understand output | OUTPUT_SPEC.md | 12-output-structure.md |
| Integrate with SQL-Adapt | 12-output-structure.md | OUTPUT_SPEC.md |
| Set up CI/CD | PHASE6_INTEGRATION_GATES.md | - |
| Understand architecture | ARCHITECTURE.md | AGENTS.md |
| Develop new features | AGENTS.md | ARCHITECTURE.md |
| Check content quality | CONTENT_QUALITY_RECOMMENDATIONS.md | - |

---

**End of Index**

*This document is maintained as part of the ALGL PDF Helper project documentation.*
