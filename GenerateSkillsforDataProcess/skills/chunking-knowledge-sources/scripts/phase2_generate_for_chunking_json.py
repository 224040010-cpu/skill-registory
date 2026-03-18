"""
脚本：phase2_generate_for_chunking_json.py

从 phase1 产出的 markdown/*_processed.json 按 section 边界生成「语义分块」JSON，供 phase3_text_QA_vectorize
与 phase3_image_vectorize 读取并向量化。

处理逻辑：
- 输入：data_prepare/markdown/ 下所有 *_processed.json（仅从此目录读取，不递归子目录）。
- 分块规则：以每个 processed.json 的 content.sections 为单位，每个 section 的 title 作为块标题；
  块内容 = 该 section 的 title + content。若某 section 的 content 长度超过 MAX_SECTION_CHARS，则按段落
  做子分块（子块最大 SUB_CHUNK_SIZE 字符，相邻块重叠 SUB_CHUNK_OVERLAP），避免单块过长。
- 文档引用：正文中的 [[DOC_REF name="..."]] 占位符原样保留；每个 chunk 的 metadata 中写入 refs_in_chunk，
  记录该块内出现的引用名列表（去重、保序），便于后续多轮查询与引用解析。
- 输出：data_prepare/semantic_chunk/<source>_for_chunking.json。结构包含 document_metadata、references
  （与 processed 一致）、chunks 数组；每个 chunk 含 metadata（含 refs_in_chunk）与 content（Markdown 文本）。
- 与 phase1 的 DOC_REF 正则一致，便于下游识别占位符。
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List
from common_schema import build_asset_record, stable_version_from_mapping

# 与 phase1 一致的 DOC_REF 占位符正则，便于后续多轮查询识别
DOC_REF_PLACEHOLDER_RE = re.compile(r'\[\[DOC_REF\s+name="([^"]+)"\s*\]\]')


def extract_refs_from_text(text: str) -> List[str]:
    """从正文中提取 [[DOC_REF name="..."] 的引用名列表（去重、保序）。"""
    if not text:
        return []
    seen: set[str] = set()
    refs: List[str] = []
    for m in DOC_REF_PLACEHOLDER_RE.finditer(text):
        name = (m.group(1) or "").strip()
        if name and name not in seen:
            seen.add(name)
            refs.append(name)
    return refs


# 从 pipeline_config.json 的 chunking_md 读取
_chunk_md = {}
try:
    import sys as _sys
    _proj = Path(__file__).resolve().parents[3]
    _configuring = _proj / "skills" / "configuring-pipeline"
    for _p in (_configuring, _proj):
        if str(_p) not in _sys.path:
            _sys.path.insert(0, str(_p))
    from pipeline_config_loader import load_config as _load_cfg
    _chunk_md = _load_cfg(ensure_dirs=False).get("chunking_md") or {}
except Exception:
    pass
MAX_SECTION_CHARS = int(_chunk_md.get("max_section_chars", 6000))
SUB_CHUNK_SIZE = int(_chunk_md.get("sub_chunk_size", 5000))
SUB_CHUNK_OVERLAP = int(_chunk_md.get("sub_chunk_overlap", 200))


def _split_section_content(content: str, max_chars: int = SUB_CHUNK_SIZE, overlap: int = SUB_CHUNK_OVERLAP) -> List[str]:
    """
    将过长的一段正文按段落拆成多块，块长尽量不超过 max_chars，相邻块可 overlap 字符。
    """
    content = (content or "").strip()
    if not content or len(content) <= max_chars:
        return [content] if content else []

    paragraphs = re.split(r"\n\s*\n", content)
    blocks: List[str] = []
    buf: List[str] = []
    buf_len = 0

    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        p_len = len(p) + 2  # +2 for \n\n
        if buf_len + p_len <= max_chars:
            buf.append(p)
            buf_len += p_len
        else:
            if buf:
                block = "\n\n".join(buf)
                blocks.append(block)
                if overlap > 0 and len(block) > overlap:
                    # 保留末尾 overlap 字符与下一块重叠
                    tail = block[-overlap:]
                    buf = [tail]
                    buf_len = len(tail) + 2
                else:
                    buf = []
                    buf_len = 0
                # 若当前段落本身超长，先截断再压入
                while len(p) > max_chars:
                    blocks.append(p[:max_chars])
                    p = p[max_chars - overlap :]
                    p_len = len(p) + 2
            if not buf and p:
                buf.append(p)
                buf_len = p_len
    if buf:
        blocks.append("\n\n".join(buf))
    return blocks


def build_chunks_from_processed(data: Dict[str, Any], max_section_chars: int = MAX_SECTION_CHARS) -> List[Dict[str, Any]]:
    """
    从单份 processed.json 的 content.sections 按 title 分界生成 chunks。
    若某 section 的 content 长度 > max_section_chars，则对该 section 做子分块。
    返回列表：每项为 { "metadata": {...}, "content": "..." }。
    """
    meta = data.get("metadata") or {}
    doc_name = meta.get("source") or meta.get("source_raw") or "unknown"
    sections = (data.get("content") or {}).get("sections") or []
    chunks: List[Dict[str, Any]] = []
    chunk_index = 0

    for sec_idx, sec in enumerate(sections):
        title = (sec.get("title") or "").strip()
        raw_content = (sec.get("content") or "").strip()
        level = int(sec.get("level") or 0)

        if not raw_content and not title:
            continue

        # 标题前缀（保留层级，便于检索）
        title_prefix = f"{'#' * (level + 1)} {title}\n\n" if title else ""

        if len(raw_content) <= max_section_chars:
            # 单块
            content = title_prefix + raw_content
            refs_in_chunk = extract_refs_from_text(content)
            chunks.append({
                "metadata": {
                    "doc_name": doc_name,
                    "chunk_id": f"{doc_name}__chunk_{chunk_index}",
                    "section_title": title,
                    "section_index": sec_idx,
                    "sub_index": 0,
                    "level": level,
                    "char_count": len(content),
                    "source_path": meta.get("source_path"),
                    "markdown_path": meta.get("markdown_path"),
                    "refs_in_chunk": refs_in_chunk,
                },
                "content": content,
            })
            chunk_index += 1
        else:
            # 子分块
            sub_blocks = _split_section_content(raw_content, max_chars=SUB_CHUNK_SIZE, overlap=SUB_CHUNK_OVERLAP)
            for sub_idx, block in enumerate(sub_blocks):
                content = title_prefix + block if sub_idx == 0 else f"{title_prefix}(续 {sub_idx + 1})\n\n{block}"
                refs_in_chunk = extract_refs_from_text(content)
                chunks.append({
                    "metadata": {
                        "doc_name": doc_name,
                        "chunk_id": f"{doc_name}__chunk_{chunk_index}",
                        "section_title": title,
                        "section_index": sec_idx,
                        "sub_index": sub_idx,
                        "level": level,
                        "char_count": len(content),
                        "source_path": meta.get("source_path"),
                        "markdown_path": meta.get("markdown_path"),
                        "refs_in_chunk": refs_in_chunk,
                    },
                    "content": content,
                })
                chunk_index += 1

    return chunks


def generate_for_chunking_json(processed_path: Path, out_path: Path, max_section_chars: int = MAX_SECTION_CHARS) -> Path:
    """
    对单份 _processed.json 生成 _for_chunking.json。
    """
    data = json.loads(processed_path.read_text(encoding="utf-8"))
    meta = data.get("metadata") or {}
    upstream_asset_meta = data.get("asset_meta") or {}
    doc_name = meta.get("source") or meta.get("source_raw") or "unknown"
    knowledge_layer = upstream_asset_meta.get("knowledge_layer") or "normative"

    chunks = build_chunks_from_processed(data, max_section_chars=max_section_chars)
    for chunk in chunks:
        chunk_meta = chunk.get("metadata") or {}
        chunk_meta["knowledge_layer"] = knowledge_layer

    document_metadata = {
        "doc_name": doc_name,
        "source_raw": meta.get("source_raw"),
        "source_path": meta.get("source_path"),
        "markdown_path": meta.get("markdown_path"),
        "processed_at": meta.get("processed_at"),
        "section_count": len((data.get("content") or {}).get("sections") or []),
        "total_chars": meta.get("total_chars"),
        "chunk_count": len(chunks),
        "image_count": meta.get("image_count"),
        "reference_count": meta.get("reference_count"),
        "knowledge_layer": knowledge_layer,
    }

    out_data = {
        "document_metadata": document_metadata,
        "references": data.get("references") or [],
        "chunks": chunks,
    }
    out_data["asset_meta"] = build_asset_record(
        asset_type="semantic_dataset",
        knowledge_layer=knowledge_layer,
        display_name=doc_name,
        source_name=meta.get("source_raw") or doc_name,
        source_path=meta.get("source_path") or "",
        storage_path=out_path,
        version=stable_version_from_mapping(
            {
                "doc_name": doc_name,
                "document_metadata": document_metadata,
                "references": out_data["references"],
                "chunks": chunks,
            }
        ),
        created_at=meta.get("processed_at"),
        updated_at=meta.get("processed_at"),
        pipeline_stage="phase2",
        is_source_of_truth=False,
        stats={
            "chunk_count": len(chunks),
            "section_count": document_metadata["section_count"],
            "image_count": document_metadata["image_count"],
            "reference_count": document_metadata["reference_count"],
            "total_chars": document_metadata["total_chars"],
        },
        attributes={
            "markdown_path": meta.get("markdown_path"),
            "source_raw": meta.get("source_raw"),
        },
    ).to_dict()

    out_path.write_text(json.dumps(out_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def main():
    import sys as _sys
    _proj = Path(__file__).resolve().parents[3]
    _configuring = _proj / "skills" / "configuring-pipeline"
    for _p in (_configuring, _proj):
        if str(_p) not in _sys.path:
            _sys.path.insert(0, str(_p))
    try:
        from pipeline_config_loader import load_config as _load_config
        _cfg = _load_config(ensure_dirs=True)
        markdown_dir = Path(_cfg["intermediate"]["markdown"])
        semantic_chunk_dir = Path(_cfg["intermediate"]["semantic_chunk"])
    except Exception:
        _dp = Path(__file__).resolve().parents[1]
        _pd = _dp / "processed_data"
        markdown_dir = _pd / "markdown"
        semantic_chunk_dir = _pd / "semantic_chunk"

    parser = argparse.ArgumentParser(description="从 markdown/*_processed.json 生成 semantic_chunk/*_for_chunking.json")
    parser.add_argument(
        "--file",
        "-f",
        type=str,
        default=None,
        help="只处理指定文件。可写文件名（如 典型问题汇总）或带 _processed.json 的完整名",
    )
    args = parser.parse_args()

    if args.file:
        stem = args.file.strip().replace("_processed.json", "").replace(".json", "").rstrip("_processed")
        p = markdown_dir / f"{stem}_processed.json"
        if not p.exists():
            print(f"✗ 文件不存在: {p}")
            return
        processed_files = [p]
        print(f"仅处理: {p.name}")
    else:
        processed_files = list(markdown_dir.glob("*_processed.json"))
        print(f"从 markdown 文件夹找到 {len(processed_files)} 个 _processed.json 文件")

    semantic_chunk_dir.mkdir(parents=True, exist_ok=True)
    print(f"输出目录: {semantic_chunk_dir}")

    for p in sorted(processed_files):
        stem = p.stem.replace("_processed", "")
        out_path = semantic_chunk_dir / f"{stem}_for_chunking.json"
        try:
            generate_for_chunking_json(p, out_path)
            print(f"  生成: {out_path.name}")
        except Exception as e:
            print(f"  跳过 {p.name}: {e}")

    print("完成。")
    try:
        from pipeline_run_logger import append_run_record
        append_run_record(
            step_id="phase2_for_chunking",
            script="phase2_generate_for_chunking_json.py",
            status="success",
            files_processed=len(processed_files),
            detail={"output_dir": str(semantic_chunk_dir)},
        )
    except Exception as e:
        print(f"[run_log] 写入运行记录失败: {e}")


if __name__ == "__main__":
    main()
