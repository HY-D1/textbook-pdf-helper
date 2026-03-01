from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PageText:
    page: int
    text: str


@dataclass
class ChunkResult:
    """Result of chunking with provenance information."""
    chunk_id: str
    text: str
    source_block_ids: list[str]
    char_offset_start: int
    char_offset_end: int
    
    def to_tuple(self) -> tuple[str, str]:
        """Convert to tuple for backward compatibility."""
        return (self.chunk_id, self.text)


def chunk_page_words(
    *,
    doc_id: str,
    page: int,
    text: str,
    chunk_words: int,
    overlap_words: int,
    source_block_ids: list[str] | None = None,
) -> list[tuple[str, str]]:
    """Return list of (chunk_id, chunk_text).
    
    Args:
        doc_id: Document identifier
        page: Page number
        text: Text to chunk
        chunk_words: Number of words per chunk
        overlap_words: Number of words to overlap between chunks
        source_block_ids: Optional list of block IDs for this page's text
        
    Returns:
        List of (chunk_id, chunk_text) tuples for backward compatibility
    """
    results = chunk_page_words_with_provenance(
        doc_id=doc_id,
        page=page,
        text=text,
        chunk_words=chunk_words,
        overlap_words=overlap_words,
        source_block_ids=source_block_ids,
    )
    return [r.to_tuple() for r in results]


def chunk_page_words_with_provenance(
    *,
    doc_id: str,
    page: int,
    text: str,
    chunk_words: int,
    overlap_words: int,
    source_block_ids: list[str] | None = None,
) -> list[ChunkResult]:
    """Return list of ChunkResult with provenance information.
    
    Args:
        doc_id: Document identifier
        page: Page number
        text: Text to chunk
        chunk_words: Number of words per chunk
        overlap_words: Number of words to overlap between chunks
        source_block_ids: Optional list of block IDs for this page's text
        
    Returns:
        List of ChunkResult objects with full provenance
    """
    words = [w for w in text.split() if w]
    if not words:
        return []
    
    step = max(1, chunk_words - overlap_words)
    out: list[ChunkResult] = []
    
    start = 0
    chunk_index = 0
    
    while start < len(words):
        slice_words = words[start : start + chunk_words]
        if not slice_words:
            break
        
        chunk_index += 1
        chunk_id = f"{doc_id}:p{page}:c{chunk_index}"
        chunk_text = " ".join(slice_words)
        
        # Calculate character offsets
        char_start = len(" ".join(words[:start])) + (1 if start > 0 else 0)
        char_end = char_start + len(chunk_text)
        
        # For now, associate all blocks with all chunks on the page
        # In a more sophisticated implementation, we'd track which words
        # came from which blocks
        blocks = source_block_ids or []
        
        out.append(ChunkResult(
            chunk_id=chunk_id,
            text=chunk_text,
            source_block_ids=blocks,
            char_offset_start=char_start,
            char_offset_end=char_end,
        ))
        
        if start + chunk_words >= len(words):
            break
        
        start += step
    
    return out


def chunk_with_block_mapping(
    *,
    doc_id: str,
    page: int,
    text: str,
    chunk_words: int,
    overlap_words: int,
    blocks: list[dict[str, Any]],
) -> list[ChunkResult]:
    """Chunk text while preserving block-to-chunk mappings.
    
    This is an advanced chunking function that attempts to track
    which structural blocks contribute to each chunk.
    
    Args:
        doc_id: Document identifier
        page: Page number
        text: Text to chunk
        chunk_words: Number of words per chunk
        overlap_words: Number of words to overlap between chunks
        blocks: List of block dictionaries with 'id', 'text_preview', etc.
        
    Returns:
        List of ChunkResult objects with block mappings
    """
    # First, perform standard chunking
    results = chunk_page_words_with_provenance(
        doc_id=doc_id,
        page=page,
        text=text,
        chunk_words=chunk_words,
        overlap_words=overlap_words,
    )
    
    # Now attempt to map blocks to chunks
    # This is a heuristic approach: check which blocks appear in each chunk
    for result in results:
        block_ids_for_chunk = []
        result_text_lower = result.text.lower()
        
        for block in blocks:
            block_id = block.get("id")
            preview = block.get("text_preview", "").lower()
            
            # If block preview is in chunk text, include it
            if preview and preview in result_text_lower:
                block_ids_for_chunk.append(block_id)
        
        # Update the result with block IDs
        result.source_block_ids = block_ids_for_chunk
    
    return results
