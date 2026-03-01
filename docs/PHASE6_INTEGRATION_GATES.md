# Phase 6: Integration Gates + Reproducible Evaluation

This document describes the Phase 6 implementation for the ALGL PDF Helper project, which adds comprehensive integration testing, metrics, and regression detection.

## Overview

Phase 6 provides:

1. **Golden PDF Fixture** - A synthetic 8-page PDF with known SQL content for testing
2. **CI Test Suite** - Automated tests for schema stability, quality gates, and end-to-end pipeline
3. **Offline Metrics** - Coverage, retrieval sanity, and quality scoring
4. **Regression Detection** - Automated comparison against baselines
5. **Evaluation CLI** - Commands for running metrics and detecting regressions

## Components

### 1. Golden PDF Fixture (`tests/fixtures/`)

**Files:**
- `tests/fixtures/generate_golden_pdf.py` - Script to generate synthetic PDF
- `tests/fixtures/golden_concepts.yaml` - Concept mapping for golden PDF
- `tests/fixtures/golden_chapter.pdf` - Generated 8-page PDF (not version controlled)

**Content:**
- 3 SQL concepts: SELECT, WHERE, JOIN
- 2 figures/tables with reference data
- 8 pages with known structure
- Embedded text (not scanned)

**Usage:**
```bash
# Generate golden PDF
python tests/fixtures/generate_golden_pdf.py

# Or via make
make generate-golden
```

### 2. CI Test Suite (`tests/test_integration_ci.py`)

**Test Categories:**

#### Schema and Version Tests
- `test_schema_versions_match()` - Schema versions consistent across files
- `test_chunker_version_stable()` - Chunker version unchanged
- `test_embedding_model_stable()` - Embedding model unchanged

#### Chunk Count Tests
- `test_chunk_counts_stable()` - Chunk count within expected range
- `test_chunk_ids_format()` - Chunk IDs follow expected format
- `test_chunks_have_embeddings()` - All chunks have embeddings

#### Concept Generation Tests
- `test_concepts_generated()` - At least 2 concepts generated
- `test_concept_markdowns_generated()` - Markdown files created
- `test_expected_concepts_present()` - Core SQL concepts detected

#### Figure/Table Extraction Tests
- `test_figures_extracted()` - Table content found in chunks

#### Quality Gate Tests
- `test_quality_gates_pass()` - PDF passes quality checks
- `test_minimum_pages_extracted()` - All 8 pages extracted
- `test_no_empty_chunks()` - No empty chunk content
- `test_chunk_text_quality()` - Text meets quality standards

#### End-to-End Pipeline Tests
- `test_end_to_end_pipeline()` - Full pipeline runs without errors
- `test_pipeline_output_valid_json()` - All outputs are valid JSON

#### Regression Tests
- `test_against_baseline()` - Compare output to baseline

#### Metrics Tests
- `test_coverage_metric()` - Coverage calculation works
- `test_retrieval_sanity_metric()` - Retrieval tests work
- `test_quality_score()` - Quality scoring works
- `test_evaluation_report()` - Full report generation works

#### Performance Tests
- `test_processing_time()` - Processing completes in < 30 seconds

**Usage:**
```bash
# Run all CI tests
make test-ci

# Or directly
pytest tests/test_integration_ci.py -v
```

### 3. Offline Metrics (`src/algl_pdf_helper/metrics.py`)

**Classes:**

#### `CoverageMetric`
Measures concept coverage (found / expected).

```python
coverage = CoverageMetric(
    expected_concepts=["select-basic", "where-clause"],
    found_concepts=["select-basic", "join-operations"],
)
print(f"Coverage: {coverage.coverage_ratio:.1%}")
print(f"Missing: {coverage.missing_concepts}")
```

#### `RetrievalSanityMetric`
Tests if known queries retrieve expected content.

```python
metric = RetrievalSanityMetric(test_queries=[
    {"query": "SELECT statement", "expected_page": 2},
])
metric.run_tests(chunks, embedding_fn, top_k=5)
print(f"Success rate: {metric.success_rate:.1%}")
```

#### `QualityScore`
Overall quality score combining multiple factors.

```python
quality = QualityScore(
    coverage_score=0.9,
    retrieval_score=0.85,
    chunk_quality_score=0.95,
)
print(f"Overall: {quality.overall_score:.1%}")
print(f"Grade: {quality.grade}")
```

#### `EvaluationReport`
Combined metrics report.

```python
report = run_evaluation(
    document=document,
    concept_manifest=concept_manifest,
    expected_concepts=expected_concepts,
    test_queries=test_queries,
    embedding_fn=embedding_fn,
)
report.save(Path("evaluation-report.json"))
```

### 4. Regression Detection (`src/algl_pdf_helper/regression_detector.py`)

**Features:**
- Compare current output to baseline
- Detect schema version changes
- Detect chunk count changes (with tolerance)
- Detect missing/extra concepts
- Generate regression report

**Usage:**

```bash
# Via CLI
algl-pdf detect-regressions \
    ./tests/baselines/golden_chapter \
    ./out/pdf-index \
    --tolerance 0.10 \
    --output regression-report.json
```

```python
# Via Python
from algl_pdf_helper.regression_detector import detect_regression

report = detect_regression(
    baseline_dir=Path("./tests/baselines/golden_chapter"),
    current_dir=Path("./out/pdf-index"),
    chunk_count_tolerance=0.10,
)

if report.has_errors:
    print("Regressions detected!")
    for check in report.failed_checks:
        print(f"  - {check.check_name}: {check.message}")
```

**Checks Performed:**
- `schema_version` - Schema must not change (error)
- `chunker_version` - Chunker version changes (warning)
- `embedding_model` - Embedding model changes (warning)
- `chunk_count` - Chunk count within tolerance
- `source_doc_count` - Source document count stable
- `page_count` - Page count stable
- `concept_count` - Concept count changes (warning)
- `missing_concepts` - No concepts missing (error)
- `extra_concepts` - New concepts added (info)

### 5. Evaluation CLI

**Commands:**

#### `evaluate`
Run metrics against processed PDF output.

```bash
# Basic evaluation
algl-pdf evaluate ./out/pdf-index

# With baseline comparison
algl-pdf evaluate ./out/pdf-index \
    --baseline ./tests/baselines/golden_chapter

# With custom threshold
algl-pdf evaluate ./out/pdf-index \
    --threshold 0.80 \
    --output ./report.json

# With concepts config
algl-pdf evaluate ./out/pdf-index \
    --concepts-config ./concepts.yaml
```

**Output:**
- Overall score and grade
- Coverage metric
- Retrieval sanity metric
- Quality components
- Pass/fail based on threshold

#### `detect-regressions`
Compare output to baseline for regressions.

```bash
# Basic comparison
algl-pdf detect-regressions ./baseline ./current

# With custom tolerance
algl-pdf detect-regressions ./baseline ./current \
    --tolerance 0.15 \
    --output report.json
```

### 6. Baseline Storage (`tests/baselines/`)

**Structure:**
```
tests/baselines/
├── expected_chunks.json       # Expected chunk structure
├── expected_concepts.json     # Expected concept manifest
└── golden_chapter/            # Actual baseline output (generated)
    ├── index.json
    ├── manifest.json
    ├── chunks.json
    ├── concept-manifest.json
    └── concepts/
        ├── README.md
        └── *.md
```

**Management:**
```bash
# Update baselines
make update-baselines

# Or manually
algl-pdf index tests/fixtures/golden_chapter.pdf \
    --out tests/baselines/golden_chapter \
    --use-aliases \
    --concepts-config tests/fixtures/golden_concepts.yaml
```

### 7. Makefile Targets

```bash
# Run CI tests
make test-ci

# Update baselines
make update-baselines

# Run evaluation
make evaluate

# Check for regressions
make regression-check

# Full clean
make clean
```

## CI/CD Integration

### GitHub Actions (`.github/workflows/ci.yml`)

The CI workflow:

1. **Matrix Testing** - Python 3.10, 3.11, 3.12
2. **Dependency Installation** - All extras + reportlab
3. **Golden PDF Generation** - Create test fixture
4. **CI Tests** - Run `test_integration_ci.py`
5. **Regression Detection** - Compare to baseline
6. **Evaluation** - Generate quality metrics
7. **Quality Gates** - Schema version, chunk count, concept count checks
8. **Artifact Upload** - On failure, upload outputs for debugging

### Quality Thresholds

| Metric | Minimum | Target |
|--------|---------|--------|
| Overall Score | 0.70 | 0.85 |
| Coverage | 0.60 | 0.90 |
| Retrieval | 0.50 | 0.80 |
| Chunk Quality | 0.80 | 0.95 |

### Failure Conditions

CI fails when:
- Any error-level regression detected
- Quality score below threshold (0.70)
- Schema version changes
- Source document count changes
- Required concepts missing
- Tests fail

## Workflow Examples

### Adding a New Feature

```bash
# 1. Run tests to ensure baseline passes
make test-ci

# 2. Make your changes
# ... edit code ...

# 3. Run tests again
make test-ci

# 4. Check for regressions
make regression-check

# 5. If changes are expected/intentional
make update-baselines
```

### Investigating a Failure

```bash
# Run specific test
pytest tests/test_integration_ci.py::test_chunk_counts_stable -v

# Run with baseline comparison
algl-pdf evaluate ./out/pdf-index --baseline ./tests/baselines/golden_chapter

# Check regression details
algl-pdf detect-regressions ./tests/baselines/golden_chapter ./out/pdf-index
```

### Release Preparation

```bash
# 1. Full clean
make clean

# 2. Install fresh
make install-dev

# 3. Generate fixtures
make generate-golden

# 4. Update baselines
make update-baselines

# 5. Run full test suite
make test

# 6. Verify evaluation
make evaluate

# 7. Commit baselines if changed
git add tests/baselines/
git commit -m "Update baselines for vX.Y.Z"
```

## Extending the System

### Adding New Metrics

1. Create metric class in `metrics.py`
2. Add test in `test_integration_ci.py`
3. Update `run_evaluation()` to include new metric
4. Document in this file

### Adding New Regression Checks

1. Add check method in `RegressionDetector` class
2. Call from `compare_documents()` or `compare_concept_manifests()`
3. Update report display in CLI

### Adding New Test Cases

1. Add test to `test_integration_ci.py`
2. Use `processed_golden_doc` fixture for pre-processed document
3. Follow existing test naming conventions
4. Add docstring describing what the test verifies

## Troubleshooting

### "Golden PDF not found"
```bash
python tests/fixtures/generate_golden_pdf.py
# or
make generate-golden
```

### "Baseline not found"
```bash
make update-baselines
```

### "reportlab not found"
```bash
pip install reportlab
```

### Tests timeout
Golden fixture tests should complete in < 30 seconds. If timing out:
- Check OCR is not being triggered (use `--no-auto-ocr` if needed)
- Verify PDF is the generated fixture, not a real scanned PDF
- Check system resources

## References

- Golden PDF: `tests/fixtures/golden_chapter.pdf`
- Golden Concepts: `tests/fixtures/golden_concepts.yaml`
- CI Tests: `tests/test_integration_ci.py`
- Metrics: `src/algl_pdf_helper/metrics.py`
- Regression: `src/algl_pdf_helper/regression_detector.py`
- CI Config: `.github/workflows/ci.yml`
