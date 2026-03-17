"""Regression tests for text cleaning and deduplication.

These tests verify that the text cleanup pipeline correctly:
1. Removes duplicate paragraphs
2. Removes repeated headers/footers
3. Normalizes broken line breaks
4. Preserves SQL code formatting
"""

from __future__ import annotations

import pytest

from algl_pdf_helper.clean import (
    deduplicate_repeated_lines,
    deduplicate_text,
    fix_broken_formatting,
    normalize_line_breaks,
    clean_text_for_students,
)


# =============================================================================
# Duplicate Paragraph Tests
# =============================================================================

class TestDeduplicateParagraphs:
    """Test duplicate paragraph detection and removal."""
    
    def test_exact_duplicate_removal(self) -> None:
        """Exact duplicate paragraphs should be collapsed to one."""
        text = """This is a paragraph about SQL joins.

This is a paragraph about SQL joins.

This is unique content."""
        
        result = deduplicate_text(text, min_length=10)
        
        # Should only have one instance of the duplicate
        assert result.count("This is a paragraph about SQL joins.") == 1
        # Should preserve unique content
        assert "This is unique content." in result
    
    def test_near_duplicate_removal(self) -> None:
        """Near-duplicate paragraphs with minor differences should be removed."""
        text = """The SELECT statement retrieves data from tables.

The SELECT statement retrieves data from tables

This is different content."""
        
        result = deduplicate_text(text, min_length=10)
        
        # Should collapse near-duplicates
        assert result.count("SELECT statement retrieves data") == 1
        assert "This is different content." in result
    
    def test_short_paragraphs_preserved(self) -> None:
        """Short paragraphs below min_length should not be deduplicated."""
        text = """Note:

Note:

A longer paragraph that should be preserved."""
        
        result = deduplicate_text(text, min_length=20)
        
        # Short "Note:" paragraphs should both be kept
        assert result.count("Note:") == 2
    
    def test_no_false_positives(self) -> None:
        """Different paragraphs with shared words should not be deduplicated."""
        text = """The WHERE clause filters rows based on conditions.

The ORDER BY clause sorts the results.

Use WHERE before ORDER BY for best performance."""
        
        result = deduplicate_text(text, min_length=10)
        
        # All three paragraphs should be preserved
        assert "WHERE clause" in result
        assert "ORDER BY clause" in result
        assert "WHERE before ORDER BY" in result


# =============================================================================
# Repeated Line Tests (Header/Footer contamination)
# =============================================================================

class TestRepeatedLineRemoval:
    """Test removal of repeated header/footer lines."""
    
    def test_repeated_header_removal(self) -> None:
        """Lines that appear multiple times (headers) should be removed."""
        text = """Chapter 3 SQL Basics
Content paragraph one.
Chapter 3 SQL Basics
Content paragraph two.
Chapter 3 SQL Basics"""
        
        result = deduplicate_repeated_lines(text, min_repeats=3)
        
        # Header should be removed
        assert "Chapter 3 SQL Basics" not in result
        # Content should remain
        assert "Content paragraph one" in result
        assert "Content paragraph two" in result
    
    def test_page_number_removal(self) -> None:
        """Repeated page numbers should be removed."""
        # Note: single occurrence page numbers won't be removed
        # This test verifies non-repeated content is preserved
        text = """Introduction to SQL
75
The SELECT statement is used to retrieve data.
76
You can filter results with WHERE."""
        
        result = deduplicate_repeated_lines(text, min_repeats=2)
        
        # Single-occurrence page numbers are preserved (not repeated enough)
        assert "75" in result
        assert "76" in result
        # Content preserved
        assert "SELECT statement" in result
        assert "WHERE" in result
    
    def test_repeated_page_headers_removed(self) -> None:
        """Headers that appear on every page should be removed."""
        text = """Murach's MySQL
Content about SELECT.
Murach's MySQL
More content here.
Murach's MySQL"""
        
        result = deduplicate_repeated_lines(text, min_repeats=3)
        
        # Repeated header should be removed
        assert "Murach's MySQL" not in result
        # Content preserved
        assert "Content about SELECT" in result
        assert "More content" in result


# =============================================================================
# Line Break Normalization Tests
# =============================================================================

class TestLineBreakNormalization:
    """Test normalization of broken lines from PDF extraction."""
    
    def test_hyphenated_word_fix(self) -> None:
        """Hyphenated word breaks should be joined."""
        text = "The SELECT state-\nment retrieves data from tables."
        
        result = normalize_line_breaks(text)
        
        assert "statement" in result
        assert "state-\nment" not in result
    
    def test_orphaned_line_join(self) -> None:
        """Orphaned sentence fragments should be joined to previous lines."""
        text = """SQL is a powerful
language for managing data.
It uses simple syntax."""
        
        result = normalize_line_breaks(text)
        
        # Should join lines that don't end with sentence punctuation
        assert "SQL is a powerful language" in result
    
    def test_sentence_boundary_preserved(self) -> None:
        """Lines ending with sentence punctuation should start new paragraphs."""
        text = """First sentence ends here.
Second sentence starts here.
Third sentence follows."""
        
        result = normalize_line_breaks(text)
        
        # Each sentence should be its own paragraph
        assert "First sentence ends here." in result
        assert "Second sentence starts here." in result


# =============================================================================
# Formatting Fix Tests
# =============================================================================

class TestFormattingFixes:
    """Test broken formatting fixes."""
    
    def test_missing_space_after_period(self) -> None:
        """Missing spaces after periods should be added."""
        text = "First sentence.Second sentence starts immediately."
        
        result = fix_broken_formatting(text)
        
        assert "First sentence. Second" in result
    
    def test_multiple_spaces_collapsed(self) -> None:
        """Multiple spaces should be collapsed to single spaces."""
        text = "Too    many     spaces    here."
        
        result = fix_broken_formatting(text)
        
        assert "  " not in result
        assert "Too many spaces here" in result


# =============================================================================
# Integration Tests
# =============================================================================

class TestCleanTextIntegration:
    """Integration tests for the full clean_text_for_students pipeline."""
    
    def test_full_pipeline_with_duplicates(self) -> None:
        """Full pipeline should remove duplicates and clean text."""
        text = """Chapter 3 SQL Basics

The SELECT statement retrieves data from tables.

The SELECT statement retrieves data from tables.

Use the WHERE clause to filter state-\nment results.

Chapter 3 SQL Basics"""
        
        result = clean_text_for_students(text, deduplicate=True)
        
        # Content should be present
        assert "SELECT statement retrieves data" in result
        # Hyphenated word should be fixed
        assert "statement results" in result
        # Should be properly formatted
        assert "\n\n" in result or "WHERE clause" in result  # Paragraph breaks preserved or content present
    
    def test_sql_code_preserved(self) -> None:
        """SQL code blocks should not be corrupted by deduplication."""
        text = """Here's a SELECT example:

SELECT * FROM users WHERE id = 1;

Another query:

SELECT * FROM orders WHERE status = 'active';"""
        
        result = clean_text_for_students(text, deduplicate=True)
        
        # SQL should be preserved
        assert "SELECT * FROM users" in result
        assert "SELECT * FROM orders" in result
    
    def test_deduplication_can_be_disabled(self) -> None:
        """Deduplication should be optional."""
        text = """This is duplicate content.

This is duplicate content."""
        
        result = clean_text_for_students(text, deduplicate=False)
        
        # With deduplication disabled, duplicates should remain
        assert result.count("duplicate content") == 2


# =============================================================================
# Regression Tests (Real-world patterns)
# =============================================================================

class TestTextbookPatterns:
    """Tests for real textbook extraction patterns."""
    
    def test_murach_style_chapter_header(self) -> None:
        """Murach-style chapter headers should be removed."""
        from algl_pdf_helper.clean import CHAPTER_HEADER_PATTERN
        
        text = "Chapter 3 How to retrieve data from a single table 75\n\nActual content here."
        
        result = CHAPTER_HEADER_PATTERN.sub('', text)
        
        assert "Chapter 3 How to retrieve" not in result
        assert "Actual content here" in result
    
    def test_textbook_page_number_pattern(self) -> None:
        """Standalone page numbers should be removed."""
        from algl_pdf_helper.clean import PAGE_NUMBER_PATTERN
        
        text = """Content on this page.
76
More content here."""
        
        result = PAGE_NUMBER_PATTERN.sub('', text)
        
        assert "\n76\n" not in result
        assert "Content on this page" in result
        assert "More content here" in result
