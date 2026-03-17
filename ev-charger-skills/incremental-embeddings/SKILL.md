---
name: incremental-embeddings
description: Fast embedding updates for RAG knowledge base - only encodes new/changed chunks. Use after uploading knowledge packages, running regenerate_cloud_production.sh, or when embeddings are outdated. Triggers on "update embeddings", "refresh embeddings", "incremental embed", "semantic index update".
---

# Incremental Embedding Update

Fast embedding updates for RAG knowledge base - only encodes new/changed chunks.

## When to Use

- After uploading new knowledge to EC2 (`feishu_mcp`, `jira`, etc.)
- After running `regenerate_cloud_production.sh`
- When embeddings are outdated (warning: "Embeddings outdated X vs Y chunks")
- Any time you need to update semantic search index

## Performance

| Method | Time | When to Use |
|--------|------|-------------|
| **Incremental** | ~5 min | Default - only new chunks |
| Full rebuild | ~45 min | First time or after schema change |

## Quick Command

```bash
# Set EC2_HOST to your EC2 instance alias or IP
ssh $EC2_HOST "cd <project-dir> && python3 rag/shared/scripts/incremental_embeddings.py"
```

## How It Works

1. Loads existing embeddings from `rag/cloud/production/indexes/semantic/`
2. Loads all current chunks from `rag/cloud/production/knowledge/`
3. Identifies new chunks (by `chunk_id` not in existing embeddings)
4. Encodes **only new chunks** using sentence-transformers
5. Merges new embeddings with existing ones
6. Saves updated embeddings

## Output Location

```
rag/cloud/production/indexes/semantic/
├── embeddings.npz      # Numpy array (N, 384)
├── chunk_ids.json      # List of chunk IDs matching embedding order
└── metadata.json       # Build info (if exists)
```

## Example Output

```
Loading existing embeddings...
  Existing: 21385 chunks
Loading current chunks...
  Total chunks: 39034
  New chunks to encode: 3685
Loading model...
Encoding 3685 new chunks...
Batches: 100%|██████████| 58/58 [05:30<00:00]
  New embeddings shape: (3685, 384)
Done! Total embeddings: 39034
```

## Full Workflow: Upload + Merge + Embeddings

```bash
# Set EC2_HOST to your EC2 instance alias or IP, EC2_DIR to your project directory
# 1. Upload knowledge package from local
./scripts/upload_knowledge.sh feishu_mcp ./rag/cloud/sources/feishu_mcp

# 2. Regenerate production RAG on EC2
ssh $EC2_HOST "cd $EC2_DIR && bash rag/shared/scripts/regenerate_cloud_production.sh"

# 3. Update embeddings (incremental - fast!)
ssh $EC2_HOST "cd $EC2_DIR && python3 rag/shared/scripts/incremental_embeddings.py"
```

## Force Full Rebuild

If you need a complete rebuild (e.g., after model change):

```bash
# Delete existing embeddings first
ssh $EC2_HOST "rm -rf $EC2_DIR/rag/cloud/production/indexes/semantic/*"

# Then run incremental (will encode all chunks)
ssh $EC2_HOST "cd $EC2_DIR && python3 rag/shared/scripts/incremental_embeddings.py"
```

## Verify Embeddings

```bash
ssh $EC2_HOST "cd $EC2_DIR && python3 << 'EOF'
import json, numpy as np
ids = json.load(open('rag/cloud/production/indexes/semantic/chunk_ids.json'))
emb = np.load('rag/cloud/production/indexes/semantic/embeddings.npz')
print(f'Chunks: {len(ids)}')
print(f'Embeddings: {emb[\"embeddings\"].shape}')
EOF"
```

## Model Info

- **Model**: `paraphrase-multilingual-MiniLM-L12-v2`
- **Embedding dimension**: 384
- **Languages**: 50+ (multilingual)
- **Batch size**: 64

## Related Skills

- `knowledge-package-exporter` - Package knowledge for upload
- `feishu-doc-crawler` - Extract Feishu content
- `excel-to-rag` - Convert Excel to RAG chunks
