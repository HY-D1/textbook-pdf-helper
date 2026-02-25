from __future__ import annotations

import json
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import ConceptInfo, ConceptManifest, ConceptSection, PdfIndexChunk


def load_concepts_config(config_path: Path) -> dict[str, Any]:
    """Load concept configuration from YAML file.
    
    Args:
        config_path: Path to concepts.yaml file
        
    Returns:
        Dictionary with concepts configuration
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Concepts config not found: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    if not config or "concepts" not in config:
        raise ValueError("Invalid concepts config: must have 'concepts' key")
    
    return config


def get_chunks_for_pages(
    chunks: list[PdfIndexChunk],
    page_numbers: list[int],
    doc_id: str | None = None,
) -> list[PdfIndexChunk]:
    """Get all chunks that belong to specified page numbers.
    
    Args:
        chunks: All available chunks
        page_numbers: Page numbers to filter by
        doc_id: Optional document ID to filter by
        
    Returns:
        List of chunks matching the page numbers
    """
    result = []
    for chunk in chunks:
        if chunk.page in page_numbers:
            if doc_id is None or chunk.docId == doc_id:
                result.append(chunk)
    return result


def build_concept_manifest(
    concepts_config: dict[str, Any],
    chunks: list[PdfIndexChunk],
    source_doc_id: str,
    created_at: str | None = None,
) -> ConceptManifest:
    """Build concept manifest from config and chunks.
    
    Args:
        concepts_config: Loaded concepts configuration
        chunks: All extracted chunks from the PDF
        source_doc_id: Primary document ID
        created_at: Optional timestamp (ISO format)
        
    Returns:
        ConceptManifest with mapped chunks
    """
    if created_at is None:
        created_at = datetime.now(timezone.utc).isoformat()
    
    concepts: dict[str, ConceptInfo] = {}
    
    for concept_id, concept_data in concepts_config.get("concepts", {}).items():
        # Get page numbers for each section
        section_pages = concept_data.get("sections", {})
        all_page_numbers: list[int] = []
        sections: dict[str, ConceptSection] = {}
        
        for section_name, pages in section_pages.items():
            if isinstance(pages, int):
                pages = [pages]
            elif not isinstance(pages, list):
                continue
            
            page_nums = [int(p) for p in pages]
            section_chunks = get_chunks_for_pages(chunks, page_nums, source_doc_id)
            
            sections[section_name] = ConceptSection(
                chunkIds=[c.chunkId for c in section_chunks],
                pageNumbers=page_nums,
            )
            all_page_numbers.extend(page_nums)
        
        # Get all chunks for this concept (from all sections)
        unique_pages = sorted(set(all_page_numbers))
        all_chunk_ids = []
        for section in sections.values():
            all_chunk_ids.extend(section.chunkIds)
        
        concepts[concept_id] = ConceptInfo(
            id=concept_id,
            title=concept_data.get("title", concept_id.replace("-", " ").title()),
            definition=concept_data.get("definition", ""),
            difficulty=concept_data.get("difficulty", "beginner"),
            estimatedReadTime=concept_data.get("estimatedReadTime", 5),
            pageReferences=unique_pages,
            sections=sections,
            relatedConcepts=concept_data.get("relatedConcepts", []),
            tags=concept_data.get("tags", []),
        )
    
    return ConceptManifest(
        schemaVersion="concept-manifest-v1",
        sourceDocId=source_doc_id,
        createdAt=created_at,
        conceptCount=len(concepts),
        concepts=concepts,
    )


def save_concept_manifest(
    manifest: ConceptManifest,
    out_path: Path,
) -> None:
    """Save concept manifest to JSON file.
    
    Args:
        manifest: Concept manifest to save
        out_path: Output file path
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to dict for JSON serialization
    manifest_dict = {
        "schemaVersion": manifest.schemaVersion,
        "sourceDocId": manifest.sourceDocId,
        "createdAt": manifest.createdAt,
        "conceptCount": manifest.conceptCount,
        "concepts": {
            k: v.model_dump() for k, v in manifest.concepts.items()
        },
    }
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest_dict, f, indent=2)
        f.write("\n")


def find_concepts_config(input_path: Path) -> Path | None:
    """Find concepts.yaml file near input path.
    
    Looks for concepts.yaml in:
    1. Same directory as input file
    2. Parent directory of input directory
    3. Current working directory
    
    Args:
        input_path: Path to PDF file or directory
        
    Returns:
        Path to concepts.yaml if found, None otherwise
    """
    # If input is a file, look in same directory
    if input_path.is_file():
        config_path = input_path.parent / "concepts.yaml"
        if config_path.exists():
            return config_path
    
    # If input is a directory, look in it
    if input_path.is_dir():
        config_path = input_path / "concepts.yaml"
        if config_path.exists():
            return config_path
    
    # Look in parent of input directory
    parent_config = input_path.parent / "concepts.yaml"
    if parent_config.exists():
        return parent_config
    
    # Look in current working directory
    cwd_config = Path("concepts.yaml")
    if cwd_config.exists():
        return cwd_config
    
    return None
