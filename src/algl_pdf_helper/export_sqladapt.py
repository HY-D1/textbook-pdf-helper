"""
Export PDF index to SQL-Adapt compatible format.

This module handles the integration between the PDF helper project and
the SQL-Adapt main application using the textbook-static-v1 schema.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .learner_quality_audit import (
    audit_concept_markdown,
    build_learner_safe_key_points,
    extract_learner_safe_sql_blocks,
)
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


def load_source_metadata(input_dir: Path, source_doc_id: str) -> dict:
    """
    Load real source document metadata (sha256, pageCount, filename) from the
    index artifacts produced by the indexer.

    Tries manifest.json first (PdfIndexManifest), then index.json
    (PdfIndexDocument).  Returns a dict with keys sha256, pageCount, filename,
    sourceName.  Falls back to sentinel values if the files are absent so that
    callers can detect missing metadata explicitly.
    """
    sentinel = {
        "sha256": None,
        "pageCount": None,
        "filename": f"{source_doc_id}.pdf",
        "sourceName": source_doc_id,
    }

    for candidate in ("manifest.json", "index.json"):
        candidate_path = input_dir / candidate
        if not candidate_path.exists():
            continue
        try:
            with open(candidate_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            source_docs = data.get("sourceDocs", [])
            for doc in source_docs:
                if doc.get("docId") == source_doc_id:
                    return {
                        "sha256": doc.get("sha256"),
                        "pageCount": doc.get("pageCount"),
                        "filename": doc.get("filename", f"{source_doc_id}.pdf"),
                        "sourceName": doc.get("filename", source_doc_id),
                    }
            # If we found the file but the specific docId isn't present, use
            # the first entry if there is exactly one (single-doc export).
            if len(source_docs) == 1:
                doc = source_docs[0]
                return {
                    "sha256": doc.get("sha256"),
                    "pageCount": doc.get("pageCount"),
                    "filename": doc.get("filename", f"{source_doc_id}.pdf"),
                    "sourceName": doc.get("filename", source_doc_id),
                }
        except Exception:
            continue

    return sentinel


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
            tags=concept.tags,
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
    
    # Pre-build list strings to avoid backslashes in f-string expressions (Python 3.10 compatibility)
    chunk_ids_str = ''.join([f"\n  - {cid}" for cid in all_chunk_ids])
    related_str = ''.join([f"\n  - {rid}" for rid in namespaced_related])
    tags_str = ''.join([f"\n  - {tag}" for tag in concept.tags])
    
    markdown = f"""---
id: {concept.id}
title: {concept.title}
definition: {concept.definition or "No definition available."}
difficulty: {concept.difficulty}
estimatedReadTime: {concept.estimatedReadTime}
pageReferences: {concept.pageReferences}
chunkIds:{chunk_ids_str}
relatedConcepts:{related_str}
tags:{tags_str}
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
            "tags": concept_entry.tags,
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


def build_textbook_units(merged_concept_map: dict) -> list[dict]:
    """Build the textbook-units catalog from a merged concept map.

    Each unit has a *deterministic* unitId derived from sha256 of
    ``"{sourceDocId}:{bareConceptId}"``, truncated to 16 hex characters and
    prefixed with ``"unit-"``.  The ID is stable across repeated exports from
    the same source content because it is derived solely from the logical
    identity of the concept, not from timestamps or random state.

    New fields added for adaptive orchestration:
        canonicalConceptKey  -- stable join key (= namespacedId)
        unitType             -- "explanation" | "example" | "summary" | "reference"
                               derived deterministically from chunkIds section names
        keywords             -- tags list propagated from the source concept manifest
        aliases              -- title-derived alternate identifiers (stable)
        shortExcerpt         -- first 200 chars of definition
        sourceSectionTitles  -- sorted list of section names present in chunkIds
        prerequisiteConceptIds -- reserved for future enrichment; always []
        sourceOrder          -- 0-based stable position in the sorted unit list
        unitOrderWithinConcept -- always 1 (one unit per concept in current schema)

    Args:
        merged_concept_map: The full merged concept-map dict produced by
            ``merge_concept_maps()`` or built in-memory during export.
            Expected keys: ``concepts`` (dict of namespaced_id → entry),
            ``sourceDocIds`` (list[str]).

    Returns:
        Stable-sorted (sourceDocId, conceptId) list of unit record dicts,
        one record per concept entry, with sourceOrder set after sorting.
    """
    # Section-name sets for deterministic unitType classification
    _REFERENCE_SECTIONS: frozenset[str] = frozenset({"reference", "api", "syntax"})
    _SUMMARY_SECTIONS: frozenset[str] = frozenset({"summary", "review", "overview"})
    _EXAMPLE_SECTIONS: frozenset[str] = frozenset({"examples", "example", "worked-examples"})

    units: list[dict] = []

    for namespaced_id, concept_data in merged_concept_map.get("concepts", {}).items():
        source_doc_id: str = concept_data.get("sourceDocId", "")

        # Bare concept ID — the part after the namespace prefix
        if "/" in namespaced_id:
            _, bare_id = namespaced_id.split("/", 1)
        else:
            bare_id = namespaced_id

        # Deterministic unit ID: sha256 of canonical identity string
        unit_id = (
            "unit-"
            + hashlib.sha256(f"{source_doc_id}:{bare_id}".encode()).hexdigest()[:16]
        )

        # Relative markdown path from the textbook-static root
        markdown_path = f"concepts/{source_doc_id}/{bare_id}.md"

        # Sorted page list and a compact span object
        page_numbers: list[int] = sorted(concept_data.get("pageNumbers", []))
        page_span: dict | None = (
            {"start": page_numbers[0], "end": page_numbers[-1]}
            if page_numbers
            else None
        )

        # Flat deduplicated chunk IDs, preserving section order
        source_chunk_ids: list[str] = list(
            dict.fromkeys(
                cid
                for section_chunks in concept_data.get("chunkIds", {}).values()
                for cid in section_chunks
            )
        )

        # --- New enrichment fields (all deterministic) ---

        # Canonical join key: stable primary lookup identifier for adaptive
        canonical_concept_key: str = namespaced_id

        # Section names present in this concept (sorted for stability)
        section_names: set[str] = set(concept_data.get("chunkIds", {}).keys())
        source_section_titles: list[str] = sorted(section_names)

        # unitType: derived from section presence, checked in priority order
        if section_names & _REFERENCE_SECTIONS:
            unit_type: str = "reference"
        elif section_names & _SUMMARY_SECTIONS:
            unit_type = "summary"
        elif section_names & _EXAMPLE_SECTIONS:
            unit_type = "example"
        else:
            unit_type = "explanation"

        # Keywords: tags propagated from the concept manifest
        keywords: list[str] = list(concept_data.get("tags", []))

        # Short excerpt: first 200 chars of the definition
        definition: str = concept_data.get("definition", "")
        short_excerpt: str = definition[:200] if definition else ""

        # Aliases: stable alternate identifiers derived from title
        # Rule: slugify title → kebab-case lowercase; include if different from bare_id
        title_str: str = concept_data.get("title", "") or bare_id
        title_slug: str = re.sub(r"[^a-z0-9]+", "-", title_str.lower()).strip("-")
        aliases: list[str] = list(
            dict.fromkeys(a for a in [title_slug] if a and a != bare_id)
        )

        # prerequisiteConceptIds: not derivable from current data; reserved field
        prerequisite_concept_ids: list[str] = []

        # unitOrderWithinConcept: always 1 (one unit per concept in v1 schema)
        unit_order_within_concept: int = 1

        units.append(
            {
                "unitId": unit_id,
                "sourceDocId": source_doc_id,
                "conceptId": bare_id,
                "namespacedId": namespaced_id,
                "canonicalConceptKey": canonical_concept_key,
                "title": concept_data.get("title", ""),
                "difficulty": concept_data.get("difficulty", "beginner"),
                "unitType": unit_type,
                "keywords": keywords,
                "aliases": aliases,
                "shortExcerpt": short_excerpt,
                "markdownPath": markdown_path,
                "pageNumbers": page_numbers,
                "pageSpan": page_span,
                "sourceChunkIds": source_chunk_ids,
                "sourceSectionTitles": source_section_titles,
                "relatedConcepts": concept_data.get("relatedConcepts", []),
                "prerequisiteConceptIds": prerequisite_concept_ids,
                "unitOrderWithinConcept": unit_order_within_concept,
                # sourceOrder is assigned after sorting (see below)
            }
        )

    # Deterministic ordering: sort by (sourceDocId, conceptId)
    units.sort(key=lambda u: (u["sourceDocId"], u["conceptId"]))

    # Assign stable 0-based position after sort so sourceOrder is consistent
    for i, u in enumerate(units):
        u["sourceOrder"] = i

    return units


def enrich_units_with_learner_quality(
    units: list[dict],
    concepts_root_dir: Path,
) -> list[dict]:
    """Add learner-facing quality metadata to each unit in-place.

    Reads the exported markdown file for each unit (via ``markdownPath``
    relative to ``concepts_root_dir``'s parent, i.e. the textbook-static
    output dir) and runs :func:`audit_concept_markdown`.

    Quality fields added to every unit:
        readabilityStatus   -- "ok" | "fallback_only"
        readabilityWarnings -- list[str]  (empty when status is "ok")
        exampleQuality      -- "valid" | "filtered" | "hidden"
        learnerSafeSummary  -- always-safe fallback text

    Args:
        units: List of unit dicts produced by ``build_textbook_units()``.
            Modified **in place** and returned for convenience.
        concepts_root_dir: The ``concepts/`` directory inside the
            textbook-static output directory. The parent of this dir is
            used as the base for resolving ``markdownPath`` values.

    Returns:
        The same list, with quality fields added to each unit.
    """
    textbook_static_dir = concepts_root_dir.parent
    for unit in units:
        md_path = textbook_static_dir / unit.get("markdownPath", "")
        if md_path.exists():
            md_text = md_path.read_text(encoding="utf-8")
        else:
            md_text = ""

        result = audit_concept_markdown(
            md_text=md_text,
            concept_id=unit.get("conceptId", ""),
            title=unit.get("title", ""),
            definition=unit.get("shortExcerpt", ""),
        )
        unit["readabilityStatus"] = result.readabilityStatus
        unit["readabilityWarnings"] = result.readabilityWarnings
        unit["exampleQuality"] = result.exampleQuality
        unit["learnerSafeSummary"] = result.learnerSafeSummary

        # Richer learner-safe fallback fields — derived from safe structured
        # metadata only (never raw extracted prose).
        unit["learnerSafeKeyPoints"] = build_learner_safe_key_points(
            title=unit.get("title", ""),
            definition=unit.get("shortExcerpt", ""),
            keywords=unit.get("keywords", []),
            related_concepts=unit.get("relatedConcepts", []),
            source_section_titles=unit.get("sourceSectionTitles", []),
            page_span=unit.get("pageSpan") or {},
        )

        # Safe SQL examples: extract prose-free individual blocks.
        # When exampleQuality is "hidden" there are no SQL blocks at all.
        if result.exampleQuality != "hidden":
            safe_examples = extract_learner_safe_sql_blocks(md_text)
            unit["learnerSafeExamples"] = safe_examples
            # If no examples survived filtering, update exampleQuality to "hidden"
            if not safe_examples and result.exampleQuality == "valid":
                unit["exampleQuality"] = "hidden"
        else:
            unit["learnerSafeExamples"] = []

    return units


def build_concept_quality_index(
    units: list[dict],
    source_doc_ids: list[str],
) -> dict:
    """Build a concept-quality lookup index from enriched unit records.

    Produces the ``concept-quality.json`` artifact that the adaptive app can
    load once at startup and use for O(1) concept-quality lookups without
    scanning ``textbook-units.json`` at render time.

    Args:
        units: Enriched unit dicts from ``build_textbook_units()`` +
               ``enrich_units_with_learner_quality()``.  Each unit must carry
               the four quality fields (readabilityStatus, readabilityWarnings,
               exampleQuality, learnerSafeSummary).
        source_doc_ids: Ordered list of source document IDs, propagated to the
               index header for provenance.

    Returns:
        Dict with schema:
          {
            "schemaVersion": "concept-quality-v1",
            "generatedAt": "<ISO-8601>",
            "sourceDocIds": [...],
            "totalConcepts": N,
            "qualityByConcept": {
              "<docId>/<bareId>": {
                "readabilityStatus": "ok" | "fallback_only",
                "readabilityWarnings": [...],
                "exampleQuality": "valid" | "filtered" | "hidden",
                "learnerSafeSummary": "...",
                "learnerSafeKeyPoints": ["...", ...],
                "learnerSafeExamples": [{"title": "...", "sql": "..."}, ...]
              },
              ...
            }
          }

        ``learnerSafeKeyPoints`` is always a list of plain-text bullets derived
        from safe structured metadata (title, definition, keywords, section
        titles, related concepts, page span).

        ``learnerSafeExamples`` is a list of individual SQL code blocks that are
        free of prose contamination, extracted from the concept markdown.  Empty
        when ``exampleQuality == 'hidden'``.
    """
    quality_by_concept: dict[str, dict] = {}
    for unit in units:
        namespaced_id: str = unit.get("namespacedId", "")
        if not namespaced_id:
            continue
        quality_by_concept[namespaced_id] = {
            "readabilityStatus": unit.get("readabilityStatus", "ok"),
            "readabilityWarnings": unit.get("readabilityWarnings", []),
            "exampleQuality": unit.get("exampleQuality", "hidden"),
            "learnerSafeSummary": unit.get("learnerSafeSummary", ""),
            "learnerSafeKeyPoints": unit.get("learnerSafeKeyPoints", []),
            "learnerSafeExamples": unit.get("learnerSafeExamples", []),
        }

    return {
        "schemaVersion": "concept-quality-v1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceDocIds": source_doc_ids,
        "totalConcepts": len(quality_by_concept),
        "qualityByConcept": quality_by_concept,
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

    # Load real source metadata from the indexer artifacts
    source_meta = load_source_metadata(input_dir, manifest.sourceDocId)

    # Generate concept map for this PDF
    concept_map = convert_to_concept_map(manifest)

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
                "tags": concept_entry.tags,
                "provenance": concept_entry.provenance,
            }
        final_concept_count = len(merged_map["concepts"])
        is_new_pdf = True

    # Save merged concept map
    with open(concept_map_file, "w", encoding="utf-8") as f:
        json.dump(merged_map, f, indent=2)

    # Build merge-safe textbook manifest:
    # Preserve all existing sourceDocs entries and only add/update the current doc.
    existing_textbook_manifest: dict = {}
    if merge and textbook_manifest_file.exists():
        try:
            with open(textbook_manifest_file, "r", encoding="utf-8") as f:
                existing_textbook_manifest = json.load(f)
        except Exception:
            existing_textbook_manifest = {}

    # Build the PdfSourceDoc for this document with real metadata
    new_source_doc = PdfSourceDoc(
        docId=manifest.sourceDocId,
        filename=source_meta["filename"],
        sha256=source_meta["sha256"] if source_meta["sha256"] is not None else "unavailable",
        pageCount=source_meta["pageCount"] if source_meta["pageCount"] is not None else 0,
    )

    if existing_textbook_manifest:
        # Merge: preserve existing sourceDocs, replace or append the current doc
        existing_docs: list[dict] = existing_textbook_manifest.get("sourceDocs", [])
        merged_docs = [d for d in existing_docs if d.get("docId") != manifest.sourceDocId]
        merged_docs.append(json.loads(new_source_doc.model_dump_json()))
        # Recount chunks across all docs (approximate: existing stored count + this doc)
        existing_chunk_count = existing_textbook_manifest.get("chunkCount", 0)
        if is_new_pdf:
            total_chunk_count = existing_chunk_count + len(chunks)
        else:
            total_chunk_count = existing_chunk_count  # updated doc, not adding new chunks
        textbook_manifest_data = {
            **existing_textbook_manifest,
            "sourceDocs": merged_docs,
            "docCount": len(merged_docs),
            "chunkCount": total_chunk_count,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        }
    else:
        # Fresh manifest using real metadata
        textbook_manifest = create_textbook_manifest(
            source_doc_id=manifest.sourceDocId,
            filename=source_meta["filename"],
            sha256=source_meta["sha256"] if source_meta["sha256"] is not None else "unavailable",
            page_count=source_meta["pageCount"] if source_meta["pageCount"] is not None else 0,
            chunk_count=len(chunks),
            source_name=source_meta["sourceName"],
        )
        textbook_manifest_data = json.loads(textbook_manifest.model_dump_json())

    # Ensure docCount is consistent with concept-map sourceDocIds
    textbook_manifest_data["docCount"] = len(merged_map.get("sourceDocIds", [manifest.sourceDocId]))

    with open(textbook_manifest_file, "w", encoding="utf-8") as f:
        json.dump(textbook_manifest_data, f, indent=2)
    
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

    # Build and write textbook-units.json.
    # Markdown files for this doc are now on disk, so the quality audit reads
    # real text instead of empty strings.
    units_catalog_file = output_dir / "textbook-units.json"
    all_units = build_textbook_units(merged_map)
    enrich_units_with_learner_quality(all_units, concepts_dir)
    units_catalog: dict = {
        "schemaVersion": "textbook-units-v1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceDocIds": merged_map.get("sourceDocIds", [manifest.sourceDocId]),
        "totalUnits": len(all_units),
        "units": all_units,
    }
    with open(units_catalog_file, "w", encoding="utf-8") as f:
        json.dump(units_catalog, f, indent=2)

    # Build and write concept-quality.json — concept-level quality index for
    # direct lookup by the adaptive app without scanning textbook-units.json.
    concept_quality_index = build_concept_quality_index(
        all_units,
        merged_map.get("sourceDocIds", [manifest.sourceDocId]),
    )
    concept_quality_file = output_dir / "concept-quality.json"
    with open(concept_quality_file, "w", encoding="utf-8") as f:
        json.dump(concept_quality_index, f, indent=2)

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

    # Surface whether source metadata was real or fell back to sentinel values

    metadata_is_real = (
        source_meta["sha256"] is not None and source_meta["pageCount"] is not None
    )

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
        "source_metadata_real": metadata_is_real,
        "source_sha256": source_meta["sha256"],
        "source_page_count": source_meta["pageCount"],
    }


def validate_handoff_integrity(output_dir: Path) -> dict[str, Any]:
    """
    Validate the textbook-static export directory for adaptive app handoff integrity.

    Checks enforced:
    1. Every concept ID in concept-map.json has a corresponding .md file under
       concepts/{docId}/{bareConceptId}.md
    2. Every .md file (excluding README.md) maps back to a concept-map entry.
    3. textbook-manifest.json sourceDocs count and docCount agree with the
       exported document directories under concepts/.
    4. chunks-metadata.json contains all exported docIds found in concept-map.json.

    Returns a dict with:
        valid (bool): True if all checks pass.
        errors (list[str]): Fatal integrity violations.
        warnings (list[str]): Non-fatal anomalies.
        concept_map_entries (int): Number of entries in concept-map.json.
        markdown_files (int): Number of .md concept files found.
        missing_pages (list[str]): concept-map IDs without a matching .md file.
        orphan_pages (list[str]): .md files without a matching concept-map entry.
        source_docs_count (int): sourceDocs count from textbook-manifest.json.
        doc_dirs_count (int): Number of docId directories under concepts/.
        chunks_meta_doc_ids (list[str]): docIds in chunks-metadata.json.
    """
    errors: list[str] = []
    warnings: list[str] = []

    concept_map_file = output_dir / "concept-map.json"
    textbook_manifest_file = output_dir / "textbook-manifest.json"
    chunks_meta_file = output_dir / "chunks-metadata.json"
    units_catalog_file = output_dir / "textbook-units.json"
    concepts_dir = output_dir / "concepts"

    # -- Load concept-map.json --
    if not concept_map_file.exists():
        errors.append("concept-map.json is missing")
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "concept_map_entries": 0,
            "markdown_files": 0,
            "missing_pages": [],
            "orphan_pages": [],
            "source_docs_count": 0,
            "doc_dirs_count": 0,
            "chunks_meta_doc_ids": [],
            "units_count": 0,
        }

    with open(concept_map_file, "r", encoding="utf-8") as f:
        concept_map_data = json.load(f)

    all_concepts: dict[str, dict] = concept_map_data.get("concepts", {})
    map_source_doc_ids: list[str] = concept_map_data.get("sourceDocIds", [])

    # -- Check 1 & 2: concept-map <-> markdown file correspondence --
    # Build expected set: for each namespaced ID "docId/bareId", expect
    # concepts/docId/bareId.md
    missing_pages: list[str] = []
    for namespaced_id in all_concepts:
        if "/" in namespaced_id:
            doc_id, bare_id = namespaced_id.split("/", 1)
        else:
            doc_id = namespaced_id
            bare_id = namespaced_id
        md_file = concepts_dir / doc_id / f"{bare_id}.md"
        if not md_file.exists():
            missing_pages.append(namespaced_id)

    if missing_pages:
        errors.append(
            f"{len(missing_pages)} concept-map entries missing markdown files: "
            + ", ".join(missing_pages[:5])
            + ("..." if len(missing_pages) > 5 else "")
        )

    # Build set of concept IDs expected from existing .md files
    orphan_pages: list[str] = []
    markdown_file_count = 0
    if concepts_dir.exists():
        for doc_dir in concepts_dir.iterdir():
            if not doc_dir.is_dir():
                continue
            for md_file in doc_dir.glob("*.md"):
                if md_file.name == "README.md":
                    continue
                markdown_file_count += 1
                bare_id = md_file.stem
                doc_id = doc_dir.name
                namespaced_id = f"{doc_id}/{bare_id}"
                if namespaced_id not in all_concepts:
                    # Also check non-namespaced fallback
                    if bare_id not in all_concepts:
                        orphan_pages.append(namespaced_id)

    if orphan_pages:
        warnings.append(
            f"{len(orphan_pages)} markdown files have no concept-map entry: "
            + ", ".join(orphan_pages[:5])
            + ("..." if len(orphan_pages) > 5 else "")
        )

    # -- Check 3: textbook-manifest.json consistency --
    source_docs_count = 0
    if not textbook_manifest_file.exists():
        errors.append("textbook-manifest.json is missing")
    else:
        with open(textbook_manifest_file, "r", encoding="utf-8") as f:
            tm_data = json.load(f)
        source_docs_count = len(tm_data.get("sourceDocs", []))
        manifest_doc_count = tm_data.get("docCount", source_docs_count)

        if manifest_doc_count != source_docs_count:
            errors.append(
                f"textbook-manifest.json docCount={manifest_doc_count} "
                f"does not match len(sourceDocs)={source_docs_count}"
            )

        # Check that every sourceDocs docId is also in concept-map sourceDocIds
        manifest_doc_ids = {d.get("docId") for d in tm_data.get("sourceDocs", [])}
        map_doc_ids_set = set(map_source_doc_ids)
        extra_in_manifest = manifest_doc_ids - map_doc_ids_set
        missing_from_manifest = map_doc_ids_set - manifest_doc_ids
        if extra_in_manifest:
            warnings.append(
                f"textbook-manifest.json has docIds not in concept-map: {extra_in_manifest}"
            )
        if missing_from_manifest:
            errors.append(
                f"concept-map sourceDocIds missing from textbook-manifest: {missing_from_manifest}"
            )

    # Count doc directories
    doc_dirs_count = 0
    if concepts_dir.exists():
        doc_dirs_count = sum(1 for d in concepts_dir.iterdir() if d.is_dir())

    if doc_dirs_count != len(map_source_doc_ids):
        warnings.append(
            f"concepts/ has {doc_dirs_count} doc directories but concept-map lists "
            f"{len(map_source_doc_ids)} sourceDocIds"
        )

    # -- Check 4: chunks-metadata.json has all exported docIds --
    chunks_meta_doc_ids: list[str] = []
    if not chunks_meta_file.exists():
        errors.append("chunks-metadata.json is missing")
    else:
        with open(chunks_meta_file, "r", encoding="utf-8") as f:
            chunks_meta = json.load(f)
        chunks_meta_doc_ids = list(chunks_meta.keys())
        missing_from_chunks_meta = set(map_source_doc_ids) - set(chunks_meta_doc_ids)
        if missing_from_chunks_meta:
            errors.append(
                f"chunks-metadata.json missing docIds: {missing_from_chunks_meta}"
            )

    # -- Check 5: textbook-units.json --
    units_count = 0
    if not units_catalog_file.exists():
        errors.append("textbook-units.json is missing")
    else:
        with open(units_catalog_file, "r", encoding="utf-8") as f:
            units_data = json.load(f)

        units_list: list[dict] = units_data.get("units", [])
        units_count = len(units_list)

        # unitId uniqueness
        unit_ids = [u.get("unitId", "") for u in units_list]
        if len(unit_ids) != len(set(unit_ids)):
            errors.append("textbook-units.json contains duplicate unitIds")

        # markdownPath resolution (all must point to existing files)
        missing_md_paths = [
            u["markdownPath"]
            for u in units_list
            if not (output_dir / u.get("markdownPath", "__missing__")).exists()
        ]
        if missing_md_paths:
            errors.append(
                f"textbook-units.json: {len(missing_md_paths)} markdownPath values "
                "don't resolve: "
                + ", ".join(missing_md_paths[:5])
                + ("..." if len(missing_md_paths) > 5 else "")
            )

        # Coverage: every concept-map entry must have a unit, and vice-versa
        units_namespaced_ids = {u.get("namespacedId", "") for u in units_list}
        map_namespaced_ids = set(all_concepts.keys())

        missing_from_units = map_namespaced_ids - units_namespaced_ids
        if missing_from_units:
            errors.append(
                f"textbook-units.json missing {len(missing_from_units)} concept-map "
                "entries: "
                + ", ".join(sorted(missing_from_units)[:5])
                + ("..." if len(missing_from_units) > 5 else "")
            )

        extra_in_units = units_namespaced_ids - map_namespaced_ids
        if extra_in_units:
            warnings.append(
                f"textbook-units.json has {len(extra_in_units)} entries not in "
                "concept-map: "
                + ", ".join(sorted(extra_in_units)[:5])
            )

        # sourceOrder: must be a contiguous 0..N-1 sequence (no gaps, no dups)
        source_orders = [u.get("sourceOrder") for u in units_list]
        if any(o is None for o in source_orders):
            errors.append(
                "textbook-units.json: some units are missing the sourceOrder field"
            )
        elif sorted(source_orders) != list(range(len(units_list))):
            errors.append(
                "textbook-units.json: sourceOrder values are not a contiguous "
                "0..N-1 sequence"
            )

        # unitType: must be one of the recognised values
        _valid_unit_types = {"explanation", "example", "summary", "reference"}
        bad_types = [
            u.get("unitType")
            for u in units_list
            if u.get("unitType") not in _valid_unit_types
        ]
        if bad_types:
            errors.append(
                f"textbook-units.json: {len(bad_types)} units have invalid unitType "
                "values: " + ", ".join(str(t) for t in sorted(set(str(b) for b in bad_types)))
            )

        # Required enrichment fields must be present on every unit
        _required_enrichment = {
            "canonicalConceptKey",
            "unitType",
            "keywords",
            "aliases",
            "shortExcerpt",
            "sourceSectionTitles",
            "prerequisiteConceptIds",
            "sourceOrder",
            "unitOrderWithinConcept",
        }
        for u in units_list:
            missing_fields = _required_enrichment - set(u.keys())
            if missing_fields:
                errors.append(
                    f"textbook-units.json unit '{u.get('unitId', '?')}' missing "
                    "enrichment fields: " + ", ".join(sorted(missing_fields))
                )
                break  # report once to avoid log noise

        # -- Check 6: Learner-facing quality metadata --
        # All units must have the quality fields (readabilityStatus etc.).
        _required_quality_fields = {
            "readabilityStatus",
            "readabilityWarnings",
            "exampleQuality",
            "learnerSafeSummary",
        }
        _valid_readability_statuses = {"ok", "fallback_only"}
        _valid_example_qualities = {"valid", "filtered", "hidden"}

        missing_quality_fields_sample: list[str] = []
        fallback_only_count = 0
        invalid_status_sample: list[str] = []

        for u in units_list:
            missing_qf = _required_quality_fields - set(u.keys())
            if missing_qf:
                missing_quality_fields_sample.append(u.get("unitId", "?"))
                if len(missing_quality_fields_sample) >= 5:
                    break

        if missing_quality_fields_sample:
            warnings.append(
                f"textbook-units.json: {len(missing_quality_fields_sample)}+ units "
                "are missing learner quality fields (readabilityStatus, "
                "readabilityWarnings, exampleQuality, learnerSafeSummary). "
                "Re-run the export to populate these fields."
            )
        else:
            # All quality fields present; check values are valid
            for u in units_list:
                rs = u.get("readabilityStatus")
                eq = u.get("exampleQuality")
                if rs not in _valid_readability_statuses:
                    invalid_status_sample.append(
                        f"{u.get('unitId', '?')}:readabilityStatus={rs!r}"
                    )
                if eq not in _valid_example_qualities:
                    invalid_status_sample.append(
                        f"{u.get('unitId', '?')}:exampleQuality={eq!r}"
                    )
                if rs == "fallback_only":
                    fallback_only_count += 1

            if invalid_status_sample:
                errors.append(
                    "textbook-units.json: invalid quality field values: "
                    + "; ".join(invalid_status_sample[:5])
                )

            # Warn (not error) when a large fraction of concepts are fallback-only
            if units_count > 0:
                fallback_ratio = fallback_only_count / units_count
                if fallback_ratio > 0.50:
                    warnings.append(
                        f"learner_quality: {fallback_only_count}/{units_count} "
                        f"({fallback_ratio:.0%}) concepts have "
                        "readabilityStatus=fallback_only — extraction quality "
                        "may be too low for learner-facing use"
                    )

    # -- Check 7: concept-quality.json --
    concept_quality_file = output_dir / "concept-quality.json"
    concept_quality_key_count = 0
    if not concept_quality_file.exists():
        errors.append("concept-quality.json is missing")
    else:
        try:
            with open(concept_quality_file, "r", encoding="utf-8") as _cqf:
                cq_data = json.load(_cqf)

            cq_schema = cq_data.get("schemaVersion", "")
            if cq_schema != "concept-quality-v1":
                errors.append(
                    f"concept-quality.json has unexpected schemaVersion={cq_schema!r}; "
                    "expected 'concept-quality-v1'"
                )

            quality_by_concept: dict = cq_data.get("qualityByConcept", {})
            concept_quality_key_count = len(quality_by_concept)

            # Keys must be a subset of concept-map namespaced IDs
            cq_keys = set(quality_by_concept.keys())
            map_keys = set(all_concepts.keys())
            extra_cq_keys = cq_keys - map_keys
            if extra_cq_keys:
                warnings.append(
                    f"concept-quality.json has {len(extra_cq_keys)} keys not in "
                    "concept-map: " + ", ".join(sorted(extra_cq_keys)[:5])
                )

            missing_cq_keys = map_keys - cq_keys
            if missing_cq_keys:
                warnings.append(
                    f"concept-quality.json missing {len(missing_cq_keys)} concept-map "
                    "keys — re-run export to populate: "
                    + ", ".join(sorted(missing_cq_keys)[:5])
                    + ("..." if len(missing_cq_keys) > 5 else "")
                )

            # Validate field values for each concept entry
            _valid_rs = {"ok", "fallback_only"}
            _valid_eq = {"valid", "filtered", "hidden"}
            bad_cq_values: list[str] = []
            for cq_key, cq_entry in quality_by_concept.items():
                rs = cq_entry.get("readabilityStatus")
                eq = cq_entry.get("exampleQuality")
                if rs not in _valid_rs:
                    bad_cq_values.append(f"{cq_key}:readabilityStatus={rs!r}")
                if eq not in _valid_eq:
                    bad_cq_values.append(f"{cq_key}:exampleQuality={eq!r}")
                if len(bad_cq_values) >= 5:
                    break
            if bad_cq_values:
                errors.append(
                    "concept-quality.json: invalid field values: "
                    + "; ".join(bad_cq_values)
                )
        except Exception as _cqe:
            errors.append(f"concept-quality.json: failed to parse — {_cqe}")

    # Aggregate quality counts (and enrichment coverage) for return payload
    fallback_only_total = 0
    fallback_enriched_total = 0   # fallback_only units that have learnerSafeKeyPoints
    fallback_with_examples_total = 0  # fallback_only units that have learnerSafeExamples
    # Detailed example quality breakdown for fallback_only concepts
    fallback_with_valid_examples = 0      # exampleQuality="valid" with non-empty examples
    fallback_with_filtered_examples = 0   # exampleQuality="filtered" with non-empty examples
    fallback_with_hidden_examples = 0     # exampleQuality="hidden" or no examples
    per_doc_fallback_counts: dict[str, int] = {}
    per_doc_fallback_enriched: dict[str, int] = {}  # per-doc enrichment counts
    per_doc_fallback_examples: dict[str, int] = {}  # per-doc examples counts
    # Per-doc breakdown by example quality
    per_doc_fallback_valid_examples: dict[str, int] = {}
    per_doc_fallback_filtered_examples: dict[str, int] = {}
    per_doc_fallback_hidden_examples: dict[str, int] = {}
    if units_catalog_file.exists():
        try:
            with open(units_catalog_file, "r", encoding="utf-8") as _fq:
                _qdata = json.load(_fq)
            for _u in _qdata.get("units", []):
                if _u.get("readabilityStatus") == "fallback_only":
                    fallback_only_total += 1
                    _nid = _u.get("namespacedId", "")
                    if "/" in _nid:
                        _did = _nid.split("/", 1)[0]
                        per_doc_fallback_counts[_did] = per_doc_fallback_counts.get(_did, 0) + 1
                    # Count units that have the enriched learner-safe fields
                    _key_points = _u.get("learnerSafeKeyPoints", [])
                    if _key_points and len(_key_points) > 0:
                        fallback_enriched_total += 1
                        if "/" in _nid:
                            _did = _nid.split("/", 1)[0]
                            per_doc_fallback_enriched[_did] = per_doc_fallback_enriched.get(_did, 0) + 1
                    # Count fallback units with learnerSafeExamples (when exampleQuality != hidden)
                    _example_quality = _u.get("exampleQuality", "hidden")
                    _examples = _u.get("learnerSafeExamples", [])
                    if _example_quality != "hidden" and _examples and len(_examples) > 0:
                        fallback_with_examples_total += 1
                        if "/" in _nid:
                            _did = _nid.split("/", 1)[0]
                            per_doc_fallback_examples[_did] = per_doc_fallback_examples.get(_did, 0) + 1
                    # Detailed breakdown by exampleQuality
                    if _example_quality == "valid" and _examples and len(_examples) > 0:
                        fallback_with_valid_examples += 1
                        if "/" in _nid:
                            _did = _nid.split("/", 1)[0]
                            per_doc_fallback_valid_examples[_did] = per_doc_fallback_valid_examples.get(_did, 0) + 1
                    elif _example_quality == "filtered" and _examples and len(_examples) > 0:
                        fallback_with_filtered_examples += 1
                        if "/" in _nid:
                            _did = _nid.split("/", 1)[0]
                            per_doc_fallback_filtered_examples[_did] = per_doc_fallback_filtered_examples.get(_did, 0) + 1
                    else:
                        # exampleQuality="hidden" or no examples
                        fallback_with_hidden_examples += 1
                        if "/" in _nid:
                            _did = _nid.split("/", 1)[0]
                            per_doc_fallback_hidden_examples[_did] = per_doc_fallback_hidden_examples.get(_did, 0) + 1
        except Exception:
            pass

    # Per-sourceDoc counts for richer CLI output
    per_doc_concept_counts: dict[str, int] = {}
    for doc_id in map_source_doc_ids:
        per_doc_concept_counts[doc_id] = sum(
            1 for k in all_concepts if k.startswith(f"{doc_id}/")
        )

    per_doc_unit_counts: dict[str, int] = {}
    if units_catalog_file.exists():
        try:
            with open(units_catalog_file, "r", encoding="utf-8") as _fu:
                _udata = json.load(_fu)
            for _u in _udata.get("units", []):
                _nid = _u.get("namespacedId", "")
                if "/" in _nid:
                    _did = _nid.split("/", 1)[0]
                    per_doc_unit_counts[_did] = per_doc_unit_counts.get(_did, 0) + 1
        except Exception:
            pass

    valid = len(errors) == 0

    return {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "concept_map_entries": len(all_concepts),
        "markdown_files": markdown_file_count,
        "missing_pages": missing_pages,
        "orphan_pages": orphan_pages,
        "source_docs_count": source_docs_count,
        "doc_dirs_count": doc_dirs_count,
        "chunks_meta_doc_ids": chunks_meta_doc_ids,
        "units_count": units_count,
        "fallback_only_count": fallback_only_total,
        "fallback_enriched_count": fallback_enriched_total,
        "fallback_with_examples_count": fallback_with_examples_total,
        "fallback_with_valid_examples": fallback_with_valid_examples,
        "fallback_with_filtered_examples": fallback_with_filtered_examples,
        "fallback_with_hidden_examples": fallback_with_hidden_examples,
        "concept_quality_key_count": concept_quality_key_count,
        "per_doc_concept_counts": per_doc_concept_counts,
        "per_doc_unit_counts": per_doc_unit_counts,
        "per_doc_fallback_counts": per_doc_fallback_counts,
        "per_doc_fallback_enriched": per_doc_fallback_enriched,
        "per_doc_fallback_examples": per_doc_fallback_examples,
        "per_doc_fallback_valid_examples": per_doc_fallback_valid_examples,
        "per_doc_fallback_filtered_examples": per_doc_fallback_filtered_examples,
        "per_doc_fallback_hidden_examples": per_doc_fallback_hidden_examples,
    }
