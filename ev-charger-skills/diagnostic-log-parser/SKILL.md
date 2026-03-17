---
name: diagnostic-log-parser
description: ETL skill - convert raw logs to structured JSONL for RAG ingestion. Use for DATA PIPELINE tasks like "parse logs", "extract faults", "log to JSON", "ingest logs". NOT for analyzing/diagnosing issues - use log-analyzer for that.
bundle_scope: diagnosis-agent
risk_level: L1
---

# Purpose

Transform raw log files into structured JSONL chunks for RAG pipelines (ETL/data transformation).

# Trigger

**Use when:**
- User says "parse this log file into JSONL"
- User wants to "extract faults for RAG ingestion"
- User asks to "build log knowledge base"
- User mentions "convert logs to chunks", "ingest logs"
- Data pipeline/ETL tasks for log processing

**Do NOT use when:**
- User asks "what's wrong in this log?" → use `log-analyzer`
- User wants to "diagnose the issue from logs" → use `log-analyzer`
- User wants real-time log monitoring
- User is asking about specific errors (analysis, not ETL)

| Task | Skill |
|------|-------|
| Parse log file into JSONL | **THIS SKILL** |
| Extract faults for RAG ingestion | **THIS SKILL** |
| Build log knowledge base | **THIS SKILL** |
| What's wrong in this log? | `log-analyzer` |
| Diagnose the issue from logs | `log-analyzer` |

# Workflow

## Step 1: Detect Log Format

Sample first 100 lines and match against known patterns:
- `standard` - ISO timestamp + level + module + message
- `syslog` - Traditional syslog format
- `android` - Android logcat format
- `cellular` - Charger-specific format
- `json_line` - JSON per line

## Step 2: Parse Lines

```python
def parse_log_file(filepath, output_path, faults_only=False):
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    
    format_name, pattern = detect_log_format(lines[:100])
    events = parse_multiline_logs(lines, pattern)
    
    if faults_only:
        events = [e for e in events if is_fault_event(e)]
    
    chunks = [event_to_rag_chunk(e, filepath, i) for i, e in enumerate(events)]
    
    with open(output_path, 'w') as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
```

## Step 3: Classify Events

- **Fault detection**: Check level (ERROR, FATAL) or message content
- **Module classification**: network, power, storage, hardware, system, application
- **Severity scoring**: 1 (VERBOSE) to 7 (FATAL), boosted for critical keywords

## Step 4: Extract Error Codes

Multiple patterns for different code formats:
- `error: CODE123`
- `[E0001]`
- `0x3001`

## Step 5: Aggregate Sessions

Group events by time gaps (default 5 minutes) into session summaries.

# Output Format

Each log event becomes a RAG chunk:

```json
{
  "chunk_id": "log:file.log:42:a1b2c3",
  "source_type": "log_event",
  "title": "NetworkModule: Connection timeout",
  "text": "Time: ...\nModule: ...\nLevel: ERROR\nMessage: ...",
  "tags": {
    "rag_type": "curated",
    "log_level": "ERROR",
    "module_category": "network",
    "severity": 5,
    "is_fault": true
  }
}
```

# Reporting

When done, report:
- Total lines processed
- Events parsed successfully
- Parse failures (with samples)
- Fault events found
- Module distribution
- Severity distribution
- Error codes found
- Time range covered

# References

| File | Contents |
|------|----------|
| `reference.md` | Regex patterns, classification maps, code examples |
