# Knowledge Package Exporter - Implementation Details

## Multi-language Content Handling

### Language-specific exports
```python
def filter_by_language(chunks, target_lang, include_universal=True):
    """Filter chunks for target language."""
    result = []
    for chunk in chunks:
        lang = chunk.get('language', 'en')
        if lang == target_lang:
            result.append(chunk)
        elif include_universal and lang == 'universal':
            result.append(chunk)
    return result
```

### Bilingual content
For chunks with both English and Chinese content:
- Keep as single chunk if tightly coupled (error codes with dual descriptions)
- Split into separate chunks if content is independent
- Tag with `language: bilingual` and include both `text_en` and `text_zh` fields

## Bundle Compression

For large bundles:
```bash
# Create compressed archive
tar -czvf knowledge_package_v1.tar.gz knowledge_package/

# Or use zip for cross-platform
zip -r knowledge_package_v1.zip knowledge_package/
```

Include compression info in manifest:
```json
{
  "compression": {
    "format": "gzip",
    "original_size_mb": 150,
    "compressed_size_mb": 45
  }
}
```

## Schema Version Migration

### Version tracking
Include schema version in manifest:
```json
{
  "schema_version": "2.0",
  "previous_version": "1.0",
  "migration_applied": true
}
```

### Migration patterns
When upgrading from v1 to v2 schema:
```python
def migrate_v1_to_v2(chunk):
    """Migrate chunk from schema v1 to v2."""
    migrated = chunk.copy()
    
    # Rename fields
    if 'source' in migrated:
        migrated['source_type'] = migrated.pop('source')
    
    # Add required fields with defaults
    if 'rag_type' not in migrated:
        migrated['rag_type'] = 'curated'
    
    # Restructure nested fields
    if 'meta' in migrated:
        migrated['tags'] = migrated.pop('meta')
    
    # Add version marker
    migrated['_schema_version'] = '2.0'
    
    return migrated
```

### Backward compatibility
When target system needs older schema:
```python
def downgrade_v2_to_v1(chunk):
    """Downgrade chunk for v1 compatibility."""
    downgraded = chunk.copy()
    
    # Reverse field renames
    if 'source_type' in downgraded:
        downgraded['source'] = downgraded.pop('source_type')
    
    # Remove v2-only fields
    for field in ['rag_type', '_schema_version']:
        downgraded.pop(field, None)
    
    return downgraded
```

## Preserving Full Raw Data

### Why preserve raw details
Downstream agents often need the **complete original data**, not just summaries. Common complaints:
- "Truncated descriptions"
- "Missing message threads"  
- "No timestamps on messages"
- "Agent names stripped"

### Raw data preservation pattern
Include `raw_detail` in ticket chunks for full retrieval:
```python
chunk = {
    "chunk_id": "...",
    "text": "...",  # Formatted summary for embedding
    "raw_detail": {
        "ticket_id": detail.get("id"),
        "order_no": detail.get("orderNo"),
        "sn": detail.get("sn"),
        "contact_name": detail.get("contactName"),
        "contact_email": detail.get("contactEmail"),
        "deal_user_name": detail.get("dealUserName"),
        "message_count": len(messages),
        "attachment_count": len(file_list),
    },
    "case_fields": {
        "symptoms": [...],
        "root_cause": "...",
        "root_cause_category": "hardware|firmware|network|config|...",
        "solution": "...",
        "solution_category": "replacement|config_change|firmware_update|...",
        "is_resolved": True,
    }
}
```

### Full message thread formatting
```python
def format_messages(messages):
    """Format messages with full context."""
    lines = []
    for msg in messages:
        agent = msg.get("createByName", "Unknown")
        timestamp = format_timestamp(msg.get("createTime"))
        content = msg.get("information", "")
        files = msg.get("fileList", [])
        
        lines.append(f"[{timestamp}] {agent}:")
        lines.append(content)
        
        for f in files:
            lines.append(f"  Attachment: {f.get('fileName')}")
        lines.append("")
    return "\n".join(lines)
```

### Also export raw source data
In addition to RAG chunks, export the raw ticket details for agents that need full access:
```
export/
├── knowledge_bundle/
│   ├── chunks.jsonl      # RAG chunks with embeddings
│   └── manifest.json
└── raw_ticket_details/
    ├── all_ticket_details.jsonl  # Full JSON for each ticket
    └── README.md
```

## Validation Checks

Complete checklist:
- No local machine paths in `evidence`
- Required fields present on all `ticket`-type chunks
- `rag_type` set on all chunks (canonical/curated/etc.)
- Manifest includes bundle name, version, build time, counts
- All chunks have valid `language` field
- No exact duplicate `chunk_id` values
- Schema version is consistent across all chunks
- Attachment files exist for all `evidence` references
- `raw_detail` included for ticket chunks (if full data needed downstream)
