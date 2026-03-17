---
name: extracting-excel-to-rag
description: |
  Extract structured knowledge from Excel/CSV/Google Sheets and output RAG-ready JSONL chunks. Use when user mentions Excel, XLSX, CSV, spreadsheet, tabular data, FMEA tables, error-code tables, data dictionaries, or converting tables to knowledge chunks for RAG.
---

# Purpose

Extract structured knowledge from ANY Excel/CSV file for RAG pipelines, regardless of file structure.

# Trigger

**Use when:**
- User provides Excel/CSV/XLSX files for processing
- Keywords: Excel, spreadsheet, CSV, XLSX, tabular, FMEA table, error codes table
- Converting tables to JSONL/RAG chunks
- Google Sheets API integration

**Do NOT use when:**
- Analyzing log files → use `log-analyzer` or `diagnostic-log-parser`
- Extracting from PDFs/images → use `image-extraction`
- Processing Feishu docs → use `feishu-doc-crawler`

## Core Principles

1. **NEVER Assume Structure** - Each sheet is different
2. **Inspect Before Processing** - Always run inspection first
3. **Each Sheet is Independent** - Headers may differ across sheets

## Step-by-Step Workflow

### Phase 1: Discovery

```python
import pandas as pd

xlsx = pd.ExcelFile("file.xlsx")
print(f"Sheets: {xlsx.sheet_names}")

# Inspect each sheet WITHOUT assuming header position
for sheet_name in xlsx.sheet_names:
    df = pd.read_excel(xlsx, sheet_name=sheet_name, header=None, nrows=20)
    print(f"\n=== Sheet: {sheet_name} ({df.shape}) ===")
    for i in range(min(10, len(df))):
        row_vals = [f"[{j}]{str(v)[:20]}" for j, v in enumerate(df.iloc[i]) if pd.notna(v)]
        print(f"Row {i}: {' | '.join(row_vals[:6])}")
```

### Phase 2: Mapping

Identify header row by looking for rows with:
- Multiple text cells (not numbers)
- Matches expected field names
- Followed by data rows

| Pattern | Header Row | Example |
|---------|------------|---------|
| Standard | 0 | Simple Excel files |
| Title + Header | 1-2 | Files with title row |
| Multi-row Header | 3-5 | Complex reports |

For mapping functions, see `references/reference.md`.

### Phase 3: Validation

**CRITICAL: Always validate mapping before processing!**

```python
# Show 5 sample records to verify mapping
for field, info in mapping.items():
    val = df.iloc[data_row, info['index']]
    print(f"  {field}: {val}")
```

### Phase 4: Extraction

Extract records and convert to RAG format. See `references/reference.md` for full functions.

## Quick Reference Commands

```python
# Inspect any Excel file
import pandas as pd
xlsx = pd.ExcelFile('file.xlsx')
print('Sheets:', xlsx.sheet_names)
for s in xlsx.sheet_names:
    df = pd.read_excel(xlsx, s, header=None, nrows=10)
    print(f'\n{s}: {df.shape}')
```

```python
# Count records in JSONL output (cross-platform)
with open('output.jsonl') as f:
    print(sum(1 for _ in f), 'records')

# Check a sample record
import json
with open('output.jsonl') as f:
    print(json.dumps(json.loads(f.readline()), indent=2, ensure_ascii=False))
```

## Verification Checklist

- [ ] Inspected ALL sheets (not just first one)
- [ ] Identified correct header row for EACH sheet
- [ ] Validated mapping with sample data
- [ ] Checked for missing required fields
- [ ] Handled empty/merged cells
- [ ] Verified output has meaningful text content
- [ ] Spot-checked random records in output

## Generic Extractor Script

Use the zero-hardcoding extractor in `feishu-mcp/scripts/generic_excel_extractor.py`:

```bash
# Run from your feishu-mcp project directory
cd <feishu-mcp-project>/
python3 scripts/generic_excel_extractor.py .
```

**Key Principles - ZERO HARDCODING:**
- Uses column headers AS-IS (no semantic mapping like `error_code` → `告警码`)
- Content type inferred ONLY from filename/sheetname
- NO predefined column patterns
- Deduplicates files and chunks automatically
- **Auto-adds `entity_type`** for relationship chunks (vehicle_brand, issue, component)

**Output:** `export/generic_excel_chunks.jsonl` with v2 schema

**Layer 2 Graph Support:** Relationship chunks automatically get:
- `entity_type`: vehicle_brand, issue, component, unknown
- `entity`: Extracted entity value (e.g., "BMW iX", "4G断线")
- `entity_normalized`: Lowercase with underscores (e.g., "bmw_ix")

For full RAG rebuild including existing data:
```bash
# Run from feishu-mcp project directory
python3 scripts/rebuild_all_rag.py
# Output: export/unified_v2/chunks.jsonl + manifest.json
```

## References

| File | Contents |
|------|----------|
| `scripts/generic_excel_extractor.py` | Zero-hardcoding generic extractor |
| `references/reference.md` | Full code for mapping, extraction, RAG conversion |
| `references/pitfalls.md` | Common pitfalls and solutions |
| `references/fields.md` | Specialized field patterns (Error Code, FMEA, FAQ) |

## Summary

1. **INSPECT** - Look at every sheet before processing
2. **DISCOVER** - Find headers dynamically
3. **MAP** - Build column mapping based on content
4. **VALIDATE** - Show samples before bulk processing
5. **EXTRACT** - Handle errors gracefully
6. **VERIFY** - Check output quality

**Remember: Every Excel file is unique. Treat each one as a new puzzle.**
