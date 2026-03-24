"""
Regression tests for the canonical concept-ID resolver
(concept_id_resolver.py + data/concept_id_aliases.json).

All tests are offline and deterministic — they operate only on the data
files checked into this repository.

Test groups
-----------
TestResolutionResult       — dataclass behaviour
TestExactMatch             — registry IDs resolve as-is
TestAliasResolution        — alias-mapped IDs resolve to canonical
TestNormalisedResolution   — underscore/uppercase variants normalise
TestNotFound               — IDs with no mapping report NOT_FOUND
TestConcreteAliases        — named alias pairs from the spec
TestRegistryContents       — registry has the expected 48 concepts
TestDefaultResolver        — singleton factory convenience
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from algl_pdf_helper.concept_id_resolver import (
    ALIAS,
    EXACT,
    NORMALIZED,
    NOT_FOUND,
    ConceptIdResolver,
    ResolutionResult,
    get_default_resolver,
)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_REGISTRY_PATH = _DATA_DIR / "concept_registry.yaml"
_ALIASES_PATH = _DATA_DIR / "concept_id_aliases.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_resolver(**overrides) -> ConceptIdResolver:
    """Build a resolver from the real data files."""
    return ConceptIdResolver.from_data_dir(
        registry_path=_REGISTRY_PATH,
        aliases_path=_ALIASES_PATH,
        **overrides,
    )


# ---------------------------------------------------------------------------
# TestResolutionResult
# ---------------------------------------------------------------------------


class TestResolutionResult:
    def test_resolved_true_when_canonical_id_set(self):
        r = ResolutionResult(requested_id="foo", canonical_id="bar", resolution=ALIAS)
        assert r.resolved is True

    def test_resolved_false_when_canonical_id_none(self):
        r = ResolutionResult(requested_id="foo", canonical_id=None, resolution=NOT_FOUND)
        assert r.resolved is False

    def test_to_metadata_fields(self):
        r = ResolutionResult(requested_id="stored-procedures", canonical_id="stored-procedure", resolution=ALIAS)
        meta = r.to_metadata()
        assert meta["requested_concept_id"] == "stored-procedures"
        assert meta["resolved_concept_id"] == "stored-procedure"
        assert meta["content_source_resolution"] == ALIAS

    def test_to_metadata_not_found_uses_requested(self):
        r = ResolutionResult(requested_id="ghost-concept", canonical_id=None, resolution=NOT_FOUND)
        meta = r.to_metadata()
        # Falls back to requested ID when no canonical found
        assert meta["resolved_concept_id"] == "ghost-concept"


# ---------------------------------------------------------------------------
# TestExactMatch
# ---------------------------------------------------------------------------


class TestExactMatch:
    @pytest.fixture(scope="class")
    def resolver(self):
        return _make_resolver()

    def test_select_basic_exact(self, resolver):
        r = resolver.resolve("select-basic")
        assert r.resolution == EXACT
        assert r.canonical_id == "select-basic"
        assert r.resolved is True

    def test_where_clause_exact(self, resolver):
        r = resolver.resolve("where-clause")
        assert r.resolution == EXACT

    def test_having_exact(self, resolver):
        r = resolver.resolve("having")
        assert r.resolution == EXACT
        assert r.canonical_id == "having"

    def test_transaction_exact(self, resolver):
        r = resolver.resolve("transaction")
        assert r.resolution == EXACT

    def test_stored_procedure_exact(self, resolver):
        r = resolver.resolve("stored-procedure")
        assert r.resolution == EXACT

    def test_cte_exact(self, resolver):
        # cte was added to registry to fix curated coverage
        r = resolver.resolve("cte")
        assert r.resolution == EXACT

    def test_window_functions_exact(self, resolver):
        r = resolver.resolve("window-functions")
        assert r.resolution == EXACT

    def test_case_expressions_exact(self, resolver):
        r = resolver.resolve("case-expressions")
        assert r.resolution == EXACT

    def test_database_design_exact(self, resolver):
        r = resolver.resolve("database-design")
        assert r.resolution == EXACT


# ---------------------------------------------------------------------------
# TestAliasResolution
# ---------------------------------------------------------------------------


class TestAliasResolution:
    @pytest.fixture(scope="class")
    def resolver(self):
        return _make_resolver()

    @pytest.mark.parametrize("alias,canonical", [
        ("stored-procedures", "stored-procedure"),
        ("transactions", "transaction"),
        ("having-clause", "having"),
        ("insert-statement", "insert"),
        ("update-statement", "update"),
        ("delete-statement", "delete"),
        ("views", "view"),
        ("indexes", "index"),
        ("triggers", "trigger"),
        ("functions", "function"),
        ("subqueries-intro", "subquery"),
        ("joins-intro", "join"),
        ("union", "set-operations"),
        ("exists-operator", "correlated-subquery"),
        ("exists-subqueries", "correlated-subquery"),
        ("subquery-in-select", "subquery"),
        ("subquery-in-where", "subquery"),
        ("coalesce-nullif", "null-handling"),
        ("cte-common-table-expressions", "cte"),
        ("recursive-cte", "cte"),
        ("erd-basics", "database-design"),
    ])
    def test_alias_resolves_to_canonical(self, resolver, alias, canonical):
        r = resolver.resolve(alias)
        assert r.resolution == ALIAS, f"{alias!r} → expected ALIAS, got {r.resolution!r}"
        assert r.canonical_id == canonical, f"{alias!r} → expected {canonical!r}, got {r.canonical_id!r}"

    def test_alias_result_is_resolved(self, resolver):
        r = resolver.resolve("stored-procedures")
        assert r.resolved is True

    def test_resolve_for_lookup_returns_canonical(self, resolver):
        lookup_id, result = resolver.resolve_for_lookup("stored-procedures")
        assert lookup_id == "stored-procedure"
        assert result.resolution == ALIAS


# ---------------------------------------------------------------------------
# TestNormalisedResolution
# ---------------------------------------------------------------------------


class TestNormalisedResolution:
    @pytest.fixture(scope="class")
    def resolver(self):
        return _make_resolver()

    def test_underscore_to_hyphen(self, resolver):
        # select_basic → select-basic
        r = resolver.resolve("select_basic")
        assert r.resolution == NORMALIZED
        assert r.canonical_id == "select-basic"

    def test_uppercase_normalised(self, resolver):
        r = resolver.resolve("WHERE-CLAUSE")
        assert r.resolution == NORMALIZED
        assert r.canonical_id == "where-clause"

    def test_mixed_case_underscore(self, resolver):
        r = resolver.resolve("Order_By")
        assert r.resolution == NORMALIZED
        assert r.canonical_id == "order-by"


# ---------------------------------------------------------------------------
# TestNotFound
# ---------------------------------------------------------------------------


class TestNotFound:
    @pytest.fixture(scope="class")
    def resolver(self):
        return _make_resolver()

    def test_completely_unknown_id(self, resolver):
        r = resolver.resolve("completely-unknown-concept-xyz")
        assert r.resolution == NOT_FOUND
        assert r.canonical_id is None
        assert r.resolved is False

    def test_empty_string(self, resolver):
        r = resolver.resolve("")
        assert r.resolution == NOT_FOUND

    def test_resolve_for_lookup_falls_back_to_original(self, resolver):
        lookup_id, result = resolver.resolve_for_lookup("ghost-concept")
        assert lookup_id == "ghost-concept"  # Falls back to the original
        assert result.resolved is False


# ---------------------------------------------------------------------------
# TestConcreteAliases — spec-named pairs from the task
# ---------------------------------------------------------------------------


class TestConcreteAliases:
    """Verify every alias pair mentioned in the task specification."""

    @pytest.fixture(scope="class")
    def resolver(self):
        return _make_resolver()

    def test_cte_common_table_expressions_to_cte(self, resolver):
        r = resolver.resolve("cte-common-table-expressions")
        assert r.canonical_id == "cte"

    def test_stored_procedures_to_stored_procedure(self, resolver):
        r = resolver.resolve("stored-procedures")
        assert r.canonical_id == "stored-procedure"

    def test_transactions_to_transaction(self, resolver):
        r = resolver.resolve("transactions")
        assert r.canonical_id == "transaction"

    def test_having_clause_to_having(self, resolver):
        r = resolver.resolve("having-clause")
        assert r.canonical_id == "having"

    def test_insert_statement_to_insert(self, resolver):
        r = resolver.resolve("insert-statement")
        assert r.canonical_id == "insert"

    def test_delete_statement_to_delete(self, resolver):
        r = resolver.resolve("delete-statement")
        assert r.canonical_id == "delete"

    def test_subqueries_intro_to_subquery(self, resolver):
        r = resolver.resolve("subqueries-intro")
        assert r.canonical_id == "subquery"


# ---------------------------------------------------------------------------
# TestRegistryContents
# ---------------------------------------------------------------------------


class TestRegistryContents:
    """Verify the registry now contains all expected concepts."""

    @pytest.fixture(scope="class")
    def registry_ids(self):
        return _make_resolver().registry_ids

    @pytest.mark.parametrize("concept_id", [
        # Original registry
        "select-basic", "where-clause", "order-by", "alias", "distinct",
        "comparison-operators", "null-handling", "pattern-matching",
        "join", "inner-join", "outer-join", "self-join",
        "aggregate-functions", "group-by", "having",
        "subquery", "correlated-subquery", "set-operations",
        "insert", "update", "delete", "merge",
        "create-table", "alter-table", "drop-table", "truncate-table",
        "constraints", "primary-key", "foreign-key",
        "index", "view",
        "transaction", "isolation-levels",
        "stored-procedure", "function", "trigger", "cursor",
        "normalization", "grant-revoke",
        # Newly added
        "cte", "window-functions", "case-expressions",
        "limit-offset", "cross-join", "data-types",
        "string-functions", "date-functions", "database-design",
    ])
    def test_concept_in_registry(self, registry_ids, concept_id):
        assert concept_id in registry_ids, f"{concept_id!r} missing from registry"

    def test_registry_size_at_least_48(self, registry_ids):
        # Started with 39, added 9 new concepts → at least 48
        assert len(registry_ids) >= 48


# ---------------------------------------------------------------------------
# TestDefaultResolver
# ---------------------------------------------------------------------------


class TestDefaultResolver:
    def test_returns_resolver_instance(self):
        resolver = get_default_resolver()
        assert isinstance(resolver, ConceptIdResolver)

    def test_singleton_same_object(self):
        r1 = get_default_resolver()
        r2 = get_default_resolver()
        assert r1 is r2

    def test_can_resolve_canonical(self):
        resolver = get_default_resolver()
        r = resolver.resolve("select-basic")
        assert r.resolved


# ---------------------------------------------------------------------------
# TestAliasFileIntegrity
# ---------------------------------------------------------------------------


class TestAliasFileIntegrity:
    """Verify the alias file itself is well-formed."""

    @pytest.fixture(scope="class")
    def alias_data(self):
        with open(_ALIASES_PATH, encoding="utf-8") as fh:
            return json.load(fh)

    def test_has_version(self, alias_data):
        assert "version" in alias_data

    def test_has_aliases_key(self, alias_data):
        assert "aliases" in alias_data
        assert isinstance(alias_data["aliases"], dict)

    def test_all_alias_targets_in_registry(self, alias_data):
        """Every value in aliases must be a canonical registry ID."""
        resolver = _make_resolver()
        for alias, canonical in alias_data["aliases"].items():
            assert resolver.is_canonical(canonical), (
                f"Alias target {canonical!r} (from {alias!r}) is not in registry"
            )

    def test_no_alias_points_to_itself(self, alias_data):
        for alias, canonical in alias_data["aliases"].items():
            assert alias != canonical, f"Alias {alias!r} maps to itself"
