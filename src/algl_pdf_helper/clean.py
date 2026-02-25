from __future__ import annotations

import re
from collections import Counter


_SPACE_TABS = re.compile(r"[ \t]+")
_MULTI_NL = re.compile(r"\n{2,}")


def normalize_text(text: str) -> str:
    return _MULTI_NL.sub("\n", _SPACE_TABS.sub(" ", text.replace("\x00", " "))).strip()


def strip_repeated_headers_footers(
    pages: list[tuple[int, str]],
    *,
    head_lines: int = 2,
    foot_lines: int = 2,
    min_pages: int = 5,
    ratio: float = 0.6,
    max_line_len: int = 80,
) -> list[tuple[int, str]]:
    """Heuristic removal of repeating headers/footers.

    Safe default: only triggers when there are enough pages.
    """
    if len(pages) < min_pages:
        return pages

    head_counter: Counter[str] = Counter()
    foot_counter: Counter[str] = Counter()

    split_pages: list[tuple[int, list[str]]] = []
    for page, text in pages:
        lines = [ln.strip() for ln in text.splitlines()]
        split_pages.append((page, lines))
        for ln in lines[:head_lines]:
            if 0 < len(ln) <= max_line_len:
                head_counter[ln] += 1
        for ln in lines[-foot_lines:]:
            if 0 < len(ln) <= max_line_len:
                foot_counter[ln] += 1

    threshold = int(len(pages) * ratio)
    head_remove = {ln for ln, c in head_counter.items() if c >= threshold}
    foot_remove = {ln for ln, c in foot_counter.items() if c >= threshold}

    cleaned: list[tuple[int, str]] = []
    for page, lines in split_pages:
        out_lines = []
        for i, ln in enumerate(lines):
            if i < head_lines and ln in head_remove:
                continue
            if i >= len(lines) - foot_lines and ln in foot_remove:
                continue
            out_lines.append(ln)
        cleaned.append((page, "\n".join(out_lines)))

    return cleaned
