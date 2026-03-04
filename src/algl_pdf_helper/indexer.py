from __future__ import annotations

import hashlib
import json
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import typer

from .optimized_indexer import (
    fast_json_dump,
    fast_json_dumps,
    optimize_for_large_document,
)

from .chunker import chunk_for_learning, chunk_page_words
from .clean import (
    clean_pages_for_students,
    normalize_text,
    strip_repeated_headers_footers,
)
from .embedding import build_hash_embedding
from .extract import (
    check_extraction_quality,
    cleanup_temp_pdf,
    extract_pages_fitz,
    maybe_ocr_pdf,
    sha256_file,
)
from .concept_mapper import (
    build_concept_manifest,
    find_concepts_config,
    load_concepts_config,
    save_concept_manifest,
)
from .markdown_generator import (
    generate_all_concept_markdowns,
    generate_index_readme,
)
from .models import (
    ASSET_MANIFEST_VERSION,
    AssetManifest,
    AssetReference,
    ConceptManifest,
    IndexBuildOptions,
    PdfIndexChunk,
    PdfIndexDocument,
    PdfIndexManifest,
    PdfSourceDoc,
)


try:
    from .asset_extractor import (
        AssetExtractor,
        ExtractedAsset,
        extract_assets_from_pdf,
    )
    ASSET_EXTRACTION_AVAILABLE = True
except ImportError:
    ASSET_EXTRACTION_AVAILABLE = False
    # Type placeholder for when asset_extractor is not available
    ExtractedAsset = Any  # type: ignore


_DEFAULT_ALIASES: dict[str, str] = {
    "SQL_Course_Textbook.pdf": "sql-textbook",
    "sql-course-textbook.pdf": "sql-textbook",
}


def get_doc_alias(filename: str) -> str:
    if filename in _DEFAULT_ALIASES:
        return _DEFAULT_ALIASES[filename]

    lower = filename.lower()
    for k, v in _DEFAULT_ALIASES.items():
        if k.lower() == lower:
            return v

    base = filename
    if base.lower().endswith(".pdf"):
        base = base[:-4]

    out = []
    prev_dash = False
    for ch in base.lower():
        ok = ("a" <= ch <= "z") or ("0" <= ch <= "9")
        if ok:
            out.append(ch)
            prev_dash = False
        else:
            if not prev_dash:
                out.append("-")
                prev_dash = True

    alias = "".join(out).strip("-")
    return alias or "pdf"


def unique_doc_id(base_id: str, used: set[str]) -> str:
    if base_id not in used:
        used.add(base_id)
        return base_id
    suffix = 2
    while f"{base_id}-{suffix}" in used:
        suffix += 1
    out = f"{base_id}-{suffix}"
    used.add(out)
    return out


def discover_pdfs(input_path: Path) -> list[Path]:
    if input_path.is_file() and input_path.suffix.lower() == ".pdf":
        return [input_path]
    if not input_path.is_dir():
        return []
    pdfs = sorted([p for p in input_path.rglob("*.pdf") if p.is_file()])
    return pdfs


def extract_and_save_assets(
    pdf_path: Path,
    doc_id: str,
    out_dir: Path,
    backend: Literal["pymupdf", "marker"] = "pymupdf",
    extract_images: bool = True,
    extract_tables: bool = True,
) -> AssetManifest | None:
    """Extract and save assets from a PDF.
    
    Args:
        pdf_path: Path to the PDF file
        doc_id: Document ID for asset naming
        out_dir: Output directory for assets
        backend: Extraction backend to use
        extract_images: Whether to extract images
        extract_tables: Whether to extract tables
        
    Returns:
        AssetManifest if extraction successful, None otherwise
    """
    if not ASSET_EXTRACTION_AVAILABLE:
        return None
    
    try:
        extractor = AssetExtractor(backend=backend)
        
        images: list[ExtractedAsset] = []
        tables: list[ExtractedAsset] = []
        
        if extract_images:
            images = extractor.extract_images(pdf_path, doc_id)
        
        if extract_tables:
            tables = extractor.extract_tables(pdf_path, doc_id)
        
        # Save assets to disk
        extractor.save_assets(images, out_dir)
        extractor.save_assets(tables, out_dir)
        
        # Build provenance mapping
        provenance: dict[str, list[int]] = {}
        for asset in images + tables:
            if asset.id not in provenance:
                provenance[asset.id] = []
            if asset.page not in provenance[asset.id]:
                provenance[asset.id].append(asset.page)
        
        # Create manifest
        created_at = datetime.now(timezone.utc).isoformat()
        
        # Convert to Pydantic models for JSON serialization
        def asset_to_reference(asset) -> AssetReference:
            """Convert extracted asset to AssetReference."""
            ref = AssetReference(
                id=asset.id,
                type=asset.type,
                path=asset.get_relative_path(),
                pageNumber=asset.page,
                caption=asset.caption or "",
                extractedText=asset.metadata.get("extracted_text", ""),
            )
            # Add dimensions if available
            if hasattr(asset, 'metadata') and asset.metadata:
                if 'width' in asset.metadata:
                    ref.width = asset.metadata['width']
                if 'height' in asset.metadata:
                    ref.height = asset.metadata['height']
            return ref
        
        all_assets = []
        for a in images:
            all_assets.append(asset_to_reference(a))
        for a in tables:
            all_assets.append(asset_to_reference(a))
        
        manifest = AssetManifest(
            schemaVersion=ASSET_MANIFEST_VERSION,
            docId=doc_id,
            createdAt=created_at,
            assets=all_assets,
        )
        
        return manifest
        
    except Exception as e:
        # Log warning but don't fail the index build
        warnings.warn(f"Asset extraction failed for '{pdf_path.name}': {e}")
        return None


def save_asset_manifest(
    manifest: AssetManifest,
    out_path: Path,
) -> None:
    """Save asset manifest to JSON file.
    
    Args:
        manifest: Asset manifest to save
        out_path: Output path for JSON file
    """
    fast_json_dump(manifest.model_dump(), out_path, indent=True)


def build_index(
    input_path: Path,
    out_dir: Path,
    *,
    options: IndexBuildOptions,
    ocr: bool = False,
    auto_ocr: bool = True,
    use_aliases: bool = False,
    strip_headers: bool = True,
    concepts_config: Path | None = None,
    extract_assets: bool = True,
    asset_backend: Literal["pymupdf", "marker"] = "pymupdf",
    smart_skip_threshold: float = 0.90,
) -> PdfIndexDocument:
    """Build index from PDF(s).
    
    Args:
        input_path: Path to PDF file or directory of PDFs
        out_dir: Output directory for generated files
        options: Index build options
        ocr: Force OCR processing
        auto_ocr: Automatically use OCR if quality is poor
        use_aliases: Use stable doc aliases instead of SHA-based IDs
        strip_headers: Strip repeated headers/footers
        concepts_config: Path to concepts config file
        extract_assets: Whether to extract images and tables
        asset_backend: Backend to use for asset extraction
        smart_skip_threshold: Quality threshold above which OCR is skipped
                             even if ocr=True (default 0.90 = 90%)
        
    Returns:
        The generated index document
    """
    options.validate_pair()

    pdfs = discover_pdfs(input_path)
    if not pdfs:
        raise FileNotFoundError(f"No PDF files found at: {input_path}")

    used_doc_ids: set[str] = set()
    source_docs: list[PdfSourceDoc] = []
    chunks: list[PdfIndexChunk] = []
    asset_manifests: dict[str, AssetManifest] = {}  # doc_id -> manifest

    for pdf_path in pdfs:
        did_ocr = False
        pdf_to_use = pdf_path
        quality_info = None
        
        try:
            # Step 1: Try without OCR first (unless force OCR)
            # SMART SKIP: High quality PDFs skip OCR even when ocr=True
            try:
                pdf_to_use, did_ocr = maybe_ocr_pdf(
                    pdf_path,
                    force=ocr,
                    auto=auto_ocr,
                    smart_skip_threshold=smart_skip_threshold,
                )
            except RuntimeError as e:
                if "ocrmypdf is not installed" in str(e):
                    if ocr:
                        typer.echo(f"❌ Error: {e}", err=True)
                        typer.echo("Install with: pip install -e '.[ocr]'", err=True)
                        raise typer.Exit(1)
                    else:
                        # Auto-OCR was triggered but ocrmypdf not installed
                        warnings.warn(
                            f"Low quality text detected but ocrmypdf not installed. "
                            f"Install with: pip install -e '.[ocr]'"
                        )
                        pdf_to_use = pdf_path
                        did_ocr = False
                else:
                    raise

            sha = sha256_file(pdf_path)
            filename = pdf_path.name

            if use_aliases:
                base_id = get_doc_alias(filename)
                doc_id = unique_doc_id(base_id, used_doc_ids)
            else:
                # Upload-mode doc IDs: match main app
                doc_id = f"doc-{sha[:12]}"

            pages = extract_pages_fitz(pdf_to_use)
            
            # Step 2: Check quality of extracted text
            quality_info = check_extraction_quality(pages)
            
            # Step 3: If quality is poor and we didn't OCR yet, retry with OCR
            if not quality_info["is_quality_good"] and not did_ocr and not ocr:
                warnings.warn(
                    f"Low quality extraction for '{filename}': {quality_info['reason']}. "
                    f"Retrying with OCR..."
                )
                
                # Clean up temp if we created one
                if pdf_to_use != pdf_path:
                    cleanup_temp_pdf(pdf_to_use)
                
                # Force OCR (but still respect smart skip for very high quality)
                try:
                    pdf_to_use, did_ocr = maybe_ocr_pdf(
                        pdf_path,
                        force=True,
                        auto=False,
                        smart_skip_threshold=1.0,  # Disable smart skip when we really need OCR
                    )
                except RuntimeError as e:
                    if "ocrmypdf is not installed" in str(e):
                        warnings.warn(
                            f"OCR recommended but ocrmypdf not installed. "
                            f"Install with: pip install -e '.[ocr]'"
                        )
                        pdf_to_use = pdf_path
                        did_ocr = False
                    else:
                        raise
                
                # Re-extract with OCR
                pages = extract_pages_fitz(pdf_to_use)
                quality_info = check_extraction_quality(pages)
                
                if quality_info["is_quality_good"]:
                    warnings.warn(f"OCR improved quality for '{filename}'!")
            
            if not pages:
                raise RuntimeError(
                    f"No text extracted from '{filename}'. "
                    "Try --ocr or check the PDF is not corrupted."
                )

            if strip_headers:
                # Use student-optimized cleaning
                pages = clean_pages_for_students(pages)

            source_docs.append(
                PdfSourceDoc(
                    docId=doc_id,
                    filename=filename,
                    sha256=sha,
                    pageCount=len(pages),
                )
            )

            # Step 4: Extract assets (images and tables) if enabled
            if extract_assets and ASSET_EXTRACTION_AVAILABLE:
                asset_manifest = extract_and_save_assets(
                    pdf_path=pdf_to_use,
                    doc_id=doc_id,
                    out_dir=out_dir,
                    backend=asset_backend,
                    extract_images=True,
                    extract_tables=True,
                )
                if asset_manifest:
                    asset_manifests[doc_id] = asset_manifest

            for page_num, page_text in pages:
                for chunk_id, chunk_text in chunk_page_words(
                    doc_id=doc_id,
                    page=page_num,
                    text=page_text,
                    chunk_words=options.chunkWords,
                    overlap_words=options.overlapWords,
                ):
                    emb = build_hash_embedding(chunk_text, options.embeddingDim)
                    chunks.append(
                        PdfIndexChunk(
                            chunkId=chunk_id,
                            docId=doc_id,
                            page=page_num,
                            text=chunk_text,
                            embedding=emb,
                        )
                    )
        finally:
            if did_ocr:
                cleanup_temp_pdf(pdf_to_use)

    source_docs.sort(key=lambda d: d.docId)
    chunks.sort(key=lambda c: (c.docId, c.page, c.chunkId))

    created_at = datetime.now(timezone.utc).isoformat()

    index_id_payload = {
        "schemaVersion": options.schemaVersion,
        "chunkerVersion": options.chunkerVersion,
        "embeddingModelId": options.embeddingModelId,
        "sourceDocs": [
            {
                "docId": d.docId,
                "sha256": d.sha256,
                "pageCount": d.pageCount,
                "filename": d.filename,
            }
            for d in source_docs
        ],
        "chunkCount": len(chunks),
    }
    index_hash = hashlib.sha256(
        json.dumps(index_id_payload).encode("utf-8")
    ).hexdigest()[:16]
    index_id = f"pdf-index-{index_hash}"

    manifest = PdfIndexManifest(
        indexId=index_id,
        createdAt=created_at,
        schemaVersion=options.schemaVersion,
        chunkerVersion=options.chunkerVersion,
        embeddingModelId=options.embeddingModelId,
        sourceDocs=source_docs,
        docCount=len(source_docs),
        chunkCount=len(chunks),
    )

    document = PdfIndexDocument(
        indexId=index_id,
        sourceName=(
            source_docs[0].filename
            if len(source_docs) == 1
            else f"{len(source_docs)} documents"
        ),
        createdAt=created_at,
        schemaVersion=options.schemaVersion,
        chunkerVersion=options.chunkerVersion,
        embeddingModelId=options.embeddingModelId,
        sourceDocs=source_docs,
        docCount=len(source_docs),
        chunkCount=len(chunks),
        chunks=chunks,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Get optimized settings based on document size
    total_pages = sum(d.pageCount for d in source_docs)
    optimize_settings = optimize_for_large_document(total_pages)
    use_compact = optimize_settings.get("skip_pretty_print", False)
    
    # Use fast JSON serialization
    fast_json_dump(manifest.model_dump(), out_dir / "manifest.json", indent=not use_compact)
    fast_json_dump([c.model_dump() for c in chunks], out_dir / "chunks.json", indent=not use_compact)
    fast_json_dump(document.model_dump(), out_dir / "index.json", indent=not use_compact)

    # Save asset manifests
    if asset_manifests:
        for doc_id, asset_manifest in asset_manifests.items():
            asset_manifest_path = out_dir / f"asset-manifest-{doc_id}.json"
            save_asset_manifest(asset_manifest, asset_manifest_path)

    # Generate concept manifest and markdown files if config exists
    concept_manifest: ConceptManifest | None = None
    
    # Find concepts config
    config_path = concepts_config
    if config_path is None:
        config_path = find_concepts_config(input_path)
    
    if config_path and config_path.exists():
        try:
            concepts_cfg = load_concepts_config(config_path, input_path)
            
            # Use first source doc as primary
            primary_doc_id = source_docs[0].docId if source_docs else ""
            
            concept_manifest = build_concept_manifest(
                concepts_config=concepts_cfg,
                chunks=chunks,
                source_doc_id=primary_doc_id,
                created_at=created_at,
            )
            
            # Save concept manifest
            save_concept_manifest(
                concept_manifest,
                out_dir / "concept-manifest.json",
            )
            
            # Get combined asset manifest for primary doc
            combined_asset_manifest = asset_manifests.get(primary_doc_id)
            
            # Generate markdown files
            concepts_dir = out_dir / "concepts"
            generate_all_concept_markdowns(
                concept_manifest,
                chunks,
                concepts_dir,
                asset_manifest=combined_asset_manifest,
            )
            
            # Generate README index
            generate_index_readme(
                concept_manifest,
                concepts_dir / "README.md",
                asset_manifest=combined_asset_manifest,
            )
            
        except Exception as e:
            # Log warning but don't fail the whole index build
            warnings.warn(f"Failed to generate concepts: {e}")

    return document
