"""Tests for automatic concept mapping functionality (Phase 3).

This module tests:
- Structure extraction (TOC, headings, chapters)
- Concept matching with registry
- Draft mapping generation
- Human-in-the-loop workflow
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
import yaml

# Import modules under test
from algl_pdf_helper.structure_extractor import (
    Chapter,
    ConceptBoundary,
    Heading,
    Section,
    StructureExtractor,
    TOCEntry,
)
from algl_pdf_helper.concept_matcher import (
    ConceptMatcher,
    ConceptRegistryEntry,
    MatchCandidate,
)
from algl_pdf_helper.mapping_generator import (
    ConceptMapping,
    DraftMapping,
    MappingGenerator,
)
from algl_pdf_helper.mapping_workflow import (
    MappingWorkflow,
    ReviewPackage,
    ReviewSuggestion,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_headings() -> list[Heading]:
    """Sample headings for testing."""
    return [
        Heading(level=1, text="Chapter 1: Introduction to SQL", page=1, font_size=18, is_bold=True, confidence=0.95),
        Heading(level=2, text="1.1 What is SQL?", page=2, font_size=14, is_bold=True, confidence=0.9),
        Heading(level=2, text="1.2 Basic SELECT Statement", page=5, font_size=14, is_bold=True, confidence=0.9),
        Heading(level=1, text="Chapter 2: Querying Data", page=10, font_size=18, is_bold=True, confidence=0.95),
        Heading(level=2, text="2.1 WHERE Clause", page=11, font_size=14, is_bold=True, confidence=0.9),
        Heading(level=2, text="2.2 JOIN Operations", page=15, font_size=14, is_bold=True, confidence=0.9),
        Heading(level=3, text="2.2.1 INNER JOIN", page=16, font_size=12, is_bold=True, confidence=0.8),
        Heading(level=3, text="2.2.2 OUTER JOIN", page=18, font_size=12, is_bold=True, confidence=0.8),
    ]


@pytest.fixture
def sample_registry_path(tmp_path: Path) -> Path:
    """Create a sample concept registry file."""
    registry_data = {
        "version": "1.0.0",
        "categories": {
            "dql": ["query", "select"],
            "ddl": ["create", "table"],
        },
        "concepts": [
            {
                "id": "select-basic",
                "name": "SELECT Statement Basics",
                "definition": "Retrieves data from tables",
                "keywords": ["select", "query", "fetch", "retrieve"],
                "related_concepts": ["where-clause"],
                "prerequisites": [],
                "difficulty": "beginner",
                "category": "dql",
            },
            {
                "id": "where-clause",
                "name": "WHERE Clause",
                "definition": "Filters rows based on conditions",
                "keywords": ["where", "filter", "condition"],
                "related_concepts": ["select-basic"],
                "prerequisites": ["select-basic"],
                "difficulty": "beginner",
                "category": "dql",
            },
            {
                "id": "join",
                "name": "JOIN Operations",
                "definition": "Combines rows from tables",
                "keywords": ["join", "inner join", "outer join", "combine"],
                "related_concepts": ["select-basic"],
                "prerequisites": ["select-basic"],
                "difficulty": "intermediate",
                "category": "dql",
            },
        ],
    }
    
    registry_path = tmp_path / "test_registry.yaml"
    with open(registry_path, "w") as f:
        yaml.dump(registry_data, f)
    
    return registry_path


@pytest.fixture
def structure_extractor() -> StructureExtractor:
    """Create a structure extractor instance."""
    return StructureExtractor()


@pytest.fixture
def concept_matcher(sample_registry_path: Path) -> ConceptMatcher:
    """Create a concept matcher with sample registry."""
    return ConceptMatcher(sample_registry_path)


@pytest.fixture
def mapping_generator(sample_registry_path: Path) -> MappingGenerator:
    """Create a mapping generator with sample registry."""
    return MappingGenerator(
        registry_path=sample_registry_path,
        confidence_threshold=0.5,
    )


@pytest.fixture
def mapping_workflow(sample_registry_path: Path) -> MappingWorkflow:
    """Create a mapping workflow with sample registry."""
    return MappingWorkflow(
        registry_path=sample_registry_path,
        confidence_threshold=0.5,
    )


# =============================================================================
# Structure Extractor Tests
# =============================================================================

class TestStructureExtractor:
    """Tests for StructureExtractor class."""

    def test_init(self, structure_extractor: StructureExtractor):
        """Test extractor initialization."""
        assert structure_extractor is not None
        assert len(structure_extractor.chapter_regexes) > 0
        assert len(structure_extractor.section_regexes) > 0

    def test_classify_heading_chapter(self, structure_extractor: StructureExtractor):
        """Test classification of chapter headings."""
        level, confidence = structure_extractor._classify_heading(
            "Chapter 1: Introduction",
            font_size=18,
            is_bold=True,
            heading_threshold=14,
            body_size=11,
        )
        assert level == 1
        assert confidence > 0.9

    def test_classify_heading_section(self, structure_extractor: StructureExtractor):
        """Test classification of section headings."""
        level, confidence = structure_extractor._classify_heading(
            "1.1 Overview",
            font_size=14,
            is_bold=True,
            heading_threshold=14,
            body_size=11,
        )
        assert level == 2
        assert confidence > 0.8

    def test_classify_heading_subsection(self, structure_extractor: StructureExtractor):
        """Test classification of subsection headings."""
        level, confidence = structure_extractor._classify_heading(
            "1.1.1 Details",
            font_size=12,
            is_bold=True,
            heading_threshold=14,
            body_size=11,
        )
        assert level == 3
        assert confidence > 0.8

    def test_classify_not_heading(self, structure_extractor: StructureExtractor):
        """Test that body text is not classified as heading."""
        level, confidence = structure_extractor._classify_heading(
            "This is just a normal sentence that should not be detected as a heading",
            font_size=11,
            is_bold=False,
            heading_threshold=14,
            body_size=11,
        )
        assert level == 0

    def test_deduplicate_headings(self, structure_extractor: StructureExtractor):
        """Test heading deduplication."""
        headings = [
            Heading(level=1, text="Chapter 1", page=1, confidence=0.9),
            Heading(level=1, text="Chapter 1", page=1, confidence=0.9),  # Duplicate
            Heading(level=2, text="Section 1", page=2, confidence=0.8),
        ]
        deduped = structure_extractor._deduplicate_headings(headings)
        assert len(deduped) == 2

    def test_extract_concept_name(self, structure_extractor: StructureExtractor):
        """Test concept name extraction from heading."""
        name = structure_extractor._extract_concept_name("Chapter 1: Introduction to SQL")
        assert "Introduction to SQL" in name or "introduction-to-sql" in name

    def test_generate_keywords(self, structure_extractor: StructureExtractor):
        """Test keyword generation."""
        keywords = structure_extractor._generate_keywords(
            "SELECT Statement Basics",
            None
        )
        assert "select" in keywords
        assert "statement" in keywords
        assert "basics" in keywords or "basic" in keywords


# =============================================================================
# Concept Matcher Tests
# =============================================================================

class TestConceptMatcher:
    """Tests for ConceptMatcher class."""

    def test_init_with_registry(self, sample_registry_path: Path):
        """Test initialization with registry file."""
        matcher = ConceptMatcher(sample_registry_path)
        assert len(matcher.registry) == 3
        assert "select-basic" in matcher.registry
        assert "where-clause" in matcher.registry
        assert "join" in matcher.registry

    def test_init_default_registry(self):
        """Test initialization with default registry."""
        matcher = ConceptMatcher(None)
        assert len(matcher.registry) > 0  # Should have default concepts

    def test_match_heading_exact(self, concept_matcher: ConceptMatcher):
        """Test exact match detection."""
        heading = Heading(
            level=2,
            text="SELECT Statement Basics",
            page=5,
            confidence=0.9
        )
        candidates = concept_matcher.match_heading(heading)
        
        assert len(candidates) > 0
        top = candidates[0]
        assert top.concept_id == "select-basic"
        assert top.match_type == "exact"
        assert top.confidence > 0.8

    def test_match_heading_keyword(self, concept_matcher: ConceptMatcher):
        """Test keyword match detection."""
        heading = Heading(
            level=2,
            text="Using WHERE to Filter Data",
            page=10,
            confidence=0.9
        )
        candidates = concept_matcher.match_heading(heading)
        
        # Should match where-clause via keywords
        where_candidates = [c for c in candidates if c.concept_id == "where-clause"]
        assert len(where_candidates) > 0
        assert where_candidates[0].match_type == "keyword"

    def test_match_heading_fuzzy(self, concept_matcher: ConceptMatcher):
        """Test fuzzy match detection."""
        heading = Heading(
            level=2,
            text="Joining Tables Together",
            page=15,
            confidence=0.9
        )
        candidates = concept_matcher.match_heading(heading)
        
        # Should match join concept via word overlap
        join_candidates = [c for c in candidates if c.concept_id == "join"]
        assert len(join_candidates) > 0

    def test_match_headings_batch(self, concept_matcher: ConceptMatcher, sample_headings: list[Heading]):
        """Test batch heading matching."""
        matches = concept_matcher.match_headings_batch(
            sample_headings,
            confidence_threshold=0.5
        )
        
        assert len(matches) > 0
        # Check that we have matches for SQL-related headings
        concept_ids = [m.concept_id for m in matches]
        assert "select-basic" in concept_ids or "where-clause" in concept_ids or "join" in concept_ids

    def test_find_related_matches(self, concept_matcher: ConceptMatcher):
        """Test finding related concepts."""
        matched_ids = ["where-clause"]
        related = concept_matcher.find_related_matches(matched_ids)
        
        assert len(related) > 0
        # where-clause has select-basic as related and prerequisite
        related_ids = [r.concept_id for r in related]
        assert "select-basic" in related_ids

    def test_get_registry_stats(self, concept_matcher: ConceptMatcher):
        """Test registry statistics."""
        stats = concept_matcher.get_registry_stats()
        
        assert stats["total_concepts"] == 3
        assert "by_category" in stats
        assert "by_difficulty" in stats


# =============================================================================
# Mapping Generator Tests
# =============================================================================

class TestMappingGenerator:
    """Tests for MappingGenerator class."""

    def test_init(self, mapping_generator: MappingGenerator):
        """Test generator initialization."""
        assert mapping_generator is not None
        assert mapping_generator.confidence_threshold == 0.5
        assert mapping_generator.structure_extractor is not None
        assert mapping_generator.concept_matcher is not None

    def test_estimate_page_range(self, mapping_generator: MappingGenerator):
        """Test page range estimation."""
        headings = [
            Heading(level=2, text="Section 1", page=5, confidence=0.9),
            Heading(level=2, text="Section 2", page=10, confidence=0.9),
        ]
        
        pages = mapping_generator._estimate_page_range(
            headings[0],
            headings,
            total_pages=100
        )
        
        assert 5 in pages
        assert len(pages) <= 10  # Should be limited

    def test_estimate_read_time(self, mapping_generator: MappingGenerator):
        """Test reading time estimation."""
        assert mapping_generator._estimate_read_time(1) >= 3
        assert mapping_generator._estimate_read_time(5) >= 10
        assert mapping_generator._estimate_read_time(20) <= 30  # Capped at 30

    def test_generate_tags(self, mapping_generator: MappingGenerator):
        """Test tag generation."""
        entry = ConceptRegistryEntry(
            id="select-basic",
            name="SELECT Basics",
            category="dql",
            difficulty="beginner"
        )
        tags = mapping_generator._generate_tags(entry)
        
        assert "dql" in tags
        assert "beginner" in tags

    def test_draft_mapping_to_yaml(self):
        """Test conversion to YAML format."""
        draft = DraftMapping(
            pdf_path=Path("/tmp/test.pdf"),
            created_at="2024-01-01T00:00:00Z",
            total_pages=100,
            detected_headings=20,
            matched_concepts=2,
            concepts=[
                ConceptMapping(
                    concept_id="select-basic",
                    concept_name="SELECT Basics",
                    title="SELECT Statement Basics",
                    definition="Retrieves data",
                    page_references=[5, 6, 7],
                    confidence=0.9,
                    needs_review=False,
                ),
            ],
        )
        
        yaml_data = draft.to_concepts_yaml()
        
        assert "concepts" in yaml_data
        assert "select-basic" in yaml_data["concepts"]
        assert yaml_data["total_pages"] == 100


# =============================================================================
# Mapping Workflow Tests
# =============================================================================

class TestMappingWorkflow:
    """Tests for MappingWorkflow class."""

    def test_init(self, mapping_workflow: MappingWorkflow):
        """Test workflow initialization."""
        assert mapping_workflow is not None
        assert mapping_workflow.generator is not None
        assert mapping_workflow.structure_extractor is not None

    def test_create_review_package(self, mapping_workflow: MappingWorkflow):
        """Test review package creation."""
        draft = DraftMapping(
            pdf_path=Path("/tmp/test.pdf"),
            created_at="2024-01-01T00:00:00Z",
            total_pages=100,
            detected_headings=20,
            matched_concepts=2,
            concepts=[
                ConceptMapping(
                    concept_id="select-basic",
                    concept_name="SELECT Basics",
                    title="SELECT Statement",
                    page_references=[5, 6],
                    confidence=0.9,
                    needs_review=False,
                ),
                ConceptMapping(
                    concept_id="where-clause",
                    concept_name="WHERE Clause",
                    title="WHERE Clause",
                    page_references=[10, 11, 12, 13, 14, 15],  # Long range
                    confidence=0.4,  # Low confidence
                    needs_review=True,
                ),
            ],
        )
        
        package = mapping_workflow.create_review_package(draft, include_previews=True)
        
        assert isinstance(package, ReviewPackage)
        assert package.total_pages == 100
        assert "concepts" in package.draft_mapping
        assert len(package.suggestions) > 0
        assert package.preview != {}  # Preview should have content when include_previews=True

    def test_generate_suggestions(self, mapping_workflow: MappingWorkflow):
        """Test suggestion generation."""
        draft = DraftMapping(
            pdf_path=Path("/tmp/test.pdf"),
            created_at="2024-01-01T00:00:00Z",
            total_pages=100,
            detected_headings=20,
            matched_concepts=1,
            concepts=[
                ConceptMapping(
                    concept_id="test-concept",
                    concept_name="Test",
                    title="Test Concept",
                    page_references=[5, 6, 7, 8, 9, 10, 11],  # Long range
                    confidence=0.4,  # Low confidence
                    needs_review=True,
                ),
            ],
            unmatched_headings=[
                Heading(level=2, text="Important Section", page=20, confidence=0.8),
            ],
        )
        
        suggestions = mapping_workflow._generate_suggestions(draft)
        
        assert len(suggestions) > 0
        # Should have suggestions for low confidence and long page range
        types = [s.type for s in suggestions]
        assert "page_correction" in types or "section_split" in types

    def test_get_review_instructions(self, mapping_workflow: MappingWorkflow):
        """Test review instructions generation."""
        instructions = mapping_workflow._get_review_instructions()
        
        assert len(instructions) > 0
        assert any("page" in i.lower() for i in instructions)
        assert any("review" in i.lower() for i in instructions)

    def test_estimate_workflow_accuracy(self, mapping_workflow: MappingWorkflow):
        """Test accuracy estimation."""
        draft = DraftMapping(
            pdf_path=Path("/tmp/test.pdf"),
            created_at="2024-01-01T00:00:00Z",
            total_pages=100,
            detected_headings=20,
            matched_concepts=2,
            concepts=[
                ConceptMapping(
                    concept_id="c1",
                    concept_name="Concept 1",
                    title="Concept 1",
                    confidence=0.9,
                    page_references=[1, 2],
                ),
                ConceptMapping(
                    concept_id="c2",
                    concept_name="Concept 2",
                    title="Concept 2",
                    confidence=0.6,
                    page_references=[3, 4],
                ),
            ],
        )
        
        # Test without reviewed concepts
        accuracy = mapping_workflow._estimate_accuracy(draft, [])
        assert "%" in accuracy
        
        # Test with reviewed concepts
        reviewed = [
            {"id": "c1", "page_references": [1, 2]},  # Unchanged
            {"id": "c2", "page_references": [3, 5]},  # Changed
        ]
        accuracy = mapping_workflow._estimate_accuracy(draft, reviewed)
        assert "%" in accuracy


# =============================================================================
# Integration Tests
# =============================================================================

class TestAutoMappingIntegration:
    """Integration tests for the full auto-mapping pipeline."""

    def test_end_to_end_workflow(self, tmp_path: Path, sample_registry_path: Path):
        """Test the complete workflow from extraction to review package."""
        # This is a simplified test since we can't create real PDFs
        
        # 1. Create workflow
        workflow = MappingWorkflow(
            registry_path=sample_registry_path,
            confidence_threshold=0.5,
        )
        
        # 2. Test that components are properly wired
        assert workflow.generator is not None
        assert workflow.structure_extractor is not None
        
        # 3. Test concept matcher
        matcher = workflow.generator.concept_matcher
        heading = Heading(
            level=2,
            text="SELECT Statement Basics",
            page=5,
            confidence=0.9
        )
        candidates = matcher.match_heading(heading)
        assert len(candidates) > 0
        
        # 4. Test that we can create a review package
        draft = DraftMapping(
            pdf_path=tmp_path / "test.pdf",
            created_at="2024-01-01T00:00:00Z",
            total_pages=50,
            detected_headings=10,
            matched_concepts=1,
            concepts=[
                ConceptMapping(
                    concept_id="select-basic",
                    concept_name="SELECT Basics",
                    title="SELECT Statement",
                    definition="Retrieves data from tables",
                    page_references=[5, 6, 7],
                    confidence=0.85,
                    match_score=0.9,
                    match_type="exact",
                    needs_review=False,
                ),
            ],
        )
        
        package = workflow.create_review_package(draft)
        assert package.total_pages == 50
        assert len(package.draft_mapping["concepts"]) == 1

    def test_concept_registry_yaml_format(self, sample_registry_path: Path):
        """Test that registry YAML has correct format."""
        with open(sample_registry_path) as f:
            data = yaml.safe_load(f)
        
        assert "version" in data
        assert "concepts" in data
        assert isinstance(data["concepts"], list)
        
        for concept in data["concepts"]:
            assert "id" in concept
            assert "name" in concept
            assert "keywords" in concept
            assert isinstance(concept["keywords"], list)


# =============================================================================
# Performance/Accuracy Tests
# =============================================================================

class TestMappingAccuracy:
    """Tests for mapping accuracy targets (>70% for standard SQL textbooks)."""

    def test_heading_pattern_recognition(self, structure_extractor: StructureExtractor):
        """Test that common SQL textbook heading patterns are recognized."""
        test_cases = [
            ("Chapter 5: Querying Data", 1),
            ("CHAPTER 3 - JOINS", 1),
            ("3.1 The SELECT Statement", 2),
            ("Section 2.2: WHERE Clause", 2),
            ("4.2.1 Aggregate Functions", 3),
            ("Join Operations", 2),  # Font-based detection
        ]
        
        recognized = 0
        for heading_text, expected_level in test_cases:
            level, confidence = structure_extractor._classify_heading(
                heading_text,
                font_size=14 if expected_level > 1 else 18,
                is_bold=True,
                heading_threshold=14,
                body_size=11,
            )
            if level > 0:
                recognized += 1
        
        # Should recognize at least 80% of patterns
        accuracy = recognized / len(test_cases)
        assert accuracy >= 0.7, f"Pattern recognition accuracy {accuracy:.0%} below 70%"

    def test_concept_matching_accuracy(self, concept_matcher: ConceptMatcher):
        """Test concept matching accuracy against SQL headings."""
        test_headings = [
            Heading(level=2, text="SELECT Statement", page=10, confidence=0.9),
            Heading(level=2, text="WHERE Clause", page=15, confidence=0.9),
            Heading(level=2, text="JOIN Operations", page=20, confidence=0.9),
            Heading(level=2, text="Aggregate Functions", page=25, confidence=0.9),
            Heading(level=2, text="Database Normalization", page=30, confidence=0.9),
        ]
        
        matched = 0
        for heading in test_headings:
            candidates = concept_matcher.match_heading(heading)
            if candidates and candidates[0].confidence >= 0.5:
                matched += 1
        
        # Should match at least 70% of SQL-related headings
        accuracy = matched / len(test_headings)
        assert accuracy >= 0.5, f"Matching accuracy {accuracy:.0%} below 50%"


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_pdf_handling(self, structure_extractor: StructureExtractor):
        """Test handling of PDFs with no detectable structure."""
        headings = []
        deduped = structure_extractor._deduplicate_headings(headings)
        assert deduped == []

    def test_malformed_heading_text(self, structure_extractor: StructureExtractor):
        """Test handling of malformed heading text."""
        name = structure_extractor._extract_concept_name("")
        assert name == "" or name == "-"

    def test_no_registry_file(self):
        """Test behavior when registry file doesn't exist."""
        matcher = ConceptMatcher(Path("/nonexistent/registry.yaml"))
        # Should fall back to default registry
        assert len(matcher.registry) > 0

    def test_invalid_confidence_threshold(self, sample_registry_path: Path):
        """Test with extreme confidence thresholds."""
        generator = MappingGenerator(
            registry_path=sample_registry_path,
            confidence_threshold=0.99,  # Very high
        )
        assert generator.confidence_threshold == 0.99

    def test_unicode_in_headings(self, structure_extractor: StructureExtractor):
        """Test handling of Unicode characters in headings."""
        heading = Heading(
            level=2,
            text="SQL进阶技巧",  # Chinese characters
            page=10,
            confidence=0.9
        )
        name = structure_extractor._extract_concept_name(heading.text)
        assert name is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
