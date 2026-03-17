from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import AssetManifest, AssetReference, ConceptInfo, ConceptManifest, ConceptSection, PdfIndexChunk


# ============================================================================
# Chunk Deduplication
# ============================================================================


def _chunk_similarity_hash(text: str) -> str:
    """Generate a similarity hash for chunk comparison.
    
    Normalizes the text to detect near-duplicate chunks.
    """
    import hashlib
    # Normalize: lowercase, collapse whitespace, strip
    normalized = ' '.join(text.lower().split())
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()


def deduplicate_chunk_list(chunks: list[PdfIndexChunk]) -> list[PdfIndexChunk]:
    """Remove duplicate chunks from a list while preserving order.
    
    Uses content hashing to detect chunks with identical or near-identical
    text content. This prevents duplication when chunks from overlapping
    regions are combined.
    
    Args:
        chunks: List of chunks potentially containing duplicates
        
    Returns:
        List of unique chunks in original order
    """
    if not chunks:
        return []
    
    seen_hashes: set[str] = set()
    unique_chunks: list[PdfIndexChunk] = []
    
    for chunk in chunks:
        chunk_hash = _chunk_similarity_hash(chunk.text)
        
        # Check for exact match
        if chunk_hash in seen_hashes:
            continue
        
        # Check for near-duplicates (truncated or extended versions)
        is_near_duplicate = False
        for seen_hash in list(seen_hashes):
            # Simple heuristic: if hashes share prefix, might be related
            if chunk_hash[:16] == seen_hash[:16]:
                # Additional check: one text contains the other
                normalized_chunk = ' '.join(chunk.text.lower().split())
                normalized_seen = ' '.join(next(
                    c.text for c in unique_chunks 
                    if _chunk_similarity_hash(c.text) == seen_hash
                ).lower().split())
                
                if normalized_chunk in normalized_seen or normalized_seen in normalized_chunk:
                    is_near_duplicate = True
                    break
        
        if not is_near_duplicate:
            seen_hashes.add(chunk_hash)
            unique_chunks.append(chunk)
    
    return unique_chunks


def _clean_and_deduplicate_section_texts(section_texts: list[str]) -> str:
    """Clean and deduplicate section texts before joining.
    
    Args:
        section_texts: List of text chunks from a section
        
    Returns:
        Cleaned, deduplicated text
    """
    from .clean import deduplicate_text, normalize_line_breaks
    
    if not section_texts:
        return ""
    
    # First pass: deduplicate at chunk level
    unique_texts: list[str] = []
    seen_previews: set[str] = set()
    
    for text in section_texts:
        # Create a preview (first 100 chars normalized)
        preview = ' '.join(text[:100].lower().split())
        
        # Check if we've seen this content
        is_duplicate = False
        for seen in seen_previews:
            if preview in seen or seen in preview:
                # Check length ratio
                len_ratio = min(len(preview), len(seen)) / max(len(preview), len(seen))
                if len_ratio > 0.9:
                    is_duplicate = True
                    break
        
        if not is_duplicate:
            seen_previews.add(preview)
            # Clean individual chunk
            cleaned = normalize_line_breaks(text)
            unique_texts.append(cleaned)
    
    # Join with paragraph separator
    full_text = "\n\n".join(unique_texts)
    
    # Second pass: deduplicate at paragraph level
    full_text = deduplicate_text(full_text, min_length=30)
    
    return full_text


# ============================================================================
# Section Titles for Student Learning
# ============================================================================

SECTION_TITLES = {
    "definition": "📚 Definition",
    "explanation": "💡 Explanation",
    "examples": "📝 Examples",
    "commonMistakes": "⚠️ Common Mistakes",
    "syntax": "🔤 Syntax",
    "notes": "📋 Notes",
    "tips": "✨ Tips",
    "practice": "🏋️ Practice",
}

# Pedagogical section titles for newer content
PEDAGOGICAL_SECTION_TITLES = {
    "learning_objectives": "🎯 Learning Objectives",
    "prerequisite_concepts": "📖 Prerequisites",
    "definition": "📚 What is This?",
    "examples": "📝 Examples",
    "common_mistakes": "⚠️ Common Mistakes",
    "practice_challenge": "🏋️ Practice Challenge",
    "practice_problems": "🎯 Related Practice Problems",
}


# ============================================================================
# Difficulty Indicators
# ============================================================================

DIFFICULTY_EMOJI = {
    "beginner": "🟢",
    "intermediate": "🟡",
    "advanced": "🔴",
}

DIFFICULTY_DESCRIPTION = {
    "beginner": "Beginner - No prior knowledge needed",
    "intermediate": "Intermediate - Some SQL experience recommended",
    "advanced": "Advanced - Solid SQL foundation required",
}


# ============================================================================
# Helper Functions
# ============================================================================

def get_chunk_by_id(chunks: list[PdfIndexChunk], chunk_id: str) -> PdfIndexChunk | None:
    """Find a chunk by its ID."""
    for chunk in chunks:
        if chunk.chunkId == chunk_id:
            return chunk
    return None


def is_pedagogical_format(concept: ConceptInfo) -> bool:
    """Check if a concept is in the new pedagogical format."""
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
    
    return False


def format_sql_code(text: str) -> str:
    """Format SQL code with proper markdown syntax.
    
    Identifies SQL code blocks and formats them with syntax highlighting.
    """
    lines = text.split('\n')
    result = []
    in_sql_block = False
    sql_buffer = []
    
    sql_keywords = ['SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 
                    'CREATE', 'ALTER', 'DROP', 'JOIN', 'GROUP', 'ORDER', 'HAVING']
    
    for line in lines:
        stripped = line.strip().upper()
        
        # Check if this looks like SQL
        is_sql = any(stripped.startswith(kw) for kw in sql_keywords)
        is_sql = is_sql or (stripped and '=' in stripped and any(kw in stripped for kw in sql_keywords))
        
        if is_sql and not in_sql_block:
            # Start SQL block
            in_sql_block = True
            sql_buffer = [line]
        elif is_sql and in_sql_block:
            # Continue SQL block
            sql_buffer.append(line)
        elif not is_sql and in_sql_block:
            # End SQL block
            if sql_buffer:
                result.append("```sql")
                result.extend(sql_buffer)
                result.append("```")
                sql_buffer = []
            in_sql_block = False
            result.append(line)
        else:
            result.append(line)
    
    # Handle SQL block at end
    if in_sql_block and sql_buffer:
        result.append("```sql")
        result.extend(sql_buffer)
        result.append("```")
    
    return '\n'.join(result)


def format_table_output(text: str) -> str:
    """Format table output sections.
    
    Identifies result tables and formats them as markdown tables or code blocks.
    """
    lines = text.split('\n')
    result = []
    in_table = False
    table_buffer = []
    
    for line in lines:
        # Detect table-like output
        has_table_chars = '|' in line or '---' in line or line.strip().startswith('►')
        looks_like_data = any(c.isdigit() for c in line) and len(line.split()) >= 2
        
        if (has_table_chars or looks_like_data) and not in_table:
            in_table = True
            table_buffer = [line]
        elif (has_table_chars or looks_like_data or line.strip() == '') and in_table:
            table_buffer.append(line)
        elif in_table:
            # End table
            if table_buffer:
                result.append("```")
                result.extend(table_buffer)
                result.append("```")
                table_buffer = []
            in_table = False
            result.append(line)
        else:
            result.append(line)
    
    # Handle table at end
    if in_table and table_buffer:
        result.append("```")
        result.extend(table_buffer)
        result.append("```")
    
    return '\n'.join(result)


def clean_chunk_text(text: str) -> str:
    """Clean and format chunk text for student reading.
    
    This function:
    1. Formats SQL code blocks
    2. Formats table outputs
    3. Removes redundant whitespace
    4. Fixes common formatting issues
    """
    # Format SQL and tables
    text = format_sql_code(text)
    text = format_table_output(text)
    
    # Clean up multiple blank lines
    while '\n\n\n' in text:
        text = text.replace('\n\n\n', '\n\n')
    
    return text.strip()


def generate_frontmatter(
    concept: ConceptInfo,
    asset_manifest: AssetManifest | None,
) -> str:
    """Generate YAML frontmatter for a concept markdown file."""
    lines: list[str] = []
    lines.append("---")
    lines.append(f'id: "{concept.id}"')
    lines.append(f'title: "{concept.title}"')
    lines.append(f'difficulty: "{concept.difficulty}"')
    lines.append(f'estimated_read_time: {concept.estimatedReadTime}')
    
    if concept.tags:
        tags_quoted = [f'"{t}"' for t in concept.tags]
        tags_str = ', '.join(tags_quoted)
        lines.append(f"tags: [{tags_str}]")
    
    if concept.pageReferences:
        pages_str = ", ".join(str(p) for p in concept.pageReferences)
        lines.append(f'pages: [{pages_str}]')
    
    # Add reading time estimate in minutes
    lines.append(f'reading_time: "{concept.estimatedReadTime} min read"')
    
    lines.append("---")
    lines.append("")
    
    return "\n".join(lines)


def _get_asset_path_and_page(asset: Any) -> tuple[str, int]:
    """Get path and page number from asset (handles both AssetReference and ExtractedAsset)."""
    if hasattr(asset, 'path'):
        return asset.path, asset.pageNumber
    elif hasattr(asset, 'get_relative_path'):
        return asset.get_relative_path(), asset.page
    else:
        raise ValueError(f"Unknown asset type: {type(asset)}")


def format_asset_reference(asset: AssetReference | Any) -> str:
    """Format an asset reference for markdown."""
    if hasattr(asset, 'path'):
        path = asset.path
        page = asset.pageNumber
    elif hasattr(asset, 'get_relative_path'):
        path = asset.get_relative_path()
        page = asset.page
    else:
        raise ValueError(f"Unknown asset type: {type(asset)}")
    
    if asset.type == "image":
        caption = asset.caption or f"Figure on page {page}"
        return f"![{caption}]({path})"
    else:  # table
        return f"📊 [{asset.caption or 'Table'}]({path})"


def get_assets_for_section(
    section: "ConceptSection",
    asset_manifest: AssetManifest | None,
) -> list[AssetReference]:
    """Get all assets referenced by a concept section."""
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
    assets: list[Any],
    section_name: str | None = None,
) -> str:
    """Generate markdown for displaying assets."""
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
    
    # Render tables
    for asset in tables:
        path, page = _get_asset_path_and_page(asset)
        caption = asset.caption or f"Table on page {page}"
        lines.append("")
        lines.append(f"📊 [{caption}]({path})")
        lines.append("")
    
    return "\n".join(lines)


def generate_provenance_footer(
    doc_id: str,
    page_numbers: list[int],
    include_separator: bool = True,
) -> str:
    """Generate a provenance footer with source and page information."""
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


def format_page_links(page_numbers: list[int], doc_id: str) -> str:
    """Create markdown page reference links."""
    if not page_numbers:
        return ""
    
    pages_str = ", ".join(f"Page {p}" for p in sorted(set(page_numbers)))
    return f"📖 *Source: {pages_str}*"


# ============================================================================
# Main Markdown Generation
# ============================================================================

def generate_concept_markdown(
    concept: ConceptInfo,
    chunks: list[PdfIndexChunk],
    doc_id: str,
    asset_manifest: AssetManifest | None = None,
    include_provenance: bool = True,
    base_url: str = "",
) -> str:
    """Generate markdown content for a single concept optimized for student learning.
    
    Features:
    - Clean, readable formatting
    - SQL code syntax highlighting
    - Difficulty indicators with descriptions
    - Clear section structure
    - Related concept links
    - Reading time estimates
    
    Args:
        concept: Concept metadata
        chunks: All available chunks (to look up text)
        doc_id: Source document ID
        asset_manifest: Optional asset manifest for inline assets
        include_provenance: Whether to include provenance metadata
        base_url: Base URL for source viewer links
        
    Returns:
        Markdown formatted string optimized for student learning
    """
    # Check for pedagogical format
    if is_pedagogical_format(concept):
        return generate_pedagogical_markdown(concept, chunks, doc_id, asset_manifest)
    
    lines: list[str] = []
    
    # Frontmatter
    lines.append(generate_frontmatter(concept, asset_manifest))
    
    # Title with concept ID for reference
    lines.append(f"# {concept.title}")
    lines.append("")
    
    # Metadata section with enhanced difficulty indicator
    difficulty_emoji = DIFFICULTY_EMOJI.get(concept.difficulty, "⚪")
    difficulty_desc = DIFFICULTY_DESCRIPTION.get(concept.difficulty, concept.difficulty.title())
    
    lines.append(f"{difficulty_emoji} **Difficulty:** {difficulty_desc}")
    lines.append(f"⏱️ **Estimated Read Time:** {concept.estimatedReadTime} minutes")
    lines.append("")
    
    # Definition/overview from metadata
    if concept.definition:
        lines.append("## 📚 Overview")
        lines.append("")
        lines.append(concept.definition)
        lines.append("")
    
    # Page references
    page_link = format_page_links(concept.pageReferences, doc_id)
    if page_link:
        lines.append(page_link)
        lines.append("")
    
    # Sections with enhanced formatting
    for section_name, section in concept.sections.items():
        section_title = SECTION_TITLES.get(section_name, section_name.replace("-", " ").title())
        lines.append(f"## {section_title}")
        lines.append("")
        
        # Get chunk texts for this section
        section_chunks: list[PdfIndexChunk] = []
        for chunk_id in section.chunkIds:
            chunk = get_chunk_by_id(chunks, chunk_id)
            if chunk:
                section_chunks.append(chunk)
        
        # Deduplicate chunks to remove overlap duplicates
        section_chunks = deduplicate_chunk_list(section_chunks)
        
        # Clean and deduplicate texts
        section_texts: list[str] = []
        for chunk in section_chunks:
            cleaned_text = clean_chunk_text(chunk.text)
            if cleaned_text.strip():
                section_texts.append(cleaned_text)
        
        if section_texts:
            # Clean and deduplicate before joining
            full_text = _clean_and_deduplicate_section_texts(section_texts)
            lines.append(full_text)
        else:
            lines.append("*Content not available in source.*")
        
        lines.append("")
        
        # Add inline assets for this section
        if asset_manifest:
            assets = get_assets_for_section(section, asset_manifest)
            if assets:
                lines.append(generate_asset_markdown(assets, section_name))
    
    # Related concepts with better formatting
    if concept.relatedConcepts:
        lines.append("## 🔗 Related Concepts")
        lines.append("")
        lines.append("You may also want to learn about:")
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
    
    lines.append(generate_provenance_footer(doc_id, sorted(set(all_pages)), include_separator=True))
    
    # Student-friendly footer
    lines.append("---")
    lines.append("")
    lines.append("📚 *This content is part of the SQL-Adapt Learning Platform*")
    lines.append("")
    lines.append("**Need help?** Review the related concepts above or check the textbook pages listed in the source.")
    lines.append("")
    
    return "\n".join(lines)


def generate_pedagogical_markdown(
    concept: ConceptInfo,
    chunks: list[PdfIndexChunk],
    doc_id: str,
    asset_manifest: AssetManifest | None = None,
) -> str:
    """Generate markdown for a concept in the pedagogical format."""
    lines: list[str] = []
    
    # Frontmatter
    lines.append(generate_frontmatter(concept, asset_manifest))
    
    # Title
    lines.append(f"# {concept.title}")
    lines.append("")
    
    # Metadata with difficulty and time estimate
    difficulty_emoji = DIFFICULTY_EMOJI.get(concept.difficulty, "⚪")
    lines.append(f"{difficulty_emoji} **Difficulty:** {concept.difficulty.title()}")
    lines.append(f"⏱️ **Estimated Read Time:** {concept.estimatedReadTime} minutes")
    lines.append("")
    
    # Learning Objectives
    learning_obj_section = concept.sections.get("learning_objectives")
    if learning_obj_section:
        lines.append("## 🎯 Learning Objectives")
        lines.append("")
        objectives = getattr(learning_obj_section, "items", [])
        if not objectives and hasattr(learning_obj_section, "text"):
            objectives = learning_obj_section.text.split("\n")
        for obj in objectives:
            if obj.strip():
                lines.append(f"- {obj.strip()}")
        lines.append("")
    
    # Prerequisites
    prereq_section = concept.sections.get("prerequisite_concepts")
    if prereq_section:
        lines.append("## 📖 Prerequisites")
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
    
    # Definition
    definition_section = concept.sections.get("definition")
    if definition_section:
        lines.append("## 📚 What is This?")
        lines.append("")
        if hasattr(definition_section, "text"):
            lines.append(clean_chunk_text(definition_section.text))
        elif hasattr(definition_section, "concept_explanation"):
            lines.append(definition_section.concept_explanation)
        lines.append("")
    
    # Examples with pedagogical structure
    examples_section = concept.sections.get("examples")
    if examples_section:
        lines.append("## 📝 Examples")
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
                sql = ex.get("sql", "") if isinstance(ex, dict) else ""
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
                    lines.append(f"```\n{expected}\n```")
                    lines.append("")
    
    # Common Mistakes
    mistakes_section = concept.sections.get("common_mistakes")
    if mistakes_section:
        lines.append("## ⚠️ Common Mistakes")
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
        lines.append("## 🏋️ Practice Challenge")
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
                lines.append("<summary>✨ Click to see solution</summary>")
                lines.append("")
                lines.append("```sql")
                lines.append(solution)
                lines.append("```")
                lines.append("")
                if explanation:
                    lines.append(f"**Explanation:** {explanation}")
                lines.append("</details>")
                lines.append("")
    
    # Related concepts
    if concept.relatedConcepts:
        lines.append("## 🔗 Related Concepts")
        lines.append("")
        for related_id in concept.relatedConcepts:
            lines.append(f"- [{related_id}](./{related_id}.md)")
        lines.append("")
    
    # Tags
    if concept.tags:
        lines.append("---")
        lines.append("")
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
    
    lines.append(generate_provenance_footer(doc_id, sorted(set(all_pages)), include_separator=True))
    
    # Student-friendly footer
    lines.append("---")
    lines.append("")
    lines.append("📚 *This content is part of the SQL-Adapt Learning Platform*")
    lines.append("")
    lines.append("**Need help?** Review the related concepts above or check the textbook pages listed in the source.")
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
    """Generate and save markdown for a concept."""
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
    """Generate markdown files for all concepts in manifest."""
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
    """Generate README.md index of all concepts."""
    lines: list[str] = [
        "# 📚 SQL Concept Library",
        "",
        f"**Source:** `{manifest.sourceDocId}`",
        f"**Total Concepts:** {manifest.conceptCount}",
    ]
    
    # Add asset statistics if available
    if asset_manifest:
        total_images = len(asset_manifest.images)
        total_tables = len(asset_manifest.tables)
        if total_images > 0 or total_tables > 0:
            lines.append(f"**Images:** {total_images} | **Tables:** {total_tables}")
    
    lines.extend([
        "",
        "Welcome to the SQL Learning Library! Browse concepts by difficulty level below.",
        "",
        "## 🎯 Quick Navigation",
        "",
        "- 🟢 [Beginner Concepts](#-beginner) - Start here if you're new to SQL",
        "- 🟡 [Intermediate Concepts](#-intermediate) - Build on your foundation",
        "- 🔴 [Advanced Concepts](#-advanced) - Master complex topics",
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
        
        emoji = DIFFICULTY_EMOJI[difficulty]
        desc = DIFFICULTY_DESCRIPTION[difficulty]
        lines.append(f"### {emoji} {difficulty.title()}")
        lines.append(f"*{desc}*")
        lines.append("")
        
        for concept in sorted(concepts, key=lambda c: c.title):
            lines.append(f"- [{concept.title}](./{concept.id}.md) - ⏱️ {concept.estimatedReadTime} min")
        lines.append("")
    
    # Full list
    lines.append("---")
    lines.append("")
    lines.append("## 📑 All Concepts (Alphabetical)")
    lines.append("")
    
    for concept_id in sorted(manifest.concepts.keys()):
        concept = manifest.concepts[concept_id]
        emoji = DIFFICULTY_EMOJI.get(concept.difficulty, "⚪")
        lines.append(f"- {emoji} [{concept.title}](./{concept.id}.md)")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Happy learning! 🚀*")
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        f.write("\n")
    
    return out_path
