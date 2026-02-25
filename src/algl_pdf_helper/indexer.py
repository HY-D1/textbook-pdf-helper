from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from .chunker import chunk_page_words
from .clean import normalize_text, strip_repeated_headers_footers
from .embedding import build_hash_embedding
from .extract import extract_pages_fitz, maybe_ocr_pdf, sha256_file, cleanup_temp_pdf
from .models import (
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
        try:
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

    return document
