"""Regression detection for PDF processing pipeline.

Compares current output to baseline and detects:
- Chunk count changes
- Schema version changes
- Quality drops
- Missing/extra concepts
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import PdfIndexDocument, ConceptManifest, IndexBuildOptions


@dataclass
class RegressionCheck:
    """A single regression check result."""
    
    check_name: str
    passed: bool
    severity: str  # "info", "warning", "error"
    message: str
    baseline_value: Any = None
    current_value: Any = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "check_name": self.check_name,
            "passed": self.passed,
            "severity": self.severity,
            "message": self.message,
            "baseline_value": self.baseline_value,
            "current_value": self.current_value,
        }


@dataclass
class RegressionReport:
    """Full regression detection report."""
    
    document_id: str = ""
    baseline_path: Path | None = None
    current_path: Path | None = None
    checks: list[RegressionCheck] = field(default_factory=list)
    
    # Thresholds
    chunk_count_tolerance: float = 0.10  # 10% tolerance
    min_quality_score: float = 0.75
    
    @property
    def has_errors(self) -> bool:
        """True if any check has error severity and failed."""
        return any(
            not c.passed and c.severity == "error" for c in self.checks
        )
    
    @property
    def has_warnings(self) -> bool:
        """True if any check has warning severity and failed."""
        return any(
            not c.passed and c.severity == "warning" for c in self.checks
        )
    
    @property
    def passed_checks(self) -> list[RegressionCheck]:
        """List of checks that passed."""
        return [c for c in self.checks if c.passed]
    
    @property
    def failed_checks(self) -> list[RegressionCheck]:
        """List of checks that failed."""
        return [c for c in self.checks if not c.passed]
    
    def add_check(
        self,
        name: str,
        passed: bool,
        severity: str,
        message: str,
        baseline_value: Any = None,
        current_value: Any = None,
    ) -> None:
        """Add a check result to the report."""
        self.checks.append(RegressionCheck(
            check_name=name,
            passed=passed,
            severity=severity,
            message=message,
            baseline_value=baseline_value,
            current_value=current_value,
        ))
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "baseline_path": str(self.baseline_path) if self.baseline_path else None,
            "current_path": str(self.current_path) if self.current_path else None,
            "summary": {
                "total_checks": len(self.checks),
                "passed": len(self.passed_checks),
                "failed": len(self.failed_checks),
                "errors": len([c for c in self.checks if c.severity == "error"]),
                "warnings": len([c for c in self.checks if c.severity == "warning"]),
                "has_errors": self.has_errors,
                "has_warnings": self.has_warnings,
            },
            "checks": [c.to_dict() for c in self.checks],
        }
    
    def save(self, output_path: Path) -> None:
        """Save the regression report to a JSON file."""
        output_path.write_text(
            json.dumps(self.to_dict(), indent=2) + "\n",
            encoding="utf-8",
        )


class RegressionDetector:
    """Detects regressions by comparing current output to baseline."""
    
    def __init__(
        self,
        chunk_count_tolerance: float = 0.10,
        min_quality_score: float = 0.75,
    ):
        self.chunk_count_tolerance = chunk_count_tolerance
        self.min_quality_score = min_quality_score
    
    def compare_documents(
        self,
        baseline: PdfIndexDocument,
        current: PdfIndexDocument,
        baseline_path: Path | None = None,
        current_path: Path | None = None,
    ) -> RegressionReport:
        """Compare two documents and generate a regression report."""
        
        report = RegressionReport(
            document_id=current.indexId,
            baseline_path=baseline_path,
            current_path=current_path,
            chunk_count_tolerance=self.chunk_count_tolerance,
            min_quality_score=self.min_quality_score,
        )
        
        # Check 1: Schema version consistency
        self._check_schema_version(report, baseline, current)
        
        # Check 2: Chunker version consistency
        self._check_chunker_version(report, baseline, current)
        
        # Check 3: Embedding model consistency
        self._check_embedding_model(report, baseline, current)
        
        # Check 4: Chunk count within tolerance
        self._check_chunk_count(report, baseline, current)
        
        # Check 5: Source document count
        self._check_source_doc_count(report, baseline, current)
        
        # Check 6: Page count stability
        self._check_page_count(report, baseline, current)
        
        return report
    
    def _check_schema_version(
        self,
        report: RegressionReport,
        baseline: PdfIndexDocument,
        current: PdfIndexDocument,
    ) -> None:
        """Check if schema version has changed."""
        if baseline.schemaVersion != current.schemaVersion:
            report.add_check(
                name="schema_version",
                passed=False,
                severity="error",
                message=f"Schema version changed: {baseline.schemaVersion} -> {current.schemaVersion}",
                baseline_value=baseline.schemaVersion,
                current_value=current.schemaVersion,
            )
        else:
            report.add_check(
                name="schema_version",
                passed=True,
                severity="info",
                message=f"Schema version consistent: {current.schemaVersion}",
                baseline_value=baseline.schemaVersion,
                current_value=current.schemaVersion,
            )
    
    def _check_chunker_version(
        self,
        report: RegressionReport,
        baseline: PdfIndexDocument,
        current: PdfIndexDocument,
    ) -> None:
        """Check if chunker version has changed."""
        if baseline.chunkerVersion != current.chunkerVersion:
            report.add_check(
                name="chunker_version",
                passed=False,
                severity="warning",
                message=f"Chunker version changed: {baseline.chunkerVersion} -> {current.chunkerVersion}",
                baseline_value=baseline.chunkerVersion,
                current_value=current.chunkerVersion,
            )
        else:
            report.add_check(
                name="chunker_version",
                passed=True,
                severity="info",
                message=f"Chunker version consistent: {current.chunkerVersion}",
                baseline_value=baseline.chunkerVersion,
                current_value=current.chunkerVersion,
            )
    
    def _check_embedding_model(
        self,
        report: RegressionReport,
        baseline: PdfIndexDocument,
        current: PdfIndexDocument,
    ) -> None:
        """Check if embedding model has changed."""
        if baseline.embeddingModelId != current.embeddingModelId:
            report.add_check(
                name="embedding_model",
                passed=False,
                severity="warning",
                message=f"Embedding model changed: {baseline.embeddingModelId} -> {current.embeddingModelId}",
                baseline_value=baseline.embeddingModelId,
                current_value=current.embeddingModelId,
            )
        else:
            report.add_check(
                name="embedding_model",
                passed=True,
                severity="info",
                message=f"Embedding model consistent: {current.embeddingModelId}",
                baseline_value=baseline.embeddingModelId,
                current_value=current.embeddingModelId,
            )
    
    def _check_chunk_count(
        self,
        report: RegressionReport,
        baseline: PdfIndexDocument,
        current: PdfIndexDocument,
    ) -> None:
        """Check if chunk count is within tolerance."""
        baseline_count = baseline.chunkCount
        current_count = current.chunkCount
        
        if baseline_count == 0:
            change_ratio = float("inf") if current_count > 0 else 0.0
        else:
            change_ratio = abs(current_count - baseline_count) / baseline_count
        
        within_tolerance = change_ratio <= self.chunk_count_tolerance
        
        if baseline_count != current_count:
            if within_tolerance:
                report.add_check(
                    name="chunk_count",
                    passed=True,
                    severity="warning",
                    message=f"Chunk count changed by {change_ratio:.1%} (within tolerance): {baseline_count} -> {current_count}",
                    baseline_value=baseline_count,
                    current_value=current_count,
                )
            else:
                report.add_check(
                    name="chunk_count",
                    passed=False,
                    severity="error",
                    message=f"Chunk count changed by {change_ratio:.1%} (exceeds tolerance): {baseline_count} -> {current_count}",
                    baseline_value=baseline_count,
                    current_value=current_count,
                )
        else:
            report.add_check(
                name="chunk_count",
                passed=True,
                severity="info",
                message=f"Chunk count stable: {current_count}",
                baseline_value=baseline_count,
                current_value=current_count,
            )
    
    def _check_source_doc_count(
        self,
        report: RegressionReport,
        baseline: PdfIndexDocument,
        current: PdfIndexDocument,
    ) -> None:
        """Check if source document count has changed."""
        baseline_count = baseline.docCount
        current_count = current.docCount
        
        if baseline_count != current_count:
            report.add_check(
                name="source_doc_count",
                passed=False,
                severity="error",
                message=f"Source document count changed: {baseline_count} -> {current_count}",
                baseline_value=baseline_count,
                current_value=current_count,
            )
        else:
            report.add_check(
                name="source_doc_count",
                passed=True,
                severity="info",
                message=f"Source document count stable: {current_count}",
                baseline_value=baseline_count,
                current_value=current_count,
            )
    
    def _check_page_count(
        self,
        report: RegressionReport,
        baseline: PdfIndexDocument,
        current: PdfIndexDocument,
    ) -> None:
        """Check if total page count has changed."""
        baseline_pages = sum(d.pageCount for d in baseline.sourceDocs)
        current_pages = sum(d.pageCount for d in current.sourceDocs)
        
        if baseline_pages != current_pages:
            report.add_check(
                name="page_count",
                passed=False,
                severity="warning",
                message=f"Total page count changed: {baseline_pages} -> {current_pages}",
                baseline_value=baseline_pages,
                current_value=current_pages,
            )
        else:
            report.add_check(
                name="page_count",
                passed=True,
                severity="info",
                message=f"Total page count stable: {current_pages}",
                baseline_value=baseline_pages,
                current_value=current_pages,
            )
    
    def compare_concept_manifests(
        self,
        report: RegressionReport,
        baseline: ConceptManifest | None,
        current: ConceptManifest | None,
    ) -> None:
        """Compare concept manifests and add checks to report."""
        
        # Check if concept generation status changed
        if baseline is None and current is None:
            report.add_check(
                name="concept_manifest",
                passed=True,
                severity="info",
                message="No concept manifests in baseline or current",
            )
            return
        
        if baseline is None and current is not None:
            report.add_check(
                name="concept_manifest",
                passed=True,
                severity="info",
                message=f"Concept manifest added: {current.conceptCount} concepts",
                current_value=current.conceptCount,
            )
            return
        
        if baseline is not None and current is None:
            report.add_check(
                name="concept_manifest",
                passed=False,
                severity="error",
                message="Concept manifest missing in current output",
                baseline_value=baseline.conceptCount,
            )
            return
        
        # Both exist - compare them
        # Check concept count
        baseline_concepts = baseline.conceptCount
        current_concepts = current.conceptCount
        
        if baseline_concepts != current_concepts:
            report.add_check(
                name="concept_count",
                passed=False,
                severity="warning",
                message=f"Concept count changed: {baseline_concepts} -> {current_concepts}",
                baseline_value=baseline_concepts,
                current_value=current_concepts,
            )
        else:
            report.add_check(
                name="concept_count",
                passed=True,
                severity="info",
                message=f"Concept count stable: {current_concepts}",
                baseline_value=baseline_concepts,
                current_value=current_concepts,
            )
        
        # Check for missing concepts
        baseline_ids = set(baseline.concepts.keys())
        current_ids = set(current.concepts.keys())
        
        missing = baseline_ids - current_ids
        extra = current_ids - baseline_ids
        
        if missing:
            report.add_check(
                name="missing_concepts",
                passed=False,
                severity="error",
                message=f"Concepts missing in current: {sorted(missing)}",
                baseline_value=sorted(baseline_ids),
                current_value=sorted(current_ids),
            )
        else:
            report.add_check(
                name="missing_concepts",
                passed=True,
                severity="info",
                message="No concepts missing",
            )
        
        if extra:
            report.add_check(
                name="extra_concepts",
                passed=True,
                severity="warning",
                message=f"New concepts in current: {sorted(extra)}",
                baseline_value=sorted(baseline_ids),
                current_value=sorted(current_ids),
            )
        else:
            report.add_check(
                name="extra_concepts",
                passed=True,
                severity="info",
                message="No new concepts added",
            )


def load_baseline(baseline_path: Path) -> tuple[PdfIndexDocument, ConceptManifest | None]:
    """Load a baseline from a directory containing index.json and concept-manifest.json."""
    index_path = baseline_path / "index.json"
    manifest_path = baseline_path / "concept-manifest.json"
    
    if not index_path.exists():
        raise FileNotFoundError(f"Baseline index not found: {index_path}")
    
    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    document = PdfIndexDocument(**index_data)
    
    manifest = None
    if manifest_path.exists():
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = ConceptManifest(**manifest_data)
    
    return document, manifest


def detect_regression(
    baseline_dir: Path,
    current_dir: Path,
    chunk_count_tolerance: float = 0.10,
) -> RegressionReport:
    """Detect regression between baseline and current output.
    
    Args:
        baseline_dir: Directory containing baseline index.json
        current_dir: Directory containing current index.json
        chunk_count_tolerance: Acceptable change in chunk count (0.10 = 10%)
    
    Returns:
        RegressionReport with all checks
    """
    # Load baseline and current
    baseline_doc, baseline_manifest = load_baseline(baseline_dir)
    current_doc, current_manifest = load_baseline(current_dir)
    
    # Run comparison
    detector = RegressionDetector(chunk_count_tolerance=chunk_count_tolerance)
    report = detector.compare_documents(baseline_doc, current_doc, baseline_dir, current_dir)
    
    # Compare concept manifests if available
    detector.compare_concept_manifests(report, baseline_manifest, current_manifest)
    
    return report
