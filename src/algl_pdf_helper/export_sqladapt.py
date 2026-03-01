"""
Export PDF index to SQL-Adapt compatible format.

This module handles the integration between the PDF helper project and
the SQL-Adapt main application using the textbook-static-v1 schema.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .markdown_generator import generate_concept_markdown
from .models import (
    TEXTBOOK_STATIC_SCHEMA_ID,
    TEXTBOOK_STATIC_VERSION,
    ConceptInfo,
    ConceptManifest,
    ConceptMap,
    ConceptMapEntry,
    TextbookStaticManifest,
    PdfSourceDoc,
)


def load_chunks(chunks_file: Path) -> list[dict]:
    """Load chunks from JSON file."""
    with open(chunks_file, "r", encoding="utf-8") as f:
        return json.load(f)


def load_concept_manifest(manifest_file: Path) -> ConceptManifest:
    """Load concept manifest from JSON file."""
    with open(manifest_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    concepts = {}
    for cid, cdata in data.get("concepts", {}).items():
        concepts[cid] = ConceptInfo(**cdata)
    
    return ConceptManifest(
        schemaVersion=data.get("schemaVersion", "concept-manifest-v1"),
        sourceDocId=data.get("sourceDocId", ""),
        createdAt=data.get("createdAt", ""),
        conceptCount=len(concepts),
        concepts=concepts,
    )


def convert_to_concept_map(manifest: ConceptManifest) -> ConceptMap:
    """Convert internal concept manifest to SQL-Adapt concept map format."""
    concepts: dict[str, ConceptMapEntry] = {}
    
    for cid, concept in manifest.concepts.items():
        # Convert sections to chunkIds dict
        chunk_ids: dict[str, list[str]] = {}
        source_blocks: list[dict] = []
        all_pages: set[int] = set()
        
        for section_name, section in concept.sections.items():
            chunk_ids[section_name] = section.chunkIds
            all_pages.update(section.pageNumbers)
            
            # Collect source blocks from sections
            if hasattr(section, 'sourceBlocks') and section.sourceBlocks:
                for block in section.sourceBlocks:
                    if isinstance(block, dict):
                        source_blocks.append(block)
        
        # Build provenance structure
        provenance = {
            "chunks": list(set(
                chunk_id 
                for section_chunks in chunk_ids.values() 
                for chunk_id in section_chunks
            )),
            "pages": sorted(all_pages),
            "blocks": source_blocks,
            "extraction_method": "pymupdf",
            "source_doc_id": manifest.sourceDocId,
        }
        
        concepts[cid] = ConceptMapEntry(
            title=concept.title,
            definition=concept.definition,
            difficulty=concept.difficulty,
            pageNumbers=concept.pageReferences,
            chunkIds=chunk_ids,
            relatedConcepts=concept.relatedConcepts,
            practiceProblemIds=concept.practiceProblemIds,
            sourceDocId=manifest.sourceDocId,
            provenance=provenance,
        )
    
    return ConceptMap(
        version=TEXTBOOK_STATIC_VERSION,
        generatedAt=datetime.now(timezone.utc).isoformat(),
        sourceDocIds=[manifest.sourceDocId],
        concepts=concepts,
    )


def create_textbook_manifest(
    source_doc_id: str,
    filename: str,
    sha256: str,
    page_count: int,
    chunk_count: int,
    source_name: str = "",
) -> TextbookStaticManifest:
    """
    Create a TextbookStaticManifest for the exported content.
    
    Args:
        source_doc_id: Document ID (e.g., 'sql-textbook')
        filename: Original filename
        sha256: SHA256 hash of the PDF
        page_count: Number of pages
        chunk_count: Number of chunks
        source_name: Human-readable source name
        
    Returns:
        TextbookStaticManifest with schema v1
    """
    if not source_name:
        source_name = filename
    
    source_doc = PdfSourceDoc(
        docId=source_doc_id,
        filename=filename,
        sha256=sha256,
        pageCount=page_count,
    )
    
    return TextbookStaticManifest(
        schemaVersion=TEXTBOOK_STATIC_VERSION,
        schemaId=TEXTBOOK_STATIC_SCHEMA_ID,
        indexId=f"idx-{source_doc_id}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        createdAt=datetime.now(timezone.utc).isoformat(),
        sourceName=source_name,
        sourceDocs=[source_doc],
        docCount=1,
        chunkCount=chunk_count,
    )


def get_chunk_by_id(chunks: list[dict], chunk_id: str) -> dict | None:
    """Find chunk by ID."""
    for chunk in chunks:
        if chunk.get("chunkId") == chunk_id:
            return chunk
    return None


def extract_sql_examples(text: str) -> list[dict]:
    """Extract SQL examples from text."""
    examples = []
    
    # Look for SQL patterns
    sql_patterns = [
        (r'(SELECT\s+.+?;)', "SELECT"),
        (r'(INSERT\s+.+?;)', "INSERT"),
        (r'(UPDATE\s+.+?;)', "UPDATE"),
        (r'(DELETE\s+.+?;)', "DELETE"),
        (r'(CREATE\s+TABLE\s+.+?;)', "CREATE TABLE"),
        (r'(DROP\s+TABLE\s+.+?;)', "DROP TABLE"),
    ]
    
    for pattern, stmt_type in sql_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        for match in matches[:2]:  # Max 2 per type
            examples.append({
                "title": f"{stmt_type} Example",
                "code": match.strip(),
                "explanation": f"Example {stmt_type} statement from textbook."
            })
    
    return examples


def extract_common_mistakes(text: str) -> list[dict]:
    """Extract common mistakes from text."""
    mistakes = []
    
    warning_phrases = [
        "warning", "caution", "note:", "important",
        "common error", "mistake", "incorrect", "avoid",
        "be careful", "watch out", "don't forget"
    ]
    
    lines = text.split('\n')
    for line in lines:
        line_lower = line.lower()
        if any(phrase in line_lower for phrase in warning_phrases):
            if len(line) > 30 and len(line) < 300:
                mistakes.append({
                    "title": "Common Pitfall",
                    "description": line.strip(),
                    "explanation": "This issue is documented in the textbook as a common pitfall."
                })
    
    return mistakes[:3]  # Limit to 3


def generate_sqladapt_markdown(
    concept: ConceptInfo,
    chunks: list[dict],
    doc_id: str,
) -> str:
    """Generate SQL-Adapt compatible markdown for a concept."""
    
    # Get all chunks for this concept
    concept_chunks: list[dict] = []
    for section in concept.sections.values():
        for chunk_id in section.chunkIds:
            chunk = get_chunk_by_id(chunks, chunk_id)
            if chunk:
                concept_chunks.append(chunk)
    
    # Sort by page
    concept_chunks.sort(key=lambda c: (c.get("page", 0), c.get("chunkId", "")))
    
    # Merge text
    full_text = "\n\n".join(c.get("text", "") for c in concept_chunks)
    
    # Extract examples and mistakes
    examples = extract_sql_examples(full_text)
    mistakes = extract_common_mistakes(full_text)
    
    # Format examples section
    examples_md = ""
    if examples:
        for i, ex in enumerate(examples[:3], 1):
            examples_md += f"""### Example {i}: {ex['title']}
```sql
{ex['code']}
```
{ex['explanation']}

"""
    else:
        examples_md = """### Example 1
```sql
-- No specific example available in textbook
```
No example available for this concept.

"""
    
    # Format mistakes section
    mistakes_md = ""
    if mistakes:
        for i, m in enumerate(mistakes, 1):
            mistakes_md += f"""### Mistake {i}: {m['title']}
{m['description']}

**Why this happens:** {m['explanation']}

"""
    else:
        mistakes_md = """### No common mistakes listed
No specific mistakes documented in textbook.

"""
    
    # Build full markdown with YAML frontmatter
    pages_str = ", ".join(map(str, sorted(concept.pageReferences))) if concept.pageReferences else "Unknown"
    
    # Build chunk IDs list for frontmatter
    all_chunk_ids = []
    for section in concept.sections.values():
        all_chunk_ids.extend(section.chunkIds)
    all_chunk_ids = list(dict.fromkeys(all_chunk_ids))  # Remove duplicates, preserve order
    
    # Build related concepts list (namespaced)
    namespaced_related = [f"{doc_id}/{rid}" if "/" not in rid else rid for rid in concept.relatedConcepts]
    
    markdown = f"""---
id: {concept.id}
title: {concept.title}
definition: {concept.definition or "No definition available."}
difficulty: {concept.difficulty}
estimatedReadTime: {concept.estimatedReadTime}
pageReferences: {concept.pageReferences}
chunkIds:{''.join([f"\n  - {cid}" for cid in all_chunk_ids])}
relatedConcepts:{''.join([f"\n  - {rid}" for rid in namespaced_related])}
tags:{''.join([f"\n  - {tag}" for tag in concept.tags])}
sourceDocId: {doc_id}
---

# {concept.title}

## Definition
{concept.definition or "No definition available."}

## Explanation
{full_text[:2000] if len(full_text) > 2000 else full_text}

## Examples
{examples_md.strip()}

## Common Mistakes
{mistakes_md.strip()}

---
*Source: {doc_id}, Pages {pages_str}*
"""
    
    return markdown


def merge_concept_maps(
    existing_map: dict,
    new_map: ConceptMap,
    source_doc_id: str,
) -> dict:
    """Merge new concept map into existing one."""
    # Use namespaced concept IDs to avoid conflicts
    merged_concepts = existing_map.get("concepts", {}).copy()
    
    for cid, concept_entry in new_map.concepts.items():
        # Namespace the concept ID with source doc
        namespaced_id = f"{source_doc_id}/{cid}"
        
        # Convert ConceptMapEntry to dict with provenance
        merged_concepts[namespaced_id] = {
            "title": concept_entry.title,
            "definition": concept_entry.definition,
            "difficulty": concept_entry.difficulty,
            "pageNumbers": concept_entry.pageNumbers,
            "chunkIds": concept_entry.chunkIds,
            "relatedConcepts": [
                f"{source_doc_id}/{rid}" if "/" not in rid else rid
                for rid in concept_entry.relatedConcepts
            ],
            "practiceProblemIds": concept_entry.practiceProblemIds,
            "sourceDocId": source_doc_id,
            "provenance": concept_entry.provenance,
        }
    
    # Merge source doc IDs
    existing_source_ids = existing_map.get("sourceDocIds", [])
    if isinstance(existing_source_ids, str):
        existing_source_ids = [existing_source_ids]
    all_source_ids = list(set(existing_source_ids + [source_doc_id]))
    
    return {
        "version": TEXTBOOK_STATIC_VERSION,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceDocIds": all_source_ids,
        "concepts": merged_concepts,
    }


def export_to_sqladapt(
    input_dir: Path,
    output_dir: Path | None = None,
    merge: bool = True,
) -> dict[str, Any]:
    """
    Export PDF index to SQL-Adapt compatible format.
    
    This function creates textbook-static-v1 compatible output including:
    - textbook-manifest.json (main manifest with schema v1)
    - concept-map.json (concept index for web app)
    - chunks.json (all chunks with embeddings)
    - concepts/{docId}/{concept-id}.md (individual concept files)
    
    Args:
        input_dir: Directory containing processed PDF output (concept-manifest.json, chunks.json)
        output_dir: SQL-Adapt output directory (required, no default)
        merge: If True, merge with existing concept map instead of overwriting
        
    Returns:
        Summary of exported files
        
    Raises:
        ValueError: If output_dir is not provided
        FileNotFoundError: If required input files are missing
    """
    if output_dir is None:
        raise ValueError(
            "output_dir is required. Provide --output-dir or set SQL_ADAPT_PUBLIC_DIR environment variable."
        )
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    concepts_dir = output_dir / "concepts"
    concepts_dir.mkdir(exist_ok=True)
    
    # Load files
    manifest_file = input_dir / "concept-manifest.json"
    chunks_file = input_dir / "chunks.json"
    
    if not manifest_file.exists():
        raise FileNotFoundError(f"Concept manifest not found: {manifest_file}")
    if not chunks_file.exists():
        raise FileNotFoundError(f"Chunks file not found: {chunks_file}")
    
    manifest = load_concept_manifest(manifest_file)
    chunks = load_chunks(chunks_file)
    
    # Generate concept map for this PDF
    concept_map = convert_to_concept_map(manifest)
    
    # Create textbook manifest (schema v1)
    # Note: We don't have access to the original PDF file here, so we use placeholder values
    # In production, these should be passed from the indexer
    textbook_manifest = create_textbook_manifest(
        source_doc_id=manifest.sourceDocId,
        filename=f"{manifest.sourceDocId}.pdf",
        sha256="unknown",  # Should be provided by caller
        page_count=0,  # Should be provided by caller
        chunk_count=len(chunks),
        source_name=manifest.sourceDocId,
    )
    
    # Load or create merged concept map
    concept_map_file = output_dir / "concept-map.json"
    textbook_manifest_file = output_dir / "textbook-manifest.json"
    
    if merge and concept_map_file.exists():
        # Load existing and merge
        with open(concept_map_file, "r", encoding="utf-8") as f:
            existing_map = json.load(f)
        
        merged_map = merge_concept_maps(existing_map, concept_map, manifest.sourceDocId)
        final_concept_count = len(merged_map["concepts"])
        is_new_pdf = manifest.sourceDocId not in existing_map.get("sourceDocIds", [])
    else:
        # Create new or overwrite
        merged_map = {
            "version": TEXTBOOK_STATIC_VERSION,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "sourceDocIds": [manifest.sourceDocId],
            "concepts": {},
        }
        for cid, concept_entry in concept_map.concepts.items():
            namespaced_id = f"{manifest.sourceDocId}/{cid}"
            merged_map["concepts"][namespaced_id] = {
                "title": concept_entry.title,
                "definition": concept_entry.definition,
                "difficulty": concept_entry.difficulty,
                "pageNumbers": concept_entry.pageNumbers,
                "chunkIds": concept_entry.chunkIds,
                "relatedConcepts": [
                    f"{manifest.sourceDocId}/{rid}" for rid in concept_entry.relatedConcepts
                ],
                "practiceProblemIds": concept_entry.practiceProblemIds,
                "sourceDocId": manifest.sourceDocId,
                "provenance": concept_entry.provenance,
            }
        final_concept_count = len(merged_map["concepts"])
        is_new_pdf = True
    
    # Save merged concept map
    with open(concept_map_file, "w", encoding="utf-8") as f:
        json.dump(merged_map, f, indent=2)
    
    # Save textbook manifest
    with open(textbook_manifest_file, "w", encoding="utf-8") as f:
        json.dump(
            json.loads(textbook_manifest.model_dump_json()),
            f,
            indent=2
        )
    
    # Generate markdown files (namespaced by docId)
    generated_files = []
    updated_files = []
    
    doc_concepts_dir = concepts_dir / manifest.sourceDocId
    doc_concepts_dir.mkdir(parents=True, exist_ok=True)
    
    for cid, concept in manifest.concepts.items():
        markdown = generate_sqladapt_markdown(concept, chunks, manifest.sourceDocId)
        md_file = doc_concepts_dir / f"{cid}.md"
        
        # Check if file exists (for reporting)
        if md_file.exists():
            updated_files.append(str(md_file))
        else:
            generated_files.append(str(md_file))
            
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(markdown)
    
    # Generate README for this document's concepts
    readme_content = f"""# {manifest.sourceDocId} Concepts

This directory contains concept documentation for **{manifest.sourceDocId}**.

## Concepts

"""
    for cid, concept in manifest.concepts.items():
        readme_content += f"- [{concept.title}](./{cid}.md)\n"
    
    readme_content += f"""
---
*Generated: {datetime.now(timezone.utc).isoformat()}*
*Schema: {TEXTBOOK_STATIC_SCHEMA_ID} v{TEXTBOOK_STATIC_VERSION}*
"""
    
    readme_file = doc_concepts_dir / "README.md"
    with open(readme_file, "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    # Save chunks metadata (for reference)
    chunks_meta_file = output_dir / "chunks-metadata.json"
    chunks_metadata = {}
    
    if merge and chunks_meta_file.exists():
        with open(chunks_meta_file, "r", encoding="utf-8") as f:
            chunks_metadata = json.load(f)
    
    # Add this PDF's chunks metadata
    chunks_metadata[manifest.sourceDocId] = {
        "totalChunks": len(chunks),
        "sourceFile": manifest.sourceDocId,
        "exportedAt": datetime.now(timezone.utc).isoformat(),
    }
    
    with open(chunks_meta_file, "w", encoding="utf-8") as f:
        json.dump(chunks_metadata, f, indent=2)
    
    return {
        "concept_map": str(concept_map_file),
        "textbook_manifest": str(textbook_manifest_file),
        "concepts_dir": str(doc_concepts_dir),
        "generated_files": generated_files,
        "updated_files": updated_files,
        "concept_count": len(manifest.concepts),
        "total_concepts": final_concept_count,
        "is_new_pdf": is_new_pdf,
        "source_doc_id": manifest.sourceDocId,
        "schema_id": TEXTBOOK_STATIC_SCHEMA_ID,
        "schema_version": TEXTBOOK_STATIC_VERSION,
    }
