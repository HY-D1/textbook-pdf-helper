"""Tests for section extractor hierarchy establishment.

Regression tests for hierarchy popping bug where same-level headings
could cause IndexError when popping from empty stack.
"""

from __future__ import annotations

import pytest

from algl_pdf_helper.section_extractor import SectionExtractor, ContentBlock, BlockType


class TestHierarchyEstablishment:
    """Regression tests for hierarchy popping bug."""
    
    def test_same_level_headings_no_underflow(self):
        """Two headings of same level should not cause pop from empty list."""
        extractor = SectionExtractor()
        headings = [
            ContentBlock(
                block_id="test:p1:b1",
                block_type=BlockType.HEADING,
                page_number=1,
                char_start=0,
                char_end=10,
                text_content="Chapter 1",
                metadata={"heading_level": 1}
            ),
            ContentBlock(
                block_id="test:p1:b2",
                block_type=BlockType.HEADING,
                page_number=1,
                char_start=20,
                char_end=30,
                text_content="Chapter 2",
                metadata={"heading_level": 1}
            ),
        ]
        # Should not raise IndexError
        result = extractor._establish_hierarchy(headings)
        assert len(result) == 2
    
    def test_shallow_after_deep_no_underflow(self):
        """Shallow heading after deep heading should not underflow."""
        extractor = SectionExtractor()
        headings = [
            ContentBlock(
                block_id="test:p1:b1",
                block_type=BlockType.HEADING,
                page_number=1,
                char_start=0,
                char_end=10,
                text_content="Chapter 1",
                metadata={"heading_level": 1}
            ),
            ContentBlock(
                block_id="test:p1:b2",
                block_type=BlockType.HEADING,
                page_number=1,
                char_start=20,
                char_end=35,
                text_content="Section 1.1.1",
                metadata={"heading_level": 3}
            ),
            ContentBlock(
                block_id="test:p1:b3",
                block_type=BlockType.HEADING,
                page_number=1,
                char_start=40,
                char_end=50,
                text_content="Chapter 2",
                metadata={"heading_level": 1}
            ),
        ]
        # Should not raise IndexError
        result = extractor._establish_hierarchy(headings)
        assert len(result) == 3
