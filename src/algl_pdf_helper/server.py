from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from pydantic import BaseModel

try:
    from fastapi import FastAPI, File, UploadFile
    from fastapi.responses import JSONResponse
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "fastapi is not installed. Install with: pip install -e '.[server]'"
    ) from e

from .indexer import build_index
from .models import IndexBuildOptions

api = FastAPI(title="algl-pdf-helper")


class IndexResponse(BaseModel):
    document: dict
    manifest: dict
    chunks: list[dict]


@api.post("/v1/index")
async def index_pdf(
    pdf: UploadFile = File(...),
    ocr: bool = False,
    auto_ocr: bool = True,
    use_aliases: bool = False,
    chunk_words: int = 180,
    overlap_words: int = 30,
    embedding_dim: int = 24,
    strip_headers: bool = True,
):
    tmp_root = Path(tempfile.mkdtemp(prefix="algl_pdf_api_"))
    try:
        pdf_path = tmp_root / (pdf.filename or "upload.pdf")
        data = await pdf.read()
        pdf_path.write_bytes(data)

        out_dir = tmp_root / "pdf-index"
        opts = IndexBuildOptions(
            chunkWords=chunk_words,
            overlapWords=overlap_words,
            embeddingDim=embedding_dim,
        )

        doc = build_index(
            pdf_path,
            out_dir,
            options=opts,
            ocr=ocr,
            auto_ocr=auto_ocr,
            use_aliases=use_aliases,
            strip_headers=strip_headers,
        )

        manifest = (out_dir / "manifest.json").read_text(encoding="utf-8")
        chunks = (out_dir / "chunks.json").read_text(encoding="utf-8")

        return JSONResponse(
            {
                "document": doc.model_dump(),
                "manifest": __import__("json").loads(manifest),
                "chunks": __import__("json").loads(chunks),
            }
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    finally:
        try:
            shutil.rmtree(tmp_root)
        except Exception:
            pass
