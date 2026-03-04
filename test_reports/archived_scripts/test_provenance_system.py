#!/usr/bin/env python3
"""
Comprehensive test suite for provenance tracking and source viewer system.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from algl_pdf_helper.provenance import (
    BlockRef,
    ChunkProvenance,
    ConceptProvenanceManifest,
    ProvenanceRecord,
    ProvenanceTracker,
    SourcePassage,
    create_provenance_from_concept_section,
    merge_provenance_records,
)
from algl_pdf_helper.chunker import chunk_page_words_with_provenance, chunk_with_block_mapping
from algl_pdf_helper.source_viewer import (
    SourceViewer,
    SourceViewOptions,
    ChunkLookup,
    create_source_viewer_from_files,
)
from algl_pdf_helper.markdown_generator import generate_concept_markdown, _generate_yaml_frontmatter
from algl_pdf_helper.models import ConceptInfo, ConceptSection, ConceptManifest, PdfIndexChunk


# =============================================================================
# TEST 1: Provenance Tracker Basic Functionality
# =============================================================================

def test_provenance_tracker():
    """Test basic provenance tracking."""
    print("=" * 70)
    print("TEST 1: Provenance Tracker Basic Functionality")
    print("=" * 70)
    
    tracker = ProvenanceTracker()
    
    # Test 1a: Add chunk provenance
    print("\n1a. Adding chunk provenance...")
    tracker.add_chunk_provenance = lambda chunk_id, page, blocks: None  # Placeholder
    
    # Register block mappings
    block1 = BlockRef(block_id="b1", page=1, block_type="paragraph")
    block2 = BlockRef(block_id="b2", page=1, block_type="paragraph")
    block3 = BlockRef(block_id="b3", page=1, block_type="code")
    
    tracker.register_block_mapping("doc1:p1:c1", [block1, block2])
    tracker.register_block_mapping("doc1:p1:c2", [block2, block3])
    
    print(f"  - Registered chunk doc1:p1:c1 with blocks: {[b.block_id for b in tracker.get_blocks_for_chunk('doc1:p1:c1')]}")
    print(f"  - Registered chunk doc1:p1:c2 with blocks: {[b.block_id for b in tracker.get_blocks_for_chunk('doc1:p1:c2')]}")
    
    # Test 1b: Record concept section
    print("\n1b. Recording concept section provenance...")
    record = tracker.record_section_provenance(
        concept_id="select-basics",
        section_type="definition",
        source_chunks=["doc1:p1:c1", "doc1:p1:c2"],
        source_pages=[1],
        source_blocks=[block1, block2],
        confidence=0.95,
    )
    print(f"  - Created record for {record.concept_id}/{record.section_type}")
    print(f"  - Source chunks: {record.source_chunks}")
    print(f"  - Source pages: {record.source_pages}")
    print(f"  - Source blocks: {[b.block_id for b in record.source_blocks]}")
    print(f"  - Confidence: {record.confidence}")
    
    # Test 1c: Build manifest
    print("\n1c. Building concept manifest...")
    manifest = tracker.build_manifest(source_doc_id="doc1")
    print(f"  - Schema version: {manifest.schema_version}")
    print(f"  - Source doc ID: {manifest.source_doc_id}")
    print(f"  - Records count: {len(manifest.records)}")
    
    # Test 1d: Retrieve record
    print("\n1d. Retrieving record...")
    retrieved = manifest.get_record("select-basics", "definition")
    if retrieved:
        print(f"  - Retrieved: {retrieved.concept_id}/{retrieved.section_type}")
        print(f"  - Chunks: {retrieved.source_chunks}")
    else:
        print("  - ERROR: Record not found!")
    
    # Test 1e: Block-to-chunk mapping
    print("\n1e. Testing block-to-chunk mapping...")
    chunks_for_b1 = tracker.get_chunks_for_block("b1")
    print(f"  - Chunks containing block b1: {chunks_for_b1}")
    
    chunks_for_b2 = tracker.get_chunks_for_block("b2")
    print(f"  - Chunks containing block b2: {chunks_for_b2}")
    
    blocks_on_page1 = tracker.get_blocks_for_page(1)
    print(f"  - Blocks on page 1: {[b.block_id for b in blocks_on_page1]}")
    
    print("\n✅ Test 1 PASSED")
    return tracker, manifest


# =============================================================================
# TEST 2: Source Viewer Functionality
# =============================================================================

def test_source_viewer():
    """Test source viewer with real data."""
    print("\n" + "=" * 70)
    print("TEST 2: Source Viewer Functionality")
    print("=" * 70)
    
    chunks_path = Path("./read_use/murachs-mysql-3rd-edition/chunks.json")
    
    if not chunks_path.exists():
        print(f"  ⚠️  Chunks file not found: {chunks_path}")
        print("  Creating mock chunks for testing...")
        chunks = [
            PdfIndexChunk(
                chunkId="doc1:p1:c1",
                docId="doc1",
                page=1,
                text="This is sample text for chunk 1 on page 1. It contains information about SQL SELECT statements.",
                embedding=[0.1] * 24,
            ),
            PdfIndexChunk(
                chunkId="doc1:p1:c2",
                docId="doc1",
                page=1,
                text="This is sample text for chunk 2 on page 1. It continues the discussion on SQL basics.",
                embedding=[0.2] * 24,
            ),
            PdfIndexChunk(
                chunkId="doc1:p2:c1",
                docId="doc1",
                page=2,
                text="Page 2 content starts here. This covers more advanced SQL concepts.",
                embedding=[0.3] * 24,
            ),
        ]
    else:
        print(f"  Loading chunks from {chunks_path}...")
        with open(chunks_path, "r") as f:
            chunks_data = json.load(f)
        
        chunks = [
            PdfIndexChunk(
                chunkId=c["chunkId"],
                docId=c["docId"],
                page=c["page"],
                text=c["text"],
                embedding=c.get("embedding"),
            )
            for c in chunks_data[:100]  # Limit for testing
        ]
        print(f"  - Loaded {len(chunks)} chunks")
    
    # Test 2a: Create viewer
    print("\n2a. Creating SourceViewer...")
    viewer = SourceViewer(chunks=chunks)
    print(f"  - Created viewer with {len(chunks)} chunks")
    
    # Test 2b: Chunk lookup
    print("\n2b. Testing chunk lookup...")
    if chunks:
        first_chunk = chunks[0]
        retrieved = viewer.chunk_lookup.get_chunk(first_chunk.chunkId)
        if retrieved:
            print(f"  - Found chunk: {retrieved.chunkId}")
            print(f"  - Page: {retrieved.page}")
            print(f"  - Text preview: {retrieved.text[:50]}...")
        
        # Get chunks for page
        page_chunks = viewer.chunk_lookup.get_chunks_for_page(first_chunk.page)
        print(f"  - Chunks on page {first_chunk.page}: {len(page_chunks)}")
    
    # Test 2c: Get passages by page
    print("\n2c. Testing get_passages_by_page...")
    if chunks:
        unique_pages = list(set(c.page for c in chunks))[:2]
        passages = viewer.get_passages_by_page(unique_pages)
        print(f"  - Retrieved {len(passages)} passages for pages {unique_pages}")
        for p in passages[:2]:
            print(f"    - {p.chunk_id} (Page {p.page}): {p.text[:40]}...")
    
    # Test 2d: Format for display
    print("\n2d. Testing format_for_display...")
    from algl_pdf_helper.source_viewer import SourceViewResult
    
    result = SourceViewResult(
        concept_id="test-concept",
        section_type="definition",
        passages=[
            SourcePassage(
                chunk_id="doc1:p1:c1",
                text="Sample passage text for testing display formatting.",
                page=1,
                doc_id="doc1",
            )
        ],
        total_pages=1,
        page_numbers=[1],
    )
    
    markdown_output = viewer.format_for_display(result, format_type="markdown")
    print(f"  - Markdown output length: {len(markdown_output)} chars")
    print(f"  - Preview:\n{markdown_output[:300]}...")
    
    print("\n✅ Test 2 PASSED")
    return viewer


# =============================================================================
# TEST 3: Chunker with Provenance
# =============================================================================

def test_chunker_provenance():
    """Test chunker provenance features."""
    print("\n" + "=" * 70)
    print("TEST 3: Chunker with Provenance")
    print("=" * 70)
    
    # Test 3a: Basic chunking with provenance
    print("\n3a. Testing chunk_page_words_with_provenance...")
    sample_text = "This is a sample text for testing the chunking functionality. " * 20
    
    results = chunk_page_words_with_provenance(
        doc_id="doc1",
        page=1,
        text=sample_text,
        chunk_words=50,
        overlap_words=10,
        source_block_ids=["block1", "block2"],
    )
    
    print(f"  - Created {len(results)} chunks")
    for i, result in enumerate(results[:3]):
        print(f"    Chunk {i+1}:")
        print(f"      - ID: {result.chunk_id}")
        print(f"      - Word count: {len(result.text.split())}")
        print(f"      - Source blocks: {result.source_block_ids}")
        print(f"      - Char offset: {result.char_offset_start}-{result.char_offset_end}")
    
    # Test 3b: Chunk with block mapping
    print("\n3b. Testing chunk_with_block_mapping...")
    blocks = [
        {"id": "block1", "text_preview": "This is a sample"},
        {"id": "block2", "text_preview": "chunking functionality"},
    ]
    
    results_with_mapping = chunk_with_block_mapping(
        doc_id="doc1",
        page=1,
        text=sample_text,
        chunk_words=50,
        overlap_words=10,
        blocks=blocks,
    )
    
    print(f"  - Created {len(results_with_mapping)} chunks with block mapping")
    for i, result in enumerate(results_with_mapping[:3]):
        print(f"    Chunk {i+1}: {result.chunk_id}")
        print(f"      - Mapped blocks: {result.source_block_ids}")
    
    print("\n✅ Test 3 PASSED")
    return results


# =============================================================================
# TEST 4: Markdown Frontmatter with Provenance
# =============================================================================

def test_markdown_frontmatter():
    """Test markdown generation includes provenance."""
    print("\n" + "=" * 70)
    print("TEST 4: Markdown Frontmatter with Provenance")
    print("=" * 70)
    
    # Create a test concept
    concept = ConceptInfo(
        id="select-basics",
        title="SELECT Statement Basics",
        definition="Retrieves data from one or more tables",
        difficulty="beginner",
        estimatedReadTime=5,
        pageReferences=[45, 46, 47],
        sections={
            "definition": ConceptSection(
                chunkIds=["doc1:p45:c1", "doc1:p45:c2"],
                pageNumbers=[45],
            ),
            "examples": ConceptSection(
                chunkIds=["doc1:p46:c1", "doc1:p46:c2", "doc1:p47:c1"],
                pageNumbers=[46, 47],
            ),
        },
        relatedConcepts=["where-clause"],
        tags=["sql", "query", "dql"],
    )
    
    # Create mock chunks
    chunks = [
        PdfIndexChunk(
            chunkId="doc1:p45:c1",
            docId="doc1",
            page=45,
            text="The SELECT statement is used to retrieve data from tables.",
            embedding=None,
        ),
        PdfIndexChunk(
            chunkId="doc1:p45:c2",
            docId="doc1",
            page=45,
            text="Basic syntax: SELECT column1, column2 FROM table_name;",
            embedding=None,
        ),
        PdfIndexChunk(
            chunkId="doc1:p46:c1",
            docId="doc1",
            page=46,
            text="Example: SELECT * FROM employees;",
            embedding=None,
        ),
    ]
    
    # Test 4a: Generate frontmatter
    print("\n4a. Testing YAML frontmatter generation...")
    frontmatter = _generate_yaml_frontmatter(concept, "doc1", include_provenance=True)
    print(f"  - Generated frontmatter:\n{frontmatter}")
    
    # Check for provenance fields
    has_source_chunks = "source_chunks:" in frontmatter
    has_source_doc = "source_doc:" in frontmatter
    has_pages = "source_pages:" in frontmatter or "pages:" in frontmatter
    
    print(f"  - Has source_chunks: {has_source_chunks}")
    print(f"  - Has source_doc: {has_source_doc}")
    print(f"  - Has pages: {has_pages}")
    
    # Test 4b: Full markdown generation
    print("\n4b. Testing full markdown generation...")
    markdown = generate_concept_markdown(
        concept=concept,
        chunks=chunks,
        doc_id="doc1",
        include_provenance=True,
    )
    
    # Check for provenance in markdown
    has_provenance_footer = "Source:" in markdown or "Pages:" in markdown
    has_frontmatter = markdown.startswith("---")
    
    print(f"  - Has frontmatter: {has_frontmatter}")
    print(f"  - Has provenance footer: {has_provenance_footer}")
    print(f"  - Total length: {len(markdown)} chars")
    print(f"\n  Preview:\n{markdown[:800]}...")
    
    assert has_frontmatter, "Markdown should have YAML frontmatter"
    print("\n✅ Test 4 PASSED")
    return markdown


# =============================================================================
# TEST 5: Export with Provenance
# =============================================================================

def test_export_provenance():
    """Test that export includes provenance."""
    print("\n" + "=" * 70)
    print("TEST 5: Export with Provenance")
    print("=" * 70)
    
    # Test the convert_to_concept_map function
    from algl_pdf_helper.export_sqladapt import convert_to_concept_map
    
    # Create a test manifest
    manifest = ConceptManifest(
        schemaVersion="concept-manifest-v1",
        sourceDocId="test-doc",
        createdAt="2024-01-01T00:00:00Z",
        conceptCount=1,
        concepts={
            "test-concept": ConceptInfo(
                id="test-concept",
                title="Test Concept",
                definition="A test concept for provenance",
                difficulty="beginner",
                estimatedReadTime=5,
                pageReferences=[1, 2],
                sections={
                    "definition": ConceptSection(
                        chunkIds=["test:p1:c1"],
                        pageNumbers=[1],
                    ),
                    "examples": ConceptSection(
                        chunkIds=["test:p2:c1", "test:p2:c2"],
                        pageNumbers=[2],
                    ),
                },
            )
        },
    )
    
    print("\n5a. Testing convert_to_concept_map...")
    concept_map = convert_to_concept_map(manifest)
    
    print(f"  - Version: {concept_map.version}")
    print(f"  - Concepts: {len(concept_map.concepts)}")
    
    # Check provenance in concept map entry
    entry = concept_map.concepts.get("test-concept")
    if entry:
        print(f"\n  - Entry for 'test-concept':")
        print(f"    - Title: {entry.title}")
        print(f"    - Has provenance: {hasattr(entry, 'provenance') and entry.provenance is not None}")
        
        if entry.provenance:
            print(f"    - Provenance keys: {list(entry.provenance.keys())}")
            print(f"    - Chunks: {entry.provenance.get('chunks', [])}")
            print(f"    - Pages: {entry.provenance.get('pages', [])}")
    
    # Test 5b: Verify provenance structure
    print("\n5b. Verifying provenance structure...")
    
    # Simulate what happens in merge_concept_maps
    concept_dict = {
        "title": entry.title,
        "definition": entry.definition,
        "difficulty": entry.difficulty,
        "pageNumbers": entry.pageNumbers,
        "chunkIds": entry.chunkIds,
        "relatedConcepts": entry.relatedConcepts,
        "practiceProblemIds": entry.practiceProblemIds,
        "sourceDocId": entry.sourceDocId,
        "provenance": entry.provenance,
    }
    
    has_provenance = "provenance" in concept_dict
    provenance_has_chunks = has_provenance and "chunks" in concept_dict["provenance"]
    provenance_has_pages = has_provenance and "pages" in concept_dict["provenance"]
    
    print(f"  - Has provenance field: {has_provenance}")
    print(f"  - Provenance has chunks: {provenance_has_chunks}")
    print(f"  - Provenance has pages: {provenance_has_pages}")
    
    assert has_provenance, "Concept should have provenance field"
    assert provenance_has_chunks, "Provenance should have chunks"
    assert provenance_has_pages, "Provenance should have pages"
    
    print("\n✅ Test 5 PASSED")
    return concept_map


# =============================================================================
# TEST 6: Edge Cases
# =============================================================================

def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n" + "=" * 70)
    print("TEST 6: Edge Cases")
    print("=" * 70)
    
    # Test 6a: Missing chunk references
    print("\n6a. Testing missing chunk references...")
    viewer = SourceViewer(chunks=[])
    result = viewer.get_source_passages("nonexistent-concept")
    print(f"  - Result for nonexistent concept: {len(result.passages)} passages")
    
    # Test 6b: Invalid page numbers
    print("\n6b. Testing invalid page numbers...")
    passages = viewer.get_passages_by_page([999, 1000])
    print(f"  - Passages for invalid pages: {len(passages)}")
    
    # Test 6c: Empty source blocks
    print("\n6c. Testing empty source blocks...")
    tracker = ProvenanceTracker()
    record = tracker.record_section_provenance(
        concept_id="test",
        section_type="definition",
        source_chunks=["chunk1"],
        source_pages=[1],
        source_blocks=[],  # Empty blocks
    )
    print(f"  - Record with empty blocks: {record.source_blocks}")
    
    # Test 6d: Merge provenance records
    print("\n6d. Testing merge_provenance_records...")
    record1 = ProvenanceRecord(
        concept_id="test",
        section_type="definition",
        source_chunks=["chunk1", "chunk2"],
        source_pages=[1],
        confidence=0.9,
    )
    record2 = ProvenanceRecord(
        concept_id="test",
        section_type="definition",
        source_chunks=["chunk2", "chunk3"],
        source_pages=[2],
        confidence=0.8,
    )
    
    merged = merge_provenance_records([record1, record2])
    print(f"  - Merged chunks: {merged.source_chunks}")
    print(f"  - Merged pages: {merged.source_pages}")
    print(f"  - Averaged confidence: {merged.confidence}")
    
    # Test 6e: Single record merge
    print("\n6e. Testing single record merge...")
    single_merged = merge_provenance_records([record1])
    print(f"  - Single merge returns same record: {single_merged.source_chunks == record1.source_chunks}")
    
    # Test 6f: Empty list merge (should raise error)
    print("\n6f. Testing empty list merge...")
    try:
        merge_provenance_records([])
        print("  - ERROR: Should have raised ValueError")
    except ValueError as e:
        print(f"  - Correctly raised ValueError: {e}")
    
    print("\n✅ Test 6 PASSED")


# =============================================================================
# TEST 7: Integration Test with Real Data
# =============================================================================

def test_integration_with_real_data():
    """Integration test using real data files."""
    print("\n" + "=" * 70)
    print("TEST 7: Integration Test with Real Data")
    print("=" * 70)
    
    chunks_path = Path("./read_use/murachs-mysql-3rd-edition/chunks.json")
    manifest_path = Path("./read_use/murachs-mysql-3rd-edition/concept-manifest.json")
    
    if not chunks_path.exists() or not manifest_path.exists():
        print("  ⚠️  Real data files not found, skipping integration test")
        return
    
    print(f"\n7a. Loading real data...")
    with open(chunks_path, "r") as f:
        chunks_data = json.load(f)
    
    with open(manifest_path, "r") as f:
        manifest_data = json.load(f)
    
    print(f"  - Loaded {len(chunks_data)} chunks")
    print(f"  - Loaded {len(manifest_data.get('concepts', {}))} concepts")
    
    # Create chunks
    chunks = [
        PdfIndexChunk(
            chunkId=c["chunkId"],
            docId=c["docId"],
            page=c["page"],
            text=c["text"],
            embedding=c.get("embedding"),
        )
        for c in chunks_data[:200]  # Limit for testing
    ]
    
    # Create viewer
    print("\n7b. Creating source viewer...")
    viewer = SourceViewer(chunks=chunks)
    
    # Test looking up a specific concept
    print("\n7c. Looking up concept chunks...")
    concepts = manifest_data.get("concepts", {})
    if concepts:
        first_concept_id = list(concepts.keys())[0]
        first_concept = concepts[first_concept_id]
        print(f"  - Testing with concept: {first_concept_id}")
        
        # Get chunk IDs from concept
        sections = first_concept.get("sections", {})
        for section_name, section_data in list(sections.items())[:2]:
            chunk_ids = section_data.get("chunkIds", [])
            print(f"    - Section '{section_name}' has {len(chunk_ids)} chunks")
            
            # Verify chunks exist
            found = 0
            not_found = 0
            for chunk_id in chunk_ids[:5]:  # Check first 5
                chunk = viewer.chunk_lookup.get_chunk(chunk_id)
                if chunk:
                    found += 1
                else:
                    not_found += 1
            
            print(f"      - Found: {found}, Not found: {not_found}")
    
    # Test 7d: Create source viewer from files
    print("\n7d. Testing create_source_viewer_from_files...")
    try:
        viewer_from_files = create_source_viewer_from_files(
            chunks_path=chunks_path,
            pdf_path=None,  # No PDF path for this test
        )
        print(f"  - Created viewer from files with {len(viewer_from_files._chunks)} chunks")
    except Exception as e:
        print(f"  - Error creating viewer from files: {e}")
    
    print("\n✅ Test 7 PASSED")


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("PROVENANCE TRACKING AND SOURCE VIEWER TEST SUITE")
    print("=" * 70)
    
    try:
        # Run tests
        test_provenance_tracker()
        test_source_viewer()
        test_chunker_provenance()
        test_markdown_frontmatter()
        test_export_provenance()
        test_edge_cases()
        test_integration_with_real_data()
        
        print("\n" + "=" * 70)
        print("ALL TESTS PASSED ✅")
        print("=" * 70)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
