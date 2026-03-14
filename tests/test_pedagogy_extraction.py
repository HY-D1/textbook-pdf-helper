"""
Tests for Textbook Pedagogy Preservation.

Tests cover:
- Pedagogy model validation
- Chapter structure extraction
- Exercise extraction
- Example extraction with paired-page detection
- Learning path classification
- Navigation index building
"""

from __future__ import annotations

import pytest
from pathlib import Path

from algl_pdf_helper.pedagogy_models import (
    ChapterInfo,
    ChapterSummary,
    TopicInfo,
    ExerciseInfo,
    ExampleInfo,
    NavigationIndex,
    PedagogyManifest,
    ChapterGraphEntry,
    ExerciseBankEntry,
    ExampleBankEntry,
    LearningPathType,
    infer_path_type,
    generate_exercise_id,
    generate_example_id,
    is_likely_exercise_section,
    detect_paired_page_format,
    estimate_progressive_structure,
)

from algl_pdf_helper.pedagogy_extractor import (
    PedagogyExtractor,
    PedagogyIntegrator,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_chapter():
    """Fixture for a sample chapter."""
    return ChapterInfo(
        chapter_number=3,
        chapter_title="Retrieving Data from One Table",
        page_range=(45, 89),
        topics=[
            TopicInfo(
                topic_id="ch3-1",
                title="SELECT statement basics",
                concept_ids=["select-basic"],
                page_range=(45, 50),
                subsection_ids=["3.1"],
            ),
            TopicInfo(
                topic_id="ch3-2",
                title="WHERE clause",
                concept_ids=["where-clause"],
                page_range=(51, 58),
                subsection_ids=["3.2"],
            ),
        ],
        exercises=["murach-ch3-ex1", "murach-ch3-ex2"],
        path_type="developer",
        objectives=["Write basic SELECT statements", "Filter data with WHERE"],
    )


@pytest.fixture
def sample_exercise():
    """Fixture for a sample exercise."""
    return ExerciseInfo(
        exercise_id="murach-ch3-ex1",
        chapter_number=3,
        exercise_number=1,
        problem_text="Write a SELECT statement to retrieve all columns from the customers table.",
        solution_text="SELECT * FROM customers;",
        concepts_tested=["select-basic"],
        difficulty="beginner",
        exercise_type="coding",
        page_number=88,
    )


@pytest.fixture
def sample_example():
    """Fixture for a sample SQL example."""
    return ExampleInfo(
        example_id="murach-ch3-ex1",
        chapter_number=3,
        page_number=47,
        sql_code="SELECT * FROM customers;",
        explanation="This query retrieves all columns and rows from the customers table.",
        concept_ids=["select-basic"],
        example_type="syntax",
    )


# =============================================================================
# PEDAGOGY MODELS TESTS
# =============================================================================

class TestChapterInfo:
    """Tests for ChapterInfo dataclass."""
    
    def test_chapter_creation(self, sample_chapter):
        """Test creating a ChapterInfo instance."""
        assert sample_chapter.chapter_number == 3
        assert sample_chapter.chapter_title == "Retrieving Data from One Table"
        assert len(sample_chapter.topics) == 2
        assert sample_chapter.path_type == "developer"
    
    def test_chapter_page_count(self, sample_chapter):
        """Test page count calculation."""
        assert sample_chapter.page_count == 45  # 89 - 45 + 1
    
    def test_chapter_concept_ids(self, sample_chapter):
        """Test getting concept IDs from chapter."""
        concepts = sample_chapter.get_concept_ids()
        assert "select-basic" in concepts
        assert "where-clause" in concepts
    
    def test_chapter_to_dict(self, sample_chapter):
        """Test serialization to dictionary."""
        data = sample_chapter.to_dict()
        assert data["chapter_number"] == 3
        assert data["chapter_title"] == "Retrieving Data from One Table"
        assert "topics" in data
        assert len(data["topics"]) == 2


class TestTopicInfo:
    """Tests for TopicInfo dataclass."""
    
    def test_topic_creation(self):
        """Test creating a TopicInfo instance."""
        topic = TopicInfo(
            topic_id="ch3-1",
            title="SELECT statement basics",
            concept_ids=["select-basic"],
            page_range=(45, 50),
        )
        assert topic.topic_id == "ch3-1"
        assert topic.title == "SELECT statement basics"


class TestExerciseInfo:
    """Tests for ExerciseInfo dataclass."""
    
    def test_exercise_creation(self, sample_exercise):
        """Test creating an ExerciseInfo instance."""
        assert sample_exercise.exercise_id == "murach-ch3-ex1"
        assert sample_exercise.chapter_number == 3
        assert sample_exercise.difficulty == "beginner"
    
    def test_exercise_to_dict(self, sample_exercise):
        """Test serialization to dictionary."""
        data = sample_exercise.to_dict()
        assert data["exercise_id"] == "murach-ch3-ex1"
        assert data["chapter"] == 3
        assert data["difficulty"] == "beginner"


class TestExampleInfo:
    """Tests for ExampleInfo dataclass."""
    
    def test_example_creation(self, sample_example):
        """Test creating an ExampleInfo instance."""
        assert sample_example.example_id == "murach-ch3-ex1"
        assert sample_example.sql_code == "SELECT * FROM customers;"
        assert sample_example.page_number == 47
    
    def test_example_paired_format(self):
        """Test paired format flag."""
        example = ExampleInfo(
            example_id="test-ex",
            chapter_number=1,
            page_number=10,
            sql_code="SELECT * FROM users;",
            explanation="Retrieves all users",
            is_paired_format=True,
            paired_with="explanation-p10",
        )
        assert example.is_paired_format
        assert example.paired_with == "explanation-p10"


class TestNavigationIndex:
    """Tests for NavigationIndex."""
    
    def test_add_concept_mapping(self):
        """Test adding concept mapping."""
        nav = NavigationIndex()
        nav.add_concept_mapping(
            concept_id="select-basic",
            chapter_number=3,
            topic_ids=["ch3-1"],
            exercise_ids=["ex1", "ex2"],
        )
        assert "select-basic" in nav.by_concept
        assert nav.by_concept["select-basic"]["chapter"] == 3
    
    def test_add_chapter_mapping(self):
        """Test adding chapter mapping."""
        nav = NavigationIndex()
        nav.add_chapter_mapping(
            chapter_number=3,
            title="SELECT Basics",
            topic_ids=["ch3-1", "ch3-2"],
            concept_ids=["select-basic"],
            exercise_ids=["ex1"],
        )
        assert "3" in nav.by_chapter
        assert nav.by_chapter["3"]["title"] == "SELECT Basics"
    
    def test_add_path_concept(self):
        """Test adding concept to learning path."""
        nav = NavigationIndex()
        nav.add_path_concept("developer", "select-basic")
        nav.add_path_concept("developer", "where-clause")
        assert "developer" in nav.by_path
        assert "select-basic" in nav.by_path["developer"]


class TestPedagogyManifest:
    """Tests for PedagogyManifest."""
    
    def test_manifest_creation(self):
        """Test creating a PedagogyManifest."""
        manifest = PedagogyManifest(
            source_doc_id="murach-sql",
            generated_at="2024-01-01T00:00:00Z",
            total_chapters=5,
            total_exercises=50,
            total_examples=100,
        )
        assert manifest.source_doc_id == "murach-sql"
        assert manifest.total_chapters == 5
    
    def test_manifest_summary(self):
        """Test getting summary from manifest."""
        manifest = PedagogyManifest(
            source_doc_id="murach-sql",
            generated_at="2024-01-01T00:00:00Z",
            total_chapters=5,
            total_exercises=50,
            total_examples=100,
            developer_path_concepts=["c1", "c2"],
            admin_path_concepts=["c3"],
        )
        summary = manifest.get_summary()
        assert summary["total_chapters"] == 5
        assert summary["paths"]["developer"] == 2
        assert summary["paths"]["admin"] == 1


class TestPydanticModels:
    """Tests for Pydantic export models."""
    
    def test_chapter_graph_entry(self):
        """Test ChapterGraphEntry validation."""
        entry = ChapterGraphEntry(
            chapter_number=3,
            title="SELECT Basics",
            page_range=[45, 89],
            topics=[{"topic_id": "t1", "title": "SELECT", "concepts": ["select-basic"]}],
            exercises=["ex1", "ex2"],
            path_type="developer",
        )
        assert entry.chapter_number == 3
        assert entry.path_type == "developer"
    
    def test_chapter_graph_entry_invalid_path(self):
        """Test ChapterGraphEntry validates path_type."""
        with pytest.raises(ValueError):
            ChapterGraphEntry(
                chapter_number=3,
                title="Test",
                page_range=[1, 10],
                path_type="invalid",  # Invalid path type
            )
    
    def test_exercise_bank_entry(self):
        """Test ExerciseBankEntry validation."""
        entry = ExerciseBankEntry(
            exercise_id="ex-001",
            chapter=3,
            exercise_number=1,
            problem="Write a SELECT statement",
            solution="SELECT * FROM users;",
            concepts=["select-basic"],
            difficulty="beginner",
        )
        assert entry.exercise_id == "ex-001"
    
    def test_example_bank_entry(self):
        """Test ExampleBankEntry validation."""
        entry = ExampleBankEntry(
            example_id="ex-001",
            chapter=3,
            page=47,
            sql="SELECT * FROM users;",
            explanation="Retrieves all users",
            concepts=["select-basic"],
            is_paired_format=True,
        )
        assert entry.example_id == "ex-001"
        assert entry.is_paired_format


# =============================================================================
# UTILITY FUNCTION TESTS
# =============================================================================

class TestInferPathType:
    """Tests for infer_path_type function."""
    
    def test_developer_path(self):
        """Test detecting developer path."""
        result = infer_path_type("Querying Data", ["SELECT statements", "JOINs"])
        assert result == "developer"
    
    def test_admin_path(self):
        """Test detecting admin path."""
        result = infer_path_type("Database Security", ["User privileges", "GRANT"])
        assert result == "admin"
    
    def test_design_path(self):
        """Test detecting design path."""
        result = infer_path_type("Database Design", ["Normalization", "ERDs"])
        assert result == "design"
    
    def test_general_path(self):
        """Test default general path."""
        # Note: "Overview" contains "view" which matches developer keywords
        # So we use topics that don't match any keywords
        result = infer_path_type("Introduction", ["Getting Started", "History"])
        assert result == "general"


class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_generate_exercise_id(self):
        """Test exercise ID generation."""
        ex_id = generate_exercise_id("murach", 3, 1)
        assert ex_id == "murach-ch3-ex1"
    
    def test_generate_example_id(self):
        """Test example ID generation."""
        ex_id = generate_example_id("murach", 3, 1)
        assert ex_id == "murach-ch3-ex1"
    
    def test_is_likely_exercise_section(self):
        """Test exercise section detection."""
        assert is_likely_exercise_section("Exercises")
        assert is_likely_exercise_section("Practice Exercises")
        assert not is_likely_exercise_section("Introduction")
    
    def test_detect_paired_page_format(self):
        """Test paired-page format detection."""
        examples = [
            ExampleInfo(
                example_id="ex1",
                chapter_number=1,
                page_number=10,
                sql_code="SELECT * FROM users;",
                explanation="Test",
                is_paired_format=True,
            ),
            ExampleInfo(
                example_id="ex2",
                chapter_number=1,
                page_number=11,
                sql_code="SELECT * FROM orders;",
                explanation="Test",
                is_paired_format=True,
            ),
        ]
        assert detect_paired_page_format(examples, threshold=0.3)
    
    def test_estimate_progressive_structure(self):
        """Test progressive structure estimation."""
        chapters = [
            ChapterInfo(
                chapter_number=1,
                chapter_title="Intro",
                topics=[TopicInfo(topic_id="t1", title="Topic 1")],
                exercises=["ex1"],
            ),
            ChapterInfo(
                chapter_number=2,
                chapter_title="Advanced",
                topics=[TopicInfo(topic_id="t2", title="Topic 2"), TopicInfo(topic_id="t3", title="Topic 3")],
                exercises=["ex2", "ex3"],
                path_type="developer",
            ),
        ]
        result = estimate_progressive_structure(chapters)
        assert result["total_chapters"] == 2
        assert result["topic_density"]["average_per_chapter"] == 1.5


# =============================================================================
# PEDAGOGY EXTRACTOR TESTS
# =============================================================================

class TestPedagogyExtractor:
    """Tests for PedagogyExtractor class."""
    
    def test_extractor_initialization(self):
        """Test extractor initialization."""
        extractor = PedagogyExtractor(doc_id="test-doc")
        assert extractor.doc_id == "test-doc"
    
    def test_detect_chapter(self):
        """Test chapter detection from block."""
        from algl_pdf_helper.section_extractor import ContentBlock, BlockType
        
        extractor = PedagogyExtractor(doc_id="test")
        block = ContentBlock(
            block_id="test:p1:b1",
            block_type=BlockType.HEADING,
            page_number=1,
            char_start=0,
            char_end=30,
            text_content="Chapter 3: SELECT Basics",
        )
        
        chapter = extractor._detect_chapter(block)
        assert chapter is not None
        assert chapter.chapter_number == 3
        assert chapter.chapter_title == "SELECT Basics"
    
    def test_detect_topic(self):
        """Test topic detection from block."""
        from algl_pdf_helper.section_extractor import ContentBlock, BlockType
        
        extractor = PedagogyExtractor(doc_id="test")
        block = ContentBlock(
            block_id="test:p1:b2",
            block_type=BlockType.SUBHEADING,
            page_number=1,
            char_start=0,
            char_end=25,
            text_content="3.1 SELECT Statement",
        )
        
        topic = extractor._detect_topic(block)
        assert topic is not None
        assert topic.topic_id == "ch3-1"
        assert topic.title == "SELECT Statement"


# =============================================================================
# PEDAGOGY INTEGRATOR TESTS
# =============================================================================

class TestPedagogyIntegrator:
    """Tests for PedagogyIntegrator class."""
    
    def test_integrator_initialization(self):
        """Test integrator initialization."""
        integrator = PedagogyIntegrator(
            chapters=[],
            exercises=[],
            examples=[],
        )
        assert integrator.chapters == []
    
    def test_get_concept_exercises(self):
        """Test getting exercises for a concept."""
        exercise = ExerciseInfo(
            exercise_id="ex1",
            chapter_number=3,
            exercise_number=1,
            problem_text="Test",
            concepts_tested=["select-basic"],
        )
        integrator = PedagogyIntegrator(
            chapters=[],
            exercises=[exercise],
            examples=[],
        )
        
        result = integrator.get_concept_exercises("select-basic")
        assert len(result) == 1
        assert result[0].exercise_id == "ex1"
    
    def test_get_path_concepts(self):
        """Test getting concepts for a learning path."""
        chapter = ChapterInfo(
            chapter_number=3,
            chapter_title="SELECT Basics",
            path_type="developer",
            topics=[
                TopicInfo(
                    topic_id="t1",
                    title="SELECT",
                    concept_ids=["select-basic"],
                ),
            ],
        )
        integrator = PedagogyIntegrator(
            chapters=[chapter],
            exercises=[],
            examples=[],
        )
        
        concepts = integrator.get_path_concepts("developer")
        assert "select-basic" in concepts


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
