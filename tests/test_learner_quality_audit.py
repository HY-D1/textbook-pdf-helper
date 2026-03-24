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
    build_learner_safe_key_points,
    extract_learner_safe_sql_blocks,
)
from algl_pdf_helper.export_sqladapt import build_concept_quality_index


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


# ---------------------------------------------------------------------------
# UI/screenshot rendering artifact density (Check 8)
# ---------------------------------------------------------------------------


class TestUIArtifactDensity:
    """Explanation bodies from PDF screenshot pages contain block/checkbox chars."""

    # Simulates content extracted from a page full of form checkboxes and UI
    # elements — as happens when a textbook screenshot page is OCR'd.
    _SCREENSHOT_EXPLANATION = (
        "Cliapter 2 How to use MySQL Workbench and other develop,nent tools "
        "The column definitions for the Vendors table ► E2I □ □ D D D D D "
        "E2I □ □ E2I □ D D □ □ D D □ □ □ □ □ □ E2I □ □ D □ □ E2I □ D D □ "
        "Table: vendors Columns: vendor_id INT(11) AlPK vendor_name varcha "
        "vendor_addressl varcha vendor_address2 varcha □ □ □ □ E2I E2I D "
        "D D D □ □ □ D D D □ □ D □ □ D D □ D □ □ E2I □ □ D □ □ E2I □ D "
        "► to view the column definitions for a table, right-click the table"
    )

    def test_ui_artifacts_make_status_fallback_only(self):
        md = _make_md(
            title="SELECT Statement",
            definition="Retrieve rows from a table",
            explanation=self._SCREENSHOT_EXPLANATION,
        )
        result = audit_concept_markdown(
            md, "select-statement-murach",
            "SELECT Statement", "Retrieve rows from a table",
        )
        assert result.readabilityStatus == "fallback_only", (
            f"Screenshot-page content should be fallback_only. "
            f"Warnings: {result.readabilityWarnings}"
        )

    def test_ui_artifact_warning_mentions_density(self):
        md = _make_md(
            title="SELECT Statement",
            definition="Retrieve rows from a table",
            explanation=self._SCREENSHOT_EXPLANATION,
        )
        result = audit_concept_markdown(
            md, "select-statement-murach",
            "SELECT Statement", "Retrieve rows from a table",
        )
        combined = " ".join(result.readabilityWarnings).lower()
        assert "ui_artifact" in combined or "artifact" in combined, (
            f"Warning should mention ui artifact. Got: {result.readabilityWarnings}"
        )

    def test_clean_explanation_not_flagged_by_ui_rule(self):
        clean = (
            "The SELECT statement retrieves rows from one or more tables. "
            "Use the WHERE clause to filter which rows are returned. "
            "The FROM clause names the table or tables to query. "
            "You may join multiple tables using an explicit JOIN or a comma in FROM. "
            "The ORDER BY clause sorts the result set by one or more columns."
        )
        md = _make_md(
            title="SELECT Statement",
            definition="Retrieve rows from a table",
            explanation=clean,
        )
        result = audit_concept_markdown(
            md, "select-basic",
            "SELECT Statement", "Retrieve rows from a table",
        )
        ui_warnings = [w for w in result.readabilityWarnings if "ui_artifact" in w.lower()]
        assert ui_warnings == [], f"Clean text should not trigger ui_artifact: {ui_warnings}"


# ---------------------------------------------------------------------------
# Structural corruption markers (Check 9)
# ---------------------------------------------------------------------------


class TestStructuralCorruption:
    """Garbled chapter/section headers embedded in explanation prose."""

    # Simulates an explanation that was extracted from a chapter navigation
    # page — OCR produced "Cliapter" and comma-in-word artifacts.
    _GARBLED_STRUCTURAL = (
        "Cliapter 3 How to retrieve data from a single table. "
        "The WHERE clause filters rows based on a search condition. "
        "You can use comparison operators such as =, <>, <, >, <=, >=. "
        "The develop,nent tools provided by MySQL Workbench let you execute "
        "individual SQL staten,ents interactively. "
        "An introduction to the SELECT staten,ent to get you started quickly."
    )

    def test_structural_corruption_makes_status_fallback_only(self):
        md = _make_md(
            title="WHERE Clause",
            definition="Filtering rows with comparison operators",
            explanation=self._GARBLED_STRUCTURAL,
        )
        result = audit_concept_markdown(
            md, "where-clause-murach",
            "WHERE Clause", "Filtering rows with comparison operators",
        )
        assert result.readabilityStatus == "fallback_only", (
            f"Garbled structural markers should produce fallback_only. "
            f"Warnings: {result.readabilityWarnings}"
        )

    def test_structural_corruption_warning_mentions_structural(self):
        md = _make_md(
            title="WHERE Clause",
            definition="Filtering rows with comparison operators",
            explanation=self._GARBLED_STRUCTURAL,
        )
        result = audit_concept_markdown(
            md, "where-clause-murach",
            "WHERE Clause", "Filtering rows with comparison operators",
        )
        combined = " ".join(result.readabilityWarnings).lower()
        assert "structural" in combined or "corruption" in combined, (
            f"Warning should mention structural corruption. Got: {result.readabilityWarnings}"
        )

    def test_single_garbled_marker_is_not_flagged(self):
        """One isolated garbled marker should NOT trigger the rule (threshold = 2)."""
        one_garble = (
            "Cliapter 3 introduces the WHERE clause. "
            "The WHERE clause filters rows using a Boolean expression. "
            "You can combine conditions with AND and OR operators. "
            "NULL values require the IS NULL or IS NOT NULL predicates. "
            "Comparison operators include equals, not-equals, less, and greater than."
        )
        md = _make_md(
            title="WHERE Clause",
            definition="Filtering rows with comparison operators",
            explanation=one_garble,
        )
        result = audit_concept_markdown(
            md, "where-clause-murach",
            "WHERE Clause", "Filtering rows with comparison operators",
        )
        struct_warnings = [
            w for w in result.readabilityWarnings if "structural_corruption" in w.lower()
        ]
        assert struct_warnings == [], (
            f"One garbled marker should not trigger structural_corruption: {struct_warnings}"
        )

    def test_clean_explanation_not_flagged_by_structural_rule(self):
        clean = (
            "The WHERE clause filters rows using a search condition. "
            "Conditions use comparison operators: =, <>, <, >, <=, >=. "
            "Logical operators AND, OR, NOT combine multiple conditions. "
            "The IN operator tests whether a value is in a list of values. "
            "BETWEEN tests an inclusive range, LIKE tests a string pattern."
        )
        md = _make_md(
            title="WHERE Clause",
            definition="Filtering rows with comparison operators",
            explanation=clean,
        )
        result = audit_concept_markdown(
            md, "where-clause-murach",
            "WHERE Clause", "Filtering rows with comparison operators",
        )
        struct_warnings = [
            w for w in result.readabilityWarnings if "structural_corruption" in w.lower()
        ]
        assert struct_warnings == [], f"Clean text triggered structural_corruption: {struct_warnings}"


# ---------------------------------------------------------------------------
# Real-concept regression tests using built output from the two PDFs
# ---------------------------------------------------------------------------


class TestRealConceptRegressions:
    """Regression tests against actual concept markdown files from the real build.

    These tests require the textbook-static build to be present at
    output/textbook-static/.  They are skipped if the build does not exist.
    """

    _TEXTBOOK_STATIC = "output/textbook-static"

    def _read_concept(self, doc_id: str, concept_id: str) -> str | None:
        import os
        path = os.path.join(self._TEXTBOOK_STATIC, "concepts", doc_id, f"{concept_id}.md")
        if not os.path.exists(path):
            return None
        return open(path, encoding="utf-8").read()

    def _get_concept_meta(self, doc_id: str, concept_id: str) -> dict | None:
        """Get title and definition from concept-map.json for a concept."""
        import json, os
        cm_path = os.path.join(self._TEXTBOOK_STATIC, "concept-map.json")
        if not os.path.exists(cm_path):
            return None
        data = json.load(open(cm_path))
        key = f"{doc_id}/{concept_id}"
        entry = data.get("concepts", {}).get(key)
        return entry  # may be None

    @pytest.mark.skipif(
        not __import__("os").path.exists("output/textbook-static/concepts"),
        reason="Real build output not present",
    )
    def test_select_statement_murach_is_fallback_only(self):
        """select-statement-murach has high UI artifact density → must be fallback_only."""
        doc_id = "murachs-mysql-3rd-edition"
        concept_id = "select-statement-murach"
        md = self._read_concept(doc_id, concept_id)
        if md is None:
            pytest.skip(f"{concept_id}.md not in build output")
        meta = self._get_concept_meta(doc_id, concept_id) or {}
        title = meta.get("title", "SELECT Statement")
        definition = meta.get("definition", "Retrieve rows from a table")
        result = audit_concept_markdown(md, concept_id, title, definition)
        assert result.readabilityStatus == "fallback_only", (
            f"select-statement-murach should be fallback_only (UI artifact density). "
            f"Got: {result.readabilityStatus}. Warnings: {result.readabilityWarnings}"
        )

    @pytest.mark.skipif(
        not __import__("os").path.exists("output/textbook-static/concepts"),
        reason="Real build output not present",
    )
    def test_inner_join_murach_is_ok(self):
        """inner-join-murach has clean prose → must remain ok."""
        doc_id = "murachs-mysql-3rd-edition"
        concept_id = "inner-join-murach"
        md = self._read_concept(doc_id, concept_id)
        if md is None:
            pytest.skip(f"{concept_id}.md not in build output")
        meta = self._get_concept_meta(doc_id, concept_id) or {}
        title = meta.get("title", "Inner Join")
        definition = meta.get("definition", "Combine rows from two tables using a join condition")
        result = audit_concept_markdown(md, concept_id, title, definition)
        assert result.readabilityStatus == "ok", (
            f"inner-join-murach should remain ok. "
            f"Got: {result.readabilityStatus}. Warnings: {result.readabilityWarnings}"
        )

    @pytest.mark.skipif(
        not __import__("os").path.exists("output/textbook-static/concepts"),
        reason="Real build output not present",
    )
    def test_where_clause_murach_is_fallback_only(self):
        """where-clause-murach has garbled structural markers → must be fallback_only."""
        doc_id = "murachs-mysql-3rd-edition"
        concept_id = "where-clause-murach"
        md = self._read_concept(doc_id, concept_id)
        if md is None:
            pytest.skip(f"{concept_id}.md not in build output")
        meta = self._get_concept_meta(doc_id, concept_id) or {}
        title = meta.get("title", "WHERE Clause")
        definition = meta.get("definition", "Filtering rows with comparison operators")
        result = audit_concept_markdown(md, concept_id, title, definition)
        assert result.readabilityStatus == "fallback_only", (
            f"where-clause-murach should be fallback_only. "
            f"Got: {result.readabilityStatus}. Warnings: {result.readabilityWarnings}"
        )


# ---------------------------------------------------------------------------
# Learner-safe key points (build_learner_safe_key_points)
# ---------------------------------------------------------------------------


class TestBuildLearnerSafeKeyPoints:
    """Tests for build_learner_safe_key_points()."""

    def test_includes_title_and_definition(self):
        """Key points must include the formatted title and definition."""
        points = build_learner_safe_key_points(
            title="SELECT Statement",
            definition="Retrieve rows from a table",
            keywords=[],
            related_concepts=[],
            source_section_titles=[],
            page_span=None,
        )
        assert any("SELECT Statement" in p and "Retrieve rows" in p for p in points)

    def test_includes_keywords(self):
        """Key points should include formatted keywords."""
        points = build_learner_safe_key_points(
            title="JOIN",
            definition="Combine tables",
            keywords=["INNER", "OUTER", "LEFT"],
            related_concepts=[],
            source_section_titles=[],
            page_span=None,
        )
        keyword_point = [p for p in points if "Key topics:" in p]
        assert len(keyword_point) == 1
        assert "INNER" in keyword_point[0]
        assert "OUTER" in keyword_point[0]
        assert "LEFT" in keyword_point[0]

    def test_includes_related_concepts(self):
        """Key points should include related concepts."""
        points = build_learner_safe_key_points(
            title="WHERE Clause",
            definition="Filter rows",
            keywords=[],
            related_concepts=["comparison-operators", "null-values"],
            source_section_titles=[],
            page_span=None,
        )
        related_point = [p for p in points if "Related concepts:" in p]
        assert len(related_point) == 1
        # Function converts hyphens to spaces for readability
        assert "comparison operators" in related_point[0]
        assert "null values" in related_point[0]

    def test_includes_section_titles(self):
        """Key points should include source section titles."""
        points = build_learner_safe_key_points(
            title="GROUP BY",
            definition="Aggregate data",
            keywords=[],
            related_concepts=[],
            source_section_titles=["commonMistakes", "examples"],
            page_span=None,
        )
        section_point = [p for p in points if "Textbook covers:" in p]
        assert len(section_point) == 1
        assert "common mistakes" in section_point[0]  # mapped via _SECTION_READABLE
        assert "worked examples" in section_point[0]  # mapped via _SECTION_READABLE

    def test_includes_page_span(self):
        """Key points should include page range information."""
        points = build_learner_safe_key_points(
            title="Subquery",
            definition="Query within a query",
            keywords=[],
            related_concepts=[],
            source_section_titles=[],
            page_span={"start": 150, "end": 165},
        )
        page_point = [p for p in points if "Source:" in p]
        assert len(page_point) == 1
        assert "150" in page_point[0]
        assert "165" in page_point[0]

    def test_includes_single_page_span(self):
        """Key points should handle single page reference."""
        points = build_learner_safe_key_points(
            title="Subquery",
            definition="Query within a query",
            keywords=[],
            related_concepts=[],
            source_section_titles=[],
            page_span={"start": 42, "end": 42},
        )
        page_point = [p for p in points if "Source:" in p]
        assert len(page_point) == 1
        assert "page 42" in page_point[0]

    def test_empty_inputs_graceful(self):
        """Should handle empty lists and None gracefully."""
        points = build_learner_safe_key_points(
            title="Test Concept",
            definition="A test definition",
            keywords=[],
            related_concepts=[],
            source_section_titles=[],
            page_span=None,
        )
        # Should have just the title/definition point
        assert len(points) == 1
        assert "Test Concept" in points[0]
        assert "refers to:" in points[0]

    def test_section_readable_names_mapping(self):
        """Should map internal section keys to human-readable names."""
        points = build_learner_safe_key_points(
            title="Test",
            definition="Test definition",
            keywords=[],
            related_concepts=[],
            source_section_titles=["commonMistakes", "practice"],
            page_span=None,
        )
        section_point = [p for p in points if "Textbook covers:" in p][0]
        # Should use readable names from _SECTION_READABLE mapping
        assert "common mistakes" in section_point  # mapped from commonMistakes
        assert "practice problems" in section_point  # mapped from practice


# ---------------------------------------------------------------------------
# Learner-safe SQL extraction (extract_learner_safe_sql_blocks)
# ---------------------------------------------------------------------------


class TestExtractLearnerSafeSqlBlocks:
    """Tests for extract_learner_safe_sql_blocks()."""

    def test_extracts_clean_sql_block(self):
        """Should extract a clean SQL code block."""
        md = """# SELECT Statement

```sql
SELECT * FROM users WHERE id = 1;
```
"""
        blocks = extract_learner_safe_sql_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["sql"] == "SELECT * FROM users WHERE id = 1;"

    def test_rejects_block_with_embedded_prose(self):
        """Should reject SQL blocks containing English prose."""
        md = """# SELECT Statement

```sql
SELECT * FROM users;
This query retrieves all users from the table.
```
"""
        blocks = extract_learner_safe_sql_blocks(md)
        assert len(blocks) == 0  # Rejected due to prose contamination

    def test_extracts_multiple_clean_blocks(self):
        """Should extract multiple clean SQL blocks."""
        md = """# Examples

```sql
SELECT * FROM users;
```

Some text.

```sql
INSERT INTO logs VALUES (1, 'test');
```
"""
        blocks = extract_learner_safe_sql_blocks(md)
        assert len(blocks) == 2
        assert blocks[0]["sql"] == "SELECT * FROM users;"
        assert blocks[1]["sql"] == "INSERT INTO logs VALUES (1, 'test');"

    def test_generates_generic_title(self):
        """Should generate generic SQL Example N titles (not from headings)."""
        md = """# Query Examples

### Get All Users

```sql
SELECT * FROM users;
```
"""
        blocks = extract_learner_safe_sql_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["title"] == "SQL Example 1"

    def test_generates_generic_title_when_no_heading(self):
        """Should generate a generic title when no preceding heading."""
        md = """# Examples

Some intro text.

```sql
SELECT * FROM users;
```
"""
        blocks = extract_learner_safe_sql_blocks(md)
        assert len(blocks) == 1
        assert "Example" in blocks[0]["title"]

    def test_rejects_block_with_high_prose_contamination(self):
        """Should reject SQL blocks with >40% prose lines (3+ function words per line)."""
        # This block has SQL + prose line with "the", "from", "the" = 3 function words
        md = """```sql
SELECT * FROM users;
This query retrieves all rows from the table
```
"""
        blocks = extract_learner_safe_sql_blocks(md)
        # 50% prose (1 of 2 lines has 3+ function words) → rejected
        assert len(blocks) == 0

    def test_accepts_block_with_low_prose_contamination(self):
        """Should accept blocks with mostly SQL and minimal prose."""
        md = """```sql
SELECT * FROM users;
```
"""
        blocks = extract_learner_safe_sql_blocks(md)
        assert len(blocks) == 1
        assert "SELECT" in blocks[0]["sql"]

    def test_sql_comment_stays_in_sql_field(self):
        """SQL comments are kept in the sql field, not extracted separately."""
        md = """```sql
-- Retrieves all active users
SELECT * FROM users WHERE active = 1;
```
"""
        blocks = extract_learner_safe_sql_blocks(md)
        assert len(blocks) == 1
        # Comment stays in the SQL block
        assert "-- Retrieves all active users" in blocks[0]["sql"]
        # No separate explanation field is created
        assert "explanation" not in blocks[0]

    def test_handles_empty_sql_gracefully(self):
        """Should handle empty SQL blocks gracefully."""
        md = """```sql
```
"""
        blocks = extract_learner_safe_sql_blocks(md)
        assert len(blocks) == 0

    def test_preserves_sql_formatting(self):
        """Should preserve SQL formatting while cleaning."""
        md = """```sql
SELECT u.name, o.order_id
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE u.active = 1;
```
"""
        blocks = extract_learner_safe_sql_blocks(md)
        assert len(blocks) == 1
        assert "JOIN" in blocks[0]["sql"]
        assert "WHERE" in blocks[0]["sql"]


def _make_unit(
    namespaced_id: str,
    readability_status: str = "ok",
    example_quality: str = "valid",
    warnings: list | None = None,
    safe_summary: str = "Summary text",
) -> dict:
    """Build a minimal enriched unit dict suitable for the quality index builder."""
    doc_id, bare_id = namespaced_id.split("/", 1) if "/" in namespaced_id else ("doc", namespaced_id)
    return {
        "unitId": f"unit-{bare_id}",
        "sourceDocId": doc_id,
        "conceptId": bare_id,
        "namespacedId": namespaced_id,
        "title": bare_id.replace("-", " ").title(),
        "readabilityStatus": readability_status,
        "readabilityWarnings": warnings or [],
        "exampleQuality": example_quality,
        "learnerSafeSummary": safe_summary,
    }


class TestConceptQualityIndex:
    """Tests for build_concept_quality_index()."""

    def test_schema_version_header(self):
        index = build_concept_quality_index([], [])
        assert index["schemaVersion"] == "concept-quality-v1"

    def test_empty_units_produces_empty_index(self):
        index = build_concept_quality_index([], ["doc-a"])
        assert index["totalConcepts"] == 0
        assert index["qualityByConcept"] == {}

    def test_source_doc_ids_propagated(self):
        index = build_concept_quality_index([], ["murach", "ramakrishnan"])
        assert set(index["sourceDocIds"]) == {"murach", "ramakrishnan"}

    def test_bad_concept_gets_fallback_only(self):
        units = [
            _make_unit(
                "doc-a/1nf",
                readability_status="fallback_only",
                example_quality="filtered",
                warnings=["garble_density=0.02"],
                safe_summary="1NF: Eliminating repeating groups",
            )
        ]
        index = build_concept_quality_index(units, ["doc-a"])
        entry = index["qualityByConcept"]["doc-a/1nf"]
        assert entry["readabilityStatus"] == "fallback_only"
        assert entry["exampleQuality"] == "filtered"
        assert "garble_density" in entry["readabilityWarnings"][0]
        assert "1NF" in entry["learnerSafeSummary"]

    def test_clean_concept_is_ok(self):
        units = [
            _make_unit(
                "doc-a/select-basic",
                readability_status="ok",
                example_quality="valid",
                safe_summary="Select Statement: Retrieve rows from a table",
            )
        ]
        index = build_concept_quality_index(units, ["doc-a"])
        entry = index["qualityByConcept"]["doc-a/select-basic"]
        assert entry["readabilityStatus"] == "ok"
        assert entry["exampleQuality"] == "valid"
        assert entry["readabilityWarnings"] == []

    def test_keys_align_with_namespaced_ids(self):
        """Keys in qualityByConcept must exactly equal the namespacedId values."""
        units = [
            _make_unit("doc-a/join-inner"),
            _make_unit("doc-b/group-by"),
        ]
        index = build_concept_quality_index(units, ["doc-a", "doc-b"])
        assert set(index["qualityByConcept"].keys()) == {"doc-a/join-inner", "doc-b/group-by"}
        assert index["totalConcepts"] == 2

    def test_unit_without_namespaced_id_is_skipped(self):
        """Units with empty namespacedId must not appear in the index."""
        units = [
            {"unitId": "unit-x", "readabilityStatus": "ok", "exampleQuality": "valid",
             "readabilityWarnings": [], "learnerSafeSummary": "x", "namespacedId": ""},
            _make_unit("doc-a/select-basic"),
        ]
        index = build_concept_quality_index(units, ["doc-a"])
        assert set(index["qualityByConcept"].keys()) == {"doc-a/select-basic"}

    def test_total_concepts_matches_populated_entries(self):
        units = [_make_unit(f"doc-a/concept-{i}") for i in range(5)]
        index = build_concept_quality_index(units, ["doc-a"])
        assert index["totalConcepts"] == 5
        assert len(index["qualityByConcept"]) == 5
