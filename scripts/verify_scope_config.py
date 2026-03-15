#!/usr/bin/env python3
"""Verify the Week 1 v1.5 scope config structure."""

import yaml
import sys
from pathlib import Path

def main():
    config_path = Path("data/demo_scope_week1_v15.yaml")
    
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        sys.exit(1)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    # Verify structure
    checks = [
        ('contract' in data, "Missing contract section"),
        (data['contract']['version'] == '1.5.0', "Wrong version"),
        ('pipeline_paths' in data, "Missing pipeline_paths"),
        ('default' in data['pipeline_paths'], "Missing default path"),
        ('fallback' in data['pipeline_paths'], "Missing fallback path"),
        ('repair' in data['pipeline_paths'], "Missing repair path"),
        ('demo_scope' in data, "Missing demo_scope"),
        (len(data['demo_scope']['textbooks']) == 2, "Should have 2 textbooks"),
        (data['policies']['whole_book_processing'] == False, "Whole-book should be False"),
        (data['pipeline_paths']['fallback']['tool'] == 'glm-4v', "Fallback tool should be glm-4v"),
        (data['pipeline_paths']['repair']['tool'] == 'qwen3.5:9b-q8_0', "Repair tool should be qwen3.5:9b-q8_0"),
    ]
    
    all_passed = True
    for check, message in checks:
        if not check:
            print(f"FAIL: {message}")
            all_passed = False
    
    if not all_passed:
        sys.exit(1)
    
    # Print summary
    print("All structure checks passed!")
    print(f"  Contract version: {data['contract']['version']}")
    print(f"  Pipeline paths: {list(data['pipeline_paths'].keys())}")
    print(f"  Textbooks: {[t['id'] for t in data['demo_scope']['textbooks']]}")
    
    murach = data['demo_scope']['textbooks'][0]
    ramakrishnan = data['demo_scope']['textbooks'][1]
    
    print(f"  Murach slice: Ch {murach['slice']['value']}, {murach['concept_target']['count']} concepts")
    print(f"  Ramakrishnan slice: Ch {ramakrishnan['slice']['value']}, {ramakrishnan['concept_target']['count']} concepts")
    print(f"  Export mode: {murach['export_mode']}")
    print(f"  Whole-book processing: {data['policies']['whole_book_processing']}")
    print(f"  GLM OCR fallback only: {data['policies']['glm_ocr_fallback_only']}")
    print(f"  External LLM for repair: {data['policies']['external_llm_for_repair']}")
    
    # Verify concept counts
    murach_count = len(murach['concept_target']['ids'])
    ramakrishnan_count = len(ramakrishnan['concept_target']['ids'])
    
    assert 8 <= murach_count <= 12, f"Murach concepts should be 8-12, got {murach_count}"
    assert 8 <= ramakrishnan_count <= 12, f"Ramakrishnan concepts should be 8-12, got {ramakrishnan_count}"
    
    print(f"\nConcept count validation passed:")
    print(f"  Murach: {murach_count} concepts (target: 8-12)")
    print(f"  Ramakrishnan: {ramakrishnan_count} concepts (target: 8-12)")

if __name__ == "__main__":
    main()
