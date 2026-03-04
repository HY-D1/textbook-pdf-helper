__all__ = [
    "__version__",
    "models",
    "indexer",
    "concept_mapper",
    "markdown_generator",
    "pedagogical_generator",
    "prompts",
    # Phase 4: Pedagogical Generation with Validation
    "pedagogical_models",
    "validators",
    "generation_pipeline",
    "quality_gates",
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


# =============================================================================
# PHASE 4: SAFE, CONSISTENT, AND CHEAP PEDAGOGICAL GENERATION (2026-03-01)
# =============================================================================
# These modules provide structured output validation, SQL checking,
# quality gates, and multi-pass generation optimized for 8GB M1 Mac.

# Pydantic models for structured output
from .pedagogical_models import (
    PedagogicalConcept,
    SQLExample,
    Mistake,
    PracticeReference,
    GenerationResult,
    QualityGateResult,
    QualityCheckResult,
    get_pedagogical_concept_schema,
)

# Validators for JSON and SQL
from .validators import (
    validate_concept_json,
    validate_sql_snippet,
    validate_practice_schema,
    safe_parse_json,
    extract_json_from_llm_output,
)

# Multi-pass generation pipeline
from .generation_pipeline import (
    MultiPassGenerator,
    check_model_compatibility,
    get_recommended_model,
    check_ollama_available,
    list_available_models,
    M1_8GB_MODELS,
    OPTIONAL_7B_MODELS,
)

# Quality gates for content validation
from .quality_gates import (
    QualityGate,
    QualityGateConfig,
    generate_quality_report,
    print_quality_report,
)
