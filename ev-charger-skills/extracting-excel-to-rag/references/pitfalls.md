# Excel to RAG - Common Pitfalls & Solutions

## Pitfall 0: HARDCODING Column Names/Patterns

**THIS IS THE #1 MISTAKE. DO NOT DO THIS.**

```python
# ❌ WRONG - Hardcoding column patterns
FIELD_PATTERNS = {
    'error_code': [r'告警码', r'错误码', r'故障码'],  # DON'T!
    'description': [r'描述', r'说明', r'信息'],       # DON'T!
}

# ❌ WRONG - Mapping to semantic fields
col_map = {
    'error_code': 3,     # DON'T!
    'trigger': 5,        # DON'T!
}

# ✅ CORRECT - Use headers AS-IS
headers = df.iloc[header_row].tolist()
for col_idx, header in enumerate(headers):
    if pd.notna(header):
        row_data[str(header).strip()] = safe_str(row.iloc[col_idx])
```

**Why?** Every Excel file is different. Hardcoding creates brittle code that fails silently on new files.

## Pitfall 1: Column Index 0 is Falsy

```python
# ❌ WRONG - Column 0 evaluates to False!
col_idx = mapping.get('code')
if not col_idx:  # BUG: 0 is falsy!
    print("Not found")

# ✅ CORRECT - Check key existence
if 'code' not in mapping:
    print("Not found")

# ✅ ALSO CORRECT - Explicit None check
col_idx = mapping.get('code')
if col_idx is None:
    print("Not found")
```

## Pitfall 2: Multi-Row Headers

```python
# Some Excel files have headers spanning multiple rows:
# Row 3: "System Info" | "" | "" | "Error Details" | "" | ""
# Row 4: "ID" | "Name" | "Version" | "Code" | "Desc" | "Solution"

def get_combined_headers(df, header_rows: list) -> list:
    """Combine multiple header rows into single header list."""
    combined = []
    for col in range(len(df.columns)):
        parts = []
        for row in header_rows:
            val = df.iloc[row, col]
            if pd.notna(val) and str(val).strip():
                parts.append(str(val).strip())
        combined.append(' - '.join(parts) if parts else '')
    return combined
```

## Pitfall 3: Merged Cells

```python
# Merged cells appear as value in first cell, NaN in others

def handle_merged_cells(df: pd.DataFrame, cols_to_fill: list) -> pd.DataFrame:
    """Fill NaN values that result from merged cells."""
    df = df.copy()
    for col in cols_to_fill:
        if col < len(df.columns):
            df.iloc[:, col] = df.iloc[:, col].ffill()
    return df
```

## Pitfall 4: Mixed Data Types

```python
# Some cells may be numbers, dates, or formulas

def safe_str(val) -> str:
    """Safely convert any value to string."""
    if pd.isna(val):
        return ""
    if isinstance(val, float) and val == int(val):
        return str(int(val))  # Remove .0 from integers
    return str(val).strip()
```

## Pitfall 5: Hidden/Empty Sheets

```python
def is_sheet_useful(df: pd.DataFrame, min_rows: int = 3, min_cols: int = 2) -> bool:
    """Check if sheet has meaningful data."""
    if len(df) < min_rows:
        return False
    non_empty = df.notna().sum().sum()
    return non_empty >= min_rows * min_cols
```

## Pitfall 6: Formula Values vs Computed Values

```python
import openpyxl

def extract_with_formulas(file_path, sheet_name):
    """Extract both values and formulas from Excel."""
    wb = openpyxl.load_workbook(file_path, data_only=False)
    ws = wb[sheet_name]
    
    # Also load with values for computed results
    wb_values = openpyxl.load_workbook(file_path, data_only=True)
    ws_values = wb_values[sheet_name]
    
    data = []
    for row_idx, row in enumerate(ws.iter_rows(), 1):
        row_data = {'row': row_idx, 'cells': []}
        for col_idx, cell in enumerate(row, 1):
            cell_info = {
                'column': col_idx,
                'value': ws_values.cell(row_idx, col_idx).value,
                'formula': cell.value if isinstance(cell.value, str) and cell.value.startswith('=') else None
            }
            row_data['cells'].append(cell_info)
        data.append(row_data)
    
    return data
```
