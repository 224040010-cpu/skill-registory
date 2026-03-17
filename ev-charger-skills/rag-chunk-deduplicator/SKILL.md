---
name: rag-chunk-deduplicator
description: Detect and merge near-duplicate chunks across JSONL files for RAG pipelines. Use this skill when users mention deduplication, finding duplicates, merging similar chunks, cleaning knowledge bases, reducing redundancy, or optimizing RAG retrieval quality. Trigger for "duplicate detection", "similar chunks", "merge overlapping", "clean up knowledge", or any data quality improvement requests.
---

# Purpose

Identify and handle duplicate or near-duplicate chunks in RAG knowledge bases to improve retrieval quality and reduce costs.

# Trigger

**Use when:**
- User mentions "deduplication", "find duplicates", "remove duplicates"
- User asks to "merge similar chunks" or "clean up knowledge base"
- User wants to "reduce redundancy" or "optimize RAG quality"
- User says "duplicate detection", "similar chunks", "merge overlapping"
- Before exporting knowledge packages (run this first)

**Do NOT use when:**
- User wants to export/package knowledge (use `knowledge-package-exporter` after this)
- User wants to query or search the knowledge base
- User is building new chunks from source data
- User wants semantic similarity for retrieval (not dedup)

# Why Deduplication Matters

- **Retrieval quality**: Duplicates waste retrieval slots and dilute relevance
- **Cost**: Redundant embeddings increase storage and inference costs
- **Consistency**: Multiple versions may have conflicting metadata

# Workflow

## Step 1: Gather Inputs

- One or more JSONL files containing RAG chunks
- Configuration: similarity threshold, merge strategy, fields to compare
- Output path for deduplicated results

## Step 2: Run Deduplication Pipeline

```python
def deduplicate_chunks(input_files, output_file, strategy='keep_most_complete'):
    all_chunks = load_chunks(input_files)
    
    # Phase 1: Exact duplicates (fast, hash-based)
    unique, exact_dups = find_exact_duplicates(all_chunks)
    
    # Phase 2: Near duplicates (medium, text similarity)
    unique, near_dups = find_near_duplicates(unique, threshold=0.85)
    
    # Phase 3: Semantic duplicates (slow, requires embeddings)
    # Optional: unique, semantic_dups = find_semantic_duplicates(unique, threshold=0.95)
    
    # Apply merge strategy
    final_chunks = apply_merge_strategy(unique, all_duplicates, strategy)
    
    write_jsonl(output_file, final_chunks)
```

## Step 3: Choose Strategy

| Strategy | When to Use |
|----------|-------------|
| `keep_first` | Fast, oldest version is authoritative |
| `keep_most_complete` | Best metadata wins |
| `merge_metadata` | Combine all metadata from duplicates |

## Step 4: Report Results

When done, report:
- Input chunk count (per file and total)
- Output chunk count
- Duplicates found (exact, near, semantic)
- Reduction percentage
- Merge actions taken
- Validation issues

# Deduplication Methods

## 1. Exact Duplicates (Fast)
Hash-based detection for identical content using MD5 of normalized text.

## 2. Near Duplicates (Medium)
SequenceMatcher ratio comparison with configurable threshold (default 0.85).

## 3. Semantic Duplicates (Slow)
Cosine similarity on embeddings with threshold (default 0.95). Requires embeddings.

# Cross-Source Deduplication

When merging from multiple sources, use priority:

```python
sources_config = [
    {'path': 'canonical.jsonl', 'priority': 1},  # Keep these
    {'path': 'curated.jsonl', 'priority': 2},    # Defer to canonical
]
```

# Output Format

```json
{
  "chunk_id": "...",
  "text": "...",
  "provenance": {
    "merged_from": ["chunk_1", "chunk_2"],
    "dedup_strategy": "merge_metadata"
  }
}
```

# References

| File | Contents |
|------|----------|
| `reference.md` | Detection algorithms, merge functions, validation |
