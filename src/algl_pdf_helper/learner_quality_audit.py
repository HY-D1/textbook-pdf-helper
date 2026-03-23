"""Learner-facing content quality audit for exported concept markdown.

Provides deterministic (no-LLM) quality checks that flag concepts whose
explanations or examples are too corrupted or semantically wrong to show
to learners as-is.

Exported symbols
----------------
LearnerQualityResult  -- dataclass with readabilityStatus, readabilityWarnings,
                         exampleQuality, learnerSafeSummary
audit_concept_markdown -- main entry point; analyses raw markdown text and
                         returns a LearnerQualityResult
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
