import json

# Analyze L2 units from instructional_units.jsonl
l2_sources = {'default': 0, 'extracted': 0, 'curated': 0, 'unknown': 0}
l2_details = []

with open('outputs/ramakrishnan/instructional_units.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        if not line.strip():
            continue
        unit = json.loads(line)
        if unit.get('target_stage') == 'L2_hint_plus_example':
            content = unit.get('content', {})
            metadata = content.get('_metadata', {}) if isinstance(content, dict) else {}
            
            # Determine source
            source = 'unknown'
            if metadata.get('example_source_type'):
                source = metadata.get('example_source_type')
            elif metadata.get('l2_source'):
                source = metadata.get('l2_source')
            elif content.get('example_sql'):
                sql = content.get('example_sql', '')
                # Check if it looks like a default
                if 'SELECT * FROM' in sql and 'Portland' in sql:
                    source = 'default'
                elif metadata.get('used_default_example'):
                    source = 'default'
            
            l2_sources[source] = l2_sources.get(source, 0) + 1
            
            concept_id = unit.get('concept_id', 'unknown')
            example_sql = content.get('example_sql', '')[:60] if isinstance(content, dict) else ''
            l2_details.append({
                'concept': concept_id,
                'source': source,
                'sql_preview': example_sql
            })

print('=== L2 Source Distribution ===')
for k, v in sorted(l2_sources.items()):
    print(f'{k}: {v}')

print()
print('=== Core Concept L2 Details ===')
core_concepts = ['select-basic', 'where-clause', 'joins-intro', 'group-by', 'order-by', 
                 'aggregate-functions', 'subqueries-intro', 'null-handling', 
                 'pattern-matching', 'insert-statement', 'update-statement', 'delete-statement']
for detail in l2_details:
    if detail['concept'] in core_concepts:
        print(f"{detail['concept']}: {detail['source']} -> {detail['sql_preview']}")
