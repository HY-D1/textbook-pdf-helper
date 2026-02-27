from __future__ import annotations

import os
import warnings
from pathlib import Path

import typer

from .export_sqladapt import DEFAULT_OUTPUT_DIR, export_to_sqladapt
from .extract import check_extraction_quality, extract_pages_fitz
from .indexer import build_index
from .models import IndexBuildOptions

app = typer.Typer(add_completion=False)

# Import educational CLI
from .cli_educational import app as educational_app
app.add_typer(educational_app, name="edu", help="Educational note generation")


@app.command()
def index(
    input_path: Path = typer.Argument(..., exists=True, help="PDF file or directory"),
    out: Path = typer.Option(Path("./out/pdf-index"), help="Output directory"),
    ocr: bool = typer.Option(False, help="Force OCR (requires ocrmypdf)"),
    auto_ocr: bool = typer.Option(True, help="Auto OCR when little/no text is found"),
    use_aliases: bool = typer.Option(
        False,
        help="Use stable doc aliases (e.g. sql-textbook) instead of doc-<sha>",
    ),
    chunk_words: int = typer.Option(180, help="Words per chunk"),
    overlap_words: int = typer.Option(30, help="Overlapping words"),
    embedding_dim: int = typer.Option(24, help="Hash embedding dimension"),
    strip_headers: bool = typer.Option(True, help="Heuristically strip headers/footers"),
    concepts_config: Path | None = typer.Option(
        None,
        help="Path to concepts.yaml config (auto-detected if not specified)",
    ),
):
    opts = IndexBuildOptions(
        chunkWords=chunk_words,
        overlapWords=overlap_words,
        embeddingDim=embedding_dim,
    )
    doc = build_index(
        input_path,
        out,
        options=opts,
        ocr=ocr,
        auto_ocr=auto_ocr,
        use_aliases=use_aliases,
        strip_headers=strip_headers,
        concepts_config=concepts_config,
    )
    typer.echo(f"Wrote PDF index to: {out}")
    typer.echo(f"Index ID: {doc.indexId}")
    typer.echo(f"Docs: {doc.docCount}  Chunks: {doc.chunkCount}")
    
    # Check if concept files were generated
    concept_manifest_path = out / "concept-manifest.json"
    if concept_manifest_path.exists():
        import json
        manifest = json.loads(concept_manifest_path.read_text())
        typer.echo(f"Concepts: {manifest.get('conceptCount', 0)}  (concept-manifest.json)")
        concepts_dir = out / "concepts"
        if concepts_dir.exists():
            typer.echo(f"Concept markdowns: {concepts_dir}")


@app.command()
def check_quality(
    pdf_path: Path = typer.Argument(..., exists=True, help="PDF file to check"),
):
    """Check text extraction quality of a PDF without processing."""
    typer.echo(f"Checking quality of: {pdf_path.name}")
    typer.echo("")
    
    pages = extract_pages_fitz(pdf_path)
    quality = check_extraction_quality(pages)
    
    typer.echo(f"Pages with text: {quality['page_count']}")
    typer.echo(f"Total characters: {quality['total_chars']:,}")
    typer.echo(f"Readable ratio: {quality['readable_ratio']:.1%}")
    typer.echo(f"Gibberish ratio: {quality['gibberish_ratio']:.1%}")
    typer.echo("")
    
    if quality['is_quality_good']:
        typer.echo("✅ Quality is GOOD - no OCR needed")
    else:
        typer.echo(f"⚠️  Quality is POOR - OCR recommended")
        if quality['reason']:
            typer.echo(f"   Reason: {quality['reason']}")


@app.command()
def export(
    input_dir: Path = typer.Argument(..., exists=True, help="Input directory with processed PDF (contains concept-manifest.json)"),
    output_dir: Path = typer.Option(DEFAULT_OUTPUT_DIR, help="Output directory for SQL-Adapt files"),
    merge: bool = typer.Option(True, help="Merge with existing exports instead of overwriting"),
):
    """Export processed PDF to SQL-Adapt compatible format."""
    typer.echo(f"Exporting from: {input_dir}")
    typer.echo(f"Output to: {output_dir}")
    typer.echo(f"Mode: {'Merge' if merge else 'Overwrite'}")
    typer.echo("")
    
    try:
        result = export_to_sqladapt(input_dir, output_dir, merge=merge)
        
        if result.get('is_new_pdf'):
            typer.echo(f"✅ Added new PDF: {result['source_doc_id']}")
        else:
            typer.echo(f"✅ Updated PDF: {result['source_doc_id']}")
        
        typer.echo(f"   Concepts from this PDF: {result['concept_count']}")
        typer.echo(f"   Total concepts in export: {result['total_concepts']}")
        
        if result.get('generated_files'):
            typer.echo(f"   New files: {len(result['generated_files'])}")
        if result.get('updated_files'):
            typer.echo(f"   Updated files: {len(result['updated_files'])}")
            
        typer.echo(f"   Concept map: {result['concept_map']}")
        typer.echo(f"   Concepts directory: {result['concepts_dir']}")
        
    except FileNotFoundError as e:
        typer.echo(f"❌ Error: {e}")
        typer.echo("")
        typer.echo("Make sure the input directory contains:")
        typer.echo("  - concept-manifest.json")
        typer.echo("  - chunks.json")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Export failed: {e}")
        raise typer.Exit(1)


@app.command()
def export_edu(
    pdf_path: Path = typer.Argument(..., exists=True, help="Path to PDF file"),
    output_dir: Path = typer.Option(DEFAULT_OUTPUT_DIR, help="Output directory for SQL-Adapt files"),
    llm_provider: str = typer.Option("kimi", help="LLM provider: openai, kimi, or ollama"),
    use_marker: bool = typer.Option(
        True, 
        "--use-marker/--no-use-marker",
        help="Use Marker for PDF extraction (disable for large PDFs to save memory)",
    ),
    ollama_model: str = typer.Option(
        "llama3.2:3b",
        help="Ollama model to use (for local LLM): llama3.2:3b, qwen2.5:7b, phi4, mistral:7b, gemma2:9b",
    ),
    skip_llm: bool = typer.Option(
        False,
        "--skip-llm",
        help="Skip LLM enhancement (faster but lower quality output)",
    ),
    concepts_config: Path | None = typer.Option(
        None,
        "--concepts-config",
        help="Path to concepts.yaml config file (auto-detected if not specified)",
    ),
    max_concepts: int | None = typer.Option(
        None,
        "--max-concepts",
        help="Limit number of concepts to process (for testing)",
    ),
):
    """Export PDF to SQL-Adapt with educational note generation."""
    from .educational_pipeline import EducationalNoteGenerator
    from .concept_mapper import load_concepts_config, find_concepts_config
    from tqdm import tqdm
    
    typer.echo(f"📚 Generating educational notes from: {pdf_path}")
    typer.echo(f"📁 Exporting to: {output_dir}")
    typer.echo(f"🤖 LLM Provider: {llm_provider}")
    if llm_provider.lower() == "ollama":
        typer.echo(f"🦙 Ollama Model: {ollama_model}")
    typer.echo()
    
    # Check file size for info
    pdf_size_mb = pdf_path.stat().st_size / (1024 * 1024)
    
    if pdf_size_mb > 50:
        typer.echo(f"ℹ️  Large PDF detected ({pdf_size_mb:.1f}MB)")
        typer.echo(f"   Auto-split will be used if needed.")
        typer.echo()
    
    # Load concepts configuration
    concepts_config_path = concepts_config  # Use the renamed parameter
    if concepts_config_path is None:
        concepts_config_path = find_concepts_config(pdf_path)
        typer.echo(f"🔍 Looking for concepts config...")
        typer.echo(f"   Path found: {concepts_config_path}")
    else:
        typer.echo(f"🔍 Using specified concepts config: {concepts_config_path}")
    
    concepts_config_data = None
    if concepts_config_path:
        typer.echo(f"   Path exists: {concepts_config_path.exists()}")
        if concepts_config_path.exists():
            try:
                concepts_config_data = load_concepts_config(concepts_config_path, pdf_path)
                total_concepts = len(concepts_config_data.get("concepts", {}))
                matched_textbook = concepts_config_data.get("matched_textbook", "")
                typer.echo(f"📖 Loaded concepts config: {concepts_config_path}")
                if matched_textbook:
                    typer.echo(f"   Matched textbook: {matched_textbook}")
                typer.echo(f"   Found {total_concepts} concepts defined")
            except Exception as e:
                typer.echo(f"⚠️  Warning: Failed to load concepts config: {e}")
                import traceback
                typer.echo(traceback.format_exc())
        else:
            typer.echo(f"⚠️  Config file not found at {concepts_config_path}")
    else:
        typer.echo(f"⚠️  No concepts.yaml found - will auto-detect topics")
    typer.echo()
    
    # Initialize generator with API keys from environment
    import os
    generator = EducationalNoteGenerator(
        llm_provider=llm_provider, 
        use_marker=use_marker,
        ollama_model=ollama_model,
        skip_llm=skip_llm,
        kimi_api_key=os.getenv("KIMI_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )
    
    typer.echo(f"Configuration:")
    typer.echo(f"  Marker extraction: {generator.use_marker}")
    
    if skip_llm:
        typer.echo(f"  LLM enhancement: ⏭️  SKIPPED (fast mode)")
        typer.echo(f"   ⚠️  Output will be basic text extraction only!")
    else:
        typer.echo(f"  LLM enhancement: {generator.llm_status_message}")
        
        if not generator.llm_available:
            typer.echo()
            typer.echo("❌ ERROR: No LLM configured!")
            typer.echo("   For high-quality educational notes, you MUST configure an LLM:")
            typer.echo("   - Kimi: export KIMI_API_KEY='your-key'")
            typer.echo("   - OpenAI: export OPENAI_API_KEY='your-key'")
            typer.echo("   - Ollama: ollama pull qwen2.5-coder:7b && ollama serve")
            typer.echo()
            typer.echo("   Or use --skip-llm for basic extraction (NOT recommended)")
            raise typer.Exit(1)
    typer.echo()
    
    # Create progress callback
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
            current_bar = tqdm(
                total=total,
                desc=step_names.get(step, step),
                bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}] {postfix}",
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
    
    # Generate educational notes with progress
    try:
        result = generator.process_pdf(
            pdf_path, 
            concepts_config=concepts_config_data,
            output_dir=output_dir,
            progress_callback=progress_callback,
            max_concepts=max_concepts,
        )
    finally:
        if current_bar is not None:
            current_bar.close()
        typer.echo()
    
    if not result["success"]:
        typer.echo("❌ Educational note generation failed:")
        for error in result["errors"]:
            typer.echo(f"   - {error}")
        raise typer.Exit(1)
    
    typer.echo("✅ Educational notes generated!")
    typer.echo()
    typer.echo("📊 Stats:")
    for key, value in result["stats"].items():
        typer.echo(f"   {key}: {value}")
    
    # Show cost if LLM was used
    if result["stats"].get("llm_enhanced"):
        num_concepts = result["stats"].get("concepts_generated", 0)
        typer.echo()
        if hasattr(generator, 'estimate_cost') and num_concepts > 0:
            cost = generator.estimate_cost(num_concepts)
            typer.echo(f"💰 Actual Cost: ¥{cost['cost_rmb']['total']} RMB")
        else:
            typer.echo(f"💰 Concepts processed with LLM: {num_concepts}")
    
    # Show generated files
    typer.echo()
    typer.echo("📁 Generated files:")
    
    # Get doc_id from result
    doc_id = result["stats"].get("doc_id", "unknown")
    
    # Standard SQL-Adapt format outputs (REQUIRED)
    if (output_dir / "concept-map.json").exists():
        typer.echo(f"   📋 concept-map.json (main index)")
    
    # Check for concepts in textbook subdirectory
    concepts_subdir = output_dir / "concepts" / doc_id
    if concepts_subdir.exists():
        concept_count = len(list(concepts_subdir.glob("*.md")))
        typer.echo(f"   📚 concepts/{doc_id}/ ({concept_count} concept files)")
        typer.echo(f"   📖 concepts/{doc_id}/README.md")
    
    # Diagnostic/Internal files
    if (output_dir / "concept-manifest.json").exists():
        typer.echo(f"   🔧 concept-manifest.json (internal)")
    if result["outputs"].get("extraction"):
        typer.echo(f"   🔍 {doc_id}-extraction.json (diagnostic)")
    if result["outputs"].get("sqladapt"):
        typer.echo(f"   📄 {doc_id}-sqladapt.json (diagnostic)")
    if result["outputs"].get("study_guide"):
        typer.echo(f"   📖 {doc_id}-study-guide.md (combined)")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(7345),
):
    """Run the optional HTTP service."""
    try:
        import uvicorn  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Server extras not installed. Install with: pip install -e '.[server]'"
        ) from e

    from .server import api

    uvicorn.run(api, host=host, port=port)
