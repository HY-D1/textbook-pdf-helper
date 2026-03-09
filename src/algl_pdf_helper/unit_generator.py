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
            text_content = b.text_content
            excerpt = text_content[:100] + "..." if len(text_content) > 100 else text_content
            
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
            self.logger.warning(f"LLM call failed: {e}")
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
        source_text = "\n\n".join(b.text_content for b in blocks)
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
        source_text = "\n\n".join(b.text_content for b in blocks)
        
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
        source_text = "\n\n".join(b.text_content for b in blocks)
        
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
        
        if not has_llm_content:
            # Use grounded defaults from evidence spans (no-LLM path)
            content = self._build_grounded_L3_content(concept_id, blocks)
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
            real_problems = self._lookup_real_problems(concept_id)
            if real_problems:
                practice_links = [
                    PracticeLink(
                        concept_id=concept_id,
                        problem_ids=real_problems,
                        needs_resolution=False,
                    )
                ]
            else:
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
            
            content = L3Content(
                definition=def_response.get("definition", self._get_default_definition(concept_id)) if def_response else self._get_default_definition(concept_id),
                why_it_matters=def_response.get("why_it_matters", "Important for database queries.") if def_response else "Important for database queries.",
                learning_objectives=learning_objectives,
                examples=examples,
                contrast_example=contrast,
                common_mistakes=mistakes,
                practice_links=practice_links,
            )
        
        # Get source pages from blocks
        source_pages = list(set(b.page_number for b in blocks))
        
        return InstructionalUnit(
            unit_id=f"{concept_id}_L3_explanation",
            concept_id=concept_id,
            unit_type="explanation",
            target_stage="L3_explanation",
            content=content.model_dump(),
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
        source_text = "\n\n".join(b.text_content for b in blocks)
        
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
        source_text = "\n\n".join(b.text_content for b in blocks)
        
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
            grounding_confidence=0.0,
            estimated_read_time=30,
        )
        return unit
    
    # =============================================================================
    # DEFAULT CONTENT HELPERS
    # =============================================================================
    
    def _get_default_hint(self, concept_id: str) -> str:
        """Get default hint for concept."""
        hints = {
            "joins": "Use JOIN to combine rows from multiple tables based on related columns.",
            "select-basic": "Use SELECT to retrieve data from tables. Specify columns or use * for all.",
            "where-clause": "Use WHERE to filter rows based on conditions.",
            "aggregate-functions": "Use aggregate functions like COUNT, SUM, AVG to calculate summary values.",
            "group-by": "Use GROUP BY to organize rows with the same values into summary rows.",
            "subqueries": "Use subqueries to nest SELECT statements inside other queries.",
        }
        return hints.get(concept_id, f"Remember how to use {concept_id}.")
    
    def _get_default_syntax_cue(self, concept_id: str) -> str:
        """Get default syntax cue for concept."""
        cues = {
            "joins": "SELECT ... FROM table1 JOIN table2 ON table1.col = table2.col;",
            "select-basic": "SELECT columns FROM table;",
            "where-clause": "SELECT ... FROM ... WHERE condition;",
            "aggregate-functions": "SELECT AGG(column) FROM table;",
            "group-by": "SELECT ... FROM ... GROUP BY column;",
            "subqueries": "SELECT ... FROM ... WHERE column = (SELECT ...);",
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
        }
        return contexts.get(concept_id, f"When working with {concept_id}")
    
    def _get_default_example_sql(self, concept_id: str) -> str:
        """Get default example SQL for concept."""
        examples = {
            "joins": "SELECT u.name, o.product FROM users u JOIN orders o ON u.id = o.user_id;",
            "select-basic": "SELECT name, email FROM users WHERE city = 'Seattle';",
            "where-clause": "SELECT * FROM users WHERE age > 25 AND city = 'Portland';",
            "aggregate-functions": "SELECT city, COUNT(*) FROM users GROUP BY city;",
            "group-by": "SELECT city, AVG(age) FROM users GROUP BY city HAVING COUNT(*) > 2;",
            "subqueries": "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders);",
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
        }
        return pitfalls.get(concept_id, "Watch for syntax errors")
    
    def _get_default_definition(self, concept_id: str) -> str:
        """Get default definition for concept."""
        definitions = {
            "joins": "JOIN combines rows from two or more tables based on related columns between them.",
            "select-basic": "SELECT retrieves data from one or more tables in the database.",
            "where-clause": "WHERE filters query results to include only rows that meet specified conditions.",
            "aggregate-functions": "Aggregate functions perform calculations on sets of values and return a single result.",
            "group-by": "GROUP BY organizes rows with the same values in specified columns into summary rows.",
            "subqueries": "A subquery is a SELECT statement nested inside another SQL statement.",
        }
        return definitions.get(concept_id, f"{concept_id} is an important SQL concept.")
    
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
        """Get default summary for concept."""
        return f"{self._get_default_definition(concept_id)} Mastering this concept is essential for effective SQL querying."
    
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
        }
        return connections.get(concept_id, [])
    
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
        examples = []
        for block in blocks:
            if not block.text_content:
                continue
            text = block.text_content
            # Look for SQL patterns - more comprehensive pattern
            # Match SELECT, INSERT, UPDATE, DELETE, CREATE statements
            sql_pattern = r"(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\s+.+?;"
            matches = re.findall(sql_pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # Clean up the match - take first 200 chars to avoid capturing too much
                sql = match[:200] if len(match) > 200 else match
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
        ]
        
        candidates = []
        
        for block in blocks:
            if not block.text_content:
                continue
                
            # Prioritize explanatory prose and glossary blocks
            is_explanatory = (
                hasattr(block, 'block_type') and 
                block.block_type in (BlockType.EXPLANATORY_PROSE, BlockType.GLOSSARY)
            )
            
            text = block.text_content.strip()
            # Split into sentences (simple heuristic)
            sentences = re.split(r'(?<=[.!?])\s+', text)
            
            for sentence in sentences:
                sentence = sentence.strip()
                # Skip sentences that are too short or too long
                if len(sentence) < 30 or len(sentence) > 300:
                    continue
                    
                # Check for definitional patterns
                score = 0
                sentence_lower = sentence.lower()
                
                for pattern in definitional_patterns:
                    if re.search(pattern, sentence_lower):
                        score += 2
                
                # Bonus for explanatory blocks
                if is_explanatory:
                    score += 1
                    
                # Bonus for sentences starting with uppercase (likely complete sentences)
                if sentence[0].isupper():
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

    def _extract_why_it_matters(self, blocks: list[ContentBlock]) -> str | None:
        """
        Extract 'why it matters' content from evidence spans.
        
        Looks for:
        - Consequence sentences ("This enables...", "Without this...")
        - Use-case mentions ("commonly used for...", "essential when...")
        - Benefit statements ("allows you to...", "helps...")
        
        Returns the best matching content or None if no good match found.
        """
        why_patterns = [
            (r'\bthis\s+(?:enables?|allows?|permits?|makes\s+possible)\s+', 3),
            (r'\bwithout\s+this\s*[,;]?\s*\w+', 3),
            (r'\bcommonly\s+(?:used|applied)\s+(?:for|when|in)\s+', 3),
            (r'\bessential\s+(?:when|for|to)\s+', 3),
            (r'\bimportant\s+(?:when|for|to)\s+', 2),
            (r'\ballows?\s+(?:you\s+)?to\s+', 2),
            (r'\bhelps?\s+(?:you\s+)?(?:to\s+)?\w+', 2),
            (r'\buseful\s+(?:when|for)\s+', 2),
            (r'\bnecessary\s+(?:when|for)\s+', 2),
            (r'\brequired\s+(?:when|for|to)\s+', 2),
            (r'\bvaluable\s+(?:when|for)\s+', 1),
            (r'\bsignificant\s+(?:when|for)\s+', 1),
        ]
        
        candidates = []
        
        for block in blocks:
            if not block.text_content:
                continue
                
            text = block.text_content.strip()
            sentences = re.split(r'(?<=[.!?])\s+', text)
            
            for sentence in sentences:
                sentence = sentence.strip()
                # Skip sentences that are too short or too long
                if len(sentence) < 25 or len(sentence) > 250:
                    continue
                    
                # Check for why-it-matters patterns
                score = 0
                sentence_lower = sentence.lower()
                
                for pattern, weight in why_patterns:
                    if re.search(pattern, sentence_lower):
                        score += weight
                
                # Bonus for sentences starting with uppercase
                if sentence and sentence[0].isupper():
                    score += 0.5
                    
                # Penalty for code-heavy sentences
                sql_keywords = ['select', 'from', 'where', 'join']
                sql_count = sum(1 for kw in sql_keywords if kw in sentence_lower)
                if sql_count >= 2:
                    score -= 2
                    
                if score > 0:
                    candidates.append((sentence, score))
        
        if not candidates:
            return None
            
        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _extract_sql_from_code_blocks(self, blocks: list[ContentBlock]) -> list[dict]:
        """
        Aggressively extract SQL from code blocks in evidence.
        
        Returns a list of dicts with sql, explanation (nearby text), and page.
        """
        examples = []
        
        for i, block in enumerate(blocks):
            if not block.text_content:
                continue
                
            # Check if this is a code block
            is_code_block = (
                hasattr(block, 'block_type') and 
                block.block_type == BlockType.SQL_CODE
            )
            
            text = block.text_content
            
            # If it's explicitly a code block, extract all SQL statements
            if is_code_block:
                # Find all SQL statements (using finditer to get full match, not just group)
                sql_pattern = r"(?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|WITH)\s+.+?;"
                matches = re.finditer(sql_pattern, text, re.IGNORECASE | re.DOTALL)
                
                for match in matches:
                    sql = match.group(0).strip()
                    if len(sql) < 10:  # Too short to be valid SQL
                        continue
                        
                    # Look for nearby explanatory text (previous block)
                    explanation = ""
                    if i > 0:
                        prev_block = blocks[i - 1]
                        if hasattr(prev_block, 'block_type') and prev_block.block_type == BlockType.EXPLANATORY_PROSE:
                            explanation = prev_block.text_content[:200] if prev_block.text_content else ""
                    
                    examples.append({
                        "sql": sql,
                        "page": block.page_number,
                        "explanation": explanation,
                        "from_source": True,
                    })
            else:
                # Even for non-code blocks, try to find SQL patterns
                # Look for SQL within the text
                sql_pattern = r"(?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|WITH)\s+.+?;"
                matches = re.finditer(sql_pattern, text, re.IGNORECASE | re.DOTALL)
                
                for match in matches:
                    sql = match.group(0).strip()
                    if len(sql) < 10 or len(sql) > 500:  # Skip too short or too long
                        continue
                        
                    # Only include if it looks like a complete example
                    if sql.upper().startswith(('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE')):
                        examples.append({
                            "sql": sql,
                            "page": block.page_number,
                            "explanation": "",
                            "from_source": True,
                        })
        
        return examples

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

    def _lookup_real_problems(self, concept_id: str) -> list[str] | None:
        """
        Look up real problem IDs for a concept.
        
        Returns a list of problem IDs if found, or None if no mapping exists.
        """
        # Load practice map from data directory (project root)
        practice_map_path = Path(__file__).parent.parent.parent / "data" / "practice_map.json"
        if practice_map_path.exists():
            with open(practice_map_path) as f:
                practice_map = json.load(f)
            return practice_map.get(concept_id)
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
    
    def _build_grounded_L1_content(
        self, 
        concept_id: str, 
        blocks: list[ContentBlock]
    ) -> L1Content:
        """Build L1 hint content grounded in evidence spans (no-LLM path)."""
        # Get info from ontology
        ontology = self._get_ontology_info(concept_id)
        
        # Extract key terms from blocks
        key_terms = self._extract_key_terms_from_blocks(blocks)
        
        # Get page references
        page_ref = self._get_page_references_str(blocks)
        
        # Build hint text using ontology if available, otherwise extract from blocks
        if ontology.get("definition"):
            hint_text = ontology["definition"]
        else:
            first_sentence = self._get_first_sentence_from_blocks(blocks)
            if first_sentence:
                hint_text = first_sentence
            else:
                hint_text = self._get_default_hint(concept_id)
        
        # Add key terms if found
        if key_terms:
            hint_text += f" Key concepts: {', '.join(key_terms)}."
        
        # Add page reference
        if page_ref:
            hint_text += f" See {page_ref} for details."
        
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
        """Build L2 hint+example content grounded in evidence spans (no-LLM path)."""
        # Extract SQL examples from blocks
        sql_examples = self._extract_sql_examples_from_blocks(blocks)
        
        if sql_examples:
            # Use the first extracted SQL example
            example_sql = sql_examples[0]["sql"]
            example_page = sql_examples[0]["page"]
            example_explanation = f"Example from page {example_page}."
        else:
            # Fall back to default example
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
    
    def _build_grounded_L3_content(
        self,
        concept_id: str,
        blocks: list[ContentBlock],
    ) -> L3Content:
        """Build L3 explanation content grounded in evidence spans (no-LLM path)."""
        # Get ontology info (for fallback use)
        ontology = self._get_ontology_info(concept_id)
        
        # Build definition: Try to extract from text first, then ontology, then default
        definition = self._extract_definition_sentence(blocks)
        if not definition:
            if ontology.get("definition"):
                definition = ontology["definition"]
            else:
                first_sentence = self._get_first_sentence_from_blocks(blocks)
                definition = first_sentence if first_sentence else self._get_default_definition(concept_id)
        
        # Build why it matters: Try to extract from text first, then ontology, then default
        why_it_matters = self._extract_why_it_matters(blocks)
        if not why_it_matters:
            if ontology.get("use_when"):
                why_it_matters = f"Use this when {ontology['use_when']}"
            else:
                why_it_matters = "Important for effective SQL querying."
        
        # Get learning objectives from ontology
        learning_objectives = self._get_learning_objectives_from_ontology(concept_id)
        
        # Build examples: Aggressively extract real SQL from code blocks
        # Only use synthetic examples if no source-linked SQL exists
        sql_examples = self._extract_sql_from_code_blocks(blocks)
        examples: list[SQLExample] = []
        
        if sql_examples:
            for i, ex in enumerate(sql_examples[:3]):  # Max 3 examples
                sql = self.transformer.transform_to_practice_schema(
                    ex["sql"], ["Sailors", "Boats", "Reserves"]
                )
                examples.append(SQLExample(
                    title=f"Example {i+1} (page {ex['page']})" if ex.get('page') else f"Example {i+1}",
                    scenario=ex.get('explanation', f"From textbook page {ex['page']}") if ex.get('page') else "Source-based example",
                    sql=sql,
                    explanation=ex.get('explanation', f"Example extracted from page {ex['page']}.") if ex.get('page') else "Example from source material.",
                    expected_output="Returns matching rows",
                    schema_used="source",  # Mark as from source
                ))
        
        # If no real examples found, use synthetic examples marked explicitly
        if not examples:
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
        real_problems = self._lookup_real_problems(concept_id)
        if real_problems:
            practice_links = [
                PracticeLink(
                    concept_id=concept_id,
                    problem_ids=real_problems,
                    needs_resolution=False,
                )
            ]
        else:
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
        """Build L4 reflective content grounded in evidence spans (no-LLM path)."""
        # Get ontology info
        ontology = self._get_ontology_info(concept_id)
        
        # Build summary
        if ontology.get("definition"):
            key_concept_summary = f"{ontology['definition']} Mastering this concept is essential for effective SQL querying."
        else:
            key_concept_summary = self._get_default_summary(concept_id)
        
        # Use ontology key points for reflection if available
        if ontology.get("key_points"):
            reflection_prompts = [f"Why is '{point}' important?" for point in ontology["key_points"][:3]]
        else:
            reflection_prompts = self._get_default_reflection_prompts(concept_id)
        
        # Build explain prompt
        explain_in_own_words = f"Explain {concept_id} in your own words as if teaching a beginner."
        if ontology.get("use_when"):
            explain_in_own_words += f" Include when you would use this (hint: {ontology['use_when']})."
        
        # Transfer questions
        transfer_questions = self._get_default_transfer_questions(concept_id)
        
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
