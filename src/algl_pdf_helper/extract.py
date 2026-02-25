from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path

import fitz  # PyMuPDF

from .clean import normalize_text


# Minimum quality thresholds for extracted text
MIN_EXTRACTED_CHARS = 500  # Minimum total characters
MIN_READABLE_RATIO = 0.7   # Ratio of readable chars to total chars
MAX_GIBBERISH_RATIO = 0.3  # Maximum ratio of gibberish patterns


def calculate_text_quality(text: str) -> dict:
    """Calculate quality metrics for extracted text.
    
    Returns dict with:
    - total_chars: Total character count
    - readable_chars: Count of alphanumeric + spaces + punctuation
    - gibberish_patterns: Count of suspicious patterns
    - readable_ratio: Ratio of readable to total chars
    - is_quality_good: Boolean overall quality assessment
    """
    if not text:
        return {
            "total_chars": 0,
            "readable_chars": 0,
            "gibberish_patterns": 0,
            "readable_ratio": 0.0,
            "is_quality_good": False,
        }
    
    total_chars = len(text)
    
    # Count readable characters (letters, numbers, spaces, common punctuation)
    readable_pattern = re.compile(r'[\w\s.,;:!?\-\'"()\[\]{}]')
    readable_chars = len(readable_pattern.findall(text))
    readable_ratio = readable_chars / total_chars if total_chars > 0 else 0
    
    # Detect gibberish patterns (common OCR artifacts)
    gibberish_patterns = [
        r'[_\-]{3,}',           # Repeated underscores/dashes
        r'[\^\*@#%&]{2,}',      # Repeated special chars
        r'\.{4,}',              # Too many dots
        r'[a-z][A-Z]{2,}[a-z]', # Odd caps pattern
        r'[^\w\s.,;:!?\-\'"()\[\]{}]{3,}',  # Long sequences of weird chars
    ]
    
    gibberish_count = 0
    for pattern in gibberish_patterns:
        gibberish_count += len(re.findall(pattern, text))
    
    gibberish_ratio = gibberish_count / total_chars if total_chars > 0 else 0
    
    # Quality is good if:
    # 1. Enough total characters
    # 2. High ratio of readable characters
    # 3. Low ratio of gibberish patterns
    is_quality_good = (
        total_chars >= MIN_EXTRACTED_CHARS and
        readable_ratio >= MIN_READABLE_RATIO and
        gibberish_ratio <= MAX_GIBBERISH_RATIO
    )
    
    return {
        "total_chars": total_chars,
        "readable_chars": readable_chars,
        "gibberish_patterns": gibberish_count,
        "readable_ratio": readable_ratio,
        "gibberish_ratio": gibberish_ratio,
        "is_quality_good": is_quality_good,
    }


def check_extraction_quality(pages: list[tuple[int, str]]) -> dict:
    """Check quality of extracted text from all pages.
    
    Returns quality metrics and recommendation.
    """
    if not pages:
        return {
            "total_chars": 0,
            "page_count": 0,
            "is_quality_good": False,
            "needs_ocr": True,
            "reason": "No text extracted",
        }
    
    total_text = " ".join(text for _, text in pages)
    quality = calculate_text_quality(total_text)
    
    # Determine if OCR is needed
    needs_ocr = not quality["is_quality_good"]
    reason = ""
    
    if quality["total_chars"] < MIN_EXTRACTED_CHARS:
        reason = f"Too few characters ({quality['total_chars']} < {MIN_EXTRACTED_CHARS})"
    elif quality["readable_ratio"] < MIN_READABLE_RATIO:
        reason = f"Low readable ratio ({quality['readable_ratio']:.1%} < {MIN_READABLE_RATIO:.1%})"
    elif quality["gibberish_ratio"] > MAX_GIBBERISH_RATIO:
        reason = f"Too many artifacts ({quality['gibberish_ratio']:.1%} gibberish)"
    
    return {
        "total_chars": quality["total_chars"],
        "page_count": len(pages),
        "readable_ratio": quality["readable_ratio"],
        "gibberish_ratio": quality["gibberish_ratio"],
        "is_quality_good": quality["is_quality_good"],
        "needs_ocr": needs_ocr,
        "reason": reason,
    }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_pages_fitz(pdf_path: Path) -> list[tuple[int, str]]:
    doc = fitz.open(pdf_path)
    pages: list[tuple[int, str]] = []
    for i in range(doc.page_count):
        page = doc.load_page(i)
        text = page.get_text("text")
        text = normalize_text(text)
        if text:
            pages.append((i + 1, text))
    doc.close()
    return pages


def maybe_ocr_pdf(
    pdf_path: Path,
    *,
    force: bool,
    auto: bool,
    min_total_chars: int = 800,
) -> tuple[Path, bool]:
    """Return (path_to_use, did_ocr)."""
    if not (force or auto):
        return pdf_path, False

    if auto and not force:
        try:
            pages = extract_pages_fitz(pdf_path)
        except Exception:
            pages = []
        total = sum(len(t) for _, t in pages)
        if total >= min_total_chars:
            return pdf_path, False

    try:
        import ocrmypdf  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "OCR requested but ocrmypdf is not installed. "
            "Install with: pip install -e '.[ocr]'"
        ) from e

    tmp_dir = Path(tempfile.mkdtemp(prefix="algl_pdf_"))
    out_path = tmp_dir / (pdf_path.stem + ".ocr.pdf")

    # Minimal safe defaults: deskew + rotate pages.
    ocrmypdf.ocr(
        str(pdf_path),
        str(out_path),
        deskew=True,
        rotate_pages=True,
        optimize=1,
        output_type="pdf",
        progress_bar=False,
    )

    return out_path, True


def cleanup_temp_pdf(path: Path) -> None:
    # Only remove files in our temp dir pattern.
    try:
        parent = path.parent
        if parent.name.startswith("algl_pdf_"):
            for p in parent.iterdir():
                try:
                    p.unlink()
                except Exception:
                    pass
            try:
                parent.rmdir()
            except Exception:
                pass
    except Exception:
        pass
