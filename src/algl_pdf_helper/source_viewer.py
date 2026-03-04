"""
Source Viewer for "View Source" UX Support.

This module provides functionality to retrieve and display original source
passages from the textbook, enabling users to verify and explore the
original context of generated educational content.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .models import PdfIndexChunk
from .provenance import (
    BlockRef,
    ConceptProvenanceManifest,
    ProvenanceRecord,
    SourcePassage,
)


class SourceViewOptions(BaseModel):
    """Options for source view retrieval."""
    include_context: bool = Field(default=True, description="Include surrounding text for context")
    context_words: int = Field(default=50, ge=0, le=500, description="Number of context words")
    highlight_blocks: bool = Field(default=True, description="Highlight specific blocks in passage")


class SourceViewResult(BaseModel):
    """Result of a source view query."""
    concept_id: str = Field(..., description="Concept identifier")
    section_type: str | None = Field(None, description="Section type if specific")
    passages: list[SourcePassage] = Field(default_factory=list)
    total_pages: int = Field(default=0, description="Total unique pages referenced")
    page_numbers: list[int] = Field(default_factory=list, description="Sorted page numbers")
    extraction_method: str = Field(default="pymupdf")
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "concept_id": self.concept_id,
            "section_type": self.section_type,
            "passages": [p.to_dict() for p in self.passages],
            "total_pages": self.total_pages,
            "page_numbers": self.page_numbers,
            "extraction_method": self.extraction_method,
        }


@dataclass
class ChunkLookup:
    """Helper for looking up chunks by various criteria."""
    chunks_by_id: dict[str, PdfIndexChunk]
    chunks_by_page: dict[int, list[PdfIndexChunk]]
    
    @classmethod
    def from_list(cls, chunks: list[PdfIndexChunk]) -> "ChunkLookup":
        """Create lookup from list of chunks."""
        by_id: dict[str, PdfIndexChunk] = {}
        by_page: dict[int, list[PdfIndexChunk]] = {}
        
        for chunk in chunks:
            by_id[chunk.chunkId] = chunk
            if chunk.page not in by_page:
                by_page[chunk.page] = []
            by_page[chunk.page].append(chunk)
        
        return cls(by_id, by_page)
    
    def get_chunk(self, chunk_id: str) -> PdfIndexChunk | None:
        """Get chunk by ID."""
        return self.chunks_by_id.get(chunk_id)
    
    def get_chunks_for_page(self, page: int) -> list[PdfIndexChunk]:
        """Get all chunks for a page."""
        return self.chunks_by_page.get(page, [])
    
    def get_context_chunks(
        self,
        chunk_id: str,
        context_count: int = 1,
    ) -> tuple[list[PdfIndexChunk], list[PdfIndexChunk]]:
        """Get context chunks before and after a given chunk.
        
        Args:
            chunk_id: Target chunk ID
            context_count: Number of chunks to include as context
            
        Returns:
            Tuple of (before_chunks, after_chunks)
        """
        chunk = self.get_chunk(chunk_id)
        if not chunk:
            return [], []
        
        # Get all chunks on the same page
        page_chunks = self.get_chunks_for_page(chunk.page)
        
        # Sort by chunk ID to maintain order
        page_chunks_sorted = sorted(page_chunks, key=lambda c: c.chunkId)
        
        try:
            idx = page_chunks_sorted.index(chunk)
        except ValueError:
            return [], []
        
        before = page_chunks_sorted[max(0, idx - context_count):idx]
        after = page_chunks_sorted[idx + 1:idx + 1 + context_count]
        
        return before, after


class SourceViewer:
    """Main class for "View Source" functionality.
    
    Provides methods to retrieve original source passages with context,
    enabling transparency and verification of generated educational content.
    """
    
    def __init__(
        self,
        chunks: list[PdfIndexChunk],
        provenance_manifest: ConceptProvenanceManifest | None = None,
        pdf_path: Path | None = None,
    ):
        """Initialize the source viewer.
        
        Args:
            chunks: All available chunks from the PDF
            provenance_manifest: Optional provenance manifest for enhanced lookup
            pdf_path: Optional path to original PDF for direct access
        """
        self.chunk_lookup = ChunkLookup.from_list(chunks)
        self.provenance = provenance_manifest
        self.pdf_path = pdf_path
        self._chunks = chunks
    
    def get_source_passages(
        self,
        concept_id: str,
        section_type: str | None = None,
        options: SourceViewOptions | None = None,
    ) -> SourceViewResult:
        """Get source passages for a concept or specific section.
        
        This is the main entry point for "View Source" functionality.
        
        Args:
            concept_id: The concept identifier
            section_type: Optional specific section type (e.g., "definition")
            options: View options for context and formatting
            
        Returns:
            SourceViewResult with passages and metadata
        """
        opts = options or SourceViewOptions()
        
        if self.provenance:
            return self._get_from_provenance(concept_id, section_type, opts)
        else:
            return self._get_from_chunks_only(concept_id, section_type, opts)
    
    def _get_from_provenance(
        self,
        concept_id: str,
        section_type: str | None,
        options: SourceViewOptions,
    ) -> SourceViewResult:
        """Get passages using provenance manifest."""
        if not self.provenance:
            return SourceViewResult(concept_id=concept_id, section_type=section_type)
        
        passages: list[SourcePassage] = []
        all_pages: set[int] = set()
        
        if section_type:
            # Get specific section
            record = self.provenance.get_record(concept_id, section_type)
            if record:
                passage_list = self._build_passages_from_record(record, options)
                passages.extend(passage_list)
                all_pages.update(record.source_pages)
        else:
            # Get all sections for concept
            records = self.provenance.get_concept_records(concept_id)
            for record in records.values():
                passage_list = self._build_passages_from_record(record, options)
                passages.extend(passage_list)
                all_pages.update(record.source_pages)
        
        # Deduplicate passages by chunk_id
        seen_chunks: set[str] = set()
        unique_passages: list[SourcePassage] = []
        for p in passages:
            if p.chunk_id not in seen_chunks:
                seen_chunks.add(p.chunk_id)
                unique_passages.append(p)
        
        return SourceViewResult(
            concept_id=concept_id,
            section_type=section_type,
            passages=unique_passages,
            total_pages=len(all_pages),
            page_numbers=sorted(all_pages),
            extraction_method=self.provenance.extraction_method,
        )
    
    def _get_from_chunks_only(
        self,
        concept_id: str,
        section_type: str | None,
        options: SourceViewOptions,
    ) -> SourceViewResult:
        """Fallback: get passages without provenance manifest."""
        # This would require concept-to-chunk mapping from elsewhere
        # For now, return empty result
        return SourceViewResult(
            concept_id=concept_id,
            section_type=section_type,
            passages=[],
            total_pages=0,
            page_numbers=[],
        )
    
    def _build_passages_from_record(
        self,
        record: ProvenanceRecord,
        options: SourceViewOptions,
    ) -> list[SourcePassage]:
        """Build SourcePassage objects from a provenance record."""
        passages: list[SourcePassage] = []
        
        for chunk_id in record.source_chunks:
            chunk = self.chunk_lookup.get_chunk(chunk_id)
            if not chunk:
                continue
            
            # Build context
            context_before = ""
            context_after = ""
            
            if options.include_context and options.context_words > 0:
                before_chunks, after_chunks = self.chunk_lookup.get_context_chunks(
                    chunk_id, context_count=1
                )
                
                if before_chunks:
                    context_before = self._extract_context_words(
                        before_chunks[-1].text,
                        options.context_words,
                        from_end=True,
                    )
                
                if after_chunks:
                    context_after = self._extract_context_words(
                        after_chunks[0].text,
                        options.context_words,
                        from_end=False,
                    )
            
            # Find block refs for this chunk
            block_refs = [
                b for b in record.source_blocks
                if b.page == chunk.page
            ]
            
            passage = SourcePassage(
                chunk_id=chunk_id,
                text=chunk.text,
                page=chunk.page,
                doc_id=chunk.docId,
                block_refs=block_refs,
                context_before=context_before,
                context_after=context_after,
            )
            passages.append(passage)
        
        return passages
    
    def _extract_context_words(
        self,
        text: str,
        word_count: int,
        from_end: bool = False,
    ) -> str:
        """Extract a portion of text by word count.
        
        Args:
            text: Source text
            word_count: Number of words to extract
            from_end: If True, extract from end of text
            
        Returns:
            Extracted text portion
        """
        words = text.split()
        if len(words) <= word_count:
            return text
        
        if from_end:
            return " ".join(words[-word_count:])
        else:
            return " ".join(words[:word_count])
    
    def get_passages_by_page(
        self,
        page_numbers: list[int],
        doc_id: str | None = None,
    ) -> list[SourcePassage]:
        """Get all source passages for specific pages.
        
        Args:
            page_numbers: List of page numbers to retrieve
            doc_id: Optional document ID filter
            
        Returns:
            List of source passages
        """
        passages: list[SourcePassage] = []
        
        for page in page_numbers:
            chunks = self.chunk_lookup.get_chunks_for_page(page)
            for chunk in chunks:
                if doc_id and chunk.docId != doc_id:
                    continue
                
                passages.append(SourcePassage(
                    chunk_id=chunk.chunkId,
                    text=chunk.text,
                    page=chunk.page,
                    doc_id=chunk.docId,
                ))
        
        return passages
    
    def get_passages_by_block(
        self,
        block_refs: list[BlockRef],
    ) -> list[SourcePassage]:
        """Get source passages containing specific blocks.
        
        Args:
            block_refs: List of block references to find
            
        Returns:
            List of source passages containing these blocks
        """
        passages: list[SourcePassage] = []
        
        for block_ref in block_refs:
            # Get chunks for the block's page
            page_chunks = self.chunk_lookup.get_chunks_for_page(block_ref.page)
            
            # Find chunks that likely contain this block
            for chunk in page_chunks:
                passage = SourcePassage(
                    chunk_id=chunk.chunkId,
                    text=chunk.text,
                    page=chunk.page,
                    doc_id=chunk.docId,
                    block_refs=[block_ref],
                )
                passages.append(passage)
        
        return passages
    
    def format_for_display(
        self,
        result: SourceViewResult,
        format_type: str = "markdown",
    ) -> str:
        """Format source passages for display.
        
        Args:
            result: Source view result
            format_type: Output format: "markdown", "html", or "json"
            
        Returns:
            Formatted string
        """
        if format_type == "json":
            import json
            return json.dumps(result.to_dict(), indent=2)
        
        elif format_type == "html":
            lines: list[str] = [
                f'<div class="source-view" data-concept="{result.concept_id}">',
                f'  <h2>Source Passages: {result.concept_id}</h2>',
            ]
            
            for passage in result.passages:
                lines.append(f'  <div class="passage" data-chunk="{passage.chunk_id}">')
                lines.append(f'    <div class="passage-header">Page {passage.page}</div>')
                if passage.context_before:
                    lines.append(f'    <div class="context-before">{passage.context_before}</div>')
                lines.append(f'    <div class="passage-text">{passage.text}</div>')
                if passage.context_after:
                    lines.append(f'    <div class="context-after">{passage.context_after}</div>')
                lines.append('  </div>')
            
            lines.append('</div>')
            return '\n'.join(lines)
        
        else:  # markdown
            lines: list[str] = [
                f"# Source Passages: {result.concept_id}",
                "",
                f"**Pages:** {', '.join(map(str, result.page_numbers))}",
                "",
            ]
            
            for i, passage in enumerate(result.passages, 1):
                lines.append(f"## Passage {i} (Page {passage.page})")
                lines.append("")
                lines.append(f"<!-- source-chunk: {passage.chunk_id} -->")
                lines.append("")
                
                if passage.context_before:
                    lines.append(f"_...{passage.context_before}_")
                    lines.append("")
                
                lines.append(passage.text)
                lines.append("")
                
                if passage.context_after:
                    lines.append(f"_...{passage.context_after}_")
                    lines.append("")
                
                lines.append("---")
                lines.append("")
            
            return '\n'.join(lines)
    
    def generate_page_link(
        self,
        page: int,
        doc_id: str,
        base_url: str = "",
    ) -> str:
        """Generate a link to open a specific page.
        
        Args:
            page: Page number
            doc_id: Document ID
            base_url: Base URL for the link
            
        Returns:
            URL string for opening the page
        """
        if base_url:
            return f"{base_url}/view?doc={doc_id}&page={page}"
        return f"#page-{page}"


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def create_source_viewer_from_files(
    chunks_path: Path,
    provenance_path: Path | None = None,
    pdf_path: Path | None = None,
) -> SourceViewer:
    """Create a SourceViewer from JSON files.
    
    Args:
        chunks_path: Path to chunks.json file
        provenance_path: Optional path to provenance-manifest.json
        pdf_path: Optional path to original PDF
        
    Returns:
        Configured SourceViewer
    """
    import json
    
    # Load chunks
    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks_data = json.load(f)
    
    chunks = [
        PdfIndexChunk(
            chunkId=c["chunkId"],
            docId=c["docId"],
            page=c["page"],
            text=c["text"],
            embedding=c.get("embedding"),
        )
        for c in chunks_data
    ]
    
    # Load provenance if available
    provenance = None
    if provenance_path and provenance_path.exists():
        with open(provenance_path, "r", encoding="utf-8") as f:
            prov_data = json.load(f)
        # Note: Full parsing would require additional logic
        # This is a simplified version
    
    return SourceViewer(chunks=chunks, provenance_manifest=provenance, pdf_path=pdf_path)


def get_page_open_url(page: int, doc_id: str, source_format: str = "pdf") -> str:
    """Generate a URL for opening a specific page.
    
    Args:
        page: Page number
        doc_id: Document ID
        source_format: Format of source (pdf, web, etc.)
        
    Returns:
        URL string
    """
    if source_format == "pdf":
        return f"pdf://open/{doc_id}#page={page}"
    elif source_format == "web":
        return f"/viewer/{doc_id}?page={page}"
    else:
        return f"#open-page-{page}"
