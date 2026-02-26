"""
CLI commands for educational note generation.

This module provides CLI commands for the educational pipeline.
"""

from __future__ import annotations

from pathlib import Path

import typer

from .educational_pipeline import EducationalNoteGenerator

app = typer.Typer(help="Generate educational notes from PDFs")


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
        help="Use LLM to enhance notes (requires OPENAI_API_KEY)",
    ),
):
    """Generate educational notes from PDF."""
    typer.echo(f"📚 Processing: {pdf_path}")
    typer.echo(f"📁 Output: {output_dir}")
    typer.echo()
    
    # Initialize generator
    generator = EducationalNoteGenerator(
        use_marker=use_marker,
    )
    
    if use_llm and not generator.llm_available:
        typer.echo("⚠️  Warning: LLM not available (set OPENAI_API_KEY)")
        typer.echo("   Will generate basic notes without LLM enhancement")
        typer.echo()
    
    # Process PDF
    result = generator.process_pdf(pdf_path, output_dir=output_dir)
    
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
        typer.echo("✅ OpenAI (LLM enhancement): Available")
        
        import os
        if os.getenv("OPENAI_API_KEY"):
            typer.echo("✅ OPENAI_API_KEY: Set")
        else:
            typer.echo("⚠️  OPENAI_API_KEY: Not set")
            typer.echo("   Set with: export OPENAI_API_KEY='your-key'")
    else:
        typer.echo("❌ OpenAI (LLM enhancement): Not installed")
        typer.echo("   Install: pip install openai")
    
    typer.echo()
    typer.echo("💡 Recommendation:")
    if not MARKER_AVAILABLE or not OPENAI_AVAILABLE:
        typer.echo("   Install all dependencies for best results:")
        typer.echo("   pip install marker-pdf openai")
    else:
        typer.echo("   All dependencies ready! Use 'generate' command.")


if __name__ == "__main__":
    app()
