from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path
from typing import Literal

import fitz  # PyMuPDF

from .clean import normalize_text
from .quality_metrics import (
    QualityThresholds,
    TextCoverageAnalyzer,
    validate_text_quality,
)


# Legacy minimum quality thresholds (kept for backwards compatibility)
MIN_EXTRACTED_CHARS = 500  # Minimum total characters
MIN_READABLE_RATIO = 0.7   # Ratio of readable chars to total chars
MAX_GIBBERISH_RATIO = 0.3  # Maximum ratio of gibberish patterns

# Text coverage threshold for new quality system
MIN_TEXT_COVERAGE = 0.70

ExtractionStrategy = Literal["direct", "ocrmypdf", "marker"]


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


def check_text_coverage(pages: list[tuple[int, str]], min_coverage: float = None) -> dict:
    """Check text coverage using the new quality metrics system.
    
    Args:
        pages: List of (page_number, text) tuples
        min_coverage: Minimum required coverage threshold
        
    Returns:
        Coverage check results with pass/fail status
    """
    if min_coverage is None:
        min_coverage = MIN_TEXT_COVERAGE
    
    if not pages:
        return {
            "coverage_score": 0.0,
            "meets_threshold": False,
            "page_count": 0,
            "total_chars": 0,
            "reason": "No pages extracted",
        }
    
    analyzer = TextCoverageAnalyzer()
    total_text = "\n".join(text for _, text in pages)
    coverage = analyzer.calculate_coverage(total_text)
    
    meets_threshold = coverage >= min_coverage
    reason = ""
    if not meets_threshold:
        reason = f"Text coverage {coverage:.1%} below threshold {min_coverage:.1%}"
    
    return {
        "coverage_score": coverage,
        "meets_threshold": meets_threshold,
        "page_count": len(pages),
        "total_chars": len(total_text),
        "threshold": min_coverage,
        "reason": reason,
    }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_pages_fitz(pdf_path: Path) -> list[tuple[int, str]]:
    """Extract text pages from a PDF using PyMuPDF.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        List of (page_number, text) tuples
        
    Raises:
        FileNotFoundError: If the PDF file does not exist
        PermissionError: If the path is a directory or permission denied
        RuntimeError: If the PDF is corrupted, invalid, or password-protected
    """
    # Check if file exists
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    # Check if it's a file (not a directory)
    if pdf_path.is_dir():
        raise PermissionError(f"Path is a directory, not a file: {pdf_path}")
    
    try:
        doc = fitz.open(pdf_path)
    except fitz.FileDataError as e:
        error_msg = str(e).lower()
        if "password" in error_msg or "encrypted" in error_msg or "crypt" in error_msg:
            raise RuntimeError(
                f"PDF is password-protected or encrypted: {pdf_path}. "
                f"Please provide a password or decrypt the file first."
            ) from e
        elif "no file" in error_msg or "is no file" in error_msg:
            raise RuntimeError(
                f"Invalid PDF file (may be corrupted or not a PDF): {pdf_path}. "
                f"Please check the file format and try again."
            ) from e
        else:
            raise RuntimeError(
                f"Failed to open PDF file: {pdf_path}. Error: {e}"
            ) from e
    except Exception as e:
        error_msg = str(e).lower()
        if "password" in error_msg or "encrypted" in error_msg:
            raise RuntimeError(
                f"PDF is password-protected or encrypted: {pdf_path}"
            ) from e
        raise RuntimeError(
            f"Failed to open PDF file: {pdf_path}. The file may be corrupted, "
            f"truncated, or not a valid PDF. Error: {e}"
        ) from e
    
    pages: list[tuple[int, str]] = []
    try:
        for i in range(doc.page_count):
            page = doc.load_page(i)
            text = page.get_text("text")
            text = normalize_text(text)
            # Include empty pages to maintain stable page numbering
            pages.append((i + 1, text))
    finally:
        doc.close()
    return pages


def extract_pages_with_page_map(pdf_path: Path) -> tuple[list[tuple[int, str]], dict]:
    """Extract pages and return with page number mapping.
    
    This ensures page numbers remain stable after OCR processing.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Tuple of (pages, metadata) where metadata includes page count and mapping info
    """
    doc = fitz.open(pdf_path)
    pages: list[tuple[int, str]] = []
    
    try:
        page_count = doc.page_count
        
        for i in range(page_count):
            page = doc.load_page(i)
            text = page.get_text("text")
            text = normalize_text(text)
            # Always include page, even if empty, to maintain stable page numbering
            pages.append((i + 1, text))
        
        metadata = {
            "page_count": page_count,
            "source": "fitz",
            "page_numbers_stable": True,
        }
    finally:
        doc.close()
    
    return pages, metadata


def maybe_ocr_pdf(
    pdf_path: Path,
    *,
    force: bool,
    auto: bool,
    min_total_chars: int = 800,
    smart_skip_threshold: float = 0.90,
) -> tuple[Path, bool]:
    """Return (path_to_use, did_ocr).
    
    Args:
        pdf_path: Path to the PDF file
        force: Force OCR even if direct extraction seems to work
        auto: Automatically try OCR if direct extraction quality is poor
        min_total_chars: Minimum total characters threshold for auto mode
        smart_skip_threshold: Quality threshold above which OCR is skipped
                             even if force=True (0.0-1.0, default 0.90)
                             Set to 1.0 to disable smart skip.
                             
    Returns:
        Tuple of (path_to_use, did_ocr)
        
    Note:
        When force=True but the PDF has excellent text quality (above
        smart_skip_threshold), OCR will be skipped with a warning.
        This prevents OCR errors on digital PDFs that don't need it.
    """
    if not (force or auto):
        return pdf_path, False

    # Always check quality first to determine if OCR is actually needed
    try:
        pages = extract_pages_fitz(pdf_path)
        quality = check_extraction_quality(pages)
        coverage = check_text_coverage(pages)
    except Exception:
        pages = []
        quality = {"is_quality_good": False, "total_chars": 0}
        coverage = {"coverage_score": 0.0, "meets_threshold": False}

    if auto and not force:
        total = sum(len(t) for _, t in pages)
        if total >= min_total_chars and quality["is_quality_good"]:
            return pdf_path, False

    # SMART OCR SKIP: If PDF has excellent text quality, skip OCR even if forced
    # This prevents Tesseract errors on digital PDFs that don't need OCR
    if force and coverage["coverage_score"] >= smart_skip_threshold:
        import warnings
        warnings.warn(
            f"OCR was requested but PDF has excellent text quality "
            f"({coverage['coverage_score']:.1%} coverage). "
            f"Skipping OCR to avoid unnecessary processing and potential Tesseract errors. "
            f"Use --smart-skip-threshold=1.0 to force OCR anyway."
        )
        return pdf_path, False
    
    # Additional warning if OCR is forced on good quality PDF
    if force and quality["is_quality_good"]:
        import warnings
        warnings.warn(
            f"OCR is being forced on a PDF that already has good text quality "
            f"({quality['readable_ratio']:.1%} readable). "
            f"This may cause Tesseract errors and is usually unnecessary for digital PDFs."
        )

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
    # force_ocr=True allows OCR on PDFs that already have text
    try:
        ocrmypdf.ocr(
            str(pdf_path),
            str(out_path),
            deskew=True,
            rotate_pages=True,
            optimize=1,
            output_type="pdf",
            progress_bar=False,
            force_ocr=True,
        )
    except Exception as e:
        # Clean up temp directory on error
        cleanup_temp_pdf(out_path)
        error_msg = str(e).lower()
        
        # Provide helpful error messages for common Tesseract issues
        if "tesseract" in error_msg or "diacritics" in error_msg:
            raise RuntimeError(
                f"OCR failed with Tesseract error: {e}\n\n"
                f"This usually happens when trying to OCR a PDF that already has good text. "
                f"The PDF text quality was: {coverage['coverage_score']:.1%} coverage.\n\n"
                f"RECOMMENDATION: Process this PDF WITHOUT OCR using:\n"
                f"  algl-pdf index {pdf_path} --out <output-dir> --use-aliases\n\n"
                f"If you still need OCR, try:\n"
                f"  1. Check if Tesseract is properly installed: tesseract --version\n"
                f"  2. Update Tesseract to the latest version\n"
                f"  3. Process only specific pages that need OCR"
            ) from e
        else:
            raise RuntimeError(f"OCR failed: {e}") from e

    return out_path, True


def ocr_pdf_with_validation(
    pdf_path: Path,
    min_coverage: float = None,
    smart_skip_threshold: float = 0.90,
) -> tuple[Path, dict]:
    """OCR a PDF and validate the output quality.
    
    Creates a searchable PDF using OCRmyPDF and validates that
    the text extraction meets quality thresholds.
    
    SMART SKIP: If the PDF has excellent text quality (above smart_skip_threshold),
    OCR will be skipped and the original PDF will be returned.
    
    Args:
        pdf_path: Path to source PDF
        min_coverage: Minimum text coverage threshold
        smart_skip_threshold: Quality threshold above which OCR is skipped
                             even if requested (default 0.90 = 90%)
        
    Returns:
        Tuple of (output_path, validation_result)
        validation_result includes a 'skipped' flag if OCR was skipped
        due to high quality text.
        
    Raises:
        RuntimeError: If ocrmypdf is not installed or OCR fails
    """
    if min_coverage is None:
        min_coverage = MIN_TEXT_COVERAGE
    
    # Check quality first - maybe OCR isn't needed
    pages, _ = extract_pages_with_page_map(pdf_path)
    coverage_check = check_text_coverage(pages, min_coverage)
    
    # SMART SKIP: If PDF has excellent text quality, skip OCR
    if coverage_check["coverage_score"] >= smart_skip_threshold:
        import warnings
        warnings.warn(
            f"OCR skipped: PDF has excellent text quality "
            f"({coverage_check['coverage_score']:.1%} coverage). "
            f"Processing without OCR to avoid Tesseract errors."
        )
        # Return original PDF with modified coverage check showing it was skipped
        coverage_check["skipped"] = True
        coverage_check["skip_reason"] = "high_quality_text"
        return pdf_path, coverage_check
    
    try:
        import ocrmypdf  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "OCR requested but ocrmypdf is not installed. "
            "Install with: pip install -e '.[ocr]'"
        ) from e

    tmp_dir = Path(tempfile.mkdtemp(prefix="algl_pdf_"))
    out_path = tmp_dir / (pdf_path.stem + ".ocr.pdf")

    # OCR with safe defaults that preserve page structure
    # force_ocr=True allows OCR on PDFs that already have text
    try:
        ocrmypdf.ocr(
            str(pdf_path),
            str(out_path),
            deskew=True,
            rotate_pages=True,
            optimize=1,
            output_type="pdf",
            progress_bar=False,
            force_ocr=True,
        )
    except Exception as e:
        # Clean up temp directory on error
        cleanup_temp_pdf(out_path)
        error_msg = str(e).lower()
        
        # Provide helpful error messages for common Tesseract issues
        if "tesseract" in error_msg or "diacritics" in error_msg:
            raise RuntimeError(
                f"OCR failed with Tesseract error: {e}\n\n"
                f"This usually happens when trying to OCR a PDF that already has good text. "
                f"The PDF text quality was: {coverage_check['coverage_score']:.1%} coverage.\n\n"
                f"RECOMMENDATION: Process this PDF WITHOUT OCR using:\n"
                f"  algl-pdf index {pdf_path} --out <output-dir> --use-aliases\n\n"
                f"If you still need OCR, try:\n"
                f"  1. Check if Tesseract is properly installed: tesseract --version\n"
                f"  2. Update Tesseract to the latest version\n"
                f"  3. Process only specific pages that need OCR"
            ) from e
        else:
            raise RuntimeError(f"OCR failed: {e}") from e

    # Validate OCR quality
    pages, _ = extract_pages_with_page_map(out_path)
    coverage_check = check_text_coverage(pages, min_coverage)
    coverage_check["skipped"] = False
    
    return out_path, coverage_check


def extract_with_strategy(
    pdf_path: Path,
    strategy: ExtractionStrategy = "direct",
    min_coverage: float = None,
    force_ocr: bool = False,
    auto_ocr: bool = True,
    smart_skip_threshold: float = 0.90,
) -> tuple[list[tuple[int, str]], dict]:
    """Extract PDF text using specified strategy with quality validation.
    
    This is the main extraction function that supports multiple strategies:
    - "direct": Direct text extraction using PyMuPDF
    - "ocrmypdf": OCR with OCRmyPDF (creates searchable PDF first)
    - "marker": Use Marker library (if available)
    
    SMART OCR SKIP: When force_ocr=True but the PDF has excellent text quality
    (above smart_skip_threshold), OCR will be skipped to avoid Tesseract errors
    on digital PDFs that don't need OCR.
    
    Args:
        pdf_path: Path to PDF file
        strategy: Extraction strategy to use
        min_coverage: Minimum text coverage threshold (default: 0.70)
        force_ocr: Force OCR even if direct extraction seems to work
        auto_ocr: Automatically try OCR if direct extraction quality is poor
        smart_skip_threshold: Quality threshold above which OCR is skipped
                             even if force_ocr=True (default 0.90 = 90%)
        
    Returns:
        Tuple of (pages, extraction_info) where:
        - pages: List of (page_number, text) tuples
        - extraction_info: Dict with metadata about the extraction
        
    Raises:
        FileNotFoundError: If PDF doesn't exist
        RuntimeError: If extraction fails or quality threshold not met
        ValueError: If strategy is invalid
    """
    if min_coverage is None:
        min_coverage = MIN_TEXT_COVERAGE
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    extraction_info = {
        "strategy": strategy,
        "ocr_applied": False,
        "ocr_skipped": False,
        "skip_reason": None,
        "page_count": 0,
        "coverage_score": 0.0,
        "meets_threshold": False,
        "warnings": [],
    }
    
    temp_pdf_path: Path | None = None
    
    try:
        if strategy == "direct":
            # Try direct extraction first
            pages, metadata = extract_pages_with_page_map(pdf_path)
            extraction_info["page_count"] = metadata["page_count"]
            
            # Check quality
            coverage_check = check_text_coverage(pages, min_coverage)
            extraction_info["coverage_score"] = coverage_check["coverage_score"]
            extraction_info["meets_threshold"] = coverage_check["meets_threshold"]
            
            # SMART SKIP: If quality is excellent and OCR is forced, skip OCR
            if force_ocr and coverage_check["coverage_score"] >= smart_skip_threshold:
                extraction_info["warnings"].append(
                    f"⚠️ OCR was requested but PDF has excellent text quality "
                    f"({coverage_check['coverage_score']:.1%} coverage). "
                    f"Skipping OCR to avoid Tesseract errors on digital PDFs."
                )
                extraction_info["ocr_skipped"] = True
                extraction_info["skip_reason"] = "high_quality_text"
                # Continue with direct extraction results
            
            # If quality is poor and auto_ocr is enabled, retry with OCR
            elif not coverage_check["meets_threshold"] and auto_ocr and not force_ocr:
                extraction_info["warnings"].append(
                    f"Direct extraction quality poor ({coverage_check['coverage_score']:.1%}), "
                    "retrying with OCR..."
                )
                
                temp_pdf_path, ocr_validation = ocr_pdf_with_validation(
                    pdf_path, min_coverage, smart_skip_threshold
                )
                
                # Check if OCR was skipped due to high quality
                if ocr_validation.get("skipped"):
                    extraction_info["warnings"].append(
                        "OCR was auto-skipped: PDF has excellent text quality"
                    )
                    extraction_info["ocr_skipped"] = True
                    extraction_info["skip_reason"] = ocr_validation.get("skip_reason")
                else:
                    pages, metadata = extract_pages_with_page_map(temp_pdf_path)
                    extraction_info["ocr_applied"] = True
                    extraction_info["coverage_score"] = ocr_validation["coverage_score"]
                    extraction_info["meets_threshold"] = ocr_validation["meets_threshold"]
                
                if not extraction_info["meets_threshold"] and not extraction_info["ocr_skipped"]:
                    extraction_info["warnings"].append(
                        f"OCR extraction also failed quality threshold: "
                        f"{extraction_info['coverage_score']:.1%} < {min_coverage:.1%}"
                    )
            
            elif force_ocr and not extraction_info.get("ocr_skipped"):
                # Force OCR even if direct extraction was okay (unless smart skip kicked in)
                temp_pdf_path, ocr_validation = ocr_pdf_with_validation(
                    pdf_path, min_coverage, smart_skip_threshold
                )
                
                # Check if OCR was skipped due to high quality
                if ocr_validation.get("skipped"):
                    extraction_info["warnings"].append(
                        "OCR was auto-skipped: PDF has excellent text quality"
                    )
                    extraction_info["ocr_skipped"] = True
                    extraction_info["skip_reason"] = ocr_validation.get("skip_reason")
                else:
                    pages, metadata = extract_pages_with_page_map(temp_pdf_path)
                    extraction_info["ocr_applied"] = True
                    extraction_info["coverage_score"] = ocr_validation["coverage_score"]
                    extraction_info["meets_threshold"] = ocr_validation["meets_threshold"]
        
        elif strategy == "ocrmypdf":
            # Always use OCR (but respect smart skip)
            temp_pdf_path, ocr_validation = ocr_pdf_with_validation(
                pdf_path, min_coverage, smart_skip_threshold
            )
            
            # Check if OCR was skipped due to high quality
            if ocr_validation.get("skipped"):
                extraction_info["warnings"].append(
                    "OCR was auto-skipped: PDF has excellent text quality"
                )
                extraction_info["ocr_skipped"] = True
                extraction_info["skip_reason"] = ocr_validation.get("skip_reason")
                pages, metadata = extract_pages_with_page_map(pdf_path)
            else:
                pages, metadata = extract_pages_with_page_map(temp_pdf_path)
                extraction_info["ocr_applied"] = True
            
            extraction_info["page_count"] = metadata["page_count"]
            extraction_info["coverage_score"] = ocr_validation["coverage_score"]
            extraction_info["meets_threshold"] = ocr_validation["meets_threshold"]
        
        elif strategy == "marker":
            # Use Marker library if available
            try:
                pages, extraction_info = _extract_with_marker(pdf_path)
                
                # Validate coverage
                coverage_check = check_text_coverage(pages, min_coverage)
                extraction_info["coverage_score"] = coverage_check["coverage_score"]
                extraction_info["meets_threshold"] = coverage_check["meets_threshold"]
                
            except ImportError:
                raise RuntimeError(
                    "Marker strategy requested but marker is not installed. "
                    "Install with: pip install marker-pdf"
                )
        
        else:
            raise ValueError(f"Unknown extraction strategy: {strategy}")
        
        # Final validation
        if not extraction_info["meets_threshold"] and not extraction_info.get("ocr_skipped"):
            # Still return pages but warn
            extraction_info["warnings"].append(
                f"Text coverage {extraction_info['coverage_score']:.1%} "
                f"below threshold {min_coverage:.1%}"
            )
        
        return pages, extraction_info
    
    finally:
        # Cleanup temp file if we created one
        if temp_pdf_path is not None and temp_pdf_path != pdf_path:
            cleanup_temp_pdf(temp_pdf_path)


def _extract_with_marker(pdf_path: Path) -> tuple[list[tuple[int, str]], dict]:
    """Extract PDF using Marker library.
    
    Marker is better for complex layouts, tables, and multi-column documents.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Tuple of (pages, extraction_info)
    """
    try:
        from marker.convert import convert_single_pdf
        from marker.models import load_all_models
    except ImportError as e:
        raise ImportError("marker-pdf is not installed") from e
    
    # Load models (this may take time on first run)
    model_lst = load_all_models()
    
    # Convert PDF
    full_text, images, out_meta = convert_single_pdf(
        str(pdf_path),
        model_lst,
    )
    
    # Marker returns full text, need to estimate page breaks
    # For now, return as single "page" or attempt to split by form feed
    pages_text = full_text.split('\f') if '\f' in full_text else [full_text]
    
    pages = []
    for i, text in enumerate(pages_text):
        if text.strip():
            pages.append((i + 1, normalize_text(text)))
    
    extraction_info = {
        "strategy": "marker",
        "ocr_applied": False,  # Marker may use OCR internally
        "page_count": len(pages),
        "marker_metadata": out_meta,
    }
    
    return pages, extraction_info


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
