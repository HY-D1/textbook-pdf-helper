"""
Provenance Tracking System for ALGL PDF Helper.

This module provides comprehensive provenance tracking for educational content
generated from PDF textbooks. It enables:
- Tracing every sentence back to source textbook pages
- Recording which chunks/blocks contributed to each concept section
- Supporting "View Source" functionality for transparency
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class BlockRef(BaseModel):
    """Reference to a structural block in the source PDF.
    
    Blocks are structural units extracted by parsing engines like Marker,
    such as paragraphs, tables, figures, headings, etc.
    """
    block_id: str = Field(..., description="Unique block identifier")
    page: int = Field(..., description="Page number where block appears")
    block_type: str = Field(..., description="Type: paragraph, table, figure, heading, code, list")
    
    def __hash__(self) -> int:
        return hash((self.block_id, self.page, self.block_type))
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BlockRef):
            return False
        return (
            self.block_id == other.block_id
            and self.page == other.page
            and self.block_type == other.block_type
        )


class ProvenanceRecord(BaseModel):
    """Provenance record for a concept section.
    
    Tracks the complete origin of generated educational content,
    including source chunks, pages, and structural blocks.
    """
    concept_id: str = Field(..., description="Concept identifier")
    section_type: str = Field(..., description="Section type: definition, examples, commonMistakes, etc.")
    source_chunks: list[str] = Field(default_factory=list, description="List of chunk IDs used")
    source_pages: list[int] = Field(default_factory=list, description="List of page numbers")
    source_blocks: list[BlockRef] = Field(default_factory=list, description="Structural block references")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score for this mapping")
    extraction_method: str = Field(default="pymupdf", description="Extraction method used")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Custom serialization for JSON compatibility."""
        return {
            "concept_id": self.concept_id,
            "section_type": self.section_type,
            "source_chunks": self.source_chunks,
            "source_pages": self.source_pages,
            "source_blocks": [b.model_dump() for b in self.source_blocks],
            "confidence": self.confidence,
            "extraction_method": self.extraction_method,
            "created_at": self.created_at,
        }


class SourcePassage(BaseModel):
    """A source passage with context for "View Source" functionality.
    
    Represents the original text from the textbook with metadata
    to display in a "View Source" UI.
    """
    chunk_id: str = Field(..., description="Chunk identifier")
    text: str = Field(..., description="Original text content")
    page: int = Field(..., description="Page number")
    doc_id: str = Field(..., description="Document identifier")
    block_refs: list[BlockRef] = Field(default_factory=list, description="Associated block references")
    context_before: str = Field(default="", description="Preceding text for context")
    context_after: str = Field(default="", description="Following text for context")
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "page": self.page,
            "doc_id": self.doc_id,
            "block_refs": [b.model_dump() for b in self.block_refs],
            "context_before": self.context_before,
            "context_after": self.context_after,
        }


class ConceptProvenanceManifest(BaseModel):
    """Manifest containing provenance records for all concepts.
    
    This is stored alongside concept-manifest.json for complete
    traceability of generated content.
    """
    schema_version: str = Field(default="provenance-v1")
    source_doc_id: str = Field(default="", description="Primary source document ID")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    extraction_method: str = Field(default="pymupdf", description="Primary extraction method")
    records: dict[str, dict[str, ProvenanceRecord]] = Field(
        default_factory=dict,
        description="Nested dict: concept_id -> section_type -> ProvenanceRecord"
    )
    
    def add_record(self, record: ProvenanceRecord) -> None:
        """Add a provenance record to the manifest."""
        if record.concept_id not in self.records:
            self.records[record.concept_id] = {}
        self.records[record.concept_id][record.section_type] = record
    
    def get_record(self, concept_id: str, section_type: str) -> ProvenanceRecord | None:
        """Retrieve a specific provenance record."""
        return self.records.get(concept_id, {}).get(section_type)
    
    def get_concept_records(self, concept_id: str) -> dict[str, ProvenanceRecord]:
        """Get all provenance records for a concept."""
        return self.records.get(concept_id, {})
    
    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Custom serialization for JSON compatibility."""
        return {
            "schema_version": self.schema_version,
            "source_doc_id": self.source_doc_id,
            "created_at": self.created_at,
            "extraction_method": self.extraction_method,
            "records": {
                concept_id: {
                    section: record.model_dump()
                    for section, record in sections.items()
                }
                for concept_id, sections in self.records.items()
            },
        }


@dataclass
class ChunkProvenance:
    """Dataclass for tracking provenance during chunking.
    
    This is used internally during the chunking process to track
    which blocks contributed to each chunk.
    """
    chunk_id: str
    doc_id: str
    page: int
    text: str
    source_block_ids: list[str] = field(default_factory=list)
    char_offset_start: int = 0
    char_offset_end: int = 0
    
    def to_chunk_dict(self) -> dict[str, Any]:
        """Convert to dictionary format compatible with PdfIndexChunk."""
        return {
            "chunkId": self.chunk_id,
            "docId": self.doc_id,
            "page": self.page,
            "text": self.text,
            "source_block_ids": self.source_block_ids,
        }


class ProvenanceTracker:
    """Main tracker for provenance information throughout the pipeline.
    
    This class is responsible for:
    - Recording which chunks/pages/blocks contribute to each concept section
    - Building the provenance manifest
    - Providing lookup methods for "View Source" functionality
    """
    
    def __init__(self, extraction_method: str = "pymupdf") -> None:
        """Initialize the provenance tracker.
        
        Args:
            extraction_method: The PDF extraction method being used
        """
        self.extraction_method = extraction_method
        self._records: list[ProvenanceRecord] = []
        self._block_to_chunk_map: dict[str, list[str]] = {}
        self._chunk_to_blocks_map: dict[str, list[BlockRef]] = {}
        self._page_to_blocks_map: dict[int, list[BlockRef]] = {}
    
    def register_block_mapping(self, chunk_id: str, blocks: list[BlockRef]) -> None:
        """Register which blocks contributed to a chunk.
        
        Args:
            chunk_id: The chunk identifier
            blocks: List of block references in this chunk
        """
        self._chunk_to_blocks_map[chunk_id] = blocks
        for block in blocks:
            if block.block_id not in self._block_to_chunk_map:
                self._block_to_chunk_map[block.block_id] = []
            self._block_to_chunk_map[block.block_id].append(chunk_id)
            
            if block.page not in self._page_to_blocks_map:
                self._page_to_blocks_map[block.page] = []
            self._page_to_blocks_map[block.page].append(block)
    
    def record_section_provenance(
        self,
        concept_id: str,
        section_type: str,
        source_chunks: list[str],
        source_pages: list[int] | None = None,
        source_blocks: list[BlockRef] | None = None,
        confidence: float = 1.0,
    ) -> ProvenanceRecord:
        """Record provenance for a concept section.
        
        Args:
            concept_id: The concept identifier
            section_type: Type of section (definition, examples, etc.)
            source_chunks: List of chunk IDs used
            source_pages: Optional list of page numbers (derived from chunks if not provided)
            source_blocks: Optional list of block references
            confidence: Confidence score (0.0-1.0)
            
        Returns:
            The created ProvenanceRecord
        """
        # Derive pages from blocks if not provided
        if source_pages is None and source_blocks:
            source_pages = sorted(set(b.page for b in source_blocks))
        
        record = ProvenanceRecord(
            concept_id=concept_id,
            section_type=section_type,
            source_chunks=source_chunks,
            source_pages=source_pages or [],
            source_blocks=source_blocks or [],
            confidence=confidence,
            extraction_method=self.extraction_method,
        )
        self._records.append(record)
        return record
    
    def get_chunks_for_block(self, block_id: str) -> list[str]:
        """Get all chunk IDs that contain a given block.
        
        Args:
            block_id: The block identifier
            
        Returns:
            List of chunk IDs containing this block
        """
        return self._block_to_chunk_map.get(block_id, [])
    
    def get_blocks_for_chunk(self, chunk_id: str) -> list[BlockRef]:
        """Get all blocks contained in a given chunk.
        
        Args:
            chunk_id: The chunk identifier
            
        Returns:
            List of block references in this chunk
        """
        return self._chunk_to_blocks_map.get(chunk_id, [])
    
    def get_blocks_for_page(self, page: int) -> list[BlockRef]:
        """Get all blocks on a given page.
        
        Args:
            page: Page number
            
        Returns:
            List of block references on this page
        """
        return self._page_to_blocks_map.get(page, [])
    
    def build_manifest(self, source_doc_id: str = "") -> ConceptProvenanceManifest:
        """Build the complete provenance manifest.
        
        Args:
            source_doc_id: Primary source document ID
            
        Returns:
            ConceptProvenanceManifest with all records
        """
        manifest = ConceptProvenanceManifest(
            source_doc_id=source_doc_id,
            extraction_method=self.extraction_method,
        )
        
        for record in self._records:
            manifest.add_record(record)
        
        return manifest
    
    def save_manifest(self, manifest: ConceptProvenanceManifest, out_path: Path) -> None:
        """Save the provenance manifest to a JSON file.
        
        Args:
            manifest: The manifest to save
            out_path: Output file path
        """
        import json
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(manifest.model_dump(), f, indent=2)
            f.write("\n")


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def create_provenance_from_concept_section(
    concept_id: str,
    section_type: str,
    chunk_ids: list[str],
    chunks_data: dict[str, dict[str, Any]],
    extraction_method: str = "pymupdf",
) -> ProvenanceRecord:
    """Create a provenance record from concept section data.
    
    This is a convenience function for creating provenance records
    when we have chunk IDs and a lookup of chunk data.
    
    Args:
        concept_id: The concept identifier
        section_type: Type of section
        chunk_ids: List of chunk IDs
        chunks_data: Dictionary mapping chunk_id -> chunk data dict
        extraction_method: Extraction method used
        
    Returns:
        ProvenanceRecord
    """
    source_pages = []
    for chunk_id in chunk_ids:
        chunk = chunks_data.get(chunk_id, {})
        page = chunk.get("page")
        if page and page not in source_pages:
            source_pages.append(page)
    
    return ProvenanceRecord(
        concept_id=concept_id,
        section_type=section_type,
        source_chunks=chunk_ids,
        source_pages=sorted(source_pages),
        extraction_method=extraction_method,
    )


def merge_provenance_records(records: list[ProvenanceRecord]) -> ProvenanceRecord:
    """Merge multiple provenance records into one.
    
    Useful when combining sections or aggregating provenance data.
    
    Args:
        records: List of records to merge
        
    Returns:
        Merged ProvenanceRecord
    """
    if not records:
        raise ValueError("Cannot merge empty list of records")
    
    if len(records) == 1:
        return records[0]
    
    # Use the first record as base
    base = records[0]
    
    # Collect all unique values
    all_chunks: set[str] = set(base.source_chunks)
    all_pages: set[int] = set(base.source_pages)
    all_blocks: set[BlockRef] = set(base.source_blocks)
    
    for record in records[1:]:
        all_chunks.update(record.source_chunks)
        all_pages.update(record.source_pages)
        all_blocks.update(record.source_blocks)
    
    # Average confidence
    avg_confidence = sum(r.confidence for r in records) / len(records)
    
    return ProvenanceRecord(
        concept_id=base.concept_id,
        section_type=base.section_type,
        source_chunks=sorted(all_chunks),
        source_pages=sorted(all_pages),
        source_blocks=list(all_blocks),
        confidence=avg_confidence,
        extraction_method=base.extraction_method,
    )
