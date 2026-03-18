---
name: chunking-knowledge-sources
bundle_scope: ops-agent
risk_level: L3
description: |
  Splits preprocessed multi-format knowledge sources (Excel CSV, Markdown,
  Log segments) into standardized semantic chunks and QA pairs, writing
  results to processed_data/semantic_chunk/ and processed_data/qa_pair/.
  Use when all relevant preprocessing skills have completed and chunk files
  need to be generated or regenerated for vectorization.
  Do NOT use when preprocessing has not been completed (run preprocessing-*
  skills first), or when only vectorization needs to be re-run without
  re-chunking (use vectorizing-knowledge-base directly).
---

# Purpose

Produces *_for_chunking.json semantic chunks and qa_pair/*.json QA pairs from
all preprocessed data types so that vectorizing-knowledge-base can embed them
without any format-specific logic. This is Phase 2 of the pipeline.

---

# Trigger

**Use this Skill when:**
- All needed preprocessing skills have completed successfully
- Chunk parameters need to be changed and chunks regenerated
- New preprocessed files exist that have not yet been chunked
- User requests a specific file to be re-chunked (--file option)

**Do NOT use this Skill when:**
- Preprocessed source files do not yet exist — run preprocessing skills first
- Only vectorization needs to be rerun — use vectorizing-knowledge-base directly

---

# Workflow

[ ] Step 1: 验证预处理输出目录
    - ⚠️ Tool needed: `file-system-mcp:list_files(`path=data_prepare/processed_data/, pattern=table_cache/*.csv,markdown/*_processed.json,log_cache/*)
    - If all three source types are empty → return error "No preprocessed data found, run preprocessing skills first"
    - Log available source counts per type

[ ] Step 2: 分块 Excel CSV 数据
    - ⚠️ Tool needed: `data-pipeline-mcp:run_script(`
        script=scripts/phase2_generate_excel_chunk.py,
        args=["--overwrite"] (add "--file <name>" to target a specific CSV)
      )
    - Reads table_cache/*.csv → writes semantic_chunk/*_for_chunking.json
    - If 0 CSV files → skip this step with log "No CSV files, skipping Excel chunking"

[ ] Step 3: 分块 Markdown 数据
    - ⚠️ Tool needed: `data-pipeline-mcp:run_script(`
        script=scripts/phase2_generate_for_chunking_json.py,
        args=[] (add "--file <name>" to target a specific _processed.json)
      )
    - Reads markdown/*_processed.json → writes semantic_chunk/*_for_chunking.json
    - If 0 processed.json files → skip with log "No processed markdown, skipping"

[ ] Step 4: 提取 Markdown QA 对
    - ⚠️ Tool needed: `data-pipeline-mcp:run_script(`
        script=scripts/phase2_extract_qa_from_md.py,
        args=[] (add "--file <name>" for specific file; add "--no-qa" for metadata only)
      )
    - Reads markdown/*.md → writes qa_pair/*.json + metadata
    - If 0 markdown files → skip with log "No markdown files, skipping QA extraction"

[ ] Step 5: 分块 Log 数据并生成 Log QA
    - ⚠️ Tool needed: `data-pipeline-mcp:run_script(`
        script=scripts/phase2_generate_log_chunk.py,
        args=[] (add "--file <segment_path>" for specific file; "--max-segments N" to limit LLM calls)
      )
    - Reads log_cache/ merged segments → writes qa_pair/*.json + semantic_chunk/*.json
    - This step calls an LLM — use "--dry-run" to validate without writing files
    - If 0 log segments → skip with log "No log segments, skipping log chunking"

[ ] Step 6: 验证输出并返回结果
    - ⚠️ Tool needed: `file-system-mcp:list_files(`path=data_prepare/processed_data/semantic_chunk/, pattern=*_for_chunking.json)
    - ⚠️ Tool needed: `file-system-mcp:list_files(`path=data_prepare/processed_data/qa_pair/, pattern=*.json)
    - Return: {semantic_chunks: N, qa_pairs: N, skipped_types: [...]}

**Error handling:**
- If any script exits non-zero → record which step failed, return error with stderr, continue remaining steps
- If log chunking LLM call fails → return partial result with warning "Log QA generation failed, chunks may be incomplete"
- If output counts are 0 for all types → return error "Chunking produced no output"

---

# Scripts

**phase2_generate_excel_chunk.py** — Converts table_cache CSVs to semantic chunks
- Execute: `python scripts/phase2_generate_excel_chunk.py [--file FILE] [--overwrite]`
- Input: processed_data/table_cache/*.csv
- Output: processed_data/semantic_chunk/*_for_chunking.json

**phase2_generate_for_chunking_json.py** — Converts markdown processed JSONs to semantic chunks
- Execute: `python scripts/phase2_generate_for_chunking_json.py [--file FILE]`
- Input: processed_data/markdown/*_processed.json
- Output: processed_data/semantic_chunk/*_for_chunking.json

**phase2_extract_qa_from_md.py** — Extracts QA pairs and metadata from Markdown files
- Execute: `python scripts/phase2_extract_qa_from_md.py [--file FILE] [--no-qa]`
- Input: processed_data/markdown/*.md
- Output: processed_data/qa_pair/*.json + metadata
- `--no-qa`: skip QA extraction, generate metadata only

**phase2_generate_log_chunk.py** — Generates QA pairs and semantic chunks from log segments using LLM
- Execute: `python scripts/phase2_generate_log_chunk.py [--file FILE] [--dry-run] [--max-segments N]`
- Input: processed_data/log_cache/ (merged segments)
- Output: processed_data/qa_pair/*.json + processed_data/semantic_chunk/*.json
- `--dry-run`: validate chunking logic without LLM calls or file writes
- `--max-segments N`: limit LLM calls (useful for testing)

**common_schema.py** — Shared data schema definitions used by pipeline scripts

---

# Constraints

- NEVER run this skill before all needed preprocessing skills have completed
- This skill is READ (processed_data/table_cache, markdown, log_cache) + WRITE (semantic_chunk, qa_pair)
- Log chunking (Step 5) invokes an LLM — be aware of cost and latency for large log sets
- Use --dry-run on Step 5 first when processing a large new log dataset
- Output must include: semantic_chunks count, qa_pairs count, skipped_types list

---

<!--
- skill_name: chunking-knowledge-sources
  display_name: 知识源分块
  purpose: |
    将多格式预处理后的知识源（Excel CSV、Markdown、日志段）切分为标准化语义块和
    QA 对，写入 processed_data/semantic_chunk/ 和 processed_data/qa_pair/，
    为向量化技能提供统一格式的输入。
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
    external_services:
      - llm-service
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
