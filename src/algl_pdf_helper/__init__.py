__all__ = [
    "__version__",
    "models",
    "indexer",
    "concept_mapper",
    "markdown_generator",
    "pedagogical_generator",
    "prompts",
]

__version__ = "0.1.0"

# =============================================================================
# NEW PEDAGOGICAL GENERATION MODULES (Integrated 2026-02-27)
# =============================================================================
# These modules provide pedagogically structured content generation
# with practice schema alignment for SQL-Adapt integration.

from .pedagogical_generator import (
    PedagogicalContentGenerator,
    PRACTICE_SCHEMAS,
    TEXTBOOK_TO_PRACTICE_MAPPING,
    CONCEPT_TO_PROBLEMS,
)

from .prompts import (
    build_concept_prompt,
    build_sql_example_prompt,
    build_mistakes_prompt,
    build_practice_prompt,
    build_transformation_prompt,
    build_linking_prompt,
    build_batch_prompts,
    format_schema_for_prompt,
    format_examples_for_few_shot,
    get_error_patterns_for_concept,
    validate_difficulty_params,
    ERROR_PATTERNS,
    PRACTICE_SCHEMAS as PROMPT_PRACTICE_SCHEMAS,
    DIFFICULTY_GUIDELINES,
)
