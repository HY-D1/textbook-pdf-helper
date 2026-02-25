from __future__ import annotations

from pathlib import Path

import typer

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
    )
    typer.echo(f"Wrote PDF index to: {out}")
    typer.echo(f"Index ID: {doc.indexId}")
    typer.echo(f"Docs: {doc.docCount}  Chunks: {doc.chunkCount}")


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
