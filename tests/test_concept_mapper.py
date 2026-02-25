from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from algl_pdf_helper.concept_mapper import (
    build_concept_manifest,
    find_concepts_config,
    get_chunks_for_pages,
    load_concepts_config,
    save_concept_manifest,
)
from algl_pdf_helper.models import ConceptManifest, PdfIndexChunk


def test_load_concepts_config(tmp_path: Path) -> None:
    """Test loading a valid concepts config file."""
    config_path = tmp_path / "concepts.yaml"
    config_data = {
        "concepts": {
            "test-concept": {
                "title": "Test Concept",
                "definition": "A test concept",
                "sections": {
                    "definition": [1, 2],
                    "examples": [3],
                },
            }
        }
    }
    config_path.write_text(yaml.dump(config_data))
    
    loaded = load_concepts_config(config_path)
    assert "concepts" in loaded
    assert "test-concept" in loaded["concepts"]
    assert loaded["concepts"]["test-concept"]["title"] == "Test Concept"


def test_load_concepts_config_not_found() -> None:
    """Test loading a non-existent config file."""
    with pytest.raises(FileNotFoundError):
        load_concepts_config(Path("/nonexistent/concepts.yaml"))


def test_load_concepts_config_invalid() -> None:
    """Test loading an invalid config file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml.dump({"invalid": "data"}))
        f.flush()
        config_path = Path(f.name)
    
    try:
        with pytest.raises(ValueError, match="must have 'concepts' key"):
            load_concepts_config(config_path)
    finally:
        config_path.unlink()


def test_get_chunks_for_pages() -> None:
    """Test filtering chunks by page numbers."""
    chunks = [
        PdfIndexChunk(chunkId="doc1:p1:c1", docId="doc1", page=1, text="page 1 chunk 1"),
        PdfIndexChunk(chunkId="doc1:p1:c2", docId="doc1", page=1, text="page 1 chunk 2"),
        PdfIndexChunk(chunkId="doc1:p2:c1", docId="doc1", page=2, text="page 2 chunk 1"),
        PdfIndexChunk(chunkId="doc1:p3:c1", docId="doc1", page=3, text="page 3 chunk 1"),
    ]
    
    result = get_chunks_for_pages(chunks, [1, 3], "doc1")
    assert len(result) == 3
    assert all(c.page in [1, 3] for c in result)
    
    # Test with no doc_id filter
    result = get_chunks_for_pages(chunks, [2])
    assert len(result) == 1
    assert result[0].page == 2


def test_build_concept_manifest() -> None:
    """Test building a concept manifest from config and chunks."""
    chunks = [
        PdfIndexChunk(chunkId="doc1:p1:c1", docId="doc1", page=1, text="definition text"),
        PdfIndexChunk(chunkId="doc1:p2:c1", docId="doc1", page=2, text="example 1"),
        PdfIndexChunk(chunkId="doc1:p2:c2", docId="doc1", page=2, text="example 2"),
    ]
    
    config = {
        "concepts": {
            "test-concept": {
                "title": "Test Concept",
                "definition": "A test concept",
                "difficulty": "beginner",
                "estimatedReadTime": 5,
                "sections": {
                    "definition": [1],
                    "examples": [2],
                },
                "relatedConcepts": ["other-concept"],
                "tags": ["test", "sql"],
            }
        }
    }
    
    manifest = build_concept_manifest(
        concepts_config=config,
        chunks=chunks,
        source_doc_id="doc1",
        created_at="2024-01-01T00:00:00Z",
    )
    
    assert manifest.schemaVersion == "concept-manifest-v1"
    assert manifest.sourceDocId == "doc1"
    assert manifest.conceptCount == 1
    assert "test-concept" in manifest.concepts
    
    concept = manifest.concepts["test-concept"]
    assert concept.title == "Test Concept"
    assert concept.difficulty == "beginner"
    assert concept.estimatedReadTime == 5
    assert concept.pageReferences == [1, 2]
    assert concept.relatedConcepts == ["other-concept"]
    assert concept.tags == ["test", "sql"]
    
    # Check sections
    assert "definition" in concept.sections
    assert "examples" in concept.sections
    assert concept.sections["definition"].chunkIds == ["doc1:p1:c1"]
    assert concept.sections["examples"].chunkIds == ["doc1:p2:c1", "doc1:p2:c2"]


def test_save_and_load_concept_manifest(tmp_path: Path) -> None:
    """Test saving and loading a concept manifest."""
    manifest = ConceptManifest(
        schemaVersion="concept-manifest-v1",
        sourceDocId="doc1",
        createdAt="2024-01-01T00:00:00Z",
        conceptCount=1,
    )
    
    output_path = tmp_path / "concept-manifest.json"
    save_concept_manifest(manifest, output_path)
    
    assert output_path.exists()
    
    loaded = json.loads(output_path.read_text())
    assert loaded["schemaVersion"] == "concept-manifest-v1"
    assert loaded["sourceDocId"] == "doc1"
    assert loaded["conceptCount"] == 1


def test_find_concepts_config_with_file(tmp_path: Path) -> None:
    """Test finding concepts config when PDF is a file."""
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_text("dummy")
    
    config_path = tmp_path / "concepts.yaml"
    config_path.write_text(yaml.dump({"concepts": {}}))
    
    found = find_concepts_config(pdf_path)
    assert found == config_path


def test_find_concepts_config_with_directory(tmp_path: Path) -> None:
    """Test finding concepts config in a directory."""
    subdir = tmp_path / "pdfs"
    subdir.mkdir()
    
    config_path = subdir / "concepts.yaml"
    config_path.write_text(yaml.dump({"concepts": {}}))
    
    found = find_concepts_config(subdir)
    assert found == config_path


def test_find_concepts_config_not_found(tmp_path: Path) -> None:
    """Test finding concepts config when it doesn't exist."""
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_text("dummy")
    
    found = find_concepts_config(pdf_path)
    assert found is None


def test_build_concept_manifest_single_page_sections() -> None:
    """Test building manifest with single page sections (int, not list)."""
    chunks = [
        PdfIndexChunk(chunkId="doc1:p1:c1", docId="doc1", page=1, text="content"),
    ]
    
    config = {
        "concepts": {
            "single-page": {
                "title": "Single Page Concept",
                "sections": {
                    "definition": 1,  # Single int, not list
                },
            }
        }
    }
    
    manifest = build_concept_manifest(config, chunks, "doc1")
    assert manifest.concepts["single-page"].sections["definition"].pageNumbers == [1]
