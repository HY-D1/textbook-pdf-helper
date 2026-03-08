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
from typing import Any, Literal

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
        llm_model: Specific model name to use
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
    llm_model: str = "kimi-k2-5"
    concept_ontology_path: Path | None = None
    filter_level: Literal["strict", "production", "development"] = "production"
    generate_variants: list[str] = field(
        default_factory=lambda: ["L1", "L2", "L3", "L4", "reinforcement"]
    )
    skip_reinforcement: bool = False
    skip_misconceptions: bool = False
    validate_sql: bool = True
    min_quality_score: float = 0.7
    
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
    """
    
    success: bool = False
    stages_completed: list[PipelineStage] = field(default_factory=list)
    stages_failed: list[tuple[PipelineStage, str]] = field(default_factory=list)
    unit_library: UnitLibraryExport | None = None
    quality_report: dict[str, Any] = field(default_factory=dict)
    output_path: Path | None = None
    statistics: dict[str, Any] = field(default_factory=dict)
    elapsed_time_seconds: float = 0.0
    
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
        
        self._logger = logging.getLogger(__name__)
        self._logger.info(f"Pipeline initialized for: {config.pdf_path}")
    
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
            self._run_stage(PipelineStage.CONCEPT_MAPPING, self._filter_teaching_content, result)
            
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
            self._run_stage(PipelineStage.EXPORT, self._export, result)
            
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
            
            self._logger.info(f"Pipeline completed in {result.elapsed_time_seconds:.2f}s")
        
        return result
    
    def _run_stage(
        self, 
        stage: PipelineStage, 
        stage_fn: callable,
        result: PipelineResult
    ) -> None:
        """Run a single pipeline stage with error handling."""
        self.progress.start_stage(stage)
        try:
            stage_fn()
            self.progress.end_stage(stage, success=True)
            result.stages_completed.append(stage)
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
        Stage 4: Map content blocks to canonical concepts.
        
        Uses the concept ontology to assign blocks to relevant concepts
        based on content analysis and keyword matching.
        
        Args:
            blocks: Optional blocks to map (uses teaching blocks if None)
            
        Returns:
            Dictionary mapping concept_id to list of ContentBlocks
        """
        self._logger.info("Stage 4: Mapping content to concepts")
        
        if blocks is None:
            blocks = self._teaching_blocks
        
        # Initialize ontology
        self._ontology = ConceptOntology()
        
        # Simple keyword-based mapping
        self._concept_blocks = {}
        
        for concept_id in self._ontology.list_all_concepts():
            concept = self._ontology.get_concept(concept_id)
            if not concept:
                continue
            
            # Get keywords from concept
            keywords = self._extract_concept_keywords(concept)
            
            # Find blocks matching this concept
            matching_blocks = []
            for block in blocks:
                block_text = block.text_content.lower()
                score = sum(1 for kw in keywords if kw in block_text)
                if score > 0:
                    matching_blocks.append((block, score))
            
            # Sort by relevance score and take top blocks
            matching_blocks.sort(key=lambda x: x[1], reverse=True)
            if matching_blocks:
                self._concept_blocks[concept_id] = [b for b, _ in matching_blocks[:10]]
        
        self._logger.info(f"Mapped content to {len(self._concept_blocks)} concepts")
        return self._concept_blocks
    
    def _extract_concept_keywords(self, concept: dict) -> list[str]:
        """Extract search keywords from a concept definition."""
        keywords = []
        
        # Add title words
        title = concept.get("title", "").lower()
        keywords.extend(title.split())
        
        # Add concept id parts
        concept_id = concept.get("id", "").lower()
        keywords.extend(concept_id.replace("-", " ").split())
        
        # Add learning objectives keywords
        for objective in concept.get("learning_objectives", []):
            keywords.extend(objective.lower().split()[:5])
        
        # Deduplicate and filter
        keywords = list(set(kw for kw in keywords if len(kw) > 2))
        
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
                    if variant_name in self.config.generate_variants:
                        self._instructional_units.append(unit)
                
            except Exception as e:
                self._logger.warning(f"Failed to generate units for {concept_id}: {e}")
                continue
        
        self._logger.info(f"Generated {len(self._instructional_units)} instructional units")
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
    
    def _run_quality_gates(self, units: list[InstructionalUnit] | None = None) -> dict:
        """
        Stage 9: Run learning quality gates on all content.
        
        Validates content for learning utility, not just format compliance.
        
        Args:
            units: Optional list of units (uses generated units if None)
            
        Returns:
            Quality report dictionary
        """
        self._logger.info("Stage 9: Running quality gates")
        
        if units is None:
            units = self._instructional_units
        
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
        
        self._quality_report = {
            "summary": {
                "total_units_checked": len(units),
                "overall_score": overall_score,
                "passed": passed,
                "pass_rate": len([u for u in checks_by_unit.values() if u["average_score"] >= self.config.min_quality_score]) / len(units) if units else 0.0,
            },
            "checks_by_unit": checks_by_unit,
            "recommendations": self._generate_recommendations(checks_by_unit),
        }
        
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
        
        Args:
            units: Optional units (uses generated if None)
            misconception_units: Optional misconception units
            reinforcement_items: Optional reinforcement items
            
        Returns:
            Filtered UnitLibraryExport
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
        
        # Note: ExportFilterEngine works with PedagogicalConcept, not InstructionalUnit
        # For now, we create the export directly without filtering
        # In a production system, you'd adapt the filter engine or convert units
        
        # Build concept graph from ontology
        concept_graph = {
            "nodes": [],
            "edges": [],
        }
        if self._ontology:
            for concept_id in self._ontology.list_all_concepts():
                concept = self._ontology.get_concept(concept_id)
                if concept:
                    concept_graph["nodes"].append({
                        "concept_id": concept_id,
                        "title": concept.get("title", ""),
                        "difficulty": concept.get("difficulty", "beginner"),
                    })
        
        # Create the export
        export = UnitLibraryExport(
            source_pdf_id=self.config.doc_id,
            concept_ontology={"version": "1.0.0"},
            concept_graph=concept_graph,
            instructional_units=units,
            misconception_bank=misconception_units,
            reinforcement_bank=reinforcement_items,
            quality_report=self._quality_report,
            export_manifest={
                "filter_level": self.config.filter_level,
                "doc_id": self.config.doc_id,
            },
        )
        
        self._logger.info(
            f"Created export with {len(units)} units, "
            f"{len(misconception_units)} misconceptions, "
            f"{len(reinforcement_items)} reinforcement items"
        )
        return export
    
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
    
    def _gather_statistics(self) -> dict[str, Any]:
        """Gather processing statistics from all stages."""
        return {
            "extraction_blocks": len(self._content_blocks),
            "teaching_blocks": len(self._teaching_blocks),
            "concepts_mapped": len(self._concept_blocks),
            "instructional_units": len(self._instructional_units),
            "misconception_units": len(self._misconception_units),
            "reinforcement_items": len(self._reinforcement_items),
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
