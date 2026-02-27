from __future__ import annotations

import json
import re
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import ConceptInfo, ConceptManifest, ConceptSection, PdfIndexChunk


def _match_pdf_to_textbook(pdf_path: Path, textbooks: dict[str, Any]) -> str | None:
    """Match PDF filename to textbook ID using dynamic keyword extraction.
    
    Automatically detects matches for any textbook by:
    1. Extracting keywords from textbook ID (splitting on -, _, .)
    2. Matching against PDF filename
    3. Using title from textbook config
    4. Checking for partial word matches (e.g., "murach" matches "murachs")
    
    Works with any new textbooks added to concepts.yaml without code changes.
    
    Args:
        pdf_path: Path to the PDF file
        textbooks: Dictionary of textbook configurations
        
    Returns:
        Matching textbook ID or None if no match found
    """
    pdf_name = pdf_path.stem.lower()
    
    # Common words to ignore in matching
    stop_words = {'the', 'and', 'for', 'with', 'edition', 'ed', 'book', 'textbook', 
                  'introduction', 'to', 'of', 'in', 'a', 'an', 'vol', 'volume',
                  '3rd', '3e', 'third', '2nd', 'second', '4th', 'fourth', '1st', 'first'}
    
    best_match = None
    best_score = 0
    
    def extract_keywords(text: str) -> set[str]:
        """Extract meaningful keywords from text."""
        words = set(re.split(r'[-_\.\s\(\),]+', text.lower()))
        return {w for w in words if len(w) > 2 and w not in stop_words}
    
    def partial_match(word1: str, word2: str) -> bool:
        """Check if two words partially match (one contains the other)."""
        if word1 == word2:
            return True
        if len(word1) >= 5 and len(word2) >= 5:
            # For longer words, check if one contains the other
            if word1 in word2 or word2 in word1:
                return True
        return False
    
    def count_partial_matches(keywords1: set[str], keywords2: set[str]) -> int:
        """Count matching keywords allowing for partial matches."""
        matches = 0
        for k1 in keywords1:
            for k2 in keywords2:
                if partial_match(k1, k2):
                    matches += 1
                    break
        return matches
    
    pdf_keywords = extract_keywords(pdf_name)
    
    for textbook_id, textbook_config in textbooks.items():
        score = 0
        textbook_id_lower = textbook_id.lower()
        
        # 1. Exact match or substring match (highest priority)
        if textbook_id_lower in pdf_name:
            score = 100
        elif pdf_name in textbook_id_lower:
            score = 95
        else:
            # 2. Extract keywords from textbook ID
            id_keywords = extract_keywords(textbook_id_lower)
            
            # Count partial keyword matches
            if id_keywords and pdf_keywords:
                id_matches = count_partial_matches(id_keywords, pdf_keywords)
                score = max(score, (id_matches / len(id_keywords)) * 60)
            
            # 3. Check textbook title
            title = ""
            if isinstance(textbook_config, dict):
                title = textbook_config.get("title", "").lower()
            
            if title:
                title_keywords = extract_keywords(title)
                if title_keywords and pdf_keywords:
                    title_match_count = count_partial_matches(title_keywords, pdf_keywords)
                    score = max(score, (title_match_count / len(title_keywords)) * 50)
                
                # Bonus: check if any significant title word is in PDF name
                for title_word in title_keywords:
                    if len(title_word) >= 6:  # Significant words only
                        if title_word in pdf_name or any(
                            partial_match(title_word, pdf_word) for pdf_word in pdf_keywords
                        ):
                            score += 10
        
        # Keep best match
        if score > best_score and score >= 20:  # Minimum 20% match threshold
            best_score = score
            best_match = textbook_id
    
    return best_match


def load_concepts_config(config_path: Path, pdf_path: Path | None = None) -> dict[str, Any]:
    """Load concept configuration from YAML file.
    
    Supports both old flat format (with 'concepts' key) and new textbooks format
    (with 'textbooks' key containing nested concepts).
    
    For textbooks format, auto-detects which textbook to use based on PDF filename.
    
    Args:
        config_path: Path to concepts.yaml file
        pdf_path: Optional path to PDF file for textbook auto-detection
        
    Returns:
        Dictionary with concepts configuration (normalized to have 'concepts' key)
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Concepts config not found: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    if not config:
        raise ValueError("Invalid concepts config: empty file")
    
    # Handle new textbooks format (schema_version >= 2.0)
    if "textbooks" in config:
        textbooks = config["textbooks"]
        
        # Try to match PDF to specific textbook
        if pdf_path is not None:
            matched_textbook = _match_pdf_to_textbook(pdf_path, textbooks)
            if matched_textbook and matched_textbook in textbooks:
                textbook = textbooks[matched_textbook]
                if "concepts" in textbook:
                    config["concepts"] = textbook["concepts"]
                    config["matched_textbook"] = matched_textbook
                    return config
        
        # No match found or no PDF provided - merge all concepts from all textbooks
        all_concepts = {}
        for textbook_id, textbook in textbooks.items():
            if "concepts" in textbook:
                for concept_id, concept_data in textbook["concepts"].items():
                    all_concepts[concept_id] = concept_data
        config["concepts"] = all_concepts
    
    # Validate we have concepts
    if "concepts" not in config:
        raise ValueError("Invalid concepts config: must have 'concepts' or 'textbooks' key")
    
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
