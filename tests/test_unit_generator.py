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


# =============================================================================
# SQL EXTRACTION AND VALIDATION TESTS (Week 1 Demo Regression Tests)
# =============================================================================

class TestSQLExtractionValidation:
    """Regression tests for SQL example extraction and validation.
    
    These tests verify that:
    - Contaminated SQL examples are rejected
    - Valid multi-line SQL is retained
    - Concept-fit validation works correctly for Week 1 concepts
    """
    
    def test_reject_prose_contaminated_select(self, unit_generator):
        """Reject SELECT statements with prose like 'for retrieving'."""
        contaminated = [
            "SELECT for retrieving data from tables",
            "SELECT * FROM users This retrieves all users",
            "WHERE for filtering rows by condition",
        ]
        
        for sql in contaminated:
            is_valid, reason = unit_generator._is_valid_sql_lenient(sql)
            assert not is_valid, f"Should reject contaminated SQL: {sql[:40]}..."
            assert 'prose' in reason.lower() or 'keyword' in reason.lower(), \
                f"Rejection reason should indicate prose: {reason}"
    
    def test_reject_keyword_for_verb_pattern(self, unit_generator):
        """Reject SQL that starts with keyword followed by 'for' + verb."""
        contaminated = [
            "SELECT for retrieving all columns",
            "WHERE for filtering data",
            "JOIN for combining tables",
            "GROUP BY for aggregating results",
        ]
        
        for sql in contaminated:
            is_valid, reason = unit_generator._is_valid_sql_lenient(sql)
            assert not is_valid, f"Should reject keyword+for+verb: {sql[:40]}..."
    
    def test_reject_trailing_prose_after_semicolon(self, unit_generator):
        """Reject SQL with trailing prose after semicolon."""
        contaminated = [
            "SELECT * FROM users; This retrieves all users",
            "SELECT name FROM employees; Returns employee names",
        ]
        
        for sql in contaminated:
            is_valid, reason = unit_generator._is_valid_sql_lenient(sql)
            assert not is_valid, f"Should reject trailing prose: {sql[:40]}..."
    
    def test_reject_prose_first_word(self, unit_generator):
        """Reject SQL where first word after keyword is prose."""
        contaminated = [
            "SELECT returns all columns from table",
            "SELECT this is an example query",
            "WHERE the condition is met",
        ]
        
        for sql in contaminated:
            is_valid, reason = unit_generator._is_valid_sql_lenient(sql)
            assert not is_valid, f"Should reject prose first word: {sql[:40]}..."
    
    def test_accept_valid_multi_line_sql(self, unit_generator):
        """Accept valid multi-line SQL statements."""
        valid_sql = [
            "SELECT u.name, o.product FROM users u JOIN orders o ON u.id = o.user_id;",
            "SELECT department, AVG(salary) FROM employees GROUP BY department HAVING COUNT(*) > 5;",
            "SELECT name FROM customers WHERE city = 'Seattle' AND status = 'active';",
            "SELECT DISTINCT category FROM products ORDER BY category ASC;",
        ]
        
        for sql in valid_sql:
            is_valid, reason = unit_generator._is_valid_sql_lenient(sql)
            assert is_valid, f"Should accept valid SQL: {sql[:40]}... (reason: {reason})"
    
    def test_concept_fit_rejects_mismatched_sql(self, unit_generator):
        """Concept-fit validation should reject mismatched SQL for concepts."""
        # These SQL statements don't match the concept they claim to demonstrate
        mismatched = [
            ("outer-join", "SELECT * FROM users JOIN orders ON users.id = orders.user_id;"),  # INNER JOIN for outer-join
            ("inner-join", "SELECT * FROM users LEFT JOIN orders ON users.id = orders.user_id;"),  # LEFT JOIN for inner-join
            ("group-by", "SELECT * FROM users;"),  # No GROUP BY
            ("distinct", "SELECT name FROM users;"),  # No DISTINCT
            ("where-clause", "SELECT * FROM users;"),  # No WHERE
            ("order-by", "SELECT * FROM users;"),  # No ORDER BY
        ]
        
        for concept_id, sql in mismatched:
            is_valid, reason = unit_generator._validate_concept_fit(sql, concept_id)
            assert not is_valid, f"Should reject '{sql[:40]}...' for concept '{concept_id}'"
    
    def test_concept_fit_accepts_correct_sql(self, unit_generator):
        """Concept-fit validation should accept SQL that matches concept."""
        matched = [
            ("outer-join", "SELECT * FROM users LEFT JOIN orders ON users.id = orders.user_id;"),
            ("inner-join", "SELECT * FROM users INNER JOIN orders ON users.id = orders.user_id;"),
            ("group-by", "SELECT department, COUNT(*) FROM employees GROUP BY department;"),
            ("distinct", "SELECT DISTINCT city FROM customers;"),
            ("where-clause", "SELECT * FROM users WHERE age > 25;"),
            ("order-by", "SELECT * FROM products ORDER BY price DESC;"),
        ]
        
        for concept_id, sql in matched:
            is_valid, reason = unit_generator._validate_concept_fit(sql, concept_id)
            assert is_valid, f"Should accept '{sql[:40]}...' for concept '{concept_id}' (reason: {reason})"
    
    def test_strip_prose_preserves_valid_sql(self, unit_generator):
        """Prose stripping should preserve valid SQL without contamination."""
        valid_sql = [
            "SELECT * FROM users WHERE status = 'active';",
            "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id;",
            "SELECT department, AVG(salary) as avg_sal FROM employees GROUP BY department;",
        ]
        
        for sql in valid_sql:
            result = unit_generator._strip_prose_from_sql(sql)
            # Result should be very similar to input (maybe whitespace changes)
            assert 'SELECT' in result, f"Should preserve SELECT: {result}"
            assert 'FROM' in result, f"Should preserve FROM: {result}"
            assert result.endswith(';'), f"Should end with semicolon: {result}"
    
    def test_strip_prose_removes_contamination(self, unit_generator):
        """Prose stripping should remove trailing prose contamination."""
        contaminated_pairs = [
            ("SELECT * FROM users This retrieves all users", "SELECT * FROM users;"),
            ("SELECT name FROM employees; Returns employee names", "SELECT name FROM employees;"),
        ]
        
        for contaminated, expected in contaminated_pairs:
            result = unit_generator._strip_prose_from_sql(contaminated)
            assert 'This retrieves' not in result, f"Should strip 'This retrieves': {result}"
            assert 'Returns employee' not in result, f"Should strip 'Returns employee': {result}"
    
    def test_week1_concepts_sql_validation(self, unit_generator):
        """Test SQL validation for key Week 1 demo concepts with strict validation."""
        # Concepts that have strict structure requirements
        strict_concepts = [
            ("where-clause", "SELECT * FROM users;", False),  # Should reject - no WHERE
            ("where-clause", "SELECT * FROM users WHERE age > 25;", True),  # Should accept
            ("order-by", "SELECT * FROM users;", False),  # Should reject - no ORDER BY
            ("order-by", "SELECT * FROM users ORDER BY name;", True),  # Should accept
            ("distinct", "SELECT * FROM users;", False),  # Should reject - no DISTINCT
            ("distinct", "SELECT DISTINCT city FROM users;", True),  # Should accept
            ("inner-join", "SELECT * FROM users;", False),  # Should reject - no JOIN
            ("inner-join", "SELECT * FROM users JOIN orders ON users.id = orders.user_id;", True),
            ("outer-join", "SELECT * FROM users JOIN orders ON users.id = orders.user_id;", False),  # INNER JOIN for outer
            ("outer-join", "SELECT * FROM users LEFT JOIN orders ON users.id = orders.user_id;", True),
        ]
        
        for concept, sql, expected_valid in strict_concepts:
            is_valid, reason = unit_generator._validate_concept_fit(sql, concept)
            if expected_valid:
                assert is_valid, f"Concept '{concept}' should accept '{sql[:40]}...' (reason: {reason})"
            else:
                assert not is_valid, f"Concept '{concept}' should reject '{sql[:40]}...'"


class TestProseFragmentRejection:
    """Tests for prose fragment rejection in SQL validation."""
    
    def test_reject_alter_table_can_be_used(self, unit_generator):
        """Reject 'ALTER TABLE can be used' prose fragment."""
        is_valid, reason = unit_generator._is_valid_sql_lenient(
            "ALTER TABLE can be used;"
        )
        assert not is_valid, "Should reject modal verb fragment"
        assert "modal" in reason.lower() or "prose" in reason.lower(), f"Expected modal/prose reason, got: {reason}"
    
    def test_reject_alter_table_can_also_be_used(self, unit_generator):
        """Reject 'ALTER TABLE can also be used' prose fragment."""
        is_valid, reason = unit_generator._is_valid_sql_lenient(
            "ALTER TABLE can also be used;"
        )
        assert not is_valid, "Should reject modal verb fragment with 'also'"
        assert "modal" in reason.lower() or "prose" in reason.lower(), f"Expected modal/prose reason, got: {reason}"
    
    def test_reject_drop_table_command(self, unit_generator):
        """Reject 'DROP TABLE command' noun phrase fragment."""
        is_valid, reason = unit_generator._is_valid_sql_lenient(
            "DROP TABLE command.;"
        )
        assert not is_valid, "Should reject noun phrase fragment"
        assert "noun" in reason.lower() or "prose" in reason.lower() or "fragment" in reason.lower(), f"Expected noun/fragment reason, got: {reason}"
    
    def test_reject_create_table_statement(self, unit_generator):
        """Reject 'CREATE TABLE statement' noun phrase fragment."""
        is_valid, reason = unit_generator._is_valid_sql_lenient(
            "CREATE TABLE statement;"
        )
        assert not is_valid, "Should reject noun phrase fragment"
        assert "noun" in reason.lower() or "prose" in reason.lower() or "fragment" in reason.lower(), f"Expected noun/fragment reason, got: {reason}"
    
    def test_reject_with_null_values(self, unit_generator):
        """Reject 'with null values' prepositional fragment."""
        is_valid, reason = unit_generator._is_valid_sql_lenient(
            "with null values;"
        )
        assert not is_valid, "Should reject prepositional fragment"
        assert "prepositional" in reason.lower() or "prose" in reason.lower() or "fragment" in reason.lower(), f"Expected prepositional reason, got: {reason}"
    
    def test_reject_with_special_attention(self, unit_generator):
        """Reject 'with special attention' prose fragment."""
        is_valid, reason = unit_generator._is_valid_sql_lenient(
            "with special attention paid to high frequency values, so;"
        )
        assert not is_valid, "Should reject adjectival fragment"
        assert "prepositional" in reason.lower() or "prose" in reason.lower() or "fragment" in reason.lower(), f"Expected fragment reason, got: {reason}"
    
    def test_accept_valid_alter_table(self, unit_generator):
        """Accept valid ALTER TABLE statement."""
        is_valid, reason = unit_generator._is_valid_sql_lenient(
            "ALTER TABLE employees ADD COLUMN email VARCHAR(100);"
        )
        assert is_valid, f"Should accept valid ALTER TABLE, got: {reason}"
    
    def test_accept_valid_drop_table(self, unit_generator):
        """Accept valid DROP TABLE statement."""
        is_valid, reason = unit_generator._is_valid_sql_lenient(
            "DROP TABLE IF EXISTS temp_data;"
        )
        assert is_valid, f"Should accept valid DROP TABLE, got: {reason}"
    
    def test_accept_valid_create_table(self, unit_generator):
        """Accept valid CREATE TABLE statement."""
        is_valid, reason = unit_generator._is_valid_sql_lenient(
            "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(50));"
        )
        assert is_valid, f"Should accept valid CREATE TABLE, got: {reason}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
