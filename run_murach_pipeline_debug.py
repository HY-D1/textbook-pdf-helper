#!/usr/bin/env python3
"""Debug run of the Murach MySQL PDF pipeline."""
from __future__ import annotations

import time
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def log(msg):
    ts = time.strftime('%H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open("murach_debug.log", "a") as f:
        f.write(line + "\n")
        f.flush()

log("Starting debug script")

log("Importing components...")
from algl_pdf_helper.section_extractor import SectionExtractor, BlockType, ContentFilter
from algl_pdf_helper.sql_ontology import ConceptOntology
from algl_pdf_helper.unit_generator import UnitGenerator, GenerationConfig as UnitGenerationConfig
from algl_pdf_helper.instructional_pipeline import PipelineConfig, InstructionalPipeline
from algl_pdf_helper.misconception_bank import MisconceptionBank

log("Creating config...")
config = PipelineConfig(
    pdf_path=Path("raw_pdf/murachs-mysql-3rd-edition.pdf"),
    output_dir=Path("outputs/murach"),
    filter_level="production",
    skip_reinforcement=True,
    skip_misconceptions=True,
    use_ollama_repair=False
)

log("Extracting and filtering blocks...")
extractor = SectionExtractor()
blocks = extractor.extract_blocks(config.pdf_path, config.doc_id or "murach-mysql")
content_filter = ContentFilter()
teaching_blocks = content_filter.filter_blocks(blocks)
log(f"Got {len(teaching_blocks)} teaching blocks")

log("Mapping to concepts...")
pipeline = InstructionalPipeline(config)
pipeline._teaching_blocks = teaching_blocks
concept_blocks = pipeline._map_to_concepts()
log(f"Mapped to {len(concept_blocks)} concepts")

# Test generating for just one concept
log("Testing unit generation for first concept...")
first_concept_id = list(concept_blocks.keys())[0]
first_blocks = concept_blocks[first_concept_id]
log(f"First concept: {first_concept_id} with {len(first_blocks)} blocks")

unit_generator = UnitGenerator()
gen_config = UnitGenerationConfig(
    llm_provider=config.llm_provider,
    model_name=config.llm_model,
    allow_synthetic_examples=config.allow_synthetic_examples,
    enable_ollama_repair=False,  # KEY: Disable Ollama repair
)

misconception_bank = MisconceptionBank.load_default()

log("Generating L1 hint...")
start = time.time()
try:
    l1_unit = unit_generator.generate_L1_hint(
        first_concept_id, first_blocks, gen_config, [], []
    )
    elapsed = time.time() - start
    log(f"L1 hint generated in {elapsed:.1f}s")
    log(f"Title: {l1_unit.title[:50] if l1_unit.title else 'None'}...")
except Exception as e:
    elapsed = time.time() - start
    log(f"L1 FAILED after {elapsed:.1f}s: {e}")

log("DONE!")
