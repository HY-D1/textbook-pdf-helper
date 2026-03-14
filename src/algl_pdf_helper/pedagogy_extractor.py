"""
Pedagogy Extractor for Textbook Structure Preservation.

This module extracts and preserves the pedagogical structure of textbooks including:
- Chapter boundaries and topic hierarchies
- End-of-chapter exercises with solutions
- SQL examples with provenance tracking
- Paired-page format detection (syntax page + explanation page)
- Learning path classification

The extractor works on content blocks from SectionExtractor and produces
structured pedagogy data for export alongside concept-based units.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from .section_extractor import ContentBlock, BlockType, SectionExtractor
from .pedagogy_models import (
    ChapterInfo,
    ChapterSummary,
    TopicInfo,
    ExerciseInfo,
    ExampleInfo,
    LearningPathType,
    infer_path_type,
    generate_exercise_id,
    generate_example_id,
    is_likely_exercise_section,
    is_likely_example,
)


# =============================================================================
# EXTRACTION STATE
# =============================================================================

@dataclass
class ExtractionState:
    """Internal state during pedagogy extraction."""
    current_chapter: ChapterInfo | None = None
    current_topic: TopicInfo | None = None
    in_exercise_section: bool = False
    exercise_buffer: list[str] = field(default_factory=list)
    example_counter: int = 0
    exercise_counter: int = 0
    
    def reset_for_new_chapter(self, chapter: ChapterInfo) -> None:
        """Reset state for a new chapter."""
        self.current_chapter = chapter
        self.current_topic = None
        self.in_exercise_section = False
        self.exercise_buffer = []
        self.exercise_counter = 0


# =============================================================================
# PEDAGOGY EXTRACTOR
# =============================================================================

class PedagogyExtractor:
    """
    Extracts pedagogical structure from PDF content blocks.
    
    This extractor identifies:
    - Chapter boundaries ("Chapter 3", "3. Introduction", etc.)
    - Topic hierarchies within chapters ("3.1", "3.2", etc.)
    - Exercise sections and individual exercises
    - SQL examples with page locations
    - Paired-page format patterns
    
    Example:
        extractor = PedagogyExtractor()
        chapters, exercises, examples = extractor.extract_from_blocks(
            blocks, doc_id="murach-sql"
        )
    """
    
    # Chapter detection patterns
    CHAPTER_PATTERNS = [
        r'^\s*chapter\s+(\d+)[:.\s]+(.+)$',  # "Chapter 3: SELECT Basics"
        r'^\s*ch\.?\s*(\d+)[:.\s]+(.+)$',   # "Ch. 3: SELECT Basics"
        r'^\s*(\d+)[:.\s]+([A-Z][^.]+)$',   # "3. SELECT Basics"
    ]
    
    # Topic/section detection patterns (subsections like 3.1, 3.2)
    TOPIC_PATTERNS = [
        r'^\s*(\d+)\.(\d+)[:.\s]+(.+)$',     # "3.1 SELECT Statement"
        r'^\s*(\d+)\.(\d+)\.(\d+)[:.\s]+',  # "3.1.1 Basic Syntax"
    ]
    
    # Exercise detection patterns
    EXERCISE_START_PATTERNS = [
        r'^\s*exercises?\s*$',
        r'^\s*practice\s+exercises?\s*$',
        r'^\s*end[-\s]of[-\s]chapter\s+exercises?\s*$',
        r'^\s*review\s+questions?\s*$',
    ]
    
    EXERCISE_NUMBER_PATTERNS = [
        r'^\s*(\d+)[:.\s]+(.+)$',            # "1. Write a query..."
        r'^\s*\(\s*(\d+)\s*\)\s*(.+)$',     # "(1) Write a query..."
        r'^\s*ex(?:ercise)?\.?\s*(\d+)[:.\s]+(.+)$',  # "Ex. 1: Write..."
    ]
    
    # SQL code detection patterns
    SQL_PATTERNS = [
        r'\b(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\s+.+?\bFROM\b',
        r'\bJOIN\s+\w+\s+\bON\b',
        r'\bWHERE\s+.+=',
        r'\bGROUP\s+BY\b',
        r'\bORDER\s+BY\b',
    ]
    
    # Paired-page format indicators (Murach style)
    PAIRED_PAGE_INDICATORS = [
        r'\bsyntax\s+summary\s*$',
        r'^\s*the\s+syntax\s*$',
        r'^\s*code\s+explanation\s*$',
        r'^\s*description\s*$',
    ]
    
    def __init__(self, doc_id: str = "unknown"):
        """
        Initialize the pedagogy extractor.
        
        Args:
            doc_id: Document identifier for generating IDs
        """
        self.doc_id = doc_id
        self.state = ExtractionState()
        self._compiled_chapter_patterns = [re.compile(p, re.IGNORECASE) for p in self.CHAPTER_PATTERNS]
        self._compiled_topic_patterns = [re.compile(p, re.IGNORECASE) for p in self.TOPIC_PATTERNS]
        self._compiled_exercise_patterns = [re.compile(p, re.IGNORECASE) for p in self.EXERCISE_START_PATTERNS]
        self._compiled_exercise_num_patterns = [re.compile(p, re.IGNORECASE) for p in self.EXERCISE_NUMBER_PATTERNS]
        self._compiled_sql_patterns = [re.compile(p, re.IGNORECASE) for p in self.SQL_PATTERNS]
        self._compiled_paired_patterns = [re.compile(p, re.IGNORECASE) for p in self.PAIRED_PAGE_INDICATORS]
    
    def extract_from_blocks(
        self,
        blocks: list[ContentBlock],
    ) -> tuple[list[ChapterInfo], list[ExerciseInfo], list[ExampleInfo]]:
        """
        Extract pedagogy structure from content blocks.
        
        Args:
            blocks: List of ContentBlock objects from SectionExtractor
            
        Returns:
            Tuple of (chapters, exercises, examples)
        """
        chapters: list[ChapterInfo] = []
        exercises: list[ExerciseInfo] = []
        examples: list[ExampleInfo] = []
        
        for i, block in enumerate(blocks):
            # Get surrounding context for better detection
            prev_block = blocks[i - 1] if i > 0 else None
            next_block = blocks[i + 1] if i < len(blocks) - 1 else None
            
            # Check for chapter boundary
            chapter = self._detect_chapter(block)
            if chapter:
                # Save previous chapter if exists
                if self.state.current_chapter:
                    self._finalize_exercise_buffer(exercises)
                    chapters.append(self.state.current_chapter)
                
                # Start new chapter
                self.state.reset_for_new_chapter(chapter)
                continue
            
            # Check for topic/section within chapter
            topic = self._detect_topic(block)
            if topic and self.state.current_chapter:
                # Save current topic if exists
                if self.state.current_topic:
                    self.state.current_chapter.topics.append(self.state.current_topic)
                self.state.current_topic = topic
                continue
            
            # Check for exercise section start
            if self._is_exercise_section_start(block):
                self.state.in_exercise_section = True
                self._finalize_exercise_buffer(exercises)
                continue
            
            # Extract exercises if in exercise section
            if self.state.in_exercise_section and self.state.current_chapter:
                exercise = self._extract_exercise(block, prev_block)
                if exercise:
                    exercises.append(exercise)
                    self.state.current_chapter.exercises.append(exercise.exercise_id)
                continue
            
            # Extract SQL examples (not in exercise section)
            if block.block_type == BlockType.SQL_CODE and self.state.current_chapter:
                example = self._extract_example(block, prev_block, next_block)
                if example:
                    examples.append(example)
                    if self.state.current_topic:
                        self.state.current_topic.example_refs.append(example.example_id)
                continue
            
            # Detect paired-page format
            if self._is_paired_page_indicator(block):
                # Mark previous example as paired if exists
                if examples and examples[-1].chapter_number == self.state.current_chapter.chapter_number if self.state.current_chapter else False:
                    examples[-1].is_paired_format = True
        
        # Finalize last chapter
        if self.state.current_chapter:
            if self.state.current_topic:
                self.state.current_chapter.topics.append(self.state.current_topic)
            self._finalize_exercise_buffer(exercises)
            chapters.append(self.state.current_chapter)
        
        # Infer path types for chapters
        self._infer_path_types(chapters)
        
        # Link paired examples
        self._link_paired_examples(examples)
        
        return chapters, exercises, examples
    
    def extract_from_pdf(
        self,
        pdf_path: Path | str,
    ) -> tuple[list[ChapterInfo], list[ExerciseInfo], list[ExampleInfo]]:
        """
        Extract pedagogy structure directly from PDF.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (chapters, exercises, examples)
        """
        extractor = SectionExtractor()
        blocks = extractor.extract_blocks(pdf_path, self.doc_id)
        return self.extract_from_blocks(blocks)
    
    def _detect_chapter(self, block: ContentBlock) -> ChapterInfo | None:
        """
        Detect if block is a chapter heading.
        
        Args:
            block: Content block to check
            
        Returns:
            ChapterInfo if chapter detected, None otherwise
        """
        if block.block_type not in (BlockType.HEADING, BlockType.SUBHEADING):
            return None
        
        text = block.text_content.strip()
        
        for pattern in self._compiled_chapter_patterns:
            match = pattern.match(text)
            if match:
                chapter_num = int(match.group(1))
                title = match.group(2).strip()
                
                return ChapterInfo(
                    chapter_number=chapter_num,
                    chapter_title=title,
                    page_range=(block.page_number, block.page_number),
                )
        
        return None
    
    def _detect_topic(self, block: ContentBlock) -> TopicInfo | None:
        """
        Detect if block is a topic/subsection heading.
        
        Args:
            block: Content block to check
            
        Returns:
            TopicInfo if topic detected, None otherwise
        """
        if block.block_type not in (BlockType.HEADING, BlockType.SUBHEADING):
            return None
        
        text = block.text_content.strip()
        
        # Check for subsection pattern (e.g., "3.1 SELECT Statement")
        for pattern in self._compiled_topic_patterns:
            match = pattern.match(text)
            if match:
                topic_id = f"ch{match.group(1)}-{match.group(2)}"
                # Remove the section number from title
                title = re.sub(r'^\d+\.\d+(?:\.\d+)?[:.\s]+', '', text)
                
                return TopicInfo(
                    topic_id=topic_id,
                    title=title,
                    page_range=(block.page_number, block.page_number),
                    subsection_ids=[match.group(0).split()[0].rstrip('.:')],
                )
        
        return None
    
    def _is_exercise_section_start(self, block: ContentBlock) -> bool:
        """Check if block marks the start of an exercise section."""
        if block.block_type not in (BlockType.HEADING, BlockType.SUBHEADING):
            return False
        
        text = block.text_content.strip().lower()
        return any(p.match(text) for p in self._compiled_exercise_patterns)
    
    def _extract_exercise(
        self,
        block: ContentBlock,
        prev_block: ContentBlock | None,
    ) -> ExerciseInfo | None:
        """
        Extract exercise information from a block.
        
        Args:
            block: Current content block
            prev_block: Previous block for context
            
        Returns:
            ExerciseInfo if exercise found, None otherwise
        """
        text = block.text_content.strip()
        
        # Check for numbered exercise
        for pattern in self._compiled_exercise_num_patterns:
            match = pattern.match(text)
            if match:
                exercise_num = int(match.group(1))
                problem = match.group(2).strip()
                
                # Skip very short entries (likely not real exercises)
                if len(problem) < 10:
                    return None
                
                self.state.exercise_counter += 1
                
                return ExerciseInfo(
                    exercise_id=generate_exercise_id(
                        self.doc_id,
                        self.state.current_chapter.chapter_number,
                        exercise_num
                    ),
                    chapter_number=self.state.current_chapter.chapter_number,
                    exercise_number=exercise_num,
                    problem_text=problem,
                    page_number=block.page_number,
                )
        
        return None
    
    def _extract_example(
        self,
        block: ContentBlock,
        prev_block: ContentBlock | None,
        next_block: ContentBlock | None,
    ) -> ExampleInfo | None:
        """
        Extract SQL example information from a block.
        
        Args:
            block: Current content block (SQL code)
            prev_block: Previous block for context
            next_block: Next block for context
            
        Returns:
            ExampleInfo if valid example found, None otherwise
        """
        sql_code = block.text_content.strip()
        
        # Validate it's actually SQL
        if not self._contains_sql(sql_code):
            return None
        
        # Get explanation from previous or next prose block
        explanation = ""
        example_type = "syntax"
        
        if prev_block and prev_block.block_type == BlockType.EXPLANATORY_PROSE:
            explanation = prev_block.text_content.strip()
            example_type = "application"
        elif next_block and next_block.block_type == BlockType.EXPLANATORY_PROSE:
            explanation = next_block.text_content.strip()
        
        # Generate example ID
        self.state.example_counter += 1
        
        return ExampleInfo(
            example_id=generate_example_id(
                self.doc_id,
                self.state.current_chapter.chapter_number,
                self.state.example_counter
            ),
            chapter_number=self.state.current_chapter.chapter_number,
            page_number=block.page_number,
            sql_code=sql_code,
            explanation=explanation[:500],  # Limit explanation length
            example_type=example_type,
        )
    
    def _is_paired_page_indicator(self, block: ContentBlock) -> bool:
        """Check if block indicates a paired-page format explanation."""
        if block.block_type != BlockType.SUBHEADING:
            return False
        
        text = block.text_content.strip().lower()
        return any(p.match(text) for p in self._compiled_paired_patterns)
    
    def _contains_sql(self, text: str) -> bool:
        """Check if text contains valid SQL patterns."""
        return any(p.search(text) for p in self._compiled_sql_patterns)
    
    def _finalize_exercise_buffer(self, exercises: list[ExerciseInfo]) -> None:
        """Process any buffered exercise content (for multi-line exercises)."""
        # Currently exercises are single-line; buffer can be extended for multi-line
        self.state.exercise_buffer = []
    
    def _infer_path_types(self, chapters: list[ChapterInfo]) -> None:
        """Infer learning path types for chapters based on content."""
        for chapter in chapters:
            topic_titles = [t.title for t in chapter.topics]
            chapter.path_type = infer_path_type(chapter.chapter_title, topic_titles)
    
    def _link_paired_examples(self, examples: list[ExampleInfo]) -> None:
        """
        Link paired examples (syntax page with explanation page).
        
        In paired-page format books like Murach:
        - Right page often shows syntax/code
        - Left page explains the syntax
        """
        # Group examples by chapter
        by_chapter: dict[int, list[ExampleInfo]] = {}
        for ex in examples:
            if ex.chapter_number not in by_chapter:
                by_chapter[ex.chapter_number] = []
            by_chapter[ex.chapter_number].append(ex)
        
        # Link consecutive paired examples
        for chapter_examples in by_chapter.values():
            sorted_examples = sorted(chapter_examples, key=lambda e: e.page_number)
            
            for i, ex in enumerate(sorted_examples):
                if ex.is_paired_format:
                    # Find the explanation on adjacent page
                    for other in sorted_examples:
                        if other != ex and abs(other.page_number - ex.page_number) == 1:
                            if not other.is_paired_format:
                                # Link them
                                ex.paired_with = other.example_id
                                other.paired_with = ex.example_id
                                other.is_paired_format = True
                                break


# =============================================================================
# PEDAGOGY INTEGRATOR
# =============================================================================

class PedagogyIntegrator:
    """
    Integrates pedagogy structure with concept-based units.
    
    Links chapters, exercises, and examples to concepts for a
    unified view of the textbook's pedagogical organization.
    """
    
    def __init__(
        self,
        chapters: list[ChapterInfo],
        exercises: list[ExerciseInfo],
        examples: list[ExampleInfo],
    ):
        """
        Initialize with extracted pedagogy data.
        
        Args:
            chapters: List of chapter information
            exercises: List of exercise information
            examples: List of example information
        """
        self.chapters = chapters
        self.exercises = exercises
        self.examples = examples
        
        # Build lookup indexes
        self._chapter_by_number = {c.chapter_number: c for c in chapters}
        self._exercise_by_id = {e.exercise_id: e for e in exercises}
        self._example_by_id = {e.example_id: e for e in examples}
    
    def link_to_concepts(self, concept_id_map: dict[str, list[str]]) -> None:
        """
        Link exercises and examples to concepts.
        
        Args:
            concept_id_map: Dictionary mapping concept_id → list of keywords
        """
        # Link exercises to concepts
        for exercise in self.exercises:
            concepts = self._find_matching_concepts(exercise.problem_text, concept_id_map)
            exercise.concepts_tested = concepts
        
        # Link examples to concepts
        for example in self.examples:
            text = example.sql_code + " " + example.explanation
            concepts = self._find_matching_concepts(text, concept_id_map)
            example.concept_ids = concepts
        
        # Update topic concept lists
        for chapter in self.chapters:
            for topic in chapter.topics:
                # Infer concepts from topic title
                concepts = self._find_matching_concepts(topic.title, concept_id_map)
                topic.concept_ids = concepts
    
    def _find_matching_concepts(
        self,
        text: str,
        concept_id_map: dict[str, list[str]],
    ) -> list[str]:
        """Find concepts that match the given text."""
        text_lower = text.lower()
        matches = []
        
        for concept_id, keywords in concept_id_map.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    matches.append(concept_id)
                    break
        
        return matches
    
    def get_concept_chapter(self, concept_id: str) -> ChapterInfo | None:
        """Get the chapter that covers a specific concept."""
        for chapter in self.chapters:
            for topic in chapter.topics:
                if concept_id in topic.concept_ids:
                    return chapter
        return None
    
    def get_concept_exercises(self, concept_id: str) -> list[ExerciseInfo]:
        """Get all exercises testing a specific concept."""
        return [e for e in self.exercises if concept_id in e.concepts_tested]
    
    def get_concept_examples(self, concept_id: str) -> list[ExampleInfo]:
        """Get all examples demonstrating a specific concept."""
        return [e for e in self.examples if concept_id in e.concept_ids]
    
    def get_path_concepts(self, path_type: str) -> list[str]:
        """Get all concept IDs belonging to a specific learning path."""
        concepts = set()
        for chapter in self.chapters:
            if chapter.path_type == path_type:
                for topic in chapter.topics:
                    concepts.update(topic.concept_ids)
        return list(concepts)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def detect_paired_page_format(examples: list[ExampleInfo], threshold: float = 0.3) -> bool:
    """
    Detect if textbook uses paired-page format.
    
    Paired-page format (common in Murach books) has:
    - Syntax/code on one page
    - Explanation on facing page
    
    Args:
        examples: List of extracted examples
        threshold: Minimum ratio of paired examples to consider it paired-page
        
    Returns:
        True if paired-page format detected
    """
    if not examples:
        return False
    
    paired_count = sum(1 for e in examples if e.is_paired_format)
    ratio = paired_count / len(examples)
    
    return ratio >= threshold


def estimate_progressive_structure(chapters: list[ChapterInfo]) -> dict[str, Any]:
    """
    Analyze the progressive/difficulty structure of chapters.
    
    Returns statistics about how difficulty progresses through chapters.
    """
    if not chapters:
        return {}
    
    sorted_chapters = sorted(chapters, key=lambda c: c.chapter_number)
    
    # Analyze topic density
    topic_counts = [len(c.topics) for c in sorted_chapters]
    avg_topics = sum(topic_counts) / len(topic_counts) if topic_counts else 0
    
    # Analyze exercise density
    exercise_counts = [len(c.exercises) for c in sorted_chapters]
    avg_exercises = sum(exercise_counts) / len(exercise_counts) if exercise_counts else 0
    
    return {
        "total_chapters": len(chapters),
        "topic_density": {
            "average_per_chapter": avg_topics,
            "max": max(topic_counts) if topic_counts else 0,
            "min": min(topic_counts) if topic_counts else 0,
        },
        "exercise_density": {
            "average_per_chapter": avg_exercises,
            "max": max(exercise_counts) if exercise_counts else 0,
            "min": min(exercise_counts) if exercise_counts else 0,
        },
        "path_distribution": {
            "developer": len([c for c in chapters if c.path_type == "developer"]),
            "admin": len([c for c in chapters if c.path_type == "admin"]),
            "design": len([c for c in chapters if c.path_type == "design"]),
            "general": len([c for c in chapters if c.path_type == "general"]),
        },
    }
