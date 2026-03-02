#!/usr/bin/env python3
"""
Comprehensive Test Suite for Pedagogical Generation System

Tests all components:
1. Pydantic models validation
2. Validators (SQL, schema, JSON)
3. Multi-pass generation pipeline
4. Quality gates
5. Prompts
6. Edge cases
"""

from __future__ import annotations

import sys
import json
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Test results collection
test_results = {
    "passed": [],
    "failed": [],
    "warnings": [],
}


def test_section(name: str):
    """Decorator to mark test sections."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print('='*60)
    return lambda f: f


def assert_test(condition: bool, test_name: str, details: str = ""):
    """Record test result."""
    if condition:
        test_results["passed"].append(test_name)
        print(f"  ✅ PASS: {test_name}")
    else:
        test_results["failed"].append((test_name, details))
        print(f"  ❌ FAIL: {test_name}")
        if details:
            print(f"     Details: {details}")


def warn(message: str):
    """Record warning."""
    test_results["warnings"].append(message)
    print(f"  ⚠️  WARN: {message}")


# =============================================================================
# 1. TEST PYDANTIC MODELS
# =============================================================================

@test_section("Pydantic Models")
def test_pydantic_models():
    from algl_pdf_helper.pedagogical_models import (
        PedagogicalConcept, SQLExample, Mistake, 
        GenerationResult, QualityGateResult, QualityCheckResult
    )
    
    # Test 1: Create valid SQLExample
    try:
        example = SQLExample(
            description="Basic query example",
            query="SELECT * FROM users;",
            explanation="This query selects all columns from the users table.",
            schema_used="users",
            difficulty="beginner"
        )
        assert_test(True, "SQLExample creation")
        assert_test(example.query.endswith(";"), "SQLExample semicolon validation")
    except Exception as e:
        assert_test(False, "SQLExample creation", str(e))
    
    # Test 2: SQLExample auto-adds semicolon
    try:
        example = SQLExample(
            description="Basic query example",
            query="SELECT * FROM users",  # No semicolon
            explanation="This query selects all columns from the users table.",
            schema_used="users",
        )
        assert_test(example.query.endswith(";"), "SQLExample auto-semicolon")
    except Exception as e:
        assert_test(False, "SQLExample auto-semicolon", str(e))
    
    # Test 3: SQLExample validates SQL starts with keyword
    try:
        example = SQLExample(
            description="Invalid SQL",
            query="INVALID * FROM users;",
            explanation="This should fail.",
            schema_used="users",
        )
        assert_test(False, "SQLExample keyword validation (should have failed)")
    except Exception as e:
        assert_test(True, "SQLExample keyword validation")
    
    # Test 4: Create valid Mistake
    try:
        mistake = Mistake(
            error_type="Missing WHERE clause",
            incorrect_sql="DELETE FROM users",
            correct_sql="DELETE FROM users WHERE user_id = 1;",
            explanation="Without WHERE, all rows are deleted!",
            error_message="No error message shown",
            key_takeaway="Always use WHERE with DELETE"
        )
        assert_test(True, "Mistake creation")
        assert_test(mistake.correct_sql.endswith(";"), "Mistake correct_sql semicolon")
    except Exception as e:
        assert_test(False, "Mistake creation", str(e))
    
    # Test 5: Create valid PedagogicalConcept
    try:
        concept = PedagogicalConcept(
            concept_id="select-basic",
            title="SELECT Statement Basics",
            difficulty="beginner",
            definition="The SELECT statement is used to retrieve data from one or more tables in a database. It is the most commonly used SQL command and forms the foundation of data querying. With SELECT, you can specify which columns to retrieve, filter rows with WHERE, sort results with ORDER BY, and aggregate data with GROUP BY.",
            key_points=[
                "SELECT retrieves data from tables",
                "Use * for all columns or specify column names",
                "Always include a FROM clause",
                "Results can be filtered, sorted, and grouped"
            ],
            examples=[
                SQLExample(
                    description="Select all columns",
                    query="SELECT * FROM users;",
                    explanation="Retrieves all columns and rows from the users table.",
                    schema_used="users",
                    difficulty="beginner"
                )
            ],
            common_mistakes=[
                Mistake(
                    error_type="Forgetting FROM clause",
                    incorrect_sql="SELECT * WHERE age > 18;",
                    correct_sql="SELECT * FROM users WHERE age > 18;",
                    explanation="Every SELECT query needs a FROM clause to specify the table."
                )
            ],
            estimated_time_minutes=15,
            tags=["sql", "select", "query"]
        )
        assert_test(True, "PedagogicalConcept creation")
        
        # Check tags are lowercase
        assert_test(all(t.islower() for t in concept.tags), "Tags lowercase normalization")
    except Exception as e:
        assert_test(False, "PedagogicalConcept creation", str(e))
    
    # Test 6: Definition length validation
    try:
        concept = PedagogicalConcept(
            concept_id="test",
            title="Test",
            definition="Too short",  # Less than 50 chars
            key_points=["Point 1"],
            examples=[
                SQLExample(
                    description="Test",
                    query="SELECT * FROM users;",
                    explanation="Test explanation that is long enough to pass validation.",
                    schema_used="users",
                )
            ],
            common_mistakes=[
                Mistake(
                    error_type="Test error",
                    incorrect_sql="SELECT",
                    correct_sql="SELECT * FROM users;",
                    explanation="Test explanation that meets the minimum length requirement."
                )
            ]
        )
        assert_test(False, "Definition length validation (should have failed)")
    except Exception as e:
        assert_test(True, "Definition length validation")
    
    # Test 7: Empty key_points validation
    try:
        concept = PedagogicalConcept(
            concept_id="test",
            title="Test",
            definition="This is a definition that is long enough to pass the minimum length requirement of fifty characters.",
            key_points=[],  # Empty list
            examples=[
                SQLExample(
                    description="Test",
                    query="SELECT * FROM users;",
                    explanation="Test explanation that is long enough.",
                    schema_used="users",
                )
            ],
            common_mistakes=[
                Mistake(
                    error_type="Test error",
                    incorrect_sql="SELECT",
                    correct_sql="SELECT * FROM users;",
                    explanation="Test explanation that is long enough for validation."
                )
            ]
        )
        assert_test(False, "Empty key_points validation (should have failed)")
    except Exception as e:
        assert_test(True, "Empty key_points validation")
    
    # Test 8: GenerationResult model
    try:
        result = GenerationResult(
            success=True,
            concept=None,
            validation_errors=[],
            attempts=1,
            model_used="qwen2.5:3b",
            generation_time_seconds=2.5
        )
        assert_test(True, "GenerationResult creation")
    except Exception as e:
        assert_test(False, "GenerationResult creation", str(e))
    
    # Test 9: QualityGateResult model
    try:
        result = QualityGateResult(
            concept_id="test-concept",
            overall_passed=True,
            checks=[
                QualityCheckResult(
                    check_name="definition_present",
                    passed=True,
                    score=1.0,
                    message="Definition is present"
                )
            ],
            total_score=1.0
        )
        assert_test(True, "QualityGateResult creation")
        assert_test(len(result.get_failed_checks()) == 0, "QualityGateResult get_failed_checks")
        assert_test(len(result.get_passed_checks()) == 1, "QualityGateResult get_passed_checks")
    except Exception as e:
        assert_test(False, "QualityGateResult creation", str(e))
    
    # Test 10: JSON schema export
    try:
        from algl_pdf_helper.pedagogical_models import (
            get_pedagogical_concept_schema,
            get_sql_example_schema,
            get_mistake_schema
        )
        schema = get_pedagogical_concept_schema()
        assert_test("properties" in schema, "PedagogicalConcept schema export")
        
        schema = get_sql_example_schema()
        assert_test("properties" in schema, "SQLExample schema export")
        
        schema = get_mistake_schema()
        assert_test("properties" in schema, "Mistake schema export")
    except Exception as e:
        assert_test(False, "JSON schema export", str(e))


# =============================================================================
# 2. TEST VALIDATORS
# =============================================================================

@test_section("Validators")
def test_validators():
    from algl_pdf_helper.validators import (
        validate_sql_snippet,
        validate_practice_schema,
        validate_concept_json,
        safe_parse_json,
        extract_json_from_llm_output,
        ALLOWED_SCHEMAS
    )
    
    # Test 1: Valid SELECT
    result = validate_sql_snippet("SELECT * FROM users;")
    assert_test(result.is_valid, "Valid SELECT SQL")
    assert_test(result.sql_type == "SELECT", "SELECT type detection")
    
    # Test 2: Valid SELECT without semicolon (should fail)
    result = validate_sql_snippet("SELECT * FROM users")
    assert_test(not result.is_valid, "SELECT without semicolon fails")
    
    # Test 3: Valid SELECT with partial flag
    result = validate_sql_snippet("SELECT * FROM users", allow_partial=True)
    assert_test(result.is_valid, "SELECT without semicolon with allow_partial")
    
    # Test 4: Valid INSERT
    result = validate_sql_snippet("INSERT INTO users (name) VALUES ('Alice');")
    assert_test(result.is_valid, "Valid INSERT SQL")
    assert_test(result.sql_type == "INSERT", "INSERT type detection")
    
    # Test 5: Valid UPDATE
    result = validate_sql_snippet("UPDATE users SET age = 30 WHERE user_id = 1;")
    assert_test(result.is_valid, "Valid UPDATE SQL")
    assert_test(result.sql_type == "UPDATE", "UPDATE type detection")
    
    # Test 6: Valid DELETE
    result = validate_sql_snippet("DELETE FROM users WHERE user_id = 1;")
    assert_test(result.is_valid, "Valid DELETE SQL")
    assert_test(result.sql_type == "DELETE", "DELETE type detection")
    
    # Test 7: Unbalanced parentheses
    result = validate_sql_snippet("SELECT * FROM users WHERE id IN (1, 2, 3;")
    assert_test(not result.is_valid, "Unbalanced parentheses detection")
    
    # Test 8: Empty SQL
    result = validate_sql_snippet("")
    assert_test(not result.is_valid, "Empty SQL validation")
    
    result = validate_sql_snippet("   ")
    assert_test(not result.is_valid, "Whitespace-only SQL validation")
    
    # Test 9: Unknown SQL type
    result = validate_sql_snippet("UNKNOWN * FROM users;")
    assert_test(not result.is_valid, "Unknown SQL type validation")
    
    # Test 10: Duplicate clauses detection
    result = validate_sql_snippet("SELECT * FROM FROM users;")
    assert_test(not result.is_valid, "Duplicate FROM detection")
    
    # Test 11: Practice schema validation
    assert_test(validate_practice_schema("users"), "Valid schema 'users'")
    assert_test(validate_practice_schema("orders"), "Valid schema 'orders'")
    assert_test(validate_practice_schema("products"), "Valid schema 'products'")
    assert_test(not validate_practice_schema("invalid_schema"), "Invalid schema rejection")
    assert_test(not validate_practice_schema(""), "Empty schema rejection")
    
    # Test 12: Case insensitive schema validation
    assert_test(validate_practice_schema("USERS"), "Case insensitive schema validation")
    
    # Test 13: JSON parsing - valid
    success, data, error = safe_parse_json('{"key": "value"}')
    assert_test(success and data == {"key": "value"}, "Valid JSON parsing")
    
    # Test 14: JSON parsing - markdown wrapped
    success, data, error = safe_parse_json('```json\n{"key": "value"}\n```')
    assert_test(success and data == {"key": "value"}, "Markdown-wrapped JSON parsing")
    
    # Test 15: JSON parsing - invalid
    success, data, error = safe_parse_json('not json')
    assert_test(not success, "Invalid JSON detection")
    
    # Test 16: JSON parsing - empty
    success, data, error = safe_parse_json("")
    assert_test(not success, "Empty JSON detection")
    
    # Test 17: extract_json_from_llm_output
    data = extract_json_from_llm_output('{"concept_id": "test"}')
    assert_test(data == {"concept_id": "test"}, "extract_json_from_llm_output")
    
    data = extract_json_from_llm_output('Some text before {\"concept_id\": \"test\"} after')
    assert_test(data == {"concept_id": "test"}, "extract_json with surrounding text")
    
    data = extract_json_from_llm_output('No JSON here')
    assert_test(data is None, "extract_json returns None for no JSON")
    
    # Test 18: Full concept JSON validation
    valid_concept = {
        "concept_id": "test-concept",
        "title": "Test Concept",
        "difficulty": "beginner",
        "definition": "This is a test definition that is long enough to pass validation requirements.",
        "key_points": ["Point 1", "Point 2"],
        "examples": [
            {
                "description": "Example description",
                "query": "SELECT * FROM users;",
                "explanation": "This is a detailed explanation of the example.",
                "schema_used": "users",
                "difficulty": "beginner"
            }
        ],
        "common_mistakes": [
            {
                "error_type": "Syntax error",
                "incorrect_sql": "SELECT FROM users",
                "correct_sql": "SELECT * FROM users;",
                "explanation": "This explains why this is a mistake and how to fix it properly."
            }
        ],
        "practice_references": [],
        "estimated_time_minutes": 15,
        "prerequisites": [],
        "tags": ["sql", "test"]
    }
    result = validate_concept_json(valid_concept)
    assert_test(result.is_valid, "Valid concept JSON validation")
    
    # Test 19: Invalid concept - missing required field
    invalid_concept = valid_concept.copy()
    del invalid_concept["title"]
    result = validate_concept_json(invalid_concept)
    assert_test(not result.is_valid, "Missing required field detection")
    
    # Test 20: Invalid concept - invalid schema
    invalid_concept = valid_concept.copy()
    invalid_concept["examples"] = [
        {
            "description": "Example",
            "query": "SELECT * FROM invalid_table;",
            "explanation": "This is a detailed explanation of the example.",
            "schema_used": "invalid_table",
            "difficulty": "beginner"
        }
    ]
    result = validate_concept_json(invalid_concept)
    assert_test(not result.is_valid, "Invalid schema detection")


# =============================================================================
# 3. TEST QUALITY GATES
# =============================================================================

@test_section("Quality Gates")
def test_quality_gates():
    from algl_pdf_helper.quality_gates import QualityGate, QualityGateConfig, generate_quality_report
    from algl_pdf_helper.pedagogical_models import PedagogicalConcept, SQLExample, Mistake
    
    # Create a valid concept for testing
    def create_test_concept(**overrides):
        data = {
            "concept_id": "test-concept",
            "title": "Test Concept",
            "difficulty": "beginner",
            "definition": """The SELECT statement is the foundation of SQL data retrieval. 
            It allows you to query data from one or more tables, filter results with WHERE,
            sort with ORDER BY, and aggregate with GROUP BY. Understanding SELECT is 
            essential for all database operations. This concept covers basic syntax and 
            common patterns for retrieving data efficiently.""",
            "key_points": [
                "SELECT retrieves data from tables",
                "Use * for all columns or specify names",
                "FROM clause specifies the table",
                "WHERE filters rows based on conditions"
            ],
            "examples": [
                SQLExample(
                    description="Basic SELECT",
                    query="SELECT * FROM users;",
                    explanation="Retrieves all columns from the users table.",
                    schema_used="users",
                    difficulty="beginner"
                ),
                SQLExample(
                    description="Filtered SELECT",
                    query="SELECT name, email FROM users WHERE age > 18;",
                    explanation="Retrieves specific columns for adult users.",
                    schema_used="users",
                    difficulty="beginner"
                )
            ],
            "common_mistakes": [
                Mistake(
                    error_type="Missing FROM clause",
                    incorrect_sql="SELECT * WHERE age > 18;",
                    correct_sql="SELECT * FROM users WHERE age > 18;",
                    explanation="Every SELECT needs a FROM clause.",
                    error_message="Syntax error",
                    key_takeaway="Always specify the table"
                ),
                Mistake(
                    error_type="Missing semicolon",
                    incorrect_sql="SELECT * FROM users",
                    correct_sql="SELECT * FROM users;",
                    explanation="SQL statements should end with semicolon.",
                    key_takeaway="End statements with ;"
                )
            ],
            "estimated_time_minutes": 15,
            "tags": ["sql", "select"]
        }
        data.update(overrides)
        return PedagogicalConcept(**data)
    
    # Test 1: Valid concept passes quality gate
    gate = QualityGate()
    concept = create_test_concept()
    result = gate.check(concept)
    assert_test(result.overall_passed, "Valid concept passes quality gate")
    assert_test(result.total_score >= 0.7, "Valid concept meets score threshold")
    
    # Test 2: Check individual checks
    check_names = [c.check_name for c in result.checks]
    required_checks = [
        "definition_present",
        "definition_length",
        "key_points_count",
        "examples_count",
        "examples_sql_valid",
        "mistakes_count",
    ]
    for check in required_checks:
        assert_test(check in check_names, f"Quality check '{check}' exists")
    
    # Test 3: Concept with short definition is detected
    # Note: We can't create a concept with invalid definition length via Pydantic
    # So we test with the minimum allowed (50 chars) and verify quality gate detects it
    short_def = "A" * 50  # Minimum allowed by Pydantic, below quality gate min (100)
    short_concept = create_test_concept(definition=short_def)
    result = gate.check(short_concept)
    # Note: definition_length is not in required_checks, so overall_passed might still be True
    # but the check itself should report as failed
    failed_checks = [c.check_name for c in result.get_failed_checks()]
    assert_test("definition_length" in failed_checks, "Short definition detected")
    # Verify the score is reduced due to short definition
    assert_test(result.total_score < 1.0, "Short definition reduces total score")
    
    # Test 4: Concept with no examples - Pydantic prevents empty examples
    # We test the quality gate config validation instead
    # Create a mock scenario by checking an empty list directly
    config = QualityGateConfig()
    assert_test(config.min_examples >= 1, "Quality gate requires at least 1 example")
    
    # Test 5: Concept with no mistakes - Pydantic prevents empty mistakes
    # Verify quality gate config
    assert_test(config.min_mistakes >= 1, "Quality gate requires at least 1 mistake")
    
    # Test 6: Batch checking
    concepts = [
        create_test_concept(concept_id="c1"),
        create_test_concept(concept_id="c2"),
        create_test_concept(concept_id="c3"),
    ]
    results = gate.check_batch(concepts)
    assert_test(len(results) == 3, "Batch check returns all results")
    assert_test(results["c1"].overall_passed, "Batch check - concept 1 passes")
    assert_test(results["c2"].overall_passed, "Batch check - concept 2 passes")
    assert_test(results["c3"].overall_passed, "Batch check - concept 3 passes")
    
    # Test 7: Pass rate calculation
    pass_rate = gate.get_pass_rate(results)
    assert_test(pass_rate == 1.0, f"Pass rate calculation: {pass_rate}")
    
    # Test 8: Quality report generation
    report = generate_quality_report(results)
    assert_test(report["summary"]["total_concepts"] == 3, "Report total concepts")
    assert_test(report["summary"]["passed"] == 3, "Report passed count")
    assert_test(report["summary"]["failed"] == 0, "Report failed count")
    assert_test(report["summary"]["pass_rate"] == 1.0, "Report pass rate")
    
    # Test 9: Custom config
    config = QualityGateConfig(min_definition_length=50, min_key_points=1)
    gate_custom = QualityGate(config)
    result = gate_custom.check(concept)
    assert_test(result.overall_passed, "Custom config quality gate")
    
    # Test 10: Empty concept list
    empty_results = gate.check_batch([])
    assert_test(len(empty_results) == 0, "Empty batch check")
    pass_rate = gate.get_pass_rate(empty_results)
    assert_test(pass_rate == 0.0, "Empty batch pass rate is 0")


# =============================================================================
# 4. TEST PROMPTS
# =============================================================================

@test_section("Prompts")
def test_prompts():
    from algl_pdf_helper.prompts import (
        build_strict_pedagogical_prompt,
        build_strict_sql_example_prompt,
        build_strict_mistakes_prompt,
        format_schema_for_prompt,
        get_error_patterns_for_concept,
        PRACTICE_SCHEMAS,
        ERROR_PATTERNS,
        DIFFICULTY_GUIDELINES,
    )
    
    # Test 1: Strict pedagogical prompt generation
    prompt = build_strict_pedagogical_prompt(
        concept_id="joins-intro",
        concept_title="Introduction to JOINs",
        difficulty="beginner",
        raw_text="JOINs combine data from multiple tables."
    )
    assert_test("joins-intro" in prompt, "Prompt contains concept_id")
    assert_test("Introduction to JOINs" in prompt, "Prompt contains concept_title")
    assert_test("beginner" in prompt, "Prompt contains difficulty")
    assert_test("JOINs combine" in prompt, "Prompt contains raw_text")
    assert_test("JSON" in prompt or "json" in prompt, "Prompt mentions JSON")
    
    # Test 2: SQL example prompt generation
    prompt = build_strict_sql_example_prompt(
        concept_title="SELECT Basics",
        scenario="Retrieve user information",
        difficulty="beginner"
    )
    assert_test("SELECT Basics" in prompt, "SQL prompt contains concept_title")
    assert_test("Retrieve user" in prompt, "SQL prompt contains scenario")
    assert_test("users" in prompt.lower() or "orders" in prompt.lower(), "SQL prompt contains schema info")
    
    # Test 3: Mistakes prompt generation
    prompt = build_strict_mistakes_prompt(
        concept_title="WHERE Clause",
        difficulty="intermediate",
        concept_id="where-clause"
    )
    assert_test("WHERE Clause" in prompt, "Mistakes prompt contains concept_title")
    assert_test("JSON" in prompt or "json" in prompt, "Mistakes prompt mentions JSON")
    
    # Test 4: Schema formatting
    formatted = format_schema_for_prompt(PRACTICE_SCHEMAS)
    assert_test("Table: users" in formatted, "Formatted schema contains users table")
    assert_test("user_id" in formatted, "Formatted schema contains column info")
    
    # Test 5: Error patterns retrieval
    patterns = get_error_patterns_for_concept("joins-intro")
    assert_test(len(patterns) > 0, "Error patterns retrieved for joins")
    assert_test(any("JOIN" in p or "join" in p for p in patterns), "Join error patterns are relevant")
    
    patterns = get_error_patterns_for_concept("aggregation")
    assert_test(len(patterns) > 0, "Error patterns retrieved for aggregation")
    
    patterns = get_error_patterns_for_concept("unknown-concept")
    assert_test(len(patterns) > 0, "Error patterns fallback for unknown concept")
    
    # Test 6: Difficulty guidelines exist
    assert_test("beginner" in DIFFICULTY_GUIDELINES, "Beginner guidelines exist")
    assert_test("intermediate" in DIFFICULTY_GUIDELINES, "Intermediate guidelines exist")
    assert_test("advanced" in DIFFICULTY_GUIDELINES, "Advanced guidelines exist")
    
    # Test 7: Practice schemas exist
    assert_test("users" in PRACTICE_SCHEMAS, "Users schema exists")
    assert_test("orders" in PRACTICE_SCHEMAS, "Orders schema exists")
    assert_test("products" in PRACTICE_SCHEMAS, "Products schema exists")


# =============================================================================
# 5. TEST MULTI-PASS GENERATOR (without LLM)
# =============================================================================

@test_section("Multi-Pass Generator (Unit Tests)")
def test_multi_pass_generator():
    from algl_pdf_helper.generation_pipeline import (
        MultiPassGenerator, 
        get_recommended_model,
        check_model_compatibility,
        ALL_MODELS
    )
    from algl_pdf_helper.validators import safe_parse_json
    
    # Test 1: Generator initialization
    try:
        gen = MultiPassGenerator()
        assert_test(True, "MultiPassGenerator default initialization")
    except Exception as e:
        assert_test(False, "MultiPassGenerator default initialization", str(e))
    
    # Test 2: Generator with custom params
    try:
        gen = MultiPassGenerator(
            model="qwen2.5:3b",
            max_attempts=2,
            temperature=0.5,
            timeout=120
        )
        assert_test(gen.model == "qwen2.5:3b", "Custom model set")
        assert_test(gen.max_attempts == 2, "Custom max_attempts set")
        assert_test(gen.temperature == 0.5, "Custom temperature set")
    except Exception as e:
        assert_test(False, "MultiPassGenerator custom initialization", str(e))
    
    # Test 3: Model compatibility check
    compatible, warning = check_model_compatibility("qwen2.5:3b")
    assert_test(compatible, "3B model is compatible")
    
    compatible, warning = check_model_compatibility("unknown-model")
    assert_test(compatible, "Unknown model allows fallback")
    assert_test("unknown" in warning.lower(), "Unknown model warning")
    
    # Test 4: Get recommended model
    model = get_recommended_model()
    assert_test(model in ALL_MODELS, f"Recommended model '{model}' is valid")
    
    # Test 5: JSON parsing helper (used by generator)
    # Valid JSON
    success, data, error = safe_parse_json('{"key": "value"}')
    assert_test(success, "safe_parse_json valid")
    
    # JSON with markdown
    success, data, error = safe_parse_json('```json\n{"key": "value"}\n```')
    assert_test(success, "safe_parse_json markdown")
    
    # Invalid JSON
    success, data, error = safe_parse_json('not json')
    assert_test(not success, "safe_parse_json invalid")


# =============================================================================
# 6. TEST EDGE CASES
# =============================================================================

@test_section("Edge Cases")
def test_edge_cases():
    from algl_pdf_helper.pedagogical_models import PedagogicalConcept, SQLExample, Mistake
    from algl_pdf_helper.validators import validate_sql_snippet, validate_concept_json, safe_parse_json
    from algl_pdf_helper.quality_gates import QualityGate
    
    # Test 1: Very long definition
    try:
        long_def = "This is a test. " * 200  # ~4800 chars
        concept = PedagogicalConcept(
            concept_id="test",
            title="Test",
            definition=long_def[:1000],  # Truncate to max
            key_points=["Point 1"],
            examples=[
                SQLExample(
                    description="Test example with sufficient length",
                    query="SELECT * FROM users;",
                    explanation="This is a detailed explanation that meets the minimum length requirement for validation.",
                    schema_used="users",
                )
            ],
            common_mistakes=[
                Mistake(
                    error_type="Test error",
                    incorrect_sql="SELECT",
                    correct_sql="SELECT * FROM users;",
                    explanation="This is a detailed explanation of the mistake and how to correct it properly."
                )
            ]
        )
        assert_test(True, "Max length definition handling")
    except Exception as e:
        assert_test(False, "Max length definition handling", str(e))
    
    # Test 2: Unicode in content
    try:
        concept = PedagogicalConcept(
            concept_id="unicode-test",
            title="Unicode Test: 中文 🎉",
            definition="This is a definition with unicode: 中文, émojis 🎉, and special chars &<>.",
            key_points=["Unicode point: 中文"],
            examples=[
                SQLExample(
                    description="Unicode test",
                    query="SELECT * FROM users WHERE name = '中文';",
                    explanation="Testing unicode characters in SQL examples and explanations.",
                    schema_used="users",
                )
            ],
            common_mistakes=[
                Mistake(
                    error_type="Unicode error: 错误",
                    incorrect_sql="SELECT 中文",
                    correct_sql="SELECT * FROM users;",
                    explanation="Unicode explanation: 解释"
                )
            ]
        )
        assert_test(True, "Unicode content handling")
    except Exception as e:
        assert_test(False, "Unicode content handling", str(e))
    
    # Test 3: SQL with comments (may be flagged as warning but should be valid)
    result = validate_sql_snippet("SELECT * FROM users; -- Get all users")
    # Allow warnings but check it's not marked as invalid due to our check
    assert_test(result.sql_type == "SELECT", "SQL with inline comment - type detected")
    
    # Test 4: SQL with newlines
    result = validate_sql_snippet("""SELECT 
        name, 
        email 
    FROM users 
    WHERE age > 18;""")
    assert_test(result.is_valid, "SQL with newlines")
    
    # Test 5: Complex nested SQL
    result = validate_sql_snippet("""
        SELECT u.name, COUNT(o.order_id) as order_count
        FROM users u
        LEFT JOIN orders o ON u.user_id = o.user_id
        WHERE u.age > 18
        GROUP BY u.user_id, u.name
        HAVING COUNT(o.order_id) > 5
        ORDER BY order_count DESC
        LIMIT 10;
    """)
    assert_test(result.is_valid, "Complex nested SQL")
    
    # Test 6: Malformed JSON parsing
    success, data, error = safe_parse_json('{"incomplete": ')
    assert_test(not success, "Malformed JSON detection")
    
    # Test 7: JSON with extra text
    success, data, error = safe_parse_json('Here is the JSON: {"key": "value"} Thanks!')
    assert_test(success and data == {"key": "value"}, "JSON extraction from text")
    
    # Test 8: Empty arrays
    try:
        concept = PedagogicalConcept(
            concept_id="test",
            title="Test",
            definition="This is a definition that is long enough to pass validation requirements.",
            key_points=["Point 1"],
            examples=[
                SQLExample(
                    description="Test example with sufficient length",
                    query="SELECT * FROM users;",
                    explanation="This is a detailed explanation that meets the minimum length requirement.",
                    schema_used="users",
                )
            ],
            common_mistakes=[
                Mistake(
                    error_type="Test error",
                    incorrect_sql="SELECT",
                    correct_sql="SELECT * FROM users;",
                    explanation="This is a detailed explanation that meets the minimum length requirement."
                )
            ],
            practice_references=[],  # Empty but valid
            prerequisites=[],  # Empty but valid
            tags=[]  # Empty but valid
        )
        gate = QualityGate()
        result = gate.check(concept)
        assert_test(result.overall_passed, "Concept with empty optional arrays")
    except Exception as e:
        assert_test(False, "Empty optional arrays", str(e))
    
    # Test 9: SQL injection patterns (should warn but may be valid)
    result = validate_sql_snippet("SELECT * FROM users; DROP TABLE users;")
    # Should have warnings but may still be valid syntactically
    assert_test(len(result.warnings) > 0 or not result.is_valid, "SQL injection pattern detection")
    
    # Test 10: Case sensitivity in SQL keywords
    result = validate_sql_snippet("select * from users;")
    assert_test(result.is_valid, "Lowercase SQL keywords")
    assert_test(result.sql_type == "SELECT", "Lowercase SQL type detection")


# =============================================================================
# 7. TEST OLLAMA AVAILABILITY
# =============================================================================

@test_section("Ollama Availability")
def test_ollama_availability():
    from algl_pdf_helper.generation_pipeline import check_ollama_available, list_available_models
    
    is_available = check_ollama_available()
    assert_test(isinstance(is_available, bool), "Ollama check returns boolean")
    
    if is_available:
        models = list_available_models()
        assert_test(isinstance(models, list), "Models list returns list")
        print(f"  ℹ️  Ollama available with {len(models)} models")
    else:
        warn("Ollama not available - integration tests skipped")


# =============================================================================
# MAIN
# =============================================================================

def run_all_tests():
    """Run all test sections."""
    print("\n" + "="*60)
    print("PEDAGOGICAL GENERATION SYSTEM - COMPREHENSIVE TEST SUITE")
    print("="*60)
    
    start_time = time.time()
    
    # Run all tests
    test_pydantic_models()
    test_validators()
    test_quality_gates()
    test_prompts()
    test_multi_pass_generator()
    test_edge_cases()
    test_ollama_availability()
    
    # Summary
    elapsed = time.time() - start_time
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Total Tests: {len(test_results['passed']) + len(test_results['failed'])}")
    print(f"Passed: {len(test_results['passed'])} ✅")
    print(f"Failed: {len(test_results['failed'])} ❌")
    print(f"Warnings: {len(test_results['warnings'])} ⚠️")
    print(f"Time: {elapsed:.2f}s")
    
    if test_results['failed']:
        print("\nFailed Tests:")
        for name, details in test_results['failed']:
            print(f"  - {name}")
            if details:
                print(f"    {details}")
    
    if test_results['warnings']:
        print("\nWarnings:")
        for w in test_results['warnings']:
            print(f"  - {w}")
    
    # Calculate pass rate
    total = len(test_results['passed']) + len(test_results['failed'])
    pass_rate = len(test_results['passed']) / total if total > 0 else 0
    
    print(f"\nPass Rate: {pass_rate*100:.1f}%")
    
    if pass_rate >= 0.9:
        print("\n✅ QUALITY TARGET MET (>90%)")
    else:
        print("\n❌ QUALITY TARGET NOT MET (<90%)")
    
    return test_results


if __name__ == "__main__":
    results = run_all_tests()
    
    # Exit with error code if tests failed
    if results['failed']:
        sys.exit(1)
    sys.exit(0)
