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
        with pytest.raises(ValueError, match="must have 'concepts' or 'textbooks' key"):
            load_concepts_config(config_path)
    finally:
        config_path.unlink()


def test_load_concepts_config_empty() -> None:
    """Test loading an empty config file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("")
        f.flush()
        config_path = Path(f.name)
    
    try:
        with pytest.raises(ValueError, match="Invalid concepts config: empty file"):
            load_concepts_config(config_path)
    finally:
        config_path.unlink()


def test_load_concepts_config_textbooks_format(tmp_path: Path) -> None:
    """Test loading a textbooks format config."""
    config_path = tmp_path / "concepts.yaml"
    config_data = {
        "schema_version": "2.0",
        "textbooks": {
            "test-book": {
                "title": "Test Book",
                "concepts": {
                    "nested-concept": {
                        "title": "Nested Concept",
                        "definition": "A nested concept",
                        "sections": {
                            "definition": [1],
                        },
                    }
                }
            }
        }
    }
    config_path.write_text(yaml.dump(config_data))
    
    loaded = load_concepts_config(config_path)
    assert "concepts" in loaded
    assert "nested-concept" in loaded["concepts"]
    assert loaded["concepts"]["nested-concept"]["title"] == "Nested Concept"


def test_load_concepts_config_textbooks_with_pdf_matching(tmp_path: Path) -> None:
    """Test textbooks format with PDF auto-matching."""
    config_path = tmp_path / "concepts.yaml"
    pdf_path = tmp_path / "test-book.pdf"
    pdf_path.write_text("dummy pdf content")
    
    config_data = {
        "schema_version": "2.0",
        "textbooks": {
            "test-book": {
                "title": "Test Book Title",
                "concepts": {
                    "matched-concept": {
                        "title": "Matched Concept",
                        "definition": "From matched textbook",
                        "sections": {"definition": [1]},
                    }
                }
            },
            "other-book": {
                "title": "Other Book",
                "concepts": {
                    "other-concept": {
                        "title": "Other Concept",
                        "definition": "From other textbook",
                        "sections": {"definition": [2]},
                    }
                }
            }
        }
    }
    config_path.write_text(yaml.dump(config_data))
    
    loaded = load_concepts_config(config_path, pdf_path)
    assert "concepts" in loaded
    # Should only have concepts from matched textbook
    assert "matched-concept" in loaded["concepts"]
    assert "other-concept" not in loaded["concepts"]
    assert loaded.get("matched_textbook") == "test-book"


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


def test_find_concepts_config_in_parent(tmp_path: Path) -> None:
    """Test finding concepts config in parent directory."""
    parent_dir = tmp_path / "parent"
    parent_dir.mkdir()
    child_dir = parent_dir / "child"
    child_dir.mkdir()
    
    config_path = parent_dir / "concepts.yaml"
    config_path.write_text(yaml.dump({"concepts": {}}))
    
    # Should find config in parent when looking at child
    found = find_concepts_config(child_dir)
    assert found == config_path


def test_find_concepts_config_not_found(tmp_path: Path, monkeypatch) -> None:
    """Test finding concepts config when it doesn't exist nearby.
    
    This test ensures that find_concepts_config does NOT fall back to CWD
    and returns None when no config exists near the input path.
    """
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_text("dummy")
    
    # Change to temp directory to avoid finding project's concepts.yaml
    monkeypatch.chdir(tmp_path)
    
    found = find_concepts_config(pdf_path)
    assert found is None


def test_find_concepts_config_no_cwd_fallback(monkeypatch, tmp_path) -> None:
    """Test that find_concepts_config does NOT fall back to CWD.
    
    This is a critical test to ensure deterministic, input-scoped config discovery.
    """
    # Create a "project" directory with a concepts.yaml
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    project_config = project_dir / "concepts.yaml"
    project_config.write_text(yaml.dump({"concepts": {"project-concept": {}}}))
    
    # Create an "input" directory elsewhere with its own PDF but NO config
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    pdf_path = input_dir / "document.pdf"
    pdf_path.write_text("dummy")
    
    # Run from the project directory (where concepts.yaml exists)
    monkeypatch.chdir(project_dir)
    
    # But search for config for the input PDF (which has no nearby config)
    found = find_concepts_config(pdf_path)
    
    # Should return None, NOT find the project directory's config
    assert found is None, f"Expected None but found {found}"


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


def test_find_concepts_config_edge_cases() -> None:
    """Test edge cases for config discovery."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        
        # Test with non-existent path (should not raise, just return None)
        non_existent = tmp_path / "does_not_exist.pdf"
        found = find_concepts_config(non_existent)
        # Non-existent file's parent might have a config, so this is fine


def test_find_concepts_config_boundary() -> None:
    """Test the exact boundary of config discovery.
    
    Discovery order:
    1. Same directory as input file (if file)
    2. Input directory itself (if directory)
    3. Parent directory of input
    
    Does NOT search beyond parent (no grandparent or deeper).
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        
        # Create a/b/c directory structure
        deep_dir = tmp_path / "a" / "b" / "c"
        deep_dir.mkdir(parents=True)
        
        # Config at grandparent level (a/) - should NOT be found from c/
        grandparent_config = tmp_path / "a" / "concepts.yaml"
        grandparent_config.write_text(yaml.dump({"concepts": {}}))
        
        # From c/, should NOT find config at a/ (too far)
        found = find_concepts_config(deep_dir)
        assert found is None, f"Expected None (grandparent too far), got {found}"
        
        # Config at parent level (a/b/) - SHOULD be found from c/
        parent_config = tmp_path / "a" / "b" / "concepts.yaml"
        parent_config.write_text(yaml.dump({"concepts": {}}))
        
        found = find_concepts_config(deep_dir)
        assert found == parent_config, f"Expected {parent_config}, got {found}"
        
        # Config at self level (a/b/c/) - takes priority over parent
        self_config = tmp_path / "a" / "b" / "c" / "concepts.yaml"
        self_config.write_text(yaml.dump({"concepts": {}}))
        
        found = find_concepts_config(deep_dir)
        assert found == self_config, f"Expected {self_config} (self takes priority), got {found}"
