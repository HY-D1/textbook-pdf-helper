from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .concept_matcher import ConceptMatcher, MatchCandidate
from .structure_extractor import Heading, StructureExtractor


@dataclass
class ConceptMapping:
    """A single concept mapping entry."""
    concept_id: str
    concept_name: str
    title: str
    definition: str = ""
    difficulty: str = "beginner"
    estimated_read_time: int = 5
    page_references: list[int] = field(default_factory=list)
    sections: dict[str, list[int]] = field(default_factory=dict)
    related_concepts: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    source_heading: str = ""
    confidence: float = 0.0
    match_score: float = 0.0
    match_type: str = ""
    needs_review: bool = False
    review_notes: str = ""


@dataclass
class DraftMapping:
    """Complete draft mapping for a PDF."""
    pdf_path: Path
    created_at: str
    total_pages: int
    detected_headings: int
    matched_concepts: int
    concepts: list[ConceptMapping] = field(default_factory=list)
    unmatched_headings: list[Heading] = field(default_factory=list)
    suggested_additions: list[MatchCandidate] = field(default_factory=list)

    def to_concepts_yaml(self) -> dict[str, Any]:
        """Convert to concepts.yaml format."""
        concepts_dict = {}

        for mapping in self.concepts:
            concept_entry = {
                'title': mapping.title,
                'definition': mapping.definition,
                'difficulty': mapping.difficulty,
                'estimatedReadTime': mapping.estimated_read_time,
                'sections': {},
                'relatedConcepts': mapping.related_concepts,
                'tags': mapping.tags,
                '_mapping_metadata': {
                    'confidence': round(mapping.confidence, 2),
                    'match_score': round(mapping.match_score, 2),
                    'match_type': mapping.match_type,
                    'needs_review': mapping.needs_review,
                    'review_notes': mapping.review_notes,
                }
            }

            # Add page references to sections
            if mapping.page_references:
                concept_entry['sections']['definition'] = mapping.page_references[:1]
                if len(mapping.page_references) > 1:
                    concept_entry['sections']['examples'] = mapping.page_references[1:3]

            # Add any specific sections
            for section_name, pages in mapping.sections.items():
                if section_name not in concept_entry['sections']:
                    concept_entry['sections'][section_name] = pages

            concepts_dict[mapping.concept_id] = concept_entry

        return {
            'version': '1.0',
            'generated_at': self.created_at,
            'source_pdf': str(self.pdf_path),
            'total_pages': self.total_pages,
            'concepts': concepts_dict,
            '_generation_stats': {
                'total_pages': self.total_pages,
                'detected_headings': self.detected_headings,
                'matched_concepts': self.matched_concepts,
            }
        }


class MappingGenerator:
    """Generate draft concept mappings from PDF structure."""

    def __init__(
        self,
        registry_path: Path | None = None,
        confidence_threshold: float = 0.5,
        max_concepts: int | None = None
    ):
        """Initialize the mapping generator.

        Args:
            registry_path: Path to concept registry
            confidence_threshold: Minimum confidence for automatic acceptance
            max_concepts: Maximum number of concepts to generate
        """
        self.structure_extractor = StructureExtractor()
        self.concept_matcher = ConceptMatcher(registry_path)
        self.confidence_threshold = confidence_threshold
        self.max_concepts = max_concepts

    def generate_draft_mapping(
        self,
        pdf_path: Path,
        concept_registry: Path | None = None
    ) -> DraftMapping:
        """Generate a draft concept mapping from a PDF.

        Args:
            pdf_path: Path to the PDF file
            concept_registry: Optional custom registry path

        Returns:
            DraftMapping with concepts, pages, and confidence scores
        """
        # Use custom registry if provided
        if concept_registry:
            self.concept_matcher = ConceptMatcher(concept_registry)

        # Extract structure
        headings = self.structure_extractor.extract_headings(pdf_path)
        total_pages = self.structure_extractor.get_structure_summary(pdf_path)['total_pages']

        # Match headings to concepts
        matched_candidates = self.concept_matcher.match_headings_batch(
            headings,
            confidence_threshold=0.3  # Lower threshold to catch more possibilities
        )

        # Group candidates by concept (keep best match for each concept)
        concept_candidates: dict[str, list[tuple[MatchCandidate, Heading]]] = {}
        unmatched = []

        for heading in headings:
            heading_candidates = [
                c for c in matched_candidates
                if c.heading_text == heading.text and c.heading_page == heading.page
            ]

            if heading_candidates:
                best = max(heading_candidates, key=lambda c: c.confidence)
                if best.concept_id not in concept_candidates:
                    concept_candidates[best.concept_id] = []
                concept_candidates[best.concept_id].append((best, heading))
            else:
                unmatched.append(heading)

        # Build concept mappings
        concepts = []
        for concept_id, candidate_list in concept_candidates.items():
            # Sort by confidence and take best
            candidate_list.sort(key=lambda x: x[0].confidence, reverse=True)
            best_candidate, best_heading = candidate_list[0]

            # Get concept details from registry
            registry_entry = self.concept_matcher.registry.get(concept_id)
            if not registry_entry:
                continue

            # Determine page range
            pages = self._estimate_page_range(best_heading, headings, total_pages)

            # Build sections mapping
            sections = self._build_sections(candidate_list, headings, total_pages)

            # Determine if needs review
            needs_review = best_candidate.confidence < self.confidence_threshold

            # Generate review notes
            review_notes = []
            if needs_review:
                review_notes.append(f"Low confidence ({best_candidate.confidence:.2f})")
            if len(candidate_list) > 1:
                review_notes.append(f"Multiple headings matched ({len(candidate_list)})")
            if not pages:
                review_notes.append("No page range detected")

            mapping = ConceptMapping(
                concept_id=concept_id,
                concept_name=registry_entry.name,
                title=registry_entry.name,
                definition=registry_entry.definition,
                difficulty=registry_entry.difficulty,
                estimated_read_time=self._estimate_read_time(len(pages)),
                page_references=pages,
                sections=sections,
                related_concepts=registry_entry.related_concepts,
                tags=self._generate_tags(registry_entry),
                source_heading=best_heading.text,
                confidence=best_candidate.confidence,
                match_score=best_candidate.match_score,
                match_type=best_candidate.match_type,
                needs_review=needs_review,
                review_notes="; ".join(review_notes) if review_notes else ""
            )

            concepts.append(mapping)

        # Sort by confidence
        concepts.sort(key=lambda c: c.confidence, reverse=True)

        # Apply max concepts limit
        if self.max_concepts and len(concepts) > self.max_concepts:
            concepts = concepts[:self.max_concepts]

        # Find suggested additions (related concepts not yet matched)
        matched_ids = [c.concept_id for c in concepts]
        suggested_additions = self.concept_matcher.find_related_matches(matched_ids)

        return DraftMapping(
            pdf_path=pdf_path,
            created_at=datetime.utcnow().isoformat() + "Z",
            total_pages=total_pages,
            detected_headings=len(headings),
            matched_concepts=len(concepts),
            concepts=concepts,
            unmatched_headings=unmatched,
            suggested_additions=suggested_additions
        )

    def _estimate_page_range(
        self,
        heading: Heading,
        all_headings: list[Heading],
        total_pages: int
    ) -> list[int]:
        """Estimate the page range for a concept based on heading position."""
        # Find next heading at same or higher level
        start_page = heading.page
        end_page = total_pages

        heading_index = None
        for i, h in enumerate(all_headings):
            if h.text == heading.text and h.page == heading.page:
                heading_index = i
                break

        if heading_index is not None:
            for h in all_headings[heading_index + 1:]:
                if h.level <= heading.level:
                    end_page = h.page - 1
                    break

        # Limit range to reasonable size
        end_page = min(end_page, start_page + 10)

        return list(range(start_page, end_page + 1))

    def _build_sections(
        self,
        candidate_list: list[tuple[MatchCandidate, Heading]],
        all_headings: list[Heading],
        total_pages: int
    ) -> dict[str, list[int]]:
        """Build sections mapping for a concept."""
        sections = {}

        # Sort candidates by page
        sorted_candidates = sorted(candidate_list, key=lambda x: x[1].page)

        if sorted_candidates:
            # First heading is definition
            first_heading = sorted_candidates[0][1]
            sections['definition'] = self._estimate_page_range(
                first_heading, all_headings, total_pages
            )[:1]

            # Remaining headings might be examples or other sections
            if len(sorted_candidates) > 1:
                example_pages = []
                for _, heading in sorted_candidates[1:3]:  # Take next 2
                    example_pages.extend(
                        self._estimate_page_range(heading, all_headings, total_pages)[:1]
                    )
                if example_pages:
                    sections['examples'] = list(set(example_pages))

        return sections

    def _estimate_read_time(self, num_pages: int) -> int:
        """Estimate reading time in minutes based on pages."""
        # Rough estimate: 2-3 minutes per page for technical content
        minutes = max(3, num_pages * 2)
        return min(minutes, 30)  # Cap at 30 minutes

    def _generate_tags(self, registry_entry) -> list[str]:
        """Generate tags for a concept."""
        tags = []

        if registry_entry.category:
            tags.append(registry_entry.category.lower())

        if registry_entry.difficulty:
            tags.append(registry_entry.difficulty.lower())

        # Add SQL-specific tags
        if 'select' in registry_entry.id or 'query' in registry_entry.name.lower():
            tags.append('query')
        if 'join' in registry_entry.id:
            tags.append('join')
        if 'aggregate' in registry_entry.id or 'group' in registry_entry.id:
            tags.append('aggregation')

        return list(set(tags))

    def export_to_yaml(
        self,
        draft: DraftMapping,
        output_path: Path,
        include_metadata: bool = True
    ) -> Path:
        """Export draft mapping to concepts.yaml format.

        Args:
            draft: The draft mapping to export
            output_path: Where to write the YAML file
            include_metadata: Whether to include mapping metadata

        Returns:
            Path to the written file
        """
        yaml_data = draft.to_concepts_yaml()

        if not include_metadata:
            # Remove metadata fields
            for concept_data in yaml_data.get('concepts', {}).values():
                concept_data.pop('_mapping_metadata', None)
            yaml_data.pop('_generation_stats', None)

        # Custom YAML representer for cleaner output
        def str_representer(dumper, data):
            if '\n' in data:
                return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
            return dumper.represent_scalar('tag:yaml.org,2002:str', data)

        yaml.add_representer(str, str_representer)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Auto-generated concept mapping\n")
            f.write(f"# Generated: {draft.created_at}\n")
            f.write(f"# Source: {draft.pdf_path.name}\n")
            f.write(f"# Total concepts: {len(draft.concepts)}\n")
            f.write(f"# Concepts needing review: {sum(1 for c in draft.concepts if c.needs_review)}\n")
            f.write("#\n")
            f.write("# NOTE: Please review and adjust page numbers before using.\n")
            f.write("# Confidence scores and review notes are in _mapping_metadata.\n\n")

            yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        return output_path

    def export_to_json(self, draft: DraftMapping, output_path: Path) -> Path:
        """Export draft mapping to JSON format.

        Args:
            draft: The draft mapping to export
            output_path: Where to write the JSON file

        Returns:
            Path to the written file
        """
        # Convert to serializable format
        data = {
            'pdf_path': str(draft.pdf_path),
            'created_at': draft.created_at,
            'total_pages': draft.total_pages,
            'detected_headings': draft.detected_headings,
            'matched_concepts': draft.matched_concepts,
            'concepts': [
                {
                    'concept_id': c.concept_id,
                    'concept_name': c.concept_name,
                    'title': c.title,
                    'definition': c.definition,
                    'difficulty': c.difficulty,
                    'estimated_read_time': c.estimated_read_time,
                    'page_references': c.page_references,
                    'sections': c.sections,
                    'related_concepts': c.related_concepts,
                    'tags': c.tags,
                    'source_heading': c.source_heading,
                    'confidence': c.confidence,
                    'match_score': c.match_score,
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
                    'confidence': h.confidence,
                }
                for h in draft.unmatched_headings
            ],
            'suggested_additions': [
                {
                    'concept_id': c.concept_id,
                    'concept_name': c.concept_name,
                    'match_score': c.match_score,
                    'match_type': c.match_type,
                }
                for c in draft.suggested_additions[:10]  # Limit suggestions
            ],
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return output_path

    def get_mapping_summary(self, draft: DraftMapping) -> dict[str, Any]:
        """Get a summary of the draft mapping."""
        return {
            'source_pdf': draft.pdf_path.name,
            'total_pages': draft.total_pages,
            'detected_headings': draft.detected_headings,
            'matched_concepts': draft.matched_concepts,
            'high_confidence': sum(1 for c in draft.concepts if c.confidence >= 0.8),
            'medium_confidence': sum(
                1 for c in draft.concepts
                if 0.5 <= c.confidence < 0.8
            ),
            'needs_review': sum(1 for c in draft.concepts if c.needs_review),
            'unmatched_headings': len(draft.unmatched_headings),
            'suggested_additions': len(draft.suggested_additions),
            'by_difficulty': {
                'beginner': sum(1 for c in draft.concepts if c.difficulty == 'beginner'),
                'intermediate': sum(1 for c in draft.concepts if c.difficulty == 'intermediate'),
                'advanced': sum(1 for c in draft.concepts if c.difficulty == 'advanced'),
            },
        }
