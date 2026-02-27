"""
CLI commands for educational note generation.

This module provides CLI commands for the educational pipeline.
"""

from __future__ import annotations

from pathlib import Path

import typer
from tqdm import tqdm

from .educational_pipeline import EducationalNoteGenerator, LLMProvider
from .concept_mapper import load_concepts_config, find_concepts_config

app = typer.Typer(help="Generate educational notes from PDFs")


def create_progress_bar():
    """Create a progress bar callback."""
    current_bar = None
    current_step = None
    
    def progress_callback(step: str, current: int, total: int, message: str = ""):
        nonlocal current_bar, current_step
        
        # Close previous bar if step changed
        if step != current_step and current_bar is not None:
            current_bar.close()
            current_bar = None
        
        # Create new bar for new step
        if current_bar is None or step != current_step:
            current_step = step
            step_names = {
                "extract": "📄 PDF Extraction",
                "structure": "🔍 Content Analysis", 
                "enhance": "🎓 Generating Educational Notes",
                "format": "📋 Formatting Output",
                "save": "💾 Saving Files",
            }
            bar_format = "{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}] {postfix}"
            current_bar = tqdm(
                total=total,
                desc=step_names.get(step, step),
                bar_format=bar_format,
                ncols=80,
            )
        
        # Update progress
        current_bar.n = current
        if message:
            current_bar.set_postfix_str(message[:50])
        current_bar.refresh()
        
        # Close if complete
        if current >= total:
            current_bar.close()
            current_bar = None
    
    return progress_callback


@app.command()
def generate(
    pdf_path: Path = typer.Argument(..., exists=True, help="Path to PDF file"),
    output_dir: Path = typer.Option(
        Path("educational_output"),
        help="Output directory for generated notes",
    ),
    use_marker: bool = typer.Option(
        True,
        help="Use Marker for extraction (best quality, requires GPU/CPU)",
    ),
    use_llm: bool = typer.Option(
        True,
        help="Use LLM to enhance notes (requires API key)",
    ),
    llm_provider: str = typer.Option(
        "openai",
        help="LLM provider: openai or kimi",
    ),
    estimate_cost: bool = typer.Option(
        False,
        help="Show cost estimate only (don't generate)",
    ),
):
    """Generate educational notes from PDF."""
    
    # Show cost estimate first
    if estimate_cost or not use_llm:
        import os
        generator = EducationalNoteGenerator(
            llm_provider=llm_provider,
            kimi_api_key=os.getenv("KIMI_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )
        cost = generator.estimate_cost(num_concepts=30)  # Estimate for 30 concepts
        
        typer.echo("\n💰 Cost Estimate")
        typer.echo("=" * 50)
        typer.echo(f"Provider: {cost['provider']}")
        typer.echo(f"Model: {cost['model']}")
        typer.echo(f"Concepts: {cost['concepts']}")
        typer.echo(f"\nTokens:")
        typer.echo(f"  Input:  {cost['tokens']['input']:,}")
        typer.echo(f"  Output: {cost['tokens']['output']:,}")
        typer.echo(f"\nEstimated Cost (RMB):")
        typer.echo(f"  Input:  ¥{cost['cost_rmb']['input']}")
        typer.echo(f"  Output: ¥{cost['cost_rmb']['output']}")
        typer.echo(f"  Total:  ¥{cost['cost_rmb']['total']}")
        typer.echo(f"\nPer concept: ¥{cost['cost_per_concept_rmb']}")
        
        if estimate_cost:
            typer.echo("\n" + "=" * 50)
            EducationalNoteGenerator.print_cost_comparison()
            return
        
        typer.echo("")
        confirm = typer.prompt("Continue with generation? [y/n]", default="y")
        if confirm.lower() != "y":
            typer.echo("Cancelled.")
            raise typer.Exit(0)
        typer.echo("")
    
    typer.echo(f"📚 Processing: {pdf_path}")
    typer.echo(f"📁 Output: {output_dir}")
    typer.echo(f"🤖 LLM Provider: {llm_provider}")
    typer.echo()
    
    # Load concepts configuration
    concepts_config_path = find_concepts_config(pdf_path)
    concepts_config = None
    if concepts_config_path and concepts_config_path.exists():
        try:
            concepts_config = load_concepts_config(concepts_config_path, pdf_path)
            total_concepts = len(concepts_config.get("concepts", {}))
            matched_textbook = concepts_config.get("matched_textbook", "")
            typer.echo(f"📖 Loaded concepts config: {concepts_config_path}")
            if matched_textbook:
                typer.echo(f"   Matched textbook: {matched_textbook}")
            typer.echo(f"   Found {total_concepts} concepts defined")
        except Exception as e:
            typer.echo(f"⚠️  Warning: Failed to load concepts config: {e}")
    else:
        typer.echo(f"⚠️  No concepts.yaml found - will auto-detect topics")
    typer.echo()
    
    # Initialize generator
    import os
    generator = EducationalNoteGenerator(
        use_marker=use_marker,
        llm_provider=llm_provider,
        kimi_api_key=os.getenv("KIMI_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )
    
    if use_llm and not generator.llm_available:
        typer.echo("⚠️  Warning: LLM not available")
        if llm_provider == LLMProvider.KIMI:
            typer.echo("   Set KIMI_API_KEY or MOONSHOT_API_KEY environment variable")
            typer.echo("   Get key: https://platform.moonshot.cn/")
        else:
            typer.echo("   Set OPENAI_API_KEY environment variable")
        typer.echo("   Will generate basic notes without LLM enhancement")
        typer.echo()
    
    # Create progress callback
    progress_cb = create_progress_bar()
    
    # Process PDF with progress
    try:
        result = generator.process_pdf(
            pdf_path, 
            concepts_config=concepts_config,
            output_dir=output_dir,
            progress_callback=progress_cb,
        )
    finally:
        # Ensure progress bar is closed
        typer.echo()
    
    # Display results
    if result["success"]:
        typer.echo("✅ Success!")
        typer.echo()
        typer.echo("📊 Stats:")
        for key, value in result["stats"].items():
            typer.echo(f"   {key}: {value}")
        
        typer.echo()
        typer.echo("📄 Generated files:")
        for key, path in result["outputs"].items():
            typer.echo(f"   {key}: {path}")
        
        # Show cost if LLM was used
        if result["stats"].get("llm_enhanced"):
            num_concepts = result["stats"].get("concepts_generated", 0)
            if num_concepts > 0:
                cost = generator.estimate_cost(num_concepts)
                typer.echo()
                typer.echo(f"💰 Actual Cost: ¥{cost['cost_rmb']['total']} RMB")
        
        # Show preview
        if "study_guide" in result["outputs"]:
            typer.echo()
            typer.echo("📖 Study guide preview:")
            study_guide_path = Path(result["outputs"]["study_guide"])
            if study_guide_path.exists():
                content = study_guide_path.read_text()
                lines = content.split("\n")[:30]
                for line in lines:
                    typer.echo(line)
                if len(content.split("\n")) > 30:
                    typer.echo("...")
    else:
        typer.echo("❌ Errors occurred:")
        for error in result["errors"]:
            typer.echo(f"   - {error}")
        
        if result["outputs"]:
            typer.echo()
            typer.echo("⚠️  Partial outputs were generated:")
            for key, path in result["outputs"].items():
                typer.echo(f"   {key}: {path}")
        
        raise typer.Exit(1)


@app.command()
def status():
    """Check status of dependencies."""
    from .educational_pipeline import MARKER_AVAILABLE, OPENAI_AVAILABLE
    
    typer.echo("📋 Dependency Status")
    typer.echo("=" * 40)
    
    # Check Marker
    if MARKER_AVAILABLE:
        typer.echo("✅ Marker (PDF extraction): Available")
    else:
        typer.echo("❌ Marker (PDF extraction): Not installed")
        typer.echo("   Install: pip install marker-pdf")
    
    # Check OpenAI
    if OPENAI_AVAILABLE:
        typer.echo("✅ OpenAI SDK: Available")
        
        import os
        if os.getenv("OPENAI_API_KEY"):
            typer.echo("✅ OPENAI_API_KEY: Set")
        else:
            typer.echo("⚠️  OPENAI_API_KEY: Not set")
    else:
        typer.echo("❌ OpenAI SDK: Not installed")
        typer.echo("   Install: pip install openai")
    
    # Check Kimi
    import os
    if os.getenv("KIMI_API_KEY") or os.getenv("MOONSHOT_API_KEY"):
        typer.echo("✅ KIMI_API_KEY/MOONSHOT_API_KEY: Set")
    else:
        typer.echo("⚠️  KIMI_API_KEY/MOONSHOT_API_KEY: Not set")
        typer.echo("   Get key: https://platform.moonshot.cn/")
    
    typer.echo()
    typer.echo("💡 Recommendation:")
    if not MARKER_AVAILABLE:
        typer.echo("   Install all dependencies for best results:")
        typer.echo("   pip install marker-pdf openai")
    else:
        typer.echo("   For cheapest costs, use Kimi:")
        typer.echo("   export KIMI_API_KEY='your-key'")
        typer.echo("   algl-pdf edu generate book.pdf --llm-provider kimi")


@app.command()
def cost():
    """Show cost comparison between LLM providers."""
    EducationalNoteGenerator.print_cost_comparison()


if __name__ == "__main__":
    app()
