---
name: preprocessing-excel-sources
bundle_scope: ops-agent
risk_level: L3
description: |
  Converts Excel (.xlsx) files from source_file/ into CSV format and writes
  them to processed_data/table_cache/, preparing structured tabular data for
  downstream Excel chunking.
  Use when Excel files have been sorted into source_file/ and need to be
  converted to CSV before chunking.
  Do NOT use when Excel files have not been sorted yet (run sorting-raw-files
  first), or when only log/PDF data needs processing (use the respective skill).
---

# Purpose

Transforms raw Excel workbooks into per-sheet CSV files under
processed_data/table_cache/, enabling phase2_generate_excel_chunk.py to
produce semantic chunks without any Excel-parsing logic.

---

# Trigger

**Use this Skill when:**
- source_file/ contains Excel (.xlsx) files ready for conversion
- Pipeline Phase 1 is running for Excel data type
- processed_data/table_cache/ needs to be refreshed after new Excel files are added

**Do NOT use this Skill when:**
- source_file/ has not been populated yet (run sorting-raw-files first)
- Only log or PDF data needs preprocessing (use the respective skill)
- openpyxl is not installed (install first with pip install openpyxl)

---

# Workflow

[ ] Step 1: 检查 Excel 源文件及依赖
    - ⚠️ Tool needed: `file-system-mcp:list_files(`path=data_prepare/source_file/, pattern=**/*.xlsx)
    - If 0 .xlsx files found → return warning "No Excel files found in source_file/, skipping"
    - Verify openpyxl is installed; if not → return "Missing dependency: run pip install openpyxl"

[ ] Step 2: 执行 Excel 预处理（转 CSV）
    - ⚠️ Tool needed: `data-pipeline-mcp:run_script(`
        script=scripts/phase1_preprocess_excel_data.py,
        args=[]
      )
    - If ModuleNotFoundError: openpyxl → return "Missing dependency: run pip install openpyxl"
    - If script exits non-zero → return stderr as error message, stop

[ ] Step 3: 验证输出并返回结果
    - ⚠️ Tool needed: `file-system-mcp:list_files(`path=data_prepare/processed_data/table_cache/, pattern=*.csv)
    - Return: {csv_files_created: N, output_dir: "processed_data/table_cache/"}

**Error handling:**
- If openpyxl not installed → return actionable install message before running
- If an Excel file has no sheets or is corrupt → log warning per file, continue
- If output table_cache/ is empty after run → return warning "No CSV files created, check Excel file format"

---

# Scripts

**phase1_preprocess_excel_data.py** — Converts Excel workbooks to per-sheet CSVs
- Execute: `python scripts/phase1_preprocess_excel_data.py`
- Input: source_file/ (Excel files, hardcoded base dir)
- Output: processed_data/table_cache/*.csv
- Requires: `pip install openpyxl`

**common_schema.py** — Shared data schema definitions used by pipeline scripts

---

# Constraints

- NEVER modify or delete source Excel files in source_file/
- This skill is READ (source_file/) + WRITE (processed_data/table_cache/) only
- Requires openpyxl — validate installation before running in new environment
- Script has hardcoded paths — do not pass custom source/target directories
- Output must include: csv_files_created count, output_dir

---

<!--
- skill_name: preprocessing-excel-sources
  display_name: Excel 数据预处理
  purpose: |
    将 source_file/ 中的 Excel 文件转换为 CSV 格式，输出到 processed_data/table_cache/，
    为下游 Excel 分块技能提供标准化输入。
  owner_team: data-team
  owner_individual: TBD
  version: v1.0.0
  rollback_version: null
  status: draft
  risk_level: L3
  dependencies:
    mcp_servers:
      - file-system-mcp
      - data-pipeline-mcp
    packages:
      - openpyxl
    external_services: []
  supported_models:
    - claude-sonnet-4-6
  surfaces:
    - api
  bundle_scope:
    - knowledge-base-agent
  eval_status:
    last_eval_date: null
    eval_result: PENDING
    eval_score: null
  security_review:
    status: pending
    reviewer: null
    review_date: null
    checksum: null
-->
