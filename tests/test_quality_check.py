from __future__ import annotations

from algl_pdf_helper.extract import calculate_text_quality, check_extraction_quality


# Generate enough text to meet MIN_EXTRACTED_CHARS threshold
GOOD_TEXT = "This is a normal sentence with proper words and punctuation. " * 20


def test_calculate_text_quality_good_text() -> None:
    """Test quality calculation with good text."""
    quality = calculate_text_quality(GOOD_TEXT)
    
    assert quality["total_chars"] > 500  # MIN_EXTRACTED_CHARS
    assert quality["readable_ratio"] > 0.9
    assert quality["gibberish_ratio"] < 0.1
    assert quality["is_quality_good"] is True


def test_calculate_text_quality_with_gibberish() -> None:
    """Test quality calculation with gibberish patterns."""
    # Text with lots of gibberish patterns
    text = "___ ^^^ *** @@@ ### $$$ %%% &&& *** " * 100
    quality = calculate_text_quality(text)
    
    # Should detect gibberish patterns
    assert quality["gibberish_patterns"] > 0
    # The gibberish ratio should be significant
    assert quality["gibberish_ratio"] > 0


def test_calculate_text_quality_empty() -> None:
    """Test quality calculation with empty text."""
    quality = calculate_text_quality("")
    
    assert quality["total_chars"] == 0
    assert quality["is_quality_good"] is False


def test_check_extraction_quality_good_pages() -> None:
    """Test extraction quality with good pages."""
    pages = [
        (1, GOOD_TEXT),
        (2, "Page two also has readable text that makes sense. " * 20),
    ]
    
    result = check_extraction_quality(pages)
    
    assert result["page_count"] == 2
    assert result["is_quality_good"] is True
    assert result["needs_ocr"] is False


def test_check_extraction_quality_empty() -> None:
    """Test extraction quality with no pages."""
    result = check_extraction_quality([])
    
    assert result["page_count"] == 0
    assert result["is_quality_good"] is False
    assert result["needs_ocr"] is True


def test_check_extraction_quality_scanned() -> None:
    """Test extraction quality with scanned page (minimal text)."""
    pages = [
        (1, ""),
        (2, "   "),
    ]
    
    result = check_extraction_quality(pages)
    
    assert result["is_quality_good"] is False
    assert result["needs_ocr"] is True
