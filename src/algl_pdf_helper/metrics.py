"""Offline metrics for evaluating PDF processing quality.

This module provides metrics for measuring:
- Concept coverage: How many expected concepts were found
- Retrieval sanity: Can we retrieve the right content for known queries
- Overall quality score: Combined quality metric
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import PdfIndexDocument, PdfIndexChunk, ConceptManifest


@dataclass
class CoverageMetric:
    """Measures concept coverage: concepts found / expected concepts."""
    
    expected_concepts: list[str]
    found_concepts: list[str] = field(default_factory=list)
    
    @property
    def coverage_ratio(self) -> float:
        """Ratio of found concepts to expected concepts."""
        if not self.expected_concepts:
            return 0.0
        found_count = len(set(self.found_concepts) & set(self.expected_concepts))
        return found_count / len(self.expected_concepts)
    
    @property
    def missing_concepts(self) -> list[str]:
        """List of expected concepts that were not found."""
        return [c for c in self.expected_concepts if c not in self.found_concepts]
    
    @property
    def extra_concepts(self) -> list[str]:
        """List of found concepts that were not expected."""
        return [c for c in self.found_concepts if c not in self.expected_concepts]
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_name": "coverage",
            "expected_count": len(self.expected_concepts),
            "found_count": len(self.found_concepts),
            "coverage_ratio": round(self.coverage_ratio, 4),
            "missing_concepts": self.missing_concepts,
            "extra_concepts": self.extra_concepts,
        }


@dataclass
class RetrievalSanityMetric:
    """Tests if known queries retrieve expected chunks/pages."""
    
    test_queries: list[dict[str, Any]] = field(default_factory=list)
    """Each query: {"query": str, "expected_page": int, "expected_chunk_id": str}"""
    
    results: list[dict[str, Any]] = field(default_factory=list)
    
    def run_tests(
        self,
        chunks: list[PdfIndexChunk],
        embedding_fn: callable,
        top_k: int = 5,
    ) -> None:
        """Run all retrieval tests using the provided embedding function."""
        self.results = []
        
        for test in self.test_queries:
            query = test["query"]
            expected_page = test.get("expected_page")
            expected_chunk_id = test.get("expected_chunk_id")
            
            # Get query embedding
            query_emb = embedding_fn(query)
            
            # Simple cosine similarity search
            scored_chunks = []
            for chunk in chunks:
                if chunk.embedding:
                    score = self._cosine_similarity(query_emb, chunk.embedding)
                    scored_chunks.append((score, chunk))
            
            # Sort by score
            scored_chunks.sort(reverse=True, key=lambda x: x[0])
            top_results = scored_chunks[:top_k]
            
            # Check if expected content is in results
            found_expected = False
            found_page = None
            found_chunk_id = None
            
            for score, chunk in top_results:
                if expected_page and chunk.page == expected_page:
                    found_expected = True
                    found_page = chunk.page
                if expected_chunk_id and chunk.chunkId == expected_chunk_id:
                    found_expected = True
                    found_chunk_id = chunk.chunkId
            
            self.results.append({
                "query": query,
                "expected_page": expected_page,
                "expected_chunk_id": expected_chunk_id,
                "found": found_expected,
                "top_score": round(top_results[0][0], 4) if top_results else 0,
                "retrieved_pages": [c.page for _, c in top_results],
            })
    
    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(a) != len(b) or not a:
            return 0.0
        
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    @property
    def success_rate(self) -> float:
        """Ratio of successful retrievals to total tests."""
        if not self.results:
            return 0.0
        successful = sum(1 for r in self.results if r["found"])
        return successful / len(self.results)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_name": "retrieval_sanity",
            "total_tests": len(self.test_queries),
            "passed_tests": sum(1 for r in self.results if r["found"]),
            "success_rate": round(self.success_rate, 4),
            "results": self.results,
        }


@dataclass
class QualityScore:
    """Overall quality score combining multiple factors."""
    
    coverage_score: float = 0.0  # 0-1
    retrieval_score: float = 0.0  # 0-1
    chunk_quality_score: float = 0.0  # 0-1
    
    # Weights for combining scores
    coverage_weight: float = 0.35
    retrieval_weight: float = 0.35
    chunk_quality_weight: float = 0.30
    
    @property
    def overall_score(self) -> float:
        """Weighted average of all quality scores."""
        return (
            self.coverage_score * self.coverage_weight +
            self.retrieval_score * self.retrieval_weight +
            self.chunk_quality_score * self.chunk_quality_weight
        )
    
    @property
    def grade(self) -> str:
        """Letter grade based on overall score."""
        score = self.overall_score
        if score >= 0.95:
            return "A+"
        elif score >= 0.90:
            return "A"
        elif score >= 0.85:
            return "A-"
        elif score >= 0.80:
            return "B+"
        elif score >= 0.75:
            return "B"
        elif score >= 0.70:
            return "B-"
        elif score >= 0.65:
            return "C+"
        elif score >= 0.60:
            return "C"
        else:
            return "F"
    
    @property
    def passes_threshold(self, threshold: float = 0.75) -> bool:
        """Check if score passes minimum threshold."""
        return self.overall_score >= threshold
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_name": "quality_score",
            "overall_score": round(self.overall_score, 4),
            "grade": self.grade,
            "components": {
                "coverage": {
                    "score": round(self.coverage_score, 4),
                    "weight": self.coverage_weight,
                },
                "retrieval": {
                    "score": round(self.retrieval_score, 4),
                    "weight": self.retrieval_weight,
                },
                "chunk_quality": {
                    "score": round(self.chunk_quality_score, 4),
                    "weight": self.chunk_quality_weight,
                },
            },
        }


@dataclass
class EvaluationReport:
    """Combined metrics report for a processed PDF."""
    
    document_id: str = ""
    evaluation_time: str = ""
    
    coverage: CoverageMetric | None = None
    retrieval: RetrievalSanityMetric | None = None
    quality: QualityScore | None = None
    
    # Additional metadata
    chunk_count: int = 0
    concept_count: int = 0
    page_count: int = 0
    
    def calculate_chunk_quality(self, chunks: list[PdfIndexChunk]) -> None:
        """Calculate chunk quality score based on various factors."""
        if not chunks:
            self.quality.chunk_quality_score = 0.0
            return
        
        scores = []
        
        for chunk in chunks:
            chunk_score = 1.0
            
            # Penalize very short chunks
            text_len = len(chunk.text)
            if text_len < 50:
                chunk_score *= 0.5
            elif text_len < 100:
                chunk_score *= 0.8
            
            # Penalize chunks without embeddings
            if not chunk.embedding:
                chunk_score *= 0.3
            
            # Penalize chunks with garbled text (simple heuristic)
            non_printable = sum(1 for c in chunk.text if ord(c) < 32 and c not in '\n\r\t')
            if text_len > 0 and non_printable / text_len > 0.1:
                chunk_score *= 0.5
            
            scores.append(chunk_score)
        
        self.quality.chunk_quality_score = sum(scores) / len(scores) if scores else 0.0
    
    def generate_summary(self) -> dict[str, Any]:
        """Generate a summary of the evaluation."""
        return {
            "document_id": self.document_id,
            "evaluation_time": self.evaluation_time,
            "overall_score": round(self.quality.overall_score, 4) if self.quality else 0.0,
            "grade": self.quality.grade if self.quality else "N/A",
            "metrics": {
                "coverage": self.coverage.to_dict() if self.coverage else None,
                "retrieval": self.retrieval.to_dict() if self.retrieval else None,
                "quality": self.quality.to_dict() if self.quality else None,
            },
            "metadata": {
                "chunk_count": self.chunk_count,
                "concept_count": self.concept_count,
                "page_count": self.page_count,
            },
        }
    
    def save(self, output_path: Path) -> None:
        """Save the evaluation report to a JSON file."""
        output_path.write_text(
            json.dumps(self.generate_summary(), indent=2) + "\n",
            encoding="utf-8",
        )
    
    @classmethod
    def load(cls, input_path: Path) -> "EvaluationReport":
        """Load an evaluation report from a JSON file."""
        data = json.loads(input_path.read_text(encoding="utf-8"))
        
        report = cls(
            document_id=data.get("document_id", ""),
            evaluation_time=data.get("evaluation_time", ""),
        )
        
        # Load coverage if present
        if data.get("metrics", {}).get("coverage"):
            cov_data = data["metrics"]["coverage"]
            report.coverage = CoverageMetric(
                expected_concepts=cov_data.get("expected_concepts", []),
                found_concepts=cov_data.get("found_concepts", []),
            )
        
        # Load retrieval if present
        if data.get("metrics", {}).get("retrieval"):
            ret_data = data["metrics"]["retrieval"]
            report.retrieval = RetrievalSanityMetric(
                test_queries=ret_data.get("test_queries", []),
                results=ret_data.get("results", []),
            )
        
        # Load quality score
        if data.get("metrics", {}).get("quality"):
            qual_data = data["metrics"]["quality"]
            comp = qual_data.get("components", {})
            report.quality = QualityScore(
                coverage_score=comp.get("coverage", {}).get("score", 0.0),
                retrieval_score=comp.get("retrieval", {}).get("score", 0.0),
                chunk_quality_score=comp.get("chunk_quality", {}).get("score", 0.0),
            )
        
        # Load metadata
        meta = data.get("metadata", {})
        report.chunk_count = meta.get("chunk_count", 0)
        report.concept_count = meta.get("concept_count", 0)
        report.page_count = meta.get("page_count", 0)
        
        return report


def run_evaluation(
    document: PdfIndexDocument,
    concept_manifest: ConceptManifest | None,
    expected_concepts: list[str],
    test_queries: list[dict[str, Any]],
    embedding_fn: callable,
) -> EvaluationReport:
    """Run a full evaluation on a processed document.
    
    Args:
        document: The processed PDF document
        concept_manifest: Concept manifest if concepts were generated
        expected_concepts: List of expected concept IDs
        test_queries: List of test queries for retrieval sanity
        embedding_fn: Function to generate embeddings
    
    Returns:
        EvaluationReport with all metrics
    """
    from datetime import datetime, timezone
    
    report = EvaluationReport(
        document_id=document.indexId,
        evaluation_time=datetime.now(timezone.utc).isoformat(),
        chunk_count=document.chunkCount,
        concept_count=len(concept_manifest.concepts) if concept_manifest else 0,
        page_count=sum(d.pageCount for d in document.sourceDocs),
    )
    
    # Coverage metric
    found_concepts = list(concept_manifest.concepts.keys()) if concept_manifest else []
    report.coverage = CoverageMetric(
        expected_concepts=expected_concepts,
        found_concepts=found_concepts,
    )
    
    # Retrieval sanity metric
    report.retrieval = RetrievalSanityMetric(test_queries=test_queries)
    report.retrieval.run_tests(document.chunks, embedding_fn)
    
    # Quality score
    report.quality = QualityScore(
        coverage_score=report.coverage.coverage_ratio,
        retrieval_score=report.retrieval.success_rate,
    )
    report.calculate_chunk_quality(document.chunks)
    
    return report
