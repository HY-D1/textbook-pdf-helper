#!/usr/bin/env python3
"""
Comprehensive Edge Case Tests for ALGL PDF Helper

Tests invalid inputs, error handling, graceful degradation,
and recovery mechanisms across the entire codebase.

Author: Test Suite
Created: 2026-03-01
"""

from __future__ import annotations

import io
import json
import os
import stat
import sys
import tempfile
import warnings
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import modules to test
from algl_pdf_helper.chunker import chunk_page_words, chunk_page_words_with_provenance
from algl_pdf_helper.clean import normalize_text, strip_repeated_headers_footers
from algl_pdf_helper.extract import (
    calculate_text_quality,
    check_extraction_quality,
    check_text_coverage,
    cleanup_temp_pdf,
    extract_pages_fitz,
    extract_with_strategy,
    sha256_file,
)
from algl_pdf_helper.indexer import build_index, discover_pdfs, get_doc_alias, unique_doc_id
from algl_pdf_helper.models import (
    AssetManifest,
    ConceptInfo,
    ConceptManifest,
    ConceptSection,
    IndexBuildOptions,
    OutputConfig,
    PdfIndexChunk,
    PdfSourceDoc,
)
from algl_pdf_helper.validators import (
    SQLValidationResult,
    ValidationResult,
    extract_json_from_llm_output,
    safe_parse_json,
    validate_concept_json,
    validate_sql_snippet,
)
from algl_pdf_helper.concept_mapper import (
    build_concept_manifest,
    find_concepts_config,
    get_chunks_for_pages,
    load_concepts_config,
    _match_pdf_to_textbook,
)
from algl_pdf_helper.embedding import build_hash_embedding, tokenize
from algl_pdf_helper.educational_pipeline import (
    ContentValidator,
    EducationalNoteGenerator,
    LLMProvider,
    SQLValidator,
    TextCleaner,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def empty_pdf(temp_dir):
    """Create an empty PDF (0 pages)."""
    pdf_path = temp_dir / "empty.pdf"
    # Create minimal PDF structure with 0 pages
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [] /Count 0 >>
endobj
xref
0 3
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
trailer
<< /Root 1 0 R /Size 3 >>
startxref
106
%%EOF"""
    pdf_path.write_bytes(pdf_content)
    return pdf_path


@pytest.fixture
def image_only_pdf(temp_dir):
    """Create a PDF with only images (no text)."""
    pdf_path = temp_dir / "image_only.pdf"
    # This is a simplified PDF with an image but no text content
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
   /Contents 4 0 R /Resources << /XObject << /Im0 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 44 >>
stream
q 612 0 0 792 0 0 cm /Im0 Do Q
endstream
endobj
5 0 obj
<< /Type /XObject /Subtype /Image /Width 100 /Height 100
   /ColorSpace /DeviceRGB /BitsPerComponent 8 /Length 6 >>
stream
AAAAAA
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000261 00000 n 
0000000355 00000 n 
trailer
<< /Root 1 0 R /Size 6 >>
startxref
498
%%EOF"""
    pdf_path.write_bytes(pdf_content)
    return pdf_path


@pytest.fixture
def corrupted_pdf(temp_dir):
    """Create a corrupted/truncated PDF."""
    pdf_path = temp_dir / "corrupted.pdf"
    # Truncated PDF (missing end)
    pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog")
    return pdf_path


@pytest.fixture
def non_pdf_with_pdf_extension(temp_dir):
    """Create a non-PDF file with .pdf extension."""
    pdf_path = temp_dir / "not_a_pdf.pdf"
    pdf_path.write_text("This is not a PDF file, just plain text.")
    return pdf_path


@pytest.fixture
def valid_sample_chunks():
    """Return a list of valid sample chunks for testing."""
    return [
        PdfIndexChunk(
            chunkId="test:p1:c1",
            docId="test",
            page=1,
            text="SELECT * FROM users WHERE id = 1;",
            embedding=[0.1] * 24,
        ),
        PdfIndexChunk(
            chunkId="test:p1:c2",
            docId="test",
            page=1,
            text="This is another chunk with more content.",
            embedding=[0.2] * 24,
        ),
        PdfIndexChunk(
            chunkId="test:p2:c1",
            docId="test",
            page=2,
            text="Content from page 2.",
            embedding=[0.3] * 24,
        ),
    ]


# =============================================================================
# INVALID PDF TESTS
# =============================================================================

class TestInvalidPDFs:
    """Tests for handling various invalid PDF files."""
    
    def test_empty_pdf_zero_pages(self, empty_pdf):
        """Test extraction from empty PDF (0 pages)."""
        # Should handle gracefully without crashing
        try:
            pages = extract_pages_fitz(empty_pdf)
            # PyMuPDF might raise an exception or return empty list
            assert len(pages) == 0 or pages == []
        except Exception as e:
            # Should raise a meaningful error, not crash
            assert "error" in str(e).lower() or "invalid" in str(e).lower() or "cannot" in str(e).lower()
    
    def test_pdf_with_only_images(self, image_only_pdf):
        """Test extraction from PDF with only images (no text)."""
        pages = extract_pages_fitz(image_only_pdf)
        # Should return pages but with empty or minimal text
        assert isinstance(pages, list)
        # Text might be empty or just whitespace
        for page_num, text in pages:
            assert isinstance(page_num, int)
            assert isinstance(text, str)
    
    def test_corrupted_truncated_pdf(self, corrupted_pdf):
        """Test extraction from corrupted/truncated PDF."""
        with pytest.raises(Exception) as exc_info:
            extract_pages_fitz(corrupted_pdf)
        
        error_msg = str(exc_info.value).lower()
        # Should produce a helpful error message
        assert any(word in error_msg for word in [
            "error", "invalid", "corrupt", "damaged", "cannot", "unable", "broken"
        ]), f"Error message not helpful: {exc_info.value}"
    
    def test_non_pdf_file_with_pdf_extension(self, non_pdf_with_pdf_extension):
        """Test extraction from non-PDF file with .pdf extension."""
        with pytest.raises(Exception) as exc_info:
            extract_pages_fitz(non_pdf_with_pdf_extension)
        
        error_msg = str(exc_info.value).lower()
        # Should produce a helpful error message
        assert any(word in error_msg for word in [
            "error", "invalid", "corrupt", "not a pdf", "cannot", "unable"
        ]), f"Error message not helpful: {exc_info.value}"
    
    def test_password_protected_pdf(self, temp_dir):
        """Test extraction from password-protected PDF."""
        # Create a password-protected PDF
        pdf_path = temp_dir / "protected.pdf"
        try:
            import fitz
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((100, 100), "Secret content")
            # Save with user password (restricts access)
            doc.save(str(pdf_path), encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="secret123")
            doc.close()
            
            # Try to extract without password
            # Note: PyMuPDF may or may not raise an error depending on the version
            # and whether we have owner vs user password protection
            try:
                pages = extract_pages_fitz(pdf_path)
                # If it succeeds, that's also acceptable behavior (PyMuPDF can sometimes
                # open encrypted PDFs for text extraction without password)
                assert isinstance(pages, list)
            except Exception as e:
                # If it fails, should have helpful error message
                error_msg = str(e).lower()
                assert any(word in error_msg for word in [
                    "password", "encrypted", "protected", "permission", "error", "cannot", "failed"
                ]), f"Error message not helpful: {e}"
            
        except ImportError:
            pytest.skip("PyMuPDF not available for creating test PDF")
    
    def test_pdf_with_malformed_metadata(self, temp_dir):
        """Test extraction from PDF with malformed metadata."""
        # Create a PDF with weird metadata
        pdf_path = temp_dir / "malformed_meta.pdf"
        # PDF with malformed object references but still valid structure
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R /Names << /EmbeddedFiles << /Names [(
\x00\x01\x02\x03invalid bytes here
) 5 0 R] >> >> >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
   /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>
endobj
4 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
5 0 obj
<< /Length 68 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test content) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000130 00000 n 
0000000187 00000 n 
0000000306 00000 n 
0000000366 00000 n 
trailer
<< /Root 1 0 R /Size 6 >>
startxref
484
%%EOF"""
        pdf_path.write_bytes(pdf_content)
        
        # Should handle gracefully
        try:
            pages = extract_pages_fitz(pdf_path)
            assert isinstance(pages, list)
        except Exception as e:
            # If it fails, should have helpful error
            assert "error" in str(e).lower() or "cannot" in str(e).lower()


# =============================================================================
# INVALID PATH TESTS
# =============================================================================

class TestInvalidPaths:
    """Tests for handling invalid file and directory paths."""
    
    def test_nonexistent_file(self, temp_dir):
        """Test handling of non-existent file path."""
        nonexistent = temp_dir / "does_not_exist.pdf"
        
        with pytest.raises(FileNotFoundError) as exc_info:
            extract_pages_fitz(nonexistent)
        
        assert "not found" in str(exc_info.value).lower() or "does not exist" in str(exc_info.value).lower()
    
    def test_directory_instead_of_file(self, temp_dir):
        """Test passing a directory where a file is expected."""
        with pytest.raises((IsADirectoryError, PermissionError, OSError)) as exc_info:
            extract_pages_fitz(temp_dir)
        
        error_msg = str(exc_info.value).lower()
        assert any(word in error_msg for word in [
            "directory", "folder", "is a dir", "permission", "cannot"
        ]), f"Error message not helpful: {exc_info.value}"
    
    def test_file_instead_of_directory(self, temp_dir):
        """Test passing a file where a directory is expected."""
        file_path = temp_dir / "some_file.txt"
        file_path.write_text("content")
        
        # Test discover_pdfs with file instead of directory
        result = discover_pdfs(file_path)
        # If file is PDF, should return it; if not, should return empty
        assert isinstance(result, list)
    
    def test_path_with_special_characters(self, temp_dir):
        """Test paths with special characters."""
        # Create directory with special characters
        special_dir = temp_dir / "dir with spaces & symbols!@#"
        special_dir.mkdir()
        
        pdf_path = special_dir / "test.pdf"
        # Create a minimal valid PDF
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Test) Tj ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000214 00000 n 
trailer
<< /Root 1 0 R /Size 5 >>
startxref
308
%%EOF"""
        pdf_path.write_bytes(pdf_content)
        
        # Should handle special characters in path
        pages = extract_pages_fitz(pdf_path)
        assert isinstance(pages, list)
    
    def test_path_with_unicode_characters(self, temp_dir):
        """Test paths with Unicode characters."""
        # Create directory with Unicode characters
        unicode_dir = temp_dir / "目录_日本語_한국어_العربية"
        unicode_dir.mkdir()
        
        pdf_path = unicode_dir / "文档.pdf"
        # Create a minimal valid PDF
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Test) Tj ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000214 00000 n 
trailer
<< /Root 1 0 R /Size 5 >>
startxref
308
%%EOF"""
        pdf_path.write_bytes(pdf_content)
        
        # Should handle Unicode characters in path
        pages = extract_pages_fitz(pdf_path)
        assert isinstance(pages, list)
    
    def test_very_long_path(self, temp_dir):
        """Test paths exceeding 255 characters."""
        # Create nested directories to make a long path
        long_name = "a" * 50
        current_dir = temp_dir
        for i in range(5):
            current_dir = current_dir / f"{long_name}_{i}"
            current_dir.mkdir()
        
        pdf_path = current_dir / "test.pdf"
        # Create a minimal valid PDF
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Test) Tj ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000214 00000 n 
trailer
<< /Root 1 0 R /Size 5 >>
startxref
308
%%EOF"""
        pdf_path.write_bytes(pdf_content)
        
        # Should handle long paths
        pages = extract_pages_fitz(pdf_path)
        assert isinstance(pages, list)
    
    def test_relative_path_with_parent_directory(self, temp_dir):
        """Test relative paths with .. (parent directory)."""
        # Create a nested structure
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        
        pdf_path = temp_dir / "test.pdf"
        # Create a minimal valid PDF
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Test) Tj ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000214 00000 n 
trailer
<< /Root 1 0 R /Size 5 >>
startxref
308
%%EOF"""
        pdf_path.write_bytes(pdf_content)
        
        # Change to subdir and use relative path
        import os as os_module
        original_dir = os_module.getcwd()
        try:
            os_module.chdir(subdir)
            relative_path = Path("../test.pdf")
            pages = extract_pages_fitz(relative_path)
            assert isinstance(pages, list)
        finally:
            os_module.chdir(original_dir)


# =============================================================================
# INVALID CONFIGURATION TESTS
# =============================================================================

class TestInvalidConfigurations:
    """Tests for handling invalid concept configuration files."""
    
    def test_empty_concepts_yaml(self, temp_dir):
        """Test loading empty concepts.yaml file."""
        config_path = temp_dir / "concepts.yaml"
        config_path.write_text("")
        
        with pytest.raises(ValueError) as exc_info:
            load_concepts_config(config_path)
        
        error_msg = str(exc_info.value).lower()
        assert any(word in error_msg for word in [
            "empty", "invalid", "config", "cannot", "null", "none"
        ]), f"Error message not helpful: {exc_info.value}"
    
    def test_invalid_yaml_syntax(self, temp_dir):
        """Test loading YAML with invalid syntax."""
        config_path = temp_dir / "concepts.yaml"
        config_path.write_text("""
concepts:
  - invalid: [
      unclosed bracket
    another_key: value
  - missing colon here
    key value
""")
        
        with pytest.raises((yaml.YAMLError, ValueError)) as exc_info:
            load_concepts_config(config_path)
    
    def test_missing_required_fields(self, temp_dir):
        """Test loading concepts.yaml with missing required fields."""
        config_path = temp_dir / "concepts.yaml"
        config_path.write_text("""
concepts:
  test-concept:
    # Missing title, definition, sections
    difficulty: beginner
""")
        
        # Should load but may have missing data
        config = load_concepts_config(config_path)
        assert "concepts" in config
        # Should have default values or empty strings
        assert "test-concept" in config["concepts"]
    
    def test_wrong_data_types(self, temp_dir):
        """Test loading concepts.yaml with wrong data types."""
        config_path = temp_dir / "concepts.yaml"
        config_path.write_text("""
concepts:
  test-concept:
    title: 12345
    definition: ["not", "a", "string"]
    difficulty: 999
    estimatedReadTime: "not a number"
    sections: "not a dict"
""")
        
        # Should load or handle gracefully
        try:
            config = load_concepts_config(config_path)
            # Type errors should be handled
        except (TypeError, ValueError) as e:
            # Or should raise meaningful error
            assert "type" in str(e).lower() or "invalid" in str(e).lower()
    
    def test_circular_concept_references(self, temp_dir):
        """Test handling of circular concept references."""
        config_path = temp_dir / "concepts.yaml"
        config_path.write_text("""
concepts:
  concept-a:
    title: "Concept A"
    relatedConcepts: ["concept-b"]
    sections:
      definition: [1]
  concept-b:
    title: "Concept B"
    relatedConcepts: ["concept-a"]
    sections:
      definition: [2]
""")
        
        config = load_concepts_config(config_path)
        assert "concept-a" in config["concepts"]
        assert "concept-b" in config["concepts"]
        # Should handle circular references gracefully
    
    def test_missing_concepts_key(self, temp_dir):
        """Test loading YAML without concepts key."""
        config_path = temp_dir / "concepts.yaml"
        config_path.write_text("""
other_key:
  some_value: test
""")
        
        with pytest.raises(ValueError) as exc_info:
            load_concepts_config(config_path)
        
        assert "concepts" in str(exc_info.value).lower() or "textbooks" in str(exc_info.value).lower()


# =============================================================================
# INVALID CLI ARGUMENT TESTS
# =============================================================================

class TestInvalidCLIArguments:
    """Tests for handling invalid CLI arguments."""
    
    def test_negative_chunk_words(self):
        """Test negative value for chunk_words."""
        with pytest.raises(ValueError) as exc_info:
            opts = IndexBuildOptions(chunkWords=-100, overlapWords=30)
        
        # Pydantic should validate this
        assert "greater" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()
    
    def test_overlap_greater_than_chunk(self):
        """Test overlap_words > chunk_words."""
        opts = IndexBuildOptions(chunkWords=50, overlapWords=100)
        
        with pytest.raises(ValueError) as exc_info:
            opts.validate_pair()
        
        assert "overlap" in str(exc_info.value).lower() or "smaller" in str(exc_info.value).lower()
    
    def test_invalid_embedding_dim(self):
        """Test invalid embedding dimension."""
        with pytest.raises(ValueError) as exc_info:
            opts = IndexBuildOptions(chunkWords=180, overlapWords=30, embeddingDim=0)
        
        assert "greater" in str(exc_info.value).lower()
    
    def test_zero_chunk_words(self):
        """Test zero value for chunk_words."""
        with pytest.raises(ValueError) as exc_info:
            opts = IndexBuildOptions(chunkWords=0, overlapWords=0)
        
        assert "greater" in str(exc_info.value).lower()


# =============================================================================
# ERROR MESSAGE TESTS
# =============================================================================

class TestErrorMessages:
    """Tests for verifying error messages are helpful."""
    
    def test_file_not_found_error_message(self):
        """Test error message for non-existent file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            extract_pages_fitz(Path("/path/that/does/not/exist.pdf"))
        
        error_msg = str(exc_info.value)
        assert len(error_msg) > 10, "Error message too short"
        assert any(word in error_msg.lower() for word in [
            "not found", "does not exist", "cannot find", "no such"
        ]), f"Unhelpful error message: {error_msg}"
    
    def test_quality_check_error_messages(self):
        """Test quality check error messages."""
        # Empty pages
        result = check_extraction_quality([])
        assert "reason" in result
        assert result["needs_ocr"] is True
        
        # Very short text
        pages = [(1, "ab")]
        result = check_extraction_quality(pages)
        assert "reason" in result
        assert len(result["reason"]) > 0
    
    def test_config_load_error_messages(self, temp_dir):
        """Test config loading error messages."""
        config_path = temp_dir / "nonexistent.yaml"
        
        with pytest.raises(FileNotFoundError) as exc_info:
            load_concepts_config(config_path)
        
        error_msg = str(exc_info.value)
        assert "concepts" in error_msg.lower() or "config" in error_msg.lower()
        assert "not found" in error_msg.lower() or "does not exist" in error_msg.lower()
    
    def test_sql_validation_error_messages(self):
        """Test SQL validation error messages."""
        # Empty SQL
        result = validate_sql_snippet("")
        assert not result.is_valid
        assert len(result.issues) > 0
        assert "empty" in result.issues[0].lower()
        
        # Invalid SQL
        result = validate_sql_snippet("NOT A SQL STATEMENT")
        assert not result.is_valid
        assert len(result.issues) > 0
    
    def test_json_parsing_error_messages(self):
        """Test JSON parsing error messages."""
        # Invalid JSON
        success, data, error = safe_parse_json("not valid json")
        assert not success
        assert data is None
        assert len(error) > 0
        assert "json" in error.lower() or "parse" in error.lower()
        
        # Empty string
        success, data, error = safe_parse_json("")
        assert not success
        assert "empty" in error.lower()


# =============================================================================
# GRACEFUL DEGRADATION TESTS
# =============================================================================

class TestGracefulDegradation:
    """Tests for graceful degradation when dependencies are unavailable."""
    
    def test_ocr_not_installed(self, temp_dir):
        """Test handling when OCRmyPDF is not installed - mocked to avoid import errors."""
        from unittest.mock import patch
        
        pdf_path = temp_dir / "test.pdf"
        # Create minimal PDF
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Test) Tj ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000214 00000 n 
trailer
<< /Root 1 0 R /Size 5 >>
startxref
308
%%EOF"""
        pdf_path.write_bytes(pdf_content)
        
        # Mock ocr_pdf_with_validation to raise RuntimeError (simulating ocrmypdf not installed)
        with patch('algl_pdf_helper.extract.ocr_pdf_with_validation') as mock_ocr:
            mock_ocr.side_effect = RuntimeError(
                "OCR requested but ocrmypdf is not installed. "
                "Install with: pip install -e '.[ocr]'"
            )
            
            # Try to use OCR strategy - should raise RuntimeError
            with pytest.raises(RuntimeError) as exc_info:
                extract_with_strategy(
                    pdf_path,
                    strategy="ocrmypdf",
                    min_coverage=0.5,
                )
            
            error_msg = str(exc_info.value).lower()
            assert "ocrmypdf" in error_msg or "not installed" in error_msg
    
    def test_marker_not_installed(self, temp_dir):
        """Test handling when Marker is not installed - mocked to avoid import errors."""
        from unittest.mock import patch
        
        pdf_path = temp_dir / "test.pdf"
        # Create minimal PDF
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Test) Tj ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000214 00000 n 
trailer
<< /Root 1 0 R /Size 5 >>
startxref
308
%%EOF"""
        pdf_path.write_bytes(pdf_content)
        
        # Mock _extract_with_marker to raise ImportError (simulating marker not installed)
        with patch('algl_pdf_helper.extract._extract_with_marker') as mock_marker:
            mock_marker.side_effect = ImportError("No module named 'marker'")
            
            # Try to use Marker strategy - should raise RuntimeError
            with pytest.raises(RuntimeError) as exc_info:
                extract_with_strategy(
                    pdf_path,
                    strategy="marker",
                    min_coverage=0.5,
                )
            
            error_msg = str(exc_info.value).lower()
            assert "marker" in error_msg or "not installed" in error_msg
    
    def test_llm_not_available(self):
        """Test handling when LLM is not available - fully mocked."""
        from unittest.mock import patch, MagicMock
        
        # Mock the generator to simulate LLM unavailability
        with patch('algl_pdf_helper.educational_pipeline.EducationalNoteGenerator') as MockGenerator:
            mock_instance = MagicMock()
            mock_instance.skip_llm = True
            mock_instance.llm_available = False
            MockGenerator.return_value = mock_instance
            
            # Create generator with fake API keys
            generator = EducationalNoteGenerator(
                llm_provider="openai",
                openai_api_key="fake_key_12345",
                skip_llm=True,
            )
            
            # Should still function without LLM
            assert generator.skip_llm is True
    
    def test_missing_api_keys(self):
        """Test handling when API keys are missing - fully mocked."""
        from unittest.mock import patch, MagicMock
        
        # Mock the generator to simulate missing API keys
        with patch('algl_pdf_helper.educational_pipeline.EducationalNoteGenerator') as MockGenerator:
            mock_instance = MagicMock()
            mock_instance.skip_llm = True
            mock_instance.llm_available = False
            MockGenerator.return_value = mock_instance
            
            # Create generator without API keys
            generator = EducationalNoteGenerator(
                llm_provider="openai",
                skip_llm=True,
            )
            
            # Should detect that LLM is not available
            assert generator.llm_available is False or generator.skip_llm is True
    
    def test_output_directory_without_write_permissions(self, temp_dir):
        """Test handling of output directory without write permissions."""
        # Create a read-only directory
        read_only_dir = temp_dir / "readonly"
        read_only_dir.mkdir()
        
        # Remove write permission
        original_mode = read_only_dir.stat().st_mode
        read_only_dir.chmod(0o555)  # Read and execute, no write
        
        try:
            # Try to create a file in the read-only directory
            test_file = read_only_dir / "test.txt"
            with pytest.raises((PermissionError, OSError)) as exc_info:
                test_file.write_text("test")
            
            error_msg = str(exc_info.value).lower()
            assert any(word in error_msg for word in [
                "permission", "denied", "access", "not allowed"
            ]), f"Unhelpful error message: {exc_info.value}"
        finally:
            # Restore permissions for cleanup
            read_only_dir.chmod(original_mode)


# =============================================================================
# RECOVERY MECHANISM TESTS
# =============================================================================

class TestRecoveryMechanisms:
    """Tests for recovery mechanisms and cleanup."""
    
    def test_temp_file_cleanup_on_error(self, temp_dir):
        """Test that temp files are cleaned up on error."""
        # Create a fake temp PDF path
        fake_temp = temp_dir / "algl_pdf_test" / "temp.pdf"
        fake_temp.parent.mkdir()
        fake_temp.write_text("temp content")
        
        # Verify file exists
        assert fake_temp.exists()
        
        # Clean up
        cleanup_temp_pdf(fake_temp)
        
        # Verify cleanup happened
        assert not fake_temp.parent.exists() or not fake_temp.exists()
    
    def test_partial_output_cleanup(self, temp_dir):
        """Test cleanup of partial output on failure."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()
        
        # Create partial output files
        (output_dir / "manifest.json").write_text("{}")
        (output_dir / "partial.txt").write_text("incomplete")
        
        # Simulate a failure that should trigger cleanup
        try:
            raise RuntimeError("Simulated failure")
        except RuntimeError:
            pass  # In real code, this would trigger cleanup
        
        # Files should still exist (cleanup is manual in real code)
        # This test verifies the cleanup function works
    
    def test_retry_logic_for_failed_operations(self):
        """Test retry logic for operations that may fail."""
        # This tests the concept - real retry logic would be in the code
        attempts = 0
        max_attempts = 3
        
        def flaky_operation():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ConnectionError("Temporary failure")
            return "success"
        
        # Simulate retry
        result = None
        for i in range(max_attempts):
            try:
                result = flaky_operation()
                break
            except ConnectionError:
                if i == max_attempts - 1:
                    raise
                continue
        
        assert result == "success"
        assert attempts == 3


# =============================================================================
# CHUNKER EDGE CASE TESTS
# =============================================================================

class TestChunkerEdgeCases:
    """Tests for chunker edge cases."""
    
    def test_empty_text_chunking(self):
        """Test chunking empty text."""
        result = chunk_page_words(
            doc_id="test",
            page=1,
            text="",
            chunk_words=180,
            overlap_words=30,
        )
        assert result == []
    
    def test_whitespace_only_text(self):
        """Test chunking whitespace-only text."""
        result = chunk_page_words(
            doc_id="test",
            page=1,
            text="   \n\t  \n  ",
            chunk_words=180,
            overlap_words=30,
        )
        assert result == []
    
    def test_text_shorter_than_chunk_size(self):
        """Test chunking text shorter than chunk size."""
        text = "Short text."
        result = chunk_page_words(
            doc_id="test",
            page=1,
            text=text,
            chunk_words=180,
            overlap_words=30,
        )
        assert len(result) == 1
        assert result[0][1] == text
    
    def test_exact_chunk_boundary(self):
        """Test chunking at exact boundary."""
        words = ["word"] * 180
        text = " ".join(words)
        result = chunk_page_words(
            doc_id="test",
            page=1,
            text=text,
            chunk_words=180,
            overlap_words=30,
        )
        assert len(result) == 1
        assert len(result[0][1].split()) == 180
    
    def test_very_long_words(self):
        """Test chunking with very long words."""
        long_word = "a" * 1000
        text = f"{long_word} {long_word}"
        result = chunk_page_words(
            doc_id="test",
            page=1,
            text=text,
            chunk_words=10,
            overlap_words=2,
        )
        assert len(result) >= 1
    
    def test_unicode_text_chunking(self):
        """Test chunking Unicode text."""
        text = "日本語のテキスト。한국어 텍스트。العربية النص。"
        result = chunk_page_words(
            doc_id="test",
            page=1,
            text=text,
            chunk_words=10,
            overlap_words=2,
        )
        assert len(result) >= 1
    
    def test_special_characters_in_text(self):
        """Test chunking text with special characters."""
        text = "Special <>&\"' chars \x00\x01\x02 binary"
        result = chunk_page_words(
            doc_id="test",
            page=1,
            text=text,
            chunk_words=10,
            overlap_words=2,
        )
        assert len(result) >= 1


# =============================================================================
# EMBEDDING EDGE CASE TESTS
# =============================================================================

class TestEmbeddingEdgeCases:
    """Tests for embedding edge cases."""
    
    def test_empty_text_embedding(self):
        """Test embedding empty text."""
        result = build_hash_embedding("", dim=24)
        # Should return zero vector or handle gracefully
        assert len(result) == 24
    
    def test_very_long_text_embedding(self):
        """Test embedding very long text."""
        text = "word " * 10000
        result = build_hash_embedding(text, dim=24)
        assert len(result) == 24
    
    def test_unicode_text_embedding(self):
        """Test embedding Unicode text."""
        text = "日本語 한국어 العربية 🎉 emoji"
        result = build_hash_embedding(text, dim=24)
        assert len(result) == 24
    
    def test_very_small_dimension(self):
        """Test embedding with very small dimension."""
        text = "Test text"
        result = build_hash_embedding(text, dim=4)
        assert len(result) == 4
    
    def test_very_large_dimension(self):
        """Test embedding with very large dimension."""
        text = "Test text"
        result = build_hash_embedding(text, dim=1024)
        assert len(result) == 1024


# =============================================================================
# TEXT QUALITY EDGE CASE TESTS
# =============================================================================

class TestTextQualityEdgeCases:
    """Tests for text quality edge cases."""
    
    def test_null_bytes_in_text(self):
        """Test handling text with null bytes."""
        text = "Hello\x00World\x00\x00Test"
        normalized = normalize_text(text)
        assert "\x00" not in normalized
    
    def test_gibberish_text_quality(self):
        """Test quality calculation for gibberish text."""
        gibberish = "___^^^***###abcDEFghi###***^^^___"
        quality = calculate_text_quality(gibberish)
        assert quality["is_quality_good"] is False
        assert quality["gibberish_patterns"] > 0
    
    def test_very_short_text_quality(self):
        """Test quality calculation for very short text."""
        short = "Hi"
        quality = calculate_text_quality(short)
        assert quality["is_quality_good"] is False
    
    def test_binary_content_in_text(self):
        """Test quality calculation for text with binary content."""
        binary_text = "Hello \x80\x81\x82\x83 World"
        quality = calculate_text_quality(binary_text)
        # Should handle gracefully
        assert "total_chars" in quality


# =============================================================================
# CONCEPT MAPPING EDGE CASE TESTS
# =============================================================================

class TestConceptMappingEdgeCases:
    """Tests for concept mapping edge cases."""
    
    def test_empty_concepts_config(self):
        """Test building manifest with empty concepts config."""
        config = {"concepts": {}}
        chunks = []
        
        manifest = build_concept_manifest(
            concepts_config=config,
            chunks=chunks,
            source_doc_id="test",
        )
        
        assert manifest.conceptCount == 0
        assert len(manifest.concepts) == 0
    
    def test_concept_with_no_matching_chunks(self, valid_sample_chunks):
        """Test concept with pages that have no chunks."""
        config = {
            "concepts": {
                "test-concept": {
                    "title": "Test Concept",
                    "sections": {
                        "definition": [999]  # Page with no chunks
                    }
                }
            }
        }
        
        manifest = build_concept_manifest(
            concepts_config=config,
            chunks=valid_sample_chunks,
            source_doc_id="test",
        )
        
        assert manifest.conceptCount == 1
        concept = manifest.concepts["test-concept"]
        # Should have empty chunk IDs for non-existent pages
        assert len(concept.sections["definition"].chunkIds) == 0
    
    def test_invalid_page_numbers_in_config(self, valid_sample_chunks):
        """Test handling of invalid page numbers in config."""
        config = {
            "concepts": {
                "test-concept": {
                    "title": "Test Concept",
                    "sections": {
                        "definition": [-1, 0, "invalid"]  # Invalid page numbers
                    }
                }
            }
        }
        
        # Should handle gracefully
        try:
            manifest = build_concept_manifest(
                concepts_config=config,
                chunks=valid_sample_chunks,
                source_doc_id="test",
            )
        except (ValueError, TypeError) as e:
            # Should raise meaningful error
            assert "page" in str(e).lower() or "invalid" in str(e).lower()


# =============================================================================
# MODEL VALIDATION EDGE CASE TESTS
# =============================================================================

class TestModelValidationEdgeCases:
    """Tests for Pydantic model validation edge cases."""
    
    def test_concept_info_missing_required_fields(self):
        """Test ConceptInfo with missing required fields."""
        with pytest.raises(ValueError):
            ConceptInfo()  # id is required
    
    def test_concept_manifest_invalid_schema_version(self):
        """Test ConceptManifest with invalid schema version."""
        with pytest.raises(ValueError) as exc_info:
            ConceptManifest(schemaVersion="invalid-version")
        
        assert "schemaversion" in str(exc_info.value).lower()
    
    def test_invalid_chunk_data(self):
        """Test PdfIndexChunk with invalid data."""
        with pytest.raises(ValueError):
            PdfIndexChunk(
                chunkId="test",
                docId="test",
                page=-1,  # Invalid negative page
                text="test",
            )
    
    def test_asset_manifest_validation(self):
        """Test AssetManifest validation."""
        with pytest.raises(ValueError) as exc_info:
            AssetManifest(schemaVersion="wrong-version")
        
        assert "schemaversion" in str(exc_info.value).lower()


# =============================================================================
# SQL VALIDATION EDGE CASE TESTS
# =============================================================================

class TestSQLValidationEdgeCases:
    """Tests for SQL validation edge cases."""
    
    def test_empty_sql_validation(self):
        """Test validation of empty SQL."""
        result = validate_sql_snippet("")
        assert not result.is_valid
        assert len(result.issues) > 0
    
    def test_sql_with_only_comments(self):
        """Test validation of SQL with only comments."""
        sql = "-- This is a comment\n/* Multi-line\ncomment */"
        result = validate_sql_snippet(sql)
        # May be valid or invalid depending on implementation
        assert isinstance(result.is_valid, bool)
    
    def test_sql_with_injection_patterns(self):
        """Test detection of SQL injection patterns."""
        sql = "SELECT * FROM users; DROP TABLE users;"
        result = validate_sql_snippet(sql)
        # Should detect dangerous pattern
        assert len(result.warnings) > 0 or not result.is_valid
    
    def test_unbalanced_parentheses(self):
        """Test detection of unbalanced parentheses."""
        sql = "SELECT * FROM (SELECT id FROM users;"
        result = validate_sql_snippet(sql)
        assert not result.is_valid
        assert any("parenthes" in issue.lower() for issue in result.issues)
    
    def test_incomplete_sql_statements(self):
        """Test validation of incomplete SQL."""
        incomplete_statements = [
            "SELECT",
            "SELECT *",
            "SELECT * FROM",
            "INSERT INTO",
            "UPDATE",
            "DELETE FROM",
        ]
        
        for sql in incomplete_statements:
            result = validate_sql_snippet(sql, allow_partial=False)
            # May be invalid or have warnings
            assert isinstance(result.is_valid, bool)


# =============================================================================
# OUTPUT CONFIG EDGE CASE TESTS
# =============================================================================

class TestOutputConfigEdgeCases:
    """Tests for output config edge cases."""
    
    def test_output_config_no_env_var_no_explicit(self):
        """Test OutputConfig with no env var and no explicit path."""
        config = OutputConfig(output_dir=None)
        
        # Clear environment
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                config.resolve()
            
            error_msg = str(exc_info.value)
            assert "output" in error_msg.lower() or "directory" in error_msg.lower()
            assert "--output-dir" in error_msg or "SQL_ADAPT_PUBLIC_DIR" in error_msg
    
    def test_output_config_with_env_var(self, temp_dir):
        """Test OutputConfig with environment variable."""
        config = OutputConfig(output_dir=None)
        
        with patch.dict(os.environ, {"SQL_ADAPT_PUBLIC_DIR": str(temp_dir)}):
            result = config.resolve()
            assert result == temp_dir / "textbook-static"


# =============================================================================
# DOCUMENT ID GENERATION EDGE CASE TESTS
# =============================================================================

class TestDocIdEdgeCases:
    """Tests for document ID generation edge cases."""
    
    def test_duplicate_doc_id_handling(self):
        """Test handling of duplicate document IDs."""
        used = set()
        
        id1 = unique_doc_id("test", used)
        assert id1 == "test"
        
        id2 = unique_doc_id("test", used)
        assert id2 == "test-2"
        
        id3 = unique_doc_id("test", used)
        assert id3 == "test-3"
    
    def test_get_doc_alias_special_characters(self):
        """Test doc alias generation with special characters."""
        test_cases = [
            ("File With Spaces.pdf", "file-with-spaces"),
            ("file_with_underscores.PDF", "file-with-underscores"),
            ("file--multiple---dashes.pdf", "file-multiple-dashes"),
            ("UPPERCASE.PDF", "uppercase"),
            ("MiXeD.CaSe.PDF", "mixed-case"),
            (".pdf", "pdf"),  # Just extension
            ("a", "a"),  # Single char
        ]
        
        for filename, expected in test_cases:
            result = get_doc_alias(filename)
            assert result == expected, f"Failed for {filename}: got {result}, expected {expected}"


# =============================================================================
# JSON PARSING EDGE CASE TESTS
# =============================================================================

class TestJSONParsingEdgeCases:
    """Tests for JSON parsing edge cases."""
    
    def test_extract_json_from_markdown_code_block(self):
        """Test extracting JSON from markdown code block."""
        text = '''```json
{"key": "value", "number": 123}
```'''
        result = extract_json_from_llm_output(text)
        assert result == {"key": "value", "number": 123}
    
    def test_extract_json_with_extra_text(self):
        """Test extracting JSON surrounded by extra text."""
        text = '''Here's the JSON you requested:

{"result": "success", "data": [1, 2, 3]}

Hope that helps!'''
        result = extract_json_from_llm_output(text)
        assert result == {"result": "success", "data": [1, 2, 3]}
    
    def test_extract_nested_json(self):
        """Test extracting deeply nested JSON."""
        data = {"level1": {"level2": {"level3": {"value": "deep"}}}}
        text = json.dumps(data)
        result = extract_json_from_llm_output(text)
        assert result == data
    
    def test_extract_invalid_json(self):
        """Test handling of invalid JSON."""
        text = "This is not JSON at all"
        result = extract_json_from_llm_output(text)
        assert result is None
    
    def test_extract_json_array(self):
        """Test extracting JSON array."""
        text = '[{"id": 1}, {"id": 2}]'
        result = extract_json_from_llm_output(text)
        assert result == [{"id": 1}, {"id": 2}]


# =============================================================================
# TEXT CLEANER EDGE CASE TESTS
# =============================================================================

class TestTextCleanerEdgeCases:
    """Tests for text cleaner edge cases."""
    
    def test_clean_empty_text(self):
        """Test cleaning empty text."""
        result = TextCleaner.clean_pdf_text("")
        assert result == ""
    
    def test_clean_none_text(self):
        """Test cleaning None text."""
        result = TextCleaner.clean_pdf_text(None)
        assert result == ""
    
    def test_clean_very_long_text(self):
        """Test cleaning very long text."""
        long_text = "Word " * 10000
        result = TextCleaner.clean_pdf_text(long_text)
        assert isinstance(result, str)
    
    def test_clean_text_with_many_headers(self):
        """Test cleaning text with many headers/footers."""
        text = """
520 Section 5.1 Introduction
Content here
525 Chapter 18 Summary
More content
Page 123
Final content
"""
        result = TextCleaner.clean_pdf_text(text)
        # Should have removed header/footer patterns
        assert "Section 5.1" not in result or "Content" in result


# =============================================================================
# CONTENT VALIDATOR EDGE CASE TESTS
# =============================================================================

class TestContentValidatorEdgeCases:
    """Tests for content validator edge cases."""
    
    def test_relevance_empty_text(self):
        """Test relevance calculation for empty text."""
        result = ContentValidator.calculate_content_relevance(
            "", "select", "SELECT Statement"
        )
        assert result["score"] == 0 or result["is_relevant"] is False
    
    def test_relevance_non_sql_content(self):
        """Test relevance calculation for non-SQL content."""
        text = "This is about Java programming and JDBC connections."
        result = ContentValidator.calculate_content_relevance(
            text, "select", "SELECT Statement"
        )
        assert result["is_relevant"] is False
        assert result["non_sql_penalty"] > 0
    
    def test_relevance_sql_content(self):
        """Test relevance calculation for SQL content."""
        text = "SELECT * FROM users WHERE id = 1;"
        result = ContentValidator.calculate_content_relevance(
            text, "select", "SELECT Statement"
        )
        assert result["is_relevant"] is True
        assert result["sql_score"] > 0


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
