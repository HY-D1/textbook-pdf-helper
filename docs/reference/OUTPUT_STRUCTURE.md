# Output Structure Guide

## Three-Layer Concept Mapping Integration

The educational pipeline now fully integrates the three-layer concept mapping system into its outputs.

### How Outputs Map to the Three Layers

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1: Error Detection                                         │
│ Output: mappings/error-subtypes.json                            │
│ Contains: 23 SQL-Engage error subtypes                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Layer 2: Alignment Map                                           │
│ Output: mappings/alignment-map.json                             │
│ Contains: Error subtype → Concept ID mappings                   │
│           + teaching strategies, confidence levels              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Layer 3: Concept Registry                                        │
│ Output: mappings/concept-registry.json                          │
│          concepts/{doc_id}/{concept-id}.md                      │
│ Contains: Full concept content with educational material        │
└─────────────────────────────────────────────────────────────────┘
```

## Generated Output Structure

When you run the export commands, the following structure is created:

```
output/{pdf-name}/
│
├── 📋 concept-manifest.json              # Internal concept metadata
├── 📋 concept-map.json                   # SQL-Adapt merged concept map
├── 📋 {doc-id}-sqladapt.json            # Full educational notes + mappings
│
├── 🔧 mappings/                          # ⭐ THREE-LAYER SYSTEM FILES
│   ├── error-subtypes.json              # Layer 1: Error definitions
│   ├── alignment-map.json               # Layer 2: Error → Concept mappings
│   └── concept-registry.json            # Layer 3: Concept metadata
│
├── 📚 concepts/{doc_id}/                 # ⭐ CONCEPT CONTENT (Layer 3)
│   ├── README.md                        # Index of concepts in this PDF
│   ├── select-basic.md                  # Individual concept files
│   ├── joins-intro.md
│   ├── aggregation.md
│   └── ... (30+ concept files)
│
├── 📄 {doc-id}-study-guide.md           # Human-readable study guide
├── 🔍 {doc-id}-extraction.json          # Raw extraction (diagnostic)
└── 📝 {doc-id}-educational-notes.json   # Educational data (diagnostic)
```

## Key Output Files Explained

### 1. {doc-id}-sqladapt.json

The main output file containing educational content WITH three-layer mappings:

```json
{
  "schemaVersion": "educational-concept-v1",
  "sourceDocId": "murachs-mysql-3rd-edition",
  "generatedAt": "2026-02-27T...",
  "concepts": {
    "select-basic": {
      "id": "select-basic",
      "title": "SELECT Statement Basics",
      "definition": "Retrieves data from one or more tables",
      "difficulty": "beginner",
      "estimatedReadTime": 10,
      "sections": {
        "definition": { "chunkIds": [...], "text": "..." },
        "explanation": { "chunkIds": [...], "text": "..." },
        "examples": { "chunkIds": [...], "items": [...] },
        "commonMistakes": { "chunkIds": [...], "items": [...] },
        "practice": { "chunkIds": [...], "questions": {...} }
      },
      "relatedConcepts": ["where-clause", "alias"],
      "tags": ["sql", "query", "dql"],
      
      "⭐ THREE-LAYER MAPPINGS": {
        "errorSubtypes": [
          "incorrect_select_usage",
          "missing_comma_in_select"
        ],
        "teachingStrategies": [
          "select_mastery",
          "syntax_drill"
        ]
      }
    }
  },
  "errorMappings": {
    "incorrect_select_usage": {
      "errorSubtypeId": 2,
      "conceptIds": ["select-basic", "distinct"],
      "confidence": "high",
      "teachingStrategy": "select_mastery",
      "remediationOrder": ["select-basic", "distinct"]
    },
    "missing_comma_in_select": {
      "errorSubtypeId": 4,
      "conceptIds": ["select-basic", "syntax-error"],
      "confidence": "verified",
      "teachingStrategy": "syntax_drill",
      "remediationOrder": ["syntax-error", "select-basic"]
    }
  },
  "metadata": {
    "mappingSystem": "three-layer-concept-v1",
    "totalErrorSubtypes": 23,
    "totalMappings": 23
  }
}
```

### 2. mappings/error-subtypes.json (Layer 1)

```json
{
  "schemaVersion": "error-subtypes-v1",
  "subtypes": {
    "missing_comma_in_select": {
      "id": 4,
      "name": "Missing Comma in SELECT",
      "severity": "error",
      "category": "syntax"
    },
    "incorrect_join_type": {
      "id": 11,
      "name": "Incorrect JOIN Type",
      "severity": "error",
      "category": "logic"
    }
  }
}
```

### 3. mappings/alignment-map.json (Layer 2)

```json
{
  "schemaVersion": "alignment-map-v1",
  "mappings": {
    "missing_comma_in_select": {
      "error_subtype_id": 4,
      "concept_ids": ["select-basic", "syntax-error"],
      "confidence": "verified",
      "teaching_strategy": "syntax_drill",
      "remediation_order": ["syntax-error", "select-basic"]
    }
  }
}
```

### 4. mappings/concept-registry.json (Layer 3)

```json
{
  "schemaVersion": "concept-registry-v1",
  "concepts": {
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
}
```

## Concept Determination Flow

### Step 1: Error Subtype Detection (Layer 1)

When processing content, the system:
1. Extracts content from PDF pages
2. Maps content to concepts defined in `concepts.yaml`
3. Associates error subtypes based on content analysis

### Step 2: Subtype → Concept Mapping (Layer 2)

For each concept found:
```python
# Get error subtypes that map to this concept
error_subtypes = concept_mapper.get_concepts_for_error(concept_id)

# Get teaching strategies
teaching_strategies = [
    concept_mapper.get_teaching_strategy(err)
    for err in error_subtypes
]
```

### Step 3: Concept Content Generation (Layer 3)

Generated files in `concepts/{doc_id}/`:
- Individual `.md` files per concept
- Educational content with examples
- Common mistakes and practice questions

## Running the Pipeline

### Option 1: Interactive
```bash
./start.sh
# Select option 4 or 5
```

### Option 2: Command Line

```bash
# Process single PDF
python3 -m algl_pdf_helper export-edu \
    raw_pdf/murachs-mysql-3rd-edition.pdf \
    --output-dir ./output/murach-mysql \
    --llm-provider kimi

# Process all PDFs
for pdf in raw_pdf/*.pdf; do
    name=$(basename "$pdf" .pdf)
    python3 -m algl_pdf_helper export-edu \
        "$pdf" \
        --output-dir "./output/$name" \
        --llm-provider kimi
done
```

## Integration with SQL-Adapt Web App

The outputs are compatible with the SQL-Adapt concept loader:

```typescript
// concept-loader.ts integration
import { ConceptMappingSystem } from './sql-engage-adapter';

// Load the three-layer system
const mapper = new ConceptMappingSystem(
  errorSubtypesJson,    // From mappings/error-subtypes.json
  alignmentMapJson,     // From mappings/alignment-map.json
  conceptRegistryJson   // From mappings/concept-registry.json
);

// Use in error handling
const errorSubtype = detectErrorSubtype(studentError);
const conceptIds = mapper.getConceptsForError(errorSubtype);
const conceptContent = mapper.getConceptContent(conceptIds[0]);
```

## Validation

Verify the three-layer integration:

```bash
# Check output structure
ls output/*/mappings/

# Verify JSON validity
python3 -c "
import json
with open('output/murachs-mysql/mappings/alignment-map.json') as f:
    data = json.load(f)
    print(f'✓ Mappings: {data[\"totalMappings\"]}')
"

# Check concept count
python3 -c "
import json
with open('output/murachs-mysql/concept-map.json') as f:
    data = json.load(f)
    print(f'✓ Concepts: {len(data[\"concepts\"])}')
"
```

## Summary

✅ **All three layers are now included in outputs:**
- Layer 1: `mappings/error-subtypes.json` (23 error types)
- Layer 2: `mappings/alignment-map.json` (23 mappings)
- Layer 3: `concepts/{doc_id}/*.md` (30+ concept files)

✅ **Integration verified:**
- Concepts include `errorSubtypes` and `teachingStrategies`
- SQL-Adapt format includes `errorMappings` section
- Mapping files copied to each output directory
