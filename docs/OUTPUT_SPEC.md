# Textbook Static Output Specification

**Version:** 1.0.0  
**Schema ID:** `textbook-static-v1`  
**Status:** Stable

This document defines the complete contract between the ALGL PDF Helper and the SQL-Adapt web application.

## Overview

The `textbook-static-v1` specification ensures that PDF processing output is predictable, versioned, and consumable by the web app without any path or configuration edits on a fresh clone.

## Schema Versioning

| Schema ID | Version | Status | Description |
|-----------|---------|--------|-------------|
| `textbook-static-v1` | 1.0.0 | **Stable** | Initial release with concept mapping, chunks, and assets |

### Compatibility Promise

- **Minor versions** (1.0.x): Fully backward compatible, bug fixes only
- **Major versions** (1.x.0): May add optional fields, maintain backward compatibility
- **Breaking changes** (2.0.0): Requires migration guide and version detection

## Environment Configuration

The output directory is determined by (in order of precedence):

1. **CLI argument:** `--output-dir /path/to/output`
2. **Environment variable:** `SQL_ADAPT_PUBLIC_DIR` → `{SQL_ADAPT_PUBLIC_DIR}/textbook-static`
3. **Error:** If neither is provided, CLI exits with helpful message

```bash
# Option 1: CLI argument
algl-pdf index ./my.pdf --output-dir ./textbook-static

# Option 2: Environment variable
export SQL_ADAPT_PUBLIC_DIR=/path/to/adaptive-instructional-artifacts/apps/web/public
algl-pdf index ./my.pdf  # Output: /path/to/.../public/textbook-static
```

## Folder Structure

```
textbook-static/                          # Root output directory
├── textbook-manifest.json                  # Main manifest (metadata, versions)
├── concept-map.json                        # Web app concept index
├── chunks.json                             # All chunks with embeddings
├── concept-manifest.json                   # Internal concept metadata (optional)
├── chunks-metadata.json                    # Per-doc chunk stats (optional)
├── assets/
│   ├── asset-manifest.json                 # Asset metadata
│   ├── images/
│   │   └── {docId}/                        # Images per document
│   │       ├── img-p45-001.png
│   │       └── img-p46-002.png
│   └── tables/
│       └── {docId}/                        # Tables per document
│           ├── table-p45-001.csv
│           └── table-p45-002.md
└── concepts/
    ├── README.md                           # Auto-generated concept index
    ├── {docId}/                            # Namespaced by document
    │   ├── {concept-id}.md                 # Individual concept content
    │   └── README.md                       # Doc-specific concept index
    └── shared/                             # Cross-document concepts (optional)
```

## JSON Schema Files

### 1. textbook-manifest.json

Main index manifest with schema version and source document metadata.

```json
{
  "schemaVersion": "1.0.0",
  "schemaId": "textbook-static-v1",
  "indexId": "idx-abc123def456",
  "createdAt": "2024-01-15T10:30:00Z",
  "sourceName": "SQL Course Textbook",
  "chunkerVersion": "word-window-180-overlap-30-v1",
  "embeddingModelId": "hash-embedding-v1",
  "sourceDocs": [
    {
      "docId": "sql-textbook",
      "filename": "SQL_Course_Textbook.pdf",
      "sha256": "a1b2c3d4e5f6...",
      "pageCount": 350
    }
  ],
  "docCount": 1,
  "chunkCount": 1250
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schemaVersion` | string | Yes | Must be `"1.0.0"` |
| `schemaId` | string | Yes | Must be `"textbook-static-v1"` |
| `indexId` | string | Yes | Unique index identifier |
| `createdAt` | ISO8601 | Yes | Timestamp of generation |
| `sourceName` | string | Yes | Human-readable source name |
| `chunkerVersion` | string | Yes | Chunker algorithm version |
| `embeddingModelId` | string | Yes | Embedding model identifier |
| `sourceDocs` | array | Yes | Source document metadata |
| `docCount` | integer | Yes | Number of documents |
| `chunkCount` | integer | Yes | Total chunk count |

### 2. concept-map.json

Web app consumable concept index with chunk mappings.

```json
{
  "version": "1.0.0",
  "generatedAt": "2024-01-15T10:30:00Z",
  "sourceDocIds": ["sql-textbook"],
  "concepts": {
    "sql-textbook/select-basic": {
      "title": "SELECT Statement Basics",
      "definition": "Retrieves data from one or more tables",
      "difficulty": "beginner",
      "pageNumbers": [45, 46],
      "chunkIds": {
        "definition": ["sql-textbook:p45:c1"],
        "examples": ["sql-textbook:p45:c2", "sql-textbook:p46:c1"]
      },
      "relatedConcepts": ["sql-textbook/where-clause", "sql-textbook/order-by"],
      "practiceProblemIds": ["sql-select-01", "sql-select-02"],
      "sourceDocId": "sql-textbook"
    }
  }
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | Yes | Must be `"1.0.0"` |
| `generatedAt` | ISO8601 | Yes | Timestamp |
| `sourceDocIds` | array | Yes | Source document IDs |
| `concepts` | object | Yes | Concept ID → ConceptMapEntry |

**ConceptMapEntry:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | Concept title |
| `definition` | string | Yes | Brief definition |
| `difficulty` | string | No | `beginner`/`intermediate`/`advanced` |
| `pageNumbers` | array | No | Page numbers |
| `chunkIds` | object | No | Section → chunk IDs mapping |
| `relatedConcepts` | array | No | Related concept IDs (namespaced) |
| `practiceProblemIds` | array | No | Linked practice problems |
| `sourceDocId` | string | No | Source document |

### 3. chunks.json

All text chunks with embeddings for semantic search.

```json
[
  {
    "chunkId": "sql-textbook:p45:c1",
    "docId": "sql-textbook",
    "page": 45,
    "text": "The SELECT statement is the most commonly used SQL command...",
    "embedding": [0.123, -0.456, 0.789, ...]
  }
]
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `chunkId` | string | Yes | Unique ID: `{docId}:p{page}:c{index}` |
| `docId` | string | Yes | Document ID |
| `page` | integer | Yes | Page number |
| `text` | string | Yes | Text content |
| `embedding` | array | No | Vector embedding (24-dim default) |

### 4. concept-manifest.json (Optional)

Internal concept metadata with section breakdowns.

```json
{
  "schemaVersion": "concept-manifest-v1",
  "sourceDocId": "sql-textbook",
  "createdAt": "2024-01-15T10:30:00Z",
  "conceptCount": 42,
  "concepts": {
    "select-basic": {
      "id": "select-basic",
      "title": "SELECT Statement Basics",
      "definition": "Retrieves data from one or more tables",
      "difficulty": "beginner",
      "estimatedReadTime": 5,
      "pageReferences": [45, 46],
      "sections": {
        "definition": {
          "chunkIds": ["sql-textbook:p45:c1"],
          "pageNumbers": [45]
        },
        "examples": {
          "chunkIds": ["sql-textbook:p45:c2", "sql-textbook:p46:c1"],
          "pageNumbers": [45, 46]
        }
      },
      "relatedConcepts": ["where-clause", "order-by"],
      "tags": ["sql", "query", "dql"],
      "practiceProblemIds": [],
      "assetIds": []
    }
  }
}
```

### 5. asset-manifest.json (Optional)

Asset metadata for images and tables.

```json
{
  "schemaVersion": "asset-manifest-v1",
  "docId": "sql-textbook",
  "createdAt": "2024-01-15T10:30:00Z",
  "assets": [
    {
      "id": "img-p45-001",
      "type": "image",
      "path": "assets/images/sql-textbook/img-p45-001.png",
      "pageNumber": 45,
      "caption": "Figure 3.1: SELECT statement syntax",
      "width": 800,
      "height": 600,
      "extractedText": "SELECT column1, column2 FROM table_name"
    },
    {
      "id": "table-p45-001",
      "type": "table",
      "path": "assets/tables/sql-textbook/table-p45-001.csv",
      "pageNumber": 45,
      "caption": "Table 3.1: Sample data",
      "extractedText": "id,name,age\n1,Alice,30\n2,Bob,25"
    }
  ]
}
```

## Markdown Frontmatter Schema

Concept markdown files use YAML frontmatter:

```yaml
---
id: select-basic
title: SELECT Statement Basics
definition: Retrieves data from one or more tables
difficulty: beginner
estimatedReadTime: 5
pageReferences: [45, 46]
chunkIds:
  - sql-textbook:p45:c1
  - sql-textbook:p45:c2
relatedConcepts:
  - where-clause
  - order-by
tags:
  - sql
  - query
  - dql
sourceDocId: sql-textbook
---
```

**Frontmatter Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Concept ID |
| `title` | string | Yes | Concept title |
| `definition` | string | No | Brief definition |
| `difficulty` | enum | No | `beginner`/`intermediate`/`advanced` |
| `estimatedReadTime` | integer | No | Minutes |
| `pageReferences` | array | No | Page numbers |
| `chunkIds` | array | No | Chunk IDs |
| `relatedConcepts` | array | No | Related concept IDs |
| `tags` | array | No | Tags |
| `sourceDocId` | string | No | Source document |

## Chunk ID Format

Chunk IDs follow the pattern: `{docId}:p{page}:c{index}`

Examples:
- `sql-textbook:p45:c1` - Document "sql-textbook", page 45, chunk 1
- `doc-a1b2c3d4:p100:c5` - SHA-based doc ID, page 100, chunk 5

## Migration Guide

### From Pre-v1 to v1.0.0

1. **Rename `manifest.json` → `textbook-manifest.json`**
2. **Add `schemaId` field** with value `"textbook-static-v1"`
3. **Update `schemaVersion`** to `"1.0.0"` (was `"pdf-index-schema-v2"`)
4. **Move concepts to namespaced structure** `concepts/{docId}/{concept-id}.md`
5. **Remove hardcoded paths** from all configuration

### Version Detection

Web apps should check `schemaId` before consuming:

```typescript
const manifest = await fetch('/textbook-static/textbook-manifest.json').then(r => r.json());

if (manifest.schemaId !== 'textbook-static-v1') {
  console.warn(`Unknown schema: ${manifest.schemaId}`);
  // Handle migration or show error
}
```

## Validation

Use the JSON Schema for validation:

```bash
# Validate manifest
python -c "import json; from jsonschema import validate; ..."

# Or using CLI (future feature)
algl-pdf validate ./textbook-static
```

## Changes Log

### 1.0.0 (2024-01-15)
- Initial stable release
- Defined textbook-manifest.json schema
- Defined concept-map.json schema
- Standardized chunk ID format
- Added asset manifest support
- Removed all hardcoded output paths
