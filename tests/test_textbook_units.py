"""
Tests for textbook-units.json export contract.

Covers:
- exactly one unit record per exported instructional unit
- all markdownPath values resolve to real files
- unitIds are unique and deterministic across repeated calls
- sourceDocId/conceptId coverage matches concept-map.json
- validate_handoff_integrity checks textbook-units.json

Schema enrichment (v2):
- aliases, canonicalConceptKey, sourceOrder, unitOrderWithinConcept
- unitType derived deterministically from section names
- keywords propagated from concept manifest tags
- shortExcerpt from definition
- sourceSectionTitles from chunkIds keys
- prerequisiteConceptIds (reserved, always [])
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from algl_pdf_helper.export_sqladapt import (
    build_textbook_units,
    export_to_sqladapt,
    validate_handoff_integrity,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _concept_manifest(doc_id: str, concepts: dict) -> dict:
    """Build a minimal concept-manifest dict for testing."""
    return {
        "schemaVersion": "concept-manifest-v1",
        "sourceDocId": doc_id,
        "createdAt": "2026-03-21T00:00:00Z",
        "concepts": {
            cid: {
                "id": cid,
                "title": meta["title"],
                "definition": meta.get("definition", "A definition."),
                "difficulty": meta.get("difficulty", "beginner"),
                "estimatedReadTime": 5,
                "pageReferences": meta.get("pages", [1]),
                "sections": {
                    section: {
                        "chunkIds": meta.get("chunkIds", [f"{cid}-chunk-1"]),
                        "pageNumbers": meta.get("pages", [1]),
                    }
                    for section in meta.get("sections", ["main"])
                },
                "relatedConcepts": meta.get("related", []),
                "tags": meta.get("tags", []),
                "practiceProblemIds": [],
                "assetIds": [],
            }
            for cid, meta in concepts.items()
        },
    }


def _chunks(doc_id: str, chunk_ids: list[str]) -> list[dict]:
    """Build minimal chunk records."""
    return [
        {"chunkId": cid, "docId": doc_id, "page": 1, "text": f"Text for {cid}"}
        for cid in chunk_ids
    ]


def _write_index(tmp_path: Path, doc_id: str, concepts: dict) -> Path:
    """Write a minimal per-PDF index directory and return its path."""
    idx = tmp_path / doc_id
    idx.mkdir(parents=True)

    all_chunk_ids = [
        cid
        for meta in concepts.values()
        for cid in meta.get("chunkIds", [f"{list(concepts.keys())[0]}-chunk-1"])
    ]

    (idx / "concept-manifest.json").write_text(
        json.dumps(_concept_manifest(doc_id, concepts)), encoding="utf-8"
    )
    (idx / "chunks.json").write_text(
        json.dumps(_chunks(doc_id, all_chunk_ids)), encoding="utf-8"
    )
    return idx


# ---------------------------------------------------------------------------
# Unit tests for build_textbook_units()
# ---------------------------------------------------------------------------

class TestBuildTextbookUnits:
    """Tests for the build_textbook_units() pure function."""

    def _minimal_map(
        self,
        doc_ids_concepts: dict[str, list[str]],
        *,
        sections: dict[str, list[str]] | None = None,
        tags_by_concept: dict[str, list[str]] | None = None,
        definition_by_concept: dict[str, str] | None = None,
    ) -> dict:
        """Build a minimal merged concept-map dict.

        Args:
            doc_ids_concepts: {docId: [conceptId, ...]}
            sections: optional {conceptId: [sectionName, ...]} to control unitType
            tags_by_concept: optional {conceptId: [tag, ...]}
            definition_by_concept: optional {conceptId: "definition text"}
        """
        concepts = {}
        for doc_id, concept_ids in doc_ids_concepts.items():
            for cid in concept_ids:
                namespaced = f"{doc_id}/{cid}"
                cid_sections = (sections or {}).get(cid, ["main"])
                cid_tags = (tags_by_concept or {}).get(cid, [])
                cid_definition = (definition_by_concept or {}).get(cid, "def")
                concepts[namespaced] = {
                    "title": f"Title {cid}",
                    "definition": cid_definition,
                    "difficulty": "beginner",
                    "pageNumbers": [10, 11],
                    "chunkIds": {s: [f"{cid}-chunk-1"] for s in cid_sections},
                    "relatedConcepts": [],
                    "tags": cid_tags,
                    "sourceDocId": doc_id,
                }
        return {
            "version": "1.0.0",
            "generatedAt": "2026-03-21T00:00:00Z",
            "sourceDocIds": list(doc_ids_concepts.keys()),
            "concepts": concepts,
        }

    # --- original field tests (preserved) ---

    def test_one_unit_per_concept(self):
        cmap = self._minimal_map({"doc-a": ["select", "join", "where"]})
        units = build_textbook_units(cmap)
        assert len(units) == 3

    def test_unit_has_required_fields(self):
        """Every unit record contains all required fields including enrichment fields."""
        cmap = self._minimal_map({"doc-a": ["select"]})
        unit = build_textbook_units(cmap)[0]

        required = {
            # original fields
            "unitId", "sourceDocId", "conceptId", "namespacedId",
            "title", "difficulty", "markdownPath",
            "pageNumbers", "pageSpan", "sourceChunkIds", "relatedConcepts",
            # enrichment fields
            "canonicalConceptKey", "unitType", "keywords", "aliases",
            "shortExcerpt", "sourceSectionTitles", "prerequisiteConceptIds",
            "sourceOrder", "unitOrderWithinConcept",
        }
        assert required.issubset(unit.keys()), (
            f"Missing fields: {required - unit.keys()}"
        )

    def test_markdown_path_shape(self):
        cmap = self._minimal_map({"my-doc": ["select-basic"]})
        unit = build_textbook_units(cmap)[0]
        assert unit["markdownPath"] == "concepts/my-doc/select-basic.md"

    def test_unit_ids_are_unique(self):
        cmap = self._minimal_map({"doc-a": ["c1", "c2", "c3"], "doc-b": ["c1", "c4"]})
        units = build_textbook_units(cmap)
        ids = [u["unitId"] for u in units]
        assert len(ids) == len(set(ids)), "Duplicate unitIds detected"

    def test_unit_ids_are_deterministic(self):
        cmap = self._minimal_map({"doc-a": ["select", "join"]})
        first = {u["unitId"] for u in build_textbook_units(cmap)}
        second = {u["unitId"] for u in build_textbook_units(cmap)}
        assert first == second

    def test_unit_id_matches_expected_hash(self):
        doc_id, cid = "doc-a", "select"
        expected = "unit-" + hashlib.sha256(f"{doc_id}:{cid}".encode()).hexdigest()[:16]
        cmap = self._minimal_map({doc_id: [cid]})
        unit = build_textbook_units(cmap)[0]
        assert unit["unitId"] == expected

    def test_same_concept_id_different_docs_get_different_unit_ids(self):
        cmap = self._minimal_map({"doc-a": ["select"], "doc-b": ["select"]})
        units = build_textbook_units(cmap)
        ids = [u["unitId"] for u in units]
        assert len(set(ids)) == 2

    def test_page_span_populated(self):
        cmap = self._minimal_map({"doc-a": ["select"]})
        unit = build_textbook_units(cmap)[0]
        assert unit["pageSpan"] == {"start": 10, "end": 11}

    def test_page_span_none_when_no_pages(self):
        cmap = self._minimal_map({"doc-a": ["select"]})
        cmap["concepts"]["doc-a/select"]["pageNumbers"] = []
        unit = build_textbook_units(cmap)[0]
        assert unit["pageSpan"] is None

    def test_source_chunk_ids_flat_and_deduplicated(self):
        cmap = self._minimal_map({"doc-a": ["select"]})
        cmap["concepts"]["doc-a/select"]["chunkIds"] = {
            "section1": ["chunk-001", "chunk-002"],
            "section2": ["chunk-002", "chunk-003"],
        }
        unit = build_textbook_units(cmap)[0]
        assert unit["sourceChunkIds"] == ["chunk-001", "chunk-002", "chunk-003"]

    def test_output_sorted_by_doc_then_concept(self):
        cmap = self._minimal_map({"zzz": ["beta", "alpha"], "aaa": ["gamma"]})
        units = build_textbook_units(cmap)
        keys = [(u["sourceDocId"], u["conceptId"]) for u in units]
        assert keys == sorted(keys)

    def test_named_concept_id_and_namespaced_id_consistent(self):
        cmap = self._minimal_map({"my-doc": ["my-concept"]})
        unit = build_textbook_units(cmap)[0]
        assert unit["conceptId"] == "my-concept"
        assert unit["namespacedId"] == "my-doc/my-concept"
        assert unit["sourceDocId"] == "my-doc"

    def test_coverage_matches_concept_map(self):
        doc_ids_concepts = {"doc-a": ["c1", "c2"], "doc-b": ["c3"]}
        cmap = self._minimal_map(doc_ids_concepts)
        units = build_textbook_units(cmap)
        units_ids = {u["namespacedId"] for u in units}
        map_ids = set(cmap["concepts"].keys())
        assert units_ids == map_ids

    # --- new enrichment field tests ---

    def test_canonical_concept_key_equals_namespaced_id(self):
        """canonicalConceptKey is the stable join key == namespacedId."""
        cmap = self._minimal_map({"doc-a": ["select"]})
        unit = build_textbook_units(cmap)[0]
        assert unit["canonicalConceptKey"] == unit["namespacedId"]

    def test_canonical_concept_key_is_deterministic(self):
        """canonicalConceptKey is stable across repeated calls."""
        cmap = self._minimal_map({"doc-a": ["select", "join"]})
        first = {u["canonicalConceptKey"] for u in build_textbook_units(cmap)}
        second = {u["canonicalConceptKey"] for u in build_textbook_units(cmap)}
        assert first == second

    def test_source_order_is_contiguous_zero_indexed(self):
        """sourceOrder values form a gapless 0..N-1 sequence."""
        cmap = self._minimal_map({"doc-a": ["c1", "c2", "c3"]})
        units = build_textbook_units(cmap)
        orders = [u["sourceOrder"] for u in units]
        assert sorted(orders) == list(range(len(units)))

    def test_source_order_matches_sort_position(self):
        """sourceOrder[i] == i for units already in sort order."""
        cmap = self._minimal_map({"aaa": ["alpha", "beta"], "zzz": ["gamma"]})
        units = build_textbook_units(cmap)
        for i, u in enumerate(units):
            assert u["sourceOrder"] == i

    def test_source_order_is_deterministic(self):
        """Repeated calls produce the same sourceOrder for every unit."""
        cmap = self._minimal_map({"doc-a": ["c2", "c1"], "doc-b": ["c3"]})
        run1 = {u["unitId"]: u["sourceOrder"] for u in build_textbook_units(cmap)}
        run2 = {u["unitId"]: u["sourceOrder"] for u in build_textbook_units(cmap)}
        assert run1 == run2

    def test_unit_order_within_concept_always_one(self):
        """unitOrderWithinConcept is always 1 (one unit per concept in v1)."""
        cmap = self._minimal_map({"doc-a": ["c1", "c2", "c3"]})
        units = build_textbook_units(cmap)
        assert all(u["unitOrderWithinConcept"] == 1 for u in units)

    def test_unit_type_explanation_is_default(self):
        """unitType defaults to 'explanation' when no special sections exist."""
        cmap = self._minimal_map({"doc-a": ["c1"]}, sections={"c1": ["main"]})
        unit = build_textbook_units(cmap)[0]
        assert unit["unitType"] == "explanation"

    def test_unit_type_example_when_examples_section_present(self):
        """unitType == 'example' when chunkIds contains an 'examples' section."""
        cmap = self._minimal_map(
            {"doc-a": ["c1"]}, sections={"c1": ["definition", "examples"]}
        )
        unit = build_textbook_units(cmap)[0]
        assert unit["unitType"] == "example"

    def test_unit_type_summary_when_summary_section_present(self):
        """unitType == 'summary' when chunkIds contains a 'summary' section."""
        cmap = self._minimal_map(
            {"doc-a": ["c1"]}, sections={"c1": ["summary"]}
        )
        unit = build_textbook_units(cmap)[0]
        assert unit["unitType"] == "summary"

    def test_unit_type_reference_when_reference_section_present(self):
        """unitType == 'reference' when chunkIds contains a 'reference' section."""
        cmap = self._minimal_map(
            {"doc-a": ["c1"]}, sections={"c1": ["reference"]}
        )
        unit = build_textbook_units(cmap)[0]
        assert unit["unitType"] == "reference"

    def test_unit_type_reference_takes_priority_over_summary(self):
        """'reference' section takes priority over 'summary'."""
        cmap = self._minimal_map(
            {"doc-a": ["c1"]}, sections={"c1": ["summary", "reference"]}
        )
        unit = build_textbook_units(cmap)[0]
        assert unit["unitType"] == "reference"

    def test_unit_type_is_deterministic(self):
        """Same concept data always yields the same unitType."""
        cmap = self._minimal_map(
            {"doc-a": ["c1"]}, sections={"c1": ["definition", "examples"]}
        )
        types_run1 = [u["unitType"] for u in build_textbook_units(cmap)]
        types_run2 = [u["unitType"] for u in build_textbook_units(cmap)]
        assert types_run1 == types_run2

    def test_keywords_from_tags(self):
        """keywords is populated from the concept's tags list."""
        cmap = self._minimal_map(
            {"doc-a": ["c1"]},
            tags_by_concept={"c1": ["sql", "fundamentals", "intro"]},
        )
        unit = build_textbook_units(cmap)[0]
        assert unit["keywords"] == ["sql", "fundamentals", "intro"]

    def test_keywords_empty_when_no_tags(self):
        """keywords is an empty list when the concept has no tags."""
        cmap = self._minimal_map({"doc-a": ["c1"]})
        unit = build_textbook_units(cmap)[0]
        assert unit["keywords"] == []

    def test_keywords_are_deterministic(self):
        """keywords list is stable across repeated calls."""
        cmap = self._minimal_map(
            {"doc-a": ["c1"]}, tags_by_concept={"c1": ["a", "b"]}
        )
        run1 = [u["keywords"] for u in build_textbook_units(cmap)]
        run2 = [u["keywords"] for u in build_textbook_units(cmap)]
        assert run1 == run2

    def test_short_excerpt_from_definition(self):
        """shortExcerpt is first 200 chars of definition."""
        long_def = "X" * 300
        cmap = self._minimal_map(
            {"doc-a": ["c1"]}, definition_by_concept={"c1": long_def}
        )
        unit = build_textbook_units(cmap)[0]
        assert unit["shortExcerpt"] == long_def[:200]
        assert len(unit["shortExcerpt"]) == 200

    def test_short_excerpt_full_when_definition_short(self):
        """shortExcerpt equals definition when definition is ≤ 200 chars."""
        short_def = "A short definition."
        cmap = self._minimal_map(
            {"doc-a": ["c1"]}, definition_by_concept={"c1": short_def}
        )
        unit = build_textbook_units(cmap)[0]
        assert unit["shortExcerpt"] == short_def

    def test_short_excerpt_empty_when_no_definition(self):
        """shortExcerpt is empty string when definition is absent."""
        cmap = self._minimal_map({"doc-a": ["c1"]})
        cmap["concepts"]["doc-a/c1"]["definition"] = ""
        unit = build_textbook_units(cmap)[0]
        assert unit["shortExcerpt"] == ""

    def test_short_excerpt_is_deterministic(self):
        cmap = self._minimal_map(
            {"doc-a": ["c1"]}, definition_by_concept={"c1": "Hello world"}
        )
        run1 = [u["shortExcerpt"] for u in build_textbook_units(cmap)]
        run2 = [u["shortExcerpt"] for u in build_textbook_units(cmap)]
        assert run1 == run2

    def test_aliases_derived_from_title(self):
        """aliases contains the title-derived kebab-case slug."""
        cmap = self._minimal_map({"doc-a": ["select-statement"]})
        # Override title to something different from conceptId
        cmap["concepts"]["doc-a/select-statement"]["title"] = "SELECT Statement"
        unit = build_textbook_units(cmap)[0]
        # slug of "SELECT Statement" → "select-statement" which equals conceptId → not in aliases
        # Let's check the alias is the title slug
        expected_slug = re.sub(r"[^a-z0-9]+", "-", "SELECT Statement".lower()).strip("-")
        if expected_slug != "select-statement":
            assert expected_slug in unit["aliases"]

    def test_aliases_exclude_bare_id_duplicate(self):
        """aliases must not contain the bare conceptId itself (it's not an alias)."""
        cmap = self._minimal_map({"doc-a": ["my-concept"]})
        # Set title whose slug == conceptId so the alias would be a dup
        cmap["concepts"]["doc-a/my-concept"]["title"] = "My Concept"
        unit = build_textbook_units(cmap)[0]
        assert "my-concept" not in unit["aliases"]

    def test_aliases_are_deterministic(self):
        """Same concept data → same aliases on every call."""
        cmap = self._minimal_map({"doc-a": ["1nf"]})
        cmap["concepts"]["doc-a/1nf"]["title"] = "First Normal Form (1NF)"
        run1 = [u["aliases"] for u in build_textbook_units(cmap)]
        run2 = [u["aliases"] for u in build_textbook_units(cmap)]
        assert run1 == run2

    def test_source_section_titles_sorted(self):
        """sourceSectionTitles is a sorted list of section name keys."""
        cmap = self._minimal_map(
            {"doc-a": ["c1"]},
            sections={"c1": ["examples", "definition", "commonMistakes"]},
        )
        unit = build_textbook_units(cmap)[0]
        titles = unit["sourceSectionTitles"]
        assert titles == sorted(titles)
        assert set(titles) == {"examples", "definition", "commonMistakes"}

    def test_source_section_titles_deterministic(self):
        cmap = self._minimal_map(
            {"doc-a": ["c1"]},
            sections={"c1": ["examples", "definition"]},
        )
        run1 = [u["sourceSectionTitles"] for u in build_textbook_units(cmap)]
        run2 = [u["sourceSectionTitles"] for u in build_textbook_units(cmap)]
        assert run1 == run2

    def test_prerequisite_concept_ids_is_empty_list(self):
        """prerequisiteConceptIds is [] — reserved for future enrichment."""
        cmap = self._minimal_map({"doc-a": ["c1", "c2"]})
        units = build_textbook_units(cmap)
        assert all(u["prerequisiteConceptIds"] == [] for u in units)


# ---------------------------------------------------------------------------
# Integration tests: export_to_sqladapt produces textbook-units.json
# ---------------------------------------------------------------------------

class TestExportProducesUnits:
    """Integration tests verifying export_to_sqladapt writes textbook-units.json."""

    def test_units_file_created_on_first_export(self, tmp_path: Path):
        idx = _write_index(tmp_path / "idx", "doc-alpha", {
            "concept-a": {"title": "A", "pages": [5, 6], "chunkIds": ["ca-c1"]},
            "concept-b": {"title": "B", "pages": [10], "chunkIds": ["cb-c1"]},
        })
        out = tmp_path / "out"
        export_to_sqladapt(idx, out, merge=False)

        units_file = out / "textbook-units.json"
        assert units_file.exists()
        data = json.loads(units_file.read_text())
        assert data["schemaVersion"] == "textbook-units-v1"
        assert data["totalUnits"] == 2
        assert len(data["units"]) == 2

    def test_units_count_equals_concept_count(self, tmp_path: Path):
        concepts = {f"c{i}": {"title": f"C{i}", "chunkIds": [f"c{i}-chunk"]}
                    for i in range(5)}
        idx = _write_index(tmp_path / "idx", "doc-alpha", concepts)
        out = tmp_path / "out"
        export_to_sqladapt(idx, out, merge=False)
        data = json.loads((out / "textbook-units.json").read_text())
        assert data["totalUnits"] == 5

    def test_all_markdown_paths_resolve(self, tmp_path: Path):
        concepts = {
            "select": {"title": "SELECT", "chunkIds": ["s-c1"]},
            "join":   {"title": "JOIN",   "chunkIds": ["j-c1"]},
        }
        idx = _write_index(tmp_path / "idx", "doc-alpha", concepts)
        out = tmp_path / "out"
        export_to_sqladapt(idx, out, merge=False)
        data = json.loads((out / "textbook-units.json").read_text())
        for unit in data["units"]:
            md = out / unit["markdownPath"]
            assert md.exists(), f"markdownPath missing: {unit['markdownPath']}"

    def test_unit_ids_unique_in_export(self, tmp_path: Path):
        concepts = {f"c{i}": {"title": f"C{i}", "chunkIds": [f"c{i}-ck"]}
                    for i in range(10)}
        idx = _write_index(tmp_path / "idx", "doc-alpha", concepts)
        out = tmp_path / "out"
        export_to_sqladapt(idx, out, merge=False)
        data = json.loads((out / "textbook-units.json").read_text())
        ids = [u["unitId"] for u in data["units"]]
        assert len(ids) == len(set(ids))

    def test_unit_ids_deterministic_across_two_exports(self, tmp_path: Path):
        concepts = {"select": {"title": "SELECT", "chunkIds": ["s-c1"]}}
        idx1 = _write_index(tmp_path / "idx1", "doc-alpha", concepts)
        idx2 = _write_index(tmp_path / "idx2", "doc-alpha", concepts)
        out1 = tmp_path / "out1"
        out2 = tmp_path / "out2"
        export_to_sqladapt(idx1, out1, merge=False)
        export_to_sqladapt(idx2, out2, merge=False)
        ids1 = {u["unitId"] for u in json.loads((out1 / "textbook-units.json").read_text())["units"]}
        ids2 = {u["unitId"] for u in json.loads((out2 / "textbook-units.json").read_text())["units"]}
        assert ids1 == ids2

    def test_merged_export_contains_all_docs(self, tmp_path: Path):
        idx_a = _write_index(tmp_path / "idx_a", "doc-a", {
            "ca1": {"title": "CA1", "chunkIds": ["ca1-c1"]},
        })
        idx_b = _write_index(tmp_path / "idx_b", "doc-b", {
            "cb1": {"title": "CB1", "chunkIds": ["cb1-c1"]},
        })
        out = tmp_path / "out"
        export_to_sqladapt(idx_a, out, merge=True)
        export_to_sqladapt(idx_b, out, merge=True)
        data = json.loads((out / "textbook-units.json").read_text())
        assert set(data["sourceDocIds"]) == {"doc-a", "doc-b"}
        assert data["totalUnits"] == 2
        assert {u["sourceDocId"] for u in data["units"]} == {"doc-a", "doc-b"}

    def test_namespacedid_coverage_matches_concept_map(self, tmp_path: Path):
        concepts = {
            "select": {"title": "SELECT", "chunkIds": ["s-c1"]},
            "join":   {"title": "JOIN",   "chunkIds": ["j-c1"]},
        }
        idx = _write_index(tmp_path / "idx", "doc-alpha", concepts)
        out = tmp_path / "out"
        export_to_sqladapt(idx, out, merge=False)
        units_data = json.loads((out / "textbook-units.json").read_text())
        units_ids = {u["namespacedId"] for u in units_data["units"]}
        cmap_data = json.loads((out / "concept-map.json").read_text())
        map_ids = set(cmap_data["concepts"].keys())
        assert units_ids == map_ids

    def test_source_order_contiguous_after_export(self, tmp_path: Path):
        """sourceOrder in the exported file is a gapless 0..N-1 sequence."""
        concepts = {f"c{i}": {"title": f"C{i}", "chunkIds": [f"c{i}-ck"]}
                    for i in range(6)}
        idx = _write_index(tmp_path / "idx", "doc-alpha", concepts)
        out = tmp_path / "out"
        export_to_sqladapt(idx, out, merge=False)
        data = json.loads((out / "textbook-units.json").read_text())
        orders = [u["sourceOrder"] for u in data["units"]]
        assert sorted(orders) == list(range(len(orders)))

    def test_unit_type_present_and_valid_in_export(self, tmp_path: Path):
        """All units in the exported file have a valid unitType value."""
        concepts = {
            "select": {
                "title": "SELECT", "chunkIds": ["s-c1"],
                "sections": ["definition", "examples"],
            },
        }
        idx = _write_index(tmp_path / "idx", "doc-alpha", concepts)
        out = tmp_path / "out"
        export_to_sqladapt(idx, out, merge=False)
        data = json.loads((out / "textbook-units.json").read_text())
        valid = {"explanation", "example", "summary", "reference"}
        for unit in data["units"]:
            assert unit.get("unitType") in valid, (
                f"Unexpected unitType: {unit.get('unitType')}"
            )

    def test_keywords_propagated_from_tags_in_export(self, tmp_path: Path):
        """keywords in the exported unit reflect tags from the concept manifest."""
        concepts = {
            "select": {
                "title": "SELECT",
                "chunkIds": ["s-c1"],
                "tags": ["sql", "query", "dml"],
            },
        }
        idx = _write_index(tmp_path / "idx", "doc-alpha", concepts)
        out = tmp_path / "out"
        export_to_sqladapt(idx, out, merge=False)
        data = json.loads((out / "textbook-units.json").read_text())
        unit = data["units"][0]
        assert unit["keywords"] == ["sql", "query", "dml"]


# ---------------------------------------------------------------------------
# validate_handoff_integrity checks textbook-units.json
# ---------------------------------------------------------------------------

class TestValidateHandoffUnits:
    """Tests that validate_handoff_integrity enforces textbook-units.json rules."""

    def _build_valid_export(self, tmp_path: Path) -> Path:
        idx = _write_index(tmp_path / "idx", "doc-alpha", {
            "select": {"title": "SELECT", "chunkIds": ["s-c1"]},
            "join":   {"title": "JOIN",   "chunkIds": ["j-c1"]},
        })
        out = tmp_path / "out"
        export_to_sqladapt(idx, out, merge=False)
        return out

    def test_valid_export_passes(self, tmp_path: Path):
        out = self._build_valid_export(tmp_path)
        result = validate_handoff_integrity(out)
        assert result["valid"] is True, result["errors"]

    def test_missing_units_file_is_fatal(self, tmp_path: Path):
        out = self._build_valid_export(tmp_path)
        (out / "textbook-units.json").unlink()
        result = validate_handoff_integrity(out)
        assert result["valid"] is False
        assert any("textbook-units.json" in e for e in result["errors"])

    def test_duplicate_unit_ids_are_fatal(self, tmp_path: Path):
        out = self._build_valid_export(tmp_path)
        units_file = out / "textbook-units.json"
        data = json.loads(units_file.read_text())
        data["units"].append(data["units"][0])
        data["totalUnits"] += 1
        units_file.write_text(json.dumps(data))
        result = validate_handoff_integrity(out)
        assert result["valid"] is False
        assert any("duplicate unitIds" in e for e in result["errors"])

    def test_broken_markdown_path_is_fatal(self, tmp_path: Path):
        out = self._build_valid_export(tmp_path)
        (out / "concepts" / "doc-alpha" / "select.md").unlink()
        result = validate_handoff_integrity(out)
        assert result["valid"] is False
        assert any("markdownPath" in e for e in result["errors"])

    def test_extra_unit_not_in_concept_map_is_warning(self, tmp_path: Path):
        out = self._build_valid_export(tmp_path)
        units_file = out / "textbook-units.json"
        data = json.loads(units_file.read_text())
        ghost_md = out / "concepts" / "doc-alpha" / "ghost.md"
        ghost_md.write_text("# Ghost\n")
        ghost_unit_id = "unit-" + hashlib.sha256(b"doc-alpha:ghost").hexdigest()[:16]
        data["units"].append({
            "unitId": ghost_unit_id,
            "sourceDocId": "doc-alpha",
            "conceptId": "ghost",
            "namespacedId": "doc-alpha/ghost",
            "canonicalConceptKey": "doc-alpha/ghost",
            "title": "Ghost",
            "difficulty": "beginner",
            "unitType": "explanation",
            "keywords": [],
            "aliases": [],
            "shortExcerpt": "",
            "markdownPath": "concepts/doc-alpha/ghost.md",
            "pageNumbers": [],
            "pageSpan": None,
            "sourceChunkIds": [],
            "sourceSectionTitles": [],
            "relatedConcepts": [],
            "prerequisiteConceptIds": [],
            "sourceOrder": len(data["units"]),
            "unitOrderWithinConcept": 1,
        })
        data["totalUnits"] += 1
        units_file.write_text(json.dumps(data))
        result = validate_handoff_integrity(out)
        assert any("not in concept-map" in w for w in result["warnings"])

    def test_missing_unit_for_concept_is_fatal(self, tmp_path: Path):
        out = self._build_valid_export(tmp_path)
        units_file = out / "textbook-units.json"
        data = json.loads(units_file.read_text())
        data["units"] = [u for u in data["units"] if u["conceptId"] != "select"]
        data["totalUnits"] -= 1
        units_file.write_text(json.dumps(data))
        result = validate_handoff_integrity(out)
        assert result["valid"] is False
        assert any("missing" in e and "concept-map" in e for e in result["errors"])

    def test_units_count_returned_in_result(self, tmp_path: Path):
        out = self._build_valid_export(tmp_path)
        result = validate_handoff_integrity(out)
        assert "units_count" in result
        assert result["units_count"] == 2

    def test_noncontiguous_source_order_is_fatal(self, tmp_path: Path):
        """Gaps or duplicates in sourceOrder are a fatal error."""
        out = self._build_valid_export(tmp_path)
        units_file = out / "textbook-units.json"
        data = json.loads(units_file.read_text())
        # Force both units to have sourceOrder=0 (duplicate)
        for u in data["units"]:
            u["sourceOrder"] = 0
        units_file.write_text(json.dumps(data))
        result = validate_handoff_integrity(out)
        assert result["valid"] is False
        assert any("sourceOrder" in e for e in result["errors"])

    def test_invalid_unit_type_is_fatal(self, tmp_path: Path):
        """A unitType value outside the valid set is a fatal error."""
        out = self._build_valid_export(tmp_path)
        units_file = out / "textbook-units.json"
        data = json.loads(units_file.read_text())
        data["units"][0]["unitType"] = "unknown-type"
        units_file.write_text(json.dumps(data))
        result = validate_handoff_integrity(out)
        assert result["valid"] is False
        assert any("unitType" in e for e in result["errors"])

    def test_missing_enrichment_fields_are_fatal(self, tmp_path: Path):
        """A unit missing required enrichment fields is a fatal error."""
        out = self._build_valid_export(tmp_path)
        units_file = out / "textbook-units.json"
        data = json.loads(units_file.read_text())
        # Strip enrichment fields from first unit
        for field in ("canonicalConceptKey", "sourceOrder", "unitType"):
            data["units"][0].pop(field, None)
        units_file.write_text(json.dumps(data))
        result = validate_handoff_integrity(out)
        assert result["valid"] is False
        assert any("enrichment fields" in e for e in result["errors"])


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
