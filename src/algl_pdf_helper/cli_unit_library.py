"""
CLI Unit Library Module - Commands for the Unit Library Pipeline.

This module provides Typer CLI commands for processing PDFs into
the new "grounded instructional unit graph" format.

Commands:
    process       - Process PDF into unit library
    validate      - Validate an existing unit library
    inspect       - Inspect units for a specific concept
    filter        - Re-run export filters on existing library
    export-legacy - Convert old concept-map.json to new format

Usage:
    algl-pdf process ./textbook.pdf --output-dir ./output
    algl-pdf validate ./output/unit-library/
    algl-pdf inspect ./output/unit-library/ --concept select-basic
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree

# Import existing CLI app for integration
try:
    from .cli import app as main_app
    HAS_MAIN_APP = True
except ImportError:
    HAS_MAIN_APP = False

# Import unit library components
try:
    from .unit_library_exporter import (
        UnitLibraryExporter,
        ExportConfig,
        FilterLevel,
        load_unit_library,
        get_units_for_concept,
        get_manifest,
        convert_legacy_concept_map,
    )
    HAS_EXPORTER = True
except ImportError:
    HAS_EXPORTER = False

try:
    from .export_filters import (
        ExportFilterEngine, 
        STRICT_FILTERS, 
        PRODUCTION_FILTERS, 
        DEVELOPMENT_FILTERS,
        PROTOTYPE_FILTERS,
        STUDENT_READY_FILTERS,
    )
    HAS_FILTERS = True
except ImportError:
    HAS_FILTERS = False

try:
    from .instructional_models import UnitLibraryExport
    HAS_MODELS = True
except ImportError:
    HAS_MODELS = False

# Import the real pipeline and quality gates
try:
    from .instructional_pipeline import (
        InstructionalPipeline,
        PipelineConfig,
        PipelineResult,
        PipelineStage,
    )
    HAS_PIPELINE = True
except ImportError:
    HAS_PIPELINE = False

try:
    from .learning_quality_gates import LearningQualityGates, QualityReport
    HAS_LEARNING_QUALITY_GATES = True
except ImportError:
    HAS_LEARNING_QUALITY_GATES = False


# =============================================================================
# CLI APP SETUP
# =============================================================================

console = Console()

# Create standalone app for new entry point
app = typer.Typer(
    name="algl-pdf-unit",
    help="Unit Library Pipeline CLI - Process PDFs into grounded instructional unit graphs",
    add_completion=False,
)

# Export command functions for integration with main CLI
__all__ = ["process_command", "validate_command", "inspect_command", "diagnose_command", "filter_command", "export_legacy_command"]

# Filter level enum for CLI
FilterLevelCLI = typer.Option(
    "production",
    help="Export filter level: strict, production (default), or development"
)

ExportModeCLI = typer.Option(
    "prototype",
    help="Export mode: prototype (allows placeholders, default) or student_ready (strict)"
)

LLMProviderCLI = typer.Option(
    "ollama",
    help="LLM provider: ollama (default, local), grounded (no LLM), kimi, openai, or claude_local. Falls back to env var ALGL_LLM_PROVIDER."
)

# Provider-specific default models
DEFAULT_MODELS: dict[str, str] = {
    "grounded": "none",
    "kimi": "kimi-k2-5",
    "openai": "gpt-4",
    "ollama": "qwen3.5:9b-q8_0",
    "claude_local": "claude-sonnet-4-6",
    "none": "none",
}


def _check_ollama_available(provider: str, model: str) -> bool:
    """Check if Ollama server is available."""
    if provider != "ollama":
        return False  # Only check for ollama
    
    try:
        import urllib.request
        
        req = urllib.request.Request(
            "http://localhost:11434/api/tags",
            method="GET",
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                return True
    except Exception:
        pass
    
    return False


def generate_doc_id() -> str:
    """Generate a unique document ID."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"doc_{timestamp}_{unique_id}"


def filter_level_from_string(level: str) -> FilterLevel:
    """Convert string to FilterLevel enum."""
    level = level.lower()
    if level == "strict":
        return FilterLevel.STRICT
    elif level == "production":
        return FilterLevel.PRODUCTION
    elif level == "development":
        return FilterLevel.DEVELOPMENT
    else:
        return FilterLevel.STRICT


def filter_level_to_literal(level: str) -> str:
    """Convert string to valid filter level literal for PipelineConfig."""
    level = level.lower()
    if level in ("strict", "production", "development"):
        return level
    return "production"


def get_filter_rules(level: str) -> list:
    """Get filter rules based on level."""
    if not HAS_FILTERS:
        return []
    
    level = level.lower()
    if level == "strict":
        return STRICT_FILTERS
    elif level == "production":
        return PRODUCTION_FILTERS
    elif level == "development":
        return DEVELOPMENT_FILTERS
    else:
        return STRICT_FILTERS


# =============================================================================
# PROCESS COMMAND
# =============================================================================

@app.command(name="process")
def process_command(
    pdf_path: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="Path to the PDF file to process",
    ),
    output_dir: Path = typer.Option(
        ...,
        "--output-dir", "-o",
        help="Output directory for the unit library (required)",
    ),
    doc_id: str | None = typer.Option(
        None,
        "--doc-id",
        help="Document ID (auto-generated if not provided)",
    ),
    llm_provider: str = LLMProviderCLI,
    llm_model: str | None = typer.Option(
        None,
        "--llm-model",
        help="LLM model to use (defaults: kimi-k2-5, gpt-4, llama3.2:3b)",
    ),
    filter_level: str = FilterLevelCLI,
    export_mode: str = ExportModeCLI,
    skip_reinforcement: bool = typer.Option(
        False,
        "--skip-reinforcement",
        help="Skip generating reinforcement items",
    ),
    skip_misconceptions: bool = typer.Option(
        False,
        "--skip-misconceptions",
        help="Skip generating misconception units",
    ),
    validate_sql: bool = typer.Option(
        True,
        "--validate-sql/--no-validate-sql",
        help="Validate SQL examples",
    ),
    skip_llm: bool = typer.Option(
        False,
        "--skip-llm",
        help="Skip all LLM-based processing (extraction/repair only, no generation)",
    ),
    min_quality_score: float = typer.Option(
        0.8,
        "--min-quality-score",
        min=0.0,
        max=1.0,
        help="Minimum quality score threshold",
    ),
    use_ollama_repair: bool = typer.Option(
        True,
        "--use-ollama-repair/--no-ollama-repair",
        help="Use Ollama to repair weak L3 content (requires local Ollama server)",
    ),
    ollama_model: str = typer.Option(
        "qwen3.5:9b-q8_0",
        "--ollama-model",
        help="Ollama model for repair (qwen3.5:9b-q8_0 recommended for RTX 4080, qwen3.5:27b-q4_K_M for better quality)",
    ),
    ollama_repair_threshold: float = typer.Option(
        0.6,
        "--ollama-repair-threshold",
        min=0.0,
        max=1.0,
        help="Quality threshold below which to trigger Ollama repair",
    ),
    claude_local_base_url: str | None = typer.Option(
        None,
        "--claude-base-url",
        help="Base URL for Claude local endpoint (defaults to CLAUDE_LOCAL_BASE_URL env var or http://localhost:8080)",
    ),
    claude_local_model: str | None = typer.Option(
        None,
        "--claude-model",
        help="Claude local model name (defaults to CLAUDE_LOCAL_MODEL env var)",
    ),
    claude_local_api_key: str | None = typer.Option(
        None,
        "--claude-api-key",
        help="API key for Claude local endpoint (defaults to CLAUDE_LOCAL_API_KEY env var)",
    ),
    clear_repair_cache: bool = typer.Option(
        False,
        "--clear-repair-cache",
        help="Clear the repair cache before processing",
    ),
    page_range: str | None = typer.Option(
        None,
        "--page-range",
        help="Process only specific pages (e.g., '1-100' or '50,75,100-120')",
    ),
    chapter_range: str | None = typer.Option(
        None,
        "--chapter-range",
        help="Process only specific chapters (e.g., '1-5' or '3,4,7'). Note: Requires PDF bookmarks/table of contents",
    ),
    resume: bool = typer.Option(
        False,
        "--resume",
        help="Resume from last checkpoint (if available)",
    ),
    cache_extraction: bool = typer.Option(
        True,
        "--cache-extraction/--no-cache-extraction",
        help="Cache and reuse PDF extraction (speeds up re-runs)",
    ),
    allow_offbook_curated: bool = typer.Option(
        False,
        "--allow-offbook-curated",
        help="Allow off-book curated concepts not present in source PDF (opt-in augmentation)",
    ),
):
    """
    Process a PDF into a unit library.
    
    This command extracts content from a PDF, maps concepts, generates
    instructional units at all adaptive stages (L1-L4), and exports
    the grounded instructional unit graph.
    
    The Ollama repair pass automatically improves weak L3 content using
    a local Ollama instance (requires qwen3.5:9b-q8_0 or similar model).
    
    Export Modes:
        prototype (default): Allows placeholder content with warnings.
            Use for development and testing.
        
        student_ready: Strict mode, blocks all placeholder and weak content.
            Use when exporting for actual student consumption.
            Blocks: placeholder practice links, default L2 examples, 
            synthetic-only L3, weak curated content.
    
    Page/Chapter Range:
        Use --page-range to process specific pages (e.g., '1-100' or '50,75,100-120').
        Use --chapter-range to process specific chapters (requires PDF bookmarks).
        Use --resume to continue from a previous interrupted run.
        Use --no-cache-extraction to force re-extraction of the PDF.
    
    Example:
        algl-pdf process ./textbook.pdf --output-dir ./output
        algl-pdf process ./textbook.pdf -o ./output --filter-level production
        algl-pdf process ./textbook.pdf -o ./output --export-mode student_ready
        algl-pdf process ./textbook.pdf -o ./output --skip-reinforcement
        algl-pdf process ./textbook.pdf -o ./output --no-ollama-repair
        algl-pdf process ./textbook.pdf -o ./output --page-range 1-50
        algl-pdf process ./textbook.pdf -o ./output --chapter-range 1-3
        algl-pdf process ./textbook.pdf -o ./output --resume
        algl-pdf process ./textbook.pdf -o ./output --page-range 100-200 --resume
    """
    # Clear repair cache if requested
    if clear_repair_cache:
        try:
            from .ollama_repair import RepairCache
            cache = RepairCache()
            count = cache.clear_cache()
            console.print(f"[green]✓ Cleared {count} cached repairs[/green]")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not clear repair cache: {e}[/yellow]")
    
    if not HAS_EXPORTER:
        console.print("[red]❌ Error: Unit library exporter not available[/red]")
        console.print("   Install required dependencies to use this command.")
        raise typer.Exit(1)
    
    if not HAS_PIPELINE:
        console.print("[red]❌ Error: Instructional pipeline not available[/red]")
        console.print("   Install required dependencies to use this command.")
        raise typer.Exit(1)
    
    # Generate doc_id if not provided
    if doc_id is None:
        doc_id = generate_doc_id()
    
    # Parse page/chapter ranges
    parsed_page_range = _parse_range(page_range)
    parsed_chapter_range = _parse_range(chapter_range)
    
    # Show range info in header
    range_info = ""
    if parsed_page_range:
        range_info += f"\nPage Range: {page_range}"
    if parsed_chapter_range:
        range_info += f"\nChapter Range: {chapter_range}"
    if resume:
        range_info += "\nMode: Resume from checkpoint"
    if not cache_extraction:
        range_info += "\nCache: Disabled"
    
    # Show header panel
    export_mode_display = f"[green]{export_mode}[/green]" if export_mode == "student_ready" else export_mode
    console.print(Panel(
        f"[bold]ALGL PDF Helper - Unit Library Generation[/bold]\n"
        f"PDF: {pdf_path.name}\n"
        f"Output: {output_dir}/\n"
        f"Doc ID: {doc_id}\n"
        f"Filter Level: {filter_level}\n"
        f"Export Mode: {export_mode_display}"
        f"{range_info}",
        title="📚 Unit Library Pipeline",
        border_style="blue"
    ))
    console.print()
    
    # Determine the model to use
    resolved_model = llm_model or DEFAULT_MODELS.get(llm_provider, "kimi-k2-5")
    
    # Check Ollama availability if using ollama provider
    if llm_provider == "ollama":
        if not _check_ollama_available(llm_provider, resolved_model):
            console.print("[yellow]⚠️  Ollama server not available at localhost:11434[/yellow]")
            console.print("[yellow]   Switching to grounded/no-LLM mode[/yellow]")
            console.print()
            # Override to use no-LLM path
            llm_provider = "none"
            resolved_model = "none"
    
    # Create pipeline configuration from CLI arguments
    config = PipelineConfig(
        pdf_path=pdf_path,
        output_dir=output_dir,
        doc_id=doc_id,
        llm_provider=llm_provider,  # type: ignore
        llm_model=resolved_model,
        filter_level=filter_level_to_literal(filter_level),  # type: ignore
        export_mode=export_mode,  # type: ignore
        skip_reinforcement=skip_reinforcement,
        skip_misconceptions=skip_misconceptions,
        validate_sql=validate_sql,
        skip_llm=skip_llm,
        min_quality_score=min_quality_score,
        use_ollama_repair=use_ollama_repair,
        ollama_model=ollama_model,
        ollama_repair_threshold=ollama_repair_threshold,
        claude_local_base_url=claude_local_base_url or os.getenv("CLAUDE_LOCAL_BASE_URL", "http://localhost:8080"),
        claude_local_model=claude_local_model or os.getenv("CLAUDE_LOCAL_MODEL", "claude-sonnet-4-6"),
        claude_local_api_key=claude_local_api_key or os.getenv("CLAUDE_LOCAL_API_KEY", ""),
        page_range=parsed_page_range,  # type: ignore
        chapter_range=parsed_chapter_range,  # type: ignore
        resume_from_checkpoint=resume,
        cache_extraction=cache_extraction,
        allow_offbook_curated=allow_offbook_curated,
    )
    
    # Run the pipeline with progress display
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        
        # Create pipeline instance
        pipeline = InstructionalPipeline(config)
        
        # Suppress duplicate filter logging (CLI handles output display)
        pipeline._quiet_filter_logging = True
        
        # Run pipeline and capture result
        try:
            result = pipeline.run()
        except Exception as e:
            console.print(f"[red]❌ Pipeline failed:[/red] {e}")
            raise typer.Exit(1)
        
        if not result.success:
            console.print("[red]❌ Pipeline failed with errors:[/red]")
            for stage, error_msg in result.stages_failed:
                console.print(f"  - {stage.name}: {error_msg}")
            raise typer.Exit(1)
        
        # Display completed stages with real statistics
        stage_names = {
            PipelineStage.EXTRACTION: "📄 Document Extraction",
            PipelineStage.SEGMENTATION: "🔍 Content Segmentation",
            PipelineStage.CONTENT_FILTERING: "🧹 Content Filtering",
            PipelineStage.CONCEPT_MAPPING: "🗺️  Concept Mapping",
            PipelineStage.UNIT_GENERATION: "📦 Unit Generation",
            PipelineStage.MISCONCEPTION_GENERATION: "⚠️  Misconception Bank",
            PipelineStage.REINFORCEMENT_GENERATION: "🔄 Reinforcement Items",
            PipelineStage.VALIDATION: "🔒 SQL Validation",
            PipelineStage.QUALITY_GATES: "✅ Quality Gates",
            PipelineStage.FILTERING: "🚦 Export Filters",
            PipelineStage.EXPORT: "💾 Export",
        }
        
        for stage in result.stages_completed:
            stage_name = stage_names.get(stage, stage.name)
            console.print(f"  [green]✓[/green] {stage_name}")
        
        # Show skipped stages
        if skip_misconceptions:
            console.print(f"  [yellow]⊘[/yellow] ⚠️  Misconception Bank ............. Skipped")
        if skip_reinforcement:
            console.print(f"  [yellow]⊘[/yellow] 🔄 Reinforcement Items ............ Skipped")
        if not validate_sql:
            console.print(f"  [yellow]⊘[/yellow] 🔒 SQL Validation ................. Skipped")
    
    # Get real statistics from the pipeline result
    stats = result.statistics
    quality_report = result.quality_report
    
    # Print statistics table with real data
    console.print()
    console.print("[bold]Statistics:[/bold]")
    
    stats_table = Table(show_header=False, box=None)
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="white")
    
    # Get all metrics with clear naming
    generated_units = stats.get("generated_instructional_units", stats.get("generated_units", stats.get("instructional_units", 0)))
    exported_units = stats.get("exported_instructional_units", stats.get("exported_units", stats.get("instructional_units", 0)))
    filtered_out = stats.get("filtered_out_units", stats.get("filtered_out", 0))
    fallback_units = stats.get("fallback_units", 0)
    repaired_units = stats.get("repaired_units", 0)
    misconception_units = stats.get("misconception_units", 0)
    reinforcement_items = stats.get("reinforcement_items", 0)
    concepts_mapped = stats.get("concepts_mapped", 0)
    teaching_blocks = stats.get("teaching_blocks", 0)
    
    # Always show the generation pipeline clearly
    if generated_units > 0 and (generated_units != exported_units or filtered_out > 0):
        # Full breakdown when filtering occurred
        stats_table.add_row("Generated Units", str(generated_units))
        if filtered_out > 0:
            stats_table.add_row("Filtered Out", f"[red]{filtered_out}[/red]")
        stats_table.add_row("Exported Units", f"[green]{exported_units}[/green]")
    else:
        # Simple case: no filtering happened
        stats_table.add_row("Total Units", str(exported_units))
    
    stats_table.add_row("Misconception Units", str(misconception_units))
    stats_table.add_row("Reinforcement Items", str(reinforcement_items))
    stats_table.add_row("Concepts Covered", str(concepts_mapped))
    stats_table.add_row("Teaching Blocks", str(teaching_blocks))
    
    # Show export mode
    export_mode_value = getattr(config, 'export_mode', 'prototype')
    if export_mode_value == "student_ready":
        stats_table.add_row("Export Mode", "[green]student_ready (strict)[/green]")
    else:
        stats_table.add_row("Export Mode", f"{export_mode_value}")
    
    # Show fallback units if any (these are quality failures)
    if fallback_units > 0:
        stats_table.add_row("Fallback Units", f"[yellow]{fallback_units}[/yellow]")
    
    # Show repaired units if any (Ollama repair was applied)
    if repaired_units > 0:
        stats_table.add_row("Repaired Units", f"[green]{repaired_units}[/green]")
    
    # Add quality report info if available
    if quality_report and "summary" in quality_report:
        summary = quality_report["summary"]
        overall_score = summary.get("overall_score", 0)
        pass_rate = summary.get("pass_rate", 0)
        stats_table.add_row("Quality Score", f"{overall_score:.2f}")
        stats_table.add_row("Pass Rate", f"{pass_rate:.1%}")
    
    # Estimate learning time (5 min per concept)
    if concepts_mapped > 0:
        learning_time_hours = (concepts_mapped * 5) / 60
        stats_table.add_row("Est. Learning Time", f"{learning_time_hours:.1f}h")
    
    # Add timing info
    elapsed_time = result.elapsed_time_seconds
    if elapsed_time > 0:
        stats_table.add_row("Elapsed Time", f"{elapsed_time:.1f}s")
    
    console.print(stats_table)
    
    # Show blocked units with reasons if any were filtered
    if result.blocked_units_with_reasons:
        console.print()
        console.print("[yellow bold]Units blocked from production:[/yellow bold]")
        blocked_table = Table(show_header=True, box=None)
        blocked_table.add_column("Unit ID", style="cyan", no_wrap=True)
        blocked_table.add_column("Reason", style="white")
        
        for unit_id, reasons in result.blocked_units_with_reasons[:10]:
            # Get the first/highest priority reason
            reason = reasons[0] if reasons else "Unknown reason"
            # Truncate long reasons
            if len(reason) > 60:
                reason = reason[:57] + "..."
            blocked_table.add_row(unit_id, reason)
        
        if len(result.blocked_units_with_reasons) > 10:
            blocked_table.add_row(
                "...", 
                f"[dim]and {len(result.blocked_units_with_reasons) - 10} more[/dim]"
            )
        
        console.print(blocked_table)
        console.print("[dim]Run with --filter-level development to include these units with review flags[/dim]")
    
    console.print()
    console.print(f"[green]✅ Unit library exported to:[/green] {output_dir}/")
    
    # List generated files
    output_path = result.output_path if result.output_path else Path(output_dir)
    console.print()
    console.print("[bold]Generated Files:[/bold]")
    expected_files = [
        "instructional_units.jsonl",
        "source_spans.jsonl",
        "concept_graph.json",
        "quality_report.json",
        "export_manifest.json",
    ]
    for filename in expected_files:
        file_path = output_path / filename
        if file_path.exists():
            size = file_path.stat().st_size
            console.print(f"  [green]✓[/green] {filename} ({size:,} bytes)")
        else:
            console.print(f"  [yellow]○[/yellow] {filename} (not found)")
    
    # After export, reload and verify
    try:
        exported_library = load_unit_library(Path(output_dir))
        actual_unit_count = len(exported_library.instructional_units)
        
        if actual_unit_count == 0:
            console.print()
            console.print("[red bold]ERROR: Export succeeded but 0 instructional units were created![/red bold]")
            console.print("[dim]Possible causes:[/dim]")
            console.print("  - All units were filtered out (check filter level)")
            console.print("  - All units were fallback units (strict mode)")
            console.print("  - No concepts were mapped from the PDF")
            raise typer.Exit(1)
        
        console.print()
        console.print(f"[green bold]✓ Successfully exported {actual_unit_count} instructional units[/green bold]")
        
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[yellow]Warning: Could not verify exported library: {e}[/yellow]")


def _parse_range(range_str: str | None) -> tuple[int, int] | list[int] | None:
    """Parse a range string like '1-100' or '1,2,3' into a tuple or list.
    
    Args:
        range_str: Range string (e.g., '1-100', '50,75,100-120', '1,2,3') or None
        
    Returns:
        Tuple (start, end) for ranges, list of integers for comma-separated values,
        or None if range_str is None or an OptionInfo object
        
    Raises:
        ValueError: If the range string is invalid
    """
    # Handle None or OptionInfo objects (when option is not provided)
    if range_str is None:
        return None
    
    # Handle OptionInfo objects (typer internal type when option not provided)
    if type(range_str).__name__ == 'OptionInfo':
        return None
    
    range_str = range_str.strip()
    
    # Handle range format: "1-100"
    if '-' in range_str and ',' not in range_str:
        parts = range_str.split('-')
        if len(parts) == 2:
            try:
                start = int(parts[0].strip())
                end = int(parts[1].strip())
                if start < 1:
                    raise ValueError(f"Range start must be >= 1, got {start}")
                if end < start:
                    raise ValueError(f"Range end ({end}) must be >= start ({start})")
                return (start, end)
            except ValueError as e:
                if "must be" in str(e):
                    raise
                raise ValueError(f"Invalid range format: {range_str}")
    
    # Handle comma-separated format: "1,2,3" or "50,75,100-120"
    if ',' in range_str:
        pages = []
        for part in range_str.split(','):
            part = part.strip()
            if '-' in part:
                # Handle sub-range like "100-120"
                sub_parts = part.split('-')
                if len(sub_parts) == 2:
                    try:
                        start = int(sub_parts[0].strip())
                        end = int(sub_parts[1].strip())
                        pages.extend(range(start, end + 1))
                    except ValueError:
                        raise ValueError(f"Invalid sub-range format: {part}")
                else:
                    raise ValueError(f"Invalid sub-range format: {part}")
            else:
                # Single page
                try:
                    pages.append(int(part))
                except ValueError:
                    raise ValueError(f"Invalid page number: {part}")
        
        if not pages:
            raise ValueError(f"No valid pages in range: {range_str}")
        
        return sorted(set(pages))  # Remove duplicates and sort
    
    # Single page number
    try:
        page = int(range_str)
        if page < 1:
            raise ValueError(f"Page number must be >= 1, got {page}")
        return [page]
    except ValueError:
        raise ValueError(f"Invalid range format: {range_str}")


def _extract_page_count(pdf_path: Path) -> int:
    """Extract page count from PDF."""
    try:
        import fitz  # PyMuPDF
        with fitz.open(pdf_path) as doc:
            return len(doc)
    except Exception:
        # Fallback: estimate based on file size
        file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
        return int(file_size_mb * 10)  # Rough estimate: 10 pages per MB


# =============================================================================
# VALIDATE COMMAND
# =============================================================================

@app.command(name="validate")
def validate_command(
    library_dir: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Path to unit library directory",
    ),
    detailed: bool = typer.Option(
        False,
        "--detailed",
        help="Show detailed validation report",
    ),
    use_generated_report: bool = typer.Option(
        False,
        "--use-generated-report",
        help="Use the pre-filter generated quality report instead of exported report",
    ),
    recompute: bool = typer.Option(
        False,
        "--recompute",
        help="Recompute validation instead of using stored report",
    ),
):
    """
    Validate an existing unit library.
    
    Runs all quality gates on the unit library and displays a quality report.
    Uses the exported units report by default (post-filter).
    
    Example:
        algl-pdf validate ./output/unit-library/
        algl-pdf validate ./output/unit-library/ --detailed
        algl-pdf validate ./output/unit-library/ --use-generated-report
        algl-pdf validate ./output/unit-library/ --recompute
    """
    if not HAS_EXPORTER:
        console.print("[red]❌ Error: Unit library exporter not available[/red]")
        raise typer.Exit(1)
    
    console.print(Panel(
        f"[bold]Unit Library Validation[/bold]\n"
        f"Library: {library_dir}/",
        title="🔍 Validation",
        border_style="blue"
    ))
    console.print()
    
    try:
        # Load manifest
        manifest = get_manifest(library_dir)
        
        # Check for quality report information
        quality_reports = manifest.get("quality_reports", {})
        files_section = manifest.get("files", {})
        
        # Determine which quality report to use
        has_exported_report = quality_reports.get("exported") or files_section.get("quality_report_exported")
        has_generated_report = quality_reports.get("generated") or files_section.get("quality_report_generated")
        
        # Default to exported report unless user requests generated report
        if use_generated_report and has_generated_report:
            selected_report_name = "generated"
            selected_report_file = quality_reports.get("generated") or files_section.get("quality_report_generated")
        elif has_exported_report:
            selected_report_name = "exported"
            selected_report_file = quality_reports.get("exported") or files_section.get("quality_report_exported")
        elif has_generated_report:
            # Fallback to generated if exported not available
            selected_report_name = "generated"
            selected_report_file = quality_reports.get("generated") or files_section.get("quality_report_generated")
        else:
            selected_report_name = "default"
            selected_report_file = "quality_report.json"
        
        # Load full library
        library = load_unit_library(library_dir)
        
        # Check if library has units
        if not library.instructional_units:
            console.print("[red bold]ERROR: Library contains 0 instructional units![/red bold]")
            raise typer.Exit(1)
        
        # Display summary
        stats = manifest.get("statistics", {})
        
        console.print("[bold]Library Summary:[/bold]")
        summary_table = Table(show_header=False, box=None)
        summary_table.add_column("Field", style="cyan")
        summary_table.add_column("Value", style="white")
        
        # Read correct manifest keys (with fallbacks for different naming conventions)
        total_units = stats.get("instructional_units", stats.get("total_units", 0))
        filtered_out = stats.get("filtered_out", stats.get("filtered_out_units", stats.get("filtered_units", 0)))
        
        # Calculate generated units (total before filtering)
        generated_units = stats.get("generated_instructional_units", stats.get("generated_units",
                                 stats.get("total_units_generated", total_units + filtered_out)))
        
        summary_table.add_row("Generated Units", str(generated_units))
        summary_table.add_row("Filtered Out", str(filtered_out))
        summary_table.add_row("Exported Units", str(total_units))
        summary_table.add_row("Concepts Covered", str(stats.get("concepts_covered", 0)))
        summary_table.add_row("Misconceptions", str(stats.get("total_misconceptions", stats.get("misconception_units", 0))))
        summary_table.add_row("Reinforcement Items", str(stats.get("total_reinforcement", stats.get("reinforcement_items", 0))))
        
        console.print(summary_table)
        console.print()
        
        # Display quality report info
        if has_exported_report or has_generated_report:
            console.print("[bold]Quality Reports:[/bold]")
            report_table = Table(show_header=False, box=None)
            report_table.add_column("Report", style="cyan")
            report_table.add_column("File", style="white")
            report_table.add_column("Status", style="white")
            
            if has_generated_report:
                gen_file = quality_reports.get("generated") or files_section.get("quality_report_generated", "N/A")
                is_selected = selected_report_name == "generated"
                status = "[green]✓ selected[/green]" if is_selected else ""
                report_table.add_row("Generated (pre-filter)", str(gen_file), status)
            
            if has_exported_report:
                exp_file = quality_reports.get("exported") or files_section.get("quality_report_exported", "N/A")
                is_selected = selected_report_name == "exported"
                status = "[green]✓ selected[/green]" if is_selected else ""
                report_table.add_row("Exported (post-filter)", str(exp_file), status)
            
            console.print(report_table)
            console.print(f"[dim]Using {selected_report_name} quality report for validation[/dim]")
            console.print()
        
        # Run library-level validation for student_ready/deployable checks
        if HAS_LEARNING_QUALITY_GATES:
            console.print("[bold]Library-Level Validation:[/bold]")
            
            # Import and run library validation
            from .learning_quality_gates import validate_library
            
            lib_validation = validate_library(library)
            
            validation_table = Table(show_header=False, box=None)
            validation_table.add_column("Check", style="cyan")
            validation_table.add_column("Status", style="white")
            
            # L2 Coverage
            l2_cov = lib_validation["l2_coverage"]
            l2_status = f"[green]{l2_cov['count']}/{l2_cov['total']} ({l2_cov['ratio']:.0%})[/green]" if l2_cov["passed"] else f"[red]{l2_cov['count']}/{l2_cov['total']} ({l2_cov['ratio']:.0%})[/red]"
            validation_table.add_row("L2 Coverage (min 80%)", l2_status)
            
            # L3 Coverage
            l3_cov = lib_validation["l3_coverage"]
            l3_status = f"[green]{l3_cov['count']}/{l3_cov['total']} ({l3_cov['ratio']:.0%})[/green]" if l3_cov["passed"] else f"[red]{l3_cov['count']}/{l3_cov['total']} ({l3_cov['ratio']:.0%})[/red]"
            validation_table.add_row("L3 Coverage (min 80%)", l3_status)
            
            # Fallback Ratio
            fallback = lib_validation["fallback_ratio"]
            fallback_status = f"[green]{fallback['count']}/{fallback['total']} ({fallback['ratio']:.0%})[/green]" if fallback["passed"] else f"[red]{fallback['count']}/{fallback['total']} ({fallback['ratio']:.0%})[/red]"
            validation_table.add_row("Fallback Ratio (max 10%)", fallback_status)
            
            # Off-book Concepts
            offbook = lib_validation["offbook_concepts"]
            if offbook["list"]:
                offbook_str = f"[red]{len(offbook['list'])} found: {', '.join(offbook['list'][:3])}[/red]"
                if len(offbook['list']) > 3:
                    offbook_str += f" [red]and {len(offbook['list']) - 3} more[/red]"
            else:
                offbook_str = "[green]None[/green]"
            validation_table.add_row("Off-book Concepts", offbook_str)
            
            # Overall Status
            if lib_validation["valid"]:
                validation_table.add_row("[bold]Overall[/bold]", "[bold green]✓ DEPLOYABLE[/bold green]")
            else:
                validation_table.add_row("[bold]Overall[/bold]", "[bold red]✗ NOT DEPLOYABLE[/bold red]")
            
            console.print(validation_table)
            console.print()
            
            # Show deployment warning if not valid
            if not lib_validation["valid"]:
                console.print("[bold yellow]⚠️  WARNING: Library is NOT ready for deployment[/bold yellow]")
                console.print("[dim]Reasons:[/dim]")
                for reason in lib_validation.get("reasons", []):
                    console.print(f"  • {reason}")
                console.print()
                console.print("[dim]To include weak units anyway, use:[/dim]")
                console.print("  [cyan]algl-pdf filter ./output/unit-library/ --level development[/cyan]")
                console.print()
        
        # Display validation results
        console.print("[bold]File Validation:[/bold]")
        
        # Check required files
        required_files = [
            "export_manifest.json",
            "concept_ontology.json",
            "concept_graph.json",
            "instructional_units.jsonl",
        ]
        
        validation_table = Table(show_header=True)
        validation_table.add_column("Check", style="cyan")
        validation_table.add_column("Status", style="bold")
        validation_table.add_column("Details", style="white")
        
        all_passed = True
        
        for filename in required_files:
            file_path = library_dir / filename
            if file_path.exists():
                validation_table.add_row(filename, "[green]✓ PASS[/green]", "File exists")
            else:
                validation_table.add_row(filename, "[red]✗ FAIL[/red]", "Missing")
                all_passed = False
        
        # Check manifest integrity
        manifest_path = library_dir / "export_manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest_data = json.load(f)
                if "export_version" in manifest_data and "statistics" in manifest_data:
                    validation_table.add_row(
                        "Manifest Integrity", "[green]✓ PASS[/green]", "Valid structure"
                    )
                else:
                    validation_table.add_row(
                        "Manifest Integrity", "[red]✗ FAIL[/red]", "Missing required fields"
                    )
                    all_passed = False
            except json.JSONDecodeError as e:
                validation_table.add_row(
                    "Manifest Integrity", "[red]✗ FAIL[/red]", f"Invalid JSON: {e}"
                )
                all_passed = False
        
        # Check for empty unit files
        units_file = library_dir / "instructional_units.jsonl"
        if units_file.exists():
            line_count = sum(1 for _ in open(units_file, "r", encoding="utf-8"))
            if line_count > 0:
                validation_table.add_row(
                    "Instructional Units", "[green]✓ PASS[/green]", f"{line_count} units found"
                )
            else:
                validation_table.add_row(
                    "Instructional Units", "[red]✗ FAIL[/red]", "No units found"
                )
                all_passed = False
        
        console.print(validation_table)
        console.print()
        
        # Run real quality gates if available
        if HAS_LEARNING_QUALITY_GATES:
            console.print("[bold]Quality Gates:[/bold]")
            
            # Load the selected quality report file or recompute
            report_file = library_dir / selected_report_file
            if not recompute and report_file.exists():
                with open(report_file, "r", encoding="utf-8") as f:
                    quality_report = json.load(f)
                console.print(f"[dim]Loaded quality report from {selected_report_file}[/dim]")
            else:
                if recompute:
                    console.print("[yellow]Recomputing validation as requested...[/yellow]")
                else:
                    console.print(f"[yellow]Report file {selected_report_file} not found, recomputing validation...[/yellow]")
                gates = LearningQualityGates()
                report_generator = QualityReport(gates)
                quality_report = report_generator.generate_full_report(library)
            
            summary = quality_report.get("summary", {})
            
            # Normalize report schema to handle both old (pipeline) and new (validator) formats
            # Pipeline format: total_units_checked, overall_score, passed, pass_rate
            # Validator format: total_units, passed_units, failed_units, overall_pass_rate, overall_passed
            total_units = summary.get("total_units", summary.get("total_units_checked", 0))
            passed_units = summary.get("passed_units", 0)
            if "passed" in summary and "passed_units" not in summary:
                # Derive passed_units from overall_score and pass_rate if available
                pass_rate_val = summary.get("pass_rate", 0)
                if total_units > 0 and pass_rate_val > 0:
                    passed_units = int(total_units * pass_rate_val)
            failed_units = summary.get("failed_units", total_units - passed_units)
            pass_rate = summary.get("overall_pass_rate", summary.get("pass_rate", 0))
            overall_passed = summary.get("overall_passed", summary.get("passed", False))
            
            quality_table = Table(show_header=False, box=None)
            quality_table.add_column("Metric", style="cyan")
            quality_table.add_column("Value", style="white")
            
            quality_table.add_row("Total Units Checked", str(total_units))
            quality_table.add_row("Passed", f"[green]{passed_units}[/green]")
            quality_table.add_row("Failed", f"[red]{failed_units}[/red]" if failed_units > 0 else str(failed_units))
            quality_table.add_row("Pass Rate", f"{pass_rate:.1%}")
            quality_table.add_row("Overall", "[green]✓ PASSED[/green]" if overall_passed else "[red]✗ FAILED[/red]")
            
            console.print(quality_table)
            console.print()
            
            # Show gate pass rates if detailed
            if detailed:
                gate_rates = quality_report.get("gate_pass_rates", {})
                if gate_rates:
                    console.print("[bold]Gate Pass Rates:[/bold]")
                    gate_table = Table(show_header=True)
                    gate_table.add_column("Gate Category", style="cyan")
                    gate_table.add_column("Avg Score", style="white")
                    gate_table.add_column("Pass Rate", style="white")
                    gate_table.add_column("Checks", style="white")
                    
                    for gate_name, gate_stats in gate_rates.items():
                        avg_score = gate_stats.get("average_score", 0)
                        gate_pass_rate = gate_stats.get("pass_rate", 0)
                        total_checks = gate_stats.get("total_checks", 0)
                        gate_table.add_row(
                            gate_name.replace("_", " ").title(),
                            f"{avg_score:.1%}",
                            f"{gate_pass_rate:.1%}",
                            str(total_checks)
                        )
                    console.print(gate_table)
                    console.print()
            
            # Show recommendations
            recommendations = quality_report.get("recommendations", [])
            if recommendations and recommendations != ["No issues found - library ready for export!"]:
                console.print("[bold]Recommendations:[/bold]")
                for rec in recommendations[:10]:  # Show top 10
                    console.print(f"  • {rec}")
                console.print()
            
            # Update overall pass status
            if not overall_passed:
                all_passed = False
        else:
            # FAIL explicitly instead of silently passing
            console.print("[red]❌ Error: Learning quality gates not available[/red]")
            console.print("   Install required dependencies to run validation.")
            raise typer.Exit(1)
        
        # Overall result
        if HAS_LEARNING_QUALITY_GATES:
            from .learning_quality_gates import validate_library
            lib_validation = validate_library(library)
            
            if all_passed and lib_validation["valid"]:
                console.print("[bold green]✅ Validation PASSED[/bold green]")
                console.print("   All quality gates passed. Library is DEPLOYABLE.")
                raise typer.Exit(0)
            elif all_passed and not lib_validation["valid"]:
                console.print("[bold yellow]⚠️  Validation PASSED with WARNINGS[/bold yellow]")
                console.print("   Unit-level checks passed but library-level checks failed.")
                console.print("   Library is NOT DEPLOYABLE for student-ready export.")
                console.print("   Run with --filter-level development to bypass strict checks.")
                raise typer.Exit(1)
            else:
                console.print("[bold red]❌ Validation FAILED[/bold red]")
                console.print("   Some quality checks failed. Review issues above.")
                raise typer.Exit(1)
        else:
            if all_passed:
                console.print("[bold green]✅ Validation PASSED[/bold green]")
                console.print("   All quality gates passed.")
                raise typer.Exit(0)
            else:
                console.print("[bold red]❌ Validation FAILED[/bold red]")
                console.print("   Some quality checks failed. Review issues above.")
                raise typer.Exit(1)
            
    except FileNotFoundError as e:
        console.print(f"[red]❌ Error: Could not load library:[/red] {e}")
        raise typer.Exit(1)
    except typer.Exit:
        raise  # Re-raise typer.Exit to preserve exit code
    except Exception as e:
        console.print(f"[red]❌ Validation failed:[/red] {e}")
        import traceback
        console.print(traceback.format_exc())
        raise typer.Exit(1)


# =============================================================================
# INSPECT COMMAND
# =============================================================================

@app.command(name="inspect")
def inspect_command(
    library_dir: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Path to unit library directory",
    ),
    concept: str = typer.Option(
        ...,
        "--concept", "-c",
        help="Concept ID to inspect",
    ),
    show_sql: bool = typer.Option(
        True,
        "--show-sql/--no-show-sql",
        help="Show SQL examples with syntax highlighting",
    ),
):
    """
    Inspect units for a specific concept.
    
    Display all variants (L1-L4) for a concept with source evidence.
    
    Example:
        algl-pdf inspect ./output/unit-library/ --concept select-basic
        algl-pdf inspect ./output/unit-library/ -c join-operations --no-show-sql
    """
    if not HAS_EXPORTER:
        console.print("[red]❌ Error: Unit library exporter not available[/red]")
        raise typer.Exit(1)
    
    console.print(Panel(
        f"[bold]Unit Inspection[/bold]\n"
        f"Library: {library_dir}/\n"
        f"Concept: {concept}",
        title="🔍 Inspect",
        border_style="blue"
    ))
    console.print()
    
    try:
        # Load units for concept
        units = get_units_for_concept(library_dir, concept)
        
        if not units:
            console.print(f"[yellow]⚠️  No units found for concept:[/yellow] {concept}")
            console.print()
            console.print("Available concepts (from manifest):")
            
            # Try to list available concepts
            try:
                manifest = get_manifest(library_dir)
                units_per_concept = manifest.get("statistics", {}).get("units_per_concept", {})
                if units_per_concept:
                    for cid, count in list(units_per_concept.items())[:10]:
                        console.print(f"  - {cid}: {count} units")
                    if len(units_per_concept) > 10:
                        console.print(f"  ... and {len(units_per_concept) - 10} more")
                else:
                    console.print("  (Unable to determine available concepts)")
            except Exception:
                console.print("  (Unable to determine available concepts)")
            
            raise typer.Exit(1)
        
        # Display units by stage
        console.print(f"[bold]Found {len(units)} unit(s) for concept '{concept}':[/bold]")
        console.print()
        
        # Group by target_stage
        stages: dict[str, list] = {
            "L1_hint": [],
            "L2_hint_plus_example": [],
            "L3_explanation": [],
            "L4_reflective_note": [],
            "reinforcement": [],
        }
        for unit in units:
            target_stage = getattr(unit, "target_stage", "unknown")
            if target_stage in stages:
                stages[target_stage].append(unit)
            else:
                # Handle legacy or unknown stage names
                stage_mapping = {
                    "L1": "L1_hint",
                    "L2": "L2_hint_plus_example",
                    "L3": "L3_explanation",
                    "L4": "L4_reflective_note",
                }
                mapped = stage_mapping.get(str(target_stage), None)
                if mapped and mapped in stages:
                    stages[mapped].append(unit)
        
        # Display each stage
        for stage_name, stage_units in stages.items():
            if not stage_units:
                continue
            
            display_name = stage_name.replace("_", " ").title()
            console.print(f"[bold cyan]{display_name}:[/bold cyan]")
            
            for unit in stage_units:
                # Unit header
                title = getattr(unit, "title", "Untitled")
                unit_type = getattr(unit, "unit_type", "unknown")
                estimated_time = getattr(unit, "estimated_time_seconds", 0)
                
                console.print(f"  [bold]{title}[/bold]")
                console.print(f"    Type: {unit_type}")
                console.print(f"    Time: {estimated_time}s")
                
                # Content preview
                content = getattr(unit, "content", {})
                if content:
                    if stage_name == "L1_hint":
                        hint = content.get("hint_text", "") if isinstance(content, dict) else ""
                        if hint:
                            console.print(f"    Hint: {hint[:100]}...")
                    
                    elif stage_name == "L2_hint_plus_example":
                        explanation = content.get("example_explanation", "") if isinstance(content, dict) else ""
                        if explanation:
                            console.print(f"    Explanation: {explanation[:100]}...")
                        
                        if show_sql:
                            sql = content.get("example_sql", "") if isinstance(content, dict) else ""
                            if sql:
                                console.print("    SQL:")
                                console.print(Syntax(sql, "sql", theme="monokai", line_numbers=False))
                    
                    elif stage_name == "L3_explanation":
                        definition = content.get("definition", "") if isinstance(content, dict) else ""
                        if definition:
                            console.print(f"    Definition: {definition[:150]}...")
                        
                        if show_sql:
                            examples = content.get("examples", []) if isinstance(content, dict) else []
                            if examples:
                                console.print(f"    Examples ({len(examples)}):")
                                for i, ex in enumerate(examples[:2], 1):
                                    sql = ex.get("sql", "") if isinstance(ex, dict) else ""
                                    if sql:
                                        console.print(f"    Example {i}:")
                                        console.print(Syntax(sql, "sql", theme="monokai", line_numbers=False))
                    
                    elif stage_name == "L4_reflective_note":
                        reflection_prompts = content.get("reflection_prompts", []) if isinstance(content, dict) else []
                        if reflection_prompts:
                            console.print(f"    Reflection Prompts ({len(reflection_prompts)}):")
                            for prompt in reflection_prompts[:2]:
                                console.print(f"      • {prompt[:80]}...")
                    
                    elif stage_name == "reinforcement":
                        recall = content.get("recall_prompt", "") if isinstance(content, dict) else ""
                        if recall:
                            console.print(f"    Recall: {recall}")
                
                # Source evidence
                evidence_spans = getattr(unit, "evidence_spans", [])
                if evidence_spans:
                    console.print(f"    Evidence: {len(evidence_spans)} source span(s)")
                    for span in evidence_spans[:2]:
                        page = getattr(span, "page", "?")
                        excerpt = getattr(span, "excerpt", "")[:60]
                        console.print(f"      • Page {page}: {excerpt}...")
                
                console.print()
        
        # Display prerequisites
        if units:
            first_unit = units[0]
            prereqs = getattr(first_unit, "prerequisites", [])
            if prereqs:
                console.print(f"[bold]Prerequisites:[/bold] {', '.join(prereqs)}")
                console.print()
        
    except FileNotFoundError as e:
        console.print(f"[red]❌ Error: Could not load library:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Inspection failed:[/red] {e}")
        raise typer.Exit(1)


# =============================================================================
# DIAGNOSE COMMAND
# =============================================================================

@app.command(name="diagnose")
def diagnose_command(
    library_dir: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Path to unit library directory",
    ),
    detailed: bool = typer.Option(
        False,
        "--detailed",
        help="Show detailed diagnostic report",
    ),
):
    """
    Diagnose content gaps and quality issues in a unit library.
    
    Analyzes the library and reports:
    - L3 coverage gaps (concepts missing explanations)
    - L2 units using default examples
    - Unresolved practice links
    - Heading-like content in why_it_matters
    - Missing evidence spans
    
    Example:
        algl-pdf diagnose ./output/unit-library/
        algl-pdf diagnose ./output/unit-library/ --detailed
    """
    console.print(Panel(
        f"[bold]Content Diagnostics[/bold]\n"
        f"Library: {library_dir}/",
        title="🔍 Diagnose",
        border_style="blue"
    ))
    console.print()
    
    try:
        # Import diagnostics
        try:
            from .content_diagnostics import ContentDiagnostics, DiagnosticReport
            HAS_DIAGNOSTICS = True
        except ImportError:
            HAS_DIAGNOSTICS = False
        
        if not HAS_DIAGNOSTICS:
            console.print("[red]❌ Error: Content diagnostics module not available[/red]")
            raise typer.Exit(1)
        
        # Run diagnostics
        diagnostics = ContentDiagnostics()
        report = diagnostics.analyze_library(library_dir)
        
        # Display summary
        console.print(report.summary())
        
        # Display detailed report if requested
        if detailed:
            console.print()
            console.print(report.format_report())
        
        # Exit with error if not student-ready
        summary = report.summary()
        if "❌" in summary or "⚠️" in summary:
            console.print()
            console.print("[yellow]Library has issues that should be addressed before student-ready export.[/yellow]")
            raise typer.Exit(1)
        else:
            console.print()
            console.print("[green]✅ Library appears ready for student-facing use![/green]")
            raise typer.Exit(0)
        
    except FileNotFoundError as e:
        console.print(f"[red]❌ Error: Could not load library:[/red] {e}")
        raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]❌ Diagnostics failed:[/red] {e}")
        import traceback
        console.print(traceback.format_exc())
        raise typer.Exit(1)


# =============================================================================
# FILTER COMMAND
# =============================================================================

@app.command(name="filter")
def filter_command(
    library_dir: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Path to unit library directory",
    ),
    level: str = FilterLevelCLI,
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir", "-o",
        help="Output directory for filtered library (default: in-place)",
    ),
):
    """
    Re-run export filters on existing library.
    
    Creates a filtered subset of the unit library based on the specified level.
    
    Example:
        algl-pdf filter ./output/unit-library/ --level strict
        algl-pdf filter ./output/unit-library/ -o ./output/filtered/ --level production
    """
    if not HAS_EXPORTER:
        console.print("[red]❌ Error: Unit library exporter not available[/red]")
        raise typer.Exit(1)
    
    if not HAS_FILTERS:
        console.print("[red]❌ Error: Export filters not available[/red]")
        raise typer.Exit(1)
    
    # Use input directory as output if not specified
    if output_dir is None:
        output_dir = library_dir
    
    console.print(Panel(
        f"[bold]Export Filter[/bold]\n"
        f"Library: {library_dir}/\n"
        f"Filter Level: {level}\n"
        f"Output: {output_dir}/",
        title="🚦 Filter",
        border_style="blue"
    ))
    console.print()
    
    try:
        # Load library
        library = load_unit_library(library_dir)
        
        # Get filter rules
        rules = get_filter_rules(level)
        
        # Create filter engine
        engine = ExportFilterEngine(rules)
        
        # Apply filters
        console.print("[cyan]Running filters...[/cyan]")
        
        # Get statistics
        stats = engine.get_filter_statistics(library)
        
        # Get exportable subset
        filtered_library = engine.get_exportable_subset(library)
        
        # Export filtered library
        if output_dir != library_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Re-export with new filter level
        exporter = UnitLibraryExporter()
        filter_enum = filter_level_from_string(level)
        config = ExportConfig(
            output_dir=output_dir,
            filter_level=filter_enum,
            source_pdf_id=library.source_pdf_id,
        )
        
        exporter.export(filtered_library, config)
        
        # Display results
        console.print()
        console.print("[bold]Filter Results:[/bold]")
        
        result_table = Table(show_header=False, box=None)
        result_table.add_column("Metric", style="cyan")
        result_table.add_column("Value", style="white")
        
        original_count = stats.get("total_units", 0)
        filtered_count = len(filtered_library.instructional_units)
        
        result_table.add_row("Original Units", str(original_count))
        result_table.add_row("Filtered Units", str(filtered_count))
        result_table.add_row("Removed", str(original_count - filtered_count))
        result_table.add_row("Pass Rate", f"{(filtered_count / original_count * 100):.1f}%" if original_count > 0 else "N/A")
        
        console.print(result_table)
        console.print()
        
        # Show top violations if any
        top_violations = stats.get("top_violations", [])
        if top_violations:
            console.print("[bold]Top Filter Violations:[/bold]")
            for v in top_violations[:5]:
                console.print(f"  • {v['rule']}: {v['count']} units")
            console.print()
        
        console.print(f"[green]✅ Filtered library exported to:[/green] {output_dir}/")
        
    except FileNotFoundError as e:
        console.print(f"[red]❌ Error: Could not load library:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Filter operation failed:[/red] {e}")
        import traceback
        console.print(traceback.format_exc())
        raise typer.Exit(1)


# =============================================================================
# EXPORT-LEGACY COMMAND
# =============================================================================

@app.command(name="export-legacy")
def export_legacy_command(
    concept_map_path: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="Path to old concept-map.json file",
    ),
    output_dir: Path = typer.Option(
        ...,
        "--output-dir", "-o",
        help="Output directory for new format (required)",
    ),
    filter_level: str = FilterLevelCLI,
):
    """
    Convert old concept-map.json to new unit library format.
    
    Transforms the legacy concept map structure into the new grounded
    instructional unit graph format.
    
    Example:
        algl-pdf export-legacy ./old-output/concept-map.json --output-dir ./new-output/
        algl-pdf export-legacy ./old/concept-map.json -o ./new/ --filter-level strict
    """
    if not HAS_EXPORTER:
        console.print("[red]❌ Error: Unit library exporter not available[/red]")
        raise typer.Exit(1)
    
    console.print(Panel(
        f"[bold]Legacy Format Conversion[/bold]\n"
        f"Input: {concept_map_path}\n"
        f"Output: {output_dir}/\n"
        f"Filter Level: {filter_level}",
        title="🔄 Export Legacy",
        border_style="blue"
    ))
    console.print()
    
    try:
        # Load old concept map
        console.print("[cyan]Loading legacy concept map...[/cyan]")
        with open(concept_map_path, "r", encoding="utf-8") as f:
            old_concept_map = json.load(f)
        
        concept_count = len(old_concept_map.get("concepts", {}))
        console.print(f"  Found {concept_count} concepts in legacy format")
        
        # Convert to new format
        console.print("[cyan]Converting to new format...[/cyan]")
        library = convert_legacy_concept_map(old_concept_map)
        
        console.print(f"  Generated {len(library.instructional_units)} instructional units")
        console.print(f"  Source PDF: {library.source_pdf_id}")
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Export in new format
        console.print("[cyan]Exporting to new format...[/cyan]")
        
        exporter = UnitLibraryExporter()
        filter_enum = filter_level_from_string(filter_level)
        config = ExportConfig(
            output_dir=output_dir,
            filter_level=filter_enum,
            source_pdf_id=library.source_pdf_id,
        )
        
        result_path = exporter.export(library, config)
        
        # Display results
        console.print()
        console.print("[bold]Conversion Results:[/bold]")
        
        result_table = Table(show_header=False, box=None)
        result_table.add_column("Metric", style="cyan")
        result_table.add_column("Value", style="white")
        
        result_table.add_row("Original Concepts", str(concept_count))
        result_table.add_row("Instructional Units", str(len(library.instructional_units)))
        result_table.add_row("Misconceptions", str(len(library.misconception_bank)))
        result_table.add_row("Reinforcement Items", str(len(library.reinforcement_bank)))
        result_table.add_row("Output Directory", str(result_path))
        
        console.print(result_table)
        console.print()
        console.print("[green]✅ Conversion complete![/green]")
        console.print()
        console.print("[dim]New format files created:[/dim]")
        console.print("  • concept_ontology.json")
        console.print("  • concept_graph.json")
        console.print("  • source_spans.jsonl")
        console.print("  • instructional_units.jsonl")
        console.print("  • misconception_bank.jsonl")
        console.print("  • reinforcement_bank.jsonl")
        console.print("  • export_manifest.json")
        
    except FileNotFoundError as e:
        console.print(f"[red]❌ Error: Could not load concept map:[/red] {e}")
        raise typer.Exit(1)
    except json.JSONDecodeError as e:
        console.print(f"[red]❌ Error: Invalid JSON in concept map:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Conversion failed:[/red] {e}")
        import traceback
        console.print(traceback.format_exc())
        raise typer.Exit(1)


# =============================================================================
# STANDALONE ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    app()
