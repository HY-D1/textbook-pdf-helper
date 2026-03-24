from __future__ import annotations

import re
from dataclasses import dataclass
from typing import NamedTuple


class QualityThresholds:
    """Quality thresholds for text extraction.
    
    These constants define the minimum acceptable quality levels
    for various extraction metrics.
    """
    # Text coverage (ratio of readable text to total content)
    MIN_TEXT_COVERAGE: float = 0.70
    
    # Minimum characters for a page to be considered non-empty
    MIN_PAGE_CHARS: int = 50
    
    # Minimum total characters in document
    MIN_TOTAL_CHARS: int = 500
    
    # Maximum gibberish ratio
    MAX_GIBBERISH_RATIO: float = 0.30
    
    # Minimum readable character ratio
    MIN_READABLE_RATIO: float = 0.70
    
    # Header/footer detection threshold (ratio of pages with same header/footer)
    HEADER_FOOTER_THRESHOLD: float = 0.60
    
    # Column bleed threshold (ratio of page width that indicates potential bleed)
    COLUMN_BLEED_THRESHOLD: float = 0.85

    # OCR floor for PDFs that do have embedded text.
    # Coverage below this value (e.g. heavily corrupted encoding) warrants OCR
    # even when embedded text was detected.  Digital PDFs with SQL code, tables,
    # or figures will often score 0.30–0.70 on the readable-char heuristic but
    # are perfectly extractable with direct extraction – they must NOT be pushed
    # into the OCR path.
    EMBEDDED_TEXT_OCR_FLOOR: float = 0.30


class CoverageResult(NamedTuple):
    """Result of text coverage analysis."""
    coverage_score: float
    readable_chars: int
    total_chars: int
    gibberish_count: int
    meets_threshold: bool


@dataclass
class PageAnalysis:
    """Analysis results for a single page."""
    page_number: int
    text_length: int
    has_embedded_text: bool
    coverage_score: float
    has_column_bleed: bool
    has_headers_footers: bool
    potential_tables: int
    potential_figures: int
    warnings: list[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class TextCoverageAnalyzer:
    """Analyzer for text coverage and quality metrics.
    
    This class provides methods to calculate text coverage, detect
    quality issues, and determine if content meets quality thresholds.
    """
    
    # Readable characters pattern (letters, numbers, spaces, common punctuation)
    READABLE_PATTERN = re.compile(r'[\w\s.,;:!?\-\'"()\[\]{}]')
    
    # Gibberish patterns (common OCR artifacts)
    GIBBERISH_PATTERNS = [
        re.compile(r'[_\-]{3,}'),           # Repeated underscores/dashes
        re.compile(r'[\^\*@#%&]{2,}'),      # Repeated special chars
        re.compile(r'\.{4,}'),              # Too many dots
        re.compile(r'[a-z][A-Z]{2,}[a-z]'), # Odd caps pattern
        re.compile(r'[^\w\s.,;:!?\-\'"()\[\]{}]{3,}'),  # Long sequences of weird chars
        re.compile(r'\b\d{10,}\b'),        # Very long numbers (OCR noise)
        re.compile(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]'),  # Control characters
    ]
    
    def calculate_coverage(self, text: str | None) -> float:
        """Calculate text coverage score.
        
        The coverage score represents the ratio of readable characters
        to total characters, adjusted for gibberish patterns.
        
        Args:
            text: Text to analyze
            
        Returns:
            Coverage score from 0.0 to 1.0
        """
        if not text:
            return 0.0
        
        result = self._analyze_text(text)
        return result.coverage_score
    
    def _analyze_text(self, text: str) -> CoverageResult:
        """Perform detailed text analysis.
        
        Args:
            text: Text to analyze
            
        Returns:
            CoverageResult with detailed metrics
        """
        total_chars = len(text)
        if total_chars == 0:
            return CoverageResult(
                coverage_score=0.0,
                readable_chars=0,
                total_chars=0,
                gibberish_count=0,
                meets_threshold=False,
            )
        
        # Count readable characters
        readable_chars = len(self.READABLE_PATTERN.findall(text))
        readable_ratio = readable_chars / total_chars
        
        # Count gibberish patterns
        gibberish_count = 0
        for pattern in self.GIBBERISH_PATTERNS:
            gibberish_count += len(pattern.findall(text))
        
        gibberish_ratio = gibberish_count / total_chars if total_chars > 0 else 0
        
        # Calculate coverage score
        # Penalize for gibberish patterns
        coverage_score = max(0.0, readable_ratio - (gibberish_ratio * 2))
        
        meets_threshold = (
            coverage_score >= QualityThresholds.MIN_TEXT_COVERAGE and
            total_chars >= QualityThresholds.MIN_PAGE_CHARS
        )
        
        return CoverageResult(
            coverage_score=coverage_score,
            readable_chars=readable_chars,
            total_chars=total_chars,
            gibberish_count=gibberish_count,
            meets_threshold=meets_threshold,
        )
    
    def analyze_pages(self, pages: list[tuple[int, str]]) -> list[PageAnalysis]:
        """Analyze multiple pages.
        
        Args:
            pages: List of (page_number, text) tuples
            
        Returns:
            List of PageAnalysis objects
        """
        results = []
        for page_num, text in pages:
            result = self._analyze_text(text)
            
            analysis = PageAnalysis(
                page_number=page_num,
                text_length=len(text),
                has_embedded_text=result.total_chars > 0,
                coverage_score=result.coverage_score,
                has_column_bleed=False,  # Will be set by detect_column_bleed
                has_headers_footers=False,  # Will be set by detect_headers_footers
                potential_tables=0,
                potential_figures=0,
            )
            
            # Add warnings based on analysis
            if not result.meets_threshold:
                analysis.warnings.append("Low text coverage")
            if result.gibberish_count > 10:
                analysis.warnings.append("OCR artifacts detected")
            
            results.append(analysis)
        
        return results
    
    def get_document_coverage(self, pages: list[tuple[int, str]]) -> dict:
        """Get aggregate coverage metrics for a document.
        
        Args:
            pages: List of (page_number, text) tuples
            
        Returns:
            Dictionary with aggregate metrics
        """
        if not pages:
            return {
                "total_pages": 0,
                "pages_with_text": 0,
                "average_coverage": 0.0,
                "min_coverage": 0.0,
                "max_coverage": 0.0,
                "meets_threshold": False,
                "total_characters": 0,
            }
        
        page_results = self.analyze_pages(pages)
        
        coverages = [p.coverage_score for p in page_results]
        total_chars = sum(p.text_length for p in page_results)
        pages_with_text = sum(1 for p in page_results if p.has_embedded_text)
        
        return {
            "total_pages": len(pages),
            "pages_with_text": pages_with_text,
            "average_coverage": sum(coverages) / len(coverages),
            "min_coverage": min(coverages),
            "max_coverage": max(coverages),
            "meets_threshold": all(p.coverage_score >= QualityThresholds.MIN_TEXT_COVERAGE 
                                   for p in page_results if p.has_embedded_text),
            "total_characters": total_chars,
        }


def calculate_coverage(text: str | None) -> float:
    """Convenience function to calculate text coverage.
    
    Args:
        text: Text to analyze
        
    Returns:
        Coverage score from 0.0 to 1.0
    """
    analyzer = TextCoverageAnalyzer()
    return analyzer.calculate_coverage(text)


def detect_column_bleed(text: str, page_width: int = 100) -> float:
    """Detect column bleed in extracted text.
    
    Column bleed occurs when text from multiple columns is merged
    together, creating long lines that span the full page width.
    
    Args:
        text: Extracted text to analyze
        page_width: Expected character width of page (for normalization)
        
    Returns:
        Bleed score from 0.0 to 1.0 (higher = more bleed)
    """
    if not text:
        return 0.0
    
    lines = text.split('\n')
    if not lines:
        return 0.0
    
    # Calculate line lengths
    line_lengths = [len(line.strip()) for line in lines if line.strip()]
    if not line_lengths:
        return 0.0
    
    avg_length = sum(line_lengths) / len(line_lengths)
    max_length = max(line_lengths)
    
    # If max line is significantly longer than average, may indicate bleed
    if avg_length == 0:
        return 0.0
    
    length_ratio = max_length / avg_length
    
    # Check for very long lines (potential bleed)
    long_lines = sum(1 for length in line_lengths if length > page_width * 0.9)
    long_line_ratio = long_lines / len(line_lengths) if line_lengths else 0
    
    # Combine metrics
    bleed_score = min(1.0, (length_ratio - 1) * 0.3 + long_line_ratio * 0.7)
    
    return max(0.0, bleed_score)


def detect_headers_footers(
    pages: list[tuple[int, str]],
    head_lines: int = 2,
    foot_lines: int = 2,
    min_pages: int = 5,
    ratio: float = None,
) -> dict:
    """Detect repeated headers and footers across pages.
    
    Uses frequency analysis to find lines that appear consistently
    at the top or bottom of multiple pages.
    
    Args:
        pages: List of (page_number, text) tuples
        head_lines: Number of lines to check at top of page
        foot_lines: Number of lines to check at bottom of page
        min_pages: Minimum pages required for detection
        ratio: Threshold ratio for considering a line as header/footer
        
    Returns:
        Dictionary with headers, footers, and confidence scores
    """
    if ratio is None:
        ratio = QualityThresholds.HEADER_FOOTER_THRESHOLD
    
    if len(pages) < min_pages:
        return {
            "has_headers": False,
            "has_footers": False,
            "headers": [],
            "footers": [],
            "confidence": 0.0,
        }
    
    from collections import Counter
    
    header_counter: Counter[str] = Counter()
    footer_counter: Counter[str] = Counter()
    
    for page_num, text in pages:
        lines = [ln.strip() for ln in text.splitlines()]
        if not lines:
            continue
        
        # Count header lines
        for line in lines[:head_lines]:
            if line and len(line) < 100:  # Reasonable header length
                header_counter[line] += 1
        
        # Count footer lines
        for line in lines[-foot_lines:]:
            if line and len(line) < 100:  # Reasonable footer length
                footer_counter[line] += 1
    
    threshold = int(len(pages) * ratio)
    
    # Find repeated headers/footers
    headers = [line for line, count in header_counter.items() if count >= threshold]
    footers = [line for line, count in footer_counter.items() if count >= threshold]
    
    # Calculate confidence
    max_header_count = max(header_counter.values()) if header_counter else 0
    max_footer_count = max(footer_counter.values()) if footer_counter else 0
    
    confidence = max(
        max_header_count / len(pages) if pages else 0,
        max_footer_count / len(pages) if pages else 0,
    )
    
    return {
        "has_headers": len(headers) > 0,
        "has_footers": len(footers) > 0,
        "headers": headers,
        "footers": footers,
        "confidence": confidence,
    }


def validate_text_quality(
    text: str,
    min_coverage: float = None,
    min_chars: int = None,
) -> dict:
    """Validate text quality against thresholds.
    
    Args:
        text: Text to validate
        min_coverage: Minimum required coverage (uses default if None)
        min_chars: Minimum required characters (uses default if None)
        
    Returns:
        Validation result with pass/fail status and details
    """
    if min_coverage is None:
        min_coverage = QualityThresholds.MIN_TEXT_COVERAGE
    if min_chars is None:
        min_chars = QualityThresholds.MIN_PAGE_CHARS
    
    analyzer = TextCoverageAnalyzer()
    result = analyzer._analyze_text(text)
    
    passed = (
        result.coverage_score >= min_coverage and
        result.total_chars >= min_chars
    )
    
    return {
        "passed": passed,
        "coverage_score": result.coverage_score,
        "total_chars": result.total_chars,
        "readable_chars": result.readable_chars,
        "gibberish_count": result.gibberish_count,
        "threshold": {
            "min_coverage": min_coverage,
            "min_chars": min_chars,
        },
        "fail_reasons": [
            reason for reason in [
                "coverage_too_low" if result.coverage_score < min_coverage else None,
                "too_few_chars" if result.total_chars < min_chars else None,
            ] if reason
        ],
    }
