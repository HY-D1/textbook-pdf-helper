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

# =============================================================================
# INTEGRATION: Pedagogical Section Titles (Added 2026-02-27)
# =============================================================================
# These titles are used for the new pedagogical content format
PEDAGOGICAL_SECTION_TITLES = {
    "learning_objectives": "Learning Objectives",
    "prerequisite_concepts": "Prerequisites",
    "definition": "What is This?",
    "examples": "Examples",
    "common_mistakes": "Common Mistakes",
    "practice_challenge": "Practice Challenge",
    "practice_problems": "Related Practice Problems",
}


def get_chunk_by_id(chunks: list[PdfIndexChunk], chunk_id: str) -> PdfIndexChunk | None:
    """Find a chunk by its ID."""
    for chunk in chunks:
        if chunk.chunkId == chunk_id:
            return chunk
    return None


def is_pedagogical_format(concept: ConceptInfo) -> bool:
    """
    Check if a concept is in the new pedagogical format.
    
    INTEGRATION (2026-02-27): Detects if concept was generated using the
    pedagogical content generator by checking for pedagogy-specific fields.
    
    Args:
        concept: Concept metadata to check
        
    Returns:
        True if concept uses pedagogical format
    """
    # Check for pedagogy-specific fields in tags
    if concept.tags:
        if any(tag.startswith("pedagogical") for tag in concept.tags):
            return True
    
    # Check sections for pedagogical-specific keys
    if "learning_objectives" in concept.sections:
        return True
    if "prerequisite_concepts" in concept.sections:
        return True
    if "practice_challenge" in concept.sections:
        return True
    
    # Check for pedagogical items in examples section
    examples_section = concept.sections.get("examples")
    if examples_section and hasattr(examples_section, "items"):
        items = getattr(examples_section, "items", [])
        if items and len(items) > 0:
            first_item = items[0]
            if isinstance(first_item, dict):
                # Check for pedagogy-specific keys in example
                if any(key in first_item for key in ["scenario", "difficulty", "expected_output"]):
                    return True
    
    return False


def generate_pedagogical_markdown(
    concept: ConceptInfo,
    chunks: list[PdfIndexChunk],
    doc_id: str,
) -> str:
    """
    Generate markdown for a concept in the pedagogical format.
    
    INTEGRATION (2026-02-27): This function generates markdown using the
    new pedagogical structure which includes:
    - Learning objectives
    - Prerequisites
    - Scenario-based examples with expected output
    - Common mistakes with error messages and fixes
    - Practice challenges with hints and solutions
    - Links to SQL-Adapt practice problems
    
    Args:
        concept: Concept metadata in pedagogical format
        chunks: All available chunks
        doc_id: Source document ID
        
    Returns:
        Markdown formatted string
    """
    # ===================================================================
    # INTEGRATION: Check for pedagogical format (Added 2026-02-27)
    # ===================================================================
    if is_pedagogical_format(concept):
        # Use pedagogical markdown generation for richer output
        return generate_pedagogical_markdown(concept, chunks, doc_id)
    
    # ===================================================================
    # LEGACY MODE: Standard markdown generation
    # ===================================================================
    lines: list[str] = []
    
    # Title
    lines.append(f"# {concept.title}")
    lines.append("")
    
    # Metadata with difficulty and time estimate
    difficulty_emoji = {
        "beginner": "🟢",
        "intermediate": "🟡", 
        "advanced": "🔴",
    }.get(concept.difficulty, "⚪")
    
    lines.append(f"{difficulty_emoji} **Difficulty:** {concept.difficulty.title()}")
    lines.append(f"⏱️ **Estimated Read Time:** {concept.estimatedReadTime} minutes")
    lines.append("")
    
    # Learning Objectives
    learning_obj_section = concept.sections.get("learning_objectives")
    if learning_obj_section:
        lines.append("## Learning Objectives")
        lines.append("")
        objectives = getattr(learning_obj_section, "items", [])
        if not objectives and hasattr(learning_obj_section, "text"):
            # Try to parse from text
            objectives = learning_obj_section.text.split("\n")
        for obj in objectives:
            if obj.strip():
                lines.append(f"- {obj.strip()}")
        lines.append("")
    
    # Prerequisites
    prereq_section = concept.sections.get("prerequisite_concepts")
    if prereq_section:
        lines.append("## Prerequisites")
        lines.append("")
        lines.append("Before learning this concept, you should understand:")
        lines.append("")
        prereqs = getattr(prereq_section, "items", [])
        if not prereqs and hasattr(prereq_section, "text"):
            prereqs = prereq_section.text.split("\n")
        for prereq in prereqs:
            if prereq.strip():
                lines.append(f"- [{prereq.strip()}](./{prereq.strip()}.md)")
        lines.append("")
    
    # Definition (in pedagogical format this is "What is This?")
    definition_section = concept.sections.get("definition")
    if definition_section:
        lines.append("## What is This?")
        lines.append("")
        if hasattr(definition_section, "text"):
            lines.append(definition_section.text)
        elif hasattr(definition_section, "concept_explanation"):
            lines.append(definition_section.concept_explanation)
        lines.append("")
        
        # Visual diagram if available
        if hasattr(definition_section, "visual_diagram") and definition_section.visual_diagram:
            lines.append("### Visual Diagram")
            lines.append("")
            lines.append("```")
            lines.append(definition_section.visual_diagram)
            lines.append("```")
            lines.append("")
    
    # Examples with pedagogical structure
    examples_section = concept.sections.get("examples")
    if examples_section:
        lines.append("## Examples")
        lines.append("")
        
        examples = getattr(examples_section, "items", [])
        if examples:
            for i, ex in enumerate(examples, 1):
                title = ex.get("title", f"Example {i}") if isinstance(ex, dict) else f"Example {i}"
                lines.append(f"### {title}")
                lines.append("")
                
                # Difficulty badge
                ex_difficulty = ex.get("difficulty", "beginner") if isinstance(ex, dict) else "beginner"
                lines.append(f"**Difficulty:** {ex_difficulty.title()}")
                lines.append("")
                
                # Scenario
                scenario = ex.get("scenario", "") if isinstance(ex, dict) else ""
                if scenario:
                    lines.append(f"**Scenario:** {scenario}")
                    lines.append("")
                
                # SQL code
                sql = ex.get("sql", "") if isinstance(ex, dict) else (ex.get("code", "") if isinstance(ex, dict) else "")
                if sql:
                    lines.append("```sql")
                    lines.append(sql)
                    lines.append("```")
                    lines.append("")
                
                # Explanation
                explanation = ex.get("explanation", "") if isinstance(ex, dict) else ""
                if explanation:
                    lines.append(f"**Explanation:** {explanation}")
                    lines.append("")
                
                # Expected output
                expected = ex.get("expected_output", "") if isinstance(ex, dict) else ""
                if expected:
                    lines.append("**Expected Output:**")
                    lines.append("")
                    lines.append(expected)
                    lines.append("")
    
    # Common Mistakes with pedagogical structure
    mistakes_section = concept.sections.get("common_mistakes")
    if mistakes_section:
        lines.append("## Common Mistakes")
        lines.append("")
        
        mistakes = getattr(mistakes_section, "items", [])
        if mistakes:
            for i, m in enumerate(mistakes, 1):
                if isinstance(m, dict):
                    title = m.get("title", f"Mistake {i}")
                    lines.append(f"### {title}")
                    lines.append("")
                    
                    # Incorrect SQL
                    error_sql = m.get("error_sql", "")
                    if error_sql:
                        lines.append("**Incorrect SQL:**")
                        lines.append("```sql")
                        lines.append(error_sql)
                        lines.append("```")
                        lines.append("")
                    
                    # Error message
                    error_msg = m.get("error_message", "")
                    if error_msg:
                        lines.append(f"**Error Message:** `{error_msg}`")
                        lines.append("")
                    
                    # Why it happens
                    why = m.get("why_it_happens", "")
                    if why:
                        lines.append(f"**Why it happens:** {why}")
                        lines.append("")
                    
                    # Fixed SQL
                    fix_sql = m.get("fix_sql", "")
                    if fix_sql:
                        lines.append("**Corrected SQL:**")
                        lines.append("```sql")
                        lines.append(fix_sql)
                        lines.append("```")
                        lines.append("")
                    
                    # Key takeaway
                    takeaway = m.get("key_takeaway", "")
                    if takeaway:
                        lines.append(f"💡 **Key Takeaway:** {takeaway}")
                        lines.append("")
    
    # Practice Challenge
    challenge_section = concept.sections.get("practice_challenge")
    if challenge_section:
        lines.append("## Practice Challenge")
        lines.append("")
        
        if isinstance(challenge_section, dict):
            description = challenge_section.get("description", "")
            if description:
                lines.append(f"**{description}**")
                lines.append("")
            
            hint = challenge_section.get("hint", "")
            if hint:
                lines.append(f"💡 **Hint:** {hint}")
                lines.append("")
            
            # Collapsible solution
            solution = challenge_section.get("solution", "")
            explanation = challenge_section.get("explanation", "")
            if solution:
                lines.append("<details>")
                lines.append("<summary>Click to see solution</summary>")
                lines.append("")
                lines.append("```sql")
                lines.append(solution)
                lines.append("```")
                lines.append("")
                if explanation:
                    lines.append(f"**Explanation:** {explanation}")
                lines.append("</details>")
                lines.append("")
    
    # Practice Problems Links
    practice_problems_section = concept.sections.get("practice_problems")
    if practice_problems_section:
        lines.append("## Related Practice Problems")
        lines.append("")
        
        problems = getattr(practice_problems_section, "items", [])
        if problems:
            for prob_id in problems:
                lines.append(f"- [{prob_id}](/practice/{prob_id})")
            lines.append("")
    
    # Page references
    page_link = format_page_links(concept.pageReferences, doc_id)
    if page_link:
        lines.append("---")
        lines.append("")
        lines.append(page_link)
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
        # Filter out internal tags
        display_tags = [t for t in concept.tags if not t.startswith("pedagogical")]
        if display_tags:
            tags_str = " ".join(f"`{tag}`" for tag in display_tags)
            lines.append(f"**Tags:** {tags_str}")
            lines.append("")
    
    # Footer
    lines.append("---")
    lines.append("")
    lines.append("*Content generated for SQL-Adapt Learning Platform*")
    lines.append("")
    
    return "\n".join(lines)


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
    """
    Generate markdown content for a single concept.
    
    INTEGRATION (2026-02-27): Automatically detects and handles both standard
    and pedagogical formats. Use generate_pedagogical_markdown() for explicit
    pedagogical format generation.
    
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
