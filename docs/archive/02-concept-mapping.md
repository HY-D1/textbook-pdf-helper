# SQL-Engage Concept Mapping Integration Guide

## Overview

This guide explains the three-layer concept mapping system that connects SQL-Engage error detection with ALGL educational content.

## Three-Layer Architecture

```
Layer 1: Error Subtype Detection (sql-engage.ts)
    ↓
Layer 2: Alignment Map (error → concept IDs)
    ↓
Layer 3: Concept Registry (concept → textbook content)
```

### Layer 1: Error Subtype Detection

**File**: `error-subtypes.json` (generated)

23 error subtypes covering:
- Query Completeness (5 types)
- WHERE Clause (5 types)
- JOIN Operations (3 types)
- Aggregation (4 types)
- Set Operations (2 types)
- Subqueries (2 types)
- Alias & Reference (2 types)

**Example Error Subtype**:
```json
{
  "missing_comma_in_select": {
    "id": 4,
    "name": "Missing Comma in SELECT",
    "severity": "error",
    "category": "syntax"
  }
}
```

### Layer 2: Alignment Map

**File**: `alignment-map.json` (generated)

Maps each error subtype to educational concepts with:
- `concept_ids`: List of concepts to study
- `confidence`: verified / high / medium / low
- `teaching_strategy`: Pedagogical approach
- `remediation_order`: Recommended learning sequence

**Example Mapping**:
```json
{
  "missing_comma_in_select": {
    "error_subtype_id": 4,
    "concept_ids": ["select-basic", "syntax-error"],
    "confidence": "verified",
    "teaching_strategy": "syntax_drill",
    "remediation_order": ["syntax-error", "select-basic"]
  }
}
```

### Layer 3: Concept Registry

**File**: `concept-registry.json` (generated)

30 educational concepts covering:
- SELECT Basics (5 concepts)
- JOINs (3 concepts)
- Aggregation (4 concepts)
- Subqueries (4 concepts)
- Operators (4 concepts)
- Functions (4 concepts)
- Data Handling (5 concepts)
- Errors (2 concepts)

**Example Concept**:
```json
{
  "select-basic": {
    "id": "select-basic",
    "title": "SELECT Statement Basics",
    "description": "Fundamental syntax for retrieving data",
    "difficulty": "beginner",
    "estimatedReadTime": 10,
    "category": "SELECT Basics",
    "contentLocation": "concepts/select-basic.md",
    "qualityStatus": "verified",
    "learningObjectives": ["Write basic SELECT", "Understand column selection"]
  }
}
```

## Integration Methods

### Python Integration

```python
from algl_pdf_helper.concept_mapping_system import ConceptMappingSystem

# Initialize system
cms = ConceptMappingSystem()

# Layer 1→2: Get concepts for error
concepts = cms.get_concepts_for_error("missing_comma_in_select")
# Returns: ['select-basic', 'syntax-error']

# Layer 2→3: Get content for concept
content = cms.get_concept_content("select-basic")
# Returns concept metadata and content location

# Layer 1→2→3: Get complete learning path
path = cms.get_learning_path("missing_comma_in_select")
# Returns error info, concepts, total read time, difficulty
```

### TypeScript Integration

```typescript
import { ConceptMappingSystem } from './sql-engage-adapter';

// Initialize with JSON data
const mapper = new ConceptMappingSystem(
  errorSubtypesJson,
  alignmentMapJson,
  conceptRegistryJson
);

// Get concepts for error
const concepts = mapper.getConceptsForError('missing_comma_in_select');

// Get complete learning path
const path = mapper.getLearningPath('missing_comma_in_select');
console.log(path.totalReadTime);  // Minutes to study
console.log(path.difficulty);     // beginner/intermediate/advanced
```

## Teaching Strategies

| Strategy | Use Case | Description |
|----------|----------|-------------|
| `syntax_drill` | Syntax errors | Repetitive practice of correct syntax |
| `start_fundamentals` | Beginners | Introduce basic SQL concepts first |
| `select_mastery` | SELECT issues | Focus on SELECT statement details |
| `filtering_basics` | WHERE issues | Learn WHERE clause fundamentals |
| `operator_mastery` | Operators | Master logical/comparison operators |
| `join_types` | JOIN errors | Visual explanations of JOIN types |
| `join_conditions` | ON clauses | Practice table relationships |
| `group_by_mastery` | Aggregation | Master grouping and functions |
| `subquery_basics` | Subqueries | Introduction to nested queries |
| `aliasing` | Ambiguity | Learn table/column aliases |

## Data Flow Example

```
Student makes error → System detects → Maps to concepts → Serves content

1. Student writes: SELECT col1 col2 FROM table
2. Error detected: "syntax error at or near 'FROM'"
3. Subtype: missing_comma_in_select (ID: 4)
4. Concepts: syntax-error, select-basic
5. Strategy: syntax_drill
6. Content: [concepts/syntax-error.md, concepts/select-basic.md]
7. Read time: 25 minutes
8. Difficulty: beginner
```

## File Generation

```bash
# Generate all mapping files
python3 -m algl_pdf_helper.concept_mapping_system

# Files created:
# - alignment-map.json
# - error-subtypes.json
# - concept-registry.json (if regenerating)
```

## Validation

```python
from algl_pdf_helper.concept_mapping_system import ConceptMappingSystem

cms = ConceptMappingSystem()

# Check mapping completeness
result = cms.validateMapping()
print(f"Valid: {result['isValid']}")
print(f"Missing concepts: {result['missingConcepts']}")
print(f"Unmapped errors: {result['unmappedErrors']}")
```

## Statistics

Current coverage:
- **30 concepts** across 8 categories
- **23 error subtypes** with complete mappings
- **16 beginner** / **10 intermediate** / **4 advanced** concepts
- **32 practice problems** integrated
- **100%** error subtype coverage

## Adding New Mappings

### 1. Add Error Subtype (Layer 1)

Edit `concept_mapping_system.py`:
```python
ERROR_SUBTYPES = {
    "new_error": {
        "id": 24,
        "name": "New Error Type",
        "severity": "error",
        "category": "syntax"
    }
}
```

### 2. Add Alignment (Layer 2)

```python
ALIGNMENT_MAP = {
    "new_error": {
        "error_subtype_id": 24,
        "concept_ids": ["concept1", "concept2"],
        "confidence": "high",
        "teaching_strategy": "syntax_drill",
        "remediation_order": ["concept1", "concept2"]
    }
}
```

### 3. Add Concept (Layer 3)

Add to `concept-registry.json`:
```json
{
  "new-concept": {
    "id": "new-concept",
    "title": "New Concept",
    "description": "...",
    "difficulty": "beginner",
    "estimatedReadTime": 10,
    "category": "SELECT Basics",
    "contentLocation": "concepts/new-concept.md",
    "qualityStatus": "verified",
    "learningObjectives": ["Objective 1"]
  }
}
```

### 4. Regenerate Files

```bash
python3 -m algl_pdf_helper.concept_mapping_system
pytest tests/test_concept_mapping_system.py
```

## Web App Integration

For SQL-Adapt web app integration:

1. Copy JSON files to web app:
   ```bash
   cp concept-registry.json /path/to/web/public/
   cp alignment-map.json /path/to/web/public/
   cp error-subtypes.json /path/to/web/public/
   ```

2. Import TypeScript adapter:
   ```typescript
   import { ConceptMappingSystem } from './sql-engage-adapter';
   ```

3. Use in error handling:
   ```typescript
   // When student makes error
   const path = mapper.getLearningPath(detectedError);
   showLearningPath(path);
   ```

## Testing

```bash
# Run mapping system tests
pytest tests/test_concept_mapping_system.py -v

# Test specific layers
pytest tests/test_concept_mapping_system.py::TestLayer1ErrorSubtypes -v
pytest tests/test_concept_mapping_system.py::TestLayer2AlignmentMap -v
pytest tests/test_concept_mapping_system.py::TestLayer3ConceptRegistry -v
```
