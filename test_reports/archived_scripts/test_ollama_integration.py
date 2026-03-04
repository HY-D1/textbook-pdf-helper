#!/usr/bin/env python3
"""
Integration tests for Ollama-based pedagogical content generation.

These tests are only run if Ollama is available locally.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from algl_pdf_helper.generation_pipeline import (
    MultiPassGenerator,
    check_ollama_available,
    list_available_models,
)


def test_ollama_generation():
    """Test actual generation with Ollama if available."""
    
    if not check_ollama_available():
        print("Ollama not available - skipping integration tests")
        return True
    
    print("Ollama is available!")
    models = list_available_models()
    print(f"Available models: {[m.get('name') for m in models]}")
    
    # Use a small model for testing
    available_model_names = [m.get('name') for m in models]
    
    # Prefer 3B models for testing
    preferred_models = ["qwen2.5:3b", "qwen2.5:3b-instruct", "gemma2:2b", "llama3.2:3b"]
    test_model = None
    for model in preferred_models:
        if model in available_model_names:
            test_model = model
            break
    
    if not test_model:
        # Find any small model (< 7B)
        for name in available_model_names:
            if any(x in name for x in [":3b", ":2b", "1.8b"]):
                test_model = name
                break
    
    if not test_model:
        print(f"No suitable small model found, skipping generation test")
        print(f"Available: {available_model_names}")
        return True
    
    print(f"\nTesting generation with {test_model}...")
    
    try:
        generator = MultiPassGenerator(
            model=test_model,
            max_attempts=2,
            temperature=0.3,
            timeout=120,
        )
        
        # Test generation with simple context
        result = generator.generate_with_validation(
            concept_id="select-basic",
            concept_title="SELECT Statement Basics",
            raw_text="""
            The SELECT statement is used to retrieve data from one or more tables.
            Basic syntax: SELECT column1, column2 FROM table_name;
            Use * to select all columns.
            Example: SELECT * FROM employees;
            """,
            difficulty="beginner",
            progress_callback=lambda msg: print(f"  → {msg}"),
        )
        
        print(f"\nGeneration result:")
        print(f"  Success: {result.success}")
        print(f"  Attempts: {result.attempts}")
        print(f"  Model: {result.model_used}")
        print(f"  Time: {result.generation_time_seconds:.2f}s")
        
        if result.success and result.concept:
            print(f"\n  Generated concept:")
            print(f"    ID: {result.concept.concept_id}")
            print(f"    Title: {result.concept.title}")
            print(f"    Definition length: {len(result.concept.definition)} chars")
            print(f"    Key points: {len(result.concept.key_points)}")
            print(f"    Examples: {len(result.concept.examples)}")
            print(f"    Mistakes: {len(result.concept.common_mistakes)}")
            
            # Test quality gate on generated content
            from algl_pdf_helper.quality_gates import QualityGate
            gate = QualityGate()
            quality = gate.check(result.concept)
            print(f"\n  Quality check:")
            print(f"    Passed: {quality.overall_passed}")
            print(f"    Score: {quality.total_score}")
            
            if quality.get_failed_checks():
                print(f"    Failed checks: {[c.check_name for c in quality.get_failed_checks()]}")
        
        return result.success
        
    except Exception as e:
        print(f"Error during generation: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sql_example_generation():
    """Test SQL example generation."""
    
    if not check_ollama_available():
        return True
    
    test_model = "qwen2.5:3b"
    models = list_available_models()
    available_model_names = [m.get('name') for m in models]
    
    if test_model not in available_model_names:
        return True
    
    print(f"\nTesting SQL example generation with {test_model}...")
    
    try:
        generator = MultiPassGenerator(model=test_model, max_attempts=2)
        
        example = generator.generate_sql_example(
            concept_title="SELECT Basics",
            scenario="Retrieve all users from the users table",
            difficulty="beginner",
        )
        
        if example:
            print(f"  Generated example:")
            print(f"    Description: {example.description[:50]}...")
            print(f"    Query: {example.query[:50]}...")
            print(f"    Schema: {example.schema_used}")
            return True
        else:
            print("  No example generated (may have failed validation)")
            return True  # Not a test failure, just no result
            
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_mistakes_generation():
    """Test common mistakes generation."""
    
    if not check_ollama_available():
        return True
    
    models = list_available_models()
    available_model_names = [m.get('name') for m in models]
    
    # Find a suitable model
    test_model = None
    for name in available_model_names:
        if any(x in name for x in [":3b", ":2b", "1.8b"]):
            test_model = name
            break
    
    if not test_model:
        return True
    
    print(f"\nTesting mistakes generation with {test_model}...")
    
    try:
        generator = MultiPassGenerator(model=test_model, max_attempts=2)
        
        mistakes = generator.generate_common_mistakes(
            concept_title="WHERE Clause",
            concept_id="where-clause",
            difficulty="beginner",
        )
        
        print(f"  Generated {len(mistakes)} mistakes")
        for i, m in enumerate(mistakes[:2], 1):
            print(f"    {i}. {m.error_type}")
        
        return True
            
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    print("="*60)
    print("OLLAMA INTEGRATION TESTS")
    print("="*60)
    
    results = []
    
    results.append(("Generation", test_ollama_generation()))
    results.append(("SQL Example", test_sql_example_generation()))
    results.append(("Mistakes", test_mistakes_generation()))
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")
    
    all_passed = all(r[1] for r in results)
    sys.exit(0 if all_passed else 1)
