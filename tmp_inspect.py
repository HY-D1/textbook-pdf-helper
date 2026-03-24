import json, sys
data = json.load(sys.stdin)
concepts = data.get('qualityByConcept', {})
print(f"Total concepts: {len(concepts)}")

# Find fallback_only with examples
found = 0
for cid, c in concepts.items():
    if c.get('readabilityStatus') == 'fallback_only' and c.get('learnerSafeExamples'):
        found += 1
        print(f"\n{'='*60}")
        print(f"Concept: {cid}")
        print(f"  Title: {c.get('title', 'N/A')}")
        print(f"  Example Quality: {c.get('exampleQuality', 'N/A')}")
        print(f"  Examples count: {len(c.get('learnerSafeExamples', []))}")
        examples = c.get('learnerSafeExamples', [])
        for i in range(min(3, len(examples))):
            ex = examples[i]
            print(f"\n  Example {i+1}:")
            if isinstance(ex, dict):
                print(f"    Title: {ex.get('title', 'N/A')}")
                sql = ex.get('sql', '')
                print(f"    SQL: {sql[:300]}..." if len(sql) > 300 else f"    SQL: {sql}")
            else:
                print(f"    {str(ex)[:300]}...")
        if found >= 5:
            break

print(f"\n{'='*60}")
print(f"Total fallback concepts with examples: {found}")
