"""
Tests for provenance tracking and source viewing functionality.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from algl_pdf_helper.provenance import (
    BlockRef,
    ChunkProvenance,
    ConceptProvenanceManifest,
    ProvenanceRecord,
    ProvenanceTracker,
    create_provenance_from_concept_section,
    merge_provenance_records,
)
from algl_pdf_helper.source_viewer import (
    ChunkLookup,
    SourceViewOptions,
    SourceViewer,
    create_source_viewer_from_files,
    get_page_open_url,
)
from algl_pdf_helper.models import PdfIndexChunk


# =============================================================================
# Provenance Model Tests
# =============================================================================

class TestBlockRef:
    """Tests for BlockRef model."""
    
    def test_block_ref_creation(self):
        """Test creating a BlockRef."""
        block = BlockRef(
            block_id="b12",
            page=5,
            block_type="paragraph"
        )
        assert block.block_id == "b12"
        assert block.page == 5
        assert block.block_type == "paragraph"
    
    def test_block_ref_equality(self):
        """Test BlockRef equality and hashing."""
        block1 = BlockRef(block_id="b1", page=1, block_type="text")
        block2 = BlockRef(block_id="b1", page=1, block_type="text")
        block3 = BlockRef(block_id="b2", page=1, block_type="text")
        
        assert block1 == block2
        assert block1 != block3
        assert hash(block1) == hash(block2)
    
    def test_block_ref_model_dump(self):
        """Test BlockRef serialization."""
        block = BlockRef(block_id="b5", page=3, block_type="table")
        data = block.model_dump()
        
        assert data["block_id"] == "b5"
        assert data["page"] == 3
        assert data["block_type"] == "table"


class TestProvenanceRecord:
    """Tests for ProvenanceRecord model."""
    
    def test_record_creation(self):
        """Test creating a ProvenanceRecord."""
        record = ProvenanceRecord(
            concept_id="select-basic",
            section_type="definition",
            source_chunks=["doc1:p5:c1", "doc1:p5:c2"],
            source_pages=[5, 6],
            source_blocks=[
                BlockRef(block_id="b1", page=5, block_type="paragraph"),
            ],
            confidence=0.95,
        )
        
        assert record.concept_id == "select-basic"
        assert record.section_type == "definition"
        assert len(record.source_chunks) == 2
        assert record.confidence == 0.95
    
    def test_record_serialization(self):
        """Test ProvenanceRecord serialization."""
        record = ProvenanceRecord(
            concept_id="joins",
            section_type="examples",
            source_chunks=["doc1:p10:c1"],
            source_pages=[10],
            extraction_method="marker",
        )
        
        data = record.model_dump()
        assert data["concept_id"] == "joins"
        assert data["extraction_method"] == "marker"
        assert "created_at" in data


class TestConceptProvenanceManifest:
    """Tests for ConceptProvenanceManifest."""
    
    def test_manifest_creation(self):
        """Test creating a manifest."""
        manifest = ConceptProvenanceManifest(
            source_doc_id="sql-textbook",
            extraction_method="marker",
        )
        
        assert manifest.schema_version == "provenance-v1"
        assert manifest.source_doc_id == "sql-textbook"
        assert manifest.extraction_method == "marker"
    
    def test_add_and_get_record(self):
        """Test adding and retrieving records."""
        manifest = ConceptProvenanceManifest(source_doc_id="doc1")
        
        record = ProvenanceRecord(
            concept_id="where-clause",
            section_type="definition",
            source_chunks=["doc1:p3:c1"],
            source_pages=[3],
        )
        
        manifest.add_record(record)
        
        # Retrieve specific record
        retrieved = manifest.get_record("where-clause", "definition")
        assert retrieved is not None
        assert retrieved.concept_id == "where-clause"
        
        # Get all records for concept
        all_records = manifest.get_concept_records("where-clause")
        assert len(all_records) == 1
        assert "definition" in all_records
    
    def test_manifest_serialization(self):
        """Test manifest JSON serialization."""
        manifest = ConceptProvenanceManifest(source_doc_id="doc1")
        record = ProvenanceRecord(
            concept_id="group-by",
            section_type="definition",
            source_chunks=["doc1:p15:c1"],
            source_pages=[15],
        )
        manifest.add_record(record)
        
        data = manifest.model_dump()
        assert data["schema_version"] == "provenance-v1"
        assert data["source_doc_id"] == "doc1"
        assert "records" in data
        assert "group-by" in data["records"]


# =============================================================================
# ProvenanceTracker Tests
# =============================================================================

class TestProvenanceTracker:
    """Tests for ProvenanceTracker class."""
    
    def test_tracker_initialization(self):
        """Test tracker initialization."""
        tracker = ProvenanceTracker(extraction_method="marker")
        assert tracker.extraction_method == "marker"
        assert len(tracker._records) == 0
    
    def test_register_block_mapping(self):
        """Test registering block-to-chunk mappings."""
        tracker = ProvenanceTracker()
        
        block1 = BlockRef(block_id="b1", page=1, block_type="paragraph")
        block2 = BlockRef(block_id="b2", page=1, block_type="paragraph")
        
        tracker.register_block_mapping("doc1:p1:c1", [block1, block2])
        
        # Check chunk-to-blocks mapping
        blocks = tracker.get_blocks_for_chunk("doc1:p1:c1")
        assert len(blocks) == 2
        
        # Check block-to-chunks mapping
        chunks = tracker.get_chunks_for_block("b1")
        assert "doc1:p1:c1" in chunks
        
        # Check page-to-blocks mapping
        page_blocks = tracker.get_blocks_for_page(1)
        assert len(page_blocks) == 2
    
    def test_record_section_provenance(self):
        """Test recording section provenance."""
        tracker = ProvenanceTracker()
        
        record = tracker.record_section_provenance(
            concept_id="subqueries",
            section_type="examples",
            source_chunks=["doc1:p20:c1", "doc1:p20:c2"],
            source_pages=[20],
            confidence=0.90,
        )
        
        assert record.concept_id == "subqueries"
        assert record.section_type == "examples"
        assert len(tracker._records) == 1
    
    def test_build_manifest(self):
        """Test building complete manifest."""
        tracker = ProvenanceTracker(extraction_method="pymupdf")
        
        tracker.record_section_provenance(
            concept_id="aggregation",
            section_type="definition",
            source_chunks=["doc1:p25:c1"],
            source_pages=[25],
        )
        
        manifest = tracker.build_manifest(source_doc_id="sql-textbook")
        
        assert manifest.source_doc_id == "sql-textbook"
        assert manifest.extraction_method == "pymupdf"
        assert "aggregation" in manifest.records
    
    def test_save_manifest(self):
        """Test saving manifest to file."""
        tracker = ProvenanceTracker()
        tracker.record_section_provenance(
            concept_id="test",
            section_type="definition",
            source_chunks=["doc1:p1:c1"],
            source_pages=[1],
        )
        
        manifest = tracker.build_manifest()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "provenance.json"
            tracker.save_manifest(manifest, out_path)
            
            assert out_path.exists()
            data = json.loads(out_path.read_text())
            assert data["schema_version"] == "provenance-v1"


# =============================================================================
# ChunkProvenance Tests
# =============================================================================

class TestChunkProvenance:
    """Tests for ChunkProvenance dataclass."""
    
    def test_chunk_provenance_creation(self):
        """Test creating ChunkProvenance."""
        cp = ChunkProvenance(
            chunk_id="doc1:p1:c1",
            doc_id="doc1",
            page=1,
            text="Sample text",
            source_block_ids=["b1", "b2"],
            char_offset_start=0,
            char_offset_end=100,
        )
        
        assert cp.chunk_id == "doc1:p1:c1"
        assert cp.source_block_ids == ["b1", "b2"]
        assert cp.char_offset_start == 0
    
    def test_to_chunk_dict(self):
        """Test conversion to chunk dictionary."""
        cp = ChunkProvenance(
            chunk_id="doc1:p1:c1",
            doc_id="doc1",
            page=1,
            text="Sample text",
            source_block_ids=["b1"],
        )
        
        data = cp.to_chunk_dict()
        assert data["chunkId"] == "doc1:p1:c1"
        assert data["source_block_ids"] == ["b1"]


# =============================================================================
# Utility Function Tests
# =============================================================================

class TestUtilityFunctions:
    """Tests for provenance utility functions."""
    
    def test_create_provenance_from_concept_section(self):
        """Test creating provenance from concept section."""
        chunks_data = {
            "doc1:p5:c1": {"page": 5},
            "doc1:p5:c2": {"page": 5},
            "doc1:p6:c1": {"page": 6},
        }
        
        record = create_provenance_from_concept_section(
            concept_id="joins",
            section_type="examples",
            chunk_ids=["doc1:p5:c1", "doc1:p5:c2", "doc1:p6:c1"],
            chunks_data=chunks_data,
            extraction_method="marker",
        )
        
        assert record.concept_id == "joins"
        assert record.source_pages == [5, 6]
        assert record.extraction_method == "marker"
    
    def test_merge_provenance_records(self):
        """Test merging multiple provenance records."""
        record1 = ProvenanceRecord(
            concept_id="select",
            section_type="definition",
            source_chunks=["doc1:p1:c1"],
            source_pages=[1],
            confidence=0.9,
        )
        record2 = ProvenanceRecord(
            concept_id="select",
            section_type="definition",
            source_chunks=["doc1:p1:c2"],
            source_pages=[1, 2],
            confidence=0.8,
        )
        
        merged = merge_provenance_records([record1, record2])
        
        assert merged.concept_id == "select"
        assert len(merged.source_chunks) == 2
        assert merged.source_pages == [1, 2]
        assert abs(merged.confidence - 0.85) < 0.001  # Average of 0.9 and 0.8
    
    def test_merge_single_record(self):
        """Test merging single record returns itself."""
        record = ProvenanceRecord(
            concept_id="test",
            section_type="definition",
            source_chunks=["doc1:p1:c1"],
            source_pages=[1],
        )
        
        merged = merge_provenance_records([record])
        assert merged is record
    
    def test_merge_empty_raises_error(self):
        """Test merging empty list raises error."""
        with pytest.raises(ValueError):
            merge_provenance_records([])


# =============================================================================
# SourceViewer Tests
# =============================================================================

class TestChunkLookup:
    """Tests for ChunkLookup helper."""
    
    def test_from_list(self):
        """Test creating lookup from chunk list."""
        chunks = [
            PdfIndexChunk(chunkId="d1:p1:c1", docId="d1", page=1, text="Text 1"),
            PdfIndexChunk(chunkId="d1:p1:c2", docId="d1", page=1, text="Text 2"),
            PdfIndexChunk(chunkId="d1:p2:c1", docId="d1", page=2, text="Text 3"),
        ]
        
        lookup = ChunkLookup.from_list(chunks)
        
        assert len(lookup.chunks_by_id) == 3
        assert len(lookup.chunks_by_page[1]) == 2
        assert len(lookup.chunks_by_page[2]) == 1
    
    def test_get_chunk(self):
        """Test getting chunk by ID."""
        chunks = [
            PdfIndexChunk(chunkId="d1:p1:c1", docId="d1", page=1, text="Text 1"),
        ]
        lookup = ChunkLookup.from_list(chunks)
        
        chunk = lookup.get_chunk("d1:p1:c1")
        assert chunk is not None
        assert chunk.text == "Text 1"
        
        missing = lookup.get_chunk("nonexistent")
        assert missing is None
    
    def test_get_context_chunks(self):
        """Test getting context chunks."""
        chunks = [
            PdfIndexChunk(chunkId="d1:p1:c1", docId="d1", page=1, text="First"),
            PdfIndexChunk(chunkId="d1:p1:c2", docId="d1", page=1, text="Second"),
            PdfIndexChunk(chunkId="d1:p1:c3", docId="d1", page=1, text="Third"),
        ]
        lookup = ChunkLookup.from_list(chunks)
        
        before, after = lookup.get_context_chunks("d1:p1:c2", context_count=1)
        
        assert len(before) == 1
        assert before[0].chunkId == "d1:p1:c1"
        assert len(after) == 1
        assert after[0].chunkId == "d1:p1:c3"


class TestSourceViewer:
    """Tests for SourceViewer class."""
    
    def test_viewer_initialization(self):
        """Test viewer initialization."""
        chunks = [
            PdfIndexChunk(chunkId="d1:p1:c1", docId="d1", page=1, text="Sample"),
        ]
        viewer = SourceViewer(chunks=chunks)
        
        assert len(viewer._chunks) == 1
        assert viewer.chunk_lookup.get_chunk("d1:p1:c1") is not None
    
    def test_get_passages_by_page(self):
        """Test getting passages by page number."""
        chunks = [
            PdfIndexChunk(chunkId="d1:p1:c1", docId="d1", page=1, text="Page 1"),
            PdfIndexChunk(chunkId="d1:p2:c1", docId="d1", page=2, text="Page 2"),
        ]
        viewer = SourceViewer(chunks=chunks)
        
        passages = viewer.get_passages_by_page([1])
        
        assert len(passages) == 1
        assert passages[0].page == 1
        assert passages[0].text == "Page 1"
    
    def test_format_for_display_markdown(self):
        """Test formatting as markdown."""
        from algl_pdf_helper.source_viewer import SourceViewResult
        
        result = SourceViewResult(
            concept_id="test-concept",
            page_numbers=[1, 2],
        )
        
        chunks = [
            PdfIndexChunk(chunkId="d1:p1:c1", docId="d1", page=1, text="Content"),
        ]
        viewer = SourceViewer(chunks=chunks)
        
        markdown = viewer.format_for_display(result, format_type="markdown")
        
        assert "# Source Passages: test-concept" in markdown
        assert "Page 1" in markdown or "Pages:" in markdown
    
    def test_format_for_display_json(self):
        """Test formatting as JSON."""
        from algl_pdf_helper.source_viewer import SourceViewResult
        
        result = SourceViewResult(
            concept_id="test-concept",
            page_numbers=[1],
        )
        
        chunks = [
            PdfIndexChunk(chunkId="d1:p1:c1", docId="d1", page=1, text="Content"),
        ]
        viewer = SourceViewer(chunks=chunks)
        
        json_str = viewer.format_for_display(result, format_type="json")
        
        data = json.loads(json_str)
        assert data["concept_id"] == "test-concept"
        assert data["page_numbers"] == [1]
    
    def test_generate_page_link(self):
        """Test generating page links."""
        chunks = []
        viewer = SourceViewer(chunks=chunks)
        
        # Without base URL (anchor format)
        link = viewer.generate_page_link(5, "doc1")
        assert "#page-" in link or "page=" in link
        assert "5" in link
        
        # With base URL
        link = viewer.generate_page_link(5, "doc1", base_url="https://example.com")
        assert "https://example.com" in link
        assert "page=5" in link


class TestGetPageOpenUrl:
    """Tests for get_page_open_url utility."""
    
    def test_pdf_format(self):
        """Test PDF format URL."""
        url = get_page_open_url(5, "doc1", "pdf")
        assert "pdf://open/doc1" in url
        assert "page=5" in url
    
    def test_web_format(self):
        """Test web format URL."""
        url = get_page_open_url(5, "doc1", "web")
        assert "/viewer/doc1" in url
        assert "page=5" in url
    
    def test_default_format(self):
        """Test default format URL."""
        url = get_page_open_url(5, "doc1", "unknown")
        assert "#open-page-5" in url


# =============================================================================
# Integration Tests
# =============================================================================

class TestProvenanceIntegration:
    """Integration tests for provenance system."""
    
    def test_full_pipeline_simulation(self):
        """Simulate a full processing pipeline with provenance."""
        # 1. Create tracker
        tracker = ProvenanceTracker(extraction_method="marker")
        
        # 2. Register some block mappings
        block1 = BlockRef(block_id="p1_b1", page=1, block_type="heading")
        block2 = BlockRef(block_id="p1_b2", page=1, block_type="paragraph")
        
        tracker.register_block_mapping("doc1:p1:c1", [block1, block2])
        
        # 3. Record provenance for concept sections
        tracker.record_section_provenance(
            concept_id="select-basic",
            section_type="definition",
            source_chunks=["doc1:p1:c1"],
            source_pages=[1],
            source_blocks=[block1, block2],
            confidence=0.95,
        )
        
        tracker.record_section_provenance(
            concept_id="select-basic",
            section_type="examples",
            source_chunks=["doc1:p1:c1"],
            source_pages=[1],
            source_blocks=[block2],
            confidence=0.90,
        )
        
        # 4. Build manifest
        manifest = tracker.build_manifest(source_doc_id="sql-textbook")
        
        # 5. Verify manifest
        assert manifest.source_doc_id == "sql-textbook"
        assert "select-basic" in manifest.records
        assert len(manifest.records["select-basic"]) == 2  # definition + examples
        
        # 6. Verify block mappings preserved
        chunks_for_block = tracker.get_chunks_for_block("p1_b1")
        assert "doc1:p1:c1" in chunks_for_block


# =============================================================================
# End-to-End Tests
# =============================================================================

class TestEndToEnd:
    """End-to-end tests with file I/O."""
    
    def test_save_and_load_manifest(self):
        """Test saving and loading provenance manifest."""
        tracker = ProvenanceTracker()
        tracker.record_section_provenance(
            concept_id="joins",
            section_type="definition",
            source_chunks=["doc1:p10:c1"],
            source_pages=[10],
            source_blocks=[
                BlockRef(block_id="b1", page=10, block_type="paragraph"),
            ],
        )
        
        manifest = tracker.build_manifest(source_doc_id="doc1")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "provenance.json"
            
            # Save
            tracker.save_manifest(manifest, out_path)
            
            # Load and verify
            data = json.loads(out_path.read_text())
            assert data["source_doc_id"] == "doc1"
            assert "records" in data
            assert "joins" in data["records"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
