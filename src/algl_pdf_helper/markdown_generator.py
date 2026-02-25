from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import ConceptInfo, ConceptManifest, PdfIndexChunk


SECTION_TITLES = {
    "definition": "Definition",
    "explanation": "Explanation",
    "examples": "Examples",
    "commonMistakes": "Common Mistakes",
    "syntax": "Syntax",
    "notes": "Notes",
    "tips": "Tips",
    "practice": "Practice",
}


def get_chunk_by_id(chunks: list[PdfIndexChunk], chunk_id: str) -> PdfIndexChunk | None:
    """Find a chunk by its ID."""
    for chunk in chunks:
        if chunk.chunkId == chunk_id:
            return chunk
    return None


def format_page_links(page_numbers: list[int], doc_id: str) -> str:
    """Create markdown page reference links.
    
    Args:
        page_numbers: List of page numbers
        doc_id: Document ID for reference
        
    Returns:
        Markdown string with page links
    """
    if not page_numbers:
        return ""
    
    pages_str = ", ".join(f"Page {p}" for p in sorted(set(page_numbers)))
    return f"📖 *Source: {pages_str}*"


def generate_concept_markdown(
    concept: ConceptInfo,
    chunks: list[PdfIndexChunk],
    doc_id: str,
) -> str:
    """Generate markdown content for a single concept.
    
    Args:
        concept: Concept metadata
        chunks: All available chunks (to look up text)
        doc_id: Source document ID
        
    Returns:
        Markdown formatted string
    """
    lines: list[str] = []
    
    # Title
    lines.append(f"# {concept.title}")
    lines.append("")
    
    # Metadata
    difficulty_emoji = {
        "beginner": "🟢",
        "intermediate": "🟡", 
        "advanced": "🔴",
    }.get(concept.difficulty, "⚪")
    
    lines.append(f"{difficulty_emoji} **Difficulty:** {concept.difficulty.title()}")
    lines.append(f"⏱️ **Estimated Read Time:** {concept.estimatedReadTime} minutes")
    lines.append("")
    
    # Definition (from metadata, not chunks)
    if concept.definition:
        lines.append("## Overview")
        lines.append("")
        lines.append(concept.definition)
        lines.append("")
    
    # Page references
    page_link = format_page_links(concept.pageReferences, doc_id)
    if page_link:
        lines.append(page_link)
        lines.append("")
    
    # Sections
    for section_name, section in concept.sections.items():
        section_title = SECTION_TITLES.get(section_name, section_name.replace("-", " ").title())
        lines.append(f"## {section_title}")
        lines.append("")
        
        # Get chunk texts for this section
        section_texts: list[str] = []
        for chunk_id in section.chunkIds:
            chunk = get_chunk_by_id(chunks, chunk_id)
            if chunk:
                section_texts.append(chunk.text)
        
        if section_texts:
            # Join chunks with separator
            full_text = "\n\n".join(section_texts)
            lines.append(full_text)
        else:
            lines.append("*Content not available in source.*")
        
        lines.append("")
    
    # Related concepts
    if concept.relatedConcepts:
        lines.append("## Related Concepts")
        lines.append("")
        for related_id in concept.relatedConcepts:
            lines.append(f"- [{related_id}](./{related_id}.md)")
        lines.append("")
    
    # Tags
    if concept.tags:
        lines.append("---")
        lines.append("")
        tags_str = " ".join(f"`{tag}`" for tag in concept.tags)
        lines.append(f"**Tags:** {tags_str}")
        lines.append("")
    
    return "\n".join(lines)


def save_concept_markdown(
    concept: ConceptInfo,
    chunks: list[PdfIndexChunk],
    doc_id: str,
    out_dir: Path,
) -> Path:
    """Generate and save markdown for a concept.
    
    Args:
        concept: Concept to generate markdown for
        chunks: All available chunks
        doc_id: Source document ID
        out_dir: Output directory for markdown files
        
    Returns:
        Path to saved file
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    
    markdown = generate_concept_markdown(concept, chunks, doc_id)
    
    file_path = out_dir / f"{concept.id}.md"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    
    return file_path


def generate_all_concept_markdowns(
    manifest: ConceptManifest,
    chunks: list[PdfIndexChunk],
    out_dir: Path,
) -> list[Path]:
    """Generate markdown files for all concepts in manifest.
    
    Args:
        manifest: Concept manifest with all concepts
        chunks: All available chunks
        out_dir: Output directory
        
    Returns:
        List of paths to generated files
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    
    generated: list[Path] = []
    for concept in manifest.concepts.values():
        file_path = save_concept_markdown(
            concept, chunks, manifest.sourceDocId, out_dir
        )
        generated.append(file_path)
    
    return generated


def generate_index_readme(
    manifest: ConceptManifest,
    out_path: Path,
) -> Path:
    """Generate README.md index of all concepts.
    
    Args:
        manifest: Concept manifest
        out_path: Output path for README
        
    Returns:
        Path to saved file
    """
    lines: list[str] = [
        "# Concept Library",
        "",
        f"**Source:** {manifest.sourceDocId}",
        f"**Total Concepts:** {manifest.conceptCount}",
        "",
        "## Concepts by Difficulty",
        "",
    ]
    
    # Group by difficulty
    by_difficulty: dict[str, list[ConceptInfo]] = {
        "beginner": [],
        "intermediate": [],
        "advanced": [],
    }
    
    for concept in manifest.concepts.values():
        diff = concept.difficulty if concept.difficulty in by_difficulty else "beginner"
        by_difficulty[diff].append(concept)
    
    for difficulty in ["beginner", "intermediate", "advanced"]:
        concepts = by_difficulty[difficulty]
        if not concepts:
            continue
        
        emoji = {"beginner": "🟢", "intermediate": "🟡", "advanced": "🔴"}[difficulty]
        lines.append(f"### {emoji} {difficulty.title()}")
        lines.append("")
        
        for concept in sorted(concepts, key=lambda c: c.title):
            lines.append(f"- [{concept.title}](./{concept.id}.md) - {concept.estimatedReadTime} min")
        lines.append("")
    
    # Full list
    lines.append("---")
    lines.append("")
    lines.append("## All Concepts")
    lines.append("")
    
    for concept_id in sorted(manifest.concepts.keys()):
        concept = manifest.concepts[concept_id]
        lines.append(f"- [{concept.title}](./{concept.id}.md)")
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        f.write("\n")
    
    return out_path
