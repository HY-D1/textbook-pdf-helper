from __future__ import annotations

import warnings
from pathlib import Path

import typer

from .extract import check_extraction_quality, extract_pages_fitz
from .indexer import build_index
from .models import IndexBuildOptions

app = typer.Typer(add_completion=False)


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
