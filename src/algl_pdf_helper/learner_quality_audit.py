"""Learner-facing content quality audit for exported concept markdown.

Provides deterministic (no-LLM) quality checks that flag concepts whose
explanations or examples are too corrupted or semantically wrong to show
to learners as-is.

Exported symbols
----------------
LearnerQualityResult       -- dataclass with readabilityStatus, readabilityWarnings,
                              exampleQuality, learnerSafeSummary
audit_concept_markdown     -- main entry point; analyses raw markdown text and
                              returns a LearnerQualityResult
build_learner_safe_key_points  -- derive always-safe bullet points from structured
                                  concept metadata (title, keywords, sections, pages)
extract_learner_safe_sql_blocks -- extract prose-free SQL blocks from markdown for
                                   use as learnerSafeExamples
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

ReadabilityStatus = Literal["ok", "fallback_only"]
ExampleQuality = Literal["valid", "filtered", "hidden"]


@dataclass
class LearnerQualityResult:
    """Quality verdict for a single concept's exported markdown."""

    readabilityStatus: ReadabilityStatus
    """'ok' — safe to show; 'fallback_only' — explanation is too corrupted."""

    readabilityWarnings: list[str] = field(default_factory=list)
    """Non-fatal quality issues recorded for diagnostics."""

    exampleQuality: ExampleQuality = "valid"
    """'valid' — examples are usable; 'filtered' — examples have debris but
    something is salvageable; 'hidden' — examples are too broken to show."""

    learnerSafeSummary: str = ""
    """Always-safe fallback text: '{title}: {definition}'.  Present even when
    readabilityStatus == 'fallback_only'."""


# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

# OCR garble indicators: malformed HTML entities and encoding artefacts
_GARBLE_RE = re.compile(
    r"(?:"
    r"&[a-z]{1,4};|"           # incomplete/wrong HTML entities (&c; &s; &i;)
    r"[A-Z]\x26[a-z];|"        # e.g. h&c;h
    r"\b[a-z]+\x26[a-z]+\b|"   # word&word (missing space/encoding artefact)
    r"[^\x00-\x7F]{3,}"        # 3+ consecutive non-ASCII (encoding soup)
    r")",
    re.IGNORECASE,
)

# UI/screenshot rendering artifacts: block elements and checkbox characters from
# PDF screenshot pages (geometric shapes U+25A0-25FF, misc symbols U+2600-27BF),
# plus "E2l"/"E2I" which are common OCR mis-reads of the ☑ checkbox character.
_UI_ARTIFACT_RE = re.compile(
    r"(?:"
    r"[\u25A0-\u25FF\u2600-\u27BF\u2B00-\u2BFF]|"  # Unicode block/geometric chars
    r"\bE2[lI]\b"                                    # OCR artefact for ☑ checkbox
    r")",
)

# Structural corruption markers: words that are garbled versions of common
# structural terms, indicating severe OCR mis-read of chapter/section headers.
# "Cliapter" (garbled "Chapter"), comma-inside-word ("develop,nent"),
# and "lnforma" (garbled "Informa…").
_STRUCTURAL_CORRUPTION_RE = re.compile(
    r"(?:"
    r"\bC[li]i?apter\b|"            # garbled "Chapter" (e.g. "Cliapter")
    r"\b[a-zA-Z]{3,},[a-zA-Z]{2,}\b|"  # OCR comma-inside-word ("develop,nent")
    r"\blnforma[a-zA-Z]{2,}\b"      # garbled "Information/Informational"
    r")",
    re.IGNORECASE,
)

# Table-of-contents pollution signals in explanation prose
_TOC_RE = re.compile(
    r"(?:"
    r"\bChapter\s+\d+|"
    r"\bPart\s+[IVX]+|"
    r"\bSection\s+\d+\.\d+|"
    r"\.{4,}\s*\d+|"            # "........  328"  (page refs with dots)
    r"\bpage\s+\d{2,}"
    r")",
    re.IGNORECASE,
)

# Marketing / publisher boilerplate
_MARKETING_RE = re.compile(
    r"(?:"
    r"\bpublisher\b|\bMurach\b.*\bpublishing\b|"
    r"\bISBN\b|\bCopyright\s+\d{4}|"
    r"\bAll rights reserved\b|"
    r"\bprinted in\b"
    r")",
    re.IGNORECASE,
)

# Section headers inside markdown (## Explanation, ## Examples, ## Common Mistakes)
_SECTION_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)

# SQL code fence blocks
_CODE_BLOCK_RE = re.compile(r"```sql(.*?)```", re.DOTALL | re.IGNORECASE)

# Common English function words that appear in prose but rarely in pure SQL
_ENGLISH_FUNCTION_WORDS_RE = re.compile(
    r"\b(?:the|this|that|which|we|you|it|they|have|has|is|are|was|were|"
    r"can|will|be|not|if|with|from|by|an|what|how|when|where|whether|"
    r"also|such|only|more|most|all|both|each|every|some|any|would|should)\b",
    re.IGNORECASE,
)

# OCR corruption patterns inside SQL blocks
# These catch garbled tokens, incomplete words, and encoding artifacts
# NOTE: We intentionally DON'T match table.column patterns (valid SQL)
_SQL_OCR_CORRUPTION_RE = re.compile(
    r"(?:"
    r"\b[a-z]{2,},[a-z]{2,}\b|"                   # comma inside word: "develop,nent" (not "a,b")
    r"\b[a-z]*\*[a-z]+\b|"                        # asterisk inside word: "incLcount" (not "*" alone)
    r"\b[a-z]+'[a-z]+\b|"                         # apostrophe inside word: "Develop'ment"
    r"\b[a-z]+\d[a-z]+\b|"                        # digit inside word: "E2I"
    r"\bE2[lI]\b|"                                # OCR artifact for checkbox
    r"\b[a-zA-Z]*[^\x00-\x7F\s]+[a-zA-Z]*"        # non-ASCII chars
    r")",
    re.IGNORECASE,
)

# Mixed programming language indicators in SQL blocks
# Catches Java, C++, PL/SQL artifacts that shouldn't be in pure SQL examples
_SQL_MIXED_LANGUAGE_RE = re.compile(
    r"(?:"
    r"\b(?:public|private|protected|static|void|class|interface|extends|implements)\b|"
    r"\b(?:String|Integer|Boolean|int|boolean|char|float|double)\s+[a-zA-Z_]\w*\s*[=;:]\b|"
    r"\b(?:DECLARE|BEGIN|END|EXCEPTION|WHEN)\s+(?!.*\b(?:SELECT|INSERT|UPDATE|DELETE)\b)|"
    r"\b[a-zA-Z_]+\.[a-zA-Z_]+\s*\([^)]*\)\s*\{[^}]*\}|"  # method calls with braces
    r"\bnew\s+[A-Z][a-zA-Z]*\s*\(|"                        # Java-style object creation
    r"System\s*\.\s*(?:out|err|in)\s*\."                   # System.out.println etc
    r")",
    re.IGNORECASE,
)

# Navigation/index text patterns - not valid SQL
_SQL_NAVIGATION_TEXT_RE = re.compile(
    r"(?:"
    r"\b(?:insert|delete|update|select|create|drop)\s+(?:operation|statement|query|versus|vs)\b|"
    r"\b(?:node splits?|merge|redistribution|minimum occupancy|index)\b[^;]*$|"
    r"\b(?:page|chapter|section)\s+\d+|"
    r"\.{3,}\s*\d+\s*$|"                                    # ellipsis with page number
    r"^\s*[\-\u2022\u25E6]\s*[a-z]+\s*,\s*[a-z]+"            # bullet list of keywords
    r")",
    re.IGNORECASE,
)

# Placeholder/no-example patterns
_SQL_PLACEHOLDER_RE = re.compile(
    r"^\s*--\s*No specific example available",
    re.IGNORECASE,
)

# Valid SQL statement starters (for structure validation)
_SQL_VALID_STARTERS_RE = re.compile(
    r"^\s*(?:SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|WITH|BEGIN|COMMIT|ROLLBACK|GRANT|REVOKE|EXPLAIN|DESCRIBE|SHOW|USE|SET)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_section(md_text: str, section_name: str) -> str:
    """Return the text under a given ## Section heading, stopping at next ##."""
    pattern = re.compile(
        rf"^##\s+{re.escape(section_name)}\s*\n(.*?)(?=^##|\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    m = pattern.search(md_text)
    return m.group(1).strip() if m else ""


def _word_count(text: str) -> int:
    return len(text.split())


def _garble_density(text: str) -> float:
    """Fraction of text characters that are garble matches (0.0–1.0)."""
    if not text:
        return 0.0
    total_garble = sum(len(m.group()) for m in _GARBLE_RE.finditer(text))
    return total_garble / max(len(text), 1)


def _toc_hit_count(text: str) -> int:
    return len(_TOC_RE.findall(text))


def _marketing_hit_count(text: str) -> int:
    return len(_MARKETING_RE.findall(text))


def _title_keywords(title: str, definition: str) -> set[str]:
    """Extract meaningful keyword stems from title and definition.

    Returns lower-case tokens longer than 3 chars, excluding SQL stop-words.
    """
    _STOP = {
        "with", "from", "into", "that", "this", "which", "where", "when",
        "select", "using", "have", "been", "will", "shall", "more", "than",
        "what", "each", "some", "over", "also", "both", "most", "only",
    }
    tokens = re.findall(r"[a-zA-Z]{4,}", title + " " + definition)
    return {t.lower() for t in tokens if t.lower() not in _STOP}


def _keyword_overlap_ratio(keywords: set[str], text: str) -> float:
    """Fraction of title keywords found anywhere in explanation text (0.0–1.0)."""
    if not keywords or not text:
        return 0.0
    text_lower = text.lower()
    hits = sum(1 for kw in keywords if kw in text_lower)
    return hits / len(keywords)


def _duplication_ratio(text: str) -> float:
    """Estimate text duplication: fraction of sentences that are repeated.

    Splits the text on sentence-ending punctuation and newlines into
    fragments of ≥8 words, then counts how many appear more than once.
    Returns 0.0 (no duplication) – 1.0 (all sentences duplicated).
    """
    fragments = [
        s.strip()
        for s in re.split(r"[.\n!]+", text)
        if len(s.strip().split()) >= 8
    ]
    if len(fragments) < 4:
        return 0.0
    seen: set[str] = set()
    dups = 0
    for frag in fragments:
        if frag in seen:
            dups += 1
        seen.add(frag)
    return dups / len(fragments)


def _ui_artifact_density(text: str) -> float:
    """Fraction of text characters that are UI/screenshot rendering artifacts.

    PDF pages containing screenshots or GUI form layouts get OCR'd as a mix
    of real text and block/checkbox characters.  High density of these chars
    (►, □, ■, E2I OCR artifacts for ☑, etc.) indicates the extracted text is
    from a screenshot page rather than narrative prose.
    """
    if not text:
        return 0.0
    total = sum(len(m.group()) for m in _UI_ARTIFACT_RE.finditer(text))
    return total / max(len(text), 1)


def _structural_corruption_count(text: str) -> int:
    """Count distinct structural corruption markers in text.

    Markers include garbled chapter headers ("Cliapter"), comma-embedded OCR
    artefacts ("develop,nent"), and garbled section labels ("lnformation").
    Two or more such markers in an explanation strongly indicate the extraction
    pulled content from a screenshot or navigation page, not learner prose.
    """
    return len(_STRUCTURAL_CORRUPTION_RE.findall(text))


def _prose_contamination_ratio(sql_blocks: list[str]) -> float:
    """Fraction of SQL code blocks that contain embedded English prose.

    A block is considered contaminated when more than 40 % of its non-empty
    lines contain 3+ common English function words (the, is, are, can, …).
    Pure SQL lines rarely contain these words; natural-language sentences
    almost always do.
    """
    if not sql_blocks:
        return 0.0
    contaminated = 0
    for block in sql_blocks:
        lines = block.strip().splitlines()
        non_empty = [ln.strip() for ln in lines if ln.strip()]
        if not non_empty:
            continue
        prose_lines = sum(
            1
            for ln in non_empty
            if len(_ENGLISH_FUNCTION_WORDS_RE.findall(ln)) >= 3
        )
        if prose_lines / len(non_empty) > 0.40:
            contaminated += 1
    return contaminated / len(sql_blocks)


# ---------------------------------------------------------------------------
# Main audit function
# ---------------------------------------------------------------------------

# Tunable thresholds
_GARBLE_DENSITY_THRESHOLD = 0.008   # > 0.8 % of explanation chars are garble → flag
_TOC_HITS_THRESHOLD = 3             # 3+ TOC patterns in explanation → TOC pollution
_MARKETING_HITS_THRESHOLD = 2       # 2+ marketing phrases → publisher boilerplate
_KEYWORD_OVERLAP_MIN = 0.15         # < 15% of title keywords in explanation → drift
_DUPLICATION_RATIO_THRESHOLD = 0.40 # > 40% repeated windows → duplication
_PROSE_IN_SQL_THRESHOLD = 0.50      # > 50% SQL blocks have prose → SQL contamination
_EXPLANATION_MIN_WORDS = 40         # fewer words → too-thin explanation
_UI_ARTIFACT_DENSITY_THRESHOLD = 0.010   # > 1% UI chars → screenshot page extracted
_STRUCTURAL_CORRUPTION_THRESHOLD = 2     # 2+ structural corruption markers → garbled


def audit_concept_markdown(
    md_text: str,
    concept_id: str,
    title: str,
    definition: str,
) -> LearnerQualityResult:
    """Audit a concept's markdown for learner-facing content quality.

    This function is deterministic (no external calls) and executes in O(n)
    where n is the length of ``md_text``.

    Parameters
    ----------
    md_text:
        Full raw content of the exported concept .md file.
    concept_id:
        Bare concept ID (e.g. ``"1nf"``), used for context in warnings.
    title:
        Human-readable concept title (e.g. ``"First Normal Form (1NF)"``).
    definition:
        Short definition from the YAML front-matter.

    Returns
    -------
    LearnerQualityResult
        Quality verdict including readabilityStatus, warnings, exampleQuality,
        and a learnerSafeSummary that is always safe to show.
    """
    warnings: list[str] = []
    blocking_flags: list[str] = []

    # Always-safe fallback text
    safe_summary = f"{title}: {definition}".strip(": ").strip()

    explanation = _extract_section(md_text, "Explanation")
    sql_blocks = [m.group(1) for m in _CODE_BLOCK_RE.finditer(md_text)]

    # ------------------------------------------------------------------
    # Check 1: OCR / garble density
    # ------------------------------------------------------------------
    garble = _garble_density(explanation)
    if garble > _GARBLE_DENSITY_THRESHOLD:
        blocking_flags.append(
            f"garble_density={garble:.3f} exceeds threshold "
            f"({_GARBLE_DENSITY_THRESHOLD}) — likely OCR corruption"
        )

    # ------------------------------------------------------------------
    # Check 2: Table-of-contents pollution
    # ------------------------------------------------------------------
    toc_hits = _toc_hit_count(explanation)
    if toc_hits >= _TOC_HITS_THRESHOLD:
        blocking_flags.append(
            f"toc_pollution: {toc_hits} TOC-like patterns in explanation "
            f"(threshold {_TOC_HITS_THRESHOLD}) — content is an index page"
        )

    # ------------------------------------------------------------------
    # Check 3: Publisher / marketing boilerplate
    # ------------------------------------------------------------------
    mkt_hits = _marketing_hit_count(explanation)
    if mkt_hits >= _MARKETING_HITS_THRESHOLD:
        blocking_flags.append(
            f"marketing_boilerplate: {mkt_hits} publisher phrases detected"
        )

    # ------------------------------------------------------------------
    # Check 4: Semantic drift — title keywords absent from explanation
    # ------------------------------------------------------------------
    kw = _title_keywords(title, definition)
    if len(kw) >= 2:  # only meaningful when we have enough keywords
        overlap = _keyword_overlap_ratio(kw, explanation)
        if overlap < _KEYWORD_OVERLAP_MIN:
            blocking_flags.append(
                f"semantic_drift: only {overlap:.0%} of title keywords "
                f"({sorted(kw)}) appear in explanation — content may be "
                f"about a different topic"
            )

    # ------------------------------------------------------------------
    # Check 5: Content duplication
    # ------------------------------------------------------------------
    dup_ratio = _duplication_ratio(explanation)
    if dup_ratio > _DUPLICATION_RATIO_THRESHOLD:
        warnings.append(
            f"duplication: {dup_ratio:.0%} of explanation windows are repeated "
            f"(threshold {_DUPLICATION_RATIO_THRESHOLD:.0%})"
        )

    # ------------------------------------------------------------------
    # Check 6: SQL example contamination (prose mixed into code blocks)
    # ------------------------------------------------------------------
    prose_ratio = _prose_contamination_ratio(sql_blocks)
    if prose_ratio > _PROSE_IN_SQL_THRESHOLD:
        warnings.append(
            f"sql_contamination: {prose_ratio:.0%} of SQL code blocks contain "
            f"embedded English prose (threshold {_PROSE_IN_SQL_THRESHOLD:.0%})"
        )

    # ------------------------------------------------------------------
    # Check 7: Explanation too thin
    # ------------------------------------------------------------------
    exp_words = _word_count(explanation)
    if exp_words < _EXPLANATION_MIN_WORDS:
        warnings.append(
            f"thin_explanation: only {exp_words} words in explanation "
            f"(minimum {_EXPLANATION_MIN_WORDS})"
        )

    # ------------------------------------------------------------------
    # Check 8: UI/screenshot rendering artifact density
    # PDFs with embedded screenshots produce block characters (►, □, ■)
    # and "E2I" OCR mis-reads when the screenshot is extracted as text.
    # High density means the explanation was pulled from a screenshot page
    # rather than from learner-readable prose.
    # ------------------------------------------------------------------
    ui_density = _ui_artifact_density(explanation)
    if ui_density > _UI_ARTIFACT_DENSITY_THRESHOLD:
        blocking_flags.append(
            f"ui_artifact_density={ui_density:.3f} exceeds threshold "
            f"({_UI_ARTIFACT_DENSITY_THRESHOLD}) — explanation contains "
            f"screenshot/form rendering artefacts (block chars, checkbox OCR)"
        )

    # ------------------------------------------------------------------
    # Check 9: Structural corruption markers
    # Garbled structural words ("Cliapter", "develop,nent") signal that
    # the OCR captured a chapter header or navigation page, not the
    # actual concept explanation. Two or more such markers are a reliable
    # signal of misaligned extraction.
    # ------------------------------------------------------------------
    struct_hits = _structural_corruption_count(explanation)
    if struct_hits >= _STRUCTURAL_CORRUPTION_THRESHOLD:
        blocking_flags.append(
            f"structural_corruption: {struct_hits} garbled structural markers "
            f"(threshold {_STRUCTURAL_CORRUPTION_THRESHOLD}) — explanation "
            f"contains OCR artefacts of chapter/navigation text"
        )

    # ------------------------------------------------------------------
    # Aggregate readabilityStatus
    # ------------------------------------------------------------------
    readability_status: ReadabilityStatus = (
        "fallback_only" if blocking_flags else "ok"
    )

    all_warnings = blocking_flags + warnings

    # ------------------------------------------------------------------
    # Aggregate exampleQuality
    # ------------------------------------------------------------------
    if not sql_blocks:
        example_quality: ExampleQuality = "hidden"
    elif prose_ratio > _PROSE_IN_SQL_THRESHOLD or readability_status == "fallback_only":
        example_quality = "filtered"
    else:
        example_quality = "valid"

    return LearnerQualityResult(
        readabilityStatus=readability_status,
        readabilityWarnings=all_warnings,
        exampleQuality=example_quality,
        learnerSafeSummary=safe_summary,
    )


# ---------------------------------------------------------------------------
# Richer learner-safe fallback content helpers
# ---------------------------------------------------------------------------

# Human-readable names for section keys stored in concept-map chunkIds
_SECTION_READABLE: dict[str, str] = {
    "definition": "definition",
    "explanation": "explanation",
    "examples": "worked examples",
    "commonMistakes": "common mistakes",
    "syntax": "syntax reference",
    "notes": "notes",
    "tips": "tips",
    "practice": "practice problems",
    "summary": "summary",
    "reference": "reference",
    "overview": "overview",
}


def build_learner_safe_key_points(
    title: str,
    definition: str,
    keywords: list[str],
    related_concepts: list[str],
    source_section_titles: list[str],
    page_span: dict | None,
) -> list[str]:
    """Build a deterministic list of always-safe key points from structured metadata.

    Safe because it uses only pre-validated fields (title, definition, keywords,
    related concept IDs, section names, page numbers) — never raw extracted prose.
    Useful as richer fallback content when ``readabilityStatus == 'fallback_only'``.

    Parameters
    ----------
    title:
        Human-readable concept title.
    definition:
        Short definition (shortExcerpt from the unit record).
    keywords:
        Tag/keyword list from the concept manifest (e.g. ``["normalization", "1nf"]``).
    related_concepts:
        Related concept IDs (bare IDs, e.g. ``["2nf", "3nf"]``).
    source_section_titles:
        Sorted list of section names present in the concept's chunkIds
        (e.g. ``["commonMistakes", "definition", "examples"]``).
    page_span:
        Dict with ``"start"`` and ``"end"`` int keys, or ``None``.

    Returns
    -------
    list[str]
        Ordered list of plain-text bullets safe to render verbatim.
        Empty list only when all inputs are empty.
    """
    points: list[str] = []

    # 1. Concept identity — from pre-validated definition field
    if definition:
        points.append(f"{title} refers to: {definition}")

    # 2. Key topic labels from structured tags
    if keywords:
        readable = ", ".join(kw.replace("-", " ") for kw in keywords)
        points.append(f"Key topics: {readable}")

    # 3. Sections available in source textbook
    readable_sections = [
        _SECTION_READABLE.get(s, s.replace("_", " ").replace("-", " "))
        for s in sorted(source_section_titles)
    ]
    if readable_sections:
        points.append(f"Textbook covers: {', '.join(readable_sections)}")

    # 4. Related concept IDs (up to 3, converted to readable form)
    if related_concepts:
        readable_related = ", ".join(
            c.replace("-", " ") for c in related_concepts[:3]
        )
        points.append(f"Related concepts: {readable_related}")

    # 5. Page reference from page span
    if page_span:
        start = page_span.get("start")
        end = page_span.get("end")
        if start and end and start != end:
            points.append(f"Source: pages {start}\u2013{end}")
        elif start:
            points.append(f"Source: page {start}")

    return points


def extract_learner_safe_sql_blocks(md_text: str) -> list[dict[str, str]]:
    """Extract SQL code blocks that are free of corruption and safe for learners.

    A block is "safe" only if it passes ALL of these checks:
    1. ≤ 40% of lines contain embedded English prose (3+ function words)
    2. No OCR corruption (garbled tokens like "staternents", punctuation inside words)
    3. No mixed programming languages (Java, PL/SQL artifacts, method calls with braces)
    4. No navigation/index text ("insert operation, node splits", chapter references)
    5. Not a placeholder ("-- No specific example available")
    6. Must start with a valid SQL keyword or be a recognizable SQL fragment

    This is intentionally strict: we prefer fewer clean examples over many
    contaminated ones. Corrupted examples teach wrong patterns.

    Parameters
    ----------
    md_text:
        Full raw markdown text of an exported concept file.

    Returns
    -------
    list[dict[str, str]]
        Up to 3 entries, each ``{"title": "SQL Example N", "sql": "<clean sql>"}``.
        Empty list when no clean blocks are found.
    """
    safe: list[dict[str, str]] = []
    for i, m in enumerate(_CODE_BLOCK_RE.finditer(md_text), 1):
        block = m.group(1).strip()
        if not block:
            continue

        # Skip placeholder examples
        if _SQL_PLACEHOLDER_RE.search(block):
            continue

        lines = block.splitlines()
        non_empty = [ln.strip() for ln in lines if ln.strip()]
        if not non_empty:
            continue

        # Check 1: Prose contamination (existing logic)
        prose_lines = sum(
            1
            for ln in non_empty
            if len(_ENGLISH_FUNCTION_WORDS_RE.findall(ln)) >= 3
        )
        if prose_lines / len(non_empty) > 0.40:
            continue

        # Check 2: OCR corruption (garbled tokens)
        if _SQL_OCR_CORRUPTION_RE.search(block):
            continue

        # Check 3: Mixed programming languages
        if _SQL_MIXED_LANGUAGE_RE.search(block):
            continue

        # Check 4: Navigation/index text (not actual SQL)
        if _SQL_NAVIGATION_TEXT_RE.search(block):
            continue

        # Check 5: Must look like valid SQL structure
        # Either starts with a SQL keyword, or contains recognizable SQL patterns
        first_line = non_empty[0] if non_empty else ""
        has_valid_start = _SQL_VALID_STARTERS_RE.match(first_line) is not None
        has_sql_pattern = bool(re.search(r"\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN|VALUES|CREATE|TABLE)\b", block, re.IGNORECASE))

        # If it doesn't start with SQL keyword, check if it's at least a SQL fragment
        # (e.g., a WHERE clause continuation)
        if not has_valid_start and not has_sql_pattern:
            continue

        # Check 6: Minimum complexity - reject trivial SQL fragments
        # A meaningful example should have enough tokens to demonstrate a pattern
        # Count SQL keywords, identifiers, and operators like *
        tokens = re.findall(r"\b[a-zA-Z_]+\b|\*|,|;|=|<|>|\+|\-|\/", block)
        if len(tokens) < 3:  # e.g., "SELECT tags" = 2 tokens, too trivial
            continue

        # Check 7: Must have proper SQL clause structure
        # A valid example should have at least one clause beyond just the verb
        # e.g., "SELECT foo FROM bar" not just "SELECT foo"
        has_from_clause = bool(re.search(r"\bFROM\b", block, re.IGNORECASE))
        has_where_clause = bool(re.search(r"\bWHERE\b", block, re.IGNORECASE))
        has_values_clause = bool(re.search(r"\bVALUES\b", block, re.IGNORECASE))
        has_set_clause = bool(re.search(r"\bSET\b", block, re.IGNORECASE))
        has_into_clause = bool(re.search(r"\bINTO\b", block, re.IGNORECASE))

        # For SELECT/INSERT/UPDATE/DELETE, require at least one clause
        starts_with_verb = bool(re.match(r"\s*(?:SELECT|INSERT|UPDATE|DELETE)", first_line, re.IGNORECASE))
        if starts_with_verb:
            has_clause = has_from_clause or has_where_clause or has_values_clause or has_set_clause or has_into_clause
            if not has_clause:
                continue

        # Check 8: Sentence-like structure detection
        # If block contains periods followed by spaces (sentence endings), it's likely prose
        sentence_endings = len(re.findall(r'\.[\s]*[A-Z]', block))
        if sentence_endings >= 2:
            continue

        safe.append({"title": f"SQL Example {i}", "sql": block})
        if len(safe) >= 3:
            break
    return safe
