from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import AssetManifest, AssetReference, ConceptInfo, ConceptManifest, PdfIndexChunk


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


def _generate_yaml_frontmatter(
    concept: "ConceptInfo",
    doc_id: str,
    include_provenance: bool = True,
) -> str:
    """Generate YAML frontmatter with metadata and provenance.
    
    Args:
        concept: Concept metadata
        doc_id: Source document ID
        include_provenance: Whether to include provenance links
        
    Returns:
        YAML frontmatter string
    """
    lines: list[str] = ["---"]
    lines.append(f'title: "{concept.title}"')
    lines.append(f'concept_id: "{concept.id}"')
    lines.append(f'difficulty: "{concept.difficulty}"')
    lines.append(f'estimated_read_time: {concept.estimatedReadTime}')
    lines.append(f'source_doc: "{doc_id}"')
    
    if concept.pageReferences:
        pages_str = ", ".join(str(p) for p in sorted(set(concept.pageReferences)))
        lines.append(f'source_pages: [{pages_str}]')
    
    if include_provenance:
        # Collect all chunk IDs from all sections
        all_chunks: set[str] = set()
        for section in concept.sections.values():
            all_chunks.update(section.chunkIds)
        
        if all_chunks:
            chunks_list = ', '.join(f'"{c}"' for c in sorted(all_chunks))
            lines.append(f'source_chunks: [{chunks_list}]')
    
    if concept.tags:
        tags_str = ', '.join(f'"{t}"' for t in concept.tags)
        lines.append(f'tags: [{tags_str}]')
    
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _generate_view_source_links(
    concept: "ConceptInfo",
    doc_id: str,
    base_url: str = "",
) -> str:
    """Generate "View Source" links for the concept.
    
    Args:
        concept: Concept metadata
        doc_id: Source document ID
        base_url: Base URL for source viewer
        
    Returns:
        Markdown string with view source links
    """
    lines: list[str] = []
    
    if not concept.pageReferences:
        return ""
    
    lines.append("### 📖 View Source")
    lines.append("")
    lines.append("View the original textbook passages for this concept:")
    lines.append("")
    
    # Page links
    for page in sorted(set(concept.pageReferences)):
        if base_url:
            link = f"{base_url}/view?doc={doc_id}&page={page}"
            lines.append(f"- [Page {page}]({link})")
        else:
            # Use HTML comment for chunk reference
            lines.append(f"- Page {page} <!-- open-page: {doc_id}:{page} -->")
    
    lines.append("")
    
    # Source chunks hidden comment
    all_chunks: set[str] = set()
    for section in concept.sections.values():
        all_chunks.update(section.chunkIds)
    
    if all_chunks:
        chunks_str = ", ".join(sorted(all_chunks))
        lines.append(f"<!-- source-chunks: {chunks_str} -->")
        lines.append("")
    
    return "\n".join(lines)

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


def format_asset_reference(asset: AssetReference) -> str:
    """Format an asset reference for markdown.
    
    Args:
        asset: The asset reference
        
    Returns:
        Markdown string for the asset reference
    """
    if asset.type == "image":
        caption = asset.caption or f"Figure on page {asset.pageNumber}"
        return f"![{caption}]({asset.path})"
    else:  # table
        # Tables are embedded as HTML
        return f"<iframe src=\"{asset.path}\" title=\"{asset.caption or 'Table'}\" frameborder=\"0\" width=\"100%\"></iframe>"


def get_assets_for_section(
    section: "ConceptSection",
    asset_manifest: AssetManifest | None,
) -> list[AssetReference]:
    """Get all assets referenced by a concept section.
    
    Args:
        section: The concept section
        asset_manifest: The asset manifest
        
    Returns:
        List of asset references
    """
    if not asset_manifest:
        return []
    
    assets: list[AssetReference] = []
    seen_ids: set[str] = set()
    
    # First check explicit asset IDs
    for asset_id in getattr(section, "assetIds", []):
        for asset in asset_manifest.get_all_assets():
            if asset.id == asset_id and asset.id not in seen_ids:
                assets.append(asset)
                seen_ids.add(asset.id)
                break
    
    # Then check pages - include assets that fall on the section's pages
    for page in section.pageNumbers:
        page_assets = asset_manifest.get_assets_for_page(page)
        for asset in page_assets:
            if asset.id not in seen_ids:
                assets.append(asset)
                seen_ids.add(asset.id)
    
    return assets


def generate_asset_markdown(
    assets: list[AssetReference],
    section_name: str | None = None,
) -> str:
    """Generate markdown for displaying assets.
    
    Args:
        assets: List of assets to render
        section_name: Optional section name for context
        
    Returns:
        Markdown string for assets
    """
    if not assets:
        return ""
    
    lines: list[str] = []
    
    # Separate images and tables
    images = [a for a in assets if a.type == "image"]
    tables = [a for a in assets if a.type == "table"]
    
    # Render images
    for asset in images:
        ref = format_asset_reference(asset)
        if ref:
            lines.append("")
            lines.append(ref)
            lines.append("")
    
    # Render tables (as links to HTML files)
    for asset in tables:
        caption = asset.caption or f"Table on page {asset.pageNumber}"
        lines.append("")
        lines.append(f"📊 [{caption}]({asset.path})")
        lines.append("")
    
    return "\n".join(lines)


def generate_provenance_footer(
    doc_id: str,
    page_numbers: list[int],
    include_separator: bool = True,
) -> str:
    """Generate a provenance footer with source and page information.
    
    Args:
        doc_id: Source document ID
        page_numbers: List of page numbers
        include_separator: Whether to include a separator line before footer
        
    Returns:
        Markdown string for the footer
    """
    lines: list[str] = []
    
    if include_separator:
        lines.append("")
        lines.append("---")
    
    lines.append("")
    lines.append(f"**Source:** `{doc_id}`")
    
    if page_numbers:
        pages_str = ", ".join(str(p) for p in sorted(set(page_numbers)))
        lines.append(f"**Pages:** {pages_str}")
    
    lines.append("")
    
    return "\n".join(lines)


def generate_frontmatter(
    concept: ConceptInfo,
    asset_manifest: AssetManifest | None,
) -> str:
    """Generate YAML frontmatter for a concept markdown file.
    
    Args:
        concept: Concept metadata
        asset_manifest: Optional asset manifest for asset references
        
    Returns:
        YAML frontmatter string
    """
    lines: list[str] = []
    lines.append("---")
    lines.append(f'id: "{concept.id}"')
    lines.append(f'title: "{concept.title}"')
    lines.append(f'difficulty: "{concept.difficulty}"')
    lines.append(f'estimated_read_time: {concept.estimatedReadTime}')
    
    if concept.tags:
        lines.append(f"tags: [{', '.join(f'\"{t}\"' for t in concept.tags)}]")
    
    if concept.pageReferences:
        pages_str = ", ".join(str(p) for p in concept.pageReferences)
        lines.append(f"pages: [{pages_str}]")
    
    # Add asset references to frontmatter
    if asset_manifest:
        all_assets: list[AssetReference] = []
        seen_ids: set[str] = set()
        for section in concept.sections.values():
            section_assets = get_assets_for_section(section, asset_manifest)
            for asset in section_assets:
                if asset.id not in seen_ids:
                    all_assets.append(asset)
                    seen_ids.add(asset.id)
        
        if all_assets:
            lines.append("assets:")
            for asset in all_assets:
                lines.append(f'  - id: "{asset.id}"')
                lines.append(f'    type: "{asset.type}"')
                lines.append(f'    path: "{asset.path}"')
                lines.append(f'    page: {asset.pageNumber}')
                if asset.caption:
                    lines.append(f'    caption: "{asset.caption}"')
    
    lines.append("---")
    lines.append("")
    
    return "\n".join(lines)


def generate_pedagogical_markdown(
    concept: ConceptInfo,
    chunks: list[PdfIndexChunk],
    doc_id: str,
    asset_manifest: AssetManifest | None = None,
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
    - Asset references (images/tables)
    - Provenance footer
    
    Args:
        concept: Concept metadata in pedagogical format
        chunks: All available chunks
        doc_id: Source document ID
        asset_manifest: Optional asset manifest for inline assets
        
    Returns:
        Markdown formatted string
    """
    # ===================================================================
    # INTEGRATION: Check for pedagogical format (Added 2026-02-27)
    # ===================================================================
    if is_pedagogical_format(concept):
        # Use pedagogical markdown generation for richer output
        return generate_pedagogical_markdown(concept, chunks, doc_id, asset_manifest)
    
    # ===================================================================
    # LEGACY MODE: Standard markdown generation
    # ===================================================================
    lines: list[str] = []
    
    # Frontmatter
    lines.append(generate_frontmatter(concept, asset_manifest))
    
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
        
        # Add assets for this section
        if asset_manifest:
            assets = get_assets_for_section(learning_obj_section, asset_manifest)
            lines.append(generate_asset_markdown(assets, "learning_objectives"))
    
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
        
        # Add assets for this section
        if asset_manifest:
            assets = get_assets_for_section(definition_section, asset_manifest)
            lines.append(generate_asset_markdown(assets, "definition"))
        
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
        
        # Add assets for this section
        if asset_manifest:
            assets = get_assets_for_section(examples_section, asset_manifest)
            lines.append(generate_asset_markdown(assets, "examples"))
    
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
        
        # Add assets for this section
        if asset_manifest:
            assets = get_assets_for_section(mistakes_section, asset_manifest)
            lines.append(generate_asset_markdown(assets, "common_mistakes"))
    
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
    
    # Provenance footer
    all_pages: list[int] = []
    for section in concept.sections.values():
        all_pages.extend(section.pageNumbers)
    if concept.pageReferences:
        all_pages.extend(concept.pageReferences)
    
    lines.append(generate_provenance_footer(doc_id, sorted(set(all_pages))))
    
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
    asset_manifest: AssetManifest | None = None,
    include_provenance: bool = True,
    base_url: str = "",
) -> str:
    """
    Generate markdown content for a single concept.
    
    INTEGRATION (2026-02-27): Automatically detects and handles both standard
    and pedagogical formats. Now includes asset references and provenance footer.
    Phase 5: Added provenance support with YAML frontmatter and view source links.
    
    Args:
        concept: Concept metadata
        chunks: All available chunks (to look up text)
        doc_id: Source document ID
        asset_manifest: Optional asset manifest for inline assets
        include_provenance: Whether to include provenance metadata
        base_url: Base URL for source viewer links
        
    Returns:
        Markdown formatted string
    """
    # Check for pedagogical format
    if is_pedagogical_format(concept):
        return generate_pedagogical_markdown(concept, chunks, doc_id, asset_manifest)
    
    lines: list[str] = []
    
    # Frontmatter
    lines.append(generate_frontmatter(concept, asset_manifest))
    
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
        
        # Add inline assets for this section
        if asset_manifest:
            assets = get_assets_for_section(section, asset_manifest)
            if assets:
                lines.append(generate_asset_markdown(assets, section_name))
    
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
    
    # Provenance footer
    all_pages: list[int] = []
    for section in concept.sections.values():
        all_pages.extend(section.pageNumbers)
    if concept.pageReferences:
        all_pages.extend(concept.pageReferences)
    
    lines.append(generate_provenance_footer(doc_id, sorted(set(all_pages)), include_separator=True))
    
    # Footer
    lines.append("---")
    lines.append("")
    lines.append("*Content generated for SQL-Adapt Learning Platform*")
    lines.append("")
    
    return "\n".join(lines)


def save_concept_markdown(
    concept: ConceptInfo,
    chunks: list[PdfIndexChunk],
    doc_id: str,
    out_dir: Path,
    asset_manifest: AssetManifest | None = None,
    include_provenance: bool = True,
    base_url: str = "",
) -> Path:
    """Generate and save markdown for a concept.
    
    Args:
        concept: Concept to generate markdown for
        chunks: All available chunks
        doc_id: Source document ID
        out_dir: Output directory for markdown files
        asset_manifest: Optional asset manifest for inline assets
        include_provenance: Whether to include provenance metadata
        base_url: Base URL for source viewer links
        
    Returns:
        Path to saved file
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    
    markdown = generate_concept_markdown(
        concept, chunks, doc_id, asset_manifest,
        include_provenance=include_provenance,
        base_url=base_url,
    )
    
    file_path = out_dir / f"{concept.id}.md"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    
    return file_path


def generate_all_concept_markdowns(
    manifest: ConceptManifest,
    chunks: list[PdfIndexChunk],
    out_dir: Path,
    asset_manifest: AssetManifest | None = None,
    include_provenance: bool = True,
    base_url: str = "",
) -> list[Path]:
    """Generate markdown files for all concepts in manifest.
    
    Args:
        manifest: Concept manifest with all concepts
        chunks: All available chunks
        out_dir: Output directory
        asset_manifest: Optional asset manifest for inline assets
        include_provenance: Whether to include provenance metadata
        base_url: Base URL for source viewer links
        
    Returns:
        List of paths to generated files
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    
    generated: list[Path] = []
    for concept in manifest.concepts.values():
        file_path = save_concept_markdown(
            concept, chunks, manifest.sourceDocId, out_dir, asset_manifest,
            include_provenance=include_provenance,
            base_url=base_url,
        )
        generated.append(file_path)
    
    return generated


def generate_index_readme(
    manifest: ConceptManifest,
    out_path: Path,
    asset_manifest: AssetManifest | None = None,
) -> Path:
    """Generate README.md index of all concepts.
    
    Args:
        manifest: Concept manifest
        out_path: Output path for README
        asset_manifest: Optional asset manifest for statistics
        
    Returns:
        Path to saved file
    """
    lines: list[str] = [
        "# Concept Library",
        "",
        f"**Source:** {manifest.sourceDocId}",
        f"**Total Concepts:** {manifest.conceptCount}",
    ]
    
    # Add asset statistics if available
    if asset_manifest:
        total_images = len(asset_manifest.images)
        total_tables = len(asset_manifest.tables)
        if total_images > 0 or total_tables > 0:
            lines.append(f"**Total Images:** {total_images}")
            lines.append(f"**Total Tables:** {total_tables}")
    
    lines.extend([
        "",
        "## Concepts by Difficulty",
        "",
    ])
    
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
