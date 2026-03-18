"""
脚本：phase3_hippoRAG_graph.py

使用项目内的 HippoRAG2 源码，基于 phase2 产出的 semantic_chunk 与 qa_pair 构建知识图并建索引，
供检索时做图增强多跳召回（与 phase3_text_QA_vectorize 的 ChromaDB 向量检索并行使用）。

处理逻辑：
- 输入：与 phase3_text_QA_vectorize 一致
  - semantic_chunk/*_for_chunking.json：每个 chunk 转为 passage，格式 title\\ncontent（HippoRAG 要求）
  - 可选 qa_pair/*.json：每条 QA 转为一条 passage（问题\\n答案）
- 调用 HippoRAG（E:\\...\\HippoRAG\\src）的 index(docs)，完成 OpenIE、建图、chunk/entity/fact 编码
- 输出：保存到 processed_data/hipporag_index（或 --persist-dir 指定目录），与 ChromaDB 分离

输出结构（--persist-dir 即 save_dir 下，均为 HippoRAG 默认格式，便于按模型版本追索）：
  <persist-dir>/
  ├── chunk_metadata.json                   # 本脚本生成：hash_id → chunk 元数据，供 Agent 检索时多跳/引用
  ├── openie_results_ner_<llm_name>.json   # OpenIE 抽取结果（实体/三元组），JSON；llm_name 中 / 替换为 _
  ├── llm_cache/                            # LLM 调用缓存（Bedrock 等）
  │   └── <llm_name>.sqlite
  └── <llm_label>_<embedding_label>/        # working_dir：llm 与 embedding 模型名各 replace("/","_") 后拼接
      ├── graph.pickle                      # 知识图（igraph 序列化）
      ├── chunk_embeddings/
      │   └── vdb_chunk.parquet             # passage 向量
      ├── entity_embeddings/
      │   └── vdb_entity.parquet            # 实体向量
      └── fact_embeddings/
          └── vdb_fact.parquet              # 事实/三元组向量

知识更新（不删掉重建）：
- 增量新增：默认即为增量。不传 --rebuild 时，再次运行本脚本（phase2 已更新），HippoRAG 只会对
  「尚未在索引中的 passage」做 OpenIE、编码、加图；已有 passage 会跳过。因此定期重跑即可完成知识更新。
- 删除内容：需调用 HippoRAG 的 delete(docs_to_delete)，传入要删的 passage 的完整文本。本脚本支持
  --delete-from-file <path>：该文件每行一条要删的 doc 文本（与建索引时 title\\ncontent 一致），执行删除后退出。
- 更新某条：先对旧内容做删除，再重跑索引（新内容会作为新增写入）。

依赖：
- 需先安装或可导入 hipporag：将项目根下的 HippoRAG 可编辑安装（pip install -e HippoRAG）
  或本脚本会尝试把 HippoRAG/src 加入 sys.path 后 import
- HippoRAG 自身依赖：见 HippoRAG/requirements.txt（如 OpenAI 或 vLLM、embedding 模型等）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# 数据根目录：与 phase3_text_QA_vectorize 一致
import sys as _sys
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_CONFIGURING = _PROJECT_ROOT / "skills" / "configuring-pipeline"
for _p in (_CONFIGURING, _PROJECT_ROOT):
    if str(_p) not in _sys.path:
        _sys.path.insert(0, str(_p))

try:
    from pipeline_config_loader import load_config as _load_config
    _cfg = _load_config(ensure_dirs=True)
    DATA_PREPARE_DIR = Path(_cfg["input"]["raw_material"]).parent
    PROCESSED_DATA_DIR = DATA_PREPARE_DIR / "processed_data"
    PROJECT_ROOT = DATA_PREPARE_DIR.parent
    DEFAULT_HIPPORAG_SAVE_DIR = Path(_cfg["output"]["hipporag_index"])
    QA_PAIR_DIR = Path(_cfg["intermediate"]["qa_pair"])
    SEMANTIC_CHUNK_DIR = Path(_cfg["intermediate"]["semantic_chunk"])
except Exception:
    _cfg = {}
    DATA_PREPARE_DIR = Path(__file__).resolve().parents[1]
    PROCESSED_DATA_DIR = DATA_PREPARE_DIR / "processed_data"
    PROJECT_ROOT = DATA_PREPARE_DIR.parent
    DEFAULT_HIPPORAG_SAVE_DIR = PROCESSED_DATA_DIR / "hipporag_index"
    QA_PAIR_DIR = PROCESSED_DATA_DIR / "qa_pair"
    SEMANTIC_CHUNK_DIR = PROCESSED_DATA_DIR / "semantic_chunk"

HIPPORAG_SRC = PROJECT_ROOT / "HippoRAG" / "src"

_aws = _cfg.get("aws") or {}
_hippo = _cfg.get("hipporag") or {}
_vec = _cfg.get("vectorizing") or {}
_hipporag_vec = _vec.get("hipporag") or {}
try:
    from pipeline_config_loader import load_config as _load_cfg
    _c = _load_cfg(ensure_dirs=False)
    _aws = _c.get("aws") or _aws
    _hippo = _c.get("hipporag") or _hippo
    _vec = _c.get("vectorizing") or _vec
    _hipporag_vec = _vec.get("hipporag") or _hipporag_vec
except Exception:
    pass
DEFAULT_LLM_NAME = _hippo.get("llm_name", _aws.get("bedrock_model", "bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0"))
DEFAULT_EMBEDDING_NAME = _hippo.get("embedding_name", _aws.get("embedding_model", "amazon.titan-embed-text-v2:0"))
DEFAULT_AWS_REGION = _aws.get("region", "us-west-2")
HIPPORAG_DEFAULT_REBUILD = bool(_hipporag_vec.get("rebuild", False))
HIPPORAG_DEFAULT_PERSIST_DIR = str(_cfg.get("output", {}).get("hipporag_index") or DEFAULT_HIPPORAG_SAVE_DIR)


def _ensure_hipporag_importable() -> None:
    """确保可 import hipporag（优先用已安装的包，否则把 HippoRAG/src 加入 sys.path）。"""
    try:
        import hipporag  # type: ignore[import-untyped]  # noqa: F401
        return
    except ImportError:
        pass
    if HIPPORAG_SRC.exists():
        sys.path.insert(0, str(HIPPORAG_SRC))
        try:
            import hipporag  # type: ignore[import-untyped]  # noqa: F401
            return
        except ModuleNotFoundError as e:
            msg = str(e).strip()
            hint = (
                "当前环境缺少 HippoRAG 依赖。请在 **当前激活的环境** 中执行:\n"
                "  pip install transformers python_igraph litellm boto3 einops networkx tiktoken tenacity\n"
                "或安装完整 HippoRAG（项目根下）:\n"
                "  pip install -e HippoRAG\n"
                "若 pip 报错 hash 校验失败，请在新环境中安装。Windows 见 HippoRAG/WINDOWS_SETUP.md（--no-deps + requirements-windows.txt）。"
            )
            raise ModuleNotFoundError(f"{msg}\n\n{hint}") from e
    raise ImportError(
        "无法导入 hipporag。请执行: pip install -e <项目根>/HippoRAG ，或确保 HippoRAG 位于项目根下。"
    )


def load_semantic_chunk_as_docs() -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    从 semantic_chunk/*_for_chunking.json 加载，构造 HippoRAG 所需的 docs 及对应的原始 metadata。
    每条 doc 格式：title\\ncontent（与 sample_corpus.json 一致）。
    返回 (docs, metadata_list)，用于建索引与生成 chunk_metadata.json sidecar。
    """
    if not SEMANTIC_CHUNK_DIR.exists():
        return [], []
    files = list(SEMANTIC_CHUNK_DIR.glob("*_for_chunking.json"))
    if not files:
        return [], []
    docs: List[str] = []
    metas: List[Dict[str, Any]] = []
    for path in sorted(files):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        chunks = data.get("chunks") or []
        doc_meta = data.get("document_metadata") or {}
        doc_name = doc_meta.get("doc_name") or path.stem.replace("_for_chunking", "")
        for ch in chunks:
            meta = ch.get("metadata") or {}
            content = (ch.get("content") or "").strip()
            if not content:
                continue
            title = (meta.get("section_title") or "").strip() or doc_name
            doc = f"{title}\n{content}"
            docs.append(doc)

            chunk_meta = dict(meta)
            chunk_meta.setdefault("doc_name", doc_name)
            chunk_meta.setdefault("source_path", doc_meta.get("source_path", ""))
            chunk_meta.setdefault("markdown_path", doc_meta.get("markdown_path", ""))
            refs = chunk_meta.get("refs_in_chunk", [])
            if isinstance(refs, list):
                chunk_meta["refs_in_chunk"] = ", ".join(refs)
            chunk_meta["content"] = content
            metas.append(chunk_meta)
    return docs, metas


def compute_hipporag_hash_id(text: str) -> str:
    """复现 HippoRAG EmbeddingStore 的 hash_id 计算方式（namespace=chunk）。"""
    return "chunk-" + hashlib.md5(text.encode()).hexdigest()


def build_metadata_sidecar(
    docs: List[str],
    metas: List[Dict[str, Any]],
    output_path: Path,
) -> None:
    """
    构建 hash_id → metadata 的映射文件，供检索时从 sidecar 查元数据（不依赖 ChromaDB）。
    """
    mapping: Dict[str, Dict[str, Any]] = {}
    for doc_text, meta in zip(docs, metas):
        hash_id = compute_hipporag_hash_id(doc_text)
        mapping[hash_id] = meta

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[Metadata Sidecar] 已生成 {len(mapping)} 条映射 → {output_path}")


def load_qa_pair_as_docs() -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    从 qa_pair/*.json 加载，构造 HippoRAG 所需的 docs 及对应最小 metadata。
    每条 doc：问题\\n答案。metadata 供 sidecar 使用，检索时不再「降级」。
    """
    if not QA_PAIR_DIR.exists():
        return [], []
    files = [p for p in QA_PAIR_DIR.glob("*.json") if not p.name.endswith(".metadata.json")]
    if not files:
        return [], []
    docs: List[str] = []
    metas: List[Dict[str, Any]] = []
    for path in sorted(files):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        source = (data.get("metadata") or {}).get("source", path.stem)
        for qa in data.get("qa_pairs") or []:
            q = (qa.get("question") or "").strip()
            a = (qa.get("answer") or "").strip()
            if not q and not a:
                continue
            doc = f"{q}\n{a}" if q else a
            docs.append(doc)
            title = (q[:200] + "…") if len(q) > 200 else q if q else "QA"
            metas.append({
                "doc_name": source,
                "section_title": title,
                "refs_in_chunk": "",
                "content": a or doc,
                "chunk_id": "qa_" + hashlib.md5(doc.encode()).hexdigest()[:12],
                "source_path": "",
                "markdown_path": "",
            })
    return docs, metas


def build_docs(
    semantic_only: bool, qa_only: bool
) -> Tuple[List[str], int, int, List[str], List[Dict[str, Any]]]:
    """
    根据开关加载 semantic_chunk 与/或 qa_pair，返回 (docs, n_semantic, n_qa, all_docs_for_sidecar, all_metas_for_sidecar)。
    sidecar 覆盖全部 docs，便于检索时 semantic 与 QA 结果都有元数据。
    """
    if qa_only:
        sem_docs, sem_metas = [], []
    else:
        sem_docs, sem_metas = load_semantic_chunk_as_docs()
    if semantic_only:
        qa_docs, qa_metas = [], []
    else:
        qa_docs, qa_metas = load_qa_pair_as_docs()
    docs = sem_docs + qa_docs
    all_metas = sem_metas + qa_metas
    return docs, len(sem_docs), len(qa_docs), docs, all_metas


def main() -> None:
    parser = argparse.ArgumentParser(
        description="使用 HippoRAG2 对 phase2 产出的 semantic_chunk/qa_pair 建图并建索引",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--persist-dir",
        type=str,
        default=HIPPORAG_DEFAULT_PERSIST_DIR,
        help="HippoRAG 索引与图存储根目录（默认从 pipeline_config.json output.hipporag_index 读取）",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        default=HIPPORAG_DEFAULT_REBUILD,
        help="强制从头建索引；默认从 pipeline_config.json vectorizing.hipporag.rebuild 读取，通常为增量(False)",
    )
    parser.add_argument(
        "--delete-from-file",
        type=str,
        default=None,
        metavar="PATH",
        help="从文件读取要删除的 passage（每行一条，与建索引时 title\\ncontent 一致），执行删除后退出。用于知识更新时去掉过期内容。",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--semantic-only",
        action="store_true",
        help="仅使用 semantic_chunk，不加载 qa_pair",
    )
    group.add_argument(
        "--qa-only",
        action="store_true",
        help="仅使用 qa_pair，不加载 semantic_chunk",
    )
    # HippoRAG 模型与端点（默认 AWS Bedrock：Claude + Titan，us-west-2）
    parser.add_argument(
        "--llm-name",
        type=str,
        default=DEFAULT_LLM_NAME,
        help="LLM 模型名（OpenIE、QA）。默认 AWS Bedrock Claude",
    )
    parser.add_argument(
        "--embedding-name",
        type=str,
        default=DEFAULT_EMBEDDING_NAME,
        help="Embedding 模型名。默认 AWS Bedrock Titan embed-text-v2",
    )
    parser.add_argument(
        "--aws-region",
        type=str,
        default=DEFAULT_AWS_REGION,
        help="AWS Region（Bedrock LLM 与 Titan 嵌入），默认 us-west-2",
    )
    parser.add_argument(
        "--sidecar-only",
        action="store_true",
        help="仅根据当前 phase2 数据生成 chunk_metadata.json，不调用 HippoRAG index（建好索引后可单独用此选项重建 sidecar）",
    )
    args = parser.parse_args()

    save_dir = args.persist_dir
    Path(save_dir).mkdir(parents=True, exist_ok=True)

    # --sidecar-only：只写 chunk_metadata.json，不加载/调用 HippoRAG
    if args.sidecar_only:
        docs, n_sem, n_qa, docs_for_sidecar, metas_for_sidecar = build_docs(args.semantic_only, args.qa_only)
        if not docs_for_sidecar or not metas_for_sidecar:
            print("✗ 没有可加载数据（请先运行 phase2 生成 semantic_chunk 或 qa_pair）")
            sys.exit(1)
        sidecar_path = Path(save_dir) / "chunk_metadata.json"
        build_metadata_sidecar(docs_for_sidecar, metas_for_sidecar, sidecar_path)
        print("=" * 80)
        print("phase3_hippoRAG_graph: 仅生成 Metadata Sidecar（--sidecar-only）")
        print("=" * 80)
        print(f"semantic passages: {n_sem}  qa passages: {n_qa}  总条数: {len(docs_for_sidecar)}")
        print(f"输出: {sidecar_path}")
        print("=" * 80)
        return

    os.environ.setdefault("AWS_REGION", args.aws_region)
    _ensure_hipporag_importable()
    from hipporag import HippoRAG  # type: ignore[import-untyped]
    from hipporag.utils.config_utils import BaseConfig  # type: ignore[import-untyped]

    def _make_config(corpus_len: int = 0) -> "BaseConfig":
        config_kw: Dict[str, Any] = {
            "save_dir": save_dir,
            "llm_name": args.llm_name,
            "embedding_model_name": args.embedding_name,
            "force_index_from_scratch": args.rebuild,
            "force_openie_from_scratch": args.rebuild,
            "corpus_len": corpus_len,
            "retrieval_top_k": 200,
            "linking_top_k": 5,
            "graph_type": "facts_and_sim_passage_node_unidirectional",
            "openie_mode": "online",
        }
        return BaseConfig(**config_kw)

    # 仅删除：从文件读要删的 passage，执行 delete 后退出
    if args.delete_from_file:
        path = Path(args.delete_from_file)
        if not path.exists():
            print(f"✗ 文件不存在: {path}")
            sys.exit(1)
        docs_to_delete = [
            line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if not docs_to_delete:
            print("✗ 文件中没有有效行（每行一条要删的 passage 全文）")
            sys.exit(1)
        print("=" * 80)
        print("phase3_hippoRAG_graph: 删除指定 passage")
        print("=" * 80)
        print(f"保存目录:   {save_dir}")
        print(f"待删条数:   {len(docs_to_delete)}")
        print()
        hipporag = HippoRAG(global_config=_make_config())
        hipporag.delete(docs_to_delete=docs_to_delete)
        print("✓ 删除完成")
        print("=" * 80)
        return

    docs, n_sem, n_qa, docs_for_sidecar, metas_for_sidecar = build_docs(args.semantic_only, args.qa_only)
    if not docs:
        print("✗ 没有可加载数据（请先运行 phase2 生成 semantic_chunk 或 qa_pair）")
        sys.exit(1)

    sidecar_path = Path(save_dir) / "chunk_metadata.json"
    if docs_for_sidecar and metas_for_sidecar:
        build_metadata_sidecar(docs_for_sidecar, metas_for_sidecar, sidecar_path)

    print("=" * 80)
    print("phase3_hippoRAG_graph: HippoRAG2 知识图索引（默认增量，不传 --rebuild 即只增新）")
    print("=" * 80)
    print(f"semantic_chunk passages: {n_sem}")
    print(f"qa_pair passages:       {n_qa}")
    print(f"总 passages:            {len(docs)}")
    print(f"保存目录:              {args.persist_dir}")
    print(f"强制重建:              {args.rebuild}")
    print(f"LLM:                   {args.llm_name}")
    print(f"Embedding:             {args.embedding_name}")
    print(f"AWS Region:            {args.aws_region}")
    print()

    config = _make_config(corpus_len=len(docs))
    hipporag = HippoRAG(global_config=config)
    print("开始 HippoRAG index（OpenIE + 建图 + 编码；已有 passage 会跳过）...")
    hipporag.index(docs=docs)
    print("✓ HippoRAG 索引完成")
    print(f"  检索与 QA 可使用同一 HippoRAG 实例或从 {save_dir} 加载。")
    print("=" * 80)
    try:
        from pipeline_run_logger import append_run_record
        append_run_record(
            step_id="phase3_hipporag",
            script="phase3_hippoRAG_graph.py",
            status="success",
            detail={"save_dir": str(save_dir), "docs_count": len(docs)},
        )
    except Exception as e:
        print(f"[run_log] 写入运行记录失败: {e}")


if __name__ == "__main__":
    main()
