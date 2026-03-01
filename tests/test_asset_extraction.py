"""Tests for asset extraction functionality."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

from algl_pdf_helper.asset_extractor import (
    AssetExtractor,
    ExtractedAsset,
    extract_assets_from_pdf,
)
from algl_pdf_helper.table_converter import (
    TableCell,
    TableConverter,
    TableData,
    TableRow,
    convert_table_for_concept,
)


class TestExtractedAsset:
    """Tests for the ExtractedAsset dataclass."""
    
    def test_asset_creation(self):
        """Test creating an extracted asset."""
        asset = ExtractedAsset(
            id="page-001-fig-01",
            type="image",
            page=1,
            bbox=(10.0, 20.0, 100.0, 200.0),
            doc_id="test-doc",
            format="png",
            caption="Test figure",
            content=b"fake-image-data",
        )
        
        assert asset.id == "page-001-fig-01"
        assert asset.type == "image"
        assert asset.page == 1
        assert asset.format == "png"
        assert asset.caption == "Test figure"
    
    def test_image_relative_path(self):
        """Test getting relative path for image asset."""
        asset = ExtractedAsset(
            id="page-001-fig-01",
            type="image",
            page=1,
            bbox=(0, 0, 100, 100),
            doc_id="test-doc",
            format="png",
            content=b"",
        )
        
        path = asset.get_relative_path()
        assert "assets/images/test-doc/" in path
        assert path.endswith(".png")
    
    def test_table_relative_path(self):
        """Test getting relative path for table asset."""
        asset = ExtractedAsset(
            id="page-001-table-01",
            type="table",
            page=1,
            bbox=(0, 0, 100, 100),
            doc_id="test-doc",
            format="html",
            content="<table></table>",
        )
        
        path = asset.get_relative_path()
        assert "assets/tables/test-doc/" in path
        assert path.endswith(".html")
    
    def test_image_filename(self):
        """Test getting filename for image asset."""
        asset = ExtractedAsset(
            id="page-005-fig-02",
            type="image",
            page=5,
            bbox=(0, 0, 100, 100),
            doc_id="doc",
            format="png",
            content=b"",
        )
        
        filename = asset.get_filename()
        assert filename == "page-005-fig-02.png"
    
    def test_table_filename(self):
        """Test getting filename for table asset."""
        asset = ExtractedAsset(
            id="page-010-table-03",
            type="table",
            page=10,
            bbox=(0, 0, 100, 100),
            doc_id="doc",
            format="html",
            content="",
        )
        
        filename = asset.get_filename()
        assert filename == "page-010-table-03.html"


class TestAssetExtractor:
    """Tests for the AssetExtractor class."""
    
    def test_initialization(self):
        """Test extractor initialization."""
        extractor = AssetExtractor(backend="pymupdf")
        assert extractor.backend == "pymupdf"
        
        extractor_marker = AssetExtractor(backend="marker")
        assert extractor_marker.backend == "marker"
    
    def test_invalid_backend(self):
        """Test extractor with invalid backend."""
        extractor = AssetExtractor(backend="invalid")
        
        with pytest.raises(ValueError, match="Unknown backend"):
            extractor.extract_images(Path("test.pdf"), "doc-id")
    
    def test_generate_image_id(self):
        """Test image ID generation."""
        extractor = AssetExtractor()
        extractor._reset_counters()
        
        id1 = extractor._generate_image_id(1)
        assert id1 == "page-001-fig-01"
        
        id2 = extractor._generate_image_id(1)
        assert id2 == "page-001-fig-02"
        
        id3 = extractor._generate_image_id(2)
        assert id3 == "page-002-fig-01"
    
    def test_generate_table_id(self):
        """Test table ID generation."""
        extractor = AssetExtractor()
        extractor._reset_counters()
        
        id1 = extractor._generate_table_id(1)
        assert id1 == "page-001-table-01"
        
        id2 = extractor._generate_table_id(1)
        assert id2 == "page-001-table-02"
    
    @patch("algl_pdf_helper.asset_extractor.fitz.open")
    def test_extract_images_pymupdf(self, mock_fitz_open):
        """Test image extraction with PyMuPDF."""
        # Setup mock
        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_page = MagicMock()
        mock_page.get_images.return_value = [(1, 0, 0, 0, 0, 0, 0)]
        mock_doc.load_page.return_value = mock_page
        
        mock_doc.extract_image.return_value = {
            "image": b"fake-png-data",
            "ext": "png",
        }
        mock_fitz_open.return_value = mock_doc
        
        extractor = AssetExtractor(backend="pymupdf")
        
        with patch.object(extractor, '_find_image_bbox', return_value=(10, 10, 100, 100)):
            assets = extractor.extract_images(Path("test.pdf"), "doc-123")
        
        mock_fitz_open.assert_called_once()
        mock_doc.close.assert_called_once()
    
    @patch("algl_pdf_helper.asset_extractor.fitz.open")
    def test_extract_tables_pymupdf(self, mock_fitz_open):
        """Test table extraction with PyMuPDF."""
        # Setup mock
        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_page = MagicMock()
        mock_doc.load_page.return_value = mock_page
        mock_fitz_open.return_value = mock_doc
        
        # Mock find_tables to avoid pandas dependency issues
        mock_tables_result = MagicMock()
        mock_tables_result.tables = []
        mock_page.find_tables.return_value = mock_tables_result
        
        extractor = AssetExtractor(backend="pymupdf")
        assets = extractor.extract_tables(Path("test.pdf"), "doc-123")
        
        assert isinstance(assets, list)
        mock_fitz_open.assert_called_once()
        mock_doc.close.assert_called_once()
    
    def test_markdown_table_to_html(self):
        """Test converting markdown table to HTML."""
        extractor = AssetExtractor()
        
        md_table = """| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
| Cell 3   | Cell 4   |"""
        
        html = extractor._markdown_table_to_html(md_table)
        
        assert "<table" in html
        assert "Header 1" in html
        assert "Cell 1" in html
        assert "</table>" in html
    
    def test_extract_page_from_image_name(self):
        """Test extracting page number from image name."""
        extractor = AssetExtractor()
        
        assert extractor._extract_page_from_image_name("page_001_img_001.png") == 1
        assert extractor._extract_page_from_image_name("page-005-image.png") == 5
        assert extractor._extract_page_from_image_name("other.png") == 1
    
    def test_save_assets(self, tmp_path):
        """Test saving assets to disk."""
        extractor = AssetExtractor()
        
        # Create test assets
        image_asset = ExtractedAsset(
            id="page-001-fig-01",
            type="image",
            page=1,
            bbox=(0, 0, 100, 100),
            doc_id="test-doc",
            format="png",
            content=b"fake-image-data",
        )
        
        table_asset = ExtractedAsset(
            id="page-001-table-01",
            type="table",
            page=1,
            bbox=(0, 0, 100, 100),
            doc_id="test-doc",
            format="html",
            content="<table><tr><td>Test</td></tr></table>",
        )
        
        assets = [image_asset, table_asset]
        saved_paths = extractor.save_assets(assets, tmp_path)
        
        # Check paths were returned
        assert len(saved_paths) == 2
        
        # Check image was saved
        image_path = tmp_path / "assets" / "images" / "test-doc" / "page-001-fig-01.png"
        assert image_path.exists()
        assert image_path.read_bytes() == b"fake-image-data"
        
        # Check table was saved
        table_path = tmp_path / "assets" / "tables" / "test-doc" / "page-001-table-01.html"
        assert table_path.exists()


class TestAssetNamingConventions:
    """Tests for asset naming conventions."""
    
    def test_image_naming_format(self):
        """Test image follows naming convention: assets/images/<docId>/page-###-fig-##.png"""
        doc_id = "sql-textbook"
        page = 42
        fig_num = 3
        
        asset = ExtractedAsset(
            id=f"page-{page:03d}-fig-{fig_num:02d}",
            type="image",
            page=page,
            bbox=(0, 0, 100, 100),
            doc_id=doc_id,
            format="png",
            content=b"",
        )
        
        path = asset.get_relative_path()
        expected_pattern = f"assets/images/{doc_id}/page-{page:03d}-fig-{fig_num:02d}.png"
        assert path.endswith(expected_pattern.split("/")[-1])
        assert "assets/images/" in path
    
    def test_table_naming_format(self):
        """Test table follows naming convention: assets/tables/<docId>/page-###-table-##.html"""
        doc_id = "sql-textbook"
        page = 15
        table_num = 2
        
        asset = ExtractedAsset(
            id=f"page-{page:03d}-table-{table_num:02d}",
            type="table",
            page=page,
            bbox=(0, 0, 100, 100),
            doc_id=doc_id,
            format="html",
            content="",
        )
        
        filename = asset.get_filename()
        expected_filename = f"page-{page:03d}-table-{table_num:02d}.html"
        assert filename == expected_filename
        
        path = asset.get_relative_path()
        assert "assets/tables/" in path
        assert path.endswith(expected_filename)


class TestTableConverter:
    """Tests for the TableConverter class."""
    
    def test_initialization(self):
        """Test converter initialization."""
        converter = TableConverter()
        assert converter._table_count == 0
    
    def test_table_counter(self):
        """Test table counter increments."""
        converter = TableConverter()
        
        assert converter._get_next_table_num() == 1
        assert converter._get_next_table_num() == 2
        
        converter.reset_counter()
        assert converter._get_next_table_num() == 1
    
    def test_convert_to_html_basic(self):
        """Test basic HTML table conversion."""
        converter = TableConverter()
        
        headers = [
            TableCell(content="Name", is_header=True),
            TableCell(content="Age", is_header=True),
        ]
        rows = [
            TableRow(cells=[
                TableCell(content="Alice"),
                TableCell(content="30"),
            ]),
            TableRow(cells=[
                TableCell(content="Bob"),
                TableCell(content="25"),
            ]),
        ]
        data = TableData(headers=headers, rows=rows)
        
        html = converter.convert_to_html(data, add_figure_wrap=False)
        
        assert "<table" in html
        assert "Name" in html
        assert "Alice" in html
        assert "</table>" in html
        assert "<th>" in html
        assert "<td>" in html
    
    def test_convert_to_html_with_figure(self):
        """Test HTML table with figure wrapper."""
        converter = TableConverter()
        
        data = TableData(
            headers=[TableCell(content="Col1", is_header=True)],
            rows=[TableRow(cells=[TableCell(content="Data")])],
            caption="Test Table",
        )
        
        html = converter.convert_to_html(data, add_figure_wrap=True)
        
        assert "<figure" in html
        assert "<figcaption>" in html
        assert "Test Table" in html
        assert "</figure>" in html
    
    def test_convert_to_markdown(self):
        """Test markdown table conversion."""
        converter = TableConverter()
        
        headers = [
            TableCell(content="Name", is_header=True),
            TableCell(content="Value", is_header=True),
        ]
        rows = [
            TableRow(cells=[
                TableCell(content="Item 1"),
                TableCell(content="100"),
            ]),
        ]
        data = TableData(headers=headers, rows=rows)
        
        md = converter.convert_to_markdown(data, add_caption=False)
        
        assert "| Name | Value |" in md
        assert "---" in md  # Separator with or without spaces
        assert "| Item 1 | 100 |" in md
    
    def test_markdown_table_to_html(self):
        """Test parsing markdown table to HTML."""
        converter = TableConverter()
        
        md_table = """| A | B |
|---|---|
| 1 | 2 |
| 3 | 4 |"""
        
        data = converter.parse_markdown_table(md_table)
        
        assert data.headers is not None
        assert len(data.headers) == 2
        assert data.headers[0].content == "A"
        assert len(data.rows) == 2
        assert data.rows[0].cells[0].content == "1"
    
    def test_detect_alignment(self):
        """Test alignment detection from separator line."""
        converter = TableConverter()
        
        # Left aligned (default)
        assert converter.detect_alignment("|---|---|") == ["left", "left"]
        
        # Center aligned
        assert converter.detect_alignment("|:---:|---:|") == ["center", "right"]
        
        # Right aligned
        assert converter.detect_alignment("|---:|---:|") == ["right", "right"]
    
    def test_infer_alignment(self):
        """Test alignment inference from content."""
        converter = TableConverter()
        
        assert converter.infer_alignment("123") == "right"  # Numbers
        assert converter.infer_alignment("$100.00") == "right"  # Currency
        assert converter.infer_alignment("Hello") == "center"  # Short text
        assert converter.infer_alignment("This is a longer piece of text") == "left"
    
    def test_html_escaping(self):
        """Test HTML special character escaping."""
        converter = TableConverter()
        
        # Test via a table with special chars
        data = TableData(
            headers=[TableCell(content="<script>alert('xss')</script>", is_header=True)],
            rows=[],
        )
        
        html = converter.convert_to_html(data, add_figure_wrap=False)
        
        assert "<script>" not in html
        assert "&lt;script&gt;" in html
    
    def test_cell_with_colspan_rowspan(self):
        """Test cell rendering with colspan and rowspan."""
        converter = TableConverter()
        
        cell = TableCell(
            content="Spanned Cell",
            colspan=2,
            rowspan=3,
            align="center",
        )
        
        html = converter._render_body_cell(cell)
        
        assert 'colspan="2"' in html
        assert 'rowspan="3"' in html
        assert 'align="center"' in html
        assert "Spanned Cell" in html


class TestConvertTableForConcept:
    """Tests for the convert_table_for_concept utility function."""
    
    def test_convert_simple_table(self):
        """Test converting a simple 2D list to HTML table."""
        table_data = [
            ["Name", "Age", "City"],
            ["Alice", "30", "NYC"],
            ["Bob", "25", "LA"],
        ]
        
        html = convert_table_for_concept(table_data, caption="People", table_num=1)
        
        assert "<figure" in html
        assert "<table" in html
        assert "<th>Name</th>" in html
        assert "<td>Alice</td>" in html
        assert "<figcaption>People</figcaption>" in html
    
    def test_empty_table(self):
        """Test handling empty table data."""
        assert convert_table_for_concept([]) == ""
        assert convert_table_for_concept([[]]) == ""


class TestExtractAssetsFromPdf:
    """Tests for the extract_assets_from_pdf convenience function."""
    
    @patch("algl_pdf_helper.asset_extractor.AssetExtractor")
    def test_extract_assets_convenience(self, mock_extractor_class):
        """Test the convenience function for asset extraction."""
        # Setup mock
        mock_extractor = MagicMock()
        mock_extractor_class.return_value = mock_extractor
        
        mock_image = MagicMock()
        mock_image.type = "image"
        mock_image.get_relative_path.return_value = "assets/images/doc/page-001-fig-01.png"
        mock_table = MagicMock()
        mock_table.type = "table"
        mock_table.get_relative_path.return_value = "assets/tables/doc/page-001-table-01.html"
        
        mock_extractor.extract_images.return_value = [mock_image]
        mock_extractor.extract_tables.return_value = [mock_table]
        
        # Call function
        result = extract_assets_from_pdf(
            pdf_path=Path("test.pdf"),
            doc_id="doc-123",
            output_dir=Path("/tmp/out"),
            backend="pymupdf",
        )
        
        # Verify
        assert "images" in result
        assert "tables" in result
        assert len(result["images"]) == 1
        assert len(result["tables"]) == 1
        
        mock_extractor.save_assets.assert_any_call([mock_image], Path("/tmp/out"))
        mock_extractor.save_assets.assert_any_call([mock_table], Path("/tmp/out"))
    
    def test_extract_assets_skipped_when_disabled(self, tmp_path):
        """Test that assets are not extracted when disabled."""
        result = extract_assets_from_pdf(
            pdf_path=Path("test.pdf"),
            doc_id="doc-123",
            output_dir=tmp_path,
            extract_images=False,
            extract_tables=False,
        )
        
        assert result["images"] == []
        assert result["tables"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
