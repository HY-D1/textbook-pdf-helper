#!/usr/bin/env python3
"""Student Learning Quality Artifact Report

Produces a human-readable quality summary from built textbook-static output.
Reads concept-quality.json and textbook-units.json to report on:
- Total concepts and quality distribution
- Fallback enrichment coverage (key points, examples)
- Examples that were intentionally suppressed due to corruption
- Representative concept examples for each category

Usage:
    python scripts/report_student_learning_quality.py ./output/textbook-static
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any] | None:
    """Load JSON file if it exists."""
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Error loading {path}: {e}", file=sys.stderr)
        return None


def find_representative_concepts(
    quality_by_concept: dict[str, dict],
    textbook_static_dir: Path,
) -> dict[str, dict | None]:
    """Find one representative concept for each quality category."""

    # Clean concept: readabilityStatus == "ok", exampleQuality == "valid"
    clean = None
    # Fallback with key points: readabilityStatus == "fallback_only", has learnerSafeKeyPoints
    fallback_with_key_points = None
    # Fallback with examples: readabilityStatus == "fallback_only", has learnerSafeExamples
    fallback_with_examples = None
    # Fallback with suppressed examples: readabilityStatus == "fallback_only", exampleQuality == "hidden"
    fallback_suppressed = None

    for namespaced_id, entry in quality_by_concept.items():
        rs = entry.get("readabilityStatus", "")
        eq = entry.get("exampleQuality", "")
        kp = entry.get("learnerSafeKeyPoints", [])
        ex = entry.get("learnerSafeExamples", [])

        if clean is None and rs == "ok" and eq == "valid":
            clean = {"namespaced_id": namespaced_id, **entry}

        if rs == "fallback_only":
            if fallback_with_key_points is None and kp:
                fallback_with_key_points = {"namespaced_id": namespaced_id, **entry}

            if fallback_with_examples is None and ex:
                fallback_with_examples = {"namespaced_id": namespaced_id, **entry}

            if fallback_suppressed is None and eq == "hidden":
                fallback_suppressed = {"namespaced_id": namespaced_id, **entry}

        # Early exit if we found all representatives
        if all([clean, fallback_with_key_points, fallback_with_examples, fallback_suppressed]):
            break

    return {
        "clean": clean,
        "fallback_with_key_points": fallback_with_key_points,
        "fallback_with_examples": fallback_with_examples,
        "fallback_suppressed": fallback_suppressed,
    }


def format_concept_preview(concept: dict | None, textbook_static_dir: Path) -> str:
    """Format a concept entry for display in the report."""
    if concept is None:
        return "  (none found)\n"

    lines = []
    nid = concept.get("namespaced_id", "unknown")
    title = concept.get("learnerSafeSummary", "No summary").split(":")[0]
    rs = concept.get("readabilityStatus", "unknown")
    eq = concept.get("exampleQuality", "unknown")

    lines.append(f"  Concept: {nid}")
    lines.append(f"  Title: {title}")
    lines.append(f"  readabilityStatus: {rs}")
    lines.append(f"  exampleQuality: {eq}")

    # Show key points (first 3)
    kp = concept.get("learnerSafeKeyPoints", [])
    if kp:
        lines.append(f"  learnerSafeKeyPoints ({len(kp)} total):")
        for point in kp[:3]:
            lines.append(f"    - {point}")
        if len(kp) > 3:
            lines.append(f"    ... and {len(kp) - 3} more")
    else:
        lines.append("  learnerSafeKeyPoints: (none)")

    # Show examples (first 1, truncated)
    ex = concept.get("learnerSafeExamples", [])
    if ex:
        lines.append(f"  learnerSafeExamples ({len(ex)} total):")
        sql = ex[0].get("sql", "")
        sql_preview = sql[:100].replace("\n", " ")
        if len(sql) > 100:
            sql_preview += "..."
        lines.append(f"    Example 1: {sql_preview}")
    else:
        lines.append("  learnerSafeExamples: (none)")

    # Show warnings if any
    warnings = concept.get("readabilityWarnings", [])
    if warnings:
        lines.append(f"  readabilityWarnings ({len(warnings)}):")
        for w in warnings[:2]:
            lines.append(f"    - {w[:100]}{'...' if len(w) > 100 else ''}")
        if len(warnings) > 2:
            lines.append(f"    ... and {len(warnings) - 2} more")

    lines.append("")
    return "\n".join(lines)


def generate_report(textbook_static_dir: Path) -> str:
    """Generate the full student learning quality report."""

    # Load concept-quality.json
    cq_path = textbook_static_dir / "concept-quality.json"
    cq_data = load_json(cq_path)
    if cq_data is None:
        return f"Error: Could not load {cq_path}\n"

    quality_by_concept = cq_data.get("qualityByConcept", {})
    total_concepts = len(quality_by_concept)

    if total_concepts == 0:
        return "Error: No concepts found in concept-quality.json\n"

    # Compute statistics
    ok_count = 0
    fallback_count = 0
    fallback_with_key_points = 0
    fallback_with_examples = 0
    fallback_with_suppressed = 0

    for entry in quality_by_concept.values():
        rs = entry.get("readabilityStatus", "")
        eq = entry.get("exampleQuality", "")
        kp = entry.get("learnerSafeKeyPoints", [])
        ex = entry.get("learnerSafeExamples", [])

        if rs == "ok":
            ok_count += 1
        elif rs == "fallback_only":
            fallback_count += 1
            if kp:
                fallback_with_key_points += 1
            if ex:
                fallback_with_examples += 1
            if eq == "hidden":
                fallback_with_suppressed += 1

    # Find representative concepts
    representatives = find_representative_concepts(quality_by_concept, textbook_static_dir)

    # Build report
    lines = []
    lines.append("=" * 70)
    lines.append("STUDENT LEARNING QUALITY ARTIFACT REPORT")
    lines.append("=" * 70)
    lines.append("")

    # Summary statistics
    lines.append("SUMMARY")
    lines.append("-" * 40)
    lines.append(f"  Total concepts:           {total_concepts}")
    lines.append(f"  Clean (ok):               {ok_count} ({ok_count/total_concepts:.1%})")
    lines.append(f"  Fallback only:            {fallback_count} ({fallback_count/total_concepts:.1%})")
    lines.append("")

    # Fallback enrichment
    if fallback_count > 0:
        lines.append("FALLBACK ENRICHMENT COVERAGE")
        lines.append("-" * 40)
        lines.append(f"  With learnerSafeKeyPoints:   {fallback_with_key_points}/{fallback_count} ({fallback_with_key_points/fallback_count:.1%})")
        lines.append(f"  With learnerSafeExamples:    {fallback_with_examples}/{fallback_count} ({fallback_with_examples/fallback_count:.1%})")
        lines.append(f"  With suppressed examples:    {fallback_with_suppressed}/{fallback_count} (examples intentionally hidden due to corruption)")
        lines.append("")

    # Example quality breakdown (all concepts)
    valid_count = sum(1 for e in quality_by_concept.values() if e.get("exampleQuality") == "valid")
    filtered_count = sum(1 for e in quality_by_concept.values() if e.get("exampleQuality") == "filtered")
    hidden_count = sum(1 for e in quality_by_concept.values() if e.get("exampleQuality") == "hidden")

    lines.append("EXAMPLE QUALITY DISTRIBUTION (all concepts)")
    lines.append("-" * 40)
    lines.append(f"  valid:    {valid_count} ({valid_count/total_concepts:.1%})")
    lines.append(f"  filtered: {filtered_count} ({filtered_count/total_concepts:.1%})")
    lines.append(f"  hidden:   {hidden_count} ({hidden_count/total_concepts:.1%})")
    lines.append("")

    # Representative examples
    lines.append("=" * 70)
    lines.append("REPRESENTATIVE CONCEPT EXAMPLES")
    lines.append("=" * 70)
    lines.append("")

    lines.append("1. CLEAN CONCEPT (readabilityStatus=ok, exampleQuality=valid)")
    lines.append("-" * 60)
    lines.append(format_concept_preview(representatives["clean"], textbook_static_dir))

    lines.append("2. FALLBACK CONCEPT WITH KEY POINTS")
    lines.append("-" * 60)
    lines.append(format_concept_preview(representatives["fallback_with_key_points"], textbook_static_dir))

    lines.append("3. FALLBACK CONCEPT WITH EXAMPLES")
    lines.append("-" * 60)
    lines.append(format_concept_preview(representatives["fallback_with_examples"], textbook_static_dir))

    lines.append("4. FALLBACK CONCEPT WITH SUPPRESSED EXAMPLES")
    lines.append("   (examples were intentionally hidden due to corruption)")
    lines.append("-" * 60)
    lines.append(format_concept_preview(representatives["fallback_suppressed"], textbook_static_dir))

    # Sync readiness assessment
    lines.append("=" * 70)
    lines.append("SYNC READINESS ASSESSMENT")
    lines.append("=" * 70)
    lines.append("")

    # Determine if output is good enough to sync
    fallback_ratio = fallback_count / total_concepts if total_concepts > 0 else 0
    key_points_coverage = fallback_with_key_points / fallback_count if fallback_count > 0 else 1.0

    if fallback_ratio > 0.70:
        lines.append("  Status: ⚠️  WARNING")
        lines.append(f"  More than 70% of concepts are fallback_only ({fallback_ratio:.0%}).")
        lines.append("  Consider reviewing extraction quality before syncing.")
    elif fallback_ratio > 0.50:
        lines.append("  Status: ⚠️  CAUTION")
        lines.append(f"  {fallback_ratio:.0%} of concepts are fallback_only.")
        lines.append("  Output is usable but has significant quality limitations.")
    else:
        lines.append("  Status: ✅ GOOD")
        lines.append(f"  {fallback_ratio:.0%} of concepts are fallback_only.")
        lines.append("  Output quality is acceptable for sync.")

    lines.append("")

    if key_points_coverage < 0.80 and fallback_count > 0:
        lines.append("  ⚠️  Key points coverage is below 80% threshold.")
        lines.append("     Fallback concepts may lack structured metadata.")
        lines.append("")

    lines.append("=" * 70)
    lines.append("END OF REPORT")
    lines.append("=" * 70)

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate student learning quality report from textbook-static output"
    )
    parser.add_argument(
        "output_dir",
        help="Path to textbook-static output directory (e.g., ./output/textbook-static)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    if not output_dir.is_dir():
        print(f"Error: Directory not found: {output_dir}", file=sys.stderr)
        return 1

    report = generate_report(output_dir)
    print(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
