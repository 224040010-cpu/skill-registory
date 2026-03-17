---
name: knowledge-package-exporter
description: Package RAG knowledge into a portable bundle with manifest, README, and validation. Use for "export", "bundle", "package", "share knowledge", "prepare for deployment". For deduplication before export, use rag-chunk-deduplicator first.
bundle_scope: ops-agent
risk_level: L1
---

# Purpose

Create a portable, validated knowledge package from existing RAG chunks for sharing or deployment.

# Trigger

**Use when:**
- User mentions "export", "bundle", "package knowledge"
- User wants to "share knowledge", "prepare for deployment"
- User asks to "create a knowledge package"
- User needs to migrate RAG data between systems

**Do NOT use when:**
- User wants to deduplicate data (use `rag-chunk-deduplicator` first)
- User wants to query/search the knowledge base
- User is asking about RAG retrieval or embeddings
- User wants to analyze knowledge quality (use analytics skills)

# Workflow

```
1. Deduplicate → rag-chunk-deduplicator (recommended first)
2. Export     → THIS SKILL
```

**Recommended:** For full rebuild with deduplication built-in:
```bash
# Run from your feishu-mcp project directory
cd <feishu-mcp-project>/
python3 scripts/rebuild_all_rag.py
# Output: export/unified_v2/chunks.jsonl + manifest.json
```

## Step 1: Gather Requirements

Ask up front:
- Target schema requirements (fields, enums, required vs optional)
- Which data is production vs testing (e.g., closed vs processing tickets)
- Whether attachments must be included
- Expected bundle layout and naming conventions
- Target schema version (if migrating from older format)
- Language requirements (single/multi-language exports)

## Step 2: Build Bundle

ALWAYS produce these files:
- `chunks.jsonl` - Knowledge chunks (one JSON per line)
- `manifest.json` - Package metadata with schema version
- `README.md` - Human-readable description

Include `attachments/` if evidence references local files.

## Step 3: Enhance for Layer 2 (Optional but Recommended)

For knowledge graph traversal, add:
- `entity_type`: Classification (e.g., `issue`, `error_code`, `vehicle_brand`)
- `relationships`: Links to other entities

```python
chunk["entity_type"] = "issue"
chunk["relationships"] = [
    {"type": "affects_product", "target": "ProductName"},
    {"type": "has_solution", "target": "Solution text..."}
]
```

## Step 4: Validate

Run validation checks:
- No local machine paths in `evidence` (e.g., `/Users/...`)
- Required fields present on all chunks
- `rag_type` set on all chunks (canonical/curated)
- All chunks have valid `language` field
- No duplicate `chunk_id` values
- Attachment files exist for all `evidence` references
- Layer 2 fields present: `entity_type`, `relationships` (recommended)

## Step 5: Report

When done, report:
- Bundle path
- Counts (chunks, attachments, by language, by source_type)
- Layer 2 coverage (entity_type count, chunks with relationships)
- Any missing required fields or evidence
- Schema migrations applied
- Bundle size
- Validation warnings/errors

# Key Patterns

## Manifest Format (v2.0)

```json
{
  "dataset_name": "knowledge_bundle",
  "schema_version": "v2",
  "build_at": "2026-03-10T12:00:00Z",
  "counts": { "chunks": 1823 },
  "layer_counts": { "process": 1823 },
  "freshness_stats": { "daily": 1823 },
  "entity_type_counts": { "issue": 1823 },
  "relationship_stats": { "chunks_with_relationships": 1726 }
}
```

## Layer 2 Knowledge Graph Fields (IMPORTANT)

Add these fields to enable Knowledge Graph indexing:

```json
{
  "entity_type": "issue",
  "entity": "VRC-1234",
  "entity_normalized": "vrc_1234",
  "relationships": [
    {"type": "resolved_by", "target": "Replace CCU module", "properties": {"category": "replacement"}},
    {"type": "caused_by", "target": "Hardware failure", "properties": {"category": "hardware"}}
  ]
}
```

**Entity types**: `diagnostic_pattern`, `issue`, `error_code`, `component`, `vehicle_brand`

**Relationship types**: `detected_in`, `resolved_by`, `caused_by`, `has_signal`, `compatible_with`

## Anti-Pattern: One Chunk Per Detection

**❌ WRONG**: Creating one chunk per signal detection
```
12,527 chunks = one chunk per (case × signal detection)
```

**✅ CORRECT**: Consolidate into entity chunks
```
11 rule chunks (entity_type: diagnostic_pattern)
499 case chunks (entity_type: issue) with detected_signals list
```

## Evidence Rules

- Use relative paths: `attachments/file.txt`
- URLs are OK: `https://...`
- NEVER use local paths: `/Users/...` or `C:\...`
- Empty `[]` if no local evidence

## Language Detection

```python
def detect_language(text):
    cjk_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    if cjk_chars / max(len(text), 1) > 0.3:
        return 'zh'
    return 'en'
```

# References

| File | Contents |
|------|----------|
| `references/implementation.md` | Full code examples, schema migration, raw data preservation |
