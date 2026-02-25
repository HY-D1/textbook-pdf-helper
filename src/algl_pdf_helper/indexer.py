from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from .chunker import chunk_page_words
from .clean import normalize_text, strip_repeated_headers_footers
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
    ConceptManifest,
    IndexBuildOptions,
    PdfIndexChunk,
    PdfIndexDocument,
    PdfIndexManifest,
    PdfSourceDoc,
)


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
) -> PdfIndexDocument:
    options.validate_pair()

    pdfs = discover_pdfs(input_path)
    if not pdfs:
        raise FileNotFoundError(f"No PDF files found at: {input_path}")

    used_doc_ids: set[str] = set()
    source_docs: list[PdfSourceDoc] = []
    chunks: list[PdfIndexChunk] = []

    for pdf_path in pdfs:
        did_ocr = False
        pdf_to_use = pdf_path
        quality_info = None
        
        try:
            # Step 1: Try without OCR first (unless force OCR)
            pdf_to_use, did_ocr = maybe_ocr_pdf(
                pdf_path,
                force=ocr,
                auto=auto_ocr,
            )

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
                import warnings
                warnings.warn(
                    f"Low quality extraction for '{filename}': {quality_info['reason']}. "
                    f"Retrying with OCR..."
                )
                
                # Clean up temp if we created one
                if pdf_to_use != pdf_path:
                    cleanup_temp_pdf(pdf_to_use)
                
                # Force OCR
                pdf_to_use, did_ocr = maybe_ocr_pdf(
                    pdf_path,
                    force=True,
                    auto=False,
                )
                
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
                pages = strip_repeated_headers_footers(pages)
                pages = [(p, normalize_text(t)) for p, t in pages]

            source_docs.append(
                PdfSourceDoc(
                    docId=doc_id,
                    filename=filename,
                    sha256=sha,
                    pageCount=len(pages),
                )
            )

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
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest.model_dump(), indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "chunks.json").write_text(
        json.dumps([c.model_dump() for c in chunks], indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "index.json").write_text(
        json.dumps(document.model_dump(), indent=2) + "\n",
        encoding="utf-8",
    )

    # Generate concept manifest and markdown files if config exists
    concept_manifest: ConceptManifest | None = None
    
    # Find concepts config
    config_path = concepts_config
    if config_path is None:
        config_path = find_concepts_config(input_path)
    
    if config_path and config_path.exists():
        try:
            concepts_cfg = load_concepts_config(config_path)
            
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
            
            # Generate markdown files
            concepts_dir = out_dir / "concepts"
            generate_all_concept_markdowns(
                concept_manifest,
                chunks,
                concepts_dir,
            )
            
            # Generate README index
            generate_index_readme(
                concept_manifest,
                concepts_dir / "README.md",
            )
            
        except Exception as e:
            # Log warning but don't fail the whole index build
            import warnings
            warnings.warn(f"Failed to generate concepts: {e}")

    return document
