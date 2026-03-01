from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .mapping_generator import DraftMapping, MappingGenerator
from .structure_extractor import StructureExtractor


@dataclass
class ReviewSuggestion:
    """A suggestion for review."""
    type: str  # 'page_correction', 'section_split', 'concept_merge', 'add_concept'
    description: str
    current_value: Any
    suggested_value: Any
    confidence: float = 0.5
    reasoning: str = ""


@dataclass
class ReviewPackage:
    """Complete review package for human-in-the-loop workflow."""
    package_id: str
    created_at: str
    pdf_path: str
    pdf_name: str
    total_pages: int
    draft_mapping: dict[str, Any]
    suggestions: list[ReviewSuggestion]
    preview: dict[str, Any]
    statistics: dict[str, Any]
    export_ready: bool = False


class MappingWorkflow:
    """Human-in-the-loop workflow for concept mapping review."""

    def __init__(
        self,
        registry_path: Path | None = None,
        confidence_threshold: float = 0.5
    ):
        """Initialize the mapping workflow.

        Args:
            registry_path: Path to concept registry
            confidence_threshold: Minimum confidence for automatic acceptance
        """
        self.generator = MappingGenerator(
            registry_path=registry_path,
            confidence_threshold=confidence_threshold
        )
        self.structure_extractor = StructureExtractor()
        self.confidence_threshold = confidence_threshold

    def create_review_package(
        self,
        draft_mapping: DraftMapping,
        include_previews: bool = True
    ) -> ReviewPackage:
        """Create a review package from a draft mapping.

        Args:
            draft_mapping: The draft mapping to review
            include_previews: Whether to include preview of generated content

        Returns:
            ReviewPackage with all review information
        """
        package_id = f"review-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

        # Generate suggestions
        suggestions = self._generate_suggestions(draft_mapping)

        # Create preview of what will be generated
        preview = {}
        if include_previews:
            preview = self._create_preview(draft_mapping)

        # Calculate statistics
        statistics = self.generator.get_mapping_summary(draft_mapping)

        # Check if export-ready
        export_ready = all(
            not c.needs_review or c.confidence >= 0.4
            for c in draft_mapping.concepts
        )

        return ReviewPackage(
            package_id=package_id,
            created_at=datetime.now(timezone.utc).isoformat() + "Z",
            pdf_path=str(draft_mapping.pdf_path),
            pdf_name=draft_mapping.pdf_path.name,
            total_pages=draft_mapping.total_pages,
            draft_mapping=self._draft_to_dict(draft_mapping),
            suggestions=suggestions,
            preview=preview,
            statistics=statistics,
            export_ready=export_ready
        )

    def _draft_to_dict(self, draft: DraftMapping) -> dict[str, Any]:
        """Convert draft mapping to dictionary format."""
        return {
            'concepts': [
                {
                    'id': c.concept_id,
                    'title': c.title,
                    'definition': c.definition,
                    'difficulty': c.difficulty,
                    'page_references': c.page_references,
                    'sections': c.sections,
                    'related_concepts': c.related_concepts,
                    'tags': c.tags,
                    'source_heading': c.source_heading,
                    'confidence': round(c.confidence, 3),
                    'match_score': round(c.match_score, 3),
                    'match_type': c.match_type,
                    'needs_review': c.needs_review,
                    'review_notes': c.review_notes,
                }
                for c in draft.concepts
            ],
            'unmatched_headings': [
                {
                    'text': h.text,
                    'page': h.page,
                    'level': h.level,
                    'confidence': round(h.confidence, 3),
                }
                for h in draft.unmatched_headings[:20]  # Limit to first 20
            ],
            'suggested_additions': [
                {
                    'id': c.concept_id,
                    'name': c.concept_name,
                    'match_type': c.match_type,
                    'reason': 'Related to matched concepts',
                }
                for c in draft.suggested_additions[:10]
            ],
        }

    def _generate_suggestions(self, draft: DraftMapping) -> list[ReviewSuggestion]:
        """Generate review suggestions based on the draft mapping."""
        suggestions = []

        # 1. Suggest page corrections for low confidence mappings
        for concept in draft.concepts:
            if concept.confidence < 0.6 and concept.page_references:
                suggestions.append(ReviewSuggestion(
                    type='page_correction',
                    description=f"Verify page numbers for '{concept.title}'",
                    current_value=concept.page_references,
                    suggested_value=concept.page_references[:1],  # Suggest just first page
                    confidence=concept.confidence,
                    reasoning=f"Low confidence match ({concept.confidence:.2f}). "
                              f"Pages may need manual verification."
                ))

        # 2. Suggest section splits for long page ranges
        for concept in draft.concepts:
            if len(concept.page_references) > 5:
                mid = len(concept.page_references) // 2
                suggestions.append(ReviewSuggestion(
                    type='section_split',
                    description=f"Consider splitting '{concept.title}' into sections",
                    current_value={'definition': concept.page_references},
                    suggested_value={
                        'definition': concept.page_references[:2],
                        'examples': concept.page_references[2:mid+2],
                        'advanced': concept.page_references[mid+2:] if len(concept.page_references) > mid + 2 else []
                    },
                    confidence=0.6,
                    reasoning=f"Long page range ({len(concept.page_references)} pages). "
                              f"Consider splitting into definition, examples, and advanced sections."
                ))

        # 3. Suggest concept merges for similar headings on same page
        concepts_by_page: dict[int, list] = {}
        for concept in draft.concepts:
            if concept.page_references:
                page = concept.page_references[0]
                if page not in concepts_by_page:
                    concepts_by_page[page] = []
                concepts_by_page[page].append(concept)

        for page, concepts in concepts_by_page.items():
            if len(concepts) > 1:
                concept_names = [c.title for c in concepts]
                suggestions.append(ReviewSuggestion(
                    type='concept_merge',
                    description=f"Multiple concepts detected on page {page}",
                    current_value=concept_names,
                    suggested_value=f"Consider if these should be combined: {', '.join(concept_names)}",
                    confidence=0.5,
                    reasoning=f"Found {len(concepts)} concepts starting on the same page. "
                              f"They may be subsections of a larger concept."
                ))

        # 4. Suggest adding unmatched concepts
        if draft.unmatched_headings:
            significant_unmatched = [
                h for h in draft.unmatched_headings
                if h.level <= 2 and h.confidence > 0.5
            ][:5]

            if significant_unmatched:
                headings_list = [h.text for h in significant_unmatched]
                suggestions.append(ReviewSuggestion(
                    type='add_concept',
                    description="Unmatched headings may need manual concept creation",
                    current_value=f"{len(draft.unmatched_headings)} unmatched headings",
                    suggested_value=headings_list,
                    confidence=0.4,
                    reasoning="These headings didn't match any concepts in the registry. "
                              f"Consider adding custom concepts for: {', '.join(headings_list[:3])}"
                ))

        return suggestions

    def _create_preview(self, draft: DraftMapping) -> dict[str, Any]:
        """Create a preview of what will be generated."""
        concepts_preview = []

        for concept in draft.concepts[:5]:  # Preview first 5 concepts
            preview = {
                'id': concept.concept_id,
                'title': concept.title,
                'pages': concept.page_references,
                'difficulty': concept.difficulty,
                'estimated_content': self._estimate_content(concept),
            }
            concepts_preview.append(preview)

        return {
            'total_concepts': len(draft.concepts),
            'concepts_preview': concepts_preview,
            'output_files': [
                'concept-manifest.json',
                'concepts/README.md',
                f'concepts/{draft.pdf_path.stem}/*.md',
            ],
            'estimated_processing_time': f"{len(draft.concepts) * 2} minutes",
        }

    def _estimate_content(self, concept) -> dict[str, Any]:
        """Estimate content that will be generated for a concept."""
        num_pages = len(concept.page_references)

        return {
            'chunks_estimate': num_pages * 3,  # Rough estimate: 3 chunks per page
            'has_definition': bool(concept.definition),
            'sections_count': len(concept.sections),
            'related_concepts_count': len(concept.related_concepts),
        }

    def export_review_package(
        self,
        package: ReviewPackage,
        output_path: Path
    ) -> Path:
        """Export review package to JSON file.

        Args:
            package: The review package to export
            output_path: Where to write the file

        Returns:
            Path to the written file
        """
        data = {
            'package_id': package.package_id,
            'created_at': package.created_at,
            'pdf_path': package.pdf_path,
            'pdf_name': package.pdf_name,
            'total_pages': package.total_pages,
            'draft_mapping': package.draft_mapping,
            'suggestions': [
                {
                    'type': s.type,
                    'description': s.description,
                    'current_value': s.current_value,
                    'suggested_value': s.suggested_value,
                    'confidence': s.confidence,
                    'reasoning': s.reasoning,
                }
                for s in package.suggestions
            ],
            'preview': package.preview,
            'statistics': package.statistics,
            'export_ready': package.export_ready,
            'review_instructions': self._get_review_instructions(),
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return output_path

    def _get_review_instructions(self) -> list[str]:
        """Get instructions for reviewing the package."""
        return [
            "1. Review each concept's page_references - ensure they match the actual content",
            "2. Check concepts marked with 'needs_review': true - these have low confidence",
            "3. Adjust section mappings if needed (definition, examples, commonMistakes, etc.)",
            "4. Add any missing concepts from 'suggested_additions' or 'unmatched_headings'",
            "5. Remove any incorrect matches",
            "6. When satisfied, save the edited file as 'concepts.yaml' and run the indexer",
        ]

    def apply_review_edits(
        self,
        review_package_path: Path,
        edits: dict[str, Any]
    ) -> dict[str, Any]:
        """Apply review edits to a review package.

        Args:
            review_package_path: Path to the review package JSON
            edits: Dictionary of edits to apply

        Returns:
            Updated draft mapping
        """
        with open(review_package_path, 'r', encoding='utf-8') as f:
            package_data = json.load(f)

        draft = package_data['draft_mapping']

        # Apply concept updates
        if 'concept_updates' in edits:
            for update in edits['concept_updates']:
                concept_id = update.get('id')
                for concept in draft['concepts']:
                    if concept['id'] == concept_id:
                        concept.update(update.get('changes', {}))
                        concept['needs_review'] = False
                        concept['review_notes'] = 'Manually verified'

        # Apply concept removals
        if 'remove_concepts' in edits:
            remove_ids = set(edits['remove_concepts'])
            draft['concepts'] = [
                c for c in draft['concepts']
                if c['id'] not in remove_ids
            ]

        # Apply concept additions
        if 'add_concepts' in edits:
            for new_concept in edits['add_concepts']:
                new_concept['needs_review'] = False
                new_concept['review_notes'] = 'Manually added'
                draft['concepts'].append(new_concept)

        # Update statistics
        package_data['statistics']['matched_concepts'] = len(draft['concepts'])
        package_data['statistics']['needs_review'] = sum(
            1 for c in draft['concepts'] if c.get('needs_review')
        )

        return draft

    def generate_workflow_report(
        self,
        draft: DraftMapping,
        reviewed_concepts: list[dict] | None = None
    ) -> dict[str, Any]:
        """Generate a workflow completion report.

        Args:
            draft: The original draft mapping
            reviewed_concepts: Optional list of reviewed concepts

        Returns:
            Report statistics
        """
        reviewed = reviewed_concepts or []

        original_ids = {c.concept_id for c in draft.concepts}
        reviewed_ids = {c['id'] for c in reviewed}

        return {
            'workflow_completed_at': datetime.now(timezone.utc).isoformat() + "Z",
            'original_draft': {
                'total_concepts': len(draft.concepts),
                'needs_review': sum(1 for c in draft.concepts if c.needs_review),
                'high_confidence': sum(1 for c in draft.concepts if c.confidence >= 0.8),
            },
            'after_review': {
                'total_concepts': len(reviewed),
                'accepted_from_draft': len(original_ids & reviewed_ids),
                'removed': len(original_ids - reviewed_ids),
                'added': len(reviewed_ids - original_ids),
            },
            'time_saved_estimate': f"{len(draft.concepts) * 10} minutes",
            'accuracy_estimate': self._estimate_accuracy(draft, reviewed),
        }

    def _estimate_accuracy(
        self,
        draft: DraftMapping,
        reviewed: list[dict]
    ) -> str:
        """Estimate mapping accuracy after review."""
        if not reviewed:
            # Estimate based on draft confidence scores
            high_conf = sum(1 for c in draft.concepts if c.confidence >= 0.7)
            total = len(draft.concepts)
            if total > 0:
                return f"{((high_conf / total) * 100):.0f}% (estimated)"
            return "N/A"

        # Calculate based on changes made
        original_pages = {
            c.concept_id: set(c.page_references)
            for c in draft.concepts
        }

        unchanged = 0
        for r in reviewed:
            rid = r['id']
            if rid in original_pages:
                original = original_pages[rid]
                current = set(r.get('page_references', []))
                if original == current:
                    unchanged += 1

        if reviewed:
            accuracy = (unchanged / len(reviewed)) * 100
            return f"{accuracy:.0f}%"

        return "N/A"
