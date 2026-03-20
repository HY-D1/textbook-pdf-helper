from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import fitz  # PyMuPDF

from .quality_metrics import TextCoverageAnalyzer, QualityThresholds

# Alias for the per-embedded-text OCR floor (kept local to avoid long dot-path)
_EMBEDDED_TEXT_OCR_FLOOR = QualityThresholds.EMBEDDED_TEXT_OCR_FLOOR


ExtractionStrategy = Literal["direct", "ocrmypdf", "marker"]


@dataclass
class PreflightReport:
    """Comprehensive preflight analysis report for a PDF.
    
    This report helps determine the best extraction strategy and flags
    potential issues before processing.
    """
    # Core detection
    has_embedded_text: bool = False
    ocr_needed: bool = False
    
    # Structure estimation
    estimated_table_count: int = 0
    estimated_figure_count: int = 0
    
    # Quality flags
    warning_flags: list[str] = field(default_factory=list)
    
    # Coverage metrics
    text_coverage_score: float = 0.0
    
    # Recommendation
    recommended_strategy: ExtractionStrategy = "direct"
    
    # Additional metadata
    page_count: int = 0
    sample_pages_analyzed: list[int] = field(default_factory=list)
    average_page_text_density: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert report to dictionary for JSON serialization."""
        return {
            "has_embedded_text": self.has_embedded_text,
            "ocr_needed": self.ocr_needed,
            "estimated_table_count": self.estimated_table_count,
            "estimated_figure_count": self.estimated_figure_count,
            "warning_flags": self.warning_flags,
            "text_coverage_score": self.text_coverage_score,
            "recommended_strategy": self.recommended_strategy,
            "page_count": self.page_count,
            "sample_pages_analyzed": self.sample_pages_analyzed,
            "average_page_text_density": self.average_page_text_density,
        }
    
    @property
    def is_extractable(self) -> bool:
        """Check if PDF is extractable with current strategy."""
        # OCR / Marker strategies are always considered extractable (the tool
        # handles the heavy lifting).
        if self.recommended_strategy in ("ocrmypdf", "marker"):
            return True
        # For the direct strategy, extractability is determined by whether OCR
        # is genuinely needed.  A digital PDF whose coverage heuristic lands
        # between EMBEDDED_TEXT_OCR_FLOOR (0.30) and MIN_TEXT_COVERAGE (0.70)
        # is still perfectly fine for direct extraction; ocr_needed will be
        # False for it, so this correctly returns True.
        if self.recommended_strategy == "direct":
            return not self.ocr_needed
        return False
    
    @property
    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"PDF Analysis Report ({self.page_count} pages)",
            f"  Embedded text: {'Yes' if self.has_embedded_text else 'No'}",
            f"  OCR needed: {'Yes' if self.ocr_needed else 'No'}",
            f"  Text coverage: {self.text_coverage_score:.1%}",
            f"  Tables detected: ~{self.estimated_table_count}",
            f"  Figures detected: ~{self.estimated_figure_count}",
            f"  Recommended strategy: {self.recommended_strategy}",
        ]
        if self.warning_flags:
            lines.append(f"  Warnings: {', '.join(self.warning_flags)}")
        return "\n".join(lines)


def select_sample_pages(page_count: int, min_samples: int = 5) -> list[int]:
    """Select representative page samples from beginning, middle, and end.
    
    Args:
        page_count: Total number of pages in PDF
        min_samples: Minimum number of samples to return
        
    Returns:
        List of 0-based page indices to sample
    """
    if page_count <= min_samples:
        return list(range(page_count))
    
    samples = set()
    
    # Always include first few pages (usually contain TOC, intro)
    samples.update([0, 1, 2])
    
    # Middle section samples
    mid = page_count // 2
    samples.update([mid - 1, mid, mid + 1])
    
    # End samples (often have index, references)
    samples.update([page_count - 2, page_count - 1])
    
    # Ensure we have enough by adding evenly spaced pages
    if len(samples) < min_samples:
        step = page_count // min_samples
        for i in range(0, page_count, step):
            samples.add(i)
            if len(samples) >= min_samples:
                break
    
    # Filter valid pages and sort
    return sorted([s for s in samples if 0 <= s < page_count])


def detect_embedded_text(doc: fitz.Document, sample_pages: list[int]) -> bool:
    """Check if PDF has extractable embedded text.
    
    Args:
        doc: Open PyMuPDF document
        sample_pages: List of page indices to check
        
    Returns:
        True if significant embedded text is found
    """
    total_text_len = 0
    pages_with_text = 0
    
    for page_idx in sample_pages:
        try:
            page = doc.load_page(page_idx)
            text = page.get_text("text")
            text_len = len(text.strip()) if text else 0
            if text_len > 10:  # At least some real text
                pages_with_text += 1
                total_text_len += text_len
        except Exception:
            continue
    
    # Consider it has embedded text if:
    # 1. At least 50% of sampled pages have text
    # 2. Average text length per page is reasonable
    if len(sample_pages) == 0:
        return False
    
    page_ratio = pages_with_text / len(sample_pages)
    avg_text_len = total_text_len / len(sample_pages) if sample_pages else 0
    
    return page_ratio >= 0.5 and avg_text_len >= 100


def estimate_structure_complexity(
    doc: fitz.Document, 
    sample_pages: list[int]
) -> tuple[int, int, list[str]]:
    """Estimate tables, figures, and layout complexity.
    
    Args:
        doc: Open PyMuPDF document
        sample_pages: List of page indices to check
        
    Returns:
        Tuple of (table_count, figure_count, warning_flags)
    """
    table_count = 0
    figure_count = 0
    flags = []
    
    column_bleed_scores = []
    header_footer_scores = []
    
    for page_idx in sample_pages:
        try:
            page = doc.load_page(page_idx)
            
            # Detect tables via layout analysis
            tables = detect_tables_on_page(page)
            table_count += len(tables)
            
            # Detect figures (images without much text)
            figures = detect_figures_on_page(page)
            figure_count += len(figures)
            
            # Check for column bleed
            bleed_score = detect_column_bleed(page)
            if bleed_score > 0.3:
                column_bleed_scores.append(bleed_score)
            
            # Check headers/footers
            hf_score = detect_headers_footers(page)
            if hf_score > 0.5:
                header_footer_scores.append(hf_score)
                
        except Exception:
            continue
    
    # Extrapolate to full document based on sample
    if sample_pages:
        scale_factor = doc.page_count / len(sample_pages)
        table_count = int(table_count * scale_factor)
        figure_count = int(figure_count * scale_factor)
    
    # Set warning flags based on aggregated scores
    if column_bleed_scores:
        avg_bleed = sum(column_bleed_scores) / len(column_bleed_scores)
        if avg_bleed > 0.5:
            flags.append("2-column bleed detected")
    
    if header_footer_scores:
        avg_hf = sum(header_footer_scores) / len(header_footer_scores)
        if avg_hf > 0.7:
            flags.append("heavy headers/footers")
    
    return table_count, figure_count, flags


def detect_tables_on_page(page: fitz.Page) -> list[dict]:
    """Detect potential tables on a page.
    
    Uses heuristics like:
    - Multiple lines with similar vertical spacing
    - Columnar text alignment
    - Ruling lines (if vector graphics present)
    
    Returns:
        List of detected table regions
    """
    tables = []
    
    try:
        # Get text blocks
        blocks = page.get_text("blocks")
        if not blocks:
            return tables
        
        # Look for aligned text patterns suggesting columns
        y_positions = {}
        for block in blocks:
            if len(block) >= 5:
                y_pos = round(block[1], 1)  # y0 coordinate
                if y_pos not in y_positions:
                    y_positions[y_pos] = []
                y_positions[y_pos].append(block)
        
        # Find rows with multiple blocks (potential table rows)
        table_rows = 0
        for y_pos, row_blocks in y_positions.items():
            if len(row_blocks) >= 3:  # At least 3 columns
                table_rows += 1
        
        # If we have 3+ aligned rows, it's likely a table
        if table_rows >= 3:
            tables.append({
                "rows": table_rows,
                "confidence": min(1.0, table_rows / 10),
            })
    
    except Exception:
        pass
    
    return tables


def detect_figures_on_page(page: fitz.Page) -> list[dict]:
    """Detect potential figures on a page.
    
    Figures are detected by:
    - Image presence with minimal surrounding text
    - Caption patterns ("Figure X", "Fig. X")
    
    Returns:
        List of detected figure regions
    """
    figures = []
    
    try:
        # Check for images
        image_list = page.get_images()
        
        # Get text to check for captions
        text = page.get_text("text")
        
        # Count figure captions
        caption_patterns = [
            r'Figure\s+\d+',
            r'Fig\.\s+\d+',
            r'Fig\s+\d+',
        ]
        
        caption_count = 0
        for pattern in caption_patterns:
            caption_count += len(re.findall(pattern, text, re.IGNORECASE))
        
        # Estimate figures based on images and captions
        estimated = max(len(image_list), caption_count)
        
        for i in range(estimated):
            figures.append({"index": i, "confidence": 0.7})
    
    except Exception:
        pass
    
    return figures


def detect_column_bleed(page: fitz.Page) -> float:
    """Detect if text bleeds across columns.
    
    Returns:
        Score from 0-1 indicating likelihood of column bleed issues
    """
    try:
        blocks = page.get_text("blocks")
        if not blocks:
            return 0.0
        
        # Get page width
        page_rect = page.rect
        page_width = page_rect.width
        
        # Look for text blocks that span too much of the page width
        # which might indicate column bleed
        wide_blocks = 0
        for block in blocks:
            if len(block) >= 4:
                block_width = block[2] - block[0]  # x1 - x0
                width_ratio = block_width / page_width
                if width_ratio > 0.85:  # Spans >85% of page
                    wide_blocks += 1
        
        if not blocks:
            return 0.0
        
        return min(1.0, wide_blocks / len(blocks))
    
    except Exception:
        return 0.0


def detect_headers_footers(page: fitz.Page) -> float:
    """Detect presence of headers and footers.
    
    Returns:
        Score from 0-1 indicating likelihood of heavy headers/footers
    """
    try:
        page_rect = page.rect
        page_height = page_rect.height
        
        # Define header/footer regions (top/bottom 10%)
        header_zone = page_height * 0.1
        footer_zone = page_height * 0.9
        
        blocks = page.get_text("blocks")
        if not blocks:
            return 0.0
        
        header_footer_blocks = 0
        for block in blocks:
            if len(block) >= 5:
                y_center = (block[1] + block[3]) / 2
                # Check if block is in header or footer zone
                if y_center < header_zone or y_center > footer_zone:
                    # Short text is likely header/footer
                    text = block[4] if len(block) > 4 else ""
                    if len(text.strip()) < 100:
                        header_footer_blocks += 1
        
        if not blocks:
            return 0.0
        
        return min(1.0, header_footer_blocks / len(blocks))
    
    except Exception:
        return 0.0


def calculate_text_coverage(
    doc: fitz.Document, 
    sample_pages: list[int]
) -> float:
    """Calculate text coverage score across sample pages.
    
    Args:
        doc: Open PyMuPDF document
        sample_pages: List of page indices to check
        
    Returns:
        Coverage score from 0-1
    """
    if not sample_pages:
        return 0.0
    
    total_coverage = 0.0
    analyzer = TextCoverageAnalyzer()
    
    for page_idx in sample_pages:
        try:
            page = doc.load_page(page_idx)
            text = page.get_text("text")
            coverage = analyzer.calculate_coverage(text)
            total_coverage += coverage
        except Exception:
            continue
    
    return total_coverage / len(sample_pages) if sample_pages else 0.0


def determine_strategy(
    has_embedded_text: bool,
    text_coverage: float,
    table_count: int,
    warning_flags: list[str],
    ocr_available: bool = True,
) -> ExtractionStrategy:
    """Determine the best extraction strategy based on analysis.

    For PDFs with embedded text (digital born-digital documents), OCR is only
    triggered when coverage falls below EMBEDDED_TEXT_OCR_FLOOR (0.30) —
    indicating severely corrupted or heavily-encoded content.  The old
    MIN_TEXT_COVERAGE (0.70) threshold applies only to documents without any
    detected embedded text (scanned images).

    This distinction is critical: SQL textbooks and other technical PDFs
    frequently contain code blocks, tables, and figures that push the
    readable-character heuristic into the 0.30–0.70 range even though the
    embedded text itself is perfectly clean and extractable directly.

    Args:
        has_embedded_text: Whether PDF has embedded text
        text_coverage: Text coverage score from the readable-char heuristic
        table_count: Estimated table count
        warning_flags: List of warning flags
        ocr_available: Whether OCR tools are available

    Returns:
        Recommended extraction strategy
    """
    # No embedded text at all → must use OCR (scanned / image-only PDF)
    if not has_embedded_text:
        return "ocrmypdf" if ocr_available else "marker"

    # Embedded text exists but coverage is extremely low → content is likely
    # corrupted or character-encoded in an unreadable way.
    if text_coverage < _EMBEDDED_TEXT_OCR_FLOOR:
        return "ocrmypdf" if ocr_available else "marker"

    # Complex multi-column layout that may produce garbled extraction
    if table_count > 10 and "2-column bleed detected" in warning_flags:
        return "marker"

    # Born-digital PDF with usable embedded text — use direct extraction
    return "direct"


def run_preflight(
    pdf_path: Path,
    ocr_available: bool = True,
) -> PreflightReport:
    """Run comprehensive preflight analysis on a PDF.
    
    This function samples pages from the PDF, analyzes text quality,
    detects structural elements, and recommends an extraction strategy.
    
    Args:
        pdf_path: Path to the PDF file
        ocr_available: Whether OCR tools are installed
        
    Returns:
        PreflightReport with analysis results
        
    Raises:
        FileNotFoundError: If PDF doesn't exist
        RuntimeError: If PDF cannot be opened
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        raise RuntimeError(f"Cannot open PDF: {e}") from e
    
    try:
        page_count = doc.page_count
        
        # Select sample pages
        sample_pages = select_sample_pages(page_count)
        
        # Detect embedded text
        has_embedded_text = detect_embedded_text(doc, sample_pages)
        
        # Calculate text coverage
        text_coverage = calculate_text_coverage(doc, sample_pages)
        
        # Estimate structure complexity
        table_count, figure_count, warning_flags = estimate_structure_complexity(
            doc, sample_pages
        )
        
        # Calculate average text density
        total_text = 0
        for page_idx in sample_pages:
            try:
                page = doc.load_page(page_idx)
                text = page.get_text("text")
                total_text += len(text)
            except Exception:
                continue
        avg_density = total_text / len(sample_pages) if sample_pages else 0
        
        # OCR is needed when there is no embedded text at all, OR when embedded
        # text exists but the coverage score is below the per-embedded-text
        # floor (indicating corrupted content rather than a digital PDF with
        # code / tables scoring in the 0.30–0.70 range).
        ocr_needed = not has_embedded_text or text_coverage < _EMBEDDED_TEXT_OCR_FLOOR
        
        # Determine strategy
        strategy = determine_strategy(
            has_embedded_text=has_embedded_text,
            text_coverage=text_coverage,
            table_count=table_count,
            warning_flags=warning_flags,
            ocr_available=ocr_available,
        )
        
        return PreflightReport(
            has_embedded_text=has_embedded_text,
            ocr_needed=ocr_needed,
            estimated_table_count=table_count,
            estimated_figure_count=figure_count,
            warning_flags=warning_flags,
            text_coverage_score=text_coverage,
            recommended_strategy=strategy,
            page_count=page_count,
            sample_pages_analyzed=[p + 1 for p in sample_pages],  # Convert to 1-based
            average_page_text_density=avg_density,
        )
    
    finally:
        doc.close()
