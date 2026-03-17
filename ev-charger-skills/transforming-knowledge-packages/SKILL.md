---
name: transforming-knowledge-packages
description: Transform RAG chunks to KNOWLEDGE_PACKAGE schema v2 with required fields (knowledge_layer, freshness_level, unique titles). Use when user mentions "knowledge package", "RAG export", "transform chunks", "schema migration", "prepare for cloud RAG", "export to EC2", "layer_counts", "knowledge_layer", or asks to convert existing JSONL data to the standard package format.
---

# Transforming Knowledge Packages

Transform RAG data to KNOWLEDGE_PACKAGE schema v2 for cloud RAG deployment.

## Purpose

Convert raw/legacy RAG chunks into compliant knowledge packages with:
- Required fields: `chunk_id`, `source_system`, `source_type`, `title`, `text`, `tags`, `provenance`
- Layer classification: `knowledge_layer` (norm/evidence/relation/process)
- Freshness tagging: `freshness_level` (static/daily/realtime)
- Unique titles (no duplicates)
- Special fields: `fmea_fields`, `error_code_fields`, `case_fields`
- **Layer 2 Graph fields**: `entity_type`, `entity`, `relationships` (for relationship chunks)

## Trigger

**Use when:** knowledge package, RAG export, transform chunks, schema migration, cloud RAG, EC2 upload, layer_counts, knowledge_layer, freshness_level

**Do NOT use when:** querying existing RAG, analyzing logs, troubleshooting issues

## Layer Mapping

| source_type | knowledge_layer | freshness_level |
|-------------|-----------------|-----------------|
| doc, document, faq, error_code, wiki_doc, code, rule | norm | static |
| fmea, relationship, vehicle | relation | static |
| ticket, field_experience, case | process | daily |
| log | evidence | daily |
| ocr | evidence | static |

**Note:** `other` source_types default to `norm` + `static`.

## Workflow

### Step 1: Analyze Source Data

```bash
# Count chunks and check current schema
wc -l input.jsonl
head -n 2 input.jsonl | python3 -m json.tool
```

Check for:
- Missing required fields
- Invalid `source_system` (must be: eu, us, other)
- Missing `tags.rag_type` (must be: canonical, curated)

### Step 2: Run Transformation

**Recommended:** Use the unified rebuild script in `feishu-mcp`:

```bash
# Run from your feishu-mcp project directory
cd <feishu-mcp-project>/
python3 scripts/rebuild_all_rag.py
```

This processes ALL data sources:
- Existing JSONL files in `download/chrome-scan/rag_data/`
- All Excel/CSV files (using zero-hardcoding generic extractor)
- Deduplicates and transforms to v2 schema

**Output:** `export/unified_v2/chunks.jsonl` + `manifest.json`

Or inline transformation:

```python
# Required field mapping
LAYER_MAP = {
    'doc': ('norm', 'static'),
    'faq': ('norm', 'static'),
    'error_code': ('norm', 'static'),
    'fmea': ('relation', 'static'),
    'relationship': ('relation', 'static'),
    'field_experience': ('process', 'daily'),
    'ticket': ('process', 'daily'),
    'log': ('evidence', 'realtime'),
    'ocr': ('evidence', 'static'),
}

for chunk in chunks:
    st = chunk.get('source_type', 'doc')
    layer, freshness = LAYER_MAP.get(st, ('norm', 'static'))
    chunk['knowledge_layer'] = layer
    chunk['freshness_level'] = freshness
```

### Step 3: Validate Output

```bash
python3 scripts/validate.py /path/to/output/
```

Validation checks:
- [ ] All chunks have required fields
- [ ] `tags.rag_type` is canonical or curated
- [ ] `source_system` is eu, us, or other
- [ ] No local machine paths in evidence
- [ ] All titles are unique
- [ ] `knowledge_layer` and `freshness_level` present
- [ ] **Relationship chunks have `entity_type`** (for Layer 2 graph)

### Step 3.5: Add Entity Type for Relationship Chunks

**CRITICAL for Layer 2 graph traversal.** All `source_type: "relationship"` chunks must have:

```python
# Required for relationship chunks
if chunk['source_type'] == 'relationship':
    chunk['entity_type'] = infer_entity_type(chunk)  # vehicle_brand, error_code, component, issue
    chunk['entity'] = extract_entity(chunk)           # "BMW iX", "0x3001", etc.
    chunk['entity_normalized'] = normalize(entity)    # "bmw_ix", "0x3001"
```

| entity_type | Example entities |
|-------------|------------------|
| `vehicle_brand` | BMW iX, Tesla Model 3, VW ID.4 |
| `error_code` | 0x3001, 604B, BMS_TIMEOUT |
| `component` | CCU, TCU, ECU, 液冷系统 |
| `issue` | 4G断线, 充电中断 |

### Step 4: Generate Manifest

Manifest must include:

```json
{
  "dataset_name": "your_agent_knowledge",
  "schema_version": "v2",
  "build_at": "2026-03-10T12:00:00Z",
  "counts": {"chunks": 3112},
  "layer_counts": {
    "norm": 2172,
    "evidence": 14,
    "relation": 885,
    "process": 41
  }
}
```

### Step 5: Copy to Cloud Agent

```bash
mkdir -p /path/to/cloud-agent/rag/sources/<agent_name>/
cp chunks.jsonl manifest.json /path/to/cloud-agent/rag/sources/<agent_name>/
```

## Quality Fixes

Common issues to fix during transformation:

| Issue | Fix |
|-------|-----|
| Empty chunks | Filter: skip if title AND text empty |
| Placeholder entries | Filter: skip minimal "issue: X \| solution: Y" |
| Duplicate titles | Add distinguishing suffix (row#, hash) |
| Invalid source_system | Normalize to "other" |
| Invalid rag_type | Set based on source_type |
| Local machine paths | Remove or convert to relative |

## Special Fields

### FMEA chunks → `fmea_fields`

```json
{
  "fmea_fields": {
    "failure_mode_id": "FM-001",
    "components": ["CCU", "sensor"],
    "severity": 8,
    "occurrence": 5,
    "detection": 7,
    "rpn": 280
  }
}
```

### Error codes → `error_code_fields`

```json
{
  "error_code_fields": {
    "code": "604B",
    "code_hex": "0x604B",
    "description_zh": "温湿度变送器通讯异常告警",
    "trigger_condition": "...",
    "maintenance_guide": "...",
    "severity": "warning",
    "components": ["DECU", "传感器"]
  }
}
```

### Cases/tickets → `case_fields`

```json
{
  "case_fields": {
    "symptoms": ["4G断线", "uptime低"],
    "root_cause": "运营商问题",
    "root_cause_category": "network",
    "solution": "更新APN",
    "solution_category": "config_change",
    "is_resolved": true
  }
}
```

## Output Report

After transformation, report:

1. **Agent name**: e.g., `feishu_mcp`
2. **Chunk count**: `wc -l chunks.jsonl`
3. **Schema version**: from manifest.json
4. **Layer counts**: norm/evidence/relation/process

## References

- Full schema: See KNOWLEDGE_PACKAGE_README.md in project
- Validation script: `scripts/validate.py`
- Transform script: `scripts/transform.py`
