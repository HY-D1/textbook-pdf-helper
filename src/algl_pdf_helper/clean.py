from __future__ import annotations

import hashlib
import re
from collections import Counter


# ============================================================================
# Text Normalization
# ============================================================================

_SPACE_TABS = re.compile(r"[ \t]+")
_MULTI_NL = re.compile(r"\n{2,}")


def normalize_text(text: str) -> str:
    """Normalize whitespace and remove null bytes."""
    return _MULTI_NL.sub("\n", _SPACE_TABS.sub(" ", text.replace("\x00", " "))).strip()


# ============================================================================
# Duplicate Detection and Removal
# ============================================================================


def _paragraph_fingerprint(text: str) -> str:
    """Generate a normalized fingerprint for a paragraph.
    
    Normalizes whitespace and lowercase for comparison.
    """
    # Normalize: lowercase, strip, collapse whitespace
    normalized = re.sub(r'\s+', ' ', text.lower().strip())
    return normalized


def deduplicate_text(text: str, min_length: int = 20, similarity_threshold: float = 0.95) -> str:
    """Remove duplicate paragraphs from text.
    
    Uses paragraph-level fingerprinting to detect and remove exact duplicates
    and near-duplicates (e.g., same text with minor formatting differences).
    
    Args:
        text: The text to deduplicate
        min_length: Minimum paragraph length to consider for deduplication
        similarity_threshold: Threshold for considering paragraphs as duplicates (0.0-1.0)
        
    Returns:
        Text with duplicates removed, preserving original paragraph order
    """
    if not text or len(text) < min_length:
        return text
    
    paragraphs = text.split('\n\n')
    seen_fingerprints: set[str] = set()
    unique_paragraphs: list[str] = []
    
    for para in paragraphs:
        para_stripped = para.strip()
        if len(para_stripped) < min_length:
            # Keep short paragraphs as-is
            unique_paragraphs.append(para)
            continue
        
        # Generate fingerprint
        fingerprint = _paragraph_fingerprint(para_stripped)
        
        # Check for exact match or near-duplicate
        is_duplicate = False
        for seen in seen_fingerprints:
            # Simple containment check for near-duplicates
            if fingerprint in seen or seen in fingerprint:
                # Length ratio check to avoid false positives
                len_ratio = min(len(fingerprint), len(seen)) / max(len(fingerprint), len(seen))
                if len_ratio >= similarity_threshold:
                    is_duplicate = True
                    break
        
        if not is_duplicate:
            seen_fingerprints.add(fingerprint)
            unique_paragraphs.append(para)
    
    return '\n\n'.join(unique_paragraphs)


def deduplicate_repeated_lines(text: str, min_repeats: int = 3) -> str:
    """Remove lines that appear repeatedly (common in headers/footers).
    
    Args:
        text: Text to process
        min_repeats: Minimum number of times a line must appear to be removed
        
    Returns:
        Text with repeated lines removed
    """
    lines = text.split('\n')
    line_counts: dict[str, int] = {}
    
    # Count normalized lines
    for line in lines:
        normalized = line.strip().lower()
        if len(normalized) >= 2:  # Count lines with 2+ chars (catches page numbers)
            line_counts[normalized] = line_counts.get(normalized, 0) + 1
    
    # Find lines that appear too often
    repeated = {line for line, count in line_counts.items() if count >= min_repeats}
    
    # Filter out repeated lines
    filtered = []
    for line in lines:
        normalized = line.strip().lower()
        if normalized not in repeated or len(normalized) < 2:
            filtered.append(line)
    
    return '\n'.join(filtered)


# ============================================================================
# Line Break Normalization
# ============================================================================


def normalize_line_breaks(text: str) -> str:
    """Normalize broken lines from PDF extraction.
    
    Fixes:
    - Hyphenated word breaks (e.g., "state-\nment" -> "statement")
    - Orphaned sentence fragments
    - Single newlines within paragraphs
    
    Args:
        text: Text with potential line break issues
        
    Returns:
        Text with normalized line breaks
    """
    # Pattern 1: Hyphenated word breaks at end of line
    # Match: word-<newline> followed by continuation
    text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)
    
    # Pattern 2: Soft line breaks within paragraphs
    # Join lines that don't end with sentence punctuation
    lines = text.split('\n')
    result: list[str] = []
    current_para: list[str] = []
    
    sentence_enders = {'.', '!', '?', ':', ';'}
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            # Empty line ends paragraph
            if current_para:
                result.append(' '.join(current_para))
                current_para = []
            result.append('')  # Preserve empty line as paragraph break
        elif current_para and not current_para[-1].rstrip()[-1:] in sentence_enders:
            # Previous line doesn't end with sentence punctuation - join
            current_para.append(stripped)
        else:
            # Start new paragraph
            if current_para:
                result.append(' '.join(current_para))
            current_para = [stripped]
    
    # Don't forget the last paragraph
    if current_para:
        result.append(' '.join(current_para))
    
    return '\n'.join(result)


def fix_broken_formatting(text: str) -> str:
    """Fix common formatting breaks from PDF extraction.
    
    Fixes:
    - Multiple spaces after punctuation
    - Missing spaces after periods
    - Inconsistent indentation
    
    Args:
        text: Text with formatting issues
        
    Returns:
        Text with fixed formatting
    """
    # Fix missing space after period (but not in decimals or abbreviations)
    text = re.sub(r'(?<=[a-zA-Z])\.([A-Z])', r'. \1', text)
    
    # Fix multiple spaces
    text = re.sub(r' {2,}', ' ', text)
    
    # Fix space before punctuation
    text = re.sub(r'\s+([.,;:!?)\]])', r'\1', text)
    
    return text


# ============================================================================
# Student-Friendly Text Cleaning
# ============================================================================

# Chapter/section headers like "Chapter 3 How to retrieve data from a single table 75"
CHAPTER_HEADER_PATTERN = re.compile(
    r'^Chapter\s+\d+\s+.*?\d{1,3}\s*$',
    re.MULTILINE | re.IGNORECASE
)

# Figure references like "Figure 3-1 The basic syntax..."
FIGURE_REF_PATTERN = re.compile(
    r'Figure\s+\d+[\-\.]\d+.*?(?=\n|$)',
    re.IGNORECASE
)

# Page numbers (standalone digits at end of lines)
PAGE_NUMBER_PATTERN = re.compile(
    r'^\s*\d{1,3}\s*$',
    re.MULTILINE
)

# Section headers like "Section 1 An introduction to MySQL"
SECTION_HEADER_PATTERN = re.compile(
    r'^Section\s+\d+\s+.*?$',
    re.MULTILINE | re.IGNORECASE
)

# Common OCR artifacts and typos
OCR_ARTIFACTS = [
    (r'frrst', 'first'),
    (r'ru·e', 'rule'),
    (r'ru\.', 'rule'),
    (r'fr·om', 'from'),
    (r'\bo\s*f\b', 'of'),  # Common OCR split
    (r'\bt\s*o\b', 'to'),
    (r'\bs\s*t\s*a\s*t\s*e\s*m\s*e\s*n\s*t\b', 'statement'),
]

# SQL code blocks - preserve these
SQL_KEYWORDS = [
    'SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP',
    'TABLE', 'JOIN', 'INNER', 'OUTER', 'LEFT', 'RIGHT', 'ON', 'GROUP', 'BY', 'ORDER',
    'HAVING', 'LIMIT', 'OFFSET', 'UNION', 'ALL', 'DISTINCT', 'AS', 'AND', 'OR', 'NOT',
    'NULL', 'IS', 'IN', 'BETWEEN', 'LIKE', 'EXISTS', 'CASE', 'WHEN', 'THEN', 'ELSE',
    'END', 'IF', 'WHILE', 'FOR', 'LOOP', 'RETURN', 'DECLARE', 'SET', 'VALUES'
]


def remove_headers_footers_aggressive(text: str) -> str:
    """Remove chapter headers, page numbers, and section markers.
    
    This is more aggressive than the heuristic approach and uses
    patterns common in textbook PDFs.
    """
    # Remove chapter headers
    text = CHAPTER_HEADER_PATTERN.sub('', text)
    
    # Remove standalone page numbers
    text = PAGE_NUMBER_PATTERN.sub('', text)
    
    # Remove section headers  
    text = SECTION_HEADER_PATTERN.sub('', text)
    
    # Clean up multiple newlines
    text = _MULTI_NL.sub('\n', text)
    
    return text.strip()


def clean_figure_references(text: str) -> str:
    """Clean up figure references while preserving their content.
    
    Returns text with figure references formatted consistently.
    """
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Check if line is just a figure caption
        if re.match(r'^\s*Figure\s+\d+[\-\.]\d+\s*$', line, re.IGNORECASE):
            continue
        
        # Remove inline figure references but keep the rest of the line
        line = FIGURE_REF_PATTERN.sub('', line)
        
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)


def fix_ocr_artifacts(text: str) -> str:
    """Fix common OCR artifacts and typos."""
    for pattern, replacement in OCR_ARTIFACTS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Fix common character substitutions
    text = text.replace('\u00b7', ' ')  # Middle dot to space
    text = text.replace('\u2015', '-')  # Em dash to hyphen
    text = text.replace('\u2014', '-')  # Em dash to hyphen  
    text = text.replace('\u2018', "'")  # Left single quote
    text = text.replace('\u2019', "'")  # Right single quote
    text = text.replace('\u201c', '"')  # Left double quote
    text = text.replace('\u201d', '"')  # Right double quote
    
    return text


def detect_code_block(line: str) -> tuple[bool, str]:
    """Detect if a line contains SQL code.
    
    Returns:
        Tuple of (is_code, code_type)
    """
    line_upper = line.upper().strip()
    
    # Check for SQL keywords at start of line
    sql_starts = ['SELECT ', 'FROM ', 'WHERE ', 'INSERT ', 'UPDATE ', 'DELETE ',
                  'CREATE ', 'ALTER ', 'DROP ', 'JOIN ', 'GROUP ', 'ORDER ',
                  'HAVING ', 'LIMIT ', 'UNION ', 'VALUES ', 'AND ', 'OR ']
    
    for keyword in sql_starts:
        if line_upper.startswith(keyword):
            return True, 'sql'
    
    # Check for code-like patterns
    if re.match(r'^\s*\w+\s*[=<>!]+\s*[\w\'"]', line):
        return True, 'sql'
    
    # Check for table-like output (rows with | or tab alignment)
    if '|' in line or re.match(r'^\s*[-]+\s*$', line):
        return True, 'output'
    
    return False, ''


def format_code_blocks(text: str) -> str:
    """Identify and format code blocks in text.
    
    This helps markdown generators recognize code blocks.
    """
    lines = text.split('\n')
    result = []
    in_code_block = False
    code_block_type = ''
    code_buffer = []
    
    for line in lines:
        is_code, code_type = detect_code_block(line)
        
        if is_code and not in_code_block:
            # Start of code block
            in_code_block = True
            code_block_type = code_type
            code_buffer = [line]
        elif is_code and in_code_block:
            # Continue code block
            code_buffer.append(line)
        elif not is_code and in_code_block:
            # End of code block
            if len(code_buffer) >= 2:  # Only format if it's actually a block
                result.append(f"```{code_block_type}")
                result.extend(code_buffer)
                result.append("```")
            else:
                result.extend(code_buffer)
            in_code_block = False
            code_buffer = []
            result.append(line)
        else:
            result.append(line)
    
    # Handle code block at end of text
    if in_code_block and code_buffer:
        if len(code_buffer) >= 2:
            result.append(f"```{code_block_type}")
            result.extend(code_buffer)
            result.append("```")
        else:
            result.extend(code_buffer)
    
    return '\n'.join(result)


def clean_text_for_students(text: str, deduplicate: bool = True) -> str:
    """Main cleaning function optimized for student learning.
    
    This function:
    1. Removes headers, footers, and page numbers
    2. Cleans figure references
    3. Fixes OCR artifacts
    4. Normalizes broken line breaks
    5. Removes duplicate paragraphs
    6. Normalizes whitespace
    
    Args:
        text: Raw extracted text from PDF
        deduplicate: Whether to apply deduplication (default: True)
        
    Returns:
        Cleaned text suitable for student consumption
    """
    # Step 1: Normalize whitespace
    text = normalize_text(text)
    
    # Step 2: Remove headers and footers
    text = remove_headers_footers_aggressive(text)
    
    # Step 3: Clean figure references
    text = clean_figure_references(text)
    
    # Step 4: Fix OCR artifacts
    text = fix_ocr_artifacts(text)
    
    # Step 5: Normalize broken line breaks
    text = normalize_line_breaks(text)
    
    # Step 6: Fix broken formatting
    text = fix_broken_formatting(text)
    
    # Step 7: Remove duplicate paragraphs (if enabled)
    if deduplicate:
        text = deduplicate_text(text, min_length=30)
        text = deduplicate_repeated_lines(text, min_repeats=3)
    
    # Step 8: Final whitespace normalization
    text = _MULTI_NL.sub('\n\n', text)  # Keep paragraph breaks
    text = _SPACE_TABS.sub(' ', text)
    
    return text.strip()


# ============================================================================
# Legacy Functions (for backward compatibility)
# ============================================================================

def strip_repeated_headers_footers(
    pages: list[tuple[int, str]],
    *,
    head_lines: int = 2,
    foot_lines: int = 2,
    min_pages: int = 5,
    ratio: float = 0.6,
    max_line_len: int = 80,
) -> list[tuple[int, str]]:
    """Heuristic removal of repeating headers/footers.

    Safe default: only triggers when there are enough pages.
    """
    if len(pages) < min_pages:
        return pages

    head_counter: Counter[str] = Counter()
    foot_counter: Counter[str] = Counter()

    split_pages: list[tuple[int, list[str]]] = []
    for page, text in pages:
        lines = [ln.strip() for ln in text.splitlines()]
        split_pages.append((page, lines))
        for ln in lines[:head_lines]:
            if 0 < len(ln) <= max_line_len:
                head_counter[ln] += 1
        for ln in lines[-foot_lines:]:
            if 0 < len(ln) <= max_line_len:
                foot_counter[ln] += 1

    threshold = int(len(pages) * ratio)
    head_remove = {ln for ln, c in head_counter.items() if c >= threshold}
    foot_remove = {ln for ln, c in foot_counter.items() if c >= threshold}

    cleaned: list[tuple[int, str]] = []
    for page, lines in split_pages:
        out_lines = []
        for i, ln in enumerate(lines):
            if i < head_lines and ln in head_remove:
                continue
            if i >= len(lines) - foot_lines and ln in foot_remove:
                continue
            out_lines.append(ln)
        cleaned.append((page, "\n".join(out_lines)))

    return cleaned


def clean_pages_for_students(
    pages: list[tuple[int, str]]
) -> list[tuple[int, str]]:
    """Clean all pages with student-optimized settings.
    
    Args:
        pages: List of (page_number, text) tuples
        
    Returns:
        List of cleaned (page_number, text) tuples
    """
    cleaned = []
    for page_num, text in pages:
        cleaned_text = clean_text_for_students(text)
        cleaned.append((page_num, cleaned_text))
    
    return cleaned
