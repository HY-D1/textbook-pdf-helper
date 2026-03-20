"""
Regression tests for curated-content reachability through the ID resolver.

Verifies that:
1. Every curated key in the three data files is either canonical or resolvable.
2. No curated entry becomes unreachable due to ID drift.
3. Core concepts resolve to non-default content when curated content exists.
4. Unit metadata records requested_concept_id, resolved_concept_id, and
   content_source_resolution correctly.

All tests are offline and deterministic — no LLM calls, no PDF processing.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from algl_pdf_helper.concept_id_resolver import (
    ConceptIdResolver,
    get_default_resolver,
)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_SRC_DIR = Path(__file__).resolve().parent.parent / "src"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _make_resolver() -> ConceptIdResolver:
    return ConceptIdResolver.from_data_dir(
        registry_path=_DATA_DIR / "concept_registry.yaml",
        aliases_path=_DATA_DIR / "concept_id_aliases.json",
    )


# ---------------------------------------------------------------------------
# TestAllCuratedKeysResolvable
# ---------------------------------------------------------------------------


class TestAllCuratedKeysResolvable:
    """Every curated key must be canonical or resolvable — no orphaned entries."""

    @pytest.fixture(scope="class")
    def resolver(self):
        return _make_resolver()

    def _assert_all_resolvable(self, resolver, path: Path, label: str):
        data = _load_json(path)
        unreachable = []
        for key in data:
            result = resolver.resolve(key)
            if not result.resolved:
                unreachable.append(key)
        assert unreachable == [], (
            f"{label}: {len(unreachable)} unreachable key(s): {unreachable}"
        )

    def test_concept_curated_units_all_resolvable(self, resolver):
        self._assert_all_resolvable(
            resolver,
            _DATA_DIR / "concept_curated_units.json",
            "concept_curated_units.json",
        )

    def test_concept_curated_l3_all_resolvable(self, resolver):
        self._assert_all_resolvable(
            resolver,
            _DATA_DIR / "concept_curated_l3.json",
            "concept_curated_l3.json",
        )

    def test_concept_examples_all_resolvable(self, resolver):
        self._assert_all_resolvable(
            resolver,
            _DATA_DIR / "concept_examples.json",
            "concept_examples.json",
        )


# ---------------------------------------------------------------------------
# TestNoDrift — curated keys that were previously canonical still resolve
# ---------------------------------------------------------------------------


class TestNoDrift:
    """Canonical keys that already worked must continue to work exactly."""

    @pytest.fixture(scope="class")
    def resolver(self):
        return _make_resolver()

    @pytest.mark.parametrize("concept_id", [
        # concept_curated_units canonical keys
        "normalization", "outer-join", "self-join", "join",
        "comparison-operators", "alias", "distinct",
        "select-basic", "where-clause", "order-by",
        "inner-join", "pattern-matching", "null-handling",
        # concept_curated_l3 canonical keys
        "correlated-subquery", "create-table", "isolation-levels",
        "foreign-key", "primary-key", "alter-table",
        "drop-table", "constraints", "group-by", "aggregate-functions",
    ])
    def test_canonical_key_still_exact(self, resolver, concept_id):
        result = resolver.resolve(concept_id)
        assert result.resolution == "exact", (
            f"{concept_id!r} should be EXACT but got {result.resolution!r}"
        )
        assert result.canonical_id == concept_id


# ---------------------------------------------------------------------------
# TestAliasConceptsReachCuratedContent
# ---------------------------------------------------------------------------


class TestAliasConceptsReachCuratedContent:
    """
    Verify that alias IDs (non-canonical forms) actually retrieve curated
    content that would otherwise be missed.

    Simulates the lookup performed by _load_curated_unit_pack and
    _load_curated_l3_content without invoking the full UnitGenerator.
    """

    @pytest.fixture(scope="class")
    def resolver(self):
        return _make_resolver()

    @pytest.fixture(scope="class")
    def curated_units(self):
        return _load_json(_DATA_DIR / "concept_curated_units.json")

    @pytest.fixture(scope="class")
    def curated_l3(self):
        return _load_json(_DATA_DIR / "concept_curated_l3.json")

    @pytest.fixture(scope="class")
    def curated_examples(self):
        return _load_json(_DATA_DIR / "concept_examples.json")

    def _lookup(self, data: dict, concept_id: str, resolver: ConceptIdResolver):
        """Simulate the resolver-aware lookup used by the unit generator."""
        lookup_id, _ = resolver.resolve_for_lookup(concept_id)
        return data.get(concept_id) or data.get(lookup_id)

    # concept_curated_units aliases
    @pytest.mark.parametrize("alias,curated_key", [
        ("stored-procedures", "stored-procedures"),
        ("transactions", "transactions"),
        ("exists-operator", "exists-operator"),
        ("subquery-in-select", "subquery-in-select"),
        ("subquery-in-where", "subquery-in-where"),
    ])
    def test_alias_reaches_unit_pack(self, resolver, curated_units, alias, curated_key):
        content = self._lookup(curated_units, alias, resolver)
        assert content is not None, (
            f"Alias {alias!r} should reach curated unit pack (key={curated_key!r})"
        )

    # concept_curated_l3 aliases
    @pytest.mark.parametrize("alias", [
        "having-clause", "transactions", "views", "stored-procedures",
        "triggers", "joins-intro", "subqueries-intro",
        "insert-statement", "update-statement", "delete-statement",
        "union", "exists-operator", "functions", "indexes",
        "coalesce-nullif",
    ])
    def test_alias_reaches_l3_content(self, resolver, curated_l3, alias):
        content = self._lookup(curated_l3, alias, resolver)
        assert content is not None, (
            f"Alias {alias!r} should reach curated L3 content"
        )

    # concept_examples aliases
    @pytest.mark.parametrize("alias", [
        "subqueries-intro", "transactions", "views", "indexes",
        "triggers", "stored-procedures", "functions", "coalesce-nullif",
        "cte-common-table-expressions", "recursive-cte",
    ])
    def test_alias_reaches_examples(self, resolver, curated_examples, alias):
        content = self._lookup(curated_examples, alias, resolver)
        assert content is not None, (
            f"Alias {alias!r} should reach curated examples"
        )


# ---------------------------------------------------------------------------
# TestCoreConceptsReachNonDefaultContent
# ---------------------------------------------------------------------------


class TestCoreConceptsReachNonDefaultContent:
    """
    For a representative set of core concepts, verify that curated content
    is available when looked up via the resolver.
    """

    REPRESENTATIVE = [
        "select-basic",
        "where-clause",
        "joins-intro",      # alias → join
        "group-by",
        "order-by",
        "cte-common-table-expressions",  # alias → cte
        "transactions",     # alias → transaction
        "stored-procedures",  # alias → stored-procedure
        "having-clause",    # alias → having
    ]

    @pytest.fixture(scope="class")
    def resolver(self):
        return _make_resolver()

    @pytest.fixture(scope="class")
    def curated_l3(self):
        return _load_json(_DATA_DIR / "concept_curated_l3.json")

    @pytest.fixture(scope="class")
    def curated_units(self):
        return _load_json(_DATA_DIR / "concept_curated_units.json")

    def _lookup(self, data: dict, concept_id: str, resolver: ConceptIdResolver):
        lookup_id, _ = resolver.resolve_for_lookup(concept_id)
        return data.get(concept_id) or data.get(lookup_id)

    @pytest.mark.parametrize("concept_id", REPRESENTATIVE)
    def test_concept_has_any_curated_content(self, resolver, curated_l3, curated_units, concept_id):
        has_l3 = self._lookup(curated_l3, concept_id, resolver) is not None
        has_units = self._lookup(curated_units, concept_id, resolver) is not None
        assert has_l3 or has_units, (
            f"{concept_id!r} has no curated L3 or unit pack content — "
            "will fall back to defaults for all learners"
        )


# ---------------------------------------------------------------------------
# TestResolutionMetadata
# ---------------------------------------------------------------------------


class TestResolutionMetadata:
    """
    Verify that ResolutionResult.to_metadata() emits the three fields that
    unit _metadata dicts are expected to include.
    """

    @pytest.fixture(scope="class")
    def resolver(self):
        return _make_resolver()

    def _meta(self, concept_id: str, resolver: ConceptIdResolver) -> dict:
        _, result = resolver.resolve_for_lookup(concept_id)
        return result.to_metadata()

    def test_exact_match_metadata(self, resolver):
        meta = self._meta("select-basic", resolver)
        assert meta["requested_concept_id"] == "select-basic"
        assert meta["resolved_concept_id"] == "select-basic"
        assert meta["content_source_resolution"] == "exact"

    def test_alias_match_metadata(self, resolver):
        meta = self._meta("stored-procedures", resolver)
        assert meta["requested_concept_id"] == "stored-procedures"
        assert meta["resolved_concept_id"] == "stored-procedure"
        assert meta["content_source_resolution"] == "alias"

    def test_not_found_metadata_falls_back(self, resolver):
        meta = self._meta("ghost-concept", resolver)
        assert meta["requested_concept_id"] == "ghost-concept"
        assert meta["resolved_concept_id"] == "ghost-concept"  # no canonical → original
        assert meta["content_source_resolution"] == "not_found"

    @pytest.mark.parametrize("alias,canonical", [
        ("cte-common-table-expressions", "cte"),
        ("recursive-cte", "cte"),
        ("erd-basics", "database-design"),
        ("having-clause", "having"),
        ("transactions", "transaction"),
    ])
    def test_all_alias_metadata_pairs(self, resolver, alias, canonical):
        meta = self._meta(alias, resolver)
        assert meta["requested_concept_id"] == alias
        assert meta["resolved_concept_id"] == canonical
        assert meta["content_source_resolution"] == "alias"


# ---------------------------------------------------------------------------
# TestAuditScriptZeroUnreachable
# ---------------------------------------------------------------------------


class TestAuditScriptZeroUnreachable:
    """
    Integrates the audit logic directly to confirm zero unreachable curated
    keys — the acceptance criterion.
    """

    def _count_unreachable(self, resolver: ConceptIdResolver, path: Path) -> list[str]:
        data = _load_json(path)
        return [k for k in data if not resolver.resolve(k).resolved]

    def test_zero_unreachable_in_curated_units(self):
        resolver = _make_resolver()
        bad = self._count_unreachable(resolver, _DATA_DIR / "concept_curated_units.json")
        assert bad == [], f"Unreachable keys in concept_curated_units.json: {bad}"

    def test_zero_unreachable_in_curated_l3(self):
        resolver = _make_resolver()
        bad = self._count_unreachable(resolver, _DATA_DIR / "concept_curated_l3.json")
        assert bad == [], f"Unreachable keys in concept_curated_l3.json: {bad}"

    def test_zero_unreachable_in_examples(self):
        resolver = _make_resolver()
        bad = self._count_unreachable(resolver, _DATA_DIR / "concept_examples.json")
        assert bad == [], f"Unreachable keys in concept_examples.json: {bad}"
