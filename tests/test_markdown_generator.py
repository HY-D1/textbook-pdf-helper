from __future__ import annotations

from pathlib import Path

import pytest

from algl_pdf_helper.markdown_generator import (
    format_page_links,
    generate_concept_markdown,
    generate_index_readme,
    get_chunk_by_id,
    save_concept_markdown,
)
from algl_pdf_helper.models import ConceptInfo, ConceptManifest, ConceptSection, PdfIndexChunk


def test_get_chunk_by_id() -> None:
    """Test finding a chunk by ID."""
    chunks = [
        PdfIndexChunk(chunkId="doc1:p1:c1", docId="doc1", page=1, text="chunk 1"),
        PdfIndexChunk(chunkId="doc1:p1:c2", docId="doc1", page=1, text="chunk 2"),
    ]
    
    found = get_chunk_by_id(chunks, "doc1:p1:c2")
    assert found is not None
    assert found.text == "chunk 2"
    
    not_found = get_chunk_by_id(chunks, "doc1:p99:c99")
    assert not_found is None


def test_format_page_links() -> None:
    """Test formatting page reference links."""
    result = format_page_links([45, 46, 47], "doc1")
    assert "Page 45" in result
    assert "Page 46" in result
    assert "Page 47" in result
    
    # Test empty list
    result = format_page_links([], "doc1")
    assert result == ""


def test_generate_concept_markdown() -> None:
    """Test generating markdown for a concept."""
    chunks = [
        PdfIndexChunk(chunkId="doc1:p1:c1", docId="doc1", page=1, text="This is the definition."),
        PdfIndexChunk(chunkId="doc1:p2:c1", docId="doc1", page=2, text="Example 1 code here."),
        PdfIndexChunk(chunkId="doc1:p2:c2", docId="doc1", page=2, text="Example 2 code here."),
    ]
    
    concept = ConceptInfo(
        id="select-basic",
        title="SELECT Statement Basics",
        definition="Retrieves data from tables.",
        difficulty="beginner",
        estimatedReadTime=5,
        pageReferences=[1, 2],
        sections={
            "definition": ConceptSection(
                chunkIds=["doc1:p1:c1"],
                pageNumbers=[1],
            ),
            "examples": ConceptSection(
                chunkIds=["doc1:p2:c1", "doc1:p2:c2"],
                pageNumbers=[2],
            ),
        },
        relatedConcepts=["where-clause"],
        tags=["sql", "query"],
    )
    
    markdown = generate_concept_markdown(concept, chunks, "doc1")
    
    # Check title
    assert "# SELECT Statement Basics" in markdown
    
    # Check metadata
    assert "Difficulty:** Beginner" in markdown
    assert "Estimated Read Time:** 5 minutes" in markdown
    
    # Check overview
    assert "## Overview" in markdown
    assert "Retrieves data from tables." in markdown
    
    # Check sections
    assert "## Definition" in markdown
    assert "This is the definition." in markdown
    assert "## Examples" in markdown
    assert "Example 1 code here." in markdown
    assert "Example 2 code here." in markdown
    
    # Check related concepts
    assert "## Related Concepts" in markdown
    assert "[where-clause]" in markdown
    
    # Check tags
    assert "`sql`" in markdown
    assert "`query`" in markdown


def test_generate_concept_markdown_no_sections(tmp_path: Path) -> None:
    """Test generating markdown for a concept with no matching chunks."""
    chunks = []
    
    concept = ConceptInfo(
        id="empty-concept",
        title="Empty Concept",
        difficulty="beginner",
        pageReferences=[99],
        sections={
            "definition": ConceptSection(
                chunkIds=["doc1:p99:c1"],
                pageNumbers=[99],
            ),
        },
    )
    
    markdown = generate_concept_markdown(concept, chunks, "doc1")
    
    assert "# Empty Concept" in markdown
    assert "*Content not available in source.*" in markdown


def test_save_concept_markdown(tmp_path: Path) -> None:
    """Test saving markdown to file."""
    chunks = [
        PdfIndexChunk(chunkId="doc1:p1:c1", docId="doc1", page=1, text="content"),
    ]
    
    concept = ConceptInfo(
        id="test-concept",
        title="Test Concept",
        sections={
            "definition": ConceptSection(
                chunkIds=["doc1:p1:c1"],
                pageNumbers=[1],
            ),
        },
    )
    
    out_dir = tmp_path / "concepts"
    file_path = save_concept_markdown(concept, chunks, "doc1", out_dir)
    
    assert file_path.exists()
    assert file_path.name == "test-concept.md"
    content = file_path.read_text()
    assert "# Test Concept" in content


def test_generate_index_readme(tmp_path: Path) -> None:
    """Test generating the concepts README index."""
    manifest = ConceptManifest(
        schemaVersion="concept-manifest-v1",
        sourceDocId="doc1",
        createdAt="2024-01-01T00:00:00Z",
        conceptCount=3,
        concepts={
            "select-basic": ConceptInfo(
                id="select-basic",
                title="SELECT Basics",
                difficulty="beginner",
                estimatedReadTime=5,
            ),
            "joins-intro": ConceptInfo(
                id="joins-intro",
                title="Introduction to JOINs",
                difficulty="intermediate",
                estimatedReadTime=10,
            ),
            "subqueries": ConceptInfo(
                id="subqueries",
                title="Subqueries",
                difficulty="advanced",
                estimatedReadTime=15,
            ),
        },
    )
    
    out_path = tmp_path / "README.md"
    generate_index_readme(manifest, out_path)
    
    content = out_path.read_text()
    
    # Check header
    assert "# Concept Library" in content
    assert "**Total Concepts:** 3" in content
    
    # Check difficulty sections
    assert "### 🟢 Beginner" in content
    assert "### 🟡 Intermediate" in content
    assert "### 🔴 Advanced" in content
    
    # Check concept links
    assert "[SELECT Basics]" in content
    assert "[Introduction to JOINs]" in content
    assert "[Subqueries]" in content
    
    # Check read times
    assert "5 min" in content
    assert "10 min" in content
    assert "15 min" in content


def test_generate_concept_markdown_difficulty_emoji() -> None:
    """Test that correct difficulty emoji is used."""
    chunks = []
    
    for difficulty, expected_emoji in [
        ("beginner", "🟢"),
        ("intermediate", "🟡"),
        ("advanced", "🔴"),
        ("unknown", "⚪"),
    ]:
        concept = ConceptInfo(
            id=f"test-{difficulty}",
            title=f"Test {difficulty}",
            difficulty=difficulty,
            sections={},
        )
        
        markdown = generate_concept_markdown(concept, chunks, "doc1")
        assert expected_emoji in markdown
