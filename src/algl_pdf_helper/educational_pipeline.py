"""
End-to-end pipeline: PDF → Educational Notes → SQL-Adapt Format

This module provides a complete solution that:
1. Extracts PDF content using Marker (high quality)
2. Generates educational notes using LLM
3. Outputs SQL-Adapt compatible format
4. Handles all errors gracefully - no exceptions
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Try to import marker, but provide fallback
try:
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.output import text_from_rendered
    MARKER_AVAILABLE = True
except ImportError:
    MARKER_AVAILABLE = False

# Try to import OpenAI for LLM generation
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from .models import ConceptInfo, ConceptManifest


class LLMProvider:
    """Supported LLM providers."""
    OPENAI = "openai"
    KIMI = "kimi"  # Moonshot AI


class EducationalNoteGenerator:
    """
    Generates student-ready educational notes from PDF content.
    
    This class handles the complete pipeline:
    PDF extraction → Content structuring → LLM enhancement → SQL-Adapt format
    
    Supports multiple LLM providers:
    - OpenAI (GPT-4, GPT-4o-mini)
    - Kimi/Moonshot AI (Kimi Chat 8K/32K/128K)
    """
    
    def __init__(
        self,
        openai_api_key: str | None = None,
        kimi_api_key: str | None = None,
        llm_provider: str = LLMProvider.OPENAI,
        use_marker: bool = True,
    ):
        self.use_marker = use_marker and MARKER_AVAILABLE
        self.llm_provider = llm_provider.lower()
        
        # Initialize OpenAI
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.openai_available = OPENAI_AVAILABLE and bool(self.openai_api_key)
        self.openai_client = None
        if self.openai_available:
            self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
        
        # Initialize Kimi (Moonshot AI)
        self.kimi_api_key = kimi_api_key or os.getenv("KIMI_API_KEY") or os.getenv("MOONSHOT_API_KEY")
        self.kimi_available = bool(self.kimi_api_key)
        self.kimi_client = None
        if self.kimi_available:
            # Kimi uses OpenAI-compatible API
            self.kimi_client = openai.OpenAI(
                api_key=self.kimi_api_key,
                base_url="https://api.moonshot.cn/v1",
            )
        
        # Set active client based on provider
        self.llm_available = False
        self.active_client = None
        self.active_model = None
        
        if self.llm_provider == LLMProvider.KIMI and self.kimi_available:
            self.llm_available = True
            self.active_client = self.kimi_client
            self.active_model = "moonshot-v1-8k"  # Default: 8K context, cheapest
        elif self.openai_available:
            self.llm_available = True
            self.active_client = self.openai_client
            self.active_model = "gpt-4o-mini"  # Default: cost-effective
            self.llm_provider = LLMProvider.OPENAI
        
        # Cost tracking (per 1K tokens in RMB)
        self.cost_config = {
            LLMProvider.OPENAI: {
                "gpt-4o-mini": {"input": 0.11, "output": 0.44},  # ~$0.015/$0.06
                "gpt-4o": {"input": 2.75, "output": 11.0},  # ~$0.375/$1.50
            },
            LLMProvider.KIMI: {
                "moonshot-v1-8k": {"input": 0.012, "output": 0.012},
                "moonshot-v1-32k": {"input": 0.024, "output": 0.024},
                "moonshot-v1-128k": {"input": 0.12, "output": 0.12},
            },
        }
    
    def process_pdf(
        self,
        pdf_path: Path,
        concepts_config: dict[str, Any] | None = None,
        output_dir: Path | None = None,
        progress_callback: callable | None = None,
    ) -> dict[str, Any]:
        """
        Process PDF into educational notes and SQL-Adapt format.
        
        Args:
            pdf_path: Path to PDF file
            concepts_config: Optional concept mapping configuration
            output_dir: Where to save outputs
            progress_callback: Optional callback function(step, current, total, message)
            
        Returns:
            Dictionary with paths to generated files and metadata
            Never raises exceptions - returns error info in result
        """
        result = {
            "success": False,
            "pdf_path": str(pdf_path),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "outputs": {},
            "errors": [],
            "stats": {},
        }
        
        def _progress(step: str, current: int, total: int, message: str = ""):
            if progress_callback:
                progress_callback(step, current, total, message)
        
        try:
            # Step 1: Extract PDF content
            _progress("extract", 0, 100, "Starting PDF extraction...")
            extraction_result = self._extract_pdf_content(pdf_path, _progress)
            if not extraction_result["success"]:
                result["errors"].extend(extraction_result["errors"])
                return result
            _progress("extract", 100, 100, f"Extracted {extraction_result.get('page_count', 0)} pages")
            
            # Step 2: Structure content by sections/concepts
            _progress("structure", 0, 100, "Structuring content...")
            structured_content = self._structure_content(
                extraction_result["content"],
                concepts_config,
            )
            num_concepts = len(structured_content.get("concepts", {}))
            _progress("structure", 100, 100, f"Found {num_concepts} concepts")
            
            # Step 3: Generate educational notes
            _progress("enhance", 0, 100, f"Generating educational notes for {num_concepts} concepts...")
            educational_notes = self._generate_educational_notes(
                structured_content, 
                progress_callback=_progress
            )
            _progress("enhance", 100, 100, "Educational notes complete")
            
            # Step 4: Create SQL-Adapt compatible output
            _progress("format", 50, 100, "Creating SQL-Adapt format...")
            sqladapt_output = self._create_sqladapt_format(
                educational_notes,
                pdf_path,
            )
            _progress("format", 100, 100, "SQL-Adapt format ready")
            
            # Step 5: Save outputs
            _progress("save", 0, 100, "Saving output files...")
            if output_dir:
                output_paths = self._save_outputs(
                    output_dir,
                    extraction_result,
                    educational_notes,
                    sqladapt_output,
                )
                result["outputs"] = output_paths
            _progress("save", 100, 100, "All files saved")
            
            result["success"] = True
            result["stats"] = {
                "pages_extracted": extraction_result.get("page_count", 0),
                "concepts_generated": len(educational_notes.get("concepts", {})),
                "extraction_method": extraction_result.get("method", "unknown"),
                "llm_enhanced": self.llm_available,
            }
            
        except Exception as e:
            result["errors"].append(f"Processing error: {str(e)}")
            # Still return partial results if available
            if "extraction_result" in locals():
                result["partial_extraction"] = extraction_result
        
        return result
    
    def _extract_pdf_content(
        self, 
        pdf_path: Path,
        progress_callback: callable | None = None,
    ) -> dict[str, Any]:
        """Extract content from PDF using best available method."""
        result = {
            "success": False,
            "content": {},
            "errors": [],
            "method": "none",
        }
        
        def _update_progress(percent: int, message: str = ""):
            if progress_callback:
                progress_callback("extract", percent, 100, message)
        
        # Try Marker first (best quality)
        if self.use_marker:
            try:
                _update_progress(10, "Loading Marker models...")
                converter = PdfConverter(artifact_dict=create_model_dict())
                
                _update_progress(30, "Extracting text and layout...")
                rendered = converter(str(pdf_path))
                
                _update_progress(70, "Processing extracted content...")
                markdown, _, images = text_from_rendered(rendered)
                
                # Parse into pages
                _update_progress(85, "Parsing pages...")
                pages = self._parse_markdown_pages(markdown, rendered)
                
                result["content"] = {
                    "markdown": markdown,
                    "pages": pages,
                    "images_count": len(images),
                }
                result["page_count"] = len(pages)
                result["method"] = "marker"
                result["success"] = True
                return result
                
            except Exception as e:
                result["errors"].append(f"Marker extraction failed: {e}")
        
        # Fallback to PyMuPDF
        try:
            import fitz
            doc = fitz.open(str(pdf_path))
            pages = []
            
            for page_num, page in enumerate(doc, 1):
                text = page.get_text()
                pages.append({
                    "page_number": page_num,
                    "text": text,
                    "sections": self._extract_sections_from_text(text),
                })
            
            doc.close()
            
            result["content"] = {
                "markdown": "\n\n".join(p["text"] for p in pages),
                "pages": pages,
            }
            result["page_count"] = len(pages)
            result["method"] = "pymupdf"
            result["success"] = True
            
        except Exception as e:
            result["errors"].append(f"PyMuPDF extraction failed: {e}")
        
        return result
    
    def _parse_markdown_pages(self, markdown: str, rendered: Any) -> list[dict]:
        """Parse Marker markdown into page objects."""
        pages = []
        
        # Split by page markers or headers
        sections = re.split(r'\n(?=#+\s)', markdown)
        current_page = 1
        current_content = []
        
        for section in sections:
            if not section.strip():
                continue
            
            # Detect page breaks ( Marker may include page markers)
            if "<!-- Page " in section or "\f" in section:
                if current_content:
                    pages.append({
                        "page_number": current_page,
                        "text": "\n\n".join(current_content),
                        "sections": self._extract_sections_from_text(
                            "\n\n".join(current_content)
                        ),
                    })
                    current_page += 1
                    current_content = []
            
            current_content.append(section)
        
        # Don't forget last page
        if current_content:
            pages.append({
                "page_number": current_page,
                "text": "\n\n".join(current_content),
                "sections": self._extract_sections_from_text(
                    "\n\n".join(current_content)
                ),
            })
        
        # If no pages detected, treat entire markdown as one page
        if not pages:
            pages = [{
                "page_number": 1,
                "text": markdown,
                "sections": self._extract_sections_from_text(markdown),
            }]
        
        return pages
    
    def _extract_sections_from_text(self, text: str) -> list[dict]:
        """Extract sections from text based on headers."""
        sections = []
        
        # Match headers (## or ###)
        header_pattern = r'(?:^|\n)(#{1,3}\s+.+?)(?:\n|$)'
        matches = list(re.finditer(header_pattern, text))
        
        for i, match in enumerate(matches):
            title = match.group(1).strip('# ')
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()
            
            sections.append({
                "title": title,
                "content": content,
                "level": match.group(1).count('#'),
            })
        
        # If no sections found, create one from entire text
        if not sections and text.strip():
            sections = [{
                "title": "Content",
                "content": text,
                "level": 1,
            }]
        
        return sections
    
    def _structure_content(
        self,
        extraction_result: dict,
        concepts_config: dict | None,
    ) -> dict[str, Any]:
        """Structure extracted content by concepts/topics."""
        pages = extraction_result.get("pages", [])
        
        # If concepts config provided, map content to concepts
        if concepts_config and "concepts" in concepts_config:
            return self._map_to_concepts(pages, concepts_config["concepts"])
        
        # Otherwise, auto-detect topics from headers
        return self._auto_detect_topics(pages)
    
    def _map_to_concepts(
        self,
        pages: list[dict],
        concepts: dict[str, Any],
    ) -> dict[str, Any]:
        """Map page content to configured concepts."""
        structured = {"concepts": {}}
        
        for concept_id, concept_info in concepts.items():
            page_refs = concept_info.get("pages", [])
            sections = concept_info.get("sections", {})
            
            concept_content = {
                "id": concept_id,
                "title": concept_info.get("title", concept_id),
                "definition": concept_info.get("definition", ""),
                "difficulty": concept_info.get("difficulty", "intermediate"),
                "page_references": page_refs,
                "sections": {},
            }
            
            # Extract content for each section
            for section_name, section_pages in sections.items():
                section_text = []
                for page_num in section_pages:
                    for page in pages:
                        if page["page_number"] == page_num:
                            section_text.append(page["text"])
                
                concept_content["sections"][section_name] = {
                    "text": "\n\n".join(section_text),
                    "pages": section_pages,
                }
            
            structured["concepts"][concept_id] = concept_content
        
        return structured
    
    def _auto_detect_topics(self, pages: list[dict]) -> dict[str, Any]:
        """Automatically detect topics from page headers."""
        structured = {"concepts": {}}
        
        for page in pages:
            for section in page.get("sections", []):
                concept_id = self._slugify(section["title"])
                
                if concept_id not in structured["concepts"]:
                    structured["concepts"][concept_id] = {
                        "id": concept_id,
                        "title": section["title"],
                        "definition": "",
                        "difficulty": "intermediate",
                        "page_references": [page["page_number"]],
                        "sections": {
                            "content": {
                                "text": section["content"],
                                "pages": [page["page_number"]],
                            }
                        },
                    }
                else:
                    # Append to existing concept
                    existing = structured["concepts"][concept_id]
                    if page["page_number"] not in existing["page_references"]:
                        existing["page_references"].append(page["page_number"])
                    
                    existing["sections"]["content"]["text"] += "\n\n" + section["content"]
        
        return structured
    
    def _generate_educational_notes(
        self, 
        structured_content: dict,
        progress_callback: callable | None = None,
    ) -> dict[str, Any]:
        """Generate educational notes from structured content."""
        notes = {"concepts": {}}
        
        concepts = list(structured_content.get("concepts", {}).items())
        total = len(concepts)
        
        for idx, (concept_id, concept_data) in enumerate(concepts, 1):
            # Update progress
            percent = int((idx / total) * 100) if total > 0 else 100
            if progress_callback:
                progress_callback(
                    "enhance", 
                    percent, 
                    100, 
                    f"Processing concept {idx}/{total}: {concept_data.get('title', concept_id)}"
                )
            
            # Get raw text for this concept
            raw_text = concept_data.get("sections", {}).get("content", {}).get("text", "")
            if not raw_text:
                # Try other sections
                for section in concept_data.get("sections", {}).values():
                    if isinstance(section, dict) and "text" in section:
                        raw_text += section["text"] + "\n\n"
            
            # Generate educational content
            if self.llm_available and len(raw_text) > 100:
                educational_content = self._llm_enhance_concept(
                    concept_data["title"],
                    concept_data.get("definition", ""),
                    raw_text,
                )
            else:
                # Fallback: create basic educational content without LLM
                educational_content = self._create_basic_notes(
                    concept_data["title"],
                    raw_text,
                )
            
            notes["concepts"][concept_id] = {
                **concept_data,
                **educational_content,
            }
        
        return notes
    
    def _llm_enhance_concept(
        self,
        title: str,
        definition: str,
        raw_text: str,
    ) -> dict[str, Any]:
        """Use LLM to transform raw text into educational notes."""
        try:
            # Truncate if too long
            max_chars = 6000
            text_to_process = raw_text[:max_chars]
            
            prompt = f"""Transform this textbook content into educational notes for students.

TOPIC: {title}
DEFINITION: {definition}

TEXT:
{text_to_process}

Create JSON output with:
1. A clear, simple definition (2-3 sentences)
2. Detailed explanation (explain like I'm a beginner)
3. Key learning points (3-5 bullet points)
4. Code examples if applicable (with SQL or pseudocode)
5. Common mistakes students make
6. A practice question with solution

Respond ONLY with valid JSON in this format:
{{
  "definition": "...",
  "explanation": "...",
  "key_points": ["...", "..."],
  "examples": [{{"title": "...", "code": "...", "explanation": "..."}}],
  "common_mistakes": [{{"mistake": "...", "correction": "..."}}],
  "practice": {{"question": "...", "solution": "..."}}
}}
"""
            
            # Use active client (OpenAI or Kimi)
            response = self.active_client.chat.completions.create(
                model=self.active_model,
                messages=[
                    {"role": "system", "content": "You are an expert educator who creates clear, engaging learning materials."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
            )
            
            content = response.choices[0].message.content
            
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                parsed = json.loads(json_match.group())
                return {
                    "educational_notes": parsed,
                    "llm_enhanced": True,
                    "raw_text_preview": raw_text[:500],
                }
            else:
                raise ValueError("No JSON found in LLM response")
                
        except Exception as e:
            # Fallback to basic notes
            return self._create_basic_notes(title, raw_text, error=str(e))
    
    def _create_basic_notes(
        self,
        title: str,
        raw_text: str,
        error: str | None = None,
    ) -> dict[str, Any]:
        """Create basic educational notes without LLM."""
        # Extract code examples using regex
        code_examples = []
        code_pattern = r'(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)[\s\S]{10,300}?;'
        matches = re.findall(code_pattern, raw_text, re.IGNORECASE)
        for i, match in enumerate(matches[:3], 1):
            code_examples.append({
                "title": f"Example {i}",
                "code": match.strip(),
                "explanation": "SQL example from textbook",
            })
        
        # Create summary from first few sentences
        sentences = re.split(r'(?<=[.!?])\s+', raw_text)
        summary = " ".join(sentences[:3]) if len(sentences) >= 3 else raw_text[:300]
        
        notes = {
            "educational_notes": {
                "definition": f"{title}: {summary[:200]}...",
                "explanation": raw_text[:1000],
                "key_points": ["Key concept from textbook"],
                "examples": code_examples if code_examples else [],
                "common_mistakes": [],
                "practice": {},
            },
            "llm_enhanced": False,
            "raw_text_preview": raw_text[:500],
        }
        
        if error:
            notes["llm_error"] = error
        
        return notes
    
    def _create_sqladapt_format(
        self,
        educational_notes: dict,
        pdf_path: Path,
    ) -> dict[str, Any]:
        """Create SQL-Adapt compatible output format."""
        doc_id = self._slugify(pdf_path.stem)
        
        sqladapt = {
            "schemaVersion": "educational-concept-v1",
            "sourceDocId": doc_id,
            "sourceFile": str(pdf_path),
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "concepts": {},
        }
        
        for concept_id, concept_data in educational_notes.get("concepts", {}).items():
            notes = concept_data.get("educational_notes", {})
            
            # Create chunk IDs for sections
            chunk_ids = {}
            for section_name, section_data in concept_data.get("sections", {}).items():
                if isinstance(section_data, dict):
                    chunk_ids[section_name] = [
                        f"{doc_id}:p{p}:c1" 
                        for p in section_data.get("pages", [])
                    ]
            
            sqladapt["concepts"][concept_id] = {
                "id": concept_id,
                "title": concept_data.get("title", concept_id),
                "definition": notes.get("definition", concept_data.get("definition", "")),
                "difficulty": concept_data.get("difficulty", "intermediate"),
                "estimatedReadTime": self._estimate_read_time(notes),
                "pageReferences": concept_data.get("page_references", []),
                "sections": {
                    "definition": {
                        "chunkIds": chunk_ids.get("definition", chunk_ids.get("content", [])),
                        "text": notes.get("definition", ""),
                    },
                    "explanation": {
                        "chunkIds": chunk_ids.get("explanation", chunk_ids.get("content", [])),
                        "text": notes.get("explanation", ""),
                    },
                    "examples": {
                        "chunkIds": chunk_ids.get("examples", []),
                        "items": notes.get("examples", []),
                    },
                    "commonMistakes": {
                        "chunkIds": chunk_ids.get("commonMistakes", []),
                        "items": notes.get("common_mistakes", []),
                    },
                    "practice": {
                        "chunkIds": chunk_ids.get("practice", []),
                        "questions": notes.get("practice", {}),
                    },
                },
                "relatedConcepts": concept_data.get("related_concepts", []),
                "tags": concept_data.get("tags", []),
            }
        
        return sqladapt
    
    def _save_outputs(
        self,
        output_dir: Path,
        extraction_result: dict,
        educational_notes: dict,
        sqladapt_output: dict,
    ) -> dict[str, str]:
        """Save all outputs to disk."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        doc_id = sqladapt_output.get("sourceDocId", "unknown")
        
        paths = {}
        
        # Save extraction result
        extract_path = output_dir / f"{doc_id}-extraction.json"
        with open(extract_path, "w", encoding="utf-8") as f:
            json.dump(extraction_result, f, indent=2, ensure_ascii=False)
        paths["extraction"] = str(extract_path)
        
        # Save educational notes
        notes_path = output_dir / f"{doc_id}-educational-notes.json"
        with open(notes_path, "w", encoding="utf-8") as f:
            json.dump(educational_notes, f, indent=2, ensure_ascii=False)
        paths["educational_notes"] = str(notes_path)
        
        # Save SQL-Adapt format
        sqladapt_path = output_dir / f"{doc_id}-sqladapt.json"
        with open(sqladapt_path, "w", encoding="utf-8") as f:
            json.dump(sqladapt_output, f, indent=2, ensure_ascii=False)
        paths["sqladapt"] = str(sqladapt_path)
        
        # Generate markdown version for humans
        md_path = output_dir / f"{doc_id}-study-guide.md"
        self._generate_study_guide(md_path, educational_notes)
        paths["study_guide"] = str(md_path)
        
        return paths
    
    def _generate_study_guide(
        self,
        output_path: Path,
        educational_notes: dict,
    ) -> None:
        """Generate human-readable study guide."""
        lines = ["# Study Guide\n", f"Generated: {datetime.now().isoformat()}\n\n"]
        
        for concept_id, concept_data in educational_notes.get("concepts", {}).items():
            notes = concept_data.get("educational_notes", {})
            
            lines.append(f"## {concept_data.get('title', concept_id)}\n\n")
            
            if notes.get("definition"):
                lines.append(f"**Definition:** {notes['definition']}\n\n")
            
            if notes.get("explanation"):
                lines.append(f"### Explanation\n{notes['explanation']}\n\n")
            
            if notes.get("key_points"):
                lines.append("### Key Points\n")
                for point in notes["key_points"]:
                    lines.append(f"- {point}\n")
                lines.append("\n")
            
            if notes.get("examples"):
                lines.append("### Examples\n")
                for ex in notes["examples"]:
                    lines.append(f"**{ex.get('title', 'Example')}:**\n")
                    if "code" in ex:
                        lines.append(f"```sql\n{ex['code']}\n```\n")
                    if "explanation" in ex:
                        lines.append(f"{ex['explanation']}\n")
                    lines.append("\n")
            
            if notes.get("common_mistakes"):
                lines.append("### Common Mistakes\n")
                for mistake in notes["common_mistakes"]:
                    lines.append(f"**❌ {mistake.get('mistake', '')}**\n")
                    lines.append(f"**✅ {mistake.get('correction', '')}**\n\n")
            
            if notes.get("practice"):
                practice = notes["practice"]
                if practice.get("question"):
                    lines.append("### Practice Question\n")
                    lines.append(f"**Q:** {practice['question']}\n\n")
                    if practice.get("solution"):
                        lines.append(f"**Solution:** {practice['solution']}\n\n")
            
            lines.append("---\n\n")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    
    def _slugify(self, text: str) -> str:
        """Convert text to URL-safe slug."""
        text = text.lower().strip()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text[:50]
    
    def _estimate_read_time(self, notes: dict) -> int:
        """Estimate reading time in minutes."""
        total_text = ""
        for key in ["definition", "explanation", "key_points", "examples"]:
            value = notes.get(key, "")
            if isinstance(value, str):
                total_text += value
            elif isinstance(value, list):
                total_text += " ".join(str(v) for v in value)
        
        words = len(total_text.split())
        return max(1, round(words / 200))  # 200 WPM reading speed
    
    def estimate_cost(self, num_concepts: int) -> dict[str, Any]:
        """
        Estimate cost for generating educational notes.
        
        Returns cost breakdown in Chinese Yuan (RMB).
        """
        # Average tokens per concept
        input_tokens_per_concept = 4000   # Raw text + prompt
        output_tokens_per_concept = 1500  # Generated notes
        
        total_input = input_tokens_per_concept * num_concepts
        total_output = output_tokens_per_concept * num_concepts
        
        # Get pricing for active model
        provider_costs = self.cost_config.get(self.llm_provider, {})
        model_costs = provider_costs.get(self.active_model, {"input": 0, "output": 0})
        
        input_cost = (total_input / 1000) * model_costs["input"]
        output_cost = (total_output / 1000) * model_costs["output"]
        total_cost = input_cost + output_cost
        
        return {
            "provider": self.llm_provider,
            "model": self.active_model,
            "concepts": num_concepts,
            "tokens": {
                "input": total_input,
                "output": total_output,
                "total": total_input + total_output,
            },
            "cost_rmb": {
                "input": round(input_cost, 3),
                "output": round(output_cost, 3),
                "total": round(total_cost, 3),
            },
            "cost_per_concept_rmb": round(total_cost / num_concepts, 3),
        }
    
    @staticmethod
    def print_cost_comparison():
        """Print cost comparison table for all providers."""
        print("\n💰 LLM Cost Comparison (per concept, in Chinese Yuan/RMB)")
        print("=" * 70)
        print(f"{'Provider':<12} {'Model':<25} {'Input':<10} {'Output':<10} {'Total':<10}")
        print("-" * 70)
        
        # Estimated tokens per concept
        input_tokens = 4000
        output_tokens = 1500
        
        comparisons = [
            ("OpenAI", "gpt-4o-mini", 0.11, 0.44),
            ("OpenAI", "gpt-4o", 2.75, 11.0),
            ("Kimi", "moonshot-v1-8k", 0.012, 0.012),
            ("Kimi", "moonshot-v1-32k", 0.024, 0.024),
            ("Kimi", "moonshot-v1-128k", 0.12, 0.12),
        ]
        
        for provider, model, input_rate, output_rate in comparisons:
            input_cost = (input_tokens / 1000) * input_rate
            output_cost = (output_tokens / 1000) * output_rate
            total_cost = input_cost + output_cost
            
            print(f"{provider:<12} {model:<25} ¥{input_cost:<9.3f} ¥{output_cost:<9.3f} ¥{total_cost:<9.3f}")
        
        print("-" * 70)
        print("\n📊 Example: 30-concept textbook")
        print("-" * 70)
        for provider, model, input_rate, output_rate in comparisons:
            input_cost = (input_tokens / 1000) * input_rate * 30
            output_cost = (output_tokens / 1000) * output_rate * 30
            total_cost = input_cost + output_cost
            
            marker = "⭐ " if "kimi" in model else "   "
            print(f"{marker}{provider} {model}: ¥{total_cost:.2f} RMB")
        
        print("\n💡 Kimi (Moonshot AI) is ~10x cheaper than OpenAI GPT-4o-mini!")
        print("   Get API key: https://platform.moonshot.cn/")


# CLI interface
def main():
    """CLI for educational pipeline."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python educational_pipeline.py <pdf_path> [output_dir]")
        print("\nEnvironment variables:")
        print("  OPENAI_API_KEY - Required for LLM enhancement")
        sys.exit(1)
    
    pdf_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("educational_output")
    
    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    print(f"Processing: {pdf_path}")
    print(f"Output: {output_dir}")
    print()
    
    # Initialize generator
    generator = EducationalNoteGenerator()
    
    print(f"Marker available: {generator.use_marker}")
    print(f"LLM available: {generator.llm_available}")
    print()
    
    # Process PDF
    result = generator.process_pdf(pdf_path, output_dir=output_dir)
    
    # Print results
    if result["success"]:
        print("✅ Processing successful!")
        print(f"\nStats:")
        for key, value in result["stats"].items():
            print(f"  {key}: {value}")
        
        print(f"\nGenerated files:")
        for key, path in result["outputs"].items():
            print(f"  {key}: {path}")
    else:
        print("❌ Processing completed with errors:")
        for error in result["errors"]:
            print(f"  - {error}")
        
        if result["outputs"]:
            print("\nPartial outputs generated:")
            for key, path in result["outputs"].items():
                print(f"  {key}: {path}")


if __name__ == "__main__":
    main()
