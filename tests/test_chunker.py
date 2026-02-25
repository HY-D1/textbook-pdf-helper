from __future__ import annotations

from algl_pdf_helper.chunker import chunk_page_words


def test_chunk_ids_and_overlap():
    text = "one two three four five six seven eight nine ten"

    # chunk_words=4, overlap=1 => step=3
    chunks = chunk_page_words(
        doc_id="doc-abc",
        page=2,
        text=text,
        chunk_words=4,
        overlap_words=1,
    )

    ids = [cid for cid, _ in chunks]
    assert ids == ["doc-abc:p2:c1", "doc-abc:p2:c2", "doc-abc:p2:c3"]

    # Overlap check: last word of chunk1 is first overlap word of chunk2
    assert chunks[0][1].split()[-1] == chunks[1][1].split()[0]
