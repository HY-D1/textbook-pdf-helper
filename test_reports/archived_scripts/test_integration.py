#!/usr/bin/env python3
"""
Integration tests for algl-pdf-helper pipeline.
Tests the complete flow from PDF processing to SQL-Adapt export.
"""

import json
import tempfile
import shutil
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from algl_pdf_helper import (
    PedagogicalContentGenerator,
    PRACTICE_SCHEMAS,
    TEXTBOOK_TO_PRACTICE_MAPPING,
)
from algl_pdf_helper.pedagogical_generator import CONCEPT_TO_PROBLEMS
from algl_pdf_helper.prompts import (
    build_concept_prompt,
    build_sql_example_prompt,
)
from algl_pdf_helper.extract import extract_pages_fitz
from algl_pdf_helper.chunker import chunk_page_words

# Create alias for chunk_text to match expected interface
def chunk_text(text: str, chunk_size: int = 100, overlap: int = 20) -> list[tuple[str, str]]:
    """Wrapper for chunk_page_words with simpler interface."""
    return chunk_page_words(
        doc_id="test",
        page=1,
        text=text,
        chunk_words=chunk_size,
        overlap_words=overlap
    )


class IntegrationTestSuite:
    """Integration test suite for the complete pipeline."""
    
    def __init__(self):
        self.results = []
        self.temp_dir = Path(tempfile.mkdtemp())
        
    def cleanup(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def run_all_tests(self):
        """Run all integration tests."""
        tests = [
            ("Module Imports", self.test_module_imports),
            ("Pedagogical Generator Init", self.test_pedagogical_generator_init),
            ("Educational Pipeline Init", self.test_educational_pipeline_init),
            ("End-to-End Concept Generation", self.test_end_to_end_concept),
            ("SQL Transformation", self.test_sql_transformation),
            ("Markdown Generation", self.test_markdown_generation),
            ("Practice Schema Alignment", self.test_practice_schema_alignment),
            ("Prompt Building", self.test_prompt_building),
            ("Pipeline Flow", self.test_pipeline_flow),
        ]
        
        print("=" * 70)
        print("INTEGRATION TEST SUITE")
        print("=" * 70)
        
        for name, test_func in tests:
            try:
                print(f"\n🧪 Testing: {name}...")
                test_func()
                self.results.append((name, True, None))
                print(f"   ✅ PASS")
            except Exception as e:
                self.results.append((name, False, str(e)))
                print(f"   ❌ FAIL: {e}")
        
        return self.generate_report()
    
    def test_module_imports(self):
        """Test that all modules can be imported."""
        # Core modules
        from algl_pdf_helper.pedagogical_generator import PedagogicalContentGenerator
        from algl_pdf_helper.prompts import build_concept_prompt
        from algl_pdf_helper.educational_pipeline import EducationalNoteGenerator
        from algl_pdf_helper.markdown_generator import generate_concept_markdown
        from algl_pdf_helper.extract import extract_pages_fitz
        from algl_pdf_helper.chunker import chunk_page_words
        
        # Verify key classes exist
        assert PedagogicalContentGenerator is not None
        assert EducationalNoteGenerator is not None
        assert callable(build_concept_prompt)
        assert callable(generate_concept_markdown)
    
    def test_pedagogical_generator_init(self):
        """Test pedagogical generator initialization."""
        generator = PedagogicalContentGenerator(
            PRACTICE_SCHEMAS,
            TEXTBOOK_TO_PRACTICE_MAPPING
        )
        
        assert generator.practice_schemas is not None
        assert generator.schema_mapping is not None
        assert "users" in generator.practice_schemas
        assert "Sailors" in generator.schema_mapping
    
    def test_educational_pipeline_init(self):
        """Test educational pipeline initialization."""
        from algl_pdf_helper.educational_pipeline import EducationalNoteGenerator
        
        # Test with pedagogical mode (pedagogical_generator is always initialized)
        generator = EducationalNoteGenerator(
            llm_provider="openai",
            use_pedagogical=True
        )
        
        assert generator.pedagogical_generator is not None
        assert isinstance(generator.pedagogical_generator, PedagogicalContentGenerator)
        
        # Test without pedagogical mode (backward compatibility)
        generator_old = EducationalNoteGenerator(
            llm_provider="openai",
            use_pedagogical=False
        )
        # Note: pedagogical_generator is always initialized regardless of flag
        assert generator_old.pedagogical_generator is not None
    
    def test_end_to_end_concept(self):
        """Test complete concept generation flow."""
        generator = PedagogicalContentGenerator(
            PRACTICE_SCHEMAS,
            TEXTBOOK_TO_PRACTICE_MAPPING
        )
        
        # Mock raw chunks
        raw_chunks = [
            {
                "chunkId": "test:p1:c1",
                "page": 1,
                "text": "JOIN combines rows from two tables based on a related column."
            },
            {
                "chunkId": "test:p1:c2",
                "page": 1,
                "text": "Example: SELECT * FROM Sailors s JOIN Boats b ON s.sid = b.bid;"
            }
        ]
        
        # Generate concept
        concept = generator.generate_pedagogical_concept(
            concept_id="joins",
            concept_title="JOIN Operations",
            raw_chunks=raw_chunks,
            practice_problem_links=["problem-3", "problem-4"]
        )
        
        # Verify structure
        assert concept["concept_id"] == "joins", f"Expected concept_id 'joins', got {concept.get('concept_id')}"
        assert concept["title"] == "JOIN Operations", f"Expected title 'JOIN Operations', got {concept.get('title')}"
        assert len(concept["learning_objectives"]) > 0, "learning_objectives should not be empty"
        assert "sections" in concept, "sections key missing"
        assert "examples" in concept["sections"], "examples section missing"
        assert "common_mistakes" in concept["sections"], "common_mistakes section missing"
        assert concept["practice_problems"] == ["problem-3", "problem-4"], f"practice_problems mismatch: {concept.get('practice_problems')}"
        
        # Verify examples use practice schemas
        examples = concept.get("sections", {}).get("examples", [])
        assert len(examples) > 0, "No examples generated"
        for example in examples:
            sql = example.get("sql", "")
            if sql:  # Only check if SQL is present
                assert "Sailors" not in sql, f"Example still uses textbook schema Sailors: {sql[:50]}"
                assert "Boats" not in sql, f"Example still uses textbook schema Boats: {sql[:50]}"
    
    def test_sql_transformation(self):
        """Test SQL schema transformation."""
        generator = PedagogicalContentGenerator(
            PRACTICE_SCHEMAS,
            TEXTBOOK_TO_PRACTICE_MAPPING
        )
        
        test_cases = [
            ("SELECT * FROM Sailors;", "users"),
            ("SELECT * FROM Boats WHERE color='red';", "products"),
            ("SELECT * FROM Reserves;", "orders"),
        ]
        
        for original, expected_table in test_cases:
            result = generator.transform_textbook_example(original, "test")
            transformed = result["transformed"]
            
            assert expected_table in transformed.lower(), \
                f"Expected {expected_table} in: {transformed}"
    
    def test_markdown_generation(self):
        """Test markdown generation from concept."""
        generator = PedagogicalContentGenerator(
            PRACTICE_SCHEMAS,
            TEXTBOOK_TO_PRACTICE_MAPPING
        )
        
        # Generate a concept
        concept = generator.generate_pedagogical_concept(
            concept_id="select-basic",
            concept_title="SELECT Basics",
            raw_chunks=[],
            practice_problem_links=["problem-1"]
        )
        
        # Generate markdown
        markdown = generator.generate_markdown(concept)
        
        # Verify markdown contains key elements
        assert "# SELECT Basics" in markdown
        assert "## Examples" in markdown
        assert "## Common Mistakes" in markdown
        assert "```sql" in markdown  # SQL code blocks
        assert "problem-1" in markdown  # Practice problem link
        
        # Verify no textbook schemas
        assert "Sailors" not in markdown
        assert "Boats" not in markdown
    
    def test_practice_schema_alignment(self):
        """Test that all outputs use practice schemas."""
        generator = PedagogicalContentGenerator(
            PRACTICE_SCHEMAS,
            TEXTBOOK_TO_PRACTICE_MAPPING
        )
        
        # Test multiple concepts
        test_concepts = ["select-basic", "joins", "aggregation", "where-clause"]
        
        for concept_id in test_concepts:
            mistakes = generator.generate_common_mistakes(concept_id)
            
            for mistake in mistakes:
                error_sql = mistake.get("error_sql", "")
                fix_sql = mistake.get("fix_sql", "")
                
                # Check no textbook tables
                for bad_table in ["Sailors", "Boats", "Reserves", "Invoices"]:
                    assert bad_table not in error_sql, \
                        f"{concept_id} mistake uses {bad_table}"
                    assert bad_table not in fix_sql, \
                        f"{concept_id} fix uses {bad_table}"
    
    def test_prompt_building(self):
        """Test that prompt building works."""
        prompt = build_concept_prompt(
            concept_id="joins",
            raw_text="JOIN combines tables...",
            context={
                "concept_title": "JOIN Operations",
                "difficulty": "intermediate",
                "prerequisites": ["select-basic"]
            }
        )
        
        assert "JOIN" in prompt or "joins" in prompt.lower()
        assert "raw_text" in prompt or "JOIN combines" in prompt
        assert len(prompt) > 100
    
    def test_pipeline_flow(self):
        """Test the complete pipeline flow."""
        # Step 1: Initialize components
        generator = PedagogicalContentGenerator(
            PRACTICE_SCHEMAS,
            TEXTBOOK_TO_PRACTICE_MAPPING
        )
        
        # Step 2: Generate concept
        concept = generator.generate_pedagogical_concept(
            concept_id="joins",
            concept_title="JOIN Operations",
            raw_chunks=[{"text": "JOIN explanation"}],
            practice_problem_links=["problem-3"]
        )
        
        # Step 3: Generate markdown
        markdown = generator.generate_markdown(concept)
        
        # Step 4: Save and verify
        output_path = self.temp_dir / "test_concept.md"
        with open(output_path, 'w') as f:
            f.write(markdown)
        
        assert output_path.exists()
        content = output_path.read_text()
        assert len(content) > 500
        assert "JOIN" in content
    
    def generate_report(self):
        """Generate test report."""
        passed = sum(1 for _, result, _ in self.results if result)
        failed = sum(1 for _, result, _ in self.results if not result)
        
        print("\n" + "=" * 70)
        print("INTEGRATION TEST REPORT")
        print("=" * 70)
        print(f"\nTotal: {len(self.results)} tests")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {passed/len(self.results)*100:.1f}%")
        
        if failed > 0:
            print("\nFailed Tests:")
            for name, result, error in self.results:
                if not result:
                    print(f"  - {name}: {error}")
        
        print("=" * 70)
        
        return passed == len(self.results)


def main():
    """Run integration tests."""
    suite = IntegrationTestSuite()
    try:
        success = suite.run_all_tests()
        suite.cleanup()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n💥 Critical error: {e}")
        suite.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()
