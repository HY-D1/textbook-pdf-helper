from __future__ import annotations

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
):
    """Export PDF to SQL-Adapt with educational note generation."""
    from .educational_pipeline import EducationalNoteGenerator
    
    typer.echo(f"📚 Generating educational notes from: {pdf_path}")
    typer.echo(f"📁 Exporting to: {output_dir}")
    typer.echo()
    
    # Initialize generator
    generator = EducationalNoteGenerator()
    
    typer.echo(f"Configuration:")
    typer.echo(f"  Marker extraction: {generator.use_marker}")
    typer.echo(f"  LLM enhancement: {generator.llm_available}")
    typer.echo()
    
    # Create temp output for educational pipeline
    temp_output = output_dir / "_temp_edu"
    temp_output.mkdir(parents=True, exist_ok=True)
    
    # Generate educational notes
    result = generator.process_pdf(pdf_path, output_dir=temp_output)
    
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
    
    # Now export to SQL-Adapt format
    sqladapt_file = temp_output / f"{result['stats'].get('doc_id', 'unknown')}-sqladapt.json"
    
    if sqladapt_file.exists():
        typer.echo()
        typer.echo(f"✅ SQL-Adapt format ready: {sqladapt_file}")
        
        # Copy to final destination
        import shutil
        final_file = output_dir / sqladapt_file.name
        shutil.copy2(sqladapt_file, final_file)
        typer.echo(f"   Copied to: {final_file}")
    
    if result["outputs"].get("study_guide"):
        typer.echo()
        typer.echo(f"📖 Study guide: {result['outputs']['study_guide']}")


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
