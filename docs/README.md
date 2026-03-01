# ALGL PDF Helper Documentation

Complete documentation for the ALGL PDF Helper project - a Python CLI tool for processing PDFs into structured learning content.

---

## Quick Start

New to the project? Start here:

1. **[Project README](../README.md)** - Installation, basic usage, and features
2. **[AGENTS.md](../AGENTS.md)** - Development guidelines and architecture
3. **[OUTPUT_SPEC.md](OUTPUT_SPEC.md)** - Output format specification

---

## Documentation Index

### Core Documentation

| Document | Description | Audience |
|----------|-------------|----------|
| [../README.md](../README.md) | Project overview, installation, CLI usage | Users, Developers |
| [../AGENTS.md](../AGENTS.md) | AI agent guidelines, architecture, coding standards | AI Agents, Developers |
| [OUTPUT_SPEC.md](OUTPUT_SPEC.md) | Complete output format specification | Integrators |
| [../CONTENT_QUALITY_RECOMMENDATIONS.md](../CONTENT_QUALITY_RECOMMENDATIONS.md) | Content quality guidelines | Content Creators |

### Architecture & Pipeline

| Document | Description | Audience |
|----------|-------------|----------|
| [03-pipeline-architecture.md](03-pipeline-architecture.md) | Detailed 5-phase pipeline documentation | Developers |
| [PIPELINE_DIAGRAM.md](PIPELINE_DIAGRAM.md) | Visual pipeline diagrams (ASCII & Mermaid) | All |
| [12-output-structure.md](12-output-structure.md) | Output directory structure | Integrators |

### Testing & Integration

| Document | Description | Audience |
|----------|-------------|----------|
| [PHASE6_INTEGRATION_GATES.md](PHASE6_INTEGRATION_GATES.md) | CI/CD, testing, and regression detection | Developers |
| [../test_reports/COMPREHENSIVE_TEST_SUMMARY.md](../test_reports/COMPREHENSIVE_TEST_SUMMARY.md) | Complete test results | Developers |
| [../test_reports/FINAL_VALIDATION_REPORT.md](../test_reports/FINAL_VALIDATION_REPORT.md) | Final validation results | Developers |

---

## By Use Case

### I want to...

#### Process a PDF
→ See [../README.md](../README.md) - "CLI Usage" section

#### Understand the output format
→ See [OUTPUT_SPEC.md](OUTPUT_SPEC.md)

#### Integrate with SQL-Adapt
→ See [12-output-structure.md](12-output-structure.md) - "Integration with SQL-Adapt Web App"

#### Set up CI/CD
→ See [PHASE6_INTEGRATION_GATES.md](PHASE6_INTEGRATION_GATES.md)

#### Understand the codebase
→ See [../AGENTS.md](../AGENTS.md) - "Project Structure" and "Code Organization" sections

#### Configure concept mappings
→ See [../AGENTS.md](../AGENTS.md) - "Concepts Configuration" section

---

## Document Status

| Legend | Meaning |
|--------|---------|
| ✅ | Current and maintained |
| 📦 | Archived (historical reference) |
| ⚠️ | Needs review |

### Current Documentation (✅)

All documents in this directory (except `archive/`) are current as of 2026-03-01.

### Archived Documentation (📦)

Historical documents are preserved in [archive/](archive/) for reference. These include:
- Old integration approaches
- Superseded architecture decisions
- Completed roadmap items
- Outdated API documentation

---

## Contributing to Documentation

When updating documentation:

1. Update the "Last Updated" date in the document header
2. Update this README if adding/removing documents
3. Update [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) for comprehensive tracking
4. Archive (don't delete) outdated documents

---

**Last Updated:** 2026-03-01  
**Documentation Version:** 1.0.0
