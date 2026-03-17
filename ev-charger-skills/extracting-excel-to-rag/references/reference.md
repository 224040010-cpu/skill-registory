# Excel to RAG - Reference

## Dynamic Column Mapping

```python
def find_column_by_keywords(headers: list, keywords: list) -> int:
    """Find column index by matching keywords in header text."""
    for idx, header in enumerate(headers):
        if pd.isna(header):
            continue
        header_lower = str(header).lower()
        for keyword in keywords:
            if keyword.lower() in header_lower:
                return idx
    return -1  # Not found
```

## Build Field Mapping Per Sheet

```python
def build_mapping(df: pd.DataFrame, header_row: int) -> dict:
    """Build column mapping for a specific sheet."""
    headers = df.iloc[header_row].tolist()
    
    FIELD_PATTERNS = {
        'code': ['error', 'code', '故障码', '告警码', 'alarm'],
        'description': ['description', '描述', '说明', 'desc', '信息'],
        'severity': ['severity', '严重', '级别', 'level', 'S'],
        'cause': ['cause', '原因', 'reason', '根因'],
        'solution': ['solution', '解决', '措施', '处理', 'action'],
        'trigger': ['condition', '条件', 'trigger', '判断'],
    }
    
    mapping = {}
    for field, keywords in FIELD_PATTERNS.items():
        col_idx = find_column_by_keywords(headers, keywords)
        if col_idx >= 0:
            mapping[field] = {
                'index': col_idx,
                'original_header': headers[col_idx]
            }
    
    return mapping
```

## Validation Function

```python
def validate_mapping(df: pd.DataFrame, header_row: int, mapping: dict, sample_count: int = 5):
    """Show sample data to validate mapping is correct."""
    print("=== Mapping Validation ===")
    print(f"Found fields: {list(mapping.keys())}")
    
    data_start = header_row + 1
    
    for i in range(data_start, min(data_start + sample_count, len(df))):
        print(f"Row {i}:")
        for field, info in mapping.items():
            val = df.iloc[i, info['index']]
            val_str = str(val)[:50] if pd.notna(val) else "(empty)"
            print(f"  {field}: {val_str}")
    
    print("⚠️ VERIFY: Does this mapping look correct?")
```

## Extract Records

```python
def extract_records(df: pd.DataFrame, header_row: int, mapping: dict) -> list:
    """Extract records using validated mapping."""
    records = []
    data_start = header_row + 1
    
    for row_idx in range(data_start, len(df)):
        row = df.iloc[row_idx]
        
        # Skip empty rows
        non_empty = sum(1 for v in row if pd.notna(v) and str(v).strip())
        if non_empty < 2:
            continue
        
        record = {'_row': row_idx}
        
        for field, info in mapping.items():
            col_idx = info['index']
            if col_idx < len(row):
                val = row.iloc[col_idx]
                record[field] = str(val).strip() if pd.notna(val) else ""
            else:
                record[field] = ""
        
        if any(record.get(f) for f in ['code', 'description', 'title']):
            records.append(record)
    
    return records
```

## Transform to RAG Format

```python
def to_rag_chunk(record: dict, source_file: str, sheet_name: str) -> dict:
    """Convert extracted record to RAG chunk format."""
    import hashlib
    
    text_parts = []
    if record.get('code'):
        text_parts.append(f"Error Code: {record['code']}")
    if record.get('description'):
        text_parts.append(f"Description: {record['description']}")
    if record.get('cause'):
        text_parts.append(f"Cause: {record['cause']}")
    if record.get('solution'):
        text_parts.append(f"Solution: {record['solution']}")
    
    text = '\n'.join(text_parts)
    content_hash = hashlib.sha256(text.encode()).hexdigest()[:12]
    
    return {
        'chunk_id': f"excel:{source_file}:{sheet_name}:{record['_row']}:{content_hash}",
        'source_system': 'other',
        'source_type': 'error_code',
        'title': record.get('code', record.get('description', '')[:50]),
        'text': text,
        'language': 'zh' if any('\u4e00' <= c <= '\u9fff' for c in text) else 'en',
        'tags': {
            'rag_type': 'canonical',
            'source_sheet': sheet_name,
        },
        'provenance': {
            'source_path': source_file,
            'source_id': f"{sheet_name}:row_{record['_row']}",
            'content_hash': content_hash,
        }
    }
```

## Find Header Row

```python
def find_header_row(df: pd.DataFrame, max_rows: int = 15) -> int:
    """Find the most likely header row."""
    header_keywords = [
        'id', 'name', 'code', 'error', 'description', 'desc',
        '编号', '名称', '代码', '故障', '描述', '说明',
        'severity', 'cause', 'solution', 'status',
    ]
    
    best_row = None
    best_score = 0
    
    for i in range(min(max_rows, len(df))):
        row_text = ' '.join(str(v).lower() for v in df.iloc[i] if pd.notna(v))
        score = sum(1 for kw in header_keywords if kw in row_text)
        text_cells = sum(1 for v in df.iloc[i] if pd.notna(v) and isinstance(v, str))
        score += text_cells * 0.5
        
        if score > best_score:
            best_score = score
            best_row = i
    
    return best_row if best_score >= 2 else None
```

## Detect Sheet Type

```python
def detect_sheet_type(mapping: dict) -> str:
    """Detect what type of data this sheet contains."""
    if any(f in mapping for f in ['failure_mode', 'rpn', 'severity', 'occurrence']):
        return 'fmea'
    if any(f in mapping for f in ['code', 'error_code', 'alarm']):
        return 'error_code'
    if any(f in mapping for f in ['question', 'answer']):
        return 'faq'
    return 'general'
```
