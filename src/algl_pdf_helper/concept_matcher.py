from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .structure_extractor import Heading


@dataclass
class ConceptRegistryEntry:
    """A concept in the registry."""
    id: str
    name: str
    definition: str = ""
    keywords: list[str] = field(default_factory=list)
    related_concepts: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    difficulty: str = "beginner"
    category: str = ""


@dataclass
class MatchCandidate:
    """A candidate match between a heading and a concept."""
    concept_id: str
    concept_name: str
    heading_text: str
    heading_page: int
    match_score: float  # 0.0 to 1.0
    match_type: str  # 'exact', 'keyword', 'fuzzy', 'category'
    confidence: float  # Adjusted confidence based on context
    suggested_pages: list[int] = field(default_factory=list)


class ConceptMatcher:
    """Match extracted headings to SQL-Engage concept registry."""

    # SQL keywords for matching
    SQL_KEYWORDS = {
        'select': ['select', 'query', 'retrieve', 'fetch', 'projection'],
        'where': ['where', 'filter', 'condition', 'predicate', 'criteria'],
        'join': ['join', 'inner join', 'outer join', 'left join', 'right join', 'cross join'],
        'group-by': ['group by', 'aggregate', 'grouping', 'summary'],
        'order-by': ['order by', 'sort', 'ascending', 'descending', 'sequence'],
        'insert': ['insert', 'add', 'create row', 'append'],
        'update': ['update', 'modify', 'change', 'edit'],
        'delete': ['delete', 'remove', 'drop row', 'truncate'],
        'create-table': ['create table', 'table definition', 'schema', 'ddl'],
        'alter-table': ['alter table', 'modify table', 'change schema'],
        'drop-table': ['drop table', 'delete table', 'remove table'],
        'index': ['index', 'indexing', 'performance', 'lookup'],
        'view': ['view', 'virtual table', 'named query'],
        'subquery': ['subquery', 'nested query', 'inner query', 'correlated'],
        'union': ['union', 'combine', 'merge results'],
        'intersect': ['intersect', 'common rows'],
        'except': ['except', 'minus', 'difference'],
        'having': ['having', 'filter groups', 'group condition'],
        'case': ['case', 'conditional', 'if-then-else', 'decode'],
        'functions': ['function', 'aggregate function', 'scalar function', 'built-in'],
        'constraints': ['constraint', 'primary key', 'foreign key', 'unique', 'check', 'not null'],
        'normalization': ['normalization', 'normal form', '1nf', '2nf', '3nf', 'bcnf'],
        'transaction': ['transaction', 'commit', 'rollback', 'acid'],
        'trigger': ['trigger', 'event', 'automatic', 'before', 'after'],
        'stored-procedure': ['stored procedure', 'procedure', 'routine', 'pl/sql'],
    }

    def __init__(self, registry_path: Path | None = None):
        """Initialize the matcher with a concept registry.

        Args:
            registry_path: Path to concept registry YAML file
        """
        self.registry: dict[str, ConceptRegistryEntry] = {}
        self.category_keywords: dict[str, list[str]] = {}

        if registry_path and registry_path.exists():
            self._load_registry(registry_path)
        else:
            self._load_default_registry()

    def _load_registry(self, registry_path: Path) -> None:
        """Load concept registry from YAML file."""
        with open(registry_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        for concept_data in data.get('concepts', []):
            entry = ConceptRegistryEntry(
                id=concept_data['id'],
                name=concept_data['name'],
                definition=concept_data.get('definition', ''),
                keywords=concept_data.get('keywords', []),
                related_concepts=concept_data.get('related_concepts', []),
                prerequisites=concept_data.get('prerequisites', []),
                difficulty=concept_data.get('difficulty', 'beginner'),
                category=concept_data.get('category', '')
            )
            self.registry[entry.id] = entry

        self.category_keywords = data.get('categories', {})

    def _load_default_registry(self) -> None:
        """Load default SQL concept registry."""
        default_concepts = [
            ConceptRegistryEntry(
                id='select-basic',
                name='SELECT Statement Basics',
                definition='Retrieves data from one or more tables',
                keywords=['select', 'from', 'column', 'retrieve', 'query', 'fetch', 'projection', 'distinct', 'all', '*', 'asterisk'],
                related_concepts=['where-clause', 'order-by', 'alias'],
                difficulty='beginner',
                category='dql'
            ),
            ConceptRegistryEntry(
                id='where-clause',
                name='WHERE Clause',
                definition='Filters rows based on specified conditions',
                keywords=['where', 'filter', 'condition', 'predicate', 'criteria', 'comparison', 'logical operator', 'and', 'or', 'not'],
                related_concepts=['select-basic', 'comparison-operators', 'null-handling'],
                prerequisites=['select-basic'],
                difficulty='beginner',
                category='dql'
            ),
            ConceptRegistryEntry(
                id='order-by',
                name='ORDER BY Clause',
                definition='Sorts query results in ascending or descending order',
                keywords=['order by', 'sort', 'asc', 'desc', 'ascending', 'descending', 'sequence', 'ordering'],
                related_concepts=['select-basic', 'where-clause'],
                prerequisites=['select-basic'],
                difficulty='beginner',
                category='dql'
            ),
            ConceptRegistryEntry(
                id='alias',
                name='Column and Table Aliases',
                definition='Temporary names for columns or tables in queries',
                keywords=['alias', 'as', 'rename', 'temporary name', 'column alias', 'table alias'],
                related_concepts=['select-basic', 'join'],
                prerequisites=['select-basic'],
                difficulty='beginner',
                category='dql'
            ),
            ConceptRegistryEntry(
                id='comparison-operators',
                name='Comparison Operators',
                definition='Operators for comparing values (=, <>, <, >, <=, >=)',
                keywords=['=', '<>', '!=', '<', '>', '<=', '>=', 'equal', 'not equal', 'less than', 'greater than', 'comparison', 'between', 'in', 'like'],
                related_concepts=['where-clause'],
                prerequisites=['where-clause'],
                difficulty='beginner',
                category='dql'
            ),
            ConceptRegistryEntry(
                id='null-handling',
                name='NULL Handling',
                definition='Working with NULL values in SQL (IS NULL, IS NOT NULL, COALESCE)',
                keywords=['null', 'is null', 'is not null', 'coalesce', 'nvl', 'ifnull', 'missing value', 'unknown'],
                related_concepts=['where-clause', 'comparison-operators'],
                prerequisites=['where-clause'],
                difficulty='beginner',
                category='dql'
            ),
            ConceptRegistryEntry(
                id='join',
                name='JOIN Operations',
                definition='Combining rows from two or more tables based on related columns',
                keywords=['join', 'inner join', 'outer join', 'left join', 'right join', 'full join', 'cross join', 'natural join', 'self join', 'combine tables'],
                related_concepts=['select-basic', 'alias', 'table-relationships'],
                prerequisites=['select-basic', 'alias'],
                difficulty='intermediate',
                category='dql'
            ),
            ConceptRegistryEntry(
                id='aggregate-functions',
                name='Aggregate Functions',
                definition='Functions that operate on sets of rows (COUNT, SUM, AVG, MIN, MAX)',
                keywords=['count', 'sum', 'avg', 'average', 'min', 'max', 'aggregate', 'aggregation', 'group function', 'summary'],
                related_concepts=['group-by', 'having'],
                prerequisites=['select-basic'],
                difficulty='intermediate',
                category='dql'
            ),
            ConceptRegistryEntry(
                id='group-by',
                name='GROUP BY Clause',
                definition='Groups rows sharing a property for aggregate calculations',
                keywords=['group by', 'grouping', 'group', 'aggregate groups', 'summary by group'],
                related_concepts=['aggregate-functions', 'having'],
                prerequisites=['aggregate-functions'],
                difficulty='intermediate',
                category='dql'
            ),
            ConceptRegistryEntry(
                id='having',
                name='HAVING Clause',
                definition='Filters groups based on aggregate conditions',
                keywords=['having', 'filter groups', 'group condition', 'aggregate filter'],
                related_concepts=['group-by', 'aggregate-functions', 'where-clause'],
                prerequisites=['group-by'],
                difficulty='intermediate',
                category='dql'
            ),
            ConceptRegistryEntry(
                id='subquery',
                name='Subqueries',
                definition='Queries nested inside another query',
                keywords=['subquery', 'subqueries', 'nested query', 'inner query', 'correlated subquery', 'in subquery', 'exists', 'scalar subquery'],
                related_concepts=['select-basic', 'join', 'where-clause'],
                prerequisites=['select-basic', 'where-clause'],
                difficulty='intermediate',
                category='dql'
            ),
            ConceptRegistryEntry(
                id='set-operations',
                name='Set Operations',
                definition='Combining results of multiple queries (UNION, INTERSECT, EXCEPT)',
                keywords=['union', 'intersect', 'except', 'minus', 'union all', 'combine results', 'set operation'],
                related_concepts=['select-basic'],
                prerequisites=['select-basic'],
                difficulty='intermediate',
                category='dql'
            ),
            ConceptRegistryEntry(
                id='insert',
                name='INSERT Statement',
                definition='Adds new rows to a table',
                keywords=['insert', 'insert into', 'values', 'add row', 'create row', 'append'],
                related_concepts=['select-basic', 'update', 'delete'],
                difficulty='beginner',
                category='dml'
            ),
            ConceptRegistryEntry(
                id='update',
                name='UPDATE Statement',
                definition='Modifies existing rows in a table',
                keywords=['update', 'set', 'modify', 'change', 'edit row', 'update rows'],
                related_concepts=['insert', 'delete', 'where-clause'],
                prerequisites=['insert', 'where-clause'],
                difficulty='beginner',
                category='dml'
            ),
            ConceptRegistryEntry(
                id='delete',
                name='DELETE Statement',
                definition='Removes rows from a table',
                keywords=['delete', 'delete from', 'remove row', 'drop row', 'truncate table'],
                related_concepts=['insert', 'update', 'where-clause'],
                prerequisites=['update'],
                difficulty='beginner',
                category='dml'
            ),
            ConceptRegistryEntry(
                id='create-table',
                name='CREATE TABLE',
                definition='Creates a new table with specified columns and constraints',
                keywords=['create table', 'table definition', 'ddl', 'data definition', 'new table', 'define table'],
                related_concepts=['constraints', 'data-types', 'alter-table'],
                difficulty='beginner',
                category='ddl'
            ),
            ConceptRegistryEntry(
                id='alter-table',
                name='ALTER TABLE',
                definition='Modifies the structure of an existing table',
                keywords=['alter table', 'add column', 'drop column', 'modify column', 'change table'],
                related_concepts=['create-table', 'constraints'],
                prerequisites=['create-table'],
                difficulty='intermediate',
                category='ddl'
            ),
            ConceptRegistryEntry(
                id='drop-table',
                name='DROP TABLE',
                definition='Removes a table and all its data',
                keywords=['drop table', 'delete table', 'remove table', 'destroy table'],
                related_concepts=['create-table', 'truncate-table'],
                prerequisites=['create-table'],
                difficulty='beginner',
                category='ddl'
            ),
            ConceptRegistryEntry(
                id='constraints',
                name='Constraints',
                definition='Rules enforced on data columns (PK, FK, UNIQUE, CHECK, NOT NULL)',
                keywords=['constraint', 'primary key', 'foreign key', 'unique', 'check', 'not null', 'default', 'referential integrity'],
                related_concepts=['create-table', 'alter-table', 'table-relationships'],
                prerequisites=['create-table'],
                difficulty='intermediate',
                category='ddl'
            ),
            ConceptRegistryEntry(
                id='index',
                name='Indexes',
                definition='Database objects that improve query performance',
                keywords=['index', 'create index', 'b-tree', 'unique index', 'composite index', 'performance', 'query optimization'],
                related_concepts=['create-table', 'query-optimization'],
                prerequisites=['create-table'],
                difficulty='intermediate',
                category='ddl'
            ),
            ConceptRegistryEntry(
                id='view',
                name='Views',
                definition='Virtual tables based on the result of a query',
                keywords=['view', 'create view', 'virtual table', 'named query', 'drop view'],
                related_concepts=['select-basic', 'subquery'],
                prerequisites=['select-basic'],
                difficulty='intermediate',
                category='ddl'
            ),
            ConceptRegistryEntry(
                id='transaction',
                name='Transactions',
                definition='ACID units of work (COMMIT, ROLLBACK, SAVEPOINT)',
                keywords=['transaction', 'commit', 'rollback', 'savepoint', 'acid', 'atomicity', 'consistency', 'isolation', 'durability'],
                related_concepts=['concurrency-control', 'locking'],
                difficulty='advanced',
                category='advanced'
            ),
        ]

        for entry in default_concepts:
            self.registry[entry.id] = entry

        self.category_keywords = {
            'dql': ['query', 'select', 'retrieve', 'fetch', 'dql', 'data query'],
            'dml': ['modify', 'insert', 'update', 'delete', 'dml', 'manipulation'],
            'ddl': ['schema', 'create', 'alter', 'drop', 'define', 'structure', 'ddl'],
            'advanced': ['advanced', 'transaction', 'optimization', 'performance', 'concurrency'],
        }

    def match_heading(self, heading: Heading) -> list[MatchCandidate]:
        """Find matching concepts for a single heading.

        Args:
            heading: The heading to match

        Returns:
            List of match candidates sorted by score
        """
        candidates = []
        heading_lower = heading.text.lower()
        heading_words = set(re.findall(r'\w+', heading_lower))

        for concept_id, entry in self.registry.items():
            score = 0.0
            match_type = 'none'

            # 1. Exact name match
            if entry.name.lower() in heading_lower or heading_lower in entry.name.lower():
                score = max(score, 0.95)
                match_type = 'exact'

            # 2. Keyword matching
            keyword_matches = 0
            for keyword in entry.keywords:
                if keyword.lower() in heading_lower:
                    keyword_matches += 1
                # Also check if keyword words appear in heading
                kw_words = set(re.findall(r'\w+', keyword.lower()))
                if kw_words & heading_words:
                    keyword_matches += 0.5

            if keyword_matches > 0:
                keyword_score = min(0.9, 0.5 + (keyword_matches * 0.1))
                if keyword_score > score:
                    score = keyword_score
                    match_type = 'keyword'

            # 3. Category matching
            if entry.category and entry.category in self.category_keywords:
                cat_keywords = self.category_keywords[entry.category]
                cat_matches = sum(1 for kw in cat_keywords if kw in heading_lower)
                if cat_matches > 0:
                    cat_score = min(0.6, 0.3 + (cat_matches * 0.1))
                    if cat_score > score:
                        score = cat_score
                        match_type = 'category'

            # 4. Fuzzy similarity (simple word overlap)
            concept_words = set(re.findall(r'\w+', entry.name.lower()))
            concept_words.update(kw.lower() for kw in entry.keywords[:3])

            if concept_words and heading_words:
                overlap = len(concept_words & heading_words)
                similarity = overlap / max(len(concept_words), len(heading_words))
                if similarity > 0.3:
                    fuzzy_score = min(0.7, similarity)
                    if fuzzy_score > score:
                        score = fuzzy_score
                        match_type = 'fuzzy'

            if score > 0.3:  # Minimum threshold
                # Calculate confidence based on heading level and format
                confidence = self._calculate_confidence(score, heading, entry)

                # Estimate page range (this heading to next)
                suggested_pages = list(range(heading.page, heading.page + 3))

                candidates.append(MatchCandidate(
                    concept_id=concept_id,
                    concept_name=entry.name,
                    heading_text=heading.text,
                    heading_page=heading.page,
                    match_score=score,
                    match_type=match_type,
                    confidence=confidence,
                    suggested_pages=suggested_pages
                ))

        # Sort by score descending
        candidates.sort(key=lambda c: c.match_score, reverse=True)
        return candidates

    def _calculate_confidence(
        self,
        base_score: float,
        heading: Heading,
        entry: ConceptRegistryEntry
    ) -> float:
        """Calculate final confidence score based on multiple factors."""
        confidence = base_score

        # Boost for well-formatted headings
        if heading.is_bold:
            confidence += 0.05
        if heading.level == 2:  # Section level is often most reliable
            confidence += 0.05
        if heading.confidence > 0.8:
            confidence += 0.05

        # Slight boost for beginner concepts (more likely to be correct)
        if entry.difficulty == 'beginner':
            confidence += 0.02

        return min(1.0, confidence)

    def match_headings_batch(
        self,
        headings: list[Heading],
        confidence_threshold: float = 0.5
    ) -> list[MatchCandidate]:
        """Match multiple headings and return best candidates.

        Args:
            headings: List of headings to match
            confidence_threshold: Minimum confidence to include

        Returns:
            List of best match candidates for each heading
        """
        all_matches = []

        for heading in headings:
            candidates = self.match_heading(heading)

            # Take top candidates above threshold
            for candidate in candidates:
                if candidate.confidence >= confidence_threshold:
                    all_matches.append(candidate)

        return all_matches

    def find_related_matches(
        self,
        matched_concept_ids: list[str]
    ) -> list[MatchCandidate]:
        """Find related concepts that might also be covered.

        Args:
            matched_concept_ids: IDs of already matched concepts

        Returns:
            List of related concept suggestions
        """
        related = []
        matched_set = set(matched_concept_ids)

        for concept_id in matched_concept_ids:
            if concept_id not in self.registry:
                continue

            entry = self.registry[concept_id]

            # Add related concepts
            for related_id in entry.related_concepts:
                if related_id in self.registry and related_id not in matched_set:
                    related_entry = self.registry[related_id]
                    related.append(MatchCandidate(
                        concept_id=related_id,
                        concept_name=related_entry.name,
                        heading_text="",
                        heading_page=0,
                        match_score=0.4,
                        match_type='related',
                        confidence=0.4,
                        suggested_pages=[]
                    ))

            # Add prerequisites
            for prereq_id in entry.prerequisites:
                if prereq_id in self.registry and prereq_id not in matched_set:
                    prereq_entry = self.registry[prereq_id]
                    related.append(MatchCandidate(
                        concept_id=prereq_id,
                        concept_name=prereq_entry.name,
                        heading_text="",
                        heading_page=0,
                        match_score=0.35,
                        match_type='prerequisite',
                        confidence=0.35,
                        suggested_pages=[]
                    ))

        # Remove duplicates and sort
        seen = set()
        unique_related = []
        for r in related:
            if r.concept_id not in seen:
                seen.add(r.concept_id)
                unique_related.append(r)

        unique_related.sort(key=lambda c: c.confidence, reverse=True)
        return unique_related

    def get_registry_stats(self) -> dict[str, Any]:
        """Get statistics about the loaded registry."""
        categories = {}
        difficulties = {}

        for entry in self.registry.values():
            cat = entry.category or 'uncategorized'
            categories[cat] = categories.get(cat, 0) + 1

            diff = entry.difficulty
            difficulties[diff] = difficulties.get(diff, 0) + 1

        return {
            'total_concepts': len(self.registry),
            'by_category': categories,
            'by_difficulty': difficulties,
        }
