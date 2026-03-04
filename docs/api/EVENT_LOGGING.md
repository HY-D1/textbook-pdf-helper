# Event Logging Specification

**Version:** 1.0.0  
**Status:** Draft  
**Last Updated:** 2026-03-03  

---

## Overview

This document defines the complete event logging architecture for the Adaptive Textbook Helper, aligned with established learning analytics standards (xAPI, Caliper) and provenance models (PROV-DM).

### Design Goals

1. **Complete Observability**: Every significant action is logged
2. **Reproducibility**: Logs enable counterfactual replay and evaluation
3. **Interoperability**: Aligns with xAPI, Caliper, and PROV standards
4. **Correlation**: OpenTelemetry-style trace correlation across components
5. **Auditability**: Full provenance chain from raw PDF to generated content

---

## Event Model Alignment

### xAPI (Experience API)

Events follow the xAPI statement structure:

```json
{
  "actor": {"mbox": "mailto:learner@example.com"},
  "verb": {"id": "http://adlnet.gov/expapi/verbs/attempted"},
  "object": {"id": "http://example.com/problems/sql-select-01"},
  "result": {"success": false, "response": "SELECT * FORM users"},
  "context": {"contextActivities": {...}},
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Caliper

Events align with Caliper's actor-action-object-time model:

```json
{
  "@context": "http://purl.imsglobal.org/ctx/caliper/v1p2",
  "type": "AssessmentEvent",
  "actor": {"type": "Person", "id": "learner-123"},
  "action": "Submitted",
  "object": {"type": "Assessment", "id": "problem-456"},
  "eventTime": "2024-01-15T10:30:00Z"
}
```

### PROV-DM (Provenance)

Artifacts are modeled as PROV entities:

```
entity(chunk:p45:c1)
entity(concept:select-basic)
activity(generate_content, 2024-01-15T10:00:00Z, 2024-01-15T10:01:00Z)
wasGeneratedBy(concept:select-basic, generate_content, 2024-01-15T10:01:00Z)
used(generate_content, chunk:p45:c1)
```

---

## Event Taxonomy

### 1. Interaction Events

#### `attempt_submitted`

Learner submits a solution attempt.

```json
{
  "event_type": "attempt_submitted",
  "timestamp": "2024-01-15T10:30:00Z",
  "trace_id": "trace-abc123",
  "span_id": "span-def456",
  "learner_id_pseudonymous": "sha256:learner789",
  "session_id": "session-xyz",
  "problem_id": "sql-select-01",
  "attempt_id": "attempt-3",
  "payload": {
    "code": "SELECT * FROM users WHERE age > 18",
    "language": "sql",
    "time_since_start_ms": 45000,
    "keystroke_count": 127,
    "paste_events": 0
  }
}
```

**Required Fields:**
- `problem_id`: Problem identifier
- `code`: Submitted code
- `attempt_id`: Sequence number for this problem

#### `attempt_result`

Auto-grading result for an attempt.

```json
{
  "event_type": "attempt_result",
  "timestamp": "2024-01-15T10:30:01Z",
  "trace_id": "trace-abc123",
  "payload": {
    "problem_id": "sql-select-01",
    "attempt_id": "attempt-3",
    "correct": false,
    "error_subtype": "SYNTAX_ERROR",
    "error_message": "Unexpected token 'FORM'",
    "concept_ids": ["sql.select.basic", "sql.syntax.keywords"],
    "prereq_violation": false,
    "execution_time_ms": 150
  }
}
```

#### `error_classified`

Error mapped to taxonomy.

```json
{
  "event_type": "error_classified",
  "timestamp": "2024-01-15T10:30:01Z",
  "payload": {
    "error_subtype": "KEYWORD_MISSPELLING",
    "error_category": "SYNTAX",
    "mapped_concepts": ["sql.select.basic"],
    "confidence": 0.92,
    "classifier_version": "v1.2.0"
  }
}
```

#### `hint_requested`

Learner requests a hint.

```json
{
  "event_type": "hint_requested",
  "timestamp": "2024-01-15T10:32:00Z",
  "payload": {
    "problem_id": "sql-select-01",
    "attempt_id": "attempt-3",
    "hint_level_requested": null,
    "trigger_reason": "learner_initiated",
    "time_since_error_ms": 120000
  }
}
```

#### `hint_shown`

Hint is displayed to learner.

```json
{
  "event_type": "hint_shown",
  "timestamp": "2024-01-15T10:32:01Z",
  "payload": {
    "hint_id": "hint-456",
    "hint_level": 1,
    "content_id": "content-nudge-789",
    "source_chunk_ids": ["sql-textbook:p45:c2"],
    "rule_triggered": "syntax_error_nudge",
    "policy_id": "policy-slow-escalator-v1"
  }
}
```

#### `escalation_decision`

Support level escalation decision.

```json
{
  "event_type": "escalation_decision",
  "timestamp": "2024-01-15T10:35:00Z",
  "payload": {
    "problem_id": "sql-select-01",
    "attempt_id": "attempt-3",
    "from_level": "hint",
    "to_level": "explanation",
    "trigger_reason": "repeated_error_threshold",
    "trigger_details": {
      "error_count": 3,
      "error_persistence": true,
      "time_in_level_ms": 180000
    },
    "profile_id": "slow-escalator",
    "thresholds_applied": {
      "max_errors_before_escalation": 3,
      "max_time_in_level_ms": 300000
    },
    "safety_override": false
  }
}
```

**Escalation Triggers (Enum):**
- `repeated_error_threshold`: Too many errors of same type
- `time_in_level_exceeded`: Too long at current level
- `prereq_violation_detected`: Missing prerequisite knowledge
- `learner_explicit_request`: Learner asked for more help
- `bandit_selection`: Bandit algorithm selected escalation
- `safety_constraint`: Hard rule override

#### `explanation_generated`

LLM generates explanation.

```json
{
  "event_type": "explanation_generated",
  "timestamp": "2024-01-15T10:35:01Z",
  "payload": {
    "explanation_id": "exp-789",
    "explanation_type": "worked_example",
    "target_concept_ids": ["sql.select.basic"],
    "retrieved_chunk_ids": ["sql-textbook:p45:c1", "sql-textbook:p45:c2"],
    "prompt_template_id": "worked-example-v1.2",
    "llm_model_id": "kimi-k2-0711-longcontext",
    "llm_config": {
      "temperature": 0.3,
      "max_tokens": 2048,
      "top_p": 0.9
    },
    "generation_time_ms": 2500,
    "output_hash": "sha256:output123",
    "quality_gate_passed": true
  }
}
```

#### `explanation_shown`

Explanation displayed to learner.

```json
{
  "event_type": "explanation_shown",
  "timestamp": "2024-01-15T10:35:02Z",
  "payload": {
    "explanation_id": "exp-789",
    "display_format": "markdown",
    "citation_links_visible": true,
    "source_chunks_clickable": true,
    "time_spent_reading_ms": null
  }
}
```

#### `note_saved`

Learner saves a note.

```json
{
  "event_type": "note_saved",
  "timestamp": "2024-01-15T10:40:00Z",
  "payload": {
    "note_id": "note-abc",
    "note_type": "self_explanation",
    "content_hash": "sha256:note456",
    "content_preview": "The SELECT statement retrieves data from tables...",
    "concept_references": ["sql.select.basic"],
    "source_explanation_id": "exp-789",
    "edit_time_ms": 120000
  }
}
```

#### `problem_completed`

Problem finished (success or abandonment).

```json
{
  "event_type": "problem_completed",
  "timestamp": "2024-01-15T10:45:00Z",
  "payload": {
    "problem_id": "sql-select-01",
    "completion_status": "solved",  // or "abandoned", "timeout"
    "final_attempt_id": "attempt-5",
    "total_time_ms": 900000,
    "total_attempts": 5,
    "hint_count": 2,
    "escalation_count": 1,
    "explanation_count": 1,
    "note_count": 1,
    "final_error_subtype": null,
    "concepts_demonstrated": ["sql.select.basic"]
  }
}
```

### 2. Pipeline Events

#### `pdf_ingest_started`

```json
{
  "event_type": "pdf_ingest_started",
  "timestamp": "2024-01-15T09:00:00Z",
  "run_id": "run-pdf-123",
  "payload": {
    "doc_id": "sql-textbook",
    "source_path": "raw/sql-textbook/source.pdf",
    "source_hash": "sha256:pdf789",
    "ocr_required": false,
    "code_version": "git:abc123"
  }
}
```

#### `page_text_extracted`

```json
{
  "event_type": "page_text_extracted",
  "timestamp": "2024-01-15T09:00:10Z",
  "run_id": "run-pdf-123",
  "payload": {
    "doc_id": "sql-textbook",
    "page": 45,
    "extraction_method": "pymupdf",
    "char_count": 2450,
    "quality_score": 0.95,
    "flags": ["has_code_blocks", "has_tables"]
  }
}
```

#### `chunk_created`

```json
{
  "event_type": "chunk_created",
  "timestamp": "2024-01-15T09:01:00Z",
  "run_id": "run-pdf-123",
  "payload": {
    "chunk_id": "sql-textbook:p45:c1",
    "doc_id": "sql-textbook",
    "page_range": [45, 45],
    "char_span": [0, 850],
    "token_count": 150,
    "embedding_model": "hash-embedding-v1",
    "embedding_dim": 24
  }
}
```

#### `index_built`

```json
{
  "event_type": "index_built",
  "timestamp": "2024-01-15T09:05:00Z",
  "run_id": "run-pdf-123",
  "payload": {
    "doc_id": "sql-textbook",
    "chunk_count": 1250,
    "index_type": "flat",
    "embedding_model_id": "hash-embedding-v1",
    "index_params": {
      "metric": "cosine",
      "dimension": 24
    }
  }
}
```

#### `concept_link_suggested`

```json
{
  "event_type": "concept_link_suggested",
  "timestamp": "2024-01-15T09:10:00Z",
  "run_id": "run-pdf-123",
  "payload": {
    "concept_id": "select-basic",
    "chunk_id": "sql-textbook:p45:c1",
    "suggestion_method": "keyword_matching",
    "confidence": 0.85,
    "matched_keywords": ["SELECT", "FROM", "column"]
  }
}
```

#### `concept_link_confirmed`

```json
{
  "event_type": "concept_link_confirmed",
  "timestamp": "2024-01-15T09:15:00Z",
  "run_id": "run-pdf-123",
  "payload": {
    "concept_id": "select-basic",
    "chunk_id": "sql-textbook:p45:c1",
    "confirmed_by": "human_reviewer",
    "validation_method": "manual_review",
    "reviewer_id": "reviewer-001"
  }
}
```

### 3. Retrieval and Generation Events

#### `retrieval_query`

```json
{
  "event_type": "retrieval_query",
  "timestamp": "2024-01-15T10:35:00Z",
  "trace_id": "trace-abc123",
  "payload": {
    "query_id": "query-456",
    "query_text": "SELECT statement basics error FORM",
    "query_type": "error_context",
    "top_k": 5,
    "filters": {
      "concept_ids": ["sql.select.basic"],
      "difficulty": "beginner"
    }
  }
}
```

#### `retrieval_results`

```json
{
  "event_type": "retrieval_results",
  "timestamp": "2024-01-15T10:35:00Z",
  "trace_id": "trace-abc123",
  "payload": {
    "query_id": "query-456",
    "results": [
      {
        "chunk_id": "sql-textbook:p45:c1",
        "score": 0.92,
        "rank": 1
      },
      {
        "chunk_id": "sql-textbook:p45:c2",
        "score": 0.85,
        "rank": 2
      }
    ],
    "retrieval_time_ms": 45
  }
}
```

#### `generation_prompt_built`

```json
{
  "event_type": "generation_prompt_built",
  "timestamp": "2024-01-15T10:35:00Z",
  "trace_id": "trace-abc123",
  "payload": {
    "prompt_template_id": "worked-example-v1.2",
    "template_version": "1.2.0",
    "retrieved_bundle_ids": ["bundle-123", "bundle-456"],
    "context_window_tokens": 1847,
    "prompt_hash": "sha256:prompt789"
  }
}
```

#### `generation_completed`

```json
{
  "event_type": "generation_completed",
  "timestamp": "2024-01-15T10:35:02Z",
  "trace_id": "trace-abc123",
  "payload": {
    "output_hash": "sha256:output123",
    "output_length_tokens": 412,
    "generation_time_ms": 2500,
    "safety_gates_passed": ["no_pii", "sql_syntax_valid"],
    "citations_included": ["sql-textbook:p45:c1", "sql-textbook:p45:c2"]
  }
}
```

#### `quality_gate_failed`

```json
{
  "event_type": "quality_gate_failed",
  "timestamp": "2024-01-15T10:35:02Z",
  "trace_id": "trace-abc123",
  "payload": {
    "gate_name": "sql_syntax_valid",
    "failure_reason": "Generated SQL contains syntax error",
    "fallback_path": "retrieve_static_example",
    "fallback_content_id": "static-example-789"
  }
}
```

### 4. Reproducibility Events

#### `run_manifest_written`

```json
{
  "event_type": "run_manifest_written",
  "timestamp": "2024-01-15T09:00:00Z",
  "run_id": "run-pdf-123",
  "payload": {
    "manifest_path": "experiments/exp-001/manifest.json",
    "parameters": {
      "chunk_size": 150,
      "overlap": 30
    },
    "random_seed": 42,
    "code_version": "git:abc123",
    "config_hash": "sha256:config456"
  }
}
```

#### `artifact_emitted`

```json
{
  "event_type": "artifact_emitted",
  "timestamp": "2024-01-15T09:15:00Z",
  "run_id": "run-pdf-123",
  "payload": {
    "artifact_type": "concept-manifest",
    "artifact_hash": "sha256:manifest789",
    "artifact_path": "domain-pack/concepts/concept-map.json",
    "schema_version": "concept-manifest-v1"
  }
}
```

#### `dependency_snapshot`

```json
{
  "event_type": "dependency_snapshot",
  "timestamp": "2024-01-15T09:00:00Z",
  "run_id": "run-pdf-123",
  "payload": {
    "lockfile_hash": "sha256:lockfile123",
    "environment_summary": {
      "python_version": "3.10.12",
      "platform": "linux-x86_64",
      "container_image": "ghcr.io/algl/pdf-helper:v1.0.0"
    }
  }
}
```

---

## Common Fields (All Events)

Every event must include:

```json
{
  "event_type": "string",           // Event type (from taxonomy)
  "timestamp": "ISO8601",           // Event timestamp (UTC)
  "trace_id": "uuid",               // Distributed trace ID
  "span_id": "uuid",                // Operation span ID
  "run_id": "string",               // Pipeline run ID (if applicable)
  "experiment_id": "string",        // Experiment ID (if applicable)
  "policy_id": "string",            // Policy version ID
  "code_version": "git:hash",       // Git commit hash
  "config_hash": "sha256:hash",     // Configuration hash
  "payload": {...}                  // Event-specific data
}
```

---

## Storage and Retention

### Event Storage

```
events/
├── raw/
│   └── {date}/
│       └── {hour}.jsonl.gz          # Compressed raw events
├── derived/
│   ├── hdi/
│   │   └── {learner_id}.json        # Computed HDI scores
│   ├── csi/
│   │   └── {session_id}.json        # Computed CSI scores
│   └── metrics/
│       └── daily-metrics.json
└── archive/
    └── {year}/
        └── {month}.parquet          # Archived for analysis
```

### Retention Policy

| Event Type | Hot Storage | Warm Storage | Cold Storage |
|------------|-------------|--------------|--------------|
| Interaction events | 30 days | 1 year | Indefinite |
| Pipeline events | 7 days | 90 days | 1 year |
| Reproducibility events | 7 days | 90 days | 1 year |
| Derived metrics | 30 days | 1 year | Indefinite |

---

## Query Patterns

### Common Queries

```sql
-- Escalation events for a learner
SELECT * FROM events 
WHERE event_type = 'escalation_decision'
  AND learner_id_pseudonymous = 'hash'
  AND timestamp > '2024-01-01'
ORDER BY timestamp;

-- Explanation generation latency
SELECT 
  AVG(payload->>'generation_time_ms') as avg_latency,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY payload->>'generation_time_ms') as p95
FROM events
WHERE event_type = 'explanation_generated'
  AND timestamp > NOW() - INTERVAL '7 days';

-- Hint dependency by concept
SELECT 
  payload->>'concept_id' as concept,
  COUNT(*) as hint_count,
  AVG(payload->>'time_since_start_ms') as avg_time_to_hint
FROM events
WHERE event_type = 'hint_requested'
GROUP BY concept;
```

---

## Validation

### JSON Schema

All events validate against JSON Schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["event_type", "timestamp", "trace_id", "payload"],
  "properties": {
    "event_type": {
      "type": "string",
      "enum": ["attempt_submitted", "hint_shown", "..."]
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    },
    "trace_id": {
      "type": "string",
      "pattern": "^[0-9a-f-]{36}$"
    },
    "payload": {
      "type": "object"
    }
  }
}
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0.0 | 2026-03-03 | Initial event logging specification |

---

*This document defines the event logging architecture for the Adaptive Textbook Helper.*
