# RAG Chunk Deduplicator - Reference

## Exact Duplicate Detection

```python
import hashlib
import json

def find_exact_duplicates(chunks):
    """Find chunks with identical text content."""
    seen = {}
    duplicates = []
    unique = []
    
    for chunk in chunks:
        text = chunk.get('text', '').strip().lower()
        content_hash = hashlib.md5(text.encode()).hexdigest()
        
        if content_hash in seen:
            duplicates.append({
                'chunk': chunk,
                'duplicate_of': seen[content_hash]['chunk_id'],
                'match_type': 'exact'
            })
        else:
            seen[content_hash] = chunk
            unique.append(chunk)
    
    return unique, duplicates
```

## Near-Duplicate Detection

```python
from difflib import SequenceMatcher

def similarity_ratio(text1, text2):
    """Calculate similarity ratio between two texts."""
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

def find_near_duplicates(chunks, threshold=0.85):
    """Find chunks with highly similar content."""
    duplicates = []
    unique = []
    
    for chunk in chunks:
        text = chunk.get('text', '')
        is_duplicate = False
        
        for unique_chunk in unique:
            unique_text = unique_chunk.get('text', '')
            sim = similarity_ratio(text, unique_text)
            
            if sim >= threshold:
                duplicates.append({
                    'chunk': chunk,
                    'duplicate_of': unique_chunk['chunk_id'],
                    'similarity': sim,
                    'match_type': 'near'
                })
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique.append(chunk)
    
    return unique, duplicates
```

## Semantic Deduplication

```python
import numpy as np

def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors."""
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def find_semantic_duplicates(chunks, embeddings, threshold=0.95):
    """Find semantically similar chunks using embeddings."""
    duplicates = []
    unique_indices = []
    
    for i, chunk in enumerate(chunks):
        is_duplicate = False
        
        for j in unique_indices:
            sim = cosine_similarity(embeddings[i], embeddings[j])
            
            if sim >= threshold:
                duplicates.append({
                    'chunk': chunk,
                    'duplicate_of': chunks[j]['chunk_id'],
                    'similarity': float(sim),
                    'match_type': 'semantic'
                })
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_indices.append(i)
    
    unique = [chunks[i] for i in unique_indices]
    return unique, duplicates
```

## Merge Strategies

### Completeness Score

```python
def completeness_score(chunk):
    """Score chunk by metadata completeness."""
    score = 0
    score += len(chunk.get('text', '')) / 100
    score += len(chunk.get('tags', {})) * 2
    score += len(chunk.get('evidence', [])) * 3
    score += 1 if chunk.get('provenance') else 0
    return score
```

### Merge Metadata

```python
def merge_metadata(chunks_group):
    """Merge metadata from duplicate chunks into one."""
    base = max(chunks_group, key=completeness_score)
    merged = base.copy()
    
    all_tags = {}
    for chunk in chunks_group:
        all_tags.update(chunk.get('tags', {}))
    merged['tags'] = all_tags
    
    all_evidence = set()
    for chunk in chunks_group:
        all_evidence.update(chunk.get('evidence', []))
    merged['evidence'] = list(all_evidence)
    
    merged['provenance'] = merged.get('provenance', {})
    merged['provenance']['merged_from'] = [c['chunk_id'] for c in chunks_group]
    
    return merged
```

## Cross-Source Deduplication

```python
def cross_source_dedupe(sources_config):
    """Deduplicate across multiple sources with priority."""
    # sources_config: [{'path': '...', 'priority': 1, 'source_name': '...'}]
    
    sources = sorted(sources_config, key=lambda x: x['priority'])
    
    all_chunks = []
    for source in sources:
        with open(source['path'], 'r') as f:
            for line in f:
                chunk = json.loads(line)
                chunk['_priority'] = source['priority']
                chunk['_source_name'] = source['source_name']
                all_chunks.append(chunk)
    
    # When duplicates found, keep higher priority (lower number)
    # ... deduplication logic
```

## Validation

```python
def validate_deduplication(original_chunks, deduped_chunks, duplicates):
    """Validate deduplication didn't lose content."""
    issues = []
    
    original_ids = {c['chunk_id'] for c in original_chunks}
    deduped_ids = {c['chunk_id'] for c in deduped_chunks}
    dup_ids = {d['chunk']['chunk_id'] for d in duplicates}
    
    accounted_for = deduped_ids | dup_ids
    missing = original_ids - accounted_for
    
    if missing:
        issues.append(f"Missing chunk IDs: {missing}")
    
    low_similarity = [d for d in duplicates if d.get('similarity', 1.0) < 0.8]
    if low_similarity:
        issues.append(f"{len(low_similarity)} duplicates with similarity < 0.8")
    
    return issues
```

## Output Format

```json
{
  "chunk_id": "...",
  "text": "...",
  "tags": {},
  "provenance": {
    "merged_from": ["chunk_id_1", "chunk_id_2"],
    "dedup_strategy": "merge_metadata",
    "original_sources": ["file1.jsonl", "file2.jsonl"]
  }
}
```
