from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# =============================================================================
# Schema Version Constants
# =============================================================================

TEXTBOOK_STATIC_VERSION = "1.0.0"
TEXTBOOK_STATIC_SCHEMA_ID = "textbook-static-v1"
CONCEPT_MANIFEST_VERSION = "concept-manifest-v1"
ASSET_MANIFEST_VERSION = "asset-manifest-v1"
CHUNKER_VERSION = "word-window-180-overlap-30-v1"
EMBEDDING_MODEL_ID = "hash-embedding-v1"

# Legacy schema versions for backward compatibility
PDF_INDEX_SCHEMA_V2 = "pdf-index-schema-v2"


# =============================================================================
# Asset Models
# =============================================================================

class AssetReference(BaseModel):
    """Reference to an extracted asset (image or table)."""
    id: str = Field(description="Unique asset identifier (e.g., img-p45-001)")
    type: Literal["image", "table"] = Field(description="Asset type")
    path: str = Field(description="Relative path from textbook-static root")
    pageNumber: int = Field(ge=1, description="Page number where asset appears")
    caption: str = Field(default="", description="Optional caption or description")
    width: int | None = Field(default=None, description="Width in pixels (for images)")
    height: int | None = Field(default=None, description="Height in pixels (for images)")
    extractedText: str = Field(default="", description="OCR'd text or table content")


class AssetManifest(BaseModel):
    """Manifest of extracted assets for a document."""
    schemaVersion: str = Field(default=ASSET_MANIFEST_VERSION)
    docId: str = Field(description="Document ID")
    createdAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    assets: list[AssetReference] = Field(default_factory=list)

    @field_validator("schemaVersion")
    @classmethod
    def validate_schema_version(cls, v: str) -> str:
        if v != ASSET_MANIFEST_VERSION:
            raise ValueError(f"schemaVersion must be '{ASSET_MANIFEST_VERSION}'")
        return v

    def get_assets_for_page(self, page: int) -> list[AssetReference]:
        """Get all assets for a specific page.
        
        Args:
            page: Page number (1-indexed)
            
        Returns:
            List of asset references for that page
        """
        return [asset for asset in self.assets if asset.pageNumber == page]

    def get_all_assets(self) -> list[AssetReference]:
        """Get all assets in the manifest.
        
        Returns:
            List of all asset references
        """
        return self.assets.copy()

    @property
    def images(self) -> list[AssetReference]:
        """Get all image assets.
        
        Returns:
            List of image asset references
        """
        return [asset for asset in self.assets if asset.type == "image"]

    @property
    def tables(self) -> list[AssetReference]:
        """Get all table assets.
        
        Returns:
            List of table asset references
        """
        return [asset for asset in self.assets if asset.type == "table"]


# =============================================================================
# Concept Models
# =============================================================================

class ConceptSection(BaseModel):
    """Sections within a concept (definition, examples, etc.)."""
    chunkIds: list[str] = Field(default_factory=list)
    pageNumbers: list[int] = Field(default_factory=list)


class ConceptInfo(BaseModel):
    """A single concept with metadata and chunk references."""
    id: str
    title: str
    definition: str = ""
    difficulty: str = "beginner"  # beginner, intermediate, advanced
    estimatedReadTime: int = 5  # minutes
    pageReferences: list[int] = Field(default_factory=list)
    sections: dict[str, ConceptSection] = Field(default_factory=dict)
    relatedConcepts: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    practiceProblemIds: list[str] = Field(default_factory=list)
    assetIds: list[str] = Field(default_factory=list)


class ConceptManifest(BaseModel):
    """Manifest of all concepts extracted from PDF(s)."""
    schemaVersion: str = Field(default=CONCEPT_MANIFEST_VERSION)
    sourceDocId: str = ""  # Primary document these concepts come from
    createdAt: str = ""
    conceptCount: int = 0
    concepts: dict[str, ConceptInfo] = Field(default_factory=dict)

    @field_validator("schemaVersion")
    @classmethod
    def validate_schema_version(cls, v: str) -> str:
        if v != CONCEPT_MANIFEST_VERSION:
            raise ValueError(f"schemaVersion must be '{CONCEPT_MANIFEST_VERSION}'")
        return v


class ConceptMapEntry(BaseModel):
    """Entry for concept-map.json (SQL-Adapt format)."""
    title: str
    definition: str
    difficulty: str = "beginner"
    pageNumbers: list[int] = Field(default_factory=list)
    chunkIds: dict[str, list[str]] = Field(default_factory=dict)
    relatedConcepts: list[str] = Field(default_factory=list)
    practiceProblemIds: list[str] = Field(default_factory=list)
    sourceDocId: str = ""
    provenance: dict[str, Any] = Field(default_factory=dict, description="Provenance information including chunks, pages, blocks, and extraction method")


class ConceptMap(BaseModel):
    """Concept map for SQL-Adapt integration."""
    version: str = Field(default="1.0.0")
    generatedAt: str = ""
    sourceDocIds: list[str] = Field(default_factory=list)
    concepts: dict[str, ConceptMapEntry] = Field(default_factory=dict)


# =============================================================================
# PDF Index Models (Legacy but still supported)
# =============================================================================

class PdfSourceDoc(BaseModel):
    docId: str
    filename: str
    sha256: str
    pageCount: int


class PdfIndexChunk(BaseModel):
    chunkId: str
    docId: str
    page: int = Field(ge=1, description="Page number (1-indexed, must be >= 1)")
    text: str
    embedding: list[float] | None = None


class PdfIndexDocument(BaseModel):
    indexId: str
    sourceName: str
    createdAt: str
    schemaVersion: str
    chunkerVersion: str
    embeddingModelId: str
    sourceDocs: list[PdfSourceDoc]
    docCount: int
    chunkCount: int
    chunks: list[PdfIndexChunk]


class PdfIndexManifest(BaseModel):
    indexId: str
    createdAt: str
    schemaVersion: str
    chunkerVersion: str
    embeddingModelId: str
    sourceDocs: list[PdfSourceDoc]
    docCount: int
    chunkCount: int


# =============================================================================
# Textbook Static Models (New Schema v1)
# =============================================================================

class TextbookStaticManifest(BaseModel):
    """
    Main manifest for textbook-static output (textbook-manifest.json).
    
    This is the primary schema that web apps should consume.
    """
    schemaVersion: str = Field(
        default=TEXTBOOK_STATIC_VERSION,
        description="Schema version (must be '1.0.0')"
    )
    schemaId: str = Field(
        default=TEXTBOOK_STATIC_SCHEMA_ID,
        description="Schema identifier (must be 'textbook-static-v1')"
    )
    indexId: str = Field(description="Unique index identifier")
    createdAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sourceName: str = Field(description="Human-readable source name")
    chunkerVersion: str = Field(default=CHUNKER_VERSION)
    embeddingModelId: str = Field(default=EMBEDDING_MODEL_ID)
    sourceDocs: list[PdfSourceDoc] = Field(default_factory=list)
    docCount: int = Field(default=0)
    chunkCount: int = Field(default=0)

    @field_validator("schemaVersion")
    @classmethod
    def validate_schema_version(cls, v: str) -> str:
        if v != TEXTBOOK_STATIC_VERSION:
            raise ValueError(f"schemaVersion must be '{TEXTBOOK_STATIC_VERSION}'")
        return v

    @field_validator("schemaId")
    @classmethod
    def validate_schema_id(cls, v: str) -> str:
        if v != TEXTBOOK_STATIC_SCHEMA_ID:
            raise ValueError(f"schemaId must be '{TEXTBOOK_STATIC_SCHEMA_ID}'")
        return v

    def to_json(self, output_path: Path) -> None:
        """Write manifest to JSON file."""
        output_path.write_text(self.model_dump_json(indent=2))

    @classmethod
    def from_json(cls, input_path: Path) -> "TextbookStaticManifest":
        """Load manifest from JSON file."""
        import json
        data = json.loads(input_path.read_text())
        return cls(**data)


class TextbookStaticOutput(BaseModel):
    """
    Complete textbook-static output structure.
    
    This model represents the entire output directory contents.
    """
    manifest: TextbookStaticManifest
    conceptMap: ConceptMap
    chunks: list[PdfIndexChunk]
    conceptManifest: ConceptManifest | None = None
    assetManifest: AssetManifest | None = None

    def validate_schema(self) -> list[str]:
        """
        Validate that all components conform to the schema.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Validate manifest
        if self.manifest.schemaId != TEXTBOOK_STATIC_SCHEMA_ID:
            errors.append(f"Invalid schemaId: {self.manifest.schemaId}")
        if self.manifest.schemaVersion != TEXTBOOK_STATIC_VERSION:
            errors.append(f"Invalid schemaVersion: {self.manifest.schemaVersion}")
        
        # Validate chunk count matches
        if len(self.chunks) != self.manifest.chunkCount:
            errors.append(
                f"Chunk count mismatch: manifest says {self.manifest.chunkCount}, "
                f"but found {len(self.chunks)} chunks"
            )
        
        # Validate all chunks reference valid docIds
        valid_doc_ids = {doc.docId for doc in self.manifest.sourceDocs}
        for chunk in self.chunks:
            if chunk.docId not in valid_doc_ids:
                errors.append(f"Chunk {chunk.chunkId} references unknown docId: {chunk.docId}")
        
        # Validate concept map has valid chunk references
        all_chunk_ids = {chunk.chunkId for chunk in self.chunks}
        for concept_id, entry in self.conceptMap.concepts.items():
            for section, chunk_ids in entry.chunkIds.items():
                for chunk_id in chunk_ids:
                    if chunk_id not in all_chunk_ids:
                        errors.append(
                            f"Concept {concept_id} section '{section}' references "
                            f"unknown chunk: {chunk_id}"
                        )
        
        return errors

    def is_valid(self) -> bool:
        """Check if the output passes all schema validations."""
        return len(self.validate_schema()) == 0


# =============================================================================
# Build Options
# =============================================================================

class IndexBuildOptions(BaseModel):
    """Options for building PDF index."""
    schemaVersion: str = Field(default=PDF_INDEX_SCHEMA_V2)
    chunkerVersion: str = Field(default=CHUNKER_VERSION)
    embeddingModelId: str = Field(default=EMBEDDING_MODEL_ID)
    chunkWords: int = Field(default=180, ge=20, le=2000)
    overlapWords: int = Field(default=30, ge=0, le=1999)
    embeddingDim: int = Field(default=24, ge=4, le=4096)

    def validate_pair(self) -> None:
        if self.overlapWords >= self.chunkWords:
            raise ValueError("overlapWords must be smaller than chunkWords")


class OutputConfig(BaseModel):
    """Configuration for output directory resolution."""
    output_dir: Path | None = Field(default=None, description="Explicit output directory")
    env_var_name: str = Field(default="SQL_ADAPT_PUBLIC_DIR", description="Environment variable name")
    
    def resolve(self) -> Path:
        """
        Resolve output directory from explicit path or environment variable.
        
        Priority:
        1. Explicit output_dir if provided
        2. SQL_ADAPT_PUBLIC_DIR/textbook-static if env var exists
        3. Raise error with helpful message
        
        Returns:
            Resolved Path object
            
        Raises:
            ValueError: If no valid output directory can be determined
        """
        import os
        
        # Option 1: Explicit output directory
        if self.output_dir is not None:
            return Path(self.output_dir)
        
        # Option 2: Environment variable
        env_dir = os.getenv(self.env_var_name)
        if env_dir:
            return Path(env_dir) / "textbook-static"
        
        # No valid output directory
        raise ValueError(
            f"No output directory specified.\n"
            f"\nPlease provide one of:\n"
            f"  1. CLI argument: --output-dir /path/to/output\n"
            f"  2. Environment variable: {self.env_var_name}=/path/to/web/public\n"
            f"\nExample:\n"
            f"  export {self.env_var_name}=/path/to/adaptive-instructional-artifacts/apps/web/public\n"
            f"  algl-pdf index ./my.pdf  # Output will be in $SQL_ADAPT_PUBLIC_DIR/textbook-static/"
        )
