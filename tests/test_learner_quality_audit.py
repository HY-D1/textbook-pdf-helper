"""Tests for the learner-facing content quality audit.

Covers:
    - garbled / OCR-corrupted explanation text
    - semantically wrong explanation (content drift)
    - table-of-contents-polluted explanation
    - SQL examples contaminated with embedded prose
    - content duplication
    - clean concept that must pass with status "ok"
    - learnerSafeSummary is always populated

Run with:
    PYTHONPATH=src python -m pytest tests/test_learner_quality_audit.py -v
"""

from __future__ import annotations

import pytest

from algl_pdf_helper.learner_quality_audit import (
    LearnerQualityResult,
    audit_concept_markdown,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_md(
    title: str = "Select Statement",
    definition: str = "Retrieve rows from a table",
    explanation: str = "The SELECT statement retrieves rows from one or more tables.",
    examples: str = "```sql\nSELECT * FROM employees;\n```",
    mistakes: str = "No common mistakes listed.",
) -> str:
    return f"""---
id: select-basic
title: {title}
definition: {definition}
difficulty: beginner
---

# {title}

## Definition
{definition}

## Explanation
{explanation}

## Examples
{examples}

## Common Mistakes
{mistakes}
"""


# ---------------------------------------------------------------------------
# Garbled / OCR-corrupted text
# ---------------------------------------------------------------------------


class TestGarbledText:
    """Explanation body that contains OCR garble artefacts."""

    _GARBLED_EXPLANATION = (
        "Stomge and Inde:rin,g 29,3 Clustered indexes h&c;h-indexcs are "
        "nonetJleless expensive to maintain. When a new record h&'3 to be "
        "inserted into a full leaf page a new leaf page must be allocated &c; "
        "and sorne existing records have to be moved. In dealing with the "
        "limitation that at most one index can be clustered it is often useful "
        "to consider whether the information."
    )

    def test_garble_makes_status_fallback_only(self):
        md = _make_md(explanation=self._GARBLED_EXPLANATION)
        result = audit_concept_markdown(md, "1nf", "First Normal Form (1NF)", "Eliminating repeating groups")
        assert result.readabilityStatus == "fallback_only"

    def test_garble_warning_mentions_garble_density(self):
        md = _make_md(explanation=self._GARBLED_EXPLANATION)
        result = audit_concept_markdown(md, "1nf", "First Normal Form (1NF)", "Eliminating repeating groups")
        combined = " ".join(result.readabilityWarnings).lower()
        assert "garble" in combined or "density" in combined

    def test_learner_safe_summary_always_populated(self):
        md = _make_md(explanation=self._GARBLED_EXPLANATION)
        result = audit_concept_markdown(md, "1nf", "First Normal Form (1NF)", "Eliminating repeating groups")
        assert result.learnerSafeSummary
        assert "First Normal Form" in result.learnerSafeSummary


# ---------------------------------------------------------------------------
# Semantic drift (wrong topic in explanation)
# ---------------------------------------------------------------------------


class TestSemanticDrift:
    """Explanation body that is about a completely different topic."""

    _DRIFT_EXPLANATION = (
        "Clustered indexes are expensive to maintain. When a new record needs "
        "to be inserted into a full leaf page, a new leaf page must be "
        "allocated and some existing records moved. Index-only evaluation "
        "avoids fetching the actual data records. B+ tree index on age can "
        "retrieve only tuples that satisfy the selection condition."
    )

    def test_drift_makes_status_fallback_only(self):
        """1NF concept whose explanation is entirely about B+ tree indexes."""
        md = _make_md(
            title="First Normal Form (1NF)",
            definition="Eliminating repeating groups and ensuring atomic values in normalization",
            explanation=self._DRIFT_EXPLANATION,
        )
        result = audit_concept_markdown(
            md,
            "1nf",
            "First Normal Form (1NF)",
            "Eliminating repeating groups and ensuring atomic values in normalization",
        )
        assert result.readabilityStatus == "fallback_only"

    def test_drift_warning_mentions_semantic(self):
        md = _make_md(
            title="First Normal Form (1NF)",
            definition="Eliminating repeating groups and ensuring atomic values in normalization",
            explanation=self._DRIFT_EXPLANATION,
        )
        result = audit_concept_markdown(
            md,
            "1nf",
            "First Normal Form (1NF)",
            "Eliminating repeating groups and ensuring atomic values in normalization",
        )
        combined = " ".join(result.readabilityWarnings).lower()
        assert "drift" in combined or "keyword" in combined or "topic" in combined

    def test_safe_summary_contains_definition(self):
        md = _make_md(
            title="First Normal Form (1NF)",
            definition="Eliminating repeating groups and ensuring atomic values in normalization",
            explanation=self._DRIFT_EXPLANATION,
        )
        result = audit_concept_markdown(
            md,
            "1nf",
            "First Normal Form (1NF)",
            "Eliminating repeating groups and ensuring atomic values in normalization",
        )
        assert "Eliminating repeating groups" in result.learnerSafeSummary


# ---------------------------------------------------------------------------
# Table-of-contents pollution
# ---------------------------------------------------------------------------


class TestTocPollution:
    """Explanation body that is really just a table of contents."""

    _TOC_EXPLANATION = (
        "Chapter 1: Introduction to Databases page 1 "
        "Chapter 2: The Entity-Relationship Model page 27 "
        "Chapter 3: The Relational Model page 58 "
        "Section 8.4 discusses file organizations. "
        "Chapter 8: Storage and Indexing page 270. "
        "Chapter 9: Storing Data: Disks and Files page 290. "
    )

    def test_toc_makes_status_fallback_only(self):
        md = _make_md(
            title="Data Independence",
            definition="Ability to change schema without affecting higher layers",
            explanation=self._TOC_EXPLANATION,
        )
        result = audit_concept_markdown(
            md, "data-independence", "Data Independence",
            "Ability to change schema without affecting higher layers"
        )
        assert result.readabilityStatus == "fallback_only"

    def test_toc_warning_mentions_pollution(self):
        md = _make_md(
            title="Data Independence",
            definition="Ability to change schema without affecting higher layers",
            explanation=self._TOC_EXPLANATION,
        )
        result = audit_concept_markdown(
            md, "data-independence", "Data Independence",
            "Ability to change schema without affecting higher layers"
        )
        combined = " ".join(result.readabilityWarnings).lower()
        assert "toc" in combined or "pollution" in combined or "index" in combined


# ---------------------------------------------------------------------------
# SQL example contamination
# ---------------------------------------------------------------------------


class TestSQLContamination:
    """SQL code blocks that contain embedded English prose sentences."""

    _CONTAMINATED_SQL = """\
```sql
SELECT FROM WHERE E.dno Employees E E.age > 40 If we have a H+ tree index on
age, we can use it to retrieve only tuples that satisfy the selection E.age>40.
Whether such an index is worthwhile depends first of all on the selectivity of
the condition. What fraction of the employees are older than 40?
```
```sql
DELETE specified using an equality condition. For each of the five file
organizations, what is the cost if no record qualifies? What is the cost if
the condition is not on a key?
```"""

    def test_contaminated_sql_sets_example_quality_filtered(self):
        md = _make_md(examples=self._CONTAMINATED_SQL)
        result = audit_concept_markdown(
            md, "select-basic", "Select Statement", "Retrieve rows from a table"
        )
        assert result.exampleQuality in ("filtered", "hidden")

    def test_contaminated_sql_adds_warning(self):
        md = _make_md(examples=self._CONTAMINATED_SQL)
        result = audit_concept_markdown(
            md, "select-basic", "Select Statement", "Retrieve rows from a table"
        )
        combined = " ".join(result.readabilityWarnings).lower()
        assert "sql" in combined or "contamination" in combined or "prose" in combined


# ---------------------------------------------------------------------------
# Duplicated explanation content
# ---------------------------------------------------------------------------


class TestDuplication:
    """Explanation that repeats the same paragraph verbatim."""

    _base_para = (
        "The GROUP BY clause groups rows that have the same values into "
        "summary rows. The GROUP BY statement is often used with aggregate "
        "functions to group the result-set by one or more columns. "
    )

    def test_heavy_duplication_adds_warning(self):
        # Repeat the same paragraph 6 times to create obvious duplication
        dup_explanation = self._base_para * 6
        md = _make_md(
            title="Group By",
            definition="Groups rows with same values into summary rows",
            explanation=dup_explanation,
        )
        result = audit_concept_markdown(
            md, "group-by", "Group By",
            "Groups rows with same values into summary rows"
        )
        combined = " ".join(result.readabilityWarnings).lower()
        assert "duplication" in combined or "repeated" in combined

    def test_moderate_text_no_duplication_warning(self):
        """A diverse paragraph should NOT trigger duplication warning."""
        clean_explanation = (
            "The GROUP BY clause is used to arrange identical data into "
            "groups. It collapses multiple rows with the same value in a "
            "specified column into a single row. This is typically combined "
            "with aggregate functions like COUNT, SUM, AVG, MAX, or MIN to "
            "compute a summary value for each group. For example, grouping "
            "orders by customer ID allows computing the total order value per "
            "customer. The HAVING clause then filters groups based on the "
            "aggregate result, acting like WHERE but for grouped data."
        )
        md = _make_md(
            title="Group By",
            definition="Groups rows with same values into summary rows",
            explanation=clean_explanation,
        )
        result = audit_concept_markdown(
            md, "group-by", "Group By",
            "Groups rows with same values into summary rows"
        )
        dup_warnings = [w for w in result.readabilityWarnings if "duplication" in w.lower()]
        assert dup_warnings == [], f"Unexpected duplication warning on clean text: {dup_warnings}"


# ---------------------------------------------------------------------------
# Clean concept — must pass with status "ok"
# ---------------------------------------------------------------------------


class TestCleanConcept:
    """A well-formed concept file should pass all checks."""

    _CLEAN_EXPLANATION = (
        "The SELECT statement is the most fundamental SQL command. It retrieves "
        "rows from one or more tables based on specified criteria. The basic "
        "syntax includes the SELECT keyword followed by column names, the FROM "
        "keyword followed by table names, and an optional WHERE clause to filter "
        "rows. SELECT can return all columns using the wildcard (*) or specific "
        "columns by name. The ORDER BY clause sorts the result set, and LIMIT "
        "restricts the number of rows returned."
    )

    _CLEAN_SQL = """\
```sql
SELECT employee_id, first_name, last_name, salary
FROM employees
WHERE department_id = 10
ORDER BY last_name;
```"""

    def test_clean_concept_is_ok(self):
        md = _make_md(
            title="Select Statement",
            definition="Retrieve rows from a table using SQL SELECT syntax",
            explanation=self._CLEAN_EXPLANATION,
            examples=self._CLEAN_SQL,
        )
        result = audit_concept_markdown(
            md,
            "select-basic",
            "Select Statement",
            "Retrieve rows from a table using SQL SELECT syntax",
        )
        assert result.readabilityStatus == "ok", (
            f"Clean concept flagged as fallback_only. Warnings: {result.readabilityWarnings}"
        )

    def test_clean_concept_example_quality_valid(self):
        md = _make_md(
            title="Select Statement",
            definition="Retrieve rows from a table using SQL SELECT syntax",
            explanation=self._CLEAN_EXPLANATION,
            examples=self._CLEAN_SQL,
        )
        result = audit_concept_markdown(
            md,
            "select-basic",
            "Select Statement",
            "Retrieve rows from a table using SQL SELECT syntax",
        )
        assert result.exampleQuality == "valid"

    def test_clean_concept_learner_safe_summary(self):
        md = _make_md(
            title="Select Statement",
            definition="Retrieve rows from a table using SQL SELECT syntax",
            explanation=self._CLEAN_EXPLANATION,
            examples=self._CLEAN_SQL,
        )
        result = audit_concept_markdown(
            md,
            "select-basic",
            "Select Statement",
            "Retrieve rows from a table using SQL SELECT syntax",
        )
        assert "Select Statement" in result.learnerSafeSummary
        assert "Retrieve rows" in result.learnerSafeSummary

    def test_no_examples_sets_hidden(self):
        """Concept with no SQL code blocks should have exampleQuality='hidden'."""
        md = _make_md(
            title="Select Statement",
            definition="Retrieve rows from a table",
            explanation=self._CLEAN_EXPLANATION,
            examples="No specific example available.",
        )
        result = audit_concept_markdown(
            md, "select-basic", "Select Statement", "Retrieve rows from a table"
        )
        assert result.exampleQuality == "hidden"


# ---------------------------------------------------------------------------
# LearnerSafeSummary always populated
# ---------------------------------------------------------------------------


class TestLearnerSafeSummary:
    def test_empty_markdown_still_has_summary(self):
        result = audit_concept_markdown("", "empty", "Joins", "Combining rows from tables")
        assert result.learnerSafeSummary  # not empty
        assert "Joins" in result.learnerSafeSummary

    def test_summary_format_title_colon_definition(self):
        result = audit_concept_markdown(
            "", "join", "Inner Join", "Returns only matching rows"
        )
        assert "Inner Join" in result.learnerSafeSummary
        assert "Returns only matching rows" in result.learnerSafeSummary

    def test_summary_not_just_colon(self):
        """Edge case: empty title and definition should not produce just ':'."""
        result = audit_concept_markdown("", "x", "", "")
        # Should gracefully handle empty inputs
        assert result.learnerSafeSummary != ":"


# ---------------------------------------------------------------------------
# Real bad concept: 1nf.md from the actual exported output
# ---------------------------------------------------------------------------


class TestRealExportedBadConcept:
    """Spot-check against the known-bad 1nf.md content pattern."""

    _BAD_EXPLANATION = (
        "Stomge and Inde:rin,g 29,3 Clustered indexes, while less expensive to maintain "
        "than a fully sorted file, are nonetJleless expensive to maintain. When a new "
        "record h&'3 to be inserted into a full leaf page, a new leaf page must be "
        "allocated and sorne existing records have to be moved to the new page. "
        "If records are identified by a combination of page id and slot, &'5 is typically "
        "the case in current database systems, all places in the datab&\"ie that point to a "
        "moved record must also be updated to point to the new location."
    )

    _BAD_EXAMPLES = """\
```sql
SELECT FROM WHERE E.dno Employees E E.age > 40 If we have a H+ tree index on age,
we can use it to retrieve only tuples that satisfy the selection E. age> 40.
Whether such an index is worthwhile depends first of all on the selectivity of the
condition. vVhat fraction of the employees are older than 40?
```"""

    def test_bad_1nf_is_fallback_only(self):
        md = _make_md(
            title="First Normal Form (1NF)",
            definition="Eliminating repeating groups and ensuring atomic values",
            explanation=self._BAD_EXPLANATION,
            examples=self._BAD_EXAMPLES,
        )
        result = audit_concept_markdown(
            md,
            "1nf",
            "First Normal Form (1NF)",
            "Eliminating repeating groups and ensuring atomic values",
        )
        assert result.readabilityStatus == "fallback_only", (
            f"Expected fallback_only for known-bad 1nf content. "
            f"Warnings: {result.readabilityWarnings}"
        )

    def test_bad_1nf_example_quality_not_valid(self):
        md = _make_md(
            title="First Normal Form (1NF)",
            definition="Eliminating repeating groups and ensuring atomic values",
            explanation=self._BAD_EXPLANATION,
            examples=self._BAD_EXAMPLES,
        )
        result = audit_concept_markdown(
            md,
            "1nf",
            "First Normal Form (1NF)",
            "Eliminating repeating groups and ensuring atomic values",
        )
        assert result.exampleQuality != "valid", (
            "Contaminated SQL examples should not be marked 'valid'"
        )
