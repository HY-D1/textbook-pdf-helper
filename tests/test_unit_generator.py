"""
Tests for Unit Generator and evidence span creation.

Tests cover:
- Evidence span creation with block type mapping
- SourceSpan validation
- Block type canonicalization
"""

from __future__ import annotations

import pytest

from algl_pdf_helper.section_extractor import BlockType, ContentBlock
from algl_pdf_helper.unit_generator import UnitGenerator
from algl_pdf_helper.instructional_models import SourceSpan


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def unit_generator():
    """Fixture for UnitGenerator instance."""
    return UnitGenerator()


@pytest.fixture
def sample_content_blocks():
    """Fixture for sample content blocks with various block types."""
    return [
        ContentBlock(
            block_id="block-1",
            block_type=BlockType.SUBHEADING,
            text_content="SQL Joins Overview",
            page_number=10,
            char_start=0,
            char_end=100,
        ),
        ContentBlock(
            block_id="block-2",
            block_type=BlockType.EXPLANATORY_PROSE,
            text_content="SQL JOINs are used to combine rows from two or more tables based on related columns between them.",
            page_number=10,
            char_start=101,
            char_end=300,
        ),
        ContentBlock(
            block_id="block-3",
            block_type=BlockType.SQL_CODE,
            text_content="SELECT * FROM users JOIN orders ON users.id = orders.user_id;",
            page_number=11,
            char_start=0,
            char_end=70,
        ),
        ContentBlock(
            block_id="block-4",
            block_type=BlockType.UNKNOWN,
            text_content="Some unknown content block.",
            page_number=12,
            char_start=0,
            char_end=50,
        ),
    ]


# =============================================================================
# EVIDENCE SPAN CREATION TESTS
# =============================================================================

class TestEvidenceSpanCreation:
    """Tests for _create_evidence_spans method."""
    
    def test_subheading_maps_to_heading(self, unit_generator):
        """Test that SUBHEADING block type maps to 'heading'."""
        blocks = [
            ContentBlock(
                block_id="test-sub",
                block_type=BlockType.SUBHEADING,
                text_content="Test Subheading",
                page_number=1,
                char_start=0,
                char_end=100,
            )
        ]
        
        spans = unit_generator._create_evidence_spans(blocks, doc_id="test-doc")
        
        assert len(spans) == 1
        assert spans[0].block_type == "heading"
    
    def test_heading_maps_to_heading(self, unit_generator):
        """Test that HEADING block type maps to 'heading'."""
        blocks = [
            ContentBlock(
                block_id="test-head",
                block_type=BlockType.HEADING,
                text_content="Test Heading",
                page_number=1,
                char_start=0,
                char_end=100,
            )
        ]
        
        spans = unit_generator._create_evidence_spans(blocks, doc_id="test-doc")
        
        assert len(spans) == 1
        assert spans[0].block_type == "heading"
    
    def test_explanatory_prose_maps_to_prose(self, unit_generator):
        """Test that EXPLANATORY_PROSE block type maps to 'prose'."""
        blocks = [
            ContentBlock(
                block_id="test-prose",
                block_type=BlockType.EXPLANATORY_PROSE,
                text_content="This is explanatory text about SQL.",
                page_number=2,
                char_start=0,
                char_end=100,
            )
        ]
        
        spans = unit_generator._create_evidence_spans(blocks, doc_id="test-doc")
        
        assert len(spans) == 1
        assert spans[0].block_type == "prose"
    
    def test_sidebar_maps_to_prose(self, unit_generator):
        """Test that SIDEBAR block type maps to 'prose'."""
        blocks = [
            ContentBlock(
                block_id="test-sidebar",
                block_type=BlockType.SIDEBAR,
                text_content="Sidebar note about SQL syntax.",
                page_number=2,
                char_start=0,
                char_end=100,
            )
        ]
        
        spans = unit_generator._create_evidence_spans(blocks, doc_id="test-doc")
        
        assert len(spans) == 1
        assert spans[0].block_type == "prose"
    
    def test_sql_code_maps_to_code(self, unit_generator):
        """Test that SQL_CODE block type maps to 'code'."""
        blocks = [
            ContentBlock(
                block_id="test-code",
                block_type=BlockType.SQL_CODE,
                text_content="SELECT * FROM users;",
                page_number=3,
                char_start=0,
                char_end=100,
            )
        ]
        
        spans = unit_generator._create_evidence_spans(blocks, doc_id="test-doc")
        
        assert len(spans) == 1
        assert spans[0].block_type == "code"
    
    def test_output_table_maps_to_table(self, unit_generator):
        """Test that OUTPUT_TABLE block type maps to 'table'."""
        blocks = [
            ContentBlock(
                block_id="test-table",
                block_type=BlockType.OUTPUT_TABLE,
                text_content="| id | name |",
                page_number=4,
                char_start=0,
                char_end=100,
            )
        ]
        
        spans = unit_generator._create_evidence_spans(blocks, doc_id="test-doc")
        
        assert len(spans) == 1
        assert spans[0].block_type == "table"
    
    def test_figure_maps_to_figure(self, unit_generator):
        """Test that FIGURE block type maps to 'figure'."""
        blocks = [
            ContentBlock(
                block_id="test-figure",
                block_type=BlockType.FIGURE,
                text_content="Figure: Database Schema Diagram",
                page_number=5,
                char_start=0,
                char_end=100,
            )
        ]
        
        spans = unit_generator._create_evidence_spans(blocks, doc_id="test-doc")
        
        assert len(spans) == 1
        assert spans[0].block_type == "figure"
    
    def test_diagram_maps_to_figure(self, unit_generator):
        """Test that DIAGRAM block type maps to 'figure'."""
        blocks = [
            ContentBlock(
                block_id="test-diagram",
                block_type=BlockType.DIAGRAM,
                text_content="Diagram: JOIN visualization",
                page_number=5,
                char_start=0,
                char_end=100,
            )
        ]
        
        spans = unit_generator._create_evidence_spans(blocks, doc_id="test-doc")
        
        assert len(spans) == 1
        assert spans[0].block_type == "figure"
    
    def test_exercise_maps_to_exercise(self, unit_generator):
        """Test that EXERCISE block type maps to 'exercise'."""
        blocks = [
            ContentBlock(
                block_id="test-exercise",
                block_type=BlockType.EXERCISE,
                text_content="Practice Problem: Write a JOIN query...",
                page_number=6,
                char_start=0,
                char_end=100,
            )
        ]
        
        spans = unit_generator._create_evidence_spans(blocks, doc_id="test-doc")
        
        assert len(spans) == 1
        assert spans[0].block_type == "exercise"
    
    def test_summary_maps_to_summary(self, unit_generator):
        """Test that SUMMARY block type maps to 'summary'."""
        blocks = [
            ContentBlock(
                block_id="test-summary",
                block_type=BlockType.SUMMARY,
                text_content="Summary of JOIN concepts.",
                page_number=7,
                char_start=0,
                char_end=100,
            )
        ]
        
        spans = unit_generator._create_evidence_spans(blocks, doc_id="test-doc")
        
        assert len(spans) == 1
        assert spans[0].block_type == "summary"
    
    def test_glossary_maps_to_summary(self, unit_generator):
        """Test that GLOSSARY block type maps to 'summary'."""
        blocks = [
            ContentBlock(
                block_id="test-glossary",
                block_type=BlockType.GLOSSARY,
                text_content="Glossary: JOIN - combines tables",
                page_number=7,
                char_start=0,
                char_end=100,
            )
        ]
        
        spans = unit_generator._create_evidence_spans(blocks, doc_id="test-doc")
        
        assert len(spans) == 1
        assert spans[0].block_type == "summary"
    
    def test_admin_text_maps_to_admin(self, unit_generator):
        """Test that ADMIN_TEXT block type maps to 'admin'."""
        blocks = [
            ContentBlock(
                block_id="test-admin",
                block_type=BlockType.ADMIN_TEXT,
                text_content="Table of Contents",
                page_number=1,
                char_start=0,
                char_end=100,
            )
        ]
        
        spans = unit_generator._create_evidence_spans(blocks, doc_id="test-doc")
        
        assert len(spans) == 1
        assert spans[0].block_type == "admin"
    
    def test_unknown_maps_to_prose(self, unit_generator):
        """Test that UNKNOWN block type maps to 'prose' (default)."""
        blocks = [
            ContentBlock(
                block_id="test-unknown",
                block_type=BlockType.UNKNOWN,
                text_content="Unknown content type.",
                page_number=8,
                char_start=0,
                char_end=100,
            )
        ]
        
        spans = unit_generator._create_evidence_spans(blocks, doc_id="test-doc")
        
        assert len(spans) == 1
        assert spans[0].block_type == "prose"
    
    def test_all_block_types_validate_cleanly(self, unit_generator):
        """Test that all mapped block types produce valid SourceSpans.
        
        This is the main regression test that verifies the fix for the evidence-span
        block type mapping issue. It builds spans from SUBHEADING, EXPLANATORY_PROSE,
        and SQL_CODE (representative examples) and confirms all emitted SourceSpans
        validate cleanly.
        """
        blocks = [
            ContentBlock(
                block_id="block-subheading",
                block_type=BlockType.SUBHEADING,
                text_content="Section: SQL Basics",
                page_number=10,
                char_start=0,
                char_end=100,
            ),
            ContentBlock(
                block_id="block-prose",
                block_type=BlockType.EXPLANATORY_PROSE,
                text_content="SQL is a language for managing relational databases.",
                page_number=10,
                char_start=101,
                char_end=300,
            ),
            ContentBlock(
                block_id="block-code",
                block_type=BlockType.SQL_CODE,
                text_content="SELECT name FROM users WHERE id = 1;",
                page_number=11,
                char_start=0,
                char_end=100,
            ),
        ]
        
        spans = unit_generator._create_evidence_spans(blocks, doc_id="test-textbook")
        
        # Verify we got all spans
        assert len(spans) == 3
        
        # Verify all block types are canonical
        assert spans[0].block_type == "heading"
        assert spans[1].block_type == "prose"
        assert spans[2].block_type == "code"
        
        # Verify all spans are valid SourceSpan instances
        # This would fail before the fix with non-canonical values like "subheading"
        for span in spans:
            # Re-validate by serializing and deserializing
            span_dict = span.model_dump()
            revalidated = SourceSpan.model_validate(span_dict)
            assert revalidated.block_type == span.block_type
    
    def test_string_block_type_normalization(self, unit_generator):
        """Test that string block types are also normalized correctly."""
        # Create a mock block with string block_type
        class MockBlock:
            block_id = "mock-1"
            block_type = "SUBHEADING"  # String type
            text_content = "Mock subheading"
            page_number = 1
        
        spans = unit_generator._create_evidence_spans([MockBlock()], doc_id="test")
        
        assert len(spans) == 1
        assert spans[0].block_type == "heading"
    
    def test_string_block_type_sql_code_normalization(self, unit_generator):
        """Test that 'sql_code' string block type normalizes to 'code'."""
        class MockBlock:
            block_id = "mock-2"
            block_type = "sql_code"  # String type (non-canonical)
            text_content = "SELECT 1;"
            page_number = 2
        
        spans = unit_generator._create_evidence_spans([MockBlock()], doc_id="test")
        
        assert len(spans) == 1
        assert spans[0].block_type == "code"
    
    def test_string_block_type_explanatory_prose_normalization(self, unit_generator):
        """Test that 'explanatory_prose' string block type normalizes to 'prose'."""
        class MockBlock:
            block_id = "mock-3"
            block_type = "explanatory_prose"  # String type (non-canonical)
            text_content = "Some explanation"
            page_number = 3
        
        spans = unit_generator._create_evidence_spans([MockBlock()], doc_id="test")
        
        assert len(spans) == 1
        assert spans[0].block_type == "prose"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
