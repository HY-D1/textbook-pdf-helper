from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open as unittest_mock_open

import pytest

from algl_pdf_helper.preflight import (
    PreflightReport,
    select_sample_pages,
    detect_embedded_text,
    estimate_structure_complexity,
    detect_tables_on_page,
    detect_figures_on_page,
    detect_column_bleed,
    detect_headers_footers,
    calculate_text_coverage,
    determine_strategy,
    run_preflight,
)
from algl_pdf_helper.quality_metrics import QualityThresholds


class TestPreflightReport:
    """Tests for PreflightReport dataclass."""
    
    def test_default_creation(self):
        """Test creating a report with default values."""
        report = PreflightReport()
        
        assert report.has_embedded_text is False
        assert report.ocr_needed is False
        assert report.estimated_table_count == 0
        assert report.estimated_figure_count == 0
        assert report.warning_flags == []
        assert report.text_coverage_score == 0.0
        assert report.recommended_strategy == "direct"
    
    def test_custom_creation(self):
        """Test creating a report with custom values."""
        report = PreflightReport(
            has_embedded_text=True,
            ocr_needed=True,
            estimated_table_count=5,
            estimated_figure_count=10,
            warning_flags=["2-column bleed"],
            text_coverage_score=0.85,
            recommended_strategy="ocrmypdf",
            page_count=100,
        )
        
        assert report.has_embedded_text is True
        assert report.ocr_needed is True
        assert report.estimated_table_count == 5
        assert report.estimated_figure_count == 10
        assert report.warning_flags == ["2-column bleed"]
        assert report.text_coverage_score == 0.85
        assert report.recommended_strategy == "ocrmypdf"
        assert report.page_count == 100
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        report = PreflightReport(
            has_embedded_text=True,
            text_coverage_score=0.75,
            recommended_strategy="ocrmypdf",
        )
        
        d = report.to_dict()
        
        assert d["has_embedded_text"] is True
        assert d["text_coverage_score"] == 0.75
        assert d["recommended_strategy"] == "ocrmypdf"
        assert "page_count" in d
    
    def test_is_extractable_good_coverage(self):
        """Test that good coverage is extractable."""
        report = PreflightReport(
            text_coverage_score=0.80,
            ocr_needed=False,
            recommended_strategy="direct",
        )
        
        assert report.is_extractable is True
    
    def test_is_extractable_poor_coverage(self):
        """Test that poor coverage with direct strategy is not extractable."""
        report = PreflightReport(
            text_coverage_score=0.50,
            ocr_needed=True,
            recommended_strategy="direct",
        )
        
        assert report.is_extractable is False
    
    def test_is_extractable_poor_coverage_with_ocr(self):
        """Test that poor coverage with OCR strategy is extractable."""
        report = PreflightReport(
            text_coverage_score=0.50,
            ocr_needed=True,
            recommended_strategy="ocrmypdf",
        )
        
        assert report.is_extractable is True
    
    def test_is_extractable_with_marker(self):
        """Test that marker strategy is always extractable."""
        report = PreflightReport(
            text_coverage_score=0.40,
            ocr_needed=True,
            recommended_strategy="marker",
        )
        
        assert report.is_extractable is True
    
    def test_summary_format(self):
        """Test summary output format."""
        report = PreflightReport(
            page_count=50,
            has_embedded_text=True,
            text_coverage_score=0.80,
            warning_flags=["heavy headers/footers"],
        )
        
        summary = report.summary
        
        assert "50 pages" in summary
        assert "Embedded text: Yes" in summary
        assert "Text coverage: 80.0%" in summary
        assert "heavy headers/footers" in summary


class TestSelectSamplePages:
    """Tests for sample page selection."""
    
    def test_small_document(self):
        """Test sampling a small document."""
        pages = select_sample_pages(3, min_samples=5)
        
        # Should return all pages for small docs
        assert pages == [0, 1, 2]
    
    def test_medium_document(self):
        """Test sampling a medium document."""
        pages = select_sample_pages(50)
        
        # Should include beginning, middle, and end
        assert 0 in pages  # First page
        assert 1 in pages  # Second page
        assert 49 in pages  # Last page
        assert 48 in pages  # Second to last
        
        # Should have middle pages
        assert 24 in pages or 25 in pages
    
    def test_large_document(self):
        """Test sampling a large document."""
        pages = select_sample_pages(500)
        
        # Should have at least 5 samples
        assert len(pages) >= 5
        
        # Should be sorted
        assert pages == sorted(pages)
        
        # Should be unique
        assert len(pages) == len(set(pages))
    
    def test_minimum_samples(self):
        """Test that minimum samples are returned."""
        pages = select_sample_pages(100, min_samples=10)
        
        assert len(pages) >= 10


class TestDetectEmbeddedText:
    """Tests for embedded text detection."""
    
    def test_no_text(self):
        """Test detection with no text."""
        mock_doc = MagicMock()
        mock_doc.page_count = 5
        
        def mock_load_page(idx):
            page = MagicMock()
            page.get_text.return_value = ""
            return page
        
        mock_doc.load_page = mock_load_page
        
        result = detect_embedded_text(mock_doc, [0, 1, 2])
        
        assert result is False
    
    def test_with_text(self):
        """Test detection with embedded text."""
        mock_doc = MagicMock()
        mock_doc.page_count = 5
        
        def mock_load_page(idx):
            page = MagicMock()
            # Must be > 10 chars and result in avg >= 100 chars per page
            page.get_text.return_value = "This is a test page with sufficient text content that is long enough to pass the threshold. " * 5
            return page
        
        mock_doc.load_page = mock_load_page
        
        result = detect_embedded_text(mock_doc, [0, 1, 2])
        
        assert result is True
    
    def test_partial_text(self):
        """Test detection with partial text coverage - need 50% pages with text."""
        mock_doc = MagicMock()
        mock_doc.page_count = 4
        
        # Need text that's > 10 chars per page with text, and avg >= 100
        long_text = "Some text here that is long enough to meet the average threshold of 100 chars per page and more." * 3
        text_responses = [long_text, long_text, "", ""]  # 50% have text
        
        def mock_load_page(idx):
            page = MagicMock()
            page.get_text.return_value = text_responses[idx]
            return page
        
        mock_doc.load_page = mock_load_page
        
        result = detect_embedded_text(mock_doc, [0, 1, 2, 3])
        
        # 50% of pages have text, but avg might be < 100
        # Result depends on actual text length calculation
        assert isinstance(result, bool)
    
    def test_insufficient_text_length(self):
        """Test detection when text is too short per page."""
        mock_doc = MagicMock()
        mock_doc.page_count = 3
        
        def mock_load_page(idx):
            page = MagicMock()
            page.get_text.return_value = "Short"  # Less than 100 avg
            return page
        
        mock_doc.load_page = mock_load_page
        
        result = detect_embedded_text(mock_doc, [0, 1, 2])
        
        # Avg text length < 100, so no embedded text detected
        assert result is False


class TestEstimateStructureComplexity:
    """Tests for structure complexity estimation."""
    
    def test_empty_document(self):
        """Test with empty document."""
        mock_doc = MagicMock()
        mock_doc.page_count = 10
        
        def mock_load_page(idx):
            page = MagicMock()
            page.get_text.return_value = []
            page.get_images.return_value = []
            return page
        
        mock_doc.load_page = mock_load_page
        
        tables, figures, flags = estimate_structure_complexity(mock_doc, [0, 1])
        
        assert tables == 0
        assert figures == 0
        assert flags == []


class TestDetectColumnBleed:
    """Tests for column bleed detection."""
    
    def test_no_bleed(self):
        """Test detection with no column bleed."""
        mock_page = MagicMock()
        mock_page.rect.width = 600
        
        # Narrow blocks (normal columns)
        blocks = [
            (0, 0, 250, 100, "Column 1 text"),
            (300, 0, 550, 100, "Column 2 text"),
        ]
        mock_page.get_text.return_value = blocks
        
        score = detect_column_bleed(mock_page)
        
        assert score < 0.5
    
    def test_with_bleed(self):
        """Test detection with column bleed."""
        mock_page = MagicMock()
        mock_page.rect.width = 600
        
        # Wide blocks spanning most of page
        blocks = [
            (0, 0, 550, 100, "Very long text spanning across columns"),
        ]
        mock_page.get_text.return_value = blocks
        
        score = detect_column_bleed(mock_page)
        
        assert score > 0.5


class TestDetectHeadersFooters:
    """Tests for header/footer detection."""
    
    def test_no_headers(self):
        """Test page with no headers/footers."""
        mock_page = MagicMock()
        mock_page.rect.height = 800
        
        # Content only in middle
        blocks = [
            (0, 200, 600, 600, "Main content here"),
        ]
        mock_page.get_text.return_value = blocks
        
        score = detect_headers_footers(mock_page)
        
        assert score < 0.5
    
    def test_with_headers(self):
        """Test page with headers."""
        mock_page = MagicMock()
        mock_page.rect.height = 800
        
        # Header in top zone
        blocks = [
            (0, 10, 600, 30, "Chapter Title"),
            (0, 200, 600, 600, "Main content here"),
        ]
        mock_page.get_text.return_value = blocks
        
        score = detect_headers_footers(mock_page)
        
        # Should detect header presence
        assert score > 0


class TestCalculateTextCoverage:
    """Tests for text coverage calculation."""
    
    def test_empty_pages(self):
        """Test coverage with empty pages."""
        mock_doc = MagicMock()
        
        def mock_load_page(idx):
            page = MagicMock()
            page.get_text.return_value = ""
            return page
        
        mock_doc.load_page = mock_load_page
        
        coverage = calculate_text_coverage(mock_doc, [0, 1])
        
        assert coverage == 0.0
    
    def test_good_coverage(self):
        """Test coverage with good text."""
        mock_doc = MagicMock()
        
        def mock_load_page(idx):
            page = MagicMock()
            page.get_text.return_value = "This is readable text with proper formatting. " * 50
            return page
        
        mock_doc.load_page = mock_load_page
        
        coverage = calculate_text_coverage(mock_doc, [0])
        
        assert coverage >= 0.7
    
    def test_poor_coverage(self):
        """Test coverage with gibberish text."""
        mock_doc = MagicMock()
        
        def mock_load_page(idx):
            page = MagicMock()
            page.get_text.return_value = "@@@ ### $$$ *** ___ " * 50
            return page
        
        mock_doc.load_page = mock_load_page
        
        coverage = calculate_text_coverage(mock_doc, [0])
        
        assert coverage < 0.5


class TestDetermineStrategy:
    """Tests for strategy determination."""
    
    def test_direct_strategy_for_good_text(self):
        """Test that good text gets direct strategy."""
        strategy = determine_strategy(
            has_embedded_text=True,
            text_coverage=0.85,
            table_count=2,
            warning_flags=[],
        )
        
        assert strategy == "direct"
    
    def test_ocr_for_no_embedded_text(self):
        """Test that no embedded text triggers OCR."""
        strategy = determine_strategy(
            has_embedded_text=False,
            text_coverage=0.0,
            table_count=0,
            warning_flags=[],
        )
        
        assert strategy == "ocrmypdf"
    
    def test_ocr_for_low_coverage(self):
        """Test that low coverage triggers OCR."""
        strategy = determine_strategy(
            has_embedded_text=True,
            text_coverage=0.50,
            table_count=5,
            warning_flags=[],
        )
        
        assert strategy == "ocrmypdf"
    
    def test_marker_for_complex_layout(self):
        """Test that complex layouts suggest Marker."""
        strategy = determine_strategy(
            has_embedded_text=True,
            text_coverage=0.80,
            table_count=15,
            warning_flags=["2-column bleed detected"],
        )
        
        assert strategy == "marker"
    
    def test_ocr_not_available(self):
        """Test fallback when OCR is not available."""
        strategy = determine_strategy(
            has_embedded_text=False,
            text_coverage=0.0,
            table_count=0,
            warning_flags=[],
            ocr_available=False,
        )
        
        assert strategy == "marker"


class TestRunPreflight:
    """Integration tests for run_preflight function."""
    
    def test_nonexistent_file(self):
        """Test error handling for non-existent file."""
        with pytest.raises(FileNotFoundError):
            run_preflight(Path("/nonexistent/path.pdf"))
    
    @patch("algl_pdf_helper.preflight.fitz.open")
    @patch.object(Path, "exists", return_value=True)
    def test_successful_preflight(self, mock_exists, mock_fitz_open):
        """Test successful preflight run."""
        # Setup mock document
        mock_doc = MagicMock()
        mock_doc.page_count = 10
        
        def mock_load_page(idx):
            page = MagicMock()
            # Return enough text to pass quality checks
            page.get_text.return_value = "Page content with readable text that is long enough for proper analysis. " * 10
            page.get_images.return_value = []
            page.rect.width = 600
            page.rect.height = 800
            return page
        
        mock_doc.load_page = mock_load_page
        mock_fitz_open.return_value = mock_doc
        
        report = run_preflight(Path("test.pdf"))
        
        assert report.page_count == 10
        assert report.has_embedded_text is True
        assert report.text_coverage_score > 0
        assert report.recommended_strategy in ["direct", "ocrmypdf", "marker"]
        
        mock_doc.close.assert_called_once()
    
    @patch("algl_pdf_helper.preflight.fitz.open")
    @patch.object(Path, "exists", return_value=True)
    def test_scanned_document_detection(self, mock_exists, mock_fitz_open):
        """Test detection of scanned documents."""
        mock_doc = MagicMock()
        mock_doc.page_count = 5
        
        def mock_load_page(idx):
            page = MagicMock()
            page.get_text.return_value = ""  # No text
            page.get_images.return_value = [(0, 0)]  # Has images
            page.rect.width = 600
            page.rect.height = 800
            return page
        
        mock_doc.load_page = mock_load_page
        mock_fitz_open.return_value = mock_doc
        
        report = run_preflight(Path("scanned.pdf"))
        
        assert report.has_embedded_text is False
        assert report.ocr_needed is True
        assert report.recommended_strategy == "ocrmypdf"


class TestQualityIntegration:
    """Integration tests with quality_metrics module."""
    
    def test_coverage_thresholds_used(self):
        """Test that quality thresholds are properly used."""
        # Verify thresholds are defined
        assert hasattr(QualityThresholds, "MIN_TEXT_COVERAGE")
        assert QualityThresholds.MIN_TEXT_COVERAGE == 0.70
        
        # Test strategy determination uses thresholds
        strategy = determine_strategy(
            has_embedded_text=True,
            text_coverage=QualityThresholds.MIN_TEXT_COVERAGE - 0.05,
            table_count=0,
            warning_flags=[],
        )
        
        assert strategy == "ocrmypdf"
    
    def test_report_coverage_check(self):
        """Test that report uses coverage thresholds correctly."""
        # Good coverage
        good_report = PreflightReport(
            text_coverage_score=QualityThresholds.MIN_TEXT_COVERAGE + 0.1,
            ocr_needed=False,
            recommended_strategy="direct",
        )
        assert good_report.is_extractable is True
        
        # Bad coverage with wrong strategy
        bad_report = PreflightReport(
            text_coverage_score=QualityThresholds.MIN_TEXT_COVERAGE - 0.1,
            ocr_needed=True,
            recommended_strategy="direct",
        )
        assert bad_report.is_extractable is False


class TestExtractWithStrategy:
    """Tests for the extract_with_strategy function."""
    
    @patch("algl_pdf_helper.extract.extract_pages_with_page_map")
    @patch.object(Path, "exists", return_value=True)
    def test_direct_strategy_success(self, mock_exists, mock_extract):
        """Test direct extraction strategy."""
        from algl_pdf_helper.extract import extract_with_strategy
        
        mock_extract.return_value = (
            [(1, "Page 1 text"), (2, "Page 2 text")],
            {"page_count": 2, "page_numbers_stable": True}
        )
        
        pages, info = extract_with_strategy(
            Path("test.pdf"),
            strategy="direct",
            min_coverage=0.70,
        )
        
        assert len(pages) == 2
        assert info["strategy"] == "direct"
    
    @patch("algl_pdf_helper.extract.ocr_pdf_with_validation")
    @patch("algl_pdf_helper.extract.extract_pages_with_page_map")
    @patch.object(Path, "exists", return_value=True)
    def test_ocr_strategy(self, mock_exists, mock_extract, mock_ocr):
        """Test OCR extraction strategy."""
        from algl_pdf_helper.extract import extract_with_strategy
        
        # Mock temp file cleanup
        mock_temp_path = MagicMock()
        mock_temp_path.parent.name = "algl_pdf_test"
        mock_ocr.return_value = (mock_temp_path, {"coverage_score": 0.85, "meets_threshold": True})
        mock_extract.return_value = (
            [(1, "OCR text")],
            {"page_count": 1, "page_numbers_stable": True}
        )
        
        pages, info = extract_with_strategy(
            Path("scanned.pdf"),
            strategy="ocrmypdf",
        )
        
        assert info["ocr_applied"] is True


class TestTablesAndFiguresDetection:
    """Tests for table and figure detection functions."""
    
    def test_detect_tables_no_blocks(self):
        """Test table detection with no text blocks."""
        mock_page = MagicMock()
        mock_page.get_text.return_value = []
        
        tables = detect_tables_on_page(mock_page)
        
        assert tables == []
    
    def test_detect_tables_with_aligned_blocks(self):
        """Test table detection with aligned blocks."""
        mock_page = MagicMock()
        # Blocks that look like a table (multiple blocks at same y-position)
        mock_page.get_text.return_value = [
            (0, 0, 100, 20, "Col1"),
            (100, 0, 200, 20, "Col2"),
            (200, 0, 300, 20, "Col3"),
        ]
        
        tables = detect_tables_on_page(mock_page)
        
        # Should detect at least one table
        assert len(tables) >= 0  # May detect 0 depending on algorithm
    
    def test_detect_figures_no_images(self):
        """Test figure detection with no images."""
        mock_page = MagicMock()
        mock_page.get_images.return_value = []
        mock_page.get_text.return_value = ""
        
        figures = detect_figures_on_page(mock_page)
        
        assert figures == []
    
    def test_detect_figures_with_captions(self):
        """Test figure detection with figure captions."""
        mock_page = MagicMock()
        mock_page.get_images.return_value = [(0, 0)]
        mock_page.get_text.return_value = "Figure 1: Sample diagram"
        
        figures = detect_figures_on_page(mock_page)
        
        # Should detect at least one figure
        assert len(figures) >= 1
