#!/usr/bin/env python3
"""Test script for pedagogical content generation."""

import json
from pathlib import Path

# Import the new modules
from src.algl_pdf_helper.pedagogical_generator import (
    PedagogicalContentGenerator,
    PRACTICE_SCHEMAS,
    TEXTBOOK_TO_PRACTICE_MAPPING,
    CONCEPT_TO_PROBLEMS
)
from src.algl_pdf_helper.prompts import (
    build_concept_prompt,
    build_sql_example_prompt,
    build_mistakes_prompt
)

# Import existing modules for comparison
from src.algl_pdf_helper.extract import extract_pages_fitz
from src.algl_pdf_helper.concept_mapper import load_concepts_config

def test_schema_transformation():
    """Test 1: Transform textbook SQL to practice schemas."""
    print("\n=== TEST 1: Schema Transformation ===")
    
    generator = PedagogicalContentGenerator(
        PRACTICE_SCHEMAS,
        TEXTBOOK_TO_PRACTICE_MAPPING
    )
    
    # Test cases
    test_cases = [
        {
            "name": "SELECT from Sailors",
            "input": "SELECT * FROM Sailors WHERE rating > 5;",
            "expected_contains": ["users", "age"]
        },
        {
            "name": "JOIN with Boats",
            "input": "SELECT s.sname, b.color FROM Sailors s JOIN Boats b ON s.sid = b.bid;",
            "expected_contains": ["users", "products"]
        },
        {
            "name": "Aggregation on Reserves",
            "input": "SELECT COUNT(*) FROM Reserves;",
            "expected_contains": ["orders"]
        }
    ]
    
    for test in test_cases:
        result = generator.transform_textbook_example(test["input"], "joins")
        print(f"\n{test['name']}:")
        print(f"  Input: {test['input'][:50]}...")
        print(f"  Output: {result['transformed'][:50]}...")
        print(f"  Changes: {result['schema_mappings_used']}")
        
        # Verify transformation
        success = all(term in result['transformed'].lower() 
                     for term in test['expected_contains'])
        print(f"  ✓ PASS" if success else f"  ✗ FAIL")

def test_common_mistakes_generation():
    """Test 2: Generate realistic mistakes."""
    print("\n=== TEST 2: Common Mistakes Generation ===")
    
    generator = PedagogicalContentGenerator(
        PRACTICE_SCHEMAS,
        TEXTBOOK_TO_PRACTICE_MAPPING
    )
    
    test_concepts = ["joins", "aggregation", "select-basic"]
    
    for concept_id in test_concepts:
        mistakes = generator.generate_common_mistakes(concept_id)
        print(f"\n{concept_id}:")
        print(f"  Generated {len(mistakes)} mistakes")
        
        for i, m in enumerate(mistakes[:2], 1):  # Show first 2
            print(f"  {i}. {m['title'][:50]}...")
            print(f"     Error: {m['error_sql'][:40]}...")
            print(f"     Fix: {m['fix_sql'][:40]}...")
        
        # Verify structure
        if mistakes:
            required_keys = ['title', 'error_sql', 'error_message', 'why_it_happens', 'fix_sql', 'key_takeaway']
            has_all = all(k in mistakes[0] for k in required_keys)
            print(f"  ✓ Structure complete" if has_all else f"  ✗ Missing keys")

def test_practice_challenge():
    """Test 3: Generate practice challenges."""
    print("\n=== TEST 3: Practice Challenge Generation ===")
    
    generator = PedagogicalContentGenerator(
        PRACTICE_SCHEMAS,
        TEXTBOOK_TO_PRACTICE_MAPPING
    )
    
    test_concepts = ["joins", "aggregation", "where-clause"]
    
    for concept_id in test_concepts:
        challenge = generator.generate_practice_challenge(concept_id)
        print(f"\n{concept_id}:")
        print(f"  Challenge: {challenge['description'][:60]}...")
        print(f"  Hint: {challenge['hint'][:50]}...")
        print(f"  Solution: {challenge['solution'][:50]}...")
        
        # Verify uses practice schemas
        uses_practice = any(table in challenge['solution'] 
                           for table in ['users', 'orders', 'products'])
        print(f"  ✓ Uses practice schemas" if uses_practice else f"  ✗ Wrong schemas")

def test_full_concept_generation():
    """Test 4: Generate complete concept."""
    print("\n=== TEST 4: Full Concept Generation ===")
    
    generator = PedagogicalContentGenerator(
        PRACTICE_SCHEMAS,
        TEXTBOOK_TO_PRACTICE_MAPPING
    )
    
    # Mock raw chunks (simulating PDF extraction)
    mock_chunks = [
        {
            "chunkId": "test:p1:c1",
            "page": 1,
            "text": "JOIN combines rows from two or more tables based on related columns."
        },
        {
            "chunkId": "test:p1:c2",
            "page": 1,
            "text": "Example: SELECT * FROM Sailors s JOIN Boats b ON s.sid = b.bid;"
        }
    ]
    
    concept = generator.generate_pedagogical_concept(
        concept_id="joins",
        concept_title="JOIN Operations",
        raw_chunks=mock_chunks,
        practice_problem_links=["problem-3", "problem-4"]
    )
    
    print(f"\nGenerated concept: {concept['title']}")
    print(f"  Learning objectives: {len(concept['learning_objectives'])}")
    print(f"  Examples: {len(concept['sections']['examples'])}")
    print(f"  Mistakes: {len(concept['sections']['common_mistakes'])}")
    print(f"  Practice problems: {concept['practice_problems']}")
    
    # Verify structure
    required_sections = ['definition', 'examples', 'common_mistakes', 'practice_challenge']
    has_all = all(s in concept['sections'] for s in required_sections)
    print(f"  ✓ All sections present" if has_all else f"  ✗ Missing sections")
    
    # Save for inspection
    output_path = Path("test_output/test_concept_joins.json")
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(concept, f, indent=2)
    print(f"  Saved to: {output_path}")
    
    return concept

def test_markdown_output():
    """Test 5: Generate markdown."""
    print("\n=== TEST 5: Markdown Generation ===")
    
    generator = PedagogicalContentGenerator(
        PRACTICE_SCHEMAS,
        TEXTBOOK_TO_PRACTICE_MAPPING
    )
    
    # Use the concept from test 4 or create new
    concept = generator.generate_pedagogical_concept(
        concept_id="select-basic",
        concept_title="SELECT Statement Basics",
        raw_chunks=[],
        practice_problem_links=["problem-1"]
    )
    
    markdown = generator.generate_markdown(concept)
    
    print(f"\nGenerated markdown ({len(markdown)} chars)")
    print(f"  Preview:\n{markdown[:500]}...")
    
    # Save for inspection
    output_path = Path("test_output/test_select_basic.md")
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(markdown)
    print(f"  Saved to: {output_path}")
    
    # Verify key elements
    checks = {
        "Has practice problem links": "problem-1" in markdown,
        "Uses practice schemas": any(t in markdown for t in ['users', 'orders']),
        "Has examples section": "## Examples" in markdown,
        "Has mistakes section": "## Common Mistakes" in markdown,
        "Has runnable SQL": "```sql" in markdown,
    }
    
    for check, passed in checks.items():
        print(f"  {'✓' if passed else '✗'} {check}")

def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("PEDAGOGICAL CONTENT GENERATION TEST SUITE")
    print("=" * 60)
    
    test_schema_transformation()
    test_common_mistakes_generation()
    test_practice_challenge()
    test_full_concept_generation()
    test_markdown_output()
    
    print("\n" + "=" * 60)
    print("TEST SUITE COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    run_all_tests()
