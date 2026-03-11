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

import hashlib
import json
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
)
from .section_extractor import SectionExtractor, ContentBlock, ContentFilter, BlockType
from .pedagogy_extractor import PedagogyExtractor, PedagogyIntegrator
from .pedagogy_models import NavigationIndex
from .sql_ontology import ConceptOntology
from .unit_generator import UnitGenerator, GenerationConfig as UnitGenerationConfig
from .misconception_bank import MisconceptionBank, GenerationConfig as MisconceptionConfig
from .reinforcement_bank import ReinforcementBank, ReinforcementConfig
from .sql_validator import SQLValidator
from .learning_quality_gates import LearningQualityGates, Severity
from .ollama_repair import OllamaRepair
from .export_filters import (
    ExportFilterEngine, 
    PRODUCTION_FILTERS, 
    STRICT_FILTERS, 
    DEVELOPMENT_FILTERS,
    PROTOTYPE_FILTERS,
    STUDENT_READY_FILTERS,
    CORE_SQL_CONCEPTS as EXPORT_CORE_SQL_CONCEPTS,
)
from .unit_library_exporter import UnitLibraryExporter, ExportConfig, FilterLevel


# =============================================================================
# LOGGER SETUP
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# CORE SQL CONCEPTS
# =============================================================================

# Core SQL concepts that require proper textbook examples for L2 units.
# These concepts are fundamental to SQL learning and should not use default/generic examples.
CORE_SQL_CONCEPTS: set[str] = {
    'select-basic',
    'where-clause',
    'order-by',
    'group-by',
    'joins-intro',
    'join-inner',
    'join-outer',
    'join-left',
    'join-right',
    'aggregate-functions',
    'having-clause',
    'subqueries-intro',
    'insert-statement',
    'update-statement',
    'delete-statement',
    'null-handling',
    'pattern-matching',
}


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
    PEDAGOGY_EXTRACTION = auto()     # Extract chapter/exercise/example structure
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
        export_mode: Export mode - "prototype" (allows placeholders) or "student_ready" (strict)
        generate_variants: List of L1-L4 variants to generate
        skip_reinforcement: Whether to skip reinforcement generation
        skip_misconceptions: Whether to skip misconception generation
        validate_sql: Whether to validate SQL examples
        min_quality_score: Minimum quality score for export (0.0-1.0)
        use_ollama_repair: Whether to use Ollama for repairing weak L3 content
        ollama_model: Ollama model for repair (qwen3.5:9b-q8_0 recommended for RTX 4080)
        ollama_repair_threshold: Confidence threshold below which to trigger repair
        ollama_host: Ollama API host URL
    """
    
    pdf_path: Path
    output_dir: Path = field(default_factory=lambda: Path("./output"))
    doc_id: str | None = None
    llm_provider: Literal["kimi", "openai", "ollama"] = "kimi"
    llm_model: str | None = None  # Will be resolved to provider-specific default
    concept_ontology_path: Path | None = None
    filter_level: Literal["strict", "production", "development"] = "production"
    export_mode: Literal["prototype", "student_ready"] = "prototype"
    generate_variants: list[str] = field(
        default_factory=lambda: [
            "L1_hint", "L2_hint_plus_example", "L3_explanation", "L4_reflective_note", "reinforcement"
        ]
    )
    skip_reinforcement: bool = False
    skip_misconceptions: bool = False
    validate_sql: bool = True
    min_quality_score: float = 0.7
    allow_synthetic_examples: bool = False  # Default to False for production
    
    # Off-book curated content configuration
    allow_offbook_curated: bool = False  # Default False - must explicitly opt-in for off-book concepts
    
    # Ollama repair configuration
    use_ollama_repair: bool = True
    ollama_model: str = "qwen2.5:3b"  # Default for MacBook (small, fast)
    ollama_repair_threshold: float = 0.6  # Confidence below this triggers repair
    ollama_host: str = "http://localhost:11434"
    ollama_auto_fallback: bool = True  # Auto-fallback to available models
    
    # Provider-specific default models
    PROVIDER_DEFAULT_MODELS: ClassVar[dict[str, str]] = {
        "kimi": "kimi-k2-5",
        "openai": "gpt-4",
        "ollama": "llama3.2:3b",
    }
    
    # Range and caching configuration
    page_range: tuple[int, int] | list[int] | None = None
    chapter_range: tuple[int, int] | list[int] | None = None
    resume_from_checkpoint: bool = False
    cache_extraction: bool = True
    checkpoint_dir: Path | None = None
    
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
        
        # Set checkpoint directory
        if self.checkpoint_dir is None:
            self.checkpoint_dir = self.output_dir / ".checkpoints"
        elif isinstance(self.checkpoint_dir, str):
            self.checkpoint_dir = Path(self.checkpoint_dir)
        
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
        blocked_units_with_reasons: List of (unit_id, reasons) tuples for blocked units
        repaired_units: List of unit IDs that were repaired by Ollama
        repair_status: Detailed repair status information
        chapters: Extracted chapter structure (new)
        exercises: Extracted exercises (new)
        examples: Extracted examples (new)
        navigation: Navigation index for cross-referencing (new)
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
    blocked_units_with_reasons: list[tuple[str, list[str]]] = field(default_factory=list)
    repaired_units: list[str] = field(default_factory=list)
    repair_status: dict[str, Any] = field(default_factory=dict)
    cache_stats: dict[str, Any] = field(default_factory=dict)
    # Pedagogy data (new)
    chapters: list[Any] = field(default_factory=list)
    exercises: list[Any] = field(default_factory=list)
    examples: list[Any] = field(default_factory=list)
    navigation: dict[str, Any] = field(default_factory=dict)
    
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
            "blocked_units_with_reasons": self.blocked_units_with_reasons,
            "repaired_units": self.repaired_units,
            "cache_stats": self.cache_stats,
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
        if self.repaired_units:
            lines.append(f"Repaired Units: {len(self.repaired_units)}")
        
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
        PipelineStage.CONTENT_FILTERING: 3.0,
        PipelineStage.PEDAGOGY_EXTRACTION: 5.0,
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

class CheckpointManager:
    """Manages pipeline checkpoints for resumable processing.
    
    Saves and loads checkpoint state to enable resuming interrupted runs.
    """
    
    def __init__(self, checkpoint_dir: Path, doc_id: str):
        self.checkpoint_dir = checkpoint_dir
        self.doc_id = doc_id
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_checkpoint_path(self) -> Path:
        """Get the checkpoint file path for this document."""
        return self.checkpoint_dir / f"{self.doc_id}.checkpoint.json"
    
    def _get_cache_path(self, pdf_hash: str) -> Path:
        """Get the extraction cache file path for this PDF hash."""
        return self.checkpoint_dir / f"extraction_{pdf_hash[:16]}.cache.json"
    
    def save_checkpoint(self, state: dict[str, Any]) -> None:
        """Save the current pipeline state to checkpoint file."""
        checkpoint_path = self._get_checkpoint_path()
        checkpoint_data = {
            "doc_id": self.doc_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            **state,
        }
        with open(checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, indent=2)
    
    def load_checkpoint(self) -> dict[str, Any] | None:
        """Load checkpoint state if it exists."""
        checkpoint_path = self._get_checkpoint_path()
        if checkpoint_path.exists():
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
    
    def clear_checkpoint(self) -> None:
        """Clear the checkpoint file."""
        checkpoint_path = self._get_checkpoint_path()
        if checkpoint_path.exists():
            checkpoint_path.unlink()
    
    def save_extraction_cache(
        self, 
        pdf_hash: str, 
        pages: list[tuple[int, str]], 
        metadata: dict[str, Any]
    ) -> None:
        """Save extracted pages to cache."""
        cache_path = self._get_cache_path(pdf_hash)
        cache_data = {
            "pdf_hash": pdf_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pages": pages,
            "metadata": metadata,
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)
    
    def load_extraction_cache(self, pdf_hash: str) -> tuple[list[tuple[int, str]], dict[str, Any]] | None:
        """Load cached extraction if it exists and hash matches."""
        cache_path = self._get_cache_path(pdf_hash)
        if cache_path.exists():
            with open(cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
                if cache_data.get("pdf_hash") == pdf_hash:
                    pages = [(p[0], p[1]) for p in cache_data["pages"]]
                    return pages, cache_data.get("metadata", {})
        return None
    
    def clear_extraction_cache(self, pdf_hash: str) -> None:
        """Clear the extraction cache for a given PDF hash."""
        cache_path = self._get_cache_path(pdf_hash)
        if cache_path.exists():
            cache_path.unlink()


def compute_pdf_hash(pdf_path: Path) -> str:
    """Compute SHA256 hash of PDF file for cache validation."""
    sha256 = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


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
        
        # Run-level Ollama availability tracking (one-time check)
        self._ollama_preflight_done = False
        self._ollama_available = False
        
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
        self._rejected_units: list[tuple[str, list[str]]] = []
        # Pedagogy data (new)
        self._chapters: list[Any] = []
        self._exercises: list[Any] = []
        self._examples: list[Any] = []
        self._navigation_index: NavigationIndex = NavigationIndex()
        
        self._logger = logging.getLogger(__name__)
        self._logger.info(f"Pipeline initialized for: {config.pdf_path}")
        
        # Initialize checkpoint manager
        self._checkpoint_manager = CheckpointManager(
            checkpoint_dir=config.checkpoint_dir or config.output_dir / ".checkpoints",
            doc_id=config.doc_id or "unknown",
        )
        
        # Track checkpoint state
        self._checkpoint_state: dict[str, Any] = {
            "completed_stages": [],
            "processed_concepts": [],
            "current_page": 0,
            "pdf_hash": None,
        }
        
        # Control whether to log detailed filter results (set to True when CLI handles output)
        self._quiet_filter_logging = False
        
        # Cache stats for reporting
        self._cache_stats: dict[str, Any] = {
            "extraction_cache_hit": False,
            "extraction_cache_saved": False,
            "pages_from_cache": 0,
            "pages_extracted": 0,
        }
    
    def run(self) -> PipelineResult:
        """
        Execute the full pipeline.
        
        Runs all stages sequentially with error handling. If a stage fails,
        returns partial results with error information.
        
        Supports resuming from checkpoints if --resume is enabled.
        
        Returns:
            PipelineResult with success status and all outputs
        """
        start_time = time.time()
        result = PipelineResult()
        
        # Load checkpoint if resuming
        checkpoint = None
        if self.config.resume_from_checkpoint:
            checkpoint = self._checkpoint_manager.load_checkpoint()
            if checkpoint:
                self._logger.info(f"Resuming from checkpoint: {checkpoint.get('timestamp')}")
                self._checkpoint_state["completed_stages"] = checkpoint.get("completed_stages", [])
                self._checkpoint_state["processed_concepts"] = checkpoint.get("processed_concepts", [])
                self._checkpoint_state["current_page"] = checkpoint.get("current_page", 0)
        
        # Compute PDF hash for cache validation
        pdf_hash = compute_pdf_hash(self.config.pdf_path)
        self._checkpoint_state["pdf_hash"] = pdf_hash
        
        try:
            # Stage 1: Document Extraction (skip if cached and not resumed)
            if (PipelineStage.EXTRACTION.name not in self._checkpoint_state["completed_stages"] or 
                not self.config.resume_from_checkpoint):
                self._run_stage(PipelineStage.EXTRACTION, self._extract_pdf, result)
                self._checkpoint_state["completed_stages"].append(PipelineStage.EXTRACTION.name)
                self._save_checkpoint()
            else:
                self._logger.info("Skipping EXTRACTION stage (already completed)")
                result.stages_completed.append(PipelineStage.EXTRACTION)
            
            # Stage 2: Section Segmentation
            if (PipelineStage.SEGMENTATION.name not in self._checkpoint_state["completed_stages"] or 
                not self.config.resume_from_checkpoint):
                self._run_stage(PipelineStage.SEGMENTATION, self._segment_content, result)
                self._checkpoint_state["completed_stages"].append(PipelineStage.SEGMENTATION.name)
                self._save_checkpoint()
            else:
                self._logger.info("Skipping SEGMENTATION stage (already completed)")
                result.stages_completed.append(PipelineStage.SEGMENTATION)
            
            # Stage 3: Content Filtering
            if (PipelineStage.CONTENT_FILTERING.name not in self._checkpoint_state["completed_stages"] or 
                not self.config.resume_from_checkpoint):
                self._run_stage(PipelineStage.CONTENT_FILTERING, self._filter_teaching_content, result)
                self._checkpoint_state["completed_stages"].append(PipelineStage.CONTENT_FILTERING.name)
                self._save_checkpoint()
            else:
                self._logger.info("Skipping CONTENT_FILTERING stage (already completed)")
                result.stages_completed.append(PipelineStage.CONTENT_FILTERING)
            
            # Stage 4: Concept Mapping
            if (PipelineStage.CONCEPT_MAPPING.name not in self._checkpoint_state["completed_stages"] or 
                not self.config.resume_from_checkpoint):
                self._run_stage(PipelineStage.CONCEPT_MAPPING, self._map_to_concepts, result)
                self._checkpoint_state["completed_stages"].append(PipelineStage.CONCEPT_MAPPING.name)
                self._save_checkpoint()
            else:
                self._logger.info("Skipping CONCEPT_MAPPING stage (already completed)")
                result.stages_completed.append(PipelineStage.CONCEPT_MAPPING)
            
            # Stage 5: Unit Generation
            if (PipelineStage.UNIT_GENERATION.name not in self._checkpoint_state["completed_stages"] or 
                not self.config.resume_from_checkpoint):
                self._run_stage(PipelineStage.UNIT_GENERATION, self._generate_units, result)
                self._checkpoint_state["completed_stages"].append(PipelineStage.UNIT_GENERATION.name)
                self._save_checkpoint()
            else:
                self._logger.info("Skipping UNIT_GENERATION stage (already completed)")
                result.stages_completed.append(PipelineStage.UNIT_GENERATION)
            
            # Stage 6: Misconception Bank
            if not self.config.skip_misconceptions:
                if (PipelineStage.MISCONCEPTION_GENERATION.name not in self._checkpoint_state["completed_stages"] or 
                    not self.config.resume_from_checkpoint):
                    self._run_stage(
                        PipelineStage.MISCONCEPTION_GENERATION, 
                        self._generate_misconceptions, 
                        result
                    )
                    self._checkpoint_state["completed_stages"].append(PipelineStage.MISCONCEPTION_GENERATION.name)
                    self._save_checkpoint()
                else:
                    self._logger.info("Skipping MISCONCEPTION_GENERATION stage (already completed)")
                    result.stages_completed.append(PipelineStage.MISCONCEPTION_GENERATION)
            
            # Stage 7: Reinforcement Bank
            if not self.config.skip_reinforcement:
                if (PipelineStage.REINFORCEMENT_GENERATION.name not in self._checkpoint_state["completed_stages"] or 
                    not self.config.resume_from_checkpoint):
                    self._run_stage(
                        PipelineStage.REINFORCEMENT_GENERATION,
                        self._generate_reinforcement,
                        result
                    )
                    self._checkpoint_state["completed_stages"].append(PipelineStage.REINFORCEMENT_GENERATION.name)
                    self._save_checkpoint()
                else:
                    self._logger.info("Skipping REINFORCEMENT_GENERATION stage (already completed)")
                    result.stages_completed.append(PipelineStage.REINFORCEMENT_GENERATION)
            
            # Stage 8: SQL Validation
            if self.config.validate_sql:
                if (PipelineStage.VALIDATION.name not in self._checkpoint_state["completed_stages"] or 
                    not self.config.resume_from_checkpoint):
                    self._run_stage(PipelineStage.VALIDATION, self._validate_sql_examples, result)
                    self._checkpoint_state["completed_stages"].append(PipelineStage.VALIDATION.name)
                    self._save_checkpoint()
                else:
                    self._logger.info("Skipping VALIDATION stage (already completed)")
                    result.stages_completed.append(PipelineStage.VALIDATION)
            
            # Stage 9: Quality Gates
            if (PipelineStage.QUALITY_GATES.name not in self._checkpoint_state["completed_stages"] or 
                not self.config.resume_from_checkpoint):
                self._run_stage(PipelineStage.QUALITY_GATES, self._run_quality_gates, result)
                self._checkpoint_state["completed_stages"].append(PipelineStage.QUALITY_GATES.name)
                self._save_checkpoint()
            else:
                self._logger.info("Skipping QUALITY_GATES stage (already completed)")
                result.stages_completed.append(PipelineStage.QUALITY_GATES)
            
            # Stage 10: Export Filtering
            if (PipelineStage.FILTERING.name not in self._checkpoint_state["completed_stages"] or 
                not self.config.resume_from_checkpoint):
                self._run_stage(PipelineStage.FILTERING, self._apply_export_filters, result)
                self._checkpoint_state["completed_stages"].append(PipelineStage.FILTERING.name)
                self._save_checkpoint()
            else:
                self._logger.info("Skipping FILTERING stage (already completed)")
                result.stages_completed.append(PipelineStage.FILTERING)
            
            # Stage 11: Export
            if (PipelineStage.EXPORT.name not in self._checkpoint_state["completed_stages"] or 
                not self.config.resume_from_checkpoint):
                export_path = self._run_stage(PipelineStage.EXPORT, self._export, result)
                if export_path:
                    result.output_path = export_path
                self._checkpoint_state["completed_stages"].append(PipelineStage.EXPORT.name)
                self._save_checkpoint()
            else:
                self._logger.info("Skipping EXPORT stage (already completed)")
                result.stages_completed.append(PipelineStage.EXPORT)
            
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
            result.blocked_units_with_reasons = getattr(self, '_rejected_units', [])
            result.repaired_units = getattr(self, '_repaired_unit_ids', [])
            result.repair_status = getattr(self, '_repair_status', {})
            result.cache_stats = self._cache_stats
            
            # Clear checkpoint on successful completion
            if result.success and self.config.resume_from_checkpoint:
                self._checkpoint_manager.clear_checkpoint()
            
            self._logger.info(f"Pipeline completed in {result.elapsed_time_seconds:.2f}s")
        
        return result
    
    def _save_checkpoint(self) -> None:
        """Save current checkpoint state."""
        try:
            self._checkpoint_manager.save_checkpoint(self._checkpoint_state)
        except Exception as e:
            self._logger.warning(f"Failed to save checkpoint: {e}")
    
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
            # Only append if not already added (e.g., during resume)
            if stage not in result.stages_completed:
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
        Stage 1: Extract raw text from PDF with caching and page range support.
        
        Uses SectionExtractor to extract text with layout preservation.
        Supports extraction caching and page range filtering.
        
        Returns:
            Tuple of (raw_text, metadata)
        """
        self._logger.info("Stage 1: Extracting PDF content")
        
        # Check extraction cache if enabled
        pdf_hash = self._checkpoint_state.get("pdf_hash")
        if self.config.cache_extraction and pdf_hash:
            cached = self._checkpoint_manager.load_extraction_cache(pdf_hash)
            if cached:
                pages, cache_metadata = cached
                self._logger.info(f"Using cached extraction: {len(pages)} pages")
                self._cache_stats["extraction_cache_hit"] = True
                self._cache_stats["pages_from_cache"] = len(pages)
                # Convert cached pages to blocks
                return self._process_extracted_pages(pages, from_cache=True)
        
        self._extractor = SectionExtractor()
        
        # Extract with page range support if specified
        page_range = self.config.page_range
        chapter_range = self.config.chapter_range
        
        if page_range or chapter_range:
            # If chapter range is specified, we need to resolve it to page numbers
            if chapter_range and not page_range:
                page_range = self._resolve_chapter_range(chapter_range)
                self._logger.info(f"Resolved chapter range to pages: {page_range}")
            
            # Extract specific pages
            blocks = self._extractor.extract_blocks(
                self.config.pdf_path,
                self.config.doc_id,
                page_range=page_range,
            )
            self._logger.info(f"Extracted with page range: {page_range}")
        else:
            # Extract all pages
            blocks = self._extractor.extract_blocks(
                self.config.pdf_path,
                self.config.doc_id
            )
        
        return self._process_extracted_blocks(blocks)
    
    def _resolve_chapter_range(
        self, 
        chapter_range: tuple[int, int] | list[int]
    ) -> tuple[int, int] | list[int]:
        """Resolve chapter numbers to page numbers using PDF bookmarks.
        
        Args:
            chapter_range: Chapter numbers (e.g., (1, 5) or [1, 3, 5])
            
        Returns:
            Corresponding page numbers
            
        Note:
            This requires the PDF to have bookmarks/table of contents.
            If bookmarks are not available, raises an error.
        """
        try:
            import fitz
            doc = fitz.open(self.config.pdf_path)
            
            # Get bookmarks/outline
            toc = doc.get_toc()
            if not toc:
                doc.close()
                raise ValueError(
                    "PDF has no bookmarks/table of contents. "
                    "Cannot resolve chapter numbers to pages. "
                    "Use --page-range instead."
                )
            
            # Build chapter -> page mapping from bookmarks
            # TOC format: [(level, title, page), ...]
            chapter_pages = {}
            chapter_num = 0
            for level, title, page in toc:
                # Look for chapter indicators in title
                if level == 1:  # Top-level entries are usually chapters
                    chapter_num += 1
                    chapter_pages[chapter_num] = page
            
            doc.close()
            
            if not chapter_pages:
                raise ValueError(
                    "Could not identify chapters in PDF bookmarks. "
                    "Use --page-range instead."
                )
            
            # Resolve chapter numbers to pages
            if isinstance(chapter_range, tuple):
                start_ch, end_ch = chapter_range
                start_page = chapter_pages.get(start_ch)
                end_page = chapter_pages.get(end_ch)
                
                if start_page is None:
                    raise ValueError(f"Chapter {start_ch} not found in PDF")
                if end_page is None:
                    # Use start of next chapter - 1, or end of document
                    next_page = chapter_pages.get(end_ch + 1)
                    if next_page:
                        end_page = next_page - 1
                    else:
                        # Get total page count
                        import fitz
                        doc = fitz.open(self.config.pdf_path)
                        end_page = len(doc)
                        doc.close()
                
                return (start_page, end_page)
            else:
                # List of chapters
                pages = []
                for ch in chapter_range:
                    page = chapter_pages.get(ch)
                    if page is None:
                        raise ValueError(f"Chapter {ch} not found in PDF")
                    pages.append(page)
                return pages
                
        except ImportError:
            raise RuntimeError("PyMuPDF (fitz) is required for chapter resolution")
        except Exception as e:
            if "no bookmarks" in str(e).lower() or "not found" in str(e).lower():
                raise
            raise ValueError(f"Failed to resolve chapter range: {e}")
    
    def _process_extracted_blocks(self, blocks: list[ContentBlock]) -> tuple[str, dict]:
        """Process extracted blocks and create metadata."""
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
        
        # Save to cache if enabled
        if self.config.cache_extraction and self._checkpoint_state.get("pdf_hash"):
            # Convert blocks to pages format for caching
            pages = self._blocks_to_pages(blocks)
            if pages:
                self._checkpoint_manager.save_extraction_cache(
                    self._checkpoint_state["pdf_hash"],
                    pages,
                    self._extraction_metadata
                )
                self._cache_stats["extraction_cache_saved"] = True
                self._logger.info(f"Saved extraction cache: {len(pages)} pages")
        
        return self._raw_text, self._extraction_metadata
    
    def _process_extracted_pages(
        self, 
        pages: list[tuple[int, str]], 
        from_cache: bool = False
    ) -> tuple[str, dict]:
        """Process cached pages and reconstruct blocks."""
        # For cached pages, we need to re-create blocks
        # This is simplified - in production, you'd store block structure in cache
        self._extractor = SectionExtractor()
        
        # Re-extract to get proper block structure
        blocks = self._extractor.extract_blocks(
            self.config.pdf_path,
            self.config.doc_id,
            page_range=[p[0] for p in pages] if pages else None,
        )
        
        return self._process_extracted_blocks(blocks)
    
    def _blocks_to_pages(self, blocks: list[ContentBlock]) -> list[tuple[int, str]]:
        """Convert blocks back to page format for caching."""
        pages_dict: dict[int, list[str]] = {}
        for block in blocks:
            page = getattr(block, 'page_number', 0) or 0
            if page not in pages_dict:
                pages_dict[page] = []
            pages_dict[page].append(block.text_content)
        
        pages = []
        for page_num in sorted(pages_dict.keys()):
            text = "\n\n".join(pages_dict[page_num])
            pages.append((page_num, text))
        
        return pages
    
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
        if "exists" in concept_id_lower:
            keywords.update(["exists", "not exists", "existence", "semi-join"])
        
        # Learning objectives keywords
        for objective in concept.get("learning_objectives", []):
            words = objective.lower().split()
            keywords.update(w for w in words[:5] if len(w) > 2)
        
        return keywords
    
    def _validate_core_concept_l2(self, units: list[InstructionalUnit]) -> list[InstructionalUnit]:
        """Mark core concepts with default L2 as needing review.
        
        Post-generation quality check that flags core SQL concepts using
        default examples in their L2 units. This helps identify content gaps
        before export filtering.
        
        Args:
            units: List of generated instructional units
            
        Returns:
            List of units with metadata updated for flagged core concepts
        """
        flagged_count = 0
        
        for unit in units:
            if unit.target_stage != 'L2_hint_plus_example':
                continue
            
            if unit.concept_id not in CORE_SQL_CONCEPTS:
                continue
            
            # Check if using default example
            content = unit.content or {}
            metadata = content.get('example_metadata', {})
            is_default = metadata.get('used_default_example', False) or \
                        metadata.get('example_source_type') == 'default'
            
            if is_default:
                # Mark for review
                if unit.content is None:
                    unit.content = {}
                if '_metadata' not in unit.content:
                    unit.content['_metadata'] = {}
                
                unit.content['_metadata']['review_needed'] = True
                unit.content['_metadata']['review_reason'] = 'Core concept using default L2 example'
                unit.content['_metadata']['core_concept_default_l2'] = True
                
                flagged_count += 1
                print(f"[QUALITY GATE] {unit.concept_id}: Default L2 flagged for review")
        
        if flagged_count > 0:
            print(f"[QUALITY GATE] Flagged {flagged_count} core concepts with default L2 examples")
        
        return units
    
    def _pre_validate_core_concepts(self, units: list[InstructionalUnit]) -> list[str]:
        """Pre-flight check: Warn if core concepts will be blocked in student_ready.
        
        This check runs before export filtering to give early warning about
        which core concepts will be blocked when using student_ready mode.
        
        Args:
            units: List of instructional units to validate
            
        Returns:
            List of concept IDs that will be blocked in student_ready mode
        """
        blocked: list[str] = []
        
        for unit in units:
            if unit.target_stage != 'L2_hint_plus_example':
                continue
            
            if unit.concept_id not in CORE_SQL_CONCEPTS:
                continue
            
            # Check metadata for default example indicator
            content = unit.content or {}
            metadata = content.get('example_metadata', {})
            content_metadata = content.get('_metadata', {})
            
            # Multiple ways to detect default example
            is_default = (
                metadata.get('used_default_example', False) or
                metadata.get('example_source_type') == 'default' or
                content_metadata.get('used_default_example', False) or
                content_metadata.get('example_source_type') == 'default' or
                content.get('used_default_example', False)
            )
            
            if is_default:
                blocked.append(unit.concept_id)
        
        if blocked:
            unique_blocked = sorted(set(blocked))
            mode_indicator = "🔴 WILL BE BLOCKED" if self.config.export_mode == "student_ready" else "⚠️  WARNING"
            print(f"\n{'='*70}")
            print(f"[EXPORT PRE-CHECK] {mode_indicator} in '{self.config.export_mode}' mode:")
            print(f"  {len(unique_blocked)} core concept(s) using default L2 examples:")
            for cid in unique_blocked:
                print(f"    - {cid}")
            
            if self.config.export_mode == "student_ready":
                print(f"\n  These units will be BLOCKED from student-ready export.")
                print(f"  Fix extraction or add curated content for these concepts.")
            else:
                print(f"\n  These units will be BLOCKED if you use --export-mode student_ready.")
                print(f"  In prototype mode, they will be included with warnings.")
            print(f"{'='*70}\n")
        
        return blocked

    def _generate_units(self, concept_blocks: dict[str, list[ContentBlock]] | None = None) -> list[InstructionalUnit]:
        """
        Stage 5: Generate instructional units for all variants with Ollama repair.
        
        Creates L1-L4 variants and reinforcement units for each concept.
        Applies Ollama-based repair for weak L3 content when enabled.
        
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
            allow_synthetic_examples=self.config.allow_synthetic_examples,
            enable_ollama_repair=self.config.use_ollama_repair,
            repair_threshold=self.config.ollama_repair_threshold,
            ollama_model=self.config.ollama_model,
        )
        
        # Initialize misconception bank for error subtype lookup
        if self._misconception_bank is None:
            self._misconception_bank = MisconceptionBank.load_default()
        
        # Initialize Ollama repair if enabled - ONE preflight check
        ollama_repair = None
        self._repair_status = {
            "enabled": self.config.use_ollama_repair,
            "available": False,
            "disabled_reason": None,
            "model": self.config.ollama_model,
            "repaired_units": [],
            "failed_repairs": [],
            "repair_attempts": 0,
        }
        
        if self.config.use_ollama_repair:
            from .ollama_repair import create_ollama_repair_if_enabled
            
            ollama_repair, repair_info = create_ollama_repair_if_enabled(
                enabled=True,
                model=self.config.ollama_model,
                host=self.config.ollama_host,
                auto_fallback=self.config.ollama_auto_fallback,
            )
            
            # Update repair status with results
            self._repair_status["available"] = repair_info["available"]
            self._repair_status["disabled_reason"] = repair_info["disabled_reason"]
            self._repair_status["model"] = repair_info["model"]
            
            if ollama_repair and ollama_repair.available:
                self._logger.info(f"Ollama repair enabled with model: {repair_info['model']}")
            elif repair_info["disabled_reason"]:
                # Only log once that repair is unavailable - subsequent units skip silently
                self._logger.info(
                    f"Ollama repair unavailable ({repair_info['disabled_reason']}), "
                    "skipping repair pass"
                )
        
        self._instructional_units = []
        self._fallback_unit_ids = []
        self._repaired_unit_ids = []
        
        for concept_id, blocks in concept_blocks.items():
            if not blocks:
                continue
            
            # Debug logging for exists-operator when block count is low (potential issue)
            if concept_id == "exists-operator" and len(blocks) < 5:
                self._logger.warning(f"EXISTS-OPERATOR has only {len(blocks)} blocks mapped (potential content gap)")
            
            # Get prerequisites from ontology
            prereqs = []
            if self._ontology:
                prereqs = self._ontology.get_prerequisites(concept_id)
            
            # Get error subtypes for this concept from misconception bank
            error_subtypes = self._get_error_subtypes_for_concept(concept_id)
            
            try:
                # Generate all variants
                variants = self._unit_generator.generate_all_variants(
                    concept_id=concept_id,
                    source_blocks=blocks,
                    config=gen_config,
                    prerequisites=prereqs,
                    error_subtypes=error_subtypes,
                )
                
                # Add generated units with optional L3 repair
                for variant_name, unit in variants.items():
                    if unit.target_stage in self.config.generate_variants:
                        # Apply Ollama repair for weak L3 content
                        if (
                            unit.target_stage == "L3_explanation"
                            and ollama_repair
                            and unit.content
                        ):
                            unit = self._repair_l3_if_needed(
                                unit, concept_id, blocks, ollama_repair
                            )
                        
                        self._instructional_units.append(unit)
                        
                        # Track fallback units
                        if unit.content.get("_metadata", {}).get("is_fallback"):
                            self._fallback_unit_ids.append(unit.unit_id)
                        
                        # Track repaired units
                        if unit.content.get("_repaired_by_ollama"):
                            self._repaired_unit_ids.append(unit.unit_id)
                            self._repair_status["repaired_units"].append(unit.unit_id)
                
            except Exception as e:
                self._logger.warning(f"Failed to generate units for {concept_id}: {e}")
                continue
        
        # Generate L3 units for concepts with curated content but no blocks
        # This ensures high-quality curated content is included even for concepts
        # not covered in the source PDF
        concepts_with_blocks = set(concept_blocks.keys())
        concepts_with_curated = self._unit_generator.get_concepts_with_curated_l3()
        
        # Find concepts that have curated content but weren't generated (no blocks)
        curated_only_concepts = concepts_with_curated - concepts_with_blocks
        
        # Determine if off-book curated content should be included
        # Off-book concepts are opt-in via --allow-offbook-curated flag
        # Always skip in student_ready mode regardless of flag
        skip_offbook_curated = (
            self.config.export_mode == "student_ready" 
            or not self.config.allow_offbook_curated
        )
        
        # Track off-book concepts for manifest reporting
        offbook_included: list[str] = []
        offbook_excluded: list[str] = []
        
        if skip_offbook_curated and curated_only_concepts:
            self._logger.info(
                f"Skipping {len(curated_only_concepts)} off-book curated concepts: "
                f"{sorted(curated_only_concepts)} "
                f"(export_mode={self.config.export_mode}, "
                f"allow_offbook_curated={self.config.allow_offbook_curated})"
            )
        
        for concept_id in curated_only_concepts:
            # Only generate L3_explanation from curated content
            if "L3_explanation" not in self.config.generate_variants:
                continue
            
            # Skip off-book curated content in student_ready mode or when disabled
            if skip_offbook_curated:
                offbook_excluded.append(concept_id)
                continue
            
            # Get prerequisites from ontology
            prereqs = []
            if self._ontology:
                prereqs = self._ontology.get_prerequisites(concept_id)
            
            # Get error subtypes
            error_subtypes = self._get_error_subtypes_for_concept(concept_id)
            
            try:
                l3_unit = self._unit_generator.generate_l3_from_curated(
                    concept_id=concept_id,
                    config=gen_config,
                    prerequisites=prereqs,
                    error_subtypes=error_subtypes,
                    source_mode="curated_only_offbook",  # Mark as off-book
                )
                
                if l3_unit:
                    # Mark as needing review since it's off-book
                    if l3_unit.content is None:
                        l3_unit.content = {}
                    if "_metadata" not in l3_unit.content:
                        l3_unit.content["_metadata"] = {}
                    l3_unit.content["_metadata"]["review_needed"] = True
                    l3_unit.content["_metadata"]["offbook_concept"] = True
                    l3_unit.content["_metadata"]["source_mode"] = "curated_only_offbook"
                    # Exclude from coverage metrics
                    l3_unit.content["_metadata"]["exclude_from_coverage"] = True
                    
                    self._instructional_units.append(l3_unit)
                    offbook_included.append(concept_id)
                    self._logger.info(
                        f"Generated L3 for {concept_id} from off-book curated content "
                        f"(marked for review)"
                    )
            except Exception as e:
                self._logger.warning(f"Failed to generate curated L3 for {concept_id}: {e}")
                offbook_excluded.append(concept_id)
                continue
        
        # Store off-book tracking for manifest
        self._offbook_tracking = {
            "included": offbook_included,
            "excluded": offbook_excluded,
        }
        
        self._logger.info(f"Generated {len(self._instructional_units)} instructional units")
        
        # Log L2 generation statistics
        self._log_l2_generation_stats(self._instructional_units)
        
        # Pre-validate core concepts for student_ready export
        self._pre_validate_core_concepts(self._instructional_units)
        
        # Log repair summary (only if repair was attempted)
        if self._repair_status.get("available"):
            repaired = len(self._repair_status.get("repaired_units", []))
            failed = len(self._repair_status.get("failed_repairs", []))
            if repaired > 0 or failed > 0:
                self._logger.info(
                    f"Ollama repair: {repaired} repaired, {failed} failed"
                )
        
        # Fail strict mode if fallback units exist
        if self.config.filter_level == "strict" and self._fallback_unit_ids:
            raise RuntimeError(
                f"Strict mode: {len(self._fallback_unit_ids)} fallback units created. "
                f"Unit IDs: {self._fallback_unit_ids[:5]}..."
            )
        
        return self._instructional_units
    
    def _repair_l3_if_needed(
        self,
        unit: InstructionalUnit,
        concept_id: str,
        blocks: list[ContentBlock],
        ollama_repair: Any,
    ) -> InstructionalUnit:
        """
        Repair weak L3 content using Ollama if needed.
        
        Assesses the quality of L3 content and applies Ollama repair if
        the content is below the configured quality threshold.
        
        Args:
            unit: The L3 instructional unit to potentially repair
            concept_id: The concept identifier
            blocks: Source content blocks for evidence
            ollama_repair: OllamaRepair instance
            
        Returns:
            The unit (potentially repaired with updated content)
        """
        content = unit.content
        if not isinstance(content, dict):
            return unit
        
        # Check if already flagged as weak or has quality issues
        metadata = content.get("_metadata", {})
        needs_repair = (
            metadata.get("review_needed", False)
            or metadata.get("content_quality") == "weak"
            or metadata.get("content_quality") == "needs_review"
        )
        
        # Assess content quality if not already flagged
        if not needs_repair and ollama_repair:
            quality_score = ollama_repair.assess_content_quality(content, blocks)
            if quality_score < self.config.ollama_repair_threshold:
                needs_repair = True
                self._logger.debug(
                    f"L3 content for {concept_id} scored {quality_score:.2f}, "
                    f"below threshold {self.config.ollama_repair_threshold}"
                )
        
        if needs_repair:
            # Prepare weak content for repair
            weak_content = {
                "definition": content.get("definition", ""),
                "why_it_matters": content.get("why_it_matters", ""),
                "explanation": content.get("explanation", ""),
            }
            
            # Gather source evidence
            source_evidence = "\n\n".join(
                b.text_content for b in blocks if b.text_content
            )
            
            # Attempt repair
            try:
                repaired = ollama_repair.repair_l3_content(
                    concept_id=concept_id,
                    weak_content=weak_content,
                    source_evidence=source_evidence,
                )
                
                if repaired:
                    # Update unit content with repaired fields
                    new_content = dict(content)
                    if "definition" in repaired and repaired["definition"]:
                        new_content["definition"] = repaired["definition"]
                    if "why_it_matters" in repaired and repaired["why_it_matters"]:
                        new_content["why_it_matters"] = repaired["why_it_matters"]
                    if "explanation" in repaired and repaired["explanation"]:
                        new_content["explanation"] = repaired["explanation"]
                    
                    # Add repair metadata
                    if "_metadata" not in new_content:
                        new_content["_metadata"] = {}
                    new_content["_metadata"].update({
                        "_repaired_by_ollama": True,
                        "_repair_model": repaired.get("_repair_model", "unknown"),
                        "_repair_reason": metadata.get("review_reason", "quality_below_threshold"),
                        "content_quality": "repaired",
                        "review_needed": False,  # Clear review flag after repair
                    })
                    
                    # Create updated unit
                    from dataclasses import replace
                    unit = replace(unit, content=new_content)
                    # Don't log per-unit success - only log summary at end
                else:
                    # Track failed repair
                    self._repair_status["failed_repairs"].append(concept_id)
                    
            except Exception as e:
                # Track failed repair but don't log (summary logged at end)
                self._repair_status["failed_repairs"].append(concept_id)
        
        return unit
    
    def _get_error_subtypes_for_concept(self, concept_id: str) -> list[str]:
        """
        Get error subtype IDs for a concept from the misconception bank.
        
        Args:
            concept_id: Concept identifier
            
        Returns:
            List of error subtype IDs associated with this concept
        """
        if self._misconception_bank is None:
            return []
        
        # Get patterns for this concept
        patterns = self._misconception_bank.get_patterns_for_concept(concept_id)
        
        # Extract unique error subtype IDs
        subtypes = list(set(p.error_subtype_id for p in patterns if p.error_subtype_id))
        
        return subtypes
    
    def _log_l2_generation_stats(self, units: list[InstructionalUnit]) -> None:
        """Log L2 generation statistics.
        
        Analyzes L2 units and logs statistics about example source types,
        highlighting when a high percentage of units use default examples.
        
        Also validates core concepts and warns if any use default examples.
        
        Args:
            units: List of generated instructional units
        """
        l2_units = [u for u in units if u.target_stage == 'L2_hint_plus_example']
        if not l2_units:
            return
        
        default_count = 0
        core_concept_defaults: list[str] = []
        
        for unit in l2_units:
            content = unit.content or {}
            metadata = content.get('example_metadata', {})
            is_default = metadata.get('used_default_example', False)
            
            if is_default:
                default_count += 1
                # Check if this is a core concept
                if unit.concept_id in CORE_SQL_CONCEPTS:
                    core_concept_defaults.append(unit.concept_id)
        
        default_pct = default_count / len(l2_units) * 100
        
        print(f"[Pipeline] Generated {len(l2_units)} L2 units, "
              f"{default_count} using defaults ({default_pct:.1f}%)")
        
        # CRITICAL: Warn about core concepts using default L2
        if core_concept_defaults:
            print(f"[WARNING] {len(core_concept_defaults)} core concepts using default L2: "
                  f"{', '.join(sorted(core_concept_defaults))}")
            print("[WARNING] Consider expanding curated content or fixing extraction")
        
        if default_pct > 30:  # More than 30% defaults
            print("[Pipeline] WARNING: High default L2 rate - consider expanding curated content")
    
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
        
        # Select filter set based on export_mode first, then filter_level
        if self.config.export_mode == "student_ready":
            # Student-ready mode uses strict filters
            filters = STUDENT_READY_FILTERS
            self._logger.info("Using STUDENT_READY_FILTERS (strict mode for production learner content)")
        else:
            # Prototype mode - use filter_level to select
            filter_map = {
                "strict": STRICT_FILTERS,
                "production": PRODUCTION_FILTERS,
                "development": DEVELOPMENT_FILTERS,
            }
            filters = filter_map.get(self.config.filter_level, PRODUCTION_FILTERS)
            self._logger.info(f"Using {self.config.filter_level.upper()}_FILTERS (prototype mode)")
        
        self._filter_engine = ExportFilterEngine(filters, export_mode=self.config.export_mode)
        
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
        
        # Store filtered unit IDs and rejected units with reasons for reporting
        self._filtered_unit_ids = filter_result.filtered_units
        self._rejected_units = self._filter_engine.get_rejected_units(temp_library)
        
        # In strict mode, fail if any units are filtered
        if self.config.filter_level == "strict" and filter_result.filtered_units:
            error_msg = f"Strict mode: {len(filter_result.filtered_units)} units blocked:\n"
            for unit_id, reasons in self._rejected_units[:5]:
                error_msg += f"  - {unit_id}: {reasons[0] if reasons else 'Unknown reason'}\n"
            if len(self._rejected_units) > 5:
                error_msg += f"  ... and {len(self._rejected_units) - 5} more\n"
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
            # Add repair status to manifest
            "repair_status": {
                "enabled": self._repair_status.get("enabled", False),
                "available": self._repair_status.get("available", False),
                "disabled_reason": self._repair_status.get("disabled_reason"),
                "model": self._repair_status.get("model"),
                "repaired_units": len(self._repair_status.get("repaired_units", [])),
                "failed_repairs": len(self._repair_status.get("failed_repairs", [])),
            },
        })
        
        # Store generation stats for exporter manifest
        filtered_library.export_manifest["generation_stats"] = {
            "generated_units": generated_count,
            "filtered_out": filtered_out_count,
            "exported_units": exported_count,
            "fallback_units": len(getattr(self, '_fallback_unit_ids', [])),
            "filter_level": self.config.filter_level,
            "generated_misconceptions": len(self._misconception_units),
            "exported_misconceptions": len(misconception_units),
            "generated_reinforcement": len(self._reinforcement_items),
            "exported_reinforcement": len(reinforcement_items),
        }
        
        # Store quality report paths for exporter
        filtered_library.export_manifest["quality_reports"] = {
            "generated": "quality_report_generated.json",
            "exported": "quality_report_exported.json",
        }
        
        # Add augmentation tracking to manifest (off-book concepts)
        offbook_tracking = getattr(self, '_offbook_tracking', {})
        filtered_library.export_manifest["augmentation"] = {
            "offbook_curated_allowed": self.config.allow_offbook_curated,
            "offbook_concepts_included": offbook_tracking.get("included", []),
            "offbook_concepts_excluded": offbook_tracking.get("excluded", []),
            "offbook_count_included": len(offbook_tracking.get("included", [])),
            "offbook_count_excluded": len(offbook_tracking.get("excluded", [])),
        }
        
        # Store filtered library and stats for _gather_statistics()
        self._filtered_library = filtered_library
        self._generation_stats = {
            "generated_units": generated_count,
            "filtered_out": filtered_out_count,
            "exported_units": exported_count,
            "generated_misconceptions": len(self._misconception_units),
            "exported_misconceptions": len(misconception_units),
            "generated_reinforcement": len(self._reinforcement_items),
            "exported_reinforcement": len(reinforcement_items),
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
        Stage 12: Export the final unit library.
        
        Writes all content to output directory in JSON/JSONL format,
        including pedagogy structure exports.
        
        Args:
            library: Optional library to export (uses filtered library if None)
            
        Returns:
            Path to output directory
        """
        self._logger.info("Stage 12: Exporting final library")
        
        if library is None:
            library = self._apply_export_filters()
        
        self._exporter = UnitLibraryExporter()
        
        # Set pedagogy data for export
        if self._chapters or self._exercises or self._examples:
            self._exporter.set_pedagogy_data(
                chapters=self._chapters,
                exercises=self._exercises,
                examples=self._examples,
                navigation=self._navigation_index,
            )
            self._logger.info(
                f"Including pedagogy data: {len(self._chapters)} chapters, "
                f"{len(self._exercises)} exercises, {len(self._examples)} examples"
            )
        
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
            export_mode=self.config.export_mode,
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
        - chapters, exercises, examples: Pedagogy structure statistics
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
        repaired_count = len(getattr(self, '_repaired_unit_ids', []))
        
        # Pedagogy statistics (new)
        chapters = getattr(self, '_chapters', [])
        exercises = getattr(self, '_exercises', [])
        examples = getattr(self, '_examples', [])
        navigation = getattr(self, '_navigation_index', NavigationIndex())
        
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
            "repaired_units": repaired_count,
            "stage_timings": self.progress.get_stage_durations(),
            # Pedagogy statistics (new)
            "chapters": len(chapters),
            "exercises": len(exercises),
            "textbook_examples": len(examples),
            "navigation_index": {
                "concepts": len(navigation.by_concept),
                "chapters": len(navigation.by_chapter),
                "paths": {
                    "developer": len(navigation.by_path.get("developer", [])),
                    "admin": len(navigation.by_path.get("admin", [])),
                    "design": len(navigation.by_path.get("design", [])),
                },
            },
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
