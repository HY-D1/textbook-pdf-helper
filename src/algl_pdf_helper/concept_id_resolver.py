"""
Canonical concept-ID resolver for the SQL-Engage pipeline.

Resolves arbitrary concept IDs (from curated files, extraction output, etc.)
to canonical IDs as defined in ``concept_registry.yaml``.

Resolution chain (first match wins):
  1. Exact match against registry IDs.
  2. Known alias from ``data/concept_id_aliases.json``.
  3. Normalised form (underscore → hyphen, lowercase).

Each call returns a :class:`ResolutionResult` that records how the ID was
resolved so downstream callers can log and surface the path.

Usage::

    from algl_pdf_helper.concept_id_resolver import ConceptIdResolver

    resolver = ConceptIdResolver.from_data_dir()
    result = resolver.resolve("stored-procedures")
    # result.canonical_id  → "stored-procedure"
    # result.resolution    → "alias"
    # result.resolved      → True
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent.parent / "data"
_REGISTRY_PATH = _DATA_DIR / "concept_registry.yaml"
_ALIASES_PATH = _DATA_DIR / "concept_id_aliases.json"

# Resolution type literals
EXACT = "exact"
ALIAS = "alias"
NORMALIZED = "normalized"
NOT_FOUND = "not_found"


@dataclass
class ResolutionResult:
    """Outcome of a single concept-ID resolution attempt."""

    requested_id: str
    canonical_id: Optional[str]
    resolution: str  # EXACT | ALIAS | NORMALIZED | NOT_FOUND
    resolved: bool = field(init=False)

    def __post_init__(self) -> None:
        self.resolved = self.canonical_id is not None

    def to_metadata(self) -> dict:
        """Return a compact dict suitable for embedding in unit _metadata."""
        return {
            "requested_concept_id": self.requested_id,
            "resolved_concept_id": self.canonical_id or self.requested_id,
            "content_source_resolution": self.resolution,
        }


def _normalise(concept_id: str) -> str:
    """Replace underscores with hyphens and lowercase."""
    return re.sub(r"[_\s]+", "-", concept_id).lower()


class ConceptIdResolver:
    """
    Resolves concept IDs to their canonical form.

    Parameters
    ----------
    registry_ids:
        Set of canonical concept IDs (from concept_registry.yaml).
    aliases:
        Mapping of non-canonical IDs → canonical IDs
        (from concept_id_aliases.json).
    """

    def __init__(
        self,
        registry_ids: set[str],
        aliases: dict[str, str],
    ) -> None:
        self._registry_ids = frozenset(registry_ids)
        self._aliases = dict(aliases)
        # Pre-build a normalised-ID → canonical-ID map for step 3
        self._normalised: dict[str, str] = {
            _normalise(cid): cid for cid in registry_ids
        }

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_data_dir(
        cls,
        registry_path: Path = _REGISTRY_PATH,
        aliases_path: Path = _ALIASES_PATH,
    ) -> "ConceptIdResolver":
        """Load registry and aliases from the project's data directory."""
        registry_ids = _load_registry_ids(registry_path)
        aliases = _load_aliases(aliases_path)
        return cls(registry_ids=registry_ids, aliases=aliases)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(self, concept_id: str) -> ResolutionResult:
        """
        Resolve *concept_id* to its canonical form.

        Resolution chain
        ----------------
        1. Exact match against registry IDs.
        2. Known alias from concept_id_aliases.json.
        3. Normalised form (underscores → hyphens, lowercase).
        4. Not found — returns requested ID as canonical_id=None.
        """
        # 1. Exact match
        if concept_id in self._registry_ids:
            logger.debug("Resolved %r via exact match", concept_id)
            return ResolutionResult(
                requested_id=concept_id,
                canonical_id=concept_id,
                resolution=EXACT,
            )

        # 2. Known alias
        if concept_id in self._aliases:
            canonical = self._aliases[concept_id]
            logger.debug("Resolved %r → %r via alias", concept_id, canonical)
            return ResolutionResult(
                requested_id=concept_id,
                canonical_id=canonical,
                resolution=ALIAS,
            )

        # 3. Normalised form
        normed = _normalise(concept_id)
        if normed in self._normalised:
            canonical = self._normalised[normed]
            logger.debug("Resolved %r → %r via normalisation", concept_id, canonical)
            return ResolutionResult(
                requested_id=concept_id,
                canonical_id=canonical,
                resolution=NORMALIZED,
            )

        # 4. Not found
        logger.debug("No canonical mapping found for %r", concept_id)
        return ResolutionResult(
            requested_id=concept_id,
            canonical_id=None,
            resolution=NOT_FOUND,
        )

    def resolve_for_lookup(self, concept_id: str) -> tuple[str, ResolutionResult]:
        """
        Convenience method: resolve and return the best lookup key.

        Returns
        -------
        (lookup_id, result)
            *lookup_id* is the canonical ID if resolved, else the original.
        """
        result = self.resolve(concept_id)
        lookup_id = result.canonical_id if result.resolved else concept_id
        return lookup_id, result

    def is_canonical(self, concept_id: str) -> bool:
        """Return True if the ID is already a canonical registry ID."""
        return concept_id in self._registry_ids

    @property
    def registry_ids(self) -> frozenset[str]:
        return self._registry_ids

    @property
    def aliases(self) -> dict[str, str]:
        return dict(self._aliases)


# ------------------------------------------------------------------
# Loader helpers
# ------------------------------------------------------------------


def _load_registry_ids(path: Path) -> set[str]:
    """Parse concept_registry.yaml and return the set of concept IDs."""
    if not path.exists():
        logger.warning("concept_registry.yaml not found at %s", path)
        return set()
    try:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        concepts = data.get("concepts", [])
        return {c["id"] for c in concepts if "id" in c}
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to load concept registry from %s: %s", path, exc)
        return set()


def _load_aliases(path: Path) -> dict[str, str]:
    """Parse concept_id_aliases.json and return the alias → canonical mapping."""
    if not path.exists():
        logger.warning("concept_id_aliases.json not found at %s", path)
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return dict(data.get("aliases", {}))
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to load aliases from %s: %s", path, exc)
        return {}


# ------------------------------------------------------------------
# Module-level singleton (lazy, created on first use)
# ------------------------------------------------------------------

_default_resolver: Optional[ConceptIdResolver] = None


def get_default_resolver() -> ConceptIdResolver:
    """
    Return the module-level default resolver (loaded once from data/).

    Thread-safety: the first call constructs the resolver; subsequent calls
    return the cached instance. Construction is fast enough that a minor race
    on startup is acceptable.
    """
    global _default_resolver
    if _default_resolver is None:
        _default_resolver = ConceptIdResolver.from_data_dir()
    return _default_resolver
