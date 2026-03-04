from __future__ import annotations

from algl_pdf_helper.chunker import chunk_page_words, MIN_CHUNK_WORDS


def test_chunk_ids_and_overlap():
    """Test chunk ID format and overlap behavior.
    
    Note: MIN_CHUNK_WORDS enforces a minimum chunk size (20 words),
    so we need to use a larger text to test multiple chunks.
    """
    # Use more words than MIN_CHUNK_WORDS to get multiple chunks
    words = [f"word{i}" for i in range(50)]  # 50 words
    text = " ".join(words)

    # chunk_words=25, overlap=5 => step=20
    chunk_words = 25
    overlap_words = 5
    chunks = chunk_page_words(
        doc_id="doc-abc",
        page=2,
        text=text,
        chunk_words=chunk_words,
        overlap_words=overlap_words,
    )

    # Should have at least 2 chunks with 50 words and step=20
    assert len(chunks) >= 2, f"Expected at least 2 chunks, got {len(chunks)}"
    
    # Check ID format
    ids = [cid for cid, _ in chunks]
    assert ids[0] == "doc-abc:p2:c1"
    assert ids[1] == "doc-abc:p2:c2"

    # Overlap check: verify overlap exists between consecutive chunks
    if len(chunks) >= 2:
        first_chunk_words = set(chunks[0][1].split())
        second_chunk_words = set(chunks[1][1].split())
        overlap = first_chunk_words & second_chunk_words
        assert len(overlap) > 0, "Expected overlap between chunks"
