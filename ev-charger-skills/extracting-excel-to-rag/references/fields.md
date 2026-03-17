# Excel to RAG - Field Patterns Reference

> **WARNING: DO NOT HARDCODE THESE PATTERNS!**
> 
> These patterns are for REFERENCE ONLY to understand what fields might exist.
> ALWAYS use `generic_excel_extractor.py` which uses headers AS-IS.

## Understanding Error Code Fields (Reference Only)

Common column headers you might see (DON'T hardcode these):

```python
# Example headers - USE THEM AS-IS, DON'T MAP!
# 告警码, error_code, fault_code, alarm_code
# 描述, description, 说明, info
# 严重度, severity, level
# 判断条件, trigger_condition, when
# 维修指引, maintenance, solution, 措施
```

## Understanding FMEA Fields (Reference Only)

Common column headers in FMEA spreadsheets (DON'T hardcode):

```python
# Example headers - USE THEM AS-IS
# 子系统, subsystem, system
# 组件, component, part, 部件
# 失效模式, failure_mode
# 影响, effect, impact
# 严重度, S, severity
# 发生度, O, occurrence
# 探测度, D, detection
# RPN, 风险优先级
```

## Understanding FAQ Fields (Reference Only)

Common column headers in FAQ spreadsheets (DON'T hardcode):

```python
# Example headers - USE THEM AS-IS
# Question, 问题, Q
# Answer, 回答, 答案, A
# Category, 分类, type
# Product, 产品, model
```

## Correct Approach: Content Type from Filename

**DON'T** pattern-match columns to detect type. Instead, infer from filename:

```python
def infer_content_type(filename: str, sheetname: str) -> str:
    """Infer content type from filename/sheetname ONLY."""
    combined = (filename + sheetname).lower()
    
    if any(k in combined for k in ['faq', 'q&a', '问答']):
        return 'faq'
    elif any(k in combined for k in ['error', 'fault', 'alarm', '故障', '告警']):
        return 'error_code'
    elif any(k in combined for k in ['fmea', '失效']):
        return 'fmea'
    else:
        return 'doc'
```

## Google Sheets Integration

Convert API response to DataFrame first, then use generic extraction:

```python
def read_google_sheet(service, spreadsheet_id, range_name='Sheet1'):
    """Read data from Google Sheets as DataFrame."""
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name
    ).execute()
    
    values = result.get('values', [])
    if values:
        return pd.DataFrame(values[1:], columns=values[0])
    return pd.DataFrame()

# Then use headers AS-IS - don't map to semantic fields!
for col in df.columns:
    row_data[col] = safe_str(row[col])
```

## Key Takeaway

**Use headers AS-IS.** The RAG system doesn't need semantic field mapping - 
the original column names provide better context for retrieval.
