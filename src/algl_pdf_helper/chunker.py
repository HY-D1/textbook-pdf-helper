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


# ============================================================================
# Student-Optimized Chunking
# ============================================================================

# Optimal chunk sizes for student learning
DEFAULT_CHUNK_WORDS = 150  # Reduced from 180 for better granularity
DEFAULT_OVERLAP_WORDS = 30  # Keep same overlap for context preservation

# Minimum chunk size to avoid tiny fragments
MIN_CHUNK_WORDS = 20

# Sentence-ending punctuation for boundary detection
SENTENCE_ENDINGS = {'.', '!', '?', '。', '！', '？'}


def find_sentence_boundary(text: str, target_pos: int, max_search: int = 50) -> int:
    """Find the nearest sentence boundary to the target position.
    
    This helps chunks end at natural breaks rather than mid-sentence.
    
    Args:
        text: The text to search
        target_pos: Target position to find boundary near
        max_search: Maximum characters to search forward/backward
        
    Returns:
        Position of the best sentence boundary
    """
    if target_pos >= len(text):
        return len(text)
    
    # Search forward for sentence ending
    forward_pos = target_pos
    for i in range(target_pos, min(len(text), target_pos + max_search)):
        if text[i] in SENTENCE_ENDINGS:
            # Found ending, include the space/punctuation after
            forward_pos = i + 1
            # Skip trailing whitespace
            while forward_pos < len(text) and text[forward_pos] in ' \n\t':
                forward_pos += 1
            break
    
    # Search backward for sentence ending
    backward_pos = target_pos
    for i in range(target_pos, max(0, target_pos - max_search), -1):
        if text[i] in SENTENCE_ENDINGS:
            backward_pos = i + 1
            # Skip trailing whitespace
            while backward_pos < len(text) and text[backward_pos] in ' \n\t':
                backward_pos += 1
            break
    
    # Choose the closest boundary
    forward_dist = abs(forward_pos - target_pos)
    backward_dist = abs(backward_pos - target_pos)
    
    if forward_dist <= backward_dist and forward_dist <= max_search:
        return forward_pos
    elif backward_dist <= max_search:
        return backward_pos
    
    # No good boundary found, use target position
    return target_pos


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
    preserve_sentences: bool = True,
) -> list[ChunkResult]:
    """Return list of ChunkResult with provenance information.
    
    Student-optimized version that:
    - Uses smaller default chunk size (150 words) for better learning
    - Preserves sentence boundaries where possible
    - Ensures minimum chunk size to avoid tiny fragments
    
    Args:
        doc_id: Document identifier
        page: Page number
        text: Text to chunk
        chunk_words: Number of words per chunk
        overlap_words: Number of words to overlap between chunks
        source_block_ids: Optional list of block IDs for this page's text
        preserve_sentences: Whether to try to end chunks at sentence boundaries
        
    Returns:
        List of ChunkResult objects with full provenance
    """
    words = [w for w in text.split() if w]
    if not words:
        return []
    
    # Ensure chunk_words is at least MIN_CHUNK_WORDS
    chunk_words = max(chunk_words, MIN_CHUNK_WORDS)
    
    # Ensure overlap is smaller than chunk size
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
        
        # Join words into text
        chunk_text = " ".join(slice_words)
        
        # Try to find sentence boundary if preserving sentences
        if preserve_sentences and len(slice_words) == chunk_words:
            adjusted_text = chunk_text
            boundary_pos = find_sentence_boundary(chunk_text, len(chunk_text) - 20)
            if boundary_pos < len(chunk_text) - 10:  # Only adjust if significant
                adjusted_text = chunk_text[:boundary_pos].strip()
                # Recalculate words for next iteration
                adjusted_words = adjusted_text.split()
                # Adjust step to account for shortened chunk
                actual_step = max(1, len(adjusted_words) - overlap_words)
            else:
                actual_step = step
        else:
            actual_step = step
        
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
        
        start += actual_step
    
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


# ============================================================================
# Student-Optimized Chunking Functions
# ============================================================================

def chunk_for_learning(
    *,
    doc_id: str,
    page: int,
    text: str,
    chunk_words: int = DEFAULT_CHUNK_WORDS,
    overlap_words: int = DEFAULT_OVERLAP_WORDS,
    source_block_ids: list[str] | None = None,
) -> list[ChunkResult]:
    """Chunk text optimized for student learning.
    
    Uses smaller chunks (150 words) for better granularity while
    maintaining context through overlap. Tries to preserve sentence
    boundaries for more natural reading.
    
    Args:
        doc_id: Document identifier
        page: Page number
        text: Text to chunk
        chunk_words: Number of words per chunk (default: 150)
        overlap_words: Number of words to overlap (default: 30)
        source_block_ids: Optional list of block IDs
        
    Returns:
        List of ChunkResult objects
    """
    return chunk_page_words_with_provenance(
        doc_id=doc_id,
        page=page,
        text=text,
        chunk_words=chunk_words,
        overlap_words=overlap_words,
        source_block_ids=source_block_ids,
        preserve_sentences=True,
    )


def calculate_optimal_chunk_size(
    text: str,
    min_words: int = 100,
    max_words: int = 200,
    target_chunks: int = 5,
) -> int:
    """Calculate optimal chunk size based on text length.
    
    This helps determine the best chunk size for a given amount
    of text, balancing granularity with readability.
    
    Args:
        text: The text to analyze
        min_words: Minimum words per chunk
        max_words: Maximum words per chunk
        target_chunks: Target number of chunks for this text
        
    Returns:
        Recommended chunk size in words
    """
    words = text.split()
    word_count = len(words)
    
    if word_count <= min_words:
        return word_count
    
    # Calculate chunk size to get approximately target_chunks
    chunk_size = word_count // target_chunks
    
    # Clamp to valid range
    return max(min_words, min(max_words, chunk_size))
