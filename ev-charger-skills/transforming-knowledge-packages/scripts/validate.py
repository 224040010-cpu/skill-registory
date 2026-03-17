#!/usr/bin/env python3
"""
Validate knowledge package against KNOWLEDGE_PACKAGE schema v2.

Usage:
    python validate.py /path/to/package/
"""

import json
import re
import sys
from pathlib import Path
from collections import defaultdict


def validate_package(package_dir: Path) -> dict:
    """Validate a knowledge package and return report."""
    report = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'stats': {},
    }
    
    # Check required files
    required_files = ['chunks.jsonl', 'manifest.json']
    for fname in required_files:
        if not (package_dir / fname).exists():
            report['errors'].append(f'Missing required file: {fname}')
            report['valid'] = False
    
    if not report['valid']:
        return report
    
    # Load chunks
    chunks_path = package_dir / 'chunks.jsonl'
    chunks = []
    
    with open(chunks_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                chunk = json.loads(line)
                chunks.append((line_num, chunk))
            except json.JSONDecodeError as e:
                report['errors'].append(f'Line {line_num}: Invalid JSON - {e}')
    
    # Validate chunks
    required_fields = ['chunk_id', 'source_system', 'source_type', 'title', 'text', 'tags', 'provenance']
    v2_fields = ['knowledge_layer', 'freshness_level']
    
    valid_source_systems = ['eu', 'us', 'other']
    valid_rag_types = ['canonical', 'curated']
    valid_layers = ['norm', 'evidence', 'relation', 'process']
    valid_freshness = ['static', 'daily', 'realtime']
    
    local_path_pattern = re.compile(r'^(/Users/|/home/|C:\\|D:\\)')
    
    stats = {
        'total_chunks': len(chunks),
        'by_source_type': defaultdict(int),
        'by_knowledge_layer': defaultdict(int),
        'by_freshness_level': defaultdict(int),
        'by_rag_type': defaultdict(int),
        'missing_fields': defaultdict(int),
        'invalid_values': defaultdict(int),
    }
    
    titles = []
    
    for line_num, chunk in chunks:
        # Check required fields
        for field in required_fields:
            if field not in chunk:
                stats['missing_fields'][field] += 1
        
        # Check v2 required fields
        for field in v2_fields:
            if field not in chunk:
                stats['missing_fields'][field] += 1
        
        # Validate source_system
        ss = chunk.get('source_system', '')
        if ss not in valid_source_systems:
            stats['invalid_values']['source_system'] += 1
        
        # Validate knowledge_layer
        kl = chunk.get('knowledge_layer', '')
        if kl and kl not in valid_layers:
            stats['invalid_values']['knowledge_layer'] += 1
        stats['by_knowledge_layer'][kl] += 1
        
        # Validate freshness_level
        fl = chunk.get('freshness_level', '')
        if fl and fl not in valid_freshness:
            stats['invalid_values']['freshness_level'] += 1
        stats['by_freshness_level'][fl] += 1
        
        # Validate rag_type
        tags = chunk.get('tags', {})
        rt = tags.get('rag_type', '') if isinstance(tags, dict) else ''
        if rt not in valid_rag_types:
            stats['invalid_values']['rag_type'] += 1
        stats['by_rag_type'][rt] += 1
        
        # Check evidence for local paths
        evidence = chunk.get('evidence', [])
        if isinstance(evidence, list):
            for ev in evidence:
                if isinstance(ev, str) and local_path_pattern.match(ev):
                    stats['invalid_values']['local_machine_path'] += 1
        
        # Collect stats
        stats['by_source_type'][chunk.get('source_type', 'unknown')] += 1
        titles.append(chunk.get('title', ''))
    
    # Check for duplicate titles
    dup_titles = len(titles) - len(set(titles))
    if dup_titles > 0:
        stats['invalid_values']['duplicate_titles'] = dup_titles
        report['warnings'].append(f'{dup_titles} duplicate titles found')
    
    # Build errors from stats
    for field, count in stats['missing_fields'].items():
        if count > 0:
            report['errors'].append(f'Missing {field}: {count} chunks')
            report['valid'] = False
    
    for field, count in stats['invalid_values'].items():
        if count > 0 and field not in ['duplicate_titles']:
            report['errors'].append(f'Invalid {field}: {count} chunks')
            if field in ['rag_type', 'source_system']:
                report['valid'] = False
    
    report['stats'] = {k: dict(v) if isinstance(v, defaultdict) else v for k, v in stats.items()}
    
    return report


def main():
    if len(sys.argv) < 2:
        print('Usage: python validate.py /path/to/package/')
        sys.exit(1)
    
    package_dir = Path(sys.argv[1])
    report = validate_package(package_dir)
    
    print('=' * 60)
    print(f'Validation Report: {package_dir}')
    print('=' * 60)
    
    if report['valid']:
        print('\n✅ VALIDATION PASSED\n')
    else:
        print('\n❌ VALIDATION FAILED\n')
    
    stats = report['stats']
    print(f"Total chunks: {stats.get('total_chunks', 0)}")
    
    print('\nBy knowledge_layer:')
    for k, v in sorted(stats.get('by_knowledge_layer', {}).items()):
        print(f'  {k}: {v}')
    
    print('\nBy freshness_level:')
    for k, v in sorted(stats.get('by_freshness_level', {}).items()):
        print(f'  {k}: {v}')
    
    if report['errors']:
        print('\nERRORS:')
        for err in report['errors'][:10]:
            print(f'  ❌ {err}')
    
    if report['warnings']:
        print('\nWARNINGS:')
        for warn in report['warnings'][:5]:
            print(f'  ⚠️ {warn}')
    
    print('=' * 60)
    sys.exit(0 if report['valid'] else 1)


if __name__ == '__main__':
    main()
