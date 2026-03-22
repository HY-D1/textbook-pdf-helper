from __future__ import annotations

import json
import os
import warnings
from pathlib import Path

import typer

from .export_sqladapt import export_to_sqladapt, validate_handoff_integrity
from .extract import (
    check_extraction_quality,
    check_text_coverage,
    extract_pages_fitz,
    extract_with_strategy,
)
from .indexer import build_index
from .models import IndexBuildOptions, OutputConfig
from .preflight import run_preflight, ExtractionStrategy
from .quality_metrics import validate_text_quality
from .structure_extractor import StructureExtractor
from .mapping_generator import MappingGenerator
from .mapping_workflow import MappingWorkflow

app = typer.Typer(add_completion=False)

# Import educational CLI
try:
    from .cli_educational import app as educational_app
    app.add_typer(educational_app, name="edu", help="Educational note generation")
except ImportError:
    pass  # Educational CLI is optional

# Unit library commands are re-exported as top-level commands below (line ~1149)


def resolve_output_dir(output_dir: Path | None) -> Path:
    """
    Resolve output directory from CLI option or environment variable.
    
    Priority:
    1. --output-dir CLI option
    2. SQL_ADAPT_PUBLIC_DIR/textbook-static environment variable
    3. Error with helpful message
    """
    config = OutputConfig(output_dir=output_dir)
    try:
        return config.resolve()
    except ValueError as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def index(
    input_path: Path = typer.Argument(..., exists=True, help="PDF file or directory"),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir", "-o",
        help="Output directory (or set SQL_ADAPT_PUBLIC_DIR env var)"
    ),
    ocr: bool = typer.Option(False, help="Force OCR (requires ocrmypdf)"),
    auto_ocr: bool = typer.Option(True, help="Auto OCR when little/no text is found"),
    use_aliases: bool = typer.Option(
        False,
        help="Use stable doc aliases (e.g. sql-textbook) instead of doc-<sha>",
    ),
    chunk_words: int = typer.Option(180, help="Words per chunk"),
    overlap_words: int = typer.Option(30, help="Overlapping words"),
    embedding_dim: int = typer.Option(24, help="Hash embedding dimension"),
    strip_headers: bool = typer.Option(True, help="Heuristically strip headers/footers"),
    concepts_config: Path | None = typer.Option(
        None,
        help="Path to concepts.yaml config (auto-detected if not specified)",
    ),
    smart_skip_threshold: float = typer.Option(
        0.90,
        help="Quality threshold above which OCR is skipped (0.0-1.0). "
             "PDFs with text coverage above this threshold will skip OCR even when --ocr is used. "
             "Set to 1.0 to disable smart skip and always use OCR when requested.",
    ),
):
    """Build PDF index to textbook-static format.
    
    SMART OCR SKIP (default enabled):
    When --ocr is used but the PDF has excellent text quality (>90% coverage),
    OCR will be automatically skipped to avoid Tesseract errors on digital PDFs.
    Use --smart-skip-threshold=1.0 to force OCR regardless of quality.
    """
    out = resolve_output_dir(output_dir)
    
    opts = IndexBuildOptions(
        chunkWords=chunk_words,
        overlapWords=overlap_words,
        embeddingDim=embedding_dim,
    )
    doc = build_index(
        input_path,
        out,
        options=opts,
        ocr=ocr,
        auto_ocr=auto_ocr,
        use_aliases=use_aliases,
        strip_headers=strip_headers,
        concepts_config=concepts_config,
        smart_skip_threshold=smart_skip_threshold,
    )
    typer.echo(f"✅ Wrote PDF index to: {out}")
    typer.echo(f"   Index ID: {doc.indexId}")
    typer.echo(f"   Docs: {doc.docCount}  Chunks: {doc.chunkCount}")
    
    # Check if concept files were generated
    concept_manifest_path = out / "concept-manifest.json"
    if concept_manifest_path.exists():
        import json
        manifest = json.loads(concept_manifest_path.read_text())
        typer.echo(f"   Concepts: {manifest.get('conceptCount', 0)}")
        concepts_dir = out / "concepts"
        if concepts_dir.exists():
            typer.echo(f"   Concept markdowns: {concepts_dir}")
    
    # Show schema info
    typer.echo(f"\n📋 Schema: textbook-static-v1 (v1.0.0)")


@app.command()
def check_quality(
    pdf_path: Path = typer.Argument(..., exists=True, help="PDF file to check"),
    detailed: bool = typer.Option(
        False,
        "--detailed",
        help="Show detailed page-by-page analysis",
    ),
    preflight_check: bool = typer.Option(
        False,
        "--preflight",
        help="Show comprehensive preflight report",
    ),
):
    """Check text extraction quality of a PDF without processing."""
    typer.echo(f"Checking quality of: {pdf_path.name}")
    typer.echo("")
    
    # Run comprehensive preflight if requested
    if preflight_check:
        typer.echo("=" * 60)
        typer.echo("COMPREHENSIVE PREFLIGHT REPORT")
        typer.echo("=" * 60)
        
        try:
            report = run_preflight(pdf_path)
            
            typer.echo(f"\n📊 Document Overview")
            typer.echo(f"   Total pages: {report.page_count}")
            typer.echo(f"   Sampled pages: {', '.join(map(str, report.sample_pages_analyzed))}")
            typer.echo(f"   Average text density: {report.average_page_text_density:.0f} chars/page")
            
            typer.echo(f"\n🔍 Text Analysis")
            typer.echo(f"   Has embedded text: {'✅ Yes' if report.has_embedded_text else '❌ No'}")
            typer.echo(f"   OCR needed: {'⚠️ Yes' if report.ocr_needed else '✅ No'}")
            typer.echo(f"   Text coverage score: {report.text_coverage_score:.1%}")
            
            typer.echo(f"\n📐 Structure Detection")
            typer.echo(f"   Estimated tables: ~{report.estimated_table_count}")
            typer.echo(f"   Estimated figures: ~{report.estimated_figure_count}")
            
            if report.warning_flags:
                typer.echo(f"\n⚠️  Warning Flags")
                for flag in report.warning_flags:
                    typer.echo(f"   - {flag}")
            else:
                typer.echo(f"\n✅ No warnings")
            
            typer.echo(f"\n📋 Recommendation")
            typer.echo(f"   Strategy: {report.recommended_strategy}")
            
            if report.recommended_strategy == "direct":
                typer.echo(f"   ✅ PDF has good embedded text, direct extraction recommended")
            elif report.recommended_strategy == "ocrmypdf":
                typer.echo(f"   ⚠️  OCR recommended - use: algl-pdf index {pdf_path} --ocr")
            elif report.recommended_strategy == "marker":
                typer.echo(f"   📊 Complex layout detected - Marker may work better")
            
            typer.echo("")
            return
            
        except Exception as e:
            typer.echo(f"❌ Preflight analysis failed: {e}")
            typer.echo("Falling back to basic quality check...\n")
    
    # Basic quality check (legacy)
    pages = extract_pages_fitz(pdf_path)
    quality = check_extraction_quality(pages)
    
    typer.echo(f"Pages with text: {quality['page_count']}")
    typer.echo(f"Total characters: {quality['total_chars']:,}")
    typer.echo(f"Readable ratio: {quality['readable_ratio']:.1%}")
    typer.echo(f"Gibberish ratio: {quality['gibberish_ratio']:.1%}")
    typer.echo("")
    
    # Also show new coverage metric
    coverage = check_text_coverage(pages)
    typer.echo(f"Text coverage score: {coverage['coverage_score']:.1%}")
    typer.echo(f"Meets threshold: {'✅ Yes' if coverage['meets_threshold'] else '❌ No'}")
    typer.echo("")
    
    if quality['is_quality_good']:
        typer.echo("✅ Quality is GOOD - no OCR needed")
    else:
        typer.echo(f"⚠️  Quality is POOR - OCR recommended")
        if quality['reason']:
            typer.echo(f"   Reason: {quality['reason']}")
    
    # Detailed page analysis
    if detailed and pages:
        typer.echo("")
        typer.echo("=" * 60)
        typer.echo("PAGE-BY-PAGE ANALYSIS")
        typer.echo("=" * 60)
        
        from .quality_metrics import TextCoverageAnalyzer
        analyzer = TextCoverageAnalyzer()
        
        for page_num, text in pages[:20]:  # Limit to first 20 pages
            validation = validate_text_quality(text)
            status = "✅" if validation["passed"] else "❌"
            typer.echo(f"\n{status} Page {page_num}")
            typer.echo(f"   Characters: {validation['total_chars']:,}")
            typer.echo(f"   Coverage: {validation['coverage_score']:.1%}")
            if validation['fail_reasons']:
                typer.echo(f"   Issues: {', '.join(validation['fail_reasons'])}")
        
        if len(pages) > 20:
            typer.echo(f"\n... ({len(pages) - 20} more pages)")


@app.command()
def export(
    input_dir: Path = typer.Argument(
        ..., 
        exists=True, 
        help="Input directory with processed PDF (contains concept-manifest.json)"
    ),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir", "-o",
        help="Output directory (or set SQL_ADAPT_PUBLIC_DIR env var)"
    ),
    merge: bool = typer.Option(True, help="Merge with existing exports instead of overwriting"),
):
    """Export processed PDF to SQL-Adapt compatible format."""
    out = resolve_output_dir(output_dir)
    
    typer.echo(f"Exporting from: {input_dir}")
    typer.echo(f"Output to: {out}")
    typer.echo(f"Mode: {'Merge' if merge else 'Overwrite'}")
    typer.echo("")
    
    try:
        result = export_to_sqladapt(input_dir, out, merge=merge)
        
        if result.get('is_new_pdf'):
            typer.echo(f"✅ Added new PDF: {result['source_doc_id']}")
        else:
            typer.echo(f"✅ Updated PDF: {result['source_doc_id']}")
        
        typer.echo(f"   Concepts from this PDF: {result['concept_count']}")
        typer.echo(f"   Total concepts in export: {result['total_concepts']}")
        
        if result.get('generated_files'):
            typer.echo(f"   New files: {len(result['generated_files'])}")
        if result.get('updated_files'):
            typer.echo(f"   Updated files: {len(result['updated_files'])}")
            
        typer.echo(f"   Concept map: {result['concept_map']}")
        typer.echo(f"   Concepts directory: {result['concepts_dir']}")
        
    except FileNotFoundError as e:
        typer.echo(f"❌ Error: {e}")
        typer.echo("")
        typer.echo("Make sure the input directory contains:")
        typer.echo("  - concept-manifest.json")
        typer.echo("  - chunks.json")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Export failed: {e}")
        raise typer.Exit(1)


@app.command(name="validate-handoff")
def validate_handoff(
    output_dir: Path = typer.Argument(
        ...,
        exists=True,
        help="textbook-static export directory to validate",
    ),
):
    """Validate a textbook-static export directory for adaptive app handoff.

    Checks that concept-map.json, textbook-manifest.json, chunks-metadata.json,
    and all concept .md files are internally consistent.  Exits with code 1 if
    any fatal integrity violation is found.
    """
    result = validate_handoff_integrity(output_dir)

    typer.echo(f"Validating: {output_dir}")
    typer.echo(f"  Concept-map entries : {result['concept_map_entries']}")
    typer.echo(f"  Markdown files       : {result['markdown_files']}")
    typer.echo(f"  Textbook units        : {result['units_count']}")
    typer.echo(f"  Source docs (manifest): {result['source_docs_count']}")
    typer.echo(f"  Doc directories      : {result['doc_dirs_count']}")
    typer.echo(f"  chunks-metadata docIds: {result['chunks_meta_doc_ids']}")
    # Learner quality summary
    fallback_count = result.get("fallback_only_count", 0)
    total_units = result.get("units_count", 0)
    if total_units > 0:
        ok_count = total_units - fallback_count
        typer.echo(
            f"  Learner quality      : {ok_count} ok, "
            f"{fallback_count} fallback_only"
            f" ({fallback_count / total_units:.0%} fallback)"
        )

    if result["warnings"]:
        for w in result["warnings"]:
            typer.echo(f"  ⚠️  {w}")

    if result["errors"]:
        for e in result["errors"]:
            typer.echo(f"  ❌ {e}")
        typer.echo("")
        typer.echo("Handoff integrity: INVALID")
        raise typer.Exit(1)

    typer.echo("")
    typer.echo("✅ Handoff integrity: VALID")


@app.command()
def export_edu(
    pdf_path: Path = typer.Argument(..., exists=True, help="Path to PDF file"),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir", "-o",
        help="Output directory (or set SQL_ADAPT_PUBLIC_DIR env var)"
    ),
    llm_provider: str = typer.Option("kimi", help="LLM provider: openai, kimi, or ollama"),
    use_marker: bool = typer.Option(
        True, 
        "--use-marker/--no-use-marker",
        help="Use Marker for PDF extraction (disable for large PDFs to save memory)",
    ),
    ollama_model: str = typer.Option(
        "llama3.2:3b",
        help="Ollama model to use (for local LLM): llama3.2:3b, qwen2.5:7b, phi4, mistral:7b, gemma2:9b",
    ),
    skip_llm: bool = typer.Option(
        False,
        "--skip-llm",
        help="Skip LLM enhancement (faster but lower quality output)",
    ),
    concepts_config: Path | None = typer.Option(
        None,
        "--concepts-config",
        help="Path to concepts.yaml config file (auto-detected if not specified)",
    ),
    max_concepts: int | None = typer.Option(
        None,
        "--max-concepts",
        help="Limit number of concepts to process (for testing)",
    ),
    pedagogical: bool = typer.Option(
        False,
        "--pedagogical",
        help="Use pedagogical content generation with practice schemas and SQL-Adapt integration",
    ),
):
    """
    Export PDF to SQL-Adapt with educational note generation.
    
    Use --pedagogical flag to enable the pedagogical content generation pipeline.
    """
    out = resolve_output_dir(output_dir)
    
    try:
        from .educational_pipeline import EducationalNoteGenerator
        from .concept_mapper import load_concepts_config, find_concepts_config
        from tqdm import tqdm
    except ImportError as e:
        typer.echo(f"❌ Error: Missing dependencies for educational export: {e}")
        typer.echo("Install with: pip install -e '.[unit]'")
        raise typer.Exit(1)
    
    typer.echo(f"📚 Generating educational notes from: {pdf_path}")
    typer.echo(f"📁 Exporting to: {out}")
    typer.echo(f"🤖 LLM Provider: {llm_provider}")
    
    # Display pedagogical mode status
    if pedagogical:
        typer.echo("🎓 Pedagogical Mode: ENABLED")
        typer.echo("   - Using practice schemas (users, orders, products, employees, departments)")
        typer.echo("   - Generating learning objectives and prerequisites")
        typer.echo("   - Linking to SQL-Adapt practice problems")
    if llm_provider.lower() == "ollama":
        typer.echo(f"🦙 Ollama Model: {ollama_model}")
    typer.echo()
    
    # Check file size for info
    pdf_size_mb = pdf_path.stat().st_size / (1024 * 1024)
    
    if pdf_size_mb > 50:
        typer.echo(f"ℹ️  Large PDF detected ({pdf_size_mb:.1f}MB)")
        typer.echo(f"   Auto-split will be used if needed.")
        typer.echo()
    
    # Load concepts configuration
    concepts_config_path = concepts_config
    if concepts_config_path is None:
        concepts_config_path = find_concepts_config(pdf_path)
        typer.echo(f"🔍 Looking for concepts config...")
        typer.echo(f"   Path found: {concepts_config_path}")
    else:
        typer.echo(f"🔍 Using specified concepts config: {concepts_config_path}")
    
    concepts_config_data = None
    if concepts_config_path:
        typer.echo(f"   Path exists: {concepts_config_path.exists()}")
        if concepts_config_path.exists():
            try:
                concepts_config_data = load_concepts_config(concepts_config_path, pdf_path)
                total_concepts = len(concepts_config_data.get("concepts", {}))
                matched_textbook = concepts_config_data.get("matched_textbook", "")
                typer.echo(f"📖 Loaded concepts config: {concepts_config_path}")
                if matched_textbook:
                    typer.echo(f"   Matched textbook: {matched_textbook}")
                typer.echo(f"   Found {total_concepts} concepts defined")
            except Exception as e:
                typer.echo(f"⚠️  Warning: Failed to load concepts config: {e}")
                import traceback
                typer.echo(traceback.format_exc())
        else:
            typer.echo(f"⚠️  Config file not found at {concepts_config_path}")
    else:
        typer.echo(f"⚠️  No concepts.yaml found - will auto-detect topics")
    typer.echo()
    
    # Initialize generator with API keys from environment
    generator = EducationalNoteGenerator(
        llm_provider=llm_provider, 
        use_marker=use_marker,
        ollama_model=ollama_model,
        skip_llm=skip_llm,
        kimi_api_key=os.getenv("KIMI_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        use_pedagogical=pedagogical,
    )
    
    typer.echo(f"Configuration:")
    typer.echo(f"  Marker extraction: {generator.use_marker}")
    
    if skip_llm:
        typer.echo(f"  LLM enhancement: ⏭️  SKIPPED (fast mode)")
        typer.echo(f"   ⚠️  Output will be basic text extraction only!")
    else:
        typer.echo(f"  LLM enhancement: {generator.llm_status_message}")
        
        if not generator.llm_available:
            typer.echo()
            typer.echo("❌ ERROR: No LLM configured!")
            typer.echo("   For high-quality educational notes, you MUST configure an LLM:")
            typer.echo("   - Kimi: export KIMI_API_KEY='your-key'")
            typer.echo("   - OpenAI: export OPENAI_API_KEY='your-key'")
            typer.echo("   - Ollama: ollama pull qwen2.5-coder:7b && ollama serve")
            typer.echo()
            typer.echo("   Or use --skip-llm for basic extraction (NOT recommended)")
            raise typer.Exit(1)
    typer.echo()
    
    # Create progress callback
    current_bar = None
    current_step = None
    
    def progress_callback(step: str, current: int, total: int, message: str = ""):
        nonlocal current_bar, current_step
        
        # Close previous bar if step changed
        if step != current_step and current_bar is not None:
            current_bar.close()
            current_bar = None
        
        # Create new bar for new step
        if current_bar is None or step != current_step:
            current_step = step
            step_names = {
                "extract": "📄 PDF Extraction",
                "structure": "🔍 Content Analysis", 
                "enhance": "🎓 Generating Educational Notes",
                "format": "📋 Formatting Output",
                "save": "💾 Saving Files",
            }
            current_bar = tqdm(
                total=total,
                desc=step_names.get(step, step),
                bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}] {postfix}",
                ncols=80,
            )
        
        # Update progress
        current_bar.n = current
        if message:
            current_bar.set_postfix_str(message[:50])
        current_bar.refresh()
        
        # Close if complete
        if current >= total:
            current_bar.close()
            current_bar = None
    
    # Generate educational notes with progress
    try:
        result = generator.process_pdf(
            pdf_path, 
            concepts_config=concepts_config_data,
            output_dir=out,
            progress_callback=progress_callback,
            max_concepts=max_concepts,
        )
    finally:
        if current_bar is not None:
            current_bar.close()
        typer.echo()
    
    if not result["success"]:
        typer.echo("❌ Educational note generation failed:")
        for error in result["errors"]:
            typer.echo(f"   - {error}")
        raise typer.Exit(1)
    
    typer.echo("✅ Educational notes generated!")
    typer.echo()
    typer.echo("📊 Stats:")
    for key, value in result["stats"].items():
        typer.echo(f"   {key}: {value}")
    
    # Show pedagogical mode summary
    if pedagogical:
        typer.echo()
        typer.echo("🎓 Pedagogical Features:")
        typer.echo("   - Content transformed to practice schemas")
        typer.echo("   - Learning objectives and prerequisites included")
        typer.echo("   - Practice problem links added where available")
    
    # Show cost if LLM was used
    if result["stats"].get("llm_enhanced"):
        num_concepts = result["stats"].get("concepts_generated", 0)
        typer.echo()
        if hasattr(generator, 'estimate_cost') and num_concepts > 0:
            cost = generator.estimate_cost(num_concepts)
            typer.echo(f"💰 Actual Cost: ¥{cost['cost_rmb']['total']} RMB")
        else:
            typer.echo(f"💰 Concepts processed with LLM: {num_concepts}")
    
    # Show generated files
    typer.echo()
    typer.echo("📁 Generated files:")
    
    # Get doc_id from result
    doc_id = result["stats"].get("doc_id", "unknown")
    
    # Standard SQL-Adapt format outputs (REQUIRED)
    if (out / "concept-map.json").exists():
        typer.echo(f"   📋 concept-map.json (main index)")
    
    # Check for concepts in textbook subdirectory
    concepts_subdir = out / "concepts" / doc_id
    if concepts_subdir.exists():
        concept_count = len(list(concepts_subdir.glob("*.md")))
        typer.echo(f"   📚 concepts/{doc_id}/ ({concept_count} concept files)")
        typer.echo(f"   📖 concepts/{doc_id}/README.md")
    
    # Diagnostic/Internal files
    if (out / "concept-manifest.json").exists():
        typer.echo(f"   🔧 concept-manifest.json (internal)")
    if result["outputs"].get("extraction"):
        typer.echo(f"   🔍 {doc_id}-extraction.json (diagnostic)")
    if result["outputs"].get("sqladapt"):
        typer.echo(f"   📄 {doc_id}-sqladapt.json (diagnostic)")
    if result["outputs"].get("study_guide"):
        typer.echo(f"   📖 {doc_id}-study-guide.md (combined)")


@app.command()
def preflight(
    pdf_path: Path = typer.Argument(..., exists=True, help="PDF file to analyze"),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output report as JSON",
    ),
):
    """Run preflight analysis on a PDF to determine extraction strategy."""
    try:
        report = run_preflight(pdf_path)
        
        if json_output:
            import json
            typer.echo(json.dumps(report.to_dict(), indent=2))
        else:
            typer.echo(report.summary)
            
            typer.echo("")
            if report.is_extractable:
                typer.echo("✅ PDF is extractable with recommended strategy")
            else:
                typer.echo("❌ PDF may have extraction issues")
                typer.echo(f"   Consider using: algl-pdf index {pdf_path} --ocr")
    
    except FileNotFoundError as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Preflight failed: {e}")
        raise typer.Exit(1)


@app.command()
def extract(
    pdf_path: Path = typer.Argument(..., exists=True, help="PDF file to extract"),
    out: Path | None = typer.Option(None, help="Output text file (default: stdout)"),
    strategy: ExtractionStrategy = typer.Option(
        "direct",
        "--strategy",
        help="Extraction strategy: direct, ocrmypdf, marker",
    ),
    min_coverage: float = typer.Option(
        0.70,
        "--min-coverage",
        help="Minimum text coverage threshold (0.0-1.0)",
    ),
    validate: bool = typer.Option(
        True,
        "--validate/--no-validate",
        help="Validate extraction quality",
    ),
):
    """Extract text from PDF with quality validation."""
    typer.echo(f"Extracting: {pdf_path.name}")
    typer.echo(f"Strategy: {strategy}")
    typer.echo("")
    
    try:
        pages, info = extract_with_strategy(
            pdf_path,
            strategy=strategy,
            min_coverage=min_coverage,
        )
        
        # Combine all text
        all_text = "\n\n".join(f"--- Page {p} ---\n{t}" for p, t in pages)
        
        # Output
        if out:
            out.write_text(all_text, encoding="utf-8")
            typer.echo(f"✅ Text written to: {out}")
        else:
            typer.echo(all_text)
        
        # Show extraction info
        typer.echo("")
        typer.echo("Extraction Summary:")
        typer.echo(f"  Pages extracted: {len(pages)}")
        typer.echo(f"  OCR applied: {'Yes' if info.get('ocr_applied') else 'No'}")
        typer.echo(f"  Coverage score: {info.get('coverage_score', 0):.1%}")
        typer.echo(f"  Meets threshold: {'✅ Yes' if info.get('meets_threshold') else '⚠️ No'}")
        
        if info.get('warnings'):
            typer.echo("\n  Warnings:")
            for warning in info['warnings']:
                typer.echo(f"    ⚠️  {warning}")
        
    except Exception as e:
        typer.echo(f"❌ Extraction failed: {e}")
        raise typer.Exit(1)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(7345),
):
    """Run the optional HTTP service."""
    try:
        import uvicorn  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Server extras not installed. Install with: pip install -e '.[server]'"
        ) from e

    from .server import api

    uvicorn.run(api, host=host, port=port)


# =============================================================================
# PHASE 3: AUTO-MAPPING COMMANDS
# =============================================================================

@app.command()
def suggest_mapping(
    pdf_path: Path = typer.Argument(..., exists=True, help="PDF file to analyze"),
    output: Path = typer.Option(Path("./draft-mapping.yaml"), help="Output YAML file path"),
    confidence_threshold: float = typer.Option(
        0.5,
        help="Minimum confidence for automatic acceptance"
    ),
    registry_path: Path | None = typer.Option(
        None,
        help="Path to concept registry YAML (uses default if not specified)"
    ),
    max_concepts: int | None = typer.Option(
        None,
        help="Maximum number of concepts to generate"
    ),
    format: str = typer.Option(
        "yaml",
        help="Output format: yaml or json"
    ),
):
    """Generate draft concepts.yaml from PDF structure analysis.
    
    This command analyzes the PDF's table of contents and headings to
    automatically suggest concept mappings. The output is a draft YAML
    file that should be reviewed before use.
    
    Example:
        algl-pdf suggest-mapping ./textbook.pdf --output ./concepts.yaml
        algl-pdf suggest-mapping ./textbook.pdf --confidence-threshold 0.7
    """
    typer.echo(f"🔍 Analyzing PDF structure: {pdf_path.name}")
    typer.echo(f"📊 Confidence threshold: {confidence_threshold}")
    
    # Use default registry if not specified
    if registry_path is None:
        registry_path = Path(__file__).parent.parent.parent / "data" / "concept_registry.yaml"
        if not registry_path.exists():
            registry_path = None  # Will use built-in defaults
    
    # Initialize generator
    generator = MappingGenerator(
        registry_path=registry_path,
        confidence_threshold=confidence_threshold,
        max_concepts=max_concepts
    )
    
    # Generate draft mapping
    try:
        draft = generator.generate_draft_mapping(pdf_path, registry_path)
    except Exception as e:
        typer.echo(f"❌ Error generating mapping: {e}")
        raise typer.Exit(1)
    
    # Get summary
    summary = generator.get_mapping_summary(draft)
    
    typer.echo(f"\n📈 Analysis Results:")
    typer.echo(f"   Total pages: {summary['total_pages']}")
    typer.echo(f"   Detected headings: {summary['detected_headings']}")
    typer.echo(f"   Matched concepts: {summary['matched_concepts']}")
    typer.echo(f"   High confidence: {summary['high_confidence']}")
    typer.echo(f"   Needs review: {summary['needs_review']}")
    typer.echo(f"   Unmatched headings: {summary['unmatched_headings']}")
    
    typer.echo(f"\n📊 By Difficulty:")
    for diff, count in summary['by_difficulty'].items():
        if count > 0:
            typer.echo(f"   {diff}: {count}")
    
    # Export based on format
    if format.lower() == "json":
        output_path = output.with_suffix(".json")
        generator.export_to_json(draft, output_path)
    else:
        output_path = output.with_suffix(".yaml") if not output.suffix == ".yaml" else output
        generator.export_to_yaml(draft, output_path, include_metadata=True)
    
    typer.echo(f"\n✅ Draft mapping saved to: {output_path}")
    
    if summary['needs_review'] > 0:
        typer.echo(f"\n⚠️  {summary['needs_review']} concepts need review.")
        typer.echo("   Run 'review-mapping' command to create a review package.")


@app.command()
def review_mapping(
    pdf_path: Path = typer.Argument(..., exists=True, help="PDF file to analyze"),
    output: Path = typer.Option(Path("./review-package.json"), help="Output review package path"),
    confidence_threshold: float = typer.Option(
        0.5,
        help="Minimum confidence for automatic acceptance"
    ),
    registry_path: Path | None = typer.Option(
        None,
        help="Path to concept registry YAML"
    ),
):
    """Create a comprehensive review package for human-in-the-loop workflow.
    
    This command creates a detailed review package with:
    - Draft concept mappings
    - Confidence scores
    - Suggested edits
    - Preview of generated content
    
    The review package should be edited and then applied to create the final
    concepts.yaml configuration.
    
    Example:
        algl-pdf review-mapping ./textbook.pdf --output ./review.json
    """
    typer.echo(f"🔍 Creating review package for: {pdf_path.name}")
    
    # Use default registry if not specified
    if registry_path is None:
        registry_path = Path(__file__).parent.parent.parent / "data" / "concept_registry.yaml"
        if not registry_path.exists():
            registry_path = None
    
    # Initialize workflow
    workflow = MappingWorkflow(
        registry_path=registry_path,
        confidence_threshold=confidence_threshold
    )
    
    # Generate draft and create review package
    try:
        generator = MappingGenerator(
            registry_path=registry_path,
            confidence_threshold=confidence_threshold
        )
        draft = generator.generate_draft_mapping(pdf_path, registry_path)
        package = workflow.create_review_package(draft, include_previews=True)
    except Exception as e:
        typer.echo(f"❌ Error creating review package: {e}")
        raise typer.Exit(1)
    
    # Export package
    output_path = workflow.export_review_package(package, output)
    
    typer.echo(f"\n📦 Review Package Created: {output_path}")
    typer.echo(f"   Package ID: {package.package_id}")
    typer.echo(f"   PDF: {package.pdf_name}")
    typer.echo(f"   Total pages: {package.total_pages}")
    typer.echo(f"   Concepts: {package.statistics['matched_concepts']}")
    typer.echo(f"   Suggestions: {len(package.suggestions)}")
    typer.echo(f"   Export ready: {'Yes' if package.export_ready else 'No'}")
    
    typer.echo(f"\n📝 Review Instructions:")
    for instruction in workflow._get_review_instructions():
        typer.echo(f"   {instruction}")
    
    # Show suggestions summary
    if package.suggestions:
        typer.echo(f"\n💡 Top Suggestions:")
        for i, suggestion in enumerate(package.suggestions[:5], 1):
            typer.echo(f"   {i}. [{suggestion.type}] {suggestion.description}")


@app.command()
def extract_structure(
    pdf_path: Path = typer.Argument(..., exists=True, help="PDF file to analyze"),
):
    """Extract and display document structure (TOC, headings, chapters).
    
    This is a diagnostic command to see what structure the auto-mapping
    system detects in the PDF.
    
    Example:
        algl-pdf extract-structure ./textbook.pdf
    """
    typer.echo(f"🔍 Extracting structure from: {pdf_path.name}")
    typer.echo()
    
    extractor = StructureExtractor()
    
    # Get full structure summary
    summary = extractor.get_structure_summary(pdf_path)
    
    typer.echo("📊 Document Summary:")
    typer.echo(f"   Total pages: {summary['total_pages']}")
    typer.echo(f"   Has TOC: {'Yes' if summary['has_toc'] else 'No'}")
    typer.echo(f"   TOC entries: {summary['toc_entries']}")
    typer.echo(f"   Detected headings: {summary['detected_headings']}")
    
    if summary['headings_by_level']:
        typer.echo(f"\n📑 Headings by Level:")
        for level, count in summary['headings_by_level'].items():
            if count > 0:
                typer.echo(f"   Level {level}: {count}")
    
    # Show chapters
    if summary['chapters']:
        typer.echo(f"\n📚 Detected Chapters:")
        for i, ch in enumerate(summary['chapters'][:10], 1):
            pages = f"pp. {ch['start_page']}-{ch['end_page']}" if ch['end_page'] else f"p. {ch['start_page']}"
            typer.echo(f"   {i}. {ch['title'][:50]}")
            typer.echo(f"      {pages}, {ch['section_count']} sections")
        
        if len(summary['chapters']) > 10:
            typer.echo(f"   ... and {len(summary['chapters']) - 10} more")
    
    # Show TOC if available
    toc = extractor.extract_toc(pdf_path)
    if toc:
        typer.echo(f"\n📋 Table of Contents (first 10):")
        for entry in toc[:10]:
            indent = "  " * (entry.level - 1)
            typer.echo(f"   {indent}• {entry.title[:40]} (p. {entry.page})")
    
    # Show sample headings
    headings = extractor.extract_headings(pdf_path)
    if headings:
        typer.echo(f"\n📝 Sample Headings (first 10):")
        for h in headings[:10]:
            confidence = "🟢" if h.confidence > 0.8 else "🟡" if h.confidence > 0.5 else "🔴"
            typer.echo(f"   {confidence} L{h.level} p.{h.page}: {h.text[:50]}")



# =============================================================================
# CI / QUALITY GATE COMMANDS
# =============================================================================

@app.command()
def evaluate(
    input_dir: Path = typer.Argument(
        ...,
        exists=True,
        help="Directory containing processed PDF output (with index.json)"
    ),
    baseline: Path | None = typer.Option(
        None,
        "--baseline",
        "-b",
        help="Baseline directory for comparison",
    ),
    threshold: float = typer.Option(
        0.70,
        "--threshold",
        "-t",
        help="Minimum quality score threshold (0.0-1.0)",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output path for evaluation report JSON",
    ),
):
    """Evaluate PDF processing quality against expected metrics.
    
    This command runs quality checks on processed PDF output and optionally
    compares against a baseline. It checks:
    - Concept coverage
    - Chunk quality
    - Schema version consistency
    - File completeness
    
    Example:
        algl-pdf evaluate ./output --threshold 0.75
        algl-pdf evaluate ./output --baseline ./baseline --output report.json
    """
    from .metrics import EvaluationReport, CoverageMetric, QualityScore
    from .regression_detector import load_baseline
    from .embedding import build_hash_embedding
    
    typer.echo(f"🔍 Evaluating: {input_dir}")
    typer.echo(f"📊 Quality threshold: {threshold:.0%}")
    
    # Load the processed document
    index_path = input_dir / "index.json"
    if not index_path.exists():
        typer.echo(f"❌ Error: index.json not found in {input_dir}")
        raise typer.Exit(1)
    
    try:
        index_data = json.loads(index_path.read_text())
        from .models import PdfIndexDocument
        document = PdfIndexDocument(**index_data)
    except Exception as e:
        typer.echo(f"❌ Error loading index: {e}")
        raise typer.Exit(1)
    
    # Load concept manifest if available
    concept_manifest_path = input_dir / "concept-manifest.json"
    concept_manifest = None
    if concept_manifest_path.exists():
        try:
            from .models import ConceptManifest
            manifest_data = json.loads(concept_manifest_path.read_text())
            concept_manifest = ConceptManifest(**manifest_data)
            typer.echo(f"✅ Loaded {concept_manifest.conceptCount} concepts")
        except Exception as e:
            typer.echo(f"⚠️  Warning: Could not load concept manifest: {e}")
    
    # Load baseline if specified
    baseline_doc = None
    if baseline:
        typer.echo(f"📋 Comparing against baseline: {baseline}")
        try:
            baseline_doc, baseline_manifest = load_baseline(baseline)
            typer.echo(f"✅ Baseline loaded: {baseline_doc.chunkCount} chunks")
        except Exception as e:
            typer.echo(f"⚠️  Warning: Could not load baseline: {e}")
            baseline_doc = None
    
    # Build evaluation report
    from datetime import datetime, timezone
    
    report = EvaluationReport(
        document_id=document.indexId,
        evaluation_time=datetime.now(timezone.utc).isoformat(),
        chunk_count=document.chunkCount,
        concept_count=len(concept_manifest.concepts) if concept_manifest else 0,
        page_count=sum(d.pageCount for d in document.sourceDocs),
    )
    
    # Coverage metric
    expected_concepts = ["select-basic", "where-clause", "join-operations"]
    found_concepts = list(concept_manifest.concepts.keys()) if concept_manifest else []
    report.coverage = CoverageMetric(
        expected_concepts=expected_concepts,
        found_concepts=found_concepts,
    )
    
    # Quality score
    report.quality = QualityScore(
        coverage_score=report.coverage.coverage_ratio,
        retrieval_score=1.0 if concept_manifest else 0.0,  # Simplified
    )
    report.calculate_chunk_quality(document.chunks)
    
    # Display results
    typer.echo("")
    typer.echo("=" * 60)
    typer.echo("EVALUATION RESULTS")
    typer.echo("=" * 60)
    typer.echo(f"")
    typer.echo(f"📄 Document: {document.sourceName}")
    typer.echo(f"🆔 Index ID: {document.indexId}")
    typer.echo(f"")
    typer.echo(f"📊 Metrics:")
    typer.echo(f"   Chunks: {document.chunkCount}")
    typer.echo(f"   Pages: {report.page_count}")
    typer.echo(f"   Concepts: {report.concept_count}")
    typer.echo(f"")
    typer.echo(f"🎯 Coverage:")
    typer.echo(f"   Expected: {len(expected_concepts)}")
    typer.echo(f"   Found: {len(found_concepts)}")
    typer.echo(f"   Ratio: {report.coverage.coverage_ratio:.1%}")
    if report.coverage.missing_concepts:
        typer.echo(f"   Missing: {', '.join(report.coverage.missing_concepts)}")
    typer.echo(f"")
    typer.echo(f"⭐ Quality Score:")
    typer.echo(f"   Overall: {report.quality.overall_score:.2f}")
    typer.echo(f"   Grade: {report.quality.grade}")
    typer.echo(f"   Coverage: {report.quality.coverage_score:.2f}")
    typer.echo(f"   Chunk Quality: {report.quality.chunk_quality_score:.2f}")
    typer.echo(f"")
    
    # Pass/fail
    passed = report.quality.overall_score >= threshold
    if passed:
        typer.echo(f"✅ PASSED (>= {threshold:.0%})")
    else:
        typer.echo(f"❌ FAILED (< {threshold:.0%})")
    
    # Save report if requested
    if output:
        report.save(output)
        typer.echo(f"")
        typer.echo(f"💾 Report saved: {output}")
    
    # Exit with error code if failed
    if not passed:
        raise typer.Exit(1)


@app.command()
def detect_regressions(
    baseline: Path = typer.Argument(
        ...,
        exists=True,
        help="Baseline output directory",
    ),
    current: Path = typer.Argument(
        ...,
        exists=True,
        help="Current output directory to compare",
    ),
    tolerance: float = typer.Option(
        0.10,
        "--tolerance",
        "-t",
        help="Chunk count change tolerance (0.10 = 10%)",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output path for regression report JSON",
    ),
):
    """Detect regressions between baseline and current output.
    
    Compares two PDF processing outputs and reports any regressions:
    - Schema version changes
    - Chunk count changes
    - Missing concepts
    - Quality score drops
    
    Example:
        algl-pdf detect-regressions ./baseline ./current
        algl-pdf detect-regressions ./baseline ./current --tolerance 0.15
    """
    from .regression_detector import detect_regression
    
    typer.echo(f"🔍 Detecting regressions...")
    typer.echo(f"📋 Baseline: {baseline}")
    typer.echo(f"📋 Current: {current}")
    typer.echo(f"📊 Tolerance: {tolerance:.0%}")
    typer.echo("")
    
    try:
        report = detect_regression(
            baseline_dir=baseline,
            current_dir=current,
            chunk_count_tolerance=tolerance,
        )
    except Exception as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1)
    
    # Display results
    typer.echo("=" * 60)
    typer.echo("REGRESSION DETECTION RESULTS")
    typer.echo("=" * 60)
    typer.echo(f"")
    typer.echo(f"📄 Document: {report.document_id}")
    typer.echo(f"")
    typer.echo(f"📊 Summary:")
    typer.echo(f"   Total checks: {len(report.checks)}")
    typer.echo(f"   Passed: {len(report.passed_checks)}")
    typer.echo(f"   Failed: {len(report.failed_checks)}")
    typer.echo(f"")
    
    # Show all checks
    typer.echo(f"🔍 Checks:")
    for check in report.checks:
        icon = "✅" if check.passed else "❌"
        severity = check.severity.upper()
        typer.echo(f"   {icon} [{severity}] {check.check_name}")
        typer.echo(f"      {check.message}")
        if check.baseline_value is not None or check.current_value is not None:
            typer.echo(f"      Baseline: {check.baseline_value} → Current: {check.current_value}")
    
    typer.echo(f"")
    
    # Final status
    if report.has_errors:
        typer.echo(f"❌ ERRORS DETECTED - DO NOT PROCEED")
        exit_code = 1
    elif report.has_warnings:
        typer.echo(f"⚠️  WARNINGS - Review recommended")
        exit_code = 0
    else:
        typer.echo(f"✅ ALL CHECKS PASSED")
        exit_code = 0
    
    # Save report if requested
    if output:
        report.save(output)
        typer.echo(f"")
        typer.echo(f"💾 Report saved: {output}")
    
    if exit_code != 0:
        raise typer.Exit(exit_code)


# =============================================================================
# UNIT LIBRARY COMMANDS (re-exported from cli_unit_library)
# =============================================================================

try:
    from .cli_unit_library import (
        process_command as _process_cmd,
        validate_command as _validate_cmd,
        inspect_command as _inspect_cmd,
        diagnose_command as _diagnose_cmd,
        filter_command as _filter_cmd,
        export_legacy_command as _export_legacy_cmd,
    )
    
    @app.command()
    def process(
        pdf_path: Path = typer.Argument(
            ...,
            exists=True,
            readable=True,
            help="Path to the PDF file to process",
        ),
        output_dir: Path = typer.Option(
            ...,
            "--output-dir", "-o",
            help="Output directory for the unit library (required)",
        ),
        doc_id: str | None = typer.Option(
            None,
            "--doc-id",
            help="Document ID (auto-generated if not provided)",
        ),
        llm_provider: str = typer.Option(
            os.getenv("ALGL_LLM_PROVIDER", "ollama"),
            "--llm-provider",
            help="LLM provider: ollama (default, local), grounded (no LLM), kimi, openai, or claude_local. Falls back to env var ALGL_LLM_PROVIDER.",
        ),
        llm_model: str | None = typer.Option(
            None,
            "--llm-model",
            help="LLM model to use (only used with non-grounded providers)",
        ),
        filter_level: str = typer.Option(
            "production",
            "--filter-level",
            help="Export filter level: strict, production (default), or development",
        ),
        skip_reinforcement: bool = typer.Option(
            False,
            "--skip-reinforcement",
            help="Skip generating reinforcement items",
        ),
        skip_misconceptions: bool = typer.Option(
            False,
            "--skip-misconceptions",
            help="Skip generating misconception units",
        ),
        validate_sql: bool = typer.Option(
            True,
            "--validate-sql/--no-validate-sql",
            help="Validate SQL examples",
        ),
        skip_llm: bool = typer.Option(
            False,
            "--skip-llm",
            help="Skip all LLM-based processing (extraction/repair only, no generation)",
        ),
        min_quality_score: float = typer.Option(
            0.8,
            "--min-quality-score",
            min=0.0,
            max=1.0,
            help="Minimum quality score threshold",
        ),
        export_mode: str = typer.Option(
            "prototype",
            "--export-mode",
            help="Export mode: prototype (allows placeholders, default) or student_ready (strict)",
        ),
        use_ollama_repair: bool = typer.Option(
            True,
            "--use-ollama-repair/--no-ollama-repair",
            help="Use Ollama to repair weak L3 content (requires local Ollama server)",
        ),
        ollama_model: str = typer.Option(
            "qwen3.5:9b-q8_0",
            "--ollama-model",
            help="Ollama model for repair (qwen3.5:9b-q8_0 recommended for RTX 4080, qwen3.5:27b-q4_K_M for better quality)",
        ),
        ollama_repair_threshold: float = typer.Option(
            0.6,
            "--ollama-repair-threshold",
            min=0.0,
            max=1.0,
            help="Quality threshold below which to trigger Ollama repair",
        ),
        claude_local_base_url: str | None = typer.Option(
            None,
            "--claude-base-url",
            help="Base URL for Claude local endpoint (defaults to CLAUDE_LOCAL_BASE_URL env var or http://localhost:8080)",
        ),
        claude_local_model: str | None = typer.Option(
            None,
            "--claude-model",
            help="Claude local model name (defaults to CLAUDE_LOCAL_MODEL env var)",
        ),
        claude_local_api_key: str | None = typer.Option(
            None,
            "--claude-api-key",
            help="API key for Claude local endpoint (defaults to CLAUDE_LOCAL_API_KEY env var)",
        ),
        page_range: str | None = typer.Option(
            None,
            "--page-range",
            help="Process only specific pages (e.g., '1-100' or '50,75,100-120')",
        ),
        chapter_range: str | None = typer.Option(
            None,
            "--chapter-range",
            help="Process only specific chapters (e.g., '1-5' or '3,4,7'). Note: Requires PDF bookmarks/table of contents",
        ),
        resume: bool = typer.Option(
            False,
            "--resume",
            help="Resume from last checkpoint (if available)",
        ),
        cache_extraction: bool = typer.Option(
            True,
            "--cache-extraction/--no-cache-extraction",
            help="Cache and reuse PDF extraction (speeds up re-runs)",
        ),
        allow_offbook_curated: bool = typer.Option(
            False,
            "--allow-offbook-curated",
            help="Allow off-book curated concepts not present in source PDF (opt-in augmentation)",
        ),
        clear_repair_cache: bool = typer.Option(
            False,
            "--clear-repair-cache",
            help="Clear the repair cache before processing",
        ),
    ):
        """Process a PDF into a unit library.
        
        This command extracts content from a PDF, maps concepts, generates
        instructional units at all adaptive stages (L1-L4), and exports
        the grounded instructional unit graph.
        
        The Ollama repair pass automatically improves weak L3 content using
        a local Ollama instance (requires qwen3.5:9b-q8_0 or similar model).
        
        Export Modes:
            prototype (default): Allows placeholder content with warnings.
                Use for development and testing.
            
            student_ready: Strict mode, blocks all placeholder and weak content.
                Use when exporting for actual student consumption.
                Blocks: placeholder practice links, default L2 examples, 
                synthetic-only L3, weak curated content.
        
        Page/Chapter Range:
            Use --page-range to process specific pages (e.g., '1-100' or '50,75,100-120').
            Use --chapter-range to process specific chapters (requires PDF bookmarks).
            Use --resume to continue from a previous interrupted run.
            Use --no-cache-extraction to force re-extraction of the PDF.
        
        Example:
            algl-pdf process ./textbook.pdf --output-dir ./output
            algl-pdf process ./textbook.pdf -o ./output --filter-level production
            algl-pdf process ./textbook.pdf -o ./output --export-mode student_ready
            algl-pdf process ./textbook.pdf -o ./output --skip-reinforcement
            algl-pdf process ./textbook.pdf -o ./output --no-ollama-repair
            algl-pdf process ./textbook.pdf -o ./output --page-range 1-50
            algl-pdf process ./textbook.pdf -o ./output --chapter-range 1-3
            algl-pdf process ./textbook.pdf -o ./output --resume
        """
        _process_cmd(
            pdf_path=pdf_path,
            output_dir=output_dir,
            doc_id=doc_id,
            llm_provider=llm_provider,
            llm_model=llm_model,
            filter_level=filter_level,
            skip_reinforcement=skip_reinforcement,
            skip_misconceptions=skip_misconceptions,
            validate_sql=validate_sql,
            skip_llm=skip_llm,
            min_quality_score=min_quality_score,
            export_mode=export_mode,
            use_ollama_repair=use_ollama_repair,
            ollama_model=ollama_model,
            ollama_repair_threshold=ollama_repair_threshold,
            claude_local_base_url=claude_local_base_url,
            claude_local_model=claude_local_model,
            claude_local_api_key=claude_local_api_key,
            page_range=page_range,
            chapter_range=chapter_range,
            resume=resume,
            cache_extraction=cache_extraction,
            allow_offbook_curated=allow_offbook_curated,
            clear_repair_cache=clear_repair_cache,
        )

    @app.command()
    def validate(
        library_dir: Path = typer.Argument(
            ...,
            exists=True,
            file_okay=False,
            dir_okay=True,
            help="Path to unit library directory",
        ),
        detailed: bool = typer.Option(
            False,
            "--detailed",
            help="Show detailed validation report",
        ),
        use_generated_report: bool = typer.Option(
            False,
            "--use-generated-report",
            help="Use the quality report generated during export (if available)",
        ),
        recompute: bool = typer.Option(
            False,
            "--recompute",
            help="Force recompute validation instead of using cached report",
        ),
    ):
        """Validate an existing unit library.
        
        Runs all quality gates on the unit library and displays a quality report.
        
        Example:
            algl-pdf validate ./output/unit-library/
            algl-pdf validate ./output/unit-library/ --detailed
        """
        _validate_cmd(
            library_dir=library_dir,
            detailed=detailed,
            use_generated_report=use_generated_report,
            recompute=recompute,
        )

    @app.command()
    def inspect(
        library_dir: Path = typer.Argument(
            ...,
            exists=True,
            file_okay=False,
            dir_okay=True,
            help="Path to unit library directory",
        ),
        concept: str = typer.Option(
            ...,
            "--concept", "-c",
            help="Concept ID to inspect",
        ),
        show_sql: bool = typer.Option(
            True,
            "--show-sql/--no-show-sql",
            help="Show SQL examples with syntax highlighting",
        ),
    ):
        """Inspect units for a specific concept.
        
        Display all variants (L1-L4) for a concept with source evidence.
        
        Example:
            algl-pdf inspect ./output/unit-library/ --concept select-basic
            algl-pdf inspect ./output/unit-library/ -c join-operations --no-show-sql
        """
        _inspect_cmd(library_dir=library_dir, concept=concept, show_sql=show_sql)

    @app.command(name="diagnose")
    def diagnose(
        library_dir: Path = typer.Argument(
            ...,
            exists=True,
            file_okay=False,
            dir_okay=True,
            help="Path to unit library directory",
        ),
        detailed: bool = typer.Option(
            False,
            "--detailed",
            help="Show detailed diagnostic report",
        ),
    ):
        """Diagnose content gaps and quality issues in a unit library.
        
        Analyzes the library and reports:
        - L3 coverage gaps (concepts missing explanations)
        - L2 units using default examples
        - Unresolved practice links
        - Heading-like content in why_it_matters
        - Missing evidence spans
        
        Example:
            algl-pdf diagnose ./output/unit-library/
            algl-pdf diagnose ./output/unit-library/ --detailed
        """
        _diagnose_cmd(library_dir=library_dir, detailed=detailed)

    @app.command()
    def filter(
        library_dir: Path = typer.Argument(
            ...,
            exists=True,
            file_okay=False,
            dir_okay=True,
            help="Path to unit library directory",
        ),
        level: str = typer.Option(
            "strict",
            "--level",
            help="Export filter level: strict, production, or development",
        ),
        output_dir: Path | None = typer.Option(
            None,
            "--output-dir", "-o",
            help="Output directory for filtered library (default: in-place)",
        ),
    ):
        """Re-run export filters on existing library.
        
        Creates a filtered subset of the unit library based on the specified level.
        
        Example:
            algl-pdf filter ./output/unit-library/ --level strict
            algl-pdf filter ./output/unit-library/ -o ./output/filtered/ --level production
        """
        _filter_cmd(library_dir=library_dir, level=level, output_dir=output_dir)

    @app.command(name="export-legacy")
    def export_legacy(
        concept_map_path: Path = typer.Argument(
            ...,
            exists=True,
            readable=True,
            help="Path to old concept-map.json file",
        ),
        output_dir: Path = typer.Option(
            ...,
            "--output-dir", "-o",
            help="Output directory for new format (required)",
        ),
        filter_level: str = typer.Option(
            "strict",
            "--filter-level",
            help="Export filter level: strict, production, or development",
        ),
    ):
        """Convert old concept-map.json to new unit library format.
        
        Transforms the legacy concept map structure into the new grounded
        instructional unit graph format.
        
        Example:
            algl-pdf export-legacy ./old-output/concept-map.json --output-dir ./new-output/
            algl-pdf export-legacy ./old/concept-map.json -o ./new/ --filter-level strict
        """
        _export_legacy_cmd(
            concept_map_path=concept_map_path,
            output_dir=output_dir,
            filter_level=filter_level,
        )


except ImportError:
    pass  # Unit library commands not available


# Cache management command (always available)
@app.command(name="cache")
def cache_command(
    action: str = typer.Argument(
        "stats",
        help="Action: stats, clear, or show-path",
    ),
):
    """
    Manage the Ollama repair cache.
    
    View cache statistics, clear cached repairs, or show cache directory.
    
    Example:
        algl-pdf cache stats     # Show cache statistics
        algl-pdf cache clear     # Clear all cached repairs
        algl-pdf cache show-path # Show cache directory path
    """
    try:
        from .ollama_repair import RepairCache
        
        cache = RepairCache()
        
        if action == "clear":
            count = cache.clear_cache()
            typer.echo(f"✅ Cleared {count} cached repairs")
        elif action == "show-path":
            typer.echo(f"Cache directory: {cache.cache_dir}")
        elif action == "stats":
            stats = cache.get_cache_stats()
            typer.echo("📊 Repair Cache Statistics:")
            typer.echo(f"  Cache directory: {stats['cache_dir']}")
            typer.echo(f"  Cached files: {stats['cached_files']}")
            typer.echo(f"  Total size: {stats['total_size_bytes']:,} bytes")
            if stats['hits'] + stats['misses'] > 0:
                typer.echo(f"  Cache hits: {stats['hits']}")
                typer.echo(f"  Cache misses: {stats['misses']}")
                typer.echo(f"  Hit rate: {stats['hit_rate']:.1%}")
        else:
            typer.echo(f"❌ Unknown action: {action}")
            typer.echo("Valid actions: stats, clear, show-path")
            raise typer.Exit(1)
            
    except ImportError:
        typer.echo("❌ Error: RepairCache not available")
        raise typer.Exit(1)


# Replay/evidence command
@app.command()
def replay(
    trace_input: Path = typer.Argument(
        ...,
        exists=True,
        help="Path to trace JSON file or directory of traces",
    ),
    output_dir: Path = typer.Option(
        ...,
        "--output-dir", "-o",
        help="Output directory for replay artifacts",
    ),
    policy: list[str] = typer.Option(
        None,
        "--policy",
        help="Policy ID(s) to run (default: all 3 policies)",
    ),
    flags_file: Path | None = typer.Option(
        None,
        "--flags",
        help="JSON file with experiment flags",
    ),
    synthetic_fixture: bool = typer.Option(
        False,
        "--synthetic-fixture",
        help="Generate and use synthetic fixture trace",
    ),
    run_id: str | None = typer.Option(
        None,
        "--run-id",
        help="Custom run identifier",
    ),
):
    """
    Replay learner trace(s) under formal policies for comparison.

    This command replays traces under multiple escalation policies and
    produces research-ready artifacts for policy comparison.

    Artifacts produced:
    - replay_summary.json / replay_summary.csv
    - per_learner_metrics.csv
    - policy_comparison.csv

    Available policies:
    - fast_escalator: Aggressive early escalation
    - slow_escalator: Conservative, favors independence
    - adaptive_escalator: Context-aware strain-based

    Example:
        algl replay traces/ --output-dir outputs/day4
        algl replay trace.json -o out --policy fast_escalator --policy slow_escalator
        algl replay traces/ -o out --synthetic-fixture
    """
    from .replay import run_replay
    from .experiment_flags import ExperimentFlags, load_flags
    from .trace_schema import make_synthetic_trace
    import json

    # Load or create flags
    experiment_flags = None
    if flags_file:
        try:
            experiment_flags = load_flags(flags_file)
            typer.echo(f"✅ Loaded flags from {flags_file}")
        except Exception as e:
            typer.echo(f"⚠️ Could not load flags: {e}")

    # Generate synthetic fixture if requested
    if synthetic_fixture:
        synthetic_dir = output_dir / "synthetic_traces"
        synthetic_dir.mkdir(parents=True, exist_ok=True)

        # Create a few synthetic traces
        synthetic_traces = [
            make_synthetic_trace("struggling_001", "struggling_with_joins", num_problems=3, error_rate=0.7),
            make_synthetic_trace("fast_001", "fast_learner", num_problems=3, error_rate=0.2),
            make_synthetic_trace("average_001", "average_learner", num_problems=3, error_rate=0.5),
        ]

        for trace in synthetic_traces:
            trace_path = synthetic_dir / f"{trace.trace_id}.json"
            trace.save(trace_path)
            typer.echo(f"📝 Created synthetic trace: {trace_path}")

        # Update input to use synthetic traces
        trace_input = synthetic_dir

    # Run replay
    try:
        typer.echo(f"🔄 Replaying traces from {trace_input}...")
        typer.echo(f"📁 Output directory: {output_dir}")

        artifacts = run_replay(
            trace_input=trace_input,
            output_dir=output_dir,
            flags=experiment_flags,
            policy_filter=policy if policy else None,
            run_id=run_id,
        )

        typer.echo("\n✅ Replay complete! Artifacts generated:")
        for name, path in artifacts.items():
            typer.echo(f"  📄 {name}: {path}")

        # Print summary
        summary_path = artifacts.get("replay_summary_json")
        if summary_path and summary_path.exists():
            with open(summary_path, encoding="utf-8") as f:
                summary = json.load(f)
            typer.echo(f"\n📊 Summary:")
            typer.echo(f"  Total traces: {summary.get('total_traces', 0)}")
            typer.echo(f"  Policies compared: {summary.get('total_policies', 0)}")
            for policy_id, metrics in summary.get("policy_metrics", {}).items():
                typer.echo(f"\n  Policy: {policy_id}")
                typer.echo(f"    Avg HDI: {metrics.get('avg_hdi', 0):.3f}")
                typer.echo(f"    Avg CSI: {metrics.get('avg_csi', 0):.3f}")
                typer.echo(f"    Avg APS: {metrics.get('avg_aps', 0):.3f}")

    except ValueError as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Unexpected error: {e}", err=True)
        raise typer.Exit(1)


# =============================================================================
# HINTWISE COMMAND
# =============================================================================


@app.command(name="hintwise")
def hintwise_command(
    concept_units_path: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="Path to concept_units.json (or any JSON with concept/unit dicts)",
    ),
    concept_id: str = typer.Option(
        ...,
        "--concept", "-c",
        help="Concept ID to build the payload for",
    ),
    learner_id: str | None = typer.Option(
        None,
        "--learner-id",
        help="Learner identifier (optional)",
    ),
    problem_id: str | None = typer.Option(
        None,
        "--problem-id",
        help="Problem identifier (optional)",
    ),
    escalation_level: str = typer.Option(
        "L1",
        "--escalation-level",
        help="Escalation level: L1 (default), L2, L3, or L4",
    ),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir", "-o",
        help="Directory to save hintwise-results.jsonl (skipped if omitted)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Build payload and show eligibility, but do not call the endpoint",
    ),
):
    """
    Build a HintWise payload from an existing artifact and optionally call the live endpoint.

    Reads concept_units.json, finds the specified concept, builds a HintwisePayload,
    and calls the configured HintWise HTTP endpoint (HINTWISE_BASE_URL env var).
    When HINTWISE_BASE_URL is not set the command runs in offline mode (payload
    inspection only, no network call is made).

    Results are appended to hintwise-results.jsonl in --output-dir (if specified).

    Environment variables
    ---------------------
    HINTWISE_BASE_URL    Base URL of the HintWise service (optional)
    HINTWISE_ENDPOINT    Endpoint path (default: /api/hint)
    HINTWISE_API_KEY     Bearer token for the endpoint (optional)
    HINTWISE_TIMEOUT     Request timeout in seconds (default: 10)

    Examples
    --------
    # Inspect payload only (offline, no HTTP call)
    algl-pdf hintwise ./output/concept_units.json --concept select-basic --dry-run

    # Call live endpoint and save result
    algl-pdf hintwise ./output/concept_units.json -c join-operations \\
        --learner-id abc --problem-id p01 --output-dir ./outputs/hints/
    """
    import json as _json

    from .hintwise_adapter import make_hintwise_payload
    from .hintwise_client import HintwiseClient
    from .hintwise_service import HintwiseService

    # --- load units file ---
    try:
        raw = _json.loads(concept_units_path.read_text(encoding="utf-8"))
    except Exception as exc:
        typer.echo(f"Error reading {concept_units_path}: {exc}", err=True)
        raise typer.Exit(1)

    units: list[dict] = raw if isinstance(raw, list) else raw.get("units", [])
    unit_data = next((u for u in units if u.get("concept_id") == concept_id), None)
    if unit_data is None:
        typer.echo(f"Concept '{concept_id}' not found in {concept_units_path}.", err=True)
        available = sorted({u.get("concept_id", "") for u in units})[:10]
        if available:
            typer.echo(f"Available (first 10): {', '.join(available)}", err=True)
        raise typer.Exit(1)

    learner_ctx = {
        "escalation_level": escalation_level,
        "learner_id": learner_id,
        "problem_id": problem_id,
    }
    payload = make_hintwise_payload(unit_data, learner_context=learner_ctx)

    # --- show payload summary ---
    typer.echo(f"Concept: {payload.concept_context.concept_id}")
    typer.echo(f"Unit ID: {payload.concept_context.unit_id or '(none)'}")
    typer.echo(f"Escalation: {payload.learner_context.escalation_level}")
    typer.echo(f"Supports HintWise: {payload.supports_hintwise}")
    elig = payload.get_hint_eligibility()
    typer.echo(f"Eligibility: eligible_for_hints={elig['eligible_for_hints']}")

    if dry_run:
        typer.echo("\n[dry-run] Payload built. No HTTP call made.")
        typer.echo(_json.dumps(payload.to_dict(), indent=2))
        return

    # --- call endpoint ---
    client = HintwiseClient.from_env()
    if not client.is_configured:
        typer.echo(
            "\n[offline] HINTWISE_BASE_URL is not set — no HTTP call made.\n"
            "Set HINTWISE_BASE_URL to enable live endpoint calls."
        )
        return

    typer.echo(f"\nCalling {client._build_url()} ...")

    out_path: Path | None = None
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / "hintwise-results.jsonl"

    svc = HintwiseService(client=client, output_path=out_path)
    result = svc.request(unit_data, learner_context=learner_ctx)

    if result.succeeded():
        typer.echo(f"Status: {result.status_code} OK")
        if result.hint_id:
            typer.echo(f"Hint ID: {result.hint_id}")
        if result.hint_content:
            typer.echo(f"Hint: {result.hint_content}")
    elif result.error:
        typer.echo(f"Error: {result.error}", err=True)
        raise typer.Exit(1)
    else:
        typer.echo(f"Status: {result.status_code}")

    if out_path:
        typer.echo(f"Result saved to: {out_path}")
