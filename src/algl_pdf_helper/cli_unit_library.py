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
    from .export_filters import ExportFilterEngine, STRICT_FILTERS, PRODUCTION_FILTERS, DEVELOPMENT_FILTERS
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
__all__ = ["process_command", "validate_command", "inspect_command", "filter_command", "export_legacy_command"]

# Filter level enum for CLI
FilterLevelCLI = typer.Option(
    "strict",
    help="Export filter level: strict (production-ready), production (validated), development (all content)"
)

LLMProviderCLI = typer.Option(
    "kimi",
    help="LLM provider: kimi, openai, or ollama"
)


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

@app.command()
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
    llm_model: str = typer.Option(
        "kimi-k2-5",
        "--llm-model",
        help="LLM model to use",
    ),
    filter_level: str = FilterLevelCLI,
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
    min_quality_score: float = typer.Option(
        0.8,
        "--min-quality-score",
        min=0.0,
        max=1.0,
        help="Minimum quality score threshold",
    ),
):
    """
    Process a PDF into a unit library.
    
    This command extracts content from a PDF, maps concepts, generates
    instructional units at all adaptive stages (L1-L4), and exports
    the grounded instructional unit graph.
    
    Example:
        algl-pdf process ./textbook.pdf --output-dir ./output
        algl-pdf process ./textbook.pdf -o ./output --filter-level production
        algl-pdf process ./textbook.pdf -o ./output --skip-reinforcement
    """
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
    
    # Show header panel
    console.print(Panel(
        f"[bold]ALGL PDF Helper - Unit Library Generation[/bold]\n"
        f"PDF: {pdf_path.name}\n"
        f"Output: {output_dir}/\n"
        f"Doc ID: {doc_id}\n"
        f"Filter Level: {filter_level}",
        title="📚 Unit Library Pipeline",
        border_style="blue"
    ))
    console.print()
    
    # Create pipeline configuration from CLI arguments
    config = PipelineConfig(
        pdf_path=pdf_path,
        output_dir=output_dir,
        doc_id=doc_id,
        llm_provider=llm_provider,  # type: ignore
        llm_model=llm_model,
        filter_level=filter_level_to_literal(filter_level),  # type: ignore
        skip_reinforcement=skip_reinforcement,
        skip_misconceptions=skip_misconceptions,
        validate_sql=validate_sql,
        min_quality_score=min_quality_score,
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
    
    total_units = stats.get("instructional_units", 0)
    misconception_units = stats.get("misconception_units", 0)
    reinforcement_items = stats.get("reinforcement_items", 0)
    concepts_mapped = stats.get("concepts_mapped", 0)
    teaching_blocks = stats.get("teaching_blocks", 0)
    
    stats_table.add_row("Total Units", str(total_units))
    stats_table.add_row("Misconception Units", str(misconception_units))
    stats_table.add_row("Reinforcement Items", str(reinforcement_items))
    stats_table.add_row("Concepts Covered", str(concepts_mapped))
    stats_table.add_row("Teaching Blocks", str(teaching_blocks))
    
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
    console.print()
    console.print(f"[green]✅ Unit library exported to:[/green] {output_dir}/")
    
    # List generated files
    if result.output_path:
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
            file_path = result.output_path / filename
            if file_path.exists():
                size = file_path.stat().st_size
                console.print(f"  [green]✓[/green] {filename} ({size:,} bytes)")
            else:
                console.print(f"  [yellow]○[/yellow] {filename} (not found)")


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


def _create_manifest(
    doc_id: str,
    stats: dict[str, Any],
    filter_level: str,
    llm_provider: str,
    llm_model: str,
) -> dict[str, Any]:
    """Create export manifest."""
    return {
        "export_version": "2.0.0-unit-library",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_pdf_id": doc_id,
        "statistics": {
            "total_units": stats["units_generated"],
            "exported_units": stats["exported"],
            "filtered_units": stats["filtered"],
            "concepts_covered": stats["concepts"],
            "misconception_units": stats["misconceptions"],
            "reinforcement_items": stats["reinforcement"],
        },
        "configuration": {
            "filter_level": filter_level,
            "llm_provider": llm_provider,
            "llm_model": llm_model,
        },
        "files": {
            "manifest": "export_manifest.json",
            "concept_ontology": "concept_ontology.json",
            "concept_graph": "concept_graph.json",
            "source_spans": "source_spans.jsonl",
            "instructional_units": "instructional_units.jsonl",
            "misconception_bank": "misconception_bank.jsonl",
            "reinforcement_bank": "reinforcement_bank.jsonl",
        }
    }


# =============================================================================
# VALIDATE COMMAND
# =============================================================================

@app.command()
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
):
    """
    Validate an existing unit library.
    
    Runs all quality gates on the unit library and displays a quality report.
    
    Example:
        algl-pdf validate ./output/unit-library/
        algl-pdf validate ./output/unit-library/ --detailed
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
        
        # Load full library
        library = load_unit_library(library_dir)
        
        # Display summary
        stats = manifest.get("statistics", {})
        
        console.print("[bold]Library Summary:[/bold]")
        summary_table = Table(show_header=False, box=None)
        summary_table.add_column("Field", style="cyan")
        summary_table.add_column("Value", style="white")
        
        summary_table.add_row("Total Units", str(stats.get("total_units", 0)))
        summary_table.add_row("Exported Units", str(stats.get("exported_units", 0)))
        summary_table.add_row("Filtered Units", str(stats.get("filtered_units", 0)))
        summary_table.add_row("Concepts Covered", str(stats.get("concepts_covered", 0)))
        summary_table.add_row("Misconceptions", str(stats.get("misconception_units", 0)))
        summary_table.add_row("Reinforcement Items", str(stats.get("reinforcement_items", 0)))
        
        console.print(summary_table)
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
            
            gates = LearningQualityGates()
            report_generator = QualityReport(gates)
            quality_report = report_generator.generate_full_report(library)
            
            summary = quality_report.get("summary", {})
            total_units = summary.get("total_units", 0)
            passed_units = summary.get("passed_units", 0)
            failed_units = summary.get("failed_units", 0)
            pass_rate = summary.get("overall_pass_rate", 0)
            overall_passed = summary.get("overall_passed", False)
            
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
        
        # Overall result
        if all_passed:
            console.print("[bold green]✅ Validation PASSED[/bold green]")
            console.print("   All quality gates passed. Library is ready for deployment.")
            raise typer.Exit(0)
        else:
            console.print("[bold red]❌ Validation FAILED[/bold red]")
            console.print("   Some quality checks failed. Review issues above.")
            raise typer.Exit(1)
            
    except FileNotFoundError as e:
        console.print(f"[red]❌ Error: Could not load library:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Validation failed:[/red] {e}")
        import traceback
        console.print(traceback.format_exc())
        raise typer.Exit(1)


# =============================================================================
# INSPECT COMMAND
# =============================================================================

@app.command()
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
        
        # Group by stage
        stages = {"L1": [], "L2": [], "L3": [], "L4": [], "reinforcement": []}
        for unit in units:
            stage = getattr(unit, "stage", "unknown")
            if stage in stages:
                stages[stage].append(unit)
        
        # Display each stage
        for stage_name, stage_units in stages.items():
            if not stage_units:
                continue
            
            console.print(f"[bold cyan]{stage_name.upper()} Stage:[/bold cyan]")
            
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
                    if stage_name == "L1":
                        hint = content.get("hint_text", "") if isinstance(content, dict) else ""
                        if hint:
                            console.print(f"    Hint: {hint[:100]}...")
                    
                    elif stage_name == "L2":
                        explanation = content.get("example_explanation", "") if isinstance(content, dict) else ""
                        if explanation:
                            console.print(f"    Explanation: {explanation[:100]}...")
                        
                        if show_sql:
                            sql = content.get("example_sql", "") if isinstance(content, dict) else ""
                            if sql:
                                console.print("    SQL:")
                                console.print(Syntax(sql, "sql", theme="monokai", line_numbers=False))
                    
                    elif stage_name == "L3":
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
                    
                    elif stage_name == "L4":
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
# FILTER COMMAND
# =============================================================================

@app.command()
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
