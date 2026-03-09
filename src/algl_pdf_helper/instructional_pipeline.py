"""
Integrated Pipeline Orchestrator for Adaptive Textbook Helper.

This module provides the main orchestration layer that ties together all pipeline
components into a complete end-to-end system for transforming PDF textbooks into
grounded instructional unit graphs.

Pipeline Flow:
    PDF Input → Document Extraction → Section Segmentation → Content Filtering
    → Concept Mapping → Unit Generation → Misconception Bank → Reinforcement Bank
    → SQL Validation → Quality Gates → Export Filtering → Final Export

Usage:
    from algl_pdf_helper.instructional_pipeline import (
        PipelineConfig,
        InstructionalPipeline,
        PipelineStage,
        PipelineResult,
        process_pdf_to_unit_library,
        quick_process,
    )
    
    # Full configuration
    config = PipelineConfig(
        pdf_path=Path("textbook.pdf"),
        output_dir=Path("./output"),
        doc_id="sql-textbook-v1",
        llm_provider="kimi",
        llm_model="kimi-k2-5",
        filter_level="production",
    )
    
    # Run pipeline
    pipeline = InstructionalPipeline(config)
    result = pipeline.run()
    
    # Quick start
    result = quick_process("textbook.pdf", "./output")
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
from typing import Any, ClassVar, Literal

from .instructional_models import (
    InstructionalUnit,
    MisconceptionUnit,
    ReinforcementItem,
    UnitLibraryExport,
    SourceSpan,
)
from .section_extractor import SectionExtractor, ContentBlock, ContentFilter, BlockType
from .sql_ontology import ConceptOntology, SQL_CONCEPTS
from .unit_generator import UnitGenerator, GenerationConfig as UnitGenerationConfig
from .misconception_bank import MisconceptionBank, GenerationConfig as MisconceptionConfig
from .reinforcement_bank import ReinforcementBank, ReinforcementConfig
from .sql_validator import SQLValidator, ValidationLevel
from .learning_quality_gates import LearningQualityGates, Severity
from .export_filters import ExportFilterEngine, PRODUCTION_FILTERS, STRICT_FILTERS, DEVELOPMENT_FILTERS
from .unit_library_exporter import UnitLibraryExporter, ExportConfig, FilterLevel


# =============================================================================
# LOGGER SETUP
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# PIPELINE STAGE ENUM
# =============================================================================

class PipelineStage(Enum):
    """
    Enumeration of pipeline stages for progress tracking and reporting.
    
    Each stage represents a discrete processing step in the pipeline,
    allowing for granular progress tracking and checkpoint recovery.
    """
    
    EXTRACTION = auto()              # PDF text extraction
    SEGMENTATION = auto()            # Content block segmentation
    CONTENT_FILTERING = auto()       # Filtering teaching content
    CONCEPT_MAPPING = auto()         # Mapping blocks to concepts
    UNIT_GENERATION = auto()         # Generating instructional units
    MISCONCEPTION_GENERATION = auto()  # Creating misconception bank
    REINFORCEMENT_GENERATION = auto()  # Creating reinforcement items
    VALIDATION = auto()              # SQL validation
    QUALITY_GATES = auto()           # Learning quality checks
    FILTERING = auto()               # Export filtering
    EXPORT = auto()                  # Final export
    
    def __str__(self) -> str:
        """Return human-readable stage name."""
        return self.name.lower().replace("_", " ")


# =============================================================================
# PIPELINE CONFIGURATION
# =============================================================================

@dataclass
class PipelineConfig:
    """
    Configuration for the instructional pipeline.
    
    Controls all aspects of PDF processing, content generation, validation,
    and export. Provides sensible defaults for quick-start usage.
    
    Attributes:
        pdf_path: Path to the input PDF file
        output_dir: Directory for output files
        doc_id: Document identifier (auto-generated if None)
        llm_provider: LLM provider (kimi, openai, ollama)
        llm_model: Specific model name to use (provider-specific default if None)
        concept_ontology_path: Optional path to custom ontology
        filter_level: Content filtering strictness (strict/production/development)
        generate_variants: List of L1-L4 variants to generate
        skip_reinforcement: Whether to skip reinforcement generation
        skip_misconceptions: Whether to skip misconception generation
        validate_sql: Whether to validate SQL examples
        min_quality_score: Minimum quality score for export (0.0-1.0)
    """
    
    pdf_path: Path
    output_dir: Path = field(default_factory=lambda: Path("./output"))
    doc_id: str | None = None
    llm_provider: Literal["kimi", "openai", "ollama"] = "kimi"
    llm_model: str | None = None  # Will be resolved to provider-specific default
    concept_ontology_path: Path | None = None
    filter_level: Literal["strict", "production", "development"] = "production"
    generate_variants: list[str] = field(
        default_factory=lambda: [
            "L1_hint", "L2_hint_plus_example", "L3_explanation", "L4_reflective_note", "reinforcement"
        ]
    )
    skip_reinforcement: bool = False
    skip_misconceptions: bool = False
    validate_sql: bool = True
    min_quality_score: float = 0.7
    
    # Provider-specific default models
    PROVIDER_DEFAULT_MODELS: ClassVar[dict[str, str]] = {
        "kimi": "kimi-k2-5",
        "openai": "gpt-4",
        "ollama": "llama3.2:3b",
    }
    
    def __post_init__(self):
        """Validate configuration and set defaults."""
        # Ensure paths are Path objects
        self.pdf_path = Path(self.pdf_path)
        self.output_dir = Path(self.output_dir)
        
        # Generate doc_id if not provided
        if self.doc_id is None:
            self.doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        
        # Validate filter level
        if self.filter_level not in ("strict", "production", "development"):
            raise ValueError(f"Invalid filter_level: {self.filter_level}")
        
        # Validate quality score range
        if not 0.0 <= self.min_quality_score <= 1.0:
            raise ValueError("min_quality_score must be between 0.0 and 1.0")
        
        # Check PDF exists
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {self.pdf_path}")
        
        # Resolve provider-specific default model
        if self.llm_model is None:
            self.llm_model = self.PROVIDER_DEFAULT_MODELS.get(
                self.llm_provider, "kimi-k2-5"
            )
        
        # Validate provider-model combination
        self._validate_provider_model()
    
    def _validate_provider_model(self) -> None:
        """Validate that the model is appropriate for the provider."""
        provider = self.llm_provider
        model = self.llm_model
        
        # Provider-specific model patterns
        provider_patterns = {
            "kimi": ["kimi-"],
            "openai": ["gpt-", "o1-", "o3-", "text-"],
            "ollama": [],  # Ollama accepts any local model name
        }
        
        patterns = provider_patterns.get(provider, [])
        
        # Check if model appears to be for a different provider
        if provider == "kimi" and any(model.startswith(p) for p in ["gpt-", "o1-", "o3-"]):
            raise ValueError(
                f"Model '{model}' appears to be an OpenAI model, "
                f"but provider is set to '{provider}'. "
                f"Did you mean to use --llm-provider openai?"
            )
        
        if provider == "openai" and model.startswith("kimi-"):
            raise ValueError(
                f"Model '{model}' appears to be a Kimi model, "
                f"but provider is set to '{provider}'. "
                f"Did you mean to use --llm-provider kimi?"
            )
        
        # For Ollama, warn about potential incompatible models but don't fail
        if provider == "ollama":
            if any(model.startswith(p) for p in ["kimi-", "gpt-", "o1-", "o3-", "claude-"]):
                logger.warning(
                    f"Model '{model}' appears to be a cloud API model, "
                    f"but provider is set to 'ollama'. "
                    f"This will likely fail. Use a local model name like 'llama3.2:3b'."
                )


# =============================================================================
# PIPELINE RESULT
# =============================================================================

@dataclass
class PipelineResult:
    """
    Result of running the instructional pipeline.
    
    Contains success status, completed/failed stages, generated content,
    quality metrics, and timing information.
    
    Attributes:
        success: Whether the pipeline completed successfully
        stages_completed: List of stages that completed
        stages_failed: List of (stage, error_message) tuples for failures
        unit_library: Generated UnitLibraryExport (if successful)
        quality_report: Detailed quality metrics
        output_path: Path to exported files
        statistics: Processing statistics by stage
        elapsed_time_seconds: Total pipeline execution time
        fallback_units: List of unit IDs that used fallback generation
        filtered_units: List of unit IDs that were filtered out
    """
    
    success: bool = False
    stages_completed: list[PipelineStage] = field(default_factory=list)
    stages_failed: list[tuple[PipelineStage, str]] = field(default_factory=list)
    unit_library: UnitLibraryExport | None = None
    quality_report: dict[str, Any] = field(default_factory=dict)
    output_path: Path | None = None
    statistics: dict[str, Any] = field(default_factory=dict)
    elapsed_time_seconds: float = 0.0
    fallback_units: list[str] = field(default_factory=list)
    filtered_units: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "success": self.success,
            "stages_completed": [s.name for s in self.stages_completed],
            "stages_failed": [(s.name, msg) for s, msg in self.stages_failed],
            "has_unit_library": self.unit_library is not None,
            "quality_report": self.quality_report,
            "output_path": str(self.output_path) if self.output_path else None,
            "statistics": self.statistics,
            "elapsed_time_seconds": self.elapsed_time_seconds,
            "fallback_units": self.fallback_units,
            "filtered_units": self.filtered_units,
        }
    
    def get_summary(self) -> str:
        """Generate a human-readable summary of the pipeline result."""
        lines = [
            "=" * 60,
            "Pipeline Execution Summary",
            "=" * 60,
            f"Success: {'✅ Yes' if self.success else '❌ No'}",
            f"Stages Completed: {len(self.stages_completed)}/10",
            f"Stages Failed: {len(self.stages_failed)}",
            f"Elapsed Time: {self.elapsed_time_seconds:.2f}s",
        ]
        
        if self.fallback_units:
            lines.append(f"Fallback Units: {len(self.fallback_units)}")
        if self.filtered_units:
            lines.append(f"Filtered Units: {len(self.filtered_units)}")
        
        if self.stages_failed:
            lines.append("\nFailed Stages:")
            for stage, msg in self.stages_failed:
                lines.append(f"  - {stage.name}: {msg}")
        
        if self.statistics:
            lines.append("\nStatistics:")
            for key, value in self.statistics.items():
                lines.append(f"  - {key}: {value}")
        
        if self.output_path:
            lines.append(f"\nOutput: {self.output_path}")
        
        lines.append("=" * 60)
        return "\n".join(lines)


# =============================================================================
# PIPELINE PROGRESS TRACKER
# =============================================================================

class PipelineProgressTracker:
    """
    Tracks progress through pipeline stages with ETA estimation.
    
    Provides real-time progress updates, stage timing, and ETA calculations
    based on historical stage durations.
    
    Example:
        tracker = PipelineProgressTracker()
        tracker.start_stage(PipelineStage.EXTRACTION)
        # ... do work ...
        tracker.end_stage(PipelineStage.EXTRACTION)
        print(tracker.get_progress_report())
    """
    
    # Historical average durations for ETA estimation (in seconds)
    STAGE_DURATIONS: dict[PipelineStage, float] = {
        PipelineStage.EXTRACTION: 5.0,
        PipelineStage.SEGMENTATION: 10.0,
        PipelineStage.CONCEPT_MAPPING: 15.0,
        PipelineStage.UNIT_GENERATION: 60.0,
        PipelineStage.MISCONCEPTION_GENERATION: 30.0,
        PipelineStage.REINFORCEMENT_GENERATION: 30.0,
        PipelineStage.VALIDATION: 20.0,
        PipelineStage.QUALITY_GATES: 10.0,
        PipelineStage.FILTERING: 5.0,
        PipelineStage.EXPORT: 5.0,
    }
    
    def __init__(self):
        """Initialize the progress tracker."""
        self.stage_timings: dict[PipelineStage, tuple[float, float | None]] = {}
        self.current_stage: PipelineStage | None = None
        self.stage_start_time: float | None = None
        self._logger = logging.getLogger(__name__)
    
    def start_stage(self, stage: PipelineStage) -> None:
        """Mark the start of a pipeline stage."""
        self.current_stage = stage
        self.stage_start_time = time.time()
        self.stage_timings[stage] = (self.stage_start_time, None)
        self._logger.info(f"Starting stage: {stage.name}")
    
    def end_stage(self, stage: PipelineStage, success: bool = True) -> float:
        """
        Mark the end of a pipeline stage.
        
        Args:
            stage: The stage that completed
            success: Whether the stage completed successfully
            
        Returns:
            Duration of the stage in seconds
        """
        end_time = time.time()
        start_time = self.stage_timings.get(stage, (end_time, None))[0]
        duration = end_time - start_time
        
        self.stage_timings[stage] = (start_time, end_time)
        self.current_stage = None
        self.stage_start_time = None
        
        status = "✅ completed" if success else "❌ failed"
        self._logger.info(f"Stage {stage.name} {status} in {duration:.2f}s")
        
        return duration
    
    def get_current_progress(self) -> dict[str, Any]:
        """Get current progress information."""
        completed = [s for s, (_, end) in self.stage_timings.items() if end is not None]
        total_stages = len(PipelineStage)
        progress_pct = len(completed) / total_stages * 100
        
        result = {
            "completed_stages": len(completed),
            "total_stages": total_stages,
            "progress_percentage": progress_pct,
            "current_stage": self.current_stage.name if self.current_stage else None,
        }
        
        # Calculate ETA if there's a current stage
        if self.current_stage:
            elapsed = time.time() - self.stage_start_time
            expected = self.STAGE_DURATIONS.get(self.current_stage, 30.0)
            remaining = max(0, expected - elapsed)
            
            # Add remaining stages
            for stage in PipelineStage:
                if stage not in self.stage_timings:
                    remaining += self.STAGE_DURATIONS.get(stage, 30.0)
            
            result["eta_seconds"] = remaining
        else:
            result["eta_seconds"] = 0.0
        
        return result
    
    def get_stage_durations(self) -> dict[str, float]:
        """Get durations for all completed stages."""
        durations = {}
        for stage, (start, end) in self.stage_timings.items():
            if end is not None:
                durations[stage.name] = end - start
            elif stage == self.current_stage and self.stage_start_time:
                durations[stage.name] = time.time() - self.stage_start_time
        return durations
    
    def get_progress_report(self) -> str:
        """Generate a human-readable progress report."""
        progress = self.get_current_progress()
        lines = [
            "-" * 50,
            f"Progress: {progress['completed_stages']}/{progress['total_stages']} stages "
            f"({progress['progress_percentage']:.1f}%)",
        ]
        
        if progress["current_stage"]:
            lines.append(f"Current: {progress['current_stage']}")
            lines.append(f"ETA: {progress['eta_seconds']:.1f}s")
        
        lines.append("-" * 50)
        return "\n".join(lines)


# =============================================================================
# INSTRUCTIONAL PIPELINE
# =============================================================================

class InstructionalPipeline:
    """
    Main orchestrator for the PDF → grounded instructional unit graph pipeline.
    
    Coordinates all pipeline stages from document extraction through final export,
    with comprehensive error handling, progress tracking, and checkpoint support.
    
    Example:
        config = PipelineConfig(pdf_path="textbook.pdf", output_dir="./output")
        pipeline = InstructionalPipeline(config)
        result = pipeline.run()
        
        if result.success:
            print(f"Exported to: {result.output_path}")
        else:
            print(f"Failed stages: {result.stages_failed}")
    """
    
    def __init__(self, config: PipelineConfig):
        """
        Initialize the pipeline with configuration.
        
        Args:
            config: Pipeline configuration
        """
        self.config = config
        self.progress = PipelineProgressTracker()
        self._ontology: ConceptOntology | None = None
        self._extractor: SectionExtractor | None = None
        self._unit_generator: UnitGenerator | None = None
        self._misconception_bank: MisconceptionBank | None = None
        self._reinforcement_bank: ReinforcementBank | None = None
        self._sql_validator: SQLValidator | None = None
        self._quality_gates: LearningQualityGates | None = None
        self._filter_engine: ExportFilterEngine | None = None
        self._exporter: UnitLibraryExporter | None = None
        
        # Store intermediate results
        self._raw_text: str = ""
        self._extraction_metadata: dict[str, Any] = {}
        self._content_blocks: list[ContentBlock] = []
        self._teaching_blocks: list[ContentBlock] = []
        self._concept_blocks: dict[str, list[ContentBlock]] = {}
        self._instructional_units: list[InstructionalUnit] = []
        self._misconception_units: list[MisconceptionUnit] = []
        self._reinforcement_items: list[ReinforcementItem] = []
        self._validation_results: dict[str, Any] = {}
        self._quality_report: dict[str, Any] = {}
        self._filtered_unit_ids: list[str] = []
        self._filtered_library: UnitLibraryExport | None = None
        self._generation_stats: dict[str, int] = {}
        
        self._logger = logging.getLogger(__name__)
        self._logger.info(f"Pipeline initialized for: {config.pdf_path}")
        
        # Control whether to log detailed filter results (set to True when CLI handles output)
        self._quiet_filter_logging = False
    
    def run(self) -> PipelineResult:
        """
        Execute the full pipeline.
        
        Runs all stages sequentially with error handling. If a stage fails,
        returns partial results with error information.
        
        Returns:
            PipelineResult with success status and all outputs
        """
        start_time = time.time()
        result = PipelineResult()
        
        try:
            # Stage 1: Document Extraction
            self._run_stage(PipelineStage.EXTRACTION, self._extract_pdf, result)
            
            # Stage 2: Section Segmentation
            self._run_stage(PipelineStage.SEGMENTATION, self._segment_content, result)
            
            # Stage 3: Content Filtering
            self._run_stage(PipelineStage.CONTENT_FILTERING, self._filter_teaching_content, result)
            
            # Stage 4: Concept Mapping
            self._run_stage(PipelineStage.CONCEPT_MAPPING, self._map_to_concepts, result)
            
            # Stage 5: Unit Generation
            self._run_stage(PipelineStage.UNIT_GENERATION, self._generate_units, result)
            
            # Stage 6: Misconception Bank
            if not self.config.skip_misconceptions:
                self._run_stage(
                    PipelineStage.MISCONCEPTION_GENERATION, 
                    self._generate_misconceptions, 
                    result
                )
            
            # Stage 7: Reinforcement Bank
            if not self.config.skip_reinforcement:
                self._run_stage(
                    PipelineStage.REINFORCEMENT_GENERATION,
                    self._generate_reinforcement,
                    result
                )
            
            # Stage 8: SQL Validation
            if self.config.validate_sql:
                self._run_stage(PipelineStage.VALIDATION, self._validate_sql_examples, result)
            
            # Stage 9: Quality Gates
            self._run_stage(PipelineStage.QUALITY_GATES, self._run_quality_gates, result)
            
            # Stage 10: Export Filtering
            self._run_stage(PipelineStage.FILTERING, self._apply_export_filters, result)
            
            # Stage 11: Export
            export_path = self._run_stage(PipelineStage.EXPORT, self._export, result)
            if export_path:
                result.output_path = export_path
            
            result.success = len(result.stages_failed) == 0
            
        except Exception as e:
            self._logger.exception("Pipeline execution failed")
            result.success = False
            if self.progress.current_stage:
                result.stages_failed.append((self.progress.current_stage, str(e)))
        
        finally:
            result.elapsed_time_seconds = time.time() - start_time
            result.quality_report = self._quality_report
            result.statistics = self._gather_statistics()
            result.filtered_units = getattr(self, '_filtered_unit_ids', [])
            result.fallback_units = getattr(self, '_fallback_unit_ids', [])
            
            self._logger.info(f"Pipeline completed in {result.elapsed_time_seconds:.2f}s")
        
        return result
    
    def _run_stage(
        self, 
        stage: PipelineStage, 
        stage_fn: callable,
        result: PipelineResult
    ) -> Any:
        """Run a single pipeline stage with error handling.
        
        Returns:
            The return value from the stage function, or None if stage failed.
        """
        self.progress.start_stage(stage)
        try:
            result_value = stage_fn()
            self.progress.end_stage(stage, success=True)
            result.stages_completed.append(stage)
            return result_value
        except Exception as e:
            self.progress.end_stage(stage, success=False)
            result.stages_failed.append((stage, str(e)))
            self._logger.error(f"Stage {stage.name} failed: {e}")
            raise  # Re-raise to stop pipeline
    
    # ========================================================================
    # STAGE METHODS
    # ========================================================================
    
    def _extract_pdf(self) -> tuple[str, dict]:
        """
        Stage 1: Extract raw text from PDF.
        
        Uses SectionExtractor to extract text with layout preservation.
        
        Returns:
            Tuple of (raw_text, metadata)
        """
        self._logger.info("Stage 1: Extracting PDF content")
        
        self._extractor = SectionExtractor()
        
        # For now, we extract blocks which gives us text content
        blocks = self._extractor.extract_blocks(
            self.config.pdf_path,
            self.config.doc_id
        )
        
        # Combine all text content
        text_parts = []
        for block in blocks:
            if block.block_type not in (BlockType.ADMIN_TEXT, BlockType.UNKNOWN):
                text_parts.append(block.text_content)
        
        self._raw_text = "\n\n".join(text_parts)
        self._extraction_metadata = {
            "total_blocks": len(blocks),
            "text_length": len(self._raw_text),
            "doc_id": self.config.doc_id,
        }
        
        self._logger.info(f"Extracted {len(self._raw_text)} characters from {len(blocks)} blocks")
        return self._raw_text, self._extraction_metadata
    
    def _segment_content(self, raw_text: str | None = None) -> list[ContentBlock]:
        """
        Stage 2: Segment content into typed blocks.
        
        Uses SectionExtractor to identify headings, code blocks, exercises, etc.
        
        Args:
            raw_text: Optional raw text (uses extracted text if None)
            
        Returns:
            List of ContentBlock objects
        """
        self._logger.info("Stage 2: Segmenting content")
        
        if raw_text is None:
            raw_text = self._raw_text
        
        # Re-use extractor or create new one
        if self._extractor is None:
            self._extractor = SectionExtractor()
        
        self._content_blocks = self._extractor.extract_blocks(
            self.config.pdf_path,
            self.config.doc_id
        )
        
        self._logger.info(f"Segmented into {len(self._content_blocks)} content blocks")
        return self._content_blocks
    
    def _filter_teaching_content(self, blocks: list[ContentBlock] | None = None) -> list[ContentBlock]:
        """
        Stage 3: Filter out non-teaching content.
        
        Removes TOC, copyright, configuration, and other non-instructional material.
        
        Args:
            blocks: Optional blocks to filter (uses stored blocks if None)
            
        Returns:
            Filtered list of teaching ContentBlocks
        """
        self._logger.info("Stage 3: Filtering teaching content")
        
        if blocks is None:
            blocks = self._content_blocks
        
        content_filter = ContentFilter()
        self._teaching_blocks = content_filter.filter_blocks(blocks)
        
        self._logger.info(
            f"Filtered to {len(self._teaching_blocks)} teaching blocks "
            f"(removed {len(blocks) - len(self._teaching_blocks)} non-teaching)"
        )
        return self._teaching_blocks
    
    def _map_to_concepts(self, blocks: list[ContentBlock] | None = None) -> dict[str, list[ContentBlock]]:
        """
        Stage 4: Map content blocks to canonical concepts with weighted scoring.
        
        Uses heading-aware matching, block-type weighting, and ontology aliases
        to assign blocks to relevant concepts with higher precision.
        
        Args:
            blocks: Optional blocks to map (uses teaching blocks if None)
            
        Returns:
            Dictionary mapping concept_id to list of ContentBlocks
        """
        self._logger.info("Stage 4: Mapping content to concepts with weighted scoring")
        
        if blocks is None:
            blocks = self._teaching_blocks
        
        # Initialize ontology
        self._ontology = ConceptOntology()
        
        # Block type weights for scoring
        BLOCK_WEIGHTS = {
            BlockType.HEADING: 2.0,
            BlockType.SUBHEADING: 1.5,
            BlockType.SQL_CODE: 1.3,
            BlockType.EXPLANATORY_PROSE: 1.0,
            BlockType.FIGURE: 0.8,
            BlockType.SIDEBAR: 0.6,
            BlockType.ADMIN_TEXT: 0.0,
            BlockType.UNKNOWN: 0.3,
        }
        
        concept_blocks = {}
        
        for concept_id in self._ontology.list_all_concepts():
            concept = self._ontology.get_concept(concept_id)
            if not concept:
                continue
            
            # Get keywords from concept title + aliases
            keywords = self._extract_concept_keywords(concept)
            
            scored_blocks = []
            for block in blocks:
                # Skip admin blocks
                if block.block_type == BlockType.ADMIN_TEXT:
                    continue
                
                # Base score from keyword overlap
                block_text = block.text_content.lower()
                keyword_matches = sum(1 for kw in keywords if kw in block_text)
                base_score = keyword_matches / max(len(keywords), 1)
                
                # Boost for headings containing keywords
                if block.block_type in (BlockType.HEADING, BlockType.SUBHEADING):
                    if any(kw in block_text for kw in keywords):
                        base_score *= 2.0
                
                # Boost for SQL code blocks near concept examples
                if block.block_type == BlockType.SQL_CODE:
                    concept_id_lower = concept_id.lower()
                    if concept_id_lower in block_text:
                        base_score *= 1.5
                
                # Apply block type weight
                weight = BLOCK_WEIGHTS.get(block.block_type, 0.5)
                final_score = base_score * weight
                
                if final_score > 0.3:  # Threshold
                    scored_blocks.append((block, final_score))
            
            # Sort by score and take top blocks
            scored_blocks.sort(key=lambda x: x[1], reverse=True)
            concept_blocks[concept_id] = [b for b, s in scored_blocks[:15]]
        
        # Filter to concepts with actual content
        self._concept_blocks = {k: v for k, v in concept_blocks.items() if v}
        
        self._logger.info(f"Mapped content to {len(self._concept_blocks)} concepts")
        return self._concept_blocks
    
    def _extract_concept_keywords(self, concept: dict) -> set[str]:
        """Extract keywords from concept definition including ontology aliases."""
        keywords = set()
        
        # Title words
        title = concept.get("title", "").lower()
        keywords.update(w for w in title.split() if len(w) > 2)
        
        # Aliases/synonyms from ontology
        aliases = concept.get("aliases", [])
        for alias in aliases:
            keywords.update(w for w in alias.lower().split() if len(w) > 2)
        
        # Add concept id parts
        concept_id = concept.get("id", "").lower()
        keywords.update(w for w in concept_id.replace("-", " ").split() if len(w) > 2)
        
        # Key SQL terms based on concept type
        concept_id_lower = concept.get("id", "").lower()
        if "select" in concept_id_lower:
            keywords.update(["select", "column", "retrieve", "query"])
        if "join" in concept_id_lower:
            keywords.update(["join", "inner", "outer", "left", "right", "on"])
        if "group" in concept_id_lower:
            keywords.update(["group by", "aggregate", "count", "sum", "avg"])
        if "where" in concept_id_lower:
            keywords.update(["where", "filter", "condition"])
        if "order" in concept_id_lower:
            keywords.update(["order by", "sort", "asc", "desc"])
        if "subquery" in concept_id_lower:
            keywords.update(["subquery", "nested", "inner query"])
        if "aggregate" in concept_id_lower:
            keywords.update(["count", "sum", "avg", "min", "max"])
        if "null" in concept_id_lower:
            keywords.update(["null", "is null", "is not null"])
        
        # Learning objectives keywords
        for objective in concept.get("learning_objectives", []):
            words = objective.lower().split()
            keywords.update(w for w in words[:5] if len(w) > 2)
        
        return keywords
    
    def _generate_units(self, concept_blocks: dict[str, list[ContentBlock]] | None = None) -> list[InstructionalUnit]:
        """
        Stage 5: Generate instructional units for all variants.
        
        Creates L1-L4 variants and reinforcement units for each concept.
        
        Args:
            concept_blocks: Optional concept block mapping (uses stored if None)
            
        Returns:
            List of generated InstructionalUnit objects
        """
        self._logger.info("Stage 5: Generating instructional units")
        
        if concept_blocks is None:
            concept_blocks = self._concept_blocks
        
        self._unit_generator = UnitGenerator()
        gen_config = UnitGenerationConfig(
            llm_provider=self.config.llm_provider,
            model_name=self.config.llm_model,
        )
        
        self._instructional_units = []
        self._fallback_unit_ids = []
        
        for concept_id, blocks in concept_blocks.items():
            if not blocks:
                continue
            
            # Get prerequisites from ontology
            prereqs = []
            if self._ontology:
                prereqs = self._ontology.get_prerequisites(concept_id)
            
            try:
                # Generate all variants
                variants = self._unit_generator.generate_all_variants(
                    concept_id=concept_id,
                    source_blocks=blocks,
                    config=gen_config,
                    prerequisites=prereqs,
                )
                
                # Add generated units
                for variant_name, unit in variants.items():
                    if unit.target_stage in self.config.generate_variants:
                        self._instructional_units.append(unit)
                        
                        # Track fallback units
                        if unit.content.get("_metadata", {}).get("is_fallback"):
                            self._fallback_unit_ids.append(unit.unit_id)
                
            except Exception as e:
                self._logger.warning(f"Failed to generate units for {concept_id}: {e}")
                continue
        
        self._logger.info(f"Generated {len(self._instructional_units)} instructional units")
        
        # Fail strict mode if fallback units exist
        if self.config.filter_level == "strict" and self._fallback_unit_ids:
            raise RuntimeError(
                f"Strict mode: {len(self._fallback_unit_ids)} fallback units created. "
                f"Unit IDs: {self._fallback_unit_ids[:5]}..."
            )
        
        return self._instructional_units
    
    def _generate_misconceptions(
        self, 
        concept_blocks: dict[str, list[ContentBlock]] | None = None
    ) -> list[MisconceptionUnit]:
        """
        Stage 6: Generate misconception remediation units.
        
        Creates error-linked remediation content for common mistakes.
        
        Args:
            concept_blocks: Optional concept block mapping (uses stored if None)
            
        Returns:
            List of generated MisconceptionUnit objects
        """
        self._logger.info("Stage 6: Generating misconception bank")
        
        if concept_blocks is None:
            concept_blocks = self._concept_blocks
        
        self._misconception_bank = MisconceptionBank.load_default()
        config = MisconceptionConfig()
        
        self._misconception_units = []
        
        for concept_id, blocks in concept_blocks.items():
            # Get patterns for this concept
            patterns = self._misconception_bank.get_patterns_for_concept(concept_id)
            
            if not patterns:
                continue
            
            # Generate units for each error subtype
            error_subtypes = list(set(p.error_subtype_id for p in patterns))
            
            try:
                units = self._misconception_bank.generate_for_concept(
                    concept_id=concept_id,
                    source_blocks=[b.to_dict() for b in blocks],
                    error_subtypes=error_subtypes,
                    config=config,
                )
                self._misconception_units.extend(units)
                
            except Exception as e:
                self._logger.warning(f"Failed to generate misconceptions for {concept_id}: {e}")
                continue
        
        self._logger.info(f"Generated {len(self._misconception_units)} misconception units")
        return self._misconception_units
    
    def _generate_reinforcement(self, units: list[InstructionalUnit] | None = None) -> list[ReinforcementItem]:
        """
        Stage 7: Generate reinforcement items for spaced repetition.
        
        Creates micro-checks for concept reinforcement.
        
        Args:
            units: Optional list of units (uses generated units if None)
            
        Returns:
            List of generated ReinforcementItem objects
        """
        self._logger.info("Stage 7: Generating reinforcement bank")
        
        if units is None:
            units = self._instructional_units
        
        self._reinforcement_bank = ReinforcementBank()
        config = ReinforcementConfig()
        
        self._reinforcement_items = []
        
        # Group units by concept
        units_by_concept: dict[str, list[InstructionalUnit]] = {}
        for unit in units:
            if unit.concept_id not in units_by_concept:
                units_by_concept[unit.concept_id] = []
            units_by_concept[unit.concept_id].append(unit)
        
        for concept_id, concept_units in units_by_concept.items():
            try:
                items = self._reinforcement_bank.generate_for_concept(
                    concept_id=concept_id,
                    concept_units=concept_units,
                    config=config,
                )
                self._reinforcement_items.extend(items)
                
            except Exception as e:
                self._logger.warning(f"Failed to generate reinforcement for {concept_id}: {e}")
                continue
        
        self._logger.info(f"Generated {len(self._reinforcement_items)} reinforcement items")
        return self._reinforcement_items
    
    def _validate_sql_examples(self, units: list[InstructionalUnit] | None = None) -> dict:
        """
        Stage 8: Validate SQL examples in instructional units.
        
        Runs three-layer validation: parse, execution, and semantic.
        
        Args:
            units: Optional list of units (uses generated units if None)
            
        Returns:
            Dictionary with validation results by unit
        """
        self._logger.info("Stage 8: Validating SQL examples")
        
        if units is None:
            units = self._instructional_units
        
        self._sql_validator = SQLValidator()
        self._validation_results = {
            "total_units": len(units),
            "validated_units": 0,
            "valid_units": 0,
            "invalid_units": 0,
            "details": {},
        }
        
        for unit in units:
            unit_results = []
            
            # Extract SQL examples from unit content
            content = unit.content or {}
            examples = content.get("examples", [])
            
            for ex in examples:
                sql = ex.get("sql", "") if isinstance(ex, dict) else ""
                if not sql:
                    continue
                
                try:
                    result = self._sql_validator.validate(
                        sql=sql,
                        expected_concept=unit.concept_id,
                    )
                    unit_results.append({
                        "sql": sql[:100],
                        "is_valid": result.is_valid,
                        "semantic_score": result.semantic_score,
                        "errors": [e.message for e in result.errors],
                    })
                    
                    if result.is_valid:
                        self._validation_results["valid_units"] += 1
                    else:
                        self._validation_results["invalid_units"] += 1
                        
                except Exception as e:
                    unit_results.append({
                        "sql": sql[:100],
                        "is_valid": False,
                        "error": str(e),
                    })
                    self._validation_results["invalid_units"] += 1
            
            if unit_results:
                self._validation_results["details"][unit.unit_id] = unit_results
                self._validation_results["validated_units"] += 1
        
        self._logger.info(
            f"Validated SQL: {self._validation_results['valid_units']} valid, "
            f"{self._validation_results['invalid_units']} invalid"
        )
        return self._validation_results
    
    def _gather_quality_report(self, units: list[InstructionalUnit]) -> dict:
        """
        Generate a quality report for the given units.
        
        This helper method runs quality gates on any set of units and
        returns a complete quality report dictionary.
        
        Args:
            units: List of units to check
            
        Returns:
            Quality report dictionary
        """
        if self._quality_gates is None:
            self._quality_gates = LearningQualityGates(ontology=self._ontology)
        
        checks_by_unit = {}
        total_score = 0.0
        
        for unit in units:
            unit_checks = []
            unit_score = 0.0
            check_count = 0
            
            # Run key quality checks
            checks = [
                self._quality_gates.validate_canonical_mapping(unit),
                self._quality_gates.validate_source_evidence(unit),
                self._quality_gates.validate_content_relevance(unit),
                self._quality_gates.validate_explanation_quality(unit),
                self._quality_gates.validate_practice_included(unit),
                self._quality_gates.validate_takeaway_present(unit),
                self._quality_gates.validate_prerequisite_tags(unit),
                self._quality_gates.validate_error_subtype_tags(unit),
            ]
            
            for check in checks:
                unit_checks.append({
                    "name": check.check_name,
                    "passed": check.passed,
                    "score": check.score,
                    "message": check.message,
                    "severity": check.severity.value,
                })
                unit_score += check.score
                check_count += 1
            
            avg_score = unit_score / check_count if check_count > 0 else 0.0
            checks_by_unit[unit.unit_id] = {
                "checks": unit_checks,
                "average_score": avg_score,
            }
            total_score += avg_score
        
        overall_score = total_score / len(units) if units else 0.0
        passed = overall_score >= self.config.min_quality_score
        
        return {
            "summary": {
                "total_units_checked": len(units),
                "overall_score": overall_score,
                "passed": passed,
                "pass_rate": len([u for u in checks_by_unit.values() if u["average_score"] >= self.config.min_quality_score]) / len(units) if units else 0.0,
            },
            "checks_by_unit": checks_by_unit,
            "recommendations": self._generate_recommendations(checks_by_unit),
        }
    
    def _save_quality_report(self, report: dict, filename: str) -> Path:
        """
        Save a quality report to the output directory.
        
        Args:
            report: Quality report dictionary
            filename: Name of the file to save (e.g., "quality_report_generated.json")
            
        Returns:
            Path to the saved file
        """
        # Enhance report with timestamp and version
        enhanced_report = {
            "version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            **report,
        }
        
        filepath = self.config.output_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        import json
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(enhanced_report, f, indent=2)
        
        self._logger.info(f"Saved quality report: {filepath}")
        return filepath
    
    def _run_quality_gates(self, units: list[InstructionalUnit] | None = None) -> dict:
        """
        Stage 9: Run learning quality gates on all content.
        
        Validates content for learning utility, not just format compliance.
        Generates a pre-filter quality report for all generated units.
        
        Args:
            units: Optional list of units (uses generated units if None)
            
        Returns:
            Quality report dictionary (for generated units)
        """
        self._logger.info("Stage 9: Running quality gates")
        
        if units is None:
            units = self._instructional_units
        
        # Generate pre-filter quality report for all generated units
        self._quality_report = self._gather_quality_report(units)
        
        # Save as pre-filter report
        self._save_quality_report(self._quality_report, "quality_report_generated.json")
        
        overall_score = self._quality_report["summary"]["overall_score"]
        passed = self._quality_report["summary"]["passed"]
        self._logger.info(f"Quality gates: overall score {overall_score:.2f}, passed: {passed}")
        return self._quality_report
    
    def _generate_recommendations(self, checks_by_unit: dict) -> list[str]:
        """Generate improvement recommendations from quality check results."""
        recommendations = []
        
        # Count common failures
        failure_counts: dict[str, int] = {}
        for unit_data in checks_by_unit.values():
            for check in unit_data["checks"]:
                if not check["passed"]:
                    name = check["name"]
                    failure_counts[name] = failure_counts.get(name, 0) + 1
        
        # Generate recommendations for common issues
        if failure_counts.get("source_evidence", 0) > len(checks_by_unit) * 0.3:
            recommendations.append(
                "Many units lack source evidence - improve extraction confidence"
            )
        
        if failure_counts.get("explanation_quality", 0) > len(checks_by_unit) * 0.3:
            recommendations.append(
                "Many units lack quality explanations - review content generation"
            )
        
        if failure_counts.get("practice_included", 0) > len(checks_by_unit) * 0.3:
            recommendations.append(
                "Many units lack practice items - add exercises and checks"
            )
        
        return recommendations
    
    def _apply_export_filters(
        self,
        units: list[InstructionalUnit] | None = None,
        misconception_units: list[MisconceptionUnit] | None = None,
        reinforcement_items: list[ReinforcementItem] | None = None
    ) -> UnitLibraryExport:
        """
        Stage 10: Apply export filters to content.
        
        Filters content based on configured filter level (strict/production/development).
        In strict mode, raises RuntimeError if any units are filtered.
        
        Args:
            units: Optional units (uses generated if None)
            misconception_units: Optional misconception units
            reinforcement_items: Optional reinforcement items
            
        Returns:
            Filtered UnitLibraryExport
            
        Raises:
            RuntimeError: In strict mode if any units fail filtering
        """
        self._logger.info("Stage 10: Applying export filters")
        
        if units is None:
            units = self._instructional_units
        if misconception_units is None:
            misconception_units = self._misconception_units
        if reinforcement_items is None:
            reinforcement_items = self._reinforcement_items
        
        # Select filter set based on config
        filter_map = {
            "strict": STRICT_FILTERS,
            "production": PRODUCTION_FILTERS,
            "development": DEVELOPMENT_FILTERS,
        }
        filters = filter_map.get(self.config.filter_level, PRODUCTION_FILTERS)
        
        self._filter_engine = ExportFilterEngine(filters)
        
        # Create a temporary library for filtering
        temp_library = UnitLibraryExport(
            source_pdf_id=self.config.doc_id,
            instructional_units=units,
            misconception_bank=misconception_units,
            reinforcement_bank=reinforcement_items,
        )
        
        # Apply filters to get filtered library
        filter_result = self._filter_engine.filter_unit_library(temp_library)
        filtered_library = self._filter_engine.get_exportable_subset(temp_library)
        
        # Store filtered unit IDs for reporting
        self._filtered_unit_ids = filter_result.filtered_units
        
        # In strict mode, fail if any units are filtered
        if self.config.filter_level == "strict" and filter_result.filtered_units:
            rejected = self._filter_engine.get_rejected_units(temp_library)
            error_msg = f"Strict mode: {len(filter_result.filtered_units)} units blocked:\n"
            for unit_id, reasons in rejected[:5]:
                error_msg += f"  - {unit_id}: {reasons[0] if reasons else 'Unknown reason'}\n"
            if len(rejected) > 5:
                error_msg += f"  ... and {len(rejected) - 5} more\n"
            raise RuntimeError(error_msg)
        
        # Log filter results (skip detailed logging if CLI handles output)
        if not self._quiet_filter_logging:
            if filter_result.filtered_units:
                self._logger.warning(
                    f"Filtered {len(filter_result.filtered_units)} units "
                    f"({filter_result.pass_rate:.1%} pass rate)"
                )
                for unit_id in filter_result.filtered_units[:5]:
                    self._logger.warning(f"  Filtered: {unit_id}")
                if len(filter_result.filtered_units) > 5:
                    self._logger.warning(f"  ... and {len(filter_result.filtered_units) - 5} more")
            else:
                self._logger.info("All units passed export filters")
        
        # Build concept graph from actually mapped concepts
        concept_graph = self._build_concept_graph(filtered_library)
        
        # Calculate generation statistics
        generated_count = len(units)
        filtered_out_count = len(filter_result.filtered_units)
        exported_count = len(filtered_library.instructional_units)
        
        # Generate post-filter quality report for exported units
        self._logger.info("Generating post-filter quality report for exported units")
        post_filter_report = self._gather_quality_report(filtered_library.instructional_units)
        self._save_quality_report(post_filter_report, "quality_report_exported.json")
        
        # Store both quality reports for the exporter
        self._post_filter_quality_report = post_filter_report
        
        # Update the filtered library with remaining metadata
        filtered_library.concept_ontology = {"version": "1.0.0"}
        filtered_library.concept_graph = concept_graph
        # Use post-filter report as the primary quality report (represents what's actually exported)
        filtered_library.quality_report = post_filter_report
        if not filtered_library.export_manifest:
            filtered_library.export_manifest = {}
        filtered_library.export_manifest.update({
            "filter_level": self.config.filter_level,
            "doc_id": self.config.doc_id,
            "original_unit_count": generated_count,
            "filtered_unit_count": filtered_out_count,
            "exportable_unit_count": exported_count,
        })
        
        # Store generation stats for exporter manifest
        filtered_library.export_manifest["generation_stats"] = {
            "generated_units": generated_count,
            "filtered_out": filtered_out_count,
            "exported_units": exported_count,
            "fallback_units": len(getattr(self, '_fallback_unit_ids', [])),
            "filter_level": self.config.filter_level,
        }
        
        # Store quality report paths for exporter
        filtered_library.export_manifest["quality_reports"] = {
            "generated": "quality_report_generated.json",
            "exported": "quality_report_exported.json",
        }
        
        # Store filtered library and stats for _gather_statistics()
        self._filtered_library = filtered_library
        self._generation_stats = {
            "generated_units": generated_count,
            "filtered_out": filtered_out_count,
            "exported_units": exported_count,
        }
        
        self._logger.info(
            f"Created export with {len(filtered_library.instructional_units)} units "
            f"({len(filter_result.filtered_units)} filtered), "
            f"{len(misconception_units)} misconceptions, "
            f"{len(reinforcement_items)} reinforcement items"
        )
        return filtered_library
    
    def _export(self, library: UnitLibraryExport | None = None) -> Path:
        """
        Stage 11: Export the final unit library.
        
        Writes all content to output directory in JSON/JSONL format.
        
        Args:
            library: Optional library to export (uses filtered library if None)
            
        Returns:
            Path to output directory
        """
        self._logger.info("Stage 11: Exporting final library")
        
        if library is None:
            library = self._apply_export_filters()
        
        self._exporter = UnitLibraryExporter()
        
        # Mark library as already filtered to prevent double-filtering in exporter
        library._pre_filtered = True
        
        filter_level_map = {
            "strict": FilterLevel.STRICT,
            "production": FilterLevel.PRODUCTION,
            "development": FilterLevel.DEVELOPMENT,
        }
        
        export_config = ExportConfig(
            output_dir=self.config.output_dir,
            filter_level=filter_level_map.get(self.config.filter_level, FilterLevel.PRODUCTION),
            source_pdf_id=self.config.doc_id,
        )
        
        output_path = self._exporter.export(library, export_config)
        
        self._logger.info(f"Exported to: {output_path}")
        return output_path
    
    def _build_concept_graph(self, library: UnitLibraryExport) -> dict:
        """Build concept graph from mapped concepts in this PDF.
        
        Instead of including all concepts from the ontology, this builds
        the graph only from concepts that have instructional units in
        the exported library.
        
        Args:
            library: The filtered unit library export
            
        Returns:
            Dict with nodes, edges, and metadata about included concepts
        """
        # Get concepts that actually have units in this document
        mapped_concept_ids = set()
        for unit in library.instructional_units:
            mapped_concept_ids.add(unit.concept_id)
        
        # Build nodes only for mapped concepts
        nodes = []
        for concept_id in mapped_concept_ids:
            concept = self._ontology.get_concept(concept_id) if self._ontology else None
            if concept:
                evidence_count = len(self._concept_blocks.get(concept_id, []))
                nodes.append({
                    "id": concept_id,
                    "concept_id": concept_id,
                    "title": concept.get("title", concept_id),
                    "difficulty": concept.get("difficulty", "beginner"),
                    "category": concept.get("category", "unknown"),
                    "evidence_span_count": evidence_count,
                    "has_content": evidence_count > 0,
                })
        
        # Build edges from prerequisites where both ends are mapped
        edges = []
        if self._ontology:
            for concept_id in mapped_concept_ids:
                concept = self._ontology.get_concept(concept_id)
                if concept:
                    # Get prerequisites for this concept
                    prereqs = self._ontology.get_prerequisites(concept_id)
                    for prereq_id in prereqs:
                        if prereq_id in mapped_concept_ids:
                            edges.append({
                                "source": prereq_id,
                                "target": concept_id,
                                "type": "prerequisite",
                            })
        
        # Metadata about what's included vs omitted
        all_ontology = set(self._ontology.list_all_concepts()) if self._ontology else set()
        omitted = all_ontology - mapped_concept_ids
        
        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_ontology_concepts": len(all_ontology),
                "mapped_concepts": len(mapped_concept_ids),
                "exported_concepts": len(mapped_concept_ids),
                "omitted_concepts": sorted(omitted),
                "omitted_count": len(omitted),
                "edge_count": len(edges),
            }
        }
    
    def _gather_statistics(self) -> dict[str, Any]:
        """Gather processing statistics from all stages.
        
        Returns accurate counts including:
        - generated_instructional_units: Total units created before filtering
        - exported_instructional_units: Units actually exported (after filtering)
        - filtered_out_units: Units removed by quality/export filters
        - fallback_units: Units that failed generation and used fallback content
        """
        # Use stored generation stats if available, otherwise compute from current state
        stats = getattr(self, '_generation_stats', {})
        
        # Get exported units count from filtered library if available
        filtered_library = getattr(self, '_filtered_library', None)
        if filtered_library and filtered_library.instructional_units is not None:
            exported_units = len(filtered_library.instructional_units)
        else:
            exported_units = 0
        
        # Get counts from stored stats or compute from current state
        generated_units = stats.get('generated_units', len(self._instructional_units))
        filtered_out = stats.get('filtered_out', len(getattr(self, '_filtered_unit_ids', [])))
        fallback_count = len(getattr(self, '_fallback_unit_ids', []))
        
        return {
            "extraction_blocks": len(self._content_blocks),
            "teaching_blocks": len(self._teaching_blocks),
            "concepts_mapped": len(self._concept_blocks),
            # Legacy field for backward compatibility - equals exported_units
            "instructional_units": exported_units,
            # Clear separation of metrics for generated vs exported
            "generated_instructional_units": generated_units,
            "exported_instructional_units": exported_units,
            "filtered_out_units": filtered_out,
            "misconception_units": len(self._misconception_units),
            "reinforcement_items": len(self._reinforcement_items),
            "filtered_units": len(getattr(self, '_filtered_unit_ids', [])),
            "fallback_units": fallback_count,
            "stage_timings": self.progress.get_stage_durations(),
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def process_pdf_to_unit_library(config: PipelineConfig) -> PipelineResult:
    """
    Process a PDF to a unit library using full configuration.
    
    This is the main entry point for programmatic usage with full control.
    
    Args:
        config: Pipeline configuration
        
    Returns:
        PipelineResult with all outputs and status
        
    Example:
        config = PipelineConfig(
            pdf_path=Path("textbook.pdf"),
            output_dir=Path("./output"),
            filter_level="production",
        )
        result = process_pdf_to_unit_library(config)
        
        if result.success:
            print(f"Generated {result.statistics['instructional_units']} units")
    """
    pipeline = InstructionalPipeline(config)
    return pipeline.run()


def quick_process(
    pdf_path: str | Path,
    output_dir: str | Path,
    doc_id: str | None = None,
) -> PipelineResult:
    """
    Quick-start function for simple use cases.
    
    Processes a PDF with sensible defaults for quick results.
    
    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory for output
        doc_id: Optional document identifier
        
    Returns:
        PipelineResult with all outputs and status
        
    Example:
        result = quick_process("textbook.pdf", "./output")
        
        if result.success:
            print("Processing complete!")
            print(result.get_summary())
        else:
            print(f"Failed: {result.stages_failed}")
    """
    config = PipelineConfig(
        pdf_path=Path(pdf_path),
        output_dir=Path(output_dir),
        doc_id=doc_id,
        filter_level="production",
    )
    
    pipeline = InstructionalPipeline(config)
    return pipeline.run()


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # Simple CLI for testing
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Process PDF to instructional unit library"
    )
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("--output", "-o", default="./output", help="Output directory")
    parser.add_argument("--filter-level", default="production", 
                       choices=["strict", "production", "development"],
                       help="Content filtering level")
    parser.add_argument("--doc-id", help="Document identifier")
    parser.add_argument("--skip-misconceptions", action="store_true",
                       help="Skip misconception generation")
    parser.add_argument("--skip-reinforcement", action="store_true",
                       help="Skip reinforcement generation")
    parser.add_argument("--no-sql-validation", action="store_true",
                       help="Skip SQL validation")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    config = PipelineConfig(
        pdf_path=Path(args.pdf_path),
        output_dir=Path(args.output),
        doc_id=args.doc_id,
        filter_level=args.filter_level,
        skip_misconceptions=args.skip_misconceptions,
        skip_reinforcement=args.skip_reinforcement,
        validate_sql=not args.no_sql_validation,
    )
    
    result = process_pdf_to_unit_library(config)
    print(result.get_summary())
    
    exit(0 if result.success else 1)
