"""
Three-Layer Concept Mapping System for SQL-Engage Integration.

This module implements the mapping between error subtypes (Layer 1), 
concept IDs (Layer 2), and textbook content (Layer 3).

Layer 1: Error Subtype Detection (from sql-engage.ts)
Layer 2: Alignment Map (error → concept IDs)  
Layer 3: Concept Registry (concept → textbook content)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class ConceptMappingSystem:
    """
    Three-layer mapping system for SQL-Engage educational content.
    
    Usage:
        cms = ConceptMappingSystem()
        
        # Layer 1→2: Error to concepts
        concepts = cms.get_concepts_for_error("missing_comma_in_select")
        
        # Layer 2→3: Concept to content
        content = cms.get_concept_content("select-basic")
    """
    
    # Layer 1: Error Subtype Definitions (from sql-engage.ts)
    ERROR_SUBTYPES = {
        # Query Completeness Errors
        "incomplete_query": {
            "id": 1,
            "name": "Incomplete Query",
            "severity": "error",
            "category": "completeness"
        },
        "incorrect_select_usage": {
            "id": 2,
            "name": "Incorrect SELECT Usage",
            "severity": "error",
            "category": "syntax"
        },
        "incorrect_wildcard_usage": {
            "id": 3,
            "name": "Incorrect Wildcard Usage",
            "severity": "warning",
            "category": "syntax"
        },
        "missing_comma_in_select": {
            "id": 4,
            "name": "Missing Comma in SELECT",
            "severity": "error",
            "category": "syntax"
        },
        "extra_comma_in_select": {
            "id": 5,
            "name": "Extra Comma in SELECT",
            "severity": "error",
            "category": "syntax"
        },
        # WHERE Clause Errors
        "missing_where_clause": {
            "id": 6,
            "name": "Missing WHERE Clause",
            "severity": "warning",
            "category": "logic"
        },
        "incorrect_operator_usage": {
            "id": 7,
            "name": "Incorrect Operator Usage",
            "severity": "error",
            "category": "logic"
        },
        "incorrect_function_usage": {
            "id": 8,
            "name": "Incorrect Function Usage",
            "severity": "error",
            "category": "logic"
        },
        "incorrect_parentheses": {
            "id": 9,
            "name": "Incorrect Parentheses",
            "severity": "error",
            "category": "syntax"
        },
        "incorrect_null_comparison": {
            "id": 10,
            "name": "Incorrect NULL Comparison",
            "severity": "error",
            "category": "logic"
        },
        # JOIN Errors
        "incorrect_join_type": {
            "id": 11,
            "name": "Incorrect JOIN Type",
            "severity": "error",
            "category": "logic"
        },
        "missing_join_condition": {
            "id": 12,
            "name": "Missing JOIN Condition",
            "severity": "error",
            "category": "syntax"
        },
        "incorrect_join_table_order": {
            "id": 13,
            "name": "Incorrect JOIN Table Order",
            "severity": "warning",
            "category": "logic"
        },
        # Aggregation Errors
        "missing_group_by": {
            "id": 14,
            "name": "Missing GROUP BY",
            "severity": "error",
            "category": "logic"
        },
        "incorrect_group_by_columns": {
            "id": 15,
            "name": "Incorrect GROUP BY Columns",
            "severity": "error",
            "category": "logic"
        },
        "having_without_group_by": {
            "id": 16,
            "name": "HAVING Without GROUP BY",
            "severity": "warning",
            "category": "logic"
        },
        "incorrect_aggregate_function": {
            "id": 17,
            "name": "Incorrect Aggregate Function",
            "severity": "error",
            "category": "logic"
        },
        # Set Operation Errors
        "incorrect_union_usage": {
            "id": 18,
            "name": "Incorrect UNION Usage",
            "severity": "error",
            "category": "syntax"
        },
        "incompatible_columns_in_union": {
            "id": 19,
            "name": "Incompatible Columns in UNION",
            "severity": "error",
            "category": "logic"
        },
        # Subquery Errors
        "incorrect_subquery_usage": {
            "id": 20,
            "name": "Incorrect Subquery Usage",
            "severity": "error",
            "category": "logic"
        },
        "correlated_subquery_error": {
            "id": 21,
            "name": "Correlated Subquery Error",
            "severity": "error",
            "category": "logic"
        },
        # Alias and Reference Errors
        "ambiguous_column_reference": {
            "id": 22,
            "name": "Ambiguous Column Reference",
            "severity": "error",
            "category": "syntax"
        },
        "undefined_alias": {
            "id": 23,
            "name": "Undefined Alias",
            "severity": "error",
            "category": "syntax"
        }
    }
    
    # Layer 2: Alignment Map (Error Subtype → Concept IDs)
    ALIGNMENT_MAP: dict[str, dict[str, Any]] = {
        # Query Completeness
        "incomplete_query": {
            "error_subtype_id": 1,
            "concept_ids": ["select-basic", "syntax-error"],
            "confidence": "high",
            "teaching_strategy": "start_fundamentals",
            "remediation_order": ["select-basic", "syntax-error"]
        },
        "incorrect_select_usage": {
            "error_subtype_id": 2,
            "concept_ids": ["select-basic", "distinct"],
            "confidence": "high",
            "teaching_strategy": "select_mastery",
            "remediation_order": ["select-basic", "distinct"]
        },
        "incorrect_wildcard_usage": {
            "error_subtype_id": 3,
            "concept_ids": ["select-basic"],
            "confidence": "medium",
            "teaching_strategy": "explicit_columns",
            "remediation_order": ["select-basic"]
        },
        "missing_comma_in_select": {
            "error_subtype_id": 4,
            "concept_ids": ["select-basic", "syntax-error"],
            "confidence": "verified",
            "teaching_strategy": "syntax_drill",
            "remediation_order": ["syntax-error", "select-basic"]
        },
        "extra_comma_in_select": {
            "error_subtype_id": 5,
            "concept_ids": ["select-basic", "syntax-error"],
            "confidence": "verified",
            "teaching_strategy": "syntax_drill",
            "remediation_order": ["syntax-error", "select-basic"]
        },
        # WHERE Clause
        "missing_where_clause": {
            "error_subtype_id": 6,
            "concept_ids": ["where-clause"],
            "confidence": "high",
            "teaching_strategy": "filtering_basics",
            "remediation_order": ["where-clause"]
        },
        "incorrect_operator_usage": {
            "error_subtype_id": 7,
            "concept_ids": ["where-clause", "logical-operators", "comparison-operators"],
            "confidence": "medium",
            "teaching_strategy": "operator_mastery",
            "remediation_order": ["logical-operators", "where-clause"]
        },
        "incorrect_function_usage": {
            "error_subtype_id": 8,
            "concept_ids": ["string-functions", "date-functions", "aggregate-functions"],
            "confidence": "medium",
            "teaching_strategy": "function_basics",
            "remediation_order": ["string-functions", "date-functions"]
        },
        "incorrect_parentheses": {
            "error_subtype_id": 9,
            "concept_ids": ["logical-operators"],
            "confidence": "high",
            "teaching_strategy": "precedence_drill",
            "remediation_order": ["logical-operators"]
        },
        "incorrect_null_comparison": {
            "error_subtype_id": 10,
            "concept_ids": ["null-handling", "is-null-operator"],
            "confidence": "verified",
            "teaching_strategy": "null_mastery",
            "remediation_order": ["null-handling"]
        },
        # JOIN Errors
        "incorrect_join_type": {
            "error_subtype_id": 11,
            "concept_ids": ["joins", "inner-join", "outer-join"],
            "confidence": "high",
            "teaching_strategy": "join_types",
            "remediation_order": ["joins", "inner-join", "outer-join"]
        },
        "missing_join_condition": {
            "error_subtype_id": 12,
            "concept_ids": ["joins", "join-condition-missing", "on-clause"],
            "confidence": "verified",
            "teaching_strategy": "join_conditions",
            "remediation_order": ["joins", "join-condition-missing"]
        },
        "incorrect_join_table_order": {
            "error_subtype_id": 13,
            "concept_ids": ["joins"],
            "confidence": "medium",
            "teaching_strategy": "join_basics",
            "remediation_order": ["joins"]
        },
        # Aggregation
        "missing_group_by": {
            "error_subtype_id": 14,
            "concept_ids": ["group-by", "group-by-error", "aggregation"],
            "confidence": "verified",
            "teaching_strategy": "group_by_mastery",
            "remediation_order": ["aggregation", "group-by"]
        },
        "incorrect_group_by_columns": {
            "error_subtype_id": 15,
            "concept_ids": ["group-by", "group-by-error"],
            "confidence": "high",
            "teaching_strategy": "group_by_drill",
            "remediation_order": ["group-by"]
        },
        "having_without_group_by": {
            "error_subtype_id": 16,
            "concept_ids": ["having-clause", "group-by"],
            "confidence": "verified",
            "teaching_strategy": "having_basics",
            "remediation_order": ["group-by", "having-clause"]
        },
        "incorrect_aggregate_function": {
            "error_subtype_id": 17,
            "concept_ids": ["aggregation", "count-function", "sum-function", "avg-function"],
            "confidence": "medium",
            "teaching_strategy": "aggregate_functions",
            "remediation_order": ["aggregation"]
        },
        # Set Operations
        "incorrect_union_usage": {
            "error_subtype_id": 18,
            "concept_ids": ["union", "union-all"],
            "confidence": "high",
            "teaching_strategy": "set_operations",
            "remediation_order": ["union", "union-all"]
        },
        "incompatible_columns_in_union": {
            "error_subtype_id": 19,
            "concept_ids": ["union", "data-types"],
            "confidence": "medium",
            "teaching_strategy": "union_compatibility",
            "remediation_order": ["union"]
        },
        # Subqueries
        "incorrect_subquery_usage": {
            "error_subtype_id": 20,
            "concept_ids": ["subqueries", "in-operator", "exists-operator"],
            "confidence": "high",
            "teaching_strategy": "subquery_basics",
            "remediation_order": ["subqueries"]
        },
        "correlated_subquery_error": {
            "error_subtype_id": 21,
            "concept_ids": ["correlated-subquery", "subqueries"],
            "confidence": "medium",
            "teaching_strategy": "correlated_subqueries",
            "remediation_order": ["subqueries", "correlated-subquery"]
        },
        # Alias and Reference
        "ambiguous_column_reference": {
            "error_subtype_id": 22,
            "concept_ids": ["alias", "ambiguous-column", "table-alias"],
            "confidence": "verified",
            "teaching_strategy": "aliasing",
            "remediation_order": ["alias", "ambiguous-column"]
        },
        "undefined_alias": {
            "error_subtype_id": 23,
            "concept_ids": ["alias", "column-alias"],
            "confidence": "high",
            "teaching_strategy": "alias_scope",
            "remediation_order": ["alias"]
        }
    }
    
    def __init__(self, registry_path: str | Path | None = None):
        """
        Initialize the mapping system.
        
        Args:
            registry_path: Path to concept-registry.json. If None, uses default.
        """
        self.registry_path = registry_path or Path(__file__).parent.parent.parent / "output" / "mappings" / "concept-registry.json"
        self.concept_registry: dict[str, Any] = {}
        self._load_registry()
    
    def _load_registry(self) -> None:
        """Load the concept registry (Layer 3)."""
        if not Path(self.registry_path).exists():
            raise FileNotFoundError(f"Concept registry not found: {self.registry_path}")
        
        with open(self.registry_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.concept_registry = data.get("concepts", {})
    
    # Layer 1: Error Subtype Methods
    def get_error_info(self, error_subtype: str) -> dict[str, Any] | None:
        """
        Get information about an error subtype (Layer 1).
        
        Args:
            error_subtype: The error subtype string (e.g., "missing_comma_in_select")
            
        Returns:
            Error information or None if not found
        """
        return self.ERROR_SUBTYPES.get(error_subtype)
    
    def list_error_subtypes(self) -> list[str]:
        """List all available error subtypes."""
        return list(self.ERROR_SUBTYPES.keys())
    
    def detect_error_subtype(self, error_message: str, sql_code: str) -> str | None:
        """
        Detect error subtype from error message and SQL code.
        
        Args:
            error_message: The database error message
            sql_code: The SQL code that caused the error
            
        Returns:
            Detected error subtype or None
        """
        error_lower = error_message.lower()
        sql_upper = sql_code.upper()
        
        # Pattern matching for error detection
        patterns = {
            "missing_comma_in_select": [
                r'near ".*": syntax error',
                r"missing comma",
                r'syntax error at or near "FROM"'
            ],
            "extra_comma_in_select": [
                r'near "\)": syntax error'
            ],
            "missing_where_clause": [
                r"where clause"
            ],
            "missing_join_condition": [
                r"join.*condition",
                r"on clause"
            ],
            "missing_group_by": [
                r"group by",
                r"must appear in the group by"
            ],
            "ambiguous_column_reference": [
                r"ambiguous column",
                r"ambiguous attribute"
            ],
            "incorrect_null_comparison": [
                r"null",
                r"operator does not exist"
            ]
        }
        
        for subtype, regex_patterns in patterns.items():
            for pattern in regex_patterns:
                if re.search(pattern, error_lower):
                    return subtype
        
        return None
    
    # Layer 2: Alignment Map Methods
    def get_concepts_for_error(self, error_subtype: str) -> list[str]:
        """
        Map error subtype to concept IDs (Layer 1→2).
        
        Args:
            error_subtype: The error subtype string
            
        Returns:
            List of concept IDs to study
        """
        mapping = self.ALIGNMENT_MAP.get(error_subtype)
        if not mapping:
            return []
        
        # Filter by confidence level
        confidence = mapping.get("confidence", "low")
        if confidence in ["high", "verified", "medium"]:
            return mapping.get("concept_ids", [])
        
        return []
    
    def get_remediation_order(self, error_subtype: str) -> list[str]:
        """
        Get the recommended order to learn concepts for an error.
        
        Args:
            error_subtype: The error subtype string
            
        Returns:
            Ordered list of concept IDs
        """
        mapping = self.ALIGNMENT_MAP.get(error_subtype)
        if mapping:
            return mapping.get("remediation_order", mapping.get("concept_ids", []))
        return []
    
    def get_teaching_strategy(self, error_subtype: str) -> str | None:
        """
        Get the teaching strategy for an error subtype.
        
        Args:
            error_subtype: The error subtype string
            
        Returns:
            Teaching strategy identifier
        """
        mapping = self.ALIGNMENT_MAP.get(error_subtype)
        if mapping:
            return mapping.get("teaching_strategy")
        return None
    
    # Layer 3: Concept Content Methods
    def get_concept_content(self, concept_id: str) -> dict[str, Any] | None:
        """
        Get content for a concept (Layer 2→3).
        
        Args:
            concept_id: The concept ID
            
        Returns:
            Concept content including metadata and file paths
        """
        concept = self.concept_registry.get(concept_id)
        if not concept:
            return None
        
        return {
            "id": concept.get("id"),
            "title": concept.get("title"),
            "description": concept.get("description"),
            "difficulty": concept.get("difficulty"),
            "estimatedReadTime": concept.get("estimatedReadTime"),
            "category": concept.get("category"),
            "contentLocation": concept.get("contentLocation"),
            "qualityStatus": concept.get("qualityStatus"),
            "learningObjectives": concept.get("learningObjectives", [])
        }
    
    def list_concepts(self) -> list[str]:
        """List all available concept IDs."""
        return list(self.concept_registry.keys())
    
    def get_concepts_by_difficulty(self, difficulty: str) -> list[dict[str, Any]]:
        """
        Get all concepts of a specific difficulty level.
        
        Args:
            difficulty: "beginner", "intermediate", or "advanced"
            
        Returns:
            List of concept content dictionaries
        """
        results = []
        for concept_id, concept in self.concept_registry.items():
            if concept.get("difficulty") == difficulty:
                results.append(self.get_concept_content(concept_id))
        return [r for r in results if r is not None]
    
    def get_concepts_by_category(self, category: str) -> list[dict[str, Any]]:
        """
        Get all concepts in a specific category.
        
        Args:
            category: Category name (e.g., "SELECT Basics", "JOINs")
            
        Returns:
            List of concept content dictionaries
        """
        results = []
        for concept_id, concept in self.concept_registry.items():
            if concept.get("category") == category:
                results.append(self.get_concept_content(concept_id))
        return [r for r in results if r is not None]
    
    # Cross-Layer Methods
    def get_learning_path(self, error_subtype: str) -> dict[str, Any] | None:
        """
        Get complete learning path from error to content (Layer 1→2→3).
        
        Args:
            error_subtype: The error subtype string
            
        Returns:
            Complete learning path with error info, concepts, and content
        """
        # Layer 1: Error info
        error_info = self.get_error_info(error_subtype)
        if not error_info:
            return None
        
        # Layer 2: Alignment
        concept_ids = self.get_remediation_order(error_subtype)
        teaching_strategy = self.get_teaching_strategy(error_subtype)
        
        # Layer 3: Content
        concepts = []
        for cid in concept_ids:
            content = self.get_concept_content(cid)
            if content:
                concepts.append(content)
        
        return {
            "errorSubtype": error_subtype,
            "errorInfo": error_info,
            "teachingStrategy": teaching_strategy,
            "concepts": concepts,
            "totalReadTime": sum(c.get("estimatedReadTime", 0) for c in concepts),
            "difficulty": self._calculate_path_difficulty(concepts)
        }
    
    def _calculate_path_difficulty(self, concepts: list[dict]) -> str:
        """Calculate overall difficulty of a learning path."""
        if not concepts:
            return "beginner"
        
        difficulties = [c.get("difficulty", "beginner") for c in concepts]
        if "advanced" in difficulties:
            return "advanced"
        elif "intermediate" in difficulties:
            return "intermediate"
        return "beginner"
    
    def search_concepts(self, query: str) -> list[dict[str, Any]]:
        """
        Search concepts by keyword.
        
        Args:
            query: Search query string
            
        Returns:
            List of matching concept content dictionaries
        """
        query_lower = query.lower()
        results = []
        
        for concept_id, concept in self.concept_registry.items():
            # Search in title and description
            if (query_lower in concept.get("title", "").lower() or
                query_lower in concept.get("description", "").lower()):
                results.append(self.get_concept_content(concept_id))
            # Search in learning objectives
            elif any(query_lower in obj.lower() 
                    for obj in concept.get("learningObjectives", [])):
                results.append(self.get_concept_content(concept_id))
        
        return [r for r in results if r is not None]


def export_alignment_map(output_path: str | Path | None = None) -> None:
    """
    Export the alignment map to JSON for web app integration.
    
    Args:
        output_path: Path to write the alignment map JSON. 
                    Defaults to output/mappings/alignment-map.json
    """
    cms = ConceptMappingSystem()
    
    if output_path is None:
        output_path = Path(__file__).parent.parent.parent / "output" / "mappings" / "alignment-map.json"
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    alignment_map = {
        "schemaVersion": "alignment-map-v1",
        "description": "Maps SQL error subtypes to educational concept IDs",
        "createdAt": "2026-02-26T00:00:00Z",
        "totalMappings": len(cms.ALIGNMENT_MAP),
        "mappings": cms.ALIGNMENT_MAP
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(alignment_map, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Alignment map exported to {output_path}")


def export_error_subtypes(output_path: str | Path | None = None) -> None:
    """
    Export error subtypes to JSON for web app integration.
    
    Args:
        output_path: Path to write the error subtypes JSON.
                    Defaults to output/mappings/error-subtypes.json
    """
    cms = ConceptMappingSystem()
    
    if output_path is None:
        output_path = Path(__file__).parent.parent.parent / "output" / "mappings" / "error-subtypes.json"
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    error_subtypes = {
        "schemaVersion": "error-subtypes-v1",
        "description": "SQL-Engage error subtype definitions",
        "createdAt": "2026-02-26T00:00:00Z",
        "totalSubtypes": len(cms.ERROR_SUBTYPES),
        "subtypes": cms.ERROR_SUBTYPES
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(error_subtypes, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Error subtypes exported to {output_path}")


if __name__ == "__main__":
    # Demo usage
    cms = ConceptMappingSystem()
    
    print("=" * 60)
    print("SQL-Engage Three-Layer Concept Mapping System")
    print("=" * 60)
    
    # Demo Layer 1→2→3
    print("\n1. ERROR SUBTYPE → CONCEPT IDS")
    print("-" * 40)
    error_subtype = "missing_comma_in_select"
    concept_ids = cms.get_concepts_for_error(error_subtype)
    print(f"Error: {error_subtype}")
    print(f"Concepts: {concept_ids}")
    
    print("\n2. CONCEPT ID → CONTENT")
    print("-" * 40)
    concept_id = "select-basic"
    content = cms.get_concept_content(concept_id)
    if content:
        print(f"Concept: {content['id']}")
        print(f"Title: {content['title']}")
        print(f"Difficulty: {content['difficulty']}")
        print(f"Read Time: {content['estimatedReadTime']} min")
    
    print("\n3. COMPLETE LEARNING PATH")
    print("-" * 40)
    path = cms.get_learning_path("missing_comma_in_select")
    if path:
        print(f"Error: {path['errorInfo']['name']}")
        print(f"Strategy: {path['teachingStrategy']}")
        print(f"Total Concepts: {len(path['concepts'])}")
        print(f"Total Read Time: {path['totalReadTime']} min")
        print(f"Path Difficulty: {path['difficulty']}")
    
    print("\n4. EXPORT INTEGRATION FILES")
    print("-" * 40)
    export_alignment_map("alignment-map.json")
    export_error_subtypes("error-subtypes.json")
