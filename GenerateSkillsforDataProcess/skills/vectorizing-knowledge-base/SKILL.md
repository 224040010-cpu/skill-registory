---
name: vectorizing-knowledge-base
bundle_scope: ops-agent
risk_level: L3
description: |
  Embeds semantic chunks and QA pairs into ChromaDB (dual collection), builds
  a HippoRAG knowledge graph, and vectorizes images using AWS Bedrock or local
  embeddings, producing a fully searchable knowledge base under processed_data/.
  Use when chunking-knowledge-sources has completed and the knowledge base needs
  to be built or updated for retrieval.
  Do NOT use when chunk files do not exist yet (run chunking-knowledge-sources
  first), or when only a manifest update is needed (use building-data-manifest).
---

# Purpose

Transforms semantic_chunk/ and qa_pair/ files into three complementary retrieval
indexes — ChromaDB vector store, HippoRAG knowledge graph, and image embeddings —
enabling the downstream agent to perform hybrid retrieval over the full
knowledge base.

---

# Trigger

**Use this Skill when:**
- chunking-knowledge-sources has completed and vectors need to be built
- Knowledge base needs to be rebuilt from scratch (--rebuild)
- Only QA or only semantic data needs to be re-embedded (--qa-only / --semantic-only)
- AWS Bedrock or local embedding model needs to be switched

**Do NOT use this Skill when:**
- Chunk files do not exist yet — run chunking-knowledge-sources first
- Only the manifest needs updating — use building-data-manifest
- No changes to chunk files since last successful vectorization run

---

# Workflow

[ ] Step 1: 验证分块输出目录
    - ⚠️ Tool needed: `file-system-mcp:list_files(`path=data_prepare/processed_data/semantic_chunk/, pattern=*_for_chunking.json)
    - ⚠️ Tool needed: `file-system-mcp:list_files(`path=data_prepare/processed_data/qa_pair/, pattern=*.json)
    - If both are empty → return error "No chunk files found, run chunking-knowledge-sources first"

[ ] Step 2: 构建 ChromaDB 向量库（文本 QA + Semantic 双 collection）
    - ⚠️ Tool needed: `data-pipeline-mcp:run_script(`
        script=scripts/phase3_text_QA_vectorize.py,
        args=[
          "--use-aws" | "--use-local",
          "--persist-dir", <persist_dir (default: processed_data/chromadb_ver3/)>,
          "--rebuild" (optional),
          "--qa-only" | "--semantic-only" (optional)
        ]
      )
    - If ModuleNotFoundError: boto3 and --use-aws → return "Missing dependency: pip install boto3"
    - If script exits non-zero → return stderr, stop

[ ] Step 3: 构建 HippoRAG 知识图谱
    - ⚠️ Tool needed: `data-pipeline-mcp:run_script(`
        script=scripts/phase3_hippoRAG_graph.py,
        args=[
          "--persist-dir", <persist_dir (default: processed_data/hipporag_index/)>,
          "--rebuild" (optional),
          "--semantic-only" | "--qa-only" (optional),
          "--llm-name", <llm_name (default: AWS Bedrock Claude)>,
          "--embedding-name", <embedding_name (default: AWS Bedrock Titan embed-text-v2)>,
          "--aws-region", <region (default: us-west-2)>
        ]
      )
    - Uses LLM for OpenIE and QA generation — be aware of cost for large datasets
    - "--sidecar-only": regenerates sidecar index only, skips full HippoRAG rebuild
    - If script exits non-zero → return stderr, stop

[ ] Step 4: 向量化图像
    - ⚠️ Tool needed: `data-pipeline-mcp:run_script(`
        script=scripts/phase3_image_vectorize.py,
        args=[]
      )
    - Requires boto3 — if not installed → return "Missing dependency: pip install boto3"
    - If no image files found → log warning "No images to vectorize, skipping" and continue

[ ] Step 5: 验证输出并返回结果
    - ⚠️ Tool needed: `file-system-mcp:list_files(`path=data_prepare/processed_data/chromadb_ver3/)
    - ⚠️ Tool needed: `file-system-mcp:list_files(`path=data_prepare/processed_data/hipporag_index/)
    - Return: {chromadb: {status: "ok"|"failed"}, hipporag: {status: "ok"|"failed"}, image_vectors: {status: "ok"|"skipped"|"failed"}}

**Error handling:**
- If ChromaDB build fails → return error immediately, do not proceed to HippoRAG
- If HippoRAG LLM call hits rate limit → report partial completion, suggest --sidecar-only for retry
- If image vectorization fails → return warning (non-blocking), report ChromaDB + HippoRAG status

---

# Scripts

**phase3_text_QA_vectorize.py** — Builds ChromaDB with QA + semantic_chunk dual collection
- Execute: `python scripts/phase3_text_QA_vectorize.py [options]`
- Input: processed_data/semantic_chunk/, processed_data/qa_pair/
- Output: processed_data/chromadb_ver3/ (default)
- Key options: `--use-aws` (default), `--use-local`, `--persist-dir DIR`, `--rebuild`, `--qa-only`, `--semantic-only`

**phase3_hippoRAG_graph.py** — Builds HippoRAG2 knowledge graph from chunks and QA pairs
- Execute: `python scripts/phase3_hippoRAG_graph.py [options]`
- Input: processed_data/semantic_chunk/, processed_data/qa_pair/
- Output: processed_data/hipporag_index/ (default)
- Key options: `--persist-dir DIR`, `--rebuild`, `--semantic-only`, `--qa-only`, `--llm-name`, `--embedding-name`, `--aws-region`, `--sidecar-only`
- Requires: AWS Bedrock (default) or custom LLM/embedding endpoint

**phase3_image_vectorize.py** — Vectorizes images via AWS Bedrock
- Execute: `python scripts/phase3_image_vectorize.py`
- Input: image files in processed_data/
- Output: image vector store
- Requires: `pip install boto3`, AWS credentials

**common_schema.py** — Shared data schema definitions used by pipeline scripts

---

# Constraints

- NEVER run this skill before chunking-knowledge-sources has completed
- This skill is READ (processed_data/semantic_chunk, qa_pair) + WRITE (chromadb, hipporag_index) + EXTERNAL (AWS Bedrock)
- HippoRAG graph construction calls an LLM — validate chunk volume before full rebuild
- Use --sidecar-only for HippoRAG incremental updates instead of full --rebuild when possible
- Output must include status for all three indexes: chromadb, hipporag, image_vectors

---

<!--
- skill_name: vectorizing-knowledge-base
  display_name: 知识库向量化
  purpose: |
    将 semantic_chunk/ 和 qa_pair/ 文件嵌入 ChromaDB 向量库（QA + semantic 双集合）、
    构建 HippoRAG 知识图谱，并向量化图像，在 processed_data/ 下生成可检索的完整知识库。
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
      - boto3
    external_services:
      - aws-bedrock
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
