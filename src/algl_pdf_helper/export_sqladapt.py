"""
Export PDF index to SQL-Adapt compatible format.

This module handles the integration between the PDF helper project and
the SQL-Adapt main application.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .markdown_generator import generate_concept_markdown
from .models import ConceptInfo, ConceptManifest, ConceptMap, ConceptMapEntry


# Output paths for SQL-Adapt integration
DEFAULT_OUTPUT_DIR = Path("/Users/harrydai/Desktop/Personal Portfolio/adaptive-instructional-artifacts/apps/web/public/textbook-static")


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
        for section_name, section in concept.sections.items():
            chunk_ids[section_name] = section.chunkIds
        
        concepts[cid] = ConceptMapEntry(
            title=concept.title,
            definition=concept.definition,
            difficulty=concept.difficulty,
            pageNumbers=concept.pageReferences,
            chunkIds=chunk_ids,
            relatedConcepts=concept.relatedConcepts,
            practiceProblemIds=[],  # To be filled by SQL-Adapt
        )
    
    return ConceptMap(
        version="1.0.0",
        generatedAt=datetime.now(timezone.utc).isoformat(),
        sourceDocId=manifest.sourceDocId,
        concepts=concepts,
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
    
    # Build full markdown
    pages_str = ", ".join(map(str, sorted(concept.pageReferences))) if concept.pageReferences else "Unknown"
    
    markdown = f"""# {concept.title}

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


def export_to_sqladapt(
    input_dir: Path,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Export PDF index to SQL-Adapt compatible format.
    
    Args:
        input_dir: Directory containing processed PDF output (concept-manifest.json, chunks.json)
        output_dir: SQL-Adapt output directory (defaults to DEFAULT_OUTPUT_DIR)
        
    Returns:
        Summary of exported files
    """
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR
    
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
    
    # Generate concept map
    concept_map = convert_to_concept_map(manifest)
    
    # Save concept map
    concept_map_file = output_dir / "concept-map.json"
    with open(concept_map_file, "w", encoding="utf-8") as f:
        json.dump(concept_map.model_dump(), f, indent=2)
    
    # Generate markdown files
    generated_files = []
    for cid, concept in manifest.concepts.items():
        markdown = generate_sqladapt_markdown(concept, chunks, manifest.sourceDocId)
        md_file = concepts_dir / f"{cid}.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(markdown)
        generated_files.append(str(md_file))
    
    return {
        "concept_map": str(concept_map_file),
        "concepts_dir": str(concepts_dir),
        "generated_files": generated_files,
        "concept_count": len(manifest.concepts),
    }
