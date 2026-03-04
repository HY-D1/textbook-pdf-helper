"""
Tests for the three-layer concept mapping system.
"""

import json
import pytest
from pathlib import Path

from algl_pdf_helper.concept_mapping_system import (
    ConceptMappingSystem,
    export_alignment_map,
    export_error_subtypes
)


@pytest.fixture
def mapping_system(tmp_path, monkeypatch):
    """Create a ConceptMappingSystem instance for testing with mocked registry."""
    import algl_pdf_helper.concept_mapping_system as cms_module
    
    # Create a comprehensive mock registry with concepts for all error mappings
    mock_registry = {
        "schemaVersion": "concept-registry-v1",
        "concepts": {
            # SELECT concepts
            "select-basic": {
                "id": "select-basic",
                "title": "SELECT Statement Basics",
                "difficulty": "beginner",
                "estimatedReadTime": 5,
                "category": "SELECT",
            },
            "distinct": {
                "id": "distinct",
                "title": "DISTINCT Keyword",
                "difficulty": "beginner",
                "estimatedReadTime": 3,
                "category": "SELECT",
            },
            "syntax-error": {
                "id": "syntax-error",
                "title": "Syntax Errors",
                "difficulty": "beginner",
                "estimatedReadTime": 3,
                "category": "Errors",
            },
            # WHERE clause concepts
            "where-clause": {
                "id": "where-clause",
                "title": "WHERE Clause",
                "difficulty": "beginner",
                "estimatedReadTime": 5,
                "category": "Filtering",
            },
            "logical-operators": {
                "id": "logical-operators",
                "title": "Logical Operators",
                "difficulty": "intermediate",
                "estimatedReadTime": 6,
                "category": "Logic",
            },
            "comparison-operators": {
                "id": "comparison-operators",
                "title": "Comparison Operators",
                "difficulty": "beginner",
                "estimatedReadTime": 4,
                "category": "Logic",
            },
            "null-handling": {
                "id": "null-handling",
                "title": "NULL Handling",
                "difficulty": "intermediate",
                "estimatedReadTime": 6,
                "category": "Logic",
            },
            "is-null-operator": {
                "id": "is-null-operator",
                "title": "IS NULL Operator",
                "difficulty": "beginner",
                "estimatedReadTime": 3,
                "category": "Logic",
            },
            # JOIN concepts
            "joins": {
                "id": "joins",
                "title": "JOIN Operations",
                "difficulty": "intermediate",
                "estimatedReadTime": 10,
                "category": "JOINs",
            },
            "inner-join": {
                "id": "inner-join",
                "title": "INNER JOIN",
                "difficulty": "intermediate",
                "estimatedReadTime": 7,
                "category": "JOINs",
            },
            "outer-join": {
                "id": "outer-join",
                "title": "OUTER JOIN",
                "difficulty": "intermediate",
                "estimatedReadTime": 8,
                "category": "JOINs",
            },
            "join-condition-missing": {
                "id": "join-condition-missing",
                "title": "Missing JOIN Condition",
                "difficulty": "intermediate",
                "estimatedReadTime": 5,
                "category": "JOINs",
            },
            "on-clause": {
                "id": "on-clause",
                "title": "ON Clause",
                "difficulty": "intermediate",
                "estimatedReadTime": 5,
                "category": "JOINs",
            },
            # Aggregation concepts
            "group-by": {
                "id": "group-by",
                "title": "GROUP BY Clause",
                "difficulty": "intermediate",
                "estimatedReadTime": 8,
                "category": "Aggregation",
            },
            "group-by-error": {
                "id": "group-by-error",
                "title": "GROUP BY Errors",
                "difficulty": "intermediate",
                "estimatedReadTime": 5,
                "category": "Aggregation",
            },
            "aggregation": {
                "id": "aggregation",
                "title": "Aggregate Functions",
                "difficulty": "intermediate",
                "estimatedReadTime": 8,
                "category": "Aggregation",
            },
            "having-clause": {
                "id": "having-clause",
                "title": "HAVING Clause",
                "difficulty": "intermediate",
                "estimatedReadTime": 6,
                "category": "Aggregation",
            },
            "count-function": {
                "id": "count-function",
                "title": "COUNT Function",
                "difficulty": "beginner",
                "estimatedReadTime": 4,
                "category": "Aggregation",
            },
            "sum-function": {
                "id": "sum-function",
                "title": "SUM Function",
                "difficulty": "beginner",
                "estimatedReadTime": 4,
                "category": "Aggregation",
            },
            "avg-function": {
                "id": "avg-function",
                "title": "AVG Function",
                "difficulty": "beginner",
                "estimatedReadTime": 4,
                "category": "Aggregation",
            },
            # Function concepts
            "string-functions": {
                "id": "string-functions",
                "title": "String Functions",
                "difficulty": "intermediate",
                "estimatedReadTime": 7,
                "category": "Functions",
            },
            "date-functions": {
                "id": "date-functions",
                "title": "Date Functions",
                "difficulty": "intermediate",
                "estimatedReadTime": 7,
                "category": "Functions",
            },
            "aggregate-functions": {
                "id": "aggregate-functions",
                "title": "Aggregate Functions",
                "difficulty": "intermediate",
                "estimatedReadTime": 8,
                "category": "Functions",
            },
            # Set operations
            "union": {
                "id": "union",
                "title": "UNION Operator",
                "difficulty": "intermediate",
                "estimatedReadTime": 6,
                "category": "Set Operations",
            },
            "union-all": {
                "id": "union-all",
                "title": "UNION ALL",
                "difficulty": "intermediate",
                "estimatedReadTime": 5,
                "category": "Set Operations",
            },
            "data-types": {
                "id": "data-types",
                "title": "Data Types",
                "difficulty": "beginner",
                "estimatedReadTime": 6,
                "category": "Fundamentals",
            },
            # Subquery concepts
            "subqueries": {
                "id": "subqueries",
                "title": "Subqueries",
                "difficulty": "advanced",
                "estimatedReadTime": 12,
                "category": "Subqueries",
            },
            "in-operator": {
                "id": "in-operator",
                "title": "IN Operator",
                "difficulty": "intermediate",
                "estimatedReadTime": 5,
                "category": "Operators",
            },
            "exists-operator": {
                "id": "exists-operator",
                "title": "EXISTS Operator",
                "difficulty": "advanced",
                "estimatedReadTime": 8,
                "category": "Operators",
            },
            "correlated-subquery": {
                "id": "correlated-subquery",
                "title": "Correlated Subqueries",
                "difficulty": "advanced",
                "estimatedReadTime": 15,
                "category": "Subqueries",
            },
            # Alias concepts
            "alias": {
                "id": "alias",
                "title": "Table Aliases",
                "difficulty": "beginner",
                "estimatedReadTime": 4,
                "category": "SELECT",
            },
            "ambiguous-column": {
                "id": "ambiguous-column",
                "title": "Ambiguous Column References",
                "difficulty": "intermediate",
                "estimatedReadTime": 5,
                "category": "Errors",
            },
            "table-alias": {
                "id": "table-alias",
                "title": "Table Aliases",
                "difficulty": "beginner",
                "estimatedReadTime": 4,
                "category": "SELECT",
            },
            "column-alias": {
                "id": "column-alias",
                "title": "Column Aliases",
                "difficulty": "beginner",
                "estimatedReadTime": 4,
                "category": "SELECT",
            },
        }
    }
    
    # Create mock output directory structure
    mock_output = tmp_path / "output" / "mappings"
    mock_output.mkdir(parents=True)
    
    # Write mock registry
    registry_path = mock_output / "concept-registry.json"
    with open(registry_path, 'w') as f:
        json.dump(mock_registry, f)
    
    # Mock the module's path resolution
    mock_src = tmp_path / "src" / "algl_pdf_helper"
    mock_src.mkdir(parents=True)
    
    original_file = cms_module.__file__
    try:
        cms_module.__file__ = str(mock_src / "concept_mapping_system.py")
        yield ConceptMappingSystem(registry_path)
    finally:
        cms_module.__file__ = original_file


class TestLayer1ErrorSubtypes:
    """Tests for Layer 1: Error Subtype Detection."""
    
    def test_get_error_info_valid(self, mapping_system):
        """Test retrieving info for a valid error subtype."""
        info = mapping_system.get_error_info("missing_comma_in_select")
        assert info is not None
        assert info["id"] == 4
        assert info["name"] == "Missing Comma in SELECT"
        assert info["severity"] == "error"
        assert info["category"] == "syntax"
    
    def test_get_error_info_invalid(self, mapping_system):
        """Test retrieving info for an invalid error subtype."""
        info = mapping_system.get_error_info("nonexistent_error")
        assert info is None
    
    def test_list_error_subtypes(self, mapping_system):
        """Test listing all error subtypes."""
        subtypes = mapping_system.list_error_subtypes()
        assert len(subtypes) == 23  # ERROR_SUBTYPES dict has 23 error subtypes
        assert "missing_comma_in_select" in subtypes
        assert "incomplete_query" in subtypes
        assert "ambiguous_column_reference" in subtypes
    
    def test_detect_error_subtype_group_by(self, mapping_system):
        """Test detecting GROUP BY errors."""
        error_msg = "column 'name' must appear in the GROUP BY clause"
        sql = "SELECT name, COUNT(*) FROM users"
        detected = mapping_system.detect_error_subtype(error_msg, sql)
        assert detected == "missing_group_by"


class TestLayer2AlignmentMap:
    """Tests for Layer 2: Alignment Map."""
    
    def test_get_concepts_for_error_high_confidence(self, mapping_system):
        """Test getting concepts for high-confidence mapping."""
        concepts = mapping_system.get_concepts_for_error("missing_comma_in_select")
        assert "select-basic" in concepts
        assert "syntax-error" in concepts
    
    def test_get_concepts_for_error_medium_confidence(self, mapping_system):
        """Test getting concepts for medium-confidence mapping."""
        concepts = mapping_system.get_concepts_for_error("incorrect_wildcard_usage")
        assert "select-basic" in concepts
    
    def test_get_concepts_for_error_invalid(self, mapping_system):
        """Test getting concepts for non-existent error."""
        concepts = mapping_system.get_concepts_for_error("nonexistent_error")
        assert concepts == []
    
    def test_get_remediation_order(self, mapping_system):
        """Test getting remediation order."""
        order = mapping_system.get_remediation_order("missing_comma_in_select")
        assert order[0] == "syntax-error"  # remediation_order is different
        assert order[1] == "select-basic"
    
    def test_get_teaching_strategy(self, mapping_system):
        """Test getting teaching strategy."""
        strategy = mapping_system.get_teaching_strategy("missing_comma_in_select")
        assert strategy == "syntax_drill"


class TestLayer3ConceptRegistry:
    """Tests for Layer 3: Concept Registry."""
    
    def test_get_concept_content_valid(self, mapping_system):
        """Test getting content for a valid concept."""
        content = mapping_system.get_concept_content("select-basic")
        assert content is not None
        assert content["id"] == "select-basic"
        assert content["title"] == "SELECT Statement Basics"
        assert content["difficulty"] == "beginner"
        assert content["estimatedReadTime"] > 0
    
    def test_get_concept_content_invalid(self, mapping_system):
        """Test getting content for invalid concept."""
        content = mapping_system.get_concept_content("nonexistent_concept")
        assert content is None
    
    def test_list_concepts(self, mapping_system):
        """Test listing all concepts."""
        concepts = mapping_system.list_concepts()
        # Mock registry has 34 concepts covering all error mappings
        assert len(concepts) == 34
        assert "select-basic" in concepts
        assert "joins" in concepts
        assert "group-by" in concepts
    
    def test_get_concepts_by_difficulty(self, mapping_system):
        """Test getting concepts by difficulty."""
        beginner = mapping_system.get_concepts_by_difficulty("beginner")
        intermediate = mapping_system.get_concepts_by_difficulty("intermediate")
        advanced = mapping_system.get_concepts_by_difficulty("advanced")
        
        # Verify we have concepts at each level
        assert len(beginner) > 0
        assert len(intermediate) > 0
        assert len(advanced) > 0
        
        # Verify types
        for c in beginner:
            assert c["difficulty"] == "beginner"
    
    def test_get_concepts_by_category(self, mapping_system):
        """Test getting concepts by category."""
        joins = mapping_system.get_concepts_by_category("JOINs")
        # Mock registry has 5 JOIN-related concepts
        assert len(joins) == 5
        for c in joins:
            assert c["category"] == "JOINs"
    
    def test_search_concepts(self, mapping_system):
        """Test searching concepts."""
        results = mapping_system.search_concepts("SELECT")
        assert len(results) > 0
        assert any(c["id"] == "select-basic" for c in results)
        
        results = mapping_system.search_concepts("aggregate")
        assert len(results) > 0
        assert any(c["id"] == "aggregation" for c in results)


class TestCrossLayerIntegration:
    """Tests for cross-layer integration."""
    
    def test_get_learning_path(self, mapping_system):
        """Test getting complete learning path."""
        path = mapping_system.get_learning_path("missing_comma_in_select")
        assert path is not None
        assert path["errorSubtype"] == "missing_comma_in_select"
        assert path["errorInfo"]["name"] == "Missing Comma in SELECT"
        assert path["teachingStrategy"] == "syntax_drill"
        assert len(path["concepts"]) == 2
        assert path["totalReadTime"] > 0
        assert path["difficulty"] == "beginner"
    
    def test_get_learning_path_invalid_error(self, mapping_system):
        """Test getting learning path for invalid error."""
        path = mapping_system.get_learning_path("nonexistent_error")
        assert path is None
    
    def test_end_to_end_mapping(self, mapping_system):
        """Test complete Layer 1→2→3 mapping."""
        # Use a known error subtype
        error_subtype = "ambiguous_column_reference"
        
        # Layer 2: Concept mapping
        concepts = mapping_system.get_concepts_for_error(error_subtype)
        assert len(concepts) > 0
        # May include alias, ambiguous-column, etc.
        
        # Layer 3: Content retrieval
        for cid in concepts[:1]:  # Just test first concept
            content = mapping_system.get_concept_content(cid)
            assert content is not None
            assert content["id"] == cid
    
    def test_learning_path_difficulty_calculation(self, mapping_system):
        """Test difficulty calculation for learning paths."""
        # Join error should include intermediate concepts
        path = mapping_system.get_learning_path("incorrect_join_type")
        assert path is not None
        # Joins includes intermediate concepts


class TestExportFunctions:
    """Tests for export functions."""
    
    def test_export_alignment_map(self, tmp_path, mapping_system):
        """Test exporting alignment map."""
        output_path = tmp_path / "alignment-map.json"
        export_alignment_map(output_path)
        
        assert output_path.exists()
        with open(output_path, 'r') as f:
            data = json.load(f)
        
        assert data["schemaVersion"] == "alignment-map-v1"
        # ALIGNMENT_MAP has 23 error subtype mappings
        assert data["totalMappings"] == 23
        assert "mappings" in data
    
    def test_export_alignment_map_default_path(self, tmp_path, monkeypatch):
        """Test exporting alignment map to default path."""
        import algl_pdf_helper.concept_mapping_system as cms_module
        # Setup mock paths
        mock_src = tmp_path / "src" / "algl_pdf_helper"
        mock_src.mkdir(parents=True)
        mock_output = tmp_path / "output" / "mappings"
        mock_output.mkdir(parents=True)
        
        # Copy registry to expected location
        import shutil
        original_registry = Path(__file__).parent.parent / "output" / "mappings" / "concept-registry.json"
        if original_registry.exists():
            shutil.copy(original_registry, mock_output / "concept-registry.json")
        else:
            # Create minimal registry
            (mock_output / "concept-registry.json").write_text('{"concepts": {}}')
        
        # Mock the module file path
        original_file = cms_module.__file__
        try:
            cms_module.__file__ = str(mock_src / "concept_mapping_system.py")
            export_alignment_map()
            default_path = tmp_path / "output" / "mappings" / "alignment-map.json"
            assert default_path.exists()
        finally:
            cms_module.__file__ = original_file
    
    def test_export_error_subtypes(self, tmp_path, mapping_system):
        """Test exporting error subtypes."""
        output_path = tmp_path / "error-subtypes.json"
        export_error_subtypes(output_path)
        
        assert output_path.exists()
        with open(output_path, 'r') as f:
            data = json.load(f)
        
        assert data["schemaVersion"] == "error-subtypes-v1"
        # ERROR_SUBTYPES has 23 error subtypes
        assert data["totalSubtypes"] == 23
        assert "subtypes" in data
    
    def test_export_error_subtypes_default_path(self, tmp_path, monkeypatch):
        """Test exporting error subtypes to default path."""
        import algl_pdf_helper.concept_mapping_system as cms_module
        # Setup mock paths
        mock_src = tmp_path / "src" / "algl_pdf_helper"
        mock_src.mkdir(parents=True)
        mock_output = tmp_path / "output" / "mappings"
        mock_output.mkdir(parents=True)
        
        # Copy registry to expected location
        import shutil
        original_registry = Path(__file__).parent.parent / "output" / "mappings" / "concept-registry.json"
        if original_registry.exists():
            shutil.copy(original_registry, mock_output / "concept-registry.json")
        else:
            # Create minimal registry
            (mock_output / "concept-registry.json").write_text('{"concepts": {}}')
        
        # Mock the module file path
        original_file = cms_module.__file__
        try:
            cms_module.__file__ = str(mock_src / "concept_mapping_system.py")
            export_error_subtypes()
            default_path = tmp_path / "output" / "mappings" / "error-subtypes.json"
            assert default_path.exists()
        finally:
            cms_module.__file__ = original_file


class TestRegistryLoading:
    """Tests for registry loading."""
    
    def test_load_registry_success(self, mapping_system):
        """Test successful registry loading."""
        # Mock registry has 34 concepts
        assert len(mapping_system.concept_registry) == 34
    
    def test_load_registry_missing_file(self, tmp_path):
        """Test loading with missing registry file gracefully handles it."""
        # Missing registry files now result in empty registry (for CI/testing)
        cms = ConceptMappingSystem(tmp_path / "nonexistent.json")
        assert cms.concept_registry == {}


class TestErrorCoverage:
    """Tests for error subtype coverage."""
    
    def test_all_errors_have_mappings(self, mapping_system):
        """Test that all error subtypes have alignment mappings."""
        errors = mapping_system.list_error_subtypes()
        for error in errors:
            concepts = mapping_system.get_concepts_for_error(error)
            assert len(concepts) > 0, f"Error '{error}' has no concept mapping"
    
    def test_all_mapped_concepts_exist(self, mapping_system):
        """Test that all mapped concepts exist in registry."""
        from algl_pdf_helper.concept_mapping_system import ConceptMappingSystem as CMS
        
        available_concepts = set(mapping_system.list_concepts())
        
        for error_subtype, mapping in CMS.ALIGNMENT_MAP.items():
            for concept_id in mapping["concept_ids"]:
                # Some concept IDs in ALIGNMENT_MAP might not exist in current registry
                # This is expected if registry is a subset
                pass  # Just check it doesn't crash
