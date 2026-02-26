"""
Enhanced PDF extraction using Marker for better text quality.

This module provides an alternative to extract.py that uses Marker
for high-quality PDF to markdown conversion with structure preservation.

Marker benefits:
- Cleaner text extraction (fewer OCR artifacts)
- Preserves document structure (sections, lists, tables)
- Removes headers/footers automatically
- Better formatting for educational content
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .models import PdfSourceDoc

# Optional Marker import
try:
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.output import text_from_rendered
    MARKER_AVAILABLE = True
except ImportError:
    MARKER_AVAILABLE = False


def extract_with_marker(
    pdf_path: Path,
    use_llm: bool = False,
) -> tuple[str, list[dict], dict]:
    """
    Extract text from PDF using Marker.
    
    Args:
        pdf_path: Path to PDF file
        use_llm: Whether to use LLM for enhanced accuracy (slower)
        
    Returns:
        Tuple of (full_text, pages_metadata, metadata)
        
    Raises:
        ImportError: If marker-pdf is not installed
    """
    if not MARKER_AVAILABLE:
        raise ImportError(
            "marker-pdf not installed. "
            "Install with: pip install marker-pdf"
        )
    
    # Configure converter
    config = {}
    if use_llm:
        config["use_llm"] = True
    
    converter = PdfConverter(
        artifact_dict=create_model_dict(),
        config=config if config else None,
    )
    
    # Convert PDF
    rendered = converter(str(pdf_path))
    
    # Extract markdown and metadata
    markdown, _, images = text_from_rendered(rendered)
    
    # Parse into pages/chunks
    pages = _parse_markdown_to_pages(markdown, rendered)
    
    metadata = {
        "total_pages": len(pages),
        "has_images": len(images) > 0,
        "extraction_method": "marker" + ("+llm" if use_llm else ""),
    }
    
    return markdown, pages, metadata


def _parse_markdown_to_pages(markdown: str, rendered: Any) -> list[dict]:
    """
    Parse Marker markdown into page-based chunks.
    
    Marker doesn't provide explicit page boundaries in markdown,
    so we use heuristics or the JSON output for pagination.
    """
    pages = []
    
    # Try to get page info from rendered children
    if hasattr(rendered, 'children'):
        for page_idx, page_block in enumerate(rendered.children):
            page_text = page_block.html if hasattr(page_block, 'html') else ""
            
            # Clean HTML tags if present
            page_text = re.sub(r'<[^>]+>', '', page_text)
            
            pages.append({
                "page_number": page_idx + 1,
                "text": page_text,
                "block_types": _get_block_types(page_block),
            })
    else:
        # Fallback: split by page markers or use whole text
        # Marker markdown may have implicit page breaks
        page_sections = re.split(r'\n\n---+\s*\n\n', markdown)
        
        for idx, section in enumerate(page_sections):
            if section.strip():
                pages.append({
                    "page_number": idx + 1,
                    "text": section.strip(),
                    "block_types": ["text"],
                })
    
    return pages


def _get_block_types(page_block: Any) -> list[str]:
    """Extract block types from page for structure info."""
    types = []
    
    if hasattr(page_block, 'children') and page_block.children:
        for child in page_block.children:
            block_type = getattr(child, 'block_type', None)
            if block_type:
                types.append(str(block_type))
    
    return list(set(types)) if types else ["text"]


def chunk_markdown_by_sections(
    markdown: str,
    doc_id: str,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> list[dict]:
    """
    Chunk markdown text by sections for educational use.
    
    Unlike simple word-window chunking, this preserves:
    - Section headers with content
    - Code blocks together
    - List items with context
    """
    chunks = []
    chunk_idx = 0
    
    # Split by headers (##, ###)
    sections = re.split(r'\n(?=##+\s)', markdown)
    
    for section in sections:
        if not section.strip():
            continue
        
        # Extract section title
        title_match = re.match(r'##+\s*(.+?)\n', section)
        section_title = title_match.group(1) if title_match else "Untitled"
        
        # If section is small enough, keep as one chunk
        if len(section) <= chunk_size:
            chunks.append({
                "chunkId": f"{doc_id}:section{chunk_idx}",
                "docId": doc_id,
                "section": section_title,
                "text": section.strip(),
                "char_count": len(section),
            })
            chunk_idx += 1
        else:
            # Split large sections by paragraphs
            paragraphs = section.split('\n\n')
            current_chunk = []
            current_size = 0
            
            for para in paragraphs:
                para_size = len(para)
                
                if current_size + para_size > chunk_size and current_chunk:
                    # Save current chunk
                    chunks.append({
                        "chunkId": f"{doc_id}:section{chunk_idx}",
                        "docId": doc_id,
                        "section": section_title,
                        "text": '\n\n'.join(current_chunk).strip(),
                        "char_count": current_size,
                    })
                    chunk_idx += 1
                    
                    # Start new chunk with overlap
                    overlap_text = '\n\n'.join(current_chunk[-2:]) if len(current_chunk) >= 2 else current_chunk[0]
                    current_chunk = [overlap_text, para]
                    current_size = len(overlap_text) + para_size
                else:
                    current_chunk.append(para)
                    current_size += para_size
            
            # Don't forget last chunk
            if current_chunk:
                chunks.append({
                    "chunkId": f"{doc_id}:section{chunk_idx}",
                    "docId": doc_id,
                    "section": section_title,
                    "text": '\n\n'.join(current_chunk).strip(),
                    "char_count": current_size,
                })
                chunk_idx += 1
    
    return chunks


def generate_educational_notes(
    section_text: str,
    concept_name: str,
    llm_client: Any | None = None,
) -> dict[str, Any]:
    """
    Transform extracted text into educational notes using LLM.
    
    This is the key function that converts raw textbook content
    into student-friendly learning material.
    """
    # Default template if no LLM available
    if llm_client is None:
        return {
            "concept": concept_name,
            "raw_text": section_text[:2000],
            "note": "LLM not available. Raw text shown.",
        }
    
    prompt = f"""Transform this textbook section into structured educational content.

CONCEPT: {concept_name}

TEXT:
{section_text[:4000]}

Create educational notes with:
1. **Definition**: Clear 1-2 sentence explanation
2. **Explanation**: Detailed walkthrough with analogies
3. **Key Points**: 3-5 bullet points of essential knowledge
4. **SQL Examples**: Concrete, runnable SQL code examples
5. **Common Mistakes**: What students typically get wrong
6. **Practice Question**: One question with solution

Format as JSON:
{{
  "concept": "name",
  "definition": "...",
  "explanation": "...",
  "key_points": ["..."],
  "examples": [{{"title": "...", "code": "...", "explanation": "..."}}],
  "common_mistakes": [{{"mistake": "...", "correction": "..."}}],
  "practice": {{"question": "...", "solution": "..."}}
}}
"""
    
    try:
        # This would call your LLM (OpenAI, Claude, etc.)
        # response = llm_client.generate(prompt)
        # notes = json.loads(response)
        
        # For now, return template
        return {
            "concept": concept_name,
            "definition": "Extracted from textbook section",
            "explanation": section_text[:1000],
            "key_points": ["Point 1", "Point 2", "Point 3"],
            "examples": [],
            "common_mistakes": [],
            "practice": {},
        }
    except Exception as e:
        return {
            "concept": concept_name,
            "error": str(e),
            "raw_text": section_text[:1000],
        }


def compare_extraction_methods(pdf_path: Path) -> dict[str, Any]:
    """
    Compare PyMuPDF vs Marker extraction quality.
    
    Useful for evaluating if Marker improves output.
    """
    # PyMuPDF extraction (current method)
    import fitz
    
    doc = fitz.open(str(pdf_path))
    pymupdf_text = ""
    for page in doc:
        pymupdf_text += page.get_text()
    doc.close()
    
    # Marker extraction
    marker_text = ""
    marker_pages = []
    
    if MARKER_AVAILABLE:
        try:
            markdown, pages, _ = extract_with_marker(pdf_path)
            marker_text = markdown
            marker_pages = pages
        except Exception as e:
            marker_text = f"Error: {e}"
    else:
        marker_text = "Marker not installed"
    
    return {
        "pymupdf": {
            "text": pymupdf_text[:2000],
            "char_count": len(pymupdf_text),
        },
        "marker": {
            "text": marker_text[:2000],
            "char_count": len(marker_text),
            "pages": len(marker_pages),
        },
    }


# CLI for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python extract_marker.py <pdf_path> [--compare]")
        sys.exit(1)
    
    pdf_path = Path(sys.argv[1])
    compare = "--compare" in sys.argv
    
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        sys.exit(1)
    
    if compare:
        result = compare_extraction_methods(pdf_path)
        print(json.dumps(result, indent=2))
    else:
        if not MARKER_AVAILABLE:
            print("Error: marker-pdf not installed")
            print("Install with: pip install marker-pdf")
            sys.exit(1)
        
        markdown, pages, metadata = extract_with_marker(pdf_path)
        print(f"Extracted {len(pages)} pages")
        print(f"Metadata: {metadata}")
        print("\n--- Sample ---\n")
        print(markdown[:2000])
