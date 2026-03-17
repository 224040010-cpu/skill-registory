#!/usr/bin/env python3
"""
Generic Excel Extractor - ZERO Hardcoding!

Principles:
1. NO predefined column patterns
2. NO semantic field mapping
3. Use column headers AS-IS from the data
4. Let the data define the structure
5. Content type inferred from filename/sheetname only
"""

import pandas as pd
import json
import hashlib
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional, Any


def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def safe_str(val, max_len=500) -> str:
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if s.lower() == 'nan':
        return ""
    return s[:max_len]


def detect_language(text: str) -> str:
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    return 'zh' if chinese_chars > len(text) * 0.1 else 'en'


def detect_header_row(df: pd.DataFrame, max_rows: int = 20) -> Optional[int]:
    """
    Find the row that looks most like a header.
    Heuristic: row with most non-empty short text values that are unique.
    """
    best_row = None
    best_score = 0
    
    for i in range(min(max_rows, len(df))):
        row = df.iloc[i]
        values = []
        
        for v in row:
            if pd.notna(v):
                s = str(v).strip()
                if s and s.lower() != 'nan':
                    values.append(s)
        
        if len(values) < 2:
            continue
        
        # Score based on: short text, uniqueness, not numeric
        score = 0
        for v in values:
            if len(v) < 50:  # Short = likely header
                score += 2
            if not v.replace('.', '').replace('-', '').replace(',', '').isdigit():
                score += 1  # Not a number
        
        # Uniqueness bonus
        if len(set(values)) == len(values):
            score *= 1.5
        
        # Coverage bonus - more columns = better
        score += len(values) * 0.5
        
        if score > best_score:
            best_score = score
            best_row = i
    
    return best_row


def get_column_headers(df: pd.DataFrame, header_row: int) -> List[Dict]:
    """
    Extract column headers with their indices.
    Returns list of {index, header, has_data}
    """
    headers = []
    data_start = header_row + 1
    
    for i, val in enumerate(df.iloc[header_row]):
        header_str = safe_str(val)
        if not header_str:
            header_str = f"Column_{i}"
        
        # Check if column has data
        if data_start < len(df):
            col_data = df.iloc[data_start:min(data_start + 20, len(df)), i]
            has_data = any(pd.notna(v) and str(v).strip() for v in col_data)
        else:
            has_data = False
        
        headers.append({
            'index': i,
            'header': header_str,
            'has_data': has_data
        })
    
    return headers


def infer_content_type(filename: str, sheetname: str) -> tuple:
    """
    Infer content type from filename/sheetname only.
    Returns (source_type, knowledge_layer, freshness_level)
    """
    combined = (filename + sheetname).lower()
    
    # Simple keyword matching on filename/sheetname
    if any(k in combined for k in ['faq', 'q&a', '问答']):
        return ('faq', 'norm', 'static')
    elif any(k in combined for k in ['error', 'fault', 'alarm', '故障', '告警', '错误']):
        return ('error_code', 'norm', 'static')
    elif any(k in combined for k in ['车型', 'vehicle', 'car', '兼容', 'compatibility']):
        return ('relationship', 'relation', 'static')
    elif any(k in combined for k in ['log', '记录', 'record', '数据']):
        return ('log', 'evidence', 'daily')
    elif any(k in combined for k in ['case', 'ticket', '问题', 'issue', '分析']):
        return ('field_experience', 'process', 'daily')
    else:
        return ('doc', 'norm', 'static')


def extract_row_to_chunk(row_data: Dict[str, str], 
                         source_file: str,
                         sheet_name: str,
                         row_idx: int,
                         content_info: tuple) -> Optional[Dict]:
    """
    Convert a row of data to a chunk using original column headers.
    """
    source_type, layer, freshness = content_info
    
    # Build text from all non-empty fields using original headers
    text_parts = []
    for header, value in row_data.items():
        if value:
            text_parts.append(f"{header}: {value}")
    
    if not text_parts:
        return None
    
    text = '\n'.join(text_parts)
    
    # Title from first 1-2 non-empty values
    non_empty_vals = [v for v in row_data.values() if v]
    if non_empty_vals:
        title = ' - '.join(non_empty_vals[:2])[:80]
    else:
        title = f"{sheet_name} row {row_idx}"
    
    content_hash = compute_hash(text)
    
    return {
        'chunk_id': f"{source_type}:{sheet_name}:{row_idx}:{content_hash}",
        'source_system': 'other',
        'source_type': source_type,
        'title': title,
        'text': text,
        'language': detect_language(text),
        'created_at': datetime.now().isoformat(),
        'knowledge_layer': layer,
        'freshness_level': freshness,
        'tags': {
            'rag_type': 'curated',
            'source_sheet': sheet_name,
        },
        'evidence': [source_file],
        'provenance': {
            'source_path': source_file,
            'source_id': f"{sheet_name}:row_{row_idx}",
            'content_hash': content_hash,
        }
    }


def process_sheet(df: pd.DataFrame, 
                  filename: str, 
                  sheet_name: str,
                  verbose: bool = True) -> List[Dict]:
    """
    Process a single sheet generically.
    """
    chunks = []
    
    if len(df) < 2:
        if verbose:
            print(f"    Skipping - too few rows ({len(df)})")
        return chunks
    
    # Detect header
    header_row = detect_header_row(df)
    if header_row is None:
        if verbose:
            print(f"    Skipping - no header detected")
        return chunks
    
    if verbose:
        print(f"    Header row: {header_row}")
    
    # Get columns with data
    columns = get_column_headers(df, header_row)
    data_columns = [c for c in columns if c['has_data']]
    
    if not data_columns:
        if verbose:
            print(f"    Skipping - no data columns")
        return chunks
    
    if verbose:
        headers = [c['header'][:20] for c in data_columns[:5]]
        print(f"    Columns ({len(data_columns)}): {headers}...")
    
    # Infer content type from filename/sheetname
    content_info = infer_content_type(filename, sheet_name)
    if verbose:
        print(f"    Type: {content_info[0]}")
    
    # Extract rows
    data_start = header_row + 1
    for idx in range(data_start, len(df)):
        row = df.iloc[idx]
        
        # Build row data dict with original headers
        row_data = {}
        for col in data_columns:
            val = safe_str(row.iloc[col['index']])
            if val:
                row_data[col['header']] = val
        
        if not row_data:
            continue
        
        chunk = extract_row_to_chunk(row_data, filename, sheet_name, idx, content_info)
        if chunk:
            chunks.append(chunk)
    
    if verbose:
        print(f"    Extracted: {len(chunks)} chunks")
    
    return chunks


def extract_excel(filepath: Path, verbose: bool = True) -> List[Dict]:
    """Extract all sheets from Excel file."""
    chunks = []
    
    try:
        xlsx = pd.ExcelFile(filepath)
    except Exception as e:
        if verbose:
            print(f"  Error: {e}")
        return chunks
    
    for sheet_name in xlsx.sheet_names:
        if verbose:
            print(f"\n  Sheet: {sheet_name}")
        
        try:
            df = pd.read_excel(xlsx, sheet_name=sheet_name, header=None)
            sheet_chunks = process_sheet(df, filepath.name, sheet_name, verbose)
            chunks.extend(sheet_chunks)
        except Exception as e:
            if verbose:
                print(f"    Error: {e}")
    
    return chunks


def extract_csv(filepath: Path, verbose: bool = True) -> List[Dict]:
    """Extract from CSV file."""
    for encoding in ['utf-8', 'gbk', 'latin1', 'cp1252']:
        try:
            df = pd.read_csv(filepath, header=None, encoding=encoding)
            return process_sheet(df, filepath.name, 'csv', verbose)
        except:
            continue
    
    if verbose:
        print(f"  Error: Could not read CSV with any encoding")
    return []


def main():
    import sys
    
    search_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/Users/sharon/w/energy/feishu-mcp")
    output_file = search_dir / "export" / "generic_excel_chunks.jsonl"
    
    print("=" * 70)
    print("GENERIC EXCEL/CSV EXTRACTION (Zero Hardcoding)")
    print("=" * 70)
    print(f"Directory: {search_dir}")
    
    # Find files
    excel_files = list(search_dir.glob("**/*.xlsx")) + list(search_dir.glob("**/*.xls"))
    csv_files = list(search_dir.glob("**/*.csv"))
    
    # Filter irrelevant paths
    skip_patterns = ['.venv', 'node_modules', 'umath-validation', '__pycache__', 'export']
    excel_files = [f for f in excel_files if not any(p in str(f) for p in skip_patterns)]
    csv_files = [f for f in csv_files if not any(p in str(f) for p in skip_patterns)]
    
    # Dedupe by filename (assume same filename = same file content)
    seen_names = set()
    unique_excel = []
    for f in sorted(excel_files, key=lambda x: len(str(x))):  # Prefer shorter paths
        if f.name not in seen_names:
            seen_names.add(f.name)
            unique_excel.append(f)
    excel_files = unique_excel
    
    unique_csv = []
    for f in sorted(csv_files, key=lambda x: len(str(x))):
        if f.name not in seen_names:
            seen_names.add(f.name)
            unique_csv.append(f)
    csv_files = unique_csv
    
    print(f"Found: {len(excel_files)} Excel, {len(csv_files)} CSV files")
    
    all_chunks = []
    
    for fp in sorted(excel_files):
        print(f"\n📊 {fp.name}")
        chunks = extract_excel(fp)
        all_chunks.extend(chunks)
    
    for fp in sorted(csv_files):
        print(f"\n📄 {fp.name}")
        chunks = extract_csv(fp)
        all_chunks.extend(chunks)
    
    # Dedupe
    seen = set()
    unique = []
    for c in all_chunks:
        h = c['provenance']['content_hash']
        if h not in seen:
            seen.add(h)
            unique.append(c)
    
    print(f"\n{'=' * 70}")
    print(f"Total: {len(unique)} unique chunks (before dedupe: {len(all_chunks)})")
    
    # Write
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        for c in unique:
            f.write(json.dumps(c, ensure_ascii=False) + '\n')
    
    print(f"Output: {output_file}")
    
    # Stats
    by_type = defaultdict(int)
    by_layer = defaultdict(int)
    by_file = defaultdict(int)
    
    for c in unique:
        by_type[c['source_type']] += 1
        by_layer[c['knowledge_layer']] += 1
        by_file[c['evidence'][0]] += 1
    
    print(f"\nBy source_type:")
    for k, v in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")
    
    print(f"\nBy knowledge_layer:")
    for k, v in sorted(by_layer.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")
    
    print(f"\nBy file (top 10):")
    for k, v in sorted(by_file.items(), key=lambda x: -x[1])[:10]:
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
