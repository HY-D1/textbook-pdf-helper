#!/usr/bin/env python3
"""
Regenerate all concept files using the new pedagogical pipeline.
This script processes existing PDF indices and regenerates concepts
with the new pedagogical format.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))

from algl_pdf_helper.pedagogical_generator import (
    PedagogicalContentGenerator,
    PRACTICE_SCHEMAS,
    TEXTBOOK_TO_PRACTICE_MAPPING,
    CONCEPT_TO_PROBLEMS
)


def load_existing_index(index_path: Path) -> dict:
    """Load existing PDF index."""
    with open(index_path) as f:
        return json.load(f)


def regenerate_concepts_for_pdf(
    pdf_name: str,
    input_dir: Path,
    output_dir: Path,
    generator: PedagogicalContentGenerator
) -> dict:
    """Regenerate all concepts for a single PDF."""
    
    print(f"\n{'='*60}")
    print(f"Processing: {pdf_name}")
    print(f"{'='*60}")
    
    # Load chunks and manifest
    chunks_path = input_dir / "chunks.json"
    manifest_path = input_dir / "concept-manifest.json"
    
    if not chunks_path.exists():
        print(f"  ❌ No chunks.json found at {chunks_path}")
        return {"status": "skipped", "reason": "no_chunks"}
    
    if not manifest_path.exists():
        print(f"  ❌ No concept-manifest.json found at {manifest_path}")
        return {"status": "skipped", "reason": "no_manifest"}
    
    with open(chunks_path) as f:
        chunks = json.load(f)
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    concepts = manifest.get("concepts", {})
    print(f"  📚 Found {len(concepts)} concepts to regenerate")
    
    # Create output directories
    concepts_output = output_dir / "concepts"
    concepts_output.mkdir(parents=True, exist_ok=True)
    
    regenerated = []
    errors = []
    
    for concept_id, concept_info in concepts.items():
        try:
            print(f"  📝 Regenerating: {concept_id}...", end=" ")
            
            # Get chunks for this concept
            concept_chunks = []
            for section in concept_info.get("sections", {}).values():
                for chunk_id in section.get("chunkIds", []):
                    # Find chunk by ID
                    for chunk in chunks:
                        if chunk.get("chunkId") == chunk_id:
                            concept_chunks.append(chunk)
                            break
            
            # Get practice problem links
            practice_links = CONCEPT_TO_PROBLEMS.get(concept_id, [])
            
            # Generate pedagogical concept
            new_concept = generator.generate_pedagogical_concept(
                concept_id=concept_id,
                concept_title=concept_info.get("title", concept_id),
                raw_chunks=concept_chunks,
                practice_problem_links=practice_links
            )
            
            # Generate markdown
            markdown = generator.generate_markdown(new_concept)
            
            # Save markdown
            md_path = concepts_output / f"{concept_id}.md"
            with open(md_path, 'w') as f:
                f.write(markdown)
            
            # Save JSON
            json_path = concepts_output / f"{concept_id}.json"
            with open(json_path, 'w') as f:
                json.dump(new_concept, f, indent=2)
            
            regenerated.append(concept_id)
            print(f"✅")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            errors.append({"concept": concept_id, "error": str(e)})
    
    # Generate new concept map
    concept_map = {
        "version": "2.0.0",
        "generatedAt": datetime.now().isoformat(),
        "sourceDocId": manifest.get("sourceDocId", pdf_name),
        "concepts": {}
    }
    
    for concept_id, concept_info in concepts.items():
        # Get chunk IDs from original manifest
        chunk_ids = {"definition": [], "examples": [], "commonMistakes": []}
        for section_name, section in concept_info.get("sections", {}).items():
            if section_name in chunk_ids:
                chunk_ids[section_name] = section.get("chunkIds", [])
        
        concept_map["concepts"][concept_id] = {
            "title": concept_info.get("title", concept_id),
            "definition": concept_info.get("definition", ""),
            "difficulty": concept_info.get("difficulty", "beginner"),
            "pageNumbers": concept_info.get("pageReferences", []),
            "chunkIds": chunk_ids,
            "relatedConcepts": concept_info.get("relatedConcepts", []),
            "practiceProblemIds": CONCEPT_TO_PROBLEMS.get(concept_id, [])
        }
    
    # Save concept map
    map_path = output_dir / "concept-map.json"
    with open(map_path, 'w') as f:
        json.dump(concept_map, f, indent=2)
    
    print(f"\n  ✅ Regenerated {len(regenerated)} concepts")
    print(f"  📄 Output: {output_dir}")
    print(f"  🗺️  Concept map: {map_path}")
    
    if errors:
        print(f"  ⚠️  Errors: {len(errors)}")
        for err in errors:
            print(f"      - {err['concept']}: {err['error']}")
    
    return {
        "status": "success",
        "regenerated": len(regenerated),
        "errors": len(errors),
        "output_dir": str(output_dir)
    }


def main():
    """Main regeneration function."""
    print("="*70)
    print("CONCEPT REGENERATION PIPELINE")
    print("="*70)
    print("\nThis will regenerate all concept files using the new")
    print("pedagogical pipeline with practice schema alignment.")
    print()
    
    # Initialize generator
    generator = PedagogicalContentGenerator(
        PRACTICE_SCHEMAS,
        TEXTBOOK_TO_PRACTICE_MAPPING
    )
    
    # Find all processed PDFs
    read_use_dir = Path("read_use")
    if not read_use_dir.exists():
        print("❌ No read_use/ directory found!")
        print("   Please process PDFs first using ./start.sh")
        return
    
    pdf_dirs = [d for d in read_use_dir.iterdir() if d.is_dir()]
    
    if not pdf_dirs:
        print("❌ No processed PDFs found in read_use/")
        return
    
    print(f"Found {len(pdf_dirs)} processed PDF(s):")
    for pdf_dir in pdf_dirs:
        print(f"  - {pdf_dir.name}")
    
    # Create main output directory
    output_base = Path("output/regenerated")
    output_base.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    for pdf_dir in pdf_dirs:
        input_dir = pdf_dir  # Files are directly in the pdf_dir, not in pdf-index subdir
        output_dir = output_base / pdf_dir.name
        
        result = regenerate_concepts_for_pdf(
            pdf_name=pdf_dir.name,
            input_dir=input_dir,
            output_dir=output_dir,
            generator=generator
        )
        
        results.append({
            "pdf": pdf_dir.name,
            **result
        })
    
    # Summary
    print("\n" + "="*70)
    print("REGENERATION SUMMARY")
    print("="*70)
    
    total_regenerated = sum(r.get("regenerated", 0) for r in results)
    total_errors = sum(r.get("errors", 0) for r in results)
    
    print(f"\nTotal PDFs processed: {len(results)}")
    print(f"Total concepts regenerated: {total_regenerated}")
    print(f"Total errors: {total_errors}")
    print(f"\nOutput location: {output_base}")
    
    # Copy to SQL-Adapt
    sql_adapt_target = Path("/Users/harrydai/Desktop/Personal Portfolio/adaptive-instructional-artifacts/apps/web/public/textbook-static")
    
    if sql_adapt_target.exists():
        print(f"\n📤 To copy to SQL-Adapt, run:")
        print(f"   cp -r {output_base}/* {sql_adapt_target}/")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
