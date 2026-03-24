#!/usr/bin/env python3
"""
audit_curated_coverage.py
=========================
Reports how well curated data files align with the canonical concept registry.

Emits human-readable text to stdout and (optionally) a JSON summary to
``--output`` / ``audit_coverage_report.json``.

Usage::

    python scripts/audit_curated_coverage.py
    python scripts/audit_curated_coverage.py --output reports/coverage.json

Exit codes
----------
0  All curated keys are canonical or resolvable (zero unreachable).
1  One or more curated keys are unreachable (no canonical mapping).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap: add src/ to path so we can import from algl_pdf_helper
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from algl_pdf_helper.concept_id_resolver import ConceptIdResolver  # noqa: E402

_DATA_DIR = _REPO_ROOT / "data"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_json_keys(path: Path) -> list[str]:
    if not path.exists():
        print(f"  [WARN] File not found: {path}", file=sys.stderr)
        return []
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return list(data.keys())


def _check_file(
    label: str,
    keys: list[str],
    resolver: ConceptIdResolver,
) -> dict:
    """Audit one curated file and return a summary dict."""
    total = len(keys)
    exact, alias, normalized, not_found = [], [], [], []

    for key in keys:
        result = resolver.resolve(key)
        if result.resolution == "exact":
            exact.append(key)
        elif result.resolution == "alias":
            alias.append(key)
        elif result.resolution == "normalized":
            normalized.append(key)
        else:
            not_found.append(key)

    resolvable = len(exact) + len(alias) + len(normalized)

    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  Total keys       : {total}")
    print(f"  Canonical (exact): {len(exact)}")
    print(f"  Resolved via alias    : {len(alias)}")
    print(f"  Resolved via normalise: {len(normalized)}")
    print(f"  No canonical mapping  : {len(not_found)}  ← UNREACHABLE")
    if alias:
        print(f"\n  Alias resolutions:")
        for k in sorted(alias):
            canonical = resolver.resolve(k).canonical_id
            print(f"    {k!r:40s} → {canonical!r}")
    if normalized:
        print(f"\n  Normalised resolutions:")
        for k in sorted(normalized):
            canonical = resolver.resolve(k).canonical_id
            print(f"    {k!r:40s} → {canonical!r}")
    if not_found:
        print(f"\n  Unreachable keys (no canonical mapping):")
        for k in sorted(not_found):
            print(f"    {k!r}")

    return {
        "file": label,
        "total": total,
        "exact": len(exact),
        "alias": len(alias),
        "normalized": len(normalized),
        "unreachable": len(not_found),
        "resolvable": resolvable,
        "coverage_pct": round(100 * resolvable / total, 1) if total else 0.0,
        "exact_keys": sorted(exact),
        "alias_keys": sorted(alias),
        "normalized_keys": sorted(normalized),
        "unreachable_keys": sorted(not_found),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional JSON output path for the coverage report.",
    )
    args = parser.parse_args(argv)

    resolver = ConceptIdResolver.from_data_dir(
        registry_path=_DATA_DIR / "concept_registry.yaml",
        aliases_path=_DATA_DIR / "concept_id_aliases.json",
    )

    registry_count = len(resolver.registry_ids)
    print(f"\nSQL-Engage Curated Coverage Audit")
    print(f"Registry canonical concepts: {registry_count}")
    print(f"Aliases defined            : {len(resolver.aliases)}")

    files = {
        "concept_curated_units.json": _DATA_DIR / "concept_curated_units.json",
        "concept_curated_l3.json": _DATA_DIR / "concept_curated_l3.json",
        "concept_examples.json": _DATA_DIR / "concept_examples.json",
    }

    summaries = []
    any_unreachable = False

    for label, path in files.items():
        keys = _load_json_keys(path)
        summary = _check_file(label, keys, resolver)
        summaries.append(summary)
        if summary["unreachable"] > 0:
            any_unreachable = True

    # -----------------------------------------------------------------------
    # Cross-file summary: which canonical concepts have curated coverage?
    # -----------------------------------------------------------------------
    print(f"\n{'='*60}")
    print("  Cross-file canonical coverage")
    print(f"{'='*60}")

    # Build sets of canonical IDs that each file covers
    def _canonical_coverage(path: Path) -> set[str]:
        keys = _load_json_keys(path)
        covered = set()
        for k in keys:
            r = resolver.resolve(k)
            if r.resolved:
                covered.add(r.canonical_id)
        return covered

    units_coverage = _canonical_coverage(_DATA_DIR / "concept_curated_units.json")
    l3_coverage = _canonical_coverage(_DATA_DIR / "concept_curated_l3.json")
    examples_coverage = _canonical_coverage(_DATA_DIR / "concept_examples.json")

    all_canonical = sorted(resolver.registry_ids)
    rows = []
    default_only = []
    for cid in all_canonical:
        has_units = cid in units_coverage
        has_l3 = cid in l3_coverage
        has_examples = cid in examples_coverage
        row = {
            "concept_id": cid,
            "curated_unit_pack": has_units,
            "curated_l3": has_l3,
            "curated_examples": has_examples,
            "any_curated": has_units or has_l3 or has_examples,
        }
        rows.append(row)
        if not row["any_curated"]:
            default_only.append(cid)

    any_coverage_count = sum(1 for r in rows if r["any_curated"])
    print(f"  Canonical concepts with any curated coverage : {any_coverage_count}/{registry_count}")
    print(f"  Concepts with curated unit pack              : {len(units_coverage)}")
    print(f"  Concepts with curated L3                     : {len(l3_coverage)}")
    print(f"  Concepts with curated examples               : {len(examples_coverage)}")
    print(f"  Concepts still default-only                  : {len(default_only)}")
    if default_only:
        print(f"\n  Default-only concepts:")
        for cid in sorted(default_only):
            print(f"    {cid}")

    # -----------------------------------------------------------------------
    # Overall verdict
    # -----------------------------------------------------------------------
    total_unreachable = sum(s["unreachable"] for s in summaries)
    print(f"\n{'='*60}")
    if total_unreachable == 0:
        print("  VERDICT: ALL curated keys are canonical or resolvable. ✓")
    else:
        print(f"  VERDICT: {total_unreachable} curated key(s) are UNREACHABLE. ✗")
        print("           Run audit again after adding aliases to fix these.")
    print(f"{'='*60}\n")

    # -----------------------------------------------------------------------
    # JSON output
    # -----------------------------------------------------------------------
    report = {
        "registry_count": registry_count,
        "aliases_defined": len(resolver.aliases),
        "files": summaries,
        "cross_file_coverage": {
            "any_curated_count": any_coverage_count,
            "unit_pack_count": len(units_coverage),
            "l3_count": len(l3_coverage),
            "examples_count": len(examples_coverage),
            "default_only_count": len(default_only),
            "default_only_concepts": sorted(default_only),
        },
        "per_concept": rows,
        "total_unreachable": total_unreachable,
        "verdict": "pass" if total_unreachable == 0 else "fail",
    }

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"JSON report written to: {args.output}")
    else:
        print(json.dumps(report, indent=2))

    return 1 if any_unreachable else 0


if __name__ == "__main__":
    sys.exit(main())
