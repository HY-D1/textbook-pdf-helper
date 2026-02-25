from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

import fitz  # PyMuPDF

from .clean import normalize_text


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
