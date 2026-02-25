from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PageText:
    page: int
    text: str


def chunk_page_words(
    *,
    doc_id: str,
    page: int,
    text: str,
    chunk_words: int,
    overlap_words: int,
) -> list[tuple[str, str]]:
    """Return list of (chunk_id, chunk_text)."""
    words = [w for w in text.split() if w]
    if not words:
        return []

    step = max(1, chunk_words - overlap_words)
    out: list[tuple[str, str]] = []

    start = 0
    while start < len(words):
        slice_words = words[start : start + chunk_words]
        if not slice_words:
            break

        chunk_index = (start // step) + 1
        chunk_id = f"{doc_id}:p{page}:c{chunk_index}"
        out.append((chunk_id, " ".join(slice_words)))

        if start + chunk_words >= len(words):
            break

        start += step

    return out
