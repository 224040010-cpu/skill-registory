# EV Charger Knowledge Base v4.0

A shareable Cursor skill package containing comprehensive EV charger knowledge for diagnostics, troubleshooting, and support.

## Package Contents

| File | Description | Size |
|------|-------------|------|
| `chunks.jsonl` | 6,114 knowledge chunks | 7 MB |
| `SKILL.md` | Main skill with query patterns | 8 KB |
| `LOOKUP_TABLES.md` | Parseable JSON lookup tables | 10 KB |
| `DATA_RELATIONSHIPS.md` | Entity relationship maps | 8 KB |
| `README.md` | This file | 3 KB |

## Statistics

| Metric | Value |
|--------|-------|
| Total Chunks | 6,114 |
| Error Code Entries | 1,271 |
| FAQ Entries | 704 |
| FMEA Entries | 391 |
| Documents | 3,556 |
| English Content | 4,272 |
| Chinese Content | 1,841 |

## How to Share

### Option 1: Copy Folder
```bash
cp -r ~/.cursor/skills/ev-charger-knowledge /path/to/destination/
```

### Option 2: Zip Archive
```bash
cd ~/.cursor/skills
zip -r ev-charger-knowledge.zip ev-charger-knowledge/
# Send ev-charger-knowledge.zip to recipient
```

### Option 3: Git Repository
```bash
cd ~/.cursor/skills/ev-charger-knowledge
git init
git add .
git commit -m "EV Charger Knowledge Base v4.0"
git remote add origin <your-repo-url>
git push -u origin main
```

## How Recipients Use It

1. **Place in skills folder:**
```bash
# Unzip or copy to:
~/.cursor/skills/ev-charger-knowledge/
```

2. **Skill auto-triggers on:**
- "error code", "故障码", "what does code mean"
- "charging problem", "充电失败"
- "troubleshoot", "diagnose"
- Vehicle names: "BMW", "Tesla", "VW"

3. **Query the knowledge base:**
```python
import json

# Load chunks
with open('chunks.jsonl', 'r') as f:
    chunks = [json.loads(line) for line in f if line.strip()]

# Filter by type
error_codes = [c for c in chunks if c.get('source_type') == 'error_code']
faq = [c for c in chunks if c.get('source_type') == 'faq']
fmea = [c for c in chunks if c.get('source_type') == 'fmea']
```

## Extending the Knowledge

To add new knowledge:

1. Create new JSONL entries:
```json
{
  "chunk_id": "custom:my_knowledge:001",
  "source_system": "custom",
  "source_type": "document",
  "title": "My Knowledge Entry",
  "text": "Content here...",
  "language": "en",
  "tags": {"rag_type": "curated"}
}
```

2. Append to `chunks.jsonl`

3. Update statistics in `SKILL.md`

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v4.0.0 | 2026-03-02 | Full rebuild, 70% deduplication, 6,114 chunks |
| v3.0.0 | 2026-03-01 | Added vehicle compatibility |
| v2.0.0 | 2026-02-28 | Added vision-based image analysis |
| v1.0.0 | 2026-02-27 | Initial extraction |

## Related Skills

| Skill | Purpose |
|-------|---------|
| `ev-charger-troubleshoot` | Step-by-step diagnosis |
| `vehicle-compatibility-rag` | Vehicle-specific queries |
| `log-analyzer` | Log file analysis |
| `case-search` | Historical case search |

## Source Project

Built from: `feishu-mcp` project
Pipeline: `scripts/full_pipeline_rebuild.py`
