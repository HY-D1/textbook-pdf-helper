from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from .clean import normalize_text


@dataclass
class Heading:
    """A detected heading in the PDF."""
    level: int  # 1 = chapter, 2 = section, 3 = subsection, etc.
    text: str
    page: int
    font_size: float = 0.0
    is_bold: bool = False
    confidence: float = 1.0  # Confidence this is actually a heading


@dataclass
class TOCEntry:
    """A table of contents entry."""
    level: int
    title: str
    page: int


@dataclass
class Chapter:
    """A chapter with its sections."""
    title: str
    start_page: int
    end_page: int | None = None
    sections: list[Section] = field(default_factory=list)
    headings: list[Heading] = field(default_factory=list)


@dataclass
class Section:
    """A section within a chapter."""
    title: str
    level: int
    start_page: int
    end_page: int | None = None
    subsections: list[Section] = field(default_factory=list)


@dataclass
class ConceptBoundary:
    """Estimated boundary of a concept based on headings."""
    concept_name: str
    heading: Heading
    start_page: int
    end_page: int | None = None
    confidence: float = 0.5
    suggested_keywords: list[str] = field(default_factory=list)


class StructureExtractor:
    """Extract document structure (TOC, headings, chapters) from PDFs."""

    # Common heading patterns
    CHAPTER_PATTERNS = [
        r'^chapter\s+(\d+|[ivxlc]+)[\s:.-]*(.+)?$',
        r'^ch\s*\.?\s*(\d+)[\s:.-]*(.+)?$',
        r'^(\d+)\s*\.\s+([A-Z][^a-z]*|[A-Z][a-z].+)$',  # "1. Introduction"
    ]

    SECTION_PATTERNS = [
        r'^(\d+\.\d+)\s+(.+)$',  # "1.1 Overview"
        r'^(\d+\.\d+\.\d+)\s+(.+)$',  # "1.1.1 Subsection"
    ]

    # Font size thresholds for heading detection (relative to body text)
    HEADING_SIZE_THRESHOLD = 1.2  # 20% larger than body
    SUBHEADING_SIZE_THRESHOLD = 1.1  # 10% larger than body

    def __init__(self):
        self.chapter_regexes = [re.compile(p, re.IGNORECASE) for p in self.CHAPTER_PATTERNS]
        self.section_regexes = [re.compile(p, re.IGNORECASE) for p in self.SECTION_PATTERNS]

    def extract_toc(self, pdf_path: Path) -> list[TOCEntry]:
        """Extract table of contents from PDF metadata.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of TOC entries with level, title, and page number
        """
        doc = fitz.open(pdf_path)
        toc_entries = []

        try:
            # Get TOC from PDF metadata
            toc = doc.get_toc()
            for level, title, page in toc:
                toc_entries.append(TOCEntry(
                    level=level,
                    title=normalize_text(title).strip(),
                    page=page
                ))
        finally:
            doc.close()

        return toc_entries

    def extract_headings(self, pdf_path: Path) -> list[Heading]:
        """Extract headings by analyzing text formatting.

        Uses font size, bold formatting, and text patterns to identify
        chapter and section headings.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of detected headings sorted by page
        """
        doc = fitz.open(pdf_path)
        headings = []

        try:
            # First pass: collect font statistics
            font_sizes = []
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                blocks = page.get_text("dict")["blocks"]

                for block in blocks:
                    if "lines" not in block:
                        continue
                    for line in block["lines"]:
                        for span in line["spans"]:
                            font_sizes.append(span["size"])

            if not font_sizes:
                return headings

            # Calculate body text size (mode of font sizes)
            body_size = max(set(font_sizes), key=font_sizes.count)
            heading_threshold = body_size * self.HEADING_SIZE_THRESHOLD

            # Second pass: detect headings
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                blocks = page.get_text("dict")["blocks"]

                for block in blocks:
                    if "lines" not in block:
                        continue

                    for line in block["lines"]:
                        line_text = ""
                        max_font_size = 0
                        is_bold = False

                        for span in line["spans"]:
                            line_text += span["text"]
                            max_font_size = max(max_font_size, span["size"])
                            if span["flags"] & 2**4:  # Bold flag
                                is_bold = True

                        line_text = normalize_text(line_text).strip()
                        if not line_text or len(line_text) > 200:
                            continue

                        # Determine if this is a heading
                        level, confidence = self._classify_heading(
                            line_text, max_font_size, is_bold,
                            heading_threshold, body_size
                        )

                        if level > 0:
                            headings.append(Heading(
                                level=level,
                                text=line_text,
                                page=page_num + 1,
                                font_size=max_font_size,
                                is_bold=is_bold,
                                confidence=confidence
                            ))

        finally:
            doc.close()

        # Sort by page and remove duplicates
        headings = self._deduplicate_headings(headings)
        return headings

    def _classify_heading(
        self,
        text: str,
        font_size: float,
        is_bold: bool,
        heading_threshold: float,
        body_size: float
    ) -> tuple[int, float]:
        """Classify text as a heading and determine its level.

        Returns:
            Tuple of (level, confidence) where level 0 means not a heading
        """
        confidence = 0.0
        level = 0

        # Check chapter patterns
        for pattern in self.chapter_regexes:
            if pattern.match(text):
                level = 1
                confidence = 0.95
                return level, confidence

        # Check section patterns
        for pattern in self.section_regexes:
            match = pattern.match(text)
            if match:
                section_num = match.group(1)
                # Determine level by number of dots
                dot_count = section_num.count(".")
                level = min(dot_count + 1, 4)  # 1 dot = level 2, 2 dots = level 3, etc.
                confidence = 0.9
                return level, confidence

        # Check font-based heuristics
        if font_size >= heading_threshold:
            if is_bold:
                level = 2
                confidence = 0.75
            else:
                level = 2
                confidence = 0.6
        elif font_size >= body_size * self.SUBHEADING_SIZE_THRESHOLD and is_bold:
            level = 3
            confidence = 0.5

        # Boost confidence for short, title-like text
        if level > 0:
            word_count = len(text.split())
            if word_count <= 5:
                confidence += 0.1
            elif word_count > 15:
                confidence -= 0.2

            # Check for title case
            if text.istitle() or text.upper() == text:
                confidence += 0.1

        return level, max(0.0, min(1.0, confidence))

    def _deduplicate_headings(self, headings: list[Heading]) -> list[Heading]:
        """Remove duplicate headings that appear on the same or adjacent pages."""
        if not headings:
            return headings

        # Sort by page, then by level
        headings.sort(key=lambda h: (h.page, h.level))

        deduplicated = []
        last_text = ""
        last_page = 0

        for heading in headings:
            # Skip if very similar to last heading on same/adjacent page
            text_normalized = heading.text.lower().strip()
            if text_normalized == last_text and abs(heading.page - last_page) <= 1:
                continue

            deduplicated.append(heading)
            last_text = text_normalized
            last_page = heading.page

        return deduplicated

    def extract_chapters(self, pdf_path: Path) -> list[Chapter]:
        """Extract chapters with their sections from the PDF.

        Uses TOC if available, otherwise falls back to heading detection.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of chapters with nested sections
        """
        # Try TOC first
        toc = self.extract_toc(pdf_path)
        if toc:
            return self._chapters_from_toc(toc, pdf_path)

        # Fall back to heading detection
        headings = self.extract_headings(pdf_path)
        return self._chapters_from_headings(headings, pdf_path)

    def _chapters_from_toc(self, toc: list[TOCEntry], pdf_path: Path) -> list[Chapter]:
        """Build chapter structure from TOC entries."""
        chapters = []
        current_chapter: Chapter | None = None
        current_section: Section | None = None

        # Get total pages for end_page calculation
        doc = fitz.open(pdf_path)
        total_pages = doc.page_count
        doc.close()

        for i, entry in enumerate(toc):
            # Determine end page
            end_page = toc[i + 1].page - 1 if i + 1 < len(toc) else total_pages

            if entry.level == 1:
                # New chapter
                if current_chapter:
                    current_chapter.end_page = entry.page - 1
                    chapters.append(current_chapter)

                current_chapter = Chapter(
                    title=entry.title,
                    start_page=entry.page,
                    end_page=end_page,
                    headings=[Heading(level=1, text=entry.title, page=entry.page)]
                )
                current_section = None

            elif entry.level == 2 and current_chapter:
                # New section in current chapter
                section = Section(
                    title=entry.title,
                    level=entry.level,
                    start_page=entry.page,
                    end_page=end_page
                )
                current_chapter.sections.append(section)
                current_section = section

            elif entry.level >= 3 and current_section:
                # Subsection
                subsection = Section(
                    title=entry.title,
                    level=entry.level,
                    start_page=entry.page,
                    end_page=end_page
                )
                current_section.subsections.append(subsection)

        # Don't forget the last chapter
        if current_chapter:
            if current_chapter.end_page is None:
                current_chapter.end_page = total_pages
            chapters.append(current_chapter)

        return chapters

    def _chapters_from_headings(self, headings: list[Heading], pdf_path: Path) -> list[Chapter]:
        """Build chapter structure from detected headings."""
        chapters = []
        current_chapter: Chapter | None = None
        current_section: Section | None = None

        # Get total pages
        doc = fitz.open(pdf_path)
        total_pages = doc.page_count
        doc.close()

        for i, heading in enumerate(headings):
            # Determine end page
            end_page = headings[i + 1].page - 1 if i + 1 < len(headings) else total_pages

            if heading.level == 1:
                # New chapter
                if current_chapter:
                    chapters.append(current_chapter)

                current_chapter = Chapter(
                    title=heading.text,
                    start_page=heading.page,
                    end_page=end_page,
                    headings=[heading]
                )
                current_section = None

            elif heading.level == 2 and current_chapter:
                section = Section(
                    title=heading.text,
                    level=heading.level,
                    start_page=heading.page,
                    end_page=end_page
                )
                current_chapter.sections.append(section)
                current_section = section

            elif heading.level >= 3 and current_section:
                subsection = Section(
                    title=heading.text,
                    level=heading.level,
                    start_page=heading.page,
                    end_page=end_page
                )
                current_section.subsections.append(subsection)

            # Add all headings to chapter for reference
            if current_chapter and heading.level > 1:
                current_chapter.headings.append(heading)

        if current_chapter:
            chapters.append(current_chapter)

        return chapters

    def estimate_concept_boundaries(
        self,
        pdf_path: Path,
        concept_keywords: dict[str, list[str]] | None = None
    ) -> list[ConceptBoundary]:
        """Estimate concept boundaries based on headings and keywords.

        Args:
            pdf_path: Path to the PDF file
            concept_keywords: Optional mapping of concept names to keywords

        Returns:
            List of estimated concept boundaries with confidence scores
        """
        headings = self.extract_headings(pdf_path)
        doc = fitz.open(pdf_path)
        total_pages = doc.page_count
        doc.close()

        boundaries = []

        for i, heading in enumerate(headings):
            # Determine end page
            end_page = headings[i + 1].page - 1 if i + 1 < len(headings) else total_pages

            # Extract concept name from heading
            concept_name = self._extract_concept_name(heading.text)

            # Calculate confidence based on heading level and format
            confidence = heading.confidence

            # Generate suggested keywords
            keywords = self._generate_keywords(heading.text, concept_keywords)

            boundary = ConceptBoundary(
                concept_name=concept_name,
                heading=heading,
                start_page=heading.page,
                end_page=end_page,
                confidence=confidence,
                suggested_keywords=keywords
            )
            boundaries.append(boundary)

        return boundaries

    def _extract_concept_name(self, heading_text: str) -> str:
        """Extract a clean concept name from heading text."""
        # Remove chapter/section numbers
        text = heading_text
        for pattern in self.chapter_regexes + self.section_regexes:
            match = pattern.match(text)
            if match:
                # Get the title part (last group)
                if match.lastindex and match.lastindex > 1:
                    text = match.group(match.lastindex)
                break

        # Clean up
        text = text.strip()
        # Convert to snake_case for ID
        concept_id = re.sub(r'[^\w\s]', '', text.lower())
        concept_id = re.sub(r'\s+', '-', concept_id).strip('-')

        return text or concept_id

    def _generate_keywords(
        self,
        heading_text: str,
        concept_keywords: dict[str, list[str]] | None
    ) -> list[str]:
        """Generate suggested keywords for a concept."""
        keywords = []
        text_lower = heading_text.lower()

        # Add words from heading (excluding common words)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'in', 'on', 'at', 'to', 'for',
                      'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'be',
                      'chapter', 'section', 'introduction', 'overview', 'summary'}

        words = [w for w in re.findall(r'\w+', text_lower) if w not in stop_words]
        keywords.extend(words[:5])  # Top 5 words

        # Check against concept registry if provided
        if concept_keywords:
            for concept, concept_words in concept_keywords.items():
                if any(kw in text_lower for kw in concept_words):
                    keywords.append(concept)

        return list(set(keywords))[:8]  # Deduplicate and limit

    def get_structure_summary(self, pdf_path: Path) -> dict[str, Any]:
        """Get a complete summary of document structure.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary with TOC, headings, chapters, and statistics
        """
        doc = fitz.open(pdf_path)
        total_pages = doc.page_count
        doc.close()

        toc = self.extract_toc(pdf_path)
        headings = self.extract_headings(pdf_path)
        chapters = self.extract_chapters(pdf_path)

        return {
            "total_pages": total_pages,
            "has_toc": len(toc) > 0,
            "toc_entries": len(toc),
            "detected_headings": len(headings),
            "chapters": [
                {
                    "title": ch.title,
                    "start_page": ch.start_page,
                    "end_page": ch.end_page,
                    "section_count": len(ch.sections),
                }
                for ch in chapters
            ],
            "headings_by_level": {
                level: len([h for h in headings if h.level == level])
                for level in range(1, 5)
            },
        }
