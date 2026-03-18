---
name: sorting-raw-files
bundle_scope: ops-agent
risk_level: L3
description: |
  Scans raw_material/ and copies files by knowledge category into source_file/
  subdirectories (derived_index, evidence, memory_case, etc.), preparing
  categorized input for downstream preprocessing skills.
  Use when new raw source files have been added to raw_material/ and need to be
  sorted before any preprocessing step.
  Do NOT use when raw_material/ is empty, or when source files have already been
  sorted and no new files have been added.
---

# Purpose

Distributes raw mixed-format files from raw_material/ into typed subdirectories
under source_file/, enabling each preprocessing skill to operate on its own
file type without format-detection logic.

---

# Trigger

**Use this Skill when:**
- New files have been placed in raw_material/ and need to be sorted
- Pipeline Phase 0 is starting from scratch
- source_file/ subdirectories are empty or stale

**Do NOT use this Skill when:**
- raw_material/ is empty — nothing to sort
- Files have already been sorted and no changes have been made to raw_material/

---

# Workflow

[ ] Step 1: 校验 raw_material 目录结构（脚本内强制）
    - **校验 1**：`base_dir/raw_material` 必须存在且为目录
    - **校验 2**：其下必须存在五个知识层子文件夹：`derived_index`, `evidence`, `memory_case`, `memory_rule`, `normative`
    - 缺任一则脚本报错退出，流程不继续；通过后再执行分拣
[ ] Step 2: 检查 raw_material 源目录（可选，用于提示）
    - ⚠️ Tool needed: `file-system-mcp:list_files(`path=data_prepare/raw_material/, recursive=true)
    - If 0 files found → return warning "raw_material/ is empty, nothing to sort"
    - Log: total file count and file types discovered

[ ] Step 3: 执行文件分拣
    - ⚠️ Tool needed: `data-pipeline-mcp:run_script(`
        script=scripts/phase0_sort_files.py,
        args=[]
      )
    - Script reads from raw_material/ and copies into source_file/ subdirectories
    - If script exits non-zero → return stderr as error message, stop

[ ] Step 4: 验证输出并返回结果
    - ⚠️ Tool needed: `file-system-mcp:list_files(`path=data_prepare/source_file/, recursive=false)
    - Return: {categories: [...], total_files: N, by_category: {category: count}, output_dir: "source_file/"}

**Error handling:**
- If raw_material/ does not exist → script exits with error, do not proceed
- If raw_material/ 下缺少五知识层子文件夹（derived_index, evidence, memory_case, memory_rule, normative）任一 → script exits with error, do not proceed
- If sort script encounters unrecognized file type → log warning per file, continue
- If output source_file/ is empty after run → return warning "No files were sorted, check raw_material/ content"

---

# Scripts

**phase0_sort_files.py** — Scans and distributes raw files into source_file/ categories
- Execute: `python scripts/phase0_sort_files.py`
- Input: data_prepare/raw_material/ (hardcoded base dir)
- Output: data_prepare/source_file/{derived_index,evidence,memory_case,...}/

**common_schema.py** — Shared data schema definitions used by pipeline scripts

---

# Constraints

- **前置条件**：raw_material 必须存在，且其下必须存在五知识层子文件夹：derived_index, evidence, memory_case, memory_rule, normative；否则脚本直接退出，不执行分拣
- NEVER delete or modify source files in raw_material/
- This skill is READ (raw_material/) + WRITE (source_file/) only
- Script paths come from pipeline_config.json (base_dir/raw_material)
- Output must include: categories list, total_files count, by_category breakdown

---

<!--
- skill_name: sorting-raw-files
  display_name: 原始文件分拣
  purpose: |
    扫描 raw_material/ 并按知识类别将文件复制到 source_file/ 子目录
    （derived_index、evidence、memory_case 等），为各预处理技能准备分类整理的输入。
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
    packages: []
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
