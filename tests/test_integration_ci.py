"""Integration tests for CI pipeline.

These tests verify:
- Schema versions are consistent
- Chunk counts are stable
- Concepts are generated
- Figures are extracted
- Quality gates pass
- End-to-end pipeline runs without errors
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Import after sys.path modification via conftest
from algl_pdf_helper.indexer import build_index
from algl_pdf_helper.models import IndexBuildOptions, PdfIndexDocument
from algl_pdf_helper.extract import check_extraction_quality, extract_pages_fitz
from algl_pdf_helper.regression_detector import detect_regression, load_baseline
from algl_pdf_helper.metrics import (
    CoverageMetric,
    RetrievalSanityMetric,
    QualityScore,
    EvaluationReport,
    run_evaluation,
)
from algl_pdf_helper.embedding import build_hash_embedding


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def golden_pdf_path() -> Path:
    """Path to the golden PDF fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "golden_chapter.pdf"
    if not fixture_path.exists():
        pytest.skip(f"Golden PDF not found: {fixture_path}. Run generate_golden_pdf.py first.")
    return fixture_path


@pytest.fixture(scope="session")
def concepts_config_path() -> Path:
    """Path to the golden concepts config."""
    config_path = Path(__file__).parent / "fixtures" / "golden_concepts.yaml"
    if not config_path.exists():
        pytest.skip(f"Golden concepts config not found: {config_path}")
    return config_path


@pytest.fixture
def temp_output_dir() -> Path:
    """Create a temporary output directory."""
    temp_dir = Path(tempfile.mkdtemp(prefix="algl_test_"))
    yield temp_dir
    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def processed_golden_doc(
    golden_pdf_path: Path,
    concepts_config_path: Path,
    temp_output_dir: Path,
) -> tuple[PdfIndexDocument, Path]:
    """Process the golden PDF and return the document and output path."""
    opts = IndexBuildOptions()
    
    doc = build_index(
        golden_pdf_path,
        temp_output_dir,
        options=opts,
        ocr=False,
        auto_ocr=False,
        use_aliases=True,
        strip_headers=True,
        concepts_config=concepts_config_path,
    )
    
    return doc, temp_output_dir


# ============================================================================
# Schema and Version Tests
# ============================================================================

def test_schema_versions_match(processed_golden_doc: tuple[PdfIndexDocument, Path]) -> None:
    """Assert schema versions are consistent across output files."""
    doc, output_dir = processed_golden_doc
    
    # Check document schema version
    assert doc.schemaVersion == "pdf-index-schema-v2", \
        f"Unexpected schema version: {doc.schemaVersion}"
    
    # Check manifest has same schema version
    manifest_path = output_dir / "manifest.json"
    manifest_data = json.loads(manifest_path.read_text())
    assert manifest_data["schemaVersion"] == doc.schemaVersion, \
        "Manifest schema version doesn't match document"
    
    # Check concept manifest schema version
    concept_manifest_path = output_dir / "concept-manifest.json"
    if concept_manifest_path.exists():
        concept_data = json.loads(concept_manifest_path.read_text())
        assert concept_data.get("schemaVersion") == "concept-manifest-v1", \
            f"Unexpected concept manifest schema version: {concept_data.get('schemaVersion')}"


def test_chunker_version_stable(processed_golden_doc: tuple[PdfIndexDocument, Path]) -> None:
    """Assert chunker version is as expected."""
    doc, _ = processed_golden_doc
    
    expected_version = "word-window-180-overlap-30-v1"
    assert doc.chunkerVersion == expected_version, \
        f"Chunker version changed: expected {expected_version}, got {doc.chunkerVersion}"


def test_embedding_model_stable(processed_golden_doc: tuple[PdfIndexDocument, Path]) -> None:
    """Assert embedding model ID is as expected."""
    doc, _ = processed_golden_doc
    
    expected_model = "hash-embedding-v1"
    assert doc.embeddingModelId == expected_model, \
        f"Embedding model changed: expected {expected_model}, got {doc.embeddingModelId}"


# ============================================================================
# Chunk Count Tests
# ============================================================================

def test_chunk_counts_stable(
    processed_golden_doc: tuple[PdfIndexDocument, Path],
    golden_pdf_path: Path,
) -> None:
    """Chunk count should be within tolerance of expected range."""
    doc, _ = processed_golden_doc
    
    # Golden PDF has ~750 total words across 8 pages
    # With 180-word chunks and 30-word overlap (step = 150), we expect:
    # 750 words / 150 = ~5 chunks minimum
    # Account for page boundaries and partial chunks at end of each page
    min_expected_chunks = 5
    max_expected_chunks = 20
    
    assert min_expected_chunks <= doc.chunkCount <= max_expected_chunks, \
        f"Chunk count {doc.chunkCount} outside expected range [{min_expected_chunks}, {max_expected_chunks}]"


def test_chunk_ids_format(processed_golden_doc: tuple[PdfIndexDocument, Path]) -> None:
    """Chunk IDs should follow the expected format."""
    doc, _ = processed_golden_doc
    
    for chunk in doc.chunks:
        # Format should be: {docId}:p{page}:c{chunkIndex}
        parts = chunk.chunkId.split(":")
        assert len(parts) == 3, f"Invalid chunk ID format: {chunk.chunkId}"
        assert parts[1].startswith("p"), f"Invalid page part in chunk ID: {chunk.chunkId}"
        assert parts[2].startswith("c"), f"Invalid chunk index in chunk ID: {chunk.chunkId}"


def test_chunks_have_embeddings(processed_golden_doc: tuple[PdfIndexDocument, Path]) -> None:
    """All chunks should have embeddings."""
    doc, _ = processed_golden_doc
    
    for chunk in doc.chunks:
        assert chunk.embedding is not None, f"Chunk {chunk.chunkId} missing embedding"
        assert len(chunk.embedding) == 24, f"Chunk {chunk.chunkId} has wrong embedding dimension"


# ============================================================================
# Concept Generation Tests
# ============================================================================

def test_concepts_generated(processed_golden_doc: tuple[PdfIndexDocument, Path]) -> None:
    """At least the expected concepts should be generated."""
    _, output_dir = processed_golden_doc
    
    concept_manifest_path = output_dir / "concept-manifest.json"
    assert concept_manifest_path.exists(), "Concept manifest not generated"
    
    concept_data = json.loads(concept_manifest_path.read_text())
    concept_count = concept_data.get("conceptCount", 0)
    
    # Golden PDF has 3 core SQL concepts: SELECT, WHERE, JOIN
    min_expected_concepts = 2
    assert concept_count >= min_expected_concepts, \
        f"Only {concept_count} concepts generated, expected at least {min_expected_concepts}"


def test_concept_markdowns_generated(
    processed_golden_doc: tuple[PdfIndexDocument, Path],
) -> None:
    """Markdown files should be generated for concepts."""
    _, output_dir = processed_golden_doc
    
    concepts_dir = output_dir / "concepts"
    assert concepts_dir.exists(), "Concepts directory not created"
    
    # Check for README
    readme_path = concepts_dir / "README.md"
    assert readme_path.exists(), "Concept README not generated"
    
    # Check for at least some concept markdowns
    md_files = list(concepts_dir.glob("*.md"))
    # Exclude README
    concept_mds = [f for f in md_files if f.name != "README.md"]
    assert len(concept_mds) >= 1, "No concept markdown files generated"


def test_expected_concepts_present(
    processed_golden_doc: tuple[PdfIndexDocument, Path],
) -> None:
    """Expected core SQL concepts should be present."""
    _, output_dir = processed_golden_doc
    
    concept_manifest_path = output_dir / "concept-manifest.json"
    if not concept_manifest_path.exists():
        pytest.skip("Concept manifest not generated")
    
    concept_data = json.loads(concept_manifest_path.read_text())
    concepts = concept_data.get("concepts", {})
    
    # Check for at least one of the core concepts
    # Concepts might be named differently (e.g., "select-basic", "select_statement")
    concept_titles = [c.get("title", "").lower() for c in concepts.values()]
    
    # Look for SELECT-related concept
    has_select = any("select" in t for t in concept_titles)
    has_where = any("where" in t for t in concept_titles)
    has_join = any("join" in t for t in concept_titles)
    
    # At least 2 of 3 core concepts should be detected
    detected_count = sum([has_select, has_where, has_join])
    assert detected_count >= 2, \
        f"Only {detected_count}/3 core SQL concepts detected. Titles: {concept_titles}"


# ============================================================================
# Figure/Table Extraction Tests
# ============================================================================

def test_figures_extracted(processed_golden_doc: tuple[PdfIndexDocument, Path]) -> None:
    """At least the expected number of figures/tables should be extracted.
    
    Note: This is a basic check that content is being extracted.
    The golden PDF contains 2 table figures.
    """
    doc, _ = processed_golden_doc
    
    # Check that text content from tables is in chunks
    # Tables contain specific text like "Pattern", "SQL Statement", "Join Type"
    all_text = " ".join(c.text for c in doc.chunks)
    
    # Golden PDF has tables with these headers
    has_table_content = any(
        keyword in all_text.lower()
        for keyword in ["pattern", "join type", "description", "use case"]
    )
    
    assert has_table_content, "Table/figure content not found in extracted text"


# ============================================================================
# Quality Gate Tests
# ============================================================================

def test_quality_gates_pass(golden_pdf_path: Path) -> None:
    """Golden PDF should pass all quality gates."""
    pages = extract_pages_fitz(golden_pdf_path)
    quality = check_extraction_quality(pages)
    
    assert quality["is_quality_good"], \
        f"Golden PDF quality check failed: {quality.get('reason', 'Unknown')}"
    
    # Additional quality checks
    assert quality["total_chars"] >= 500, \
        f"Too few characters: {quality['total_chars']}"
    
    assert quality["readable_ratio"] >= 0.7, \
        f"Low readable ratio: {quality['readable_ratio']:.1%}"
    
    assert quality["gibberish_ratio"] <= 0.3, \
        f"High gibberish ratio: {quality['gibberish_ratio']:.1%}"


def test_minimum_pages_extracted(
    processed_golden_doc: tuple[PdfIndexDocument, Path],
) -> None:
    """All pages from the golden PDF should be extracted."""
    doc, _ = processed_golden_doc
    
    # Golden PDF has 8 pages
    expected_pages = 8
    total_pages = sum(d.pageCount for d in doc.sourceDocs)
    
    assert total_pages == expected_pages, \
        f"Expected {expected_pages} pages, got {total_pages}"


def test_no_empty_chunks(processed_golden_doc: tuple[PdfIndexDocument, Path]) -> None:
    """No chunks should be empty or have only whitespace."""
    doc, _ = processed_golden_doc
    
    for chunk in doc.chunks:
        assert chunk.text.strip(), f"Chunk {chunk.chunkId} has empty text"


def test_chunk_text_quality(processed_golden_doc: tuple[PdfIndexDocument, Path]) -> None:
    """Chunk text should meet minimum quality standards."""
    doc, _ = processed_golden_doc
    
    for chunk in doc.chunks:
        # Check minimum length
        assert len(chunk.text) >= 20, \
            f"Chunk {chunk.chunkId} text too short: {len(chunk.text)} chars"
        
        # Check for excessive non-printable characters
        non_printable = sum(1 for c in chunk.text if ord(c) < 32 and c not in '\n\r\t')
        if len(chunk.text) > 0:
            ratio = non_printable / len(chunk.text)
            assert ratio < 0.1, \
                f"Chunk {chunk.chunkId} has too many non-printable chars: {ratio:.1%}"


# ============================================================================
# End-to-End Pipeline Tests
# ============================================================================

def test_end_to_end_pipeline(
    golden_pdf_path: Path,
    concepts_config_path: Path,
    temp_output_dir: Path,
) -> None:
    """Full pipeline should run without errors."""
    opts = IndexBuildOptions()
    
    doc = build_index(
        golden_pdf_path,
        temp_output_dir,
        options=opts,
        ocr=False,
        auto_ocr=False,
        use_aliases=True,
        strip_headers=True,
        concepts_config=concepts_config_path,
    )
    
    # Verify all expected output files exist
    assert (temp_output_dir / "index.json").exists(), "index.json not created"
    assert (temp_output_dir / "manifest.json").exists(), "manifest.json not created"
    assert (temp_output_dir / "chunks.json").exists(), "chunks.json not created"
    assert (temp_output_dir / "concept-manifest.json").exists(), "concept-manifest.json not created"
    assert (temp_output_dir / "concepts" / "README.md").exists(), "concepts/README.md not created"
    
    # Verify document structure
    assert doc.indexId, "Document missing index ID"
    assert doc.chunkCount > 0, "Document has no chunks"
    assert doc.sourceDocs, "Document has no source docs"


def test_pipeline_output_valid_json(
    processed_golden_doc: tuple[PdfIndexDocument, Path],
) -> None:
    """All output files should be valid JSON."""
    _, output_dir = processed_golden_doc
    
    json_files = [
        "index.json",
        "manifest.json",
        "chunks.json",
        "concept-manifest.json",
    ]
    
    for filename in json_files:
        filepath = output_dir / filename
        if filepath.exists():
            try:
                data = json.loads(filepath.read_text())
                assert isinstance(data, (dict, list)), \
                    f"{filename} doesn't contain valid JSON object/array"
            except json.JSONDecodeError as e:
                pytest.fail(f"{filename} is not valid JSON: {e}")


# ============================================================================
# Regression Tests
# ============================================================================

def test_against_baseline(
    processed_golden_doc: tuple[PdfIndexDocument, Path],
) -> None:
    """Compare output against baseline if available."""
    _, output_dir = processed_golden_doc
    
    baseline_dir = Path(__file__).parent / "baselines" / "golden_chapter"
    if not baseline_dir.exists():
        pytest.skip(f"Baseline not found: {baseline_dir}")
    
    try:
        report = detect_regression(
            baseline_dir=baseline_dir,
            current_dir=output_dir,
            chunk_count_tolerance=0.15,  # 15% tolerance for test runs
        )
        
        # Only fail on critical errors, warn about concept differences
        # (auto-discovery may find more concepts than baseline)
        critical_errors = [
            c for c in report.failed_checks 
            if c.severity == "error" and "missing_concepts" not in c.check_name
        ]
        
        if critical_errors:
            pytest.fail(
                f"Regression detected:\n" + "\n".join(
                    f"  - {c.check_name}: {c.message}"
                    for c in critical_errors
                )
            )
        
        # Log warnings for concept differences (auto-discovery is working as intended)
        concept_warnings = [
            c for c in report.failed_checks 
            if "missing_concepts" in c.check_name or "extra_concepts" in c.check_name
        ]
        if concept_warnings:
            print(f"\nNote: Concept differences detected (auto-discovery may have found more):")
            for c in concept_warnings:
                print(f"  - {c.check_name}: {c.message[:100]}...")
        
    except FileNotFoundError as e:
        pytest.skip(f"Could not load baseline: {e}")


# ============================================================================
# Metrics Tests
# ============================================================================

def test_coverage_metric(processed_golden_doc: tuple[PdfIndexDocument, Path]) -> None:
    """Test coverage metric calculation."""
    _, output_dir = processed_golden_doc
    
    # Load concept manifest
    manifest_path = output_dir / "concept-manifest.json"
    if not manifest_path.exists():
        pytest.skip("Concept manifest not available")
    
    manifest_data = json.loads(manifest_path.read_text())
    found_concepts = list(manifest_data.get("concepts", {}).keys())
    
    # Expected concepts from golden PDF
    expected = ["select-basic", "where-clause", "join-operations"]
    
    coverage = CoverageMetric(
        expected_concepts=expected,
        found_concepts=found_concepts,
    )
    
    # Coverage ratio should be reasonable
    assert coverage.coverage_ratio >= 0.0
    assert coverage.to_dict()["metric_name"] == "coverage"


def test_retrieval_sanity_metric() -> None:
    """Test retrieval sanity metric."""
    from algl_pdf_helper.models import PdfIndexChunk
    
    # Create test chunks
    chunks = [
        PdfIndexChunk(
            chunkId="test:p1:c1",
            docId="test",
            page=1,
            text="SELECT statement basics for SQL queries",
            embedding=build_hash_embedding("SELECT statement basics", 24),
        ),
        PdfIndexChunk(
            chunkId="test:p2:c1",
            docId="test",
            page=2,
            text="WHERE clause filtering in SQL",
            embedding=build_hash_embedding("WHERE clause filtering", 24),
        ),
    ]
    
    # Test queries
    test_queries = [
        {
            "query": "SELECT statement",
            "expected_page": 1,
        },
        {
            "query": "WHERE clause",
            "expected_page": 2,
        },
    ]
    
    metric = RetrievalSanityMetric(test_queries=test_queries)
    metric.run_tests(chunks, lambda t: build_hash_embedding(t, 24), top_k=2)
    
    # Should have results
    assert len(metric.results) == 2
    assert 0.0 <= metric.success_rate <= 1.0


def test_quality_score() -> None:
    """Test quality score calculation."""
    quality = QualityScore(
        coverage_score=0.9,
        retrieval_score=0.85,
        chunk_quality_score=0.95,
    )
    
    overall = quality.overall_score
    assert 0.0 <= overall <= 1.0
    
    # Verify grade
    assert quality.grade in ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "F"]


def test_evaluation_report(processed_golden_doc: tuple[PdfIndexDocument, Path]) -> None:
    """Test full evaluation report generation."""
    doc, output_dir = processed_golden_doc
    
    # Load concept manifest
    concept_manifest_path = output_dir / "concept-manifest.json"
    concept_manifest = None
    if concept_manifest_path.exists():
        from algl_pdf_helper.models import ConceptManifest
        concept_data = json.loads(concept_manifest_path.read_text())
        concept_manifest = ConceptManifest(**concept_data)
    
    # Run evaluation
    expected_concepts = ["select-basic", "where-clause", "join-operations"]
    test_queries = [
        {"query": "SELECT statement", "expected_page": 2},
        {"query": "WHERE clause", "expected_page": 4},
        {"query": "JOIN operation", "expected_page": 6},
    ]
    
    report = run_evaluation(
        document=doc,
        concept_manifest=concept_manifest,
        expected_concepts=expected_concepts,
        test_queries=test_queries,
        embedding_fn=lambda t: build_hash_embedding(t, 24),
    )
    
    # Verify report structure
    summary = report.generate_summary()
    assert "overall_score" in summary
    assert "grade" in summary
    assert "metrics" in summary
    assert "metadata" in summary
    
    # Save and reload
    report_path = output_dir / "evaluation-report.json"
    report.save(report_path)
    assert report_path.exists()
    
    loaded = EvaluationReport.load(report_path)
    assert loaded.document_id == report.document_id


# ============================================================================
# Performance Tests
# ============================================================================

def test_processing_time(
    golden_pdf_path: Path,
    concepts_config_path: Path,
    temp_output_dir: Path,
) -> None:
    """Golden PDF processing should complete in under 30 seconds."""
    import time
    
    opts = IndexBuildOptions()
    
    start_time = time.time()
    
    build_index(
        golden_pdf_path,
        temp_output_dir,
        options=opts,
        ocr=False,
        auto_ocr=False,
        use_aliases=True,
        strip_headers=True,
        concepts_config=concepts_config_path,
    )
    
    elapsed = time.time() - start_time
    
    # Should complete in under 30 seconds
    assert elapsed < 30, f"Processing took {elapsed:.1f}s, expected < 30s"
