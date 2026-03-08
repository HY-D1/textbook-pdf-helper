"""
Section-Aware Extraction System for PDF Content.

This module segments PDF content by pedagogical structure (not just pages)
and creates typed spans with evidence tracking. It transforms PDF content
into an instructional unit graph for adaptive learning systems.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from .clean import normalize_text


# =============================================================================
# BLOCK TYPE ENUMERATION
# =============================================================================

class BlockType(Enum):
    """
    Types of content blocks in pedagogical documents.
    
    Each type represents a distinct instructional element that serves
    a specific purpose in the learning experience.
    """
    HEADING = auto()           # Main section titles (chapter/section level)
    SUBHEADING = auto()        # Subsection titles
    EXPLANATORY_PROSE = auto() # Explanatory text paragraphs
    SQL_CODE = auto()          # SQL code examples and queries
    OUTPUT_TABLE = auto()      # Tabular output/results
    FIGURE = auto()            # Figures with captions
    DIAGRAM = auto()           # Diagrams and visual representations
    EXERCISE = auto()          # Practice exercises and problems
    SIDEBAR = auto()           # Side notes, tips, warnings
    SUMMARY = auto()           # Chapter/section summaries
    GLOSSARY = auto()          # Glossary entries and definitions
    ADMIN_TEXT = auto()        # Administrative content (TOC, copyright, etc.)
    UNKNOWN = auto()           # Unclassified content


# =============================================================================
# CONTENT BLOCK DATA CLASS
# =============================================================================

@dataclass
class ContentBlock:
    """
    A typed content block with provenance and metadata.
    
    Content blocks are the fundamental units of the instructional unit graph.
    Each block has a unique ID, type, location information, and relationships
    to other blocks (for hierarchical structure).
    """
    # Identity
    block_id: str                          # Unique ID like "{doc_id}:p{page}:b{index}"
    block_type: BlockType                  # Type of content
    
    # Location
    page_number: int                       # 1-indexed page number
    char_start: int                        # Character offset start in page
    char_end: int                          # Character offset end in page
    
    # Content
    text_content: str                      # The actual text content
    
    # Quality
    confidence: float = 1.0                # OCR/extraction confidence (0.0-1.0)
    
    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    # Contains:
    #   - heading_level: int (for HEADING/SUBHEADING)
    #   - language: str (for SQL_CODE)
    #   - font_name: str
    #   - font_size: float
    #   - is_bold: bool
    #   - is_italic: bool
    #   - bbox: tuple[float, float, float, float] (bounding box)
    
    # Hierarchy
    parent_block_id: str | None = None     # Parent block for hierarchical structure
    child_block_ids: list[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate block data after initialization."""
        # Ensure confidence is in valid range
        self.confidence = max(0.0, min(1.0, self.confidence))
    
    @property
    def char_length(self) -> int:
        """Return the character length of this block."""
        return self.char_end - self.char_start
    
    @property
    def is_structural(self) -> bool:
        """Check if this is a structural element (heading)."""
        return self.block_type in (BlockType.HEADING, BlockType.SUBHEADING)
    
    @property
    def is_code(self) -> bool:
        """Check if this is a code block."""
        return self.block_type == BlockType.SQL_CODE
    
    @property
    def is_teaching_content(self) -> bool:
        """Check if this block contains teaching content (not admin)."""
        return self.block_type not in (BlockType.ADMIN_TEXT, BlockType.UNKNOWN)
    
    def get_heading_level(self) -> int | None:
        """Get heading level if this is a heading block."""
        if self.block_type in (BlockType.HEADING, BlockType.SUBHEADING):
            return self.metadata.get("heading_level")
        return None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert block to dictionary representation."""
        return {
            "block_id": self.block_id,
            "block_type": self.block_type.name,
            "page_number": self.page_number,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "text_content": self.text_content,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "parent_block_id": self.parent_block_id,
            "child_block_ids": self.child_block_ids,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContentBlock:
        """Create a ContentBlock from a dictionary."""
        return cls(
            block_id=data["block_id"],
            block_type=BlockType[data["block_type"]],
            page_number=data["page_number"],
            char_start=data["char_start"],
            char_end=data["char_end"],
            text_content=data["text_content"],
            confidence=data.get("confidence", 1.0),
            metadata=data.get("metadata", {}),
            parent_block_id=data.get("parent_block_id"),
            child_block_ids=data.get("child_block_ids", []),
        )


# =============================================================================
# SECTION EXTRACTOR CLASS
# =============================================================================

class SectionExtractor:
    """
    Extracts content blocks from PDFs with pedagogical structure awareness.
    
    Uses PyMuPDF (fitz) for extraction with layout preservation, detecting
    headings by font size/boldness, code blocks by font characteristics,
    and tables by structure.
    """
    
    # Font size thresholds (relative to body text)
    HEADING_SIZE_THRESHOLD = 1.25      # 25% larger than body
    SUBHEADING_SIZE_THRESHOLD = 1.15   # 15% larger than body
    
    # Minimum text length for valid blocks
    MIN_BLOCK_LENGTH = 3
    MAX_BLOCK_LENGTH = 10000
    
    # Code detection patterns
    SQL_KEYWORDS = [
        r'\bSELECT\b', r'\bFROM\b', r'\bWHERE\b', r'\bINSERT\b',
        r'\bUPDATE\b', r'\bDELETE\b', r'\bCREATE\b', r'\bDROP\b',
        r'\bALTER\b', r'\bJOIN\b', r'\bINNER\b', r'\bOUTER\b',
        r'\bLEFT\b', r'\bRIGHT\b', r'\bGROUP\b', r'\bORDER\b',
        r'\bHAVING\b', r'\bLIMIT\b', r'\bUNION\b', r'\bVALUES\b',
    ]
    
    # Monospace font indicators
    MONOSPACE_FONTS = [
        'courier', 'monaco', 'consolas', 'monospace', 'mono',
        'lucida console', 'andale mono', 'fira code', 'source code',
    ]
    
    # Table detection patterns
    TABLE_PATTERNS = [
        r'^\s*\|[-\s|]+\|\s*$',           # Markdown-style table separator
        r'^[\s\w]+\t[\s\w]+\t',           # Tab-separated values
        r'^\s*[\w\s]+\s{3,}[\w\s]+\s{3,}', # Columnar whitespace
    ]
    
    # Administrative content patterns (for filtering)
    TOC_PATTERNS = [
        r'^\s*table\s+of\s+contents\s*$',
        r'^\s*contents\s*$',
        r'^\s*chapter\s+\d+\s+\.\.\.\s*\d+\s*$',
        r'^\s*\d+\.\d+\s+.+\s+\.\.\.\s*\d+\s*$',
    ]
    
    CONFIG_PATTERNS = [
        r'^\s*configuration\s+variables?\s*$',
        r'^\s*system\s+variables?\s*$',
        r'^\s*environment\s+variables?\s*$',
        r'^\s*setting\s+up\s+',
        r'^\s*installation\s+',
        r'^\s*prerequisites?\s*$',
    ]
    
    APPENDIX_PATTERNS = [
        r'^\s*appendix\s+[a-z]\s*$',
        r'^\s*appendix\s*:\s*.+\s*$',
        r'^\s*reference\s+guide\s*$',
        r'^\s*quick\s+reference\s*$',
    ]
    
    # Exercise patterns
    EXERCISE_PATTERNS = [
        r'^\s*(?:exercise|problem|question)\s+[\d.]+',
        r'^\s*\d+\.\d+\.\s+(?:exercise|practice)',
        r'^\s*practice\s+(?:exercise|problem)\s*',
    ]
    
    # Figure patterns
    FIGURE_PATTERNS = [
        r'^\s*figure\s+\d+[-.]?\d*\s*:?\s*',
        r'^\s*fig\.?\s*\d+',
        r'^\s*diagram\s+\d+',
    ]
    
    # Summary patterns
    SUMMARY_PATTERNS = [
        r'^\s*(?:chapter\s+)?summary\s*$',
        r'^\s*key\s+points?\s*$',
        r'^\s*takeaways?\s*$',
        r'^\s*in\s+summary\s*$',
    ]
    
    # Glossary patterns
    GLOSSARY_PATTERNS = [
        r'^\s*glossary\s*$',
        r'^\s*terminology\s*$',
        r'^\s*key\s+terms?\s*$',
    ]
    
    def __init__(self):
        """Initialize the extractor with compiled patterns."""
        self.sql_patterns = [re.compile(p, re.IGNORECASE) for p in self.SQL_KEYWORDS]
        self.toc_patterns = [re.compile(p, re.IGNORECASE) for p in self.TOC_PATTERNS]
        self.config_patterns = [re.compile(p, re.IGNORECASE) for p in self.CONFIG_PATTERNS]
        self.appendix_patterns = [re.compile(p, re.IGNORECASE) for p in self.APPENDIX_PATTERNS]
        self.exercise_patterns = [re.compile(p, re.IGNORECASE) for p in self.EXERCISE_PATTERNS]
        self.figure_patterns = [re.compile(p, re.IGNORECASE) for p in self.FIGURE_PATTERNS]
        self.summary_patterns = [re.compile(p, re.IGNORECASE) for p in self.SUMMARY_PATTERNS]
        self.glossary_patterns = [re.compile(p, re.IGNORECASE) for p in self.GLOSSARY_PATTERNS]
        self.table_patterns = [re.compile(p) for p in self.TABLE_PATTERNS]
    
    def extract_blocks(
        self,
        pdf_path: Path | str,
        doc_id: str,
    ) -> list[ContentBlock]:
        """
        Extract content blocks from a PDF with pedagogical structure awareness.
        
        Uses PyMuPDF to extract text with layout preservation, detecting
        block types based on font characteristics, content patterns, and
        structural heuristics.
        
        Args:
            pdf_path: Path to the PDF file
            doc_id: Document identifier for block ID generation
            
        Returns:
            List of ContentBlock objects with type annotations
            
        Raises:
            FileNotFoundError: If PDF file doesn't exist
            RuntimeError: If PDF is corrupted or password-protected
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        if pdf_path.is_dir():
            raise PermissionError(f"Path is a directory, not a file: {pdf_path}")
        
        try:
            doc = fitz.open(pdf_path)
        except fitz.FileDataError as e:
            error_msg = str(e).lower()
            if "password" in error_msg or "encrypted" in error_msg:
                raise RuntimeError(
                    f"PDF is password-protected: {pdf_path}"
                ) from e
            raise RuntimeError(f"Invalid PDF file: {pdf_path}") from e
        
        blocks: list[ContentBlock] = []
        
        try:
            # First pass: collect font statistics to determine body text size
            font_sizes = []
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                text_dict = page.get_text("dict")
                
                for block in text_dict.get("blocks", []):
                    if "lines" not in block:
                        continue
                    for line in block["lines"]:
                        for span in line.get("spans", []):
                            font_sizes.append(span.get("size", 12))
            
            # Calculate body text size (mode of font sizes)
            if font_sizes:
                body_size = max(set(font_sizes), key=font_sizes.count)
            else:
                body_size = 12.0
            
            heading_threshold = body_size * self.HEADING_SIZE_THRESHOLD
            subheading_threshold = body_size * self.SUBHEADING_SIZE_THRESHOLD
            
            # Second pass: extract blocks with type detection
            block_index = 0
            prev_block: ContentBlock | None = None
            
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                text_dict = page.get_text("dict")
                
                page_char_offset = 0
                
                for block in text_dict.get("blocks", []):
                    if "lines" not in block:
                        continue
                    
                    # Extract text and font info from block
                    block_text = ""
                    max_font_size = 0.0
                    is_bold = False
                    is_italic = False
                    font_name = ""
                    bbox = block.get("bbox", (0, 0, 0, 0))
                    
                    for line in block["lines"]:
                        line_text = ""
                        for span in line.get("spans", []):
                            span_text = span.get("text", "")
                            line_text += span_text
                            
                            # Track font properties
                            span_size = span.get("size", 12)
                            if span_size > max_font_size:
                                max_font_size = span_size
                                font_name = span.get("font", "").lower()
                            
                            # Check flags (bit 4 = bold, bit 1 = italic)
                            flags = span.get("flags", 0)
                            if flags & 2**4:
                                is_bold = True
                            if flags & 2**1:
                                is_italic = True
                        
                        if line_text.strip():
                            block_text += line_text + "\n"
                    
                    block_text = block_text.rstrip()
                    
                    # Skip empty or invalid blocks
                    if not block_text or len(block_text) < self.MIN_BLOCK_LENGTH:
                        continue
                    
                    if len(block_text) > self.MAX_BLOCK_LENGTH:
                        # Truncate very long blocks
                        block_text = block_text[:self.MAX_BLOCK_LENGTH] + "..."
                    
                    # Normalize text
                    block_text = normalize_text(block_text)
                    
                    # Detect block type
                    font_info = {
                        "font_size": max_font_size,
                        "is_bold": is_bold,
                        "is_italic": is_italic,
                        "font_name": font_name,
                        "body_size": body_size,
                        "heading_threshold": heading_threshold,
                        "subheading_threshold": subheading_threshold,
                    }
                    
                    block_type = self._detect_block_type(
                        block_text, font_info, prev_block
                    )
                    
                    # Calculate character offsets
                    char_start = page_char_offset
                    char_end = char_start + len(block_text)
                    page_char_offset = char_end + 1  # +1 for separator
                    
                    # Determine heading level
                    heading_level = None
                    if block_type == BlockType.HEADING:
                        heading_level = 1
                    elif block_type == BlockType.SUBHEADING:
                        heading_level = self._determine_heading_level(
                            block_text, max_font_size, heading_threshold, subheading_threshold
                        )
                    
                    # Build metadata
                    metadata: dict[str, Any] = {
                        "font_name": font_name,
                        "font_size": max_font_size,
                        "is_bold": is_bold,
                        "is_italic": is_italic,
                        "bbox": bbox,
                    }
                    if heading_level:
                        metadata["heading_level"] = heading_level
                    if block_type == BlockType.SQL_CODE:
                        metadata["language"] = "sql"
                    
                    # Calculate confidence (based on OCR quality if available)
                    confidence = self._calculate_confidence(block, font_info)
                    
                    # Create block
                    block_index += 1
                    block_id = f"{doc_id}:p{page_num + 1}:b{block_index}"
                    
                    content_block = ContentBlock(
                        block_id=block_id,
                        block_type=block_type,
                        page_number=page_num + 1,
                        char_start=char_start,
                        char_end=char_end,
                        text_content=block_text,
                        confidence=confidence,
                        metadata=metadata,
                        parent_block_id=None,
                    )
                    
                    # Update hierarchy: link to previous heading if applicable
                    if prev_block and prev_block.is_structural and not content_block.is_structural:
                        content_block.parent_block_id = prev_block.block_id
                    
                    blocks.append(content_block)
                    prev_block = content_block
        
        finally:
            doc.close()
        
        # Post-processing: establish parent-child relationships
        blocks = self._establish_hierarchy(blocks)
        
        return blocks
    
    def _detect_block_type(
        self,
        text: str,
        font_info: dict[str, Any],
        prev_block: ContentBlock | None,
    ) -> BlockType:
        """
        Detect the type of a content block based on heuristics.
        
        Args:
            text: The block text content
            font_info: Dictionary with font properties
            prev_block: Previous block for context
            
        Returns:
            Detected BlockType
        """
        font_size = font_info.get("font_size", 0)
        is_bold = font_info.get("is_bold", False)
        font_name = font_info.get("font_name", "")
        heading_threshold = font_info.get("heading_threshold", 14)
        subheading_threshold = font_info.get("subheading_threshold", 13)
        
        # Check for administrative content first
        if self._is_admin_content(text):
            return BlockType.ADMIN_TEXT
        
        # Check for heading
        if self._is_likely_heading(text, font_size, is_bold, heading_threshold):
            return BlockType.HEADING
        
        # Check for subheading
        if self._is_likely_subheading(text, font_size, is_bold, subheading_threshold):
            return BlockType.SUBHEADING
        
        # Check for code
        if self._is_likely_code(text, font_name):
            return BlockType.SQL_CODE
        
        # Check for table/output
        if self._is_likely_table(text):
            # Distinguish between data tables and output tables
            if self._looks_like_query_output(text):
                return BlockType.OUTPUT_TABLE
            return BlockType.FIGURE
        
        # Check for exercise
        if self._is_likely_exercise(text):
            return BlockType.EXERCISE
        
        # Check for figure
        if self._is_likely_figure(text):
            return BlockType.FIGURE
        
        # Check for summary
        if self._is_likely_summary(text):
            return BlockType.SUMMARY
        
        # Check for glossary
        if self._is_likely_glossary(text):
            return BlockType.GLOSSARY
        
        # Check for sidebar (based on visual cues or content)
        if self._is_likely_sidebar(text, prev_block):
            return BlockType.SIDEBAR
        
        # Default to explanatory prose
        return BlockType.EXPLANATORY_PROSE
    
    def _is_likely_heading(
        self,
        text: str,
        font_size: float,
        is_bold: bool,
        heading_threshold: float = 14.0,
    ) -> bool:
        """
        Determine if text is likely a heading based on font and content.
        
        Args:
            text: The text to check
            font_size: Font size of the text
            is_bold: Whether the text is bold
            heading_threshold: Minimum font size for heading
            
        Returns:
            True if text appears to be a heading
        """
        # Normalize text
        text_stripped = text.strip()
        text_lower = text_stripped.lower()
        
        # Check length (headings are typically short)
        word_count = len(text_stripped.split())
        if word_count > 15:
            return False
        
        # Check for chapter patterns
        chapter_patterns = [
            r'^chapter\s+\d+',
            r'^ch\.?\s*\d+',
            r'^\d+\s*\.\s+[A-Z]',
            r'^part\s+[ivxlc\d]+',
        ]
        for pattern in chapter_patterns:
            if re.match(pattern, text_lower):
                return True
        
        # Font size check
        if font_size >= heading_threshold:
            # If bold or title case, more likely a heading
            if is_bold or text_stripped.istitle():
                return True
        
        return False
    
    def _is_likely_subheading(
        self,
        text: str,
        font_size: float,
        is_bold: bool,
        subheading_threshold: float = 13.0,
    ) -> bool:
        """
        Determine if text is likely a subheading.
        
        Args:
            text: The text to check
            font_size: Font size of the text
            is_bold: Whether the text is bold
            subheading_threshold: Minimum font size for subheading
            
        Returns:
            True if text appears to be a subheading
        """
        text_stripped = text.strip()
        word_count = len(text_stripped.split())
        
        # Subheadings are typically short
        if word_count > 12:
            return False
        
        # Check for section patterns like "1.1", "2.3.1"
        section_pattern = re.match(r'^(\d+\.)+\s+\w', text_stripped)
        if section_pattern:
            return True
        
        # Font-based detection
        if font_size >= subheading_threshold and is_bold:
            return True
        
        return False
    
    def _determine_heading_level(
        self,
        text: str,
        font_size: float,
        heading_threshold: float,
        subheading_threshold: float,
    ) -> int:
        """Determine the heading level (1-4) based on font size and patterns."""
        # Check for section number patterns
        match = re.match(r'^(\d+(?:\.\d+)*)(?:\s|$)', text.strip())
        if match:
            section_num = match.group(1)
            dot_count = section_num.count(".")
            return min(dot_count + 1, 4)
        
        # Font size based level
        if font_size >= heading_threshold * 1.2:
            return 1
        elif font_size >= heading_threshold:
            return 2
        elif font_size >= subheading_threshold:
            return 3
        else:
            return 4
    
    def _is_likely_code(self, text: str, font_name: str = "") -> bool:
        """
        Determine if text is likely code based on content and font.
        
        Args:
            text: The text to check
            font_name: Font name (may indicate monospace)
            
        Returns:
            True if text appears to be code
        """
        # Check for monospace font
        font_lower = font_name.lower()
        if any(mono in font_lower for mono in self.MONOSPACE_FONTS):
            # Additional check: code usually has specific patterns
            code_indicators = sum(
                1 for pattern in self.sql_patterns if pattern.search(text)
            )
            if code_indicators >= 2:
                return True
        
        # Check for SQL patterns without monospace font
        code_indicators = sum(
            1 for pattern in self.sql_patterns if pattern.search(text)
        )
        
        # If multiple SQL keywords found, likely code
        if code_indicators >= 3:
            return True
        
        # Check for code formatting patterns
        code_patterns = [
            r'^\s*(?:SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER)\s+',
            r';\s*$',  # Ends with semicolon
            r'\b(?:WHERE|FROM|JOIN|GROUP BY|ORDER BY)\b',
        ]
        
        matches = sum(1 for p in code_patterns if re.search(p, text, re.IGNORECASE))
        if matches >= 2:
            return True
        
        return False
    
    def _is_likely_table(self, text: str) -> bool:
        """
        Determine if text represents a table or tabular data.
        
        Args:
            text: The text to check
            
        Returns:
            True if text appears to be a table
        """
        lines = text.strip().split('\n')
        if len(lines) < 2:
            return False
        
        # Check for table patterns
        for pattern in self.table_patterns:
            if pattern.search(text):
                return True
        
        # Check for consistent column structure
        # Count lines that appear to have multiple columns
        tab_separated = sum(1 for line in lines if '\t' in line)
        if tab_separated >= len(lines) * 0.5:
            return True
        
        # Check for pipe-separated (markdown-style)
        pipe_separated = sum(1 for line in lines if '|' in line)
        if pipe_separated >= len(lines) * 0.5:
            return True
        
        # Check for aligned whitespace columns
        if len(lines) >= 2:
            # Look for consistent spacing patterns
            space_pattern = re.compile(r'\s{3,}')
            multi_column_lines = sum(
                1 for line in lines if len(space_pattern.findall(line)) >= 2
            )
            if multi_column_lines >= len(lines) * 0.6:
                return True
        
        return False
    
    def _looks_like_query_output(self, text: str) -> bool:
        """Check if table text looks like SQL query output."""
        output_indicators = [
            r'\d+\s+rows?\s+(?:selected|returned|affected)',
            r'^\s*id\s+|\s+name\s+|\s+date\s+',
            r'----[+\-]+',  # Separator lines
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in output_indicators)
    
    def _is_likely_exercise(self, text: str) -> bool:
        """Check if text is an exercise or practice problem."""
        text_lower = text.lower().strip()
        
        for pattern in self.exercise_patterns:
            if pattern.search(text_lower):
                return True
        
        # Check for numbered exercises
        if re.match(r'^\s*\(\d+\)|^\s*\[\d+\]', text):
            # Additional check: contains question words
            question_words = ['write', 'create', 'find', 'list', 'explain', 'describe']
            if any(word in text_lower for word in question_words):
                return True
        
        return False
    
    def _is_likely_figure(self, text: str) -> bool:
        """Check if text is a figure caption or diagram description."""
        text_lower = text.lower().strip()
        
        for pattern in self.figure_patterns:
            if pattern.search(text_lower):
                return True
        
        return False
    
    def _is_likely_summary(self, text: str) -> bool:
        """Check if text is a summary section."""
        text_lower = text.lower().strip()
        
        for pattern in self.summary_patterns:
            if pattern.search(text_lower):
                return True
        
        return False
    
    def _is_likely_glossary(self, text: str) -> bool:
        """Check if text is a glossary entry."""
        text_lower = text.lower().strip()
        
        for pattern in self.glossary_patterns:
            if pattern.search(text_lower):
                return True
        
        # Check for definition pattern (term: definition)
        if re.match(r'^[A-Z][A-Z\s]+:\s+', text):
            return True
        
        return False
    
    def _is_likely_sidebar(
        self,
        text: str,
        prev_block: ContentBlock | None,
    ) -> bool:
        """Check if text is a sidebar, tip, or note."""
        text_lower = text.lower().strip()
        
        # Sidebar indicators
        sidebar_prefixes = [
            'tip:', 'note:', 'warning:', 'important:', 'caution:',
            'hint:', 'remember:', 'key point:',
        ]
        
        for prefix in sidebar_prefixes:
            if text_lower.startswith(prefix):
                return True
        
        # Boxed content (often sidebars)
        if text.startswith('┌') or text.startswith('+' + '-'):
            return True
        
        return False
    
    def _is_admin_content(self, text: str) -> bool:
        """
        Check if text is administrative content (not teaching material).
        
        Filters out:
        - Table of contents
        - Configuration variable lists
        - Installation instructions
        - Appendix material
        - Copyright/legal text
        
        Args:
            text: The text to check
            
        Returns:
            True if text is administrative
        """
        text_lower = text.lower().strip()
        
        # Check TOC patterns
        for pattern in self.toc_patterns:
            if pattern.search(text_lower):
                return True
        
        # Check config patterns
        for pattern in self.config_patterns:
            if pattern.search(text_lower):
                return True
        
        # Check appendix patterns
        for pattern in self.appendix_patterns:
            if pattern.search(text_lower):
                return True
        
        # Copyright/legal patterns
        copyright_patterns = [
            r'^\s*copyright\s+©?\s*\d{4}',
            r'^\s*©\s*\d{4}',
            r'^\s*all\s+rights\s+reserved',
            r'^\s*isbn\s*:?\s*\d',
            r'^\s*printed\s+in',
        ]
        for pattern in copyright_patterns:
            if re.search(pattern, text_lower):
                return True
        
        # Page numbers and headers/footers
        if re.match(r'^\s*\d+\s*$', text_stripped := text.strip()):
            # Just a number - likely page number
            if len(text_stripped) <= 3:
                return True
        
        # Index entries
        if re.match(r'^[A-Z][a-z]+,?\s+\d+(-\d+)?$', text.strip()):
            return True
        
        return False
    
    def _calculate_confidence(
        self,
        block: dict[str, Any],
        font_info: dict[str, Any],
    ) -> float:
        """
        Calculate OCR/extraction confidence for a block.
        
        Args:
            block: PyMuPDF block dictionary
            font_info: Font information dictionary
            
        Returns:
            Confidence score (0.0-1.0)
        """
        confidence = 1.0
        
        # Reduce confidence for very small fonts (may be OCR artifacts)
        font_size = font_info.get("font_size", 12)
        if font_size < 6:
            confidence -= 0.3
        elif font_size < 8:
            confidence -= 0.15
        
        # Check for suspicious characters (OCR artifacts)
        text = ""
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text += span.get("text", "")
        
        # Count suspicious patterns
        suspicious = len(re.findall(r'[_\-]{3,}', text))
        suspicious += len(re.findall(r'[\^\*@#%&]{2,}', text))
        suspicious += len(re.findall(r'[^\w\s.,;:!?\-\'"()\[\]{}]', text))
        
        if len(text) > 0:
            artifact_ratio = suspicious / len(text)
            confidence -= min(0.5, artifact_ratio * 5)
        
        return max(0.0, min(1.0, confidence))
    
    def _establish_hierarchy(self, blocks: list[ContentBlock]) -> list[ContentBlock]:
        """
        Establish parent-child relationships between blocks.
        
        Updates blocks in place to link sections with their parent headings.
        
        Args:
            blocks: List of content blocks
            
        Returns:
            Updated list of blocks with hierarchy established
        """
        if not blocks:
            return blocks
        
        # Track current heading stack
        heading_stack: list[ContentBlock] = []
        
        for block in blocks:
            if block.is_structural:
                # This is a heading - update stack
                heading_level = block.get_heading_level() or 2
                
                # Pop higher or equal level headings
                while heading_stack and heading_stack[-1].get_heading_level() or 2 >= heading_level:
                    heading_stack.pop()
                
                # Set parent if there's a heading in the stack
                if heading_stack:
                    block.parent_block_id = heading_stack[-1].block_id
                    heading_stack[-1].child_block_ids.append(block.block_id)
                
                # Add to stack
                heading_stack.append(block)
            else:
                # Non-structural block - find appropriate parent
                if heading_stack:
                    # Use most recent heading as parent
                    parent = heading_stack[-1]
                    block.parent_block_id = parent.block_id
                    parent.child_block_ids.append(block.block_id)
        
        return blocks


# =============================================================================
# CONTENT FILTER CLASS
# =============================================================================

class ContentFilter:
    """
    Filters content blocks to exclude non-teaching material.
    
    Provides both hard filters (definitive exclusions) and pattern-based
    filtering for removing administrative content, TOC pages, configuration
    lists, and other non-instructional material.
    """
    
    # Hard filter patterns - always exclude these
    EXCLUSION_PATTERNS = [
        # Table of contents
        r'^\s*table\s+of\s+contents\s*$',
        r'^\s*contents\s*$',
        r'^\s*in\s+this\s+(?:chapter|section)\s*$',
        
        # Administrative
        r'^\s*preface\s*$',
        r'^\s*foreword\s*$',
        r'^\s*acknowledgments?\s*$',
        r'^\s*about\s+(?:the\s+)?author',
        r'^\s*introduction\s+to\s+the\s+book',
        
        # Configuration/Installation
        r'^\s*appendix\s+[a-z]:?\s*(?:configuration|installation|setup)',
        r'^\s*setting\s+up\s+(?:your\s+)?environment',
        r'^\s*system\s+requirements\s*$',
        r'^\s*installation\s+guide\s*$',
        
        # Reference material (often not teaching content)
        r'^\s*appendix\s+[a-z]:?\s*(?:reference|command|function)',
        r'^\s*quick\s+reference\s+card\s*$',
        r'^\s*error\s+code\s+reference\s*$',
        
        # Copyright/legal
        r'^\s*copyright\s+',
        r'^\s*all\s+rights\s+reserved',
        r'^\s*disclaimer\s*$',
        r'^\s*trademarks?\s*$',
        
        # Navigation elements
        r'^\s*previous\s+chapter\s*$',
        r'^\s*next\s+chapter\s*$',
        r'^\s*chapter\s+summary\s*$',  # Often just navigation
    ]
    
    # Conditional exclusions - exclude unless explicitly keeping
    CONDITIONAL_PATTERNS = {
        'exercises': [
            r'^\s*exercises?\s*$',
            r'^\s*practice\s+problems?\s*$',
            r'^\s*review\s+questions?\s*$',
        ],
        'figures': [
            r'^\s*figure\s+\d+[-.]?\d*\s*$',  # Just "Figure 1.1" with no content
        ],
        'summaries': [
            r'^\s*(?:chapter\s+)?summary\s*$',
            r'^\s*key\s+points?\s*$',
        ],
    }
    
    def __init__(self):
        """Initialize filter with compiled patterns."""
        self.exclusion_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.EXCLUSION_PATTERNS
        ]
        self.conditional_patterns = {
            key: [re.compile(p, re.IGNORECASE) for p in patterns]
            for key, patterns in self.CONDITIONAL_PATTERNS.items()
        }
    
    def should_exclude_block(
        self,
        block: ContentBlock,
        keep_exercises: bool = True,
        keep_figures: bool = True,
        keep_summaries: bool = True,
    ) -> bool:
        """
        Determine if a block should be excluded.
        
        Args:
            block: Content block to evaluate
            keep_exercises: Whether to keep exercise content
            keep_figures: Whether to keep figure captions
            keep_summaries: Whether to keep summary sections
            
        Returns:
            True if block should be excluded
        """
        # Always exclude admin text
        if block.block_type == BlockType.ADMIN_TEXT:
            return True
        
        text = block.text_content.strip()
        text_lower = text.lower()
        
        # Check hard exclusions
        for pattern in self.exclusion_patterns:
            if pattern.search(text_lower):
                return True
        
        # Check conditional exclusions
        if not keep_exercises:
            for pattern in self.conditional_patterns['exercises']:
                if pattern.search(text_lower):
                    return True
        
        if not keep_figures:
            for pattern in self.conditional_patterns['figures']:
                if pattern.search(text_lower):
                    return True
        
        if not keep_summaries:
            for pattern in self.conditional_patterns['summaries']:
                if pattern.search(text_lower):
                    return True
        
        # Exclude very short blocks (likely artifacts)
        if len(text) < 5:
            return True
        
        # Exclude blocks with very low confidence
        if block.confidence < 0.3:
            return True
        
        return False
    
    def filter_blocks(
        self,
        blocks: list[ContentBlock],
        keep_exercises: bool = True,
        keep_figures: bool = True,
        keep_summaries: bool = True,
    ) -> list[ContentBlock]:
        """
        Filter a list of blocks, returning only teaching content.
        
        Args:
            blocks: List of content blocks
            keep_exercises: Whether to keep exercise content
            keep_figures: Whether to keep figure captions
            keep_summaries: Whether to keep summary sections
            
        Returns:
            Filtered list of content blocks
        """
        return [
            block for block in blocks
            if not self.should_exclude_block(
                block, keep_exercises, keep_figures, keep_summaries
            )
        ]
    
    def get_excluded_blocks(
        self,
        blocks: list[ContentBlock],
    ) -> list[tuple[ContentBlock, str]]:
        """
        Get list of excluded blocks with reasons.
        
        Args:
            blocks: List of content blocks
            
        Returns:
            List of (block, reason) tuples for excluded blocks
        """
        excluded = []
        
        for block in blocks:
            reason = self._get_exclusion_reason(block)
            if reason:
                excluded.append((block, reason))
        
        return excluded
    
    def _get_exclusion_reason(self, block: ContentBlock) -> str | None:
        """Get the reason a block would be excluded, or None if not excluded."""
        if block.block_type == BlockType.ADMIN_TEXT:
            return "Administrative content"
        
        text = block.text_content.strip().lower()
        
        for pattern in self.exclusion_patterns:
            if pattern.search(text):
                return f"Matches exclusion pattern: {pattern.pattern[:30]}..."
        
        if len(block.text_content.strip()) < 5:
            return "Too short (likely artifact)"
        
        if block.confidence < 0.3:
            return f"Low confidence ({block.confidence:.2f})"
        
        return None


# =============================================================================
# EVIDENCE TRACKER CLASS
# =============================================================================

class EvidenceTracker:
    """
    Tracks evidence linking content blocks to concepts.
    
    Provides keyword matching and context analysis to identify which
    source blocks ground a particular concept or learning objective.
    """
    
    def __init__(self):
        """Initialize the evidence tracker."""
        self.concept_cache: dict[str, list[ContentBlock]] = {}
    
    def get_spans_for_concept(
        self,
        blocks: list[ContentBlock],
        concept_id: str,
        keywords: list[str] | None = None,
        context_window: int = 2,
    ) -> list[ContentBlock]:
        """
        Get content blocks that ground a specific concept.
        
        Uses keyword matching and context analysis to find relevant blocks.
        Returns the exact source blocks with surrounding context.
        
        Args:
            blocks: List of all content blocks
            concept_id: Concept identifier (e.g., "sql-joins", "aggregate-functions")
            keywords: Optional list of keywords to match (derived from concept_id if not provided)
            context_window: Number of surrounding blocks to include for context
            
        Returns:
            List of content blocks that ground the concept
        """
        # Derive keywords from concept_id if not provided
        if keywords is None:
            keywords = self._derive_keywords(concept_id)
        
        # Normalize keywords
        keywords = [kw.lower().strip() for kw in keywords]
        
        # Find matching block indices
        matching_indices: set[int] = set()
        
        for i, block in enumerate(blocks):
            block_text = block.text_content.lower()
            
            # Check for keyword matches
            for keyword in keywords:
                if keyword in block_text:
                    matching_indices.add(i)
                    break
        
        # Expand with context window
        expanded_indices: set[int] = set()
        for idx in matching_indices:
            for offset in range(-context_window, context_window + 1):
                context_idx = idx + offset
                if 0 <= context_idx < len(blocks):
                    expanded_indices.add(context_idx)
        
        # Return blocks in order
        return [blocks[i] for i in sorted(expanded_indices)]
    
    def _derive_keywords(self, concept_id: str) -> list[str]:
        """Derive search keywords from a concept ID."""
        # Split on common separators
        words = re.split(r'[-_\s]', concept_id.lower())
        
        # Filter out common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'in', 'on', 'at', 'to', 'for'}
        keywords = [w for w in words if w and w not in stop_words]
        
        # Add compound variations
        if len(words) >= 2:
            keywords.append(' '.join(words))
        
        return keywords
    
    def calculate_relevance_score(
        self,
        block: ContentBlock,
        concept_id: str,
        keywords: list[str] | None = None,
    ) -> float:
        """
        Calculate a relevance score for a block to a concept.
        
        Args:
            block: Content block to score
            concept_id: Concept identifier
            keywords: Optional keywords to match
            
        Returns:
            Relevance score (0.0-1.0)
        """
        if keywords is None:
            keywords = self._derive_keywords(concept_id)
        
        keywords = [kw.lower().strip() for kw in keywords]
        block_text = block.text_content.lower()
        
        # Count keyword occurrences
        keyword_count = sum(block_text.count(kw) for kw in keywords)
        
        # Calculate density
        word_count = len(block_text.split())
        if word_count == 0:
            return 0.0
        
        density = keyword_count / word_count
        
        # Boost for headings (more likely to be concept-defining)
        if block.is_structural:
            density *= 2.0
        
        # Boost for code examples (often demonstrate concepts)
        if block.is_code:
            density *= 1.5
        
        # Cap at 1.0
        return min(1.0, density * 10)  # Scale factor for normalization
    
    def get_top_blocks_for_concept(
        self,
        blocks: list[ContentBlock],
        concept_id: str,
        keywords: list[str] | None = None,
        top_n: int = 5,
    ) -> list[tuple[ContentBlock, float]]:
        """
        Get top N most relevant blocks for a concept.
        
        Args:
            blocks: List of content blocks
            concept_id: Concept identifier
            keywords: Optional keywords to match
            top_n: Number of top blocks to return
            
        Returns:
            List of (block, score) tuples, sorted by relevance
        """
        scored_blocks = [
            (block, self.calculate_relevance_score(block, concept_id, keywords))
            for block in blocks
        ]
        
        # Sort by score descending
        scored_blocks.sort(key=lambda x: x[1], reverse=True)
        
        return scored_blocks[:top_n]
    
    def create_evidence_map(
        self,
        blocks: list[ContentBlock],
        concept_ids: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Create an evidence map for multiple concepts.
        
        Args:
            blocks: List of content blocks
            concept_ids: List of concept identifiers
            
        Returns:
            Dictionary mapping concept_id to list of evidence entries
        """
        evidence_map: dict[str, list[dict[str, Any]]] = {}
        
        for concept_id in concept_ids:
            relevant_blocks = self.get_spans_for_concept(blocks, concept_id)
            
            evidence_map[concept_id] = [
                {
                    "block_id": block.block_id,
                    "block_type": block.block_type.name,
                    "page_number": block.page_number,
                    "relevance_score": self.calculate_relevance_score(
                        block, concept_id
                    ),
                    "text_preview": block.text_content[:200] + "..."
                    if len(block.text_content) > 200
                    else block.text_content,
                }
                for block in relevant_blocks
            ]
        
        return evidence_map


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def extract_and_filter_blocks(
    pdf_path: Path | str,
    doc_id: str,
    keep_exercises: bool = True,
    keep_figures: bool = True,
    keep_summaries: bool = True,
) -> tuple[list[ContentBlock], dict[str, Any]]:
    """
    Convenience function to extract and filter blocks in one call.
    
    Args:
        pdf_path: Path to PDF file
        doc_id: Document identifier
        keep_exercises: Whether to keep exercise content
        keep_figures: Whether to keep figure captions
        keep_summaries: Whether to keep summary sections
        
    Returns:
        Tuple of (filtered_blocks, extraction_stats)
    """
    extractor = SectionExtractor()
    filter_ = ContentFilter()
    
    # Extract all blocks
    all_blocks = extractor.extract_blocks(pdf_path, doc_id)
    
    # Calculate stats
    total_blocks = len(all_blocks)
    type_counts: dict[str, int] = {}
    for block in all_blocks:
        type_name = block.block_type.name
        type_counts[type_name] = type_counts.get(type_name, 0) + 1
    
    # Filter blocks
    filtered_blocks = filter_.filter_blocks(
        all_blocks,
        keep_exercises=keep_exercises,
        keep_figures=keep_figures,
        keep_summaries=keep_summaries,
    )
    
    # Get excluded blocks with reasons
    excluded = filter_.get_excluded_blocks(all_blocks)
    
    stats = {
        "total_blocks": total_blocks,
        "filtered_blocks": len(filtered_blocks),
        "excluded_blocks": len(excluded),
        "type_distribution": type_counts,
        "exclusion_reasons": {},
    }
    
    # Count exclusion reasons
    for _, reason in excluded:
        reason_key = reason.split("(")[0].strip()  # Simplify reason
        stats["exclusion_reasons"][reason_key] = stats["exclusion_reasons"].get(reason_key, 0) + 1
    
    return filtered_blocks, stats


def export_blocks_to_json(
    blocks: list[ContentBlock],
    output_path: Path | str,
) -> None:
    """
    Export content blocks to JSON file.
    
    Args:
        blocks: List of content blocks
        output_path: Path to output JSON file
    """
    import json
    
    output_path = Path(output_path)
    data = {
        "version": "1.0.0",
        "block_count": len(blocks),
        "blocks": [block.to_dict() for block in blocks],
    }
    
    output_path.write_text(json.dumps(data, indent=2))


def load_blocks_from_json(input_path: Path | str) -> list[ContentBlock]:
    """
    Load content blocks from JSON file.
    
    Args:
        input_path: Path to input JSON file
        
    Returns:
        List of content blocks
    """
    import json
    
    input_path = Path(input_path)
    data = json.loads(input_path.read_text())
    
    return [ContentBlock.from_dict(b) for b in data.get("blocks", [])]
