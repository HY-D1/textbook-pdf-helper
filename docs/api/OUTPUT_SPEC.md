# Textbook Static Output Specification

**Version:** 2.0.0  
**Schema ID:** `textbook-static-v2`  
**Status:** Draft

---

## Overview

This document defines the complete contract between the Adaptive Textbook Helper and the SQL-Adapt web application. It specifies the four-pack output structure: Document Pack, Domain Pack, Trace Pack, and Policy Pack.

The specification ensures that PDF processing output is:
- **Content-addressed**: Immutable, hash-based identifiers
- **Versioned**: Schema versions for compatibility
- **Auditable**: Complete provenance chain
- **Reproducible**: Deterministic processing with logged parameters

---

## Schema Versioning

| Schema ID | Version | Status | Description |
|-----------|---------|--------|-------------|
| `textbook-static-v2` | 2.0.0 | **Draft** | Four-pack architecture with prerequisite DAG |
| `textbook-static-v1` | 1.0.0 | Stable | Legacy format |

### Compatibility Promise

- **Minor versions** (2.0.x): Fully backward compatible, bug fixes only
- **Major versions** (2.x.0): May add optional fields, maintain backward compatibility
- **Breaking changes** (3.0.0): Requires migration guide

---

## Four-Pack Structure

### Document Pack

Immutable artifacts derived from source PDFs.

```
document-pack/
├── raw/
│   └── {doc_alias}/
│       └── source.pdf                    # SHA256: {source_hash}
├── derived/
│   └── {doc_alias}/
│       ├── ocr.pdf                       # OCR output (if applied)
│       ├── pages/
│       │   └── {page}.txt                # Per-page extraction
│       └── layout.json                   # Structure metadata
└── index/
    └── {doc_alias}/
        ├── chunks.jsonl                  # Chunked content
        ├── embeddings.jsonl              # Hash embeddings
        └── index.faiss                   # Vector index
```

### Domain Pack

Knowledge graph with concepts and prerequisites.

```
domain-pack/
├── concepts/
│   ├── concept-map.json                  # Concept nodes
│   └── concept-definitions.yaml          # Human definitions
├── prerequisites/
│   └── prereq-dag.json                   # Prerequisite edges
└── errors/
    └── error-taxonomy.json               # Error → concept mappings
```

### Trace Pack

Event logging and derived metrics infrastructure.

```
trace-pack/
├── events/
│   └── schemas/                          # Event JSON schemas
├── derived/
│   ├── hdi-calculator.json               # Hint Dependency Index
│   ├── csi-calculator.json               # Cognitive Strain Index
│   ├── aps-calculator.json               # Affective Proxy Score
│   └── rqs-calculator.json               # Reflection Quality Score
└── manifests/
    └── run-manifest-schema.json          # Run manifest schema
```

### Policy Pack

Escalation rules and adaptive policy configuration.

```
policy-pack/
├── profiles/
│   ├── fast-escalator.json
│   ├── slow-escalator.json
│   ├── explanation-first.json
│   └── adaptive-bandit.json
├── thresholds/
│   └── escalation-ladder.yaml
└── bandit/
    ├── arm-configs.json
    └── reward-function.json
```

---

## JSON Schema Files

### 1. textbook-manifest.json

Main index with schema version and pack metadata.

```json
{
  "schemaVersion": "2.0.0",
  "schemaId": "textbook-static-v2",
  "indexId": "idx-abc123def456",
  "createdAt": "2024-01-15T10:30:00Z",
  "sourceName": "SQL Course Textbook",
  "chunkerVersion": "word-window-150-overlap-30-v1",
  "embeddingModelId": "hash-embedding-v1",
  "provenance": {
    "codeVersion": "git:abc123",
    "configHash": "sha256:def456",
    "runId": "run-789"
  },
  "packs": {
    "document": {
      "path": "document-pack",
      "artifactCount": 1252
    },
    "domain": {
      "path": "domain-pack",
      "conceptCount": 42,
      "prereqEdgeCount": 38
    },
    "trace": {
      "path": "trace-pack",
      "eventSchemas": ["attempt_submitted", "hint_shown", "escalation_decision"]
    },
    "policy": {
      "path": "policy-pack",
      "profileCount": 4
    }
  },
  "sourceDocs": [
    {
      "docId": "sql-textbook",
      "filename": "SQL_Course_Textbook.pdf",
      "sha256": "a1b2c3d4e5f6...",
      "pageCount": 350
    }
  ]
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schemaVersion` | string | Yes | Must be `"2.0.0"` |
| `schemaId` | string | Yes | Must be `"textbook-static-v2"` |
| `indexId` | string | Yes | Unique index identifier |
| `createdAt` | ISO8601 | Yes | Timestamp of generation |
| `provenance` | object | Yes | Code version, config hash, run ID |
| `packs` | object | Yes | Four-pack structure metadata |
| `sourceDocs` | array | Yes | Source document metadata |

### 2. concept-map.json

Web app consumable concept index.

```json
{
  "version": "2.0.0",
  "schemaId": "concept-map-v2",
  "generatedAt": "2024-01-15T10:30:00Z",
  "sourceDocIds": ["sql-textbook"],
  "concepts": {
    "sql-textbook/select-basic": {
      "id": "select-basic",
      "canonicalName": "sql.select.basic",
      "title": "SELECT Statement Basics",
      "definition": "Retrieves data from one or more tables",
      "difficulty": "beginner",
      "estimatedReadTime": 5,
      "pageNumbers": [45, 46],
      "chunkIds": {
        "definition": ["sql-textbook:p45:c1"],
        "examples": ["sql-textbook:p45:c2", "sql-textbook:p46:c1"]
      },
      "relatedConcepts": ["sql-textbook/where-clause"],
      "prerequisites": [],
      "teaches": ["sql.dql.basic"],
      "evidence": {
        "sourceChunks": ["sql-textbook:p45:c1"],
        "validatedBy": "human-reviewer-001",
        "validationDate": "2024-01-15T09:10:00Z"
      },
      "practiceProblemIds": ["sql-select-01"]
    }
  }
}
```

**ConceptMapEntry Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Concept ID |
| `canonicalName` | string | Yes | Global concept identifier |
| `title` | string | Yes | Human-readable title |
| `definition` | string | Yes | Brief definition |
| `difficulty` | enum | Yes | `beginner`/`intermediate`/`advanced` |
| `prerequisites` | array | Yes | Prerequisite concept IDs |
| `teaches` | array | Yes | Concepts this teaches |
| `evidence` | object | Yes | Validation metadata |

### 3. prereq-dag.json (NEW)

Prerequisite directed acyclic graph.

```json
{
  "schemaVersion": "1.0.0",
  "schemaId": "prereq-dag-v1",
  "generatedAt": "2024-01-15T10:30:00Z",
  "dagId": "dag-sql-textbook-v1",
  "version": "1.0.0",
  "lastModified": "2024-01-15T09:10:00Z",
  "modifiedBy": "human-reviewer-001",
  "provenance": {
    "autoSuggested": true,
    "humanValidated": true,
    "validationDate": "2024-01-15T09:10:00Z"
  },
  "nodes": ["select-basic", "where-clause", "order-by", "group-by"],
  "edges": [
    {
      "from": "select-basic",
      "to": "where-clause",
      "type": "prerequisite",
      "confidence": 1.0,
      "validated": true,
      "validationMethod": "manual_review"
    },
    {
      "from": "select-basic",
      "to": "order-by",
      "type": "prerequisite",
      "confidence": 1.0,
      "validated": true
    },
    {
      "from": "where-clause",
      "to": "group-by",
      "type": "prerequisite",
      "confidence": 0.85,
      "validated": true
    }
  ],
  "metadata": {
    "nodeCount": 4,
    "edgeCount": 3,
    "depth": 2,
    "rootNodes": ["select-basic"]
  }
}
```

**PrereqEdge Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `from` | string | Yes | Prerequisite concept ID |
| `to` | string | Yes | Target concept ID |
| `type` | string | Yes | Edge type (e.g., `prerequisite`) |
| `confidence` | float | Yes | Confidence score (0-1) |
| `validated` | boolean | Yes | Human validation status |

### 4. chunks.json

All text chunks with embeddings.

```json
[
  {
    "chunkId": "sql-textbook:p45:c1",
    "docId": "sql-textbook",
    "page": 45,
    "pageRange": [45, 45],
    "charSpan": [0, 850],
    "tokenCount": 150,
    "text": "The SELECT statement is the most commonly used SQL command...",
    "embedding": [0.123, -0.456, 0.789, ...],
    "embeddingModel": "hash-embedding-v1",
    "provenance": {
      "extractionMethod": "pymupdf",
      "cleaningApplied": ["header_removal", "whitespace_normalize"]
    }
  }
]
```

### 5. concept-manifest.json

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
      "prerequisites": [],
      "tags": ["sql", "query", "dql"]
    }
  }
}
```

### 6. escalation-ladder.yaml (NEW)

Policy configuration for adaptive support.

```yaml
schemaVersion: "1.0.0"
schemaId: "escalation-ladder-v1"
policyId: "ladder-default-v1"

levels:
  - name: "hint_level_1"
    displayName: "Nudge"
    description: "Subtle hint pointing toward solution"
    escalationTriggers:
      - type: "error_count"
        threshold: 3
        window: "problem"
      - type: "time_in_level_ms"
        threshold: 180000
    
  - name: "hint_level_2"
    displayName: "Directed Hint"
    description: "More specific guidance"
    escalationTriggers:
      - type: "error_count"
        threshold: 5
      - type: "time_in_level_ms"
        threshold: 300000
    
  - name: "explanation"
    displayName: "Explanation"
    description: "Concept explanation with examples"
    escalationTriggers:
      - type: "error_count"
        threshold: 7
      - type: "prereq_violation_detected"
        immediate: true
    
  - name: "worked_example"
    displayName: "Worked Example"
    description: "Step-by-step solution walkthrough"

safetyOverrides:
  - trigger: "repeated_prereq_failure"
    action: "jump_to_explanation"
    bypassLevels: ["hint_level_1", "hint_level_2"]
  
  - trigger: "learner_explicit_request"
    action: "escalate_one_level"

profiles:
  fastEscalator:
    multiplier: 0.5  # 50% of default thresholds
  slowEscalator:
    multiplier: 1.5  # 150% of default thresholds
  explanationFirst:
    override: "explanation"
    conditions: ["prereq_violation_detected"]
```

### 7. event-schema/attempt_submitted.json (NEW)

JSON Schema for event validation.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "schemaId": "event-attempt-submitted-v1",
  "title": "Attempt Submitted Event",
  "type": "object",
  "required": ["event_type", "timestamp", "trace_id", "payload"],
  "properties": {
    "event_type": {
      "type": "string",
      "enum": ["attempt_submitted"]
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    },
    "trace_id": {
      "type": "string",
      "format": "uuid"
    },
    "span_id": {
      "type": "string",
      "format": "uuid"
    },
    "run_id": {
      "type": "string"
    },
    "experiment_id": {
      "type": "string"
    },
    "policy_id": {
      "type": "string"
    },
    "learner_id_pseudonymous": {
      "type": "string"
    },
    "session_id": {
      "type": "string"
    },
    "code_version": {
      "type": "string",
      "pattern": "^git:[a-f0-9]+$"
    },
    "config_hash": {
      "type": "string",
      "pattern": "^sha256:[a-f0-9]+$"
    },
    "payload": {
      "type": "object",
      "required": ["problem_id", "code", "attempt_id"],
      "properties": {
        "problem_id": { "type": "string" },
        "code": { "type": "string" },
        "language": { "type": "string", "enum": ["sql"] },
        "attempt_id": { "type": "string" },
        "time_since_start_ms": { "type": "integer" },
        "keystroke_count": { "type": "integer" }
      }
    }
  }
}
```

---

## Markdown Frontmatter Schema

### Concept Markdown Files

```yaml
---
id: select-basic
canonicalName: sql.select.basic
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
prerequisites: []
teaches:
  - sql.dql.basic
tags:
  - sql
  - query
  - dql
sourceDocId: sql-textbook
evidence:
  sourceChunks: [sql-textbook:p45:c1]
  validatedBy: human-reviewer-001
  validationDate: "2024-01-15T09:10:00Z"
provenance:
  generatedAt: "2024-01-15T10:30:00Z"
  generationMethod: llm_retrieval_augmented
  promptTemplate: worked-example-v1.2
---
```

**Frontmatter Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Concept ID |
| `canonicalName` | string | Yes | Global identifier |
| `title` | string | Yes | Human-readable title |
| `prerequisites` | array | Yes | Prerequisite concept IDs |
| `teaches` | array | Yes | Concepts this teaches |
| `evidence` | object | Yes | Validation metadata |
| `provenance` | object | Yes | Generation metadata |

---

## Chunk ID Format

Chunk IDs follow the pattern: `{docId}:p{page}:c{index}`

Examples:
- `sql-textbook:p45:c1` - Document "sql-textbook", page 45, chunk 1
- `doc-a1b2c3d4:p100:c5` - SHA-based doc ID, page 100, chunk 5

---

## Migration Guide

### From v1.0.0 to v2.0.0

1. **Add prerequisite DAG**
   - Create `prereq-dag.json` from existing concept relationships
   - Add `prerequisites` field to all concepts

2. **Add provenance metadata**
   - Add `provenance` object to manifest
   - Include `codeVersion`, `configHash`, `runId`

3. **Update concept schema**
   - Add `canonicalName` field
   - Add `evidence` object with validation metadata

4. **Add four-pack structure**
   - Organize outputs into document/domain/trace/policy packs
   - Update paths in manifest

---

## Validation

### JSON Schema Validation

```python
import json
from jsonschema import validate

# Load schema
with open('schemas/textbook-manifest-v2.json') as f:
    schema = json.load(f)

# Load manifest
with open('textbook-manifest.json') as f:
    manifest = json.load(f)

# Validate
validate(instance=manifest, schema=schema)
```

### CLI Validation

```bash
# Validate all outputs
algl-pdf validate ./textbook-static

# Validate specific pack
algl-pdf validate ./textbook-static --pack domain

# Check provenance completeness
algl-pdf validate ./textbook-static --check-provenance
```

---

## Changes Log

### 2.0.0 (2024-03-03)
- Added four-pack architecture
- Added prerequisite DAG schema
- Added provenance metadata
- Added policy pack specification
- Added event schema definitions

### 1.0.0 (2024-01-15)
- Initial stable release
- Basic concept mapping
- Chunk and embedding output

---

*This document defines the output specification for the Adaptive Textbook Helper.*
