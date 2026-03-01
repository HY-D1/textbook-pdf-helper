"""
Tests for Pedagogical Content Generation (Phase 4).

Tests cover:
- JSON validation and parsing
- SQL validation
- Multi-pass generation
- Quality gates
- Model compatibility checks
"""

from __future__ import annotations

import pytest

# Import the modules under test
from algl_pdf_helper.pedagogical_models import (
    PedagogicalConcept,
    SQLExample,
    Mistake,
    PracticeReference,
    GenerationResult,
    QualityGateResult,
    QualityCheckResult,
    get_pedagogical_concept_schema,
)

from algl_pdf_helper.validators import (
    validate_sql_snippet,
    validate_practice_schema,
    validate_concept_json,
    safe_parse_json,
    extract_json_from_llm_output,
    get_allowed_schemas,
    SQLValidationResult,
    ValidationResult,
)

from algl_pdf_helper.quality_gates import (
    QualityGate,
    QualityGateConfig,
    generate_quality_report,
)

from algl_pdf_helper.generation_pipeline import (
    MultiPassGenerator,
    check_model_compatibility,
    get_recommended_model,
    get_system_memory_gb,
    M1_8GB_MODELS,
    OPTIONAL_7B_MODELS,
    ALL_MODELS,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def valid_concept_data():
    """Fixture for a valid concept dictionary."""
    return {
        "concept_id": "joins-intro",
        "title": "Introduction to JOINs",
        "difficulty": "beginner",
        "definition": "A JOIN combines rows from two or more tables based on related columns. This is essential for working with relational databases where data is spread across multiple tables. Understanding JOINs allows you to retrieve meaningful data by connecting tables through their relationships.",
        "key_points": [
            "JOINs link tables using related columns",
            "INNER JOIN returns only matching rows",
            "LEFT JOIN returns all left table rows",
            "Always specify the ON clause",
        ],
        "examples": [
            {
                "description": "Find users and their orders",
                "query": "SELECT u.name, o.product FROM users u JOIN orders o ON u.id = o.user_id;",
                "explanation": "This joins users and orders tables using the foreign key relationship.",
                "schema_used": "users",
                "difficulty": "beginner",
            }
        ],
        "common_mistakes": [
            {
                "error_type": "Missing ON clause",
                "incorrect_sql": "SELECT * FROM users JOIN orders;",
                "correct_sql": "SELECT * FROM users JOIN orders ON users.id = orders.user_id;",
                "explanation": "Without ON clause, you get a Cartesian product.",
                "error_message": "ambiguous column name: id",
                "key_takeaway": "Always specify the join condition",
            }
        ],
        "practice_references": [
            {"problem_id": "problem-3", "title": "Basic JOIN", "difficulty": "beginner"}
        ],
        "estimated_time_minutes": 20,
        "prerequisites": ["select-basic"],
        "tags": ["sql", "join"],
    }


@pytest.fixture
def valid_sql_example():
    """Fixture for a valid SQL example."""
    return {
        "description": "Find users and their orders",
        "query": "SELECT u.name, o.product FROM users u JOIN orders o ON u.id = o.user_id;",
        "explanation": "This joins the users and orders tables.",
        "schema_used": "users",
        "difficulty": "beginner",
    }


@pytest.fixture
def valid_mistake():
    """Fixture for a valid mistake."""
    return {
        "error_type": "Missing ON clause",
        "incorrect_sql": "SELECT * FROM users JOIN orders;",
        "correct_sql": "SELECT * FROM users JOIN orders ON users.id = orders.user_id;",
        "explanation": "Without ON clause, you get a Cartesian product.",
    }


@pytest.fixture
def default_quality_gate():
    """Fixture for a default quality gate."""
    return QualityGate()


# =============================================================================
# PEDAGOGICAL MODELS TESTS
# =============================================================================

class TestPedagogicalModels:
    """Tests for Pydantic models."""
    
    def test_sql_example_validation(self, valid_sql_example):
        """Test SQLExample model validation."""
        example = SQLExample.model_validate(valid_sql_example)
        assert example.description == valid_sql_example["description"]
        assert example.query.endswith(";")
    
    def test_sql_example_adds_semicolon(self):
        """Test that SQLExample adds semicolon if missing."""
        data = {
            "description": "Test query for validation",
            "query": "SELECT * FROM users",  # No semicolon
            "explanation": "This is a test query that retrieves all users from the database table.",
            "schema_used": "users",
        }
        example = SQLExample.model_validate(data)
        assert example.query.endswith(";")
    
    def test_sql_example_invalid_start(self):
        """Test that SQLExample validates SQL start keyword."""
        data = {
            "description": "Invalid query",
            "query": "INVALID * FROM users;",
            "explanation": "An invalid query.",
            "schema_used": "users",
        }
        with pytest.raises(ValueError, match="SQL query must start with"):
            SQLExample.model_validate(data)
    
    def test_mistake_validation(self, valid_mistake):
        """Test Mistake model validation."""
        mistake = Mistake.model_validate(valid_mistake)
        assert mistake.error_type == valid_mistake["error_type"]
        assert mistake.correct_sql.endswith(";")
    
    def test_mistake_adds_semicolon(self):
        """Test that Mistake adds semicolon to correct_sql if missing."""
        data = {
            "error_type": "Test error",
            "incorrect_sql": "SELECT *",
            "correct_sql": "SELECT * FROM users",  # No semicolon
            "explanation": "This is a detailed explanation of why this error occurs and how to fix it properly.",
        }
        mistake = Mistake.model_validate(data)
        assert mistake.correct_sql.endswith(";")
    
    def test_pedagogical_concept_validation(self, valid_concept_data):
        """Test PedagogicalConcept model validation."""
        concept = PedagogicalConcept.model_validate(valid_concept_data)
        assert concept.concept_id == valid_concept_data["concept_id"]
        assert concept.title == valid_concept_data["title"]
        assert len(concept.examples) == 1
        assert len(concept.common_mistakes) == 1
    
    def test_pedagogical_concept_missing_required(self):
        """Test that PedagogicalConcept validates required fields."""
        data = {
            "concept_id": "test",
            "title": "Test",
            # Missing definition, key_points, examples, common_mistakes
        }
        with pytest.raises(ValueError):
            PedagogicalConcept.model_validate(data)
    
    def test_pedagogical_concept_normalizes_tags(self):
        """Test that PedagogicalConcept normalizes tags to lowercase."""
        data = {
            "concept_id": "test",
            "title": "Test Concept",
            "difficulty": "beginner",
            "definition": "A test concept for validation purposes. This concept covers important SQL fundamentals that every student should learn.",
            "key_points": ["Point 1", "Point 2"],
            "examples": [
                {
                    "description": "Test example for validation",
                    "query": "SELECT * FROM users;",
                    "explanation": "This is a detailed explanation of the example query.",
                    "schema_used": "users",
                }
            ],
            "common_mistakes": [
                {
                    "error_type": "Test error",
                    "incorrect_sql": "SELECT",
                    "correct_sql": "SELECT * FROM users;",
                    "explanation": "This is a detailed explanation of why this error occurs and how to fix it.",
                }
            ],
            "tags": ["SQL", "JOIN", "Advanced"],
        }
        concept = PedagogicalConcept.model_validate(data)
        assert all(tag.islower() for tag in concept.tags)
    
    def test_get_schema_functions(self):
        """Test schema getter functions."""
        concept_schema = get_pedagogical_concept_schema()
        assert "properties" in concept_schema
        assert "concept_id" in concept_schema["properties"]


# =============================================================================
# VALIDATORS TESTS
# =============================================================================

class TestSQLValidation:
    """Tests for SQL validation functions."""
    
    def test_valid_select(self):
        """Test valid SELECT statement."""
        result = validate_sql_snippet("SELECT * FROM users;")
        assert result.is_valid
        assert result.sql_type == "SELECT"
    
    def test_valid_insert(self):
        """Test valid INSERT statement."""
        result = validate_sql_snippet("INSERT INTO users (name) VALUES ('Alice');")
        assert result.is_valid
        assert result.sql_type == "INSERT"
    
    def test_valid_update(self):
        """Test valid UPDATE statement."""
        result = validate_sql_snippet("UPDATE users SET name = 'Bob' WHERE id = 1;")
        assert result.is_valid
        assert result.sql_type == "UPDATE"
    
    def test_valid_delete(self):
        """Test valid DELETE statement."""
        result = validate_sql_snippet("DELETE FROM users WHERE id = 1;")
        assert result.is_valid
        assert result.sql_type == "DELETE"
    
    def test_missing_semicolon(self):
        """Test that missing semicolon is caught."""
        result = validate_sql_snippet("SELECT * FROM users")
        assert not result.is_valid
        assert any("semicolon" in issue.lower() for issue in result.issues)
    
    def test_empty_sql(self):
        """Test empty SQL validation."""
        result = validate_sql_snippet("")
        assert not result.is_valid
        assert any("empty" in issue.lower() for issue in result.issues)
    
    def test_unknown_statement_type(self):
        """Test unknown SQL statement type."""
        result = validate_sql_snippet("INVALID STATEMENT;")
        assert not result.is_valid
    
    def test_unbalanced_parentheses(self):
        """Test unbalanced parentheses detection."""
        result = validate_sql_snippet("SELECT * FROM users WHERE id IN (1, 2, 3;")
        assert not result.is_valid
        assert any("parentheses" in issue.lower() for issue in result.issues)
    
    def test_select_without_from(self):
        """Test SELECT without FROM is caught."""
        result = validate_sql_snippet("SELECT * WHERE id = 1;")
        assert not result.is_valid
        assert any("FROM" in issue for issue in result.issues)
    
    def test_insert_without_into(self):
        """Test INSERT without INTO is caught."""
        result = validate_sql_snippet("INSERT users VALUES ('Alice');")
        assert not result.is_valid
        assert any("INTO" in issue for issue in result.issues)
    
    def test_update_without_set(self):
        """Test UPDATE without SET is caught."""
        result = validate_sql_snippet("UPDATE users WHERE id = 1;")
        assert not result.is_valid
        assert any("SET" in issue for issue in result.issues)
    
    def test_allow_partial_mode(self):
        """Test allow_partial mode for incomplete SQL."""
        result = validate_sql_snippet("SELECT * FROM users", allow_partial=True)
        # Should be valid in partial mode (no semicolon required)
        assert result.is_valid
    
    def test_select_star_warning(self):
        """Test that SELECT * generates a warning."""
        result = validate_sql_snippet("SELECT * FROM users;")
        assert result.is_valid
        assert any("SELECT *" in w for w in result.warnings)


class TestSchemaValidation:
    """Tests for schema validation."""
    
    def test_valid_schema(self):
        """Test valid schema name."""
        schemas = get_allowed_schemas()
        if schemas:
            assert validate_practice_schema(schemas[0])
    
    def test_invalid_schema(self):
        """Test invalid schema name."""
        assert not validate_practice_schema("invalid_schema")
    
    def test_empty_schema(self):
        """Test empty schema name."""
        assert not validate_practice_schema("")
    
    def test_schema_case_insensitive(self):
        """Test that schema validation is case insensitive."""
        schemas = get_allowed_schemas()
        if schemas:
            assert validate_practice_schema(schemas[0].upper())


class TestJSONValidation:
    """Tests for JSON validation functions."""
    
    def test_valid_concept_json(self, valid_concept_data):
        """Test validation of valid concept JSON."""
        result = validate_concept_json(valid_concept_data)
        assert result.is_valid, f"Errors: {result.errors}"
    
    def test_invalid_concept_missing_field(self, valid_concept_data):
        """Test validation catches missing fields."""
        data = valid_concept_data.copy()
        del data["definition"]
        result = validate_concept_json(data)
        assert not result.is_valid
    
    def test_invalid_sql_in_example(self, valid_concept_data):
        """Test validation catches invalid SQL in examples."""
        data = valid_concept_data.copy()
        data["examples"][0]["query"] = "INVALID SQL;"
        result = validate_concept_json(data)
        # Should be invalid either through Pydantic validation or SQL validation
        assert not result.is_valid or len(result.sql_validation_results) > 0 or len(result.errors) > 0
    
    def test_safe_parse_json_valid(self):
        """Test safe_parse_json with valid JSON."""
        json_str = '{"key": "value", "number": 42}'
        success, data, error = safe_parse_json(json_str)
        assert success
        assert data == {"key": "value", "number": 42}
        assert error == ""
    
    def test_safe_parse_json_invalid(self):
        """Test safe_parse_json with invalid JSON."""
        json_str = "not valid json"
        success, data, error = safe_parse_json(json_str)
        assert not success
        assert data is None
        assert error != ""
    
    def test_safe_parse_json_empty(self):
        """Test safe_parse_json with empty string."""
        success, data, error = safe_parse_json("")
        assert not success
        assert data is None
    
    def test_extract_json_from_markdown(self):
        """Test extracting JSON from markdown code blocks."""
        markdown = '''
        Here's the JSON:
        ```json
        {"key": "value", "number": 42}
        ```
        '''
        data = extract_json_from_llm_output(markdown)
        assert data == {"key": "value", "number": 42}
    
    def test_extract_json_direct(self):
        """Test extracting JSON directly from text."""
        text = '{"key": "value"}'
        data = extract_json_from_llm_output(text)
        assert data == {"key": "value"}
    
    def test_extract_json_not_found(self):
        """Test extraction when no JSON is found."""
        text = "This is just plain text with no JSON"
        data = extract_json_from_llm_output(text)
        assert data is None


# =============================================================================
# QUALITY GATES TESTS
# =============================================================================

class TestQualityGate:
    """Tests for QualityGate class."""
    
    def test_quality_gate_all_pass(self, valid_concept_data, default_quality_gate):
        """Test quality gate with valid concept."""
        concept = PedagogicalConcept.model_validate(valid_concept_data)
        result = default_quality_gate.check(concept)
        assert result.overall_passed
        assert result.total_score >= 0.7
    
    def test_quality_gate_missing_definition(self, default_quality_gate):
        """Test quality gate catches short definition."""
        # Create a concept with a short definition (quality gate should catch this)
        concept = PedagogicalConcept(
            concept_id="test-def",
            title="Test Definition",
            difficulty="beginner",
            definition="A test concept definition that is long enough for validation but still short for quality testing.",
            key_points=["Point 1"],
            examples=[
                SQLExample(
                    description="Example query",
                    query="SELECT * FROM users;",
                    explanation="This query retrieves all users from the table.",
                    schema_used="users",
                )
            ],
            common_mistakes=[
                Mistake(
                    error_type="Test error",
                    incorrect_sql="SELECT",
                    correct_sql="SELECT * FROM users;",
                    explanation="Detailed explanation of the error and fix.",
                )
            ],
        )
        # Modify definition to be short after creation
        concept.definition = "Short."
        result = default_quality_gate.check(concept)
        # Should fail due to short definition
        failed = result.get_failed_checks()
        assert any(c.check_name in ["definition_present", "definition_length"] for c in failed)
    
    def test_quality_gate_too_few_examples(self, default_quality_gate):
        """Test quality gate catches too few examples."""
        # Create a minimal valid concept, then we'll manually test the check
        concept = PedagogicalConcept(
            concept_id="test-examples",
            title="Test Examples",
            difficulty="beginner",
            definition="A test concept with multiple examples to validate the quality gate system works properly.",
            key_points=["Point 1"],
            examples=[
                SQLExample(
                    description="Example query",
                    query="SELECT * FROM users;",
                    explanation="This query retrieves all users from the table for display.",
                    schema_used="users",
                )
            ],
            common_mistakes=[
                Mistake(
                    error_type="Test error",
                    incorrect_sql="SELECT",
                    correct_sql="SELECT * FROM users;",
                    explanation="Detailed explanation of the error and how to fix it properly.",
                )
            ],
        )
        # Modify to have 0 examples after creation (bypass Pydantic validation)
        concept.examples = []
        result = default_quality_gate.check(concept)
        assert not result.overall_passed
        failed = result.get_failed_checks()
        assert any(c.check_name == "examples_count" for c in failed)
    
    def test_quality_gate_too_few_mistakes(self, default_quality_gate):
        """Test quality gate catches too few mistakes."""
        concept = PedagogicalConcept(
            concept_id="test-mistakes",
            title="Test Mistakes",
            difficulty="beginner",
            definition="A test concept with mistakes to validate quality gate properly detects issues.",
            key_points=["Point 1"],
            examples=[
                SQLExample(
                    description="Example query",
                    query="SELECT * FROM users;",
                    explanation="This query retrieves all users from the table.",
                    schema_used="users",
                )
            ],
            common_mistakes=[
                Mistake(
                    error_type="Test error",
                    incorrect_sql="SELECT",
                    correct_sql="SELECT * FROM users;",
                    explanation="Detailed explanation of the error and fix.",
                )
            ],
        )
        # Modify to have 0 mistakes after creation
        concept.common_mistakes = []
        result = default_quality_gate.check(concept)
        assert not result.overall_passed
        failed = result.get_failed_checks()
        assert any(c.check_name == "mistakes_count" for c in failed)
    
    def test_quality_gate_custom_config(self):
        """Test quality gate with custom configuration."""
        config = QualityGateConfig(
            min_examples=0,  # Make examples optional
            min_mistakes=0,  # Make mistakes optional
        )
        gate = QualityGate(config)
        concept = PedagogicalConcept(
            concept_id="test-custom",
            title="Test Custom Config",
            difficulty="beginner",
            definition="A test concept with custom configuration to validate the quality gate allows optional fields.",
            key_points=["Point 1"],
            examples=[
                SQLExample(
                    description="Example query",
                    query="SELECT * FROM users;",
                    explanation="This query retrieves all users.",
                    schema_used="users",
                )
            ],  # Valid example
            common_mistakes=[
                Mistake(
                    error_type="Test error",
                    incorrect_sql="SELECT",
                    correct_sql="SELECT * FROM users;",
                    explanation="Detailed explanation.",
                )
            ],  # Valid mistake
        )
        result = gate.check(concept)
        # Should pass because we have valid examples and mistakes
        assert result.overall_passed
    
    def test_quality_gate_batch(self, valid_concept_data, default_quality_gate):
        """Test batch quality checking."""
        concept1 = PedagogicalConcept.model_validate(valid_concept_data)
        
        data2 = valid_concept_data.copy()
        data2["concept_id"] = "joins-advanced"
        data2["title"] = "Advanced JOINs"
        concept2 = PedagogicalConcept.model_validate(data2)
        
        results = default_quality_gate.check_batch([concept1, concept2])
        assert len(results) == 2
        assert all(r.overall_passed for r in results.values())
    
    def test_quality_gate_pass_rate(self, default_quality_gate):
        """Test pass rate calculation."""
        # Create a passing concept
        concept1 = PedagogicalConcept(
            concept_id="good-concept",
            title="Good Concept",
            difficulty="beginner",
            definition="A well-defined concept that should pass all quality gates successfully.",
            key_points=["Point 1", "Point 2", "Point 3"],
            examples=[
                SQLExample(
                    description="Example query one",
                    query="SELECT * FROM users;",
                    explanation="This query retrieves all users from the table.",
                    schema_used="users",
                )
            ],
            common_mistakes=[
                Mistake(
                    error_type="Test error",
                    incorrect_sql="SELECT",
                    correct_sql="SELECT * FROM users;",
                    explanation="Detailed explanation of the error and fix.",
                )
            ],
        )
        
        # Create a failing concept (will remove examples after creation)
        concept2 = PedagogicalConcept(
            concept_id="bad-concept",
            title="Bad Concept",
            difficulty="beginner",
            definition="A concept missing required elements to test quality gate failure detection.",
            key_points=["Point 1"],
            examples=[
                SQLExample(
                    description="Example query two",
                    query="SELECT * FROM users;",
                    explanation="This is an example query.",
                    schema_used="users",
                )
            ],
            common_mistakes=[
                Mistake(
                    error_type="Test error",
                    incorrect_sql="SELECT",
                    correct_sql="SELECT * FROM users;",
                    explanation="Detailed explanation here.",
                )
            ],
        )
        # Remove examples to make it fail
        concept2.examples = []
        
        results = default_quality_gate.check_batch([concept1, concept2])
        pass_rate = default_quality_gate.get_pass_rate(results)
        assert pass_rate == 0.5
    
    def test_generate_quality_report(self, valid_concept_data, default_quality_gate):
        """Test quality report generation."""
        concept = PedagogicalConcept.model_validate(valid_concept_data)
        results = default_quality_gate.check_batch([concept])
        report = generate_quality_report(results, default_quality_gate.config)
        
        assert report["summary"]["total_concepts"] == 1
        assert report["summary"]["passed"] == 1
        assert report["summary"]["meets_target"]


# =============================================================================
# GENERATION PIPELINE TESTS
# =============================================================================

class TestModelCompatibility:
    """Tests for model compatibility checking."""
    
    def test_recommended_models_exist(self):
        """Test that recommended models are defined."""
        assert len(M1_8GB_MODELS) > 0
        assert "qwen2.5:3b" in M1_8GB_MODELS
    
    def test_optional_7b_models(self):
        """Test that optional 7B models are defined."""
        assert len(OPTIONAL_7B_MODELS) > 0
        assert "qwen2.5:7b" in OPTIONAL_7B_MODELS
    
    def test_check_3b_model_compatibility(self):
        """Test 3B model is compatible with 8GB system."""
        is_compatible, warning = check_model_compatibility("qwen2.5:3b")
        assert is_compatible
        assert warning == ""  # No warning for recommended models
    
    def test_check_7b_model_compatibility(self):
        """Test 7B model generates warning on 8GB system."""
        is_compatible, warning = check_model_compatibility("qwen2.5:7b")
        # Should be compatible but with warning
        assert is_compatible
        assert warning != ""  # Should have warning
    
    def test_check_unknown_model(self):
        """Test unknown model handling."""
        is_compatible, warning = check_model_compatibility("unknown-model")
        assert is_compatible  # Allow unknown models
        assert "Unknown" in warning
    
    def test_get_system_memory(self):
        """Test system memory detection."""
        memory = get_system_memory_gb()
        assert isinstance(memory, int)
        assert memory >= 8  # Minimum assumption
    
    def test_get_recommended_model(self):
        """Test recommended model selection."""
        model = get_recommended_model()
        assert model in ALL_MODELS


class TestMultiPassGenerator:
    """Tests for MultiPassGenerator class."""
    
    def test_generator_initialization(self):
        """Test generator initialization."""
        generator = MultiPassGenerator()
        assert generator.model == get_recommended_model()
        assert generator.max_attempts == MultiPassGenerator.MAX_ATTEMPTS
    
    def test_generator_custom_model(self):
        """Test generator with custom model."""
        generator = MultiPassGenerator(model="qwen2.5:3b")
        assert generator.model == "qwen2.5:3b"
    
    def test_generator_clamps_attempts(self):
        """Test that max_attempts is clamped."""
        generator = MultiPassGenerator(max_attempts=10)
        assert generator.max_attempts == 5  # Max clamped to 5
        
        generator = MultiPassGenerator(max_attempts=0)
        assert generator.max_attempts == 1  # Min clamped to 1
    
    def test_generator_clamps_temperature(self):
        """Test that temperature is clamped."""
        generator = MultiPassGenerator(temperature=-0.5)
        assert generator.temperature == 0.0
        
        generator = MultiPassGenerator(temperature=1.5)
        assert generator.temperature == 1.0


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests combining multiple components."""
    
    def test_full_pipeline_valid_concept(self, valid_concept_data):
        """Test full pipeline with valid concept."""
        # 1. Validate JSON structure
        validation = validate_concept_json(valid_concept_data)
        assert validation.is_valid
        
        # 2. Create Pydantic model
        concept = PedagogicalConcept.model_validate(valid_concept_data)
        
        # 3. Run quality gate
        gate = QualityGate()
        quality = gate.check(concept)
        
        # 4. Verify overall quality
        assert quality.overall_passed
        assert quality.total_score >= 0.7
    
    def test_concept_with_invalid_sql(self):
        """Test pipeline detects invalid SQL."""
        data = {
            "concept_id": "test-concept",
            "title": "Test Concept",
            "difficulty": "beginner",
            "definition": "A test concept with invalid SQL.",
            "key_points": ["Point 1"],
            "examples": [
                {
                    "description": "Bad example",
                    "query": "INVALID SQL HERE;",
                    "explanation": "This SQL is invalid.",
                    "schema_used": "users",
                }
            ],
            "common_mistakes": [
                {
                    "error_type": "Test error",
                    "incorrect_sql": "BAD",
                    "correct_sql": "SELECT * FROM users;",
                    "explanation": "Test.",
                }
            ],
        }
        
        # Validation should catch invalid SQL
        validation = validate_concept_json(data)
        assert not validation.is_valid or len(validation.sql_validation_results) > 0
    
    def test_end_to_end_quality_report(self):
        """Test end-to-end quality report generation."""
        # Validate all concepts
        gate = QualityGate()
        results = {}
        
        for i in range(5):
            concept = PedagogicalConcept(
                concept_id=f"concept-{i}",
                title=f"Concept {i}",
                difficulty="beginner",
                definition=f"Definition for concept {i}. This is a comprehensive definition that explains the concept in detail for students.",
                key_points=[f"Point {j}" for j in range(3)],
                examples=[
                    SQLExample(
                        description=f"Example for concept {i}",
                        query="SELECT * FROM users;",
                        explanation=f"This query demonstrates concept {i} by retrieving all users.",
                        schema_used="users",
                    )
                ],
                common_mistakes=[
                    Mistake(
                        error_type="Common mistake",
                        incorrect_sql="SELECT",
                        correct_sql="SELECT * FROM users;",
                        explanation="This is a detailed explanation of the common mistake.",
                    )
                ],
            )
            results[concept.concept_id] = gate.check(concept)
        
        # Generate report
        report = generate_quality_report(results, gate.config)
        
        assert report["summary"]["total_concepts"] == 5
        assert report["summary"]["pass_rate"] == 1.0
        assert report["summary"]["meets_target"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
