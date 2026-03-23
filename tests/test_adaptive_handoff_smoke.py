"""Adaptive handoff smoke gate.

One command proves the full producer path:
    PYTHONPATH=src python -m pytest tests/test_adaptive_handoff_smoke.py -v

Sub-checks are organised in three tiers:
  1. STATIC   — pure file/code checks; no PDFs or output required; always run.
  2. PREFLIGHT — real-PDF routing checks; skipped when raw_pdf/ not present.
  3. ARTIFACT  — checks on existing output/textbook-static/; skipped when absent.

The gate FAILS on the old uploaded-zip state (missing build script, wrong
preflight routing, no validate-handoff, missing merge) and PASSES on the
corrected repo snapshot.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Repo-root fixture
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Tier 1 — STATIC checks (always run, no real PDFs needed)
# ---------------------------------------------------------------------------


class TestStaticProducerPath:
    """Checks that the canonical producer-path files/code exist in the repo."""

    def test_build_script_exists(self):
        """scripts/build_textbook_static.sh must be present."""
        script = REPO_ROOT / "scripts" / "build_textbook_static.sh"
        assert script.exists(), (
            "scripts/build_textbook_static.sh is missing — "
            "the canonical adaptive-export script was not committed."
        )

    def test_build_script_is_executable_or_bash(self):
        """build_textbook_static.sh must be a bash script (not a stub)."""
        script = REPO_ROOT / "scripts" / "build_textbook_static.sh"
        text = script.read_text()
        assert text.strip().startswith("#!/bin/bash"), (
            "build_textbook_static.sh does not start with #!/bin/bash"
        )
        # Must contain all three phase labels
        for phase in ("Phase 1", "Phase 2", "Phase 3"):
            assert phase in text, f"build_textbook_static.sh missing '{phase}' section"

    def test_no_hardcoded_absolute_paths_in_build_script(self):
        """build_textbook_static.sh must not contain /Users/... or /home/... paths.

        This is the test that would FAIL on the old uploaded-zip state where
        the script either did not exist or contained hard-coded local paths.
        """
        script = REPO_ROOT / "scripts" / "build_textbook_static.sh"
        text = script.read_text()
        # Match any line that is not a comment and contains an absolute home path
        non_comment_lines = [
            ln for ln in text.splitlines() if not ln.lstrip().startswith("#")
        ]
        bad_lines = [
            ln
            for ln in non_comment_lines
            if re.search(r"/(Users|home)/\w", ln)
        ]
        assert bad_lines == [], (
            "build_textbook_static.sh contains hard-coded absolute paths:\n"
            + "\n".join(bad_lines)
        )

    def test_no_hardcoded_absolute_paths_in_run_reprocess(self):
        """run_reprocess.sh (if present) must not contain /Users/... paths."""
        script = REPO_ROOT / "scripts" / "run_reprocess.sh"
        if not script.exists():
            pytest.skip("run_reprocess.sh not present")
        text = script.read_text()
        non_comment_lines = [
            ln for ln in text.splitlines() if not ln.lstrip().startswith("#")
        ]
        bad_lines = [
            ln for ln in non_comment_lines if re.search(r"/(Users|home)/\w", ln)
        ]
        assert bad_lines == [], (
            "run_reprocess.sh contains hard-coded absolute paths:\n"
            + "\n".join(bad_lines)
        )

    def test_validate_handoff_cli_command_registered(self):
        """validate-handoff must be a registered CLI command.

        Importing the CLI module and inspecting its registered commands is
        sufficient — no subprocess needed, no PDFs needed.
        """
        # Insert src into path so we can import without installation
        src = str(REPO_ROOT / "src")
        if src not in sys.path:
            sys.path.insert(0, src)

        from algl_pdf_helper.cli import app  # noqa: PLC0415

        registered = [cmd.name for cmd in app.registered_commands]
        assert "validate-handoff" in registered, (
            f"'validate-handoff' not found in CLI commands: {registered}"
        )

    def test_validate_handoff_integrity_function_exists(self):
        """validate_handoff_integrity() must be importable."""
        src = str(REPO_ROOT / "src")
        if src not in sys.path:
            sys.path.insert(0, src)
        from algl_pdf_helper import export_sqladapt  # noqa: PLC0415

        assert hasattr(export_sqladapt, "validate_handoff_integrity"), (
            "validate_handoff_integrity function missing from export_sqladapt"
        )

    def test_preflight_uses_embedded_text_ocr_floor(self):
        """determine_strategy() must use EMBEDDED_TEXT_OCR_FLOOR (0.30), not
        MIN_TEXT_COVERAGE (0.70), as the threshold for digital PDFs.

        This is the regression guard: before the fix, digital SQL textbooks
        with coverage in the 0.30–0.70 range were routed to OCR.
        """
        src = str(REPO_ROOT / "src")
        if src not in sys.path:
            sys.path.insert(0, src)
        from algl_pdf_helper.preflight import determine_strategy  # noqa: PLC0415

        for coverage in (0.35, 0.45, 0.55, 0.62, 0.68):
            strategy = determine_strategy(
                has_embedded_text=True,
                text_coverage=coverage,
                table_count=3,
                warning_flags=[],
            )
            assert strategy == "direct", (
                f"Digital PDF with coverage={coverage} routed to '{strategy}' "
                f"instead of 'direct' — EMBEDDED_TEXT_OCR_FLOOR fix missing."
            )

    def test_build_concept_quality_index_function_exists(self):
        """build_concept_quality_index() must be importable from export_sqladapt."""
        src = str(REPO_ROOT / "src")
        if src not in sys.path:
            sys.path.insert(0, src)
        from algl_pdf_helper import export_sqladapt  # noqa: PLC0415

        assert hasattr(export_sqladapt, "build_concept_quality_index"), (
            "build_concept_quality_index function missing from export_sqladapt"
        )

    def test_export_sqladapt_has_merge_logic(self):
        """export_sqladapt.py must contain the merge-safe textbook-manifest code."""
        export_file = REPO_ROOT / "src" / "algl_pdf_helper" / "export_sqladapt.py"
        assert export_file.exists(), "export_sqladapt.py not found"
        text = export_file.read_text()
        assert "existing_textbook_manifest" in text, (
            "export_sqladapt.py is missing the merge-safe textbook-manifest logic"
        )
        assert "merged_docs" in text, (
            "export_sqladapt.py is missing merged_docs assembly (sourceDocs merge)"
        )

    def test_build_script_processes_both_pdfs(self):
        """build_textbook_static.sh must reference both known PDF filenames."""
        script = REPO_ROOT / "scripts" / "build_textbook_static.sh"
        text = script.read_text()
        assert "murachs-mysql-3rd-edition.pdf" in text
        assert "dbms-ramakrishnan-3rd-edition.pdf" in text

    def test_build_script_calls_validate_handoff(self):
        """build_textbook_static.sh must call validate-handoff (Phase 3)."""
        script = REPO_ROOT / "scripts" / "build_textbook_static.sh"
        text = script.read_text()
        assert "validate-handoff" in text, (
            "build_textbook_static.sh does not call validate-handoff in Phase 3"
        )

    def test_build_script_uses_merge_flag(self):
        """build_textbook_static.sh must pass --merge to the export command."""
        script = REPO_ROOT / "scripts" / "build_textbook_static.sh"
        text = script.read_text()
        assert "--merge" in text, (
            "build_textbook_static.sh does not pass --merge to export — "
            "second PDF export would overwrite first instead of merging."
        )


# ---------------------------------------------------------------------------
# Tier 2 — PREFLIGHT checks (skipped if raw PDFs absent)
# ---------------------------------------------------------------------------

MURACH_PDF = REPO_ROOT / "raw_pdf" / "murachs-mysql-3rd-edition.pdf"
RAMI_PDF = REPO_ROOT / "raw_pdf" / "dbms-ramakrishnan-3rd-edition.pdf"
_REAL_PDFS = MURACH_PDF.exists() and RAMI_PDF.exists()


@pytest.mark.skipif(not _REAL_PDFS, reason="raw PDFs not present — skipping live preflight")
class TestRealPdfPreflightRouting:
    """Both real textbooks must route to 'direct', not OCR.

    This would FAIL on the old state where MIN_TEXT_COVERAGE was used as the
    threshold and digital SQL textbooks were incorrectly sent to OCR.
    """

    def _run_preflight(self, pdf_path: Path):
        src = str(REPO_ROOT / "src")
        if src not in sys.path:
            sys.path.insert(0, src)
        from algl_pdf_helper.preflight import run_preflight  # noqa: PLC0415
        return run_preflight(pdf_path)

    def test_murach_routes_to_direct(self):
        report = self._run_preflight(MURACH_PDF)
        assert report.recommended_strategy == "direct", (
            f"Murach PDF routed to '{report.recommended_strategy}' "
            f"(coverage={report.text_coverage_score:.2f}) — expected 'direct'"
        )

    def test_ramakrishnan_routes_to_direct(self):
        report = self._run_preflight(RAMI_PDF)
        assert report.recommended_strategy == "direct", (
            f"Ramakrishnan PDF routed to '{report.recommended_strategy}' "
            f"(coverage={report.text_coverage_score:.2f}) — expected 'direct'"
        )

    def test_both_pdfs_have_embedded_text(self):
        for pdf in (MURACH_PDF, RAMI_PDF):
            report = self._run_preflight(pdf)
            assert report.has_embedded_text, (
                f"{pdf.name}: has_embedded_text=False — PDF may not be digital"
            )


# ---------------------------------------------------------------------------
# Tier 3 — ARTIFACT checks (skipped if output absent)
# ---------------------------------------------------------------------------

OUTPUT_DIR = REPO_ROOT / "output" / "textbook-static"
_OUTPUT_EXISTS = OUTPUT_DIR.exists()


@pytest.mark.skipif(not _OUTPUT_EXISTS, reason="output/textbook-static not present — run build first")
class TestOutputArtifacts:
    """Verify that the output directory contains all required adaptive-app files."""

    def test_concept_map_exists(self):
        assert (OUTPUT_DIR / "concept-map.json").exists()

    def test_textbook_manifest_exists(self):
        assert (OUTPUT_DIR / "textbook-manifest.json").exists()

    def test_chunks_metadata_exists(self):
        assert (OUTPUT_DIR / "chunks-metadata.json").exists()

    def test_textbook_units_exists(self):
        assert (OUTPUT_DIR / "textbook-units.json").exists(), (
            "textbook-units.json missing — enrichment step may not have run"
        )

    def test_manifest_doc_count_is_two(self):
        """Merged manifest must reference both source docs (docCount == 2)."""
        data = json.loads((OUTPUT_DIR / "textbook-manifest.json").read_text())
        doc_count = data.get("docCount", 0)
        assert doc_count == 2, (
            f"textbook-manifest.json docCount={doc_count}, expected 2 — "
            "manifest merge is broken (second export overwrote first)"
        )

    def test_manifest_contains_both_source_docs(self):
        data = json.loads((OUTPUT_DIR / "textbook-manifest.json").read_text())
        doc_ids = {d["docId"] for d in data.get("sourceDocs", [])}
        assert "murachs-mysql-3rd-edition" in doc_ids, (
            f"Murach docId missing from sourceDocs: {doc_ids}"
        )
        assert "dbms-ramakrishnan-3rd-edition" in doc_ids, (
            f"Ramakrishnan docId missing from sourceDocs: {doc_ids}"
        )

    def test_concept_map_has_both_source_doc_ids(self):
        data = json.loads((OUTPUT_DIR / "concept-map.json").read_text())
        ids = set(data.get("sourceDocIds", []))
        assert "murachs-mysql-3rd-edition" in ids
        assert "dbms-ramakrishnan-3rd-edition" in ids

    def test_concept_directories_exist_for_both_docs(self):
        concepts_dir = OUTPUT_DIR / "concepts"
        assert (concepts_dir / "murachs-mysql-3rd-edition").is_dir(), (
            "concepts/murachs-mysql-3rd-edition/ directory missing"
        )
        assert (concepts_dir / "dbms-ramakrishnan-3rd-edition").is_dir(), (
            "concepts/dbms-ramakrishnan-3rd-edition/ directory missing"
        )

    def test_concept_map_entries_resolve_to_markdown(self):
        """Every concept-map entry must have a corresponding .md file."""
        concept_map = json.loads((OUTPUT_DIR / "concept-map.json").read_text())
        concepts_dir = OUTPUT_DIR / "concepts"
        missing = []
        for concept_id in concept_map.get("concepts", {}):
            # concept_id is namespaced: "<docId>/<bareId>"
            parts = concept_id.split("/", 1)
            if len(parts) == 2:
                doc_id, bare_id = parts
                md_file = concepts_dir / doc_id / f"{bare_id}.md"
                if not md_file.exists():
                    missing.append(str(md_file.relative_to(OUTPUT_DIR)))
        assert missing == [], (
            f"{len(missing)} concept-map entries have no .md file:\n"
            + "\n".join(missing[:10])
            + ("\n  ..." if len(missing) > 10 else "")
        )

    def test_concept_quality_exists(self):
        assert (OUTPUT_DIR / "concept-quality.json").exists(), (
            "concept-quality.json missing — re-run export to generate the quality index"
        )

    def test_concept_quality_schema_version(self):
        data = json.loads((OUTPUT_DIR / "concept-quality.json").read_text())
        assert data.get("schemaVersion") == "concept-quality-v1", (
            f"Unexpected schemaVersion in concept-quality.json: {data.get('schemaVersion')!r}"
        )

    def test_concept_quality_keys_align_with_concept_map(self):
        """Every key in concept-quality.json must be in concept-map.json."""
        concept_map = json.loads((OUTPUT_DIR / "concept-map.json").read_text())
        concept_quality = json.loads((OUTPUT_DIR / "concept-quality.json").read_text())
        map_keys = set(concept_map.get("concepts", {}).keys())
        quality_keys = set(concept_quality.get("qualityByConcept", {}).keys())
        extra = quality_keys - map_keys
        assert not extra, (
            f"concept-quality.json has {len(extra)} keys not in concept-map: "
            + ", ".join(sorted(extra)[:5])
        )

    def test_concept_quality_covers_all_concept_map_entries(self):
        """Every concept-map key must appear in concept-quality.json."""
        concept_map = json.loads((OUTPUT_DIR / "concept-map.json").read_text())
        concept_quality = json.loads((OUTPUT_DIR / "concept-quality.json").read_text())
        map_keys = set(concept_map.get("concepts", {}).keys())
        quality_keys = set(concept_quality.get("qualityByConcept", {}).keys())
        missing = map_keys - quality_keys
        assert not missing, (
            f"concept-quality.json missing {len(missing)} concept-map entries: "
            + ", ".join(sorted(missing)[:5])
        )

    def test_concept_quality_field_values_valid(self):
        """readabilityStatus and exampleQuality values must be from allowed sets."""
        data = json.loads((OUTPUT_DIR / "concept-quality.json").read_text())
        _valid_rs = {"ok", "fallback_only"}
        _valid_eq = {"valid", "filtered", "hidden"}
        bad = []
        for key, entry in data.get("qualityByConcept", {}).items():
            rs = entry.get("readabilityStatus")
            eq = entry.get("exampleQuality")
            if rs not in _valid_rs:
                bad.append(f"{key}: readabilityStatus={rs!r}")
            if eq not in _valid_eq:
                bad.append(f"{key}: exampleQuality={eq!r}")
        assert not bad, "Invalid quality field values: " + "; ".join(bad[:5])

    def test_textbook_units_has_units(self):
        data = json.loads((OUTPUT_DIR / "textbook-units.json").read_text())
        units = data.get("units", [])
        assert len(units) > 0, "textbook-units.json contains no units"

    def test_manifest_schema_version(self):
        data = json.loads((OUTPUT_DIR / "textbook-manifest.json").read_text())
        assert data.get("schemaVersion") == "1.0.0"
        assert data.get("schemaId") == "textbook-static-v1"


# ---------------------------------------------------------------------------
# Tier 3b — validate-handoff CLI integration (skipped if output absent)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _OUTPUT_EXISTS, reason="output/textbook-static not present — run build first")
class TestValidateHandoffCLI:
    """Run validate-handoff as a subprocess and assert exit-code 0."""

    def test_validate_handoff_exits_zero(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "algl_pdf_helper",
                "validate-handoff",
                str(OUTPUT_DIR),
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env={**__import__("os").environ, "PYTHONPATH": str(REPO_ROOT / "src")},
        )
        assert result.returncode == 0, (
            "validate-handoff exited with non-zero code.\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert "VALID" in result.stdout, (
            f"Expected 'VALID' in validate-handoff output:\n{result.stdout}"
        )


# ---------------------------------------------------------------------------
# Tier 3c — Fallback enrichment coverage regression checks
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _OUTPUT_EXISTS, reason="output/textbook-static not present — run build first")
class TestFallbackEnrichmentCoverage:
    """Regression checks for fallback enrichment coverage.

    These tests verify that the build-time coverage guarantees are met:
    - ≥80% of fallback_only concepts must have learnerSafeKeyPoints
    - ≥50% of fallback_only concepts (where exampleQuality != hidden) must have learnerSafeExamples
    """

    KEY_POINTS_THRESHOLD = 0.80
    EXAMPLES_THRESHOLD = 0.50

    def _load_units(self) -> list[dict]:
        """Load textbook units from output."""
        data = json.loads((OUTPUT_DIR / "textbook-units.json").read_text())
        return data.get("units", [])

    def test_key_points_coverage_threshold(self):
        """≥80% of fallback_only concepts must have learnerSafeKeyPoints."""
        units = self._load_units()
        fallback_units = [u for u in units if u.get("readabilityStatus") == "fallback_only"]

        if not fallback_units:
            pytest.skip("No fallback_only concepts found — coverage check not applicable")

        enriched = [u for u in fallback_units if u.get("learnerSafeKeyPoints")]
        coverage = len(enriched) / len(fallback_units)

        assert coverage >= self.KEY_POINTS_THRESHOLD, (
            f"Key points coverage {coverage:.1%} is below threshold {self.KEY_POINTS_THRESHOLD:.0%}. "
            f"Only {len(enriched)}/{len(fallback_units)} fallback_only concepts have learnerSafeKeyPoints. "
            "This is a build-quality regression — enrichment pipeline may be broken."
        )

    def test_examples_coverage_threshold(self):
        """≥50% of fallback_only concepts (where exampleQuality != hidden) must have learnerSafeExamples."""
        units = self._load_units()
        fallback_units = [u for u in units if u.get("readabilityStatus") == "fallback_only"]

        if not fallback_units:
            pytest.skip("No fallback_only concepts found — coverage check not applicable")

        # Only count fallback units where examples are expected (exampleQuality != hidden)
        fallback_with_examples_expected = [
            u for u in fallback_units
            if u.get("exampleQuality") != "hidden"
        ]

        if not fallback_with_examples_expected:
            pytest.skip("No fallback_only concepts with expected examples — coverage check not applicable")

        with_examples = [
            u for u in fallback_with_examples_expected
            if u.get("learnerSafeExamples")
        ]
        coverage = len(with_examples) / len(fallback_with_examples_expected)

        assert coverage >= self.EXAMPLES_THRESHOLD, (
            f"Examples coverage {coverage:.1%} is below threshold {self.EXAMPLES_THRESHOLD:.0%}. "
            f"Only {len(with_examples)}/{len(fallback_with_examples_expected)} fallback_only concepts "
            f"with exampleQuality != hidden have learnerSafeExamples. "
            "This is a build-quality regression — SQL extraction pipeline may be broken."
        )

    def test_all_fallback_have_learner_safe_summary(self):
        """Every fallback_only concept must have a learnerSafeSummary."""
        units = self._load_units()
        fallback_units = [u for u in units if u.get("readabilityStatus") == "fallback_only"]

        missing_summary = [u.get("unitId", "?") for u in fallback_units if not u.get("learnerSafeSummary")]

        assert not missing_summary, (
            f"{len(missing_summary)} fallback_only concepts missing learnerSafeSummary: "
            + ", ".join(missing_summary[:5])
        )

    def test_key_points_structure(self):
        """learnerSafeKeyPoints must be a non-empty list of strings when present."""
        units = self._load_units()
        fallback_units = [u for u in units if u.get("readabilityStatus") == "fallback_only"]

        bad_structure = []
        for u in fallback_units:
            kp = u.get("learnerSafeKeyPoints")
            if kp is not None:
                if not isinstance(kp, list) or not all(isinstance(item, str) for item in kp):
                    bad_structure.append(u.get("unitId", "?"))

        assert not bad_structure, (
            f"learnerSafeKeyPoints has invalid structure in units: " + ", ".join(bad_structure)
        )

    def test_examples_structure(self):
        """learnerSafeExamples must be a list of {title, sql} objects when present."""
        units = self._load_units()
        fallback_units = [u for u in units if u.get("readabilityStatus") == "fallback_only"]

        bad_structure = []
        for u in fallback_units:
            ex = u.get("learnerSafeExamples")
            if ex is not None:
                if not isinstance(ex, list):
                    bad_structure.append(f"{u.get('unitId', '?')}: not a list")
                    continue
                for item in ex:
                    if not isinstance(item, dict) or "sql" not in item:
                        bad_structure.append(f"{u.get('unitId', '?')}: missing 'sql' field")
                        break

        assert not bad_structure, (
            f"learnerSafeExamples has invalid structure: " + "; ".join(bad_structure[:5])
        )

    def test_concept_quality_index_has_enrichment_fields(self):
        """concept-quality.json must include enrichment fields for all entries."""
        cq = json.loads((OUTPUT_DIR / "concept-quality.json").read_text())
        quality_by_concept = cq.get("qualityByConcept", {})

        missing_fields = []
        for key, entry in quality_by_concept.items():
            if "learnerSafeKeyPoints" not in entry:
                missing_fields.append(f"{key}: missing learnerSafeKeyPoints")
            if "learnerSafeExamples" not in entry:
                missing_fields.append(f"{key}: missing learnerSafeExamples")

        assert not missing_fields, (
            f"concept-quality.json missing enrichment fields: " + "; ".join(missing_fields[:5])
        )
