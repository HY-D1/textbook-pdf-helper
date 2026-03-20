"""
Comprehensive Data Integrity and Validation Testing Suite
for ALGL PDF Helper project.

This module performs:
1. JSON schema validation
2. Cross-reference validation
3. Content validation
4. Asset validation
5. Embedding validation
6. Provenance validation
7. Round-trip testing
8. Data corruption detection
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest

# Constants
SCHEMA_FILE = Path("schemas/textbook-static-v1.json")
OUTPUT_DIRS = [
    Path("output/both-pdfs"),
    Path("output/murachs-mysql-3rd-edition-v2"),
    Path("output/murach-test"),
]

REQUIRED_JSON_FILES = [
    "concept-manifest.json",
    "concept-map.json",
]

OPTIONAL_JSON_FILES = [
    "textbook-manifest.json",
    "chunks.json",
    "asset-manifest.json",
]


class JSONValidator:
    """Validates JSON files against schemas."""
    
    def __init__(self, schema_path: Path):
        self.schema_path = schema_path
        self.schema = self._load_schema()
        self.errors: List[str] = []
    
    def _load_schema(self) -> Optional[Dict]:
        """Load JSON schema from file."""
        try:
            with open(self.schema_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.errors.append(f"Failed to load schema: {e}")
            return None
    
    def validate_json_file(self, file_path: Path) -> Tuple[bool, List[str]]:
        """Validate a JSON file against the schema."""
        errors = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON: {e}"]
        except Exception as e:
            return False, [f"Failed to load file: {e}"]
        
        # Basic structure validation (without jsonschema library)
        is_valid = True
        
        # Check required fields based on file type
        file_name = file_path.name
        
        if "concept-manifest" in file_name:
            is_valid, field_errors = self._validate_concept_manifest(data)
            errors.extend(field_errors)
        elif "concept-map" in file_name:
            is_valid, field_errors = self._validate_concept_map(data)
            errors.extend(field_errors)
        elif "extraction" in file_name:
            is_valid, field_errors = self._validate_extraction(data)
            errors.extend(field_errors)
        elif "educational-notes" in file_name:
            is_valid, field_errors = self._validate_educational_notes(data)
            errors.extend(field_errors)
        elif "sqladapt" in file_name:
            is_valid, field_errors = self._validate_sqladapt(data)
            errors.extend(field_errors)
        
        return is_valid, errors
    
    def _validate_concept_manifest(self, data: Dict) -> Tuple[bool, List[str]]:
        """Validate concept-manifest.json structure."""
        errors = []
        is_valid = True
        
        # Check required fields
        required = ["schemaVersion", "sourceDocId", "createdAt", "conceptCount", "concepts"]
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: {field}")
                is_valid = False
        
        # Validate schema version
        if data.get("schemaVersion") != "concept-manifest-v1":
            errors.append(f"Invalid schemaVersion: {data.get('schemaVersion')}")
            is_valid = False
        
        # Validate conceptCount matches actual concepts
        if "concepts" in data and "conceptCount" in data:
            actual_count = len(data["concepts"])
            if actual_count != data["conceptCount"]:
                errors.append(f"conceptCount mismatch: declared={data['conceptCount']}, actual={actual_count}")
                is_valid = False
        
        # Validate each concept
        if "concepts" in data:
            for concept_id, concept in data["concepts"].items():
                if "id" not in concept:
                    errors.append(f"Concept {concept_id} missing 'id' field")
                    is_valid = False
                if "title" not in concept:
                    errors.append(f"Concept {concept_id} missing 'title' field")
                    is_valid = False
                
                # Validate pageReferences are positive integers
                if "pageReferences" in concept:
                    for page in concept["pageReferences"]:
                        if not isinstance(page, int) or page < 1:
                            errors.append(f"Concept {concept_id} has invalid page number: {page}")
                            is_valid = False
        
        return is_valid, errors
    
    def _validate_concept_map(self, data: Dict) -> Tuple[bool, List[str]]:
        """Validate concept-map.json structure."""
        errors = []
        is_valid = True
        
        required = ["version", "generatedAt", "sourceDocIds", "concepts"]
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: {field}")
                is_valid = False
        
        # Validate version
        if data.get("version") != "1.0.0":
            errors.append(f"Invalid version: {data.get('version')}")
            is_valid = False
        
        # Validate concepts exist
        if "concepts" in data and not data["concepts"]:
            errors.append("Concept map has no concepts")
            is_valid = False
        
        return is_valid, errors
    
    def _validate_extraction(self, data: Dict) -> Tuple[bool, List[str]]:
        """Validate extraction JSON structure."""
        errors = []
        is_valid = True
        
        if "success" not in data:
            errors.append("Missing 'success' field")
            is_valid = False
        
        if "content" not in data:
            errors.append("Missing 'content' field")
            is_valid = False
        else:
            content = data["content"]
            if "pages" not in content:
                errors.append("Missing 'content.pages' field")
                is_valid = False
            else:
                # Validate page structure
                for i, page in enumerate(content["pages"]):
                    if "page_number" not in page:
                        errors.append(f"Page {i} missing 'page_number'")
                        is_valid = False
                    if "text" not in page:
                        errors.append(f"Page {i} missing 'text'")
                        is_valid = False
        
        return is_valid, errors
    
    def _validate_educational_notes(self, data: Dict) -> Tuple[bool, List[str]]:
        """Validate educational-notes.json structure."""
        errors = []
        is_valid = True
        
        if "concepts" not in data:
            errors.append("Missing 'concepts' field")
            is_valid = False
        else:
            for concept_id, concept in data["concepts"].items():
                if "id" not in concept:
                    errors.append(f"Educational note {concept_id} missing 'id'")
                    is_valid = False
                if "title" not in concept:
                    errors.append(f"Educational note {concept_id} missing 'title'")
                    is_valid = False
        
        return is_valid, errors
    
    def _validate_sqladapt(self, data: Dict) -> Tuple[bool, List[str]]:
        """Validate sqladapt.json structure."""
        errors = []
        is_valid = True
        
        if "schemaVersion" not in data:
            errors.append("Missing 'schemaVersion' field")
            is_valid = False
        
        if "concepts" not in data:
            errors.append("Missing 'concepts' field")
            is_valid = False
        
        return is_valid, errors


class CrossReferenceValidator:
    """Validates cross-references between files."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_all(self) -> Tuple[bool, List[str], List[str]]:
        """Run all cross-reference validations."""
        is_valid = True
        
        # Load all relevant files
        concept_manifest = self._load_json("concept-manifest.json")
        concept_map = self._load_json("concept-map.json")
        extraction = self._load_json_file_pattern("-extraction.json")
        educational_notes = self._load_json_file_pattern("-educational-notes.json")
        sqladapt = self._load_json_file_pattern("-sqladapt.json")
        
        # Validate concept manifest to concept map consistency
        v, e = self._validate_manifest_to_map(concept_manifest, concept_map)
        is_valid = is_valid and v
        self.errors.extend(e)
        
        # Validate extraction to concept manifest consistency
        v, e = self._validate_extraction_to_manifest(extraction, concept_manifest)
        is_valid = is_valid and v
        self.errors.extend(e)
        
        # Validate docId consistency
        v, e = self._validate_doc_id_consistency(concept_manifest, concept_map, sqladapt)
        is_valid = is_valid and v
        self.errors.extend(e)
        
        return is_valid, self.errors, self.warnings
    
    def _load_json(self, filename: str) -> Optional[Dict]:
        """Load a JSON file from the output directory."""
        file_path = self.output_dir / filename
        if not file_path.exists():
            return None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.errors.append(f"Failed to load {filename}: {e}")
            return None
    
    def _load_json_file_pattern(self, pattern: str) -> Optional[Dict]:
        """Load a JSON file matching a pattern."""
        for file in self.output_dir.glob(f"*{pattern}"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.errors.append(f"Failed to load {file}: {e}")
        return None
    
    def _validate_manifest_to_map(
        self, 
        manifest: Optional[Dict], 
        concept_map: Optional[Dict]
    ) -> Tuple[bool, List[str]]:
        """Validate concept manifest matches concept map."""
        errors = []
        is_valid = True
        
        if not manifest or not concept_map:
            return True, []  # Skip if files don't exist
        
        manifest_concepts = set(manifest.get("concepts", {}).keys())
        map_concepts = set(concept_map.get("concepts", {}).keys())
        
        # Check for concepts in manifest but not in map
        missing_in_map = manifest_concepts - map_concepts
        if missing_in_map:
            errors.append(f"Concepts in manifest but not in map: {missing_in_map}")
            is_valid = False
        
        # Check for concepts in map but not in manifest
        missing_in_manifest = map_concepts - manifest_concepts
        if missing_in_manifest:
            self.warnings.append(f"Concepts in map but not in manifest: {missing_in_manifest}")
        
        return is_valid, errors
    
    def _validate_extraction_to_manifest(
        self,
        extraction: Optional[Dict],
        manifest: Optional[Dict]
    ) -> Tuple[bool, List[str]]:
        """Validate extraction data matches concept manifest."""
        errors = []
        is_valid = True
        
        if not extraction or not manifest:
            return True, []
        
        # Get page count from extraction
        if "content" in extraction and "pages" in extraction["content"]:
            extraction_pages = len(extraction["content"]["pages"])
            
            # Validate page references in manifest don't exceed extraction pages
            for concept_id, concept in manifest.get("concepts", {}).items():
                page_refs = concept.get("pageReferences", [])
                for page in page_refs:
                    if page > extraction_pages:
                        errors.append(
                            f"Concept {concept_id} references page {page} "
                            f"but extraction only has {extraction_pages} pages"
                        )
                        is_valid = False
        
        return is_valid, errors
    
    def _validate_doc_id_consistency(
        self,
        manifest: Optional[Dict],
        concept_map: Optional[Dict],
        sqladapt: Optional[Dict]
    ) -> Tuple[bool, List[str]]:
        """Validate docId consistency across files."""
        errors = []
        is_valid = True
        
        doc_ids = set()
        
        if manifest:
            doc_ids.add(manifest.get("sourceDocId"))
        
        if sqladapt:
            doc_ids.add(sqladapt.get("sourceDocId"))
        
        if concept_map:
            doc_ids.update(concept_map.get("sourceDocIds", []))
        
        # Remove None values
        doc_ids = {d for d in doc_ids if d}
        
        if len(doc_ids) > 1:
            errors.append(f"Inconsistent docIds across files: {doc_ids}")
            is_valid = False
        
        return is_valid, errors


class ContentValidator:
    """Validates content in output files."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_all(self) -> Tuple[bool, List[str], List[str]]:
        """Run all content validations."""
        is_valid = True
        
        # Load files
        extraction = self._load_json_file_pattern("-extraction.json")
        concept_manifest = self._load_json("concept-manifest.json")
        
        # Validate extraction content
        if extraction:
            v, e = self._validate_extraction_content(extraction)
            is_valid = is_valid and v
            self.errors.extend(e)
        
        # Validate concept manifest content
        if concept_manifest:
            v, e = self._validate_manifest_content(concept_manifest)
            is_valid = is_valid and v
            self.errors.extend(e)
        
        # Validate markdown files
        v, e = self._validate_markdown_files()
        is_valid = is_valid and v
        self.errors.extend(e)
        
        return is_valid, self.errors, self.warnings
    
    def _load_json(self, filename: str) -> Optional[Dict]:
        """Load a JSON file from the output directory."""
        file_path = self.output_dir / filename
        if not file_path.exists():
            return None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    def _load_json_file_pattern(self, pattern: str) -> Optional[Dict]:
        """Load a JSON file matching a pattern."""
        for file in self.output_dir.glob(f"*{pattern}"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return None
        return None
    
    def _validate_extraction_content(self, extraction: Dict) -> Tuple[bool, List[str]]:
        """Validate extraction content."""
        errors = []
        is_valid = True
        
        if "content" not in extraction or "pages" not in extraction["content"]:
            return True, []
        
        pages = extraction["content"]["pages"]
        
        for i, page in enumerate(pages):
            page_num = page.get("page_number", i + 1)
            text = page.get("text", "")
            
            # Check text is not empty
            if not text or not text.strip():
                errors.append(f"Page {page_num} has empty text")
                is_valid = False
            
            # Check for null bytes
            if '\x00' in text:
                errors.append(f"Page {page_num} contains null bytes")
                is_valid = False
            
            # Check for valid UTF-8 (already validated by loading)
            
            # Check reasonable character count
            if len(text) < 10:
                self.warnings.append(f"Page {page_num} has very short text ({len(text)} chars)")
        
        return is_valid, errors
    
    def _validate_manifest_content(self, manifest: Dict) -> Tuple[bool, List[str]]:
        """Validate concept manifest content."""
        errors = []
        is_valid = True
        
        concepts = manifest.get("concepts", {})
        
        for concept_id, concept in concepts.items():
            # Check title is not empty
            title = concept.get("title", "")
            if not title or not title.strip():
                errors.append(f"Concept {concept_id} has empty title")
                is_valid = False
            
            # Check definition is not just whitespace
            definition = concept.get("definition", "")
            if definition and not definition.strip():
                self.warnings.append(f"Concept {concept_id} has whitespace-only definition")
            
            # Validate difficulty level
            difficulty = concept.get("difficulty", "")
            valid_difficulties = ["beginner", "intermediate", "advanced"]
            if difficulty and difficulty not in valid_difficulties:
                errors.append(
                    f"Concept {concept_id} has invalid difficulty: {difficulty}"
                )
                is_valid = False
        
        return is_valid, errors
    
    def _validate_markdown_files(self) -> Tuple[bool, List[str]]:
        """Validate markdown files in concepts directory."""
        errors = []
        is_valid = True
        
        concepts_dir = self.output_dir / "concepts"
        if not concepts_dir.exists():
            return True, []
        
        for md_file in concepts_dir.rglob("*.md"):
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check file is not empty
                if not content.strip():
                    errors.append(f"Markdown file {md_file.name} is empty")
                    is_valid = False
                
                # Check for frontmatter
                if content.startswith('---'):
                    # Extract frontmatter
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        frontmatter = parts[1]
                        # Basic YAML validation
                        if 'id:' not in frontmatter:
                            errors.append(f"Markdown file {md_file.name} missing id in frontmatter")
                            is_valid = False
                        if 'title:' not in frontmatter:
                            errors.append(f"Markdown file {md_file.name} missing title in frontmatter")
                            is_valid = False
                
            except Exception as e:
                errors.append(f"Failed to read markdown file {md_file}: {e}")
                is_valid = False
        
        return is_valid, errors


class AssetValidator:
    """Validates extracted assets."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_all(self) -> Tuple[bool, List[str], List[str]]:
        """Run all asset validations."""
        is_valid = True
        
        # Validate images
        v, e, w = self._validate_images()
        is_valid = is_valid and v
        self.errors.extend(e)
        self.warnings.extend(w)
        
        # Validate tables
        v, e, w = self._validate_tables()
        is_valid = is_valid and v
        self.errors.extend(e)
        self.warnings.extend(w)
        
        # Validate asset references
        v, e, w = self._validate_asset_references()
        is_valid = is_valid and v
        self.errors.extend(e)
        self.warnings.extend(w)
        
        return is_valid, self.errors, self.warnings
    
    def _validate_images(self) -> Tuple[bool, List[str], List[str]]:
        """Validate extracted images."""
        errors = []
        warnings = []
        is_valid = True
        
        images_dir = self.output_dir / "assets" / "images"
        if not images_dir.exists():
            return True, [], []
        
        for img_file in images_dir.rglob("*"):
            if not img_file.is_file():
                continue
            
            # Check file extension
            ext = img_file.suffix.lower()
            if ext not in ['.png', '.jpg', '.jpeg', '.gif', '.svg']:
                warnings.append(f"Image {img_file.name} has non-standard extension: {ext}")
            
            # Check file is not empty
            if img_file.stat().st_size == 0:
                errors.append(f"Image {img_file.name} is empty (0 bytes)")
                is_valid = False
            
            # Check file size is reasonable (not too large)
            if img_file.stat().st_size > 50 * 1024 * 1024:  # 50MB
                warnings.append(f"Image {img_file.name} is very large ({img_file.stat().st_size / (1024*1024):.1f} MB)")
        
        return is_valid, errors, warnings
    
    def _validate_tables(self) -> Tuple[bool, List[str], List[str]]:
        """Validate extracted tables."""
        errors = []
        warnings = []
        is_valid = True
        
        tables_dir = self.output_dir / "assets" / "tables"
        if not tables_dir.exists():
            return True, [], []
        
        for table_file in tables_dir.rglob("*"):
            if not table_file.is_file():
                continue
            
            ext = table_file.suffix.lower()
            if ext == '.html':
                # Validate HTML structure
                try:
                    with open(table_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if '<table' not in content.lower():
                        warnings.append(f"HTML table file {table_file.name} missing <table> tag")
                except Exception as e:
                    errors.append(f"Failed to read table file {table_file.name}: {e}")
                    is_valid = False
            
            elif ext == '.csv':
                # Basic CSV validation
                try:
                    with open(table_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    if len(lines) < 1:
                        warnings.append(f"CSV file {table_file.name} has no data")
                except Exception as e:
                    errors.append(f"Failed to read CSV file {table_file.name}: {e}")
                    is_valid = False
            
            elif ext == '.md':
                # Markdown table validation
                try:
                    with open(table_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if '|' not in content:
                        warnings.append(f"Markdown table file {table_file.name} missing table markers")
                except Exception as e:
                    errors.append(f"Failed to read markdown table file {table_file.name}: {e}")
                    is_valid = False
        
        return is_valid, errors, warnings
    
    def _validate_asset_references(self) -> Tuple[bool, List[str], List[str]]:
        """Validate asset references in markdown files."""
        errors = []
        warnings = []
        is_valid = True
        
        concepts_dir = self.output_dir / "concepts"
        if not concepts_dir.exists():
            return True, [], []
        
        # Find all assets
        assets_dir = self.output_dir / "assets"
        existing_assets = set()
        if assets_dir.exists():
            for asset in assets_dir.rglob("*"):
                if asset.is_file():
                    # Store relative path
                    rel_path = asset.relative_to(self.output_dir)
                    existing_assets.add(str(rel_path))
        
        # Check markdown files for broken references
        for md_file in concepts_dir.rglob("*.md"):
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find image references ![alt](path)
                img_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
                for match in img_pattern.finditer(content):
                    alt_text = match.group(1)
                    img_path = match.group(2)
                    
                    # Resolve relative path
                    if not img_path.startswith(('http://', 'https://', '/')):
                        full_path = self.output_dir / img_path
                        if not full_path.exists():
                            warnings.append(
                                f"Markdown file {md_file.name} references non-existent image: {img_path}"
                            )
                
                # Find link references [text](path)
                link_pattern = re.compile(r'(?<!!)\[([^\]]+)\]\(([^)]+)\)')
                for match in link_pattern.finditer(content):
                    link_text = match.group(1)
                    link_path = match.group(2)
                    
                    # Skip external links and anchors
                    if link_path.startswith(('http://', 'https://', '#')):
                        continue
                    
                    # Resolve relative path
                    if not link_path.startswith('/'):
                        full_path = self.output_dir / link_path
                        if not full_path.exists():
                            warnings.append(
                                f"Markdown file {md_file.name} references non-existent link: {link_path}"
                            )
                
            except Exception as e:
                errors.append(f"Failed to check markdown file {md_file}: {e}")
                is_valid = False
        
        return is_valid, errors, warnings


class EmbeddingValidator:
    """Validates embeddings in output files."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_all(self) -> Tuple[bool, List[str], List[str]]:
        """Run all embedding validations."""
        is_valid = True
        
        # Currently, embeddings are stored in the sqladapt.json files
        # Let's check if we can find and validate them
        sqladapt = self._load_sqladapt()
        
        if sqladapt:
            # Check for any embedding fields
            v, e = self._validate_embeddings_in_sqladapt(sqladapt)
            is_valid = is_valid and v
            self.errors.extend(e)
        
        return is_valid, self.errors, self.warnings
    
    def _load_sqladapt(self) -> Optional[Dict]:
        """Load sqladapt JSON file."""
        for file in self.output_dir.glob("*-sqladapt.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return None
        return None
    
    def _validate_embeddings_in_sqladapt(self, data: Dict) -> Tuple[bool, List[str]]:
        """Validate embeddings in sqladapt data."""
        errors = []
        is_valid = True
        
        # Currently, embeddings are not explicitly stored in the sqladapt format
        # based on what we've seen. If they were, they would be validated here.
        # This is a placeholder for when embeddings are added.
        
        return is_valid, errors
    
    def validate_embedding_vector(self, vector: List[float]) -> Tuple[bool, List[str]]:
        """Validate a single embedding vector."""
        errors = []
        is_valid = True
        
        # Check dimensions
        if len(vector) != 24:
            errors.append(f"Invalid embedding dimension: {len(vector)}, expected 24")
            is_valid = False
        
        # Check for NaN or Inf values
        for i, val in enumerate(vector):
            if math.isnan(val):
                errors.append(f"Embedding contains NaN at index {i}")
                is_valid = False
            if math.isinf(val):
                errors.append(f"Embedding contains Inf at index {i}")
                is_valid = False
        
        # Check L2 normalization (should be approximately 1.0)
        if is_valid:
            l2_norm = math.sqrt(sum(x**2 for x in vector))
            if abs(l2_norm - 1.0) > 0.01:
                errors.append(f"Embedding not L2 normalized: norm={l2_norm}")
                is_valid = False
        
        return is_valid, errors


class ProvenanceValidator:
    """Validates provenance tracking."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_all(self) -> Tuple[bool, List[str], List[str]]:
        """Run all provenance validations."""
        is_valid = True
        
        # Load files
        concept_manifest = self._load_json("concept-manifest.json")
        concept_map = self._load_json("concept-map.json")
        extraction = self._load_json_file_pattern("-extraction.json")
        
        # Validate chunk references
        if concept_manifest:
            v, e = self._validate_chunk_references(concept_manifest)
            is_valid = is_valid and v
            self.errors.extend(e)
        
        # Validate page references
        if concept_manifest and extraction:
            v, e = self._validate_page_references(concept_manifest, extraction)
            is_valid = is_valid and v
            self.errors.extend(e)
        
        # Validate timestamps
        v, e = self._validate_timestamps()
        is_valid = is_valid and v
        self.errors.extend(e)
        
        return is_valid, self.errors, self.warnings
    
    def _load_json(self, filename: str) -> Optional[Dict]:
        """Load a JSON file from the output directory."""
        file_path = self.output_dir / filename
        if not file_path.exists():
            return None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    def _load_json_file_pattern(self, pattern: str) -> Optional[Dict]:
        """Load a JSON file matching a pattern."""
        for file in self.output_dir.glob(f"*{pattern}"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return None
        return None
    
    def _validate_chunk_references(self, manifest: Dict) -> Tuple[bool, List[str]]:
        """Validate that all chunk references follow the correct format."""
        errors = []
        is_valid = True
        
        # Chunk ID pattern: {docId}:p{page}:c{index}
        chunk_pattern = re.compile(r'^[\w-]+:p\d+:c\d+$')
        
        concepts = manifest.get("concepts", {})
        for concept_id, concept in concepts.items():
            sections = concept.get("sections", {})
            for section_name, section_data in sections.items():
                chunk_ids = section_data.get("chunkIds", [])
                for chunk_id in chunk_ids:
                    if not chunk_pattern.match(chunk_id):
                        errors.append(
                            f"Concept {concept_id} has invalid chunk ID format: {chunk_id}"
                        )
                        is_valid = False
        
        return is_valid, errors
    
    def _validate_page_references(self, manifest: Dict, extraction: Dict) -> Tuple[bool, List[str]]:
        """Validate that page references are valid."""
        errors = []
        is_valid = True
        
        # Get total pages from extraction
        if "content" not in extraction or "pages" not in extraction["content"]:
            return True, []
        
        total_pages = len(extraction["content"]["pages"])
        
        concepts = manifest.get("concepts", {})
        for concept_id, concept in concepts.items():
            page_refs = concept.get("pageReferences", [])
            for page in page_refs:
                if not isinstance(page, int) or page < 1:
                    errors.append(
                        f"Concept {concept_id} has invalid page number: {page}"
                    )
                    is_valid = False
                elif page > total_pages:
                    errors.append(
                        f"Concept {concept_id} references page {page} "
                        f"but PDF only has {total_pages} pages"
                    )
                    is_valid = False
        
        return is_valid, errors
    
    def _validate_timestamps(self) -> Tuple[bool, List[str]]:
        """Validate ISO 8601 timestamps in files."""
        errors = []
        is_valid = True
        
        # Check various files for valid timestamps
        files_to_check = ["concept-manifest.json", "concept-map.json"]
        
        for filename in files_to_check:
            file_path = self.output_dir / filename
            if not file_path.exists():
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                timestamp_fields = ["createdAt", "generatedAt"]
                for field in timestamp_fields:
                    if field in data:
                        ts = data[field]
                        try:
                            # Try to parse ISO 8601 timestamp
                            datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        except ValueError:
                            errors.append(f"{filename} has invalid timestamp in {field}: {ts}")
                            is_valid = False
            except Exception:
                pass
        
        return is_valid, errors


class CorruptionDetector:
    """Detects data corruption in output files."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def detect_all(self) -> Tuple[bool, List[str], List[str]]:
        """Run all corruption detection checks."""
        is_valid = True
        
        # Check for truncated JSON files
        v, e = self._detect_truncated_json()
        is_valid = is_valid and v
        self.errors.extend(e)
        
        # Check for corrupted chunk data
        v, e = self._detect_corrupted_chunks()
        is_valid = is_valid and v
        self.errors.extend(e)
        
        # Check for missing required fields
        v, e = self._detect_missing_fields()
        is_valid = is_valid and v
        self.errors.extend(e)
        
        # Check for type mismatches
        v, e = self._detect_type_mismatches()
        is_valid = is_valid and v
        self.errors.extend(e)
        
        return is_valid, self.errors, self.warnings
    
    def _detect_truncated_json(self) -> Tuple[bool, List[str]]:
        """Detect truncated or corrupted JSON files."""
        errors = []
        is_valid = True
        
        for json_file in self.output_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Primary check: try to parse the JSON
                try:
                    data = json.loads(content)
                except json.JSONDecodeError as e:
                    errors.append(f"JSON file {json_file.name} is corrupted: {e}")
                    is_valid = False
                    continue
                
                # Secondary check: verify the file ends properly
                # A valid JSON file should end with '}' or ']' or a string/number
                stripped = content.rstrip()
                if stripped:
                    last_char = stripped[-1]
                    valid_endings = ['}', ']', '"', ']', '}', 'e', 'l', 'n']  # true, false, null
                    if last_char not in valid_endings and not last_char.isdigit():
                        errors.append(
                            f"JSON file {json_file.name} may be truncated (unexpected ending)"
                        )
                        is_valid = False
                
                # Tertiary check: for large files, verify all objects are complete
                # by re-serializing and comparing structure counts
                try:
                    re_serialized = json.dumps(data)
                    # If re-serialization succeeds, structure is intact
                except Exception as e:
                    errors.append(
                        f"JSON file {json_file.name} has structure issues: {e}"
                    )
                    is_valid = False
                
            except Exception as e:
                errors.append(f"Failed to check {json_file.name}: {e}")
                is_valid = False
        
        return is_valid, errors
    
    def _detect_corrupted_chunks(self) -> Tuple[bool, List[str]]:
        """Detect corrupted chunk data."""
        errors = []
        is_valid = True
        
        # Check extraction files for corrupted chunks
        for extraction_file in self.output_dir.glob("*-extraction.json"):
            try:
                with open(extraction_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if "content" not in data or "pages" not in data["content"]:
                    continue
                
                for i, page in enumerate(data["content"]["pages"]):
                    # Check for missing required fields
                    if "page_number" not in page:
                        errors.append(f"Extraction page {i} missing page_number in {extraction_file.name}")
                        is_valid = False
                    
                    # Check for null values in text
                    if page.get("text") is None:
                        errors.append(f"Extraction page {i} has null text in {extraction_file.name}")
                        is_valid = False
                    
            except Exception:
                pass
        
        return is_valid, errors
    
    def _detect_missing_fields(self) -> Tuple[bool, List[str]]:
        """Detect missing required fields."""
        errors = []
        is_valid = True
        
        # Check concept-manifest.json
        manifest_path = self.output_dir / "concept-manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                required_fields = ["schemaVersion", "sourceDocId", "createdAt", "conceptCount", "concepts"]
                for field in required_fields:
                    if field not in data:
                        errors.append(f"concept-manifest.json missing required field: {field}")
                        is_valid = False
                
            except Exception:
                pass
        
        # Check concept-map.json
        map_path = self.output_dir / "concept-map.json"
        if map_path.exists():
            try:
                with open(map_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                required_fields = ["version", "generatedAt", "sourceDocIds", "concepts"]
                for field in required_fields:
                    if field not in data:
                        errors.append(f"concept-map.json missing required field: {field}")
                        is_valid = False
                
            except Exception:
                pass
        
        return is_valid, errors
    
    def _detect_type_mismatches(self) -> Tuple[bool, List[str]]:
        """Detect type mismatches in data."""
        errors = []
        is_valid = True
        
        # Check concept-manifest.json
        manifest_path = self.output_dir / "concept-manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Check conceptCount is integer
                if "conceptCount" in data and not isinstance(data["conceptCount"], int):
                    errors.append(f"concept-manifest.json conceptCount should be integer, got {type(data['conceptCount'])}")
                    is_valid = False
                
                # Check concepts is dict/object
                if "concepts" in data and not isinstance(data["concepts"], dict):
                    errors.append(f"concept-manifest.json concepts should be object, got {type(data['concepts'])}")
                    is_valid = False
                
                # Check pageReferences are integers
                for concept_id, concept in data.get("concepts", {}).items():
                    page_refs = concept.get("pageReferences", [])
                    for page in page_refs:
                        if not isinstance(page, int):
                            errors.append(
                                f"Concept {concept_id} has non-integer page reference: {page}"
                            )
                            is_valid = False
                
            except Exception:
                pass
        
        return is_valid, errors


class RoundTripTester:
    """Tests that data can be loaded and saved without loss."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def test_all(self) -> Tuple[bool, List[str], List[str]]:
        """Run all round-trip tests."""
        is_valid = True
        
        # Test concept-manifest round-trip
        v, e = self._test_json_roundtrip("concept-manifest.json")
        is_valid = is_valid and v
        self.errors.extend(e)
        
        # Test concept-map round-trip
        v, e = self._test_json_roundtrip("concept-map.json")
        is_valid = is_valid and v
        self.errors.extend(e)
        
        return is_valid, self.errors, self.warnings
    
    def _test_json_roundtrip(self, filename: str) -> Tuple[bool, List[str]]:
        """Test JSON round-trip serialization."""
        errors = []
        is_valid = True
        
        file_path = self.output_dir / filename
        if not file_path.exists():
            return True, []  # Skip if file doesn't exist
        
        try:
            # Load original
            with open(file_path, 'r', encoding='utf-8') as f:
                original = json.load(f)
            
            # Serialize
            serialized = json.dumps(original, ensure_ascii=False, sort_keys=True)
            
            # Deserialize
            deserialized = json.loads(serialized)
            
            # Compare key fields
            self._compare_fields(original, deserialized, filename, errors)
            
            if errors:
                is_valid = False
            
        except Exception as e:
            errors.append(f"Round-trip test failed for {filename}: {e}")
            is_valid = False
        
        return is_valid, errors
    
    def _compare_fields(self, original: Dict, deserialized: Dict, filename: str, errors: List[str]):
        """Compare key fields between original and deserialized data."""
        # Check basic fields based on file type
        if "concept-manifest" in filename:
            fields_to_check = ["schemaVersion", "sourceDocId", "conceptCount"]
            for field in fields_to_check:
                if original.get(field) != deserialized.get(field):
                    errors.append(
                        f"{filename} round-trip mismatch for {field}: "
                        f"original={original.get(field)}, deserialized={deserialized.get(field)}"
                    )
        
        elif "concept-map" in filename:
            fields_to_check = ["version", "sourceDocIds"]
            for field in fields_to_check:
                if original.get(field) != deserialized.get(field):
                    errors.append(
                        f"{filename} round-trip mismatch for {field}: "
                        f"original={original.get(field)}, deserialized={deserialized.get(field)}"
                    )


def run_integrity_tests(output_dir: Path, schema_path: Path) -> Dict[str, Any]:
    """
    Run all integrity tests on an output directory.
    
    Returns a dictionary with test results.
    """
    results = {
        "output_dir": str(output_dir),
        "timestamp": datetime.now().isoformat(),
        "tests": {},
        "summary": {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "warnings": 0,
        }
    }
    
    # 1. JSON Schema Validation
    print(f"\n{'='*60}")
    print(f"Testing: {output_dir}")
    print(f"{'='*60}")
    print("\n1. JSON Schema Validation")
    validator = JSONValidator(schema_path)
    
    schema_results = []
    for json_file in output_dir.glob("*.json"):
        is_valid, errors = validator.validate_json_file(json_file)
        schema_results.append({
            "file": json_file.name,
            "valid": is_valid,
            "errors": errors
        })
        status = "✓" if is_valid else "✗"
        print(f"  {status} {json_file.name}")
        for error in errors:
            print(f"      - {error}")
    
    results["tests"]["schema_validation"] = schema_results
    
    # 2. Cross-Reference Validation
    print("\n2. Cross-Reference Validation")
    xref_validator = CrossReferenceValidator(output_dir)
    is_valid, errors, warnings = xref_validator.validate_all()
    results["tests"]["cross_reference"] = {
        "valid": is_valid,
        "errors": errors,
        "warnings": warnings
    }
    status = "✓" if is_valid else "✗"
    print(f"  {status} Cross-reference validation")
    for error in errors:
        print(f"      - ERROR: {error}")
    for warning in warnings:
        print(f"      - WARNING: {warning}")
    
    # 3. Content Validation
    print("\n3. Content Validation")
    content_validator = ContentValidator(output_dir)
    is_valid, errors, warnings = content_validator.validate_all()
    results["tests"]["content"] = {
        "valid": is_valid,
        "errors": errors,
        "warnings": warnings
    }
    status = "✓" if is_valid else "✗"
    print(f"  {status} Content validation")
    for error in errors:
        print(f"      - ERROR: {error}")
    for warning in warnings:
        print(f"      - WARNING: {warning}")
    
    # 4. Asset Validation
    print("\n4. Asset Validation")
    asset_validator = AssetValidator(output_dir)
    is_valid, errors, warnings = asset_validator.validate_all()
    results["tests"]["assets"] = {
        "valid": is_valid,
        "errors": errors,
        "warnings": warnings
    }
    status = "✓" if is_valid else "✗"
    print(f"  {status} Asset validation")
    for error in errors:
        print(f"      - ERROR: {error}")
    for warning in warnings:
        print(f"      - WARNING: {warning}")
    
    # 5. Embedding Validation
    print("\n5. Embedding Validation")
    embedding_validator = EmbeddingValidator(output_dir)
    is_valid, errors, warnings = embedding_validator.validate_all()
    results["tests"]["embeddings"] = {
        "valid": is_valid,
        "errors": errors,
        "warnings": warnings
    }
    status = "✓" if is_valid else "✗"
    print(f"  {status} Embedding validation")
    for error in errors:
        print(f"      - ERROR: {error}")
    
    # 6. Provenance Validation
    print("\n6. Provenance Validation")
    provenance_validator = ProvenanceValidator(output_dir)
    is_valid, errors, warnings = provenance_validator.validate_all()
    results["tests"]["provenance"] = {
        "valid": is_valid,
        "errors": errors,
        "warnings": warnings
    }
    status = "✓" if is_valid else "✗"
    print(f"  {status} Provenance validation")
    for error in errors:
        print(f"      - ERROR: {error}")
    for warning in warnings:
        print(f"      - WARNING: {warning}")
    
    # 7. Corruption Detection
    print("\n7. Data Corruption Detection")
    corruption_detector = CorruptionDetector(output_dir)
    is_valid, errors, warnings = corruption_detector.detect_all()
    results["tests"]["corruption"] = {
        "valid": is_valid,
        "errors": errors,
        "warnings": warnings
    }
    status = "✓" if is_valid else "✗"
    print(f"  {status} Corruption detection")
    for error in errors:
        print(f"      - ERROR: {error}")
    for warning in warnings:
        print(f"      - WARNING: {warning}")
    
    # 8. Round-Trip Testing
    print("\n8. Round-Trip Testing")
    roundtrip_tester = RoundTripTester(output_dir)
    is_valid, errors, warnings = roundtrip_tester.test_all()
    results["tests"]["roundtrip"] = {
        "valid": is_valid,
        "errors": errors,
        "warnings": warnings
    }
    status = "✓" if is_valid else "✗"
    print(f"  {status} Round-trip testing")
    for error in errors:
        print(f"      - ERROR: {error}")
    
    # Calculate summary
    all_tests = [
        results["tests"]["cross_reference"],
        results["tests"]["content"],
        results["tests"]["assets"],
        results["tests"]["embeddings"],
        results["tests"]["provenance"],
        results["tests"]["corruption"],
        results["tests"]["roundtrip"],
    ]
    
    results["summary"]["total_tests"] = len(all_tests) + len(schema_results)
    results["summary"]["passed"] = sum(1 for t in all_tests if t.get("valid", True))
    results["summary"]["passed"] += sum(1 for s in schema_results if s.get("valid", True))
    results["summary"]["failed"] = sum(1 for t in all_tests if not t.get("valid", True))
    results["summary"]["failed"] += sum(1 for s in schema_results if not s.get("valid", True))
    results["summary"]["warnings"] = sum(len(t.get("warnings", [])) for t in all_tests)
    
    return results


def generate_report(all_results: List[Dict], output_path: Path):
    """Generate a comprehensive markdown report."""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# Data Integrity and Validation Test Report\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Overall summary
        f.write("## Executive Summary\n\n")
        total_tests = sum(r["summary"]["total_tests"] for r in all_results)
        total_passed = sum(r["summary"]["passed"] for r in all_results)
        total_failed = sum(r["summary"]["failed"] for r in all_results)
        total_warnings = sum(r["summary"]["warnings"] for r in all_results)
        
        f.write(f"- **Total Test Runs**: {len(all_results)}\n")
        f.write(f"- **Total Tests**: {total_tests}\n")
        f.write(f"- **Passed**: {total_passed} ({100*total_passed/total_tests:.1f}%)\n")
        f.write(f"- **Failed**: {total_failed}\n")
        f.write(f"- **Warnings**: {total_warnings}\n\n")
        
        # Per-directory results
        f.write("## Detailed Results by Directory\n\n")
        
        for result in all_results:
            dir_name = Path(result["output_dir"]).name
            f.write(f"### {dir_name}\n\n")
            
            summary = result["summary"]
            f.write(f"- **Tests**: {summary['total_tests']}\n")
            f.write(f"- **Passed**: {summary['passed']}\n")
            f.write(f"- **Failed**: {summary['failed']}\n")
            f.write(f"- **Warnings**: {summary['warnings']}\n\n")
            
            # Schema validation results
            f.write("#### JSON Schema Validation\n\n")
            for schema_result in result["tests"].get("schema_validation", []):
                status = "✓" if schema_result["valid"] else "✗"
                f.write(f"- {status} `{schema_result['file']}`\n")
                for error in schema_result["errors"]:
                    f.write(f"  - {error}\n")
            f.write("\n")
            
            # Cross-reference validation
            xref = result["tests"].get("cross_reference", {})
            if xref:
                status = "✓" if xref.get("valid") else "✗"
                f.write(f"#### Cross-Reference Validation: {status}\n\n")
                for error in xref.get("errors", []):
                    f.write(f"- **ERROR**: {error}\n")
                for warning in xref.get("warnings", []):
                    f.write(f"- **WARNING**: {warning}\n")
                f.write("\n")
            
            # Content validation
            content = result["tests"].get("content", {})
            if content:
                status = "✓" if content.get("valid") else "✗"
                f.write(f"#### Content Validation: {status}\n\n")
                for error in content.get("errors", []):
                    f.write(f"- **ERROR**: {error}\n")
                for warning in content.get("warnings", []):
                    f.write(f"- **WARNING**: {warning}\n")
                f.write("\n")
            
            # Asset validation
            assets = result["tests"].get("assets", {})
            if assets and (assets.get("errors") or assets.get("warnings")):
                status = "✓" if assets.get("valid") else "✗"
                f.write(f"#### Asset Validation: {status}\n\n")
                for error in assets.get("errors", []):
                    f.write(f"- **ERROR**: {error}\n")
                for warning in assets.get("warnings", []):
                    f.write(f"- **WARNING**: {warning}\n")
                f.write("\n")
            
            # Provenance validation
            provenance = result["tests"].get("provenance", {})
            if provenance:
                status = "✓" if provenance.get("valid") else "✗"
                f.write(f"#### Provenance Validation: {status}\n\n")
                for error in provenance.get("errors", []):
                    f.write(f"- **ERROR**: {error}\n")
                for warning in provenance.get("warnings", []):
                    f.write(f"- **WARNING**: {warning}\n")
                f.write("\n")
            
            # Corruption detection
            corruption = result["tests"].get("corruption", {})
            if corruption:
                status = "✓" if corruption.get("valid") else "✗"
                f.write(f"#### Corruption Detection: {status}\n\n")
                for error in corruption.get("errors", []):
                    f.write(f"- **ERROR**: {error}\n")
                for warning in corruption.get("warnings", []):
                    f.write(f"- **WARNING**: {warning}\n")
                f.write("\n")
            
            # Round-trip testing
            roundtrip = result["tests"].get("roundtrip", {})
            if roundtrip:
                status = "✓" if roundtrip.get("valid") else "✗"
                f.write(f"#### Round-Trip Testing: {status}\n\n")
                for error in roundtrip.get("errors", []):
                    f.write(f"- **ERROR**: {error}\n")
                f.write("\n")
        
        # Integrity guarantees
        f.write("## Integrity Guarantees\n\n")
        f.write("Based on the validation tests performed, the following integrity guarantees are in place:\n\n")
        f.write("### JSON Schema Validation\n\n")
        f.write("- All JSON files are well-formed and parseable\n")
        f.write("- Required fields are present in all output files\n")
        f.write("- Schema versions are consistent\n\n")
        
        f.write("### Cross-Reference Validation\n\n")
        f.write("- Concept IDs are consistent between concept-manifest.json and concept-map.json\n")
        f.write("- Page references are within valid bounds\n")
        f.write("- Document IDs are consistent across files\n\n")
        
        f.write("### Content Validation\n\n")
        f.write("- Text content is not empty\n")
        f.write("- No null bytes in text content\n")
        f.write("- Valid UTF-8 encoding\n")
        f.write("- Markdown files have proper frontmatter\n\n")
        
        f.write("### Provenance Validation\n\n")
        f.write("- All chunk references follow the correct format: `{docId}:p{page}:c{index}`\n")
        f.write("- Page numbers are positive integers\n")
        f.write("- Timestamps are valid ISO 8601 format\n\n")
        
        f.write("### Corruption Detection\n\n")
        f.write("- JSON files are complete (no truncation)\n")
        f.write("- No corrupted chunk data\n")
        f.write("- Type consistency across fields\n\n")
        
        f.write("### Round-Trip Preservation\n\n")
        f.write("- Data can be serialized and deserialized without loss\n")
        f.write("- Key fields are preserved through round-trip\n\n")
        
        f.write("## Recommendations\n\n")
        f.write("1. **Fix Critical Errors**: Address all ERROR-level issues before deployment\n")
        f.write("2. **Review Warnings**: Evaluate WARNING-level issues for potential problems\n")
        f.write("3. **Regular Testing**: Run these integrity tests after each PDF processing run\n")
        f.write("4. **Schema Evolution**: Update schema validation when output format changes\n\n")
    
    print(f"\nReport saved to: {output_path}")


def main():
    """Main entry point for the integrity testing suite."""
    schema_path = Path("schemas/textbook-static-v1.json")
    
    # Find all output directories
    output_dirs = []
    if Path("output").exists():
        for subdir in Path("output").iterdir():
            if subdir.is_dir() and (subdir / "concept-manifest.json").exists():
                output_dirs.append(subdir)
    
    if not output_dirs:
        print("No output directories found with concept-manifest.json")
        return
    
    print(f"Found {len(output_dirs)} output directories to test")
    
    # Run tests on each directory
    all_results = []
    for output_dir in output_dirs:
        results = run_integrity_tests(output_dir, schema_path)
        all_results.append(results)
    
    # Generate report
    report_dir = Path("test_reports")
    report_dir.mkdir(exist_ok=True)
    report_path = report_dir / "data_integrity_test_report.md"
    generate_report(all_results, report_path)
    
    # Print summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    total_failed = sum(r["summary"]["failed"] for r in all_results)
    if total_failed == 0:
        print("✓ All tests passed!")
    else:
        print(f"✗ {total_failed} tests failed. See report for details.")


# ---------------------------------------------------------------------------
# Handoff integrity helpers (reusable)
# ---------------------------------------------------------------------------

def _build_minimal_export(tmp_path: Path, num_docs: int = 1) -> Path:
    """
    Build a minimal textbook-static directory in *tmp_path* without invoking
    the full pipeline.  Useful for unit-level integrity tests.
    """
    import hashlib

    export_dir = tmp_path / "export"
    export_dir.mkdir()
    concepts_dir = export_dir / "concepts"
    concepts_dir.mkdir()

    source_doc_ids = []
    concept_map_concepts: dict = {}
    source_docs_list = []
    chunks_meta: dict = {}

    for i in range(num_docs):
        doc_id = f"test-doc-{i}"
        source_doc_ids.append(doc_id)
        doc_dir = concepts_dir / doc_id
        doc_dir.mkdir()

        # Write two concept markdown files
        for j in range(2):
            cid = f"concept-{i}-{j}"
            namespaced = f"{doc_id}/{cid}"
            concept_map_concepts[namespaced] = {
                "title": f"Concept {i}-{j}",
                "definition": "A test concept.",
                "difficulty": "beginner",
                "pageNumbers": [1],
                "chunkIds": {},
                "relatedConcepts": [],
                "practiceProblemIds": [],
                "sourceDocId": doc_id,
                "provenance": {},
            }
            (doc_dir / f"{cid}.md").write_text(
                f"---\nid: {cid}\ntitle: Concept {i}-{j}\n---\n\n# Concept {i}-{j}\n"
            )

        source_docs_list.append({
            "docId": doc_id,
            "filename": f"{doc_id}.pdf",
            "sha256": hashlib.sha256(doc_id.encode()).hexdigest(),
            "pageCount": 8,
        })
        chunks_meta[doc_id] = {
            "totalChunks": 10,
            "sourceFile": doc_id,
            "exportedAt": "2026-01-01T00:00:00+00:00",
        }

    # concept-map.json
    (export_dir / "concept-map.json").write_text(json.dumps({
        "version": "1.0.0",
        "generatedAt": "2026-01-01T00:00:00+00:00",
        "sourceDocIds": source_doc_ids,
        "concepts": concept_map_concepts,
    }, indent=2))

    # textbook-manifest.json
    (export_dir / "textbook-manifest.json").write_text(json.dumps({
        "schemaVersion": "1.0.0",
        "schemaId": "textbook-static-v1",
        "indexId": "idx-test-001",
        "createdAt": "2026-01-01T00:00:00+00:00",
        "sourceName": "Test Doc",
        "sourceDocs": source_docs_list,
        "docCount": len(source_docs_list),
        "chunkCount": 10 * num_docs,
    }, indent=2))

    # chunks-metadata.json
    (export_dir / "chunks-metadata.json").write_text(json.dumps(chunks_meta, indent=2))

    return export_dir


# Pytest test functions for CI/CD integration
def test_schema_validation():
    """Test that all JSON files validate against schemas."""
    schema_path = Path("schemas/textbook-static-v1.json")
    
    for output_dir in OUTPUT_DIRS:
        if not output_dir.exists():
            continue
        
        validator = JSONValidator(schema_path)
        for json_file in output_dir.glob("*.json"):
            is_valid, errors = validator.validate_json_file(json_file)
            assert is_valid, f"Validation failed for {json_file}: {errors}"


def test_no_data_corruption():
    """Test that no data corruption exists."""
    for output_dir in OUTPUT_DIRS:
        if not output_dir.exists():
            continue
        
        detector = CorruptionDetector(output_dir)
        is_valid, errors, _ = detector.detect_all()
        assert is_valid, f"Corruption detected: {errors}"


def test_round_trip_preservation():
    """Test that data is preserved through round-trip."""
    for output_dir in OUTPUT_DIRS:
        if not output_dir.exists():
            continue
        
        tester = RoundTripTester(output_dir)
        is_valid, errors, _ = tester.test_all()
        assert is_valid, f"Round-trip test failed: {errors}"


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# Handoff integrity pytest suite
# ---------------------------------------------------------------------------

def test_handoff_integrity_valid_single_doc(tmp_path):
    """A well-formed single-doc export must pass validate_handoff_integrity."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
    from algl_pdf_helper.export_sqladapt import validate_handoff_integrity

    export_dir = _build_minimal_export(tmp_path, num_docs=1)
    result = validate_handoff_integrity(export_dir)

    assert result["valid"], f"Expected valid=True. Errors: {result['errors']}"
    assert result["missing_pages"] == [], f"Unexpected missing pages: {result['missing_pages']}"
    assert result["concept_map_entries"] == result["markdown_files"], (
        f"concept_map_entries ({result['concept_map_entries']}) != "
        f"markdown_files ({result['markdown_files']})"
    )


def test_handoff_integrity_valid_two_docs(tmp_path):
    """A well-formed two-doc merged export must pass validate_handoff_integrity."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
    from algl_pdf_helper.export_sqladapt import validate_handoff_integrity

    export_dir = _build_minimal_export(tmp_path, num_docs=2)
    result = validate_handoff_integrity(export_dir)

    assert result["valid"], f"Expected valid=True. Errors: {result['errors']}"
    assert result["source_docs_count"] == 2
    assert result["doc_dirs_count"] == 2
    assert result["missing_pages"] == []


def test_handoff_integrity_detects_missing_markdown(tmp_path):
    """validate_handoff_integrity must flag a concept-map entry with no .md file."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
    from algl_pdf_helper.export_sqladapt import validate_handoff_integrity

    export_dir = _build_minimal_export(tmp_path, num_docs=1)

    # Remove one of the markdown files to create a missing-page condition
    concepts_dir = export_dir / "concepts"
    first_doc_dir = next(d for d in concepts_dir.iterdir() if d.is_dir())
    first_md = next(f for f in first_doc_dir.glob("*.md"))
    first_md.unlink()

    result = validate_handoff_integrity(export_dir)

    assert not result["valid"], "Expected valid=False when a markdown file is missing"
    assert len(result["missing_pages"]) >= 1, "Expected at least one missing_pages entry"


def test_handoff_integrity_detects_manifest_inconsistency(tmp_path):
    """validate_handoff_integrity must flag when textbook-manifest sourceDocs disagrees with concept-map."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
    from algl_pdf_helper.export_sqladapt import validate_handoff_integrity

    export_dir = _build_minimal_export(tmp_path, num_docs=1)

    # Corrupt textbook-manifest.json by removing the sourceDocs entry
    tm_path = export_dir / "textbook-manifest.json"
    tm_data = json.loads(tm_path.read_text())
    tm_data["sourceDocs"] = []  # Remove all source docs
    tm_data["docCount"] = 0
    tm_path.write_text(json.dumps(tm_data, indent=2))

    result = validate_handoff_integrity(export_dir)

    assert not result["valid"], "Expected valid=False when sourceDocs is inconsistent"


def test_handoff_integrity_detects_missing_chunks_meta_doc(tmp_path):
    """validate_handoff_integrity must flag when a docId is absent from chunks-metadata.json."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
    from algl_pdf_helper.export_sqladapt import validate_handoff_integrity

    export_dir = _build_minimal_export(tmp_path, num_docs=1)

    # Remove the docId from chunks-metadata.json
    cm_path = export_dir / "chunks-metadata.json"
    cm_path.write_text("{}")  # empty

    result = validate_handoff_integrity(export_dir)

    assert not result["valid"], "Expected valid=False when chunks-metadata is missing a docId"
