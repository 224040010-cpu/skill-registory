#!/usr/bin/env python3
"""
Transform RAG chunks to KNOWLEDGE_PACKAGE schema v2.

Usage:
    python transform.py --input chunks.jsonl --output output_dir/
"""

import json
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

# Layer mapping: source_type -> (knowledge_layer, freshness_level)
LAYER_MAP = {
    'doc': ('norm', 'static'),
    'document': ('norm', 'static'),
    'faq': ('norm', 'static'),
    'error_code': ('norm', 'static'),
    'wiki_doc': ('norm', 'static'),
    'code': ('norm', 'static'),
    'rule': ('norm', 'static'),
    'other': ('norm', 'static'),
    'fmea': ('relation', 'static'),
    'relationship': ('relation', 'static'),
    'vehicle': ('relation', 'static'),
    'field_experience': ('process', 'daily'),
    'ticket': ('process', 'daily'),
    'case': ('process', 'daily'),
    'log': ('evidence', 'daily'),
    'ocr': ('evidence', 'static'),
}

VALID_SOURCE_SYSTEMS = ['eu', 'us', 'other']
VALID_RAG_TYPES = ['canonical', 'curated']


def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def transform_chunk(chunk: dict) -> dict:
    """Add required fields to chunk."""
    # Add knowledge_layer and freshness_level
    source_type = chunk.get('source_type', 'doc')
    layer, freshness = LAYER_MAP.get(source_type, ('norm', 'static'))
    chunk['knowledge_layer'] = layer
    chunk['freshness_level'] = freshness
    
    # Fix source_system
    if chunk.get('source_system') not in VALID_SOURCE_SYSTEMS:
        chunk['source_system'] = 'other'
    
    # Fix rag_type
    tags = chunk.get('tags', {})
    if isinstance(tags, list):
        tags = {'keywords': tags}
    if tags.get('rag_type') not in VALID_RAG_TYPES:
        # Default based on source_type
        if source_type in ['fmea', 'error_code', 'doc']:
            tags['rag_type'] = 'canonical'
        else:
            tags['rag_type'] = 'curated'
    chunk['tags'] = tags
    
    return chunk


def make_titles_unique(chunks: list) -> list:
    """Ensure all titles are unique."""
    title_counter = Counter(c.get('title', '') for c in chunks)
    dup_titles = {t for t, count in title_counter.items() if count > 1}
    
    title_index = defaultdict(int)
    for chunk in chunks:
        title = chunk.get('title', '')
        if title in dup_titles:
            title_index[title] += 1
            prov = chunk.get('provenance', {})
            source_id = prov.get('source_id', '')
            content_hash = prov.get('content_hash', '')[:6]
            
            if source_id and 'row_' in source_id:
                row = source_id.split('row_')[-1]
                chunk['title'] = f'{title} (row {row})'
            elif content_hash:
                chunk['title'] = f'{title} [{content_hash}]'
            else:
                chunk['title'] = f'{title} #{title_index[title]}'
    
    return chunks


def filter_empty_chunks(chunks: list) -> list:
    """Remove empty and placeholder chunks."""
    filtered = []
    for c in chunks:
        title = (c.get('title') or '').strip()
        text = (c.get('text') or '').strip()
        
        # Skip empty
        if not title and not text:
            continue
        
        # Skip placeholders
        if text.count('|') <= 3 and len(text) < 100:
            labels = ['issue', 'solution', 'status']
            if sum(1 for l in labels if l in text.lower()) >= 2:
                continue
        
        filtered.append(c)
    return filtered


def main():
    parser = argparse.ArgumentParser(description='Transform to KNOWLEDGE_PACKAGE v2')
    parser.add_argument('--input', '-i', required=True, help='Input JSONL file')
    parser.add_argument('--output', '-o', required=True, help='Output directory')
    parser.add_argument('--name', '-n', default='knowledge', help='Dataset name')
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Read chunks
    chunks = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line.strip()))
    
    print(f'Loaded {len(chunks)} chunks')
    
    # Transform
    chunks = filter_empty_chunks(chunks)
    print(f'After filtering: {len(chunks)}')
    
    for c in chunks:
        transform_chunk(c)
    
    chunks = make_titles_unique(chunks)
    
    # Calculate stats
    layer_counts = defaultdict(int)
    stats = {
        'by_source_type': defaultdict(int),
        'by_language': defaultdict(int),
        'by_rag_type': defaultdict(int),
    }
    
    for c in chunks:
        layer_counts[c.get('knowledge_layer', 'unknown')] += 1
        stats['by_source_type'][c.get('source_type', 'unknown')] += 1
        stats['by_language'][c.get('language', 'unknown')] += 1
        stats['by_rag_type'][c.get('tags', {}).get('rag_type', 'unknown')] += 1
    
    # Write chunks
    chunks_path = output_dir / 'chunks.jsonl'
    with open(chunks_path, 'w', encoding='utf-8') as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + '\n')
    
    # Write manifest
    manifest = {
        'dataset_name': args.name,
        'schema_version': 'v2',
        'build_at': datetime.now().isoformat(),
        'source_system': 'other',
        'counts': {'chunks': len(chunks)},
        'layer_counts': dict(layer_counts),
        'statistics': {k: dict(v) for k, v in stats.items()},
    }
    
    manifest_path = output_dir / 'manifest.json'
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    print(f'\nOutput: {output_dir}')
    print(f'Chunks: {len(chunks)}')
    print(f'Layer counts: {dict(layer_counts)}')


if __name__ == '__main__':
    main()
