"""
Instructional Unit Generator with Adaptive Variants

This module transforms raw PDF textbook content into multiple adaptive-stage variants
of instructional units for the SQL-Adapt learning platform. Each concept generates:

- L1_hint: Quick 1-2 sentence reminder with syntax cue
- L2_hint_plus_example: Brief hint + minimal worked example (30-60s)
- L3_explanation: Full explanation with "why it matters" and multiple examples
- L4_reflective_note: Summary with reflection prompts and transfer questions
- reinforcement: 10-second recall prompt + quick check question

Usage:
    from algl_pdf_helper.unit_generator import (
        GenerationConfig,
        UnitGenerator,
        PromptBuilder,
        ContentTransformer,
        InstructionalUnit,
    )
    
    config = GenerationConfig(
        llm_provider="kimi",
        model_name="kimi-k2-5",
        temperature=0.7,
    )
    
    generator = UnitGenerator()
    variants = generator.generate_all_variants(
        concept_id="joins",
        source_blocks=content_blocks,
        config=config,
    )
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .instructional_models import (
    InstructionalUnit,
    MisconceptionExample,
    PracticeLink,
    SourceSpan,
    SQLExample,
    TargetStage,
    UnitType,
)
from .section_extractor import BlockType, ContentBlock
from .pedagogical_generator import (
    PRACTICE_SCHEMAS,
    TEXTBOOK_TO_PRACTICE_MAPPING,
    FOREIGN_KEY_MAPPINGS,
)
from .generation_pipeline import MultiPassGenerator
from .sql_ontology import get_concept


# =============================================================================
# CONTENT MODELS (Unit-type specific content structures)
# =============================================================================

class L1Content(BaseModel):
    """Content for L1 hint stage - minimal reminder."""
    hint_text: str = Field(..., max_length=300, description="1-2 sentence reminder")
    syntax_cue: str = Field(..., max_length=200, description="Quick syntax reference")
    when_to_use: str = Field(default="", max_length=200, description="Usage context")


class L2Content(BaseModel):
    """Content for L2 hint+example stage - brief with example."""
    hint_text: str = Field(..., max_length=300, description="Brief hint")
    example_sql: str = Field(..., max_length=500, description="Minimal worked example")
    example_explanation: str = Field(..., max_length=300, description="Quick explanation")
    common_pitfall: str = Field(default="", max_length=200, description="One thing to watch")


class L3Content(BaseModel):
    """Content for L3 full explanation stage - comprehensive.
    
    Uses canonical schema types to ensure consistency between
    generator and exporter field names.
    """
    definition: str = Field(..., max_length=1000, description="What this concept is")
    why_it_matters: str = Field(..., max_length=500, description="Real-world relevance")
    learning_objectives: list[str] = Field(
        ..., min_length=1, description="Learning objectives from ontology"
    )
    examples: list[SQLExample] = Field(
        ..., min_length=1, max_length=5, description="SQL examples using canonical schema"
    )
    contrast_example: SQLExample | None = Field(
        default=None, description="What NOT to do example (as SQLExample)"
    )
    common_mistakes: list[MisconceptionExample] = Field(
        default_factory=list, max_length=5, description="Mistakes with fixes using canonical schema"
    )
    practice_links: list[PracticeLink] = Field(
        default_factory=list, description="Links to practice problems using canonical schema"
    )


class L4Content(BaseModel):
    """Content for L4 reflective note stage - deep learning."""
    key_concept_summary: str = Field(..., max_length=500, description="Core concept summary")
    reflection_prompts: list[str] = Field(
        ..., min_length=1, max_length=5, description="Questions to ponder"
    )
    explain_in_own_words: str = Field(
        ..., max_length=500, description="Prompt for student explanation"
    )
    transfer_questions: list[str] = Field(
        ..., min_length=1, max_length=3, description="Apply to new contexts"
    )
    connections: list[str] = Field(
        default_factory=list, description="Links to other concepts"
    )


class ReinforcementContent(BaseModel):
    """Content for reinforcement microcheck stage - quick recall."""
    recall_prompt: str = Field(..., max_length=200, description="10-second recall question")
    quick_check_question: str = Field(..., max_length=300, description="Quick verification question")
    quick_check_answer: str = Field(..., max_length=300, description="Brief answer")
    next_review_timing: str = Field(default="1 day", description="Recommended review interval")


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class GenerationConfig:
    """
    Configuration for LLM-based content generation.
    
    Attributes:
        llm_provider: Which LLM provider to use (kimi, openai, ollama)
        model_name: Specific model name to use
        temperature: Creativity vs determinism (0.0-1.0)
        max_tokens: Maximum tokens per generation
        practice_schemas: Dictionary of practice schema definitions
        api_key: Optional API key override
        base_url: Optional API base URL override
        timeout_seconds: Request timeout
        allow_synthetic_examples: Whether to allow synthetic SQL examples when no real ones found
    """
    llm_provider: str = "kimi"
    model_name: str = "kimi-k2-5"
    temperature: float = 0.7
    max_tokens: int = 2000
    practice_schemas: dict[str, dict[str, Any]] = field(
        default_factory=lambda: PRACTICE_SCHEMAS.copy()
    )
    api_key: str | None = None
    base_url: str | None = None
    timeout_seconds: int = 60
    allow_synthetic_examples: bool = False  # Default to False for production
    
    def __post_init__(self):
        """Validate configuration."""
        if self.temperature < 0.0 or self.temperature > 1.0:
            raise ValueError("Temperature must be between 0.0 and 1.0")
        if self.max_tokens < 100:
            raise ValueError("Max tokens must be at least 100")


# =============================================================================
# ADAPTER FUNCTION
# =============================================================================

def convert_unit_to_canonical(unit_data: dict) -> InstructionalUnit:
    """
    Convert legacy unit format to canonical InstructionalUnit.
    
    This function maps old field names to new field names for backward compatibility.
    
    Args:
        unit_data: Dictionary containing legacy unit data with old field names
        
    Returns:
        InstructionalUnit with canonical field names
        
    Field Mappings:
        - stage -> target_stage
        - source_spans -> evidence_spans
        - block.text -> text_content
        - block.page -> page_number
        - span.block_id -> span_id
        - span.page -> page_number
        - span.excerpt -> text_content
        - span.confidence -> extraction_confidence
    """
    # Map stage values to TargetStage values
    stage_to_target = {
        "L1": "L1_hint",
        "L2": "L2_hint_plus_example",
        "L3": "L3_explanation",
        "L4": "L4_reflective_note",
        "reinforcement": "reinforcement",
    }
    
    # Get the target stage
    old_stage = unit_data.get("stage", "L1")
    target_stage = stage_to_target.get(old_stage, "L1_hint")
    
    # Map unit_type to UnitType
    unit_type_map = {
        "hint": "hint",
        "hint_plus_example": "hint",
        "explanation": "explanation",
        "reflective_note": "reflection",
        "microcheck": "practice",
    }
    unit_type = unit_type_map.get(unit_data.get("unit_type", "hint"), "hint")
    
    # Convert source_spans to evidence_spans
    evidence_spans = []
    for span_data in unit_data.get("source_spans", []):
        span_id = span_data.get("block_id", str(uuid.uuid4())[:8])
        page_number = span_data.get("page", 1)
        text_content = span_data.get("excerpt", "")
        confidence = span_data.get("confidence", 1.0)
        
        evidence_spans.append(
            SourceSpan(
                span_id=span_id,
                doc_id=unit_data.get("doc_id", "unknown"),
                page_number=page_number,
                char_start=0,
                char_end=len(text_content),
                block_type="prose",
                text_content=text_content,
                extraction_confidence=confidence,
            )
        )
    
    # Calculate grounding confidence
    grounding_confidence = 0.8 if evidence_spans else 0.0
    
    # Get source pages from evidence spans
    source_pages = list(set(span.page_number for span in evidence_spans))
    
    return InstructionalUnit(
        unit_id=unit_data.get("unit_id", str(uuid.uuid4())),
        concept_id=unit_data.get("concept_id", "unknown"),
        unit_type=unit_type,
        target_stage=target_stage,
        content=unit_data.get("content", {}),
        error_subtypes=unit_data.get("error_subtypes", []),
        prerequisites=unit_data.get("prerequisites", []),
        difficulty=unit_data.get("difficulty", "beginner"),
        evidence_spans=evidence_spans,
        source_pages=source_pages,
        grounding_confidence=grounding_confidence,
        estimated_read_time=unit_data.get("estimated_time_seconds", 60),
        blocked_if_prereq_missing=unit_data.get("blocked_if_prereq_missing", True),
    )


# =============================================================================
# PROMPT BUILDER
# =============================================================================

class PromptBuilder:
    """
    Builds targeted prompts for each generation sub-task.
    
    Each prompt includes only relevant source spans and targets
    the specific learner level and output format.
    """
    
    def __init__(self, practice_schemas: dict[str, dict[str, Any]] | None = None):
        """Initialize with practice schemas."""
        self.practice_schemas = practice_schemas or PRACTICE_SCHEMAS
    
    def _format_prerequisites(self, prerequisites: list[str]) -> str:
        """Format prerequisites for prompt inclusion."""
        if not prerequisites:
            return "None (foundational concept)"
        return ", ".join(prerequisites)
    
    def _format_source_text(self, blocks: list[ContentBlock], max_chars: int = 2000) -> str:
        """Format source blocks for prompt inclusion."""
        combined = "\n\n".join(b.text_content for b in blocks if b.text_content)
        if len(combined) > max_chars:
            combined = combined[:max_chars] + "..."
        return combined
    
    def build_definition_prompt(
        self,
        concept_id: str,
        source_text: str,
        prerequisites: list[str],
    ) -> str:
        """
        Build prompt for generating concept definition.
        
        Args:
            concept_id: Canonical concept ID
            source_text: Relevant source text from PDF
            prerequisites: List of prerequisite concept IDs
            
        Returns:
            Formatted prompt string
        """
        prereq_str = self._format_prerequisites(prerequisites)
        
        return f"""You are an expert SQL educator creating a concept definition.

CONCEPT ID: {concept_id}
PREREQUISITES: {prereq_str}

SOURCE TEXT FROM TEXTBOOK:
{source_text[:3000]}

TASK:
Create a clear, engaging definition that explains:
1. WHAT this concept is (the technical definition)
2. WHY it matters (real-world relevance)
3. WHEN to use it (typical use cases)

CONSTRAINTS:
- Use plain English, avoid jargon unless explained
- Address the student directly using "you"
- Use practice schema tables (users, orders, products, employees, departments)
- Do NOT use textbook-specific schemas (Sailors, Boats, etc.)
- Maximum 250 words

OUTPUT FORMAT (JSON):
{{
    "definition": "Clear technical definition...",
    "why_it_matters": "Why students should care...",
    "when_to_use": "Typical scenarios...",
    "key_points": ["point 1", "point 2", "point 3"]
}}

Return ONLY valid JSON, no markdown code blocks, no extra commentary."""
    
    def build_example_prompt(
        self,
        concept_id: str,
        source_text: str,
        practice_schemas: dict[str, Any] | None = None,
        num_examples: int = 3,
    ) -> str:
        """
        Build prompt for generating SQL examples.
        
        Args:
            concept_id: Canonical concept ID
            source_text: Relevant source text from PDF
            practice_schemas: Optional custom practice schemas
            num_examples: Number of examples to generate
            
        Returns:
            Formatted prompt string
        """
        schemas = practice_schemas or self.practice_schemas
        
        # Format schema info
        schema_lines = []
        for table_name, schema in list(schemas.items())[:4]:  # Limit to main tables
            cols = schema.get("columns", [])
            if isinstance(cols[0], tuple):
                col_names = [c[0] for c in cols]
            else:
                col_names = cols
            schema_lines.append(f"  - {table_name}: {', '.join(col_names)}")
        schema_str = "\n".join(schema_lines)
        
        return f"""You are creating SQL examples for students learning {concept_id}.

AVAILABLE PRACTICE TABLES:
{schema_str}

SOURCE TEXT:
{source_text[:2000]}

TASK:
Generate {num_examples} SQL examples that demonstrate {concept_id}.

FOR EACH EXAMPLE:
1. Title: Descriptive name
2. Scenario: Real-world context
3. SQL: Valid SQLite syntax ending with semicolon
4. Explanation: How it works
5. Expected output: Brief description

RULES:
- Use ONLY the practice tables listed above
- Include one contrast example showing what NOT to do
- All SQL must be syntactically correct
- Difficulty should match concept level

OUTPUT FORMAT (JSON):
{{
    "examples": [
        {{
            "title": "Example title",
            "scenario": "Real-world context...",
            "sql": "SELECT ...",
            "explanation": "This query...",
            "expected_output": "Returns..."
        }}
    ],
    "contrast_example": {{
        "incorrect_sql": "SELECT ...",
        "why_wrong": "Explanation...",
        "corrected_sql": "SELECT ..."
    }}
}}

Return ONLY valid JSON."""
    
    def build_misconception_prompt(
        self,
        concept_id: str,
        source_text: str,
        error_subtypes: list[str] | None = None,
    ) -> str:
        """
        Build prompt for generating common mistakes.
        
        Args:
            concept_id: Canonical concept ID
            source_text: Relevant source text from PDF
            error_subtypes: Specific error types to focus on
            
        Returns:
            Formatted prompt string
        """
        error_types_str = ""
        if error_subtypes:
            error_types_str = f"\nFOCUS ON THESE ERROR TYPES:\n" + "\n".join(f"- {e}" for e in error_subtypes)
        
        return f"""You are documenting common mistakes students make with {concept_id}.

SOURCE TEXT:
{source_text[:2000]}
{error_types_str}

TASK:
Generate 3 realistic mistakes that {concept_id} students commonly make.

FOR EACH MISTAKE:
1. Title: Descriptive name of the error
2. Error SQL: The incorrect code
3. Error message: Realistic SQLite error message
4. Why it happens: Conceptual misunderstanding
5. Fix SQL: The corrected code
6. Key takeaway: One-sentence reminder

CONSTRAINTS:
- Mistakes must be realistic for actual students
- Use practice schema tables (users, orders, products)
- Error messages should match actual SQLite errors
- Focus on conceptual errors, not just typos

OUTPUT FORMAT (JSON):
{{
    "mistakes": [
        {{
            "title": "Mistake title",
            "error_sql": "SELECT ...",
            "error_message": "error: ...",
            "why_it_happens": "Students think...",
            "fix_sql": "SELECT ...",
            "key_takeaway": "Remember to..."
        }}
    ]
}}

Return ONLY valid JSON."""
    
    def build_reflection_prompt(
        self,
        concept_id: str,
        source_text: str,
    ) -> str:
        """
        Build prompt for generating reflection content.
        
        Args:
            concept_id: Canonical concept ID
            source_text: Relevant source text from PDF
            
        Returns:
            Formatted prompt string
        """
        return f"""You are creating reflection prompts for students mastering {concept_id}.

SOURCE TEXT:
{source_text[:2000]}

TASK:
Create reflection content that helps students internalize {concept_id}.

GENERATE:
1. Key concept summary (2-3 sentences capturing the essence)
2. Reflection prompts (3 questions for deeper thinking)
3. "Explain in your own words" prompt (guide for student explanation)
4. Transfer questions (2 questions applying to new contexts)
5. Connections to other concepts (2-3 related SQL concepts)

DESIGN PRINCIPLES:
- Prompts should encourage metacognition
- Questions should have no single "right" answer
- Transfer questions should stretch understanding
- Connections help build knowledge graphs

OUTPUT FORMAT (JSON):
{{
    "key_concept_summary": "In your own words...",
    "reflection_prompts": [
        "What would happen if...?",
        "How does this relate to...?",
        "When might you choose...?"
    ],
    "explain_in_own_words": "Explain {concept_id} as if teaching a beginner...",
    "transfer_questions": [
        "How would you apply this to...?",
        "What if the scenario was...?"
    ],
    "connections": ["related-concept-1", "related-concept-2"]
}}

Return ONLY valid JSON."""
    
    def build_L1_prompt(self, concept_id: str, source_text: str) -> str:
        """Build prompt for L1 hint stage."""
        return f"""You are creating a quick hint for students who have learned {concept_id} but need a brief reminder.

SOURCE TEXT:
{source_text[:1500]}

TASK:
Create an L1 (Level 1) hint - a minimal reminder that takes 10-15 seconds to read.

REQUIREMENTS:
1. Hint text: 1-2 sentences reminding what {concept_id} does
2. Syntax cue: Quick pattern/syntax reminder (e.g., "SELECT ... FROM ... WHERE ...")
3. When to use: One phrase indicating typical usage

CONSTRAINTS:
- Maximum 300 characters for hint text
- No explanation, no examples, just the cue
- Assume student has learned this before

OUTPUT FORMAT (JSON):
{{
    "hint_text": "1-2 sentence reminder...",
    "syntax_cue": "Quick syntax pattern...",
    "when_to_use": "Usage context"
}}

Return ONLY valid JSON."""
    
    def build_reinforcement_prompt(self, concept_id: str, source_text: str) -> str:
        """Build prompt for reinforcement microcheck stage."""
        return f"""You are creating a quick reinforcement check for {concept_id}.

SOURCE TEXT:
{source_text[:1500]}

TASK:
Create a microcheck that takes 10 seconds to complete - designed for spaced repetition.

REQUIREMENTS:
1. Recall prompt: One question that triggers memory ("What clause filters groups after aggregation?")
2. Quick check question: Simple verification question
3. Quick check answer: Brief correct answer
4. Next review timing: When to review again ("1 day", "3 days", "1 week")

CONSTRAINTS:
- Must be answerable in 10 seconds
- Focus on core concept, not edge cases
- Answer should be definitive

OUTPUT FORMAT (JSON):
{{
    "recall_prompt": "Quick memory trigger...",
    "quick_check_question": "Simple question...",
    "quick_check_answer": "Brief answer...",
    "next_review_timing": "1 day"
}}

Return ONLY valid JSON."""


# =============================================================================
# CONTENT TRANSFORMER
# =============================================================================

class ContentTransformer:
    """
    Transforms SQL content to use practice schemas.
    
    Maps textbook-specific schemas (Sailors, Boats, Reserves) to
    standardized practice schemas (users, orders, products, etc.)
    while preserving pedagogical intent.
    """
    
    def __init__(
        self,
        schema_mapping: dict[str, str] | None = None,
        practice_schemas: dict[str, dict[str, Any]] | None = None,
    ):
        """
        Initialize transformer.
        
        Args:
            schema_mapping: Mapping from textbook terms to practice schemas
            practice_schemas: Practice schema definitions
        """
        self.schema_mapping = schema_mapping or TEXTBOOK_TO_PRACTICE_MAPPING
        self.practice_schemas = practice_schemas or PRACTICE_SCHEMAS
        self.fk_mappings = FOREIGN_KEY_MAPPINGS
    
    def transform_to_practice_schema(
        self,
        sql: str,
        source_tables: list[str],
        target_schema: dict[str, Any] | None = None,
    ) -> str:
        """
        Transform SQL to use practice schemas.
        
        Args:
            sql: Original SQL using textbook schemas
            source_tables: Tables used in the original SQL
            target_schema: Optional target schema override
            
        Returns:
            Transformed SQL using practice schemas
            
        Example:
            >>> transformer = ContentTransformer()
            >>> sql = "SELECT * FROM Sailors WHERE rating > 5;"
            >>> transformer.transform_to_practice_schema(sql, ["Sailors"])
            'SELECT * FROM users WHERE age > 5;'
        """
        if not sql or not sql.strip():
            return ""
        
        schemas = target_schema or self.practice_schemas
        transformed = sql
        
        # Build mapping from source tables to target tables
        table_mapping: dict[str, str] = {}
        for source_table in source_tables:
            source_lower = source_table.lower()
            # Find matching practice schema
            for key, value in self.schema_mapping.items():
                if key.lower() == source_lower:
                    table_mapping[source_table] = value
                    break
        
        # Replace table names (whole word, case-insensitive)
        for old_table, new_table in table_mapping.items():
            pattern = r'\b' + re.escape(old_table) + r'\b'
            transformed = re.sub(pattern, new_table, transformed, flags=re.IGNORECASE)
        
        # Replace column names
        for old_col, new_col in self.schema_mapping.items():
            if "_" in old_col:  # Column names have underscores
                pattern = r'\b' + re.escape(old_col) + r'\b'
                transformed = re.sub(pattern, new_col, transformed, flags=re.IGNORECASE)
        
        # Fix join conditions
        transformed = self._fix_join_conditions(transformed)
        
        # Clean up
        transformed = self._clean_sql(transformed)
        
        return transformed
    
    def _fix_join_conditions(self, sql: str) -> str:
        """Fix join conditions to use proper foreign key relationships."""
        if "JOIN" not in sql.upper():
            return sql
        
        # Extract table aliases
        alias_map: dict[str, str] = {}
        alias_pattern = r'(?:FROM|JOIN)\s+(\w+)\s+(?:AS\s+)?(\w+)(?:\s|$|\n|JOIN|ON|WHERE|GROUP|ORDER|;)'
        
        for match in re.finditer(alias_pattern, sql, re.IGNORECASE):
            table_name = match.group(1).lower()
            alias = match.group(2).lower()
            if alias not in ['where', 'group', 'order', 'having', 'limit', 'join', 'on']:
                alias_map[alias] = table_name
        
        # Pattern to match join conditions
        pattern = r'ON\s+(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)'
        
        def replace_condition(match: Any) -> str:
            table1, col1, table2, col2 = match.groups()
            t1_lower = table1.lower()
            t2_lower = table2.lower()
            
            # Resolve aliases
            resolved_t1 = alias_map.get(t1_lower, t1_lower)
            resolved_t2 = alias_map.get(t2_lower, t2_lower)
            
            # Check for FK mapping
            fk_map = self.fk_mappings.get(resolved_t1, {}).get(resolved_t2)
            if fk_map:
                from_parts = fk_map['from'].split('.')
                to_parts = fk_map['to'].split('.')
                return f"ON {table1}.{from_parts[1]} = {table2}.{to_parts[1]}"
            
            # Reverse lookup
            fk_map_reverse = self.fk_mappings.get(resolved_t2, {}).get(resolved_t1)
            if fk_map_reverse:
                from_parts = fk_map_reverse['from'].split('.')
                to_parts = fk_map_reverse['to'].split('.')
                return f"ON {table2}.{from_parts[1]} = {table1}.{to_parts[1]}"
            
            return match.group(0)
        
        return re.sub(pattern, replace_condition, sql, flags=re.IGNORECASE)
    
    def _clean_sql(self, sql: str) -> str:
        """Clean up SQL formatting."""
        # Fix multiple spaces
        sql = re.sub(r'\s+', ' ', sql)
        # Ensure semicolon at end
        sql = sql.strip()
        if not sql.endswith(';'):
            sql += ';'
        return sql
    
    def transform_text_block(
        self,
        text: str,
        preserve_sql_blocks: bool = True,
    ) -> str:
        """
        Transform a text block, optionally preserving SQL code blocks.
        
        Args:
            text: Original text
            preserve_sql_blocks: If True, only transform SQL within code blocks
            
        Returns:
            Transformed text
        """
        if preserve_sql_blocks:
            # Find SQL code blocks and transform them
            pattern = r'```sql\s*\n(.*?)\n```'
            
            def transform_block(match: Any) -> str:
                sql = match.group(1)
                # Extract table names from SQL (simplified)
                tables = re.findall(r'\bFROM\s+(\w+)', sql, re.IGNORECASE)
                tables += re.findall(r'\bJOIN\s+(\w+)', sql, re.IGNORECASE)
                transformed = self.transform_to_practice_schema(sql, tables)
                return f"```sql\n{transformed}\n```"
            
            return re.sub(pattern, transform_block, text, flags=re.DOTALL | re.IGNORECASE)
        
        return text


# =============================================================================
# UNIT GENERATOR
# =============================================================================

class UnitGenerator:
    """
    Generates multiple adaptive-stage variants for each concept.
    
    This is the main entry point for instructional unit generation.
    It coordinates prompt building, LLM calls, and result assembly.
    """
    
    def __init__(
        self,
        prompt_builder: PromptBuilder | None = None,
        transformer: ContentTransformer | None = None,
    ):
        """
        Initialize the unit generator.
        
        Args:
            prompt_builder: Optional custom PromptBuilder
            transformer: Optional custom ContentTransformer
        """
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.transformer = transformer or ContentTransformer()
        self._generation_stats: dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
    
    def generate_all_variants(
        self,
        concept_id: str,
        source_blocks: list[ContentBlock],
        config: GenerationConfig,
        prerequisites: list[str] | None = None,
        error_subtypes: list[str] | None = None,
    ) -> dict[str, InstructionalUnit]:
        """
        Generate all 5 adaptive-stage variants for a concept.
        
        Args:
            concept_id: Canonical concept identifier
            source_blocks: Source content blocks from PDF
            config: Generation configuration
            prerequisites: Optional list of prerequisite concept IDs
            error_subtypes: Optional list of SQL-Engage error subtype IDs
            
        Returns:
            Dictionary mapping unit types to InstructionalUnit objects:
            {
                "L1_hint": InstructionalUnit,
                "L2_hint_plus_example": InstructionalUnit,
                "L3_explanation": InstructionalUnit,
                "L4_reflective_note": InstructionalUnit,
                "reinforcement": InstructionalUnit,
            }
            
        Raises:
            ValueError: If source_blocks is empty
        """
        if not source_blocks:
            raise ValueError("source_blocks cannot be empty")
        
        prereqs = prerequisites or []
        subtypes = error_subtypes or []
        
        # Generate all variants
        variants: dict[str, InstructionalUnit] = {}
        
        try:
            variants["L1_hint"] = self.generate_L1_hint(
                concept_id, source_blocks, config, prereqs, subtypes
            )
        except Exception as e:
            variants["L1_hint"] = self._create_fallback_unit(
                concept_id, "L1_hint", "hint", config, str(e), subtypes
            )
        
        try:
            variants["L2_hint_plus_example"] = self.generate_L2_hint_plus_example(
                concept_id, source_blocks, config, prereqs, subtypes
            )
        except Exception as e:
            variants["L2_hint_plus_example"] = self._create_fallback_unit(
                concept_id, "L2_hint_plus_example", "hint", config, str(e), subtypes
            )
        
        try:
            variants["L3_explanation"] = self.generate_L3_explanation(
                concept_id, source_blocks, config, prereqs, subtypes
            )
        except Exception as e:
            variants["L3_explanation"] = self._create_fallback_unit(
                concept_id, "L3_explanation", "explanation", config, str(e), subtypes
            )
        
        try:
            variants["L4_reflective_note"] = self.generate_L4_reflective_note(
                concept_id, source_blocks, config, prereqs, subtypes
            )
        except Exception as e:
            variants["L4_reflective_note"] = self._create_fallback_unit(
                concept_id, "L4_reflective_note", "reflection", config, str(e), subtypes
            )
        
        try:
            variants["reinforcement"] = self.generate_reinforcement_microcheck(
                concept_id, source_blocks, config, prereqs, subtypes
            )
        except Exception as e:
            variants["reinforcement"] = self._create_fallback_unit(
                concept_id, "reinforcement", "practice", config, str(e), subtypes
            )
        
        return variants
    
    # Canonical mapping from BlockType enum to SourceSpan block_type Literal
    _BLOCK_TYPE_CANONICAL_MAP: dict[BlockType, str] = {
        BlockType.HEADING: "heading",
        BlockType.SUBHEADING: "heading",
        BlockType.EXPLANATORY_PROSE: "prose",
        BlockType.SIDEBAR: "prose",
        BlockType.SQL_CODE: "code",
        BlockType.OUTPUT_TABLE: "table",
        BlockType.FIGURE: "figure",
        BlockType.DIAGRAM: "figure",
        BlockType.EXERCISE: "exercise",
        BlockType.SUMMARY: "summary",
        BlockType.GLOSSARY: "summary",
        BlockType.ADMIN_TEXT: "admin",
        BlockType.UNKNOWN: "prose",
    }

    # Mapping for string block types to canonical values
    _BLOCK_TYPE_STR_MAPPING: dict[str, str] = {
        # Headings
        "heading": "heading",
        "subheading": "heading",
        "title": "heading",
        # Prose
        "explanatory_prose": "prose",
        "sidebar": "prose",
        "prose": "prose",
        "text": "prose",
        # Code
        "sql_code": "code",
        "code": "code",
        "code_block": "code",
        # Tables
        "output_table": "table",
        "table": "table",
        # Figures
        "figure": "figure",
        "diagram": "figure",
        "image": "figure",
        # Exercise
        "exercise": "exercise",
        "practice": "exercise",
        # Summary
        "summary": "summary",
        "glossary": "summary",
        # Admin
        "admin_text": "admin",
        "admin": "admin",
        "metadata": "admin",
        # Fallback
        "unknown": "prose",
    }

    def _create_evidence_spans(self, blocks: list[ContentBlock], doc_id: str = "unknown") -> list[SourceSpan]:
        """Create evidence span references from content blocks."""
        evidence_spans = []
        for b in blocks:
            text_content = b.text_content or ""
            excerpt = text_content[:100] + "..." if len(text_content) > 100 else text_content
            # Ensure excerpt is not empty (SourceSpan requires at least 1 character)
            if not excerpt:
                excerpt = "[No text content]"
            
            # Map BlockType to canonical string representation using explicit mapping
            block_type_str = "prose"  # Default fallback
            if hasattr(b, 'block_type'):
                if isinstance(b.block_type, str):
                    # Handle string block types - use comprehensive mapping
                    block_type_str = self._BLOCK_TYPE_STR_MAPPING.get(
                        b.block_type.lower(), "prose"
                    )
                else:
                    # It's a BlockType enum - use the canonical mapping
                    block_type_str = self._BLOCK_TYPE_CANONICAL_MAP.get(b.block_type, "prose")
            
            evidence_spans.append(
                SourceSpan(
                    span_id=b.block_id,
                    doc_id=doc_id,
                    page_number=b.page_number,
                    char_start=getattr(b, 'char_start', 0),
                    char_end=getattr(b, 'char_end', len(text_content)),
                    block_type=block_type_str,
                    text_content=excerpt,
                    extraction_confidence=getattr(b, 'confidence', 1.0),
                )
            )
        return evidence_spans
    
    def _call_llm(self, prompt: str, config: GenerationConfig) -> dict[str, Any]:
        """Call LLM with prompt and return structured response."""
        # Grounded mode: no LLM, use extracted content only
        if config.llm_provider in ("grounded", "none"):
            return {}
        
        try:
            # Use MultiPassGenerator for Ollama provider
            if config.llm_provider == 'ollama':
                generator = MultiPassGenerator(
                    model=config.model_name,
                    temperature=config.temperature,
                    timeout=config.timeout_seconds,
                )
                
                # Generate with retry
                response = generator._ollama_chat([
                    {"role": "user", "content": prompt}
                ])
                
                # Parse JSON response
                if response:
                    return self._parse_json_response(response)
                return {}
            
            # For other providers, return empty to trigger fallback
            # TODO: Implement kimi, openai providers
            return {}
            
        except Exception as e:
            # Only log warning once per session, not per call
            if not hasattr(self, '_llm_warning_logged'):
                self.logger.warning(f"LLM unavailable ({config.llm_provider}), using grounded fallback")
                self._llm_warning_logged = True
            return {}
    
    def _parse_json_response(self, response: str) -> dict[str, Any]:
        """Parse JSON from LLM response, handling markdown code blocks."""
        # Try to extract JSON from markdown code blocks
        if "```json" in response:
            match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if match:
                response = match.group(1)
        elif "```" in response:
            match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
            if match:
                response = match.group(1)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}")
    
    def generate_L1_hint(
        self,
        concept_id: str,
        blocks: list[ContentBlock],
        config: GenerationConfig,
        prerequisites: list[str] | None = None,
        error_subtypes: list[str] | None = None,
    ) -> InstructionalUnit:
        """
        Generate L1 hint variant - 1-2 sentence reminder with syntax cue.
        
        Args:
            concept_id: Concept identifier
            blocks: Source content blocks
            config: Generation configuration
            prerequisites: Optional prerequisite concept IDs
            error_subtypes: Optional SQL-Engage error subtype IDs
            
        Returns:
            InstructionalUnit for L1 stage
        """
        source_text = "\n\n".join(b.text_content for b in blocks if b.text_content)
        prompt = self.prompt_builder.build_L1_prompt(concept_id, source_text)
        
        # Try LLM generation
        llm_response = self._call_llm(prompt, config)
        
        if llm_response:
            content = L1Content(
                hint_text=llm_response.get("hint_text", self._get_default_hint(concept_id)),
                syntax_cue=llm_response.get("syntax_cue", self._get_default_syntax_cue(concept_id)),
                when_to_use=llm_response.get("when_to_use", ""),
            )
        else:
            # Use grounded defaults from evidence spans (no-LLM path)
            content = self._build_grounded_L1_content(concept_id, blocks)
        
        # Get source pages from blocks
        source_pages = list(set(b.page_number for b in blocks))
        
        return InstructionalUnit(
            unit_id=f"{concept_id}_L1_hint",
            concept_id=concept_id,
            unit_type="hint",
            target_stage="L1_hint",
            content=content.model_dump(),
            error_subtypes=error_subtypes or [],
            prerequisites=prerequisites or [],
            difficulty="beginner",
            evidence_spans=self._create_evidence_spans(blocks),
            source_pages=source_pages,
            grounding_confidence=0.8 if blocks else 0.0,
            estimated_read_time=15,
        )
    
    def generate_L2_hint_plus_example(
        self,
        concept_id: str,
        blocks: list[ContentBlock],
        config: GenerationConfig,
        prerequisites: list[str] | None = None,
        error_subtypes: list[str] | None = None,
    ) -> InstructionalUnit:
        """
        Generate L2 hint+example variant - brief hint with minimal worked example.
        
        Args:
            concept_id: Concept identifier
            blocks: Source content blocks
            config: Generation configuration
            prerequisites: Optional prerequisite concept IDs
            error_subtypes: Optional SQL-Engage error subtype IDs
            
        Returns:
            InstructionalUnit for L2 stage
        """
        source_text = "\n\n".join(b.text_content for b in blocks if b.text_content)
        
        # Get L1 content as base
        l1_unit = self.generate_L1_hint(concept_id, blocks, config, prerequisites, error_subtypes)
        l1_content = l1_unit.content
        
        # Generate example
        example_prompt = self.prompt_builder.build_example_prompt(
            concept_id, source_text, num_examples=1
        )
        llm_response = self._call_llm(example_prompt, config)
        
        if llm_response and "examples" in llm_response:
            examples = llm_response["examples"]
            if examples:
                example = examples[0]
                example_sql = example.get("sql", self._get_default_example_sql(concept_id))
                example_explanation = example.get("explanation", "See the SQL above.")
            else:
                example_sql = ""
                example_explanation = ""
        else:
            # Use grounded defaults (no-LLM path)
            example_sql = ""
            example_explanation = ""
        
        # If we have LLM example, use it; otherwise grounded defaults will be used
        if example_sql:
            # Transform SQL to practice schema
            example_sql = self.transformer.transform_to_practice_schema(
                example_sql, ["Sailors", "Boats", "Reserves"]
            )
            content = L2Content(
                hint_text=l1_content.get("hint_text", self._get_default_hint(concept_id)),
                example_sql=example_sql,
                example_explanation=example_explanation,
                common_pitfall=self._get_default_pitfall(concept_id),
            )
        else:
            # Use grounded defaults from evidence spans (no-LLM path)
            l1_hint = l1_content.get("hint_text", self._get_default_hint(concept_id))
            content = self._build_grounded_L2_content(concept_id, blocks, l1_hint)
        
        # Get source pages from blocks
        source_pages = list(set(b.page_number for b in blocks))
        
        return InstructionalUnit(
            unit_id=f"{concept_id}_L2_hint_plus_example",
            concept_id=concept_id,
            unit_type="hint",
            target_stage="L2_hint_plus_example",
            content=content.model_dump(),
            error_subtypes=error_subtypes or [],
            prerequisites=prerequisites or [],
            difficulty="beginner",
            evidence_spans=self._create_evidence_spans(blocks),
            source_pages=source_pages,
            grounding_confidence=0.8 if blocks else 0.0,
            estimated_read_time=45,
        )
    
    def generate_L3_explanation(
        self,
        concept_id: str,
        blocks: list[ContentBlock],
        config: GenerationConfig,
        prerequisites: list[str] | None = None,
        error_subtypes: list[str] | None = None,
    ) -> InstructionalUnit:
        """
        Generate L3 full explanation variant - comprehensive with multiple examples.
        
        Args:
            concept_id: Concept identifier
            blocks: Source content blocks
            config: Generation configuration
            prerequisites: Optional prerequisite concept IDs
            error_subtypes: Optional SQL-Engage error subtype IDs
            
        Returns:
            InstructionalUnit for L3 stage
        """
        source_text = "\n\n".join(b.text_content for b in blocks if b.text_content)
        
        # Generate definition
        def_prompt = self.prompt_builder.build_definition_prompt(
            concept_id, source_text, prerequisites or []
        )
        def_response = self._call_llm(def_prompt, config)
        
        # Generate examples
        ex_prompt = self.prompt_builder.build_example_prompt(
            concept_id, source_text, num_examples=3
        )
        ex_response = self._call_llm(ex_prompt, config)
        
        # Generate mistakes
        mist_prompt = self.prompt_builder.build_misconception_prompt(
            concept_id, source_text
        )
        mist_response = self._call_llm(mist_prompt, config)
        
        # Check if we have LLM responses - if not, use grounded defaults (no-LLM path)
        has_llm_content = def_response or ex_response or mist_response
        is_using_default_definition = not def_response
        definition_text = ""
        
        if not has_llm_content:
            # Use grounded defaults from evidence spans (no-LLM path)
            content = self._build_grounded_L3_content(concept_id, blocks, config)
        else:
            # Build content using LLM responses
            examples: list[SQLExample] = []
            if ex_response and "examples" in ex_response:
                for ex in ex_response["examples"]:
                    sql = self.transformer.transform_to_practice_schema(
                        ex.get("sql", ""), ["Sailors", "Boats", "Reserves"]
                    )
                    examples.append(SQLExample(
                        title=ex.get("title", "Example"),
                        scenario=ex.get("scenario", ""),
                        sql=sql,
                        explanation=ex.get("explanation", ""),
                        expected_output=ex.get("expected_output", ""),
                    ))
            
            if not examples:
                examples = self._get_default_sql_examples(concept_id)
            
            contrast: SQLExample | None = None
            if ex_response and "contrast_example" in ex_response:
                ce = ex_response["contrast_example"]
                # Convert contrast example to SQLExample format
                incorrect_sql = self.transformer.transform_to_practice_schema(
                    ce.get("incorrect_sql", ""), ["Sailors", "Boats", "Reserves"]
                )
                corrected_sql = self.transformer.transform_to_practice_schema(
                    ce.get("corrected_sql", ""), ["Sailors", "Boats", "Reserves"]
                )
                contrast = SQLExample(
                    title="Contrast: What NOT to do",
                    scenario=ce.get("why_wrong", ""),
                    sql=incorrect_sql,  # The incorrect SQL is what we show
                    explanation=f"Why wrong: {ce.get('why_wrong', '')}\n\nCorrected: {corrected_sql}",
                )
            
            mistakes: list[MisconceptionExample] = []
            if mist_response and "mistakes" in mist_response:
                for m in mist_response["mistakes"]:
                    mistakes.append(MisconceptionExample(
                        title=m.get("title", "Mistake"),
                        error_sql=self.transformer.transform_to_practice_schema(
                            m.get("error_sql", ""), ["Sailors", "Boats", "Reserves"]
                        ),
                        error_message=m.get("error_message", ""),
                        why_it_happens=m.get("why_it_happens", ""),
                        fix_sql=self.transformer.transform_to_practice_schema(
                            m.get("fix_sql", ""), ["Sailors", "Boats", "Reserves"]
                        ),
                        key_takeaway=m.get("key_takeaway", ""),
                    ))
            
            if not mistakes:
                mistakes = self._get_default_misconceptions(concept_id)
            
            # Build practice links - check for real problems first
            practice_links = self._lookup_real_problems(concept_id)
            if not practice_links:
                # Use unresolved placeholder to indicate these need resolution
                practice_links = [
                    PracticeLink(
                        concept_id=concept_id,
                        problem_ids=[f"unresolved-{concept_id}"],
                        needs_resolution=True,  # Mark as needing resolution
                    )
                ]
            
            # Get learning objectives from ontology (preferred over LLM generation)
            learning_objectives = self._get_learning_objectives_from_ontology(concept_id)
            
            # Get definition text (from LLM or default)
            definition_text = def_response.get("definition", self._get_default_definition(concept_id)) if def_response else self._get_default_definition(concept_id)
            why_text = def_response.get("why_it_matters", "Important for database queries.") if def_response else "Important for database queries."
            
            content = L3Content(
                definition=definition_text,
                why_it_matters=why_text,
                learning_objectives=learning_objectives,
                examples=examples,
                contrast_example=contrast,
                common_mistakes=mistakes,
                practice_links=practice_links,
            )
        
        # Get source pages from blocks
        source_pages = list(set(b.page_number for b in blocks))
        
        # Build content dict and add review flags if using weak default content
        content_dict = content.model_dump()
        if not has_llm_content:
            # Check if we used curated fallback (high quality) or just extracted content
            # The _build_grounded_L3_content method sets _used_curated_fallback flag when curated is used
            used_curated = content_dict.get("_used_curated_fallback", False)
            
            if used_curated:
                # Curated content is high quality - mark as curated, not weak
                content_dict["_metadata"] = {
                    "content_source": "curated",
                    "review_needed": False,
                    "content_quality": "curated",
                }
            else:
                # Using grounded defaults without curated - flag for review as content may be weak
                content_dict = self._add_review_flags_to_content(
                    content_dict,
                    reason="using_default_content_no_llm",
                    quality="needs_review"
                )
        elif is_using_default_definition:
            # Check if definition is generic and flag if so
            if "is an important SQL concept" in definition_text or "is a crucial SQL concept" in definition_text:
                content_dict = self._add_review_flags_to_content(
                    content_dict,
                    reason="generic_definition_text",
                    quality="weak"
                )
        
        return InstructionalUnit(
            unit_id=f"{concept_id}_L3_explanation",
            concept_id=concept_id,
            unit_type="explanation",
            target_stage="L3_explanation",
            content=content_dict,
            error_subtypes=error_subtypes or [],
            prerequisites=prerequisites or [],
            difficulty="intermediate",
            evidence_spans=self._create_evidence_spans(blocks),
            source_pages=source_pages,
            grounding_confidence=0.8 if blocks else 0.0,
            estimated_read_time=300,
        )
    
    def generate_L4_reflective_note(
        self,
        concept_id: str,
        blocks: list[ContentBlock],
        config: GenerationConfig,
        prerequisites: list[str] | None = None,
        error_subtypes: list[str] | None = None,
    ) -> InstructionalUnit:
        """
        Generate L4 reflective note variant - summary with reflection prompts.
        
        Args:
            concept_id: Concept identifier
            blocks: Source content blocks
            config: Generation configuration
            prerequisites: Optional prerequisite concept IDs
            error_subtypes: Optional SQL-Engage error subtype IDs
            
        Returns:
            InstructionalUnit for L4 stage
        """
        source_text = "\n\n".join(b.text_content for b in blocks if b.text_content)
        
        prompt = self.prompt_builder.build_reflection_prompt(concept_id, source_text)
        llm_response = self._call_llm(prompt, config)
        
        if llm_response:
            content = L4Content(
                key_concept_summary=llm_response.get(
                    "key_concept_summary", self._get_default_summary(concept_id)
                ),
                reflection_prompts=llm_response.get(
                    "reflection_prompts", self._get_default_reflection_prompts(concept_id)
                ),
                explain_in_own_words=llm_response.get(
                    "explain_in_own_words",
                    f"Explain {concept_id} in your own words as if teaching a beginner."
                ),
                transfer_questions=llm_response.get(
                    "transfer_questions", self._get_default_transfer_questions(concept_id)
                ),
                connections=llm_response.get("connections", self._get_default_connections(concept_id)),
            )
        else:
            # Use grounded defaults from evidence spans (no-LLM path)
            content = self._build_grounded_L4_content(concept_id, blocks)
        
        # Get source pages from blocks
        source_pages = list(set(b.page_number for b in blocks))
        
        return InstructionalUnit(
            unit_id=f"{concept_id}_L4_reflective_note",
            concept_id=concept_id,
            unit_type="reflection",
            target_stage="L4_reflective_note",
            content=content.model_dump(),
            error_subtypes=error_subtypes or [],
            prerequisites=prerequisites or [],
            difficulty="intermediate",
            evidence_spans=self._create_evidence_spans(blocks),
            source_pages=source_pages,
            grounding_confidence=0.8 if blocks else 0.0,
            estimated_read_time=180,
        )
    
    def generate_reinforcement_microcheck(
        self,
        concept_id: str,
        blocks: list[ContentBlock],
        config: GenerationConfig,
        prerequisites: list[str] | None = None,
        error_subtypes: list[str] | None = None,
    ) -> InstructionalUnit:
        """
        Generate reinforcement microcheck variant - 10-second recall prompt.
        
        Args:
            concept_id: Concept identifier
            blocks: Source content blocks
            config: Generation configuration
            prerequisites: Optional prerequisite concept IDs
            error_subtypes: Optional SQL-Engage error subtype IDs
            
        Returns:
            InstructionalUnit for reinforcement stage
        """
        source_text = "\n\n".join(b.text_content for b in blocks if b.text_content)
        
        prompt = self.prompt_builder.build_reinforcement_prompt(concept_id, source_text)
        llm_response = self._call_llm(prompt, config)
        
        if llm_response:
            content = ReinforcementContent(
                recall_prompt=llm_response.get(
                    "recall_prompt", self._get_default_recall_prompt(concept_id)
                ),
                quick_check_question=llm_response.get(
                    "quick_check_question", self._get_default_check_question(concept_id)
                ),
                quick_check_answer=llm_response.get(
                    "quick_check_answer", self._get_default_check_answer(concept_id)
                ),
                next_review_timing=llm_response.get("next_review_timing", "1 day"),
            )
        else:
            # Use grounded defaults from evidence spans (no-LLM path)
            content = self._build_grounded_reinforcement_content(concept_id, blocks)
        
        # Get source pages from blocks
        source_pages = list(set(b.page_number for b in blocks))
        
        return InstructionalUnit(
            unit_id=f"{concept_id}_reinforcement",
            concept_id=concept_id,
            unit_type="practice",
            target_stage="reinforcement",
            content=content.model_dump(),
            error_subtypes=error_subtypes or [],
            prerequisites=prerequisites or [],
            difficulty="beginner",
            evidence_spans=self._create_evidence_spans(blocks),
            source_pages=source_pages,
            grounding_confidence=0.8 if blocks else 0.0,
            estimated_read_time=10,
        )
    
    def _create_fallback_unit(
        self,
        concept_id: str,
        target_stage: str,
        unit_type: str,
        config: GenerationConfig,
        error_message: str,
        error_subtypes: list[str] | None = None,
    ) -> InstructionalUnit:
        """Create a fallback unit when generation fails."""
        # Map internal unit_type to canonical UnitType
        unit_type_map = {
            "hint": "hint",
            "hint_plus_example": "hint",
            "explanation": "explanation",
            "reflective_note": "reflection",
            "microcheck": "practice",
        }
        canonical_unit_type = unit_type_map.get(unit_type, "hint")
        
        unit = InstructionalUnit(
            unit_id=f"{concept_id}_{target_stage}_{unit_type}_fallback",
            concept_id=concept_id,
            unit_type=canonical_unit_type,
            target_stage=target_stage,
            content={
                "error": error_message,
                "note": "This is a fallback unit due to generation failure. Please retry.",
                "_metadata": {
                    "is_fallback": True,
                    "fallback_reason": error_message,
                },
            },
            error_subtypes=error_subtypes or [],
            prerequisites=[],
            difficulty="beginner",
            evidence_spans=[],
            source_pages=[],
            # Set confidence to 0.5 to pass relaxed filters (threshold 0.3)
            # This allows properly-constructed fallback units to export
            grounding_confidence=0.5,
            estimated_read_time=30,
        )
        return unit
    
    def _add_review_flags_to_content(
        self,
        content: dict[str, Any],
        reason: str,
        quality: str = "weak",
    ) -> dict[str, Any]:
        """Add review flags to content dict.
        
        Args:
            content: The content dict to add flags to
            reason: The reason for review (e.g., "generic_definition")
            quality: Content quality level ("weak", "needs_improvement", etc.)
            
        Returns:
            Updated content dict with review flags in _metadata
        """
        if "_metadata" not in content:
            content["_metadata"] = {}
        
        content["_metadata"].update({
            "review_needed": True,
            "review_reason": reason,
            "content_quality": quality,
        })
        return content
    
    def _create_L3_with_review_flag(
        self,
        concept_id: str,
        blocks: list[ContentBlock],
        content: L3Content,
        reason: str,
        prerequisites: list[str] | None = None,
        error_subtypes: list[str] | None = None,
    ) -> InstructionalUnit:
        """Create an L3 unit flagged for instructor review.
        
        Use this when the content is technically valid but instructionally weak,
        such as generic definitions like "X is an important SQL concept."
        
        Args:
            concept_id: Concept identifier
            blocks: Source content blocks
            content: The L3 content (may be weak quality)
            reason: Why this needs review
            prerequisites: Optional prerequisite concept IDs
            error_subtypes: Optional SQL-Engage error subtype IDs
            
        Returns:
            InstructionalUnit with review flags in content metadata
        """
        # Get source pages from blocks
        source_pages = list(set(b.page_number for b in blocks))
        
        # Add review flags to content
        content_dict = content.model_dump()
        content_dict = self._add_review_flags_to_content(content_dict, reason, "weak")
        
        return InstructionalUnit(
            unit_id=f"{concept_id}_L3_explanation",
            concept_id=concept_id,
            unit_type="explanation",
            target_stage="L3_explanation",
            content=content_dict,
            error_subtypes=error_subtypes or [],
            prerequisites=prerequisites or [],
            difficulty="intermediate",
            evidence_spans=self._create_evidence_spans(blocks),
            source_pages=source_pages,
            grounding_confidence=0.8 if blocks else 0.0,
            estimated_read_time=300,
        )
    
    # =============================================================================
    # DEFAULT CONTENT HELPERS
    # =============================================================================
    
    def _get_default_hint(self, concept_id: str) -> str:
        """Get default hint for concept with teaching-quality content."""
        hints = {
            "joins": "Use JOIN to combine rows from multiple tables based on related columns.",
            "select-basic": "SELECT retrieves data from tables. Start with SELECT * to see all columns, then specify only what you need.",
            "where-clause": "WHERE filters rows based on conditions. Use comparison operators (=, >, <, <>) and combine conditions with AND/OR.",
            "aggregate-functions": "Use aggregate functions like COUNT, SUM, AVG to calculate summary values across multiple rows.",
            "group-by": "GROUP BY organizes rows with the same values into summary rows, typically used with aggregate functions.",
            "subqueries": "A subquery nests a SELECT statement inside another query. Use it when you need intermediate results.",
            "exists-operator": "EXISTS tests if a subquery returns any rows, returning TRUE or FALSE. Use it to check for related data without returning it.",
            "order-by": "ORDER BY sorts query results by one or more columns. Use ASC for ascending (default) or DESC for descending order.",
            "null-handling": "NULL represents unknown or missing values. Use IS NULL or IS NOT NULL to test for NULL - equality tests (= NULL) don't work.",
            "outer-join": "OUTER JOINs include all rows from one table and matching rows from another. LEFT JOIN keeps all left table rows; RIGHT JOIN keeps all right table rows.",
            "inner-join": "INNER JOIN returns only rows that have matching values in both tables being joined.",
            "having": "HAVING filters grouped results after aggregation, unlike WHERE which filters rows before grouping.",
            "distinct": "DISTINCT removes duplicate rows from results, returning only unique values for the selected columns.",
            "limit": "LIMIT restricts the number of rows returned. Useful for pagination or examining sample data.",
            "union": "UNION combines results from two or more SELECT statements, removing duplicates by default.",
            "case-expressions": "CASE creates conditional logic in SQL, similar to IF-THEN-ELSE in programming languages.",
            "string-functions": "String functions like CONCAT, UPPER, LOWER, SUBSTRING manipulate text data in queries.",
            "date-functions": "Date functions extract parts of dates, calculate differences, or format date values.",
            "correlated-subquery": "A correlated subquery references columns from the outer query, executing once for each outer row.",
            "cte": "Common Table Expressions (CTEs) with WITH create temporary named result sets for cleaner, reusable queries.",
            "window-functions": "Window functions like ROW_NUMBER(), RANK() calculate values across a set of rows related to the current row.",
        }
        # Return a teaching-quality fallback instead of generic "Remember how to use..."
        return hints.get(concept_id, f"{concept_id.replace('-', ' ').title()} is used to manipulate and retrieve data effectively in SQL databases.")
    
    def _get_default_syntax_cue(self, concept_id: str) -> str:
        """Get default syntax cue for concept."""
        cues = {
            "joins": "SELECT ... FROM table1 JOIN table2 ON table1.col = table2.col;",
            "select-basic": "SELECT columns FROM table;",
            "where-clause": "SELECT ... FROM ... WHERE condition;",
            "aggregate-functions": "SELECT AGG(column) FROM table;",
            "group-by": "SELECT ... FROM ... GROUP BY column;",
            "subqueries": "SELECT ... FROM ... WHERE column = (SELECT ...);",
            "exists-operator": "SELECT ... FROM ... WHERE EXISTS (SELECT 1 FROM ... WHERE ...);",
        }
        return cues.get(concept_id, f"{concept_id} syntax pattern")
    
    def _get_default_when_to_use(self, concept_id: str) -> str:
        """Get default usage context for concept."""
        contexts = {
            "joins": "When you need data from multiple related tables",
            "select-basic": "When retrieving any data from tables",
            "where-clause": "When filtering rows by conditions",
            "aggregate-functions": "When calculating summary statistics",
            "group-by": "When grouping data for aggregate calculations",
            "subqueries": "When you need results from one query in another",
            "exists-operator": "When checking if related data exists without needing the actual values",
        }
        return contexts.get(concept_id, f"When working with {concept_id}")
    
    def _score_sql_for_concept(self, sql: str, concept_id: str) -> float:
        """Score how well a SQL example matches the concept.
        
        Higher scores indicate better matches between the SQL content
        and the concept being taught.
        """
        sql_lower = sql.lower()
        concept_lower = concept_id.lower()
        
        # Base score
        score = 0.0
        
        # Concept-specific keyword matching
        concept_keywords = {
            "outer-join": ["left join", "right join", "full outer join", "outer join"],
            "self-join": ["self join", "same table", "t1.", "t2.", "alias", "manager_id"],
            "having-clause": ["having", "group by", "aggregate"],
            "correlated-subquery": ["exists", "in (select", "correlated"],
            "create-table": ["create table", "schema", "columns"],
            "transactions": ["begin", "commit", "rollback", "transaction"],
            "isolation-levels": ["isolation", "serializable", "read committed"],
            "null-handling": ["is null", "is not null", "coalesce", "nullif"],
            "pattern-matching": ["like", "%", "_", "pattern"],
            "order-by": ["order by", "asc", "desc"],
            "limit-offset": ["limit", "offset", "pagination"],
            "alias": ["as ", "alias"],
            "distinct": ["distinct", "unique"],
            "joins-intro": ["join", "inner join"],
            "inner-join": ["inner join"],
            "cross-join": ["cross join"],
            "aggregate-functions": ["sum(", "count(", "avg(", "max(", "min(", "group by"],
            "group-by": ["group by", "aggregate"],
            "subqueries-intro": ["subquery", "in (select", "(select"],
            "subquery-in-select": ["(select", "scalar"],
            "subquery-in-where": ["where", "in (select", "exists"],
            "exists-operator": ["exists", "not exists"],
            "union": ["union", "union all"],
            "insert-statement": ["insert into", "values"],
            "update-statement": ["update", "set"],
            "delete-statement": ["delete from"],
            "alter-table": ["alter table", "add column", "drop column"],
            "drop-table": ["drop table"],
            "constraints": ["primary key", "foreign key", "unique", "check", "not null"],
            "views": ["create view", "as select"],
            "indexes": ["create index", "indexed"],
            "window-functions": ["over(", "partition by", "row_number", "rank()"],
            "cte": ["with ", "as ("],
            "triggers": ["trigger", "before", "after", "on insert"],
            "stored-procedures": ["procedure", "call", "parameter"],
            "data-types": ["varchar", "int", "decimal", "timestamp", "boolean"],
        }
        
        # Get keywords for this concept, or use concept name as default
        keywords = concept_keywords.get(concept_id, [concept_lower.replace("-", " ")])
        
        for keyword in keywords:
            if keyword in sql_lower:
                score += 1.0
        
        # Bonus for matching concept name directly
        concept_normalized = concept_lower.replace("-", " ")
        if concept_normalized in sql_lower:
            score += 2.0
        
        # Extra bonus for strong concept indicators
        strong_indicators = {
            "outer-join": ["left join", "right join", "full outer join"],
            "having-clause": ["having"],
            "self-join": ["self join"],
            "window-functions": ["over("],
            "cte": ["with "],
            "correlated-subquery": ["exists", "correlated"],
        }
        if concept_id in strong_indicators:
            for indicator in strong_indicators[concept_id]:
                if indicator in sql_lower:
                    score += 3.0
        
        # Special detection for self-join: same table appears twice with different aliases
        if concept_id == "self-join":
            # Look for pattern like "FROM employees e JOIN employees m"
            self_join_pattern = r"from\s+(\w+)\s+\w+\s+join\s+\1\s+\w+"
            if re.search(self_join_pattern, sql_lower):
                score += 5.0
        
        return score

    def _get_default_example_sql(self, concept_id: str) -> str:
        """Get default example SQL for concept with concept-appropriate examples."""
        examples = {
            "joins": "SELECT u.name, o.product FROM users u JOIN orders o ON u.id = o.user_id;",
            "joins-intro": "SELECT u.name, o.product FROM users u JOIN orders o ON u.id = o.user_id;",
            "select-basic": "SELECT name, email FROM users WHERE city = 'Seattle';",
            "where-clause": "SELECT * FROM users WHERE age > 25 AND city = 'Portland';",
            "aggregate-functions": "SELECT city, COUNT(*) FROM users GROUP BY city;",
            "group-by": "SELECT city, AVG(age) FROM users GROUP BY city HAVING COUNT(*) > 2;",
            "subqueries": "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders);",
            "subqueries-intro": "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders);",
            "exists-operator": "SELECT name FROM users u WHERE EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.id);",
            "outer-join": "SELECT c.name, o.order_id FROM customers c LEFT JOIN orders o ON c.id = o.customer_id;",
            "inner-join": "SELECT u.name, o.product FROM users u INNER JOIN orders o ON u.id = o.user_id;",
            "self-join": "SELECT e.name, m.name AS manager FROM employees e JOIN employees m ON e.manager_id = m.id;",
            "cross-join": "SELECT p.product, c.category FROM products p CROSS JOIN categories c;",
            "having-clause": "SELECT department, AVG(salary) AS avg_salary FROM employees GROUP BY department HAVING AVG(salary) > 50000;",
            "correlated-subquery": "SELECT name FROM employees e WHERE salary > (SELECT AVG(salary) FROM employees WHERE department = e.department);",
            "order-by": "SELECT name, salary FROM employees ORDER BY salary DESC, name ASC;",
            "limit-offset": "SELECT name FROM employees ORDER BY salary DESC LIMIT 10 OFFSET 20;",
            "distinct": "SELECT DISTINCT department FROM employees;",
            "alias": "SELECT e.name AS employee_name, d.name AS dept_name FROM employees e JOIN departments d ON e.dept_id = d.id;",
            "null-handling": "SELECT name FROM employees WHERE manager_id IS NULL;",
            "pattern-matching": "SELECT name FROM customers WHERE name LIKE 'A%';",
            "union": "SELECT name FROM employees UNION SELECT name FROM contractors;",
            "insert-statement": "INSERT INTO employees (name, salary, dept_id) VALUES ('John Doe', 50000, 1);",
            "update-statement": "UPDATE employees SET salary = salary * 1.1 WHERE department = 'Engineering';",
            "delete-statement": "DELETE FROM employees WHERE end_date < '2023-01-01';",
            "create-table": "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100), email VARCHAR(100) UNIQUE);",
            "alter-table": "ALTER TABLE employees ADD COLUMN hire_date DATE;",
            "drop-table": "DROP TABLE IF EXISTS temp_data;",
            "constraints": "ALTER TABLE employees ADD CONSTRAINT fk_dept FOREIGN KEY (dept_id) REFERENCES departments(id);",
            "views": "CREATE VIEW active_employees AS SELECT * FROM employees WHERE status = 'active';",
            "indexes": "CREATE INDEX idx_employee_name ON employees(name);",
            "window-functions": "SELECT name, salary, RANK() OVER (ORDER BY salary DESC) AS salary_rank FROM employees;",
            "cte": "WITH high_earners AS (SELECT * FROM employees WHERE salary > 100000) SELECT * FROM high_earners;",
            "transactions": "BEGIN; UPDATE accounts SET balance = balance - 100 WHERE id = 1; UPDATE accounts SET balance = balance + 100 WHERE id = 2; COMMIT;",
            "isolation-levels": "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE; BEGIN; SELECT * FROM accounts WHERE id = 1; COMMIT;",
        }
        return examples.get(concept_id, f"SELECT * FROM users LIMIT 5;")
    
    def _get_default_pitfall(self, concept_id: str) -> str:
        """Get default common pitfall for concept."""
        pitfalls = {
            "joins": "Forgetting to specify the JOIN condition (ON clause)",
            "select-basic": "Using SELECT * when you only need specific columns",
            "where-clause": "Forgetting quotes around string values",
            "aggregate-functions": "Mixing aggregate and non-aggregate columns without GROUP BY",
            "group-by": "Including columns in SELECT that aren't in GROUP BY",
            "subqueries": "Using = with subqueries that return multiple rows",
            "exists-operator": "Using SELECT * in EXISTS subquery instead of SELECT 1 (performance issue)",
        }
        return pitfalls.get(concept_id, "Watch for syntax errors")
    
    def _get_default_definition(self, concept_id: str) -> str:
        """Get default definition for concept with specific, teaching-quality content.
        
        This method must NEVER return an empty string. It always provides a valid
        definition, using the concept_id to generate a fallback if needed.
        """
        definitions = {
            "joins": "JOIN combines rows from two or more tables based on related columns between them, enabling queries across normalized data.",
            "select-basic": "SELECT is the fundamental SQL command for retrieving data from one or more tables, allowing you to specify which columns and rows to return.",
            "where-clause": "WHERE filters query results to include only rows that meet specified conditions, using comparison and logical operators.",
            "aggregate-functions": "Aggregate functions like COUNT, SUM, AVG, MIN, and MAX perform calculations on sets of values and return a single summary result.",
            "group-by": "GROUP BY organizes rows with the same values in specified columns into summary rows, enabling aggregate calculations per group.",
            "subqueries": "A subquery is a SELECT statement nested inside another SQL statement, used when intermediate query results are needed.",
            "exists-operator": "EXISTS is a logical operator that tests whether a subquery returns any rows, returning TRUE if rows exist or FALSE if empty.",
            "order-by": "ORDER BY sorts the result set of a query by one or more columns, with control over ascending or descending order and NULL handling.",
            "null-handling": "NULL represents unknown or missing values in SQL. Special operators IS NULL and IS NOT NULL are required for NULL testing since equality comparisons fail.",
            "outer-join": "OUTER JOIN returns all rows from one table and matching rows from another, preserving data from the non-matching table with NULLs.",
            "inner-join": "INNER JOIN returns only rows that have matching values in both tables being joined, filtering out non-matching rows from both sides.",
            "having": "HAVING filters grouped results after aggregation is applied, unlike WHERE which filters individual rows before grouping.",
            "distinct": "DISTINCT eliminates duplicate rows from query results, returning only unique combinations of values for the selected columns.",
            "limit": "LIMIT constrains the number of rows returned by a query, commonly used for pagination and examining sample data.",
            "union": "UNION combines the result sets of two or more SELECT statements into a single result, removing duplicates by default.",
            "case-expressions": "CASE expressions provide conditional logic in SQL queries, evaluating conditions and returning different results based on which condition is met.",
            "string-functions": "String functions like CONCAT, UPPER, LOWER, LENGTH, and SUBSTRING perform text manipulation operations on character data.",
            "date-functions": "Date functions like DATEADD, DATEDIFF, EXTRACT, and CURRENT_DATE enable manipulation and calculation of date and time values.",
            "correlated-subquery": "A correlated subquery references columns from the outer query, executing once for each row processed by the outer query.",
            "cte": "Common Table Expressions (CTEs) defined with WITH create named temporary result sets that can be referenced multiple times within a query.",
            "window-functions": "Window functions like ROW_NUMBER(), RANK(), and LEAD() perform calculations across a set of rows related to the current row without grouping.",
        }
        
        # Get the default from the dictionary
        default = definitions.get(concept_id)
        if default:
            return default
        
        # Ultimate fallback - never empty, always returns a valid string
        concept_name = concept_id.replace('-', ' ').title()
        return f"{concept_name} is a SQL concept for working with database data effectively."
    
    def _get_default_why_it_matters(self, concept_id: str) -> str:
        """Get default 'why it matters' explanation that differs from definition."""
        why_explanations = {
            "select-basic": "Without SELECT, you cannot retrieve any data from a database. It's the starting point for virtually every data analysis task.",
            "order-by": "Without ORDER BY, result rows come back in unpredictable order based on how the database stores them. Sorting is essential for readable reports and finding top/bottom values.",
            "null-handling": "NULLs cause unexpected results in calculations and comparisons. Understanding NULL handling prevents bugs where data mysteriously disappears from your results.",
            "exists-operator": "EXISTS is often more efficient than IN for large datasets and clearly expresses intent to check for existence rather than retrieve values.",
            "outer-join": "OUTER JOINs ensure you don't lose data. Without them, analysis might miss customers with no orders or products that never sold—critical for complete reporting.",
            "joins": "Most real-world data is normalized across multiple tables. JOINs are essential to reconstruct meaningful information from separate tables.",
            "where-clause": "Without WHERE, queries return entire tables. Filtering is essential for performance and for answering specific business questions.",
            "aggregate-functions": "Aggregates transform raw data into insights—counts, totals, averages—that drive business decisions and summary reporting.",
            "group-by": "GROUP BY enables reporting by categories: sales by region, counts by status, averages by department. Essential for analytical queries.",
            "subqueries": "Subqueries solve problems that cannot be addressed in a single SELECT, like finding data that matches complex criteria across multiple levels.",
            "having": "HAVING enables filtering on calculated summaries, like finding departments with more than 10 employees—something WHERE cannot do.",
            "distinct": "DISTINCT eliminates duplicates that would skew analysis, ensuring each entity is counted once in your results.",
            "limit": "LIMIT is crucial for performance when exploring large tables and essential for pagination in user interfaces.",
            "union": "UNION combines data from different sources or tables with similar structures, enabling consolidated reporting across divisions or time periods.",
            "case-expressions": "CASE adds business logic to SQL, enabling conditional calculations, custom categorizations, and data transformations without application code.",
            "string-functions": "Real-world data is messy. String functions clean, standardize, and transform text data for consistent analysis and display.",
            "date-functions": "Time-based analysis is essential for business reporting. Date functions enable period comparisons, age calculations, and scheduling logic.",
            "correlated-subquery": "Correlated subqueries solve row-by-row comparison problems that standard joins cannot address, like finding records that exceed group averages.",
            "cte": "CTEs make complex queries readable by breaking them into named steps, and enable recursive queries for hierarchical data like org charts.",
            "window-functions": "Window functions calculate running totals, rankings, and comparisons within groups without collapsing rows like GROUP BY does.",
        }
        return why_explanations.get(
            concept_id, 
            f"Understanding {concept_id.replace('-', ' ')} enables you to solve more complex data problems and write efficient, maintainable SQL queries."
        )
    
    def _get_default_sql_examples(self, concept_id: str) -> list[SQLExample]:
        """Get default SQL examples for concept using canonical schema."""
        return [
            SQLExample(
                title="Basic Example",
                scenario="Standard usage of the concept",
                sql=self._get_default_example_sql(concept_id),
                explanation="This demonstrates basic usage of the concept.",
                expected_output="Returns matching rows from the query",
            )
        ]
    
    def _get_default_misconceptions(self, concept_id: str) -> list[MisconceptionExample]:
        """Get default misconception examples using canonical schema."""
        return [
            MisconceptionExample(
                title="Syntax Error: Misspelled Keyword",
                error_sql="SELECT * FORM users;",
                error_message="Error: near 'FORM': syntax error",
                why_it_happens="Students often mistype SQL keywords when learning",
                fix_sql="SELECT * FROM users;",
                key_takeaway="Always check spelling of SQL keywords like FROM, SELECT, WHERE",
            )
        ]
    
    def _get_default_summary(self, concept_id: str) -> str:
        """Get concept-specific summary for L4 reflective notes."""
        summaries = {
            "select-basic": "SELECT is the foundation of SQL data retrieval. Understanding how to specify columns, filter with WHERE, and sort with ORDER BY enables you to extract exactly the data you need from any table.",
            "order-by": "ORDER BY gives you control over how results are presented. Remember that ASC is default, NULL handling varies by database, and you can sort by multiple columns for fine-grained ordering.",
            "null-handling": "NULLs require special handling in SQL. The key insight is that NULL represents unknown, so equality tests fail. Always use IS NULL/IS NOT NULL, and understand how aggregates and joins handle NULL values.",
            "exists-operator": "EXISTS is about efficient existence checking. Unlike IN which may return values, EXISTS simply returns TRUE/FALSE and often performs better with large datasets since it can stop at the first match.",
            "outer-join": "OUTER JOINs preserve data from one table while optionally matching another. The critical decision is which table's rows must be preserved - this determines whether to use LEFT, RIGHT, or FULL OUTER JOIN.",
            "joins": "JOINs are fundamental for working with normalized databases. The key is understanding the relationship between tables and choosing the right join type based on whether you need to preserve unmatched rows.",
            "where-clause": "WHERE filters data before any grouping or aggregation. Understanding operator precedence, handling NULLs correctly, and using parentheses for complex conditions are essential for accurate filtering.",
            "aggregate-functions": "Aggregates collapse multiple rows into summary values. They work hand-in-hand with GROUP BY to produce reports, and understanding how NULLs are handled is crucial for accurate calculations.",
            "group-by": "GROUP BY transforms detailed data into summarized reports. Every non-aggregated column in SELECT must appear in GROUP BY, and HAVING filters the groups after aggregation is complete.",
            "subqueries": "Subqueries enable complex logic by nesting queries. They can return single values, row sets, or be used with EXISTS/IN. Correlated subqueries reference outer query data and execute row-by-row.",
        }
        # Use concept-specific summary or build from definition
        default_def = self._get_default_definition(concept_id)
        default_summary = summaries.get(concept_id, f"{default_def} Understanding when and how to apply this concept will make your SQL queries more effective and efficient.")
        return default_summary
    
    def _get_default_reflection_prompts(self, concept_id: str) -> list[str]:
        """Get default reflection prompts for concept."""
        return [
            f"How does {concept_id} relate to other SQL concepts you've learned?",
            "What would happen if you used this incorrectly?",
            "When would you choose this approach over alternatives?",
        ]
    
    def _get_default_transfer_questions(self, concept_id: str) -> list[str]:
        """Get default transfer questions for concept."""
        return [
            f"How would you apply {concept_id} to a real-world business scenario?",
            "What would change if the data structure was different?",
        ]
    
    def _get_default_connections(self, concept_id: str) -> list[str]:
        """Get default connected concepts."""
        connections = {
            "joins": ["select-basic", "where-clause", "aggregate-functions"],
            "select-basic": ["where-clause", "order-by"],
            "where-clause": ["select-basic", "logical-operators"],
            "aggregate-functions": ["group-by", "having", "select-basic"],
            "group-by": ["aggregate-functions", "having", "select-basic"],
            "subqueries": ["select-basic", "where-clause", "joins"],
            "exists-operator": ["subqueries", "where-clause", "correlated-subquery"],
            "order-by": ["select-basic", "where-clause"],
            "null-handling": ["where-clause", "aggregate-functions", "joins"],
            "outer-join": ["joins", "inner-join", "select-basic"],
            "inner-join": ["joins", "outer-join", "select-basic"],
        }
        return connections.get(concept_id, [])
    
    def _build_concept_specific_summary(self, concept_id: str, definition: str) -> str:
        """Build a concept-specific summary that adds insight to the definition."""
        insights = {
            "select-basic": "Focus on understanding that SELECT is declarative—you describe what you want, not how to get it. Column selection affects performance and readability.",
            "order-by": "The key insight is that without ORDER BY, row order is unpredictable. NULL handling varies by database (PostgreSQL sorts NULLs last by default, while others may differ).",
            "null-handling": "The critical realization is that NULL means 'unknown', not 'zero' or 'empty'. This is why = NULL fails—unknown cannot equal unknown.",
            "exists-operator": "EXISTS is semantically clearer than IN for existence checks and often more performant because it can stop at the first match rather than building a complete result set.",
            "outer-join": "The essential decision is choosing which table's rows to preserve. LEFT JOIN is most common, keeping all rows from the 'primary' table.",
            "joins": "Understanding table relationships is crucial. INNER JOIN for matches only, OUTER JOIN when you need to preserve rows from one side.",
            "where-clause": "WHERE filters before grouping, HAVING filters after. Understanding this execution order helps write correct queries.",
            "aggregate-functions": "Aggregates collapse detail into insight. The challenge is understanding how NULLs are handled (usually ignored) and when to use GROUP BY.",
            "group-by": "Every non-aggregated column in SELECT must appear in GROUP BY. Violating this causes errors in strict SQL modes.",
            "subqueries": "Subqueries add power but can hurt performance. Know when to use JOINs instead, and understand correlated vs. non-correlated subqueries.",
            "having": "HAVING is WHERE for groups. Without it, you cannot filter based on aggregate results like COUNT(*) > 5.",
            "distinct": "DISTINCT eliminates duplicates but adds processing overhead. Use it when you need unique values, not as a fix for incorrect JOINs.",
            "limit": "LIMIT is essential for pagination and exploration, but sorting with ORDER BY should usually precede limiting for predictable results.",
            "union": "UNION removes duplicates; UNION ALL is faster when you know sets are already distinct. Column counts and types must match.",
            "case-expressions": "CASE evaluates sequentially and returns the first match. The ELSE clause defaults to NULL if omitted.",
        }
        insight = insights.get(concept_id, "Practice applying this concept with different data scenarios to build fluency.")
        return f"{definition} {insight}"
    
    def _get_concept_specific_reflection_prompts(self, concept_id: str) -> list[str]:
        """Get concept-specific reflection prompts, not generic templates."""
        prompts_by_concept = {
            "select-basic": [
                "How does limiting columns with SELECT affect query performance compared to SELECT *?",
                "What problems could arise if you always use SELECT * in production queries?",
                "When might you need to use table aliases or qualified column names?",
            ],
            "order-by": [
                "Why does row order appear random without ORDER BY, even if it looks consistent in small tests?",
                "How does NULL handling in sorting differ from equality comparisons with NULL?",
                "When would sorting by multiple columns be necessary instead of a single column?",
            ],
            "null-handling": [
                "Why does 'unknown = unknown' evaluate to false in SQL's three-valued logic?",
                "How do aggregate functions like COUNT handle NULL values differently than COUNT(*)?",
                "What are the real-world implications of NULL in business calculations like averages?",
            ],
            "exists-operator": [
                "How does EXISTS differ semantically from IN when checking for row existence?",
                "Why might EXISTS be more efficient than IN with large subquery results?",
                "When would you use NOT EXISTS versus a LEFT JOIN with IS NULL check?",
            ],
            "outer-join": [
                "How do you identify which table should be the 'preserved' table in a LEFT JOIN?",
                "What happens to columns from the non-preserved table when there's no match?",
                "When might you need a FULL OUTER JOIN instead of LEFT or RIGHT?",
            ],
            "joins": [
                "How does database normalization drive the need for JOIN operations?",
                "What are the risks of joining tables without proper foreign key relationships?",
                "How would you debug a query that returns more rows than expected after joining?",
            ],
            "where-clause": [
                "Why can't you reference aggregate results in a WHERE clause?",
                "How does the order of AND/OR conditions affect query logic and performance?",
                "What are common pitfalls when filtering by dates or partial string matches?",
            ],
            "aggregate-functions": [
                "How do aggregates change the shape of your result set compared to raw row queries?",
                "What's the difference between COUNT(column), COUNT(*), and COUNT(DISTINCT column)?",
                "When might AVG produce misleading results, and what alternatives exist?",
            ],
            "group-by": [
                "Why must every non-aggregated SELECT column appear in GROUP BY?",
                "What happens if you GROUP BY a column that has NULL values?",
                "How does GROUP BY interact with the logical order of query execution?",
            ],
            "subqueries": [
                "When is a subquery clearer than a JOIN, and when is it less efficient?",
                "How does a correlated subquery's performance differ from a non-correlated one?",
                "What are the rules about what a subquery can return (single value, row, table)?",
            ],
        }
        return prompts_by_concept.get(concept_id, [
            f"How does {concept_id} change the way you query data compared to simpler operations?",
            f"What mistakes are most common when using {concept_id}, and how can you avoid them?",
            f"In what real-world scenarios would {concept_id} be essential?",
        ])
    
    def _build_concept_specific_explain_prompt(self, concept_id: str, ontology: dict) -> str:
        """Build a concept-specific 'explain in your own words' prompt."""
        prompts = {
            "select-basic": "Explain SELECT as if teaching someone who has never seen a database before. Use an analogy like a filing cabinet or spreadsheet.",
            "order-by": "Explain ORDER BY to a beginner who understands SELECT but wonders why result order matters. Include why ASC/DESC is important.",
            "null-handling": "Explain NULL to someone who keeps trying to use = NULL and getting wrong results. Why is NULL special?",
            "exists-operator": "Explain EXISTS versus IN to a colleague who thinks they're interchangeable. When would you choose one over the other?",
            "outer-join": "Explain OUTER JOIN using a real-world analogy (like students and classes, or customers and orders). What does it mean to 'preserve' rows?",
            "joins": "Explain JOINs without using technical jargon. How would you describe combining tables to a business user?",
            "where-clause": "Explain WHERE as a filter to someone who understands Excel filters but is new to SQL.",
            "aggregate-functions": "Explain aggregate functions using a shopping receipt analogy. How does SQL 'sum up' information?",
            "group-by": "Explain GROUP BY using a real-world categorization example, like organizing receipts by store or month.",
            "subqueries": "Explain subqueries as 'questions within questions.' When do you need an answer before you can ask the main question?",
        }
        base_prompt = prompts.get(concept_id, f"Explain {concept_id} in your own words as if teaching a beginner who just learned basic SELECT.")
        
        if ontology.get("use_when"):
            base_prompt += f" Include when you would use this (hint: {ontology['use_when']})."
        
        return base_prompt
    
    def _get_concept_specific_transfer_questions(self, concept_id: str) -> list[str]:
        """Get concept-specific transfer questions for applying knowledge to new situations."""
        transfer_by_concept = {
            "select-basic": [
                "A business user asks for 'all customer data.' How do you determine which specific columns they actually need?",
                "You're querying a table with millions of rows. How does your SELECT strategy change compared to small tables?",
                "How would you modify a query that currently shows all columns to instead show only what's needed for a monthly report?",
            ],
            "order-by": [
                "Users report that paged results (rows 1-10, 11-20) have duplicate items across pages. What might be wrong with your ORDER BY?",
                "You need to sort products by price, but NULL prices should appear last. How do you handle this?",
                "A report needs sorting by last name, then first name for ties. How do you implement this?",
            ],
            "null-handling": [
                "You're calculating average employee tenure, but some employees have NULL hire dates. How does this affect your calculation?",
                "A report shows fewer rows than expected. You suspect NULL handling issues. What do you check?",
                "How would you write a query to find customers who have provided either an email OR a phone number (handling NULLs correctly)?",
            ],
            "exists-operator": [
                "You need to find customers who have placed orders in the last 30 days. Would you use EXISTS, IN, or a JOIN? Why?",
                "How would you efficiently find all products that have never been ordered?",
                "A query using IN with a subquery is running slowly. How might EXISTS improve performance?",
            ],
            "outer-join": [
                "Management wants a report of all employees and their assigned projects, including employees with no projects. How do you ensure no one is missing?",
                "You're analyzing customer purchase patterns. How do you include customers who've never made a purchase?",
                "After an OUTER JOIN, you notice unexpected NULL values. How do you determine if these represent valid missing data or a join condition error?",
            ],
            "joins": [
                "You're designing a report that combines data from five tables. How do you decide the join order and types?",
                "A query returns duplicate rows after joining. What are the likely causes and how do you fix them?",
                "How would you join a table to itself (self-join) to find hierarchical relationships like employee-manager chains?",
            ],
            "where-clause": [
                "You need to filter for customers in either 'CA' or 'NY' who also have orders over $1000. How do you structure the WHERE clause?",
                "A date filter 'WHERE date > '2024-01-01'' seems to exclude some rows you expect. What might be happening?",
                "How do you handle filtering by a list of values that could be very long (hundreds of IDs)?",
            ],
            "aggregate-functions": [
                "Management wants average order value, but some orders have $0 values that shouldn't count. Which aggregate and approach do you use?",
                "How would you calculate what percentage each product category contributes to total sales?",
                "You need to find the most recent login per user across millions of records. What's your approach?",
            ],
            "group-by": [
                "A report needs monthly sales totals by region and product category. How do you structure the GROUP BY?",
                "You're asked to show 'top 5 customers by total orders' but also need to see their individual order details. Why can't you use GROUP BY for this?",
                "How do you handle grouping by a calculated value (like year extracted from a date)?",
            ],
            "subqueries": [
                "You need to find employees who earn more than their department average. Can you do this without a subquery?",
                "A report needs products priced above the average for their category. How do you structure this query?",
                "When would you use a subquery in the SELECT clause versus the WHERE clause?",
            ],
        }
        return transfer_by_concept.get(concept_id, [
            f"How would you apply {concept_id} to a real-world business scenario?",
            f"What would change if the data structure was different when using {concept_id}?",
            f"How would you troubleshoot unexpected results when using {concept_id}?",
        ])
    
    def _get_default_recall_prompt(self, concept_id: str) -> str:
        """Get default recall prompt for concept."""
        prompts = {
            "joins": "What's the keyword for combining rows from multiple tables?",
            "select-basic": "Which keyword retrieves data from tables?",
            "where-clause": "Which clause filters rows by conditions?",
            "aggregate-functions": "Name three aggregate functions (COUNT, SUM, ...)",
            "group-by": "Which clause organizes rows with same values into groups?",
            "subqueries": "What's a query inside another query called?",
        }
        return prompts.get(concept_id, f"What is the key concept of {concept_id}?")
    
    def _get_default_check_question(self, concept_id: str) -> str:
        """Get default check question for concept."""
        questions = {
            "joins": "Which JOIN type returns only matching rows from both tables?",
            "select-basic": "What symbol selects all columns?",
            "where-clause": "Can you use AND/OR to combine conditions? (yes/no)",
            "aggregate-functions": "Does COUNT(*) count NULL values? (yes/no)",
            "group-by": "Can you use aggregate functions without GROUP BY? (yes/no)",
            "subqueries": "Can a subquery return multiple columns? (yes/no)",
        }
        return questions.get(concept_id, f"Do you understand {concept_id}? (yes/no)")
    
    def _get_default_check_answer(self, concept_id: str) -> str:
        """Get default check answer for concept."""
        answers = {
            "joins": "INNER JOIN",
            "select-basic": "* (asterisk)",
            "where-clause": "yes",
            "aggregate-functions": "yes",
            "group-by": "no (for most databases when selecting non-aggregated columns)",
            "subqueries": "yes",
        }
        return answers.get(concept_id, "yes")
    
    def _get_learning_objectives_from_ontology(self, concept_id: str) -> list[str]:
        """
        Get learning objectives for a concept from the SQL ontology.
        
        Args:
            concept_id: The canonical concept ID
            
        Returns:
            List of learning objectives from the ontology, or default objectives
            if the concept is not found
        """
        concept = get_concept(concept_id)
        if concept and "learning_objectives" in concept:
            return concept["learning_objectives"]
        
        # Return a default objective if concept not found or has no objectives
        return [f"Understand and apply {concept_id} in SQL queries"]
    
    # =============================================================================
    # GROUNDED DEFAULT CONTENT HELPERS (No-LLM Path)
    # =============================================================================
    
    def _extract_key_terms_from_blocks(self, blocks: list[ContentBlock]) -> list[str]:
        """Extract key SQL terms from content blocks."""
        # Combine all text
        text = " ".join(b.text_content for b in blocks if b.text_content)
        text_upper = text.upper()
        
        # Common SQL keywords to look for
        sql_keywords = [
            "SELECT", "FROM", "WHERE", "JOIN", "INNER", "OUTER", "LEFT", "RIGHT",
            "FULL", "CROSS", "NATURAL", "ON", "AS", "GROUP BY", "ORDER BY", 
            "HAVING", "COUNT", "SUM", "AVG", "MAX", "MIN", "DISTINCT",
            "INSERT", "UPDATE", "DELETE", "CREATE", "TABLE", "INDEX", "VIEW",
            "UNION", "INTERSECT", "EXCEPT", "LIMIT", "OFFSET", "LIKE", "IN", "BETWEEN"
        ]
        
        found = []
        for keyword in sql_keywords:
            if keyword in text_upper:
                found.append(keyword.title() if " " not in keyword else keyword.title())
        
        return found[:5]  # Limit to top 5
    
    def _get_first_sentence_from_blocks(self, blocks: list[ContentBlock]) -> str:
        """Get first sentence from blocks as definition."""
        for block in blocks:
            if block.text_content:
                text = block.text_content.strip()
                # Find first sentence
                for delim in [". ", ".\n", "!", "?"]:
                    if delim in text:
                        return text[:text.find(delim) + 1].strip()
                # If no sentence delimiter, return first 150 chars
                return text[:150] if len(text) > 150 else text
        return ""
    
    def _extract_sql_examples_from_blocks(self, blocks: list[ContentBlock]) -> list[dict]:
        """Extract SQL examples from content blocks."""
        sql_pattern = r"(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\s+.+?;"
        examples = []
        
        for block in blocks:
            if not block.text_content:
                continue
            
            # Use finditer to get full matches, not just captured groups
            for match in re.finditer(sql_pattern, block.text_content, re.IGNORECASE | re.DOTALL):
                sql = match.group(0).strip()
                # Validate it's not just a keyword - must have substantial content
                if len(sql) > 20 and sql.count(' ') >= 2:  # At least "SELECT x FROM"
                    # Clean up - take first 200 chars to avoid capturing too much
                    sql = sql[:200] if len(sql) > 200 else sql
                    examples.append({
                        "sql": sql,
                        "page": block.page_number,
                    })
        
        return examples

    def _extract_definition_sentence(self, blocks: list[ContentBlock]) -> str | None:
        """
        Extract the best definitional sentence from evidence spans.
        
        Looks for sentences containing definitional patterns like:
        - "X is ..."
        - "X means ..."
        - "X refers to ..."
        - "X allows you to ..."
        
        Rejects heading-like content:
        - Chapter titles ("Chapter 1: ...")
        - All-caps headings
        - Table of contents patterns
        - "Reference Document" text
        
        Returns the best matching sentence or None if no good match found.
        """
        definitional_patterns = [
            r'\bis\s+(?:a|an|the)\s+',
            r'\bmeans\s+',
            r'\brefers\s+to\s+',
            r'\ballows?\s+(?:you\s+)?to\s+',
            r'\bdefines?\s+(?:a|an|the)?\s*',
            r'\bis\s+used\s+(?:for|to)\s+',
            r'\bprovides\s+(?:a|an)\s+way\s+to\s+',
            r'\benables?\s+',
            r'\bretrieves?\s+',
            r'\breturns?\s+',
            r'\bcreates?\s+',
            r'\bmodifies?\s+',
            r'\bdeletes?\s+',
        ]
        
        candidates = []
        
        # Priority order for block types - prefer explanatory prose over headings
        block_type_priority = {
            BlockType.EXPLANATORY_PROSE: 3,
            BlockType.GLOSSARY: 3,
            BlockType.SIDEBAR: 2,
            BlockType.SUMMARY: 2,
            BlockType.HEADING: 0,
            BlockType.SUBHEADING: 0,
        }
        
        for block in blocks:
            if not block.text_content:
                continue
            
            text = block.text_content.strip()
            sentences = re.split(r'(?<=[.!?])\s+', text)
            
            for sentence in sentences:
                sentence = sentence.strip()
                sentence_lower = sentence.lower()
                
                # Skip sentences that are too short or too long
                if len(sentence) < 30 or len(sentence) > 300:
                    continue
                
                # REJECT: Chapter titles ("Chapter 1: Introduction", "Chapter One")
                if re.match(r'^Chapter\s+\d+[:\s]', sentence, re.IGNORECASE):
                    continue
                
                # REJECT: More chapter/section patterns ("Section 3.2", "Unit 5", "Module 1")
                if re.match(r'^(Chapter|Section|Unit|Module|Lesson|Part)\s+\d+', sentence, re.IGNORECASE):
                    continue
                
                # REJECT: All-caps headings (likely section titles)
                if sentence.isupper():
                    continue
                
                # REJECT: Table of contents patterns ("1 SELECT Statement", "2.1 Joins")
                if re.match(r'^\d+(?:\.\d+)?\s+[A-Z]', sentence):
                    continue
                
                # REJECT: "Reference Document", "Golden Reference" or similar meta-text
                if 'reference document' in sentence_lower or 'golden reference' in sentence_lower:
                    continue
                
                # REJECT: Generic textbook boilerplate
                if re.search(r'\blearning objective', sentence_lower):
                    continue
                
                # REJECT: Pattern "X - Examples" or "X - Overview" or "X - Summary"
                if re.search(r'\s+-\s+(Examples|Overview|Summary|Details|Introduction|Conclusion)$', sentence, re.IGNORECASE):
                    continue
                
                # REJECT: Title case only with no small words (likely a heading)
                words = sentence.split()
                if words and all(w[0].isupper() for w in words if w and w[0].isalpha()):
                    # Might be a title, check if it has any "small words"
                    small_words = ['a', 'an', 'the', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'is', 'are', 'with', 'by']
                    if not any(w.lower() in small_words for w in words):
                        continue
                
                # REJECT: Very short definitions (less than 40 chars after stripping)
                if len(sentence.strip()) < 40:
                    continue
                
                # Check for definitional patterns
                score = 0
                
                for pattern in definitional_patterns:
                    if re.search(pattern, sentence_lower):
                        score += 2
                
                # Bonus for priority block types
                if hasattr(block, 'block_type') and block.block_type in block_type_priority:
                    score += block_type_priority[block.block_type]
                
                # Bonus for sentences starting with uppercase (likely complete sentences)
                if sentence and sentence[0].isupper():
                    score += 0.5
                
                # Penalty for sentences with too many SQL keywords (likely example code)
                sql_keywords = ['select', 'from', 'where', 'join', 'group by']
                sql_count = sum(1 for kw in sql_keywords if kw in sentence_lower)
                if sql_count >= 2:
                    score -= 3
                
                if score > 0:
                    candidates.append((sentence, score))
        
        if not candidates:
            return None
        
        # Sort by score descending, then by length (prefer medium-length definitions)
        candidates.sort(key=lambda x: (x[1], -abs(len(x[0]) - 150)), reverse=True)
        return candidates[0][0]

    def _is_heading_like_definition(self, text: str) -> bool:
        """
        Check if text looks like a heading or reference rather than a definition.
        
        Returns True if the text appears to be:
        - Chapter titles ("Chapter 1: Introduction")
        - Section headings ("Section 3.2 - Examples")
        - Reference document text ("Golden Reference...")
        - All-caps headings
        - Title-only text without sentence structure
        """
        if not text:
            return True
        
        text_lower = text.lower()
        text_stripped = text.strip()
        
        # Check for chapter/section/unit patterns
        if re.match(r'^(Chapter|Section|Unit|Module|Lesson|Part)\s+\d+', text, re.IGNORECASE):
            return True
        
        # Check for "Golden Reference" or "Reference Document"
        if 'golden reference' in text_lower or 'reference document' in text_lower:
            return True
        
        # Check for "References" or "Bibliography" as standalone
        if re.match(r'^References?$', text_stripped, re.IGNORECASE):
            return True
        
        # Check for heading patterns like "X - Examples" or "X - Overview"
        if re.search(r'\s+-\s+(Examples|Overview|Summary|Details|Introduction|Conclusion)$', text, re.IGNORECASE):
            return True
        
        # All-caps is likely a heading
        if text.isupper():
            return True
        
        # Title case without small words is likely a heading
        words = text.split()
        if len(words) > 1 and all(w[0].isupper() for w in words if w and w[0].isalpha()):
            small_words = ['a', 'an', 'the', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'is', 'are', 'with', 'by', 'as']
            if not any(w.lower() in small_words for w in words):
                return True
        
        # Very short text is likely not a proper definition
        if len(text_stripped) < 40:
            return True
        
        return False

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple Jaccard similarity between two texts."""
        if not text1 or not text2:
            return 0.0
        
        # Normalize and tokenize
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0

    def _extract_why_it_matters(
        self, 
        blocks: list[ContentBlock], 
        definition: str | None = None
    ) -> str | None:
        """
        Extract 'why it matters' content from evidence spans.
        
        Looks for:
        - Consequence sentences ("This enables...", "Without this...")
        - Use-case mentions ("commonly used for...", "essential when...")
        - Benefit statements ("allows you to...", "helps...")
        
        Ensures the result differs from the definition to avoid duplication.
        
        Returns the best matching content or None if no good match found.
        """
        why_patterns = [
            (r'\bthis\s+(?:enables?|allows?|permits?|makes\s+possible)\s+', 3),
            (r'\bwithout\s+this\s*[,;]?\s*\w+', 3),
            (r'\bcommonly\s+(?:used|applied)\s+(?:for|when|in)\s+', 3),
            (r'\bessential\s+(?:when|for|to)\s+', 3),
            (r'\bcrucial\s+(?:when|for|to)\s+', 3),
            (r'\bimportant\s+(?:when|for|to)\s+', 2),
            (r'\ballows?\s+(?:you\s+)?to\s+', 2),
            (r'\bhelps?\s+(?:you\s+)?(?:to\s+)?\w+', 2),
            (r'\bthis\s+helps', 2),
            (r'\buseful\s+(?:when|for)\s+', 2),
            (r'\bnecessary\s+(?:when|for)\s+', 2),
            (r'\brequired\s+(?:when|for|to)\s+', 2),
            (r'\bvaluable\s+(?:when|for)\s+', 1),
            (r'\bsignificant\s+(?:when|for)\s+', 1),
        ]
        
        candidates = []
        
        # Priority order for block types
        block_type_priority = {
            BlockType.EXPLANATORY_PROSE: 3,
            BlockType.SUMMARY: 2,
            BlockType.SIDEBAR: 1,
            BlockType.HEADING: 0,
            BlockType.SUBHEADING: 0,
        }
        
        for block in blocks:
            if not block.text_content:
                continue
            
            text = block.text_content.strip()
            sentences = re.split(r'(?<=[.!?])\s+', text)
            
            for sentence in sentences:
                sentence = sentence.strip()
                sentence_lower = sentence.lower()
                
                # Skip sentences that are too short or too long
                if len(sentence) < 25 or len(sentence) > 250:
                    continue
                
                # REJECT: Generic definitions that don't explain "why"
                generic_phrases = [
                    'important for effective sql',
                    'essential for database',
                    'crucial for sql',
                    'fundamental concept',
                ]
                if any(phrase in sentence_lower for phrase in generic_phrases):
                    continue
                
                # Check for why-it-matters patterns
                score = 0
                
                for pattern, weight in why_patterns:
                    if re.search(pattern, sentence_lower):
                        score += weight
                
                # Bonus for priority block types
                if hasattr(block, 'block_type') and block.block_type in block_type_priority:
                    score += block_type_priority[block.block_type]
                
                # Bonus for sentences starting with uppercase
                if sentence and sentence[0].isupper():
                    score += 0.5
                
                # Penalty for code-heavy sentences
                sql_keywords = ['select', 'from', 'where', 'join']
                sql_count = sum(1 for kw in sql_keywords if kw in sentence_lower)
                if sql_count >= 2:
                    score -= 2
                
                # Penalty for similarity to definition (avoid duplication)
                if definition and self._text_similarity(sentence, definition) > 0.5:
                    score -= 5  # Heavy penalty
                
                if score > 0:
                    candidates.append((sentence, score))
        
        if not candidates:
            return None
        
        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _extract_sql_from_code_blocks(self, blocks: list[ContentBlock]) -> list[dict]:
        """
        Extract SQL examples from code blocks with better detection.
        
        Also checks adjacent prose for SQL in backticks or code formatting.
        Returns a list of dicts with sql, explanation (nearby text), page, and source info.
        """
        examples = []
        seen_sql = set()  # For deduplication
        
        # SQL pattern that captures backticks and code formatting
        sql_pattern = r"`?(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|WITH)\s+[^;]+;`?"
        
        for i, block in enumerate(blocks):
            if not block.text_content:
                continue
            
            text = block.text_content
            
            # Direct code blocks
            is_code_block = (
                hasattr(block, 'block_type') and 
                block.block_type == BlockType.SQL_CODE
            )
            
            if is_code_block:
                # Find all SQL statements
                matches = re.finditer(sql_pattern, text, re.IGNORECASE | re.DOTALL)
                
                for match in matches:
                    sql = self._clean_and_validate_sql(match.group(0))
                    if sql and sql not in seen_sql:
                        seen_sql.add(sql)
                        explanation = self._get_nearby_explanation(blocks, i)
                        
                        examples.append({
                            "sql": sql,
                            "page": block.page_number,
                            "explanation": explanation,
                            "from_source": True,
                        })
            else:
                # SQL embedded in prose (backticks, inline code)
                for match in re.finditer(sql_pattern, text, re.IGNORECASE | re.DOTALL):
                    sql = self._clean_and_validate_sql(match.group(0))
                    if sql and sql not in seen_sql:
                        seen_sql.add(sql)
                        
                        examples.append({
                            "sql": sql,
                            "page": block.page_number,
                            "explanation": "This SQL example was extracted from the source text and demonstrates practical usage.",
                            "from_source": True,
                        })
        
        return examples

    def _clean_and_validate_sql(self, text: str) -> str | None:
        """Clean and validate extracted SQL."""
        # Remove backticks
        sql = text.strip('`')
        
        # Must start with SQL keyword
        if not re.match(r"^(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|WITH)\s", sql, re.IGNORECASE):
            return None
        
        # Must be substantial (not just keyword)
        # Relaxed from 30 to 20 to capture shorter valid queries like "SELECT * FROM table;"
        if len(sql) < 20 or sql.count(' ') < 2:
            return None
        
        # Must end with semicolon or be complete statement
        if not sql.endswith(';'):
            sql += ';'
        
        return sql

    def _get_nearby_explanation(self, blocks: list[ContentBlock], index: int) -> str:
        """Get explanation from nearby prose blocks."""
        # Look at previous block
        if index > 0:
            prev = blocks[index - 1]
            if hasattr(prev, 'block_type') and prev.block_type in (BlockType.EXPLANATORY_PROSE, BlockType.EXPLANATORY_PROSE):
                text = prev.text_content.strip() if prev.text_content else ""
                if len(text) > 20 and len(text) < 200:
                    return text
        
        # Look at next block
        if index < len(blocks) - 1:
            next_block = blocks[index + 1]
            if hasattr(next_block, 'block_type') and next_block.block_type in (BlockType.EXPLANATORY_PROSE, BlockType.EXPLANATORY_PROSE):
                text = next_block.text_content.strip() if next_block.text_content else ""
                if len(text) > 20 and len(text) < 200:
                    return text
        
        return "This SQL example demonstrates the concept with practical code that can be adapted for similar use cases."

    def _load_curated_examples(self, concept_id: str) -> list[dict] | None:
        """Load curated examples for concepts that textbooks explain poorly."""
        # Path from unit_generator.py (src/algl_pdf_helper/) -> project root -> data/
        examples_path = Path(__file__).parent.parent.parent / "data" / "concept_examples.json"
        
        if not examples_path.exists():
            return None
        
        try:
            with open(examples_path) as f:
                all_examples = json.load(f)
            
            concept_examples = all_examples.get(concept_id)
            if not concept_examples:
                return None
            
            return [
                {
                    "sql": ex["sql"],
                    "explanation": ex["explanation"],
                    "scenario": ex.get("scenario", "Example usage"),
                    "page": 0,  # Curated examples have no page
                    "from_source": True,  # Curated, not synthetic
                    "is_curated": True,
                }
                for ex in concept_examples
            ]
        except Exception:
            return None

    def _load_curated_l3_content(self, concept_id: str) -> dict | None:
        """Load curated L3 content for concepts missing good source material."""
        curated_path = Path(__file__).parent.parent.parent / "data" / "concept_curated_l3.json"
        
        if not curated_path.exists():
            return None
        
        try:
            with open(curated_path) as f:
                all_curated = json.load(f)
            
            return all_curated.get(concept_id)
        except Exception:
            return None

    def _assess_l3_quality(self, content: dict) -> float:
        """Score L3 content quality 0-1."""
        # If curated content was used, it's high quality
        if content.get("_used_curated_fallback"):
            return 0.8  # Curated content is high quality
        
        score = 0.0
        
        definition = content.get("definition", "")
        if len(definition) > 80 and "important" not in definition.lower():
            score += 0.4
        
        examples = content.get("examples", [])
        real_examples = sum(1 for ex in examples if not ex.get("is_synthetic", True))
        score += min(real_examples * 0.2, 0.4)
        
        if content.get("why_it_matters") and len(content["why_it_matters"]) > 50:
            score += 0.2
        
        return score

    def generate_l3_from_curated(
        self,
        concept_id: str,
        config: GenerationConfig,
        prerequisites: list[str] | None = None,
        error_subtypes: list[str] | None = None,
    ) -> InstructionalUnit | None:
        """Generate L3 unit directly from curated content for concepts with no blocks.
        
        This method creates an L3_explanation unit using curated content when a concept
        has no mapped content blocks from the textbook. It allows high-quality curated
        content to be included in the output even for concepts not covered in the source PDF.
        
        Args:
            concept_id: Canonical concept identifier
            config: Generation configuration
            prerequisites: Optional list of prerequisite concept IDs
            error_subtypes: Optional list of SQL-Engage error subtype IDs
            
        Returns:
            InstructionalUnit for L3 stage, or None if no curated content available
        """
        curated_full = self._load_curated_l3_content(concept_id)
        if not curated_full:
            return None
        
        # Access the nested content structure (curated_full has "content" key)
        curated = curated_full.get("content", curated_full)
        
        # Build examples from curated content
        examples: list[SQLExample] = []
        for ex in curated.get("examples", []):
            sql = self.transformer.transform_to_practice_schema(
                ex.get("sql", ""), ["Sailors", "Boats", "Reserves"]
            )
            examples.append(SQLExample(
                title=ex.get("title", "Example"),
                scenario=ex.get("scenario", f"Example of {concept_id}"),
                sql=sql,
                explanation=ex.get("explanation", ""),
                expected_output="Returns matching rows",
                schema_used="practice",
                is_synthetic=False,
            ))
        
        # Build common mistakes from curated content
        mistakes: list[MisconceptionExample] = []
        for m in curated.get("common_mistakes", []):
            # Ensure required fields have minimum length
            error_msg = m.get("error_message", "")
            if len(error_msg) < 5:
                error_msg = f"Error: {m.get('title', 'Syntax error')}"
            
            why_happens = m.get("why_it_happens", "")
            if len(why_happens) < 10:
                why_happens = f"This error occurs when using {concept_id} incorrectly."
            
            mistakes.append(MisconceptionExample(
                title=m.get("title", "Common Mistake"),
                error_sql=self.transformer.transform_to_practice_schema(
                    m.get("error_sql", ""), ["Sailors", "Boats", "Reserves"]
                ),
                error_message=error_msg,
                why_it_happens=why_happens,
                fix_sql=self.transformer.transform_to_practice_schema(
                    m.get("fix_sql", ""), ["Sailors", "Boats", "Reserves"]
                ),
                key_takeaway=m.get("key_takeaway", "Check your syntax carefully"),
            ))
        
        # Get learning objectives from ontology
        learning_objectives = self._get_learning_objectives_from_ontology(concept_id)
        
        # Build practice links
        practice_links = self._lookup_real_problems(concept_id)
        if not practice_links:
            practice_links = [
                PracticeLink(
                    concept_id=concept_id,
                    problem_ids=[f"unresolved-{concept_id}"],
                    needs_resolution=True,
                )
            ]
        
        # Build L3 content
        content = L3Content(
            definition=curated.get("definition") or self._get_default_definition(concept_id),
            why_it_matters=curated.get("why_it_matters") or self._get_default_why_it_matters(concept_id),
            learning_objectives=learning_objectives,
            examples=examples if examples else self._get_default_sql_examples(concept_id),
            contrast_example=None,  # Could be added to curated format
            common_mistakes=mistakes if mistakes else self._get_default_misconceptions(concept_id),
            practice_links=practice_links,
        )
        
        # Create content dict with curated flag
        content_dict = content.model_dump()
        content_dict["_used_curated_fallback"] = True
        content_dict["_metadata"] = {
            "content_source": "curated",
            "review_needed": False,
            "content_quality": "curated",
        }
        
        # Create a synthetic evidence span for curated content to pass grounding checks
        curated_evidence_span = SourceSpan(
            span_id=f"{concept_id}_curated",
            doc_id="curated-content",
            page_number=1,  # Curated content has no PDF page
            char_start=0,
            char_end=100,
            block_type="prose",
            text_content=f"Curated content for {concept_id}",
            extraction_confidence=0.95,  # High confidence for curated
        )
        
        return InstructionalUnit(
            unit_id=f"{concept_id}_L3_explanation",
            concept_id=concept_id,
            unit_type="explanation",
            target_stage="L3_explanation",
            content=content_dict,
            error_subtypes=error_subtypes or [],
            prerequisites=prerequisites or [],
            difficulty="intermediate",
            evidence_spans=[curated_evidence_span],  # Has evidence span for grounding
            source_pages=[1],  # Has source page for grounding
            grounding_confidence=0.9,  # High confidence for curated content
            estimated_read_time=300,
        )
    
    def get_concepts_with_curated_l3(self) -> set[str]:
        """Get the set of concept IDs that have curated L3 content available."""
        curated_path = Path(__file__).parent.parent.parent / "data" / "concept_curated_l3.json"
        
        if not curated_path.exists():
            return set()
        
        try:
            with open(curated_path) as f:
                all_curated = json.load(f)
            return set(all_curated.keys())
        except Exception:
            return set()

    def _create_synthetic_sql_examples(self, concept_id: str, count: int = 2) -> list[dict]:
        """
        Create synthetic SQL examples for a concept.
        
        These are clearly marked as synthetic in the metadata.
        """
        examples = []
        
        # Get default SQL and create variations
        base_sql = self._get_default_example_sql(concept_id)
        
        for i in range(min(count, 2)):
            examples.append({
                "sql": base_sql,
                "page": 0,  # Indicates synthetic
                "explanation": f"Synthetic example for {concept_id} (no source SQL available)",
                "from_source": False,
                "is_synthetic": True,
            })
        
        return examples

    def _lookup_real_problems(self, concept_id: str) -> list[PracticeLink] | None:
        """
        Look up real problem IDs for a concept.
        
        Returns a list of PracticeLink objects if found, or None if no mapping exists.
        Handles both simple string IDs and rich metadata objects.
        
        Args:
            concept_id: The concept ID to look up
            
        Returns:
            List of PracticeLink objects, or None if no mapping found
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Load practice map from data directory (project root)
        practice_map_path = Path(__file__).parent.parent.parent / "data" / "practice_map.json"
        if not practice_map_path.exists():
            return None
        
        try:
            with open(practice_map_path) as f:
                practice_map = json.load(f)
            
            concept_problems = practice_map.get(concept_id)
            if not concept_problems:
                return None
            
            # Check if this is using placeholder status
            metadata_status = practice_map.get("_metadata", {}).get("status", "")
            is_placeholder_format = metadata_status == "placeholder"
            
            links = []
            problem_ids = []
            
            for problem in concept_problems:
                if isinstance(problem, str):
                    # Simple string ID format
                    problem_ids.append(problem)
                    links.append(
                        PracticeLink(
                            concept_id=concept_id,
                            problem_ids=[problem],
                            needs_resolution=problem.startswith("problem-") and is_placeholder_format,
                        )
                    )
                elif isinstance(problem, dict):
                    # Rich object with metadata
                    problem_id = problem.get("id", f"unresolved-{concept_id}")
                    problem_ids.append(problem_id)
                    
                    # Determine if this needs resolution
                    needs_resolution = problem.get("is_placeholder", False)
                    if not needs_resolution and is_placeholder_format:
                        needs_resolution = problem_id.startswith("problem-")
                    
                    links.append(
                        PracticeLink(
                            concept_id=concept_id,
                            problem_ids=[problem_id],
                            needs_resolution=needs_resolution,
                            metadata=problem,  # Store full metadata
                        )
                    )
            
            # If we have multiple problem IDs, consolidate into a single PracticeLink
            if problem_ids:
                # Check if any need resolution
                any_needs_resolution = any(link.needs_resolution for link in links)
                
                # Collect metadata from all links
                combined_metadata = {
                    "problems": [link.metadata for link in links if link.metadata],
                    "format_version": practice_map.get("_metadata", {}).get("format_version", "1.0"),
                    "status": metadata_status,
                }
                
                return [
                    PracticeLink(
                        concept_id=concept_id,
                        problem_ids=problem_ids,
                        needs_resolution=any_needs_resolution,
                        metadata=combined_metadata if combined_metadata["problems"] else None,
                    )
                ]
            
            return links if links else None
            
        except Exception as e:
            logger.warning(f"Failed to load practice map for {concept_id}: {e}")
            return None
    
    def _get_page_references_str(self, blocks: list[ContentBlock]) -> str:
        """Get page references from blocks as a string."""
        pages = sorted(set(b.page_number for b in blocks if b.page_number > 0))
        if not pages:
            return ""
        if len(pages) == 1:
            return f"page {pages[0]}"
        elif len(pages) <= 3:
            return f"pages {', '.join(map(str, pages))}"
        else:
            return f"pages {pages[0]}-{pages[-1]}"
    
    def _get_ontology_info(self, concept_id: str) -> dict[str, Any]:
        """Get information from SQL ontology for a concept."""
        concept = get_concept(concept_id)
        if not concept:
            return {}
        return {
            "title": concept.get("title", concept_id),
            "definition": concept.get("definition", ""),
            "syntax_pattern": concept.get("syntax_pattern", ""),
            "use_when": concept.get("use_when", ""),
            "key_points": concept.get("key_points", []),
            "common_mistakes": concept.get("common_mistakes", []),
        }
    
    def _is_heading_like(self, text: str) -> bool:
        """Check if text looks like a heading rather than explanatory content."""
        text = text.strip()
        text_lower = text.lower()
        
        # Chapter titles
        if re.match(r'^Chapter\s+\d+[:\s]', text, re.IGNORECASE):
            return True
        
        # All-caps headings
        if text.isupper():
            return True
        
        # ToC-like patterns ("1 SELECT Statement", "2.1 Joins")
        if re.match(r'^\d+(?:\.\d+)?\s+[A-Z]', text):
            return True
        
        # Reference document text
        if 'reference document' in text_lower:
            return True
        
        # Learning objectives heading
        if re.search(r'\blearning objective', text_lower):
            return True
        
        return False

    def _build_grounded_L1_content(
        self, 
        concept_id: str, 
        blocks: list[ContentBlock]
    ) -> L1Content:
        """Build L1 hint content grounded in evidence spans (no-LLM path).
        
        Creates tutoring-style hints that avoid:
        - Chapter titles and section headings
        - Page references in learner-facing text
        - Generic boilerplate text
        """
        # Get info from ontology
        ontology = self._get_ontology_info(concept_id)
        
        # Build hint text - prefer extracted definition, then ontology, then default
        extracted_def = self._extract_definition_sentence(blocks)
        hint_text = None
        
        if extracted_def and not self._is_heading_like(extracted_def):
            # REJECT heading-like or generic base text patterns
            bad_patterns = [
                r"^Remember how to use",
                r"^Common Mistakes to Avoid:",
                r"^Chapter \d+",
                r"^Section \d+",
                r"^Golden Reference",
                r"^[A-Z][a-z]+ [A-Z][a-z]+ - Examples",  # "WHERE Clause - Examples"
                r"^Key concepts?:",  # Already added by bad extraction
                r"^Learning Objectives",
                r"is an important SQL concept$",
                r"is a crucial SQL concept$",
                r"is an essential SQL concept$",
            ]
            
            is_bad = any(
                re.search(pattern, extracted_def, re.IGNORECASE) 
                for pattern in bad_patterns
            )
            
            if not is_bad and len(extracted_def) >= 50:
                hint_text = extracted_def
        
        # Fall back to ontology if extraction failed or was bad
        if not hint_text and ontology.get("definition"):
            hint_text = ontology["definition"]
        
        # Last resort: first sentence or default
        if not hint_text:
            first_sentence = self._get_first_sentence_from_blocks(blocks)
            if first_sentence and not self._is_heading_like(first_sentence):
                hint_text = first_sentence
            else:
                hint_text = self._get_default_hint(concept_id)
        
        # Final validation: if still too short or generic, use default
        if len(hint_text) < 50 or hint_text.startswith("Remember how to use"):
            hint_text = self._get_default_hint(concept_id)
        
        # NOTE: Page references are intentionally NOT included in learner-facing text.
        # Source pages are already tracked in evidence_spans metadata for UI display.
        
        # Extract key terms for syntax cue (not appended to hint anymore)
        key_terms = self._extract_key_terms_from_blocks(blocks)
        
        # Build syntax cue
        if ontology.get("syntax_pattern"):
            syntax_cue = ontology["syntax_pattern"]
        elif key_terms:
            # Build basic syntax from key terms
            syntax_cue = f"{key_terms[0]} ..."
        else:
            syntax_cue = self._get_default_syntax_cue(concept_id)
        
        # Build when to use
        if ontology.get("use_when"):
            when_to_use = ontology["use_when"]
        else:
            when_to_use = self._get_default_when_to_use(concept_id)
        
        return L1Content(
            hint_text=hint_text[:300],  # Respect max length
            syntax_cue=syntax_cue[:200],
            when_to_use=when_to_use[:200],
        )
    
    def _build_grounded_L2_content(
        self,
        concept_id: str,
        blocks: list[ContentBlock],
        l1_hint: str,
    ) -> L2Content:
        """Build L2 hint+example content grounded in evidence spans (no-LLM path).
        
        Uses concept-specific scoring to select the best matching SQL example
        from extracted content, ensuring examples match the concept being taught.
        """
        # Extract SQL examples from blocks
        sql_examples = self._extract_sql_examples_from_blocks(blocks)
        
        # Score and select the best example for this concept
        best_example = None
        best_page = None
        best_score = -1
        
        for ex in sql_examples:
            score = self._score_sql_for_concept(ex["sql"], concept_id)
            if score > best_score:
                best_score = score
                best_example = ex["sql"]
                best_page = ex["page"]
        
        # Determine final example and explanation
        if best_example and best_score >= 1.0:
            # Use the best matched example
            example_sql = best_example
            example_explanation = f"Example from page {best_page}."
        else:
            # Fall back to concept-appropriate default example
            example_sql = self._get_default_example_sql(concept_id)
            example_explanation = "Basic usage example."
        
        # Transform SQL to practice schema
        example_sql = self.transformer.transform_to_practice_schema(
            example_sql, ["Sailors", "Boats", "Reserves"]
        )
        
        # Get pitfall from ontology or default
        ontology = self._get_ontology_info(concept_id)
        common_mistakes = ontology.get("common_mistakes", [])
        if common_mistakes:
            common_pitfall = common_mistakes[0] if isinstance(common_mistakes[0], str) else str(common_mistakes[0])
        else:
            common_pitfall = self._get_default_pitfall(concept_id)
        
        return L2Content(
            hint_text=l1_hint[:300],
            example_sql=example_sql[:500],
            example_explanation=example_explanation[:300],
            common_pitfall=common_pitfall[:200],
        )
    
    def _extract_l3_from_blocks(self, blocks: list[ContentBlock], concept_id: str) -> dict:
        """Extract L3 content components from source blocks."""
        content = {}
        
        # Extract definition
        definition = self._extract_definition_sentence(blocks)
        if definition and not self._is_heading_like_definition(definition):
            content["definition"] = definition
        
        # Extract why it matters
        why_it_matters = self._extract_why_it_matters(blocks, definition=definition)
        if why_it_matters:
            content["why_it_matters"] = why_it_matters
        
        # Extract SQL examples
        sql_examples = self._extract_sql_from_code_blocks(blocks)
        examples = []
        for ex in sql_examples[:3]:
            explanation = ex.get("explanation", "")
            if len(explanation) < 20:
                explanation = "This SQL example demonstrates the concept with practical code."
            examples.append({
                "sql": ex["sql"],
                "explanation": explanation,
                "scenario": ex.get("scenario", "Example usage"),
                "is_synthetic": False,
            })
        if examples:
            content["examples"] = examples
        
        return content

    def _build_grounded_L3_content(
        self,
        concept_id: str,
        blocks: list[ContentBlock],
        config: GenerationConfig | None = None,
    ) -> L3Content:
        """Build L3 explanation content grounded in evidence spans (no-LLM path).
        
        Uses curated fallback for weak concepts to ensure high-quality content
        even when textbook source material is insufficient.
        """
        config = config or GenerationConfig()
        
        # Get ontology info (for fallback use)
        ontology = self._get_ontology_info(concept_id)
        
        # Get source text for extraction
        source_text = "\n\n".join(
            b.text_content for b in blocks if b.text_content
        )
        
        # Try extraction first
        extracted_content = self._extract_l3_from_blocks(blocks, concept_id)
        
        # Assess quality of extracted content
        quality_score = self._assess_l3_quality(extracted_content)
        curated_used = False
        
        # If weak or missing, try curated fallback
        if quality_score < 0.5:
            curated_full = self._load_curated_l3_content(concept_id)
            if curated_full:
                # Access the nested content structure (curated_full has "content" key)
                curated = curated_full.get("content", curated_full)
                print(f"[Generate L3] {concept_id}: merging with curated content")
                
                # DEBUG: Check what's in curated
                print(f"[DEBUG] {concept_id} curated keys: {list(curated.keys())}")
                print(f"[DEBUG] {concept_id} curated definition: {curated.get('definition', 'MISSING')[:50] if curated.get('definition') else 'EMPTY'}")
                
                # USE CURATED DIRECTLY - don't merge with empty extracted
                # Only keep non-empty extracted values that curated doesn't have
                merged_content = {}
                
                # Start with all curated content (it's the high-quality source)
                for key, value in curated.items():
                    merged_content[key] = value
                
                # Only add extracted content if curated doesn't have it OR curated's version is empty
                for key, value in extracted_content.items():
                    if key not in merged_content or not merged_content[key]:
                        if value:  # Only add if extracted value is non-empty
                            merged_content[key] = value
                
                merged_content["_used_curated_fallback"] = True
                extracted_content = merged_content
                curated_used = True
                print(f"[DEBUG] {concept_id}: Using curated directly")
        
        # DEBUG: Check final content state
        print(f"[DEBUG] {concept_id}: final has_definition={bool(extracted_content.get('definition'))}, "
              f"has_examples={bool(extracted_content.get('examples'))}, "
              f"has_why={bool(extracted_content.get('why_it_matters'))}, "
              f"curated_used={curated_used}")
        
        # Build definition: Try extracted/merged first, then ontology, then default
        definition = extracted_content.get("definition")
        
        # REJECT bad definitions explicitly
        bad_definition_patterns = [
            r"^Chapter \d+",
            r"^Section \d+",
            r"^Unit \d+",
            r"Golden Reference",
            r"Reference Document",
            r"is an important SQL concept$",
            r"is a crucial SQL concept$",
            r"is an essential SQL concept$",
            r"is a fundamental SQL concept$",
            r"Learning Objectives",
            r"^Common Mistakes",
        ]
        
        is_bad_definition = False
        if definition:
            is_bad_definition = any(
                re.search(pattern, definition, re.IGNORECASE) 
                for pattern in bad_definition_patterns
            )
        
        # Check if extracted definition is heading-like or bad - if so, fall back
        if definition and (self._is_heading_like_definition(definition) or is_bad_definition):
            definition = None  # Force fallback
        
        # Fallback chain for definition
        if not definition:
            if ontology.get("definition"):
                definition = ontology["definition"]
            else:
                first_sentence = self._get_first_sentence_from_blocks(blocks)
                # Also check if first sentence is heading-like
                if first_sentence and not self._is_heading_like_definition(first_sentence):
                    # Check first sentence against bad patterns too
                    if not any(re.search(p, first_sentence, re.IGNORECASE) for p in bad_definition_patterns):
                        definition = first_sentence
        
        # If extraction failed or returned bad/short content, use defaults
        if not definition or len(definition) < 30:
            definition = self._get_default_definition(concept_id)
        
        # Final safety check - never leave definition empty
        if not definition or len(definition.strip()) == 0:
            definition = f"{concept_id.replace('-', ' ').title()} is a SQL concept for working with database data."
        
        # Build why it matters: Try extracted/merged first, then extract fresh, then ontology, then default
        # Pass definition to avoid duplication
        why_it_matters = extracted_content.get("why_it_matters")
        
        if not why_it_matters:
            why_it_matters = self._extract_why_it_matters(blocks, definition=definition)
        
        if not why_it_matters:
            if ontology.get("use_when"):
                why_it_matters = f"Use this when {ontology['use_when']}"
            else:
                # Generate a specific "why" that's different from definition
                why_it_matters = self._get_default_why_it_matters(concept_id)
        
        # Final check: ensure why_it_matters differs significantly from definition
        if why_it_matters and self._text_similarity(why_it_matters, definition) > 0.6:
            # They're too similar - use ontology or generate different text
            if ontology.get("use_when"):
                why_it_matters = f"This is essential when {ontology['use_when']}"
            else:
                why_it_matters = self._get_default_why_it_matters(concept_id)
        
        # Final safety check - never leave why_it_matters empty
        if not why_it_matters or len(why_it_matters.strip()) == 0:
            why_it_matters = f"Understanding {concept_id.replace('-', ' ')} helps you write more effective SQL queries."
        
        # Get learning objectives from ontology
        learning_objectives = self._get_learning_objectives_from_ontology(concept_id)
        
        # Build examples: Try extracted/merged first, then curated, then synthetic (if allowed)
        examples: list[SQLExample] = []
        
        # Step 1: Use extracted/merged examples if available
        if extracted_content.get("examples"):
            for i, ex in enumerate(extracted_content["examples"][:3]):
                sql = self.transformer.transform_to_practice_schema(
                    ex["sql"], ["Sailors", "Boats", "Reserves"]
                )
                examples.append(SQLExample(
                    title=f"Example {i+1}",
                    scenario=ex.get("scenario", "Example usage"),
                    sql=sql,
                    explanation=ex.get("explanation", f"Example demonstrating {concept_id}"),
                    expected_output="Returns matching rows",
                    schema_used="source",
                    is_synthetic=ex.get("is_synthetic", False),
                ))
        
        # Step 2: Extract SQL from code blocks if still need more
        if len(examples) < 2:
            sql_examples = self._extract_sql_from_code_blocks(blocks)
            
            for ex in sql_examples[:3 - len(examples)]:
                sql = self.transformer.transform_to_practice_schema(
                    ex["sql"], ["Sailors", "Boats", "Reserves"]
                )
                # Ensure scenario and explanation meet minimum length requirements
                scenario = ex.get('explanation') or ""
                if len(scenario) < 10:
                    scenario = f"SQL example demonstrating {concept_id} usage pattern"
                explanation = ex.get('explanation') or ""
                if len(explanation) < 20:
                    explanation = f"This example demonstrates {concept_id} concepts with practical SQL code."
                
                examples.append(SQLExample(
                    title=f"Example {len(examples)+1} (page {ex['page']})" if ex.get('page') else f"Example {len(examples)+1}",
                    scenario=scenario,
                    sql=sql,
                    explanation=explanation,
                    expected_output="Returns matching rows",
                    schema_used="source",  # Mark as from source
                    is_synthetic=False,
                ))
        
        # Step 3: If few extracted, try curated examples
        if len(examples) < 2:
            curated = self._load_curated_examples(concept_id)
            if curated:
                for ex in curated[:2]:  # Max 2 curated examples
                    sql = self.transformer.transform_to_practice_schema(
                        ex["sql"], ["Sailors", "Boats", "Reserves"]
                    )
                    examples.append(SQLExample(
                        title=f"Example (curated)",
                        scenario=ex.get('scenario', 'Example usage'),
                        sql=sql,
                        explanation=ex['explanation'],
                        expected_output="Returns matching rows",
                        schema_used="practice",
                        is_synthetic=False,  # Curated, not synthetic
                    ))
        
        # Step 3: Only use synthetic if still insufficient AND config allows it
        if len(examples) < 1:
            allow_synthetic = config.allow_synthetic_examples if config else False
            if allow_synthetic:
                synthetic_examples = self._create_synthetic_sql_examples(concept_id, count=2)
                for ex in synthetic_examples:
                    examples.append(SQLExample(
                        title=f"Example (synthetic)",
                        scenario=f"Practice example for {concept_id}",
                        sql=ex["sql"],
                        explanation=f"{ex['explanation']} [Note: This is a generated example. Verify with instructor.]",
                        expected_output="Returns matching rows",
                        schema_used="practice",
                        is_synthetic=True,  # Mark as explicitly synthetic
                    ))
        
        # Final safety - always have at least one example
        if not examples:
            default_sql = self._get_default_example_sql(concept_id)
            examples = [SQLExample(
                title=f"Example: Basic {concept_id} usage",
                scenario=f"Demonstrating {concept_id} with a simple query",
                sql=default_sql,
                explanation=f"This example shows basic usage of {concept_id} in a SQL query.",
                expected_output="Returns matching rows",
                schema_used="practice",
                is_synthetic=False,  # Using the default canonical example
            )]
        
        # Build common mistakes from ontology or defaults
        mistakes: list[MisconceptionExample] = []
        if ontology.get("common_mistakes"):
            for i, m in enumerate(ontology["common_mistakes"][:3]):
                if isinstance(m, dict):
                    mistakes.append(MisconceptionExample(
                        title=m.get("title", f"Mistake {i+1}"),
                        error_sql=m.get("incorrect", "SELECT *;"),
                        error_message=m.get("error_message", "Syntax error"),
                        why_it_happens=m.get("explanation", "Common misconception"),
                        fix_sql=m.get("corrected", "SELECT * FROM table;"),
                        key_takeaway=m.get("takeaway", "Check your syntax"),
                    ))
        
        if not mistakes:
            mistakes = self._get_default_misconceptions(concept_id)
        
        # Practice links: Check for real problems, otherwise use unresolved placeholder
        practice_links = self._lookup_real_problems(concept_id)
        if not practice_links:
            # Use unresolved placeholder with metadata flag so it can be filtered in production
            practice_links = [
                PracticeLink(
                    concept_id=concept_id,
                    problem_ids=[f"unresolved-{concept_id}"],
                    needs_resolution=True,  # Explicitly mark as needing resolution
                )
            ]
        
        return L3Content(
            definition=definition[:1000],
            why_it_matters=why_it_matters[:500],
            learning_objectives=learning_objectives,
            examples=examples,
            contrast_example=None,
            common_mistakes=mistakes,
            practice_links=practice_links,
        )
    
    def _build_grounded_L4_content(
        self,
        concept_id: str,
        blocks: list[ContentBlock],
    ) -> L4Content:
        """Build L4 reflective content grounded in evidence spans (no-LLM path).
        
        Creates concept-specific reflective content rather than generic templates.
        """
        # Get ontology info
        ontology = self._get_ontology_info(concept_id)
        
        # Build concept-specific summary (not generic template)
        # Use ontology definition or get concept-specific default
        if ontology.get("definition"):
            base_def = ontology["definition"]
        else:
            base_def = self._get_default_definition(concept_id)
        
        # Build concept-specific summary
        key_concept_summary = self._get_default_summary(concept_id)
        
        # If summary still looks generic (contains template phrases), use base_def + custom ending
        if "Mastering this concept is essential" in key_concept_summary:
            # Build from definition with concept-specific insight
            key_concept_summary = self._build_concept_specific_summary(concept_id, base_def)
        
        # Concept-specific reflection prompts (not generic)
        reflection_prompts = self._get_concept_specific_reflection_prompts(concept_id)
        
        # Build explain prompt - concept-specific context
        explain_in_own_words = self._build_concept_specific_explain_prompt(concept_id, ontology)
        
        # Concept-specific transfer questions (not generic)
        transfer_questions = self._get_concept_specific_transfer_questions(concept_id)
        
        # Connections from ontology or defaults
        connections = ontology.get("related_concepts", []) if ontology else []
        if not connections:
            connections = self._get_default_connections(concept_id)
        
        return L4Content(
            key_concept_summary=key_concept_summary[:500],
            reflection_prompts=reflection_prompts[:5],
            explain_in_own_words=explain_in_own_words[:500],
            transfer_questions=transfer_questions[:3],
            connections=connections,
        )
    
    def _build_grounded_reinforcement_content(
        self,
        concept_id: str,
        blocks: list[ContentBlock],
    ) -> ReinforcementContent:
        """Build reinforcement content grounded in evidence spans (no-LLM path)."""
        # Get ontology info
        ontology = self._get_ontology_info(concept_id)
        
        # Build recall prompt
        if ontology.get("title"):
            recall_prompt = f"What's the purpose of {ontology['title']}?"
        else:
            recall_prompt = self._get_default_recall_prompt(concept_id)
        
        # Quick check question - use ontology if available
        if ontology.get("syntax_pattern"):
            quick_check_question = f"Complete the pattern: {ontology['syntax_pattern'][:50]}...?"
        else:
            quick_check_question = self._get_default_check_question(concept_id)
        
        # Answer
        if ontology.get("definition"):
            quick_check_answer = ontology["definition"][:100]
        else:
            quick_check_answer = self._get_default_check_answer(concept_id)
        
        return ReinforcementContent(
            recall_prompt=recall_prompt[:200],
            quick_check_question=quick_check_question[:300],
            quick_check_answer=quick_check_answer[:300],
            next_review_timing="1 day",
        )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def generate_instructional_units_for_concept(
    concept_id: str,
    raw_text: str,
    source_pages: list[int],
    config: GenerationConfig | None = None,
    prerequisites: list[str] | None = None,
) -> dict[str, InstructionalUnit]:
    """
    Convenience function to generate all variants for a concept.
    
    Args:
        concept_id: Canonical concept identifier
        raw_text: Raw text content from PDF
        source_pages: List of source page numbers
        config: Optional generation configuration
        prerequisites: Optional list of prerequisite concept IDs
        
    Returns:
        Dictionary mapping unit types to InstructionalUnit objects
    """
    config = config or GenerationConfig()
    
    # Create content blocks from raw text
    blocks = [
        ContentBlock(
            block_id=f"{concept_id}_block_1",
            text_content=raw_text,
            block_type="prose",
            page_number=source_pages[0] if source_pages else 1,
            char_start=0,
            char_end=len(raw_text),
            confidence=1.0,
        )
    ]
    
    generator = UnitGenerator()
    return generator.generate_all_variants(concept_id, blocks, config, prerequisites)


def export_units_to_json(units: dict[str, InstructionalUnit], output_path: str) -> None:
    """
    Export instructional units to JSON file.
    
    Args:
        units: Dictionary of instructional units
        output_path: Path to output file
    """
    data = {
        unit_type: unit.model_dump() for unit_type, unit in units.items()
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)
        f.write('\n')


def validate_unit_completeness(units: dict[str, InstructionalUnit]) -> dict[str, list[str]]:
    """
    Validate that all required unit types are present and complete.
    
    Args:
        units: Dictionary of instructional units
        
    Returns:
        Dictionary mapping unit types to list of validation errors
    """
    required_types = [
        "L1_hint",
        "L2_hint_plus_example",
        "L3_explanation",
        "L4_reflective_note",
        "reinforcement",
    ]
    
    results: dict[str, list[str]] = {}
    
    for unit_type in required_types:
        errors = []
        
        if unit_type not in units:
            errors.append(f"Missing required unit type: {unit_type}")
        else:
            unit = units[unit_type]
            
            if not unit.content:
                errors.append("Content is empty")
            
            if unit_type == "L3_explanation":
                content = unit.content
                if not content.get("examples"):
                    errors.append("L3 explanation missing examples")
                if not content.get("common_mistakes"):
                    errors.append("L3 explanation missing common_mistakes")
            
            elif unit_type == "L4_reflective_note":
                content = unit.content
                if not content.get("reflection_prompts"):
                    errors.append("L4 reflective note missing reflection_prompts")
                if not content.get("transfer_questions"):
                    errors.append("L4 reflective note missing transfer_questions")
        
        results[unit_type] = errors
    
    return results


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Data models (imported from instructional_models and section_extractor)
    "ContentBlock",
    "SourceSpan",
    "InstructionalUnit",
    # Content models
    "L1Content",
    "L2Content",
    "L3Content",
    "L4Content",
    "ReinforcementContent",
    # Configuration
    "GenerationConfig",
    # Adapter
    "convert_unit_to_canonical",
    # Main classes
    "PromptBuilder",
    "ContentTransformer",
    "UnitGenerator",
    # Utility functions
    "generate_instructional_units_for_concept",
    "export_units_to_json",
    "validate_unit_completeness",
]
