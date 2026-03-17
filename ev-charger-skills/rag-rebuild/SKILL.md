---
name: rag-rebuild
description: |
  Rebuild local RAG knowledge base with 3-layer architecture: consolidation, knowledge graph, embeddings, and relationships. Use when user mentions "rebuild RAG", "update RAG", "regenerate production", "consolidate knowledge", "update embeddings", "build relationships", "refresh semantic index", "RAG pipeline", "relationship coverage", or after uploading new knowledge packages. Also use for checking RAG build status or offloading heavy work to EC2.
---

# RAG Rebuild

Orchestrates the full 3-layer RAG rebuild pipeline.

## 3-Layer Architecture

```
LAYER 1: DETERMINISTIC RULES (Exact Match)
├── MAC Pattern → Vehicle lookup
├── Compatibility Matrix (vehicle × charger × region)
└── Error Code → Direct solution rules

LAYER 2: KNOWLEDGE GRAPH (Graph Traversal)
├── Entity Graph (vehicle, issue, solution relationships)
├── Issue → Solution mappings
└── Component → Failure mode mappings

LAYER 3: SEMANTIC EMBEDDINGS (Similarity Search)
├── Vector embeddings for all chunks
├── Error Code ↔ FMEA semantic matching
└── FMEA ↔ Cases semantic matching
```

## Quick Commands

```bash
# Run from project root (cloud-agent/)
# Full local rebuild (all 3 layers)
python3 scripts/consolidate_rag.py
python3 scripts/build_knowledge_graph.py
python3 scripts/build_embeddings.py
python3 scripts/build_relationships.py

# Check status only
python3 scripts/build_knowledge_graph.py --stats
python3 scripts/build_embeddings.py --estimate-only
```

## Pipeline Steps

### Step 1: Consolidate RAG Sources

```bash
python3 scripts/consolidate_rag.py
```

**What it does:**
- Loads chunks from `rag/sources/*/chunks.jsonl`
- **Smart deduplication**: Prefers chunks with more complete data (entity_type, relationships)
- Routes by `rag_type` (canonical vs curated)
- Builds basic indexes

**Output:** `rag/production/knowledge/{canonical,curated}.jsonl`

### Step 2: Build Knowledge Graph (Layer 1 + 2)

```bash
python3 scripts/build_knowledge_graph.py
```

**Layer 1 outputs:**
- `mac_index.json` - MAC prefix → Vehicle lookup
- `compatibility_matrix.json` - Vehicle × Charger compatibility
- `error_rules.json` - Error code → direct solutions

**Layer 2 outputs:**
- `entity_graph.json` - Entity relationship graph
- `issue_solution_index.json` - Issue → Solution mappings
- `component_failure_index.json` - Component → Failure modes

### Step 3: Build Embeddings (Layer 3)

```bash
python3 scripts/build_embeddings.py        # Auto-detect incremental/full
python3 scripts/build_embeddings.py --full # Force full rebuild
```

**Output:** `embeddings.npy`, `embeddings_index.json`, `embeddings_meta.json`

### Step 4: Build Semantic Relationships (Layer 3)

```bash
python3 scripts/build_relationships.py --threshold 0.5
```

**Output:** `embedding_relationships.json`

## Local vs EC2 Offloading

| Task | Local Time | EC2 Time | Recommendation |
|------|------------|----------|----------------|
| Consolidate | <1s | N/A | **Local** |
| Knowledge Graph | <1s | N/A | **Local** |
| Embeddings | ~25s (14K chunks) | ~10s | **EC2 for large datasets** |
| Relationships | <1s | <1s | **Local** |

### When to Use EC2

Use EC2 for embedding generation when:
- Chunks > 50,000 (saves significant time/power)
- Full rebuild needed (not incremental)
- Running on battery power

### EC2 Offloading Workflow

```bash
# 1. Local: Consolidate and build knowledge graph
python3 scripts/consolidate_rag.py
python3 scripts/build_knowledge_graph.py

# 2. Upload to EC2 (via rsync or scp)
rsync -avz rag/production/knowledge/ ec2-user@EC2_HOST:~/rag/production/knowledge/

# 3. EC2: Build embeddings (faster GPU/more RAM)
ssh ec2-user@EC2_HOST "cd ~/rag && python3 scripts/build_embeddings.py --full"

# 4. Download embeddings back
rsync -avz ec2-user@EC2_HOST:~/rag/production/indexes/embeddings* rag/production/indexes/

# 5. Local: Build relationships
python3 scripts/build_relationships.py
```

### Using incremental-embeddings Skill (EC2)

For EC2-only embedding updates:
```bash
# On EC2, use the incremental-embeddings skill
# See: ~/.cursor/skills/incremental-embeddings/SKILL.md
```

## File Structure

```
rag/
├── sources/                    # Input packages
│   ├── feishu_mcp/chunks.jsonl
│   ├── chrome_mcp/chunks.jsonl
│   ├── vehicle_relationships/chunks.jsonl  # ⚠️ Must preserve entity_type, relationships
│   └── ...
│
├── production/                 # Output
│   ├── knowledge/
│   │   ├── canonical.jsonl
│   │   └── curated.jsonl
│   ├── cases/
│   │   └── case_index.jsonl
│   └── indexes/
│       ├── mac_index.json              # Layer 1
│       ├── compatibility_matrix.json   # Layer 1
│       ├── error_rules.json            # Layer 1
│       ├── entity_graph.json           # Layer 2
│       ├── issue_solution_index.json   # Layer 2
│       ├── component_failure_index.json# Layer 2
│       ├── embeddings.npy              # Layer 3
│       ├── embeddings_meta.json        # Layer 3
│       └── embedding_relationships.json# Layer 3
│
scripts/
├── consolidate_rag.py          # Step 1 (smart dedup)
├── build_knowledge_graph.py    # Step 2 (Layer 1+2)
├── build_embeddings.py         # Step 3 (Layer 3)
└── build_relationships.py      # Step 4 (Layer 3)
```

## Checking Coverage

```bash
python3 scripts/build_knowledge_graph.py --stats
```

**Example output:**
```
--- LAYER 1: DETERMINISTIC RULES ---
MAC Index: 49 prefixes, 303 full MACs
Compatibility Matrix: 560 vehicles, 2070 lookup entries
Error Rules: 25 codes

--- LAYER 2: KNOWLEDGE GRAPH ---
Entity Graph: 197 entities, 1004 relations
Issue-Solution: 1807 issues, 11 with solutions

--- LAYER 3: SEMANTIC EMBEDDINGS ---
Embeddings: 13979 chunks, 384 dims
Embedding Relations: 349 error→FMEA, 1787 FMEA→cases
```

## Troubleshooting

### "entity_type is None" after consolidation
- **Cause**: Corrupted duplicate chunks in source files
- **Fix**: Check Section 6 of KNOWLEDGE_PACKAGE_README.md
- **Prevention**: Smart dedup prefers chunks with more complete data

### Low relationship coverage
- Lower threshold: `--threshold 0.4`
- Check if FMEA/error_code chunks exist in sources

### Embeddings out of date
- Check `embeddings_meta.json` for content hash
- If hash differs from current chunks, run `--full` rebuild

## Related Skills

- `incremental-embeddings` - EC2 server embedding updates
- `knowledge-package-exporter` - Package knowledge for upload
- `extracting-excel-to-rag` - Convert Excel to RAG chunks
- `ev-charger-knowledge` - Has DATA_RELATIONSHIPS.md reference
