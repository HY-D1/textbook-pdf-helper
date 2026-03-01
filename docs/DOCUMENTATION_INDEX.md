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

#### QUICKSTART.md
- **Path:** `/QUICKSTART.md`
- **Purpose:** Quick start guide for educational output generation
- **Audience:** Users wanting to generate educational content
- **Status:** ⚠️ Partially outdated - references CLI commands that don't exist
- **Last Verified:** 2026-03-01
- **Note:** Contains references to `algl-pdf export-edu` and `algl-pdf edu` commands that are not in the current CLI

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
- **Status:** ✅ Current (created 2026-03-01)

#### README.md
- **Path:** `/docs/README.md`
- **Purpose:** Documentation directory index and navigation
- **Audience:** All
- **Status:** ✅ Current (updated 2026-03-01)

### Architecture Documentation

#### 03-pipeline-architecture.md
- **Path:** `/docs/03-pipeline-architecture.md`
- **Purpose:** Complete 5-phase pipeline architecture documentation
- **Audience:** Developers, architects
- **Status:** ✅ Current
- **Last Verified:** 2026-03-01
- **Key Content:**
  - High-level overview
  - Phase 1: PDF Extraction & OCR
  - Phase 2: Knowledge Extraction & Concept Mapping
  - Phase 3: LLM Enhancement & SQL Validation
  - Output generation
  - Complete data flow
  - Quality metrics by phase
  - Key classes & responsibilities
  - Example: Complete flow for "SELECT Statement"
  - Performance characteristics

#### PIPELINE_DIAGRAM.md
- **Path:** `/docs/PIPELINE_DIAGRAM.md`
- **Purpose:** Visual pipeline documentation with ASCII and Mermaid diagrams
- **Audience:** Visual learners, all
- **Status:** ✅ Current
- **Last Verified:** 2026-03-01
- **Key Content:**
  - High-level flow diagram
  - Phase 1: PDF Extraction & OCR (detailed)
  - Phase 2: Chunking & Embedding (detailed)
  - Phase 3: Concept Mapping (detailed)
  - Phase 4: Pedagogical Generation (detailed)
  - Phase 5: Output Generation & Export (detailed)
  - File flow diagram
  - SQL-Adapt Integration diagram
  - Component relationship diagram
  - Quality metrics by phase
  - Pipeline comparison table
  - Mermaid diagram for Markdown viewers

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
  - JSON schema definitions (textbook-manifest.json, concept-map.json, chunks.json, concept-manifest.json, asset-manifest.json)
  - Markdown frontmatter schema
  - Chunk ID format
  - Migration guide
  - Version detection

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
  - Validation commands

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
  - Offline metrics (CoverageMetric, RetrievalSanityMetric, QualityScore, EvaluationReport)
  - Regression detection
  - Evaluation CLI commands
  - Baseline storage
  - Makefile targets
  - GitHub Actions CI workflow
  - Quality thresholds

---

## test_reports/ Directory

### Current Reports (Keep)

#### DOCUMENTATION_CLEANUP_REPORT.md
- **Path:** `/test_reports/DOCUMENTATION_CLEANUP_REPORT.md`
- **Purpose:** Documentation consolidation report
- **Created:** 2026-03-01
- **Status:** ✅ Current

#### COMPREHENSIVE_TEST_SUMMARY.md
- **Path:** `/test_reports/COMPREHENSIVE_TEST_SUMMARY.md`
- **Purpose:** Master test summary across all test phases
- **Status:** ✅ Current

#### FINAL_TEST_SUMMARY.md
- **Path:** `/test_reports/FINAL_TEST_SUMMARY.md`
- **Purpose:** Final test results summary
- **Status:** ✅ Current

#### FINAL_VALIDATION_REPORT.md
- **Path:** `/test_reports/FINAL_VALIDATION_REPORT.md`
- **Purpose:** Final validation results with pass/fail status
- **Status:** ✅ Current

#### ISSUES_FOUND.md
- **Path:** `/test_reports/ISSUES_FOUND.md`
- **Purpose:** Active issue tracking
- **Status:** ✅ Current

#### OPTIMIZATION_GUIDE.md
- **Path:** `/test_reports/OPTIMIZATION_GUIDE.md`
- **Purpose:** Performance optimization recommendations
- **Status:** ✅ Current

### Individual Test Reports (Archived)

The following individual test reports are preserved for historical reference but superseded by the summary reports above:

- `asset_extraction_edge_cases_report.md`
- `asset_extraction_test_report.md`
- `auto_mapping_test_report.md`
- `ci_integration_test_report.md`
- `cli_ui_test_report.md`
- `data_integrity_test_report.md`
- `edge_cases_test_report.md`
- `end_to_end_test_report.md`
- `integration_edge_cases_report.md`
- `ocr_extraction_edge_cases_report.md`
- `pedagogical_generation_test_report.md`
- `performance_test_report.md`
- `preflight_test_report.md`
- `provenance_test_report.md`
- `real_world_simulations_report.md`

---

## docs/archive/ Directory

### Archived Documentation

All documents moved here on 2026-03-01 as part of documentation consolidation:

#### 01-integration-guide.md
- **Reason:** Old integration approach (Option B: Automated) superseded by current pipeline
- **Status:** 📦 Archived
- **Historical Value:** Shows original SQL-Adapt integration plan

#### 02-concept-mapping.md
- **Reason:** Concept system evolved significantly; content superseded by 12-output-structure.md
- **Status:** 📦 Archived
- **Historical Value:** Original three-layer concept mapping design

#### 04-educational-notes.md
- **Reason:** Superseded by OUTPUT_SPEC.md and 12-output-structure.md
- **Status:** 📦 Archived

#### 05-kimi-integration.md
- **Reason:** Kimi integration not implemented in current codebase
- **Status:** 📦 Archived
- **Historical Value:** Planned AI integration features

#### 06-cost-guide.md
- **Reason:** Outdated cost estimates for Kimi API
- **Status:** 📦 Archived

#### 07-improvement-plan.md
- **Reason:** Roadmap items completed
- **Status:** 📦 Archived
- **Historical Value:** Original improvement roadmap

#### 08-audit-report.md
- **Reason:** Old audit results
- **Status:** 📦 Archived

#### 09-quality-fixes.md
- **Reason:** Fixes already applied
- **Status:** 📦 Archived

#### 10-quality-improvements.md
- **Reason:** Improvements completed
- **Status:** 📦 Archived

#### 11-folder-structure.md
- **Reason:** Project structure changed
- **Status:** 📦 Archived

#### COMMIT_SUGGESTIONS.md
- **Reason:** Old commit guidance
- **Status:** 📦 Archived
- **Historical Value:** Shows git workflow at a point in time

---

## Documentation Relationships

```
README.md (Entry Point)
    ├── AGENTS.md (Development Guide)
    ├── docs/
    │   ├── OUTPUT_SPEC.md (Output Format)
    │   ├── 03-pipeline-architecture.md (Architecture)
    │   ├── PIPELINE_DIAGRAM.md (Visual)
    │   ├── 12-output-structure.md (Integration)
    │   └── PHASE6_INTEGRATION_GATES.md (Testing)
    └── test_reports/
        ├── DOCUMENTATION_CLEANUP_REPORT.md
        ├── COMPREHENSIVE_TEST_SUMMARY.md
        └── FINAL_VALIDATION_REPORT.md
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
| 2026-03-01 | Documentation consolidation | Multiple - see DOCUMENTATION_CLEANUP_REPORT.md |

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
| Understand architecture | 03-pipeline-architecture.md | PIPELINE_DIAGRAM.md |
| Develop new features | AGENTS.md | 03-pipeline-architecture.md |
| Check content quality | CONTENT_QUALITY_RECOMMENDATIONS.md | - |

---

**End of Index**

*This document is maintained as part of the ALGL PDF Helper project documentation.*
