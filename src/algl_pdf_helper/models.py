from __future__ import annotations

from pydantic import BaseModel, Field


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


class ConceptManifest(BaseModel):
    """Manifest of all concepts extracted from PDF(s)."""
    schemaVersion: str = Field(default="concept-manifest-v1")
    sourceDocId: str = ""  # Primary document these concepts come from
    createdAt: str = ""
    conceptCount: int = 0
    concepts: dict[str, ConceptInfo] = Field(default_factory=dict)


class ConceptMapEntry(BaseModel):
    """Entry for concept-map.json (SQL-Adapt format)."""
    title: str
    definition: str
    difficulty: str = "beginner"
    pageNumbers: list[int] = Field(default_factory=list)
    chunkIds: dict[str, list[str]] = Field(default_factory=dict)
    relatedConcepts: list[str] = Field(default_factory=list)
    practiceProblemIds: list[str] = Field(default_factory=list)


class ConceptMap(BaseModel):
    """Concept map for SQL-Adapt integration."""
    version: str = Field(default="1.0.0")
    generatedAt: str = ""
    sourceDocId: str = ""
    concepts: dict[str, ConceptMapEntry] = Field(default_factory=dict)


class PdfSourceDoc(BaseModel):
    docId: str
    filename: str
    sha256: str
    pageCount: int


class PdfIndexChunk(BaseModel):
    chunkId: str
    docId: str
    page: int
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


class IndexBuildOptions(BaseModel):
    schemaVersion: str = Field(default="pdf-index-schema-v2")
    chunkerVersion: str = Field(default="word-window-180-overlap-30-v1")
    embeddingModelId: str = Field(default="hash-embedding-v1")
    chunkWords: int = Field(default=180, ge=20, le=2000)
    overlapWords: int = Field(default=30, ge=0, le=1999)
    embeddingDim: int = Field(default=24, ge=4, le=4096)

    def validate_pair(self) -> None:
        if self.overlapWords >= self.chunkWords:
            raise ValueError("overlapWords must be smaller than chunkWords")
