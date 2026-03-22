"""
Tests for textbook-units.json export contract.

Covers:
- exactly one unit record per exported instructional unit
- all markdownPath values resolve to real files
- unitIds are unique and deterministic across repeated calls
- sourceDocId/conceptId coverage matches concept-map.json
- validate_handoff_integrity checks textbook-units.json
"""

from __future__ import annotations

import hashlib
import json
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
                    "main": {
                        "chunkIds": meta.get("chunkIds", [f"{cid}-chunk-1"]),
                        "pageNumbers": meta.get("pages", [1]),
                    }
                },
                "relatedConcepts": meta.get("related", []),
                "tags": [],
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

    def _minimal_map(self, doc_ids_concepts: dict[str, list[str]]) -> dict:
        """Build a minimal merged concept-map dict."""
        concepts = {}
        for doc_id, concept_ids in doc_ids_concepts.items():
            for cid in concept_ids:
                namespaced = f"{doc_id}/{cid}"
                concepts[namespaced] = {
                    "title": f"Title {cid}",
                    "definition": "def",
                    "difficulty": "beginner",
                    "pageNumbers": [10, 11],
                    "chunkIds": {"main": [f"{cid}-chunk-1", f"{cid}-chunk-2"]},
                    "relatedConcepts": [],
                    "sourceDocId": doc_id,
                }
        return {
            "version": "1.0.0",
            "generatedAt": "2026-03-21T00:00:00Z",
            "sourceDocIds": list(doc_ids_concepts.keys()),
            "concepts": concepts,
        }

    def test_one_unit_per_concept(self):
        """build_textbook_units returns exactly one unit per concept entry."""
        cmap = self._minimal_map({"doc-a": ["select", "join", "where"]})
        units = build_textbook_units(cmap)
        assert len(units) == 3

    def test_unit_has_required_fields(self):
        """Every unit record contains all required fields."""
        cmap = self._minimal_map({"doc-a": ["select"]})
        unit = build_textbook_units(cmap)[0]

        required = {
            "unitId", "sourceDocId", "conceptId", "namespacedId",
            "title", "difficulty", "markdownPath",
            "pageNumbers", "pageSpan", "sourceChunkIds", "relatedConcepts",
        }
        assert required.issubset(unit.keys()), (
            f"Missing fields: {required - unit.keys()}"
        )

    def test_markdown_path_shape(self):
        """markdownPath follows concepts/{sourceDocId}/{conceptId}.md."""
        cmap = self._minimal_map({"my-doc": ["select-basic"]})
        unit = build_textbook_units(cmap)[0]
        assert unit["markdownPath"] == "concepts/my-doc/select-basic.md"

    def test_unit_ids_are_unique(self):
        """unitIds are unique across all units in a merged map."""
        cmap = self._minimal_map({"doc-a": ["c1", "c2", "c3"], "doc-b": ["c1", "c4"]})
        units = build_textbook_units(cmap)
        ids = [u["unitId"] for u in units]
        assert len(ids) == len(set(ids)), "Duplicate unitIds detected"

    def test_unit_ids_are_deterministic(self):
        """Calling build_textbook_units twice with the same map yields identical unitIds."""
        cmap = self._minimal_map({"doc-a": ["select", "join"]})
        first = {u["unitId"] for u in build_textbook_units(cmap)}
        second = {u["unitId"] for u in build_textbook_units(cmap)}
        assert first == second

    def test_unit_id_matches_expected_hash(self):
        """unitId = 'unit-' + sha256('{docId}:{conceptId}')[:16]."""
        doc_id, cid = "doc-a", "select"
        expected = "unit-" + hashlib.sha256(f"{doc_id}:{cid}".encode()).hexdigest()[:16]
        cmap = self._minimal_map({doc_id: [cid]})
        unit = build_textbook_units(cmap)[0]
        assert unit["unitId"] == expected

    def test_same_concept_id_different_docs_get_different_unit_ids(self):
        """Two docs sharing a bare conceptId must have different unitIds."""
        cmap = self._minimal_map({"doc-a": ["select"], "doc-b": ["select"]})
        units = build_textbook_units(cmap)
        ids = [u["unitId"] for u in units]
        assert len(set(ids)) == 2, "Concepts with same name in different docs share a unitId"

    def test_page_span_populated(self):
        """pageSpan.start and pageSpan.end reflect min/max of pageNumbers."""
        cmap = self._minimal_map({"doc-a": ["select"]})
        unit = build_textbook_units(cmap)[0]
        assert unit["pageSpan"] == {"start": 10, "end": 11}

    def test_page_span_none_when_no_pages(self):
        """pageSpan is None when pageNumbers is empty."""
        cmap = self._minimal_map({"doc-a": ["select"]})
        # Remove page numbers from the concept
        cmap["concepts"]["doc-a/select"]["pageNumbers"] = []
        unit = build_textbook_units(cmap)[0]
        assert unit["pageSpan"] is None

    def test_source_chunk_ids_flat_and_deduplicated(self):
        """sourceChunkIds is a flat, deduplicated list across sections."""
        cmap = self._minimal_map({"doc-a": ["select"]})
        # Give the concept two sections with one shared chunk
        cmap["concepts"]["doc-a/select"]["chunkIds"] = {
            "section1": ["chunk-001", "chunk-002"],
            "section2": ["chunk-002", "chunk-003"],
        }
        unit = build_textbook_units(cmap)[0]
        assert unit["sourceChunkIds"] == ["chunk-001", "chunk-002", "chunk-003"]

    def test_output_sorted_by_doc_then_concept(self):
        """Units are sorted by (sourceDocId, conceptId)."""
        cmap = self._minimal_map({"zzz": ["beta", "alpha"], "aaa": ["gamma"]})
        units = build_textbook_units(cmap)
        keys = [(u["sourceDocId"], u["conceptId"]) for u in units]
        assert keys == sorted(keys)

    def test_named_concept_id_and_namespaced_id_consistent(self):
        """conceptId is the bare part; namespacedId = sourceDocId/conceptId."""
        cmap = self._minimal_map({"my-doc": ["my-concept"]})
        unit = build_textbook_units(cmap)[0]
        assert unit["conceptId"] == "my-concept"
        assert unit["namespacedId"] == "my-doc/my-concept"
        assert unit["sourceDocId"] == "my-doc"

    def test_coverage_matches_concept_map(self):
        """The set of namespacedIds in units == the set in concept-map concepts."""
        doc_ids_concepts = {"doc-a": ["c1", "c2"], "doc-b": ["c3"]}
        cmap = self._minimal_map(doc_ids_concepts)
        units = build_textbook_units(cmap)

        units_ids = {u["namespacedId"] for u in units}
        map_ids = set(cmap["concepts"].keys())
        assert units_ids == map_ids


# ---------------------------------------------------------------------------
# Integration tests: export_to_sqladapt produces textbook-units.json
# ---------------------------------------------------------------------------

class TestExportProducesUnits:
    """Integration tests verifying export_to_sqladapt writes textbook-units.json."""

    def test_units_file_created_on_first_export(self, tmp_path: Path):
        """textbook-units.json is created during a fresh export."""
        idx = _write_index(tmp_path / "idx", "doc-alpha", {
            "concept-a": {"title": "A", "pages": [5, 6], "chunkIds": ["ca-c1"]},
            "concept-b": {"title": "B", "pages": [10], "chunkIds": ["cb-c1"]},
        })
        out = tmp_path / "out"

        export_to_sqladapt(idx, out, merge=False)

        units_file = out / "textbook-units.json"
        assert units_file.exists(), "textbook-units.json was not created"

        data = json.loads(units_file.read_text())
        assert data["schemaVersion"] == "textbook-units-v1"
        assert data["totalUnits"] == 2
        assert len(data["units"]) == 2

    def test_units_count_equals_concept_count(self, tmp_path: Path):
        """Total units in catalog == number of concepts exported."""
        concepts = {f"c{i}": {"title": f"C{i}", "chunkIds": [f"c{i}-chunk"]}
                    for i in range(5)}
        idx = _write_index(tmp_path / "idx", "doc-alpha", concepts)
        out = tmp_path / "out"

        export_to_sqladapt(idx, out, merge=False)

        data = json.loads((out / "textbook-units.json").read_text())
        assert data["totalUnits"] == 5

    def test_all_markdown_paths_resolve(self, tmp_path: Path):
        """Every markdownPath in textbook-units.json points to an existing file."""
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
        """All unitIds are unique after export."""
        concepts = {f"c{i}": {"title": f"C{i}", "chunkIds": [f"c{i}-ck"]}
                    for i in range(10)}
        idx = _write_index(tmp_path / "idx", "doc-alpha", concepts)
        out = tmp_path / "out"

        export_to_sqladapt(idx, out, merge=False)

        data = json.loads((out / "textbook-units.json").read_text())
        ids = [u["unitId"] for u in data["units"]]
        assert len(ids) == len(set(ids))

    def test_unit_ids_deterministic_across_two_exports(self, tmp_path: Path):
        """Re-exporting the same content produces identical unitIds."""
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
        """After merging two exports, textbook-units.json covers both sourceDocIds."""
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

        src_doc_ids = {u["sourceDocId"] for u in data["units"]}
        assert src_doc_ids == {"doc-a", "doc-b"}

    def test_namespacedid_coverage_matches_concept_map(self, tmp_path: Path):
        """namespacedIds in units exactly matches concept-map.json concept keys."""
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


# ---------------------------------------------------------------------------
# validate_handoff_integrity checks textbook-units.json
# ---------------------------------------------------------------------------

class TestValidateHandoffUnits:
    """Tests that validate_handoff_integrity enforces textbook-units.json rules."""

    def _build_valid_export(self, tmp_path: Path) -> Path:
        """Create a valid export and return its output directory."""
        idx = _write_index(tmp_path / "idx", "doc-alpha", {
            "select": {"title": "SELECT", "chunkIds": ["s-c1"]},
            "join":   {"title": "JOIN",   "chunkIds": ["j-c1"]},
        })
        out = tmp_path / "out"
        export_to_sqladapt(idx, out, merge=False)
        return out

    def test_valid_export_passes(self, tmp_path: Path):
        """A freshly produced export passes validate_handoff_integrity."""
        out = self._build_valid_export(tmp_path)
        result = validate_handoff_integrity(out)
        assert result["valid"] is True, result["errors"]

    def test_missing_units_file_is_fatal(self, tmp_path: Path):
        """Missing textbook-units.json is a fatal error."""
        out = self._build_valid_export(tmp_path)
        (out / "textbook-units.json").unlink()

        result = validate_handoff_integrity(out)
        assert result["valid"] is False
        assert any("textbook-units.json" in e for e in result["errors"])

    def test_duplicate_unit_ids_are_fatal(self, tmp_path: Path):
        """Duplicate unitIds in textbook-units.json are a fatal error."""
        out = self._build_valid_export(tmp_path)
        units_file = out / "textbook-units.json"
        data = json.loads(units_file.read_text())

        # Duplicate the first unit
        data["units"].append(data["units"][0])
        data["totalUnits"] += 1
        units_file.write_text(json.dumps(data))

        result = validate_handoff_integrity(out)
        assert result["valid"] is False
        assert any("duplicate unitIds" in e for e in result["errors"])

    def test_broken_markdown_path_is_fatal(self, tmp_path: Path):
        """A markdownPath that points to a missing file is a fatal error."""
        out = self._build_valid_export(tmp_path)

        # Delete one markdown file
        (out / "concepts" / "doc-alpha" / "select.md").unlink()

        result = validate_handoff_integrity(out)
        assert result["valid"] is False
        assert any("markdownPath" in e for e in result["errors"])

    def test_extra_unit_not_in_concept_map_is_warning(self, tmp_path: Path):
        """An extra unit in textbook-units.json not in concept-map is a warning."""
        out = self._build_valid_export(tmp_path)
        units_file = out / "textbook-units.json"
        data = json.loads(units_file.read_text())

        # Inject a ghost unit that has no backing markdown or concept-map entry
        ghost_md = out / "concepts" / "doc-alpha" / "ghost.md"
        ghost_md.write_text("# Ghost\n")
        ghost_unit_id = "unit-" + hashlib.sha256(b"doc-alpha:ghost").hexdigest()[:16]
        data["units"].append({
            "unitId": ghost_unit_id,
            "sourceDocId": "doc-alpha",
            "conceptId": "ghost",
            "namespacedId": "doc-alpha/ghost",
            "title": "Ghost",
            "difficulty": "beginner",
            "markdownPath": "concepts/doc-alpha/ghost.md",
            "pageNumbers": [],
            "pageSpan": None,
            "sourceChunkIds": [],
            "relatedConcepts": [],
        })
        data["totalUnits"] += 1
        units_file.write_text(json.dumps(data))

        result = validate_handoff_integrity(out)
        # Extra entries are a warning, not a fatal error (missing entries are errors)
        assert any("not in concept-map" in w for w in result["warnings"])

    def test_missing_unit_for_concept_is_fatal(self, tmp_path: Path):
        """A concept in concept-map.json with no matching unit is a fatal error."""
        out = self._build_valid_export(tmp_path)
        units_file = out / "textbook-units.json"
        data = json.loads(units_file.read_text())

        # Remove one unit
        data["units"] = [u for u in data["units"] if u["conceptId"] != "select"]
        data["totalUnits"] -= 1
        units_file.write_text(json.dumps(data))

        result = validate_handoff_integrity(out)
        assert result["valid"] is False
        assert any("missing" in e and "concept-map" in e for e in result["errors"])

    def test_units_count_returned_in_result(self, tmp_path: Path):
        """validate_handoff_integrity result includes units_count."""
        out = self._build_valid_export(tmp_path)
        result = validate_handoff_integrity(out)
        assert "units_count" in result
        assert result["units_count"] == 2


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
