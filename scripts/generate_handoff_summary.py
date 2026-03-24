#!/usr/bin/env python3
"""
Generate a compact handoff verification summary for the textbook-static export.

Usage:
    python scripts/generate_handoff_summary.py <export_dir> [--out docs/handoff-verification-summary.md]

The script reads the actual export artifacts and writes a verification summary
that states counts and whether the handoff integrity check passed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running without install
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from algl_pdf_helper.export_sqladapt import validate_handoff_integrity


def generate_summary(export_dir: Path, out_path: Path) -> None:
    result = validate_handoff_integrity(export_dir)

    # Also gather textbook-manifest metadata for the summary
    textbook_manifest_file = export_dir / "textbook-manifest.json"
    manifest_meta: dict = {}
    if textbook_manifest_file.exists():
        with open(textbook_manifest_file, "r", encoding="utf-8") as f:
            manifest_meta = json.load(f)

    source_docs = manifest_meta.get("sourceDocs", [])
    has_placeholder_sha = any(
        d.get("sha256") in ("unknown", "unavailable", None, "")
        for d in source_docs
    )
    has_placeholder_pages = any(
        (d.get("pageCount") or 0) == 0
        for d in source_docs
    )

    status_icon = "PASS" if result["valid"] else "FAIL"
    timestamp = datetime.now(timezone.utc).isoformat()

    lines = [
        "# Handoff Verification Summary",
        "",
        f"Generated: {timestamp}",
        f"Export directory: `{export_dir}`",
        "",
        f"## Overall Status: {status_icon}",
        "",
        "## Counts",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| concept-map entries | {result['concept_map_entries']} |",
        f"| markdown files generated | {result['markdown_files']} |",
        f"| missing concept pages | {len(result['missing_pages'])} |",
        f"| orphan markdown files | {len(result['orphan_pages'])} |",
        f"| sourceDocs (textbook-manifest) | {result['source_docs_count']} |",
        f"| doc directories (concepts/) | {result['doc_dirs_count']} |",
        f"| chunks-metadata docIds | {len(result['chunks_meta_doc_ids'])} |",
        f"| sha256 placeholder detected | {'YES (needs fix)' if has_placeholder_sha else 'no'} |",
        f"| pageCount=0 detected | {'YES (needs fix)' if has_placeholder_pages else 'no'} |",
        "",
    ]

    if result["errors"]:
        lines += ["## Errors", ""]
        for e in result["errors"]:
            lines.append(f"- {e}")
        lines.append("")

    if result["warnings"]:
        lines += ["## Warnings", ""]
        for w in result["warnings"]:
            lines.append(f"- {w}")
        lines.append("")

    if result["missing_pages"]:
        lines += ["## Missing Concept Pages", ""]
        for mid in result["missing_pages"]:
            lines.append(f"- `{mid}`")
        lines.append("")

    if result["orphan_pages"]:
        lines += ["## Orphan Markdown Files", ""]
        for oid in result["orphan_pages"]:
            lines.append(f"- `{oid}`")
        lines.append("")

    lines += [
        "## Source Documents",
        "",
        "| docId | sha256 | pageCount |",
        "|-------|--------|-----------|",
    ]
    for doc in source_docs:
        sha = doc.get("sha256", "")
        pages = doc.get("pageCount", 0)
        lines.append(f"| {doc.get('docId', '?')} | {sha[:16]}{'...' if sha and len(sha) > 16 else ''} | {pages} |")
    lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Summary written to: {out_path}")
    print(f"Overall: {status_icon}")
    if result["errors"]:
        print(f"Errors ({len(result['errors'])}):")
        for e in result["errors"]:
            print(f"  - {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate handoff verification summary")
    parser.add_argument("export_dir", help="Path to textbook-static export directory")
    parser.add_argument(
        "--out",
        default="docs/handoff-verification-summary.md",
        help="Output path for the summary (default: docs/handoff-verification-summary.md)",
    )
    args = parser.parse_args()

    export_dir = Path(args.export_dir)
    if not export_dir.exists():
        print(f"Error: export directory does not exist: {export_dir}", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.out)
    generate_summary(export_dir, out_path)


if __name__ == "__main__":
    main()
